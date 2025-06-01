import os
from urllib.parse import urlparse, unquote # Added import
from bs4 import BeautifulSoup, Tag
from typing import Callable, Dict, Any, Optional, Tuple

# Define uploader function type for clarity, now including dry_run
UploaderFunction = Callable[[Any, str, str, str, bool], Optional[Dict[str, Any]]]

def process_html_images(
    html_content: str,
    base_dir_for_images: str,
    session: Any,
    site_id: str,
    static_path: Optional[str],
    uploader_func: UploaderFunction,
    dry_run: bool = False # Added dry_run parameter
) -> Tuple[str, int]: # Return modified HTML and count of uploaded images
    """
    Parses HTML content, finds local images, uploads them (or simulates if dry_run),
    and updates their src attributes with new WordPress URLs.

    Args:
        html_content: The HTML string to process.
        base_dir_for_images: The directory of the source Markdown file.
        session: The authenticated requests session.
        site_id: The WordPress site ID.
        static_path: The path to Hugo's global static content folder.
        uploader_func: The function to call for uploading images.
        dry_run: If True, simulate uploads.

    Returns:
        A tuple containing:
            - The modified HTML string with image paths updated.
            - The number of images successfully uploaded (or simulated).
    """
    if not html_content:
        return "", 0

    soup = BeautifulSoup(html_content, 'html.parser')
    images = soup.find_all('img')
    uploaded_images_count = 0

    for img_tag in images:
        if not isinstance(img_tag, Tag) or not img_tag.has_attr('src'):
            continue

        original_src = img_tag['src']

        if original_src.startswith(('http://', 'https://', '//')):
            if dry_run: print(f"[DRY RUN] Skipping external image: {original_src}")
            else: print(f"Skipping external image: {original_src}")
            continue

        # Parse the original_src to remove fragments or query parameters for local path resolution
        parsed_src = urlparse(original_src)
        cleaned_src = unquote(parsed_src.path) # Use only the path component for local file operations and replace '%20' with ' '

        full_local_path: Optional[str] = None
        # image_filename should be derived from the cleaned path
        image_filename = os.path.basename(cleaned_src)

        if cleaned_src.startswith('/'): # Use cleaned_src for path logic
            if static_path and os.path.isdir(static_path):
                # Use cleaned_src, remove its leading slash for os.path.join
                full_local_path = os.path.join(static_path, cleaned_src.lstrip('/'))
            else:
                msg_prefix = "[DRY RUN] " if dry_run else ""
                # Log with original_src to show what was in HTML, but cleaned_src for path issue context
                print(f"{msg_prefix}Warning: Image source '{original_src}' (cleaned: '{cleaned_src}') is absolute, but static_path ('{static_path}') is not set or not a directory. Skipping.")
                continue
        else:
            # Use cleaned_src for resolving relative paths
            full_local_path = os.path.abspath(os.path.join(base_dir_for_images, cleaned_src))

        if full_local_path and os.path.exists(full_local_path):
            if dry_run:
                print(f"[DRY RUN] Found local image: {original_src} (resolved from '{cleaned_src}') -> Full path: {full_local_path}")
            else:
                print(f"Found local image: {original_src} (resolved from '{cleaned_src}') -> Full path: {full_local_path}")

            # image_filename (derived from cleaned_src) is passed to uploader
            upload_response = uploader_func(session, site_id, full_local_path, image_filename, dry_run)

            if upload_response and upload_response.get('URL'):
                new_url = upload_response['URL']
                print(f"  {'[DRY RUN] ' if dry_run else ''}Image processed. New URL: {new_url}")
                img_tag['src'] = new_url
                uploaded_images_count += 1
                if img_tag.has_attr('srcset'):
                    del img_tag['srcset']
                    print(f"  {'[DRY RUN] ' if dry_run else ''}Removed srcset attribute for {original_src}")
            else:
                error_msg = upload_response.get('message', 'Unknown error') if isinstance(upload_response, dict) else 'Unknown error or None response'
                print(f"  {'[DRY RUN] ' if dry_run else ''}Failed to process image {original_src}. Error: {error_msg}")
        elif full_local_path:
            print(f"{'[DRY RUN] ' if dry_run else ''}Warning: Local image not found at resolved path: {full_local_path} (original src: {original_src})")
        else:
            print(f"{'[DRY RUN] ' if dry_run else ''}Warning: Could not determine full local path for image: {original_src}")

    return str(soup), uploaded_images_count
