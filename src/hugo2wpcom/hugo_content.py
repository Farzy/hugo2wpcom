import os
import frontmatter
from typing import List, Dict, Any, Union

# Define a type alias for the post structure for clarity
HugoPost = Dict[str, Any]

def parse_hugo_file(file_path: str) -> Union[HugoPost, None]:
    """
    Parses a single Hugo Markdown file.

    Args:
        file_path: The full path to the Markdown file.

    Returns:
        A dictionary containing 'metadata', 'content', and 'filepath',
        or None if an error occurs.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            post = frontmatter.load(f)

        return {
            'metadata': post.metadata,
            'content': post.content,
            'filepath': file_path
        }
    except IOError as e:
        print(f"Error reading file {file_path}: {e}")
        return None
    except Exception as e:
        # Catching general exceptions from frontmatter parsing, though it's usually good
        # to catch more specific exceptions if known (e.g., frontmatter.YAMLParseException)
        print(f"Error parsing frontmatter from file {file_path}: {e}")
        return None

def scan_hugo_content_path(content_path: str) -> List[HugoPost]:
    """
    Scans the Hugo content directory for Markdown files and parses them.

    Args:
        content_path: The path to the Hugo content directory.

    Returns:
        A list of parsed Hugo posts (dictionaries).
    """
    if not content_path or not os.path.exists(content_path):
        print(f"Error: Hugo content path '{content_path}' does not exist.")
        return []
    if not os.path.isdir(content_path):
        print(f"Error: Hugo content path '{content_path}' is not a directory.")
        return []

    parsed_posts: List[HugoPost] = []
    for root, _, files in os.walk(content_path):
        for filename in files:
            if filename.lower().endswith(".md"):
                file_path = os.path.join(root, filename)
                parsed_post = parse_hugo_file(file_path)
                if parsed_post:
                    parsed_posts.append(parsed_post)

    return parsed_posts
