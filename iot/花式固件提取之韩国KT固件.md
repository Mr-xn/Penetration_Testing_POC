# 花式固件提取之韩国KT固件
> chan
> 来源：https://www.iotsec-zone.com/article/459

## 前言
手上有一台韩国的路由器，一直闲置了很久，打算去挖下漏洞，无奈找了很久固件没找到，就连官网都没有这款设备的固件，看来只有拆机；
![0.png](https://www.iotsec-zone.com/api/image/v2/20240816/d3ha70wo6240sw2hjy.png)

看到flash那一刻，好吧还是上串口吧；

![1.png](https://www.iotsec-zone.com/api/image/v2/20240816/d3ha76bnwpm39wanej.png)

![2.png](https://www.iotsec-zone.com/api/image/v2/20240816/d3ha7c68amzruffr26.png)

## 启动信息:
从启动信息可以看到U-Boot 版本信息：
0xbc140000：flash加载的地址
0x80001000：镜像解压后被加载到内存中的地址
0x806beb00：这是内核镜像在解压后，执行的入口点地址

![3.png](https://www.iotsec-zone.com/api/image/v2/20240816/d3ha86jwx85z7ijssd.png)

这个固件启动信息应该是有做滤过，flash的分区信息都没有显示；
shell需要身份认证，看来想要提取固件只能从U-Boot下手；

![4.png](https://www.iotsec-zone.com/api/image/v2/20240816/d3ha8wafnlj6acyw2z.png)

重新上电进入到U-Boot，发现命令是非常少，

![5.png](https://www.iotsec-zone.com/api/image/v2/20240816/d3ha9726avtyrbhez5.png)

原本打算用nand 将flash 读到内存，再读取出来的，但是启动项根本就没有打印flash的分区信息，如果从头开始去读然后再提取的话觉得太费劲，最后还是放弃了。

最后想的思路是 通过tftpboot 将镜像加载到内存，然后通过bootm 去启动镜像，然后在新的镜像系统使用dd去提取flash；

通过进入u-boot可以知道用的是mt7621的芯片方案和nand的flash；
镜像可以从openwrt官网找个相同架构的系统；
（注意：下载的镜像系统要支持nand并带nand驱动，不然进到系统无法识别设备flash）

## 准备工作：

镜像文件：lede-17.01.7-ramips-mt7621-mt7621-initramfs-kernel .bin

u-boot配置tftp服务

```
setenv ipaddr 10.10.10.123      # 设备ip地址
setenv serverip 10.10.10.3      # tftp服务器的ip地址
saveenv                         # 保存环境变量
printenv                        # 打印环境变量信息
```

![6.png](https://www.iotsec-zone.com/api/image/v2/20240816/d3hbffnhpglepn0exl.png)

ubuntu搭建tftp服务

```
sudo apt update
sudo apt install tftpd-hpa
```

编辑配置文件，配置完成后重启服务；
```
sudo vim /etc/default/tftpd-hpa

TFTP_USERNAME="tftp"
TFTP_DIRECTORY="/home/iot/tftpboot" # 这里是默认tftp文件路径,存放镜像文件路径,可自行设置
TFTP_ADDRESS="0.0.0.0:69"
TFTP_OPTIONS="--secure"

sudo systemctl restart tftpd-hpa

```

最后把lede-17.01.7-ramips-mt7621-mt7621-initramfs-kernel .bin拷到tftpboot/目录下；
我这里为了方便名字改成lede-17.01.7.bin；

ubuntu配置网卡；

![7.png](https://www.iotsec-zone.com/api/image/v2/20240816/d3hbfvvc2fwm0bcxk7.png)

## 加载镜像

接下来使用tftpboot命令将镜像加载到内存，这里出现checksum bad没反应可以ubuntu重启下网卡，再重配下ip应该就可以了；

```
tftpboot 0x88000000 lede-17.01.7.bin
```

加载完成提示：

![8.png](https://www.iotsec-zone.com/api/image/v2/20240816/d3hbg4o2qq3zpofgsw.png)

最后使用bootm命令启动镜像

```
bootm 0x88000000
```

启动时候如果出现乱码 是因为波特率不一样，可以关闭串口终端 选择对应的波特率，重开串口终端；
下面镜像在内存里成功启动；

![9.png](https://www.iotsec-zone.com/api/image/v2/20240816/d3hbh04xubzdvhkho0.png)

查看系统分区：

![10.png](https://www.iotsec-zone.com/api/image/v2/20240816/d3hbhan38illcrghqa.png)

## 固件提取

查看分区目录，mtd0 ~ mtd3为系统分区，mtd0ro ~ mtd3ro是什么分区具体没有去分析；
这里mtdblock0 ~ mtdblock3就是flash的分区啦；
(这里是猜测的，因为除了系统分区剩下的就是flash分区)

![11.png](https://www.iotsec-zone.com/api/image/v2/20240816/d3hbhkwe2mok1ye99i.png)

接下来就是用dd命令将分区拷出来，然后再合并；

```
dd if=/dev/mtdblock0 of=/tmp/kt01.bin bs=1
dd if=/dev/mtdblock1 of=/tmp/kt02.bin bs=1
dd if=/dev/mtdblock2 of=/tmp/kt03.bin bs=1
```

最后拷贝mtdblock3的时候系统会挂掉；df查看了下tmp空间有13M，感觉是完全足够；
再查看前面拷贝的3个分区大小都不超过1M，后面分区应该是系统文件；尝试多次发现原来是tmp空间使用超过5M 系统就会崩溃；保险起见，最后一个按1M给它分片拷贝出来；
(注意：这里系统挂了比较麻烦，要断电重新进入u-boot把系统拷进内存重新启动)

分片拷贝命令：
```
dd if=/dev/mtdblock3 of=/tmp/kt04.bin bs=1M skip=0 count=1 
# 注意skip是开始提取之前跳过的块数,每次提取完记得自加一;
```

下面是拷贝和scp传ubuntu的过程，传完后删除确保tmp空间充足；
（注意：这里传数据时候看下ip确保同一网段）

![12.png](https://www.iotsec-zone.com/api/image/v2/20240816/d3hbi278ve8peqprld.png)

![13.png](https://www.iotsec-zone.com/api/image/v2/20240816/d3hbi75ff94fwj2gyj.png)

![14.png](https://www.iotsec-zone.com/api/image/v2/20240816/d3hbic33ahvtlf73nc.png)

这里拷完第12个分片时候用010编辑器查看后面全是FF，由此判断数据已经拷贝完；

![15.png](https://www.iotsec-zone.com/api/image/v2/20240816/d3hbip2eviqmmrwbvx.png)

接下来可以用cat 将分片合并，之前还担心cat合并会有乱码，后来查了下cat合并不会破坏和改变文件原始数据，最终kt.bin合并后的文件；

![16.png](https://www.iotsec-zone.com/api/image/v2/20240816/d3hbjbyeypcvpjebjt.png)
![17.png](https://www.iotsec-zone.com/api/image/v2/20240816/d3hbjh2zvyfab0aget.png)

binwalk 查看分析，一切都没有问题，继续解压；

![18.png](https://www.iotsec-zone.com/api/image/v2/20240816/d3hbjoh79ojuk8scu2.png)
![19.png](https://www.iotsec-zone.com/api/image/v2/20240816/d3hbjv8jon7zoxampx.png)

熟悉的系统文件，至此固件提取成功完成，可以愉快的挖洞了；

![20.png](https://www.iotsec-zone.com/api/image/v2/20240816/d3hbk33h7sjx4jdlpe.png)

## 总结：
第一次使用这样的方式提取固件，中间还踩了不少坑，最终还是提取成功；
提取过程主要是问题是分区数据太大，本地空间不足，导致提取数据不完整，
系统还会崩溃，最后还是建议分片提取；这样的方式提取固件确实比nand和md的方式提取效率快；
最后不得不说棒子对安全这方便还是比较注重的；
