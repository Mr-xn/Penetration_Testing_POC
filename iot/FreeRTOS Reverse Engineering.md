# FreeRTOS Reverse Engineering
> 0431物联卫士实验室
> 来源：https://www.iotsec-zone.com/article/3

# FreeRTOS简介

FreeRTOS是一个迷你的实时操作系统内核。作为一个轻量级的操作系统，功能包括：任务管理、时间管理、信号量、消息队列、内存管理、记录功能、软件定时器、协程等，可基本满足较小系统的需要。

# FreeRTOS编译

编译环境

· windows10 20H2

· keil V5.33.0.0

从FreeRTOS下载地址下载官方源代码。
![0.png](https://www.iotsec-zone.com/images/MdImg/53bffb543c8532821e68eb4bcb32f39c.png)

解压下载的文件，获得的目录如下
![1.png](https://www.iotsec-zone.com/images/MdImg/6674b7534b47d5b5f53ba0e2320e0a4d.png)

这里我们重点关注的是FreeRTOS，这里面包含FreeRTOS的内核代码以及我们要进行测试的代码。
![2.png](https://www.iotsec-zone.com/images/MdImg/e6aa3462bc8983d605ad593c562f256c.png)

这里我们选择STM32F103系列的代码进行编译，使用keil打开这个系列的项目代码

![3.png](https://www.iotsec-zone.com/images/MdImg/cf7c32d837fe359c4b5c1b3e624cc3ee.png)

![4.png](https://www.iotsec-zone.com/images/MdImg/b64c9acf6a55d5682773ed8aa3d235ea.png)

通过keil我们可以看到整个项目涉及的代码。
因为我们提取的固件普遍为BIN文件，所以我们得在keil中设置，最后编译生成BIN文件。
![5.png](https://www.iotsec-zone.com/images/MdImg/3eecbf292562e6c6327816bed44b9e8f.png)

在After Build/Rebuild选项中的Run#1处添加如下代码:

```
D:\keilv5_core\ARM\ARMCC\bin\fromelf.exe  --bin -o .\bin\RTOSDemo.bin .\RTOSDemo.axf

```

这里fromelf.exe是最后格式化为BIN的应用程序，-o是编译生成的BIN文件存放到当前目录下的bin目录中，bin目录没有会自动创建，RTOSDemo.axf文件是keil编译生成的文件。

编译成功，我们可以获得RTOSDemo.bin固件文件，这里包含我们全部的应用代码！
![6.png](https://www.iotsec-zone.com/images/MdImg/b2e10267f8f4e85270398e8cf9687d3e.webp)
![7.png](https://www.iotsec-zone.com/images/MdImg/c878f0475845636cb09d0b7630c1174c.webp)

# FreeRTOS逆向

逆向分析环境：

· IDA 7.0

· binwalk

这里我们使用IDA进行逆向分析已经编译成功的BIN固件,首先这是BIN固件的架构ARM Little-endian。
![8.png](https://www.iotsec-zone.com/images/MdImg/e020bfdedae4c5eff6391e536635c0f7.webp)

![9.png](https://www.iotsec-zone.com/images/MdImg/7fcc8af4bb9512c515fadc35b0bdf5a0.webp)
![10.png](https://www.iotsec-zone.com/images/MdImg/d191859f792f249276290d2f7b026b02.webp)

在processor type里选择ARM little endian，打开processor options。在截图上，你能看到适用于我这个环境的设置。我的Cortex-M3基于ARMv7-M架构，所以才这样设置。

接下来当我们载入IDA时，会让我们输入ROM，RAM等基地址，这里我们使用两种方式去添加。
::: hljs-center

**方式一**

:::
由于整个固件是我们自己编译的，这里我们可以在Keil中查看ROM，RAM等载入地址信息。
![11.png](https://www.iotsec-zone.com/images/MdImg/7cb8ca42670a5a8c1715c7ec38590dca.webp)

这里我们可以看到RAM和ROM对应的起始地址以及大小，我们将对应的数据添加到IDA进行分析时的Disassembly memory organization对应的ROM和RAM中，数据添加情况如下：
![12.png](https://www.iotsec-zone.com/images/MdImg/bc14a9e321905b4aa3d26fad7e8067b2.webp)

我们逐步确定，IDA自动加载，最终得到如下分析结果
![13.png](https://www.iotsec-zone.com/images/MdImg/522a0f11c0ed700bd3540fef97d2eac8.webp)

但是由于IDA没有自动去解析BIN固件，需要我们自己进行解析。首先我们设置IDA支持ARM Thumb指令，可以使用快捷键Alt+G设置指令分析格式
![14.png](https://www.iotsec-zone.com/images/MdImg/482a823473797bf887f0a515e3f5d6c0.webp)
![15.png](https://www.iotsec-zone.com/images/MdImg/f2b72452bef16673f4263de3c89b1d73.webp)

可以看到已经变成CODE16的汇编代码了。这里我们按C键进行自动分析，分析完的代码如下：
![16.png](https://www.iotsec-zone.com/images/MdImg/f8e719efdd3405a57fd46396ed82b467.png)

这里我们可以看出已经有functions和反汇编代码了。这种方式仅仅对我们分析自己编译的固件能够起到帮助作用。

::: hljs-center

**方式二**

:::

接下来，让我们看一下方式二，这种方式经常应用于逆向工程。

现在假设固件是我们从设备中提取的固件，目前不知道任何有用的信息。

根据常规方式我们使用binwalk进行简单的扫描分析，得到如下结果：

![17.png](https://www.iotsec-zone.com/images/MdImg/dc7c872d8d770d0039b59454efc09f0a.webp)

在这里我们得不到任何信息。但是我们知道这是个RTOS，所以我们直接上IDA，暴力简单！

这里我们同样要选择架构，嵌入式中比较常见的架构是ARM，MIPS，PowerPC。如果我们不知道具体架构可以都尝试一遍，根据代码解析的结果进行逐步确定。这里我们选择ARM架构，但是我们不知道具体的ROM，RAM等地址信息，我们直接默认就可以了，IDA加载得到如下结果：

![18.png](https://www.iotsec-zone.com/images/MdImg/81e56bc904ae6bee220d1716e7ba291c.webp)

可以看到得到的结果还是和前面的比较相似的，但是前面的地址变成从00000000开始的了，同样我们设置Thumb指令格式，然后进行反汇编分析得到如下结果：
![19.png](https://www.iotsec-zone.com/images/MdImg/1bf528f18eb580618ca340284587e442.webp)

这里可以看到我们仅仅得到了两个函数，那么我们就从头先简单的分析一下
![20.png](https://www.iotsec-zone.com/images/MdImg/e1d2bd746ab28349415052afc5235078.webp)

这里我们看到0x20000000和0x8000000两个比较大的段地址，那么我们就可以猜测这是否就是ROM，RAM相关的地址呢？这时我们已经可以重新载入分析了，但是我们先看一下STM32F103板子的内存布局情况

![21.png](https://www.iotsec-zone.com/images/MdImg/4333f17edd3d21855c45ac302d992809.webp)

这里我们也大概看出RAM，ROM等基地址情况。那么我们就可以使用方式一的操作对固件进行分析了，最终也成功得到反汇编代码

![22.png](https://www.iotsec-zone.com/images/MdImg/764e592fc84f6f0292e67f0d59625270.webp)

FreeRTOS由任务组成，这些任务由用户编写，所以我们根据FreeRTOS的关键代码进行逆向分析。

寻找IDLE任务(前提是用户没有更改原生代码)，我们通过字符串查找IDLE

![23.png](https://www.iotsec-zone.com/images/MdImg/3cbba8874b43485ea442fd005930bf6d.webp)

我们字符串进行跟踪，得到如下代码

![24.png](https://www.iotsec-zone.com/images/MdImg/2a91c3cd43d1c57d45f87887f2281d1a.webp)

我们将代码进行反汇编

![25.png](https://www.iotsec-zone.com/images/MdImg/ac7678e7e7d9f2087164317155d6a994.webp)

我们看一下Keil中的源代码

![26.png](https://www.iotsec-zone.com/images/MdImg/c3c7d27f44c4ab06ccda69f31ec825a5.webp)

我们这里可以确定sub_8003F5C()函数就是xTaskCreate()的任务函数，我们进行重命名sub_8003F5C()和sub_80047B8()为xTaskCreate和vTaskStartScheduler()，并查看整个函数的调用关系。

![27.png](https://www.iotsec-zone.com/images/MdImg/496730ffa510214f08cae3746dfc5f52.webp)

![28.png](https://www.iotsec-zone.com/images/MdImg/b0cf6ebca2d0cda252073d3136f3482a.webp)

通过这里我们可以看到这里也有两个xTaskCreate()任务函数，这两个任务函数就是用户自定义的代码，我们看一下源代码的情况

![29.png](https://www.iotsec-zone.com/images/MdImg/36b794713b3672f3690048932979668a.webp)

![30.png](https://www.iotsec-zone.com/images/MdImg/58b3d467f531e5963b0fdd5241e524f2.webp)

这两地址对应的就是vCheckTask和vLCDTask任务处理函数，我们跟踪地址得到如下内容:

![31.png](https://www.iotsec-zone.com/images/MdImg/28600485034d9287bcf884cd93156f97.webp)

可以看出这里还没有进行分析，我们这里手动进行分析，因为我们已经确定这里对应的就是实际的函数。选中部分代码，右键选择Analyze selected area进行代码分析，得到如下内容

![32.png](https://www.iotsec-zone.com/images/MdImg/ad938466278647fd9954a93406145eb8.webp)

![33.png](https://www.iotsec-zone.com/images/MdImg/b5b99ddd74ef0556488c794aaf3bee8b.webp)

我们源码对比可以确定这里确实是任务处理函数，我们将这个地址设置为Function，得到如下内容

![34.png](https://www.iotsec-zone.com/images/MdImg/6726ac2dae69a7b834a0a8efa802957c.webp)

根据地址自动生成函数

![35.png](https://www.iotsec-zone.com/images/MdImg/70ddae7da3eaa41843d4c12e64c2f9d0.webp)

但是调用的地方对应的地址不正确。

![36.png](https://www.iotsec-zone.com/images/MdImg/b961956acec3a5aa60ed1a3818425d59.webp)

我们将地址代码进行重定位，对应到实际任务处理函数地址 。

![37.png](https://www.iotsec-zone.com/images/MdImg/2f2b88eae4f03a4a54f8c7f2f6823f05.webp)

最终得到实际的任务处理函数。

![38.png](https://www.iotsec-zone.com/images/MdImg/ab167897c87d717c8e9721ce4ef463d0.webp)

这里就是我们的vCheckTask()的函数，我们通过源代码对比就可以看出实际的任务处理函数。

如果IDLE被处理掉，那么我们要找的就是和xTaskCreate()相关代码。这里我们看下xTaskCreate()的代码

![39.png](https://www.iotsec-zone.com/images/MdImg/502e028e62b512cd0133a745997bd24b.webp)

![40.png](https://www.iotsec-zone.com/images/MdImg/d76a8bc3d50b637e13ff52089e536949.webp)

通过汇编代码对比可以看出xTaskCreate()对应关系，如果IDLE被处理掉，那么可以根据函数参数入栈规则进行猜测和分析。

# 结语
以上就是对FreeRTOS的逆向分析，这里主要以FreeRTOS自带的Demo进行逆向分析，帮助熟悉RTOS的逆向，RTOS的逆向和传统的Linux固件有点不大一样，但分析逻辑没有任何不同。
