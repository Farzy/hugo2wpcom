import base64
import pprint

import requests
from requests_oauthlib import OAuth2Session
import configparser

def read_config(filepath="config.ini"):
    cfg = configparser.ConfigParser()
    try:
        cfg.read(filepath)
        return cfg
    except configparser.Error as e:
        print(f"Error reading config file: {e}")
        return None


def connect_to_wordpress(config):
    # OAuth2 endpoints for WordPress.com
    authorization_base_url = 'https://public-api.wordpress.com/oauth2/authorize'
    token_url = 'https://public-api.wordpress.com/oauth2/token'

    client_id = config['WordPress']['client_id']
    client_secret = config['WordPress']['client_secret']
    redirect_uri = config['WordPress']['redirect_uri']
    access_token = config['WordPress'].get('token', None)
    if access_token:
        access_token = base64.b64decode(access_token).decode('utf-8')

    if is_valid_token(client_id, access_token):
        s = requests.Session()
        s.headers.update({'Authorization': f'Bearer {access_token}'})
        return s

    # Create an OAuth2 session
    wordpress = OAuth2Session(client_id, redirect_uri=redirect_uri, scope='global')
    
    # Redirect user to WordPress for authorization
    authorization_url, state = wordpress.authorization_url(authorization_base_url)
    print(f'Please go to {authorization_url} and authorize access.')

    # Get the authorization verifier code from the callback (manual user step)
    authorization_response = input('Paste the full callback URL here: ')
    
    # Fetch the access token
    token = wordpress.fetch_token(
        token_url,
        authorization_response=authorization_response,
        client_secret=client_secret,
        include_client_id=True
    )

    print('Connected to WordPress.com successfully!')
    pprint.pprint(token)

    config['WordPress']['token'] = base64.b64encode(bytes(token['access_token'], 'utf-8')).decode('utf-8')
    with open('config.ini', 'w') as configfile:
        config.write(configfile)

    return wordpress


def is_valid_token(client_id, token=None):
    token_info_url = 'https://public-api.wordpress.com/oauth2/token-info'

    if token:
        query_params = {
            'client_id': client_id,
            'token': token
        }
        r = requests.get(token_info_url, params=query_params)
        if r.status_code == 200:
            print("Current token is still valid.")
            return True
        else:
            print("Current token is invalid.")
            return False
    else:
        return False


if __name__ == '__main__':
    rest_base_url = 'https://public-api.wordpress.com/rest/v1.1'

    config = read_config()
    session = connect_to_wordpress(config)

    r = session.get(f'{rest_base_url}/me')
    print("## /me:")
    pprint.pprint(r.json())

    r = session.get(f'{rest_base_url}/me/sites')
    print("## /me/sites:")
    pprint.pprint(r.json())
