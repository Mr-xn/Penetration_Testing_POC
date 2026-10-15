# UPnP协议漏洞挖掘与自动化（一）
> Ayaka
> 来源：https://www.iotsec-zone.com/article/208

# 前言
upnp协议是如今万物互联的支撑协议之一，绝大部分智慧家居都会选择开启这项协议，所以它的安全性也是我们必须重视起来的，本篇文章将着重介绍upnp协议以及其漏洞挖掘与自动化

# 协议介绍

upnp协议英文全程为Universal Plug and Play，即通用即插即用，它是由即插即用思想发展而来，何为即插即用？举个例子，当我们想要为自己的电脑增加一个新的设备，如声卡，打印机等，需要由于需要占用**DMA**和**IRQ**等资源，为了避免新添加的设备和已有设备对资源使用上的冲突，我们需要手工的为新添加的硬件设备设置中断和IO端口，但是这需要用户了解中断以及IO相关知识，并且能够自己分配中断地址，这大大提高了增加设备的门槛

## PnP
PnP协议正是为了解决上述的问题而诞生的。有了它以后，计算机可以**自动的为新添加的硬件分配中断和IO端口**，用户无须再做手工跳线，也不需要额外的软件来进行配置。

## UPnP
而UPnP则是将硬件设备扩展到了网络层面，当一个主机加入网络的时候，如果没有这个协议，则需要技术员手动的进行内网ip地址分配，否则将无法与外网进行通信，如果**有很多主机要加入网络，或者一些主机要频繁的退出和加入网络**，人工操作就会变得非常繁琐，并且在当今的万物互联时代，每个人的家中多多少少都会有一些智能家居，但是我们不能要求每个人学会ip地址分配，UPnP正是采用了PnP的思想诞生出来的一款网络协议。

只要路由器支持UPnP协议并开启，那么当我们主机向路由器发出端口映射请求想要访问或被互联网访问的时候，路由器设备就可以**自动的为主机分配端口并进行端口映射**，这样我们的主机就可以当做一个公网主机来使用了

## SSDP
接下来介绍一个UPnP中的核心协议——SSDP，它的英文全程是Simple Service Discover Protocol，即简单服务发现协议，它采用HTTPU和HTTPMU规范，基于UDP端口，工作在应用层，使用一个固定的组播地址239.255.255.250以及固定的端口号1900来监听其他设备

SSDP协议主要有两种消息
* 通知消息：设备和服务使用这类消息声明自己存在
* 查询消息：客户端使用此类消息查询某种类型的设备或者服务

### 通知消息
* 声明自己存在：
当一个设备加入网络的时候，必须用NOTIFY方法发送一个多播传送请求，这种消息并没有回应，而且由于UDP协议并不可信，所以设备要定期发送公告来证明它存在于网络之中，下面是一个典型的**ssdp:alive**消息
```
NOTIFY * HTTP/1.1
HOST: 239.255.255.250:1900
CACHE-CONTROL: max-age = seconds until advertisement expires
LOCATION: URL for UPnP description for root device
NT: search target
NTS: ssdp:alive
USN: advertisement UUID
```

* 声明自己溜了

当一个设备想要从网络上退出的时候，也应当使用NOTIFY方法发送通知，不过即便没有发送，控制点也会因为长时间没有接收到**ssdp:alive**消息而认定设备失效

典型的**ssdp:byebye**消息如下：
```
NOTIFY * HTTP/1.1
HOST: 239.255.255.250:1900NT: search target
NTS: ssdp:byebye
USN: advertisement UUID
```

### 查询消息

当一个客户端接入网络的时候，需要向指定端口使用M-SEARCH方法发送查询消息

典型的ssdp:discover消息如下：
```
M-SEARCH * HTTP/1.1
S:uuid:abcdefgh-7dec-11d0-a765-00a0c91e6bf6
Host:239.255.255.250:1900
Man:"ssdp:discover"ST:ge:fridge
MX:4
```

这种查询消息发出之后，还会有一个响应消息进行回应

典型的响应消息格式：
```
HTTP/1.1 200 OK
Cache-Control: max-age= seconds until advertisement expires
S: uuid:abcdefgh-7dec-11d0-a765-00a0c91e6bf6
Location: URL for UPnP description for root device
Cache-Control: no-cache="Ext",max-age=5000ST:ge:fridge
```

这里我们用wireshark来实践一下，首先打开wireshark,监听WLAN网卡，然后连接手机热点，然后再让另一个设备连接同一个热点，连接结束之后结束监听，然后来找一下UPnP相关的包：

![0.png](https://www.iotsec-zone.com/images/MdImg/a0bae5de367ea6cbf206c772910cd763.png)

![1.png](https://www.iotsec-zone.com/images/MdImg/e0bfbf65557eaf8bcad32b073dd068de.png)

可以看到抓到的包的结构和上面所描述的经典结构完全对应，UPnP协议的介绍就到这里，接下来我们来谈谈UPnP协议的漏洞挖掘工作

# 漏洞挖掘

我们以Netgear公司的R6400路由器的CVE-2020-9373漏洞为例

固件下载链接：[https://www.netgear.com/support/product/R6400.aspx](https://www.netgear.com/support/product/R6400.aspx)

固件版本：Firmware Version 1.0.1.50

解包命令
```bash
binwalk -Me R6400-V1.0.1.50_1.0.35.chk
```

解包之后可以看到文件系统
![2.png](https://www.iotsec-zone.com/images/MdImg/9c6b9b2ac09ad0a8f297f7110d98acf0.png)

一般来说处理UPnP协议的程序逻辑在httpd或者upnpd中，在这个固件的/usr/sbin路径下我们找到了upnpd程序，然后我们将其拖进IDA中分析一下漏洞

根据CVE提供的信息快速定位到漏洞点在sub_22270函数中
![3.png](https://www.iotsec-zone.com/images/MdImg/2b2c9e0c89d72ca7813aa6753386c819.png)

可以看到上来就是一个很明显的strcpy操作，其中src来自于函数参数：
![4.png](https://www.iotsec-zone.com/images/MdImg/8feadf887451f9dd1519920f009a2e32.png)

我们返回上一级函数看看
![5.png](https://www.iotsec-zone.com/images/MdImg/e376eb167ea65b65ead842f23638af61.png)

我们主要关注第一个参数，也就是v78变量，首先通过recvfrom函数获取到v78，然后再末尾补一个0，接下来就传入了漏洞函数中，所以从获取数据到到通过strcpy函数复制进栈中，全程没有对变量长度进行任何检查，这导致了栈溢出发生

```
(gdb) x/20x 0xbed442e8
0xbed442e8:  0x41414141      0x41414141      0x41414141      0x41414141
0xbed442f8:  0x41414141      0x41414141      0x41414141      0x41414141
0xbed44308:  0x41414141      0x41414141      0x41414141      0x41414141
0xbed44318:  0x41414141      0x42004200      0x42004200      0x00000000
```

从栈上数据也可以看出我们成功控制了过量的栈空间，有了栈溢出以后可以通过进一步的构造ROP链完成getshell

再来看一个案列

DIR822路由器的cgibin程序中，处理ssdp协议的函数叫ssdpcgi_main

我们来看看怎么写的

![6.png](https://www.iotsec-zone.com/images/MdImg/2463bd6dc47705addc4ae0178d98efce.png)

首先获取一些必要的环境变量

而后这里的代码有些意思
![7.png](https://www.iotsec-zone.com/images/MdImg/d92cb6d82e9204d47bc49bcc4012b44c.png)

拼接了一个字符串，然后送到一个明显和system有关的函数中去执行，我们进去看看
![8.png](https://www.iotsec-zone.com/images/MdImg/73bea985c232e5b0d1cbeebe28a09dd5.png)

这里从栈上获取了一些变量最终执行了system，通过调试我们可以发现，其中的HTTP_ST我们是可控的，并且也被拼接到了命令字符串中，这也就意味着这里存在一个命令注入，通过精心构造命令，可以实现RCE的效果

可以看出来，UPnP协议不仅是物联网中一个极为重要且基础的协议，而且在实现上各个厂家之间也不尽相同，这就意味着当某个厂家写这部分协议的程序员不注重安全时，就会存在可以利用的漏洞。本篇文章介绍了UPnP协议的由来以及相关漏洞的挖掘，下一篇文章将主要讲一下如何来自动化的针对UPnP协议进行漏洞挖掘
