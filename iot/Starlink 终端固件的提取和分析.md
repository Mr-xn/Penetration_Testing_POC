# Starlink 终端固件的提取和分析
> Rasiel
> 来源：https://www.iotsec-zone.com/article/30

请注意，本文不讨论任何特定漏洞，我们仅记录其他人可用于研究 Starlink 终端的技术。在这篇博文的结尾，我们将介绍固件的一些有趣发现。请注意，SpaceX积极鼓励人们通过其漏洞赏金计划发现和报告安全问题:[https://bugcrowd.com/spacex](https://bugcrowd.com/spacex)

我们首先将我们的终端安装在屋顶的平坦部分并玩了几个小时，让终端和路由器有机会执行固件更新。我们确实运行了一些强制性的速度测试，结果发现下载速度高达268Mbps，上传速度高达49Mbps

![0.png](https://www.iotsec-zone.com/images/MdImg/9b3de8a6711dad958ddbbd99fcc8110f.png)

## 拆解

在玩了几个小时之后，是时候弄脏我们的手并拆卸终端。

网络上有一些终端的拆解视频，但没有一个涉及我们感兴趣的细节--主要的 SoC和固件。尽管如此，这些先前的拆解视频包含许多有用的信息，使我们能够在不造成太大损坏的情况下拆开。似乎现在有一些终端的硬件修订版，拆卸过程的某些部分可能会因修订版而异，这是我们通过艰苦的方式学到的。上述拆解视频之一显示了在移除白色塑料盖之前要从主板上拆下以太网和电机控制电缆。在我们的终端上，拉动电机控制电缆将整个连接器从PCB上拉下来；幸运的是，可以修复。注意，不要拉那些电缆，而是先取下塑料后盖。取下塑料后盖后，我们可以看到覆盖 PCB的金属屏蔽层，除了一个包含以太网电缆和电机控制电缆连接器的小切口。还有一个额外的未填充连接器（4针JST SH 1.0mm），我们假设它包含一个UART调试接口，如图所示。请注意，早期的拆解视频有一个额外的连接器，但我们的终端上没有该连接器。

![1.png](https://www.iotsec-zone.com/images/MdImg/790d700401dfab5abf568783dc1a12e8.png)

![2.png](https://www.iotsec-zone.com/images/MdImg/e09294cc0959664bbcc9c933845e36fa.png)

## UART接口

连接 USB 到串口转换器后，我们可以获得有关终端启动过程的一些信息。在显示以下输出之前，输出包含有关早期引导加载程序的信息。我们可以看到终端正在使用U-Boot引导加载程序，并且提示键入“falcon”可能会中断引导过程。虽然这可以让我们访问U-Boot CLI，但我们还可以看到串行输入被配置为“nulldev”。不出所料，在启动期间通过“falcon”向串口发送信息没有任何作用

![3.png](https://www.iotsec-zone.com/images/MdImg/0ac569446264dc7dbf5b67b607c19f2a.png)

继续引导过程，我们可以看到 U-Boot从存储在嵌入式 MultiMediaCard (eMMC) 上的扁平化uImage 树 (FIT) 镜像加载内核、ramdisk 和扁平化设备树 (FDT)。我们还可以看到正在检查内核、ramdisk 和 FDT 的完整性（SHA256）和真实性（RSA 2048）。虽然我们必须执行更多测试，但似乎从早期ROM引导加载程序一直到 Linux 操作系统都实现了完整的可信引导链 (TF-A)

![4.png](https://www.iotsec-zone.com/images/MdImg/334b708ab1be5eaa782f546ec1a0af0a.png)

引导过程的其余部分包含一些其他有趣的信息。例如，我们可以看到内核命令行参数以及一些分区的起始地址和长度。此外，我们可以看到 SoC包含4个CPU内核

![5.png](https://www.iotsec-zone.com/images/MdImg/392e51474f162527c7b040ecac826778.png)

最后，当终端完成其启动过程时，我们会看到一个登录提示

![6.png](https://www.iotsec-zone.com/images/MdImg/ebdf7447840d889e88b06abcb45f2196.png)

在尝试了一些密码时，我们开始意识到这个UART 接口不太可能轻松登陆进去，不得不更深入研究。终端的后金属盖围绕外边缘粘在组件上，并在金属盖中的肋骨和底层 PCB之间涂上额外的胶水。为了松开金属盖边缘的胶水，我们使用了热风枪、撬具、异丙醇和很大的耐心。具体来说，我们首先对一小部分加热，使用撬具松开该部分，添加IPA以帮助溶解胶水和另一轮撬具。取下金属盖后，映入眼帘的是一块直径约55厘米的巨大PCB

![7.png](https://www.iotsec-zone.com/images/MdImg/b9fc81b69b08498219ad1a9c1c34facd.png)

我们感兴趣的部分如下图所示。带有金属盖的倒装芯片BGA封装是该板上的主要 SoC（型号为：ST GLLCCOCA6BF）。不出所料，SoC 以 eMMC 芯片的形式连接到一些易失性DRAM存储和非易失性闪存存储

![8.png](https://www.iotsec-zone.com/images/MdImg/d7150f9868834baf1d7faad3115688c9.png)

## 识别 eMMC 测试点

嵌入式存储芯片(eMMC) 包含闪存和控制器，与SD卡非常相似。终端包含带有封装标记 JY976 的Micron eMMC芯片，Micron 提供了一种方便的工具来将这些封装标记解码为实际部件号：https : //www.micron.com/support/tools-and-utilities/fbga。有问题的eMMC芯片的部件号为MTFC4GACAJCN-1M，并包含采用 BGA-153 封装的4GB闪存。在大多数情况下，我们会拆焊这样的 eMMC芯片，将其重新封装并使用BGA插槽进行转储。然而，在这种情况下，我们首先尝试在电路中转储eMMC，以尽量减少损坏我们的终端和eMMC芯片的几率。eMMC芯片与SD卡的相似之处在于它们共享相似的接口；eMMC芯片最多支持8条数据线，而SD卡最多支持4条数据线。eMMC芯片和SD卡都支持仅使用单条数据线，但代价是读/写速度较低。

要在线读取eMMC芯片，我们必须识别时钟(CLK)、命令(CMD)和数据 0 (D0)信号。主SoC上方的10个测试点引起了我们的注意，因为10个测试点可能是CMD、CLK和8条数据线。此外，所有这些测试点都有一个30欧姆的串联电阻连接到它们，这对于eMMC连接来说是比较常见的。我们将一条短线焊接到每个测试点，使我们能够在终端启动过程中创建逻辑分析仪捕获。使用这样的捕获，识别所需信号相对简单。CLK信号将是唯一的重复信号，CMD 是时钟开始翻转后第一个激活的信号，D0是发送数据的第一条数据线。幸运的是，确定剩余的7条数据线不需要转储eMMC内容

![9.png](https://www.iotsec-zone.com/images/MdImg/4e3dff76b759726d99833c467e29e1df.png)

![10.png](https://www.iotsec-zone.com/images/MdImg/c992b1692f032fb9f1845f56ae2d7759.png)

## 在主板上转存eMMC

要转存eMMC芯片，我们可以将读取器（支持1.8VIO）连接到已识别的测试点。存在主要用于手机维修的商业阅读器，并且应该可以很好地用于此目的（例如easy-JTAG和Medusa Pro）。或者，您可以使用带有集成电平转换器（例如[https://shop.exploitee.rs/shop/p/low-voltage-emmc-适配器](https://shop.exploitee.rs/shop/p/low-voltage-emmc-适配器)）。如果您周围有一些零件，您也可以自己动手制作一些东西。下图显示了连接到 TI TXS0202EVM 电平转换器分线板的标准USB SD卡读卡器

![11.png](https://www.iotsec-zone.com/images/MdImg/de079dc267c2b0bcc66b48ca492188f2.png)

我们只为eMMC供电，以防止主SoC干扰。eMMC可以通过附近的两个去耦电容器供电，3.3V由SD读卡器提供，1.8V由外部电源供电。一旦一切都正确连接，我们可以创建一个磁盘映像供以后分析。
请注意，在原PCB中读取 eMMC 并不总是一件容易的事；稍微过长的电线将导致读取失败。在这种情况下，它相当简单，即使连接了这些相对较长的电线，系统似乎也能正常运行，至此，成功Dump到了终端固件

![12.png](https://www.iotsec-zone.com/images/MdImg/38cf617b371bc76ab37a873d5a567f83.png)

## 解压原始 eMMC 转存

不幸的是，Binwalk无法识别完整的文件系统，因此需要手动分析。从引导日志中可以清楚地看出，U-Boot从块98304开始加载49152个数据块。这意味着U-Boot从地址0x3000000开始读取0x1800000字节（块大小为512 (0x200)字节）。我们还从U-Boot输出中知道，这块数据是一个FIT镜像。但是，当尝试使用dumpimage工具（u-boot-tools 包的一部分）读取FIT镜像标头信息时，我们没有得到任何有用的信息。

幸运的是 SpaceX在Github上发布了他们对GPL合规性的U-Boot 的修改：https : //github.com/SpaceExplorationTechnologies
通过查看这段代码，很明显固件的某些部分以包含纠错码的自定义格式存储（ECC) 数据。

## 去掉 Reed-Solomon ECC 纠错码

该文件spacex_catson_boot.h包含与设备启动方式相关的有趣信息

![13.png](https://www.iotsec-zone.com/images/MdImg/edd551dd0c7d0a3a2a420633012924e2.png)

Image该片段显示了如何从eMMC( mmc read8)读取数据以及startkernel.h的定义startkernel特别有趣，因为它显示了加载内核的地址是如何传递给名为unecc. 从unecc命令定义可以清楚地看出，此功能正在对从 eMMC 读取的数据执行纠错。

![14.png](https://www.iotsec-zone.com/images/MdImg/31dab08e0cb1a68fa4204194ed341868.png)

该unecc命令调用在中do_unecc实现的函数unecc.c，最终这将导致调用中ecc_decode_one_pass定义的函数ecc.c

![15.png](https://www.iotsec-zone.com/images/MdImg/5ba40bc5ffcc42568b61f9dad17f79af.png)

ecc.h 包含几个相关的定义：

![16.png](https://www.iotsec-zone.com/images/MdImg/f8640b0e43dd9dbd6520ad5b1918c316.png)

最终结论为，在这个实现中，一个受ECC保护的内存块以Magic值开始，SXECCv后跟一个版本字节(1)。这个神奇的值标志着ECC保护数据的开始，也是头块的开始。标头块本身包含（除了关键值和版本字节）215 字节数据、星号(*)和32字节ECC代码字。

头块后面是多个数据块。这些数据块中的每一个都有255个字节长，包含222个字节的数据，后跟一个星号(*)和32个字节的ECC代码字。最后一个数据块包含一个美元符号($)而不是星号，然后是最后一个页脚块。此页脚块以感叹号(!)开头，后跟ECC保护的内存块中的数据字节数（4字节）和对这些数据字节的MD5摘要。

至此，Binwalk 为何没有成功提取内核、initramfs 和FDT的原因就清楚了。Binwalk 能够获取指示特定文件开始的特殊字段值，但文件的每个块都有额外的数据，阻止Binwalk提取它。在使用Binwalk提取镜像之前，我们使用了一个简单的Python脚本来删除额外的ECC数据。同样，我们现在也可以使用 dumpimage 来获取有关FIT镜像的更多信息。

## FIT 镜像和电路板修订版

以下代码段包含一些dump的镜像输出。FIT镜像包含13个引导配置，所有配置都使用相同的内核和 initramfs 镜像，但使用不同的扁平设备树(FDT)

![17.png](https://www.iotsec-zone.com/images/MdImg/3e8d7b7efe54384fe2c93a19bb2a12fe.png)

从U-Boot 代码 ( spacex_catson_uterm.c)可以清楚地看出，引导配置是根据5个GPIO引脚的状态决定的

![18.png](https://www.iotsec-zone.com/images/MdImg/aff23e1d79ab964fc47ea65836d2e72a.png)

下图显示了这些引脚被拉高/拉低以指示电路板修订的位置。请注意，从早期的串行引导日志中，我们的终端使用rev2_proto2配置( case 0b00011)进行引导。在最近的视频中，Colin O'Flynn 将其中一些引脚拉高/拉低，可以观察到终端尝试使用不同的FIT配置启动，因此使用不同的设备树。我们比较了一些FDT，但没有发现任何从安全角度有趣的差异

![19.png](https://www.iotsec-zone.com/images/MdImg/beb5c42a5384079a575d458ee7f173b0.png)

回想一下，在启动过程完成后，我们会看到一个登录提示。对于进一步的研究，获得登录的能力会很有用，允许我们与实时系统进行交互。但是，通过查看镜像文件，很明显不允许任何用户登录。在启动期间，终端确实读取保险丝以确定它是否是测试硬件。如果触点未融合，它将为 root 用户设置一个密码，允许登录。出售给消费者的Starlink 终端当然是融合的，禁用登录提示。

![20.png](https://www.iotsec-zone.com/images/MdImg/c372ab62b89ee064e7f7aadb1b056b47.png)

## 开发硬件

SpaceX 的工程师为了防止终端设备被人拆开破解这种情况，似乎试图主动检测不再受他们控制的未融合开发硬件。开发硬件受地理坐标围栏限制，只能在某些预定义的区域工作，其中大部分显然是SpaceX的位置。如果在这些预定义的地理围栏之外使用开发硬件，SpaceX 可能会收到通知。

![21.png](https://www.iotsec-zone.com/images/MdImg/8e2283b37b0cb78cc53e54b39d4122d6.png)

有趣的是，其中一些地理围栏似乎与SpaceX没有明确的联系。虽然我们不会在这里透露这些位置，但我会说这SNOW_RANCH看起来是一个玩开发硬件的好地方。

## 安全芯片

从固件中的参考可以清楚地看出（我们的修订版）终端包含STMicroelectronicsSTSAFE安全芯片。安全芯片的用途尚不完全清楚，但可用于远程验证终端合法性。

![22.png](https://www.iotsec-zone.com/images/MdImg/bb92dc184df44532a84fa770a4fc9edc.png)

有人肯定关心StarLink使用哪种处理器：答案是四核的Cortex-A53，每个核都被分配了一个特定的任务。

![23.png](https://www.iotsec-zone.com/images/MdImg/7b2ad27e3f4aaa81a59cadd89cdb47f9.png)

暂时就这样，如果有兴趣，我们可能会继续研究Starlink终端，并在未来的文章中提供更多详细信息。在撰写本文时，我们能够在终端上获得一个root shell，但是现在公开分享有关此事的更多信息还为时过早。
