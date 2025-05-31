import pytest
import os
from unittest.mock import MagicMock
from urllib.parse import urlparse # Import urlparse for test adjustments
from bs4 import BeautifulSoup

from hugo2wpcom.html_processor import process_html_images

@pytest.fixture
def mock_uploader_func(mocker):
    """Fixture for a mock uploader function that now accepts dry_run."""
    uploader = mocker.MagicMock(name="mock_upload_image_to_wordpress")
    # Update signature to include dry_run
    def side_effect_uploader(session, site_id, image_path, image_name, dry_run=False):
        # The mock's behavior doesn't need to change based on dry_run for these tests,
        # as we're testing process_html_images's handling of the uploader's *return value*.
        # It just needs to accept the argument.
        return {"URL": f"https://{site_id}.files.wordpress.com/uploads/{image_name}_uploaded.jpg"}
    uploader.side_effect = side_effect_uploader
    return uploader

# Test cases for various image src patterns
HTML_WITH_IMAGES_CASES = [
    # 1. Relative image path, co-located with content
    ("<p><img src=\"image1.jpg\" alt=\"Test Image 1\"></p>", "image1.jpg", True, "content/posts", "/path/to/static", True),
    # 2. Relative image path, ../ up one level
    ("<p><img src=\"../images/image2.png\" alt=\"Test Image 2\"></p>", "../images/image2.png", True, "content/posts/subdir", "/path/to/static", True),
    # 3. Absolute image path (relative to static_path)
    ("<p><img src=\"/img/static_image.gif\" alt=\"Static Image\"></p>", "/img/static_image.gif", True, "content/posts", "/path/to/hugo/static", True),
    # 4. Image that does not exist locally
    ("<p><img src=\"nonexistent.png\" alt=\"Non Existent\"></p>", "nonexistent.png", False, "content/posts", "/path/to/static", False), # os.path.exists returns False
    # 5. External image (should be skipped)
    ("<p><img src=\"http://example.com/remote.jpg\" alt=\"Remote Image\"></p>", "http://example.com/remote.jpg", False, "content/posts", "/path/to/static", False), # uploader not called
    # 6. Image with leading slash, but static_path is None (should not resolve/upload)
    ("<p><img src=\"/img/static_image_no_static_path.gif\" alt=\"No Static Path\"></p>", "/img/static_image_no_static_path.gif", False, "content/posts", None, False), # os.path.exists effectively false
    # 7. Image with leading slash, static_path is not a directory
    ("<p><img src=\"/img/static_image_static_not_dir.gif\" alt=\"Static Not Dir\"></p>", "/img/static_image_static_not_dir.gif", False, "content/posts", "/path/to/static/file.txt", False), # os.path.isdir for static_path returns False
    # 8. Relative image path with a fragment
    ("<p><img src=\"image1.jpg#section1\" alt=\"Image with fragment\"></p>", "image1.jpg#section1", True, "content/posts", "/path/to/static", True),
    # 9. Absolute image path with a fragment
    ("<p><img src=\"/img/static_image.gif#header\" alt=\"Static with fragment\"></p>", "/img/static_image.gif#header", True, "content/posts", "/path/to/hugo/static", True),
    # 10. Relative image path with query parameters (should also be stripped by .path)
    ("<p><img src=\"image_query.png?v=123\" alt=\"Image with query\"></p>", "image_query.png?v=123", True, "content/posts", "/path/to/static", True),

]

@pytest.mark.parametrize("html_input, original_img_src_in_html, path_exists_val, base_dir, static_dir, expect_upload", HTML_WITH_IMAGES_CASES)
def test_process_html_images(mocker, mock_uploader_func, html_input, original_img_src_in_html, path_exists_val, base_dir, static_dir, expect_upload):
    site_id = "example.com"
    session_mock = MagicMock() # Mock session, not strictly used by uploader mock but passed

    # Mock os.path.exists and os.path.isdir
    mocker.patch('os.path.exists', return_value=path_exists_val)
    # Make os.path.isdir also configurable for the static_path check
    mocker.patch('os.path.isdir', lambda path_arg: path_arg == static_dir if static_dir else False)

    # process_html_images now returns a tuple (html, count)
    # and takes a dry_run argument. For existing tests, assume dry_run=False.
    processed_html, uploaded_count = process_html_images(
        html_input,
        base_dir, # base_dir_for_images
        session_mock,
        site_id,
        static_dir, # hugo_static_path
        mock_uploader_func,
        dry_run=False # Explicitly pass dry_run
    )

    soup = BeautifulSoup(processed_html, 'html.parser')
    img_tag = soup.find('img')
    assert img_tag is not None # Ensure there's an image tag to check

    if expect_upload:
        # Verify uploader was called
        mock_uploader_func.assert_called_once()
        # Check call arguments, now including dry_run (which should be False here)
        args, _ = mock_uploader_func.call_args
        _session, _site_id, resolved_image_path, image_filename_for_upload, _dry_run_arg = args

        cleaned_path_from_original_src = urlparse(original_img_src_in_html).path

        assert _site_id == site_id
        assert image_filename_for_upload == os.path.basename(cleaned_path_from_original_src)
        assert _dry_run_arg is False # Ensure dry_run was passed as False

        # Verify resolved path based on the cleaned version of original_img_src_in_html
        if cleaned_path_from_original_src.startswith('/'):
            assert resolved_image_path == os.path.join(static_dir, cleaned_path_from_original_src.lstrip('/'))
        else:
            assert resolved_image_path == os.path.abspath(os.path.join(base_dir, cleaned_path_from_original_src))

        # Verify src attribute was updated in the HTML output
        # The new URL should be based on the basename of the cleaned path
        expected_new_src = f"https://{site_id}.files.wordpress.com/uploads/{os.path.basename(cleaned_path_from_original_src)}_uploaded.jpg"
        assert img_tag['src'] == expected_new_src
    else:
        # Verify uploader was NOT called
        # Conditions for not calling: external, path doesn't exist, or absolute path with invalid static_dir
        if original_img_src_in_html.startswith("http") or \
           not path_exists_val or \
           (original_img_src_in_html.startswith("/") and (not static_dir or not os.path.isdir(static_dir))):
            mock_uploader_func.assert_not_called()
            assert img_tag['src'] == original_img_src_in_html # Src should remain original
        # (If we had a case for path_exists_val=True but uploader fails, this part might need adjustment)


def test_process_html_images_no_images():
    """Test HTML with no images."""
    html_input = "<p>Some text but no images.</p>"
    # Pass dry_run=False, expect 0 images uploaded
    processed_html, count = process_html_images(html_input, "content", MagicMock(), "site.id", "/static", MagicMock(), dry_run=False)
    assert processed_html == html_input
    assert count == 0

def test_process_html_empty_and_none_input():
    # Pass dry_run=False, expect 0 images uploaded
    html_empty, count_empty = process_html_images("", "content", MagicMock(), "site.id", "/static", MagicMock(), dry_run=False)
    assert html_empty == ""
    assert count_empty == 0

    html_none, count_none = process_html_images(None, "content", MagicMock(), "site.id", "/static", MagicMock(), dry_run=False)
    assert html_none == ""
    assert count_none == 0


def test_process_html_image_with_srcset_removed(mocker, mock_uploader_func):
    """Test that srcset is removed when src is updated."""
    html_input = '<p><img src="local.jpg" srcset="local-300.jpg 300w, local-600.jpg 600w" alt="Test"></p>'
    base_dir = "content/posts"
    static_dir = "/path/to/static" # Not used for this relative path
    site_id = "example.com"

    mocker.patch('os.path.exists', return_value=True)
    mocker.patch('os.path.isdir', return_value=True) # Assume static_dir is valid if checked

    # Pass dry_run=False
    processed_html, count = process_html_images(html_input, base_dir, MagicMock(), site_id, static_dir, mock_uploader_func, dry_run=False)
    soup = BeautifulSoup(processed_html, 'html.parser')
    img_tag = soup.find('img')

    assert img_tag is not None
    assert img_tag['src'] == f"https://{site_id}.files.wordpress.com/uploads/local.jpg_uploaded.jpg"
    assert not img_tag.has_attr('srcset') # srcset should be removed
    assert count == 1 # One image should have been "uploaded"
    mock_uploader_func.assert_called_once()

# Add more tests:
# - Multiple images in one HTML doc
# - Image src with query parameters or fragments (current logic might include them in filename)
# - Unicode characters in image paths/names
# - Case sensitivity if relevant for os.path.exists on the target OS (though mocks control it here)
