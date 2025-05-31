import json
import requests
from typing import Dict, Any, List, Optional

def create_wordpress_post(
    session: Any,
    site_id: str,
    title: str,
    content_html: str,
    status: Optional[str] = 'draft',
    date: Optional[str] = None,
    categories: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    hugo_metadata: Optional[Dict[str, Any]] = None,
    dry_run: bool = False # Added dry_run parameter
) -> Optional[Dict[str, Any]]:
    """
    Creates a new post on WordPress.com using the REST API.
    If dry_run is True, simulates post creation.

    Args:
        session: The authenticated session object.
        site_id: The WordPress.com site ID.
        title: The title of the post.
        content_html: The HTML content of the post.
        status: Post status. Defaults to 'draft'.
        date: Publication date in ISO 8601 format.
        categories: List of category names.
        tags: List of tag names.
        hugo_metadata: Full Hugo front matter.
        dry_run: If True, simulate without making live API calls.

    Returns:
        A dictionary representing the JSON response from WordPress or a simulated
        response in dry_run mode, or None if an error occurs in live mode.
    """
    payload: Dict[str, Any] = {
        'title': title,
        'content': content_html,
        'status': status,
    }
    if date:
        payload['date'] = date
    if categories:
        payload['categories'] = categories
    if tags:
        payload['tags'] = tags

    if dry_run:
        print(f"\n[DRY RUN] Would create WordPress post:")
        print(f"  Site ID: {site_id}")
        print(f"  Title: {title}")
        print(f"  Status: {status}")
        if date: print(f"  Date: {date}")
        if categories: print(f"  Categories: {categories}")
        if tags: print(f"  Tags: {tags}")

        log_payload_display = {k: (v[:100] + "..." if k == 'content' and isinstance(v, str) and len(v) > 100 else v) for k, v in payload.items()}
        print(f"  [DRY RUN] Payload (simulated request body):")
        try:
            print(json.dumps(log_payload_display, indent=2))
        except TypeError:
            print(log_payload_display)

        simulated_post_id = abs(hash(title + (date or ""))) % 10000
        simulated_post_url = f"https://{site_id.split('.')[0] if '.' in site_id else site_id}.wordpress.com/dry_run/{simulated_post_id}/{title.lower().replace(' ', '-')}"
        print(f"  [DRY RUN] Simulated success! Post would be created with ID: {simulated_post_id}")
        return {
            "ID": simulated_post_id,
            "URL": simulated_post_url,
            "status": status,
            "title": title,
            "guid": f"https://{site_id.split('.')[0] if '.' in site_id else site_id}.wordpress.com/?p={simulated_post_id}_dry_run",
            "dry_run_success": True
        }

    # Live mode
    post_creation_url = f"https://public-api.wordpress.com/rest/v1.1/sites/{site_id}/posts/new"
    print(f"\nCreating WordPress post:")
    print(f"  Site ID: {site_id}")
    print(f"  Title: {title}")
    print(f"  Status: {status}")
    if date: print(f"  Date: {date}")
    if categories: print(f"  Categories: {categories}")
    if tags: print(f"  Tags: {tags}")
    print(f"  Content HTML (snippet): {content_html[:200]}...")

    try:
        response = session.post(post_creation_url, json=payload)
        response.raise_for_status()
        response_json = response.json()
        print(f"Successfully created post. ID: {response_json.get('ID')}, URL: {response_json.get('URL')}")
        return response_json
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error during post creation: {e}")
        if e.response is not None:
            print(f"Response status code: {e.response.status_code}")
            try:
                error_details = e.response.json()
                print(f"Error details: {json.dumps(error_details, indent=2)}")
            except ValueError:
                print(f"Response content: {e.response.text}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Request error during post creation: {e}")
        return None
    except ValueError as e:
        print(f"JSON decoding error during post creation: {e}")
        if 'response' in locals() and response is not None:
             print(f"Response content: {response.text}")
        return None
