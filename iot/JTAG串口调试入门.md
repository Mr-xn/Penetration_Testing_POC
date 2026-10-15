# JTAG串口调试入门
> 0431物联卫士实验室
> 来源：https://www.iotsec-zone.com/article/1

# 0x00.准备工作

**软件部分**

- SEGGER J-Link V6.98e
- 硬件部分
- H-Link在线仿真器
- NUCLEO-746ZG板子

# 0x01.JTAG/SWD

JTAG是联合测试工作组（Joint Test Action Group）的简称，是在名为标准测试访问端口和边界扫描结构的IEEE的标准1149.1的常用名称。此标准用于验证设计与测试生产出的印刷电路板功能

1.下载器，固件下载到设备中

2.DEBUG，调试模式

3.边界扫描，可以访问芯片内部的信号逻辑状态，还有芯片引脚的状态等

JTAG根本没有标准的接口定义，甚至每家公司定义都不一样，下面是常见的JTAG引脚

![0.png](https://www.iotsec-zone.com/images/MdImg/3b4586fa2cbbe9039c981a7f65d419ca.png)
![1.png](https://www.iotsec-zone.com/images/MdImg/247cd167ee560d41b1fa7e95ac186e10.png)

在JTAG接口中，最常用的信号有四个，分别是TCK/TMS/TDO/TDI

TCK：测试时钟

TMS：测试模式选择，TMS用来设置JTAG接口处于某种特定的测试模式

TDO：测试数据输出，数据通过TDO引 脚从JTAG接口输出

TDI：测试数据输入，数据通过TDI引脚输入JTAG接口

SWD接口，算是一种和JTAG不同的调试模式，使用的调试协议也应该不一样，所以最直接的体现在调试接口上，与JTAG的20个引脚相比，SWD只需要4个（或者5个）引脚，结构简单，但是使用范围没有JTAG广泛，主流调试器上也是后来才加的SWD调试模式。

**SWD和传统的调试方式区别：**

SWD模式比JTAG在高速模式下面更加可靠。在大数据量的情况下面JTAG下载程序会失败，但是SWD发生的几率会小很多。基本使用JTAG仿真模式的情况下是可以直接使用SWD模式的，只要你的仿真器支持，所以推荐大家使用这个模式。

GPIO刚好缺一个的时候，可以使用SWD仿真，这种模式支持更少的引脚。

板子的体积有限的时候推荐使用SWD模式，它需要的引脚少。

![2.png](https://www.iotsec-zone.com/images/MdImg/51069cb3e5f121c17a88aad0b30e9458.png)
当我们进行调试的时候，只要连接这四个接口就能进行通信。

## 0x02.H-Link烧录Jlink固件

如果使用正版的J-Link可以直接使用SEGGER J-Link使用，但是由于我们使用的国内的H-Link，我们需要烧录J-Link的固件，烧录过程如下

H-Link 默认为离线烧录模式，调试需要进在线模式

![3.png](https://www.iotsec-zone.com/images/MdImg/1da10f3a6919e350218a2327dfc2c86a.png)

驱动安装完毕，再运行jlinkDownloader.exe

![4.png](https://www.iotsec-zone.com/images/MdImg/d5db6b2552c83a0bb1b41fe33df707d4.png)
![5.png](https://www.iotsec-zone.com/images/MdImg/fb06b82ee1f0fa4e097e5b49f66164e4.png)
默认会进行烧录，烧录成功

这里由于H-Link已经烧录成功，所以看不到HP_CMSIS_DAP串口了，但是查看管理接口，可以看到对应的接口

![6.png](https://www.iotsec-zone.com/images/MdImg/ef1ae55da7d411118afd7ca3861429cd.png)
接下来，就能使用SEGGER J-Link进行调试了

# 0x03.JTAG调试

查看NUCLEO-F746ZG的手册，可以找到对应的SWD引脚的位置及功能

![7.png](https://www.iotsec-zone.com/images/MdImg/c05a6aeed8cebb54de86ece6afcf1aff.png)

在H-Link的后面，我们可以看到H-Link的引脚对应关系

![8.png](https://www.iotsec-zone.com/images/MdImg/c8b605ffb00fa2ef969b8edbc9bb2f9c.png)

接下来，我们只需要根据连接线序将对应的引脚使用杜邦线连接即可，连接线序可以参考:

![9.png](https://www.iotsec-zone.com/images/MdImg/e970da25c42a539dae9323b904739e37.png)

连接完成的效果如下:

![10.png](https://www.iotsec-zone.com/images/MdImg/d1973c10f6abef9bba7019dfff17d6bb.png)

现在，我们已经连接成功，接下来使用SEGGER J-Link Commander和调试器H-Link建立连接即可

==注：进行连接之前将测试的板子进行通电==

![11.png](https://www.iotsec-zone.com/images/MdImg/379ae6c9bd928eed3361243931f81389.png)

接下来，我们使用connect进行连接，输入?选择对应芯片的型号，这里使用的芯片是STM32F746ZG

![12.png](https://www.iotsec-zone.com/images/MdImg/4846a261abf73d550ee50ce2f36990f8.png)

选择完毕，我们选择使用使用SWD进行通信，使用默认的4000kHz，这里的speed可以根据情况进行自定义设置

![13.png](https://www.iotsec-zone.com/images/MdImg/64d9e05ff465589d2292b9ac6e7c16bf.png)

这里我们输入?，进行SWD接口连接，看到如下内容可以确定，SWD接口已经连接成功

![14.png](https://www.iotsec-zone.com/images/MdImg/9c084d11586747097380dd4c9f029916.png)

使用?可以查看可以使用的命令

![15.png](https://www.iotsec-zone.com/images/MdImg/2113ea6f794e750a4295e40372a410cb.png)

# 0x04.J-Link固件提取

上面我们已经成功使用J-Link连接设备，接下来进行固件的提取。

为了提取固件，我们需要找到芯片的对应手册，我们可以在[https://www.datasheet5.com/网站上查找](https://www.datasheet5.com/网站上查找)，这里我们查找的是STM32F746ZG的数据手册，查看内存布局情况如下:

![16.png](https://www.iotsec-zone.com/images/MdImg/540946ca0e5269a66b6840095fdb0a19.png)

由于范围有限，这里只展示关键的位置，固件存储的地址从0x8000000起始。

这里我们使用mem将对应的内存位置的数据进行输出显示

![17.png](https://www.iotsec-zone.com/images/MdImg/08dd741587f1777d0f0b6749090bb676.png)

这里我们只显示50字节。由于这个固件是我们自己编译的，我们使用Sublime Text将编译的固件以十六进制的形式打开得到如下内容:

![18.png](https://www.iotsec-zone.com/images/MdImg/018be8b95da83f39af068263b58f8601.png)

可以看到固件的十六机制数据与内存中的前50字节移植，所以，这也就说明，0x8000000处存储的就是我们的固件。

我们根据Flash的实际内存布局0x8000000~0x80FFFFF，得到整个大小为0xFFFFF，我们直接使用savebin直接全部Dump下来

![19.png](https://www.iotsec-zone.com/images/MdImg/2285740e5f631209b89db5184429e436.png)

我们在jlink软件的安装目录下，可以看到DUMP下来的的aaa文件，使用Sublime Text打开查看

![20.png](https://www.iotsec-zone.com/images/MdImg/30d22a127a35b458363839554b6384cd.png)

![21.png](https://www.iotsec-zone.com/images/MdImg/35ad3b2dbd2cc6132d67cd9cf7ca2c8c.png)

可以看到数据和之前编译的固件一致，往下查看，会看到很多FF。

![22.png](https://www.iotsec-zone.com/images/MdImg/471f516d849566b51603daee31961749.png)

这是由于我们编译的固件没有0xFFFFF这么大，后面的内容没有覆盖，以FF的形式输出。我们将后面的FF全部删除就能得到最后的固件了。

通过Sublime Text进行文件比较，可以看出没有任何不同。

![23.png](https://www.iotsec-zone.com/images/MdImg/fca5feb1f278a68d3f3223336619b7f2.png)

到这里，固件已经全部提取成功。后面的就是进行二进制的逆向分析即可。

```shell
dd
```
