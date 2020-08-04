#! /usr/bin/env python3
# -*- coding:utf-8 -*-

import random
from copy import deepcopy

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.select import Select

from . import config
from ...logger import logger
from ..base_web_test import BaseWebTestCase


class BaseTestCase(BaseWebTestCase):

    uri = ''
    FIELDS = tuple()
    IMPLICIT_FIELDS = tuple()
    TABLE_HEADER = list()

    @property
    def url(self):
        return f'{config.API_ARRANGE}/{self.uri}'

    @property
    def mod_name(self):
        return config.URIS.get(self.uri, self.uri)

    @classmethod
    def login(cls, user=config.USER, pwd=config.PWD):
        logger.info("登录用户%s...", user)
        cls.driver.get(f'{config.API_ARRANGE}/{cls.uri}')
        cls.driver.implicitly_wait(config.IMPLICIT_WAIT)
        cls.driver.find_element_by_name('username').send_keys(user)
        cls.driver.find_element_by_name('password').send_keys(pwd)
        cls.driver.find_element_by_xpath(r'//input[@value="登录"]').click()
        cls.driver.implicitly_wait(config.IMPLICIT_WAIT)

    @classmethod
    def logout(cls):
        logger.info('注销用户%s...', cls.driver.find_element_by_xpath('//*[@id="user-tools"]/strong').text)
        cls.driver.find_element_by_xpath('//*[@id="user-tools"]//a[@href="/admin/logout/"]').click()

    @classmethod
    def init_table_list_header(cls):
        if cls.TABLE_HEADER:
            return
        try:
            thead = cls.driver.find_element_by_xpath(r'//table[@id="result_list"]/thead/tr')
            cls.TABLE_HEADER = cls.get_element_attribute(thead, 'text').split('\n')
        except NoSuchElementException:
            pass

    @classmethod
    def setUpClass(cls) -> None:
        super(BaseTestCase, cls).setUpClass()
        cls.login()
        cls.init_table_list_header()
        if not cls.TABLE_HEADER:
            logger.warning("%s暂无数据，无法获取列表页表头！", config.URIS.get(cls.uri, cls.uri))

    def collect_error_infos(self):
        try:
            crash = self.driver.find_element_by_id('browserTraceback')  # django exception page
            errors = crash.find_elements_by_xpath(r'//*[@class="traceback"]/li[@class="frame user"]')
            bad_codes = ['CRASH occurred!']
            for error in errors:
                py_file = self.get_element_attribute(error.find_element_by_tag_name('code'), 'text')
                ctx = error.find_element_by_class_name('context')
                err_lno = ctx.find_element_by_class_name('context-line').get_attribute('start')
                bad_codes.append(f'{py_file}[{err_lno}]    {ctx.text.replace("...", "").strip()}')
            return '\r\n'.join(bad_codes)

        except NoSuchElementException:
            for clz in config.ERROR_ELEMENT_CLASSES:  # waring tips inner page
                errors = self.driver.find_elements_by_class_name(clz)
                if errors:
                    return '， '.join([self.get_element_attribute(e, 'text') for e in errors])
            return None

    def show_all(self):
        try:
            self.driver.find_element_by_xpath(r'//a[contains(text(),"显示全部")]').click()
        except NoSuchElementException:
            pass

    def count_current_list(self):
        try:
            return len(self.driver.find_elements_by_xpath(r'//table[@id="result_list"]/thead/tr'))
        except NoSuchElementException:
            return 0

    def count_all_existed(self):
        self.driver.get(f'{self.url}/?all=')  # 显示全部
        self.driver.implicitly_wait(config.IMPLICIT_WAIT)
        return self.count_current_list()

    def get_row_values(self, row):
        cols = row.find_elements_by_tag_name('td')
        cols[0] = row.find_element_by_tag_name('th')
        return tuple([self.get_element_attribute(col, 'text') for col in cols])

    def get_current_values(self):
        try:
            rows = self.driver.find_elements_by_xpath(r'//table[@id="result_list"]/tbody/tr')
            return {rno: self.get_row_values(row) for rno, row in enumerate(rows, start=1)}
        except NoSuchElementException:
            return dict()

    def get_all_existed_values(self):
        self.driver.get(f'{self.url}/?all=')  # 显示全部
        self.driver.implicitly_wait(config.IMPLICIT_WAIT)
        return self.get_current_values()

    def check_exist(self, cur_objs, **kwargs):
        if not self.TABLE_HEADER:
            self.init_table_list_header()

        fields = set(kwargs.keys()).difference(self.IMPLICIT_FIELDS)
        inv_fields = set(fields).difference(self.TABLE_HEADER)
        if inv_fields:
            logger.error("%s没有属性%s", self.mod_name, ', '.join(inv_fields))
            return False, None

        indexes = [self.TABLE_HEADER.index(field) for field in fields]
        obj_attrs = [str(kwargs[self.TABLE_HEADER[idx]]) for idx in indexes]
        for row_no, row_values in cur_objs.items():
            for i, idx in enumerate(indexes):
                if obj_attrs[i] != row_values[idx]:
                    break
            else:
                return True, row_no
        logger.warning("没有找到%s: %s", self.mod_name, kwargs)
        return False, None

    def batch_check_exist(self, cur_objs, *args, strict=True):
        try:
            assert all(isinstance(item, dict) for item in args)
        except AssertionError:
            logger.error("批量查询条件args中的元素须均为dict")
            return False, None

        rows_no = list()
        for obj in args:
            found, row_no = self.check_exist(cur_objs, **obj)
            if found:
                rows_no.append(row_no)
            elif strict:
                return False, None
        return True, rows_no

    def select(self, *args, strict=True, **kwargs):
        if not self.count_current_list():
            return False, None

        if (not (args or kwargs)) or (args and kwargs):
            logger.error("args用于批量选中，kwargs用于选中单条目，不允许同时执行两种方式！")
            return False, None

        if not args:
            args = [kwargs]

        cur_objs = self.get_current_values()
        ret, rows_no = self.batch_check_exist(cur_objs, *args, strict=strict)
        if not (ret and rows_no):
            return False, rows_no

        for rno, row in enumerate(self.driver.find_elements_by_xpath(r'//table[@id="result_list"]/tbody/tr'), start=1):
            checkbox = row.find_element_by_xpath(r'td/input[@type="checkbox"]')
            if rno in rows_no:
                if not checkbox.is_selected():
                    checkbox.click()
            elif checkbox.is_selected():
                checkbox.click()

    def select_all(self):
        if not self.count_current_list():
            logger.error('%s暂无数据', self.mod_name)
            return False, None

        checkbox = self.driver.find_element_by_id('action-toggle')
        if not checkbox.is_selected:
            checkbox.click()

        rows_no = list(range(1, len(self.driver.find_elements_by_xpath(r'//table[@id="result_list"]/tbody/tr')) + 1))
        return checkbox.is_selected, rows_no

    def filter_options(self, options, attr='text', **kwargs):
        indexes = set(range(len(options)))

        includes = kwargs.get('includes')
        if includes:
            for idx, opt in enumerate(options):
                if self.get_element_attribute(opt, attr) not in includes:
                    indexes.remove(idx)

        excludes = kwargs.get('excludes')
        if excludes:
            for idx, opt in enumerate(options):
                if self.get_element_attribute(opt, attr) in excludes:
                    indexes.remove(idx)

        return [options[idx] for idx in indexes]

    def select_single_option(self, select_element, target=None, attr='text', **kwargs):
        if not 'select' == select_element.tag_name:
            logger.error("无法选中%s！元素不是选择框，而是%s", target, select_element.tag_name)
            return False, target
        if select_element.get_attribute('multiple'):
            logger.warning("复选选择框应使用select_multiple_options方法")

        options = select_element.find_elements_by_tag_name('option')
        if target is None:
            options = self.filter_options(options, attr, **kwargs)
            if options:
                opt = random.choice(options)
                opt.click()
                return True, self.get_element_attribute(opt, attr)
            else:
                logger.error("过滤条件无法找到可匹配的选项！ %s", kwargs)
                return False, target
        else:
            target = str(target)
            for opt in options:
                if target == self.get_element_attribute(opt, attr):
                    opt.click()
                    return True, target
            logger.error("选项中没有%s, 无法选中", target)
            return False, target

    def select_multiple_options(self, select_element, targets=None, attr='text', **kwargs):
        if not 'select' == select_element.tag_name and not select_element.get_attribute('multiple'):
            logger.error("无法选中%s！元素不是复选选择框，而是%s", targets, select_element.tag_name)
            return False, targets

        options = select_element.find_elements_by_tag_name('option')
        if targets is None:
            options = self.filter_options(options, attr, **kwargs)
            if options:
                choices = list()
                for opt in random.choices(options, k=random.randint(1, len(options))):
                    opt.click()
                    choices.append(self.get_element_attribute(opt, attr))
                return True, choices
            else:
                logger.error("过滤条件无法找到可匹配的选项！ %s", kwargs)
                return False, targets
        elif not isinstance(targets, (list, set, tuple)):
            logger.error("选项类型应为list/set/tuple，实际传入%s", type(targets))
            return False, targets

        elif len(targets) != len(set(targets)):
            logger.error("存在重复选项，无法选中！  %s", targets)
            return False, targets

        else:
            choices = list(deepcopy(targets))
            for opt in options:
                content = self.get_element_attribute(opt, attr)
                for target in targets:
                    if str(target) == content:
                        opt.click()
                        choices.remove(target)
                        break
            if choices:
                logger.error("选项中没有%s, 无法选中", choices)
                return False, targets
            else:
                return True, targets

    def add(self, **kwargs):
        # 点击新增button
        self.driver.find_element_by_xpath(f'//*[@id="changelist"]//a[ends-with(@href, "{self.uri}/add/")]').click()
        obj_dict = self.do_add(**kwargs)
        self.assertIsInstance(obj_dict, dict, f'无法增加{self.mod_name}，未生成有效对象： {obj_dict}')
        # 点击保存button
        self.driver.find_element_by_xpath(r'//button[contains(text(),"保存")]').click()
        self.driver.implicitly_wait(config.IMPLICIT_WAIT)
        if f'{self.url}/add' in self.driver.current_url:
            errors_info = self.collect_error_infos()
            try:
                self.assertIsNone(errors_info, f'增加{self.mod_name}失败！ {obj_dict}  错误信息: {errors_info}')
            finally:
                return obj_dict
        return obj_dict

    def do_add(self, **kwargs):
        raise NotImplementedError

    def do_action(self, action, attr='text'):
        """ 选择列表页下拉框中某操作并执行 """
        select = self.driver.find_element_by_xpath(r'//*[@id="changelist-form"]//select[@name="action"]')
        flag, action = self.select_single_option(select, target=action, attr=attr)
        if not flag:
            logger.error("页面%s不支持%s操作！", self.driver.current_url, action)
            return

        # 点击执行button
        self.driver.find_element_by_xpath(r'//button[contains(text(), "执行")]').click()
        try:
            # 确认执行
            self.driver.find_element_by_xpath(r'//input[@value="是的，我确定"]').click()
        except NoSuchElementException:
            errors_info = self.collect_error_infos()
            try:
                self.assertIsNone(errors_info, f'在页面{self.driver.current_url}执行{action}操作失败: {errors_info}')
            except AssertionError:
                raise

    def do_search(self, **kwargs):
        """ 设定选择条件并执行搜索 """
        try:
            search_bar = self.driver.find_element_by_xpath(r'//div[@class="search-container"]')

            items = deepcopy(kwargs)
            if 'keyword' in items:
                try:
                    kw_input = search_bar.find_element_by_xpath(r'//input[@id=searchbar]')
                    kw_input.clear()
                    kw_input.send_keys(items.pop('keyword'))
                except NoSuchElementException:
                    self.assertTrue(False, f'页面{self.driver.current_url}不支持关键字搜索操作！')

            filters = search_bar.find_elements_by_xpath(r'span[@class="search-filters"]/select')
            for fltr in filters:
                key = self.get_element_attribute(Select(fltr).first_selected_option, 'text')
                if key in kwargs:
                    self.assertTrue(self.select_single_option(fltr, items.pop(key))[0], f'{key}没有选项{kwargs[key]}')
            self.assertEqual(0, len(items), f'页面{self.driver.current_url}不支持搜索条件: {", ".join(items.keys())}')

        except NoSuchElementException:
            self.assertTrue(False, f'页面{self.driver.current_url}不支持搜索操作！')

        try:
            # 执行搜索
            self.driver.find_element_by_xpath(r'//*[@id="changelist-search"]//input[@value="搜索"]').click()
        except NoSuchElementException:
            errors_info = self.collect_error_infos()
            try:
                self.assertIsNone(errors_info, f'页面{self.driver.current_url}执行搜索出现异常！ 错误信息: {errors_info}')
            except AssertionError:
                raise

    def delete(self, *args, strict=True, **kwargs):
        if self.select(*args, **kwargs, strict=strict)[0]:
            self.do_action(action='delete_selected', attr='value')
            return True
        else:
            return False

    def check_add(self, objs_list, **kwargs):
        cnt = self.count_all_existed()
        obj = self.add(**kwargs)
        cur_cnt = self.count_all_existed()
        if self.assertEqual(1, cur_cnt - cnt, f'增加{self.mod_name}失败！ {obj}'):
            flag, row_no = self.select(**obj)
            if self.assertTrue(flag, f'增加{self.mod_name}失败！ {obj}'):
                logger.info("增加%s成功！ 第%s行: %s", self.mod_name, row_no[0], obj)
                objs_list.append(obj)
                return obj, row_no[0]
        return kwargs, None

    def check_delete(self, **kwargs):
        obj = deepcopy(kwargs)
        inv_keys = set(obj.keys()).difference(self.FIELDS)
        inv_keys.update([k for k, v in obj.items() if v is None])
        dummy = [obj.pop(k) for k in inv_keys]
        if not self.assertGreater(len(obj), 0, f'无效的{self.mod_name}查询条件: {kwargs}'):
            return

        cnt = self.count_all_existed()
        logger.info("开始删除%s: %s", self.mod_name, obj)
        if self.assertTrue(self.delete(**obj), f'删除{self.mod_name}失败！ {obj}'):
            cur_cnt = self.count_all_existed()
            if self.assertEqual(1, cnt - cur_cnt, f'删除{self.mod_name}失败！ {obj}'):
                if self.assertFalse(self.select(**obj)[0], f'删除{self.mod_name}失败！ {obj}'):
                    logger.info("删除%s成功！ %s", self.mod_name, obj)

    def clear(self, uri=''):
        if uri not in config.URI_ENUM:
            logger.critical("错误的URI: %s", uri)

        if self.count_all_existed():
            logger.info("清空%s...", config.URIS[uri])
            if self.select_all()[0]:
                self.do_action(action='delete_selected', attr='value')
            else:
                logger.error("全选%s失败，无法清空", config.URIS[uri])
        else:
            logger.info("%s暂无数据", config.URIS[uri])
