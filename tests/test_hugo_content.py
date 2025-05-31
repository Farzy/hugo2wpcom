import pytest
import os
from unittest.mock import mock_open, patch, MagicMock # For older style patch if needed
import frontmatter # To mock its methods

from hugo2wpcom.hugo_content import parse_hugo_file, scan_hugo_content_path, HugoPost

@pytest.fixture
def mock_frontmatter_post():
    post = MagicMock(spec=frontmatter.Post)
    post.metadata = {'title': 'Test Title', 'date': '2024-01-01'}
    post.content = "This is the content."
    return post

def test_parse_hugo_file_success(mocker, mock_frontmatter_post):
    """Test successful parsing of a Hugo file."""
    file_path = "/fake/path/test_post.md"
    mocker.patch('builtins.open', mock_open(read_data="---\ntitle: Test Title\ndate: 2024-01-01\n---\nThis is the content."))
    mocker.patch('frontmatter.load', return_value=mock_frontmatter_post)

    result = parse_hugo_file(file_path)

    assert result is not None
    assert result['filepath'] == file_path
    assert result['metadata']['title'] == "Test Title"
    assert result['content'] == "This is the content."
    frontmatter.load.assert_called_once()

def test_parse_hugo_file_io_error(mocker, capsys):
    """Test handling of IOError when file cannot be opened."""
    file_path = "/fake/path/non_existent.md"
    mocker.patch('builtins.open', side_effect=IOError("File not found"))

    result = parse_hugo_file(file_path)

    assert result is None
    captured = capsys.readouterr()
    assert f"Error reading file {file_path}: File not found" in captured.out

def test_parse_hugo_file_frontmatter_error(mocker, capsys):
    """Test handling of errors during frontmatter parsing."""
    file_path = "/fake/path/bad_frontmatter.md"
    mocker.patch('builtins.open', mock_open(read_data="---\ntitle: Invalid\n K YAML\n---\nContent"))
    # Simulate an error during frontmatter.load, e.g., YAMLParseException or any Exception
    mocker.patch('frontmatter.load', side_effect=Exception("YAML parsing error"))

    result = parse_hugo_file(file_path)

    assert result is None
    captured = capsys.readouterr()
    assert f"Error parsing frontmatter from file {file_path}: YAML parsing error" in captured.out

def test_scan_hugo_content_path_valid_path(mocker, mock_frontmatter_post):
    """Test scanning a directory with Markdown files."""
    content_path = "/fake/hugo_content"

    # Mock os.walk to simulate a directory structure
    mock_walk_data = [
        (content_path, ['subdir'], ['file1.md', 'file2.txt']),
        (os.path.join(content_path, 'subdir'), [], ['file3.md', 'image.jpg']),
    ]
    mocker.patch('os.walk', return_value=mock_walk_data)
    mocker.patch('os.path.exists', return_value=True)
    mocker.patch('os.path.isdir', return_value=True)

    # Mock parse_hugo_file to return a consistent result for .md files
    # We're testing scan_hugo_content_path's logic, not parse_hugo_file here again
    parsed_post_mock = {
        'metadata': {'title': 'Mocked Post'},
        'content': 'Mocked content',
        'filepath': '' # Will be set by the loop
    }

    def side_effect_parse_hugo_file(filepath_arg):
        # Create a new dict for each call to avoid modifying the same mock object
        current_post_mock = parsed_post_mock.copy()
        current_post_mock['filepath'] = filepath_arg
        return current_post_mock

    m_parse_hugo_file = mocker.patch('hugo2wpcom.hugo_content.parse_hugo_file', side_effect=side_effect_parse_hugo_file)

    results = scan_hugo_content_path(content_path)

    assert len(results) == 2 # file1.md and file3.md
    assert results[0]['filepath'] == os.path.join(content_path, 'file1.md')
    assert results[1]['filepath'] == os.path.join(content_path, 'subdir', 'file3.md')
    assert m_parse_hugo_file.call_count == 2
    m_parse_hugo_file.assert_any_call(os.path.join(content_path, 'file1.md'))
    m_parse_hugo_file.assert_any_call(os.path.join(content_path, 'subdir', 'file3.md'))

def test_scan_hugo_content_path_empty_dir(mocker):
    """Test scanning an empty directory."""
    content_path = "/fake/empty_content"
    mocker.patch('os.walk', return_value=[(content_path, [], [])]) # Empty dir
    mocker.patch('os.path.exists', return_value=True)
    mocker.patch('os.path.isdir', return_value=True)
    m_parse_hugo_file = mocker.patch('hugo2wpcom.hugo_content.parse_hugo_file')

    results = scan_hugo_content_path(content_path)

    assert len(results) == 0
    m_parse_hugo_file.assert_not_called()

def test_scan_hugo_content_path_invalid_path(capsys):
    """Test scanning a non-existent or non-directory path."""
    content_path_non_existent = "/fake/non_existent_path"
    with patch('os.path.exists', return_value=False):
      results_non_existent = scan_hugo_content_path(content_path_non_existent)
      assert len(results_non_existent) == 0
      captured = capsys.readouterr()
      assert f"Error: Hugo content path '{content_path_non_existent}' does not exist." in captured.out

    content_path_is_file = "/fake/is_a_file"
    with patch('os.path.exists', return_value=True), \
         patch('os.path.isdir', return_value=False):
      results_is_file = scan_hugo_content_path(content_path_is_file)
      assert len(results_is_file) == 0
      captured = capsys.readouterr()
      assert f"Error: Hugo content path '{content_path_is_file}' is not a directory." in captured.out

def test_scan_hugo_content_path_parse_returns_none(mocker):
    """Test that scan filters out None results from parse_hugo_file."""
    content_path = "/fake/hugo_content"
    mocker.patch('os.walk', return_value=[(content_path, [], ['good.md', 'bad.md'])])
    mocker.patch('os.path.exists', return_value=True)
    mocker.patch('os.path.isdir', return_value=True)

    def side_effect_parse(filepath):
        if "good" in filepath:
            return {'metadata': {}, 'content': '', 'filepath': filepath}
        return None # Simulate parsing error for bad.md
    mocker.patch('hugo2wpcom.hugo_content.parse_hugo_file', side_effect=side_effect_parse)

    results = scan_hugo_content_path(content_path)
    assert len(results) == 1
    assert results[0]['filepath'] == os.path.join(content_path, 'good.md')
