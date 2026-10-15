# D-Link多款路由器存在cli命令注入
> splash
> 来源：https://www.iotsec-zone.com/article/235

## 漏洞详情
CVE-2022-1262，多款D-Link 路由器固件映像上的 **/bin/protest**二进制文件容易受到命令注入的攻击。这允许经过身份验证的攻击者以 root 身份执行任意 shell 命令，并且可以很容易地用于在设备上获取 root shell。
![0.png](https://www.iotsec-zone.com/images/MdImg/1748db382915356fdba6963ff5af0ee8.png)

## 固件解密
dlink的dir系列解密方法很相似，大多都是在上一版本中存在固件解密文件，一般是以qemu用户态运行解密程序就可以完成，如果找不到未加密的版本或者中间版本的固件时，可找型号相近的固件，实际测试中，某些型号的固件解密程序确实是通用的，大致操作如下，根据架构切换执行根目录，运行相应二进制解密文件
![1.png](https://www.iotsec-zone.com/images/MdImg/f758487af8df0d331767e533b9d47049.png)

## 漏洞复现
在路由器文件系统根目录下，chroot切换根路径
![2.png](https://www.iotsec-zone.com/images/MdImg/c0115e54816a83817cbd1102833a6f25.png)

启动cli，以进入router终端。 
![3.png](https://www.iotsec-zone.com/images/MdImg/ae9ded51cf23b7da7778fb8ad34d8874.png)
（在实际运行的设备中，这里是一个后门，使用telnet连接，账户为admin，web口令+硬编码@twsz2018，如passwd@twsz2018，即可进入）

![4.png](https://www.iotsec-zone.com/images/MdImg/1bbc3ef1e5cf21565be26687d1d74dff.png)
直接运行系统命令会出错，加上分号截断，可以成功执行系统命令

## 漏洞分析
IDA分析**/bin/protest**，已知存在命令注入漏洞，首先查看system调用，有一处会将输入的client_secret值拼接到字符串使用system()去执行，复现时第一条回显信息和伪代码片段上方的printf信息吻合，说明程序确实执行到system()上方，也就没有再去调试看
![5.png](https://www.iotsec-zone.com/images/MdImg/1eee25c327572bf560d499e1a68c3e17.png)

## 漏洞复现总结
1、设备cli命令注入、溢出漏洞多见于交换机或者防火墙中，因其cli一般为受限制，是用户态接口，多为一些系统、运维的配置命令，若想直接执行系统命令getshell，就需要“逃逸”。

2、此漏洞的重点在于，通过硬编码口令，使用telnet进入router cli（是一个低权限的cli），查看所有功能接口，找到对应二进制文件或者关键字符串，在文件系统中检索，随后思路就与分析常规web管理程序或cgi程序步骤相同，找输入点路径，找危险函数，分析逻辑等等。
![6.png](https://www.iotsec-zone.com/images/MdImg/24abda3ea0b6ae145bd1b82a0e70dcf4.png)

3、如直接在固件包中分析protest（或者使用一些自动化分析脚本，污点分析脚本），由于存在漏洞的函数是被外部调用，这里是cli程序调用，再向上回溯调用流程，比较麻烦，如果没耐心的话也可能就会放弃这条链（说我自己），所以直接定位到可疑输入点/程序，无疑是提升信心和效率的一个好方法，属个人挖洞习惯的思路，各位大佬勿喷。

## 应用拓展
当复现完漏洞，在想protest其他参数是否也存在漏洞，看到protest --help有led参数，所以直接试了一下，结果是成功执行了ls命令
![7.png](https://www.iotsec-zone.com/images/MdImg/3dbef3cdd02da10f6425bdf360adc0db.png)
![8.png](https://www.iotsec-zone.com/images/MdImg/e1e478821f230bbb67ee6b7c3d5de5e0.png)

我去按照字符串检索了一下，根据我传的参数，protest程序走到了如下路径，因为确实成功创建了ban_led文件
![9.png](https://www.iotsec-zone.com/images/MdImg/0d0945e9976ffd7aec134d87725f3764.png)
![10.png](https://www.iotsec-zone.com/images/MdImg/9339f9ae4253e79c049bf684dd93c4cf.png)

但是并没有看到命令注入漏洞，怎么还会执行ls命令？查看了一些可能命令注入的敏感函数，路径也对应不上，想是不是cli程序存在命令注入，未分析前，先大胆试一下cli的其他功能接口，就ated（cli help）
![11.png](https://www.iotsec-zone.com/images/MdImg/9eee8c5093a9abd16b3fdab10154d807.png)

尝试直接在ated命令后加分号截断，执行了ip命令
![12.png](https://www.iotsec-zone.com/images/MdImg/bed8368f0696a78961897321dae4037f.png)

拖cli程序进ida分析，检索字符串ated，注册的皆为help看到的接口命令
![13.png](https://www.iotsec-zone.com/images/MdImg/99c9d2ed6b26f043be359c1d56534e28.png)

点进去函数看一下，a2被拼接到v11中，最终被systemCMD()执行，后者为封装后的popen()
![14.png](https://www.iotsec-zone.com/images/MdImg/ab30128bea02f66fac3fe4770fec6685.png)
![15.png](https://www.iotsec-zone.com/images/MdImg/399dc6610bd1409dc7b86064b1a16153.png)

其他的cli注册接口命令也是大同小异，存在与ated接口同样的漏洞。要是逐个接口再去分析，说不定还会找到更多的“逃逸”方法，像protest程序那样，不过我看其他的都是ipconfig之类的，八成厂商也不会自己改，意义不大，就没在看了。

以上只是笔者偶然复现中的发现和一些拙见，没有深入分析，如有哪里不正确，还希望各位大佬一定指正，感谢！！！
