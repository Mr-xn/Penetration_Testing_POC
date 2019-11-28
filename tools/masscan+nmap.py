#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# __author__: www.t00ls.net-rabbittb
# modified by mrxn
# you must needed install python-nmap first with pip3 or pip
import os
import time
import json
import nmap
import sys

PORT_list = [
    80, 8080, 8089, 23, 21, 5001, 7001 - 7010, 8888, 6666, 1080, 27017, 6379,
    1433, 3306, 1352, 1521, 11211, 9200, 9300, 9090, 8069, 5900, 443, 5432,
    5632, 4848, 2181
]

ports = "80,8080,8089,23,21,5001,7001-7010,8888,6666,1080,27017,6379,1433,3306,1352,1521,11211,9200,9300,9090,8069,5900,443,5432,5632,4848,2181"


def masScan(ip_file, ports):
    ip_file = ip_file
    json_name = str(time.time()) + "_masscan.log"
    payload = "masscan -iL {0} -p {2} -oJ {1} --rate 3000".format(
        ip_file, json_name, ports)
    print(payload)
    os.system(payload)
    return masscan_parse(json_name)


def masscan_parse(log_name):
    res_dic = {}
    with open(log_name) as f:
        for line in f:
            if line.startswith('{'):
                temp = json.loads(line[:-2])
                if temp['ip'] in res_dic.keys():
                    res_dic[temp['ip']].append(str(temp['ports'][0]['port']))
                else:
                    res_dic[temp['ip']] = [str(temp['ports'][0]['port'])]
    return res_dic


def callback_result(host, scan_result):
    if host in scan_result['scan'].keys(
    ) and 'tcp' in scan_result['scan'][host]:
        for x in scan_result['scan'][host]['tcp']:
            res = {
                'host': host,
                'port': x,
                'service': scan_result['scan'][host]['tcp'][x]['name'],
                'product': scan_result['scan'][host]['tcp'][x]['product'],
                'version': scan_result['scan'][host]['tcp'][x]['version']
            }
            print(res)
            return res


def nmapScan(target_list):
    scanner = nmap.PortScannerAsync()

    for target in target_list:
        scanner.scan(target,
                     arguments='-sV -PS -p' + ','.join(target_list[target]),
                     callback=callback_result)

    while scanner.still_scanning():
        scanner.wait(2)


if __name__ == "__main__":
    ports = "80,8080,8089,23,21,5001,7001-7010,8888,6666,1080,27017,6379,1433,3306,1352,1521,11211,9200,9300,9090,8069,5900,443,5432,5632,4848,2181"
    start = time.time()
    # res = masScan("1.txt", ports)
    if len(sys.argv) == 2:
        res = masScan("{ipfile}".format(ipfile=sys.argv[1]), ports)
        nmapScan(res)
    elif len(sys.argv) == 1:
        print('please input iplist file')
    else:
        print('error')
    print(time.time() - start)
