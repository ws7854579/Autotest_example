#! /usr/bin/env python3
# -*- coding:utf-8 -*-
import random

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By

from functional_tests.logger import logger
#from functional_tests.sql_executor import sql_executor
from functional_tests.web import config
from functional_tests.web.base_web_test import BaseWebTestCase


class BaseRuleTestCase(BaseWebTestCase):

    case_name = '规则'

    url = config.SERVER

    return_button = (By.XPATH, r'//button/span[contains(text(), "返回")]/..')

    @staticmethod
    def query_rules_from_db(*args, order=None, desc=False, limit=None, **kwargs):
        filters = list()
        for fld, val in kwargs.items():
            if isinstance(val, tuple):
                filters.append(f" WHERE {fld} IN {val}")
            else:
                filters.append(f" WHERE {fld} = '{val}'")

        fields = ', '.join(['rule.id' if fld == 'id' else fld for fld in args]) if args else 'rule.*'

        raw_sql = f"""SELECT DISTINCT {fields} FROM rule"""

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
    def query_apps_by_rule_code(rule_code):
        sql = f"""
            SELECT pa.name
            FROM product_application pa
                     JOIN rule ON pa.id = rule.application_id
            WHERE rule_code = '{rule_code}'
            """
        return '、'.join([app[0] for app in sql_executor.execute(sql)])

    @staticmethod
    def query_rule_set_category(rule_id):
        sql = f"""
        SELECT
            rsc. NAME
        FROM
            rule_set_category rsc
        LEFT JOIN rule_scope rs ON rsc.id = rs.rulesetcategory_id
        WHERE
            rs.rule_id = {rule_id}
                    """
        return '、'.join([app[0] for app in sql_executor.execute(sql)])

    @classmethod
    def random_rule_id(cls, **kwargs):
        rets = cls.query_rules_from_db('id', **kwargs)
        if rets:
            return random.choice(rets)[0]

        logger.error("没有匹配过滤条件的规则！ %s", kwargs)
        return None

    def click_return(self):
        try:
            self.driver.find_element(*self.return_button).click()
            self.driver.implicitly_wait(config.IMPLICIT_WAIT)
        except NoSuchElementException as ex:
            self.assertIsNone(ex, f'当前页面{self.driver.current_url}中未找到返回button！')

    @classmethod
    def setUpClass(cls) -> None:
        super(BaseRuleTestCase, cls).setUpClass()
        cls.login()
        cls.rule_fields = [field[0] for field in sql_executor.execute("DESC rule")]
