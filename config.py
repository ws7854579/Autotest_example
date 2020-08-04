import os

ENV_TEST = 'test'
ENV_PRE = 'prepublish'
ENV_ENUMS = (ENV_TEST, ENV_PRE)

env = ENV_TEST

CONFIG_MAP = {ENV_TEST: 'conf.settings_test', ENV_PRE: 'conf.settings_pre'}
os.environ.setdefault('DJANGO_SETTINGS_MODULE', CONFIG_MAP[env])


from django.conf import settings  # pylint:disable=wrong-import-position

BASEDIR = os.path.dirname(os.path.abspath(__file__))
PROJDIR = os.path.dirname(BASEDIR)

LOG_DIR = os.path.join(BASEDIR, 'logs')
SHOTS_DIR = os.path.join(BASEDIR, f'web{os.sep}screenCapture')
for dir_pth in (LOG_DIR, SHOTS_DIR):
    if not os.path.exists(dir_pth):
        try:
            os.makedirs(dir_pth)
        except Exception as e:
            print(f'can not make director {dir_pth.split(BASEDIR)[1].strip(os.sep)}')
            raise e


CHROME = 'Chrome'
FIREFOX = 'Firefox'
BROWSERS = (CHROME, FIREFOX)

DOMAIN = 'testfk.91renxin.com'

DBEXEC_TIMEOUT = 5


USER = 'testrisk'
PWD = 'testriskcontrol'

OTHER_USER = 'other_testrisk'
OTHER_PWD = 'testriskcontrol'

INACTIVE_USER = 'inactive_testrisk'
INACTIVE_PWD = 'testriskcontrol'


DATETIME_FMT = '%Y-%m-%dT%H:%M:%S.%f+08:00'
