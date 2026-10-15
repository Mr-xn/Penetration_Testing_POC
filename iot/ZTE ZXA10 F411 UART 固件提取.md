# ZTE ZXA10 F411 UART 固件提取
> WLZ
> 来源：https://www.iotsec-zone.com/article/541

# ZTE ZXA10 F411 UART 固件提取

## 简介

本文记录一次通过 UART 串口、临时网络和 BusyBox 工具链提取 **ZTE ZXA10 F411** 整片 Flash 固件的过程。目标设备是一台中兴 EPON/ONU 光猫类设备，串口日志显示其运行 `U-Boot 1.1.3`，Linux 内核为 `2.6.21.5`，Flash 总容量为 `8 MB`。这类设备通常系统较旧，工具被厂商裁剪得很厉害，不能默认拥有完整的 `dd`、`chmod`、`nc`、`tftp` 等命令，因此提取固件的重点不是简单执行一条 dump 命令，而是先确认设备信息、判断 CPU 架构和 Flash 布局，再补充可用工具，最后把完整 Flash 镜像稳定传回电脑。

## UART

UART 是嵌入式设备最常见的调试入口。通过 USB-TTL 模块连接主板上的串口引脚后，可以看到完整启动日志，也可以在启动倒计时阶段进入 U-Boot，或者等待系统启动完成后进入 Linux shell。

- **U-Boot 阶段**：启动早期，提示符通常是 `=>`，可用 `printenv`、`md.b`、`tftp`、`bootm` 等命令。
- **Linux shell 阶段**：系统启动完成后，提示符通常是 `/ #`，可用 `cat`、`ifconfig`、`wget`、`busybox` 等命令。

两者处于不同阶段，网络参数也不是同一套，Linux 里设置了 `br0` 并不代表 U-Boot 的 `ipaddr`、`serverip` 已经配置好。

## U-Boot 

U-Boot 是嵌入式设备常见 bootloader。它负责初始化硬件、加载内核，并将控制权交给 Linux。进入 U-Boot 后，可以查看启动参数、网络参数、Flash 映射地址，也可以通过 `md.b` 直接显示内存或 Flash 映射区域的数据。本设备 U-Boot 帮助命令如下：

![0.png](https://www.iotsec-zone.com/api/image/v2/20260714/djxz5b3h23wba694vb.png)

## 设备识别

串口参数使用常见的 `115200 8N1`。设备上电后，启动日志可以确认型号和硬件信息：

```text
U-Boot 1.1.3 (Jan 18 2012 - 10:08:14)
Board: ZXA10 F411 V2.0
CPU : 300 MHz
DRAM: 64 MB
Flash: 8 MB
```

进入 Linux shell 后，通过 `/proc/cpuinfo` 进一步确认 CPU 架构：

![1.png](https://www.iotsec-zone.com/api/image/v2/20260714/djxz5fwa4nd2t7yc1i.png)

关键字段如下：

```text
system type : ZXA10 F411(V2.0)
cpu model   : MIPS 24K V5.5
BogoMIPS    : 199.88
```

这说明设备是 MIPS 架构，后续下载外部 BusyBox 时应选择 MIPS 版本。

Flash 在 Linux 中通常通过 MTD 设备暴露。`/dev/mtd0` 往往表示整片 Flash，其他 `mtd1`、`mtd2` 等是按用途划分出的分区。本设备的布局可以整理为：

```text
mtd0: 00800000 00010000 "whole flash"
mtd1: 00020000 00010000 "bootloader"
mtd2: 00010000 00010000 "env"
mtd3: 003b0000 00010000 "kernel_ramfs0"
mtd4: 00060000 00010000 "userconfig"
mtd5: 00010000 00010000 "parameter tags"
mtd6: 003b0000 00010000 "kernel_ramfs1"
```

其中 `mtd0` 大小是 `0x00800000`，也就是 `8 MB`。如果目标是完整备份固件，最直接的读取对象就是 `/dev/mtd0`。单独读取 `mtd3` 或 `mtd6` 只能拿到某一个 kernel/rootfs 分区，无法覆盖 bootloader、环境变量、配置区和备用镜像。

## 初始尝试与限制

最开始直接使用原系统命令时会遇到很多限制。原厂 BusyBox 被裁剪过，缺少 `dd`、`chmod`、`nc`、`tftp`、`ftpput` 等关键工具。比如直接执行：

```sh
dd if=/dev/mtd0 of=/tmp/whole_flash.bin bs=64k
```

会失败，因为系统里没有 `dd`。不过原系统里有 `cat`，所以可以先用下面方式验证 `/dev/mtd0` 是否可读：

```sh
cat /dev/mtd0 > /tmp/whole_flash.bin
ls -l /tmp/whole_flash.bin
```

如果得到 `8388608` 字节，说明整片 Flash 可以从 Linux shell 里读出来。但后续还要稳定地把文件传回电脑，原系统自带的网络工具不够完整，所以更稳妥的做法是传入一个功能完整的静态 BusyBox。

这里还需要区分 U-Boot 阶段和 Linux 阶段的传输逻辑。U-Boot 里的 `tftp` 通常是把文件下载到某个 RAM 地址，例如 `tftp a0800000 test.bin`，它不是把文件保存到 `/tmp`。Linux shell 里的 `wget` 才是从 HTTP 服务下载文件到文件系统路径。

## 网络打通

使用网线直连电脑和设备，给电脑有线网卡设置静态地址

最终可用配置如下：

```text
电脑端:
IP 地址: 192.168.1.100
子网掩码: 255.255.255.0
默认网关: 留空
DNS: 留空

设备端:
br0: 192.168.1.1
netmask: 255.255.255.0
```

设备端执行：

```sh
ifconfig br0 192.168.1.1 netmask 255.255.255.0 up
ping 192.168.1.100
```

电脑端能 ping 通 `192.168.1.1`，设备端也能 ping 通 `192.168.1.100` 后，说明链路已经通了。Windows 防火墙也要检查，尤其是当前网络被识别为“公用网络”时，HTTP 服务和后续 TCP 接收都可能被拦截。最后使用 `8080` 端口启动 HTTP 服务，设备端可以正常下载测试文件：

```sh
wget http://192.168.1.100:8080/test2.txt -O /tmp/test8080.txt
cat /tmp/test8080.txt
```

确认设备端能从电脑下载小文件，再传 BusyBox 和传固件。

## BusyBox 工具

下载地址：[https://busybox.net/downloads/binaries/](https://busybox.net/downloads/binaries/)

电脑端准备 `busybox-mips` 后，在文件所在目录启动 HTTP 服务：

```powershell
python -m http.server 8080 --bind 0.0.0.0
```

设备端下载：

```sh
wget http://192.168.1.100:8080/busybox-mips -O /tmp/busybox-mips
ls -l /tmp/busybox-mips
```

下载成功后文件大小约为：

```text
1565400 /tmp/busybox-mips
```

![2.png](https://www.iotsec-zone.com/api/image/v2/20260714/djxz5wp6ufb32rxsuv.png)

这里出现一个关键问题：系统没有 `chmod`，无法直接给 `/tmp/busybox-mips` 添加执行权限。下面几种尝试都会失败：

```sh
busybox chmod +x /tmp/busybox-mips
chmod +x /tmp/busybox-mips
/tmp/busybox-mips
```

典型报错如下：

```text
chmod: applet not found
/bin/sh: chmod: not found
Permission denied
```

![3.png](https://www.iotsec-zone.com/api/image/v2/20260714/djxz62cso2yq28fzxk.png)

解决思路是利用已有可执行文件的权限。先复制一个本来就有执行权限的文件，再用 `cat` 覆盖它的内容。文件权限会保留下来，内容则变成新的 BusyBox。第一次命名为 `/tmp/bb` 时失败，原因是 BusyBox 会根据 `argv[0]` 判断 applet 名称，叫 `bb` 时它会尝试寻找名为 `bb` 的 applet，于是报 `bb: applet not found`。正确做法是把文件命名为 `/tmp/busybox`：

```sh
cp /bin/ls /tmp/busybox
cat /tmp/busybox-mips > /tmp/busybox
ls -l /tmp/busybox
/tmp/busybox --list
```

![4.png](https://www.iotsec-zone.com/api/image/v2/20260714/djxz66indgye1dg0n0.png)

![5.png](https://www.iotsec-zone.com/api/image/v2/20260714/djxz69s13mkl4ith2t.png)

此时 `/tmp/busybox --list` 能正常列出大量 applet，说明新的 BusyBox 已经可以执行。继续确认关键工具：

```sh
/tmp/busybox --list | grep nc
/tmp/busybox --list | grep tftp
/tmp/busybox --list | grep ftpput
```

结果包含：

```text
nc
tftp
ftpput
```

![6.png](https://www.iotsec-zone.com/api/image/v2/20260714/djxz6dm2nz7r5tmncj.png)

到这一步，后续读取和回传固件所需的工具已经准备好了。

## 固件导出

使用新 BusyBox 的 `dd` 读取整片 Flash：

```sh
/tmp/busybox dd if=/dev/mtd0 of=/tmp/whole_flash.bin bs=64k
ls -l /tmp/whole_flash.bin
```

成功输出：

```text
128+0 records in
128+0 records out
8388608 bytes (8.0MB) copied, 6.719554 seconds, 1.2MB/s
```

生成文件大小为：

```text
8388608 /tmp/whole_flash.bin
```

![7.png](https://www.iotsec-zone.com/api/image/v2/20260714/djxz6j87tl76hrpvej.png)

这里的 `8388608` 字节正好等于 `8 MB`，与启动日志和 `/proc/mtd` 中的 `mtd0` 大小一致，说明 `/tmp/whole_flash.bin` 是整片 Flash 的完整镜像。

## 固件回传与校验

固件已经在板子的 `/tmp` 里生成，下一步是回传到电脑。Windows PowerShell 默认没有 `nc`，直接执行：

```powershell
nc -l -p 4444 > zxa10_whole_flash.bin
```

会提示无法识别 `nc`。因此电脑端改用 Python TCP 接收脚本 `recv_flash.py`，监听 `4444` 端口，把收到的数据保存为 `zxa10_whole_flash.bin`，并按进度打印接收字节数。

```
import socket
from pathlib import Path

HOST = "0.0.0.0"
PORT = 4444
OUT = Path("zxa10_whole_flash.bin")
EXPECTED = 8 * 1024 * 1024

def main() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen(1)
        print(f"listening on {HOST}:{PORT}")
        conn, addr = server.accept()
        print(f"connected from {addr[0]}:{addr[1]}")
        total = 0
        with conn, OUT.open("wb") as f:
            while True:
                chunk = conn.recv(65536)
                if not chunk:
                    break
                f.write(chunk)
                total += len(chunk)
                if total % (512 * 1024) < len(chunk):
                    print(f"received {total}/{EXPECTED}")
        print(f"saved {total} bytes to {OUT}")
        if total != EXPECTED:
            print(f"warning: expected {EXPECTED} bytes")

if __name__ == "__main__":
    main()
```

电脑端运行：

```powershell
python .\recv_flash.py
```

设备端发送：

```sh
/tmp/busybox nc 192.168.1.100 4444 < /tmp/whole_flash.bin
```

电脑端最终显示：

```text
listening on 0.0.0.0:4444
connected from 192.168.1.1:44488
received 8388608/8388608
saved 8388608 bytes to zxa10_whole_flash.bin
```

![8.png](https://www.iotsec-zone.com/api/image/v2/20260714/djxz6qeejza4fjjhia.png)

大小应为：

```text
8388608 bytes
```

还可以用头部数据做一次简单校验。传回电脑的文件头部应当和 U-Boot 阶段 `md.b b0000000` 看到的 Flash 起始内容一致：

```text
10 00 00 ff 00 00 00 00 10 00 00 fd ...
```

这个校验能证明文件确实从 Flash 起始位置开始，而不是某个偏移错误的片段。

## binwalk 初步分析

拿到固件后，在 Ubuntu 中用 binwalk 初步识别：

```bash
binwalk -Me zxa10_whole_flash.bin
```

![9.png](https://www.iotsec-zone.com/api/image/v2/20260714/djxz6tu9gy1qqet64m.png)

关键偏移如下：

```text
0x01A880  U-Boot version string
0x020100  uImage header, kernel_ramfs0
0x020140  LZMA compressed data
0x3D0100  uImage header, kernel_ramfs1
0x3D0140  LZMA compressed data
0x780000  userconfig / JFFS2 区域附近
0x790000  JFFS2 filesystem, big endian
```

结合 `/proc/mtd`，整片 Flash 可以整理为：

```text
0x000000 - 0x020000  bootloader
0x020000 - 0x3D0000  kernel_ramfs0
0x3D0000 - 0x780000  kernel_ramfs1
0x780000 - 0x7E0000  userconfig
0x7E0000 - 0x7F0000  parameter tags
0x7F0000 - 0x800000  env
```

这说明该设备存在双镜像结构，即 `kernel_ramfs0` 和 `kernel_ramfs1` 两套系统区域。很多光猫和路由器会使用这种布局做升级回滚：升级时写入备用分区，启动成功后切换环境变量；如果启动失败，则回退到另一套镜像。

后续分析可以先用 `strings` 搜索账号、路径、服务名和版本信息，再用 `binwalk -e` 或手工 LZMA 解压分析内核和 rootfs。对 JFFS2 区域可以尝试 `jefferson`、`binwalk` 或 Linux MTD 工具。如果要逆向二进制程序，需要根据 CPU 信息选择 MIPS big-endian 配置，再放入 IDA Pro、Ghidra 分析。

## 结论

该 ZXA10 F411 V2.0 可以通过 UART 进入 Linux shell，利用临时网络下载 MIPS 版 BusyBox，通过权限继承绕过缺少 `chmod` 的限制，再用 `dd` 读取 `/dev/mtd0`，最后通过 `nc` 把完整 `8 MB` Flash 镜像回传到电脑。最终得到的 `zxa10_whole_flash.bin` 大小正确，头部与 U-Boot 中 `md.b` 看到的 Flash 起始内容一致，binwalk 也能识别出 U-Boot、双 uImage、LZMA 压缩数据和 JFFS2 区域，说明固件提取成功。
