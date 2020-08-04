#! /usr/bin/env python3
# -*- coding:utf-8 -*-

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from functional_tests import consts
from functional_tests.core import case_tag
from functional_tests.logger import logger
from functional_tests.web import config
from functional_tests.web.rules.base_test import BaseRuleTestCase


class TestDetail(BaseRuleTestCase):
    return_button = (By.XPATH, r'//button/span[contains(text(), "返回")]/..')

    def open_rule_detail_page(self, rule_id):
        try:
            self.driver.get(f'{config.SERVER}#/rule/{rule_id}')
            WebDriverWait(self.driver, config.IMPLICIT_WAIT).until(EC.element_to_be_clickable(self.return_button))
        except TimeoutException as ex:
            self.assertIsNone(ex, f'打开规则{rule_id}详情页失败！  {self.driver.current_url}')

    def compare_with_db(self, rule_id):
        rule = self.query_rules_from_db(*self.rule_fields, id=rule_id)[0]

        mapping = {
            '规则编号': rule['rule_code'],
            '规则名称': rule['name'],
            '外部名称': rule['external_name'],
            '规则描述': rule['description'],
            '适用范围': self.query_rule_set_category(rule_id),
            '启用状态': consts.FACTOR_STATUSES[rule['status']],
            '所属应用': self.query_apps_by_rule_code(rule['rule_code'])
        }

        for key, exp in mapping.items():
            try:
                element = self.driver.find_element_by_xpath(f'//label[contains(text(), "{key}")]/../div/div')
            except NoSuchElementException as ex:
                self.assertIsNone(ex, f'规则详情页中未找到属性： {key}')
            else:
                val = self.get_element_attribute(element, 'text')
                self.assertEqual(val, exp, f'规则({rule["rule_code"]})属性{key}不匹配！展示{val}，应为{exp}')
        logger.info("规则(%s)详情页校验成功！", rule["rule_code"])

    def click_return(self):
        try:
            self.driver.find_element(*self.return_button).click()
            self.driver.implicitly_wait(config.IMPLICIT_WAIT)
        except NoSuchElementException as ex:
            self.assertIsNone(ex, f'当前页面{self.driver.current_url}中未找到返回button！')

    @case_tag(name='【规则详情页】规则展示信息及返回')
    def test(self):
        rule_id = self.random_rule_id()
        self.open_rule_detail_page(rule_id)
        self.compare_with_db(rule_id)
