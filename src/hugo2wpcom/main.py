
from __future__ import annotations
import pprint

from src.hugo2wpcom.config import Config
from src.hugo2wpcom.wp_auth import connect_to_wordpress

if __name__ == '__main__':
    rest_base_url = 'https://public-api.wordpress.com/rest/v1.1'

    config = Config(filepath='config.ini')
    session = connect_to_wordpress(config)

    r = session.get(f'{rest_base_url}/me')
    print("## /me:")
    pprint.pprint(r.json())

    r = session.get(f'{rest_base_url}/me/sites')
    print("## /me/sites:")
    pprint.pprint(r.json())
