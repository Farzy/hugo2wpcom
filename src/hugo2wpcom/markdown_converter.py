import markdown2
from typing import List

def convert_markdown_to_html(markdown_text: str) -> str:
    """
    Converts a Markdown string to HTML using the markdown2 library.

    Args:
        markdown_text: The Markdown string to convert.

    Returns:
        The resulting HTML string.
    """
    if markdown_text is None:
        return ""

    # Common extras for markdown2
    extras: List[str] = [
        "tables",
        "fenced-code-blocks",  # For code blocks with ```
        "code-friendly",       # Disables smart-quotes, etc., in code blocks
        "footnotes",
        "cuddled-lists",
        "strike",              # For ~~strikethrough~~
        "spoiler",
        "xml",                 # To handle XML/HTML tags better
        "markdown-in-html",    # Process Markdown inside HTML tags
        "wiki-tables",         # Another table syntax
        "numbering",           # For ordered lists (e.g. start="3")
        "header-ids",          # Add IDs to headers
    ]

    try:
        html_content: str = markdown2.markdown(markdown_text, extras=extras)
        return html_content
    except Exception as e:
        # In case markdown2 has an unexpected issue with specific input
        print(f"Error during Markdown to HTML conversion: {e}")
        # Return the original text or an empty string as a fallback
        # For now, returning an empty string or a simple error message might be best
        return f"<p>Error converting Markdown: {e}</p>"
