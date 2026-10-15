# PT926G从固件提取到gdbserver调试连接与后门漏洞的发现
> 乌托邦
> 来源：https://www.iotsec-zone.com/article/506

# 固件准备与提取
## 提取前准备
1.在硬件提取之前，进行一个小的设备准备

![0.png](https://www.iotsec-zone.com/api/image/v2/20250725/dbkxshtdvfj9wlyho3.webp)

FT232模块USB转TTL

TTL电平信号的高电平通常为3.3V或5V

通过进行URAT串口连接进行调试

**Uart：** 在嵌入式开发中有很广泛的应用，其中之一就是开发板的固件烧录（交互）功能。在常见的一些IOT设备中，它的作用主要是厂商预留的一些调试接口，一般可以通过跳线的方式连接这些uart串口，实现IOT设备的日志输出，固件升级降级等功能，有些还会开放根目录与u-boot的访问权限

TTL电平信号的高电平通常为3.3V或5V（书上内容用异步收发传输器，一般都嵌入在芯片中，为了方便调试，大部分物联网设备都会把URAT引脚引到PCB板上。

如下所示，四个引脚分别是VCC,GND,TX,RX.(大部分情况下，引脚一般不会标注出来)

![1.png](https://www.iotsec-zone.com/api/image/v2/20250725/dbkxu2stqyj9lh8uxp.webp)

VCC:供电引脚，一般是3.3V或5V（不接）

GND:接地引脚

RX:接收数据     TX:发送数据

通过FT232进行连接GND接地引脚相互连接，而RX和TX因为一个是接收数据一个是发送数据，所以到转换器上连接的情况是RX-TX TX-RX这样进行连接

**标注情况下就是直接在PCB版上直接进行焊接直接连接**
**未标注情况下**
板子上的URAT串口是不进行对GND什么的进行编译，在此种情况下需要使用万用表对串口进行识别

1.首先把万用表档位调到导通档位，这样的情况下检测出GND接口（导通情况下，万用表都会给出反应）

2.然后给该pcb板接通电源，一边接地一边进行电压检测（万用表档位改到20v）当测量到VCC引脚时，电压会稳定在3.3V或5V附近

3.剩下两个口就是rx和tx两个口，当如果设备rx与转换器的rx连接之后

在软件MoBaXterm内参数不会加载

当如果串口与转换器连接正常，搜索编辑系统环境变量

![2.png](https://www.iotsec-zone.com/api/image/v2/20250725/dbkxvoqe7txtyoikfi.webp)

![3.png](https://www.iotsec-zone.com/api/image/v2/20250725/dbkxvrjlfyfg9a4fiz.webp)

![4.png](https://www.iotsec-zone.com/api/image/v2/20250725/dbkxw55zxy5axjc3b7.webp)
到这里有个com4,接下来打开软件

![5.png](https://www.iotsec-zone.com/api/image/v2/20250725/dbkxx6oql8mqkv5dj5.webp)

![6.png](https://www.iotsec-zone.com/api/image/v2/20250725/dbkxxbyb21n74irjlf.webp)

在这里的speed(波特率)一般速度都为115200，也有部分老的设备为9600，57600，在这里我们假设一次给一个错的波特率，在这里有乱码读进来!

![7.png](https://www.iotsec-zone.com/api/image/v2/20250725/dbky0fnqt5diksuy5w.webp)
正常状态下是这样使用uboot引导程序加载进来

![8.png](https://www.iotsec-zone.com/api/image/v2/20250725/dbky0meyg7uncfjgcd.webp)
在输入光猫背后的用户名名和密码之后直接进入了shell页面ps看一下进程

![9.png](https://www.iotsec-zone.com/api/image/v2/20250725/dbky0ro67texy6lzag.webp)

我们看到了uhttp，web服务在的文件夹地址，但是此时有个比较特殊的情况，我们真的进来之后发现，该文件并不存在

![10.png](https://www.iotsec-zone.com/api/image/v2/20250725/dbky3a3z3sr4alevin.webp)

使用命令查找一下，发现我们的服务是起在了opt下面的usr下面，所以rootfs才是我们要的这套文件系统

```bash
find / -name uhttpd
```

![11.png](https://www.iotsec-zone.com/api/image/v2/20250725/dbky3fbbpshqlozxdx.webp)

通过查找端口使用情况我们发现使用了80，和8080这两个端口，起了两套服务

![12.png](https://www.iotsec-zone.com/api/image/v2/20250725/dbky3nqotehvh6jwxq.webp)
本次使用的设备比较特殊，存在有usb插口，此时提取固件可以直接cp走，也可以是把我们要的固件打包成tar.gz格式的文件打包进硬盘

# 实体设备和模拟的区别思考
 我们通常进行的固件模拟，是通过系统级模拟来重建设备运行所需的整体环境，使固件能够在模拟的设备环境中运行。  
但如果我们手中有真实的实体设备，就不需要再通过模拟环境来运行固件，因为实体设备本身就具备固件运行所需的完整硬件和系统环境，我们只需直接在其上进行调试即可。 

# gdbserver连接前置准备
我们要进行远程调试，就需要在虚拟机中使用gdb和在对应的目标设备中存在gdbserver接收调试信息

本身嵌入式设备基本上都没有，这时通过我们提取的固件确定文件busybox的文件信息来匹配所需要的gdbserver给实体设备传输过去。

通过桥接网络，将本地，虚拟机，以及实体设备的网络都配置在一个网段下，通过在虚拟机上起一个http服务，将gdbserver匹配的版本下载进去

![13.png](https://www.iotsec-zone.com/api/image/v2/20250725/dbky7aj4w3z4xjubtc.webp)

![14.png](https://www.iotsec-zone.com/api/image/v2/20250725/dbky7iyuts7t0qsb5d.webp)

通过更改虚拟机的网络设置，将三端都设置在一个网段下成功ping通就可以在虚拟上起一个http服务，将需要的gdbserver传到固件里

![15.png](https://www.iotsec-zone.com/api/image/v2/20250725/dbky7nz5syl5ldbwlc.webp)
通过查看busybox的文件信息发现，适合的为

gdbserver-7.12-mipsel-mips32rel2-v1-sysv

![16.png](https://www.iotsec-zone.com/api/image/v2/20250725/dbky7ujooipjla9ceq.webp)

![17.png](https://www.iotsec-zone.com/api/image/v2/20250725/dbky8hn75v3vgcopp0.webp)

通过起一个http服务在固件中利用wget将gdbserver传输进来

```bash
python -m  http.server
wget 192.168.1.2:8000/gdbserver-7.12-mips-mips32rel2-v1-sysv
```

![18.png](https://www.iotsec-zone.com/api/image/v2/20250725/dbky84uw3lpbuxhkwt.webp)

![19.png](https://www.iotsec-zone.com/api/image/v2/20250725/dbky8821r1lku6v99u.webp)
# 实体调试与后门发现
给装载进的gdbserver 增加权限

```bash
chmod +x
```

增加完可执行文件之后进入到web服务所在的目录

查看网卡，使用attch给进程增加个1234端口用于远程调试

![20.png](https://www.iotsec-zone.com/api/image/v2/20250725/dbkya17n8n7h9ks8be.webp)

在虚拟机上使用pwndbg 将uhttp起来

```bash
pwndbg  uhttpd
set architecture mips
set endian big 
set sysroot lib/
set solb_serach-path lib/
target remote 192.168.1.1:1234
```

![21.png](https://www.iotsec-zone.com/api/image/v2/20250725/dbkya6brf6v2cdyipw.webp)

通过IDA对该二进制文件去进行分析，去搜索password 字符串，发现这里面并没有登录逻辑，只是单纯的起了web服务

通过搜索脚本去对login 和password 字符串搜索，定位到有一个单独的二进制文件login

![22.png](https://www.iotsec-zone.com/api/image/v2/20250725/dbkyahppk5mqfubztp.webp)

第一次看到login还有单独二进制文件的，对这个单独的二进制文件进行分析

进入登录验证逻辑很清晰看到这里有个特殊的条件账户

![23.png](https://www.iotsec-zone.com/api/image/v2/20250725/dbkyan52cfwpaltlkm.webp)

这个if函数的逻辑很简单，通过检查是否在/tmp目录下存在debug这个文件，存在并且用户名是diag709394就可以调用下面这个sub_400E94(0, 0, 0)函数
在此时需要通过UART进入shell页面查看是否有这个文件，如果没有就touch一个debug文件去进行验证一下这个逻辑
进入到shell页面下，查看是否tmp目录下是否有这个文件（在这里它确实没有，太可惜了）
![24.png](https://www.iotsec-zone.com/api/image/v2/20250725/dbkzo3n3lh82w8pisj.png)

先尝试这个逻辑是否能用，直接login,可以看到下下面此时这个用户名并不能用

![25.png](https://www.iotsec-zone.com/api/image/v2/20250725/dbkzodciw3sdhticlj.png)

我们尝试在touch一个文件在tmp目录下，然后在尝试使用这个特殊账户，可以在下面很清晰的看到，没有了密码验证，直接进入shell
![26.png](https://www.iotsec-zone.com/api/image/v2/20250725/dbkzos9mztv91tmqvw.png)

进入到条件账户之后可以进入的函数，就可以看到这是一个特殊的调试界面，可以非常肯定这是一个厂家预留的后门调试账户

![27.png](https://www.iotsec-zone.com/api/image/v2/20250725/dbkyatbcozkfvpcqwb.webp)
