# Hugo to WordPress.com converter

Try to convert Hugo markdown files to WP format and import in wordpress.com.

## Usage

* Create **Poetry** environment.
* Create an **Application** on WordPress using https://developer.wordpress.com/apps.
* Configure WordPress REST access by copying `config.ini.sample` to `config.ini`
and fill in the values using the WordPress Application.
* Launch script using `python -m src.hugo2wpcom.main`

## Notes

* Please note that the script overwrites the configuration file in order to store the
temporary access token inside.
* Do not store `config.ini` in a repository as it contains secrets.
