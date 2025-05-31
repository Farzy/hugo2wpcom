# Hugo to WordPress.com Importer

This script converts Hugo Markdown files to a format suitable for WordPress and imports them into a WordPress.com site using the WordPress.com REST API. It handles front matter, Markdown to HTML conversion, image uploading, and post creation.

## Features

*   Scans Hugo content directories for Markdown files.
*   Parses Hugo front matter.
*   Converts Markdown content to HTML using `markdown2` with useful extras.
*   Identifies local images in the HTML, uploads them to WordPress.com, and updates image URLs.
*   Creates new posts on WordPress.com with appropriate titles, content, dates, categories, and tags.
*   Supports a `--dry-run` mode for testing without making live changes to your WordPress site.

## Workflow

The script performs the following steps:

1.  **Configuration:** Reads `config.ini` for necessary paths and credentials.
2.  **Authentication:** Connects to WordPress.com using OAuth2 to obtain an access token.
3.  **Scan Content:** Walks through the specified Hugo content directory to find all Markdown (`.md`) files.
4.  **Process Each File:** For each Markdown file found:
    *   Parses front matter (metadata) and Markdown content.
    *   Converts the Markdown body to HTML.
    *   Scans the generated HTML for local image references.
    *   For each local image:
        *   Resolves its full path (checking both content-relative paths and paths relative to Hugo's static directory).
        *   Uploads the image to the WordPress.com media library.
        *   Updates the `<img>` tag's `src` attribute in the HTML to the new WordPress URL.
    *   Creates a new post on WordPress.com with the processed HTML content and metadata (title, date, categories, tags, status).
5.  **Summary:** Prints a report of successfully created posts, any errors, and images uploaded.

## Configuration (`config.ini`)

Before running the script, you must copy `config.ini.sample` to `config.ini` and fill in all required fields.

### `[Hugo]` Section

*   `hugo_content_path`: **Required.** The absolute or relative path to your Hugo project's content directory (e.g., `/path/to/your/hugo/content` or `my_hugo_site/content`).
*   `hugo_static_path`: Optional. The absolute or relative path to your Hugo project's static directory (e.g., `/path/to/your/hugo/static` or `my_hugo_site/static`). This is used to resolve image paths that start with `/` (e.g., `/images/foo.png`).

**Example `[Hugo]` section:**
```ini
[Hugo]
hugo_content_path = /home/user/my_blog/content
hugo_static_path = /home/user/my_blog/static
```

### `[WordPress]` Section

*   `client_id`: **Required.** The Client ID of your WordPress.com application.
*   `client_secret`: **Required.** The Client Secret of your WordPress.com application.
*   `wordpress_site_id`: **Required.** Your WordPress.com site ID or domain (e.g., `yourgroovydomain.wordpress.com` or `123456789`).
*   `default_post_status`: Optional. Default status for new posts (e.g., `draft`, `publish`, `pending`). Defaults to `draft` if not specified in `config.ini` or post front matter.
*   `default_post_category`: Optional. Default category (or comma-separated categories) for imported posts if not specified in front matter. Example: `Imported From Hugo, Tech`. Defaults to `Imported`.
*   `default_post_tags`: Optional. Default tags (comma-separated) for imported posts if not specified in front matter. Example: `hugo, import, legacy`. Defaults to `hugo, import`.

**Example `[WordPress]` section:**
```ini
[WordPress]
client_id = 12345
client_secret = yourverylongclientsecret
wordpress_site_id = yourblog.wordpress.com
default_post_status = draft
default_post_category = Imported From Hugo, Old Blog
default_post_tags = hugo, import, web
```

## Usage

1.  **Set up Environment:**
    *   It's recommended to use a virtual environment (e.g., with `venv` or `Poetry`).
    *   Install dependencies (see below). If using Poetry, `poetry install`. If using pip, create a `requirements.txt` from the listed dependencies and `pip install -r requirements.txt`.

2.  **Create WordPress.com Application:**
    *   Go to [WordPress Developer Apps](https://developer.wordpress.com/apps/) and create a new application.
    *   Note down the **Client ID** and **Client Secret**.
    *   Set the "Redirect URL" for your application to `http://localhost:8000/callback` (or any other local URL you can temporarily listen on if `wp_auth.py` is modified). The current `wp_auth.py` might require a specific one.

3.  **Configure `config.ini`:**
    *   Copy `config.ini.sample` to `config.ini`.
    *   Fill in *all* required fields as detailed above, especially `client_id`, `client_secret`, `wordpress_site_id`, and `hugo_content_path`.

4.  **Run the Script:**
    *   Execute the script from the root directory of the project:
        ```bash
        python -m src.hugo2wpcom.main
        ```
    *   **Dry Run (Recommended for first time):** To simulate the import process without making any actual changes to your WordPress site (no image uploads, no post creations), use the `--dry-run` flag:
        ```bash
        python -m src.hugo2wpcom.main --dry-run
        ```

5.  **Authentication Flow:**
    *   The first time you run the script (or if your token expires), it will print an authorization URL.
    *   Copy this URL into your web browser.
    *   Authorize the application.
    *   You will be redirected to the callback URL you configured. Copy the full URL of this redirect page (it will contain a `code` parameter).
    *   Paste this full callback URL back into the terminal when prompted by the script.
    *   The script will then obtain an access token and store it in `config.ini` for future use.

## Dependencies

The main Python libraries used are:

*   `requests`
*   `requests-oauthlib`
*   `python-frontmatter`
*   `markdown2`
*   `beautifulsoup4`
*   `python-dateutil`

Testing dependencies:
*   `pytest`
*   `pytest-mock`

## Notes

*   The script modifies `config.ini` to store the OAuth access token. **Do not commit `config.ini` to a public repository if it contains sensitive credentials or tokens.**
*   Ensure the redirect URL in your WordPress app settings matches what `wp_auth.py` expects (check its source if issues arise).
*   Error handling for API rate limits or very large sites might need further refinement.
