### 漏洞简介  

|漏洞名称|上报日期|漏洞发现者|产品首页|软件链接|版本|CVE编号|
--------|--------|---------|--------|-------|----|------|
|Couch through 2.0存在路径泄露漏洞|2018-03-04| zzw (zzw@5ecurity.cn)|[https://github.com/CouchCMS/CouchCMS/](https://github.com/CouchCMS/CouchCMS/) | [https://github.com/CouchCMS/CouchCMS/](https://github.com/CouchCMS/CouchCMS/) |2.0 | [CVE-2018-7662](http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2018-7662)|  


#### 漏洞概述  

> Couch through 2.0存在路径泄露漏洞，当访问特定url时系统返回的报错信息中暴露物理路径信息。Couch through是一个在github上开源的系统，漏洞发现者已经将漏洞信息通过[issues](https://github.com/CouchCMS/CouchCMS/issues/46)告知作者。  


### POC实现代码如下：  

------

访问如下页面，报错信息中显示完整物理路径信息。

    Location:
    includes/mysql2i/mysql2i.func.php
    addons/phpmailer/phpmailer.php
