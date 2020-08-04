#! /usr/bin/env python3
# -*- coding:utf-8 -*-

from . import config
from ... import utils
from ...logger import logger
from .base_test import BaseTestCase


class TestProdApp(BaseTestCase):
    uri = config.URI_PROD_APP

    NAME = 'Name'
    ROUTE_KEY = 'Route key'
    FIELDS = (NAME, ROUTE_KEY)

    def get_all_existed_route_keys(self):
        all_prod_apps = self.get_all_existed_values().values()
        if all_prod_apps:
            if not self.TABLE_HEADER:
                self.init_table_list_header()
            idx = self.TABLE_HEADER.index(self.ROUTE_KEY)
            return {val[idx] for val in all_prod_apps}
        else:
            return set()

    def setUp(self) -> None:
        self.all_existed_route_keys = self.get_all_existed_route_keys()

    def do_add(self, **kwargs):
        app_name = kwargs.get(self.NAME, f'TestProdApp{utils.generate_string()}')
        route_key = kwargs.get(self.ROUTE_KEY, None)

        self.driver.find_element_by_name('name').send_keys(app_name)
        route_key_select = self.driver.find_element_by_name('route_key')
        flag, route_key = self.select_single_option(route_key_select, target=route_key, attr='value', **kwargs)

        app = {self.NAME: app_name, self.ROUTE_KEY: route_key}
        logger.info("开始增加%s: %s", self.mod_name, app)
        return app

    def test(self):
        prod_apps = list()
        try:
            app, rno = self.check_add(prod_apps, excludes=self.all_existed_route_keys)
            self.all_existed_route_keys.add(app[self.ROUTE_KEY])

            app2, rno2 = self.check_add(prod_apps, excludes=self.all_existed_route_keys)
            self.all_existed_route_keys.add(app2[self.ROUTE_KEY])

            with self.assertRaises(AssertionError):
                self.check_add(prod_apps, includes=self.all_existed_route_keys)

            self.check_delete(**app)
            self.check_add(prod_apps, **app)
        finally:
            self.delete(*prod_apps, strict=False)
