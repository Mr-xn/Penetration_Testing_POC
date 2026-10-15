# TP-Link IP43AN仿真及漏洞测试
> 天问实验室
> 来源：https://www.iotsec-zone.com/article/39

## 前言 

偶然看到了这篇文章，想复现这个漏洞，作者用的是真实设备进行研究，想试试用qemu进行仿真来复现这个漏洞，本篇文章主要是通过qemu-system仿真TP-Link IP43N实现动态调试uhttpd并测试栈溢出漏洞，由于参考文章已经详细介绍了漏洞原理，本篇只讲固件仿真和漏洞测试分析，想了解漏洞细节的话可以看看漏洞参考文章。

## 固件仿真

用binwalk解开固件，查看文件是32bit ARM架构的，查看文件保护发现开了NX

![0.png](https://www.iotsec-zone.com/images/MdImg/9ca936f9970e2b14ef848bf8dd36697f.png) 

将squashfs-root和gdbserver上传到虚拟机中

```
$ chroot squashfs-root sh
```

![1.png](https://www.iotsec-zone.com/images/MdImg/307ba77125016705294a661fc9057896.png)
![2.png](https://www.iotsec-zone.com/images/MdImg/370a80ddb81a3367d328cb16cccdd24f.png)



查看httpd文件用的是uhttpd，存在openwrt_release等文件知道用的是openwrt系统，根据漏洞描述知道dsd是存在漏洞的，直接用dsd启动即可，然后在用命令启动uhttpd

```
# dsd
# uhttpd -p 80 -h /www/ -f
```

![3.png](https://www.iotsec-zone.com/images/MdImg/77ed16e9c5b4823b20030ea799500a12.png) 



发现程序卡住了，无任何字符串显示，也没有错误信息，端口也没有opend将uhttpd拖入IDA当中进行分析，发现少了jffs2_ready文件

![4.png](https://www.iotsec-zone.com/images/MdImg/3356b45bb12b74cb75c8e2d548cec4d1.png)

只要没有这个文件就一直陷入循环当中，创建一个jffs2_ready文件

```
# touch /tmp/jffs2_ready
```

再次尝试启动，发现端口已经开启，可直接访问



![5.png](https://www.iotsec-zone.com/images/MdImg/236b7918a9164b06254af3a6f2c657d3.png) 

 

但测试用户名和密码发现只能用admin进行登陆



![6.png](https://www.iotsec-zone.com/images/MdImg/4b90796b2dc4eb887ebf28fb5d54a270.png) 



但用admin用户进行登录时提示没有admin这个用户





![7.png](https://www.iotsec-zone.com/images/MdImg/44060491e7d0c488bb0b98c28845136e.png) 



查看登陆逻辑，验证username是否是admin，如果是则验证是否用户名在uci配置文件当中



![8.png](https://www.iotsec-zone.com/images/MdImg/2062c98c4596b0c53d47eb8390f853c9.png) 

![9.png](https://www.iotsec-zone.com/images/MdImg/c507f7556be4230b114533f9c29b4d2f.png)

这时候要对配置文件进行构造，根据网上查到的消息uci配置文件的用法，然后在/etc/config下创建一个user_management文件，然后写上username和password，就可以实现登录了， 

![10.png](https://www.iotsec-zone.com/images/MdImg/7e80189be862251d7842dceb7b740159.png) 

登陆的目的只是获取一个token，但登陆之后发现系统sessions(/tmp/luci-sessions)没有token
需要手动添加token（token值随意），就可以进入dsd了

![11.png](https://www.iotsec-zone.com/images/MdImg/a8a9e1086a3eda6bd4abf71ddbd6ba64.png) 

##漏洞测试分析
我们知道这是个栈溢出函数，那需要查看的是这个漏洞能带给我们怎样的效果，如何劫持
我们可以看到最后溢出变量是在v17这里，刚好是最底部的变量位置，我们能够控v17+0x10的地址
![12.png](https://www.iotsec-zone.com/images/MdImg/2b93efaa0e0f8af29b7dc58bd435624e.png)

![13.png](https://www.iotsec-zone.com/images/MdImg/55995037fcda3342ba8f465b078e9d51.png)

在返回地址处点下断点，运行exp

![14.png](https://www.iotsec-zone.com/images/MdImg/196d19ebcd55ecf2abb41e32f9c74e60.png) 



![15.png](https://www.iotsec-zone.com/images/MdImg/5a4790047ccbc5496ff2a75c2b80accb.png) 



可以看到我们能控制r4-r10以及pc寄存器，但由于有nx保护，导致无法返回到栈上执行shellcode，只能达到拒绝服务的效果
##总结
文章主要涉及的点还是如何仿真httpd和dsd进行调试和测试，其实这个仿真花了我挺长时间的，遇到一些坑如何通过逆向解决，还有一些特有的函数（uci)如何去构造配置文件都是一些可以学习的点。就目前来说路由器漏洞主要还是在web中，只要web启动起来再仔细地逆向一下说不定就会有很多漏洞，同时通过仿真模拟的话就可以自己构造一些Fuzz来进行测试和优化。
由于目前主要研究车联网漏洞，在物联网研究的时间比较少， 最近想尝试模拟仿真TBox，所以找了几个项目练练手，才做了这个分享，希望能给大家带来一点收获，如果有问题或建议欢迎留言。



漏洞参考:[漏洞参考]( [https://wzt.ac.cn/2020/05/23/IPC43AN/](https://wzt.ac.cn/2020/05/23/IPC43AN/)
)
固件下载地址：[固件下载地址](https://service.tp-link.com.cn/detail_download_7631.html)## 前言 

偶然看到了这篇文章，想复现这个漏洞，作者用的是真实设备进行研究，想试试用qemu进行仿真来复现这个漏洞，本篇文章主要是通过qemu-system仿真TP-Link IP43N实现动态调试uhttpd并测试栈溢出漏洞，由于参考文章已经详细介绍了漏洞原理，本篇只讲固件仿真和漏洞测试分析，想了解漏洞细节的话可以看看漏洞参考文章。

## 固件仿真

用binwalk解开固件，查看文件是32bit ARM架构的，查看文件保护发现开了NX

![16.png](https://www.iotsec-zone.com/images/MdImg/9ca936f9970e2b14ef848bf8dd36697f.png) 

将squashfs-root和gdbserver上传到虚拟机中

```
$ chroot squashfs-root sh
```

![17.png](https://www.iotsec-zone.com/images/MdImg/307ba77125016705294a661fc9057896.png)
![18.png](https://www.iotsec-zone.com/images/MdImg/370a80ddb81a3367d328cb16cccdd24f.png)



查看httpd文件用的是uhttpd，存在openwrt_release等文件知道用的是openwrt系统，根据漏洞描述知道dsd是存在漏洞的，直接用dsd启动即可，然后在用命令启动uhttpd

```
# dsd
# uhttpd -p 80 -h /www/ -f
```

![19.png](https://www.iotsec-zone.com/images/MdImg/77ed16e9c5b4823b20030ea799500a12.png) 



发现程序卡住了，无任何字符串显示，也没有错误信息，端口也没有opend将uhttpd拖入IDA当中进行分析，发现少了jffs2_ready文件

![20.png](https://www.iotsec-zone.com/images/MdImg/3356b45bb12b74cb75c8e2d548cec4d1.png)

只要没有这个文件就一直陷入循环当中，创建一个jffs2_ready文件

```
# touch /tmp/jffs2_ready
```

再次尝试启动，发现端口已经开启，可直接访问



![21.png](https://www.iotsec-zone.com/images/MdImg/236b7918a9164b06254af3a6f2c657d3.png) 

 

但测试用户名和密码发现只能用admin进行登陆



![22.png](https://www.iotsec-zone.com/images/MdImg/4b90796b2dc4eb887ebf28fb5d54a270.png) 



但用admin用户进行登录时提示没有admin这个用户





![23.png](https://www.iotsec-zone.com/images/MdImg/44060491e7d0c488bb0b98c28845136e.png) 



查看登陆逻辑，验证username是否是admin，如果是则验证是否用户名在uci配置文件当中



![24.png](https://www.iotsec-zone.com/images/MdImg/2062c98c4596b0c53d47eb8390f853c9.png) 

![25.png](https://www.iotsec-zone.com/images/MdImg/c507f7556be4230b114533f9c29b4d2f.png)

这时候要对配置文件进行构造，根据网上查到的消息uci配置文件的用法，然后在/etc/config下创建一个user_management文件，然后写上username和password，就可以实现登录了， 

![26.png](https://www.iotsec-zone.com/images/MdImg/7e80189be862251d7842dceb7b740159.png) 

登陆的目的只是获取一个token，但登陆之后发现系统sessions(/tmp/luci-sessions)没有token
需要手动添加token（token值随意），就可以进入dsd了

![27.png](https://www.iotsec-zone.com/images/MdImg/a8a9e1086a3eda6bd4abf71ddbd6ba64.png) 

##漏洞测试分析
我们知道这是个栈溢出函数，那需要查看的是这个漏洞能带给我们怎样的效果，如何劫持
我们可以看到最后溢出变量是在v17这里，刚好是最底部的变量位置，我们能够控v17+0x10的地址
![28.png](https://www.iotsec-zone.com/images/MdImg/2b93efaa0e0f8af29b7dc58bd435624e.png)

![29.png](https://www.iotsec-zone.com/images/MdImg/55995037fcda3342ba8f465b078e9d51.png)

在返回地址处点下断点，运行exp

![30.png](https://www.iotsec-zone.com/images/MdImg/196d19ebcd55ecf2abb41e32f9c74e60.png) 



![31.png](https://www.iotsec-zone.com/images/MdImg/5a4790047ccbc5496ff2a75c2b80accb.png) 



可以看到我们能控制r4-r10以及pc寄存器，但由于有nx保护，导致无法返回到栈上执行shellcode，只能达到拒绝服务的效果
##总结
文章主要涉及的点还是如何仿真httpd和dsd进行调试和测试，其实这个仿真花了我挺长时间的，遇到一些坑如何通过逆向解决，还有一些特有的函数（uci)如何去构造配置文件都是一些可以学习的点。就目前来说路由器漏洞主要还是在web中，只要web启动起来再仔细地逆向一下说不定就会有很多漏洞，同时通过仿真模拟的话就可以自己构造一些Fuzz来进行测试和优化。
由于目前主要研究车联网漏洞，在物联网研究的时间比较少， 最近想尝试模拟仿真TBox，所以找了几个项目练练手，才做了这个分享，希望能给大家带来一点收获，如果有问题或建议欢迎留言。



漏洞参考:[漏洞参考]( [https://wzt.ac.cn/2020/05/23/IPC43AN/](https://wzt.ac.cn/2020/05/23/IPC43AN/)
)
固件下载地址：[固件下载地址](https://service.tp-link.com.cn/detail_download_7631.html)
