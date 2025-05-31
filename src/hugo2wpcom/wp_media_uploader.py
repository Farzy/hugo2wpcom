import os
import requests
from typing import Dict, Any, Optional

def upload_image_to_wordpress(
    session: Any,
    site_id: str,
    image_path: str,
    image_name: str,
    dry_run: bool = False  # Added dry_run parameter
) -> Optional[Dict[str, Any]]:
    """
    Uploads an image to WordPress.com using the REST API.
    If dry_run is True, simulates the upload.

    Args:
        session: The authenticated requests.Session or OAuth2Session object.
        site_id: The WordPress.com site ID or domain.
        image_path: The local path to the image file.
        image_name: The desired name for the image on WordPress.
        dry_run: If True, simulate the upload without making live API calls.

    Returns:
        A dictionary containing the details of the uploaded media item (e.g., URL, ID)
        if successful or in dry_run mode, or None if an error occurs in live mode.
    """
    if not os.path.exists(image_path):
        print(f"Error: Image file not found at {image_path}")
        return None

    if dry_run:
        print(f"[DRY RUN] Would upload image '{image_name}' from '{image_path}' to WordPress site '{site_id}'.")
        # Simulate a successful upload and return a placeholder URL
        placeholder_url = f"https://{site_id.split('.')[0] if '.' in site_id else site_id}.files.wordpress.com/2024/dry_run/{image_name.replace(' ', '_')}_placeholder.jpg"
        print(f"  [DRY RUN] Simulated success! Image would be available at: {placeholder_url}")
        return {
            "URL": placeholder_url,
            "id": "dry_run_12345",
            "mime_type": "image/jpeg", # Example mime type
            "dry_run_success": True
        }

    media_upload_url = f"https://public-api.wordpress.com/rest/v1.1/sites/{site_id}/media/new"

    files = None
    try:
        with open(image_path, 'rb') as f:
            files = {'media[]': (image_name, f.read())} # Read content for requests

        print(f"Uploading image '{image_name}' from '{image_path}' to WordPress site '{site_id}'...")
        response = session.post(media_upload_url, files=files)
        response.raise_for_status()  # Raises HTTPError for bad responses (4XX or 5XX)
        response_json = response.json()

        if response_json and 'media' in response_json and len(response_json['media']) > 0:
            uploaded_media_item = response_json['media'][0]
            print(f"Successfully uploaded image. URL: {uploaded_media_item.get('URL')}, ID: {uploaded_media_item.get('ID')}")
            return uploaded_media_item
        else:
            print(f"Error: Media upload response did not contain expected data. Response: {response_json}")
            return None

    except requests.exceptions.HTTPError as e:
        print(f"HTTP error during media upload: {e}")
        if e.response is not None:
            print(f"Response content: {e.response.content}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Request error during media upload: {e}")
        return None
    except ValueError as e: # Includes JSONDecodeError
        print(f"JSON decoding error during media upload: {e}")
        if 'response' in locals() and response is not None:
             print(f"Response content: {response.text}")
        return None
    except IOError as e:
        print(f"IOError during image file handling for {image_path}: {e}")
        return None
    # 'finally' block for closing file is not needed due to 'with open()'
    # However, the 'files' dict for requests takes the file object directly,
    # and requests should handle closing it.
    # For clarity and to ensure, if we passed file object:
    # files = {'media[]': (image_name, open(image_path, 'rb'))}
    # then a finally block for files['media[]'][1].close() would be good if not using 'with'.
    # Current code reads bytes into memory: files = {'media[]': (image_name, f.read())}
    # So, the 'with open' correctly handles the file object f.
    # The previous version had a 'finally' that was a bit misleading with current `files` construction.
    # The version before that which I wrote: `files = {'media[]': (image_name, open(image_path, 'rb'))}`
    # and then `files['media[]'][1].close()` in finally.
    # `requests` documentation suggests it handles closing file objects passed in `files` if they are opened by `requests` itself,
    # but if we open it, we should close it.
    # The `f.read()` approach is safer as the file is closed immediately after read.
    # Reverted to f.read() to avoid complexity with file handles in requests.
