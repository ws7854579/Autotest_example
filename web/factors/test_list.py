#! /usr/bin/env python3
# -*- coding:utf-8 -*-

import random
import re
import time
from datetime import datetime

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from ... import consts
from ...core import case_tag, update_reset
from ...logger import logger
from ...sql_executor import sql_executor
from ...utils import utc2local
from .. import config
from .base_test import BaseTestCase
from .test_detail import DETAIL_URL_PATTERN


class TestList(BaseTestCase):

    url = f'{config.SERVER}#/factor'

    factor_columns = ('code', 'name', 'id_prefix', 'status', 'apps', 'ref_count', 'modify_user', 'modify_time')

    datetime_fmt = '%Y-%m-%d %H:%M:%S'

    factor_xpath = r'//td[contains(@class, "is-hidden")]//span[contains(text(), "查看")]/../../../../..'
    factors_count_xpath = r'//span[@class="el-pagination__total"]'

    page_size_select_xpath = f'{factors_count_xpath}/..//i[contains(@class, "el-select")]'
    page_size_item_xpath = r'//li[contains(@class, "el-select-dropdown__item selected")]/span[contains(text(), "条/页")]'

    # 筛选框定位
    factor_code_input = '//input[contains(@placeholder,"请输入因子编号")]'
    factor_name_input = '//input[contains(@placeholder,"请输入因子名称")]'
    factor_status_input = '//input[contains(@placeholder,"启用状态")]'
    factor_app_input = '//input[contains(@placeholder,"所属应用")]'

    query_button = '//span[contains(text(),"查询")]'
    reset_button = '//span[contains(text(),"重置")]'

    # 因子名称筛选参数
    factor_name_test = 'jc'

    def get_factor_attribute(self, factor_row, attr):
        if str(attr).lower() not in self.factor_columns:
            logger.error("因子列表页不展示属性%s！", attr)
            return None
        return self.get_element_attribute(
            factor_row.find_element_by_xpath(f'td[{self.factor_columns.index(attr) + 1}]'), 'text')

    def find_factor_rows(self, **kwargs):
        if set(kwargs.keys()).difference(self.factor_columns):
            logger.error("因子查询条件无效！    %s", kwargs)
            return None

        factor_rows = list()
        try:
            for row in self.driver.find_elements_by_xpath(self.factor_xpath):
                match = True
                for attr, val in kwargs.items():
                    if str(val) != self.get_factor_attribute(row, attr):
                        match = False
                        break
                if match:
                    factor_rows.append(row)
            return factor_rows if factor_rows else None
        except NoSuchElementException:
            logger.error("当前页面（%s）没有找到匹配的因子!    %s", self.driver.current_url, kwargs)
            return None

    def show_el_select_dropdown_items(self, select, target_xpath):
        try:
            select.click()
            WebDriverWait(self.driver, config.WAIT).until(EC.visibility_of_element_located((By.XPATH, target_xpath)))
        except TimeoutException as ex:
            self.assertIsNone(ex, f'显示下拉框选项失败！')

    def setUp(self) -> None:
        self.open_list_page()
        self.get_max_page()

    def compare_with_db(self, factor_row):
        factor_code = self.get_factor_attribute(factor_row, 'code')
        re_m = re.match(consts.FACTOR_CODE_PATTERN, factor_code)
        if self.assertIsNotNone(re_m, f'无效的因子编号: {factor_code}'):
            factor_id = re_m.group(1)
            factor = self.query_factors_from_db(*self.factor_fields, id=factor_id)[0]
            attrs = [
                f"{factor['id_prefix']}{factor['id']}",
                factor['name'],
                consts.FACTOR_TYPES[factor['id_prefix']],
                consts.FACTOR_STATUSES[factor['status']],
                self.query_apps_by_factor_id(factor_id),
                str(factor['ref_count']),
                factor['modify_user'],
                utc2local(factor['modify_time'], fmt=self.datetime_fmt)
            ]

            for idx, exp in enumerate(attrs, start=1):
                val = self.get_element_attribute(factor_row.find_element_by_xpath(f'td[{idx}]'), 'text')
                self.assertEqual(exp, val, f'因子({factor_code})属性不匹配！展示{val}，应为{exp}')
            logger.info("因子列表页信息(%s)校验成功！", factor_code)

    @case_tag(name='【因子列表页】因子展示信息')
    def test_check_factor_info(self):
        self.compare_with_db(random.choice(self.driver.find_elements_by_xpath(self.factor_xpath)))

    @case_tag(name='【因子列表页】翻页')
    def test_page(self):
        self.assertEqual(10, self.page_size, f'默认页面大小应为10，实际为{self.page_size}')
        self.assertEqual(self.page_size, len(self.driver.find_elements_by_xpath(self.factor_xpath)))
        for _ in range(self.max_page):
            self.page_down()
        for _ in range(self.max_page):
            self.page_up()

        self.set_page_size(30)
        self.assertEqual(self.page_size, len(self.driver.find_elements_by_xpath(self.factor_xpath)))
        for _ in range(self.max_page):
            self.page_down()
        for _ in range(self.max_page):
            self.page_up()

        self.set_page_size(3)
        self.page2number(random.randint(1, self.max_page))
        self.page2number(0)
        self.page2number(random.randint(self.max_page + 1, self.max_page * 10))
        self.page2number(random.randint(0, self.max_page * 10) / 10)

    def get_factor_mod_datetime(self, factor_row):
        return datetime.strptime(self.get_factor_attribute(factor_row, 'modify_time'), self.datetime_fmt)

    @case_tag(name='【因子列表页】因子排序')
    def test_order(self):
        cur_factors = self.driver.find_elements_by_xpath(self.factor_xpath)
        if len(cur_factors) < 2:
            logger.warning("当前因子数目小于2，无法测试排序！")
            return

        i, j = random.choices(range(len(cur_factors)), k=2)
        while i == j:
            j = random.randrange(len(cur_factors))

        mod_dts = [self.get_factor_mod_datetime(cur_factors[idx]) for idx in sorted({i, j, len(cur_factors) - 1})]
        for i in range(len(mod_dts) - 1):
            self.assertTrue(mod_dts[i] >= mod_dts[i + 1], '列表页因子未按更新时间逆序排序！')

        if self.get_current_page_num() < self.max_page:
            self.page2number(random.randint(2, self.max_page))
            mod_dt = self.get_factor_mod_datetime(random.choice(self.driver.find_elements_by_xpath(self.factor_xpath)))
            self.assertTrue(mod_dts[-1] >= mod_dt, f'当前页面因子更新时间{mod_dt}晚于首页最末因子更新时间{mod_dts[-1]}！')
        logger.info("列表页因子按更新时间逆序排序校验通过！")

    def mod_factor_status(self, factor_code, factor_stat, factor_ref_cnt, cancel_action=False):
        btn_xpath = (f'//td[contains(@class, "is-hidden")]//span[contains(text(), "{factor_code}")]/../../..'
                     f'/td[{len(self.factor_columns) + 1}]//button'
                     f'/span[contains(text(), "{consts.BTN_ENABLE}") or contains(text(), "{consts.BTN_DISABLE}")]/..')
        try:
            mod_btn = self.driver.find_element_by_xpath(btn_xpath)
            mod_btn_desc = self.get_element_attribute(mod_btn, 'text')
            action = consts.BTN_DISABLE if factor_stat == consts.STAT_ENABLE else consts.BTN_ENABLE
            self.assertEqual(action, mod_btn_desc,
                             f'{factor_stat}因子{factor_code}的button为{mod_btn_desc}，应为{action}!')

            msg_box_xpath = '//div[contains(@class, "el-message-box")]//div[contains(@class, "el-message-box__btns")]'
            confirm = consts.CANCEL if cancel_action else consts.CONFIRM
            self.do_mod_ele_status(mod_btn, msg_box_xpath, confirm, factor_code, factor_stat, factor_ref_cnt)
        except NoSuchElementException as ex:
            self.assertIsNone(ex, f'未找到因子{factor_code}的启用/停用button！')

    def check_factor_attributes(self, factor_code, **kwargs):
        self.assertSetEqual(set(), set(kwargs.keys()).difference(self.factor_columns), f'要检查的因子属性错误！  {kwargs}')
        factor_row = self.find_factor_rows(code=factor_code)
        self.assertIsNotNone(factor_row, f'当前页面无法找到因子{factor_code}！')

        factor_row = factor_row[0]
        for attr, exp in kwargs.items():
            val = self.get_factor_attribute(factor_row, attr)
            self.assertEqual(str(exp), val, f'因子{factor_code}属性{attr}应为{exp}，实际显示为{val}')
        logger.info("因子%s属性检查成功！    %s", factor_code, kwargs)

    def check_modification(self, factor_row, cancel_action=False):
        attrs = ('code', 'status', 'ref_count', 'modify_user', 'modify_time')
        code, stat, ref_cnt, mod_user, mod_dt = [self.get_factor_attribute(factor_row, col) for col in attrs]

        self.mod_factor_status(code, stat, ref_cnt, cancel_action)
        if not cancel_action and self.if_ele_status_modifiable(stat, ref_cnt):
            stat = consts.STAT_DISABLE if stat == consts.STAT_ENABLE else consts.STAT_ENABLE
            mod_user = self.user
            new_mod_dt = self.get_factor_mod_datetime(factor_row)
            self.assertTrue(new_mod_dt > datetime.strptime(mod_dt, self.datetime_fmt),
                            f'更改因子{code}状态后更新时间校验失败！  更新前时间：{mod_dt}  更新后时间：{new_mod_dt}')
            mod_dt = new_mod_dt.strftime(self.datetime_fmt)
        self.check_factor_attributes(code, status=stat, ref_count=ref_cnt, modify_user=mod_user, modify_time=mod_dt)

        self.open_list_page()
        if not cancel_action and self.if_ele_status_modifiable(stat, ref_cnt):
            first_factor = self.get_factor_attribute(self.driver.find_elements_by_xpath(self.factor_xpath)[0], 'code')
            self.assertEqual(code, first_factor, f'修改状态并刷新页面后，因子{code}应在首页首行显示！')

    @case_tag(name='【因子列表页】修改因子启用状态')
    @update_reset(table='factor')
    def test_mod_factor_status(self):
        self.page2number(self.max_page)
        factor_row = self.driver.find_elements_by_xpath(self.factor_xpath)[-1]
        attrs = ('code', 'status', 'ref_count')
        factor_code, factor_stat, factor_ref_cnt = [self.get_factor_attribute(factor_row, col) for col in attrs]
        fid = int(re.match(consts.FACTOR_CODE_PATTERN, factor_code).group(1))

        if not self.if_ele_status_modifiable(factor_stat, factor_ref_cnt):
            sql_executor.execute(
                f'UPDATE factor SET status = {consts.STAT_UNKNOWN_CODE}, ref_count = 0 WHERE id = {fid}')
            sql_executor.execute(
                f'UPDATE factor_application_relation SET factor_status = {consts.STAT_UNKNOWN_CODE} '
                f'WHERE factor_id = {fid}')
            self.open_list_page()
            self.page2number(self.max_page)
            self.check_factor_attributes(factor_code, status=consts.STAT_UNKNOWN, ref_count=0)

        # 取消更改因子状态
        self.check_modification(self.find_factor_rows(code=factor_code)[0], cancel_action=True)
        self.page2number(self.max_page)
        last_factor = self.get_factor_attribute(self.driver.find_elements_by_xpath(self.factor_xpath)[-1], 'code')
        self.assertEqual(factor_code, last_factor, f'取消修改状态，因子{factor_code}显示位置应保持不变（末页末行）！')
        # 执行更改因子状态
        self.check_modification(self.find_factor_rows(code=factor_code)[0])
        # 更换用户后执行更改因子状态
        self.logout()
        self.login(config.OTHER_USER, config.OTHER_PWD)
        self.open_list_page()
        self.check_modification(self.find_factor_rows(code=factor_code)[0])
        # 重新登录测试用户
        self.logout()
        self.login()
        # 禁止更改因子状态
        ref_cnt = random.randint(1, 100)
        logger.info("启用因子%s并设置其引用次数为%d", factor_code, ref_cnt)
        sql_executor.execute(
            f'UPDATE factor SET status = {consts.STAT_ENABLE_CODE}, ref_count = {ref_cnt} WHERE id = {fid}')
        sql_executor.execute(
            f'UPDATE factor_application_relation SET factor_status = {consts.STAT_ENABLE_CODE} WHERE factor_id = {fid}')
        self.open_list_page()
        self.check_factor_attributes(factor_code, status=consts.STAT_ENABLE, ref_count=ref_cnt)
        self.check_modification(self.find_factor_rows(code=factor_code)[0])

    def view_factor_detail(self, factor_row):
        code = self.get_factor_attribute(factor_row, 'code')
        logger.info("查看因子%s详情...", code)
        re_m = re.match(consts.FACTOR_CODE_PATTERN, code)
        if self.assertIsNotNone(re_m, f'无法打开详情页，因子编号{code}无效！'):
            try:
                self.driver.find_elements_by_xpath(f'//a[@href="#/factor/{re_m.group(1)}"]/button')[-1].click()
                try:
                    WebDriverWait(self.driver, config.IMPLICIT_WAIT).until(EC.url_matches(DETAIL_URL_PATTERN))
                    if self.assertIn(re.match(DETAIL_URL_PATTERN, self.driver.current_url).group(1), code):
                        logger.info("查看因子%s详情页成功！", code)
                    else:
                        logger.error("查看因子%s详情页失败！", code)
                except TimeoutException:
                    logger.error("查看因子%s详情页失败！", code)
                finally:
                    self.driver.find_element_by_xpath(r'//span[contains(text(), "返回")]/..').click()
            except NoSuchElementException as ex:
                self.assertIsNone(ex, f'无法找到因子{code}的查看button！')

    @case_tag(name='【因子列表页】查看因子详情')
    def test_view_detail(self):
        factor_row = random.choice(self.driver.find_elements_by_xpath(self.factor_xpath))
        self.view_factor_detail(factor_row)

    def reset_selector(self):
        try:
            self.driver.find_element_by_xpath(self.reset_button).click()
            self.driver.find_element_by_xpath(self.query_button).click()
        except NoSuchElementException:
            logger.critical("未发现重置按钮！")

    @case_tag(name='【因子列表页】查看筛选功能')
    def test_single_selector(self):
        factor_id = self.random_factor_id()
        factor = self.query_factors_from_db(id=factor_id)[0]
        factor_code = factor['id_prefix'] + str(factor_id)

        # 因子编号筛选框
        try:
            self.assertTrue(len(self.driver.find_elements_by_xpath(self.factor_xpath)) > 0, "应用下无因子，停止本次测试。")
            self.driver.find_element_by_xpath(self.factor_code_input).send_keys(factor_code)
            self.driver.find_element_by_xpath(self.query_button).click()
            time.sleep(2)
            self.assertEqual(len(self.driver.find_elements_by_xpath(self.factor_xpath)), 1, "因子编号筛选功能测试未通过！"
                                                                                            "筛选出多个结果")
            self.compare_with_db(self.driver.find_elements_by_xpath(self.factor_xpath)[0])

            # 重置筛选
            self.reset_selector()
        except NoSuchElementException:
            logger.critical("当前页面无法找到因子编号筛选框！")

        # 因子名称筛选栏
        try:
            exp_num = sql_executor.execute(
                f"""SELECT count(*) FROM factor WHERE NAME LIKE '%{self.factor_name_test}%'"""
            )[0][0]
            self.driver.find_element_by_xpath(self.factor_name_input).send_keys(self.factor_name_test)
            self.driver.find_element_by_xpath(self.query_button).click()
            time.sleep(2)
            rel_num = self.driver.find_element_by_xpath(self.factors_count_xpath).text.split()[1]
            self.assertEqual(int(exp_num), int(rel_num), '因子名称筛选功能测试未通过！筛选结果与数据库结果不一致！')

            self.reset_selector()
        except NoSuchElementException:
            logger.critical("当前页面无法找到因子名称筛选框！")

        # 因子状态筛选栏
        for code, stat in consts.FACTOR_STATUSES.items():
            self.driver.find_element_by_xpath(self.factor_status_input).click()
            WebDriverWait(self.driver, config.IMPLICIT_WAIT).until(EC.element_to_be_clickable((
                By.XPATH,
                f'//li/span[contains(text(),"{stat}")]'))
            )
            self.driver.find_element_by_xpath(f'//li/span[contains(text(),"{stat}")]').click()
            self.driver.find_element_by_xpath(self.query_button).click()
            exp_num = sql_executor.execute(
                f"""SELECT count(*) FROM factor WHERE status = {code}"""
            )[0][0]
            rel_num = self.driver.find_element_by_xpath(self.factors_count_xpath).text.split()[1]
            self.assertEqual(int(exp_num), int(rel_num), '因子状态筛选功能测试未通过！筛选结果与数据库结果不一致！')
            self.reset_selector()

        # 因子应用筛选栏
        sql_raw = f"""SELECT id,name FROM product_application"""
        sql_ret = sql_executor.execute(sql_raw)

        for app in sql_ret:
            application_num = {app[0]: app[1]}

        try:
            self.driver.find_element_by_xpath(self.factor_app_input).click()
            for aid, aname in application_num.items():
                WebDriverWait(self.driver, config.IMPLICIT_WAIT).until(EC.element_to_be_clickable((
                    By.XPATH,
                    f'//li/span[contains(text(),"{aname}")]'))
                )
                self.driver.find_element_by_xpath(f'//li/span[contains(text(),"{aname}")]').click()
                self.driver.find_element_by_xpath(self.query_button).click()
                query_sql = f"""SELECT count(*) FROM factor_application_relation WHERE application_id = {aid}"""
                exp_num = sql_executor.execute(query_sql)[0][0]
                rel_num = self.driver.find_element_by_xpath(self.factors_count_xpath).text.split()[1]
                self.assertEqual(int(exp_num), int(rel_num), "因子应用筛选功能测试未通过！筛选结果与数据库结果不一致！")
                self.reset_selector()
        except NoSuchElementException:
            logger.critical("当前页面无法找到因子应用筛选框")

    def test_multiple_selector(self):
        # 获取随机因子
        factor_info = random.choice(self.query_factors_from_db('id', 'id_prefix', 'name', 'status'))
        fid, f_prefix, name, status = factor_info
        factor_code = f_prefix + str(fid)
        stat = consts.FACTOR_STATUSES[status]
        app_name = self.query_apps_by_factor_id(fid)
        if '、' in app_name:
            app_name = app_name.split('、')[0]

        # 使用四个组合筛选栏
        try:
            self.driver.find_element_by_xpath(self.factor_code_input).send_keys(factor_code)
            self.driver.find_element_by_xpath(self.factor_name_input).send_keys(name)
            self.driver.find_element_by_xpath(self.factor_status_input).click()
            WebDriverWait(self.driver, config.IMPLICIT_WAIT).until(EC.element_to_be_clickable((
                By.XPATH,
                f'//li/span[contains(text(),"{stat}")]'))
            )
            self.driver.find_element_by_xpath(f'//li/span[contains(text(),"{stat}")]').click()
            self.driver.find_element_by_xpath(self.factor_app_input).click()
            WebDriverWait(self.driver, config.IMPLICIT_WAIT).until(EC.element_to_be_clickable((
                By.XPATH,
                f'//li/span[contains(text(),"{app_name}")]'))
            )
            self.driver.find_element_by_xpath(f'//li/span[contains(text(),"{app_name}")]').click()
        except NoSuchElementException:
            logger.critical("未找到筛选框！")

        self.driver.find_element_by_xpath(self.query_button).click()
        time.sleep(2)
        self.assertTrue(len(self.driver.find_elements_by_xpath(self.factor_xpath)) == 1, f'查询失败！当前因子{factor_code}'
                                                                                         f'查询结果不唯一')
        self.compare_with_db(self.driver.find_elements_by_xpath(self.factor_xpath)[0])

        # 进入详情页，再返回，应保留筛选栏状态
        self.driver.find_elements_by_xpath('//span[contains(text(), "查看")]')[1].click()
        WebDriverWait(self.driver, config.IMPLICIT_WAIT).until(EC.element_to_be_clickable(self.return_button))
        self.click_return()

        self.assertEqual(self.driver.find_element_by_xpath(self.factor_code_input).get_attribute('value'), factor_code)
        self.assertEqual(self.driver.find_element_by_xpath(self.factor_name_input).get_attribute('value'), name)
        self.driver.find_element_by_xpath(self.factor_status_input).click()
        self.assertTrue(self.driver.find_element_by_xpath(f'//li[contains(@class, "el-select-dropdown__item selected")]'
                                                          f'/span[contains(text(), "{stat}")]'))
        self.driver.find_element_by_xpath(self.factor_app_input).click()
        self.assertTrue(self.driver.find_element_by_xpath(f'//li[contains(@class, "el-select-dropdown__item selected")]'
                                                          f'/span[contains(text(), "{app_name}")]'))

        # 重置筛选栏，查看页码是否恢复为1
        self.reset_selector()
        self.assertTrue(
            self.driver.find_element_by_xpath('//li[contains(@class, "number active") and contains(text(), "1")]')
        )
