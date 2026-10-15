# tendaCT6摄像头命令执行
> p1yang
> 来源：https://www.iotsec-zone.com/article/251

最近逛tenda发现新上了一款摄像头，这不下载个固件看看？

直接binwalk一把梭

![0.png](https://www.iotsec-zone.com/images/MdImg/f180b0cb80c3f46aa5ea81802e0608c5.png)

## firmAE

这里先不看文件系统，尝试下用firmAE来模拟固件

> sudo ./run.sh -c ipc /mnt/hgfs/sharedir/tenda/ct6/IPC_SD_update.bin  
>
> 需要使用root权限来执行firmAE文件夹下的run.sh，-c参数为check，来检查是否可以模拟，一般check完成后模拟起来会很快，但check很慢，ipc算是项目名字可定义即可

![1.png](https://www.iotsec-zone.com/images/MdImg/5fcae87f08b73cc7842d07ea39f347dc.png)

> sudo ./run.sh -d ipc /mnt/hgfs/sharedir/tenda/ct6/IPC_SD_update.bin  
>
> check完成后可以使用 -a参数直接执行，或者-d参数以debug模式执行，debug模式

![2.png](https://www.iotsec-zone.com/images/MdImg/59426dbe517114c5007483a6ed38468a.png)

这个固件能模拟，但是不能完全模拟，知道用法就可了。

## 如何找到一个固件的服务进行分析

当解包一个固件的时候发现，没有http服务，没有html页面，没有httpd，boa，uhttpd，lighttpd等。

某些摄像头经常见到这个问题。

这个时候需要从启动来一点点看找到他启动了什么服务。

当然如果有设备并且获取了串口shell，也可以直接查看

> 这里推荐个超好用的命令 find 
>
> 大概用法 
>
> ​	find . -name "httpd"
>
> ​	 find . -name "*cfg"
>
> 支持*这样的正则匹配

linux启动最先看inittab，一般在etc下面

![3.png](https://www.iotsec-zone.com/images/MdImg/9f07afc9dc80ed7ef9e3a8571285e967.png)

启动rcS，一般都在/etc/init.d/rcS

![4.png](https://www.iotsec-zone.com/images/MdImg/a03df0f9c74fde340dc2424113027c95.png)

这里就是执行了init.d文件夹下的文件

![5.png](https://www.iotsec-zone.com/images/MdImg/082d1f9280e21d8f0fcf500d2457fe3c.png)

S00devs 里使用mknod创建Linux中的符设备文件和块设备文件，不重要

S01udev 它主要的功能是管理/dev目录底下的设备节点。它同时也是用来接替devfs及热插拔的功能，这意味着它要在添加/删除硬件时处理/dev目录以及所有用户空间的行为。也不重要

S80network中也并没有发现启动的服务

那返回到rcS，执行完S*之后，执行了/opt/app/init.sh

![6.png](https://www.iotsec-zone.com/images/MdImg/e85bca44292631f10ddb234c2abf2e06.png)

但opt中没有任何文件，这个时候就需要上面说的find命令了。

![7.png](https://www.iotsec-zone.com/images/MdImg/4c70d133406446ccdfa360a6a1722b91.png)

吧squashfs-root-0和-1的所有内容移动到opt下

![8.png](https://www.iotsec-zone.com/images/MdImg/27af63d8297ae566f9b5cfda4243ad86.png)

运行network_setup.sh，启动telnet服务，将execute放到tmp，启动execute服务，运行daemon.sh

network_setup.sh中没有服务启动，不赘述

daemon.sh中执行了tdseq服务

![9.png](https://www.iotsec-zone.com/images/MdImg/1d7381bad85b79e9858d72e0ffc2f23e.png)

从先后顺序来看，来分析个execute。

这里tenda摄像头设备基本都是armel，自行file即可

## execute

main中可以看到socket函数（具体请看socket网络编程）

![10.png](https://www.iotsec-zone.com/images/MdImg/311214938a60c0df77d8388e206559f1.png)

这里绑定了8899端口，但是并没有监听。启动下看看

![11.png](https://www.iotsec-zone.com/images/MdImg/f86caaeb31cf0b4f83691953903ef3cd.png)

发现8899的udp协议。

可以使用netcat连接

![12.png](https://www.iotsec-zone.com/images/MdImg/4b7d12c18c8bbf1118387d2299dff9b5.png)

这里分析下udp协议做了什么

![13.png](https://www.iotsec-zone.com/images/MdImg/facb05888b81373f3df0de953bc1a596.png)

通过recvfrom获取到传入的内容存放到v13，创建新线程将内容传进去。

![14.png](https://www.iotsec-zone.com/images/MdImg/3c5ebc6679fea2ee80be2b9f6b19155d.png)

在线程中，吧参数给了v9，然后注意这个v17获取了前四位做了个判断。

以为是magicnumber，满足条件执行my_system，但是这个magicnumbe没有做任何奇奇怪怪的判断。

所以可以直接命令执行，但是还是好奇这个sub_10D64做了什么。

点进去？？？？？？？？？？？？？？？？？？？？？？？？？？？？

![15.png](https://www.iotsec-zone.com/images/MdImg/adc0e56fa1da4fe1cb22c4cc88e43ad2.png)

不是，脱裤子放屁都没这么放的吧。

开发者这么做，一定有他的用(大)意(病)

查了半天，也没发现这里if分支的区别。

这里应该算是个命令执行了。直接来吧！

## qemu user导致的问题

这里本来使用的 sudo chroot . ./qemu-arm-static ./opt/app/execute 启动的，但是命令执行死活不成功。

gdb调试了一天，愣是没找到问题。

![16.png](https://www.iotsec-zone.com/images/MdImg/0eee80cf0a2472b43f468010d5614abd.png)

第二天尝试了下qemu-arm-static -L . ./opt/app/execute

可以了。。。，这里xxxx就是为了填充magic number，可以写脚本传入0x00来执行到sub函数。

![17.png](https://www.iotsec-zone.com/images/MdImg/374ed7c145a43a669739673a54a423f5.png)

所以各位有时候遇到这种问题可以看一下是否是qemu的问题。

当然，如果像我一样，有一个同架构的其他设备，又刚好有该设备的rce，就可以搞点牛头人操作了。

## 关于gdb多线程调试

gdb多线程调试，大概说一下怎么搞。

使用qemu自带的-g参数启动远程server

>  qemu-arm-static -L . -g 1234 ./opt/app/execute # 1234为监听的端口

![18.png](https://www.iotsec-zone.com/images/MdImg/040799794c0a8e7da2262913047cbc36.png)

使用gdb-multiarch来进行调试

> gdb-multiarch opt/app/execute
>
> target remote 127.0.0.1

![19.png](https://www.iotsec-zone.com/images/MdImg/f8b025c24c3318659ed52e6712cdb313.png)

在子线程函数中下个断点，我这边位置是0x000110E8

![20.png](https://www.iotsec-zone.com/images/MdImg/38099bd3cde830c77b0c821ac41c481b.png)

![21.png](https://www.iotsec-zone.com/images/MdImg/9009bab0247d2e28c311f04e54d2f6be.png)

使用c来执行程序

![22.png](https://www.iotsec-zone.com/images/MdImg/617a45432d291a1ab8c55233d1837536.png)

使用netcat连接udp

> nc -uvv 127.0.0.1 8899

![23.png](https://www.iotsec-zone.com/images/MdImg/1d9cab954a7822b06712f83038985d43.png)

连上后gdb中能发现新线程

> info threads

![24.png](https://www.iotsec-zone.com/images/MdImg/2c2b335f47dadff359ace0b603c18364.png)

ID 2 就是断下来的心线程，使用thread 2来切换线程

> thread 2

![25.png](https://www.iotsec-zone.com/images/MdImg/300b8ebebfb037c80ab6d1021f4d19f4.png)

此时pc指向我们的断点，要回主线程，只需要再次切换即可。

可能漏洞点比较简单，但确实挺多人拿到固件后发现不了http协议后会不知道怎么下手，这里算是提供一个思路。
当然思路不止这一种，也可以通过串口shell netstat -anp来查看哪个软件监听了哪个端口。
