# 卫星通信GSE封装解析
> ChaMd5
> 来源：https://www.iotsec-zone.com/article/23

## GSE介绍

卫星通信近几年逐渐火热，目前的低轨卫星通信大多数采用欧盟ETSI的数字卫星电视广播标准（DVB-S/DVB-S2 /S2X）并做改进。而通常它们用通用流封装，因此，在卫星安全的研究中，对一些数据的解析需要对GSE封装协议有所了解，所以笔者近期对官方文档阅读并做出一些笔记。

通用流封装（GSE）协议可以在物理层对IP和其他网络层数据封装，在通用流上提供网络层数据包封装和分片功能。GSE 不仅可以灵活的分片和封装，而且能使用智能调度器来优化系统性能。不仅如此还：

- 支持多协议封装(IPv4、IPv6、MPEG、ATM、以太网、802.1pQ VLANs 等)。
- 对网络层功能的透明性。
- 支持多种寻址模式。
- 可扩展性

## 封装方法

PDU（协议数据单元）可以封装在一个GSE包中，也可以分成片段封装成几个GSE包。而GSE包的长度是动态可变的。GSE包可在不同基带桢中发送，基带桢长度是可变的。GSE没有独自的完整性校验机制。通常一段数据碎片化变成几个PDU片段，在最后一段加CRC-32。如图是DVB协议的GSE封装：

![0.png](https://www.iotsec-zone.com/images/MdImg/248219ed9383cc4544b1b457f091a037.png)

GSE包的头由固定长度（2bytes）和可变长度组成（0-11bytes）。固定长度主要有S 、E 、LT 、GSE Length等字段，可变部分主要是Fragment ID、Total Length、Protocol Type和Label等字段。如下图：

![1.png](https://www.iotsec-zone.com/images/MdImg/1680009ee2f072bb1748d6c9cdd2f190.png)

每个GS流可存放最多256个PDU碎片，每个GSE数据包的头有一个开始指示位（S）和结束指示位（E），开始指示位为“1”表示PDU开始，结束指示位为“1”表示PDU结束。如果都为1表示是一个完整的PDU。

而接下来有两位标签类型指示（主要用于寻址）。标签存在时，接收者可以删去标签不匹配的数据包。当为广播包时，接收者都应该处理该数据包。标签重复时，只有上一个GSE包的地址与现在匹配，接收者才去处理。所以标签重复主要用于同一个基带桢中。

![2.png](https://www.iotsec-zone.com/images/MdImg/7ce17817318d13b3e2dc844a2ad6a392.png)

接下来12位表示GSE包长度，最大2^12（4kb）。注：End包最后包含CRC-32。

Fragment ID只会在中间包出现，同一个PDU的GSE包有相同的ID。所以只有一个PDU传输完成，才可以有另一个PDU使用这个ID。

- 含有同一PDU数据的GSE包必须用相同Frag ID
- 第一个 GSE 数据包的 S 位应等于 "1"，E 位等于 "0"。
- 中间PDU片段 S 位和 E 位等于 "0"。
- 最后一个 GSE 数据包的 S 位应等于 "0"，E 位等于 "1"。
- 一个 PDU 没穿完，它的 Frag ID 不得重复使用。
- 具有相同片段 ID 的 GSE 数据包必须按顺序传输。

Total Length这个是保存PDU的总长度，所以通常在PDU碎片的第一个包中才有。总长度最高65536个字节，CRC-32不包含其中。

Protocol Type 0-0x5FF表示Next Header，0x600-0xFFFF表示 Ether Type。

## CRC-32

为了防止PDU包的数据丢失，所以在PDU最后一个GSE包放入一个32位的CRC字段。定义的CRC多项式为

![3.png](https://www.iotsec-zone.com/images/MdImg/b4e93732ad0a42c7176b1c1c8294b8c9.png)

初始累积器为0xFFFFFFFF。然后PDU的字节、总长度、协议类型、标签、扩展头等计算。

## 数据字段

Protocol Type定义了扩展头，扩展头属于数据的一部分，所以数据段的数据结构如下

![4.png](https://www.iotsec-zone.com/images/MdImg/65cb725e564862db1f8648a72492030d.png)

- 如果有可选扩展头，跟在GSE头之后

- 如果有强制性扩展头，跟在可选扩展头之后

- PDU跟在强制扩展头之后。

上面三部分都不是必须有的。

## 解析流程图

![5.png](https://www.iotsec-zone.com/images/MdImg/32f9449cbc50a5f1070e702187b921af.png)

## PDU分片

### 首包

- S 位设置1，E 位设置 0
- GSE 长度设置为计算出的字节数（包括数据的长度和片段 ID 字段、总长度字段、协议类型字段、标签字段和任何扩展头等长度）。
- 将 Frag ID 设置为一个任意值。
- 总长度字段设置为计算出的字节数，（PDU、协议类型字段、标签字段和扩展头的长度。）
- 添加一个协议类型。
- 添加标签字段。（如果需要）
- 放入第一段PDU碎片数据。
- GSE包放入基带桢

### 中间包
（如果PDU分为2个以上碎片时）

- S 位设置0，E 位设置 0
- GSE 长度设置为计算出的字节数（包括数据的长度和片段 ID 字段长度）。
- 将 Frag ID 设置为首包设置的值。
- 放入一段PDU碎片数据。（按顺序放）
- GSE包放入基带桢

### 尾包

- S 位设置0，E 位设置 1
- GSE 长度设置为计算出的字节数（包括数据的长度和片段 ID 字段、CRC-32字段长度）。
- 将 Frag ID 设置为首包设置的值。
- 总长度字段设置为计算出的字节数，（PDU、协议类型字段、标签字段和扩展头的长度。）
- 放入最后一段PDU碎片数据，并加上CRC-32值。
- GSE包放入基带桢

## 封装器调度

GSE封装器中的调度器，在基带桢中是智能放置，以提高效率。

如下图，PDU1、PDU2 和 PDU3 构成一个 PDU 序列，由调度器预先排定。（MODCOD 表示PDU 相关的调制格式和编码率）如果 MODCOD2 的效率高于 MODCOD1 的效率，那么我们应该采取 MODCOD1 对应的才会更稳定。PDU 被封装并由 GSE 封装器排入基带帧。

![6.png](https://www.iotsec-zone.com/images/MdImg/6bbd28090b34ceb43919c98db7959044.png)

当 PDU 被分割时，像上图 PDU2 ，剩余的 PDU 片段被封装在一个独立的 GSE 包中，在下一个基带帧中传输。如果没有利用智能调度策略，PDU2剩余的包与PDU3的包封装在同一个基带桢里。基带桢不得不降级。而如下图操作，能实现更好的系统效率。

## 参考

- 本文主要参考 ETSI 官方协议文档。
