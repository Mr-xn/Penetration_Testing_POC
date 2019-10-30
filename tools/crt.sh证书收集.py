# -*- coding: utf-8 -*-
# @Time    : 2019-10-08 22:51
# @Author  : Patrilic
# @FileName: SSL_subdomain.py
# @Software: PyCharm

import requests
import re

TIME_OUT = 60


def get_SSL(domain):
    domains = []
    url = 'https://crt.sh/?q=%25.{}'.format(domain)
    response = requests.get(url, timeout=TIME_OUT)
    # print(response.text)
    ssl = re.findall("<TD>(.*?).{}</TD>".format(domain), response.text)
    for i in ssl:
        i += '.' + domain
        domains.append(i)
    print(domains)


if __name__ == '__main__':
    get_SSL("baidu.com")