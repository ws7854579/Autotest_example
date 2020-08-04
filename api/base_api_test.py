#! /usr/bin/env python3
# -*- coding:utf-8 -*-

import json
import random
from math import ceil
from unittest import TestCase

import requests
from faker import Faker
from requests.exceptions import RequestException

from ..logger import logger
from ..sql_executor import sql_executor
from . import config
from .oauth import PasswordOAuth


class BaseAPITestCase(TestCase):

    _url = f'http://api.{config.DOMAIN}/v1/api/'
    uri = ''
    db_table = ''
    verbose_name = ''

    filter_params_db_fields_mapping = dict()

    oauth = PasswordOAuth(config.AUTH_URL, config.AUTH_CLI_ID, config.AUTH_CLI_SK, config.USER, config.PWD)
    faker = Faker('zh_CN')

    new_rule_id = ''

    @classmethod
    def request(cls, method, url, **kwargs):
        kwargs.setdefault('headers', cls.token)
        kwargs.setdefault('timeout', config.REQUEST_TIMEOUT)
        try:
            response = requests.request(method, url, **kwargs)
            assert response.status_code == 200
            logger.info("%s方法请求%s成功！", method, response.url)
            return response.status_code, response.json()
        except RequestException as ex:
            logger.critical("%s方法请求%s异常", method, url, exc_info=ex)
        except AssertionError:
            logger.warning("%s方法请求%s返回状态码为%s", method, response.url, response.status_code)
            return response.status_code, response.content
        except ValueError:
            logger.critical("%s方法请求%s返回结果无法json序列化： %s", method, response.url, response.content)

    @classmethod
    def get(cls, url, **kwargs):
        kwargs.setdefault('allow_redirects', True)
        return cls.request('get', url, **kwargs)

    @classmethod
    def post(cls, url, **kwargs):
        return cls.request('post', url, **kwargs)

    @classmethod
    def put(cls, url, **kwargs):
        return cls.request('put', url, **kwargs)

    @classmethod
    def patch(cls, url, **kwargs):
        return cls.request('patch', url, **kwargs)

    @classmethod
    def delete(cls, url, **kwargs):
        return cls.request('delete', url, **kwargs)

    @classmethod
    def get_all_items_from_db(cls, pk='id'):
        logger.info("查询数据库表%s中的全部记录...", cls.db_table)
        cls.all_items = tuple([item[pk] for item in sql_executor.execute(f'SELECT DISTINCT {pk} FROM {cls.db_table}')])
        cls.all_cnt = len(cls.all_items)
        logger.info("查询成功！数据库表%s中共有%d条记录", cls.db_table, cls.all_cnt)

    @classmethod
    def get_all_matched_items_from_db(cls, *args, pk='id'):
        logger.info("查询数据库表%s中匹配过滤条件的记录...", cls.db_table)
        raw_sql = f'SELECT DISTINCT {pk} FROM {cls.db_table}'
        conditions = ' AND '.join(args)
        if conditions:
            raw_sql += f' WhERE {conditions}'
        return [item[pk] for item in sql_executor.execute(raw_sql)]

    @classmethod
    def get_all_items_from_api(cls, pk_key='id'):
        logger.info("查询全部%s数据...", cls.verbose_name)
        stat_code, resp = cls.get(cls.url, params={'page_size': cls.all_cnt})
        assert stat_code == 200, f'请求{cls.url}失败！'

        if isinstance(resp, dict):
            assert resp['next'] is None, f'请求参数中设置页面大小为{cls.all_cnt}， 下一页信息应为None'
            cls.pageable = True
            items_list = resp['results']
        else:
            cls.pageable = False
            items_list = resp

        assert len(items_list) == cls.all_cnt, \
            f'返回{cls.verbose_name}数目{len(items_list)}与数据库记录{cls.all_cnt}不匹配！'
        items_pk = tuple([item[pk_key] for item in items_list])
        assert len(set(cls.all_items).difference(items_pk)) == 0, f'返回{cls.verbose_name}数据未包含全部数据库记录！'
        assert len(set(items_pk).difference(cls.all_items)) == 0, f'返回{cls.verbose_name}数据包含数据库中不存在的记录！'
        logger.info("查询全部%s数据成功，与数据库记录完全匹配！", cls.verbose_name)

    @classmethod
    def random_item_id(cls):
        return random.choice(cls.all_items)

    @classmethod
    def setUpClass(cls) -> None:
        cls.url = f'{cls._url}{cls.uri}/'
        cls.token = cls.oauth.build_token_header()
        cls.attributes = tuple([field[0] for field in sql_executor.execute(f'DESC {cls.db_table}')])
        cls.get_all_items_from_db()
        cls.get_all_items_from_api()

    @classmethod
    def random_db_field_value(cls, field):
        return random.choice([ret[0] for ret in sql_executor.execute(f'SELECT DISTINCT {field} FROM {cls.db_table}')])

    def compare_with_db(self, item, *args):  # pylint:disable=unused-argument
        self.assertIsInstance(item, dict)
        pk = item.get('id')
        self.assertTrue(str(pk).isdigit(), f'{self.verbose_name}信息错误，无法查询数据库： {item}')
        logger.info("开始校验%s（id=%s）信息...", self.verbose_name, pk)
        db_info = sql_executor.execute(f'SELECT * FROM {self.db_table} WHERE id = {pk}')[0]
        for k, v in item.items():
            self.assertEqual(v, db_info[k], f'{self.verbose_name}{k}信息不匹配！')
        logger.info("%s（id=%s）信息校验成功！", self.verbose_name, pk)

    def check_get_items_by_default(self):
        logger.info("默认参数查询%s...", self.verbose_name)
        stat_code, resp = self.get(self.url)
        self.assertEqual(200, stat_code, f'默认参数请求{self.url}失败！')

        if self.pageable:
            items = resp['results']
            count = resp['count']
        else:
            items = resp
            count = len(items)

        self.assertEqual(self.all_cnt, count, f'返回{self.verbose_name}数目{count}与数据库记录{self.all_cnt}不匹配！')
        self.assertTrue(all([isinstance(item, dict) for item in items]), f'返回{self.verbose_name}数据格式均应为dict！')
        self.compare_with_db(random.choice(items))
        logger.info("默认参数查询%s校验成功！", self.verbose_name)

    def check_filter_items(self, param, value=None, pk='id'):
        self.assertIn(param, self.filter_params_db_fields_mapping, f'查询{self.verbose_name}不支持匹配{param}过滤！')
        logger.info("匹配%s过滤条件查询%s...", param, self.verbose_name)
        db_field = self.filter_params_db_fields_mapping[param]
        exact = not param.endswith('__contains')

        if not value:
            value = self.random_db_field_value(db_field)
        values = [value]
        if not exact and isinstance(value, str) and len(value) > 1:
            values.extend([value[1:], value[:-1]])

        for val in values:
            payload = {param: val}
            if self.pageable:
                payload.update({'page_size': self.all_cnt})
            stat_code, resp = self.get(self.url, params=payload)
            self.assertEqual(200, stat_code, f'匹配过滤条件{payload}查询{self.url}失败！')

            condition = f"{db_field} = '{val}'" if exact else f"{db_field} LIKE '%{val}%'"
            matched_factors = self.get_all_matched_items_from_db(condition, pk=pk)
            if not matched_factors:
                logger.warning("数据库表%s中未查询到匹配过滤条件%s的记录！", self.db_table, condition)
                continue

            matched_cnt = len(matched_factors)
            logger.info("数据库表%s中查询到%d条匹配%s过滤条件的记录！", self.db_table, matched_cnt, condition)
            if self.pageable:
                self.assertEqual(len(resp['results']), resp['count'],
                                 f"返回{self.verbose_name}数目与count字段结果{resp['count']}不匹配！")
                items_list = resp['results']
            else:
                items_list = resp

            self.assertEqual(matched_cnt, len(items_list),
                             f'返回{self.verbose_name}数目{len(items_list)}与数据库记录{matched_cnt}不匹配！')
            self.compare_with_db(random.choice(items_list), condition)
            logger.info("匹配%s过滤条件查询%s校验成功！\n", param, self.verbose_name)

    def check_query_item_details(self, pk=None):
        if pk is None:
            pk = self.random_item_id()

        logger.info("查询%s（id=%s）详情...", self.verbose_name, pk)
        stat_code, resp = self.get(f'{self.url}{pk}/')
        self.assertEqual(200, stat_code, f'查询{self.verbose_name}（id={pk}）详情失败！')
        self.compare_with_db(resp)
        logger.info("查询%s（id=%s）详情校验成功！", self.verbose_name, pk)

    def check_query_not_existed_item(self):
        ids = list()
        ids.append(int(sql_executor.execute(f'SELECT MAX(id) FROM {self.db_table}')[0][0]) + random.randrange(1, 9999))
        ids.append(int(sql_executor.execute(f'SELECT MIN(id) FROM {self.db_table}')[0][0]) - random.randrange(1, 9999))
        for inv_id in ids:
            logger.info("查询不存在%s数据（id=%d）详情...", self.verbose_name, inv_id)
            stat_code, resp = self.get(f'{self.url}{inv_id}/')
            self.assertEqual(404, stat_code, f'查询不存在{self.verbose_name}数据（id=%d）详情返回状态码校验失败！')
            self.assertDictEqual({'detail': '未找到。'}, json.loads(resp.decode('utf-8')),
                                 f'查询不存在{self.verbose_name}数据（id=%d）详情返回信息校验失败！')
            logger.info("查询不存在%s数据（id=%d）详情校验成功！\n", self.verbose_name, inv_id)

    def check_ordering(self, order_fields=None):
        if self.all_cnt == 1:
            logger.warning("数据库表%s中仅有一条%s记录，无法测试排序！", self.db_table, self.verbose_name)
            return

        if not order_fields:
            order_fields = self.attributes

        for order_field in order_fields:
            logger.info("按%s排序查询%s...", order_field, self.verbose_name)
            stat_code, resp = self.get(self.url, params={'ordering': order_field})
            self.assertEqual(200, stat_code, f'按{order_field}排序查询{self.verbose_name}失败！')

            items = resp['results'] if self.pageable else resp
            items_cnt = len(items)
            i, j = random.choices(range(items_cnt), k=2)
            while i == j:
                j = random.randrange(items_cnt)
            indexes = {i, j, items_cnt - 1} if self.pageable else {i, j}
            field_values = [items[idx][order_field] for idx in sorted(indexes)]

            if self.pageable and resp['next']:
                stat_code, resp = self.get(resp['next'], params={'ordering': order_field})
                self.assertEqual(200, stat_code, f"按{order_field}排序请求{resp['next']}失败！")
                field_values.append(random.choice(resp['results'])[order_field])

            if not all([str(val).isdigit() for val in field_values]):
                field_values = [str(val).lower() for val in field_values]
            self.assertListEqual(field_values, sorted(field_values),
                                 f'{self.verbose_name}数据按{order_field}排序校验失败！')
            logger.info("按%s排序查询%s校验成功！\n", order_field, self.verbose_name)

    def check_paginating(self):
        if self.all_cnt == 1:
            logger.warning("数据库表%s中仅有一条%s记录，无法测试分页！", self.db_table, self.verbose_name)
            return

        logger.info("按默认页面大小查询%s...", self.verbose_name)
        stat_code, resp = self.get(self.url)
        self.assertEqual(200, stat_code, f'按默认页面大小查询{self.verbose_name}失败！')
        self.assertIsNone(resp['previous'], f'按默认页面大小查询{self.verbose_name}，上一页信息应为None！')
        if resp['next']:
            self.assertEqual(10, len(resp['results']),
                             f"{self.verbose_name}数据较多时应默认返回10条记录，实际返回{len(resp['results'])}条！")
            logger.info("按默认页面大小查询%s校验成功！", self.verbose_name)
        else:
            logger.warning("%s数据记录较少，无法测试默认页面大小！", self.verbose_name)
        logger.info("按默认页面大小查询%s校验成功！\n", self.verbose_name)

        page_size = random.randrange(1, self.all_cnt)
        max_page = ceil(self.all_cnt / page_size)
        page = random.randrange(1, max_page)

        logger.info("设置页面大小为%d查询%s...", page_size, self.verbose_name)
        stat_code, resp = self.get(self.url, params={'page': page, 'page_size': page_size})
        self.assertEqual(200, stat_code, f'设置页面大小为{page_size}查询{self.verbose_name}失败！')
        self.assertEqual(page_size, len(resp['results']), f'设置页面大小为{page_size}查询{self.verbose_name}校验失败！')
        self.assertIsNotNone(resp['next'],
                             f'设置页面大小为{page_size}查询{self.verbose_name}, 第{page}页返回数据中下一页信息不应为空！')
        if page > 1:
            self.assertIsNotNone(resp.get('previous'),
                                 f'设置页面大小为{page_size}查询{self.verbose_name}, 第{page}页返回数据中上一页信息不应为空！')
        logger.info("设置页面大小为%d查询%s校验成功！\n", page_size, self.verbose_name)

        last_page_size = self.all_cnt % page_size
        if last_page_size == 0:
            last_page_size = page_size
        logger.info("设置页面大小为%d查询%s末页数据...", page_size, self.verbose_name)
        stat_code, resp = self.get(self.url, params={'page': max_page, 'page_size': page_size})
        self.assertEqual(200, stat_code, f'设置页面大小为{page_size}查询{self.verbose_name}末页数据失败！')
        self.assertEqual(last_page_size, len(resp['results']),
                         f'设置页面大小为{page_size}查询{self.verbose_name}，末页数据校验失败！')
        self.assertIsNotNone(resp['previous'],
                             f'设置页面大小为{page_size}查询{self.verbose_name}，末页返回数据中上一页信息不应为空！')
        self.assertIsNone(resp['next'], f'设置页面大小为{page_size}查询{self.verbose_name}，末页返回数据中下一页信息应为空！')
        logger.info("设置页面大小为%d查询%s末页数据校验成功！\n", page_size, self.verbose_name)

        page_size = random.randint(self.all_cnt + 1, 99999999)
        logger.info("设置页面大小为%d（大于全部记录数目）查询%s...", page_size, self.verbose_name)
        stat_code, resp = self.get(self.url, params={'page_size': page_size})
        self.assertEqual(200, stat_code, f'设置页面大小为{page_size}（大于全部记录数目）查询{self.verbose_name}失败！')
        self.assertEqual(self.all_cnt, len(resp['results']),
                         f'设置页面大小为{page_size}（大于全部记录数目）查询{self.verbose_name}校验失败！')
        self.assertIsNone(resp['previous'],
                          f'设置页面大小为{page_size}（大于全部记录数目）查询{self.verbose_name}，上一页信息应为空！')
        self.assertIsNone(resp['next'],
                          f'设置页面大小为{page_size}（大于全部记录数目）查询{self.verbose_name}，下一页信息应为空！')
        logger.info("设置页面大小为%d（大于全部记录数目）查询%s校验成功！\n", page_size, self.verbose_name)

    def add_rule(self, condition_dict, name, ex_name, description, app_id, scope):
        self.assertIsInstance(app_id, int, '应用id应该是int类型')
        # scope是str类型，可以为多个
        condition = json.dumps(condition_dict)
        data = {
            "condition_config": condition,
            "name": name,
            "external_name": ex_name,
            "description": description,
            "status": "0",
            "ref_count": 0,
            "application": app_id,
            "scope": [
                scope
            ]
        }

        resp_code, resp = self.post(self.url, json=data)
        self.assertEqual(resp_code, 200, '新增规则失败！')
        self.new_rule_id = resp['id']
