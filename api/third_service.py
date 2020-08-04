#! /usr/bin/env python3
# -*- coding:utf-8 -*-

from .base_api_test import BaseAPITestCase
from ..core import case_tag

THIRD_SVC_VERBOSE_NAME = '三方服务'


class TestThirdSvc(BaseAPITestCase):

    uri = 'third_service'
    db_table = 'third_service'
    verbose_name = THIRD_SVC_VERBOSE_NAME

    @case_tag(f'默认参数查询{THIRD_SVC_VERBOSE_NAME}', 'Zhang Xueyu')
    def test_get_svcs_by_default(self):
        self.check_get_items_by_default()

    @case_tag(f'查询{THIRD_SVC_VERBOSE_NAME}详情', 'Zhang Xueyu')
    def test_get_svc_details(self):
        self.check_query_item_details()

    @case_tag(f'查询不存在的{THIRD_SVC_VERBOSE_NAME}详情', 'Zhang Xueyu')
    def test_get_not_existed_svc_details(self):
        self.check_query_not_existed_item()

    @case_tag(f'{THIRD_SVC_VERBOSE_NAME}排序', 'Zhang Xueyu')
    def test_ordering(self):
        self.check_ordering()

    @case_tag(f'分页查询{THIRD_SVC_VERBOSE_NAME}', 'Zhang Xueyu')
    def test_paginate(self):
        self.check_paginating()
