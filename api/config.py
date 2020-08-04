from ..config import *  # pylint:disable=wildcard-import

AUTH_CLIENTS = {
    ENV_TEST: ('A6TUi4JaY8utjOUcYGDkc3svZf4rp6uGnm8iMSU2',
               'aqcIJrnHJsiyldjbNibZLwIprpkpJnpZiTbeIWZVAvrEzTrqPJ92dcJL4Dnhcr4Y'
               '6ZTDJRLJV6NxzfJhyE0kQ7MDc9PmXfSHwLzhM9rw1bP6JCXXutMcUP5Obfrkmv3I'),
    ENV_PRE: ('O0A8Lq6ZO66EUHElY8siTmcs31NeHyZxfjKeib7d',
              'AK0QLroRuAdQ8ChobgtifrUVj1T7kvnbD70Aj6VkLkWvErS1eD25j4hb74VtJwx6'
              'AqQxIl4zMk7a86JTqwb0Re5bWoNtW1yVr2aLM1cpcFk9HZTDLuZK3uIPPWNPjiuF')
}

AUTH_HEADERS = {"Content-type": "application/x-www-form-urlencoded", "Accept": "*/*"}
REQUEST_TIMEOUT = 100

AUTH_URL = f'http://{DOMAIN}/o/token/'
AUTH_CLI_ID, AUTH_CLI_SK = AUTH_CLIENTS[env]
