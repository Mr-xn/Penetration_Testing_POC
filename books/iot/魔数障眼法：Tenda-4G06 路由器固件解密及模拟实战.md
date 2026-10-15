# 魔数障眼法：Tenda-4G06 路由器固件解密及模拟实战
> Legion_
> 来源：https://www.iotsec-zone.com/article/556

# 魔数障眼法：Tenda-4G06 路由器固件解密及模拟实战
### 0X01:分析固件：

从官网获取路由器固件，可以看到更新时间在一个月前，到手的时候发现是.bin文件格式。

![0.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzxy6du2hnmygbrq.png)
按照常规流程，使用binwalk -E查看该固件的熵值：

![1.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzy7x5p7srosxrvs.png)
熵值接近 1.0， 通常意味着数据是**高度随机**的，有概率是被加密的固件。
尝试binwalk -Me直接提取:

![2.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzyemwix8bqa7u6w.png)

### 0x02：厂商定制的squashfs文件系统

面对这个疑似加密的固件,我们思来想去，决定回到这个.bin文件本身:
我们知道，固件在十六进制中的完整结构是这样的：
![3.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkr0p0rp0ogifgi8kd.png)
此时我们把固件放入010 editor中查看它的HEX信息：

![4.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkr0p5t1nuswywtfcl.png)

头部 4 字节 27 05 19 56 是标准 **U-Boot uImage** 魔数，
uImage 头有两个 CRC32 字段：**ih_hcrc**（头部校验）和 **ih_dcrc**（数据体校验）。

#### 使用脚本验证其CRC：

```bash
import struct, zlib
d = open("US_4G06V3.0re_V04.06.01.33_multi_TDE01.bin", "rb").read()
magic, hcrc, t, sz, load, ep, dcrc = struct.unpack(">7I", d[:28])

hdr = bytearray(d[:64]); hdr[4:8] = b"\0\0\0\0"     # hcrc 字段清零再算
print(hex(zlib.crc32(hdr) & 0xffffffff), hex(hcrc))  # 头 CRC → 相等
print(hex(zlib.crc32(d[64:64+sz]) & 0xffffffff), hex(dcrc))  # 体 CRC → 相等
print(64 + sz == len(d))                             # 若长度严丝合缝 → True
```

![5.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkr05mze15m98hwbdc.png)
通过逐字节复算 uImage 头部 CRC（**ih_hcrc**）与数据体 CRC（**ih_dcrc**），
确认两个校验值均与固件内存储值完全一致，且文件长度满足标准 uImage 结构（64 + sz = total）。
加密的数据不可能用标准 crc32 通过完整性校验。证明这个固件是标准的uimage结构，**没有加密。**

但是找遍整个文件，我们并没有发现**squashfs**和**XZ 压缩格式**的魔数，这点实在蹊跷，
通过查阅资料结合不断分析这个文件，我们确认该系列固件使用了定制修改的文件系统结构和压缩方法。
不光squashfs的魔数被修改为**y9nice**，同时**XZ压缩格式**的魔数同样被替换成厂商定义的标识。
XZ 流的尾部魔数仍是标准值 **59 5A**（"YZ"），"YZTenda" 特征串就是「上一条流的尾 "YZ" + 下一条流的头 "Tenda"」相邻拼接出来的。
![6.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkr0glmsra0oa2u139.png)

![7.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkr0grb7nkzovwrdg6.png)

![8.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkr0gxb7gix5q8f1ov.png)

### 0x03：顺腾摸瓜：恢复原始文件，魔改XZ工具
已知 Squashfs 魔数被篡改为  **y9nice**（原应为 **hsqs**），
XZ 流也被一并修改。修复的第一步很直接：把魔数改回去。
编写一个Python脚本用于修改魔数：

```python
#!/usr/bin/env python3
import sys

# 固件文件名
BIN_FILE = "US_4G06V3.0re_V04.06.01.33_multi_TDE01.bin"
SQUASHFS_FILE = "V4.bin"

# 魔数位置和值（根据你前面的分析结果）
MAGIC_OFFSET = 0x25AC50
OLD_MAGIC = b"y9nice"    # 6字节旧魔数
NEW_MAGIC = b"hsqs"      # 4字节新魔数

# 读取固件
d = open(BIN_FILE, "rb").read()

# 验证旧魔数是否存在
actual_magic = d[MAGIC_OFFSET:MAGIC_OFFSET + len(OLD_MAGIC)]
if actual_magic != OLD_MAGIC:
    print(f"警告: 预期魔数 {OLD_MAGIC}，实际是 {actual_magic}")
    sys.exit(1)

print(f"魔数验证通过: {OLD_MAGIC}")

# 数据体起始位置 = 魔数起始位置 + 魔数长度
data_start = MAGIC_OFFSET + len(OLD_MAGIC)

# 拼装新Squashfs: 新魔数(4字节) + 数据体
squashfs_data = NEW_MAGIC + d[data_start:]

# 写入文件
with open(SQUASHFS_FILE, "wb") as f:
    f.write(squashfs_data)

print(f"已生成: {SQUASHFS_FILE}，大小 {len(squashfs_data)} 字节")
```

![9.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkr0iefu3ie3orflum.png)
完成后得到名为**V4.bin**的文件，在010Editor中也能直观看到：
![10.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkr0iiuhu7n2njus8a.png)

![11.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkr0ilbl9mo0ww6iqc.png)
将修改后的文件保存，使用**unsquashfs -s V4.bin**查看文件系统的超级块信息（**superblock**）
![12.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkr0j2eltu92ux66uf.png)
**superblock全部字段合法**，魔数一对上，后面的字段全对了， 这是一个结构完全正确、能够被标准工具识别的 Squashfs 文件系统镜像。
这就是最有力的证据：文件结构未作任何改动，**仅有头部标识字段被替换。**

尝试使用**unsquashfs -d out ./V4.bin**分离：
![13.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkr0kmd5y361pjgmbv.png)
遇到了XZ 解压失败，LZMA/XZ 错误码 7 通常表示**数据格式无效或数据损坏**。这是因为厂商的魔改 XZ 数据与标准的 XZ 解压器不兼容。

更换工具，使用**binwalk**分离：
![14.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkr0l5iriir1kwsofp.png)
虽然分离失败了，但是也成功识别了squashfs 文件块。

**紧接着，我们需要解决 Squashfs 内部 XZ 流被魔改的问题。**
Binwalk、unsquashfs 等主流工具均无法直接处理这份固件，原因在于其 XZ 压缩段使用了非标准的魔数，并将 CRC 校验逻辑反转——任何遵循标准规范的解压工具都会在完整性检查阶段直接报错退出。为此，我们决定对 XZ 工具本身进行定制化魔改。

#### 魔改点定位：
动手前先明确要改什么。固件的 XZ 流有一处格式层改动 + 一处校验层改动：
![15.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkr0n509nfhffpfusg.png)

已知我们需要修改的地方，那就下载XZ源码，开始动手魔改：

```bash
#!/bin/bash

set -e
cd /tmp
rm -rf xz-5.6.2
if [ ! -s xz-5.6.2.tar.gz ]; then
  curl -sL --retry 3 --retry-delay 5 --max-time 180 -o xz-5.6.2.tar.gz https://tukaani.org/xz/xz-5.6.2.tar.gz \
    || curl -sL --retry 3 --max-time 180 -o xz-5.6.2.tar.gz https://github.com/tukaani-project/xz/releases/download/v5.6.2/xz-5.6.2.tar.gz
fi
tar xf xz-5.6.2.tar.gz
cd xz-5.6.2

python3 - <<'PYEOF'
import re

def patch(path, subs):
    s = open(path, encoding='utf-8').read()
    for old, new in subs:
        if old not in s:
            print("!! NOT FOUND in %s: %.60r" % (path, old))
        else:
            s = s.replace(old, new)
    open(path, 'w', encoding='utf-8').write(s)
    print("patched:", path)

def kill_crc_error(path):
    """把 crc/memcmp 校验附近的 return LZMA_DATA_ERROR 全部替换成空语句"""
    lines = open(path, encoding='utf-8').read().split('\n')
    n = 0
    for i, l in enumerate(lines):
        if 'return LZMA_DATA_ERROR;' in l:
            window = '\n'.join(lines[max(0, i-4):i])
            if any(k in window for k in ('crc', 'memcmp', 'raw_check')):
                lines[i] = l.replace('return LZMA_DATA_ERROR;', ';')
                n += 1
    open(path, 'w', encoding='utf-8').write('\n'.join(lines))
    print("killed %d crc-error returns in %s" % (n, path))

# 1) 头魔数 -> "Tenda\0"
patch("src/liblzma/common/stream_flags_common.c", [
    ('{ 0xFD, 0x37, 0x7A, 0x58, 0x5A, 0x00 }',
     '{ 0x54, 0x65, 0x6E, 0x64, 0x61, 0x00 } /* Tenda\0 */'),
])
# 2) 流头/流尾 flags CRC: 反转比较
patch("src/liblzma/common/stream_flags_decoder.c", [
    ('crc != read32le', 'crc == read32le'),
])
# 3) 块头 CRC: 反转比较
patch("src/liblzma/common/block_header_decoder.c", [
    ('lzma_crc32(in, in_size, 0) != read32le(in + in_size)',
     'lzma_crc32(in, in_size, 0) == read32le(in + in_size)'),
])
# 4) 块数据 Check(memcmp): 反转
s = open("src/liblzma/common/block_decoder.c", encoding='utf-8').read()
s2 = re.sub(r'memcmpcoder−>block−>rawcheck,\s∗coder−>check\.buffer\.u8,\s∗checksize\s*!=\s*0',
            'memcmp(coder->block->raw_check, coder->check.buffer.u8, check_size) == 0', s)
print("block_decoder memcmp patched:", s2 != s)
open("src/liblzma/common/block_decoder.c", 'w', encoding='utf-8').write(s2)
# 5) 索引: 删掉错误返回
for f in ("src/liblzma/common/index_hash.c",
          "src/liblzma/common/index_decoder.c",
          "src/liblzma/common/stream_flags_decoder.c",
          "src/liblzma/common/block_header_decoder.c",
          "src/liblzma/common/block_decoder.c"):
    kill_crc_error(f)
PYEOF

./configure --prefix=/opt/tenda-lzma \
  --disable-xz --disable-xzdec --disable-lzmadec --disable-lzmainfo \
  --disable-scripts --disable-doc --disable-debug
make -j$(nproc)
sudo make install
echo "done: /opt/tenda-lzma/lib/"
```
执行这个脚本，即可得到魔改版XZ工具：

```bash
sudo bash patch_xz_tenda.sh
# 只编译 liblzma、不安装 xz CLI 工具（--disable-xz --disable-xzdec ...），避免污染系统自带的 xz。
# 预期输出：
# patched: src/liblzma/common/stream_flags_common.c
# ...
# done: /opt/tenda-lzma/lib/
```

### 0x04：成功得到文件系统

此时我们拿到魔改的XZ工具若直接在宿主机上运行，有可能会污染系统环境，出现莫名其妙的问题，
所以我们当下有两条路线：

一是在本地系统下，将unsquashfs的动态链接 **liblzma.so.5**，用环境变量临时覆盖即可，无需重编 squashfs-tools。

二是Docker 隔离构建，在Docker中完成固件的提取。
权衡利弊后，我选择了路线一，原因是Doceker隔离构建的工作量相对来说更多，这里我们选择更快捷的路线一。
在宿主机上执行：

```bash
LD_LIBRARY_PATH=/opt/tenda-lzma/lib \
  unsquashfs -d newroot V4.bin
```

![16.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkr0rj6zuvo4farutk.png)

最终成功得到文件系统**newroot**

 **对整个文件系统提取的小结：**
回头再看这个包，它从头到尾都没有加密——但它的确成功地骗过了我们一轮：
魔数换成 "y9nice"，XZ 头换成 "Tenda\0"，CRC 填上占位常量，三处小改动叠在一起，就足以让整套提取工具链集体失明，也足以让人把"解不开"误解成"加密"。
解包的过程像剥洋葱：外层 uImage 一验即过，内核 LZMA 一解即出，改回 6 个字节的魔数，superblock 立刻自洽；换上魔改版的工具，文件系统应声落地。
也许这正是厂商想要的效果：挡住大多数想随便翻翻的人，但是挡不住真正较劲的人。而我们恰好属于后者。

### 0x05：固件模拟
#### 一、固件&启动项分析

使用**file**和**firmwalker**对该固件进行分析:
![17.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkr0sqpjs3017jtj1k.png)

![18.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkr0sudec3ccev8jqc.png)
可知该固件的架构为MIPS32位，web服务依靠httpd实现。

然后我们对他的启动项(**etc_ro/inittab**)进行分析:

```bash
::sysinit:/etc_ro/init.d/rcS
# 作用：系统启动后立即运行主初始化脚本,
# 该脚本通常负责：挂载文件系统、加载内核模块、配置网络、启动服务

ttyS0::respawn:/sbin/sulogin
# 作用：在串口 ttyS0 上启动单用户登录程序
# respawn：进程退出后自动重启（保证始终可登录）

::ctrlaltdel:/bin/umount -a -r
# 作用：按下 Ctrl+Alt+Del 时执行
# 最终效果：安全卸载文件系统后重启系统

::shutdown:/usr/sbin/wl leds 0
# 作用：系统关机/重启时，关闭 Broadcom 无线芯片（主接口）的 LED 灯

::shutdown:/usr/sbin/wl -i eth2 leds 0
# 作用：系统关机/重启时，关闭 Broadcom 无线芯片（eth2 接口）的 LED 灯

::shutdown:/usr/sbin/usb led_off
# 作用：系统关机/重启时，关闭 USB 接口的 LED 指示灯

:6:respawn:/bin/monitor
# 作用：启动 monitor 监控守护进程(看门狗)
# respawn：进程崩溃或被杀死后自动重启，该程序通常由厂商自研，用于监控系统关键服务是否存活
```
分析rcS主初始化脚本(**部分重点**)：

```bash
#! /bin/sh

PATH=/sbin:/bin:/usr/sbin:/usr/bin/
export PATH

mount -t ramfs none /var/
#挂载内存文件系统（ramfs）到 /var，用于存放运行时数据

mkdir -p /var/etc
mkdir -p /var/media
mkdir -p /var/webroot
mkdir -p /var/etc/iproute
mkdir -p /var/run
mkdir -p /etc/udhcpc
mkdir -p /var/debug
#创建 /var 下的运行时目录

cp -rf /etc_ro/* /etc/
cp -rf /webroot_ro/* /webroot/
#复制只读分区内容到可写目录

umount -f /tmp
mount -t tmpfs none /tmp -o size=3M
#重新挂载 /tmp 为 tmpfs，限制大小为 3MB

......
#挂载其他文件系统

echo "enable 0 interval 0" >/proc/watchdog_cmd
# 禁用硬件看门狗（enable 0）防止系统在调试/分析期间自动重启

chmod +x /etc/mdev.conf
#配置 mdev.conf 可执行权限

......

```

#### 二、Web 服务架构（进程依赖图）

通过将/bin/文件夹下的**cfmd**、**httpd** 、**ubusd**等文件放入IDA中进行分析，可以得到整个web服务的架构图：

```bash
                        ┌─────────────┐
                        │   monitor   │  (inittab 拉起，看门狗/进程守护)
                        └──────┬──────┘
                               │ spawn
          ┌────────────────────┼─────────────────────────┐
          ▼                    ▼                         ▼
   ┌────────────┐      ┌──────────────┐         ┌────────────────┐
   │   cfmd     │      │   httpd      │         │   business_proc │
   │ 配置后端    │◄─────│ (GoAhead Web) │◄──ubus─┤   业务逻辑后端   │
   │ unix socket│ cfm  │              │         │  (TCP :10004)  │
   └─────┬──────┘      └──────┬───────┘         └───────┬────────┘
         │ cfm 消息            │ ubus                   │
         ▼                    ▼                        ▼
   ┌────────────┐      ┌──────────────┐         ┌────────────────┐
   │   ubusd    │◄─────│   netctrl    │         │    multiWAN    │
   │ 消息总线    │      │ WAN/DDNS 管理 │         │   多WAN 管理    │
   └────────────┘      └──────────────┘         └────────────────┘
```

启动顺序：
**ubusd → cfmd → business_proc → httpd → monitor → (netctrl/multiWAN 由事件拉起)**

*关键依赖：*
- httpd 启动时需要：/var/run/ubus.sock（ubusd）+ /var/cfm_socket（cfmd）——缺一不可，否则启动即退出。
- cfmd 初始化需要读取/擦写 MTD 闪存分区。

#### 三、环境准备
模拟方案选择使用QEMU系统模拟+chroot的方式，让固件的 rootfs 在 guest 内 chroot 运行，用 guest 内核的真实 MTD 子系统
1.编写QEMU启动脚本：**boot.sh**

```bash
#!/bin/sh

# ---  启动 QEMU ---
echo "[boot] starting qemu-system-mipsel..."
qemu-system-mipsel \
  -M malta -m 256 \
  -kernel vmlinux-3.2.0-4-4kc-malta \
  -hda debian_wheezy_mipsel_standard.qcow2 \
  -append 'root=/dev/sda1 console=ttyS0' \
  -nographic -no-reboot \
  -netdev user,id=net0,hostfwd=tcp::2222-:22,hostfwd=tcp::8080-:80 \
  -device pcnet,netdev=net0 \
  -netdev user,id=net1,net=10.0.3.0/24,hostfwd=tcp::2223-:22,hostfwd=tcp::8081-:80 \
  -device pcnet,netdev=net1 \
  -netdev user,id=net2,net=10.0.4.0/24,hostfwd=tcp::2224-:22,hostfwd=tcp::8082-:80 \
  -device pcnet,netdev=net2 \
  < qemu_in_fifo

echo "[boot] qemu exited (rc=$?)"
rm -f qemu_in_fifo
```

启动脚本：**sudo ./boot.sh**

![19.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkr0x7hey10dhnmbfg.png)
等待QEMU启动后，宿主机使用ssh连接QEMU虚拟机：
ssh -p 2224 root@127.0.0.1     # 密码root

2.部署固件：
编写初始化引导脚本**guest_install.sh**

```bash
#!/bin/sh

R=/firm/squashfs-root
MD=/lib/modules/3.2.0-4-4kc-malta/kernel
log() { echo "[boot] $*"; }

chroot $R /bin/busybox killall monitor cfmd httpd business_proc ubusd netctrl logdebug cpe_interface_check 2>/dev/null
pkill -f "while true; do chroot" 2>/dev/null
sleep 2

rmmod block2mtd phram mtdram physmap 2>/dev/null; sleep 1
insmod $MD/drivers/block/loop.ko 2>/dev/null
mknod /dev/loop0 b 7 0 2>/dev/null
losetup -d /dev/loop0 2>/dev/null
dd if=/dev/zero of=/root/mtd_backing bs=1M count=2 2>/dev/null
losetup /dev/loop0 /root/mtd_backing 2>/dev/null
for m in mtd mtdchar mtd_blkdevs; do insmod $MD/drivers/mtd/$m.ko 2>/dev/null; done
for m in map_funcs gen_probe chipreg cfi_probe cfi_util cfi_cmdset_0001; do insmod $MD/drivers/mtd/chips/$m.ko 2>/dev/null; done
insmod $MD/drivers/mtd/maps/physmap.ko 2>/dev/null
insmod $MD/drivers/mtd/devices/mtdram.ko total_size=8192 erase_size=128 2>/dev/null
insmod $MD/drivers/mtd/devices/phram.ko phram=CFG,0x1800000,0xa0000 2>/dev/null
insmod $MD/drivers/mtd/devices/block2mtd.ko block2mtd=/dev/loop0,65536 2>/dev/null
insmod $MD/drivers/mtd/mtdblock.ko 2>/dev/null
for m in llc stp ipv6 bridge; do insmod $MD/net/*/$m.ko 2>/dev/null; done

CFG_REAL=$(grep '"CFG"' /proc/mtd | awk -F: '{print $1}' | tr -d ' ')
CFM_REAL=$(grep block2mtd /proc/mtd | awk -F: '{print $1}' | tr -d ' ')
[ -n "$CFG_REAL" ] && [ -n "$CFM_REAL" ] || { log "FATAL: MTD 未就绪"; cat /proc/mtd; exit 1; }

# ----  chroot 地基 ----
mount -t proc proc $R/proc 2>/dev/null
mount --bind /dev $R/dev 2>/dev/null
mount --bind /dev/pts $R/dev/pts 2>/dev/null
mount --bind /sys $R/sys 2>/dev/null

# ----  br0 网桥 ----
ip link add br0 type bridge 2>/dev/null
ip link set eth0 master br0 2>/dev/null
ip link set eth0 up 2>/dev/null
ip link set br0 up 2>/dev/null
ip addr add 192.168.0.1/24 dev br0 2>/dev/null

# ---- sysinit：rcS ----
chroot $R /bin/sh /etc_ro/init.d/rcS

if [ "$CFG_REAL" != "mtd4" ] || [ "$CFM_REAL" != "mtd5" ]; then
  cfgn=${CFG_REAL#mtd}; cfmn=${CFM_REAL#mtd}
  mknod $R/dev/mtd4 c 90 $((cfgn*2));   mknod $R/dev/mtd4ro c 90 $((cfgn*2+1))
  mknod $R/dev/mtd5 c 90 $((cfmn*2));   mknod $R/dev/mtd5ro c 90 $((cfmn*2+1))
  mknod $R/dev/mtd6 c 90 $((cfmn*2));   mknod $R/dev/mtd6ro c 90 $((cfmn*2+1))
  mknod $R/dev/mtdblock4 b 31 $cfgn
  mknod $R/dev/mtdblock5 b 31 $cfmn
  mknod $R/dev/mtdblock6 b 31 $cfmn
fi
ln -sf /dev/mtd4 $R/CFG; ln -sf /dev/mtd4 $R/dev/CFG

cat > /root/fake_mtd <<'EOF'
dev:    size   erasesize  name
mtd0: 00100000 00010000 "YAMON"
mtd1: 002e0000 00010000 "User FS"
mtd2: 00020000 00010000 "Board Config"
mtd3: 00800000 00020000 "mtdram test device"
mtd4: 000a0000 00001000 "CFG"
mtd5: 00200000 00010000 "CFM"
mtd6: 00200000 00010000 "CFM_BACKUP"
EOF
umount $R/proc/mtd 2>/dev/null
mount --bind /root/fake_mtd $R/proc/mtd

# monitor 自行拉起 cfmd + netctrl
setsid sh -c "while true; do chroot $R /bin/monitor; sleep 2; done" >/tmp/mon_loop.log 2>&1 </dev/null &

ip addr add 10.0.4.15/24 dev eth2 2>/dev/null
ip route add default via 10.0.4.2 dev eth2 2>/dev/null
killall python2 2>/dev/null; sleep 1
[ -f /root/guest_fwd.py ] && setsid nohup python2 /root/guest_fwd.py >/tmp/fwd.log 2>&1 </dev/null &
echo nameserver 10.0.4.3 > /etc/resolv.conf 2>/dev/null

# ----  等待服务就绪并汇报 ----
for i in $(seq 1 60); do
  chroot $R /bin/busybox ps 2>/dev/null | grep -q httpd && netstat -tln 2>/dev/null | grep -q ':80 ' && break
  sleep 1
done
log "=== 服务进程 ==="
chroot $R /bin/busybox ps 2>/dev/null | grep -E 'monitor|cfmd|httpd|ubusd|business|netctrl' | grep -v grep
log "=== 端口 80 ==="
netstat -tln 2>/dev/null | grep ':80 '
log "=== 完成 ==="
```

将启动脚本放入文件系统中，

```bash
#在宿主机上打包
tar --numeric-owner -czf /tmp/rootfs.tar.gz squashfs-root
sshpass -p root scp -P 2222 /tmp/rootfs.tar.gz root@127.0.0.1:/root/
#在QEMU中传入文件系统
mkdir /firm && tar xzf /root/rootfs.tar.gz -C /firm
#解压缩
```

在QEMU中执行**sh guest_install.sh**

![20.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkr0y8yn4g7vhkaqff.png)

成功启动web服务：

![21.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkr0ydfinqlxvl8aoc.png)

配置完路由后成功进入管理页面：

![22.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkr0yiwa2dnnukub8b.png)

至此，Tenda-4G06路由器固件解密及模拟实战在这里已经全部完成了。

***最后，在这里感谢父母、崔老师、同学以及IOTsec-Zone社区对本文章的大力支持！***
