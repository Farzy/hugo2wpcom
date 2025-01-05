
from __future__ import annotations
import base64
import os
import pprint
from typing import Union
from typing import Any

import requests
from requests_oauthlib import OAuth2Session
import configparser
import http.server
import socketserver
import threading
from urllib.parse import urlunparse


class Config:
    def __init__(self, filepath: str = "config.ini"):
        self.filepath = filepath
        self.cfg = configparser.ConfigParser()
        self.read_config()

    def read_config(self) -> Union[configparser.ConfigParser, None]:
        try:
            self.cfg.read(self.filepath)  # type: ignore[no-untyped-call]
            return self.cfg
        except configparser.Error as e:
            print(f"Error reading config file: {e}")
            return None

    def write_config(self) -> None:
        try:
            with open(self.filepath, 'w') as file:
                self.cfg.write(file)
        except IOError as e:
            print(f"Error writing to config file: {e}")

def launch_webserver_and_get_called_url(port: int) -> Union[str, None]:
    """
    Launch a webserver on a random port, listen for a single request,
    and return the full URL that the server was called.
    :param port:
    """

    class RequestHandler(http.server.SimpleHTTPRequestHandler):
        # Store the called URL in class scope so it's accessible after the request is handled
        called_url = None

        def do_GET(self):
            # Construct the full URL from the request
            host = self.headers.get('Host')
            scheme = 'http'  # HTTPS would require additional setup
            path = self.path
            RequestHandler.called_url = urlunparse((scheme, host, path, '', '', ''))

            # Respond to the request
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'Callback received. You can close this window.')

            # Stop the server (the thread will terminate)
            threading.Thread(target=self.server.shutdown).start()

    server: socketserver.TCPServer[Any] = socketserver.TCPServer(("127.0.0.1", port), RequestHandler)

    print(f"Server running at http://127.0.0.1:{port}/")

    # Start the server in a separate thread to avoid blocking
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()

    # Wait until the server is called and shutdown
    thread.join()

    # Return the full URL after shutting down the server
    return RequestHandler.called_url


def find_available_port() -> int:
    # Get an available port
    with socketserver.TCPServer(("127.0.0.1", 0), http.server.SimpleHTTPRequestHandler) as temp_server:
        return temp_server.server_address[1]


def connect_to_wordpress(config: Config) -> Union[requests.Session, OAuth2Session]:
    # OAuth2 endpoints for WordPress.com
    authorization_base_url = 'https://public-api.wordpress.com/oauth2/authorize'
    token_url = 'https://public-api.wordpress.com/oauth2/token'

    client_id = config.cfg['WordPress']['client_id']
    client_secret = config.cfg['WordPress']['client_secret']
    access_token = config.cfg['WordPress'].get('token', None)
    if access_token:
        access_token: str = base64.b64decode(access_token).decode('utf-8')

    if is_valid_token(client_id, access_token):
        s = requests.Session()
        s.headers.update({'Authorization': f'Bearer {access_token}'})
        return s

    # find an available TCP port
    tcp_port = find_available_port()

    # The redirect URL "http://localhost:..." is insecure
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

    # Create an OAuth2 session
    wordpress: OAuth2Session = OAuth2Session(client_id,
                              redirect_uri=f"http://localhost:{tcp_port}",
                              scope='global')
    
    # Redirect user to WordPress for authorization
    authorization_url, state = wordpress.authorization_url(authorization_base_url)
    print(f'Please go to {authorization_url} and authorize access.')

    # Get the authorization verifier code from the callback (manual user step)
    authorization_response = launch_webserver_and_get_called_url(tcp_port)
    
    # Fetch the access token
    token = wordpress.fetch_token(
        token_url,
        authorization_response=authorization_response,
        client_secret=client_secret,
        include_client_id=True
    )

    print('Connected to WordPress.com successfully!')
    pprint.pprint(token)

    config.cfg['WordPress']['token'] = base64.b64encode(bytes(token['access_token'], 'utf-8')).decode('utf-8')
    config.write_config()

    return wordpress


def is_valid_token(client_id: str, token: Union[str, None] = None) -> bool:
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

    config = Config(filepath='config.ini')
    session = connect_to_wordpress(config)

    r = session.get(f'{rest_base_url}/me')
    print("## /me:")
    pprint.pprint(r.json())

    r = session.get(f'{rest_base_url}/me/sites')
    print("## /me/sites:")
    pprint.pprint(r.json())
