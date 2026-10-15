# DCME-720命令注入漏洞
> 麟
> 来源：https://www.iotsec-zone.com/article/517

## 0.前言

八月中旬，在对DCME-720 路由器进行安全分析时，发现其固件在处理特定输入时存在命令注入漏洞

该漏洞源于程序在接收并解析用户输入时缺乏严格的过滤与转义，攻击者可以通过构造恶意请求在系统中注入并执行任意命令，从而造成设备功能异常，甚至在某

些情况下完全获取设备的控制权

经过验证与测试，确认该漏洞风险较高，利用门槛低，可能被远程攻击者利用，对设备及其所在网络的安全性影响严重

我整理了一份详细的技术报告，内容涵盖漏洞成因、复现步骤及修复建议，并已通过正规渠道提交给厂商及 CVE 分配机构

目前，该漏洞已被正式收录，编号为[CVE-2025-9387](https://nvd.nist.gov/vuln/detail/CVE-2025-9387)

## 1.漏洞概述

DCME-720多核出口网关采用多核高性能处理器，结合专用ASIC交换芯片，针对大容量用户数、多流量、多业务种类的业务需求而推出的新一代高性能互联网出口网关

其web管理后台存在命令执行漏洞，攻击者可以利用该系列漏洞在设备上执行任意代码以及控制设备

固件下载地址：[https://www.dcnetworks.com.cn/ruanjian.html?title=dcme-720](https://www.dcnetworks.com.cn/ruanjian.html?title=dcme-720)

## 2.漏洞细节

还是用binwalk进行一个提取

![0.png](https://www.iotsec-zone.com/api/image/v2/20250917/dcuxtux7p3ctsayk9e.png)

这里解包出来不像之前我挖的漏洞那样只有一个提取文件，而是两个，关键是这两个文件里面的内容都是一样的

那这是因为`1697860` 和 `FF56AC` 应该是 binwalk 在固件里识别出的两个文件系统分区，大概率是 SquashFS / CramFS / JFFS2 之类

binwalk 默认会把每个检测到的分区都解出来，不管它们是不是重复，`1697860` 这个名字通常代表它是从固件偏移 `0x1697860` 的位置提取出来的，

`FF56AC` 则可能是从偏移 `0xFF56AC` 提取的或者用签名 hash 命名

所以虽然内容一样，但它们在固件中的存储位置不同

基本上应该是主系统和备份系统 rootfs，企业级网关常见的设计，两个分区内容一样，用于升级回滚，然后固件打包时可能重复写入一份 rootfs 到不同偏移，保

证启动时找到

我们可以做个验证，使用md5sum对其哈希值对比，如果是一致的话，说明那就是重复镜像

![1.png](https://www.iotsec-zone.com/api/image/v2/20250917/dcuxu1vu40gqdlmrbd.png)

果然一模一样，总结起来就是DCME-720 固件之所以解包后出现两个一模一样的文件系统目录，是因为固件里本身包含了两份 rootfs 镜像，主系统和备份系统，

binwalk 都提取了出来。这和之前分析的消费级路由器，比如说什么Tenda，TP-Link之类的，通常只有一份 rootfs不同，属于企业级设备常见的冗余设计

回到正题，首先需要强调一点，DCME-720 这类企业级安全网关，大多数配置，比如说什么防火墙规则、NAT、审计、用户管理等，都是通过Web 管理界面完成

所以 Web 目录 `/usr/local/www/` 下的 PHP 脚本就是设备逻辑的主要实现，而里面都是PHP文件

![2.png](https://www.iotsec-zone.com/api/image/v2/20250917/dcuxums3rwb6hiodwo.png)

而在经过代码审计之后，发现function下的 audit/newstatistics/ip_block.php 文件存在命令注入漏洞

从路径上看，这是日志审计或流量统计的功能，而其中的 `ip_block.php` 很可能用于处理IP 封禁/解封请求，也就是说，当管理员在 Web 界面操作封锁某个 IP

时，后台就会调用这个 PHP 文件

所以这个PHP文件就属于那种一审就能够审出有漏洞的高危文件，因为毕竟要去操作IP 封禁功能，而封禁必然涉及系统层命令iptables/ipset/firewall-cmd

从它的代码上来看，本质是调用 `fpstat_client` 来修改防火墙状态，而里面又有`system` ，`exec`等关于系统调用的函数

也就是说，功能点决定了潜在风险点，凡是会调用系统命令的功能，都是重点排查目标

![3.png](https://www.iotsec-zone.com/api/image/v2/20250917/dcuxuub89i8rkusjyn.png)

ip和time都是用户输入的内容，然后没有经过任何的转义，就直接就拼接到`exec`这个危险函数里面去了，这明显就是个典型的命令注入漏洞

而switch是条件判断语句，但是也是用户输入的内容，所以也是属于我们可控制的参数，那就很好解决了

一言以蔽之，只要我们的请求路径是`/function/audit/newstatistics/ip_block.php?action=save&switch=1&ip=;[拼接命令]`; 就可以完成一次命令注入了

说个题外话，有没有发现这个路由器漏洞点不像以前其他路由器那样，源代码需要通过ida等逆向工具进行一个反编译后得到的

DCME-720漏洞和之前分析的 Tenda、TP-Link 这类消费级路由器漏洞确实不一样，差异主要在设备架构和实现方式上：

消费级路由器一般来说，Web 服务通常由厂商自研或移植的轻量级 `httpd`，而后台逻辑核心功能大多写在 `.cgi` 可执行文件里，本质是 ELF 二进制程序，C 写的

所以必须逆向二进制工具，IDA/Ghidra才能理解输入处理逻辑

而像DCME-720这类企业级网关，Web 服务是运行在更完整的软件栈上，有可能是 Apache、nginx ，而后台逻辑主要用 PHP 脚本 写在 `/usr/local/www/` 下，

调用底层命令或接口实现功能，基于如此分析方式，就只要解包 rootfs，就能直接做代码审计，不必费劲逆向

总结起来就是，消费级路由器漏洞 → 逆向分析为主，企业级网关漏洞 → 源码审计为主

## 3.漏洞证明

这里就有另外一个问题了，刚刚我们说到企业路由器其实是比消费级路由器好分析多的，但是仿真就完全反过来的，企业路由器难仿真多了

反正这个我并没有像之前那样完全仿真起来，所谓的完全仿真就是说用qemu或其他仿真工具，把固件里的内核 + rootfs都启动起来，启动 init 进程、守护进程，

比如说httpd，并且设备功能，路由、NAT、防火墙、VPN等等之类的都能用，就像真机一样

而DCME-720这个我解决不了它这个完全仿真的问题

只能把 `/usr/local/www/`，也就是Web 界面源码提取出来，然后在自己的电脑上搭了一个PHP Web 环境，然后用 **ngrok** 把本地 Web 端口映射到公网

![4.png](https://www.iotsec-zone.com/api/image/v2/20250917/dcuxv0z8c31vhqwtrn.png)

payload就很简单了，`ip/function/audit/newstatistics/ip_block.php?action=save&switch=1&ip=;echo 123 > 1.txt;`

创建1.txt文件并写入数字，然后我们去访问1.txt就会发现已经成功注入了

![5.png](https://www.iotsec-zone.com/api/image/v2/20250917/dcuxvay6cqk5jkatxg.png)
