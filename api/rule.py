#! /usr/bin/env python3
# -*- coding:utf-8 -*-
import random

from ..core import case_tag
from ..logger import logger
from ..sql_executor import sql_executor
from ..utils import utc2local
from . import config
from .base_api_test import BaseAPITestCase

RULE_VERBOSE_NAME = '规则'


class TestRule(BaseAPITestCase):

    uri = 'arrange_rule'
    db_table = 'rule'
    verbose_name = RULE_VERBOSE_NAME
    new_rule_id = ''

    filter_params_db_fields_mapping = {
        'rule_code': 'rule_code',
        'name__contains': 'name',
        'external_name__contains': 'external_name',
        'status': 'status',
        'application': 'application_id'
    }

    @classmethod
    def setUpClass(cls) -> None:
        super(TestRule, cls).setUpClass()
        attrs = [field[:-3] if field == 'application_id' else field for field in cls.attributes]
        attrs.extend(['scope', 'factor'])
        cls.attributes = tuple(attrs)

    def compare_with_db(self, item, *args):
        self.assertIsInstance(item, dict)
        rid = item.get('id')
        self.assertTrue(str(rid).isdigit(), f'{self.verbose_name}信息错误，无法查询数据库： {item}')
        logger.info("开始校验%s（id=%s）信息...", self.verbose_name, rid)
        db_info = sql_executor.execute(f'SELECT * FROM {self.db_table} WHERE id = {rid}')[0]

        factors = [ret[0] for ret in sql_executor.execute(f'SELECT factor_id FROM rule_factor WHERE rule_id = {rid}')]
        rets = sql_executor.execute(f'SELECT rulesetcategory_id FROM rule_scope WHERE rule_id = {rid}')
        scopes = [ret[0] for ret in rets]

        for k, v in item.items():
            if k == 'application':
                self.assertEqual(v, db_info['application_id'], f'{self.verbose_name}{k}信息不匹配！')
            elif k == 'factor':
                self.assertListEqual(v, factors, f'{self.verbose_name}{k}信息不匹配！')
            elif k == 'scope':
                self.assertListEqual(v, scopes, f'{self.verbose_name}{k}信息不匹配！')
            elif k == 'modify_time':
                self.assertEqual(v, utc2local(db_info[k], fmt=config.DATETIME_FMT), f'{self.verbose_name}{k}信息不匹配！')
            else:
                self.assertEqual(v, db_info[k], f'{self.verbose_name}{k}信息不匹配！')
        logger.info("%s（id=%s）信息校验成功！", self.verbose_name, rid)

    @case_tag(f'默认参数查询{RULE_VERBOSE_NAME}', 'Zhang Xueyu')
    def test_get_rules_by_default(self):
        self.check_get_items_by_default()

    @case_tag(f'匹配编码过滤条件查询{RULE_VERBOSE_NAME}', 'Zhang Xueyu')
    def test_get_rule_by_code(self):
        self.check_filter_items('rule_code')

    @case_tag(f'匹配名称过滤条件查询{RULE_VERBOSE_NAME}', 'Zhang Xueyu')
    def test_get_rule_by_name(self):
        self.check_filter_items('name__contains')

    @case_tag(f'匹配外部名称过滤条件查询{RULE_VERBOSE_NAME}', 'Zhang Xueyu')
    def test_get_rule_by_external_name(self):
        self.check_filter_items('external_name__contains')

    @case_tag(f'匹配状态过滤条件查询{RULE_VERBOSE_NAME}', 'Zhang Xueyu')
    def test_get_rule_by_status(self):
        self.check_filter_items('status')

    @case_tag(f'匹配产品应用过滤条件查询{RULE_VERBOSE_NAME}', 'Zhang Xueyu')
    def test_get_rule_by_prod_app(self):
        self.check_filter_items('application')

    @case_tag(f'查询{RULE_VERBOSE_NAME}详情', 'Zhang Xueyu')
    def test_get_rule_details(self):
        self.check_query_item_details()

    @case_tag(f'查询不存在的{RULE_VERBOSE_NAME}详情', 'Zhang Xueyu')
    def test_get_not_existed_rule_details(self):
        self.check_query_not_existed_item()

    @case_tag(f'{RULE_VERBOSE_NAME}排序', 'Zhang Xueyu')
    def test_ordering(self):
        excludes = ('description', 'condition_config', 'code_statement', 'scope', 'factor')
        self.check_ordering(set(self.attributes).difference(excludes))

    @case_tag(f'分页查询{RULE_VERBOSE_NAME}', 'Zhang Xueyu')
    def test_paginate(self):
        self.check_paginating()

    @case_tag(f'新增{RULE_VERBOSE_NAME}', 'Sun Suwei')
    def test_add_new_rule(self):
        # 1、添加非当前应用id的规则
        # 2、添加未启用因子
        # 3、添加后查看因子ref_count是否+1

        factor_sql_raw = f"""SELECT DISTINCT id,ref_count from factor WHERE status=1"""
        rets = sql_executor.execute(factor_sql_raw)
        factor_id, ref_count = random.choice(rets)
        app_sql_raw = \
            f"""SELECT DISTINCT application_id FROM factor_application_relation WHERE factor_id={factor_id}"""
        # 有可能是多个，默认选择第一个application id
        app_id = sql_executor.execute(app_sql_raw)[0][0]
        # 获取scope id，可能是多个，默认选择第一个
        scope_sql_raw = """SELECT id FROM rule_set_category"""
        scope_id = sql_executor.execute(scope_sql_raw)[0][0]

        condition_dict = {
            "tag": "common",
            "entities": [{
                "left_brackets": True,
                "right_brackets": True,
                "left_factor": factor_id,
                "right_value": 1,
                "operator": '='
            }],
            "relations": []
        }

        self.add_rule(condition_dict, f'test_api_add_rule_{factor_id}', 'test_external_name', 'test_desc', app_id,
                      scope_id)
        ref_count_new = sql_executor.execute(f"""SELECT ref_count FROM factor WHERE id={factor_id}""")[0][0]
        self.assertEqual(int(ref_count_new), ref_count+1, '')

    @case_tag(f'删除{RULE_VERBOSE_NAME}', owner='Sun Suwei')
    def test_delete_rule(self):
        if self.new_rule_id:
            self.delete(self.url+str(self.new_rule_id))

        sql_raw = f"""SELECT id FROM rule where status = 0"""
        ret = sql_executor.execute(sql_raw)
        del_id = random.choice(ret)[0]
        logger.info('测试删除id:%s的规则', del_id)
        self.delete(self.url+str(del_id))

    def test_update_rule(self):
        # patch：局部更新规则 put:更新全部字段
        # 启用状态无法更新规则的scope
        # 更新name，external_name，description,

        pass
