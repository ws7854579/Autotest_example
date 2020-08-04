import random
import re
import string
from datetime import timedelta


def get_db_table(db_table_name):
    re_m = re.match(r'(.*)_v[\d]{8}_(?:app|cld|rule)', db_table_name)
    return re_m.group(1) if re_m else db_table_name


def generate_string(length=None, blank=False):
    if length is None:
        length = random.randint(0, 20) if blank else random.randint(1, 20)
    return ''.join(random.choices(string.ascii_letters + string.digits + '_', k=length))


def generate_num_string(length=None, blank=False):
    if length is None:
        length = random.randint(0, 20) if blank else random.randint(1, 20)
    return ''.join(random.choices(string.digits, k=length))


def utc2local(dt, time_diff=8, fmt=None):
    local_dt = dt + timedelta(hours=time_diff)
    if fmt:
        return local_dt.strftime(fmt)
    return local_dt
