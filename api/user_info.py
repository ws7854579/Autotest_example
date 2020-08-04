#! /usr/bin/env python3
# -*- coding:utf-8 -*-

from .base_api_test import BaseAPITestCase
from ..core import case_tag
from ..logger import logger
from ..sql_executor import sql_executor

USER_INFO_VERBOSE_NAME = '用户信息'


class TestUserInfo(BaseAPITestCase):
    uri = 'user_info'
    db_table = 'user_info'
    verbose_name = USER_INFO_VERBOSE_NAME

    filter_params_db_fields_mapping = {'user_id': 'user_id'}

    def compare_with_db(self, item, *args):
        uipk = item.get('id')  # user_info表主键，不是user_id
        self.assertTrue(str(uipk).isdigit(), f'{self.verbose_name}信息错误，无法查询数据库： {item}')
        logger.info("开始校验%s（id=%s）信息...", self.verbose_name, uipk)
        db_info = sql_executor.execute(f'SELECT * FROM {self.db_table} WHERE id = {uipk}')[0]
        prod_apps = sql_executor.execute(
            f'SELECT productapplication_id FROM user_info_application WHERE userinfo_id = {uipk}')
        app_ids = [int(app[0]) for app in prod_apps]
        for k, v in item.items():
            if k == 'application':
                self.assertListEqual(v, app_ids, f'{self.verbose_name}{k}信息不匹配！')
            else:
                self.assertIn(k, db_info, f'数据库表{self.db_table}中没有属性: {k}')
                self.assertEqual(v, db_info[k], f'{self.verbose_name}{k}信息不匹配！')
        logger.info("%s（id=%s）信息校验成功！", self.verbose_name, uipk)

    @case_tag(f'默认参数查询{USER_INFO_VERBOSE_NAME}', 'Zhang Xueyu')
    def test_get_users_info_by_default(self):
        self.check_get_items_by_default()

    @case_tag(f'匹配用户id过滤条件查询{USER_INFO_VERBOSE_NAME}', 'Zhang Xueyu')
    def test_get_users_info_by_user_id(self):
        self.check_filter_items('user_id')

    @case_tag(f'查询{USER_INFO_VERBOSE_NAME}详情', 'Zhang Xueyu')
    def test_get_user_info_details(self):
        self.check_query_item_details()

    @case_tag(f'查询不存在的{USER_INFO_VERBOSE_NAME}详情', 'Zhang Xueyu')
    def test_get_not_existed_user_info_details(self):
        self.check_query_not_existed_item()

    @case_tag(f'{USER_INFO_VERBOSE_NAME}排序', 'Zhang Xueyu')
    def test_ordering(self):
        self.check_ordering()

    @case_tag(f'分页查询{USER_INFO_VERBOSE_NAME}', 'Zhang Xueyu')
    def test_paginate(self):
        self.check_paginating()
