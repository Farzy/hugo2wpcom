import pytest
from unittest.mock import MagicMock, patch
import requests # For requests.exceptions

from hugo2wpcom.wp_post_creator import create_wordpress_post

@pytest.fixture
def mock_session(mocker):
    """Fixture for a mock session object with a post method."""
    session = MagicMock(spec=requests.Session) # Or OAuth2Session if that's what's used
    session.post = MagicMock()
    return session

def test_create_wordpress_post_success(mock_session):
    """Test successful post creation."""
    site_id = "example.com"
    title = "Test Post Title"
    content_html = "<p>Test content.</p>"
    status = "publish"
    date_iso = "2024-07-15T10:00:00Z"
    categories = ["Tech", "Tests"]
    tags = ["pytest", "mocking"]
    hugo_meta = {"original_slug": "test-post"}

    # Mock the response from session.post
    mock_response = MagicMock()
    mock_response.status_code = 200 # Or 201, depending on typical WP API success
    mock_response.json.return_value = {
        "ID": 123,
        "URL": f"https://{site_id}/test-post-title",
        "status": status,
        "title": title,
        # ... other fields
    }
    mock_session.post.return_value = mock_response

    result = create_wordpress_post(
        session=mock_session,
        site_id=site_id,
        title=title,
        content_html=content_html,
        status=status,
        date=date_iso,
        categories=categories,
        tags=tags,
        hugo_metadata=hugo_meta
    )

    assert result is not None
    assert result["ID"] == 123
    assert result["URL"] == f"https://{site_id}/test-post-title"

    expected_url = f"https://public-api.wordpress.com/rest/v1.1/sites/{site_id}/posts/new"
    expected_payload = {
        'title': title,
        'content': content_html,
        'status': status,
        'date': date_iso,
        'categories': categories,
        'tags': tags
    }
    mock_session.post.assert_called_once_with(expected_url, json=expected_payload)
    mock_response.raise_for_status.assert_called_once()


def test_create_wordpress_post_minimal_data_success(mock_session):
    """Test successful post creation with minimal data (no date, categories, tags)."""
    site_id = "test.blog"
    title = "Minimal Post"
    content_html = "<p>Keep it simple.</p>"
    # status defaults to 'draft' in function signature

    mock_response = MagicMock()
    mock_response.json.return_value = {"ID": 456, "URL": f"https://{site_id}/minimal-post", "status": "draft"}
    mock_session.post.return_value = mock_response

    result = create_wordpress_post(
        session=mock_session,
        site_id=site_id,
        title=title,
        content_html=content_html
        # status, date, categories, tags will use defaults or be None
    )

    assert result is not None
    assert result["ID"] == 456
    assert result["status"] == "draft"

    expected_payload = {
        'title': title,
        'content': content_html,
        'status': 'draft', # Default status
        # date, categories, tags should not be in payload if None
    }
    mock_session.post.assert_called_once_with(
        f"https://public-api.wordpress.com/rest/v1.1/sites/{site_id}/posts/new",
        json=expected_payload
    )

@pytest.mark.parametrize("error_exception, response_content, response_status", [
    (requests.exceptions.HTTPError("Client Error"), {"error": "invalid_scope", "message": "Insufficient scope."}, 403),
    (requests.exceptions.HTTPError("Server Error"), "Internal Server Error text", 500), # Non-JSON error
    (requests.exceptions.RequestException("Connection Timeout"), None, None), # No response object
    (ValueError("JSON Decode Error"), "Malformed JSON", 200) # HTTP status ok, but bad JSON
])
def test_create_wordpress_post_api_errors(mock_session, capsys, error_exception, response_content, response_status):
    """Test handling of various API errors."""
    site_id = "error.site"

    mock_api_response = MagicMock()
    if response_status:
      mock_api_response.status_code = response_status
    if isinstance(response_content, dict):
        mock_api_response.json.return_value = response_content
        # if error is ValueError for JSON decoding, make .json() raise it
        if isinstance(error_exception, ValueError):
             mock_api_response.json.side_effect = error_exception
    else: # Non-JSON response
        mock_api_response.text = response_content
        mock_api_response.json.side_effect = ValueError("Simulated JSON decode error for non-JSON text")


    # Configure the mock session.post call
    if isinstance(error_exception, requests.exceptions.HTTPError):
        error_exception.response = mock_api_response # Attach response to HTTPError
        mock_session.post.return_value = mock_api_response # For raise_for_status
        mock_api_response.raise_for_status.side_effect = error_exception # raise_for_status is what throws
    elif isinstance(error_exception, requests.exceptions.RequestException): # e.g. ConnectionTimeout
        mock_session.post.side_effect = error_exception
    elif isinstance(error_exception, ValueError): # JSON Decode Error
        mock_session.post.return_value = mock_api_response # HTTP call is fine, but JSON parsing fails
        # The .json() call inside the function will raise this.

    result = create_wordpress_post(
        session=mock_session,
        site_id=site_id,
        title="Error Test Post",
        content_html="<p>Error content.</p>"
    )

    assert result is None
    captured = capsys.readouterr() # Check logged output

    if isinstance(error_exception, requests.exceptions.HTTPError):
        assert "HTTP error during post creation" in captured.out
        if response_status: assert str(response_status) in captured.out # Check if status code is logged
        if isinstance(response_content, dict): # JSON error from WP
            assert response_content["message"] in captured.out
        elif response_content: # Plain text error
            assert response_content in captured.out
    elif isinstance(error_exception, requests.exceptions.RequestException):
        assert "Request error during post creation" in captured.out
    elif isinstance(error_exception, ValueError): # JSON Decode Error
        assert "JSON decoding error during post creation" in captured.out
        if response_content: # The malformed content that was attempted to be parsed
            assert response_content in captured.out


def test_create_wordpress_post_categories_tags_as_comma_separated_string_in_payload(mock_session):
    """
    Test that if categories/tags are internally represented as comma-separated strings by some
    older version of the API or a specific requirement, the payload reflects that.
    NOTE: Current implementation sends them as lists. This test would need adjustment
    if payload format for categories/tags changes (e.g., to comma-separated strings).
    For now, this test verifies list format.
    """
    site_id = "example.com"
    title = "Tag Category Test"
    content_html = "<p>Content</p>"
    categories = ["List Cat 1", "List Cat 2"]
    tags = ["List Tag 1"]

    mock_response = MagicMock()
    mock_response.json.return_value = {"ID": 789, "URL": "..."}
    mock_session.post.return_value = mock_response

    create_wordpress_post(
        session=mock_session, site_id=site_id, title=title, content_html=content_html,
        categories=categories, tags=tags
    )

    args, kwargs = mock_session.post.call_args
    payload = kwargs.get('json')
    assert payload is not None
    assert payload['categories'] == categories # Expecting a list
    assert payload['tags'] == tags           # Expecting a list
    # If API required comma-sep string:
    # assert payload['categories'] == "List Cat 1,List Cat 2"
    # assert payload['tags'] == "List Tag 1"
