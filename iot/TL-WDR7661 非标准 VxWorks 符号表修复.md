# TL-WDR7661 非标准 VxWorks 符号表修复
> 朝阳
> 来源：https://www.iotsec-zone.com/article/529

# 简介
TP-Link TL-WDR7661 (AC1900) 固件逆向：非标准 8 字节符号表恢复实战简介：本次分析对象为 TP-Link 旗下的 AC1900 级双频千兆路由器 TL-WDR7661。该设备在 TP-Link 的 VxWorks 方案产品线中极具代表性。我们将通过对内核固件的深度剥离，复现其从“二进制黑盒”到“语义化代码”的恢复过程。
关键突破：本文在参考 Black Hat Asia 2019 关于《Dive into VxWorks Based IoT Device》修复方法论的基础上，深入剖析了该设备特有的 8 字节符号条目结构，并实现了函数名的全量恢复。 

# 一、多工具比对与符号特征 
我们先拿到固件进行解包，这里可以使用binwalk2和binwalk3解包，使用binwalk2解包内容会更多，binwalk3跑完的结果只会出现内核和几张图片，但是符号表是找不到的，binwalk2解包是完整的。
binwalk2解包查询。

![0.png](https://www.iotsec-zone.com/api/image/v2/20260123/dfw11g1wcir4ynxjlb.png)
binwalk3解包结果。
![1.png](https://www.iotsec-zone.com/api/image/v2/20260123/dfw125szqyutjz9b5p.png)
接下我们就去这个192D02去找找符号表。

# 二、基址校准与数据分析
“针对 VxWorks 5.5 内核的深度校准”
在处理 TL-WDR7661 (AC1900) 固件时，最核心的挑战在于该设备搭载的 VxWorks 5.5 并非完全遵循标准。
1. 基址差异： 参考 Black Hat Asia 2019 关于《Dive into VxWorks Based IoT Device》的研究，标准案例往往加载于 0x80001000。但根据对 WDR7661 启动序列的审计，我发现其 VxWorks 内核 实际上被锚定在 0x40205000 这一逻辑基址上。
2. 结构体变异： 传统的 VxWorks 恢复脚本通常按 16 字节步长寻找符号条目，但本固件为了优化性能，对 VxWorks Symbol Table 进行了结构压缩，改为 8 字节步长。

正如研究者在 PPT 中展示的对比（见图）：  
错误加载（Load to 0x00）：若按 IDA 默认的 0x00 地址加载，函数窗口全是 sub_xxxx，且代码中的内存偏移全部失效，导致反汇编逻辑一团乱麻。
正确加载（Load with Correct Address）：案例中展示了加载到 0x80001000 后的效果，代码引用恢复正常，这证明了基址对还原系统语义的决定性作用。

![2.png](https://www.iotsec-zone.com/api/image/v2/20260123/dfw132drdkl104e0j0.png)
左侧的错误加载，如果我们把固件丢给IDA，它默认会从0x00开始排地址，我们会看到函数名全是sub_12F0这种很小的数字，由于VxWorks固件是为高位内存编译的，这种加载方式会导致所有的绝对跳转和变量引用全部报错。
右侧正确加载，根据之前在启动代码发现的线索，手动修改起始地址。

![3.png](https://www.iotsec-zone.com/api/image/v2/20260123/dfw138tepbaasxxozy.png)
编译符号表在VxWorks5.5镜像中。
“在 VxWorks 5.5 标准结构中，每个符号条目固定为 16 字节，内存布局如下： 

![4.png](https://www.iotsec-zone.com/api/image/v2/20260123/dfw13b0j96eii2wslr.png)
因此我们整个恢复的流程就大致清晰，寻找基址->寻找符号表文件并分析数据结构->导入到内核文件。

# 三、 固件加载地址与内存布局重构 
在处理WDR7661这种Binary Blob(无格式二进制块)时，确定加载地址是静态分析的前提，如果地址设置错误，所有指针引用、字符串跳转和跳转指令都将失效，导致IDA无法正确解析逻辑。

## 1、关键情报：从BootLoader日志中寻找线索

对于WDR7661而言，我们不需要盲目测试，串口依据清晰记录了系统的跳转地址:

![5.png](https://www.iotsec-zone.com/api/image/v2/20260123/dfw13x90oq14jjuuja.png)

通过对WDR7661启动全过程的串口监控，我们捕捉到两条关键的底层指令：
需要注意的是，串口日志中的 0x30028000 是 Bootloader 在 RAM 中加载内核的 物理地址。而我们在符号表中观察到的 0x40205000 则是系统开启 MMU 后的 虚拟映射地址（逻辑基址）。在进行静态分析时，IDA 的加载基址必须设置为 0x40205000，否则所有的全局指针跳转都会指向错误的内存空间  。

## 2、衔接VxWorks启动逻辑：寻找usrInit
因为VxWorks采用usrInit进行栈初始化，usrInit是VxWorks系统引导后运行的第一个函数，因此我们使用IDA去寻找usrInit，但我们需要把原始固件拖到IDA，然后把基址设置为0。

![6.png](https://www.iotsec-zone.com/api/image/v2/20260123/dfw149jxvlxwux8pdh.png)
我们参考一篇BlackHat文章得知：
修复IDA加载环境的标准，具体说了以下三点，确定正确的加载基址(Load Address)途中标注了Correct load address is 0x80001000。在ARM架构中，观察ROM:0000004C之后的指令，如果这些代码操作0x80xxxxxx范围的内存，说明基址就在这个区间。
但在此之前我们要确定内核文件，通常情况下是解包后最大的那块lzma数据解包的文件。

![7.png](https://www.iotsec-zone.com/api/image/v2/20260123/dfw14cv093x9g6hrja.png)
他有3.9M，几乎占据了整个固件的大小，可以猜测他就是VxWorks的内核。
在我们将解包后的内核文件以 0x0 基址载入 IDA 后，通过对起始代码段（ROM:00000000）的汇编指令审计，直接锁定了固件的真实运行基址。  

![8.png](https://www.iotsec-zone.com/api/image/v2/20260123/dfw14ibr3bt5oaog87.png)

## 3、符号表深度解析
我们使用bzero时，能找到这样一个文件。

![9.png](https://www.iotsec-zone.com/api/image/v2/20260123/dfw14sukxvzngylf02.png)
我们可以把它拖到winhex中去寻找线索。

![10.png](https://www.iotsec-zone.com/api/image/v2/20260123/dfw14y4p2576aapcrs.png)
就在这里面我们能发现有sysInit的身影，作为硬件初始化的第一站，它标志着固件从通用引导阶段进入了特定硬件的配置阶段。还有sysMmapSwitch， 该函数的出现证实了 WDR7661 在内核启动中存在复杂的虚拟地址映射行为。它不仅负责开启 MMU，还负责将内核镜像正式“锚定”在 0x40205000 这一逻辑基址上。  
并且我们也能看到wrs_kernel_text_start的字样。

![11.png](https://www.iotsec-zone.com/api/image/v2/20260123/dfw155i93q2dqinbhd.png)
就在符号表中也似乎找到了基址的身影，但我们没有证据去证实，但可供参考来寻找基址。
能看到有着规律不断增加，并且也能联想到是以0x40205000为基准不断递增。

## 4、架构确定
使用binwalk -A参数进行特征码匹配。

![12.png](https://www.iotsec-zone.com/api/image/v2/20260123/dfw15fp2ilb0fsu6wh.png)
结果显示，在文件头部区域发现了大量连续ARM 32-bit Little Endian指令特征。
日志中明确输出了 Architected cp15 timer(s)  ，CP15是ARM架构的核心控制协处理器，负责MMU和缓存管理，是判定ARM架构的标志。

![13.png](https://www.iotsec-zone.com/api/image/v2/20260123/dfw15ihx5p5n86z4sg.png)

# 四、内核基址校准：基于绝对地址引用的反推  
当我们设置为正常基址后发现函数恢复了正常，接下来我们就需要寻找符号表进行修复。

![14.png](https://www.iotsec-zone.com/api/image/v2/20260123/dfw15ttbsr5vux4y6i.png)

## 1、利用符号表修复函数名
在此之前我们找到了符号表的文件，找到了内核文件，接下来就是去找他的映射。

![15.png](https://www.iotsec-zone.com/api/image/v2/20260123/dfw166cp4ecr4i5an2.png)
我们定位一下符号表的位置，能找到有bzero字样。
但我们接下来会遇到一个难点，就是这个16字节结构体的逻辑从而建立符号表文件(字典)与内核内存(代码)之间的底层逻辑映射。

## 2、映射协议破译  
我们看这一行：54 00 00 08 40 20 50 00 54 00 00 1F 40 20 50 00，一个完整的符号条目，8字节一组，后四字节是40205000是基址，这个表的特征就是有规律的往下走，猜测这是符号的内核运行的绝对内存地址。
前四字节54000008或5400001F，高位字节几乎不变，只有末尾在变化(08->1F->35->57)。

### 2.2、结构体猜测
我们先下一个猜测，这实际上是连续的8字节的条目紧密排列，并且遵循一定的格式。

![16.png](https://www.iotsec-zone.com/api/image/v2/20260123/dfw16ktqrqxvrilbgm.png)

我们先验证一个，验证目标是 wrs_kernel_text_start  ，数据内容是54 00 00 1F，对应内存地址是40 20 50 00。  
为了验证数据内容是否指向 wrs_kernel_text_start  ，我们进行一下操作，找到零号字符串的地址，看索引表第一行(0x08偏移处)54 00 00 00对应的40 20 50 00。这说明对应的第一个字符串的第一个符号名可能是sysInit。
需要注意的一个细节是：虽然在经典的 BlackHat 案例中 VxWorks 5.5 符号表通常被描述为 16 字节结构，但在 WDR7661 的实测中，其符号表采用了更为精简的 8 字节条目结构。  
#### 2.2.1 验证案例一：锚定符wrs_kernel_text_start
我们首先验证第一个关键条目，根据索引表0x10偏移处的数据54 00 00 1F。
名字偏移(4字节) ：54 00 00 1F
内存地址(4字节) ：40 20 50 00

![17.png](https://www.iotsec-zone.com/api/image/v2/20260123/dfw172oj605mrxd8dn.png)
我们要找一个参照物，观察索引表第一行(0x08处)，他的偏移是00。
在图中，我们以sysInit为准。

![18.png](https://www.iotsec-zone.com/api/image/v2/20260123/dfw17amum6mvdneclr.png)
并且我们大概能猜测到这就是符号表的开头，因为从这里开始就是明文，不是乱码。
 “符号名还原算法推导： 我们通过实测得出，符号名字符串的定位遵循：  
$Target\_String\_Addr = String\_Table\_Base + Offset\_in\_Entry$
以 _wrs_kernel_text_start 为例： 基准起点 0x1F850 + 条目偏移 0x1F = 0x1F86F。 经验证，该地址准确落在了字符串表的下划线起始位，证明该偏移逻辑是整套符号表文件的核心索引机制。

![19.png](https://www.iotsec-zone.com/api/image/v2/20260123/dfw17d04dxr1iiwpmi.png)
我们能看到光标落在了w处，我们再选一个偏移进行测试。
![20.png](https://www.iotsec-zone.com/api/image/v2/20260123/dfw17khvfhlqk9zara.png)
结果正确的。

#### 2.2.2、验证案例二
根据上一个验证我们接着往下推。

![21.png](https://www.iotsec-zone.com/api/image/v2/20260123/dfw183r7vgt4zkwyos.png)
我们很清晰的看到了光标在w处，接下来我们就根据偏移计算下一个符号地址，如果落在了sysMmapSwit的开头，那么我们推论成立。

![22.png](https://www.iotsec-zone.com/api/image/v2/20260123/dfw18fbk621qktxcvs.png)
从0x20条目撞击sysMmapSwitch，为了验证8字节双联排结构，我们选取上一个测试偏移和他紧挨着的结构进行测试。
名字偏移量：54 00 00 35（提取：0x35）  
内存运行地址：40 20 50 04
基准起点：0x1F850
计算公式：0x1F850 + 0x35 = 0x1F885

![23.png](https://www.iotsec-zone.com/api/image/v2/20260123/dfw18q6ly8nqzgdvgy.png)
至此我们的猜想全部成立。

### 2.3、结构体猜测

![24.png](https://www.iotsec-zone.com/api/image/v2/20260123/dfw199211z8suwl6n6.png)
 “观察符号条目中的 Flag 字段，我们看到的 54 和 74 本质上是 Symbol Type 的体现。在小端模式下，十六进制显示的 54 实际对应的是 Type 0x05（Global Text，代表全局函数），而 74 对应的是 Type 0x07（Global Data，代表全局变量）。这一特征是我们编写自动化恢复脚本时，区分‘重命名函数’还是‘重命名变量’的核心判据。”
 
 # 五、字符表恢复
 我们了解到了结构就可以写一个脚本恢复，推荐使用Vxhunter进行二开。
其实整个流程就是取出符号表然后导入到内核文件中即可。

![25.png](https://www.iotsec-zone.com/api/image/v2/20260123/dfw19mi9flq3otzflt.png)

 # 参考资料
 [1] Yuejin Du, et al. "Dive into VxWorks Based IoT Device: Debug the Undebuggable Device". Black Hat Asia 2019. 
 
 # 工具下载
 [https://github.com/cha0yang1/VXHUNTER_Fix](https://github.com/cha0yang1/VXHUNTER_Fix)
 
 
 
