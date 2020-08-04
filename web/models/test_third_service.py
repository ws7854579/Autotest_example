#! /usr/bin/env python3
# -*- coding:utf-8 -*-

import random

from . import config
from ... import utils
from ...logger import logger
from .base_test import BaseTestCase


class TestThirdService(BaseTestCase):
    uri = config.URI_THIRD_SVC

    NAME = 'Name'
    INDEX = 'Idx'
    FIELDS = (NAME, INDEX)

    def do_add(self, **kwargs):
        svc_name = kwargs.get(self.NAME, f'TestThirdSvc{utils.generate_string()}')
        idx = kwargs.get(self.INDEX, random.randrange(9999))
        svc = {self.NAME: svc_name, self.INDEX: idx}

        self.driver.find_element_by_name('name').send_keys(svc_name)
        self.driver.find_element_by_name('idx').send_keys(idx)
        logger.info("开始增加%s: %s", self.mod_name, svc)
        return svc

    def test(self):
        svc_records = list()
        try:
            svc, rno = self.check_add(svc_records)

            self.check_add(svc_records)

            with self.assertRaises(AssertionError):
                self.check_add(svc_records, **{self.NAME: svc[self.NAME]})

            self.check_add(svc_records, **{self.INDEX: svc[self.INDEX]})

            self.check_delete(**svc)
            self.check_add(svc_records, **svc)

        finally:
            self.delete(*svc_records, strict=False)
