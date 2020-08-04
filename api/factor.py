#! /usr/bin/env python3
# -*- coding:utf-8 -*-

import random
from datetime import datetime

from . import config
from .base_api_test import BaseAPITestCase
from .oauth import PasswordOAuth
from .. import consts
from ..core import case_tag
from ..logger import logger
from ..sql_executor import sql_executor
from ..utils import utc2local

FACTOR_VERBOSE_NAME = '因子'
FACTOR_APP_RELATION_VERBOSE_NAME = '因子-产品应用关系'


class TestFactor(BaseAPITestCase):
    uri = 'factor'
    db_table = 'factor'
    verbose_name = FACTOR_VERBOSE_NAME

    @classmethod
    def setUpClass(cls) -> None:
        super(TestFactor, cls).setUpClass()
        attrs = [field[:-3] if field in ['service_id', 'db_table_id'] else field for field in cls.attributes]
        cls.attributes = tuple(attrs)

    def compare_with_db(self, item, *args):
        self.assertIsInstance(item, dict)
        fid = item.get('id')
        self.assertTrue(str(fid).isdigit(), f'{self.verbose_name}信息错误，无法查询数据库： {item}')
        logger.info("开始校验%s（id=%s）信息...", self.verbose_name, fid)
        db_info = sql_executor.execute(f'SELECT * FROM {self.db_table} WHERE id = {fid}')[0]

        apps = sql_executor.execute(f'SELECT application_id FROM factor_application_relation WHERE factor_id = {fid}')
        app_ids = [app['application_id'] for app in apps]

        for k, v in item.items():
            if k == 'application':
                self.assertListEqual(v, app_ids, f'{self.verbose_name}{k}信息不匹配！')
            elif k in ('service', 'db_table'):
                self.assertEqual(v, db_info[f'{k}_id'], f'{self.verbose_name}{k}信息不匹配！')
            elif k == 'modify_time':
                self.assertEqual(v, utc2local(db_info[k], fmt=config.DATETIME_FMT), f'{self.verbose_name}{k}信息不匹配！')
            else:
                self.assertIn(k, db_info, f'数据库表{self.db_table}中没有属性: {k}')
                self.assertEqual(v, db_info[k], f'{self.verbose_name}{k}信息不匹配！')
        logger.info("%s（id=%s）信息校验成功！", self.verbose_name, fid)

    def update_status(self, factor, user=None, pwd=None, method='patch'):
        method = str(method).lower()
        self.assertIn(method, ('patch', 'put'), f'更新{self.verbose_name}状态仅支持使用patch或put方法，无法使用{method}！')

        if user:
            oauth = PasswordOAuth(config.AUTH_URL, config.AUTH_CLI_ID, config.AUTH_CLI_SK, user, pwd)
        oauth_token = oauth.build_token_header() if user else self.token

        fid, status, mod_time = [getattr(factor, field) for field in ['id', 'status', 'modify_time']]
        mod_stat = consts.STAT_DISABLE_CODE if status == consts.STAT_ENABLE_CODE else consts.STAT_ENABLE_CODE
        stat_code, resp = getattr(self, method)(f'{self.url}{fid}/', headers=oauth_token, data={'status': mod_stat})
        self.assertEqual(200, stat_code)
        self.assertIsInstance(resp, dict)
        for field in set(resp.keys()).intersection(factor.keys()):
            if field == 'status':
                self.assertEqual(mod_stat, resp[field])
            elif field == 'modify_user':
                self.assertEqual(user if user else config.USER, resp[field])
            elif field == 'modify_time':
                self.assertGreater(datetime.strptime(resp[field], config.DATETIME_FMT), mod_time)
            else:
                self.assertEqual(factor[field], resp[field])
        self.compare_with_db(resp)

    @case_tag(f'默认参数查询{FACTOR_VERBOSE_NAME}', 'Zhang Xueyu')
    def test_get_factors_by_default(self):
        self.check_get_items_by_default()

    @case_tag(f'查询{FACTOR_VERBOSE_NAME}详情', 'Zhang Xueyu')
    def test_get_factor_details(self):
        self.check_query_item_details()

    @case_tag(f'查询不存在的{FACTOR_VERBOSE_NAME}详情', 'Zhang Xueyu')
    def test_get_not_existed_factor_details(self):
        self.check_query_not_existed_item()

    @case_tag(f'更改{FACTOR_VERBOSE_NAME}启用状态', 'Zhang Xueyu')
    def test_update_factor_status(self):
        factors = sql_executor.execute(f'SELECT * FROM {self.db_table} WHERE ref_count = 0')
        if factors:
            factor = random.choice(factors)
        else:
            sql_executor.execute(f'UPDATE {self.db_table} SET ref_count = 0 WHERE id = {self.random_item_id()}')
            factor = sql_executor.execute('SELECT * FROM {self.db_table} WHERE ref_count = 0')[0]

        self.update_status(factor)
        self.update_status(factor, config.OTHER_USER, config.OTHER_PWD, method='put')

    @case_tag(f'无法停用已启用且引用次数大于0的{FACTOR_VERBOSE_NAME}状态', 'Zhang Xueyu')
    def test_forbid_update_factor_status(self):
        factors = sql_executor.execute(f'SELECT * FROM {self.db_table} WHERE status = 1 AND ref_count > 0')
        if factors:
            factor = random.choice(factors)
        else:
            sql_executor.execute(f'UPDATE {self.db_table} SET ref_count = 0 WHERE id = {self.random_item_id()}')
            factor = sql_executor.execute('SELECT * FROM {self.db_table} WHERE status = 1 AND ref_count > 0')[0]

        url = f"{self.url}{factor['id']}/"
        for method in ['patch', 'put']:
            stat_code, resp = getattr(self, method)(url, data={'status': consts.STAT_DISABLE_CODE})
            self.assertEqual(500, stat_code)
            self.assertIn('引用计数大于0，启用状态不能为已停用', resp.decode('utf-8'))

    @case_tag(f'{FACTOR_VERBOSE_NAME}排序', 'Zhang Xueyu')
    def test_ordering(self):
        self.check_ordering()

    @case_tag(f'分页查询{FACTOR_VERBOSE_NAME}', 'Zhang Xueyu')
    def test_paginate(self):
        self.check_paginating()


class TestFactor2AppRelation(BaseAPITestCase):

    uri = 'factor_application_relation'
    db_table = 'factor_application_relation'
    verbose_name = FACTOR_APP_RELATION_VERBOSE_NAME

    filter_params_db_fields_mapping = {
        'factor_code': 'factor_code',
        'factor_name__contains': 'factor_name',
        'factor_status': 'factor_status',
        'application': 'application_id'
    }

    @classmethod
    def random_item_id(cls):
        return random.choice([ret[0] for ret in sql_executor.execute(f'SELECT id FROM {cls.db_table}')])

    @classmethod
    def setUpClass(cls) -> None:
        cls.url = f'{cls._url}{cls.uri}/'
        cls.token = cls.oauth.build_token_header()
        cls.attributes = ('factor',)
        cls.get_all_items_from_db(pk='factor_id')
        cls.get_all_items_from_api(pk_key='factor')

    def compare_with_db(self, item, *args):
        raw_sql = f'SELECT COUNT(DISTINCT factor_id) FROM {self.db_table} WHERE '
        conditions = list(args)
        conditions.insert(0, f"factor_id = {item.get('factor')}")
        return sql_executor.execute(f"{raw_sql}{' AND '.join(conditions)}")[0] == 1

    @case_tag(f'默认参数查询{FACTOR_APP_RELATION_VERBOSE_NAME}', 'Zhang Xueyu')
    def test_get_f2a_relation_by_default(self):
        self.check_get_items_by_default()

    @case_tag(f'匹配编码过滤条件查询{FACTOR_APP_RELATION_VERBOSE_NAME}', 'Zhang Xueyu')
    def test_get_f2a_relation_by_factor_code(self):
        self.check_filter_items('factor_code', pk='factor_id')

    @case_tag(f'匹配名称过滤条件查询{FACTOR_APP_RELATION_VERBOSE_NAME}', 'Zhang Xueyu')
    def test_get_f2a_relation_by_factor_name(self):
        self.check_filter_items('factor_name__contains', pk='factor_id')

    @case_tag(f'匹配状态过滤条件查询{FACTOR_APP_RELATION_VERBOSE_NAME}', 'Zhang Xueyu')
    def test_get_f2a_relation_by_factor_status(self):
        self.check_filter_items('factor_status', pk='factor_id')

    @case_tag(f'匹配产品应用过滤条件查询{FACTOR_APP_RELATION_VERBOSE_NAME}', 'Zhang Xueyu')
    def test_get_f2a_relation_by_prod_app(self):
        self.check_filter_items('application', pk='factor_id')

    @case_tag(f'查询{FACTOR_APP_RELATION_VERBOSE_NAME}详情', 'Zhang Xueyu')
    def test_get_f2a_relation_details(self):
        self.check_query_item_details()

    @case_tag(f'查询不存在的{FACTOR_APP_RELATION_VERBOSE_NAME}详情', 'Zhang Xueyu')
    def test_get_not_existed_f2a_relation_details(self):
        self.check_query_not_existed_item()

    @case_tag(f'{FACTOR_APP_RELATION_VERBOSE_NAME}排序', 'Zhang Xueyu')
    def test_ordering(self):
        self.check_ordering()

    @case_tag(f'分页查询{FACTOR_APP_RELATION_VERBOSE_NAME}', 'Zhang Xueyu')
    def test_paginate(self):
        self.check_paginating()
