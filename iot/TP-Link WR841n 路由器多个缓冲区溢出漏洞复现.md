# TP-Link WR841n 路由器多个缓冲区溢出漏洞复现
> 大中午啊
> 来源：https://www.iotsec-zone.com/article/221

## 0x01 前言

最近看到了关于TP-Link 一个古老的路由器 WR841n 的漏洞披露文章，都是关于缓冲区溢出的漏洞，虽然设备老，但是漏洞的发现过程都挺有学习价值的。在平时对设备的漏洞挖掘过程中，可能会比较倾向于对设备的工作流程进行分析，然后逆向一些关键的函数和代码，在这些代码和函数中，找到可能存在的漏洞函数，拿缓冲区溢出漏洞来说，会分析strcpy、sprintf 、strcat、gets 诸如此类的函数，查看局部变量在拷贝字符串的时候是否对字符串的长度进行限制。但是比较少的对通过指针或者地址的拷贝字符串的方式进行分析，通过指针拷贝字符串也经常的会出现缓冲区溢出漏洞。接下来我将WR841n 设备中存在的三个缓冲区溢出的漏洞进行分析，记录，整理。所以这是一篇学习记录的文章。漏洞的披露链接在参考章节。

## 0x02 http流程分析

固件版本:  [3.16.9 Build 150310](https://www.tp-link.com/vn/support/download/tl-wr841n/v10/#Firmware)

首先通过main 函数调用httpd() 和 httpBasicRpmInit() 函数对设备的http服务进行初始化，这个函数会将设备的一些功能进行初始化，并且路由器的相关http 功能处理的函数在这个函数中进行配置，初始化。
![0.png](https://www.iotsec-zone.com/images/MdImg/0ee5ae5f196425958d32e2ebb23ec368.png)
在httpd() 函数初始化的时候，会创建httpServerCreate()函数，来用以创建http Server
![1.png](https://www.iotsec-zone.com/images/MdImg/b74f2f0f6bb14602ed5fdb7bf030ef13.png)
在经过 httpServerCreate() -->sub_4F5CD0 --> httpDispatcher() 之后。会经过httpDispatcher()函数，这个函数会处理为各个不同的url 调用httpGenListFuncGet()函数进行函数注册绑定，以保证传入的request 请求数据包中的url 有对应的注册函数进行处理传入的对应数据包。
![2.png](https://www.iotsec-zone.com/images/MdImg/f853b1cb75f7d425d790a5373f4222a3.png)
最终httpRpmConfAdd  函数会获取 request_url 对应的函数指针，然后调用函数。
![3.png](https://www.iotsec-zone.com/images/MdImg/74f5b5449480974887ddc08a397915b9.png)
具体的使用方式如httpPingIframeInit()函数。
![4.png](https://www.iotsec-zone.com/images/MdImg/fafce3f1910c6ca93832fdbf1baaa4d9.png)
## 0x03 第一个漏洞分析CVE-2020-8423

接下来分析WR841n 中的三个漏洞

首先来看一下CVE-2020-8423，vulnerability function stringModify()，这个函数是于转义一些字符的。当我们输入字符中有 "/" ，">"，"\\\\"，"<" ，' \" ' 时，会在当前字符前面添加一个"\\" ，这一块的处理代码在line23~ line 44 。如果当前的字符是 "/" , 那么字line 30 会*a1 指针指向的值是 "\\"，然后在line 33 ，a1 的指针就会加1 指向下一个内存地址。接着到达line 42，这一行会给a1 现在的地址指向的值复制为 当前的字符 "/"，因为现在的a1 指针的地址是之前已经加1 了，所以内存中的字符应该是 "\/"。

接下来在line 53 还会获取当前字符下一个字符，然后判断这个字符是否是 "\n" 并且还要是 "\r" ，否则就会在内存中添加 "\<br>"，然后指针往后移4个地址。感觉这一段很有问题，因为一个字符没办法同时等于两种不同的字符，所以最终肯定会走到这里。QAQ

因此只需要传入的字符是"/\n" 那么就会变成 "\/\<br>"，比原先多了四个字节。然后a1的大小设置是512个字节，因此当经过这个函数之后，如果我们传入512个这种字符串，就会比原先多2048个字节，从而造成buffer overflow 。

stringModify()

该函数在遇到字符\、/、<、>"时添加字符\，或者如果下一个字符不是\n和\r，则添加\<br>，当缓冲区满时进程将停止。
![5.png](https://www.iotsec-zone.com/images/MdImg/d48d9706e572e4a4f023b9304c332e7e.png)
![6.png](https://www.iotsec-zone.com/images/MdImg/da7664c0614b9285f571ca016279fed2.png)
现在我们要考虑是的stringModify() 那里会被调用并可以传入字符串，查看交叉引用可以看到writepageParamSet()函数在调用。
![7.png](https://www.iotsec-zone.com/images/MdImg/261307fbc278f19e64f9e0419216e1e0.png)
然后继续查看writepageParamSet() 函数的交叉引用，可以看到在sub_45FA94() line 308 中传入v53 变量中的字符串。
![8.png](https://www.iotsec-zone.com/images/MdImg/a86a5dc86518a9473af6eed2eca237dd.png)
在这个函数的line 240 会获取ssid 的值。然后将值复制给v53。
![9.png](https://www.iotsec-zone.com/images/MdImg/17bb6c3da6653bb0a2ce551649d1a2ec.png)
## 0x04 第二个漏洞分析  CVE-2022-30024

这个产生的原因 isAddrDispose()在处理ping_addr 的时候对ping value 长度的限制设置并没有起到效果，这种问题在缓冲区溢出中是很常见的，我们可以看到在 line28 行会对 ping value 的调用strlen 进行计算长度。这个长度的大小在于我们输入value 的大小而确定的，比如我输入一千多个字符，那么这个len_ping_addr 长度就是一千。

这就造成了在line 35 中并没有起到对输入字符长度起到任何的作用。在line 32~line 40 中是将ping value 的字符逐个传递给v23局部变量，而v23 定义的数据大小仅仅为52个字节 。因此会造成又一个buffer overflow 
![10.png](https://www.iotsec-zone.com/images/MdImg/8e704f9376e43b2f15a7a705bb109aaf.png)
这个函数会在sub_44A530() 中进行处理。

![11.png](https://www.iotsec-zone.com/images/MdImg/99d43b3e844fea65075acc230ba90b19.png)
当请求的url中是“ /userRpm/PingIframeRpm.htm ” 时，httpGetEnv() 会获取ping_addr 的value 。
![12.png](https://www.iotsec-zone.com/images/MdImg/9dcd3ad1b2fe5148474c381912acf6c4.png)
然后回调用 isAddrDispose() 函数来处理 ping_addr 的value，也就是我们前面分析过程了。
![13.png](https://www.iotsec-zone.com/images/MdImg/90fa5d771d11c038fcca0510c0cbf347.png)

## 0x05 第三个漏洞分析 CVE-2022-24355

前面我们知道了httpRpmConfAdd 函数会根据请求数据包的url 中的路径来确定调用相应的注册函数，在httpd初始化的时候，会把httpRpmFS() 函数和 url 的字符串"/loginFs/","/fs/" 进行绑定并注册函数。接下来分析httpRmpFs函数是如何处理请求URL 中带有"/loginFs/" 的数据包。 
![14.png](https://www.iotsec-zone.com/images/MdImg/de2132e60f2548daa8523d660b759120.png)
首先会函数的形参a1 是获取到的请求数据包，然后回获取到数据包的header 信息以及数据包的中的url，然后和/tmp/或者/web/文件路径进行拼接，判断是否是这两个文件夹中的文件，在判断的过程中，还做了过滤“..” ，以免请求的文件url 存在路径穿越的漏洞。
![15.png](https://www.iotsec-zone.com/images/MdImg/fc564b5faa22becdca2bec7428dac7b9.png)
接下来程序会走到sub_4EE210函数中。
![16.png](https://www.iotsec-zone.com/images/MdImg/05c7d28a5a71fe3041db0f0d3024aaeb.png)
我们来到函数sub_4EE2210() 中，这个本来是为了提取文件后缀的。但是由于首先会判断v2 的值是为空。我们知道v2 的值是 /tmp/loginfs/passwd ，接下来在line 21 获取文件路径的指针，然后一直往指针在往低地址移动，匹配是否有 “.” 。找到了之后就会把 "." 字符的下一个字符地址赋给v4。其实由于file_path 中是passwd ，因此没有 " . " 字符，因此会继续移动指针，会导致指针移动到 header 中 referer 中的 url中的 "."。因此会获取referer 中“.” 的下一个指针地址给v4。并且在line28 的循环中将后面的每个字符进行转成大写字母，然后写入到file_extension 从而造成了 buffer overflow。
![17.png](https://www.iotsec-zone.com/images/MdImg/56bb147a6ad519ad77a16ce7905f8b0b.png)
## 0x06 疑似漏洞

在分析前面的漏洞的时候，看到获取ssid 的值，这一段代码中，strncpy 函数会造成缓冲区溢出的漏洞，因为在v22 将ssid 的值复制给v53 的过程中，复制的字符串的长度是由v21 进行设置的，而v21 字符的数量恰好是我们可以输入的。因此复制给v53的字符串我们可以自己控制，当输入的字符串长度超过了局部变量v53 分配的内存大小的收，就会造成缓冲区溢出的漏洞，和前面CVE-2022-30024 中ping_addr 是一样的。由于手头上没有这一款设备，因此如果有设备的师傅，希望能帮忙验证一下。

![18.png](https://www.iotsec-zone.com/images/MdImg/827fe435ba593d61386dd31a3b30afd0.png)
## 0x07 总结

这三个漏洞的成因都是通过在指针拷贝和处理字符串的时候，并没有考虑内存的问题，比如CVE-2020-8423 漏洞在转义字符的之后，并没有对转义后的字符串进行长度的限制。在CVE-2022-3024漏洞中，ping_addr的长度限制没有固定，反而是由传入的参数进行计算。

## 0x08 参考

[https://blog.viettelcybersecurity.com/1day-to-0day-on-tl-link-tl-wr841n/](https://blog.viettelcybersecurity.com/1day-to-0day-on-tl-link-tl-wr841n/)

[https://blog.viettelcybersecurity.com/tp-link-tl-wr940n-httpd-httprpmfs-stack-based-buffer-overflow-remote-code-execution-vulnerability/](https://blog.viettelcybersecurity.com/tp-link-tl-wr940n-httpd-httprpmfs-stack-based-buffer-overflow-remote-code-execution-vulnerability/)

C program 通过指针复制字符串

[https://cloud.tencent.com/developer/article/1687616](https://cloud.tencent.com/developer/article/1687616)
