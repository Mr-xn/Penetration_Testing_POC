# Netgear DGN1000 命令执行
> 0431物联卫士实验室
> 来源：https://www.iotsec-zone.com/article/95

## 0x00. 前言

相信各位关注我们的小伙伴们，之前肯定已经阅读过了我们的一篇叫DIR600绝对路径遍历的文章，那么今天我们来了解另外一种漏洞类型：命令执行

## 0x01.固件模拟

> - 型号：Netgear DGN1000
> - 版本：DGN1000WW_V1.1.00.45
> - 官网：[https://www.netgear.com/](https://www.netgear.com/)
> - 测试环境：Ubuntu 18.04

使用FirmAE对固件进行模拟，执行的命令如下

```shell
sudo ./run.sh -r 1000dng ./firmwares/DGN1000WW_V1.1.00.45.img 
[sudo] password for iot: 
[*] ./firmwares/DGN1000WW_V1.1.00.45.img emulation start!!!
[*] extract done!!!
[*] get architecture done!!!
[*] ./firmwares/DGN1000WW_V1.1.00.45.img already succeed emulation!!!

[IID] 2
[MODE] run
[+] Network reachable on 192.168.0.1!
[+] Web service on 192.168.0.1
Creating TAP device tap2_0...
Set 'tap2_0' persistent and owned by uid 0
Bringing up TAP device...
Starting emulation of firmware... 192.168.0.1 true true .040925734 .040925734
```

当看到两个true的时候，可以证明固件的Network和Web都已经起来了，使用默认的admin:password登录即可

![0.png](https://www.iotsec-zone.com/images/MdImg/b497b52f1e026d7b2fe97b8e8d1938c5.png)

## 0x02. 命令执行漏洞

对固件使用binwalk进行解压

```bash
binwalk -Me ./DGN1000WW_V1.1.00.45.img
```

对固件进行解压，进入到系统目录下面

![1.png](https://www.iotsec-zone.com/images/MdImg/ae3b1a69575156057c6422e0171bd29c.png)

先对各个目录的文件进行检查，查看web端相关代码，可以看到很多请求都与setup.cgi有关

![2.png](https://www.iotsec-zone.com/images/MdImg/46ed9cf9568adfde13aae402182211ff.png)

那我们先去看看与setup.cgi相关的的文件

```bash
grep -r 'setup.cgi'
```

![3.png](https://www.iotsec-zone.com/images/MdImg/99e70a2f77e0df646b3e278184629c41.png)

可以看到好多前端的页面都引用了这个文件，都是通过GET，POST请求到这个文件，最后找到这个文件的源文件是在/usr/bin目录下面，接下来打开IDA对这个文件进行一下分析

![4.png](https://www.iotsec-zone.com/images/MdImg/2ab0997ef22ce7339f2a4b257e4f2162.png)

![5.png](https://www.iotsec-zone.com/images/MdImg/eea762673a32eb0592d3763239be1536.png)

可以看到setup.cgi对应的Action表，查看左侧的函数表，可以发现一个syscmd的函数

![6.png](https://www.iotsec-zone.com/images/MdImg/f6ec4155cac6f1706bff2c007ba30acd.png)

syscmd函数将cmd获取的值通过snprintf格式化到变量v7中，并且对传入的数据没有进行任何过滤，存在命令执行漏洞

通过grep检索与syscmd相关的文件

![7.png](https://www.iotsec-zone.com/images/MdImg/c9d4f6d261cf33e4f38625d92459bbe9.png)

好家伙还有一个syscmd.htm页面，我们直接访问一下看看

![8.png](https://www.iotsec-zone.com/images/MdImg/ec3eb12f9a0a1907aa5eba753b131f94.png)

是一个需要授权的命令执行页面，可以看到发送命令访问的目标url为`/setup.cgi?todo=syscmd&cmd="+$("#cmdbox").val()+"&curpath="+$("#curpath").val()`，传递的键值是todo，cmd和curpath，逆向分析setup.cgi如下：

![9.png](https://www.iotsec-zone.com/images/MdImg/35fdcff54ff7438790300575bdeca052.png)

![10.png](https://www.iotsec-zone.com/images/MdImg/1039ce52641c84764c61f7e3a5bdb6cc.png)

看到在主函数中使用todo去指定要执行的函数，既然发现了有可以执行命令的函数，那么咱们可以构建一下setug.cgi?todo=syscmd 是不是就可以去执行命令了

接下来直接浏览器访问[http://192.168.0.1/setup.cgi?todo=syscmd](http://192.168.0.1/setup.cgi?todo=syscmd)

![11.png](https://www.iotsec-zone.com/images/MdImg/b475e2b68fda6d704d570b856f6d354d.png)

发现需要授权，咱们先不管，刚刚在IDA中发现使用cmd去接受的参数，我们去给他赋值再看看

![12.png](https://www.iotsec-zone.com/images/MdImg/1865412ef055dadf2fca75e2ed25a95c.png)

一样还是需要授权，那我们就输入一下账号密码看看能不能执行

![13.png](https://www.iotsec-zone.com/images/MdImg/7b621b88dff887d72404da49dece863f.png)

可以看到命令被成功执行

## 0x03.未授权漏洞

上面已经讲解了授权下访问`http://192.168.0.1/setup.cgi?to=syscmd&cmd=cat+/www/.htpasswd`，成功读取用户名和密码存储的文件，那么如果存在未授权漏洞，则可以未授权执行任意命令

搜索和http相关的服务，可以看到耳熟能详的的mini_httpd，mini_httpd是一个小型 HTTP 服务器。它的性能不是很好，但对于小型的路由器已经足够使用了

![14.png](https://www.iotsec-zone.com/images/MdImg/478c184b810c27eb934037fdf4b8f296.png)

使用IDA打开可以得到如下反汇编内容

![15.png](https://www.iotsec-zone.com/images/MdImg/99033da06d31b8433aeb8f4749ce34fb.png)

根据mini_httpd，去github搜索，在如下链接：`https://github.com/peter-leonov/mini_httpd`，即可获得mini_httpd的相关源代码，只要找到厂商自己添加的模块即可

![16.png](https://www.iotsec-zone.com/images/MdImg/885f6d23d428a83e46730540be58c53b.png)

在main函数的第609行，对应mini_httpd的handle_request的函数


![17.png](https://www.iotsec-zone.com/images/MdImg/74743b3c00f128dc166a841f0d3a693a.png)

这里是处理http请求的函数

![18.png](https://www.iotsec-zone.com/images/MdImg/4d44ccbfed2ef9266e21e007f7ff92f8.png)


![19.png](https://www.iotsec-zone.com/images/MdImg/933678c787dddae68e5a31a5c2f304a2.png)

通过和mini_httpd的源码进行对比可以发现，从240行以后是厂商自己添加的处理函数，在这里我们可以看到比较请求的路径是否含有currentsetting.htm，有则将对应的变量设置为对应的值，继续往下跟踪


![20.png](https://www.iotsec-zone.com/images/MdImg/e41712b83fc7cf9e069b2caeac9684d0.png)

536行，对应mini_httpd的do_file函数，里面包含权限验证，跟进查看


![21.png](https://www.iotsec-zone.com/images/MdImg/69fbba5986c7aae4bb61552b10a59643.png)

通过逆向分析可以知道，携带的请求含有currentsetting.htm，则会授权响应，那么针对上面的命令执行漏洞，只要在请求中添加上currentsetting.html触发授权响应即可，payload如下：

```shell
http://192.168.0.1/setup.cgi?todo=syscmd&cmd=cat+/www/.htpasswd&currentsetting.htm
```

![22.png](https://www.iotsec-zone.com/images/MdImg/3268216733b0fbde5c2ef9bcf097fb48.png)

可以看到可以在未授权的情况下，成功读取了htpasswd密码文件，那么同理可以在未授权的情况下执行任意系统命令

## 0x04.总结

以上内容就是针对Netgear DGN1000未授权命令执行的全部分析过程，通过分析可以看到结合github开源项目对逆向分析事半功倍，常见的嵌入式设备web服务端，如goahead，lighttpd等，在市面上的使用量很高，并且也进行了开源 ，相信结合开源代码，能帮助大家快速恢复相关结构体并快速定位到厂商自己的代码，提高漏洞分析和挖掘的效率

![23.png](https://www.iotsec-zone.com/images/MdImg/72c7c58a9ee58e81bb009e5b659ca1a9.png)
