# Atmel SAM Cortex-M7 MCU rom 分析，逆向工程，仿真和模糊化
> heiyu
> 来源：https://www.iotsec-zone.com/article/467

在我的空闲时间，我喜欢探索和分析嵌入式设备，以了解它们的只读存储器是如何工作的。最近，我专注于一款时钟速度为 300MHz 的 Cortex-M7 MCU，具体是（之前的 Atmel）SAM MCU 系列。这些文档完备的 MCU 提供了各种功能，从通用功能到安全功能。然而，当涉及到“安全位保护”功能时，我发现文档不够详细，因此我决定深入研究并为他人记录我的发现。

SAM MCU 的工作原理

SAM E70/S70/V70/V71 系列嵌入了用于 SAM Boot Assistant（SAM-BA）的内部 ROM，始终映射到地址 0x0080 0000。用于用户应用程序的内部 Flash 映射到地址 0x0040 0000。在 SAM MCU 上有增强型嵌入式 Flash 控制器（EEFC），其中包括许多内容之一是通用 NVM位（GPNVM）。MCU 使用 GPNVM 位[1]来确定是否运行 ROM（SAM-BA）还是用户应用程序，通过将其内容映射到地址 0x0000 0000。

那么..

- **SAM-BA**: 由 SAM 产品使用的引导加载程序协议，记录在“SAM-BA Boot Program”中。
- **GPNVM**: SAM E70/S70/V70/V71 设备具有九个通用 NVM (GPNVM) 位，可以通过特定的 EEFC 命令设置或清除。位 1 决定 MCU 在启动时运行 ROM 代码 (0x00800000) 还是用户应用程序 (0x00400000)。GPNVM 位是 EEFC 的一部分，如“增强嵌入式闪存控制器 (EEFC)”章节所述。

![0.png](https://www.iotsec-zone.com/api/image/v2/20240828/d3r9thi761aylipawa.png)
安全位功能

SAM E70/S70/V70/V71 系列具有基于 GPNVM 位 0 的安全位。启用时，此位通过 SW-DP、ETM 和快速闪存编程等接口阻止对 Flash、SRAM、核心寄存器和内部外设的任何访问。这确保了 Flash 中代码的保密性。禁用安全位需要断言 ERASE 引脚并执行完整的 Flash 擦除。

擦除密码

![1.png](https://www.iotsec-zone.com/api/image/v2/20240828/d3r9ty5sn8thfsga59.png)

换句话说，GPNVM 位不是一个熔断配置，设置安全位后重新使用 MCU 的唯一方法是通过硬件执行完全擦除，或者在您的应用程序中实现软件触发器，如Part1中所述。

好的.... 让我们去看看它的 Flash 控制器（EEFC）！

增强型嵌入式闪存控制器（EEFC）

增强嵌入式闪存控制器（EEFC）提供 Flash 块与 32 位内部总线的接口。它在数据表中有记录，但为了更简单，让我们假设我们想要在地址 0x0040 0000 更新用户应用程序内容，序列将是：

![2.png](https://www.iotsec-zone.com/api/image/v2/20240828/d3r9u8tds3j1dgwphz.png)

1. 将内容写入文档地址（0x0040 0000）
2. 请求 EEFC 更新用户应用程序
3. \4. EEFC 从映射内存中读取内容并将其存储到内部 Flash 地址。（EEFC 知道的地址）

并且如果我们想要阅读用户应用程序：

![3.png](https://www.iotsec-zone.com/api/image/v2/20240828/d3r9uur4gw3opeptnw.png)

1. 请求 EEFC 映射用户应用程序
2. EEFC 将从未知地址（仅 EEFC 知道的地址）读取用户应用程序
3. 将数据映射到 0x0040 0000
4. CPU 可以访问用户应用程序

对于其他情况也是一样，比如从[QSPI]中读写数据，它是一个独立的外设，读取唯一标识符..

![4.png](https://www.iotsec-zone.com/api/image/v2/20240828/d3r9ve8v81ifromgqd.png)

1. CPU 使用 EEFC 命令请求数据
2. EEFC 将从页面读取数据
3. EEFC 命令将其映射到已知地址
4. CPU 可以访问这些数据

现在我们更好地了解了 SAM 将如何在地址 0x0000 0000 开始其应用程序，它看起来是这样的：

![5.png](https://www.iotsec-zone.com/api/image/v2/20240828/d3r9vwhv779bnbxeyp.png)

在通电后，通常会加载并执行 BootROM 代码以执行下一步操作，不确定其详细信息，因此我将其标记为黑匣子。

- 用户配置包括 GPNVM 位。

足够的内省，让我们开始吧。

SAM 内存映射：

![6.png](https://www.iotsec-zone.com/api/image/v2/20240828/d3r9wf2rjbfvxzwv2r.png)

理解 SAMx7x 的内存映射至关重要。ROM 代码位于地址 0x00800000 处，具有用于 EEFC 的外围控制器映射到地址 0x400E0C00。每个外围设备都有一个起始地址和中断 ID。

转储 ROM 代码（SAM-BA-）

![7.png](https://www.iotsec-zone.com/api/image/v2/20240828/d3r9wr1q5y5x5nplqq.png)

这是我们用来转储 ROM 代码的设置，起初我们遇到了关于转储 ROM 代码的问题，因为对错误的内存区域的任何访问都会导致 SAM 崩溃并卡在虚拟处理程序中，每当我们尝试转储 0x00800000 以获取大小> 0x4000 时，它都会崩溃，我们是如何知道的 —> 我们编写了一个简单的代码，访问从 0x0080 0000 开始的内存并打印其地址：内容，并看到最后一个被访问的地址。

所以我们只转储了前 0x4000（16KB），结果发现其中包含了 SAM 重复的 ROM 代码-content（0x0<->0x2000）=content（0x2000<->0x4000）-…也许是为了备用。

为了转储 ROM 代码，我们使用了 JLINK 并执行了命令

```
1. SaveBin ROM.bin 0x00800000 0x4000
```

反转 ROM 代码

我们寻找了有关安全位或 JTAG 锁定的参考资料。我们只找到了 SAM-BA 协议的实现。

这是 ROM 代码的向量表。

![8.png](https://www.iotsec-zone.com/api/image/v2/20240828/d3r9xvu49jghencaye.png)

这是 ROM 代码的主要功能，我们只发现了 SAM-BA 协议的实现，如下截图所示。因此，读取安全位并做出关于 JTAG 锁定的决定似乎与内存映射中的 ROM 部分无关。

![9.png](https://www.iotsec-zone.com/api/image/v2/20240828/d3r9y281jb58cpe6kc.png)

这是数据表中提到的 SAM-BA 命令

![10.png](https://www.iotsec-zone.com/api/image/v2/20240828/d3r9y8o922evwuq9l7.png)

![11.png](https://www.iotsec-zone.com/api/image/v2/20240828/d3r9ybqtp022ein3tf.png)

等一下...这不好玩，让我们完全模拟它的原因如下：

- 用 Python 编写
- 支持 STM MCU（cortex-M3/M4）
- 集成 AFL/gdb 调试器/IDA 插件/..
- 在 Telegram 频道上活跃

其他功能可以在他们的 github (https://github.com/qilingframework/qiling) 上找到，不幸的是，没有完美的东西... 他们对 MCU 部分没有任何文档 :|，但它是用 Python 编写的，所以我们可以阅读源代码来理解它。

模拟 ROM 代码
方法：

```
1- 模仿简单示例 —> (入门) ，具有最小功能，例如通过 UART1/USART1 发送消息的循环（ex1）
2- 模拟 UART0 回环示例（发送到 UART0 / 从 UART0 接收）（ex2）
3- 模拟 ROM（只读存储器）
```
ROM 代码将使用 UART0 作为接口：

![12.png](https://www.iotsec-zone.com/api/image/v2/20240828/d3r9zpfg6mz3muc1s8.png)

让我们说它并不简单...调试和追踪事物，以位级别调试寄存器，找到并连接 ASF 延迟函数以模拟延迟操作..

长话短说，我们成功地完全模拟了它，并创建了一个魔法补丁 ! ，以添加所有需要执行此操作的文件。
* 您需要安装 Qiling 要求和 afl-fuzz (https://aflplus.plus/)

补丁文件: [https://github.com/0xB4x/SAME70Emulator](https://github.com/0xB4x/SAME70Emulator)

模仿示例 1

![13.png](https://www.iotsec-zone.com/api/image/v2/20240828/d3ra08zb4v6tatzlgd.png)

ROM 仿真提示：

- SAM 模拟器将默认能够直接与 UART0 在终端模式下通信，或者您可以切换到正常模式

![14.png](https://www.iotsec-zone.com/api/image/v2/20240828/d3ra0nva2syvfwp5dd.png)
- 在命令行中添加 **[-s]** 将使用来自(https://github.com/abcminiuser/sam-ba-loader)的 SAM-BA 客户端工具，我已经集成到仿真器中以便使用。
- 我实现 EFC，因为有一个目录模仿存储在` [PYTHON_PATH]/site-packages/qiling/hw/flash/same70_efc_content/`中的 SAM 存储，目前我只添加了 2 个文件
- **GPNVM.storage** —> 包含 GPNVM 的 9 位
- **UID.storage** —> 包含唯一 SN

![15.png](https://www.iotsec-zone.com/api/image/v2/20240828/d3ra1zdtlx8czrzeca.png)

有许多 EFC 命令：

![16.png](https://www.iotsec-zone.com/api/image/v2/20240828/d3ra272zde2ohhbzb8.png)

我已经实现了使 ROM 代码正常工作的内容，下面的截图显示了您可以修改实现的位置。

![17.png](https://www.iotsec-zone.com/api/image/v2/20240828/d3ra2fm4jrfapxtjip.png)

**SAM-BA 客户端的屏幕截图：**

- 获取模拟 ROM 代码的版本

![18.png](https://www.iotsec-zone.com/api/image/v2/20240828/d3ra2rvrdsvqqm4yov.png)

- 读取 GPNVM 命令

![19.png](https://www.iotsec-zone.com/api/image/v2/20240828/d3ra30bs2ulrtk8xjl.png)

- 信息命令

![20.png](https://www.iotsec-zone.com/api/image/v2/20240828/d3ra3b29ar6znpiarp.png)
使用终端模式的屏幕截图:

![21.png](https://www.iotsec-zone.com/api/image/v2/20240828/d3ra3iq0fx4icf3ntx.png)

- 阅读 ROM 版本

![22.png](https://www.iotsec-zone.com/api/image/v2/20240828/d3ra3wtkm76pndtbdx.png)

- 阅读地址 0x800000 处的第一个单词

![23.png](https://www.iotsec-zone.com/api/image/v2/20240828/d3ra4c6cow7bwff6qa.png)

# 模糊测试
### 步骤：

```
1. 1- cd qiling/examples/fuzzing/same70
2. 2- 在运行 bsah fuzz.sh 之前（打开 fuzz.sh 并将 **python** 路径更改为具有 Qiling 的路径）
3. 3- bsah fuzz.sh
```
我们发现，在 Linux 虚拟机上，模糊测试过程比 macOS 快得多。
- Macos

![24.png](https://www.iotsec-zone.com/api/image/v2/20240828/d3ra5h0eb28scybltp.png)

- Linux 虚拟机

![25.png](https://www.iotsec-zone.com/api/image/v2/20240828/d3ra5rnohxzd8cnqgf.png)

# 结论
通过这次探索，我对 SAM MCU 的安全功能和模拟 ROM 代码的复杂性有了更深入的了解。虽然 Atmel 提供的文档很详尽，但像安全位保护这样的领域需要更多的实地调查。尽管 Qiling 项目最初缺乏文档，但证明是一个有价值的工具，用于模拟和理解 MCU 的行为。这段旅程不仅增加了我的知识，还突显了在嵌入式系统开发中实际实验的重要性。
随意调整任何部分，以更好地匹配您的风格，或添加您认为重要的任何特定细节。

声明：文章中涉及的程序(方法)可能带有攻击性，仅供安全研究与技术交流之用，读者将其信息做其他用途，由用户承担全部法律及连带责任，文章作者不承担任何法律及连带责任。
