# 路由器TP-Link WR740后门漏洞
> 0431物联卫士实验室
> 来源：https://www.iotsec-zone.com/article/103

## 0x00 描述

> 测试环境：Ubuntu 18.04
>
> 固件版本：wr740nv1_en_3_12_4_up(100910).bin
>
> 产品厂商：TP-Link
>
> 厂商地址：[https://www.tp-link.com.cn/](https://www.tp-link.com.cn/)

## 0x01 固件分析

将固件下载到Ubuntu中，使用命令binwalk进行解包，拿到固件的文件系统

![0.png](https://www.iotsec-zone.com/images/MdImg/6d8a83f7d416bf87f9670417fc6797d2.png)

```text
这里介绍一个常用的小工具 firmwalk.sh，工具下载链接 https：//github.com/craigz28/firmwalker

1. 它将搜索固件文件系统，以获取与敏感信息相关的东西，如：etc/shadow and etc/passwd

2. 列出 etc/ssl等目录

3. 搜索相关的文件，如. pem,. crt, 等

4. 搜索配置文件

5. 查找脚本文件

6. 搜索其他.bin 文件

7. 查找诸如管理员，密码，远程等关键字符

8. 搜索IoT设备上使用的通用网络服务器

9. 搜索常见的二进制文件，如 ssh，tftp，dropbear等

10. 搜索网址，电子邮件地址和IP地址
```

接下来我们使用工具firmwalker对提取的固件进行扫描

![1.png](https://www.iotsec-zone.com/images/MdImg/91136888c0bc0f95a51d1422f1139f1a.png)

通过上面的信息可以得到很多关键信息，这里我们着重查看图片上的几处关键信息

- 可以看到对于路由器的相关URL应该是/web/userRpm/xxxxx.htm这种，那么我们就可以合理的猜测，这应该是web服务相关的命令规范
- 含有passwd和pwd相关的文件中，可以看到嵌入式web服务httpd，部分htm文件以及其他配置文件

可以看到它把固件的敏感信息都列举出来了，先不着急对文件进行分析，接下来我们看一下启动项有没有启动什么后门服务，如telnet服务等

一般启动项文件都位于etc目录下面，我们到etc目录下面进行查看

![2.png](https://www.iotsec-zone.com/images/MdImg/7f7c3c73d71ffb3313f82fd48dc798c6.png)

根据嵌入式Linux常用启动项位置可以确定启动项文件就位于rc.d这个目录里面，打开此目录对里面的文件进行分析

![3.png](https://www.iotsec-zone.com/images/MdImg/ea67a50cff80178a6a77c85b6abbeb3e.png)

可以看到他的HTTP服务都在httpd这个文件中，启动项没有其他的异常行为

那我们通过find命令查找一下这个文件的所在位置

![4.png](https://www.iotsec-zone.com/images/MdImg/5d3742b5c4bce1b961e7fb831a76c67b.png)

可以看到文件在/usr/bin目录下面我们将文件移动到IDA中进行分析

## 0x02.IDA逆向分析

根据firmwalker收集到的跟passwd先关的文件就包含httpd二进制应用，这里我们直接在字符串窗口搜索passwd字符串

![5.png](https://www.iotsec-zone.com/images/MdImg/2c88baf14c01eeba2e3498a635f345bb.png)

可以看到和passwd先关的字符串还有很多，那么我们可以逐个进行追踪

![6.png](https://www.iotsec-zone.com/images/MdImg/1b697aa032bf725c87e3ce76aa242431.png)

在这里可以看到passwd被调用的位置，直接双击箭头向上追踪

![7.png](https://www.iotsec-zone.com/images/MdImg/a0755454a13f842022b84c9d57b55a41.png)

简单查看便可以看到很多硬编码的敏感字符串，使用F5生成伪C代码

![8.png](https://www.iotsec-zone.com/images/MdImg/800a04387970f17ae47c99e545fac24f.png)

可以看到在进行用户名和密码的比对，并且用户名和密码为osteam和5up，那么可以猜测这里应该是和某种认证相关

通过httpGetEnv函数的第二个参数名称cmd，可以猜测这应该是执行命令的地方

接着可以看到write函数调用了pty来模拟命令的执行

（知识扩充：伪终端(pseudo terminal，有时也被称为 pty)是指伪终端 master 和伪终端 slave 这一对字符设备。其中的 slave 对应 /dev/pts/ 目录下的一个文件，而 master 则在内存中标识为一个文件描述符(fd)。伪终端由终端模拟器提供，终端模拟器是一个运行在用户态的应用程序。）

根据当前函数DebugResultRpmHtm，追踪调用的位置

![9.png](https://www.iotsec-zone.com/images/MdImg/2bc0e4fd60aa29da97b710dcb003dba4.png)

这里可以看到使用httpRpmConfAdd函数进行url和执行函数的定义，这里看到当前函数为httpDebugInit，似乎是进行Debug调试的，接着可以看到有一个linux_cmdline.html的页面

![10.png](https://www.iotsec-zone.com/images/MdImg/ea6fa3f394e7d3e826ef06cdfc5e04f7.png)

一看到这个页面可以执行系统命令，可以确定linux_cmdline.html似乎是一个后门，但是想要执行命令还需要用户名和密码，根据上面的分析我们可以确定用户名为osteam和密码5up的账户为后门登录的账号和密码 

## 0x03 漏洞验证

> 工具下载地址：[https://github.com/pr0v3rbs/FirmAE](https://github.com/pr0v3rbs/FirmAE)

接下来我们去验证上面我们的猜想，接下来我们就对固件进行模拟

这里推荐使用工具FirmAE，为什么推荐呢？这个工具使用高度集成化的操作，只需要使用一条命令即可对固件进行模拟，比起使用qemu来模拟固件方便快捷了很多

![11.png](https://www.iotsec-zone.com/images/MdImg/90bafd571ab4e9efaff83c47c9fab8bc.png)

可以看到固件模拟成功，浏览器进行访问[http://192.168.1.1/userRpmNatDebugRpm26525557/linux_cmdline.html](http://192.168.1.1/userRpmNatDebugRpm26525557/linux_cmdline.html)

![12.png](https://www.iotsec-zone.com/images/MdImg/034ecc9afef2f24207866f9de37863d4.png)

可以看到需要授权，使用默认的账号密码进行登录

![13.png](https://www.iotsec-zone.com/images/MdImg/6c682284bfcd068588445b47643938b4.png)

输入用户名，密码以及要执行的命令，可以看到成功执行并返回了相应的结果

## 0x04.总结

通过上面的分析，可以看到信息收集对我们漏洞分析和漏洞挖掘有很大的帮助，通过敏感的信息，我们能更快的定位到漏洞产生的位置，并且我们掌握的信息越多，漏洞分析和漏洞挖掘的速度和效率越高。
