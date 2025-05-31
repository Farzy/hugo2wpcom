import pytest
import os
from unittest.mock import MagicMock
from bs4 import BeautifulSoup # For constructing expected output if needed, or verifying structure

from hugo2wpcom.html_processor import process_html_images

@pytest.fixture
def mock_uploader_func(mocker):
    """Fixture for a mock uploader function."""
    uploader = mocker.MagicMock(name="mock_upload_image_to_wordpress")
    def side_effect_uploader(session, site_id, image_path, image_name):
        # Simulate successful upload, return dict with URL
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
]

@pytest.mark.parametrize("html_input, img_src, path_exists_val, base_dir, static_dir, expect_upload", HTML_WITH_IMAGES_CASES)
def test_process_html_images(mocker, mock_uploader_func, html_input, img_src, path_exists_val, base_dir, static_dir, expect_upload):
    site_id = "example.com"
    session_mock = MagicMock() # Mock session, not strictly used by uploader mock but passed

    # Mock os.path.exists and os.path.isdir
    mocker.patch('os.path.exists', return_value=path_exists_val)
    # Make os.path.isdir also configurable for the static_path check
    mocker.patch('os.path.isdir', lambda path_arg: path_arg == static_dir if static_dir else False)


    processed_html = process_html_images(
        html_input,
        base_dir, # base_dir_for_images
        session_mock,
        site_id,
        static_dir, # hugo_static_path
        mock_uploader_func
    )

    soup = BeautifulSoup(processed_html, 'html.parser')
    img_tag = soup.find('img')
    assert img_tag is not None # Ensure there's an image tag to check

    if expect_upload:
        # Verify uploader was called
        mock_uploader_func.assert_called_once()
        args, _ = mock_uploader_func.call_args
        _session, _site_id, resolved_image_path, image_filename = args

        assert _site_id == site_id
        assert image_filename == os.path.basename(img_src)

        # Verify resolved path based on type of src
        if img_src.startswith('/'):
            assert resolved_image_path == os.path.join(static_dir, img_src.lstrip('/'))
        else:
            assert resolved_image_path == os.path.abspath(os.path.join(base_dir, img_src))

        # Verify src attribute was updated
        expected_new_src = f"https://{site_id}.files.wordpress.com/uploads/{os.path.basename(img_src)}_uploaded.jpg"
        assert img_tag['src'] == expected_new_src
    else:
        # Verify uploader was NOT called (or called if path_exists but upload failed - though mock always succeeds)
        if img_src.startswith("http") or not path_exists_val or \
           (img_src.startswith("/") and (not static_dir or not os.path.isdir(static_dir))):
            mock_uploader_func.assert_not_called()
            assert img_tag['src'] == img_src # Src should remain original
        # (If we had a case for path_exists_val=True but uploader fails, we'd test that too)


def test_process_html_images_no_images():
    """Test HTML with no images."""
    html_input = "<p>Some text but no images.</p>"
    processed_html = process_html_images(html_input, "content", MagicMock(), "site.id", "/static", MagicMock())
    assert processed_html == html_input

def test_process_html_empty_and_none_input():
    assert process_html_images("", "content", MagicMock(), "site.id", "/static", MagicMock()) == ""
    # Assuming the function is robust to None html_content, though type hints suggest str
    # If it's not designed for None, this test might need adjustment or the function made more robust.
    # Based on current implementation: if not html_content: return ""
    assert process_html_images(None, "content", MagicMock(), "site.id", "/static", MagicMock()) == ""


def test_process_html_image_with_srcset_removed(mocker, mock_uploader_func):
    """Test that srcset is removed when src is updated."""
    html_input = '<p><img src="local.jpg" srcset="local-300.jpg 300w, local-600.jpg 600w" alt="Test"></p>'
    base_dir = "content/posts"
    static_dir = "/path/to/static" # Not used for this relative path
    site_id = "example.com"

    mocker.patch('os.path.exists', return_value=True)
    mocker.patch('os.path.isdir', return_value=True) # Assume static_dir is valid if checked

    processed_html = process_html_images(html_input, base_dir, MagicMock(), site_id, static_dir, mock_uploader_func)
    soup = BeautifulSoup(processed_html, 'html.parser')
    img_tag = soup.find('img')

    assert img_tag is not None
    assert img_tag['src'] == f"https://{site_id}.files.wordpress.com/uploads/local.jpg_uploaded.jpg"
    assert not img_tag.has_attr('srcset') # srcset should be removed
    mock_uploader_func.assert_called_once()

# Add more tests:
# - Multiple images in one HTML doc
# - Image src with query parameters or fragments (current logic might include them in filename)
# - Unicode characters in image paths/names
# - Case sensitivity if relevant for os.path.exists on the target OS (though mocks control it here)
