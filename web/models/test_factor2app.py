#! /usr/bin/env python3
# -*- coding:utf-8 -*-

import random

from . import config
from .base_test import BaseTestCase
from .test_db_table import DTYPE_BASIC, DTYPE_THIRD, TestDBTable
from .test_factor import FTYPE_BASIC_PREFIX, FTYPE_THIRD, TYPE_BASIC, TestFactor
from .test_prod_app import TestProdApp
from .test_third_service import TestThirdService


class TestFactor2App(BaseTestCase):
    uri = config.URI_FACTOR_APP

    APP = 'Application'
    FACTOR = 'Factor'
    FACTOR_CODE = 'Factor code'
    FACTOR_NAME = 'Factor name'
    FACTOR_TYPE = 'Factor type'
    FACTOR_STAT = 'Factor status'
    FACTOR_MOD_TIME = 'Factor modify time'
    SVC = 'Service name'
    DB_TABLE = 'Db table name'

    FIELDS = (APP, FACTOR, FACTOR_CODE, FACTOR_NAME, FACTOR_TYPE, FACTOR_STAT, FACTOR_MOD_TIME, SVC, DB_TABLE)

    def generate_factor2app_from_db_table(self, db_table):
        factor_hepler = TestFactor()
        factors = factor_hepler.query_factors_from_db_table(db_table)
        factor2apps = list()
        for app in db_table[TestDBTable.APP]:
            for svc in db_table[TestDBTable.SVC]:
                for factor in factors:
                    factor2app = {
                        self.APP: app,
                        self.FACTOR: factor[TestFactor.NAME],
                        self.FACTOR_CODE: factor[TestFactor.CODE],
                        self.FACTOR_NAME: factor[TestFactor.NAME],
                        self.FACTOR_TYPE: TYPE_BASIC if FTYPE_BASIC_PREFIX == factor[TestFactor.PREFIX] else FTYPE_THIRD,
                        self.FACTOR_STAT: factor[TestFactor.STATUS],
                        self.FACTOR_MOD_TIME: factor[TestFactor.MOD_TIME],
                        self.SVC: svc,
                        self.DB_TABLE: db_table[TestDBTable.TABLE]
                    }
                    factor2apps.append(factor2app)
        return factor2apps

    def check_exist(self, cur_objs, **kwargs):
        if self.SVC in kwargs and kwargs[self.SVC] is None:
            kwargs[self.SVC] = ''
        return super(TestFactor2App, self).check_exist(cur_objs, **kwargs)

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

            factor_helper = TestFactor()
            basic_factors = factor_helper.generate_factors_from_db_table(db_table_recs[-1])
            self.driver.get(f'{factor_helper.url}/?all=')
            self.driver.implicitly_wait(config.IMPLICIT_WAIT)
            self.assertTrue(factor_helper.select(*basic_factors)[0])

            basic_factor2apps = self.generate_factor2app_from_db_table(db_table_recs[-1])
            self.driver.get(f'{self.url}/?all=')
            self.driver.implicitly_wait(config.IMPLICIT_WAIT)
            self.assertTrue(self.select(*basic_factor2apps)[0])

            kwargs = {TestDBTable.DTYPE: DTYPE_THIRD, TestDBTable.APP: [random.choice(app_recs)[TestProdApp.NAME]],
                      TestDBTable.SVC: {kvp[TestThirdService.NAME] for kvp in svc_recs}}
            db_table_helper.check_add(db_table_recs, includes=DB_TABLES,
                                      excludes=db_table_helper.all_existed_table_names, **kwargs)
            third_factors = factor_helper.generate_factors_from_db_table(db_table_recs[-1])
            self.driver.get(f'{factor_helper.url}/?all=')
            self.driver.implicitly_wait(config.IMPLICIT_WAIT)
            self.assertTrue(factor_helper.select(*third_factors)[0])

            third_factor2apps = self.generate_factor2app_from_db_table(db_table_recs[0])
            self.driver.get(f'{self.url}/?all=')
            self.driver.implicitly_wait(config.IMPLICIT_WAIT)
            self.assertTrue(self.select(*third_factor2apps)[0])

            db_table_helper.check_delete(**db_table_recs[0])
            self.driver.get(f'{factor_helper.url}/?all=')
            self.driver.implicitly_wait(config.IMPLICIT_WAIT)
            self.assertFalse(factor_helper.select(*basic_factors)[0])
            self.driver.get(f'{self.url}/?all=')
            self.driver.implicitly_wait(config.IMPLICIT_WAIT)
            self.assertFalse(self.select(*basic_factor2apps)[0])

            db_table_helper.check_delete(**db_table_recs[1])
            self.driver.get(f'{factor_helper.url}/?all=')
            self.driver.implicitly_wait(config.IMPLICIT_WAIT)
            self.assertFalse(factor_helper.select(*basic_factors)[0])
            self.driver.get(f'{self.url}/?all=')
            self.driver.implicitly_wait(config.IMPLICIT_WAIT)
            self.assertFalse(self.select(*third_factor2apps)[0])
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
