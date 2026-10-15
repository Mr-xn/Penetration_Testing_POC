# D-Link DIR-823G 命令注入漏洞分析与复现
> 0431物联卫士实验室
> 来源：https://www.iotsec-zone.com/article/345

# 0x01.漏洞原理
D-Link DIR-823G v1.02 B05及之前的版本存在命令注入漏洞，攻击者可以通过POST的方式往 /HNAP1发送精心构造的请求，执行任意的操作系统命令。

# 0x02.固件环境模拟

使用 firmadyne 对固件进行模拟

![0.png](https://www.iotsec-zone.com/images/MdImg/2bce02369bfeba4faa145cbebe9881f2.png)

模拟成功，进行初始化配置

![1.png](https://www.iotsec-zone.com/images/MdImg/193d297b150b759e969fd02e70b8e3a6.png)

通过 web 成功访问

![2.png](https://www.iotsec-zone.com/images/MdImg/447c37ba5e44fb6e2d349a1731eb0a9b.png)

# 0x03.漏洞分析

从官网上下载 D-Link DIR-823G 的固件，先用 binwalk 查看固件的文件系统格式 squashfs 和 小端架构

![3.png](https://www.iotsec-zone.com/images/MdImg/e5927ad9bb117e99afeae1eaba389091.png)

使用 binwalk 对固件进行提取

![4.png](https://www.iotsec-zone.com/images/MdImg/fa9c28237373b57c56b11870d480e862.png)

得到以下文件

![5.png](https://www.iotsec-zone.com/images/MdImg/12487d077d5cfc0424ba461074c1b173.png)

我们进行分析的就是 squashfs-root 文件夹，里面的是标准的 Linux目录结构， 可以确定这个固件基于 Linux 的。

![6.png](https://www.iotsec-zone.com/images/MdImg/606c317a9ea47515b718c0f512aee0ea.png)

查看 /etc/init.d/rcS 文件，可以确定路由器开启的服务，发现路由器开启了一个 goahead 服务

![7.png](https://www.iotsec-zone.com/images/MdImg/3b75b914dbfa5f9cbc9f2e4939708e9c.png)

GoAhead WebServer，它是一个源码,免费、功能强大、可以在多个平台运行的嵌入式WebServer。

goahead的websUrlHandlerDefine函数允许用户自定义不同url的处理函数

![8.png](https://www.iotsec-zone.com/images/MdImg/9386cfce365d72af60909c29c6ed0aa6.png)

根据不同的请求交给不同的函数进行处理，这些处理函数有统一的参数：

![9.png](https://www.iotsec-zone.com/images/MdImg/52e0ca030febdecac8eac3d4ae7239f8.png)

1    int (*fn)(webs_t wp, char_t *url, char_t *path, char_t *query)

2    wp    Web server connection handle.  
3    url    Request URL.  
4    path  Request path portion of the URL.  
5   query Query string portion of the URL.   

![10.png](https://www.iotsec-zone.com/images/MdImg/0319568a76688282f00af1192f97fbf0.png)

使用 grep 命令查找 goahead 的二进制程序

![11.png](https://www.iotsec-zone.com/images/MdImg/3922ae01fbccc8efb2da24c2e6e40fcd.png)

1.clb@clb-virtual-machine:~/home/clb/1iot/D-Link/D-Link_DIR-823G/dir-823g-v1.0-b05/_DIR823G_V1.0.2B05_20181207.bin.extracted/squashfs-root$ grep -r "goahead"

2.Binary file bin/goahead matches、

3.Binary file bin/timelycheck matches

4.Binary file bin/mtn_upgrade matches

5.etc/init.d/rcS_GW:goahead &

6.etc/init.d/rcS:goahead &    

![12.png](https://www.iotsec-zone.com/images/MdImg/4c9522a52887f14b37cc0839e24d0e41.png)

使用 IDA 分析 /bin/goahead 二进制文件

![13.png](https://www.iotsec-zone.com/images/MdImg/f61455a1899e98214f56b034b9d6774c.png)

通过关键字 HNAP1/goform/cgi-bin快速定位到关键位置。/HNAP1处理函数的逻辑函数位于 0x42383C 跟进函数

![14.png](https://www.iotsec-zone.com/images/MdImg/f74fc981510e20bf793152a08d1b6d4d.png)

这里可以看出如果 url处理的是 /HNAP1的话会成功回显200确定建立连接

继续往下分析，我们会发现一个函数列表

![15.png](https://www.iotsec-zone.com/images/MdImg/530b5b1903a63dd8eb54a5c7ce6b28ed.png)

![16.png](https://www.iotsec-zone.com/images/MdImg/1d634558686297531ee7173f3fe73488.png)

在这里我们可以发现非常熟悉的 Login 那么我们可以知道，HNAP1 根据 url 调用的不同函数来进行匹配这个函数列表，最后进行执行。由于看汇编十分墨迹，这里我使用 ghidra 进行反汇编成类C的语言

![17.png](https://www.iotsec-zone.com/images/MdImg/d26ccc6d5f0f2b25813f83baca2ffe70.png)

这里可以看到FUN_0040b1f4根据不同的 url 调用不同的函数进行处理，这里对应就是上面 IDA 最开始进行分析的图片

这里我们追踪 FUN_0042383c

![18.png](https://www.iotsec-zone.com/images/MdImg/7d5bb25e10759e975e8c502abf00780f.png)

在这里我们发现逻辑和 IDA 分析的第二个图片吻合。往下分析

![19.png](https://www.iotsec-zone.com/images/MdImg/6f53792cb7da5a028b8d5367c8372416.png)

这里 &PTR_s_SetMultipleActions_0058c560对应不同的函数列表

![20.png](https://www.iotsec-zone.com/images/MdImg/99e1037c2f5112b4a378202ac38af26e.png)

这里我们发现如果函数列表中的函数与请求的字符串相同时，会往下执行，并且调用了snprintf通过 echo的方式往 /var/hnaplog中写入了数据 param_7, param_7对应的就是 post传入的数据

![21.png](https://www.iotsec-zone.com/images/MdImg/c52bc0880ac2e2f10a84511d10e0ad6c.png)

post的数据要加上引号，因为echo ‘%s’ > /var/hnaplog中本身带了单引号，如果只是echo 0431lab，相当于

```
echo '`echo 0431lab`' > /var/hnaplog

```
·由于命令由引号括起，会当做字符串处理，不会执行命令
·如果使用' 进行闭合的话，post中的两个引号分别与自带的两个引号组合，反引号没有嵌套在单引号中，会当做命令执行

![22.png](https://www.iotsec-zone.com/images/MdImg/30fd544babad59dced2cb04e2641c93b.png)

这个时候可以通过 post进行提交请求，也可以通过 requests 进行发包

# 0x04.POC

![23.png](https://www.iotsec-zone.com/images/MdImg/ef225517cc52ec1bb906d03b6a4b5f38.png)

执行POC脚本，通过 web 访问 test.txt 文件，发现文件已经写入，证明漏洞漏洞执行成功

![24.png](https://www.iotsec-zone.com/images/MdImg/37f9788eed966c1a0f90738a19fe2c5c.png)

# 0x05.采坑

1.firmadyne 在ubuntu 64位下装不上，在32位才能装上，装了好久 ……

# 0x06. 参考

1.[https://xz.aliyun.com/t/5705#toc-4](https://xz.aliyun.com/t/5705#toc-4)

2.[https://www.heibai.org/post/1395.html](https://www.heibai.org/post/1395.html)

3.[https://github.com/attify/firmware-analysis-toolkit](https://github.com/attify/firmware-analysis-toolkit)
