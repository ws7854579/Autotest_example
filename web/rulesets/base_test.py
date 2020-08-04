#! /usr/bin/env python3
# -*- coding:utf-8 -*-

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By

from ...sql_executor import sql_executor
from .. import config
from ..base_web_test import BaseWebTestCase


class BaseRuleSetTestCase(BaseWebTestCase):
    case_name = '规则集'

    url = config.SERVER

    return_button = (By.XPATH, r'//button/span[contains(text(), "返回")]/..')

    @classmethod
    def setUpClass(cls) -> None:
        super(BaseRuleSetTestCase, cls).setUpClass()
        cls.login()
        cls.ruleset_fields = [field[0] for field in sql_executor.execute("DESC rule_set")]

    @staticmethod
    def query_ruleset_from_db(*args, order=None, desc=False, limit=None, **kwargs):
        filters = list()
        for fld, val in kwargs.items():
            if isinstance(val, tuple):
                filters.append(f" WHERE {fld} IN {val}")
            else:
                filters.append(f" WHERE {fld} = '{val}'")

        fields = ', '.join(['rule_set.id' if fld == 'id' else fld for fld in args]) if args else 'rule_set.*'

        raw_sql = f"""SELECT DISTINCT {fields} FROM rule_set"""

        if filters:
            raw_sql += ' AND'.join(filters)
        if order:
            raw_sql += f' ORDER BY {order}'
            if desc:
                raw_sql += ' DESC'
        if limit:
            raw_sql += f' LIMIT {limit}'

        return sql_executor.execute(raw_sql)

    @staticmethod
    def query_rule_set_category(ruleset_type_id):
        sql = f"""SELECT name FROM rule_set_category WHERE id = {ruleset_type_id}"""
        return sql_executor.execute(sql)[0][0]

    @staticmethod
    def query_app_name(app_id):
        sql = f"""SELECT name FROM product_application WHERE id = {app_id}"""
        return sql_executor.execute(sql)[0][0]

    def click_return(self):
        try:
            self.driver.find_element(*self.return_button).click()
            self.driver.implicitly_wait(config.IMPLICIT_WAIT)
        except NoSuchElementException as ex:
            self.assertIsNone(ex, f'当前页面{self.driver.current_url}中未找到返回button！')
