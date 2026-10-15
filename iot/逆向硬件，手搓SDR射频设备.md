# 逆向硬件，手搓SDR射频设备
> heiyu
> 来源：https://www.iotsec-zone.com/article/470

![0.png](https://www.iotsec-zone.com/api/image/v2/20240828/d3rb2ttmlcf1mtsdim.png)

# 介绍
几周前，我对我衣柜里放着的一台老式电缆调制解调器 Motorola MB7220 感到好奇。最初，我对它的硬件和是否运行 Linux 感兴趣。一番快速搜索让我找到了一个网络论坛上的帖子，人们在讨论用于诊断的内置频谱分析仪功能。有人提到他们可以看到与 FM 广播电台对应的尖峰。这引发了一个想法：如果一台电缆调制解调器和一台数字电视调谐器棒基本上在做同样的事情（接收和解调 QAM 信号），那么一个调制解调器是否可以转变成一个 SDR（软件定义无线电），就像 RTL-SDR 一样？

进入这个项目时，我对射频几乎一无所知，也不知道这个目标对硬件是否可行。我找到了基于模拟设备电缆调制解调器芯片的SDR 项目，以及一个论坛帖子，几年前有人也对同样的事情感到困惑。

用户 VK4HAT 在帖子中的最后一篇帖子中提到：

```
如果你有技能、时间和愿望，我建议尝试一下，看看你最终会走到哪里。如果谷歌没有显示任何结果，那么很可能还没有人尝试过。在生活中很少有第一次机会，抓住那些出现的机会，即使失败总是一个选择。
```
所以这正是我所做的。

# 获取访问权限

我的第一个目标是寻找一个访问向量或与设备通信的方法。我知道在 Web 界面上看不到太多内容，Telnet 被禁用了，所以我直接打开了它。

在从塑料外壳中拆下几颗螺丝以便接触电路板后，我的第一个想法是寻找UART标头以窥探串行控制台。在识别出两个由四个环绕在 PCB 边缘附近的焊盘组成的候选者后，是时候识别引脚了。使用万用表，通过检查与板上一个金属屏蔽罩之一的连续性，可以轻松识别地线引脚。当打开电路板时，可以通过测量每个引脚的电压来识别 VCC 引脚。它应该是稳定的 3.3 伏特，或在某些情况下是 1.8 伏特或 5 伏特。这个引脚是不需要的，但仍然有用于识别工作电压并排除一个 Tx 和 Rx 引脚的候选者。在启动时，Tx 引脚的平均值会略低于 VCC 引脚，并且在输出大量数据时会降得更低。这样最后一个引脚就是 Rx。

之前识别的其中一个 UART 似乎没有发送任何内容，而另一个 UART 有。在给活动 UART 焊接了一些导线后，我将 Tx 连接到树莓派上的 UART Rx GPIO 引脚，将 Rx 连接到树莓派的 Tx，地线连接到地线引脚。请注意，这只能做到是因为两个系统都是 3.3 伏特。如果不是这种情况，USB TTL 适配器可以轻松地使用，而且在大多数情况下可能更好。

树莓派不是最佳的串行接口的原因有几个，比如如果你需要奇偶校验或其他功能，但在这种情况下，我手头上有它并且它可以工作。树莓派的串行控制台也必须被禁用，以便为其他用途释放出来。我选择使用树莓派的另一个原因会在后面提到。

最后，要实际查看我使用的数据，我使用了 `cu`实用程序： `cu-l/dev/serial0-s115200` 波特率是一个幸运的猜测，但在这类设备上，115200 是非常常见的。 如果波特率错误，当您看到一堆垃圾时，您会很快知道 在屏幕上。逻辑分析仪可用于确定性地找到波特率 速率和其他参数，但猜测有时更快，总是 更便宜。

设备开机后，终端显示如下输出：

```
1. pi@raspberrypi:~/modem $ cu -l /dev/serial0 -s 115200
2. Connected.
3. �
4. B3312inim S C 84(9 m
5. ose_VS 8
6. STesldlo rh 83 rs 10
7. STesldhi: _h 8, _s 13
8. Sync: 0
9. MemSize: 128 M
10. Chip ID: BCM3383D-B0
11. BootLoader Version: 2.4.0 fyl spiboot reduced DDR drive avs
12. Build Date: Nov 12 2015
13. Build Time: 14:31:43
14. SPI flash ID 0xef4016, size 4MB, block size 64KB, write buffer 256, flags 0x0
15. Cust key size 128
16. Signature/PID: 3383
17. 
18. Image 1 Program Header:
19. Signature: 3383
20. Control: 0005
21. Major Rev: 0003
22. Minor Rev: 0000
23. Build Time: 2015/11/26 08:47:57 Z
24. File Length: 1692841 bytes
25. Load Address: 80004000
26. Filename: ecram_sto.bin
27. HCS: e749
28. CRC: 175b753f
29. 
30. Found image 1 at offset 20000
31. 
32. Enter '1', '2', or 'p' within 2 seconds or take default...
33. 
34. Performing CRC on Image 1...
35. CRC time = 282177012
36. Detected LZMA compressed image... decompressing...
37. Target Address: 0x80004000
38. decompressSpace is 0x8000000
39. Elapsed time 736066500
40. 
41. Decompressed length: 8091524
42. 
43. Executing Image 1...
44. 
45. eCos - hal_diag_init
46. Ecos memory map:
47. BLOCK OWNER MIPS SIZE MEM
48. Block 0: Owner: 0 - 0x00000000 0x07e00000 0x00000000
49. Block 0: Owner: 0 - 0 MB 126 MB 0 MB
50. Block 1: Owner: 3 - 0x07e00000 0x00200000 0x07e00000
51. Block 1: Owner: 3 - 126 MB 2 MB 126 MB
52. 126MB (129024KB) remaining for eCos
53. Init device '/dev/BrcmTelnetIoDriver'
54. Init device '/dev/ttydiag'
55. Init tty channel: 807bb020
56. Init device '/dev/tty0'
57. Init tty channel: 807bb040
58. Init device '/dev/haldiag'
59. HAL/diag SERIAL init
60. Init device '/dev/ser0'
61. BCM 33XX SERIAL init - dev: b4e00500.2
62. Set output buffer - buf: 0x80852408 len: 4096
63. Set input buffer - buf: 0x80853408 len: 4096
64. BCM 33XX SERIAL config
65. Init device '/dev/ser1'
66. BCM 33XX SERIAL init - dev: b4e00520.3
67. Set output buffer - buf: 0x80854408 len: 4096
68. Set input buffer - buf: 0x80855408 len: 4096
69. BCM 33XX SERIAL config
70. Init device '/dev/ser2'
71. InitBoard: MIPS frequency 637200000
72. 
73. ...
74. 
75. Reading Permanent settings from non-vol...
76. Checksum for permanent settings: 0xe9d88f65
77. Setting downstream calibration signature to '5.7.1mp1|die temperature:70.775degC'
78. Settings were read and verified.
79. 
80. Reading Dynamic settings from non-vol...
81. Checksum for dynamic settings: 0x6e4a329
82. Settings were read and verified.
83. 
84. Console input has been disabled in non-vol.
85. Console output has been disabled in non-vol! Goodbye...
86. [00:00:00 01/01/1970] [Reset/Standby Switch Thread] BcmResetStandbySwitchThread::ProcessRes
87. [00:00:00 01/01/1970] [Reset/Standby Switch Thread] BcmResetStandbySwitchThread::ProcessRes
```
这个输出包含大量信息。该设备在 Broadcom BCM3383 SoC 的 MIPS 处理器上运行eCos。事实证明，该 SoC 上实际上有两个 MIPS 处理器，尽管其中一个在这个调制解调器上没有使用，解释了另一个 UART。在一些设备上，第二个处理器将运行 Linux 以获得额外功能。

此外，这似乎是串行的终点，因为在启动实际操作系统后不久，它会禁用串行控制台。在引导加载程序提示处按“p”键并没有太多作用，除了通过 tftp 下载新的操作系统映像的方法以及用于读取和写入内存地址的实用程序。这可以用来绕过检查，但需要对操作系统和内存布局有更深入的了解。

# 倒掉闪存
我的目标现在是启用串行控制台。检查板子发现一个单独的SPI闪存芯片，很可能包含引导加载程序、操作系统和配置，因为它是板子上唯一可见的非易失性存储器。

这就是树莓派再次派上用场的地方。 GPIO 头部还方便地包含了一个 SPI 接口，可以用来读取闪存芯片上的数据。

在芯片上搜索编号“winbond 25Q32JV”，可以找到包含引脚图的数据表。其中重要的引脚有 VCC、芯片选择（CS）、时钟（CLK）、数据输出（DO）、数据输入（DI）和地。

将 SPI 芯片倾倒在电路板上的一个常见问题是芯片需要电源，但这也通常会给电路板供电并导致其开始引导并使用芯片。我选择通过用我的焊接铁加热 VCC 引脚，并非常小心地将其从焊盘上抬起来来克服这个问题。这是一个方便但相当粗糙的解决方案，可能会导致引脚折断，因此请自行承担风险！我还在焊盘上焊接了一根跳线，并在浮动引脚上焊接了另一根跳线，这样我就可以轻松地连接和断开它们，并允许设备再次引导。

另一个注意事项是，某些板上的芯片选择引脚被假定为始终启用，因此直接连接到 VCC。这意味着当您给 CS 引脚供电时，板子也开始启动。这可以通过类似的方式解决 VCC 引脚的问题。

现在，可以将电线焊接到其余的引脚上，然后将它们连接到树莓派上。地线连接到地线（之前的 UART 地线也可以使用），VCC 连接到树莓派的 3.3v 引脚。（再次强调，必须通过数据表验证这是一个 3.3v 芯片，因为树莓派只支持 3.3v）。DO 引脚连接到树莓派的 SPI `MISO`（主入从出）引脚，DI 连接到 `MOSI`引脚（主出从入）。最后，时钟连接到 `SCLK` GPIO 引脚，片选连接到 `CE0`引脚。

![1.png](https://www.iotsec-zone.com/api/image/v2/20240828/d3rb7e4o8hvhcmqefb.png)

要实际读取芯片，有一个名为flashrom的神奇工具，它支持大量芯片。 `flashrom`存在于许多发行版的存储库中，包括树莓派操作系统（以前称为 Raspbian）。

幸运的是，W25Q32JV 得到支持，以“W25Q32.V” 的名义。在 flashrom 维基上快速检查显示大小和电压与预期相匹配，并且芯片得到完全支持。

在继续之前，请确保使用 `raspi-config`实用程序启用 Pi 上的 SPI 接口，并在“接口选项”下进行检查。

最后我们可以读取芯片。首先验证它是否被检测到，以及一切是否连接正确：

```
1. flashrom -p linux_spi:dev=/dev/spidev0.0,spispeed=2000 \
2. --chip W25Q32.V
```
如果成功，我们现在可以倾倒内容：

```
1. flashrom -p linux_spi:dev=/dev/spidev0.0,spispeed=2000 \
2. --chip W25Q32.V \
3. --read modem.bin
```

# 固件分析
快速查看十六进制转储可以看出，大部分数据是压缩或加密的，但在接近结尾处，配置是可见的。

```
1. ...
2. 003f00c0: ffff ffff ffff ffff ffff 0000 07b0 369a ..............6.
3. 003f00d0: 6336 0010 434d 4170 0002 0000 0002 0000 c6..CMAp........
4. 003f00e0: 0000 0057 4d4c 6f67 0005 0004 7573 6572 ...WMLog....user
5. 003f00f0: 0004 7573 6572 0005 6164 6d69 6e00 086d ..user..admin..m
6. 003f0100: 6f74 6f72 6f6c 6102 7465 6368 6e69 6369 otorola.technici
7. ...
```
Web 界面凭据以及许多其他编码配置值都是明显可见的。在一番搜索后，我发现了一个名为的优秀项目，其中包含了用于转储、解析和修改 Broadcom 电缆调制解调器配置的实用工具。该存储库还包含了大量关于固件和配置格式的非常详细的文档。简要说明一下，转储功能需要 telnet 或串行连接，而我的设备上都没有这两种连接方式。

配置的开始实际上是在我的设备上的 0x003f0000，并包括 202 个 0xff 字节。从转储中提取配置后，我能够成功地使用 `bcm2cfg`读取它。

我启用了串行控制台以及 Telnet 访问，并设置了一个更简单的 Telnet 密码。

```
1. $ ./bcm2-utils/bcm2cfg set bfc.serial_console_mode "rw"
2. bfc.serial_console_mode = rw
3. $ ./bcm2-utils/bcm2cfg set userif.remote_acc_methods 0x3
4. userif.remote_acc_methods = http | telnet
5. $ ./bcm2-utils/bcm2cfg set userif.remote_acc_pass abcd
6. userif.remote_acc_pass = abcd
```
接下来，我将修改后的配置附加到一个填充了零直到适当偏移的文件上，并使用 `flashrom`将配置写回芯片。为了避免重写整个芯片，我为 `flashrom`创建了一个布局文件，这样它只会覆盖配置而不是整个内容，这就是为什么修改后的图像只是用零填充。布局文件看起来像这样：

```
1. 00000000:003effff fw
2. 003f0000:003fffff cfg
```
和命令：

```
1. flashrom -p linux_spi:dev=/dev/spidev0.0,spispeed=2000 \
2. --chip W25Q32.V \
3. --layout ./layout \
4. --image cfg \
5. --write modem-modified.bin
```
打开串行控制台并重新启动后，我看到...与之前完全相同的东西。对闪存图像的进一步检查显示，初始配置后面有许多重复的副本。这些副本有轻微的差异，最明显的是额外的错误日志消息。看起来设备会滚动备份配置，以防一个被损坏。为了简化事情，我通过网络界面进行了一次工厂重置，以摆脱所有的错误日志消息。然后我再次转储了闪存，并重复了之前的过程，修改了干净的配置，只包括第一个副本。然后使用一些 `dd`命令，我宁愿不去考虑，我重建了整个配置部分，在每个配置开始的偏移处附加修改后的配置。刷入这个新镜像并再次启动后，我终于能够查看整个引导日志，然后访问控制台，尽管输出被一个正在寻找信号的进程淹没。

```
1. ...
2. 
3. Reading Permanent settings from non-vol...
4. Checksum for permanent settings: 0xe9d88f65
5. Setting downstream calibration signature to '5.7.1mp1|die temperature:70.775degC^@^@^@^@^@
6. Settings were read and verified.
7. 
8. 
9. Reading Dynamic settings from non-vol...
10. Checksum for dynamic settings: 0x2630e508
11. Settings were read and verified.
12. 
13. [00:00:00 01/01/1970] [tStartup] BcmBfcFpmDriver::Init: (BFC FPM Driver) Setting FPM Buffe
14. [00:00:00 01/01/1970] [tStartup] BcmBfcFpmDriver::Init: (BFC FPM Driver) fFpmLargestBuffer
15. [00:00:00 01/01/1970] [tStartup] BcmBfcFpmDriver::Init: (BFC FPM Driver) Pool index: 0 po
16. [00:00:00 01/01/1970] [tStartup] BcmBfcFpmDriver::Init: (BFC FPM Driver) Pool index: 1 po
17. [00:00:00 01/01/1970] [tStartup] BcmBfcFpmDriver::Init: (BFC FPM Driver) Pool index: 2 po
18. [00:00:00 01/01/1970] [tStartup] BcmBfcFpmDriver::Init: (BFC FPM Driver) Pool index: 3 po
19. [00:00:00 01/01/1970] [tStartup] BcmBfcFpmDriver::Init: (BFC FPM Driver) Lookup table inde
20. 
21. ...
22. 
23. [00:00:18 01/01/1970] [Scan Downstream Thread] BcmGenericCmDownstreamScanThread::ThreadMain
24. [00:00:18 01/01/1970] [Scan Downstream Thread] BcmGenericCmDownstreamScanThread::ScanStarti
25. Resetting EnergyDetected to false.
26. Forgetting energy frequency.
27. Executing fast scan algorithm...
28. 
29. Type 'help' or '?' for a list of commands...
30. 
31. CM> Scanned 489000000 Hz...
32. Scanned 495000000 Hz...
33. Scanned 501000000 Hz...
34. Scanned 507000000 Hz...
35. Scanned 513000000 Hz...
```

# eCos 控制台
eCos 控制台包含许多配置和调试命令。可以使用以下命令停止输出的过程：

```
1. cd cm_hal
2. scan_stop
```

作为一点说明，这些“目录”并不是一个真正的文件系统，它们只是一种组织命令组的方式。Telnet 访问也可以在 IP 地址 `192.168.100.1`上使用。用户名是“technician”，密码是我在修改配置时更改的密码。Telnet 会将您放入一个受限制的 shell 版本，但可以使用 `su`命令和密码 `brcm`来访问完整的 shell（感谢 bcm2-utils 的作者 jclehner）。这个密码可能会因设备制造商而异。最初，我只是想看看是否可以启用这台设备上似乎被禁用的基于网络的频谱分析仪。有一些与此相关的设置，但没有关于启用或禁用外部接口的内容。在各种菜单和命令中花了几个小时后，我决定是时候转向分析操作系统了。

# 反向工程固件
由于引导日志，我们知道操作系统位于 0x20000 处，且为 LZMA 压缩。`bcm2-utils`的 README 指引我到一个包含名为 `ProgramStore`的实用程序的Broadcom repo。构建 `ProgramStore`后，我能够使用以下命令提取解压缩的图像：

```
1. ./ProgramStore -f ./ecram_sto.bin -o decompressed_fw.bin -c 4 -x
```
现在我们可以使用引导日志中的基地址 0x80004000 将其投入Ghidra，并将架构设置为大端 MIPS。
自动分析完成后，现在是时候开始深入挖掘了。幸运的是，有很多调试字符串使得一些函数非常容易识
别。
我开始给我遇到的任何函数命名，使用字符串以及函数签名，结合上下文和任何交叉引用。最终，当进
入一个未知函数时，对已命名函数的交叉引用会给出一些线索，以便最终更容易地理解函数的上下文。
在大多数情况下，我只是在搜索有趣的字符串，比如“调谐器”和“ADC”，并尽可能地理解，随着各种函
数调用带我去的地方，并在一个单独的文本文档中记录有趣的函数、结构、地址和工作原理的理论。
eCos 控制台的一个有用功能是 call命令，它允许您在任意地址调用一个函数，并传递给定的参数。
这使我们能够实际执行一个函数来测试关于其功能的假设。
操作系统上有大量的 Broadcom 代码，全部用 C++编写。这使得反向工程变得更加烦人，因为在函数
调用和多态性方面增加了很多间接性。例如，您经常会看到这样的代码：

```
1. case 0x24:
2. uVar23 = (**(code **)(*piParm1_00 + 0x1c))(piParm1_00);
```
这不仅使代码难以跟踪，还意味着 Ghidra 无法跟踪以这种方式调用的函数的交叉引用。有时可以通过跟踪对象指针直到初始化的位置来确定类，但有时更容易的方法是在使用未知对象的地方补丁一个函数，将指针的值写入已知位置，然后返回。这可以通过 eCos 控制台中的 `write_memory` 命令来完成。然后可以使用 `call` 命令调用包含未知对象的函数，然后使用 `read_memory` 命令从已知位置检索指针。这种类型的技巧以及结合静态和动态分析对于避免陷入困境至关重要。

一些功能在我尝试调用它们时会导致设备崩溃。更仔细的检查显示它们使用了超过 4 个参数，并且使用了 t0、t1、t2 和 t3 寄存器来传递额外的参数。对于 32 位 MIPS 设备来说，这有点不寻常，但事实证明调用约定是由 ABI 和 MIPS 的许多不同 ABI 确定的。很难找到关于确切调用约定的信息，但使用Godbolt，我能够确定 EABI 是最有可能使用 t0-t3 传递额外参数的候选者。不幸的是，Ghidra 似乎不支持 MIPS EABI，但手动设置一些函数的参数寄存器并不太麻烦，参数似乎是唯一的重要区别。

挖掘了一段时间后，我把目光投向了频谱分析仪。虽然代码已经存在，但我从未弄清楚如何启用 Web 界面。我发现了许多其他有用的功能，比如用于设置下行（接收）通道频率的功能，套接字/绑定/监听/发送/接收功能，线程创建功能，以及用于读写调谐器和低噪声放大器寄存器的功能。

# 突破
最终我找到了一个控制台命令，可以对给定频率范围进行带宽测量。

我开始密切关注执行过程，以查看它如何处理频率范围参数，并发现它调用了一个非常熟悉的函数 - 几乎与用于调整下行通道的函数相同，但频率设置的内存映射寄存器地址仅略高于用于正常通道的地址。这表明频谱分析仪使用了一个额外的通道，否则在调谐和设置增益方面与正常下行通道的方式非常相似。

继续进行，测量功能将目标缓冲区的物理地址写入内存映射寄存器，然后在另一个寄存器中设置一个位，并循环直到再次取消设置。然后调用函数，该函数可能计算 FFT，传入缓冲区地址。计算完成后，另一个函数对缓冲区进行一些处理，但保持其原样。

将一根跳线插入同轴连接器充当天线后，我调用了 bandpower 函数，然后在目标缓冲区上执行了 `read_memory`。

```
1. CM> read_memory -n256 0x86fb3e80
2. 
3. 86fb3e80: 00 00 06 8c 00 3f fe 48 00 00 06 41 00 20 00 3d | .....?.H...A. .=
4. 86fb3e90: 00 00 08 56 00 20 02 11 00 00 0a b3 00 20 03 f2 | ...V. ....... ..
5. 86fb3ea0: 00 00 0a 50 00 20 04 84 00 00 06 61 00 20 03 d7 | ...P. .....a. ..
6. 86fb3eb0: 00 00 01 1d 00 20 02 da 00 1f fd f4 00 20 00 4d | ..... ....... .M
7. 86fb3ec0: 00 1f fd 11 00 3f fc 20 00 1f fb 95 00 3f fa ad | .....?. .....?..
8. 86fb3ed0: 00 1f fa 32 00 3f fd fc 00 1f fc a3 00 20 00 cb | ...2.?....... ..
9. 86fb3ee0: 00 00 01 97 00 3f fe b5 00 00 04 0f 00 3f fb 6a | .....?.......?.j
10. 86fb3ef0: 00 00 03 9f 00 3f fb d6 00 00 03 1d 00 3f fe 55 | .....?.......?.U
11. 86fb3f00: 00 00 02 f8 00 3f ff a9 00 00 02 ee 00 20 01 49 | .....?....... .I
12. 86fb3f10: 00 00 03 8f 00 20 04 87 00 00 03 94 00 20 05 09 | ..... ....... ..
13. 86fb3f20: 00 00 01 81 00 3f ff bb 00 1f ff 14 00 3f fa 97 | .....?.......?..
14. 86fb3f30: 00 1f fe 8d 00 3f fc 9d 00 1f ff 89 00 20 01 82 | .....?....... ..
15. 86fb3f40: 00 00 00 be 00 20 00 09 00 00 01 8f 00 3f fa 3a | ..... .......?.:
16. 86fb3f50: 00 00 01 78 00 3f fa 66 00 00 00 7b 00 20 01 35 | ...x.?.f...{. .5
17. 86fb3f60: 00 1f ff 79 00 20 04 f6 00 1f fe e2 00 20 02 62 | ...y. ....... .b
18. 86fb3f70: 00 1f fd 93 00 3f ff 4d 00 1f fa ee 00 3f fe 16 | .....?.M.....?..
```
希望这是 I/Q 数据，看起来很有希望。在 FFT 之后处理数据的函数支持这一点-它检查第一个 32 位字中的 0x00200000 位是否为零，如果是，则丢弃数据的第一个和最后一个字。我假设这个位表示样本是 I 还是 Q 值，如果第一个样本是 Q，则从开头丢弃不匹配的 Q，从结尾丢弃不匹配的 I。例如：

```
1. Case 1: Case 2:
2. Q IQ IQ IQ I IQ IQ IQ IQ
3. 
4. | | do nothing
5. v v
6. 
7. IQ IQ IQ IQ IQ IQ IQ
```

要确定的唯一方法是获取更多数据并对其进行分析。

# 你好，世界

为了使以后的事情变得更容易，我决定编写一个程序，该程序将在调制解调器上运行，调用调谐和带宽功能，然后打开一个监听套接字，并通过 TCP 连接发送缓冲区的内容。我还应该指出，我在这一点上停止了在树莓派上的工作，这样我就不必创建一个 ARM 到 MIPS 的交叉编译器。

编写可以加载并在“几乎裸金属”上执行的代码的基本方法如下。

通过将我们希望使用的外部函数的签名添加到一个头文件中，并使用包含函数地址的链接器脚本，可以轻松编译利用这些函数的程序。此外，为了使程序在加载到预定内存位置时正常运行，并确保入口点位于该地址，需要使用一个部分映射。链接器脚本大致如下：

```
1. memset = 0x80522d7c;
2. memcpy = 0x80004f30;
3. malloc = 0x80596998;
4. printf = 0x8052b178;
5. socket = 0x80332fd0;
6. bind = 0x800ae7bc;
7. listen = 0x80412ed4;
8. accept = 0x80413118;
9. send = 0x80413240;
10. recv = 0x804134bc;
11. tune_aux_channel = 0x80082108;
12. 
13. SECTIONS
14. {
15. . = 0x80810000;
16. .start : { *(.start) }
17. .text : { *(.text) }
18. .data : { *(.data) }
19. .rodata : { *(.rodata) }
20. }
```
它是用以下命令构建的：

```
1. mips-linux-gcc measure.c \
2. -march=mips32 \
3. -mabi=eabi \
4. -msoft-float \
5. -mno-abicalls \
6. -fno-builtin 
7. -nostdlib \
8. -nodefaultlibs \
9. -nostartfiles \
10. -T ./script.ld
```

MIPS CPU 没有 FPU，因此使用 `-msoft-float`。在使用 `-mabi=eabi`时似乎需要 `-mno-abicalls`。 `-fno-builtin`防止编译器通过添加对 `memcpy`等函数的调用来优化某些部分，这将导致未定义符号。 `-nostdlib`和 `-nostartfiles`防止编译器使用标准 C 库中的“crt0.o”入口点，该入口点执行一些我们不关心的设置。

使用 `objcopy`我们可以从编译后的 elf 文件中提取我们关心的部分。

```
1. mips-linux-objcopy -O binary \
2. -j .start \
3. -j .text \
4. -j .data \
5. -j .rodata \
6. a.out bin
```
最后，为了实际加载它，我编写了一个使用 pexpect telnet 登录到调制解调器并使用 `write_memory`命令将二进制文件写入目标地址的 Python 脚本。该程序使用 `call`命令执行。

看看我是否能接收到 FM 广播，我将其调到 100MHz 并获取了一些数据。

使用 numpy、scipy 和 matplotlib Python 库，我能够将数据解释为复值样本，计算 FFT 并绘制出一个漂亮的带通滤波频谱，其中有明显的尖峰。

![2.png](https://www.iotsec-zone.com/api/image/v2/20240828/d3rbkwiu4tc7sayz34.png)

当时我还不是真的相信，但回顾起来，这确实表明我成功地捕捉了复杂的样本，因为如果不是这样，这样的情节是不可能的。

我不打算完全相信，直到我能解调信号并收听 FM 广播。将频谱移动到其中一个尖峰的中心，将其减少以隔离频率范围，并使用我在网上找到的用于复值 FM 的非常简单的解调技术，我能够清楚地看到广播的不同部分，包括（应该是）19kHz 的导频音调。

![3.png](https://www.iotsec-zone.com/api/image/v2/20240828/d3rblfgk80nbiyweet.png)

通过一些实验，我确定每秒 1500 万个样本的采样率将飞行员音调放在 19kHz。这似乎与带功率函数以 7.5MHz 的块进行测量的事实一致。尽管您获得了完整的 15MHz，因为这些是复值样本，但带通滤波器的可用范围更像是 7.5-8MHz，假设 15MHz 的采样率是匹配的。

# 优化
以每秒 1500 万个样本和每个样本占用 8 字节的速度，大约 100MB 的空闲 RAM 中可以存储不到一秒的数据。

一个明显的改进是在填充缓冲区后发送数据，然后捕获更多数据。处理时间和网络吞吐量意味着捕获之间大约有 11 秒的间隔。通过实施一个设置寄存器并启动捕获的新功能，将这个时间缩短到约 5 秒，从而消除了 FFT 计算和其他处理。

经过一些对未知寄存器值的实验，希望找到 会影响采样率的一个位，我发现一个似乎限制了 我和 Q 值到 14 个有效位。虽然它们仍然占用 8 个字节。 每个样本，这意味着我可以将两个样本打包成一个 32 位字。 注意：我不确定 ADC 实际上是否采样了 14/20 位，因为这似乎 相当高，但这是每个样本值的有效大小。

我编写了另一个函数来处理每个捕获，确定它是以 I 值还是 Q 值开头，然后迭代通过缓冲区将每个 I/Q 对打包成一个整数，并将其写入缓冲区中的下一个位置。这样做并没有显著提高性能，但通过仅采用每第 N 个样本，我可以降低有效采样率，缩短处理时间，并减少需要发送回去的字节数，从而大大提高了延迟。

另一个改进是线程处理。我通过一些调试消息找到了用于创建和启动新线程以及用于计数信号量的函数。有了这些工具，我可以有两个或更多的缓冲区。然后一个线程不断地将数据捕获到下一个可用的缓冲区中，然后通过信号量向另一个线程发出写入完成的信号。第二个线程对数据进行打包和降采样，将其发送到网络上，然后发出缓冲区再次可写入的信号。

通过这些改进和采样率降低了 32 倍（降至 464kHz），我可以无限地捕获和发送数据，同时丢失约 12％。我相信这主要是由于捕获完成和“完成”标志设置之间存在几毫秒的固有延迟。此外，我不知道是否有一种方法可以在完成时生成中断或其他内容，因此我必须依靠在 while 循环中休眠，因为这是原始函数中的操作方式。

我希望有某种时钟分频器寄存器，可以降低 ADC 的时钟，从而降低采样率，可能减少延迟并消除后处理时间，但我还没有找到这样的寄存器。

以这种方式进行降采样似乎会丢失很多信息 - 超过噪声底线约 16 倍后，噪声会更高，FM 广播的立体声通道也不再可辨。

尽管在某些应用程序中丢失一些数据是不好的，但它可以相当无缝地流式传输 FM 广播，尽管音频必须稍微减慢，以便不会比接收速度更快地消耗。我还能够接收到当地消防局使用的 154MHz 窄带 FM 广播。

这是使用调制解调器捕获的一段解调音频的简短示例

# 结论
尽管这个项目大部分只是对自己的一个挑战，并不是一个严肃的 SDR，但我对结果感到满意，并希望继续改进它。这句话真的让我产生共鸣，所以再次引用 VK4HAT 的话说：“在生活中可获得的第一次机会很少，抓住那些出现的机会并尝试一下”

声明：文章中涉及的程序(方法)可能带有攻击性，仅供安全研究与技术交流之用，读者将其信息做其他用途，由用户承担全部法律及连带责任，文章作者不承担任何法律及连带责任。
