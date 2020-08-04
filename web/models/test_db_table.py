#! /usr/bin/env python3
# -*- coding:utf-8 -*-

import random
from copy import deepcopy

from . import config
from ... import utils
from ...consts import DB_TABLE_TYPE_ENUM, DTYPE_BASIC
from ...logger import logger
from ...sql_executor import sql_executor
from .base_test import BaseTestCase


class TestDBTable(BaseTestCase):
    uri = config.URI_DB_TABLE

    DTYPE = 'Data type'
    CTX_KEY = 'Context key'
    TABLE = 'Db table name'
    APP = 'Application'
    SVC = 'Service'
    FIELDS = (DTYPE, CTX_KEY, TABLE, APP, SVC)
    IMPLICIT_FIELDS = (APP, SVC)

    @classmethod
    def get_all_real_tables(cls):
        sql = "SELECT db_table_name FROM model_schema_v20190715_rule"
        return set(map(lambda ret: ret[0], sql_executor.execute(sql)))

    def get_all_existed_tables(self):
        all_db_tables = self.get_all_existed_values().values()
        if all_db_tables:
            if not self.TABLE_HEADER:
                self.init_table_list_header()
            idx = self.TABLE_HEADER.index(self.TABLE)
            return {val[idx] for val in all_db_tables}
        else:
            return set()

    @classmethod
    def setUpClass(cls) -> None:
        super(TestDBTable, cls).setUpClass()
        cls.all_real_tables = cls.get_all_real_tables()

    def setUp(self) -> None:
        self.all_existed_table_names = self.get_all_existed_tables()

    def do_add(self, **kwargs):
        dtype = kwargs.get(self.DTYPE, random.choice(DB_TABLE_TYPE_ENUM))
        table_name = kwargs.get(self.TABLE)
        if not table_name:
            table_choices = deepcopy(self.all_real_tables)
            if 'includes' in kwargs:
                if all([tbl in table_choices for tbl in kwargs['includes']]):
                    table_choices = kwargs.pop('includes')
                else:
                    logger.error("以下数据库表不存在：%s", ' '.join(set(kwargs['includes']).difference(table_choices)))
                    return
            if 'excludes' in kwargs:
                table_choices = set(table_choices).difference(kwargs.pop('excludes'))
            table_name = random.choice(tuple(table_choices))

        ctx_key = kwargs.get(self.CTX_KEY, utils.get_db_table(table_name).replace('DBTable', 'Key'))
        apps = kwargs.get(self.APP)
        svcs = kwargs.get(self.SVC)

        self.driver.find_element_by_name('data_type').send_keys(dtype)
        self.driver.find_element_by_name('context_key').send_keys(ctx_key)
        self.driver.find_element_by_name('db_table_name').send_keys(table_name)
        app_select = self.driver.find_element_by_name('application')
        flag, apps = self.select_multiple_options(app_select, targets=apps, **kwargs)
        if dtype == DTYPE_BASIC:
            svcs = {None}
        else:
            svc_select = self.driver.find_element_by_name('service')
            flag, svcs = self.select_multiple_options(svc_select, targets=svcs, **kwargs)

        db_table = {self.DTYPE: dtype, self.TABLE: table_name, self.CTX_KEY: ctx_key, self.APP: apps, self.SVC: svcs}
        logger.info("开始增加%s: %s", self.mod_name, db_table)
        return db_table

    def test(self):
        db_tables = list()
        try:
            with self.assertRaises(AssertionError):
                self.check_add(db_tables, **{self.TABLE: f'TestDBTable{utils.generate_string()}'})

            app, rno = self.check_add(db_tables, excludes=self.all_existed_table_names)
            self.all_existed_table_names.add(app[self.TABLE])

            app2, rno2 = self.check_add(db_tables, excludes=self.all_existed_table_names)
            self.all_existed_table_names.add(app2[self.TABLE])

            with self.assertRaises(AssertionError):
                self.check_add(db_tables, includes=self.all_existed_table_names)

            self.check_delete(**app)
            self.check_add(db_tables, **app)
        finally:
            self.delete(*db_tables, strict=False)
