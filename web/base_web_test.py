#! /usr/bin/env python3
# -*- coding:utf-8 -*-

import math
import os
import random
import re
import time
from unittest import TestCase
from unittest.util import safe_repr

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from .. import consts
from ..logger import logger
#from ..sql_executor import sql_executor
from . import config

HANDLED_EX_MSG = '查看截屏'


def get_screen_shot(cls):
    shot_name = f"shot_{time.strftime('%Y%m%d-%H%M%S')}.png"
    shot_path = os.path.join(config.SHOTS_DIR, shot_name)
    if os.path.exists(shot_path):
        time.sleep(1)
    cls.driver.get_screenshot_as_file(shot_path)
    return shot_name


def get_screen_shot_wrapper(assert_func):

    def wrapper(self, *args, **kwargs):
        try:
            assert_func(self, *args, **kwargs)
            return True
        except AssertionError as ex:
            if HANDLED_EX_MSG in str(ex):
                raise ex  # raise for unittest to judge result of test case

            shot_name = get_screen_shot(self)
            _ex = AssertionError(f'{HANDLED_EX_MSG} {shot_name}')
            logger.error(str(_ex), exc_info=ex)
            raise _ex

    return wrapper


assert_pattern = re.compile('^assert(?!(_|Raises|Warns))')
assert_methods = list(filter(lambda m: callable(getattr(TestCase, m)) and assert_pattern.match(m), dir(TestCase)))


class Meta(type):
    def __new__(mcs, name, bases, attrs):  # pylint:disable=bad-mcs-classmethod-argument
        """
        元类，批量修改需要装饰的方法

        :param name: 类名
        :param bases: 基类
        :param attrs: 类属性
        :return: 被修改后的类
        """
        new_class = super().__new__(mcs, name, bases, attrs)

        for method in assert_methods:
            setattr(new_class, method, get_screen_shot_wrapper(getattr(new_class, method)))

        return new_class


class BaseWebTestCase(TestCase, metaclass=Meta):
    # pylint:disable=too-many-public-methods

    driver = getattr(webdriver, 'Chrome')()
    actions = ActionChains(driver)

    wait_el_xpath = r'//td[contains(@class, "is-hidden")]//span[contains(text(), "查看")]/../../../../..'
    count_xpath = r'//span[@class="el-pagination__total"]'

    page_size_select_xpath = f'{count_xpath}/..//i[contains(@class, "el-select")]'
    page_size_item_xpath = r'//li[contains(@class, "el-select-dropdown__item selected")]/span[contains(text(), "条/页")]'

    cur_ele_count = r'//div[@class="pagination el-pagination"]/span[@class="el-pagination__total"]'

    url = config.SERVER
    case_name = ''

    user = None
    prod_app = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.driver.maximize_window()
        logger.info("准备测试...")

    @classmethod
    def tearDownClass(cls) -> None:
        logger.info("测试结束！")
        cls.driver.quit()

    @staticmethod
    def get_element_attribute(element, attribute):
        value = element.text if attribute == 'text' else element.get_attribute(attribute)
        return value.strip() if isinstance(value, str) else value

    def open_list_page(self):
        if self.driver.current_url == self.url:
            self.driver.refresh()
        else:
            self.driver.get(self.url)
        try:
            WebDriverWait(self.driver, config.IMPLICIT_WAIT).until(
                EC.presence_of_all_elements_located((By.XPATH, self.wait_el_xpath)))
            WebDriverWait(self.driver, config.IMPLICIT_WAIT).until(
                EC.element_to_be_clickable((By.XPATH, self.page_size_select_xpath)))
        except TimeoutException as ex:
            self.assertIsNone(ex, f'打开{self.case_name}列表页失败！    {self.driver.current_url}')

    def count_shown(self):
        try:
            text = self.get_element_attribute(self.driver.find_element_by_xpath(self.count_xpath), 'text')
            re_m = re.match(r'共\s*(\d+)\s*条', text)
            if self.assertIsNotNone(re_m, f'无法解析{self.case_name}计数信息： {text}'):
                return int(re_m.group(1))
            return None
        except NoSuchElementException as ex:
            self.assertIsNone(ex, f'无法在当前页面找到{self.case_name}计数信息！    {self.driver.current_url}')

    def show_el_select_dropdown_items(self, select, target_xpath):
        try:
            select.click()
            WebDriverWait(self.driver, config.WAIT).until(EC.visibility_of_element_located((By.XPATH, target_xpath)))
        except TimeoutException as ex:
            self.assertIsNone(ex, f'显示下拉框选项失败！')

    def get_page_size(self):
        try:
            select = self.driver.find_element_by_xpath(self.page_size_select_xpath)
            self.show_el_select_dropdown_items(select, self.page_size_item_xpath)
            try:
                item = self.driver.find_element_by_xpath(self.page_size_item_xpath)
                text = self.get_element_attribute(item, 'text')
                re_m = re.match(r'(\d+)\s*条/页', text)
                if self.assertIsNotNone(re_m, f'无法解析页面大小信息： {text}'):
                    self.page_size = int(re_m.group(1))  #pylint:disable=attribute-defined-outside-init
            except NoSuchElementException as ex:
                self.assertIsNone(ex, f'无法在当前页面找到页面大小信息！    {self.driver.current_url}')
            finally:
                select.click()
        except NoSuchElementException as ex:
            self.assertIsNone(ex, f'无法在当前页面找到页面大小控件！    {self.driver.current_url}')

    def get_max_page(self):
        try:
            pager = self.driver.find_elements_by_xpath(r'//ul[@class="el-pager"]/li')[-1]
            max_page = int(self.get_element_attribute(pager, 'text'))
            el_count = self.count_shown()
            self.get_page_size()
            if self.assertEqual(max_page, math.ceil(el_count / self.page_size),
                                f'总条数: {el_count}  页面大小: {self.page_size}  页数: {max_page}'):
                self.max_page = max_page  #pylint:disable=attribute-defined-outside-init
        except NoSuchElementException as ex:
            self.assertIsNone(ex, f'无法在当前页面找到页码控件！    {self.driver.current_url}')

    @classmethod
    def login(cls, user=config.USER, pwd=config.PWD, prod_app=None):
        logger.info("登录用户%s...", user)
        cls.driver.get(config.SERVER)
        login_btn = (By.XPATH, r'//button/span[contains(text(), "登录")]/..')
        try:
            WebDriverWait(cls.driver, config.IMPLICIT_WAIT).until(EC.url_contains(f'{config.SERVER}#/login?'))
            WebDriverWait(cls.driver, config.IMPLICIT_WAIT).until(EC.element_to_be_clickable(login_btn))
            cls.driver.find_element_by_name('username').send_keys(user)
            cls.driver.find_element_by_name('password').send_keys(pwd)
            cls.driver.find_element(*login_btn).click()
            login_tip = (By.XPATH, r'//*[contains(text(), "登录成功")]')
            try:
                WebDriverWait(cls.driver, config.IMPLICIT_WAIT).until(EC.presence_of_element_located(login_tip))
                cls.user = user
                logger.info("用户%s登录成功！", user)
                cls.choose_product_application(prod_app)
            except TimeoutException:
                get_screen_shot(cls)
                logger.critical("登录失败！")
        except TimeoutException:
            get_screen_shot(cls)
            logger.critical("当前页面无法找到登录button！  %s", cls.driver.current_url)

    @classmethod
    def choose_product_application(cls, prod_app=None):
        app_chooser_xpath = f'//div[@class="el-dialog"]//button/span[contains(text(), {consts.CONFIRM})]/..'
        try:
            WebDriverWait(cls.driver, config.WAIT).until(EC.element_to_be_clickable((By.XPATH, app_chooser_xpath)))
            cls.driver.find_element_by_xpath(r'//div[@class="el-dialog"]//div[@class="el-select"]').click()
            if prod_app:
                app = cls.driver.find_element_by_xpath(
                    f'//ul[@class="el-scrollbar__view el-select-dropdown__list"]/li/span[text()="{prod_app}"]/..')
            else:
                app = random.choice(
                    cls.driver.find_elements_by_xpath(r'//ul[@class="el-scrollbar__view el-select-dropdown__list"]/li'))
                prod_app = cls.get_element_attribute(app, 'text')

            app.click()
            # TODO: 检查选择产品应用之后，选择框显示与选择一致
            cls.driver.find_element_by_xpath(app_chooser_xpath).click()
            try:
                WebDriverWait(cls.driver, config.WAIT).until_not(
                    EC.element_to_be_clickable((By.XPATH, app_chooser_xpath)))
                cls.prod_app = prod_app
                logger.info("用户选择的应用为: %s", prod_app)
            except TimeoutException:
                get_screen_shot(cls)
                logger.critical("用户选择产品应用并点击确定之后弹窗不消失！")
        except TimeoutException:
            sql = f"""
                SELECT name
                FROM product_application pa
                         JOIN user_info_application uia ON pa.id = uia.productapplication_id
                WHERE userinfo_id IN (SELECT user_info.id
                                      FROM user_info
                                               JOIN default_web.auth_user ON user_id = default_web.auth_user.id
                                      WHERE username = '{cls.user}')"""
            apps = sql_executor.execute(sql)
            if apps:
                if len(apps[0]) > 1:
                    get_screen_shot(cls)
                    logger.critical("用户%s关联了%d个产品应用，但登录后未弹出选择窗口！", cls.user, apps)
                elif len(apps[0]) == 1:
                    logger.info("用户%s仅关联了1个产品应用，登录后不弹出选择窗口验证成功！", cls.user)
                    cls.prod_app = apps[0][0]
            else:
                logger.info("用户%s尚未关联产品应用，登录后不弹出选择窗口验证成功！", cls.user)

        cls.check_current_product_application()

    @classmethod
    def get_prod_app(cls):
        WebDriverWait(cls.driver, config.IMPLICIT_WAIT).until(
            EC.presence_of_element_located(r"//div[contains(@class, 'wrapper')]/ul[contains(@role, 'menubar')]"))
        prod_app = cls.get_element_attribute(
            cls.driver.find_element_by_xpath(r"//div[contains(@class, 'wrapper')]/ul[contains(@role, 'menubar')]"),
            'text'
        ).split()[0]
        return prod_app

    @classmethod
    def check_current_product_application(cls):
        if not cls.prod_app:
            # 再次获取登录应用，之前有登录时无法获取控件的情况
            if cls.get_prod_app is True:
                cls.prod_app = cls.get_prod_app()
            else:
                logger.critical("用户%s尚未选择产品，无法校验并进行后续测试！", cls.user)
        try:
            cls.driver.find_element_by_xpath(f'//header//ul[contains(text(), "{cls.prod_app}")]')
            return True
        except NoSuchElementException:
            get_screen_shot(cls)
            logger.critical("用户选择了产品应用%s，但页面中未找到！", cls.prod_app)

    @classmethod
    def logout(cls):
        user_btns = cls.driver.find_elements_by_xpath(r'//ul[@class="float-right el-menu--horizontal el-menu"]//button')
        cur_user = cls.get_element_attribute(user_btns[0], 'text')
        logger.info('登出用户%s...', cur_user)
        user_btns[-1].click()
        logout_btn = (By.XPATH, r'//li[contains(text(), "登出")]/..')
        try:
            WebDriverWait(cls.driver, config.IMPLICIT_WAIT).until(EC.presence_of_element_located(logout_btn))
            cls.driver.find_element(*logout_btn).click()
            cls.user = None
            logger.info("用户%s登出成功！", cur_user)
        except TimeoutException:
            get_screen_shot(cls)
            logger.critical("当前页面无法找到登出button！  %s", cls.driver.current_url)

    def set_page_size(self, size):
        try:
            select = self.driver.find_element_by_xpath(self.page_size_select_xpath)
            self.show_el_select_dropdown_items(select, self.page_size_item_xpath)
            try:
                target = f'//li[contains(@class, "el-select-dropdown__item")]/span[contains(text(), "{size}条/页")]'
                self.driver.find_element_by_xpath(target).click()
                self.get_max_page()
                self.assertEqual(size, self.page_size, f'设置页面大小（n={size}）失败！')
                logger.info("设置页面大小（n=%s）成功！", size)
            except NoSuchElementException as e:
                self.assertIsNone(e, f'设置页面大小（n={size}）失败！')
                select.click()
        except NoSuchElementException as ex:
            self.assertIsNone(ex, f'无法在当前页面找到页面大小控件！    {self.driver.current_url}')

    def get_current_page_num(self):
        try:
            pager = self.driver.find_element_by_xpath(r'//ul[@class="el-pager"]/li[contains(@class, "active")]')
            return int(self.get_element_attribute(pager, 'text'))
        except NoSuchElementException as ex:
            self.assertIsNone(ex, f'无法在当前页面找到页码控件！    {self.driver.current_url}')

    def page_up(self):
        try:
            cur_page = self.get_current_page_num()
            btn = self.driver.find_element_by_xpath(r'//button[@class="btn-prev"]')
            if self.get_element_attribute(btn, 'disabled'):
                self.assertEqual(1, cur_page, '不在首页，但上一页控件不可用！')
                logger.warning("当前在首页，无法向上翻页！")
            else:
                btn.click()
                time.sleep(config.WAIT)
                self.assertEqual(1, cur_page - self.get_current_page_num(), '向上翻页失败！')
                logger.info("向上翻页成功！当前为第%s页", cur_page - 1)
        except NoSuchElementException as ex:
            self.assertIsNone(ex, f'无法在当前页面找到上一页控件！    {self.driver.current_url}')

    def page_down(self):
        try:
            cur_page = self.get_current_page_num()
            btn = self.driver.find_element_by_xpath(r'//button[@class="btn-next"]')
            if self.get_element_attribute(btn, 'disabled'):
                self.assertEqual(self.max_page, cur_page, '不在首页，但下一页控件不可用！')
                logger.warning("当前在末页，无法向下翻页！")
            else:
                btn.click()
                time.sleep(config.WAIT)
                self.assertEqual(1, self.get_current_page_num() - cur_page, '向下翻页失败！')
                logger.info("向下翻页成功！当前为第%s页", cur_page + 1)
        except NoSuchElementException as ex:
            self.assertIsNone(ex, f'无法在当前页面找到下一页控件！    {self.driver.current_url}')

    def page2number(self, number):
        try:
            page_input = self.driver.find_element_by_xpath(
                r'//span[@class="el-pagination__jump"]//input[@class="el-input__inner"]')
            page_input.send_keys(Keys.CONTROL + 'A', Keys.BACKSPACE)
            page_input.send_keys(str(number), Keys.ENTER)
            time.sleep(config.WAIT)

            page_no = int(number)
            if page_no < 1:
                page_no = 1
            elif page_no > self.max_page:
                page_no = self.max_page

            self.assertEqual(page_no, self.get_current_page_num(), f'跳转至第{number}页失败！')
            logger.info("跳转至第%s页成功！", number)
        except NoSuchElementException as ex:
            self.assertIsNone(ex, f'无法在当前页面找到页面跳转控件！    {self.driver.current_url}')

    def act_message_box(self, msg_box_xpath, confirm):
        try:
            self.driver.find_element_by_xpath(f'{msg_box_xpath}//button/span[contains(text(), "{confirm}")]/..').click()
            WebDriverWait(self.driver, config.WAIT).until_not(
                EC.visibility_of_element_located((By.XPATH, msg_box_xpath)))
        except NoSuchElementException as ex:
            self.assertIsNone(ex, f'未在确认弹窗中找到{confirm}按钮！')
        except TimeoutException as ex:
            self.assertIsNone(ex, f'点击{confirm}后确认弹窗未消失！')

    def check_forbidden_mod_status(self, ele_code):
        msg_box_xpath = (f'//div[contains(@class, "el-message-box")]'
                         f'//p[contains(text(), "该{self.case_name}正在使用, 无法停用")]/../../..')
        try:
            self.driver.find_element_by_xpath(msg_box_xpath)
            self.act_message_box(msg_box_xpath, consts.CONFIRM)
            logger.info("%s%s已启用且引用次数大于零，禁止停用验证成功！", self.case_name, ele_code)
        except NoSuchElementException as ex:
            self.assertIsNone(ex, f'{self.case_name}{ele_code}已启用且引用次数大于零，点击停用后未弹出提示窗口！')

    def do_mod_ele_status(self, mod_btn, msg_box_xpath, confirm, ele_code, ele_stat, ele_ref_cnt):
        logger.info("%s%s%s...", self.get_element_attribute(mod_btn, 'text'), self.case_name, ele_code)
        try:
            mod_btn.click()
            WebDriverWait(self.driver, config.WAIT).until(EC.visibility_of_element_located((By.XPATH, msg_box_xpath)))
            logger.info("%s修改%s%s状态", confirm, self.case_name, ele_code)
            self.act_message_box(msg_box_xpath, confirm)
        except TimeoutException:
            if self.assertFalse(self.if_ele_status_modifiable(ele_stat, ele_ref_cnt),
                                f'点击{self.case_name}{ele_code}状态修改button后未弹出确认弹窗！'):
                self.check_forbidden_mod_status(ele_code)

    @staticmethod
    def if_ele_status_modifiable(ele_stat, ele_ref_cnt):
        return ele_stat != consts.STAT_ENABLE or str(ele_ref_cnt) == '0'

    def _formatMessage(self, msg, standardMsg):
        if not self.longMessage:
            return msg or standardMsg
        if msg is None:
            return standardMsg

        try:
            return f'{standardMsg}\r\n{msg}'
        except UnicodeDecodeError:
            return f'{safe_repr(standardMsg)}\r\n{safe_repr(msg)}'
