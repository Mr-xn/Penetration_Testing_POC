# 手把手带你分析mips架构下固件分析与漏洞挖掘
>  meigui
> 来源：https://www.iotsec-zone.com/article/503

## 固件分析和解包

 拿到固件后，第一步是对其进行解包分析。我们通常查找 `busybox` 可执行文件来判断固件的 CPU 架构（如 MIPS、ARM）、端序（大端或小端），以及是否开启了安全机制（如堆栈保护、NX）。`busybox` 一般位于 `/bin` 目录中。通过如下命令我们可以快速获取架构信息，本例中结果显示为 MIPS32 小端架构。  

```c
binwalk -Me WN579A3-WAVLINK-WO-2022-03-23-854d73f.bin
```

![0.png](https://www.iotsec-zone.com/api/image/v2/20250616/danpxosyyro0fdzs3r.png)

### file busybox

用于识别可执行文件类型。通过这个命令我们可以判断 `busybox` 是哪种架构（如 MIPS、ARM）、位数（32/64位），以及是否为静态或动态链接。本例结果显示为：MIPS、32位、小端、静态链接的 ELF 可执行文件。

```c
file busybox
```
![1.png](https://www.iotsec-zone.com/api/image/v2/20250616/danqrt65qxr8smf9of.png)

### readelf -h busybox

查看 ELF 文件头，进一步确认架构信息、字节序、入口点等关键信息。比如：

+ `Class` 显示是 ELF32
+ `Data` 显示是 Little endian（小端）
+ `Machine` 显示是 MIPS  
  这确认了我们之前用 `file` 得出的结论。

```c
readelf -h busybox
```

![2.png](https://www.iotsec-zone.com/api/image/v2/20250616/danqtjxoxy4i0n5ubi.png)

### checksec busybox ### 

用于检查二进制文件的安全特性是否开启，例如：

+ `NX`（No eXecute，是否启用不可执行栈）
+ `PIE`（位置无关执行）
+ `Stack Canary`（堆栈保护）  
  这些信息可以帮助我们判断程序是否容易受到缓冲区溢出等攻击。本例中，大多数保护机制未启用，表明存在潜在的利用空间。

```c
checksec busybox
```

![3.png](https://www.iotsec-zone.com/api/image/v2/20250616/danqvpfx5uzakmqhmb.png)

我们使用自动化工具firmAE起不来考虑系统模拟或者用户模拟

![4.png](https://www.iotsec-zone.com/api/image/v2/20250616/danqvy6w6fdjudkj6g.png)

## 系统模拟
### 启动项分析

 启动项是指设备启动后自动执行的程序或脚本，通常用于初始化系统服务或前后端程序。我们一般在 `/etc/init.d/` 目录中查找这些启动脚本（以 `.sh` 为后缀）。在嵌入式设备中，常见的 Web 服务启动程序有 `httpd`、`lighttpd`、`mini_httpd` 等。发现相关脚本后，应进一步检查其配置文件路径和依赖项。  

![5.png](https://www.iotsec-zone.com/api/image/v2/20250616/danr2oh0hepk8i6pz4.webp)

![6.png](https://www.iotsec-zone.com/api/image/v2/20250616/danr2qkwhy1ic3lare.webp)

![7.png](https://www.iotsec-zone.com/api/image/v2/20250616/danr2sic7tuwre3aeq.webp)

![8.png](https://www.iotsec-zone.com/api/image/v2/20250616/danr2uyk5xp3kgcrzb.webp)

我们在进行mips系统模拟前需要先配置我们的网卡

```c
创建虚拟网卡
sudo tunctl -t tap0 -u `whoami`
sudo ifconfig tap0 192.168.100.1/24 up
```

接下来运行我们mips系统模拟脚本

```c
#!/bin/sh
qemu-system-mipsel \
-M malta \
-kernel /home/iotsec-zone/Tools/qemu-images/mipsel/vmlinux-3.2.0-4-4kc-malta \
-hda //home/iotsec-zone/Tools/qemu-images/mipsel/debian_wheezy_mipsel_standard.qcow2 \
-append "root=/dev/sda1 console=ttyS0"  \
-nographic \
-net nic -net tap,ifname=tap0,script=no,downscript=no
```

我们传输我们解密的文件系统squashfs-root到我们qemu系统模拟中

```c
打包squashfs-root文件
tar -cvf s.tar.gz  squashfs-root

开启7878端口让qemu下载squashfs-root
cd squashfs-root
python -m http.server 7878

qemu模拟
wget http://192.168.100.1:7878/s.tar.gz
解压
tar -zvxf s.tar.gz
```

![9.png](https://www.iotsec-zone.com/api/image/v2/20250616/danr5xzprfqqawcumo.png)

![10.png](https://www.iotsec-zone.com/api/image/v2/20250616/danr61e1k4b6tohy0r.png)

![11.png](https://www.iotsec-zone.com/api/image/v2/20250616/danr6at2sl4nk47tck.png)
我们需要去配置系统环境

```c
目录挂载
mount --bind /proc/ proc/
mount --bind /sys/ sys/
mount --bind /dev/ dev/

qemu虚拟机配置网卡：
ip link add br0 type dummy
ifconfig eth0 192.168.100.2/24
ifconfig br0 192.168.100.3/24
```

 进入模拟系统后尝试使用 bash，但报出非法指令错误，通常是因为 CPU 架构不兼容。我们更换 QEMU 使用的 CPU 为 74Kf（支持更多指令集），重新运行脚本后问题解决  

![12.png](https://www.iotsec-zone.com/api/image/v2/20250616/danr8e9u129wlvvlnd.png)

```c
#!/bin/sh
qemu-system-mipsel \
-M malta \
-cpu 74Kf \
-kernel /home/iotsec-zone/Tools/qemu-images/mipsel/vmlinux-3.2.0-4-4kc-malta \
-hda //home/iotsec-zone/Tools/qemu-images/mipsel/debian_wheezy_mipsel_standard.qcow2 \
-append "root=/dev/sda1 console=ttyS0"  \
-nographic \
-net nic -net tap,ifname=tap0,script=no,downscript=no
```

![13.png](https://www.iotsec-zone.com/api/image/v2/20250616/danr8n7v11t6lbk4bh.png)

我们运行lighttpd程序出现报错，需要去解决错误，我们去我们之前解包的文件系统里面去搜索

![14.png](https://www.iotsec-zone.com/api/image/v2/20250616/danr8q1hy348thqcfl.png)

发现lib目录下有functions.sh，我们先运行这个

![15.png](https://www.iotsec-zone.com/api/image/v2/20250616/danr8svgk4nrukgn3e.png)

![16.png](https://www.iotsec-zone.com/api/image/v2/20250616/danr8wowypnlipn866.png)
我们继续运行./lighttpd，继续解决报错，发现在/rom/etc/lighttpd/没有这文件lighttpd.conf，那我们手动创建一个就行。

![17.png](https://www.iotsec-zone.com/api/image/v2/20250616/danr91gtreeo8sk1he.png)

我们继续运行./lighttpd，没有报错。

![18.png](https://www.iotsec-zone.com/api/image/v2/20250616/danr94klviyvr3glxo.png)
需要注意，这个ip是我们本机配的192.168.100.2,我们需要配置host,关联相关域名。

![19.png](https://www.iotsec-zone.com/api/image/v2/20250616/danrakk9n01ulqsp1b.webp)

![20.png](https://www.iotsec-zone.com/api/image/v2/20250616/danrapzu0cdicrqddj.webp)
### 未授权漏洞(0day)

1.我们使用burp的intruder功能进行快速的寻找漏洞点,我们复制里面文件在web进行拼接

![21.png](https://www.iotsec-zone.com/api/image/v2/20250616/danratpa9lhevjcuib.webp)

我们先弄成全部的文件名。

![22.png](https://www.iotsec-zone.com/api/image/v2/20250616/danrb0878dvkwilcbz.webp)

![23.png](https://www.iotsec-zone.com/api/image/v2/20250616/danrb28r3rskqm7vda.webp)
我们在请求头路径上打点，在payloads复制我们的文件名。点击attack就行。

![24.png](https://www.iotsec-zone.com/api/image/v2/20250616/danrb56uf76mho0wwp.webp)

![25.png](https://www.iotsec-zone.com/api/image/v2/20250616/danrb72js655imvdvu.webp)

我们可以看到有个803f5d.txt信息泄露

![26.png](https://www.iotsec-zone.com/api/image/v2/20250616/danrcsh9sqglalvgl5.webp)
 通过爆破结果可以发现存在信息泄露文件，如 803f5d.txt，该文件可能包含敏感的配置、日志或用户信息，需进一步分析文件内容  

![27.png](https://www.iotsec-zone.com/api/image/v2/20250616/danrc9dc6yfpb8rvwn.webp)
