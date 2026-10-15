#  tendaCP3摄像头分析-2
> p1yang
> 来源：https://www.iotsec-zone.com/article/206

上次的坑来填了

之前没有系统学习过网络编程，花了一周时间把tinyhttpd的源代码阅读理解了一下，并且仿照用python写了一个简易的httpd，可以看我另一篇文章

## noodles服务分析

通过分析发现noodles监听了1300端口

### 启动

> sudo chroot . ./qemu-arm-static ./usr/bin/noodles

![0.png](https://www.iotsec-zone.com/images/MdImg/3d13f83cfe6fc440d757d5e279be172e.png)

可以使用nmap来查看是否监听1300

![1.png](https://www.iotsec-zone.com/images/MdImg/9ffa4e9cbb0ab6e8f83e1b39e8552e0f.png)

可以看到1300端口已开放，并且noodles也对nmap有反应了

### 静态分析

对于程序的静态分析，可以从main函数来正向递进分析，也可以从一些字符串来分析，又或者从一些关键函数

这里通过nmap扫描时noodles的打印来查找

通过交叉引用发现在FUN_00011878函数中存在相关信息。

创建并监听1300端口

![2.png](https://www.iotsec-zone.com/images/MdImg/fafe6205e772cb0248a7079d95f987fd.png)

![3.png](https://www.iotsec-zone.com/images/MdImg/d4510ddcc1d8c8611cb4d2d6a5bf826e.png)

等待用户连接

![4.png](https://www.iotsec-zone.com/images/MdImg/b14cb73da819b6e31bc1fcc85db22a5d.png)

获取client传进来的内容

![5.png](https://www.iotsec-zone.com/images/MdImg/443c386e4012d61e5a6cd8676c495802.png)

![6.png](https://www.iotsec-zone.com/images/MdImg/a403e2cc936dfa70d5b694d7832c8063.png)

主要内容处理在下面相似的内容处

![7.png](https://www.iotsec-zone.com/images/MdImg/d33dd12a940bf476d3208cfe57ac7950.png)

1300端口大概做了这些事情

参数有一下几种

> UPGRADE
>
> BURNMAC
>
> ELFEXEC
>
> SYSTEM
>
> SYSTEMEX
>
> DOWNLOAD
>
> UPLOAD
>
> FLASHDUMP
>
> BURNSN
>
> READSN
>
> WRITEENV
>
> READENV

#### fun_00014f90()函数

![8.png](https://www.iotsec-zone.com/images/MdImg/d8cba7ea688dcfedb596148127b5e3bf.png)

三个参数分别为从client传入的内容，字符串，0

![9.png](https://www.iotsec-zone.com/images/MdImg/a968701ecde25e1d7d67954faa9c8240.png)

这里是xml参数处理。

### 成果

这里出了一个代码注入和一个设备重启

#### 设备重启

设备重启是利用了代码问题，更像是设计时不严谨导致的

当标签中含有upgrade时，会运行到FUN_000146f4函数，执行完毕后必然会执行到FUN_00016b90函数来使设备重启。

![10.png](https://www.iotsec-zone.com/images/MdImg/193dfd8faf75211d2db5365f20bfeba3.png)

只需要运行到此处，脚本会使设备重启

![11.png](https://www.iotsec-zone.com/images/MdImg/0089b4e6d4a50f60b421d7053ab280af.png)

#### 代码注入

这里更像一个后门，直接在 FUN_000140b4函数中发现，如果`<system></system>`中的参数不是iwlist便会直接使用system执行

![12.png](https://www.iotsec-zone.com/images/MdImg/7ed2e5ab79dd0343214d9260aa217a8a.png) 

这里就不贴poc了，诸位可自行测试
