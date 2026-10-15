# Mikrotik SMB 缓冲区溢出漏洞复现
> Ayaka
> 来源：https://www.iotsec-zone.com/article/277

最近需要去研究一下MikroTik，所以来复现一下它的经典漏洞。
# 漏洞简介
漏洞出现在MikroTik路由器所使用的MikroTik公司自研的一款操作系统routerOS。

MikroTik是一家拉脱维亚公司，成立于1996年，旨在开发路由器和无线ISP系统。MikroTik现在为世界上大多数国家的互联网连接提供硬件和软件。RouterOS是MikroTik基于Linux v3.3.5内核的独立操作系统。

在MikroTik RouterOS SMB服务中发现缓冲区溢出。访问该服务的远程攻击者可以利用此漏洞并在系统上执行代码。溢出发生在身份验证之前，因此未经身份验证的远程攻击者可能会利用它进行攻击

然后简单了解一下SMB服务是个什么东西(来自百度百科）:

SMB 一种客户机/服务器、请求/响应协议。通过 SMB 协议，客户端应用程序可以在各种网络环境下读、写服务器上的文件，以及对服务器程序提出服务请求。此外通过 SMB 协议，应用程序可以访问远程服务器端的文件、以及打印机、邮件槽（mailslot）、命名管道（named pipe）等资源。

在 TCP/IP 环境下，客户机通过 NetBIOS over TCP/IP（或 NetBEUI/TCP 或 SPX/IPX）连接服务器。一旦连接成功，客户机可发送 SMB 命令到服务器上，从而客户机能够访问共享目录、打开文件、读写文件，以及一切在文件系统上能做的所有事情。

# 环境搭建

首先到官网下载好vmdk文件，然后新建一个虚拟机用来装routerOS操作系统

首先新建虚拟机然后选择稍后安装操作系统：
![0.png](https://www.iotsec-zone.com/images/MdImg/07061d0ffb4a78fcbe6c365f33a009fa.png)

选择内核的时候记得使用3.x
![1.png](https://www.iotsec-zone.com/images/MdImg/204b37c7a2508aea3d4e65503228f3b3.png)
然后随便起个名字，这里我直接用mikrotik了
![2.png](https://www.iotsec-zone.com/images/MdImg/868a07ec318a45fb01cefe0171b5dca6.png)

处理器和内核都指定1个就够了，内存也不用太大，routerOS毕竟大部分时候运行在小路由器上，所以对硬件要求不高，网络类型的话使用NET就可以。

磁盘选择这个：
![3.png](https://www.iotsec-zone.com/images/MdImg/3a1055f44055c345991a0f1bbc948a81.png)

使用现有磁盘：
![4.png](https://www.iotsec-zone.com/images/MdImg/a7e95939b51c960adf1a91270cff6fc8.png)
然后将之前下载好的指定版本的磁盘文件选中
![5.png](https://www.iotsec-zone.com/images/MdImg/6b5271ca0f5360c71290aa821528306a.png)

最后打开虚拟机，输入用户名admin,密码是空，即可进入到一个shell界面

在shell界面输入：
```bash
ip smb set enabled=yes
ip address print
```
第一行是把smb服务启动，第二行是查看一下ip

接下来是开启telnet，由于现在虚拟机里的shell并不是linux的shell，并不是很方便。使用github上写好的项目

项目地址：[https://github.com/0ki/mikrotik-tools](https://github.com/0ki/mikrotik-tools)

运行脚本可以一把梭开启telnet
![6.png](https://www.iotsec-zone.com/images/MdImg/35a0791c115a945426cfafb5d07eeae7.png)

成功开启后会有如下提示
![7.png](https://www.iotsec-zone.com/images/MdImg/a4aba6a3a46957cf3589c2b5155ee0ad.png)

我们使用devel登录一下telnet试试：

![8.png](https://www.iotsec-zone.com/images/MdImg/d6ea6ee85d0372f712fe0369a96a0e32.png)

可以看到已经能够在刚才搭建好的OS上执行linux命令了。最后用netstat检查一下是否开启了smb服务：
![9.png](https://www.iotsec-zone.com/images/MdImg/74f5af73e2f376ffd963f12e6003d81f.png)
也可以用nmap确认一下：
![10.png](https://www.iotsec-zone.com/images/MdImg/09c1baccdad9fdbf2dde539197f402c1.png)
这里的139端口下的netbios-ssn指的就是smb服务

至此整个环境的搭建就基本结束了，下面开始漏洞复现

# 漏洞复现

首先要做的肯定是找到smb这个服务是靠哪个二进制程序开启的，有了telnet是真的方便了很多：
![11.png](https://www.iotsec-zone.com/images/MdImg/2664bc732eed2264aa98b3e43d1e964e.png)
这里基本可以确定了smb服务应该就是/nova/bin/smb开启的，所以需要将这个文件拿出来进行逆向分析，问题又来了，该怎么拿呢，我们并没有往routerOS那个虚拟机中安装vmtools。

其中一个方法是利用ftp服务，但是多少有点麻烦，既然有linux命令了，不如直接nc你说是吧，在自己的环境里执行：
```bash
nc -lp 1234 > out
```
然后在telnet里执行：
```bash
nc -w 3 192.168.58.135 1234 < /nova/bin/smb
```
可以看到smb已经成功被我们搞出来了，非常简单方便:
![12.png](https://www.iotsec-zone.com/images/MdImg/b92d9c6bb7b62d2e76c097a820f6afca.png)

漏洞主要出现在sub_806B11C函数中，这个函数是开启一个新的smb连接，这也意味着我们无须验证就可以直接触发，不需要进行登录绕过：
![13.png](https://www.iotsec-zone.com/images/MdImg/78c201b1fc81624354b90158ff180284.png)

v41是栈上的缓冲区，第二个参数暂时还不清楚，点进来分析一下：
![14.png](https://www.iotsec-zone.com/images/MdImg/fb47ce69dfa01c24803af9de492958ec.png)

在while循环中不断执行复制，复制长度位v2，这里并没有对v2做出限制，意味着我们输入的是\xff，它就允许复制0xff个字节进去，但是栈上并没有这么大的空间，于是导致了栈溢出，这里我更倾向这个洞是fuzz出来的，也有可能是我对这个系统并不熟悉的缘故。

想要到达这段代码，就需要有一定的smb服务的基础，可以参考这个：
[https://blog.csdn.net/vevenlcf/article/details/17716053](https://blog.csdn.net/vevenlcf/article/details/17716053)

定义如下：

 
UCHAR Type; // Type of the packet
UCHAR Flags; // Flags
USHORT Length; // Count of data bytes (netbios header not included)

 
“Flags”域的值总是被置为0。

 
“Type”域有几种可能的选择：

 
0x81 对应一个NETBIOS会话请求。这个代码在客户端发送它的NETBIOS名字到服务器是使用。

 
0x82 对应一个NETBIOS会话应答。这个代码在服务器向客户端批准NETBIOS会话时使用。

 
0x00 对应一个会话消息。这个代码总是在SMB会话中被使用。

 
“Length”域包含了数据字节的长度(NETBIOS头部没有被包含在内)。

通过cyclic来确认返回地址的偏移是99，这意味着我们可以精准的控制返回地址了，接下来寻找gadget，由于smb程序并没有链接libc，所以没有system函数可以直接使用，但是可以用syscall
![15.png](https://www.iotsec-zone.com/images/MdImg/a43f054f6053b717316ec39b0dff9aaa.png)

有了syscall,接下来需要控制eax,ebx,ecx,edx
![16.png](https://www.iotsec-zone.com/images/MdImg/f6c3d71802533d057d579ff64a9eb245.png)

![17.png](https://www.iotsec-zone.com/images/MdImg/f44f96e31d9b56b874996340ca6c0eb4.png)

通过如图所示的两个gadget,可以完美控制syscall的所需参数，由于执行write或者exec这类系统调用，我们不容易直观的看到效果，所以直接选择调用reboot来尝试让虚拟机重启，要注意一件事情，reboot需要两个magic number，并且还有一个cmd参数要填：
![18.png](https://www.iotsec-zone.com/images/MdImg/20fa52f46753eeefd46337151d4b858b.png)

所以这里如果想让机器自动重启，需要让rdx等于0x1234567
让rbx和ecx分别等于对应的magic number，即：
```
eax=88

ebx=0xfee1dead

ecx=672274793

edx=0x1234567
```

poc就留给读者自行完成吧，最后的效果如下
![19.png](https://www.iotsec-zone.com/images/MdImg/99053f349ddb6cd222e97416d960351a.png)
