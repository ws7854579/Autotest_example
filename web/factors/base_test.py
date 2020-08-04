#! /usr/bin/env python3
# -*- coding:utf-8 -*-
import random

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By

from ...logger import logger
from ...sql_executor import sql_executor
from .. import config
from ..base_web_test import BaseWebTestCase


class BaseTestCase(BaseWebTestCase):

    url = config.SERVER

    case_name = '因子'

    return_button = (By.XPATH, r'//button/span[contains(text(), "返回")]/..')

    user = None
    prod_app = None

    @staticmethod
    def query_factors_from_db(*args, order=None, desc=False, limit=None, **kwargs):
        fields = ', '.join(['factor.id' if fld == 'id' else fld for fld in args]) if args else 'factor.*'

        filters = list()
        for fld, val in kwargs.items():
            if fld == 'id':
                fld = 'factor.id'
            if isinstance(val, tuple):
                filters.append(f" WHERE {fld} IN {val}")
            else:
                filters.append(f" WHERE {fld} = '{val}'")

        raw_sql = f"""
        SELECT DISTINCT {fields} 
        FROM factor 
                 RIGHT JOIN factor_application_relation far on factor.id = far.factor_id"""
        if filters:
            raw_sql += ' AND'.join(filters)
        if order:
            raw_sql += f' ORDER BY {order}'
            if desc:
                raw_sql += ' DESC'
        if limit:
            raw_sql += f' LIMIT {limit}'

        return sql_executor.execute(raw_sql)

    @classmethod
    def random_factor_id(cls, **kwargs):
        rets = cls.query_factors_from_db('id', **kwargs)
        if rets:
            return random.choice(rets)[0]

        logger.error("没有匹配过滤条件的因子！ %s", kwargs)
        return None

    @staticmethod
    def query_apps_by_factor_id(factor_id):
        sql = f"""
        SELECT name
        FROM product_application pa
                 JOIN factor_application_relation far ON pa.id = far.application_id
        WHERE factor_id = {factor_id}
        """
        return '、'.join([app[0] for app in sql_executor.execute(sql)])

    def click_return(self):
        try:
            self.driver.find_element(*self.return_button).click()
            self.driver.implicitly_wait(config.IMPLICIT_WAIT)
        except NoSuchElementException as ex:
            self.assertIsNone(ex, f'当前页面{self.driver.current_url}中未找到返回button！')

    @classmethod
    def setUpClass(cls) -> None:
        super(BaseTestCase, cls).setUpClass()
        cls.login()
        cls.factor_fields = [field[0] for field in sql_executor.execute("DESC factor")]
