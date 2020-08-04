#! /usr/bin/env python3
# -*- coding:utf-8 -*-

import os

import django

from . import config
from .logger import logger

os.environ.setdefault('DJANGO_SETTINGS_MODULE', config.CONFIG_MAP[config.env])
django.setup(set_prefix=False)

# pylint:disable=wrong-import-position, wrong-import-order
from horand.parser.sql_executor import SQLExecutor as BaseSQLExecutor
from sqlalchemy import create_engine


class SQLExecutor(BaseSQLExecutor):

    def __init__(self, host, db, user, pwd, port=3306, **kwargs):  # pylint:disable=super-init-not-called
        db_string = f'mysql://{user}:{pwd}@{host}:{port}/{db}?charset=utf8'
        try:
            self.engine = create_engine(db_string, encoding='utf-8', execution_options={'no_parameters': True})
            self.engine_description = db_string
        except Exception as ex:  # pylint:disable=broad-except
            logger.critical("无法连接到数据库: %s, %s", db_string, **kwargs, exc_info=ex)

    @property
    def select_max_time(self):
        return config.DBEXEC_TIMEOUT

    @staticmethod
    def mysql_execute_sql(connection, raw_sql, result_container):
        try:
            ret_proxy = connection.execute(raw_sql)
            result_container['result'] = ret_proxy.fetchall() if ret_proxy.returns_rows else None
        except Exception as error:  # pylint:disable=broad-except
            result_container['error'] = error

    def execute(self, sql):
        try:
            results = self._mysql_execute(sql)
        except Exception as ex:  # pylint:disable=broad-except
            logger.error("SQL执行失败: %s", sql, exc_info=ex)
            return None
        else:
            logger.info("SQL执行成功: %s", sql)
            return results


sql_executor = SQLExecutor(host='10.66.5.112', port=3306, db='rule',
                           user='risk', pwd='2IqG7fRRaXTy9XsT')
