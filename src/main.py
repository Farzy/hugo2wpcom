import os
import argparse # For --dry-run
from datetime import datetime
from typing import List, Optional
from dateutil import parser as dateutil_parser

from src.hugo2wpcom.config import Config
from src.hugo2wpcom.hugo_content import scan_hugo_content_path
from src.hugo2wpcom.markdown_converter import convert_markdown_to_html
from src.hugo2wpcom.html_processor import process_html_images
from src.hugo2wpcom.wp_media_uploader import upload_image_to_wordpress
from src.hugo2wpcom.wp_post_creator import create_wordpress_post
from src.hugo2wpcom.wp_auth import connect_to_wordpress

def main():
    parser = argparse.ArgumentParser(description="Import Hugo content to WordPress.com.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate execution without making live API calls to WordPress (no uploads, no post creations)."
    )
    args = parser.parse_args()

    if args.dry_run:
        print("*** Running in DRY-RUN mode. No actual changes will be made to WordPress. ***")

    print("Starting hugo2wpcom importer...")

    # --- Configuration Loading and Validation ---
    config = Config()

    required_hugo_configs = ['hugo_content_path']
    # client_id and client_secret are needed for connect_to_wordpress
    required_wp_configs = ['wordpress_site_id', 'client_id', 'client_secret']

    for key in required_hugo_configs:
        if not config['Hugo'].get(key):
            print(f"Error: Missing required configuration in [Hugo] section: '{key}'. Please check config.ini.")
            return
    for key in required_wp_configs:
        if not config['WordPress'].get(key):
            print(f"Error: Missing required configuration in [WordPress] section: '{key}'. Please check config.ini.")
            return

    hugo_content_path = config['Hugo']['hugo_content_path']
    hugo_static_path = config['Hugo'].get('hugo_static_path')

    wordpress_site_id = config['WordPress']['wordpress_site_id']
    default_post_status = config['WordPress'].get('default_post_status', 'draft')
    default_post_category_str = config['WordPress'].get('default_post_category', '')
    default_post_tags_str = config['WordPress'].get('default_post_tags', '')

    if not hugo_static_path:
        print("Warning: 'hugo_static_path' is not configured. Absolute image paths ('/...') in Markdown may not be resolved correctly.")

    print(f"Hugo Content Path: {hugo_content_path}")
    if hugo_static_path: print(f"Hugo Static Path: {hugo_static_path}")
    print(f"WordPress Site ID: {wordpress_site_id}")
    print(f"Default Post Status: {default_post_status}")
    if default_post_category_str: print(f"Default Post Category: {default_post_category_str}")
    if default_post_tags_str: print(f"Default Post Tags: {default_post_tags_str}")

    # --- WordPress Authentication ---
    session = None
    if not args.dry_run:
        print("\nConnecting to WordPress.com...")
        session = connect_to_wordpress(config) # connect_to_wordpress should handle its own errors/return None
        if not session:
            print("Failed to connect to WordPress.com. Please check your credentials and configuration. Cannot proceed with live run.")
            return
        print("Successfully connected to WordPress.com.")
    else:
        print("\n[DRY RUN] Skipping WordPress.com authentication.")
        # Session remains None, but API functions will use their dry_run logic

    # --- Content Scanning ---
    print(f"\nScanning Hugo content from: {hugo_content_path}...")
    all_hugo_posts = scan_hugo_content_path(hugo_content_path)
    if not all_hugo_posts:
        print("No Markdown files found in the specified Hugo content path.")
        return
    print(f"Found {len(all_hugo_posts)} Markdown files to process.")

    # --- Processing and Uploading ---
    successfully_created_posts_count = 0
    failed_post_files: List[str] = []
    total_images_uploaded_count = 0

    for i, post_data in enumerate(all_hugo_posts):
        filepath = post_data['filepath']
        metadata = post_data['metadata']
        markdown_content = post_data['content']
        title_for_log = metadata.get('title', os.path.basename(filepath))

        print(f"\n--- Processing post {i+1}/{len(all_hugo_posts)}: {title_for_log} ({filepath}) ---")

        try:
            # 1. Convert Markdown to HTML
            print("Converting Markdown to HTML...")
            html_content = convert_markdown_to_html(markdown_content)
            if not html_content or html_content.strip() == "<p></p>": # Check for effectively empty
                print("Markdown conversion resulted in empty or minimal HTML. Skipping post.")
                failed_post_files.append(filepath + " (Markdown conversion failed or empty)")
                continue
            print("Markdown converted successfully.")

            # 2. Process HTML images (upload and update paths)
            print("Processing HTML for images...")
            base_dir_for_images = os.path.dirname(filepath)

            processed_html, images_uploaded_for_this_post = process_html_images(
                html_content,
                base_dir_for_images,
                session, # Will be None if dry_run and no connection was made
                wordpress_site_id,
                hugo_static_path,
                upload_image_to_wordpress, # Pass the actual function
                dry_run=args.dry_run
            )
            total_images_uploaded_count += images_uploaded_for_this_post
            print(f"HTML image processing complete. {images_uploaded_for_this_post} images processed/uploaded for this post.")

            # 3. Prepare data for WordPress post
            title = metadata.get('title', os.path.basename(filepath))

            date_str: Optional[str] = None
            date_val = metadata.get('date')
            if date_val:
                try:
                    if isinstance(date_val, datetime):
                        date_str = date_val.isoformat()
                    else:
                        parsed_date = dateutil_parser.parse(str(date_val))
                        # Ensure timezone info if WordPress requires it, though API often defaults to site TZ
                        # For now, directly convert. Add .replace(tzinfo=...) or .astimezone(...) if needed.
                        date_str = parsed_date.isoformat()
                except (ValueError, TypeError, OverflowError) as e: # OverflowError for dates too far in past/future
                    print(f"Warning: Could not parse date '{date_val}' for post '{title}'. Error: {e}. Post will use server current time.")

            categories: List[str] = []
            raw_categories = metadata.get('categories', metadata.get('category'))
            if isinstance(raw_categories, str):
                categories = [cat.strip() for cat in raw_categories.split(',')]
            elif isinstance(raw_categories, list):
                categories = [str(cat).strip() for cat in raw_categories if str(cat).strip()] # Ensure not empty
            if not categories and default_post_category_str:
                categories = [cat.strip() for cat in default_post_category_str.split(',') if cat.strip()]

            tags: List[str] = []
            raw_tags = metadata.get('tags')
            if isinstance(raw_tags, str):
                tags = [tag.strip() for tag in raw_tags.split(',')]
            elif isinstance(raw_tags, list):
                tags = [str(tag).strip() for tag in raw_tags if str(tag).strip()]
            if not tags and default_post_tags_str:
                tags = [tag.strip() for tag in default_post_tags_str.split(',') if tag.strip()]

            status = default_post_status
            if isinstance(metadata.get('draft'), bool):
                status = 'draft' if metadata['draft'] else 'publish'
            elif metadata.get('status'):
                status = str(metadata['status']).lower()

            # 4. Create post on WordPress
            print(f"Creating WordPress post for '{title}' with status '{status}'...")
            wp_post_response = create_wordpress_post(
                session=session, # Will be None if dry_run and no connection
                site_id=wordpress_site_id,
                title=title,
                content_html=processed_html,
                status=status,
                date=date_str,
                categories=categories if categories else None,
                tags=tags if tags else None,
                hugo_metadata=metadata,
                dry_run=args.dry_run
            )

            if wp_post_response and (wp_post_response.get('ID') or wp_post_response.get('dry_run_success')):
                msg_prefix = "[DRY RUN] " if args.dry_run else ""
                print(f"{msg_prefix}Successfully processed WordPress post! ID: {wp_post_response.get('ID')}, URL: {wp_post_response.get('URL')}")
                successfully_created_posts_count += 1
            else:
                print(f"Failed to create WordPress post for '{filepath}'. Response: {wp_post_response}")
                failed_post_files.append(filepath + " (WordPress post creation failed/no success status)")

        except Exception as e:
            print(f"An unexpected error occurred while processing '{filepath}': {type(e).__name__} - {e}")
            failed_post_files.append(filepath + f" (Unexpected error: {type(e).__name__})")

    # --- Summary Report ---
    print("\n--- Import Summary ---")
    if args.dry_run:
        print("*** Results are from a DRY RUN. No actual changes were made to WordPress. ***")
    print(f"Total Markdown files found: {len(all_hugo_posts)}")
    print(f"Posts processed for WordPress creation: {successfully_created_posts_count}")
    print(f"Total images processed/uploaded: {total_images_uploaded_count}")
    if failed_post_files:
        print(f"Posts/files that encountered errors ({len(failed_post_files)}):")
        for f_path in failed_post_files:
            print(f"  - {f_path}")
    else:
        if 0 < len(all_hugo_posts) == successfully_created_posts_count:
            print("All posts processed successfully!")
        elif len(all_hugo_posts) == 0:
            print("No posts were processed.")

    print("----------------------")
    print("Import process finished.")

if __name__ == "__main__":
    main()
