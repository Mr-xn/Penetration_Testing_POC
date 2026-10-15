# 智能门锁安全分析：多方位探索硬件、固件、app和云端
> 小黑
> 来源：https://www.iotsec-zone.com/article/387

## 简介

本文主要针对一款智能门锁进行安全分析，并探索了从硬件、固件、App到云端多个层面的安全问题。在分析过程中，发现了门锁采用的离线动态密码生成算法,并对其进行了分析。同时，利用序列号越权获取门锁状态信息。在挖掘漏洞的过程中，我们进行了固件提取、固件分析、获取UART shell、分析App和通信协议等多种手段，从不同的角度深入分析了门锁的安全问题。

## 功能分析和离线动态密码生成机制

该智能门锁采用了一种离线动态密码生成算法。门锁在进入配网模式后，会生成一串经过AES加密的数据，并通过wifi模组发送给App。App需要使用管理员密码进行解密，从而得到randomcode。此时，randomcode作为生成动态密码的参数之一。另一个参数是门锁的序列号。但是，生成动态密码的过程还需要考虑时间同步的问题。如果门锁的时间与App的时间不同步，就可能导致生成的动态密码无效，无法开锁。

 

## App分析和动态密码生成过程追踪

如下图,Yb方法，它返回一个动态密码，是在用户使用App开锁时自动生成的且每五分钟更换一次。

 

首先，代码通过调用this.v来获取WifiLockInfo对象，这个对象包含了门锁的一些信息，如wifiSN和randomCode等。然后将这些信息和当前时间戳组合成一个字符串str。

 

接下来，代码将字符串str转换为一个字节数组，并使用SHA-256哈希算法对字节数组进行哈希运算，得到一个长度为32字节的哈希值。然后从哈希值中取出前4个字节，将它们转换为一个整数i。

 

最后，将整数i对1000000取模，得到一个6位数的动态密码，然后将其返回。

![0.png](https://www.iotsec-zone.com/images/MdImg/66645042cf011e5a62f48d5e374d888b.png)

由此可知生成动态密码需要序列号以及一个未知的randomCode参数
![1.png](https://www.iotsec-zone.com/images/MdImg/53a944e11c95fe65e5ad3e828a79523a.png)

## 随机码的产生过程定位

1.通过抓包分析和逆向工程，定位到了门锁绑定接口的位置

![2.png](https://www.iotsec-zone.com/images/MdImg/639f2950148594aa8a27e0d289b28634.png)

![3.png](https://www.iotsec-zone.com/images/MdImg/23c9209f2fda16321c361e303b7fb47e.png)

2.在绑定接口的代码中，通过调用 getstringextra("wifilockrandomcode") 方法获取了随机码。

![4.png](https://www.iotsec-zone.com/images/MdImg/6b7ee401f4701e7acceaef87c86f8740.png)

![5.png](https://www.iotsec-zone.com/images/MdImg/32118e632d17152963fd240ea4f0d05b.png)

3.为了追溯随机码的产生过程，使用全局搜索找到了随机码赋值的位置。

![6.png](https://www.iotsec-zone.com/images/MdImg/dfcb41fc94dc95ef032db1a6e945836a.png)

4.下图就是赋值randomcode的方法，在m14595e方法中首先将输入的字符串进行补0操作，再进行 SHA-256 的摘要计算；将摘要值与输入的字节数组进行 AES 解密操作，得到随机数和校验和；对随机数进行 CRC32 校验，与解密得到的校验和进行比较，判断是否匹配。
其中，第一步是对输入的密码进行处理，以便于后续的加密和解密操作。第二步是通过密钥将输入的字节数组进行解密，得到随机数和校验和。第三步是对随机数进行 CRC32 校验，以验证其合法性。

我们只关心randomcode的生成也就是bArr4，根据代码分析得知调用m20569e进行aes解密之后得到了e2，其中参数一是由m14595e中的参数二取0-32得来，参数二是由m14595e的参数一补0然后sha256得来。

![7.png](https://www.iotsec-zone.com/images/MdImg/15aebd9e218ac8e4cbff621da023d70e.png)

5.通过回溯调用关系可以推断参数一为门锁的管理员密码，参数二为AP模式下设备发给app的aes加密过的数据。

![8.png](https://www.iotsec-zone.com/images/MdImg/8d4b3725987450d3a214318ab84c5647.png)

![9.png](https://www.iotsec-zone.com/images/MdImg/ba634b4233e64887b70a3fa22868087d.png)

![10.png](https://www.iotsec-zone.com/images/MdImg/0d14e3b3a520d2d88b2c24e88d2d7e18.png)

 

## wifi模组固件提取

1.通过芯片手册还可以得知其是外置flash，拆下来的flash芯片将其焊接到转接板上。

![11.png](https://www.iotsec-zone.com/images/MdImg/591d752948decef4e8e091d1aed7dc02.png)

2.放入编程器读取固件，编程器识别出flash芯片型号。读取固件另存为bin文件。

![12.png](https://www.iotsec-zone.com/images/MdImg/f6e3086513bd1ce169456983299f7534.png)

## 串口shell

1.可以看到主板上预留的uart接口，查看芯片手册可以确认芯片预留有uart和spi接口。现在开始连接uart接口先接GND让主板和ch340共地然后主板的rx与ch340的tx相连接，主板的tx与ch340的rx相连接。

![13.png](https://www.iotsec-zone.com/images/MdImg/ba99c11e57b9e2fdbc76540b16825054.png)

2.连接电脑后设置波特率20000获得shell，如下是输出的日志。

![14.png](https://www.iotsec-zone.com/images/MdImg/164a7a8fbb3b0e5b8194bdf9d528b200.png)

## AES加密数据分析和随机码的推测

1.在进行配网的时候查看wifi模组日志看到g_tx_buffer[45]与app中大小一致且是在配网过程产生的由此可以推测打印出的这串数据很有可能就是randomcode aes加密过的数据。

![15.png](https://www.iotsec-zone.com/images/MdImg/9ac637e6206348263640b4bc5eb01937.png)

2.查看固件可以看到序列号,连接的wifi名，密码等，设置好固件架构，基地址等搜索字符串send opf data定位到日志输出的位置回溯，FUN 230acdd8的代码表示将0x4201cc08处的内容赋值给DAT_420122d0.

![16.png](https://www.iotsec-zone.com/images/MdImg/d2e84489ae2851895870209aaef544c2.png)

![17.png](https://www.iotsec-zone.com/images/MdImg/f13dae31f176a79773535dd329d2afc1.png)

![18.png](https://www.iotsec-zone.com/images/MdImg/f1affff7ac80289d0e6b4f978eee03bc.png)

3.在门锁进入配网模式后可以看到0x4201cc08有了内容。

![19.png](https://www.iotsec-zone.com/images/MdImg/cba8e63eafda74e36af5c38b3f0193d0.png)

4.全局搜索-0x3f8的位置查看操作0x4201cc08的位置,下面代码0x4201cc08开始到0x4201cc28就是aes加密过的randomcode,从0x4201cc28开启0xe个字节这里其实是设备的序列号，他们都取决于参数二。

![20.png](https://www.iotsec-zone.com/images/MdImg/8a03e3b8f6e9b3effecea37b729b4f68.png)

![21.png](https://www.iotsec-zone.com/images/MdImg/32912e03d50479f53b85cd3196d203d0.png)

5.回溯看到可能是一个回调函数。推测参数二可能是门锁向wifi模组传输的数据。

![22.png](https://www.iotsec-zone.com/images/MdImg/f7c24696a1e3c19a8e59765746f2f5fe.png)

6.同时发现在进入配网模式后wifi模组会recv一段data而这串数据包含0x4201cc08的内容，由此可以确定aes加密过的数据是在门锁固件里面生成发给wifi模组的。

![23.png](https://www.iotsec-zone.com/images/MdImg/369a8394ce01f9aeeffc4eacc5bb1fdf.png)

7.下面是把wifi模组recv data的aes加密的部分拿出来，并使用管理员密码对其aes解密得到的就是randomcode。

![24.png](https://www.iotsec-zone.com/images/MdImg/cf808107ec4237a0811eabf750721749.png)

8.	那这里如果想知道randomcode怎么生成的就需要提一下门锁固件了，要说明的是固件存放的位置一般分为两种，一种是集成在MCU中，另外一种是单独放在一块芯片上，这里的芯片没有找到datasheet，所以就直接把看着像外置flash的芯片提了一下发现都不是，难受噢，不过想了两种情况：
第一种：门锁->随机数->sha224->randomcode
第二种：门锁->随机28个字节的十六进制数->randomcode
后面有机会在验证下！

## 序列号越权绑定门锁和劫持门锁状态信息

1.回到绑定过程，请求包是加密的，对其hook可以看到包含六个参数，其中包含了设备的序列号，用户id，randomcode等。因为randomcode是门锁生成的通过ap模式传给了app，app会把randomcode发给云端保存，但是在这里randomcode云端是没有校验的。所以我们要想劫持门锁app权限，只需要将arg0与arg1写成我们想要劫持的设备的序列号就可以了。

![25.png](https://www.iotsec-zone.com/images/MdImg/7abcbffd3518ff1158fddca28ec56b53.png)

![26.png](https://www.iotsec-zone.com/images/MdImg/9c88637e227dd416be7d222e26aabd11.png)

2.然后逆向一下算法写个脚本跑一下就可以劫持指定序列号的门锁获取其app权限了。

![27.png](https://www.iotsec-zone.com/images/MdImg/f4ccd34ec6492c15b6917a88a53fce21.png)

## 总结
在本文的分析过程中，我们深入探索了一款智能门锁的多个安全层面，包括从硬件、固件、App到云端。我们发现了该门锁采用的离线动态密码生成算法，以及利用序列号越权获取门锁状态信息。通过固件提取、分析、获取UART shell、分析App和通信协议等多种手段，我们从不同的角度深入挖掘了门锁的安全问题。这些发现和分析提醒我们，智能设备的安全性需要重视，并且在设计、开发和使用过程中要采取有效的安全措施。
