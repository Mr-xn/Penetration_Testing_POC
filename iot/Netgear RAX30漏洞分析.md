# Netgear RAX30漏洞分析
> 博智非攻研究院
> 来源：https://www.iotsec-zone.com/article/336

Pwn2Own Toronto 2022正在举行，本文对Netgear RAX30路由器的2个在比赛前几天被修复的漏洞进行分析，当时的NETGEAR固件版本是1.0.7.78，可以在官网上直接下载：[https://www.netgear.com/support/product/RAX30#download](https://www.netgear.com/support/product/RAX30#download)。

### LAN漏洞分析

下载固件，使用binwalk命令提取所有文件，得到了一个非常标准的Linux内核和文件系统。首先通过列出目录来识别路由器中的文件和服务，一个二进制文件立即引起了我们的注意：

![0.png](https://www.iotsec-zone.com/images/MdImg/60edfc4d2dcca1551c5e8e9fd115cb47.png)

我们还可以看到，这个二进制文件是默认启动的：

![1.png](https://www.iotsec-zone.com/images/MdImg/e3ce655ac865958d2da38acb99692868.png)

使用Strings命令，可以发现如下内容：

![2.png](https://www.iotsec-zone.com/images/MdImg/730826b91e9626b67a4c8746d8e70f49.png)

基于这个片段，我们就可以想象到设备的工作流程。此二进制文件插入NFLOG iptables用以执行回调。“User-Agent”字符串引导我们需要搜索的内容，pudil -i %s "%s" 行非常有趣。下面是User-Agent部分处理的反编译：

![3.png](https://www.iotsec-zone.com/images/MdImg/e1e58bbc06a1c41bb5afc67279387fbe.png)

NFLOG目标由输入（INPUT）和FORWARD串所触发，Webadmin在br0网卡的tcp 80端口监听，我们可以直接在默认IP地址上发送数据，将任意数据放入User-Agent中用来触发代码注入：

![4.png](https://www.iotsec-zone.com/images/MdImg/f1400947ddc60bf53dce79a84234bc95.png)

发送此类请求将使路由器重新启动，由此产生拒绝服务，这对局域网来说是一个快速的攻击。另外，我们可以在“User-Agent”字符串中注入255个字符，这足以执行接管路由器所需的任何操作，例如下载全功能BusyBox和启动反向shell。

### WAN漏洞分析

DHCP服务器被设置为Netgear Wan接口分配IP，利用LAN漏洞获取的shell，我们首先从列举出路由器系统运行的进行和对应的网络端口号，可看到ssh tpc 22和telnet TCP 23端口均开启，23端口的扫描结果如下：

![5.png](https://www.iotsec-zone.com/images/MdImg/fd0f676f9378a0c3b7377012513672ee.png)

可从WAN端访问TCP 23端口，这是一个巨大的缺陷。虽然有些ip6tables规则可以用来定义限制访问，但它们仅应用于br0接口（LAN接口），如果提供了公网IPv6地址，则仅用于Wan接口。如果只有一个链接Wan接口上正在使用本地地址，规则为启用，因此同一网段上除NETGEAR之外的任何人都可以查询IPv6链路本地地址以连接到服务，包括WebAdmin、Telnet、SSH、SOAP_serverd等。
基于Netgear路由器中以前的漏洞，我们可以在/etc/passwd文件中找到硬编码的帐户:

![6.png](https://www.iotsec-zone.com/images/MdImg/e8e7f16fc4590ac0576b558aafe3cd52.png)

“support”账户的密码可使用John the Ripper工具迅速破解，另外，请注意，“support”帐户的UID为0。基于“support”帐户通过telnet登录到路由器，获得一个受限shell连接：

![7.png](https://www.iotsec-zone.com/images/MdImg/fcb445e259b81fe51e233d51d949542a.png)

可以通过多种方式来摆脱这种受限制shell，使用$（..）调用subshell，使用'；'调用链式命令，甚至调用'sh'（隐藏命令）。

![8.png](https://www.iotsec-zone.com/images/MdImg/55e424154b918e52af719e80d6ca89b1.png)

可以知道Wan接口的MAC地址（例如通过ping），就可以推断出IPv6链路本地地址（RFC 4291 第2.5.6节+附录A），启动telnet命令，连接并退出shell。

### 补丁

Pwn2Own竞赛的规则很明确：在抽签之前，所有设备都是最新的。抽签仪式于12月2日举行。11月30日，NETGEAR公司推出了1.0.9.90版本的修补程序。这两个漏洞都在此更新中被修复。Puhttsniff文件中不再调用system()命令，取而代之的是execve()，因此也不再有命令注入了。

![9.png](https://www.iotsec-zone.com/images/MdImg/abeaf5034226c95fffcedcd83421a1f6.png)

IPv6防火墙仍然为Wan接口设置，因此无法再通过本地链路访问IPv6服务。
