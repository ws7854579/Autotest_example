#! /usr/bin/env python3
# -*- coding:utf-8 -*-

from ..config import *

SERVER = f'http://api.{DOMAIN}'

API_ARRANGE = f'{SERVER}/admin/arrange'

URI_PROD_APP = 'productapplication'
URI_FACTOR = 'factor'
URI_FACTOR_APP = 'factorapplicationrelation'
URI_DB_TABLE = 'databasetable'
URI_THIRD_SVC = 'thirdservice'
URI_USER = 'userinfo'

URIS = {
    URI_PROD_APP: '产品应用',
    URI_FACTOR: '因子',
    URI_FACTOR_APP: '因子-产品应用关系',
    URI_DB_TABLE: '数据库表',
    URI_THIRD_SVC: '三方服务',
    URI_USER: '用户'
}
URI_ENUM = tuple(URIS.keys())

ERROR_ELEMENT_CLASSES = ('errorlist', 'alert')
