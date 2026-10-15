# Modbus利用手法与规则监测
> 达达
> 来源：https://www.iotsec-zone.com/article/253

# 前言
Modbus协议是一种已广泛应用于当今工业控制领域的通用通讯协议。通过此协议，控制器相互之间、或控制器经由网络（如以太网）可以和其它设备之间进行通信。Modbus协议使用的是主从通讯技术，即由主设备主动查询和操作从设备。一般将主控设备方所使用的协议称为Modbus Master，从设备方使用的协议称为Modbus Slave。典型的主设备包括工控机和工业控制器等；典型的从设备如PLC可编程控制器等。今天的例子利用模拟器，带来模拟读寄存器，写寄存器，Force Listen Only Mode攻击的协议和IDS规则分析。

跟suricata相关的在之前病毒分析的时候有提到:

IDS规则:搜索Th0r安全公众号，搜索IDS规则关键字

# 正文

针对modbus的协议遵守:

主设备向从设备发送请求

从设备分析并处理主设备的请求，然后向主设备发送结果

如果出现任何差错，从设备将返回一个异常功能码 

所以这里需要两个模拟软件，Poll和Slave。

![0.png](https://www.iotsec-zone.com/images/MdImg/708bc15be26258edf86c2ebe0add6c2d.png)
![1.png](https://www.iotsec-zone.com/images/MdImg/c2c6912361c3d39bb23695110387473e.png)

将主和从模拟，配置好，发送修改请求。

![2.png](https://www.iotsec-zone.com/images/MdImg/98ef1255599e3e5c65efbcdf67b17e58.png)

利用MSF的模块，对其进行读取寄存器

![3.png](https://www.iotsec-zone.com/images/MdImg/787f9b98724870df0775dc5e3c728cdd.png)
![4.png](https://www.iotsec-zone.com/images/MdImg/b67f992568bce314e3493f3c7008b946.png)

下面是写寄存器
![5.png](https://www.iotsec-zone.com/images/MdImg/5b335bcb76c512e26de48930351343ce.png)

流量形式:
![6.png](https://www.iotsec-zone.com/images/MdImg/cb3df69eeaeb137453f8e191b8e0c49d.png)

这里下载前人的规则和流量包来学习

[https://github.com/digitalbond/Quickdraw-Snort](https://github.com/digitalbond/Quickdraw-Snort)

这里一条规则是Force Listen Only Mode的攻击
![7.png](https://www.iotsec-zone.com/images/MdImg/af13db1f133f326052645f5a32992266.png)

查看规则的定位，偏移两处00 00,偏移7 08 00 04，这里要注意的偏移是modbus字段位置的偏移，因为用到的是如图。

![8.png](https://www.iotsec-zone.com/images/MdImg/14f2777dd74fc126707a7bb7e77ccef6.png)

查看流量包，偏移和长度一致。

![9.png](https://www.iotsec-zone.com/images/MdImg/1d90cf4e4fcf582ffef1267f91fb4968.png)
