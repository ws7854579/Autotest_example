from selenium.webdriver.common.keys import Keys

from .base_test import BaseTestCase
from .test_factor2app import TestFactor2App


class TestDebug(BaseTestCase):

    def test_debug(self):
        helper = TestFactor2App()
        self.driver.get(f'{helper.url}/?all=')
        factor2app = {
            'Application': 'TestProdA',
            'Factor': 'N/A',
            'Factor code': 'JCYZ278',
            'Factor name': 'N/A',
            'Factor type': '基础因子',
            'Factor status': '未启用',
            'Factor modify time': '2019年8月28日 10:32',
            'Service name': '',
            'Db table name': 'ysd_user_info_v20181210_cld'
        }
        self.assertTrue(helper.check_exist(helper.get_current_values(), **factor2app))
        # name_input = self.driver.find_element_by_id('id_name')
        # self.actions.click(name_input).key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL)
        # self.actions.send_keys(Keys.BACKSPACE).send_keys('TestFactor').perform()
        # name_input.send_keys(Keys.CONTROL + 'a')
        # name_input.send_keys('TestFactor')

        # self.actions.click(name_input).send_keys(Keys.CONTROL + 'a').perform()
        # self.actions.click(name_input).send_keys(Keys.BACKSPACE).perform()
        # self.actions.click(name_input).send_keys('TetsFactor').perform()
        # name_input.send_keys(Keys.CONTROL, 'a')
        # name_input.send_keys('TestFactor')
        print('debug finished!')
