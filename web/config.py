import random

from functional_tests.config import *  # pylint:disable=wildcard-import

browser = random.choice(BROWSERS)
IMPLICIT_WAIT = 10
WAIT = 3

SERVER = f'http://manager.{DOMAIN}/arrange'
