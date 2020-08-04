#! /usr/bin/env python3
# -*- coding:utf-8 -*-

from .base_api_test import BaseAPITestCase
from ..core import case_tag

PROD_APP_VERBOSE_NAME = '产品应用'


class TestProductApp(BaseAPITestCase):

    uri = 'product_application'
    db_table = 'product_application'
    verbose_name = PROD_APP_VERBOSE_NAME

    @case_tag(f'默认参数查询{PROD_APP_VERBOSE_NAME}', 'Zhang Xueyu')
    def test_get_prod_apps_by_default(self):
        self.check_get_items_by_default()

    @case_tag(f'查询{PROD_APP_VERBOSE_NAME}详情', 'Zhang Xueyu')
    def test_get_prod_app_details(self):
        self.check_query_item_details()

    @case_tag(f'查询不存在的{PROD_APP_VERBOSE_NAME}详情', 'Zhang Xueyu')
    def test_get_not_existed_prod_app_details(self):
        self.check_query_not_existed_item()

    @case_tag(f'{PROD_APP_VERBOSE_NAME}排序', 'Zhang Xueyu')
    def test_ordering(self):
        self.check_ordering()
