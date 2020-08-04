#! /usr/bin/env python3
# -*- coding:utf-8 -*-

import re

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from ... import consts
from ...core import case_tag
from ...logger import logger
from ...sql_executor import sql_executor
from .. import config
from .base_test import BaseTestCase

DETAIL_URL_PATTERN = f'{config.SERVER}#/factor/([0-9]+)'


class TestDetail(BaseTestCase):

    def open_factor_detail_page(self, factor_id):
        try:
            self.driver.get(f'{config.SERVER}#/factor/{factor_id}')
            WebDriverWait(self.driver, config.IMPLICIT_WAIT).until(EC.element_to_be_clickable(self.return_button))
        except TimeoutException as ex:
            self.assertIsNone(ex, f'打开因子{factor_id}详情页失败！  {self.driver.current_url}')

    def compare_with_db(self, factor_code):
        re_m = re.match(consts.FACTOR_CODE_PATTERN, factor_code)
        if self.assertIsNotNone(re_m, f'无效的因子编号: {factor_code}'):
            factor_id = re_m.group(1)
            factor = self.query_factors_from_db(*self.factor_fields, id=factor_id)[0]

            mapping = {
                '因子编号': f"{factor['id_prefix']}{factor['id']}",
                '因子名称': factor['name'],
                '因子类型': consts.FACTOR_TYPES[factor['id_prefix']],
                '被引用次数': str(factor['ref_count']),
                '启用状态': consts.FACTOR_STATUSES[factor['status']],
                '所属应用': self.query_apps_by_factor_id(factor_id)
            }
            if factor_code.startswith(consts.FTYPE_THIRD_PREFIX):
                svc = sql_executor.execute(f"SELECT name FROM third_service WHERE id = {factor['service_id']}")[0][0]
                mapping['第三方服务名称'] = svc
            else:
                # 基础因子不应展示服务相关信息
                with self.assertRaises(NoSuchElementException):
                    self.driver.find_element_by_xpath(r'//label[contains(text(), "第三方服务名称")]')

            for key, exp in mapping.items():
                try:
                    element = self.driver.find_element_by_xpath(f'//label[contains(text(), "{key}")]/../div/div')
                except NoSuchElementException as ex:
                    self.assertIsNone(ex, f'因子详情页中未找到属性： {key}')
                else:
                    val = self.get_element_attribute(element, 'text')
                    self.assertEqual(val, exp, f'因子({factor_code})属性{key}不匹配！展示{val}，应为{exp}')
            logger.info("因子(%s)详情页校验成功！", factor_code)

    @case_tag(name='【因子详情页】因子展示信息及返回')
    def test(self):
        # 基础因子
        basic_factor_id = self.random_factor_id(id_prefix=consts.FTYPE_BASIC_PREFIX)
        self.open_factor_detail_page(basic_factor_id)
        basic_factor = f'{consts.FTYPE_BASIC_PREFIX}{basic_factor_id}'
        self.compare_with_db(basic_factor)

        # 三方因子
        third_factor_id = self.random_factor_id(id_prefix=consts.FTYPE_THIRD_PREFIX)
        self.open_factor_detail_page(third_factor_id)
        third_factor = f'{consts.FTYPE_THIRD_PREFIX}{third_factor_id}'
        self.compare_with_db(third_factor)

        # 返回
        self.click_return()
        exp_url = f'{config.SERVER}#/factor/{basic_factor_id}'
        try:
            WebDriverWait(self.driver, config.IMPLICIT_WAIT).until(EC.url_contains(exp_url))
        except TimeoutException as ex:
            self.assertIsNone(ex, f'未返回至基础因子{basic_factor_id}详情页！')
        else:
            self.compare_with_db(basic_factor)
