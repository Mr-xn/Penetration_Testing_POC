# RFID/NFC入门小记
> XCES
> 来源：https://www.iotsec-zone.com/article/514

本文为小白入门RFID安全方面的小记，大佬勿喷。
# 简述
此处为对RFID，M1卡，NFC的整体介绍

## RFID
射频识别，即RFID是Radio Frequency Identification的缩写，又称无线射频识别，是一种通信技术，可通过无线电讯号识别特定目标并读写相关数据，而无需识别系统与特定目标之间建立机械或光学接触。
一套完整RFID硬件统由 Reader 与 Transponder 两部份组成，其动作原理为由 Reader 发射一特定频率之无限电波能量给 Transponder，用以驱动 Transponder 电路将内部的 ID Code 送出，此时 Reader 便接收此 ID Code。
RFID读写器由射频模块，控制处理模块，天线组成。RFID电子标签可按供电方式分为有源、无源和半有源；按工作频率分为低频、高频、超高频和微波；按封装形式分为卡片、线形、纸状、玻璃管、圆形及异形等多种类型。RFID标签一般由RDFID晶片、天线（包裹RFID晶片的铜丝）、电力来源（主动式：由标签内部的所附电源提供；被动式：由读写器发射的无线电波提供）组成。读写器与电子标签之间的通信协议一般为ISO 14443协议，它规定了 物理层特性、通信方式和防碰撞机制。

RFID读写器在正常情况下一个时间点只能对一张卡进行读写操作，当多张卡片同时进入读写器的射频场时，读写器会采用防碰撞机制来解决多个卡的冲突问题使得读卡器不能同时对不同卡进行读写等操作，具体的防冲突机制不在此处展开。

此处以MFRC522为例来展示读写器结构，可以从图中看到主机与芯片之间的通信需要先经过FIFO缓冲区：

![0.png](https://www.iotsec-zone.com/api/image/v2/20250831/dcgms4sogw8d6is62y.png)
以下是MFRC522的一组通用命令说明，它解释了芯片内部如何通过寄存器命令来控制通信过程，此处有一种命令是控制MFRC522本身的，还有一种命令是控制tag的。
- IDLE 命令，MFRC522 处于空闲模式。该命令也用来终止实际正在执行的命令；
- CALCCRC 命令，FIFO 的内容被传输到 CRC 协处理器并执行 CRC 计算。这个命令必须通过向命令寄存器写入任何一个命令（如空闲命令）来进行清除；
- TRANSMIT 命令，发送 FIFO 的内容。在发送 FIFO 的内容之前必须对所有相关的寄存器进行设置。该命令在 FIFO 变成空后自动终止；
- RECEIVE 命令，该命令在接收到的数据流结束时自动终止；
- TRANSCEIVE 命令，该循环命令会重复发送 FIFO 的数据，并不断接收 RF 场的数据。第一个动作是发送，发送结束后命令变为接收数据流；
- MFAUTHENT 命令 (P69，17)，该命令用来处理 Mifare 认证以便到任何 Mifare 普通卡的安全通信。在命令激活前以下数据必须被写入 FIFO：认证命令码、块地址、秘钥、序列号。该命令在 Mifare 卡被认证且 Status2Reg 寄存器的 MFCrypto1On 位置位时自动终止；
- SOFTRESET 命令，所有寄存器都设置成复位值。命令完成后自动终止。

寻卡、防冲突、选卡协议：
寻卡为0x26 或者 0x52，协议内容一个寻卡命令就可以了，接着就可以发送，它的返回是2byte 卡类型 (4, 0)
防冲突为0x93，协议内容为防冲突命令 + 0x20，并返回4byte 卡ID，1byte 校验 (异或) (62 A8 2B B EA)
选卡协议内容为命令字 + 0x70 + 4byte 卡号 + 1byte 校验 + 2byte CRC16 校验，返回卡校验 0x08。

在这里实际唤醒流程将ISO14443-A协议的0x26（0x52）写入FIFO，然后使用TRANSCEIVE发出，最终来唤醒卡片。

阅读器和电子标签之间的射频信号的耦合类型有两种：
1. 电感耦合
变压器模型，通过空间高频交变磁场实现耦合，依据的是电磁感应定律。电感耦合方式一般适合于中、低频工作的近距离射频识别系统。典型的工作频率有：125kHz、225kHz 和 13.56MHz。识别作用距离小于 1m，典型作用距离为 10～20cm。
2. 电磁反向散射耦合
雷达原理模型，发射出去的电磁波，碰到目标后反射，同时携带回目标信息，依据的是电磁波的空间传播规律。
电磁反向散射耦合方式一般适合于高频、微波工作的远距离射频识别系统。典型的工作频率有：433MHz、915MHz、2.45GHz、5.8GHz。识别作用距离大于 1m，典型作用距离为 3～10m。

## M1卡
下图为M1卡结构图：

![1.png](https://www.iotsec-zone.com/api/image/v2/20250831/dcgmu2o8icwphhlvhp.png)
RF-Interface（射频接口）：和读写器“空中对话”的物理层，把无线电变成比特，又从比特变回无线电
- Modulator / Demodulator（调制器/解调器）：
读写器→卡用 ASK（幅移键控）+ Miller 编码（位编码方式）；卡→读写器用 负载调制（load modulation，用副载波在读写器场里“轻微扰动”）+ Manchester 编码。这块把射频信号和数字数据互相转换。
- Clock / Data（时钟/数据）：把还原出的时钟与数据送往数字逻辑区。
- Voltage Regulator（稳压器）：从读写器磁场取能并稳压，整片芯片就靠它“吃电”（卡片本身没电池）。
- POR / E²POR（上电复位/EEPROM 上电复位）：上电时把逻辑与存储拉到安全初始态，防止乱跑。
- Energy（能量）：说明供电来自 RF 前端耦合的能量。
Digital Section（数字逻辑区）：协议、选择、防碰撞、认证、加密、控制
- ATR / ATQA（Answer to Request，唤起响应）：读写器发 REQA/WUPA（唤醒/查询命令） 后，卡首先回一个 ATQA 告诉“我是谁、属于 Type A”之类的基本信息。
- Anti-Collision（防碰撞）：多卡同场时按 级联级别（cascade level，CL1/CL2/CL3） 逐步“点名”，最终唯一选中一张卡（防止同时说话）。
- Select Application（选择）：把被选中的卡置为 Active（活动）状态，进入会话。
- Authentication & Access Control（认证与访问控制）：
MIFARE Classic 用 三次握手（three-pass） 与 KeyA/KeyB（两套密钥/每扇区）做认证。认证成功后建立会话密钥，后续读写按 访问位（access bits） 判定权限。
- Crypto Unit（加密单元）：
实现 Crypto1（流密码，stream cipher（按位生成密钥流加解密）），在 RF 链路上对数据（含 CRC、奇偶）做加/解密，抵抗窃听与重放。
- Control & Arithmetic Unit（控制与运算单元）：
状态机与微运算（如 INCREMENT/DECREMENT/RESTORE/TRANSFER（值块增减与搬移） 指令），统一调度“收发 → 认证 → 访问 EEPROM”。
E²-Memory（EEPROM，电可擦可编程存储器）：扇区/块组织的永久存储
容量 1 KB：16 扇区 × 每扇区 4 块 × 每块 16 字节。
每扇区最后一块是 Sector Trailer（扇区尾块）：存 KeyA（6B）+ 访问位（4B）+ KeyB（6B）。
其它块存放用户数据或 Value Block（值块）。
通过 E²-Interface（存储接口） 与数字逻辑区连接，只有认证通过且权限允许时才可读写。

操作流程如下：

![2.png](https://www.iotsec-zone.com/api/image/v2/20250831/dcgmv5ror10jaouyyk.png)
此处读卡流程为先复位，然后进行请求，防冲突，选卡，认证，读写充值操作
此处S50读卡示例命令：
请求：0x26
防冲突：0x93，0x70
A认证0x60（B认证为0x61），addr，keyA，ID
读0x30,addr,CRC16
在这里需要注意的是上文的MFAUTHENT 命令，该命令用于处理 Mifare 认证，以使得任何 Mifare 普通卡的安全通信。在命令激活前以下数据必须被写入 FIFO：
```
认证命令代码 (0x60, 0x61)
块地址
扇区密钥字节 0
扇区密钥字节 1
扇区密钥字节 2
扇区密钥字节 3
扇区密钥字节 4
扇区密钥字节 5
卡序列号字节 0
卡序列号字节 1
卡序列号字节 2
卡序列号字节 3
```
以上总共12字节必须写入FIFO中
## NFC
而NFC (Near Field Communication) 近场通信是从RFID演变而来，由飞利浦半导体（现恩智浦半导体公司）、诺基亚和索尼共同研制开发，其基础是 RFID 及互连技术。它是一种短距离高频的无线电技术，在 13.56Mhz 频率运行于 20cm 距离内，也就是在高频范围内。其传输速度有 106Kbit/s、212Kbit/s 或者 424Kbit/s 三种。NFC 采用主动和被动两种读写模式。

下图就是 读写器与卡进行交互的展示图，展示了 读卡器端（PCD, Proximity Coupling Device） 和 卡片端（PICC, Proximity Integrated Circuit Card） 之间的关系，此处读卡器与标签之间的射频信号耦合为电感耦合。

![3.png](https://www.iotsec-zone.com/api/image/v2/20250831/dcgmx6b22bu1mssjh6.png)
 NFC 技术的三种主要工作模式：卡模式、读写器模式、点对点模式
卡模式：这个模式其实是相当于一张采用 RFID 技术的 IC 卡，可以替代大量的 IC 卡（包括信用卡、公交卡、门禁管理、车票、门票等）。
读写器模式：这个模式可以模拟读卡器功能，读取 MIFARE 和 FeliCa 卡的信息。
点对点模式：这个模式和红外线差不多，可用于数据交换，只是传输距离较短，传输速度可稍低，功能便捷。将两个具有 NFC 功能的设备链接，能实现数据点对点传输，如下载音乐、交换图片或通讯录等。一次通过这种 NFC，多台设备如数码相机、PDA、计算机和手机之间都可以交换资料或服务。

这里以PN532芯片为例进行介绍，它是一款高度集成的非接触式通讯模块，基于 8051 单片机核心。它支持 6 个不同的操作模式：ISO/IEC 14443A/MIFARE 读/写器FeliCa 读/写器，ISO/IEC 14443B 读/写器，ISO/IEC 14443A MIFARE 卡模拟模式，FeliCa 卡模拟模式，ISO/IEC 18092 ECMA 340 点对点。这款芯片提供 3 种和主机通信的接口zSPI/I²C/USART。下图为PN532结构图示：

![4.png](https://www.iotsec-zone.com/api/image/v2/20250831/dcgmxis2bd8gaamlc3.png)
很多 NFC 芯片（例如 NXP PN532、复旦 FM 系列）都支持多种接口（I²C（两线制接口，常用于低速、简单连接）、SPI（四线制接口，速度快，常用于 MCU 通信）、HSU（High Speed UART，高速串口接口）），而具体用哪一种，需要通过 硬件引脚 I0 和 I1 来配置。
![5.png](https://www.iotsec-zone.com/api/image/v2/20250831/dcgmymnmyayw8iz846.png)

下图为PN532的请求包与应答包格式图

![6.png](https://www.iotsec-zone.com/api/image/v2/20250831/dcgmyx872uldvff2rt.png)

![7.png](https://www.iotsec-zone.com/api/image/v2/20250831/dcgmz0t35yuv6b8pxt.png)
当数据超过256使用该数据包

![8.png](https://www.iotsec-zone.com/api/image/v2/20250831/dcgmz78hkbr8lejikw.png)

从手册可以看出，唤醒命令要在原有的数据包之前加入唤醒头，这个比较特殊一点，0xd4 代表主机向 PN532 写入数据，0x14,0x01 代表选择了普通模式
```
//唤醒头如下：
0x55,0x55,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0xFF,0x03,0xFD,0xD4,0x14,0x01,0x17,0x00
```
唤醒后读卡流程如下：
第一部分：扫描并初始化两张卡
Command
```
4A   # 命令码: InListPassiveTargets
02   # 需要初始化的卡片数（这里要求最多 2 张）
00   # 通信速率 = 106 kbps
```
Response
```
4B        # 响应命令码
02        # 发现 2 张卡
01        # Target number = 1
04 00     # SENS_RES(2字节)：卡1的类型信息
08        # SEL_RES：选择响应（卡片类型附加信息）
04        # NFCID1 长度 = 4
12 67 58 32 # 卡1的UID（序列号）
02        # Target number = 2
44 00     # SENS_RES of card 2
00        # SEL_RES of card 2
08        # NFCID1 长度 = 8
88 04 B6 E4 00 00 00 00 # 卡2的UID（8字节）
00 00     # 结束标志
```
- PN532 成功检测到两张卡：
  - 卡1：Mifare Standard 卡，UID 长度 4 字节 → 12 67 58 32
  - 卡2：Mifare Ultralight 卡，UID 长度 8 字节 → 88 04 B6 E4 00 00 00 00
第二部分：对 Mifare Standard 卡（卡1）进行认证
Action
- 使用默认密钥对卡1进行认证。
Command
```
40        # 命令码: InDataExchange
01        # 目标卡编号 = 1（即卡1）
60        # Mifare 命令：认证块 (0x60 = Key A, 0x61 = Key B)
07        # 认证的区块地址
FF FF FF FF FF FF # 默认密钥 (6字节全FF)
12 67 58 32        # 卡的 UID（NFCID1，来自扫描阶段）
```
Response
```
41   # 响应命令码
00   # 状态码 = 0（认证成功）
```
第三部分 读卡（Read out card 1 memory）
Command
```
40      # Command code: InDataExchange
01      # 目标卡号 = 1
30      # Mifare 指令：读块 (0x30 = Read 16 bytes)
04      # 要读取的块地址
```
Response
```
41   # 响应命令码
00   # Status = 0（成功，无错误）
EE EE EE EE EE EE EE EE  # 读取到的 16字节数据（这里只是例子）
EE EE EE EE EE EE EE EE
```
PN532的充值与扣款使用的是Value Blocks（数值块）

![9.png](https://www.iotsec-zone.com/api/image/v2/20250831/dcgn24t3gjnsnd2ygs.png)
Value Blocks 主要用于 电子钱包（Electronic Purse）功能，比如读余额、充值（increment）、扣款（decrement）、转账（transfer）、恢复（restore）等操作。
value：32 位有符号二进制补码（2’s complement）表示，存储三次。芯片会自动检查三者是否一致，再进行计算。
address：一个 8 位地址重复存储 4 次（虽然不会被芯片内部使用）。

![10.png](https://www.iotsec-zone.com/api/image/v2/20250831/dcgn2f3r6n8i5nkydy.png)
MIFARE MF1ICS50 芯片中 Value Block（数值块）运算的内部工作流程如上
1. Value Block 的生成
- 一个数值块第一次出现，是通过 WRITE 指令写入芯片存储器（chip memory）里的某个地址。
- 之后，这个数值块就可以被用来进行 递增（Increment）、递减（Decrement）、恢复（Restore） 等操作。
类比：就像你第一次往电子钱包里“充值”一个初始余额，之后你就能对它进行加钱、扣钱或恢复操作。

2. 主要组成部分
- chip memory（芯片存储器）：存放数值块的地方。
- source value（源值）：从内存中取出的数值。
- ALU（算术逻辑单元, Arithmetic Logic Unit）：用来执行加法、减法等运算的电路。
- result（结果寄存器）：保存 ALU 运算后的结果。
- DATA register（数据寄存器）：用于临时保存数据，方便后续的传输或写回存储器。

3. 操作流程
- mif_increment / mif_decrement / mif_restore
  - 输入参数有 源地址（SOURCE_ADR） 和 操作值（DECR_VALUE 或 INCR_VALUE）。
  - 芯片会从存储器里取出对应的 source value，交给 ALU 进行加/减/恢复操作，结果写回存储器。
- mif_transfer
  - 输入参数是 目标地址（DEST_ADR）。
  - 将 ALU 计算后的结果从数据寄存器传送到指定的目标地址。

MIFARE 卡操作命令（增值、减值、转移） 的字节数组定义：
```
uint8_t INCREMENT[8] = {0x40, 0x01, 0xC1, 0x02, 1, 0, 0, 0}; // 充值
uint8_t DECREMENT[8] = {0x40, 0x01, 0xC0, 0x02, 1, 0, 0, 0}; // 扣款
uint8_t TRANSFER[4]  = {0x40, 0x01, 0xB0, 0x02};             // 转移
```
0xC1 / 0xC0 / 0xB0：具体的操作指令码。
- 0xC1 → INCREMENT（增值/充值）
- 0xC0 → DECREMENT（减值/扣款）
- 0xB0 → TRANSFER（转移数据）
0x02：表示目标块地址
1,0,0,0：这是一个 4 字节的数值，采用小端模式（Little Endian），表示操作的金额或数值。意味着加 1 或减 1（单位通常取决于应用场景，比如 1 单位钱、1 次次数等）

INCREMENT（增值命令）
- {0x40, 0x01, 0xC1, 0x02, 1, 0, 0, 0}
- 对 1 号卡的 2 号地址块执行充值操作，金额是 +1。
DECREMENT（减值命令）
- {0x40, 0x01, 0xC0, 0x02, 1, 0, 0, 0}
- 对 1 号卡的 2 号地址块执行扣款操作，金额是 –1。
TRANSFER（转移命令）
- {0x40, 0x01, 0xB0, 0x02}
- 表示把之前 ALU 计算好的结果存入 2 号地址块。
- 因为转移不涉及具体金额，所以只有前 4 个字节。

# PM3读取M1卡
## 读取某业主卡
使用PM3读取M1卡
![11.png](https://www.iotsec-zone.com/api/image/v2/20250831/dcgn44bvpi22dme4ei.png)
NXP：恩智浦半导体公司
MIFARE Classic 1K：就是M1卡。Classic 1K：代表这张卡片的存储容量为 1KB，内部被划分为 16个扇区，每个扇区有 4 个块（Block）。采用传统的 Crypto-1 加密算法。
MIFARE Plus 2K SL1：MIFARE Plus：是 NXP 对 MIFARE Classic 的升级版本，提供更高安全性，就是M2卡。2K：存储容量为 2KB，比 Classic 1K 大。
SL1（Security Level 1，安全级别1）：
- 在这个模式下，它的行为几乎和 MIFARE Classic 一样（兼容旧系统），仍使用 Crypto-1 算法。
- 但是在更高的安全级别（SL3），它可以切换到更强的 AES 加密，安全性大大提升。
可以看到第0号扇区0块数据前8位是UID：45 4c 99 2d
![12.png](https://www.iotsec-zone.com/api/image/v2/20250831/dcgn4fsk5alpcg3zlq.png)
第四块存放密钥（KEYA、KEYB）和控制位，它们决定了谁可以访问这个扇区的数据，以及能做什么操作。在使用时，读卡器需要输入正确的 KeyA 或 KeyB 才能访问相应的扇区。KeyA 一般用于“读卡”权限（比如公交卡余额查询）。KeyB 可以用于“写卡”或“更新权限”，也可用于作为另一个读取口令。控制位（Access Bits）：规定了这个扇区的每个数据块（Block）对 KeyA、KeyB 的权限。能控制的内容包括：
- 某个块是否能被读/写；
- 是否只能用 KeyA 或只能用 KeyB 才能读/写；
- 扇区尾块（Sector Trailer）本身的修改权限（即能否更换密钥）。
默认的控制字为FF078069
![13.png](https://www.iotsec-zone.com/api/image/v2/20250831/dcgn4p582d8kw9r2mv.png)
MIFARE Classic 的密钥机制：
Key A 和 Key B应该是 用户自定义的随机值，这样才安全。但是在现实中：很多厂商出厂时为了方便，并没有修改密钥，而是用了统一的“默认值”。
这些默认密钥往往是一些固定的模式，比如：
```
FF FF FF FF FF FF（全 F）
00 00 00 00 00 00（全 0）
A0 A1 A2 A3 A4 A5
D3 F7 D3 F7 D3 F7
B0 B1 B2 B3 B4 B5
```
在Proxmark3 的固件里内置了 13 组常见的默认密钥。
当你用 Proxmark3 去攻击/读取一张卡时，它会自动尝试用这 13 组密钥去认证：
- 如果成功，就说明这个扇区还在用默认密钥 → 可以继续读写。
- 如果失败，就说明该扇区被设置了自定义密钥，需要进一步破解

这里也可以直接使用命令行进行嗅探，使用命令行打开proxmark3软件
```
proxmark3 COM10
```

![14.png](https://www.iotsec-zone.com/api/image/v2/20250831/dcgn5b89qweqncti7f.png)
```
hf 14a reader 
//hf：高频模式（13.56MHz）。
//14a:ISO14443A 协议, 这是高频 RFID 常见的一种协议，MIFARE Classic、MIFARE Ultralight、NFC 卡片都属于这一类。
//reader:执行读卡操作
```

![15.png](https://www.iotsec-zone.com/api/image/v2/20250831/dcgn5iz7qy71g6fien.png)
可以看到与图形化读卡类型相同的内容
```
hf mf chk * ?
//mf：针对 MIFARE Classic 卡。
//chk：check，检查密钥。
//*：检查所有扇区。
//?：使用默认密钥列表。
```
![16.png](https://www.iotsec-zone.com/api/image/v2/20250831/dcgn5wi99ndoii46ab.png)
使用命令hf mf dump提取数据，提取后的数据默认保存在当前目录下的dumpdata.bin文件中
```
hf mf dump
```
![17.png](https://www.iotsec-zone.com/api/image/v2/20250831/dcgn68utej8wmfjjdi.png)
但是直接看bin文件不太好看
![18.png](https://www.iotsec-zone.com/api/image/v2/20250831/dcgn6oac16q7ogg7vm.png)
可以使用命令script run dumptoemul.lua将bin文件转为EML格式文件（具有更好的可读性）
```
script run dumptoemul.lua
```
![19.png](https://www.iotsec-zone.com/api/image/v2/20250831/dcgn75aoflhuohtqiu.png)
![20.png](https://www.iotsec-zone.com/api/image/v2/20250831/dcgn798o0cne243exf.png)
可以看到第六扇区的第1块也就是第25块如下
```
15030a0000190c1f00000000173b7f00
```
此处16进制15 03 0a转换为10进制为21 03 10，19 0c 1f转换为10进制为25 12 31，这里猜测可能是该业主卡的有效日期为2021年3月10日至2025年12月31日，此处可以通过PM3对该卡的数据进行更改，不再演示。
## 读取支付宝碰一碰静态NFC卡

![21.png](https://www.iotsec-zone.com/api/image/v2/20250831/dcgn8hjcj04838u5cf.png)
```
proxmark3> hf 14a reader
ATQA : 00 44
 UID : 1d f8 3d 13 94 00 00
 SAK : 00 [2]
MANUFACTURER : Shanghai Fudan Microelectronics Co. Ltd. P.R. China
TYPE : NXP MIFARE Ultralight | Ultralight C
proprietary non iso14443-4 card found, RATS not supported
Answers to chinese magic backdoor commands: NO
```

![22.png](https://www.iotsec-zone.com/api/image/v2/20250831/dcgn8zgq58yh9imbbi.png)
```
proxmark3> hf mfu cauth
#db# Authentication part1: Fail.
Command execute timeout
//无加密
```
![23.png](https://www.iotsec-zone.com/api/image/v2/20250831/dcgn9d7yhz4iqqhmsu.png)
```
proxmark3> hf mfu dump
Dumping Ultralight Card Data...
#db# Pages 16
#db# Pages read 16
Block 00:1d f8 3d 50
Block 01:13 94 00 00
Block 02:87 a3 ff ff
Block 03:e1 10 3e 00  [1]
Block 04:03 c8 91 01  [1]
Block 05:70 55 00 68  [1]
Block 06:74 74 70 73  [1]
Block 07:3a 2f 2f 72  [1]
Block 08:65 6e 64 65  [1]
Block 09:72 2e 61 6c  [1]
Block 0a:69 70 61 79  [1]
Block 0b:2e 63 6f 6d  [1]
Block 0c:2f 70 2f 73  [1]
Block 0d:2f 75 6c 69  [1]
Block 0e:6e 6b 2f 78  [1]
Block 0f:66 71 3f 73  [1]
Dumped 16 pages, wrote 64 bytes to 1DF83D13940000.bin
```

![24.png](https://www.iotsec-zone.com/api/image/v2/20250831/dcgn9oe9byjccehrpr.png)
可以看到存储的是一个网址，但是通过PM3的这种方法并不能拿到完整的存储内容，通过搜索文章发现[https://xiaohei.moe/post/2024/11/25/alipay-nfc-tag](https://xiaohei.moe/post/2024/11/25/alipay-nfc-tag)
采用该文章的方法进行复现然后将数据进行导出分析如下：
该卡是上海复旦微电子股份有限公司生产，符合 NFC Forum Type 2 标准，支持 ISO/IEC 14443-3 协议（Type A），但是不支持 ISO/IEC 14443-2（Type A）
该NDEF 数据有三个记录分别是URI 记录，Android 应用记录，NFC Forum 外部类型记录
url记录：
![25.png](https://www.iotsec-zone.com/api/image/v2/20250831/dcgn9y6195yfivbffq.png)
```
https://render.alipay.com/p/s/ulink/xfq?s=dc&scheme=alipay://nfc/app?id=2000xxxx&t=xxxxx
```

Android 应用记录：
![26.png](https://www.iotsec-zone.com/api/image/v2/20250831/dcgnacwxlnbndvplml.png)
类型：android.com:pkg 包名：com.eg.android.AlipayGphone，这是支付宝应用的包名。

NFC Forum 外部类型记录：

![27.png](https://www.iotsec-zone.com/api/image/v2/20250831/dcgnakosgx3su2r7tq.png)
其类型为 ohos.com:pkg，包名为 com.alipay.mo

# 认证与安全控制
## 存储器访问（Memory Access）
在任何存储器操作前，卡需要先被选择，并经过认证（KEYA或KEYB）。对于可寻址的数据块的可能的存储器操作取决于使用的key和存储在相应的区尾的访问条件。

![28.png](https://www.iotsec-zone.com/api/image/v2/20250831/dcgnb95migmcyghmcq.png)
- POR (Power-On Reset，上电复位)：当卡片被感应到电磁场时，它会经历 POR，清空之前的状态，准备进入正常工作流程。
- Identification and Selection Procedure（识别与选择过程）：系统会在多个可能的卡片中识别并选择出当前要通信的那一张。如果换了一个扇区（Sector，存储区域），就必须重新进行这个步骤。
- Authentication Procedure（认证过程）：卡片和读卡器之间会进行双向认证，确保双方都可信。如果认证失败，就无法继续访问对应的存储区。
- Memory Operations（存储操作）：一旦认证成功，就可以对卡片的存储区进行操作。这里有两种类型的存储块：
（1）Value Block（数值块）
数值块的内容有固定结构（数值的补码 + 地址 + 校验），通常用于计数器。比如里面的数据是 数值正码、数值反码、数值正码、地址、地址反码、地址重复 这种模式。（普通读写块无固定格式）
这种块是 带有计数功能的特殊存储块，常用于储值（像公交卡余额）。支持操作：
- Read（读取）
- Write（写入）
- Increment（增加）
- Decrement（减少）
- Transfer（转移数值）
- Restore（恢复数值）
（2）Read/Write Block（读写块）
这是普通的存储块，就像一个小笔记本，可以存放数据。支持：
- Read（读取）
- Write（写入）

![29.png](https://www.iotsec-zone.com/api/image/v2/20250831/dcgnc03hmg7hnii8my.png)
Read/Write Block（普通读写块）
Value Block（数值块）:一般用于饭卡等电子消费的余额存放以及加减
Sector Trailer（扇区尾块，用于存放密钥和访问条件）
Read（读取）：读取一个存储块的内容。
Write（写入）：向一个存储块写入内容。 和读取类似，所有块也都可以被写入（但写入规则不同，比如 Value Block 必须符合特定格式）。
Increment（增加数值）：对存储块里的数值进行加法，并把结果放到 内部数据寄存器 中。
Decrement（减少数值）：对存储块里的数值进行减法，并把结果放到 内部数据寄存器 中。
Transfer（传送）：把 内部数据寄存器 中的内容写入某个 Value Block。
Restore（恢复）：把某个 Value Block 的数值读到 内部数据寄存器 中。

## 控制位（Access Bits）分析
假设若已知Sector 10的Block 3的数据（Hex 表示），共计16 个字节，如下所示：
```
00 00 00 00 00 00 FF 07 80 69 0B 0B 0B 0B 0B 0B
```

![30.png](https://www.iotsec-zone.com/api/image/v2/20250831/dcgnd3nvvl47sfv1y8.png)
根据上面的访问条件（Access Conditions）图表，可知：
 
1）字节分布
前6个字节（Byte 0 - Byte 5）为密钥Key A，即00 00 00 00 00 00
中间4个字节（Byte 6 - Byte 9）为访问位(Access Bits)，即FF 07 80 69
后6个字节（Byte 10 - byte 15）为密钥Key B，即0B 0B 0B 0B 0B 0B
这里每个字节的bit7控制块3，bit6控制块2，bit5控制块1，bit4控制块0，bit0-3为bit4-7的取反
2）访问控制位分布
区尾（sector trailer）和数据段（data block）的访问条件（Access conditions）是不一致的
1）区尾的访问条件（Access conditions for the sector trailer）

![31.png](https://www.iotsec-zone.com/api/image/v2/20250831/dcgndc2s3spwlskacy.png)
注：用灰色标明的行是密钥B 可被读的访问条件，此时密钥B 可以存放数据，此处的密钥A永远不可读，如果不可读会返回000000。
这里block3由bit7控制，出厂默认区尾的访问位为0 0 1，可以看到只能使用KEY A（KeyB可读情况下不作为认证密钥），可写入密钥KEYA但不可读，可读写访问控制位和KEYB。

2）数据段的访问条件（Access conditions for data blocks）

![32.png](https://www.iotsec-zone.com/api/image/v2/20250831/dcgndkk30xvjbdusfv.png)
如果密钥B 可以在相应的区尾被读出，它就不能用于确认（在区尾的访问条件表中所有灰色行）。结果：如果RWD（读写装置Read Write Device）要用这些（带灰色标记的）访问条件的密钥B 确认任何段，卡会在确认后拒绝任何存储器访问操作。
例如数据段的C1 C2 C3为0 0 0 用于传输配置（transport configuration），此时KEY B不能用来认证。

## M1卡认证过程
这个图是MIFARE 1k 卡片与读卡器之间的认证过程，遵循 ISO14443-A 的规范。
![33.png](https://www.iotsec-zone.com/api/image/v2/20250831/dcgneefijsywp6bcwn.png)
1. 初始请求 (Step 01–02)：
01 Reader → 26：读卡器先发出请求（req type A）
02 Tag → 04 00：卡片回应（answer req）
2. 卡片选择 (Step 03–06)：
03 Reader → 93 20：读卡器发送 select 命令，意思是“我想选中你这张卡”。
04 Tag → c2 a8 2d f4 b3：卡片返回自己的 UID（唯一识别码）和校验位 BCC。
05 Reader → 93 70 c2 a8 2d f4 b3 ba a3：读卡器确认选择（select(uid)），指定这张卡。
06 Tag → 08 b6 dd：卡片确认自己是 MIFARE 1k 类型。
3. 认证阶段 (Step 07–10)
07 Reader → 60 30 76 4a：读卡器发起认证请求 auth(block 30)，表示想要访问存储在第 30 块（block 30）的数据。
08 Tag → 42 97 c0 a4：卡片生成一个随机数 n_T，发送给读卡器，作为挑战（Challenge）。
09 Reader → 7d db 9b ...：读卡器返回 (n_R ⊕ k_s1, a_R ⊕ k_s2)，包含自己的随机数 n_R 和部分卡片随机数 a_R，但它们都经过密钥流 k_s1, k_s2 异或(⊕)加密，防止泄露。
10 Tag → 8b d4 10 08：卡片再回一个 (a_T ⊕ k_s3)，确认双方的认证。
如果双方的加密/解密结果一致，说明都拥有同一把密钥，认证通过，接下来就能安全读写卡片的数据了。
## 伪随机数
在Dismantling MIFARE Classic这篇论文中可以看到这里说明了标签中的伪随机数生成器（LFSR，线性反馈移位寄存器）是完全确定性的。因此它生成的随机数仅取决于上电和通信开始之间的时间，比如上电后过了 100ms 启动通信，永远会得到同一个“随机数”。所以如果攻击者能控制读卡器，就能确保卡片每次产生完全相同的随机数。

![34.png](https://www.iotsec-zone.com/api/image/v2/20250831/dcgnfhk467chnvzvvv.png)
标签中用于生成32位的n_T的随机生成器是以下多项式的16位的 LFSR（线性反馈移位寄存器：用若干前位按固定异或规则算出下一位的移位器）来实现伪随机数发生器（PRNG）

![35.png](https://www.iotsec-zone.com/api/image/v2/20250831/dcgnfodlmi6q3mxyhr.png)
所以 32 位随机数 n_T 的前半部分可以推出后半部分。读到一个 nonce，只要做一些异或（XOR）运算，就能判断它是不是“合法”的卡片随机数。合法 nonce判断：只要满足该多项式成立就可以

![36.png](https://www.iotsec-zone.com/api/image/v2/20250831/dcgnftlterrtczwyub.png)
从上述可以推得

![37.png](https://www.iotsec-zone.com/api/image/v2/20250831/dcgnfz759hdcfaxi4r.png)
后半段的每一位都由前半段的四个位（相隔 0、2、3、5 的位置）异或得到。于是只要知道 n0 ⁣∼ ⁣n15，就能依次算出 n16 ⁣∼ ⁣n31。所以n_T是完全可以控制的
这里的密钥流第一个keystream ks1算法如下：

![38.png](https://www.iotsec-zone.com/api/image/v2/20250831/dcgng5qy75p8rqb6lj.png)
K = 共享密钥（Key A 或 Key B）
UID ⊕ n_T  = 输入偏移量
如果UID ⊕ n_T 一样，keystream 就一样；如果不同，keystream 的差值是固定的。
在这里因为大部分0号扇区是可以直接读取的，所以这里UID是可以直接获取到的，读卡器在上电和防冲突流程中就能直接获取 UID（不需要认证）

![39.png](https://www.iotsec-zone.com/api/image/v2/20250831/dcgngmjuy74vnruabg.png)
在这里部分密钥流是可以被恢复的

![40.png](https://www.iotsec-zone.com/api/image/v2/20250831/dcgnhuxgpvbslusovg.png)
上图描述了卡（Tag）和读卡器（Reader）在认证时交换的步骤：
1. 读卡器先点名（anti-collision），确定 UID。
2. 读卡器请求认证某个扇区（auth(block)）。
3. 卡片生成一个随机数 n_T并发给读卡器。
4. 双方用 K、UID 和 n_T 算出第一个 keystream 块ks_1。
5. 读卡器生成自己的随机数 n_R。
6. 读卡器把 n_R⊕ks1 发给卡，卡就能解出来n_R。
7. 双方继续用n_T, n_R更新 keystream，得到 ks2,ks3,…
8. 卡和读卡器互相发加密后的数据（例如 suc²(n_T)⊕ks2） 来证明自己。
9. 最后卡再发一个 suc³(n_T)⊕ks3，读卡器验证是否正确。
如果验证通过，认证成功，之后的所有通信都会用 keystream 加密。
这里 suc(n_T)，就是指 把 n_T 当作一个 32 位的 LFSR 状态，然后往前跑一步得到的后继状态。
- 同理：
  - suc²(n_T) = n_T 先跑两步后的状态
  - suc³(n_T) = n_T 跑三步后的状态

这里认证协议过程中，攻击者可以推测出部分的keystream，这里攻击思路如下：
- 攻击者看到n_T（卡发出的随机数，明文可见）和suc^2(n_T)⊕ks2,因为suc^2(n_T)是可以算出来的，所以 XOR 一下就能得到 ks2（32 位 keystream）
- 在第 9 步，如果卡不发最后一个响应，读卡器会超时并发送一个 halt 命令。
Halt 命令的字节内容是公开的（比如 0x500057cd）。但是通信是加密的 → 实际上传输的是 halt ⊕ ks_3。所以攻击者知道明文 halt，就能把 ks3 直接推出来。
- 有的读卡器不会发 halt，而是发一个 read 命令。Read 命令的内容和格式也是已知的，所以同样能恢复 ks3。
攻击者只要监听一次认证过程，就能恢复 ks₂ 和 ks₃，甚至在没有知道密钥 K 的情况下，也能得到 keystream。一旦拿到足够的 keystream，就可以用数学方法反推出 Crypto1 的内部状态，最终破解密钥 K。

## Crypto1 密码
### 总体结构：48 位 LFSR + 过滤函
CRYPTO1 是一种流密码（stream cipher：按位/按字节生成密钥流并与明文异或的加密方式）。
核心是一条 48 位 LFSR（线性反馈移位寄存器：用若干抽头位按异或规则计算新位并整体左移），其生成多项式（generating polynomial：决定哪些位异或参与反馈）为：

![41.png](https://www.iotsec-zone.com/api/image/v2/20250831/dcgnirkzo1vhoz025z.png)
每个时钟拍，寄存器左移一位，最左位丢弃，按上式异或得到的新 反馈位 从右端灌入。初始化阶段还有一个外部输入位 i 会与反馈再异或后送入（正常工作阶段就不再用了）。
```
时刻 k 的寄存器状态（48 位，左→右）：
[r_k][r_{k+1}][r_{k+2}] ... [r_{k+42}][r_{k+43}][r_{k+44}][r_{k+45}][r_{k+46}][r_{k+47}]
  |      |        |                    |                               ^
  |      |        |                    |                               |
  |      |        |                    +-------------------------------+---- 抽头(tap：被选来参与计算的位)
  |      |        +----------------------------------------------------+---- 抽头
  |      +-------------------------------------------------------------+---- 抽头
  +--------------------------------------------------------------------+---- 抽头
                                 这些“抽头”位一起送去做异或 →  ○  （⊕）
                                                     外部输入 i →  ↘  （仅初始化阶段）
                                                              反馈位 fb = (抽头异或) ⊕ i

左移一位（最左丢弃），把新反馈位 fb 从右端灌入 → 得到时刻 k+1：
[r_{k+1}][r_{k+2}][r_{k+3}] ... [r_{k+43}][r_{k+44}][r_{k+45}][r_{k+46}][r_{k+47}][ fb ]

同时，从固定的 20 个抽头位取值送入过滤函数 f(x)（把多位压成1位的布尔函数）：
     ┌───────────────────────────────────────────────────────────────┐
抽头 ─┤            f(x)  ──► 输出 1 位密钥流 keystream               ├─► 与明文做 XOR 进行加/解密
     └───────────────────────────────────────────────────────────────┘
```
- 取反馈：从若干抽头（tap：被g(x)指定参与计算的寄存器位）取值做异或（XOR：相同为0，不同为1），在初始化时再与外部输入 i做一次异或，得到反馈位 fb。
- 左移：整条 LFSR（线性反馈移位寄存器：按固定异或规则移位的寄存器） 向左移一格，最左位被丢弃。
- 灌入：把刚算出的 fb 塞进最右端，形成下一拍的 48 位状态。与此同时，从固定 20 个抽头位送入 f(x)（过滤函数：把多位压成 1 位的非线性布尔函数），输出一位 密钥流（keystream：用来和明文异或加/解密的序列）。

当初始化时fb计算公式也就是这样，i 是“外部输入位（input bit）”。只在初始化阶段使用，用来把会话信息“揉”进寄存器。初始化结束后，就不再喂外部输入，等价于 i=0。之后每一拍只用抽头异或产生新位。

![42.png](https://www.iotsec-zone.com/api/image/v2/20250831/dcgnjfmol06zd6kgle.png)
所以这里的密钥流（keystream：用来与明文 XOR 的比特序列）不是直接从 LFSR 的某一位取出，而是把 LFSR 的若干位送入一个 过滤函数 f(x)（非线性布尔函数：把多位输入压成 1 位的函数），其输出就是当拍的密钥流位。

![43.png](https://www.iotsec-zone.com/api/image/v2/20250831/dcgnjt5gt2fgllqsoj.png)

![44.png](https://www.iotsec-zone.com/api/image/v2/20250831/dcgnk04q8vq0ahbiak.png)
### 滤波函数f(x)
当读卡器随机数的第 1 位 n_R,0 发送时，f第一次被调用，而研究员可以把此刻 LFSR 的状态 α 精确设成自己想要的值（把 uid=0、key=0，并用 48 位 tag nonce 定位状态）。因此他们能观测到 n_R,0⊕f(α)；又因为每次都重新上电，n_R,0 在每次实验里是同一个常数，等价于是直接在看 f(α) 的变化。若前后不同 ⇒ 第 i 位一定是 f 的输入。在这里f 只读 20 个“奇数编号”位：9, 11, …, 45, 47。
    在这里研究员猜测CRYPTO1 的 𝑓也分两层：
- 第一层：5 个“四输入小电路”，分别吃 5 组奇数位：(9,11,13,15), (17,19,21,23), (25,27,29,31), (33,35,37,39), (41,43,45,47)
- 第二层：把这 5 个一位输出再组合成最终 1 位密钥流。
并后续通过穷举方式验证了这种猜测（输入只取 9–47 的奇数位）

    接着他们猜测这些输入被分成5 组，每组 4 个，先各自进“一层小电路”，再把 5 个输出丢进“二层电路”合成最终的密钥流位。这跟另一款 NXP 标签 Hitag2 的结构很像。于是就做实验：固定其它位，只把某一组 4 位在 16 种组合里全试一遍，观察第一位密钥流是全 0、全 1，还是“8 个 0 + 8 个 1（平衡）”。若出现“平衡”，就说明这 4 位确实是一颗 4 输入小电路的真正输入。
结果发现：一层有两种 4 输入小电路：
- 两颗用函数 fₐ，它的真值表（truth table（把输入到输出的映射按顺序列成 16/32 位的表））是 0x26c7；
- 三颗用函数 f_b，真值表 0x0dd3。
这 5 个输出再进二层 f_c（5 输入），真值表 0x4457c3b3。
下图就是整个滤波器的“接线图”：LFSR（上面那条长长的格子线）取奇数位，先过五个 4 输入门（左右各两颗 fₐ，中间三颗 f_b），它们的 5 位结果再喂给二层 f_c，产出“密钥流一位”。

![45.png](https://www.iotsec-zone.com/api/image/v2/20250831/dcgnkjwr1ev24hfpcm.png)
该图就是整个滤波器的“接线图”：LFSR（上面那条长长的格子线）取奇数位，先过五个 4 输入门（三个f_b，两个f_a），它们的 5 位结果再喂给二层 f_c，产出“密钥流一位”。
### MIFARE 的弱点与利用
这里是结合现有论文以及自己理解的攻击面分析
#### LFSR 状态恢复（恢复密钥）
##### 通过表格分割密钥
首先，构建一个由元组 (lfsr, ks) 组成的表，其中 lfsr 遍历所有形如 0x000WWWWWWWWWW 的 LFSR 状态，ks 是它们生成的密钥流的前 64 位。这个一次性计算可以在普通计算机上执行，并且可以用于任何读卡器/密钥。这会生成一个包含 2 行的表。

现在我们专注于一个我们想要攻击的特定读卡器。对于每个 12 位数字 0xXXX，我们使用相同的 uid 启动一个认证会话。我们将标签的挑战随机数设置为 n= 0x0000XXX0。当读卡器回答 n_R⊕ks1、suc²(n_T)⊕ks2 后，我们不回复。然后大多数读卡器会发送 halt⊕ks3。由于我们知道 suc²(n_T) 和 halt，我们可以恢复 ks2，ks3。

也就是说攻击者首先进行离线计算：创建一个表格，存储 LFSR 的状态 和 密钥流的前 64 字节。这个表格的计算只需要一个标准硬件平台和 约 1TB 的存储空间。这意味着，攻击者可以通过预先计算这个表格来缩短攻击时间。
通过 计算机逆向，当得到 与密钥流相关的 64 字节 后，可以 反向推算 LFSR 初始状态，从而获得 MIFARE Classic 的密钥。

攻击过程：
- 离线部分：创建表格，包含 LFSR 状态 和 密钥流的前 64 字节。只要表格创建完毕，攻击者就可以利用这个表格进行攻击，而无需再次计算。
- 在线部分：攻击者需要 与读卡器进行 212 次认证会话。每次会话都计算出 下一次的密钥流，并根据已经计算的表格来推算出 密钥。
效率：
- 每次计算密钥流时，一秒钟内可以记录 5 到 35 次认证会话。因此，收集完 212 次认证会话所需的时间为 2 到 14 分钟，攻击者需要站在读卡器旁边等待。
所需资源：
- 需要 约 1TB 的存储空间来保存表格，用于重复攻击。

##### 通过 CRYPTO1 函数反转密钥流
这种攻击方法不再依赖于离线计算，而是利用 CRYPTO1 算法的可逆性。Gans 等人发现，通过 反转 CRYPTO1 的 f(x) 函数，攻击者能够在认证结束后恢复 LFSR 的状态。一旦恢复了 LFSR 的状态，攻击者就能够 反向推算到初始状态，从而恢复密钥。因为CRYPTO1 的滤波函数 f(x) 是可逆的（invertible）；只凭一次会话里若干已知明文（known-plaintext）对应的密钥流（keystream：流加密按位异或到明文上的伪随机比特序列），就能把 LFSR 的末态“解出来”。随后利用 LFSR 的线性递推把状态反向回溯到初始=密钥。
大致步骤如下：
Step 0｜抓一段完整的“认证→首个读/写交互”
嗅探或主动发起一次认证（Key A/Key B 均可），从卡发 N_T 之后开始把每一帧的密文位逐位记下（含数据位与 CRC；奇偶位按“重用密钥流位”的规则标注好偏移）。
Step 1｜定位“已知明文”并扣出密钥流片段
- 选一段你确定明文的密文字段（例如去读扇区尾块：返回“0^6”那 6 字节）。
- 逐位做：keystream_bit = ciphertext_bit ⊕ known_plain_bit，得到连续密钥流片段（长度尽量长，越长越稳）。
Step 2｜用 f(x)的可逆性恢复 LFSR 状态
把这段连续密钥流喂给“CRYPTO1 反求器”（本质是利用 f(x)可逆与抽头关系解方程），解出会话末端（或某时刻）的 48 位 LFSR 状态。
Step 3｜把 LFSR“倒车”回初态
LFSR 是线性的，上一拍状态可由当前状态确定性回推。把刚恢复的末态逐拍回退，越过会话期间的移位，继续回退穿过“注入 UID/随机数”的阶段，回到初始化时刻。CRYPTO1 在最开始用秘密密钥给 LFSR 置初值，所以初态 = 密钥。
Step 4｜验证
用你恢复的 Key A/Key B 去对该扇区或其它扇区做一次认证，若成功则密钥正确。
#### 嵌套攻击（nested attack）
设你知道任意一个扇区的密钥（现实里很多卡某些扇区仍是出厂默认密钥），步骤如下：
1. 先和已知密钥的扇区完成一次认证
得到一条正在运行的加密通道 S₀（我们“掌握”它，因为我们知道密钥且明文可控）。
2. 在这条通道里发起“第二次认证”到目标扇区（未知密钥 Ku）
读卡器要发送两字节的 AUTH 命令 + 块地址 + CRC，这些明文我们全知道。由于此时这批字节会被 S₀ 加密：
  - 我们立刻得到对应的密钥流片段：KS_known = CIPHER ⊕ PLAINTEXT。
  - 更关键的是：流加密可任意改明文（已知密钥流即可构造任意密文让卡“看到”我们想要的明文），所以我们能精确控制“卡何时收到认证请求”。
3. 卡对第二次认证做回应：发出新的 nonce（NT₂）
差异点来了：在“第二次及之后的认证”里，卡对这次认证的第一个响应（NT₂）已经切换到目标扇区的密钥 Ku 上来加密。
  - 也就是说我们收到的是：C = NT₂ ⊕ KS_u(前若干比特)，这里的 KS_u 是未知密钥 Ku对应的密钥流。
4. 我们“知道”NT₂ → 直接扣出未知密钥流片段
为什么能“知道” NT₂？因为卡的 nonce 由弱 LFSR产生，且按固定节拍推进。借助第 2 步我们对发送时机的微调：
  - 我们可以预测卡此刻会给出的 NT₂（LFSR 只有 16 位有效熵量级、可前后推演）。
  - 一旦知道 NT₂，当场就有：KS_u = C ⊕ NT₂。这就获得了用未知密钥 Ku 生成的密钥流片段。
5. 用 (NT₂, KS_u) 反推 Ku
CRYPTO1 的内部是 48 位 LFSR + 过滤函数。给定卡 UID、NT₂ 和一段起始密钥流，可以用已公开的逆向算法/预计算表快速求解 Ku。
这一步不必完成第二次认证——只要拿到第一帧 C = NT₂ ⊕ KS_u 就够了。
6. 连锁扩展
拿到一个新扇区的密钥后，重复 1–5，很快把整张卡所有扇区密钥都“串”出来。这就是“多扇区认证”的连锁效应。
#### 重放攻击
1. 攻击者先监听一次合法的读卡器（reader）和卡片（tag）之间的通信，拿到一次完整的交易数据。
2. 因为 PRNG 在卡片每次通电后都会重复同样的序列，所以攻击者可以推算：在通电后第 t_n 时刻，卡一定会产生和之前一模一样的随机数（nonce）。
3. 攻击者在同样的时间点 t_n 发起交易，卡会产生和之前相同的 nonce → 从而整个加密通信过程可被重放。

#### 密钥流恢复
利用 弱 PRNG（伪随机数发生器：产生“随机数”的算法） 和 流加密（stream cipher：用“密钥流”与明文逐位异或） 的性质，在重复密钥流出现时，把密钥流“扣”出来，从而读出部分明文、进而解密更多内容。

![46.png](https://www.iotsec-zone.com/api/image/v2/20250831/dcgnom6ny4cebpuars.png)
把密钥流想成一条“遮光胶带”。明文贴上这条胶带（与密钥流做 XOR/异或）就变成密文。同一条胶带如果贴在两张纸上，然后你把两张纸叠一起再撕一次（两份密文相互异或），胶带会对消掉，露出两张纸上被胶带覆盖处的差异；只要其中一张纸的内容你事先知道，另一张纸对应的那部分就能被读出来。
在 MIFARE Classic 里：
- 由于卡的 PRNG 用 LFSR（线性反馈移位寄存器：会按固定节拍从同一初始状态重复同样序列），在控制好“上电后的相同时间点 tnt_ntn”发起会话，就能得到相同随机数（nonce），从而导出相同的密钥流；研究者用 Proxmark III 做到了重复 nonce → 重复密钥流。
- CRYPTO1 是流加密：收发的比特都是“明文 ⊕ 密钥流”。（连奇偶位的处理也会重用密钥流的比特。）​
具体思路如下：
1. 先抓一条含“读命令”的合法事务，然后重放这条事务，但把要读的块号改掉（仍在同一个 t_n上电时刻，以保证密钥流相同）。
2. 为了得到“已知明文”，利用 MIFARE 的访问规则：Key A 永远不可读；若去读它，卡会回 6 字节全 0（而不是密钥本身）。如果扇区用 Key B 作为“钥匙而非数据”，读 Key B 也会返回 0。这就给了我们“已知明文 = 0…0（6 字节）”。
3. 在同一 t_n：
  - 读“钥匙块”→ 得到密文 C_1 = 0^6 ⊕ K_n（后续字节另当别论，关键是前 6 个字节）。
  - 立刻再读另一个目标块→ 得到密文C_2 = P ⊕ K_n（P 是目标块的明文数据）。
  - 把两条响应相异或：C_1⊕C_2=(0^6⊕K_n)⊕(P⊕K_n)=0^6⊕P=P
4. 因为“同样的密钥流 K_n”被异或了两次而抵消，于是我们直接得到目标块前 6 字节明文（上图就画的是这个“密钥流掉出（drops out）”的过程）。

小结：已知明文（6 个 0）+ 重复密钥流 → 两个密文相异或，密钥流消掉，露出另一个未知块的前 6 字节明文。

# 参考文章：
[https://flaviodgarcia.com/publications/Dismantling.Mifare.pdf](https://flaviodgarcia.com/publications/Dismantling.Mifare.pdf)
[https://zhuanlan.zhihu.com/p/465900396](https://zhuanlan.zhihu.com/p/465900396)
[https://www.cnblogs.com/klchang/p/4668202.html](https://www.cnblogs.com/klchang/p/4668202.html)
[https://zhuanlan.zhihu.com/p/22600997](https://zhuanlan.zhihu.com/p/22600997)
[https://bbs.kanxue.com/thread-225059.htm](https://bbs.kanxue.com/thread-225059.htm)
[https://www.freebuf.com/vuls/382162.html](https://www.freebuf.com/vuls/382162.html)
[https://xiaohei.moe/post/2024/11/25/alipay-nfc-tag/](https://xiaohei.moe/post/2024/11/25/alipay-nfc-tag/)
[https://blog.csdn.net/liudong200618/article/details/133749250](https://blog.csdn.net/liudong200618/article/details/133749250)
[https://www.bilibili.com/video/BV1K7411s7b7/?spm_id_from=333.788.player.switch&vd_source=ff26bb27f81e2e2fd718cd0717f360a8&p=16](https://www.bilibili.com/video/BV1K7411s7b7/?spm_id_from=333.788.player.switch&vd_source=ff26bb27f81e2e2fd718cd0717f360a8&p=16)
