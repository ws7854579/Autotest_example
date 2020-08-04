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

from functional_tests import consts
from functional_tests.logger import logger
from functional_tests.web import config


class CleanEnvTest(TestCase):
    driver = getattr(webdriver, 'Chrome')()
    actions = ActionChains(driver)
    url = "http://manager.testfk.91renxin.com/arrange#/"

    @classmethod
    def setUpClass(cls) -> None:
        cls.driver.maximize_window()
        logger.info("准备测试...")
        cls.login()

    @classmethod
    def tearDownClass(cls) -> None:
        logger.info("测试结束！")
        cls.driver.quit()

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
                logger.critical("登录失败！")
        except TimeoutException:
            logger.critical("当前页面无法找到登录button！  %s", cls.driver.current_url)

    @staticmethod
    def get_element_attribute(element, attribute):
        value = element.text if attribute == 'text' else element.get_attribute(attribute)
        return value.strip() if isinstance(value, str) else value

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
                logger.critical("用户选择产品应用并点击确定之后弹窗不消失！")
        except Exception as e:
            print('ooooooppppps')

    def test_add_rules(self):
        self.driver.get(self.url+'rule')
