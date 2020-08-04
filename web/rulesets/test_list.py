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
from .base_test import BaseRuleSetTestCase


class TestList(BaseRuleSetTestCase):  # pylint:disable=too-many-public-methods

    url = f'{config.SERVER}#/rule_set'

    wait_el_xpath = r'//td[contains(@class, "is-hidden")]//span[contains(text(), "规则列表")]/../../../../..'

    ruleset_columns = ('code', 'name', 'description', 'scope', 'risk_control_mode', 'route_mode', 'status',
                       'application', 'ref_count', 'modify_user', 'modify_time')

    ruleset_xpath = r'//td[contains(@class, "is-hidden")]//span[contains(text(), "规则列表")]/../../../../..'
    ruleset_count_xpath = r'//span[@class="el-pagination__total"]'

    datetime_fmt = '%Y-%m-%d %H:%M:%S'

    # 筛选框定位
    ruleset_code_input = '//input[contains(@placeholder,"请输入规则集编号")]'
    ruleset_name_input = '//input[contains(@placeholder,"请输入规则集名称")]'
    ruleset_type_input = '//input[contains(@placeholder,"规则集类型")]'
    ruleset_status_input = '//input[contains(@placeholder,"启用状态")]'

    query_button = '//span[contains(text(),"查询")]'
    reset_button = '//span[contains(text(),"重置")]'

    # 规则集名称筛选参数
    ruleset_name_test = 'uk'

    create_button = '//button[contains(@class, "el-button add-audit el-button--primary el-button--medium")]/span' \
                    '[contains(text(),"添加规则集")]'

    cancel_button = '//button[contains(@class, "el-button el-button--default")]/span[contains(text(), "取 消")]'

    def setUp(self) -> None:
        self.open_list_page()
        self.get_max_page()

    @classmethod
    def random_ruleset_id(cls, **kwargs):
        rets = cls.query_ruleset_from_db('id', **kwargs)
        if rets:
            return random.choice(rets)[0]

        logger.error("没有匹配过滤条件的规则集！ %s", kwargs)
        return None

    # 1、拿随机rule set的信息与数据库做比对
    def compare_random_ruleset_with_db(self, ruleset_row):
        ruleset_code = self.get_ruleset_attribute(ruleset_row, 'code')
        if self.assertIsNotNone(ruleset_code, f'无效的规则集编号: {ruleset_code}'):
            ruleset = self.query_ruleset_from_db(*self.ruleset_fields, rule_set_code=ruleset_code)[0]

            attrs = [
                f"{ruleset['rule_set_code']}",
                ruleset['name'],
                '' if ruleset['description'] is None else ruleset['description'],
                self.query_rule_set_category(ruleset['rule_set_type_id']),
                '' if ruleset['risk_control_mode'] is None else consts.RISK_CONTROL_MODEL[ruleset['risk_control_mode']],
                '' if ruleset['route_mode'] is None else consts.ROUTE_MODEL[ruleset['route_mode']],
                consts.FACTOR_STATUSES[ruleset['status']],
                self.query_app_name(ruleset['application_id']),
                str(ruleset['ref_count']),
                ruleset['modify_user'],
                utc2local(ruleset['modify_time'], fmt=self.datetime_fmt)
            ]

            for idx, exp in enumerate(attrs, start=1):
                val = self.get_element_attribute(ruleset_row.find_element_by_xpath(f'td[{idx}]'), 'text')
                self.assertEqual(exp, val, f'规则集({ruleset_code})属性不匹配！展示{val}，应为{exp}')
            logger.info("规则列表页信息(%s)校验成功！", ruleset_code)

    def get_ruleset_attribute(self, ruleset_row, attr):
        if str(attr).lower() not in self.ruleset_columns:
            logger.error("%s列表页不展示属性%s！", self.case_name, attr)
            return None
        return self.get_element_attribute(
            ruleset_row.find_element_by_xpath(f'td[{self.ruleset_columns.index(attr) + 1}]'), 'text')

    @case_tag(name='【规则集列表页】规则集展示信息')
    def test_check_ruleset_info(self):
        self.compare_random_ruleset_with_db(random.choice(self.driver.find_elements_by_xpath(self.ruleset_xpath)))

    @case_tag(name='【规则集列表页】翻页')
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

    def get_ruleset_mod_datetime(self, ruleset_row):
        return datetime.strptime(self.get_ruleset_attribute(ruleset_row, 'modify_time'), self.datetime_fmt)

    @case_tag(name='【规则集列表页】规则集排序')
    def test_order(self):
        cur_ruleset = self.driver.find_elements_by_xpath(self.ruleset_xpath)
        if len(cur_ruleset) < 2:
            logger.warning("当前规则集数目小于2，无法测试排序！")
            return

        i, j = random.choices(range(len(cur_ruleset)), k=2)
        while i == j:
            j = random.randrange(len(cur_ruleset))

        mod_dts = [self.get_ruleset_mod_datetime(cur_ruleset[idx]) for idx in sorted({i, j, len(cur_ruleset) - 1})]
        for i in range(len(mod_dts) - 1):
            self.assertTrue(mod_dts[i] >= mod_dts[i + 1], '列表页规则集未按更新时间逆序排序！')

        if self.get_current_page_num() < self.max_page:
            self.page2number(random.randint(2, self.max_page))
            mod_dt = self.get_ruleset_mod_datetime(
                random.choice(self.driver.find_elements_by_xpath(self.ruleset_xpath))
            )
            self.assertTrue(mod_dts[-1] >= mod_dt, f'当前页面规则集更新时间{mod_dt}晚于首页最末规则集更新时间{mod_dts[-1]}！')
        logger.info("列表页规则集按更新时间逆序排序校验通过！")

    def mod_ruleset_status(self, ruleset_code, ruleset_stat, ruleset_ref_cnt, cancel_action=False):
        btn_xpath = (f'//td[contains(@class, "is-hidden")]//div[contains(text(), "{ruleset_code}")]/../..'
                     f'/td[{len(self.ruleset_columns) + 1}]//button'
                     f'/span[contains(text(), "{consts.BTN_ENABLE}") or contains(text(), "{consts.BTN_DISABLE}")]/..')
        try:
            mod_btn = self.driver.find_element_by_xpath(btn_xpath)
            mod_btn_desc = self.get_element_attribute(mod_btn, 'text')
            action = consts.BTN_DISABLE if ruleset_stat == consts.STAT_ENABLE else consts.BTN_ENABLE
            self.assertEqual(action, mod_btn_desc,
                             f'{ruleset_stat}规则集{ruleset_code}的button为{mod_btn_desc}，应为{action}!')

            msg_box_xpath = '//div[contains(@class, "el-message-box")]//div[contains(@class, "el-message-box__btns")]'
            confirm = consts.CANCEL if cancel_action else consts.CONFIRM
            self.do_mod_ele_status(mod_btn, msg_box_xpath, confirm, ruleset_code, ruleset_stat, ruleset_ref_cnt)
        except NoSuchElementException as ex:
            self.assertIsNone(ex, f'未找到规则集{ruleset_code}的启用/停用button！')

    def find_ruleset_rows(self, **kwargs):
        if set(kwargs.keys()).difference(self.ruleset_columns):
            logger.error("规则集查询条件无效！    %s", kwargs)
            return None

        ruleset_rows = list()
        try:
            for row in self.driver.find_elements_by_xpath(self.ruleset_xpath):
                match = True
                for attr, val in kwargs.items():
                    if str(val) != self.get_ruleset_attribute(row, attr):
                        match = False
                        break
                if match:
                    ruleset_rows.append(row)
            return ruleset_rows if ruleset_rows else None
        except NoSuchElementException:
            logger.error("当前页面（%s）没有找到匹配的规则集!    %s", self.driver.current_url, kwargs)
            return None

    def check_ruleset_attributes(self, ruleset_code, **kwargs):
        self.assertSetEqual(set(), set(kwargs.keys()).difference(self.ruleset_columns), f'要检查的规则集属性错误！  {kwargs}')
        ruleset_row = self.find_ruleset_rows(code=ruleset_code)
        self.assertIsNotNone(ruleset_row, f'当前页面无法找到规则集{ruleset_row}！')

        ruleset_row = ruleset_row[0]
        for attr, exp in kwargs.items():
            val = self.get_ruleset_attribute(ruleset_row, attr)
            self.assertEqual(str(exp), val, f'规则集{ruleset_code}属性{attr}应为{exp}，实际显示为{val}')
        logger.info("规则集%s属性检查成功！    %s", ruleset_code, kwargs)

    def check_modification(self, ruleset_row, cancel_action=False):
        attrs = ('code', 'status', 'ref_count', 'modify_user', 'modify_time')
        code, stat, ref_cnt, mod_user, mod_dt = [self.get_ruleset_attribute(ruleset_row, col) for col in attrs]

        self.mod_ruleset_status(code, stat, ref_cnt, cancel_action)
        if not cancel_action and self.if_ele_status_modifiable(stat, ref_cnt):
            stat = consts.STAT_DISABLE if stat == consts.STAT_ENABLE else consts.STAT_ENABLE
            mod_user = self.user
            new_mod_dt = self.get_ruleset_mod_datetime(ruleset_row)
            self.assertTrue(new_mod_dt > datetime.strptime(mod_dt, self.datetime_fmt),
                            f'更改规则集{code}状态后更新时间校验失败！  更新前时间：{mod_dt}  更新后时间：{new_mod_dt}')
            mod_dt = new_mod_dt.strftime(self.datetime_fmt)
        self.check_ruleset_attributes(code, status=stat, ref_count=ref_cnt, modify_user=mod_user, modify_time=mod_dt)

        self.open_list_page()
        if not cancel_action and self.if_ele_status_modifiable(stat, ref_cnt):
            first_ruleset = self.get_ruleset_attribute(
                self.driver.find_elements_by_xpath(self.ruleset_xpath)[0], 'code'
            )
            self.assertEqual(code, first_ruleset, f'修改状态并刷新页面后，规则集{code}应在首页首行显示！')

    @case_tag(name='【规则列表页】修改规则集启用状态')
    @update_reset(table='rule_set')
    def test_mod_ruleset_status(self):
        self.page2number(self.max_page)
        ruleset_row = self.driver.find_elements_by_xpath(self.ruleset_xpath)[-1]
        attrs = ('code', 'status', 'ref_count')
        ruleset_code, ruleset_stat, ruleset_ref_cnt = [self.get_ruleset_attribute(ruleset_row, col) for col in attrs]

        if not self.if_ele_status_modifiable(ruleset_stat, ruleset_ref_cnt):
            sql_executor.execute(
                f"UPDATE rule_set SET status = {consts.STAT_UNKNOWN_CODE}, ref_count = 0 "
                f"WHERE rule_set_code = '{ruleset_code}'")
            self.open_list_page()
            self.page2number(self.max_page)
            self.check_ruleset_attributes(ruleset_code, status=consts.STAT_UNKNOWN, ref_count=0)

        # 取消更改规则集状态
        self.check_modification(self.find_ruleset_rows(code=ruleset_code)[0], cancel_action=True)
        self.page2number(self.max_page)
        last_rule = self.get_ruleset_attribute(self.driver.find_elements_by_xpath(self.ruleset_xpath)[-1], 'code')
        self.assertEqual(ruleset_code, last_rule, f'取消修改状态，规则集{ruleset_code}显示位置应保持不变（末页末行）！')
        # 执行更改规则集状态
        self.check_modification(self.find_ruleset_rows(code=ruleset_code)[0])
        # 重新登录测试用户
        self.logout()
        self.login(prod_app=self.prod_app)
        # 禁止更改规则集状态
        ref_cnt = random.randint(1, 100)
        logger.info("启用规则集%s并设置其引用次数为%d", ruleset_code, ref_cnt)
        sql_executor.execute(
            f"UPDATE rule_set SET status = {consts.STAT_ENABLE_CODE}, ref_count = {ref_cnt} "
            f"WHERE rule_set_code = '{ruleset_code}'")
        self.open_list_page()
        self.check_ruleset_attributes(ruleset_code, status=consts.STAT_ENABLE, ref_count=ref_cnt)
        self.check_modification(self.find_ruleset_rows(code=ruleset_code)[0])

    def reset_selector(self):
        try:
            self.driver.find_element_by_xpath(self.reset_button).click()
            self.driver.find_element_by_xpath(self.query_button).click()
        except NoSuchElementException:
            logger.critical("未发现重置按钮！")

    @case_tag(name='【规则集列表页】查看筛选功能')
    def test_selector(self):
        # 获取当前产品id
        prod_id = sql_executor.execute(
            f"""SELECT id FROM product_application WHERE name = '{self.prod_app}'"""
        )[0][0]

        ruleset = self.query_ruleset_from_db(id=self.random_ruleset_id(application_id=prod_id))[0]
        ruleset_code = ruleset['rule_set_code']

        _ruleset_xpath = '//div[contains(@class, "el-table__body-wrapper is-scrolling-left")]/table[contains(@class, ' \
                         '"el-table__body")]/tbody//tr'

        # 规则集编号筛选框
        try:
            self.assertTrue(len(self.driver.find_elements_by_xpath(_ruleset_xpath)) > 0, "应用下无规则集，停止本次测试。")
            self.driver.find_element_by_xpath(self.ruleset_code_input).send_keys(ruleset_code)
            self.driver.find_element_by_xpath(self.query_button).click()
            time.sleep(2)
            self.assertEqual(len(self.driver.find_elements_by_xpath(_ruleset_xpath)), 1, "规则集编号筛选功能测试未通过！"
                                                                                         "筛选出多个结果")
            self.compare_random_ruleset_with_db(self.driver.find_elements_by_xpath(_ruleset_xpath)[0])

            # 重置筛选
            self.reset_selector()
        except NoSuchElementException:
            logger.critical("当前页面无法找到规则集编号筛选框！")

        # 规则集名称筛选栏
        try:
            sql_raw = f"SELECT count(*) FROM rule_set WHERE NAME LIKE '%{self.ruleset_name_test}%' " \
                      f"AND application_id = {prod_id}"
            self.driver.find_element_by_xpath(self.ruleset_name_input).send_keys(self.ruleset_name_test)
            self.driver.find_element_by_xpath(self.query_button).click()
            self.assertEqual(
                int(sql_executor.execute(sql_raw)[0][0]),
                int(self.driver.find_element_by_xpath(self.ruleset_count_xpath).text.split()[1]),
                '规则集名称筛选功能测试未通过！筛选结果与数据库结果不一致！')

            self.reset_selector()
        except NoSuchElementException:
            logger.critical("当前页面无法找到规则集名称筛选框！")

        # 规则集类型筛选栏
        try:
            sql_ret = sql_executor.execute(
                f"""SELECT id,name FROM rule_set_category"""
            )

            category_num = {category[0]: category[1] for category in sql_ret}
            self.driver.find_element_by_xpath(self.ruleset_type_input).click()
            for cid, cname in category_num.items():
                WebDriverWait(self.driver, config.IMPLICIT_WAIT).until(EC.element_to_be_clickable((
                    By.XPATH,
                    f'//li/span[contains(text(),"{cname}")]'))
                )
                self.driver.find_element_by_xpath(f'//li/span[contains(text(),"{cname}")]').click()
                self.driver.find_element_by_xpath(self.query_button).click()
                query_sql = \
                    f"""SELECT count(*) FROM rule_set WHERE rule_set_type_id = {cid} AND application_id={prod_id}"""
                self.assertEqual(
                    int(sql_executor.execute(query_sql)[0][0]),
                    int(self.driver.find_element_by_xpath(self.ruleset_count_xpath).text.split()[1]),
                    "规则集类型筛选功能测试未通过！筛选结果与数据库结果不一致！"
                )
                self.reset_selector()
        except NoSuchElementException:
            logger.critical("当前页面无法找到规则集类型筛选框")

        # 规则集状态筛选栏
        for code, stat in consts.FACTOR_STATUSES.items():
            self.driver.find_element_by_xpath(self.ruleset_status_input).click()
            WebDriverWait(self.driver, config.IMPLICIT_WAIT).until(EC.element_to_be_clickable((
                By.XPATH,
                f'//li/span[contains(text(),"{stat}")]'))
            )
            self.driver.find_element_by_xpath(f'//li/span[contains(text(),"{stat}")]').click()
            self.driver.find_element_by_xpath(self.query_button).click()
            sql_raw = f"""SELECT count(*) FROM rule_set WHERE status = {code} AND application_id = {prod_id}"""
            self.assertEqual(
                int(sql_executor.execute(sql_raw)[0][0]),
                int(self.driver.find_element_by_xpath(self.ruleset_count_xpath).text.split()[1]),
                '规则集状态筛选功能测试未通过！筛选结果与数据库结果不一致！'
            )
            self.reset_selector()

    def test_multiple_selector(self):
        sql = f"""SELECT id FROM product_application WHERE name = '{self.prod_app}'"""
        prod_id = sql_executor.execute(sql)[0][0]

        _ruleset_xpath = '//div[contains(@class, "el-table__body-wrapper is-scrolling-left")]/table[contains(@class, ' \
                         '"el-table__body")]/tbody//tr'

        # 获取随机规则集
        rule_set_info = random.choice(self.query_ruleset_from_db('rule_set_code', 'name', 'rule_set_type_id',
                                                                 'status', application_id=prod_id))
        rule_set_code, name, rule_set_type, status = rule_set_info
        stat = consts.FACTOR_STATUSES[status]
        type_name = sql_executor.execute(f"""SELECT NAME from rule_set_category WHERE id={rule_set_type}""")[0][0]

        # 使用四个组合筛选栏
        try:
            self.driver.find_element_by_xpath(self.ruleset_code_input).send_keys(rule_set_code)
            self.driver.find_element_by_xpath(self.ruleset_name_input).send_keys(name)
            self.driver.find_element_by_xpath(self.ruleset_type_input).click()
            WebDriverWait(self.driver, config.IMPLICIT_WAIT).until(EC.element_to_be_clickable((
                By.XPATH,
                f'//li/span[contains(text(),"{type_name}")]'))
            )
            self.driver.find_element_by_xpath(f'//li/span[contains(text(),"{type_name}")]').click()
            self.driver.find_element_by_xpath(self.ruleset_status_input).click()
            WebDriverWait(self.driver, config.IMPLICIT_WAIT).until(EC.element_to_be_clickable((
                By.XPATH,
                f'//li/span[contains(text(),"{stat}")]'))
            )
            self.driver.find_element_by_xpath(f'//li/span[contains(text(),"{stat}")]').click()
        except NoSuchElementException:
            logger.critical("未找到筛选框！")

        self.driver.find_element_by_xpath(self.query_button).click()
        time.sleep(2)
        self.assertTrue(len(self.driver.find_elements_by_xpath(_ruleset_xpath)) == 1, f'查询失败！当前规则{rule_set_code}'
                                                                                      f'查询结果不唯一')
        self.compare_random_ruleset_with_db(self.driver.find_elements_by_xpath(_ruleset_xpath)[0])

        # 进入详情页，再返回，应保留筛选栏状态
        self.driver.find_elements_by_xpath('//span[contains(text(), "规则列表")]')[1].click()
        WebDriverWait(self.driver, config.IMPLICIT_WAIT).until(EC.element_to_be_clickable(self.return_button))
        self.click_return()

        self.assertEqual(
            self.driver.find_element_by_xpath(self.ruleset_code_input).get_attribute('value'),
            rule_set_code
        )
        self.assertEqual(self.driver.find_element_by_xpath(self.ruleset_name_input).get_attribute('value'), name)
        self.driver.find_element_by_xpath(self.ruleset_type_input).click()
        self.assertTrue(self.driver.find_element_by_xpath(f'//li[contains(@class, "el-select-dropdown__item selected")]'
                                                          f'/span[contains(text(), "{type_name}")]'))
        self.driver.find_element_by_xpath(self.ruleset_status_input).click()
        self.assertTrue(self.driver.find_element_by_xpath(f'//li[contains(@class, "el-select-dropdown__item selected")]'
                                                          f'/span[contains(text(), "{stat}")]'))

        # 重置筛选栏，查看页码是否恢复为1
        self.reset_selector()
        self.assertTrue(self.driver.find_element_by_xpath(
            '//li[contains(@class, "number active") and contains(text(), "1")]'))

    # pylint:disable=too-many-locals
    @classmethod
    def create_ruleset(cls, name, ruleset_type, model, parallel=None, desc=None, cancel=False):
        # 单选框元素定位value属性
        mode_dict = {'路由': [1, '路由模式'], '风控': [2, '运行模式']}
        parallel_list = ['黑', '白', '白名单', '灰']
        save_button = '//button[contains(@class, "el-button el-button--primary")]/span[contains(text(), "保 存")]'

        try:
            WebDriverWait(cls.driver, config.IMPLICIT_WAIT).until(EC.element_to_be_clickable((
                By.XPATH,
                cls.create_button)
            ))
            cls.driver.find_element_by_xpath(cls.create_button).click()
            WebDriverWait(cls.driver, config.IMPLICIT_WAIT).until(EC.element_to_be_clickable((
                By.XPATH,
                f'//div[contains(@class, "el-dialog" )and contains(@aria-label, "添加规则集")]//input[contains(@class, '
                f'"el-radio__original") and contains(@value, "{mode_dict[ruleset_type][0]}")]/../span'))
            )
            cls.driver.find_element_by_xpath(
                f'//div[contains(@class, "el-dialog" )and contains(@aria-label, "添加规则集")]//input[contains(@class, '
                f'"el-radio__original") and contains(@value, "{mode_dict[ruleset_type][0]}")]/../span'
            ).click()

            WebDriverWait(cls.driver, config.IMPLICIT_WAIT).until(EC.visibility_of_element_located((
                By.XPATH,
                f'//label[contains(@class, "el-form-item__label") and contains'
                f'(text(), "{mode_dict[ruleset_type][1]}")]'))
            )

            cls.driver.find_element_by_xpath(
                f'//label[contains(text(), "规则集名称")]/../div//textarea'
            ).send_keys(name)

            if desc:
                cls.driver.find_element_by_xpath(
                    f'//label[contains(text(), "规则集描述")]/../div//textarea'
                ).send_keys(desc)

            cls.driver.find_element_by_xpath(
                f'//label[contains(@class, "el-form-item__label") and contains(text(), "{mode_dict[ruleset_type][1]}")]'
                f'/../div//input'
            ).click()

            WebDriverWait(cls.driver, config.IMPLICIT_WAIT).until(EC.element_to_be_clickable((
                By.XPATH,
                f'//li[contains(@class, "el-select-dropdown__item")]//span[contains(text(), "{model}")]'))
            )

            cls.driver.find_element_by_xpath(
                f'//li[contains(@class, "el-select-dropdown__item")]//span[contains(text(), "{model}")]'
            ).click()
        except NoSuchElementException:
            logger.critical('未找到添加规则集相关按钮')

        if model == '并行':
            WebDriverWait(cls.driver, config.IMPLICIT_WAIT).until(EC.element_to_be_clickable((
                By.XPATH,
                '//label[contains(@class, "el-form-item__label") and contains(text(), "结果优先级")]'))
            )

            disabled_input = '//div[contains(@class, "el-form-item is-required")]//div/div[contains(@class, ' \
                             '"el-input is-disabled el-input--suffix")]'
            assert len(cls.driver.find_elements_by_xpath(disabled_input)) == 3

            body_xpath = '//body[contains(@class, "el-popup-parent--hidden")]'

            para_idx = 5
            input_idx = 1
            for para in parallel:
                new_para_list = list()
                # 点击优先级下拉框
                cls.driver.find_element_by_xpath(f'//label[contains(text(), "结果优先级")]/../div[1]/div[{input_idx}]'
                                                 f'//input[contains(@class, "el-input__inner")]').click()
                input_idx += 1

                for idx in range(1, len(cls.driver.find_elements_by_xpath(f'{body_xpath}/div[{para_idx}]//li')) + 1):
                    new_para_list.append(cls.driver.find_element_by_xpath(
                        f'{body_xpath}/div[{para_idx}]//li[{idx}]/span').text)
                assert parallel_list == new_para_list
                # 选中优先级
                cls.driver.find_element_by_xpath(f'{body_xpath}/div[{para_idx}]//li/span[contains(text(), "{para}")]')\
                    .click()

                para_idx += 1
                parallel_list.remove(para)

        if cancel:
            cls.cancel_create()
            logger.info("取消新建规则集!")
            return
        cls.driver.find_element_by_xpath(save_button).click()
        logger.info("新建规则集:%s成功！", name)

    @classmethod
    def cancel_create(cls):
        try:
            cls.driver.find_element_by_xpath(cls.cancel_button).click()
        except NoSuchElementException:
            logger.critical('未找到取消按钮，当前页面无法完成取消操作')
        WebDriverWait(cls.driver, config.IMPLICIT_WAIT).until(EC.visibility_of_element_located((
            By.XPATH,
            '//p[contains(text(), "是否确认离开本页面，确认离开将不会保存所填信息")]'))
        )
        cls.driver.find_element_by_xpath(
            '//button[contains(@class, "el-button el-button--default el-button--small el-button--primary ")]'
            '/span[contains(text(), "确定")]'
        ).click()

    def check_create_result(self, name, scope, mode):
        _ruleset_xpath = '//div[contains(@class, "el-table__body-wrapper is-scrolling-left")]/table[contains(@class, ' \
                         '"el-table__body")]/tbody//tr'

        ret_name = self.get_ruleset_attribute(self.driver.find_element_by_xpath(f'{_ruleset_xpath}[1]'), 'name')
        self.assertEqual(name, ret_name, f'当前列表第一个规则集:{ret_name}不是新建规则集:{name}，新建规则集失败！')
        ret_scope = self.get_ruleset_attribute(self.driver.find_element_by_xpath(f'{_ruleset_xpath}[1]'), 'scope')
        self.assertEqual(scope, ret_scope, f'当前列表第一个规则集类型:{ret_scope}不是{scope}，新建规则集失败！')
        if scope == '风控':
            ret_mode = self.get_ruleset_attribute(self.driver.find_element_by_xpath(f'{_ruleset_xpath}[1]'),
                                                  'risk_control_mode')
        else:
            ret_mode = self.get_ruleset_attribute(self.driver.find_element_by_xpath(f'{_ruleset_xpath}[1]'),
                                                  'route_mode')
        self.assertEqual(mode, ret_mode, f'当前列表第一个规则集模式:{ret_mode}不是{mode}，新建规则集失败！')

    @staticmethod
    def get_random_name():
        formatted_today = datetime.today().strftime('%y%m%d')
        return formatted_today + str(random.randint(1, 100))

    def test_create_ruleset(self):
        _ruleset_xpath = '//div[contains(@class, "el-table__body-wrapper is-scrolling-left")]/table[contains(@class, ' \
                         '"el-table__body")]/tbody//tr'

        random_name = self.get_random_name()
        self.create_ruleset(random_name, '风控', '并行', ['黑', '白', '白名单', '灰'])
        time.sleep(2)
        self.check_create_result(random_name, '风控', '并行')
        self.compare_random_ruleset_with_db(self.driver.find_element_by_xpath(f'{_ruleset_xpath}[1]'))

        # 新建并取消，查看是否未保存
        random_name2 = self.get_random_name()
        self.create_ruleset(random_name2, '路由', '与路由', cancel=True)
        ret_name = self.get_ruleset_attribute(self.driver.find_element_by_xpath(f'{_ruleset_xpath}[1]'), 'name')
        self.assertNotEqual(ret_name, random_name2, '取消新建失败！')

        random_name3 = self.get_random_name()
        self.create_ruleset(random_name3, '路由', '与路由')
        time.sleep(2)
        self.check_create_result(random_name3, '路由', '与路由')
        self.compare_random_ruleset_with_db(self.driver.find_element_by_xpath(f'{_ruleset_xpath}[1]'))

        random_name4 = self.get_random_name()
        self.create_ruleset(random_name4, '路由', '或路由')
        time.sleep(2)
        self.check_create_result(random_name4, '路由', '或路由')
        self.compare_random_ruleset_with_db(self.driver.find_element_by_xpath(f'{_ruleset_xpath}[1]'))

        random_name5 = self.get_random_name()
        self.create_ruleset(random_name5, '风控', '串行')
        time.sleep(2)
        self.check_create_result(random_name5, '风控', '串行')
        self.compare_random_ruleset_with_db(self.driver.find_element_by_xpath(f'{_ruleset_xpath}[1]'))
