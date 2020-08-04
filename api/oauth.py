import json
from urllib.parse import urlencode

import requests

from . import config
from ..logger import logger


class OAuth:
    auth_type_enums = ('authorization_code', 'password', 'client_credentials')

    def __init__(self, url, auth_type, client, client_sk):
        auth_type = str(auth_type).strip().lower()
        if auth_type not in self.auth_type_enums:
            logger.critical("current authorization type is not supported: %s", auth_type)

        self.url = url
        self.auth_type = auth_type
        self.client = client
        self.client_sk = client_sk

        self.payload = {
            'grant_type': self.auth_type,
            'client_id': self.client,
            'client_secret': self.client_sk
        }

        self.token_type = None
        self.access_token = None
        self.refresh_token = None
        self.expired = False

    def access(self):
        logger.info("start accessing oauth2 token...")
        resp = requests.post(url=self.url, data=urlencode(self.payload), headers=config.AUTH_HEADERS,
                             timeout=config.REQUEST_TIMEOUT)
        if resp.status_code != 200:
            logger.critical("access oauth2 token failed! return code: %s  response: %s", resp.status_code,
                            resp.content.decode('utf-8'))
        try:
            resp = json.loads(resp.content.decode('utf-8'))
            self.token_type = resp['token_type']
            self.access_token = resp['access_token']
            self.refresh_token = resp.get('refresh_token')
            self.expired = False
            logger.info("access oauth2 token succeeded!")
        except (json.JSONDecodeError, TypeError):
            logger.critical("access oauth2 token failed! can not parse response: %s", resp.content.decode('utf-8'))
        except KeyError:
            logger.critical("access oauth2 token failed! can not parse response: %s", resp)

    def refresh(self):
        if self.refresh_token is None:
            self.access()
            return

        payload = {
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token,
            'client_id': self.client,
            'client_secret': self.client_sk
        }
        logger.info("start refreshing oauth2 token...")
        resp = requests.post(url=self.url, data=urlencode(payload), headers=config.AUTH_HEADERS,
                             timeout=config.REQUEST_TIMEOUT)
        if resp.status_code != 200:
            logger.critical("refresh oauth2 token failed! return code: %s  response: %s", resp.status_code,
                            resp.content.decode('utf-8'))
        try:
            resp = json.loads(resp.content.decode('utf-8'))
            self.token_type = resp['token_type']
            self.access_token = resp['access_token']
            self.refresh_token = resp.get('refresh_token')
            self.expired = False
            logger.info("refresh oauth2 token succeeded!")
        except (json.JSONDecodeError, TypeError):
            logger.critical("refresh oauth2 token failed! can not parse response: %s", resp.content.decode('utf-8'))
        except KeyError:
            logger.critical("refresh oauth2 token failed! can not parse response: %s", resp)

    def build_token_header(self):
        if self.access_token is None:
            self.access()
        elif self.expired:
            self.refresh()
        return {'Authorization': f'{self.token_type} {self.access_token}'}


class AuthorizationCodeOAuth(OAuth):

    def __init__(self, url, client, client_sk, code, callback_url):
        super(AuthorizationCodeOAuth, self).__init__(url, 'authorization_code', client, client_sk)
        self.payload.update({'code': code, 'redirect_uri': callback_url})


class PasswordOAuth(OAuth):

    def __init__(self, url, client, client_sk, user, pwd):
        super(PasswordOAuth, self).__init__(url, 'password', client, client_sk)
        self.payload.update({'username': user, 'password': pwd})


class ClientCredentialsOAuth(OAuth):

    def __init__(self, url, client, client_sk):
        super(ClientCredentialsOAuth, self).__init__(url, 'client_credentials', client, client_sk)
