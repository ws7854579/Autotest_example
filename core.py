from functools import wraps
from subprocess import PIPE, Popen

from functional_tests import config
from functional_tests.logger import logger
#from functional_tests.sql_executor import sql_executor

case_owner = None


def get_case_owner():
    global case_owner
    if case_owner:
        return case_owner

    logger.info("尝试获取当前git用户...")
    git_exec = Popen(['git', 'config', 'user.name'], cwd=config.PROJDIR, stdout=PIPE, stderr=PIPE)
    ret, error = git_exec.communicate()
    if git_exec.poll() == 0:
        case_owner = ret.decode("utf-8").strip()
        return case_owner

    logger.warning("无法获取当前git用户: %s", error.decode("utf-8").strip())
    return None


def case_tag(name, owner='QA'):

    def tag(method):

        @wraps(method)
        def wrapper(self):
            case_desc = f'{name} by {owner}' if owner else name
            logger.info("================== %s ==================", case_desc)
            return method(self)

        return wrapper

    return tag


def update_reset(table):

    def reset(func):

        @wraps(func)
        def wrapper(self):
            before_list = list()

            if table == 'factor':
                sql_raw = f"""SELECT id, status, ref_count FROM {table} ORDER BY modify_time ASC LIMIT 1"""
            else:
                query_app_id = f"""SELECT DISTINCT application_id FROM {table}"""
                app_id_num = [ele[0] for ele in sql_executor.execute(query_app_id)]
                for eid in app_id_num:
                    sql_raw = \
                        f"""SELECT id, status, ref_count FROM {table} WHERE application_id={eid}
                        ORDER BY modify_time ASC LIMIT 1"""
            before_list.append(sql_executor.execute(sql_raw)[0])

            try:
                func(self)

            finally:
                for element in before_list:
                    sql_reset = \
                        f"""UPDATE {table} SET status={element[1]}, ref_count={element[2]} WHERE id='{element[0]}'"""
                    sql_executor.execute(sql_reset)
        return wrapper
    return reset
