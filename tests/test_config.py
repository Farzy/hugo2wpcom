import pytest
import io
from hugo2wpcom.config import Config # Assuming Config is in this path

# Sample config.ini content as a string
SAMPLE_CONFIG_INI_CONTENT = """
[Hugo]
hugo_content_path = /path/to/hugo/content
hugo_static_path = /path/to/hugo/static

[WordPress]
wordpress_site_id = example.wordpress.com
client_id = test_client_id
client_secret = test_client_secret
default_post_status = publish
# default_post_category is intentionally omitted to test defaults
# default_post_tags is intentionally omitted to test defaults
"""

SAMPLE_CONFIG_INI_MINIMAL = """
[Hugo]
hugo_content_path = /another/path

[WordPress]
wordpress_site_id = test.com
client_id = min_client_id
client_secret = min_client_secret
"""

@pytest.fixture
def mock_config_file(mocker, content):
    """Mocks reading from a config file with specified content."""
    mock_open = mocker.patch('builtins.open', mocker.mock_open(read_data=content))
    # Also need to mock configparser.ConfigParser.read to use the mocked open content
    # However, Config class directly calls self.cfg.read(self.filepath)
    # So, mocking 'open' should be sufficient if ConfigParser uses it.
    # Let's ensure configparser itself is not reading a real file by also mocking its read method for safety.

    # Forcing ConfigParser to use the string directly for simplicity here
    # rather than fighting with mocking file reads for ConfigParser.
    # We can achieve this by mocking cfg.read() itself within the Config class.

    # Simpler approach: Patch Config.read_config to directly load from string
    # This avoids issues with how ConfigParser interacts with mocked 'open'
    def mock_read_config_method(self_config_instance):
        try:
            self_config_instance.cfg.read_string(content) # type: ignore[no-untyped-call]
            # Ensure sections Hugo and WordPress are added if not present from string
            if 'Hugo' not in self_config_instance.cfg:
                self_config_instance.cfg.add_section('Hugo')
            if 'WordPress' not in self_config_instance.cfg:
                self_config_instance.cfg.add_section('WordPress')
            return self_config_instance.cfg
        except Exception as e:
            print(f"Mock read_config error: {e}")
            return None

    mocker.patch.object(Config, 'read_config', mock_read_config_method)


def test_config_initialization_and_read(mocker):
    """Test that Config initializes and reads mocked config data."""
    mock_read_config_method = mocker.patch.object(Config, 'read_config')
    mock_read_config_method.return_value = None # Simulate successful read call

    config = Config("dummy_path.ini")
    assert config.filepath == "dummy_path.ini"
    mock_read_config_method.assert_called_once()

@pytest.mark.parametrize("content", [SAMPLE_CONFIG_INI_CONTENT])
def test_config_get_values(mock_config_file, content): # content is from parametrize
    config = Config("dummy_path.ini") # Path doesn't matter due to mock

    assert config['Hugo']['hugo_content_path'] == "/path/to/hugo/content"
    assert config['Hugo'].get('hugo_static_path') == "/path/to/hugo/static"
    assert config['WordPress']['wordpress_site_id'] == "example.wordpress.com"
    assert config['WordPress'].get('client_id') == "test_client_id"
    assert config['WordPress'].get('client_secret') == "test_client_secret"
    assert config['WordPress'].get('default_post_status') == "publish"

@pytest.mark.parametrize("content", [SAMPLE_CONFIG_INI_MINIMAL])
def test_config_default_values(mock_config_file, content):
    config = Config("dummy_path.ini")

    # These were set as defaults in Config.__init__
    # default_post_status is 'draft'
    # default_post_category is 'Imported'
    # default_post_tags is 'hugo, import'

    # If the key is present in defaults passed to ConfigParser, section.get(key) will return it.
    # Also, direct access config['WordPress']['default_post_status'] will work.
    assert config['WordPress'].get('default_post_status', 'fallback_if_not_even_in_defaults') == "draft" # Default from Config
    assert config['WordPress'].get('default_post_category', 'fallback_if_not_even_in_defaults') == "Imported" # Default from Config
    assert config['WordPress'].get('default_post_tags', 'fallback_if_not_even_in_defaults') == "hugo, import" # Default from Config

    # Test that values not in this minimal sample and not in defaults return None for .get()
    assert config['Hugo'].get('hugo_static_path') is None # Not in MINIMAL, no default for this one

    # Check that section access for a non-existent key raises KeyError for direct access
    with pytest.raises(KeyError):
        _ = config['Hugo']['non_existent_key_for_hugo']

    with pytest.raises(KeyError):
        _ = config['WordPress']['non_existent_key_for_wp']

def test_config_section_not_present(mocker):
    # Simulate a config where a section might be entirely missing by providing empty content
    # and ensuring our __init__ still creates the sections.
    mocker.patch.object(Config, 'read_config', lambda self: self.cfg.read_string("")) # Empty config
    config = Config()

    # __init__ in Config.py ensures 'Hugo' and 'WordPress' sections are added.
    assert config['Hugo'] is not None
    assert config['WordPress'] is not None

    # Accessing a key in these empty-but-created sections should yield None or default
    assert config['Hugo'].get('hugo_content_path') is None
    assert config['WordPress'].get('default_post_status') == 'draft' # From defaults

    # Accessing a completely non-existent section should raise KeyError
    with pytest.raises(KeyError):
        _ = config['NonExistentSection']
