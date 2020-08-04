#! /usr/bin/env python3
# -*- coding:utf-8 -*-

import random
import time
from datetime import datetime

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from ... import consts
from ...core import case_tag, update_reset
from ...logger import logger
from ...sql_executor import sql_executor
from ...utils import utc2local
from .. import config
from .base_test import BaseRuleTestCase


class TestList(BaseRuleTestCase):

    url = f'{config.SERVER}#/rule'

    rule_columns = ('code', 'name', 'external_name', 'description', 'scope', 'status', 'application',
                    'ref_count', 'modify_user', 'modify_time')

    rule_xpath = r'//td[contains(@class, "is-hidden")]//span[contains(text(), "查看")]/../../../../..'
    rules_count_xpath = r'//span[@class="el-pagination__total"]'

    datetime_fmt = '%Y-%m-%d %H:%M:%S'

    # 筛选框定位
    rule_code_input = '//input[contains(@placeholder,"请输入规则编号")]'
    rule_name_input = '//input[contains(@placeholder,"请输入规则名称")]'
    rule_external_name_input = '//input[contains(@placeholder,"请输入规则外部名称")]'
    rule_status_input = '//input[contains(@placeholder,"启用状态")]'

    query_button = '//span[contains(text(),"查询")]'
    reset_button = '//span[contains(text(),"重置")]'

    # 规则名称筛选参数
    rule_name_test = 'uk'

    def setUp(self) -> None:
        self.open_list_page()
        self.get_max_page()

    # 1、拿随机rule的信息与数据库做比对
    def compare_random_rule_with_db(self, rule_row):
        rule_code = self.get_rule_attribute(rule_row, 'code')
        if self.assertIsNotNone(rule_code, f'无效的规则编号: {rule_code}'):
            rule = self.query_rules_from_db(*self.rule_fields, rule_code=rule_code)[0]

            attrs = [
                f"{rule['rule_code']}",
                rule['name'],
                rule['external_name'],
                '' if rule['description'] is None else rule['description'],
                self.query_rule_set_category(rule['id']),
                consts.FACTOR_STATUSES[rule['status']],
                self.query_apps_by_rule_code(rule_code),
                str(rule['ref_count']),
                rule['modify_user'],
                utc2local(rule['modify_time'], fmt=self.datetime_fmt)
            ]

            for idx, exp in enumerate(attrs, start=1):
                val = self.get_element_attribute(rule_row.find_element_by_xpath(f'td[{idx}]'), 'text')
                self.assertEqual(exp, val, f'规则({rule_code})属性不匹配！展示{val}，应为{exp}')
            logger.info("规则列表页信息(%s)校验成功！", rule_code)

    # 2、拿所有的rule，与数据库相对应的应用id做条件，查询是否符合结果
    def compare_rules_relate_application_with_db(self):
        rule_code_list = list()

        for rule in self.driver.find_elements_by_xpath(self.rule_xpath):
            rule_code_list.append(self.get_rule_attribute(rule, 'code'))

        self.assertIsNotNone(rule_code_list)

        rules_code = ', '.join([f"'{code}'" for code in rule_code_list])

        raw_sql = f'''
                SELECT
                    application_id
                FROM
                    rule
                WHERE
                    rule_code IN ({rules_code})'''
        rules_app_id = sql_executor.execute(raw_sql)

        raw_sql_prod_app = f"""SELECT id FROM product_application WHERE name = '{self.get_prod_app()}'"""
        exp_prod_app_id = sql_executor.execute(raw_sql_prod_app)

        for app_id in rules_app_id:
            self.assertEqual(app_id['application_id'],
                             exp_prod_app_id[0]['id'],
                             f"规则与应用不匹配！{app_id['application_id']} != {exp_prod_app_id[0]['id']}")

    def get_rule_attribute(self, rule_row, attr):
        if str(attr).lower() not in self.rule_columns:
            logger.error("%s列表页不展示属性%s！", self.case_name, attr)
            return None
        return self.get_element_attribute(
            rule_row.find_element_by_xpath(f'td[{self.rule_columns.index(attr) + 1}]'), 'text')

    def get_prod_app(self):
        prod_app = BaseRuleTestCase.get_element_attribute(
            self.driver.find_element_by_xpath(r"//div[contains(@class, 'wrapper')]/ul[contains(@role, 'menubar')]"),
            'text'
        ).split()[0]
        return prod_app

    @case_tag(name='【规则列表页】规则展示信息')
    def test_check_rule_info(self):
        self.compare_random_rule_with_db(random.choice(self.driver.find_elements_by_xpath(self.rule_xpath)))

    @case_tag(name='【规则列表页】规则与应用关联展示')
    def test_check_app_relation(self):
        self.set_page_size(30)
        btn = self.driver.find_element_by_xpath(r'//button[@class="btn-next"]')

        self.compare_rules_relate_application_with_db()
        # 取出所有rule_code
        while self.get_element_attribute(btn, 'disabled') is False:
            self.compare_rules_relate_application_with_db()

        logger.info("规则页校验所有规则与应用是否关联成功！现在刷新页面。")
        self.driver.refresh()

    @case_tag(name='【规则列表页】翻页')
    def test_page(self):
        self.assertEqual(10, self.page_size, f'默认页面大小应为10，实际为{self.page_size}')
        for _ in range(self.max_page):
            self.page_down()
        for _ in range(self.max_page):
            self.page_up()

        self.set_page_size(30)
        for _ in range(self.max_page):
            self.page_down()
        for _ in range(self.max_page):
            self.page_up()

        self.set_page_size(3)
        self.page2number(random.randint(1, self.max_page))
        self.page2number(0)
        self.page2number(random.randint(self.max_page + 1, self.max_page * 10))
        self.page2number(random.randint(0, self.max_page * 10) / 10)

    def get_rule_mod_datetime(self, rule_row):
        return datetime.strptime(self.get_rule_attribute(rule_row, 'modify_time'), self.datetime_fmt)

    @case_tag(name='【规则列表页】规则排序')
    def test_order(self):
        cur_rules = self.driver.find_elements_by_xpath(self.rule_xpath)
        if len(cur_rules) < 2:
            logger.warning("当前规则数目小于2，无法测试排序！")
            return

        i, j = random.choices(range(len(cur_rules)), k=2)

        while i == j:
            j = random.randint(0, len(cur_rules) - 1)

        mod_dts = [self.get_rule_mod_datetime(cur_rules[idx]) for idx in sorted({i, j, len(cur_rules) - 1})]
        for i in range(len(mod_dts) - 1):
            self.assertTrue(mod_dts[i] >= mod_dts[i + 1], '列表页规则未按更新时间逆序排序！')

        if self.get_current_page_num() < self.max_page:
            self.page2number(random.randint(2, self.max_page))
            mod_dt = self.get_rule_mod_datetime(random.choice(self.driver.find_elements_by_xpath(self.rule_xpath)))
            self.assertTrue(mod_dts[-1] >= mod_dt, f'当前页面规则更新时间{mod_dt}晚于首页最末规则更新时间{mod_dts[-1]}！')
        logger.info("列表页规则按更新时间逆序排序校验通过！")

    def mod_rule_status(self, rule_code, rule_stat, rule_ref_cnt, cancel_action=False):
        btn_xpath = (f'//td[contains(@class, "is-hidden")]//div[contains(text(), "{rule_code}")]/../..'
                     f'/td[{len(self.rule_columns) + 1}]//button'
                     f'/span[contains(text(), "{consts.BTN_ENABLE}") or contains(text(), "{consts.BTN_DISABLE}")]/..')
        try:
            mod_btn = self.driver.find_element_by_xpath(btn_xpath)
            mod_btn_desc = self.get_element_attribute(mod_btn, 'text')
            action = consts.BTN_DISABLE if rule_stat == consts.STAT_ENABLE else consts.BTN_ENABLE
            self.assertEqual(action, mod_btn_desc,
                             f'{rule_stat}规则{rule_code}的button为{mod_btn_desc}，应为{action}!')

            msg_box_xpath = '//div[contains(@class, "el-message-box")]//div[contains(@class, "el-message-box__btns")]'
            confirm = consts.CANCEL if cancel_action else consts.CONFIRM
            self.do_mod_ele_status(mod_btn, msg_box_xpath, confirm, rule_code, rule_stat, rule_ref_cnt)
        except NoSuchElementException as ex:
            self.assertIsNone(ex, f'未找到规则{rule_code}的启用/停用button！')

    def find_rule_rows(self, **kwargs):
        if set(kwargs.keys()).difference(self.rule_columns):
            logger.error("规则查询条件无效！    %s", kwargs)
            return None

        rule_rows = list()
        try:
            for row in self.driver.find_elements_by_xpath(self.rule_xpath):
                match = True
                for attr, val in kwargs.items():
                    if str(val) != self.get_rule_attribute(row, attr):
                        match = False
                        break
                if match:
                    rule_rows.append(row)
            return rule_rows if rule_rows else None
        except NoSuchElementException:
            logger.error("当前页面（%s）没有找到匹配的规则!    %s", self.driver.current_url, kwargs)
            return None

    def check_rule_attributes(self, rule_code, **kwargs):
        self.assertSetEqual(set(), set(kwargs.keys()).difference(self.rule_columns), f'要检查的规则属性错误！  {kwargs}')
        rule_row = self.find_rule_rows(code=rule_code)
        self.assertIsNotNone(rule_row, f'当前页面无法找到规则{rule_row}！')

        rule_row = rule_row[0]
        for attr, exp in kwargs.items():
            val = self.get_rule_attribute(rule_row, attr)
            self.assertEqual(str(exp), val, f'规则{rule_code}属性{attr}应为{exp}，实际显示为{val}')
        logger.info("规则%s属性检查成功！    %s", rule_code, kwargs)

    def check_modification(self, rule_row, cancel_action=False):
        attrs = ('code', 'status', 'ref_count', 'modify_user', 'modify_time')
        code, stat, ref_cnt, mod_user, mod_dt = [self.get_rule_attribute(rule_row, col) for col in attrs]

        self.mod_rule_status(code, stat, ref_cnt, cancel_action)
        if not cancel_action and self.if_ele_status_modifiable(stat, ref_cnt):
            stat = consts.STAT_DISABLE if stat == consts.STAT_ENABLE else consts.STAT_ENABLE
            mod_user = self.user
            new_mod_dt = self.get_rule_mod_datetime(rule_row)
            self.assertTrue(new_mod_dt > datetime.strptime(mod_dt, self.datetime_fmt),
                            f'更改规则{code}状态后更新时间校验失败！  更新前时间：{mod_dt}  更新后时间：{new_mod_dt}')
            mod_dt = new_mod_dt.strftime(self.datetime_fmt)
        self.check_rule_attributes(code, status=stat, ref_count=ref_cnt, modify_user=mod_user, modify_time=mod_dt)

        self.open_list_page()
        if not cancel_action and self.if_ele_status_modifiable(stat, ref_cnt):
            first_rule = self.get_rule_attribute(self.driver.find_elements_by_xpath(self.rule_xpath)[0], 'code')
            self.assertEqual(code, first_rule, f'修改状态并刷新页面后，规则{code}应在首页首行显示！')

    @case_tag(name='【规则列表页】修改规则启用状态')
    @update_reset('rule')
    def test_mod_rule_status(self):
        self.page2number(self.max_page)
        rule_row = self.driver.find_elements_by_xpath(self.rule_xpath)[-1]
        attrs = ('code', 'status', 'ref_count')
        rule_code, rule_stat, rule_ref_cnt = [self.get_rule_attribute(rule_row, col) for col in attrs]

        if not self.if_ele_status_modifiable(rule_stat, rule_ref_cnt):
            sql_executor.execute(
                f"UPDATE rule SET status = {consts.STAT_UNKNOWN_CODE}, ref_count = 0 WHERE rule_code = '{rule_code}'")
            self.open_list_page()
            self.page2number(self.max_page)
            self.check_rule_attributes(rule_code, status=consts.STAT_UNKNOWN, ref_count=0)

        # 取消更改规则状态
        self.check_modification(self.find_rule_rows(code=rule_code)[0], cancel_action=True)
        self.page2number(self.max_page)
        last_rule = self.get_rule_attribute(self.driver.find_elements_by_xpath(self.rule_xpath)[-1], 'code')
        self.assertEqual(rule_code, last_rule, f'取消修改状态，规则{rule_code}显示位置应保持不变（末页末行）！')
        # 执行更改规则状态
        self.check_modification(self.find_rule_rows(code=rule_code)[0])
        # 重新登录测试用户
        self.logout()
        self.login(prod_app=self.prod_app)
        # 禁止更改规则状态
        ref_cnt = random.randint(1, 100)
        logger.info("启用规则%s并设置其引用次数为%d", rule_code, ref_cnt)
        sql_executor.execute(
            f"UPDATE rule SET status = {consts.STAT_ENABLE_CODE}, ref_count = {ref_cnt} "
            f"WHERE rule_code = '{rule_code}'")
        self.open_list_page()
        self.check_rule_attributes(rule_code, status=consts.STAT_ENABLE, ref_count=ref_cnt)
        self.check_modification(self.find_rule_rows(code=rule_code)[0])

    def reset_selector(self):
        try:
            self.driver.find_element_by_xpath(self.reset_button).click()
            self.driver.find_element_by_xpath(self.query_button).click()
        except NoSuchElementException:
            logger.critical("未发现重置按钮！")

    @case_tag(name='【规则列表页】查看筛选功能')
    def test_selector(self):
        # 获取当前产品id
        sql = f"""SELECT id FROM product_application WHERE name = '{self.prod_app}'"""
        prod_id = sql_executor.execute(sql)[0][0]

        rule_id = self.random_rule_id(application_id=prod_id)
        rule = self.query_rules_from_db(id=rule_id)[0]
        rule_code = rule['rule_code']

        # 规则编号筛选框
        try:
            self.assertTrue(len(self.driver.find_elements_by_xpath(self.rule_xpath)) > 0, "应用下无规则，停止本次测试。")
            self.driver.find_element_by_xpath(self.rule_code_input).send_keys(rule_code)
            self.driver.find_element_by_xpath(self.query_button).click()
            self.assertEqual(len(self.driver.find_elements_by_xpath(self.rule_xpath)), 1, "规则编号筛选功能测试未通过！"
                                                                                          "筛选出多个结果")
            self.compare_random_rule_with_db(self.driver.find_elements_by_xpath(self.rule_xpath)[0])

            # 重置筛选
            self.reset_selector()
        except NoSuchElementException:
            logger.critical("当前页面无法找到规则编号筛选框！")

        # 规则名称筛选栏
        try:
            sql_raw = \
                f"SELECT count(*) FROM rule WHERE NAME LIKE '%{self.rule_name_test}%' AND application_id = {prod_id}"
            exp_num = sql_executor.execute(sql_raw)[0][0]
            self.driver.find_element_by_xpath(self.rule_name_input).send_keys(self.rule_name_test)
            self.driver.find_element_by_xpath(self.query_button).click()
            rel_num = self.driver.find_element_by_xpath(self.rules_count_xpath).text.split()[1]
            self.assertEqual(int(exp_num), int(rel_num), '规则名称筛选功能测试未通过！筛选结果与数据库结果不一致！')

            self.reset_selector()
        except NoSuchElementException:
            logger.critical("当前页面无法找到规则名称筛选框！")

        # 规则外部名称筛选栏
        try:
            sql_raw = f"SELECT count(*) FROM rule WHERE external_name LIKE '%{self.rule_name_test}%' " \
                      f"AND application_id={prod_id}"
            exp_num = sql_executor.execute(sql_raw)[0][0]
            self.driver.find_element_by_xpath(self.rule_name_input).send_keys(self.rule_name_test)
            self.driver.find_element_by_xpath(self.query_button).click()
            rel_num = self.driver.find_element_by_xpath(self.rules_count_xpath).text.split()[1]
            self.assertEqual(int(exp_num), int(rel_num), '规则名称筛选功能测试未通过！筛选结果与数据库结果不一致！')

            self.reset_selector()
        except NoSuchElementException:
            logger.critical("当前页面无法找到规则名称筛选框！")

        # 规则状态筛选栏
        for code, stat in consts.FACTOR_STATUSES.items():
            self.driver.find_element_by_xpath(self.rule_status_input).click()
            WebDriverWait(self.driver, config.IMPLICIT_WAIT).until(EC.element_to_be_clickable((
                By.XPATH,
                f'//li/span[contains(text(),"{stat}")]'))
            )
            self.driver.find_element_by_xpath(f'//li/span[contains(text(),"{stat}")]').click()
            self.driver.find_element_by_xpath(self.query_button).click()
            sql_raw = f"""SELECT count(*) FROM rule WHERE status = {code} AND application_id = {prod_id}"""
            exp_num = sql_executor.execute(sql_raw)[0][0]
            rel_num = self.driver.find_element_by_xpath(self.rules_count_xpath).text.split()[1]
            self.assertEqual(int(exp_num), int(rel_num), '规则状态筛选功能测试未通过！筛选结果与数据库结果不一致！')
            self.reset_selector()

    def test_multiple_selector(self):
        sql = f"""SELECT id FROM product_application WHERE name = '{self.prod_app}'"""
        prod_id = sql_executor.execute(sql)[0][0]

        # 获取随机规则
        rule_info = random.choice(self.query_rules_from_db('rule_code', 'name', 'external_name', 'status',
                                                           application_id=prod_id))
        rule_code, name, external_name, status = rule_info
        stat = consts.FACTOR_STATUSES[status]

        # 使用四个组合筛选栏
        try:
            self.driver.find_element_by_xpath(self.rule_code_input).send_keys(rule_code)
            self.driver.find_element_by_xpath(self.rule_name_input).send_keys(name)
            self.driver.find_element_by_xpath(self.rule_external_name_input).send_keys(external_name)
            self.driver.find_element_by_xpath(self.rule_status_input).click()
            WebDriverWait(self.driver, config.IMPLICIT_WAIT).until(EC.element_to_be_clickable((
                By.XPATH,
                f'//li/span[contains(text(),"{stat}")]'))
            )
            self.driver.find_element_by_xpath(f'//li/span[contains(text(),"{stat}")]').click()
        except NoSuchElementException:
            logger.critical("未找到筛选框！")

        self.driver.find_element_by_xpath(self.query_button).click()
        time.sleep(2)
        self.assertTrue(len(self.driver.find_elements_by_xpath(self.rule_xpath)) == 1, f'查询失败！当前规则{rule_code}'
                                                                                       f'查询结果不唯一')
        self.compare_random_rule_with_db(self.driver.find_elements_by_xpath(self.rule_xpath)[0])

        # 进入详情页，再返回，应保留筛选栏状态
        self.driver.find_elements_by_xpath('//span[contains(text(), "查看")]')[1].click()
        WebDriverWait(self.driver, config.IMPLICIT_WAIT).until(EC.element_to_be_clickable(self.return_button))
        self.click_return()

        self.assertEqual(self.driver.find_element_by_xpath(self.rule_code_input).get_attribute('value'), rule_code)
        self.assertEqual(self.driver.find_element_by_xpath(self.rule_name_input).get_attribute('value'), name)
        self.assertEqual(self.driver.find_element_by_xpath(self.rule_external_name_input).get_attribute('value'),
                         external_name)
        self.driver.find_element_by_xpath(self.rule_status_input).click()
        self.assertTrue(self.driver.find_element_by_xpath(f'//li[contains(@class, "el-select-dropdown__item selected")]'
                                                          f'/span[contains(text(), "{stat}")]'))

        # 重置筛选栏，查看页码是否恢复为1
        self.reset_selector()
        self.assertTrue(self.driver.find_element_by_xpath(
            '//li[contains(@class, "number active") and contains(text(), "1")]'))
