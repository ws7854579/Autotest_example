#! /usr/bin/env python3
# -*- coding:utf-8 -*-

import random
import re
from copy import deepcopy

from . import config
from ... import utils
from ...consts import (
    DTYPE_BASIC, DTYPE_THIRD, FACTOR_STATUS_ENUM, FACTOR_STATUSES, FACTOR_TYPE_ENUM, FACTOR_TYPES, FTYPE_BASIC_PREFIX,
    FTYPE_THIRD, FTYPE_THIRD_PREFIX, STAT_DISABLE, STAT_ENABLE, STAT_UNKNOWN
)
from ...logger import logger
from ...sql_executor import sql_executor
from .base_test import BaseTestCase
from .test_db_table import TestDBTable
from .test_prod_app import TestProdApp
from .test_third_service import TestThirdService

FACTOR_STAT_ENUM = (STAT_ENABLE, STAT_DISABLE)


class TestFactor(BaseTestCase):
    uri = config.URI_FACTOR

    ID = 'id'
    PREFIX = 'Id prefix'
    NAME = 'Name'
    STATUS = 'Status'
    CODE_VAR = 'Code var'
    SVC = 'Service'
    DB_TABLE = 'Db table'
    MOD_USER = 'Modify user'
    MOD_TIME = 'Modify time'
    REF_CNT = 'Ref count'
    CODE = 'Factor code'
    APP = 'Application'

    FIELDS = (PREFIX, NAME, STATUS, CODE_VAR, SVC, DB_TABLE, MOD_USER, MOD_TIME, REF_CNT, CODE, APP)
    IMPLICIT_FIELDS = (ID, APP)

    """
    数据库表模型字段的统计[108个数据库表  2019-09-05]
    min = 1, max = 832, average = 64, median = 21
    """

    def generate_factors_from_db_table(self, db_table):
        prfx = FTYPE_BASIC_PREFIX if db_table[TestDBTable.DTYPE] == DTYPE_BASIC else FTYPE_THIRD_PREFIX
        basic_info = {
            self.PREFIX: FACTOR_TYPES[prfx],
            self.NAME: 'N/A',
            self.STATUS: STAT_UNKNOWN,
            self.DB_TABLE: db_table[TestDBTable.TABLE],
            self.MOD_USER: 'system',
            self.REF_CNT: 0,
            self.CODE: prfx,
        }

        sql = f"""
        SELECT alias_name
        FROM field_schema_v20190715_rule
        WHERE id IN (SELECT field_id
                     FROM model_field_schema_v20190715_rule mfsv20190715r
                              JOIN model_schema_v20190715_rule msv20190715r ON mfsv20190715r.model_id = msv20190715r.id
                     WHERE msv20190715r.db_table_name = '{basic_info[self.DB_TABLE]}');
        """

        ctx_key = db_table[TestDBTable.CTX_KEY]
        fields = tuple(map(lambda ret: ret[0], sql_executor.execute(sql)))
        factors = list()
        for svc in db_table[TestDBTable.SVC]:
            for fld in fields:
                factor = deepcopy(basic_info)
                factor.update({self.CODE_VAR: f'{ctx_key}.{fld}', self.SVC: svc})
                factors.append(factor)

        return factors

    def query_factors_from_db_table(self, db_table):
        db_table_name = db_table[TestDBTable.TABLE]
        sql = f"""
        SELECT *
        FROM factor
                 JOIN database_table dt ON factor.db_table_id = dt.id
        WHERE db_table_name = '{db_table_name}'
        """
        keys = [
            self.ID,
            self.PREFIX,
            self.NAME,
            self.STATUS,
            self.CODE_VAR,
            self.MOD_TIME,
            self.REF_CNT,
            self.SVC,
            self.MOD_USER,
            self.DB_TABLE,
        ]
        factors = [dict(zip(keys, ret)) for ret in sql_executor.execute(sql)]

        svc_ids = {factor[self.SVC] for factor in factors}
        if None in svc_ids:
            svc_ids.remove(None)
        svcs = dict()
        if svc_ids:
            for ret in sql_executor.execute(f"SELECT id, name FROM third_service WHERE id IN ({', '.join(svc_ids)})"):
                svcs[ret['id']] = ret['name']

        for factor in factors:
            factor[self.CODE] = f'{factor[self.PREFIX]}{factor[self.ID]}'
            factor[self.STATUS] = FACTOR_STATUSES[int(factor[self.STATUS])]
            factor[self.MOD_TIME] = utils.utc2local(factor[self.MOD_TIME], fmt='%Y年%-m月%-d日 %H:%M')
            factor[self.SVC] = svcs.get(factor[self.SVC])
            factor[self.DB_TABLE] = db_table_name
        return factors

    def do_add(self, **kwargs):
        id_prefix_select = self.driver.find_element_by_name('id_prefix')
        id_prefix = kwargs.get(self.PREFIX, random.choice(FACTOR_TYPE_ENUM))
        flag, id_prefix = self.select_single_option(id_prefix_select, target=id_prefix)

        name_input = self.driver.find_element_by_name('name')
        name_input.clear()
        name_input.send_keys(kwargs.get(self.NAME, 'N/A'))

        status_select = self.driver.find_element_by_name('status')
        status = kwargs.get(self.STATUS, random.choice(FACTOR_STATUS_ENUM))
        self.select_single_option(status_select, target=status, attr='value')

        code_var = kwargs.get(self.CODE_VAR, utils.generate_string())
        self.driver.find_element_by_name('code_var').send_keys(code_var)

        db_table_select = self.driver.find_element_by_name('db_table')
        self.select_single_option(db_table_select, target=kwargs.get(self.DB_TABLE), **kwargs)

        if id_prefix == FTYPE_THIRD:
            svc_select = self.driver.find_element_by_name('service')
            self.select_single_option(svc_select, target=kwargs.get(self.SVC), **kwargs)

        factor = {}
        logger.info("开始增加%s: %s", self.mod_name, factor)

    def check_exist(self, cur_objs, **kwargs):
        if self.STATUS in kwargs:
            val = kwargs[self.STATUS]
            kwargs[self.STATUS] = FACTOR_STATUSES.get(val, val)

        if self.SVC in kwargs and kwargs[self.SVC] is None:
            kwargs[self.SVC] = '-'

        factor_code = kwargs.pop(self.CODE) if self.CODE in kwargs else None
        ret, row_no = super(TestFactor, self).check_exist(cur_objs, **kwargs)
        if ret and factor_code:
            idx = self.TABLE_HEADER.index(self.CODE)
            if not re.match(f'{factor_code}[0-9]*', cur_objs[row_no][idx]):
                logger.error("查找失败！因子Code格式错误: %s", factor_code)
                return False, None
        return ret, row_no

    def test(self):
        DB_TABLES = (
            'nwd_applicant_history_v20190821_cld',
            'jsy_risk_info_v20190808_cld',
            'zhima_score_v20180408_cld',
            'jsy_history_v20190808_cld',
            'hyuk_id_pictures_v20180619_cld'
        )

        app_recs = list()
        svc_recs = list()
        db_table_recs = list()

        try:
            app_helper = TestProdApp()
            existed_route_keys = app_helper.get_all_existed_route_keys()
            for _ in range(3):
                app_helper.check_add(app_recs, excludes=existed_route_keys)
                existed_route_keys.add(app_recs[-1][TestProdApp.ROUTE_KEY])

            svc_helper = TestThirdService()
            dummy = [svc_helper.check_add(svc_recs) for _ in range(3)]

            db_table_helper = TestDBTable()
            db_table_helper.all_real_tables = db_table_helper.get_all_real_tables()
            db_table_helper.all_existed_table_names = db_table_helper.get_all_existed_tables()
            kwargs = {TestDBTable.DTYPE: DTYPE_BASIC, TestDBTable.APP: {kvp[TestProdApp.NAME] for kvp in app_recs}}
            db_table_helper.check_add(db_table_recs, includes=DB_TABLES,
                                      excludes=db_table_helper.all_existed_table_names, **kwargs)
            db_table_helper.all_existed_table_names.add(db_table_recs[-1][TestDBTable.TABLE])
            basic_factors = self.generate_factors_from_db_table(db_table_recs[-1])
            self.driver.get(f'{self.url}/?all=')
            self.driver.implicitly_wait(config.IMPLICIT_WAIT)
            self.assertTrue(self.select(*basic_factors)[0])

            kwargs = {TestDBTable.DTYPE: DTYPE_THIRD, TestDBTable.APP: [random.choice(app_recs)[TestProdApp.NAME]],
                      TestDBTable.SVC: {kvp[TestThirdService.NAME] for kvp in svc_recs}}
            db_table_helper.check_add(db_table_recs, includes=DB_TABLES,
                                      excludes=db_table_helper.all_existed_table_names, **kwargs)
            third_factors = self.generate_factors_from_db_table(db_table_recs[-1])
            self.driver.get(f'{self.url}/?all=')
            self.driver.implicitly_wait(config.IMPLICIT_WAIT)
            self.assertTrue(self.select(*third_factors)[0])

            db_table_helper.check_delete(**db_table_recs[0])
            self.driver.get(f'{self.url}/?all=')
            self.driver.implicitly_wait(config.IMPLICIT_WAIT)
            self.assertFalse(self.select(*basic_factors)[0])

            db_table_helper.check_delete(**db_table_recs[1])
            self.driver.get(f'{self.url}/?all=')
            self.driver.implicitly_wait(config.IMPLICIT_WAIT)
            self.assertFalse(self.select(*basic_factors)[0])
        finally:
            if db_table_recs:
                self.driver.get(f'{db_table_helper.url}/?all=')
                self.driver.implicitly_wait(config.IMPLICIT_WAIT)
                db_table_helper.delete(*db_table_recs, strict=False)
            if svc_recs:
                self.driver.get(f'{svc_helper.url}/?all=')
                self.driver.implicitly_wait(config.IMPLICIT_WAIT)
                svc_helper.delete(*svc_recs, strict=False)
            if app_recs:
                self.driver.get(f'{app_helper.url}/?all=')
                self.driver.implicitly_wait(config.IMPLICIT_WAIT)
                app_helper.delete(*app_recs, strict=False)
