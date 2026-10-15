# 基于PCILeech和MemProcFS的DMA攻击浅谈
> ol4three
> 来源：https://www.iotsec-zone.com/article/165

---
![Overview of DMA attacks](https://oss-map.oss-cn-beijing.aliyuncs.com/img/DVhR_cLWsAA52bB.jpg)

## 0x00 DMA攻击

> ​	DMA攻击是一种侧信道攻击，即攻击者可以通过利用高速扩展端口，穿透计算机和操作系统，直接读取DMA，DMA包含在许多连接中，DMA可以通过例如便携式摄像机、网卡、存储设备或者其他可直接读取或写入主内存的互动设备。此类设备的合法使用已导致DMA连接广泛，攻击者可以采用工具连接到DMA接口，绕过操作系统的安全机制和屏幕密码等，来访问部分或者全部的计算机物理内存地址，读取计算机的所有工作，窃取数据和加密密钥，安装运行间谍软件和其他漏洞利用程序，或者修改系统以允许后门或其他恶意软件

允许DMA攻击的设备包括：FireWire、CardBus、ExpressCard、Thunderbolt、PCI和PCI Express

首先放一张图来总结
![0.png](https://www.iotsec-zone.com/images/MdImg/6e1e4ca364b6973c2933fc7a04089cb4.png)

## 0x01 DMA 是什么

> DMA(Direct Memory Access，直接存储器访问) 是所有现代电脑的重要特色，它允许不同速度的硬件装置来沟通，而不需要依赖于 CPU 的大量中断负载。否则，CPU 需要从来源把每一片段的资料复制到暂存器，然后把它们再次写回到新的地方。在这个时间中，CPU 对于其他的工作来说就无法使用。

​	正常情况一般只有CPU才能进入主存，现在加了DMA，直接在I/O设备和主存之间打通了一个通路，用来减少CPU的负担。如果出现DMA和CPU同时访存的情况，DMA优先级更高，当两者争抢时CPU是DMA的小弟卧槽 好家伙我TM直接好家伙。

那么CPU和DMA同时访问主存就会出现一下三种情况：

### 	

​	**1.CPU停止访问主存**

​			a.CPU放弃地址线的使用权
​			b.CPU放弃数据线的使用权
​			c.CPU放弃控制线的使用权

![image-20201203193831422](https://oss-map.oss-cn-beijing.aliyuncs.com/img/image-20201203193831422.png)

优点: 控制简单，它适用于数据传输率很高的设备进行成组传送。

缺点: 在DMA控制器访问内存阶段，内存的效能没有充分发挥，相当一部分内存工作周期是空闲的。这是因为，外围设备传送两个数据之间的间隔一般总是大于内存存储周期，即使高速I/O设备也是如此。例如，软盘读出一个8位二进制数大约需要32us，而半导体内存的存储周期小于0.5us，因此许多空闲的存储周期不能被CPU利用。



​	**2.周期挪用**

​	DMA请求时，I/O设备挪用或者窃取总线占用权一个或几个主存周期

![image-20201203193850311](https://oss-map.oss-cn-beijing.aliyuncs.com/img/image-20201203193850311.png)

I/O设备要求DMA传送时可能遇到两种情况：

​			(1)此时CPU不需要访内，如CPU正在执行乘法指令。由于乘法指令执行时间较长，此时I/O访内与CPU访内没有冲突，即I/O设备挪用一二个内存周期对CPU执行程序没有任何影响。

​			(2)I/O设备要求访内时CPU也要求访内，这就产生了访内冲突，在这种情况下I/O设备访内优先，因为I/O访内有时间要求，前一个I/O数据必须在下一个访问请求到来之前存取完毕。显然，在这种情况下I/O 设备挪用一二个内存周期，意味着CPU延缓了对指令的执行，或者更明确地说，在CPU执行访内指令的过程中插入DMA请求，挪用了一二个内存周期。 与停止CPU访内的DMA方法比较，周期挪用的方法既实现了I/O传送，又较好地发挥了内存和CPU的效率，是一种广泛采用的方法。但是I/O设备每一次周期挪用都有申请总线控制权、建立线控制权和归还总线控制权的过程，所以传送一个字对内存来说要占用一个周期，但对DMA控制器来说一般要2—5个内存周期(视逻辑线路的延迟而定)。因此，周期挪用的方法适用于I/O设备读写周期大于内存存储周期的情况。

3.DMA和CPU交替访问

​			适用于CPU的工作周期比主存存取周期长的情况。这样可以将CPU的周期拆分成两部分，前一部分用于DMA访存，后一部分用于CPU访存

![image-20201203194201769](https://oss-map.oss-cn-beijing.aliyuncs.com/img/image-20201203194201769.png)

​			这种传送方式又称为“透明的DMA”方式，其来由是这种DMA传送对CPU来说，如同透明的玻璃一般，没有任何感觉或影响。在透明的DMA方式下工作，CPU既不停止主程序的运行，也不进入等待状态，是一种高效率的工作方式。当然，相应的硬件逻辑也就更加复杂。
## 0x02 PCILeech 和MemProcFS的攻击利用
我们发现在DMA和CPU同时进行内存访问的情况下，DMA的优先级会更高，我们便可以硬件设备模拟DMA请求来进行内存访问
![1.png](https://www.iotsec-zone.com/images/MdImg/39223ae50d3c00edfa0f4e8dc636e478.png)
同时我们可以使用很多不同的设备去模拟PCIE请求来进行内存访问
![2.png](https://www.iotsec-zone.com/images/MdImg/7c9e197df075757a575b272d09def161.png)
同时在github也开源了PCILeech和MemProcFS的利用脚本
[PCILeech](https://github.com/ufrisk/pcileech "PCILeech")
同时在windows系统下给出了GUI工具
![3.png](https://www.iotsec-zone.com/images/MdImg/1bb732657189d457d0d8d87e9e79e1b1.png)
我们这边使用测试板子如下
![4.png](https://www.iotsec-zone.com/images/MdImg/ae22712bfe4b91c9f30318c40777542e.png)
### Linux攻击方式
首先连接设备进行内存扫描
![5.png](https://www.iotsec-zone.com/images/MdImg/17fba120adc55c0a19ce48155e168fb3.png)
扫描成功后加载KMD地址，并将Linux内存挂载到本地的K盘
![6.png](https://www.iotsec-zone.com/images/MdImg/5c97e0bebdccb93a27b59135252f0326.png)
![7.png](https://www.iotsec-zone.com/images/MdImg/0ecf27b0c49e424805c043b8ff5b1182.png)
我们可以去读取几乎所有的文件比如读取\etc\shadow文件如下
![8.png](https://www.iotsec-zone.com/images/MdImg/2e1b57a9ffa03ed585e3944c5d12050c.png)
### Windows 攻击方式
环境如下
```
Intel NUC
ScreamerM2
```
![9.png](https://www.iotsec-zone.com/images/MdImg/0ae1aa0472e00eaf73fd4970af068acb.png)
在windows系统上我们同样可以挂载内存到本地的K盘
![10.png](https://www.iotsec-zone.com/images/MdImg/429113b0b1c3b41f1263af110b00f42a.png)
获取System权限并建立用户进行登录
![11.png](https://www.iotsec-zone.com/images/MdImg/44bec4e8030337ab105c82b9e765531f.png)
获取系统进程信息
![12.png](https://www.iotsec-zone.com/images/MdImg/d266d2ef02ace5fbe766b12d2b435d35.png)
获取SAM哈希存储信息
![13.png](https://www.iotsec-zone.com/images/MdImg/93d9c4fcfbd679e0ccadd963755e2b96.png)
获取系统日志信息等
![14.png](https://www.iotsec-zone.com/images/MdImg/907ee0e5b47c76a4e9ebaa7f51399016.png)
同时也可以进行一些有趣的操作比如Bypass锁屏密码，动态修改Notepad显示内容等
### 利用姿势优化
PS:很多时候我们测试需要插入PCIE或者M2接口导致比较麻烦，或者M2接口可能失效的情况下我们可以去使用M2延长线
![15.png](https://www.iotsec-zone.com/images/MdImg/ce7f35185fac1a81fb55043a133ed2bd.png)
或者使用Thunderbolt3 转接装置，将PCIE和M2接口转换为thunderbolt3 同时也涉及了Thunderspy攻击利用
![16.png](https://www.iotsec-zone.com/images/MdImg/e9bacef3881f1f0b27207869a0b9b166.jpg)
![17.png](https://www.iotsec-zone.com/images/MdImg/3e1b1bab7dfffa8ee9f31524d6dacec1.png)
同样对Thunderbolt3的 安全讨论在下文进行简单描述
在ThunderSPY的官网提供了漏洞的检测工具
![18.png](https://www.iotsec-zone.com/images/MdImg/d82a4e60e745de3c1707d83ef8bc7ad2.png)
同样的DMA利用方式还有：
[火线接口的DMZ攻击](https://github.com/carmaa/inception "火线接口的DMZ攻击")同样也可以进行火线转Thunderbolt3的攻击方式
## 0x03 Thunderbolt 3 安全等级

**无安全性（SL0）**

> 在位于SL0模式时，任何Thunderbolt 3设备连接后将立即开始工作。此模式的危险在于，由于Thunderbolt 3支持PCIe，并且PCIe允许直接访问系统内存，因此恶意的Thunderbolt 3设备可以访问系统内存中的潜在敏感数据，而在SL0模式下，只需要简单的插入设备。

**用户授权（SL1）Default**

> 连接Thunderbolt 3设备时，用户必须响应弹出对话框以明确允许连接。用户可以选择允许一次或始终允许该特定设备。这减轻了上述SL0风险。

**安全连接（SL2）**

> 与SL1相同，不同之处在于，如果用户选择始终允许特定设备，则系统会向该设备写入加密密钥，并将其记录在其自己的固件中，以执行更强大的“身份验证”使用质询/响应机制在后续连接上对该设备的性能进行评估。这样可以防止攻击者获取已被授予“始终允许”访问权限的外围设备的设备ID并将其克隆到恶意设备上，这在SL1模式下将允许该恶意设备获得“始终允许”访问权限。但是，并非所有的Thunderbolt 3外设都支持SL2。

**仅DisplayPort和USB（SL3）**

> 通过Thunderbolt 3允许DisplayPort流量，但不允许PCIe。
>
> 如果设置安全模式为SL3，并且连接到实际的Thunderbolt 3扩展坞，则将获得视频输出，但将无法使用通过扩展坞的USB控制器运行的任何USB 3.x端口或其他扩展坞功能。（通常包括所有其他端口，以太网，音频等）

**Daisy chaining disabled / USB docks only (SL4)**



![image-20200514221739727](https://oss-map.oss-cn-beijing.aliyuncs.com/img/4729ovyQtZWmVOd.png)



> SL4 会禁用thunderbolt菊花链，而不是DisplayPort菊花链。
>
> 在SL4模式下，允许设备使用PCIe，但仅允许链中的第一个Thunderbolt 3设备。链下游的thunderbolt设备将不允许使用PCIe。
>
> 此模式旨在防止恶意的Thunderbolt外围设备通过受信任的设备（例如扩展坞）来访问系统。

**内核DMA保护**

> 此模式需要系统固件，操作系统，驱动程序和Thunderbolt 3外围设备的支持。
>
> 内核DMA保护使系统仅允许外围设备直接访问系统内存的指定部分，从而降低了风险。
>
> 如果系统支持内核DMA保护，但所连接的特定Thunderbolt外围设备不支持它，则该系统将退回到该特定设备连接（通常为SL1）

## 0x04 攻击方式

1. 对于默认采用了SL1的设备，可以通过其主板上的SPI接口dump出Thunderbolt接口控制的固件，对固件进行修改并写回，以此将SL1降级为SL0。

   p.s. 在对设备进行写SPI闪存进行降级的时候，可以将审批闪存设置为只读，这样用户就无法通过BIOS更改 Thunderbolt接口 的安全等级。

2. 降级成功后通过Thunderbolt接口连接被攻击的设备，执行DMA攻击（PCILeech 攻击程序）

   > PCILeech部分功能:
   >
   > - 可以通过>150MB/s的速度检索内存
   > - 将数据写入目标内存
   > - 将活动的RAM挂载位文件
   > - 将文件系统挂载为驱动器
   > - 在目标系统上执行内核代码
   > - 解锁系统

PCILeech攻击使用PCIe硬件设备读取和写入目标系统内存。这是通过在PCIe上使用DMA来实现的。目标系统上不需要驱动程序。

PCILeech还可以在没有硬件的情况下运行，并可以使用LeechCore库支持的多种软件内存获取方法-包括使用DumpIt或WinPmem捕获远程实时内存。PCILeech还支持本地捕获内存和多种内存转储文件格式。

支持多个内存采集器比如：

1.基于USB3380的硬件（基于USB3380的硬件只能本地读取4GB内存，但是如果首先将内核模块(KMD)插入目标系统内核，则可以读取所有内存。）
2.基于FPGA

支持的目标系统：

```
	UEFI
	Linux
	FreeBSD
	macOS（不支持macOS High Sierra及更高版本）
	Windows
```

​	这需要有内存（USB3380硬件，FPGA硬件或CVE-2018-1038“ Total Meltdown”）的写访问权。

## 0x05 安全思考

1.设备位于SL1模式下，是否可以 窃取\克隆 已经获得授权的设备ID，以此获得无提示的设备接入。
2.针对上一点作出防御的SL2模式，如果在THunderbolt 3外设不支持SL2的情况下会自动降级到SL1。攻击者完全可以随心所欲降级。SL2如果不是强制实施的话等于无效

## 0x08 如何缓解

BIOS中启用VT-d(IOMMU)防护DMA攻击
![19.png](https://www.iotsec-zone.com/images/MdImg/58cf8b4cc9a95dc6fed87a87fe721797.png)
比如可以使用[HelloIommuPkg](https://github.com/tandasat/HelloIommuPkg "HelloIommuPkg")是一个运行时DXE驱动程序，可以使DMA重映射并保护它的第一页（PE头）从DMA读取和写入。
加载命令后的成功保护
![20.png](https://www.iotsec-zone.com/images/MdImg/9a19e271b3db4db7d3588b219fa75102.png)
使用PCILeech进行检测
![21.png](https://www.iotsec-zone.com/images/MdImg/ff20044b252bb42264a32bd09defe502.png)
受保护之后如下
![22.png](https://www.iotsec-zone.com/images/MdImg/226304b908c3bf7ebd5ab7cd4a776397.png)
通过使用[RWEverything](http://rweverything.com "RWEverything")报告的故障记录寄存器，可以确认DMA确实由于缺少读取权限而被阻塞。
![23.png](https://www.iotsec-zone.com/images/MdImg/28c3d8f139fa3bb1ea9e811c73568ebb.png)
· 第一列表示故障地址（0x6ff48000）

· 第三列表示请求设备的源ID（总线6：设备0：功能0）

· 第四列中的6表示缺少读取权限Intel 处理器 VT-d 架构 Kernel DMA 保护机制研究
![24.png](https://www.iotsec-zone.com/images/MdImg/d5e7b9e0208d016f9ca156ab9861d827.png)
