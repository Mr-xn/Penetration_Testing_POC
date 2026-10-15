# Bus Pirate 5：硬件黑客的瑞士军刀
> heiyu
> 来源：https://www.iotsec-zone.com/article/461

# 介绍
Bus Pirate 是一个开源硬件黑客平台，旨在与各种协议和硬件接口进行接口，作为硬件黑客的“瑞士军刀”。我总是随身携带一个，因为你永远不知道什么时候会发现自己试图黑掉一些电子设备，需要一些支持 JTAG 或其他协议的工具。Bus Pirate 最初发布于 2008 年，随后在 2009 年推出了 v3，然后在 2011 年推出了 v4。每次都有各种改进和附加功能。Bus Pirate 5 的开发已经进行了一段时间，最终于 2024 年推出。Bus Pirate 5 具有一些显著的特点，包括：

- 硬件平台（和固件）已移植到 RP2040

- 液晶屏幕，包括连接细节（包括电压）

- 1 Gbit NAND 闪存芯片，可通过 SPI 总线访问，也可作为 USB 存储设备访问

- 十八个可编程 LED 灯

- 连接器配置的几种不同选项

![0.png](https://www.iotsec-zone.com/api/image/v2/20240820/d3krzgex29w2ht4vde.png)

我的 Bus Pirate 5 刚刚到达不久。

Bus Pirate 是由 Dangerous Prototypes 的 Ian Lesnet 设计的。一定要收听最近在 Unnamed Reverse Engineering Podcast 上与 Ian 的播客采访 - 第 69 集 - 罐装奶酪和洋葱圈（他们解释了罐装奶酪和洋葱圈的参考，以及其他几个食物参考）。

我已经在各种小型项目和调试练习中使用了 Bus Pirate 5，并发现各种电缆套件非常有用。以下套件可用：

- 探头电缆套件 - 探头钩对不同类型的应用非常方便，虽然我还没有使用过铣制的面包板适配器引脚，但它们确实很整洁（甚至在中间是方形的，而不是圆形的，所以它们不会从桌子上滚下来）。
- 辅助电缆套件 - 我真的很喜欢颜色编码的压接外壳，特别是当您连接到狭窄空间中的引脚时。
- SPI Flash 适配器 - 遗憾的是，当我下原始订单时没有订购这个，现在正在等待它的到货。
- KF141 快速连接适配器带丝印 - 有时您需要快速连接和断开电线，这个适配器具有弹簧保持夹和清晰标记的连接点。

# 访问和更新固件
要访问 Bus Pirate，我喜欢使用“tio”（适用于 Linux/MacOS/Windows），访问如下：

$ **tio /dev/ttyACM0 -b 115200**

[12:10:06.750] tio v3.3 [12:10:06.750] 按下 ctrl-t q 退出 [12:10:06.751] 连接到 /dev/ttyACM0

VT100 兼容的彩色模式？（Y / n）> Y

Bus Pirate 会询问您是否要启用彩色模式，这很方便，因为终端中的颜色与电缆连接上的颜色相对应。使用“i”命令获取正在运行的固件版本：

![1.png](https://www.iotsec-zone.com/api/image/v2/20240820/d3ks12x33yhqjhu6iq.png)

接下来，您可以从 Bus Pirate 论坛下载最新版本的固件。固件发布是定期进行的，因此在开始与硬件进行接口操作之前最好先检查一下。使用“$”命令将 Bus Pirate 置于引导加载程序模式：

![2.png](https://www.iotsec-zone.com/api/image/v2/20240820/d3ks1k7az3kyiz6tus.png)

接下来，将固件复制到出现的驱动器上，并等待设备重新启动。然后再次运行“i”命令，并验证升级是否成功：

![3.png](https://www.iotsec-zone.com/api/image/v2/20240820/d3ks1u1qmce6s1oavf.png)

# 基本任务：UART
虽然有几种不同的选项可以与 UART 进行接口，但我喜欢 Bus Pirate 5，因为圆形的热缩连接器非常通用，可以连接到不同类型的引脚排针（甚至是间距较小的引脚排针），LCD 显示屏使得轻松监控电压（是的，您也可以使用万用表，但使用同一设备实时监控并始终显示电压也很方便）。我将 GND、TX 和 RX 连接到了树莓派。

![4.png](https://www.iotsec-zone.com/api/image/v2/20240820/d3ks28lkukpfbhlhbd.png)

注意：阅读连接到的板子的文档，以便提供正确的电压。在树莓派 3 型 B 型上，您通过 USB 供电，而不是通过引脚连接上的电源连接，否则可能会释放“魔法烟”。

接下来，我进入了 UART 模式，设置了正确的设置，启用了电源，并触发了 UART 桥接，以查看树莓派的引导消息（并获取串行控制台）：

![5.png](https://www.iotsec-zone.com/api/image/v2/20240820/d3ks2irzrsahfaby1g.png)
您需要进行一些额外的设置来复制此设置，具体取决于您使用的树莓派型号和选择安装的操作系统。这篇名为“在树莓派上启用 UART：逐步指南”的文章是一个很好的起点。我也使用了类似的设置来访问树莓派 5 调试端口上的 UART 功能。为此，我购买了一套售价 12.00 美元的树莓派调试探针套件，其中包含了用于 UART 和 SWD（串行线调试）的硬件（RP2040）以及适当的电缆和连接器。您可以使用上述套件中附带的电缆，通过杜邦线和连接器将总线海盗连接到树莓派 5 调试端口（注意：您可能还想再购买一些这些电缆，以便与 3 针调试端口进行接口连接和备用）。

# 读取 SPI 闪存
我可以访问一些使用 Winbond SPI 闪存芯片的旧退役 PC，这些芯片通过 DIP（双列直插封装）连接，易于取下进行测试。使用专为此任务设计的 SPI 闪存读写器是最佳选择（例如来自 Dediprog 的这款产品，尽管价格要高得多）。然而，我想测试使用 Bus Pirate 读取 SPI 闪存芯片，我的 Bus Pirate SPI 闪存读取套件尚未到货，因此我使用了一个变通方法：

![6.png](https://www.iotsec-zone.com/api/image/v2/20240820/d3ks2yw4kayu0zbqxz.png)
再次强调，这并不是推荐的方法，但我可以证明它确实有效（但请温柔！请参阅下面的披露部分）。我有几颗 Winbond W25Q64 芯片要读取，这是一种标准的 SPI 闪存芯片，文档齐全。我将 Bus Pirate 设置为读取这个特定芯片，在仔细连接引脚到正确引脚后，确保只有需要电压的引脚接收到正确的电压，否则你会让“魔法烟”出现：

![7.png](https://www.iotsec-zone.com/api/image/v2/20240820/d3ks36kww3nnrhibvo.png)

接下来，我在 VCC 连接上启用了电压和上拉电阻，以将电源发送到正确的位置：

![8.png](https://www.iotsec-zone.com/api/image/v2/20240820/d3ks3e49v3laqg8ux7.png)

接下来，我使用“flash”命令读取了 SPI 闪存芯片的内容：

SPI> **flash read -f spidump.bin**

![9.png](https://www.iotsec-zone.com/api/image/v2/20240820/d3ks3o2013yzfs2fvm.png)

并成功地将内容读入上述指定的文件中：

![10.png](https://www.iotsec-zone.com/api/image/v2/20240820/d3ks3vuxc58li899lo.png)

文件然后存储在内部闪存中

![11.png](https://www.iotsec-zone.com/api/image/v2/20240820/d3ks43x1uvg6qws9kn.png)

断开与 Bus Pirate 串行控制台的连接应该允许您的操作系统读取 Bus Pirate 上的内部存储器以传输文件（尽管这个功能存在一些已知的错误）。然后，我使用 UEFITool 验证了我得到了一个 UEFI 转储文件：

![12.png](https://www.iotsec-zone.com/api/image/v2/20240820/d3ks4diysj82qdrqxl.png)

# 总线海盗技巧

- 文件系统访问可能有点“奇怪”。当您连接到 USB UART 时，可以通过终端界面访问内部存储。如果您断开连接，内部存储应该显示为连接到计算机的驱动器。我不得不将总线海盗从 USB 断开，然后重新连接到计算机，以便复制 SPI 闪存转储。
- 有一次，无论是通过 USB UART 还是我的电脑，都无法读取内部存储。我不得不重置设备并重新刷写固件。
- 如果您按住背面的按钮，然后通过 USB 插入它，它将进入引导加载程序模式，并允许您重新刷新固件（我曾经这样做过）。
- 务必查看文档，以确保正确连接和适当电压，对于 SPI 闪存，请查看 SPI 协议命令和演示 W25Q64 SPI 闪存板。

# 结论
Bus Pirate 5 是一个方便携带的设备（以及各种电缆和连接器），可用于与各种平台和连接器进行接口。用户应该勤于检查最新的固件更新，因为开发非常活跃，通常每周发布新的固件。尽管存在一些小问题，但 Bus Pirate 5 对许多不同的硬件黑客项目和调试固件/硬件问题非常有用。

# 披露
很遗憾，在撰写这篇博客文章时，芯片受到了损害。我正在处理的 SPI 闪存芯片上的引脚非常脆弱。再次建议您使用上述硬件套件，而不是直接将桶连接器连接到 SPI 闪存芯片！

![13.png](https://www.iotsec-zone.com/api/image/v2/20240820/d3ks5o19het69japbu.png)

声明：文章中涉及的程序(方法)可能带有攻击性，仅供安全研究与技术交流之用，读者将其信息做其他用途，由用户承担全部法律及连带责任，文章作者不承担任何法律及连带责任。
