# 从零开始的NetGear RAX50 模拟环境搭建
> AiMiLiYa
> 来源：https://www.iotsec-zone.com/article/498

## 背景
在尝试模拟NetGear RAX50(RAX50-V1.0.9.108_2.0.74)时，使用FirmAE，Firmadyne,都起不来固件时。
最后尝试qemu-system模拟，OK发现问题所在，amhf使用的kernel太老，无法启动。哎~这真是一个悲伤的故事。

![0.png](https://www.iotsec-zone.com/api/image/v2/20250524/da4a9bn9dwos7sppgj.png)

**后续内容简介：低版本linux kernel编译，busybox制作根文件系统，从固件中提取nvram.ini(写的ida插件)，qemu-system系统模拟。有需要的读者可以根据内容自行查看。**

## 编译 linux kernel 4.1.1 
由于我的qemu系统模拟提供的镜像其内核太老，无法模拟。
可以看到我们的目标环境是ARM，内核版本为Linux 4.1.0
```bash
file ./squashfs-root/usr/sbin/httpd 
./squashfs-root/usr/sbin/httpd: ELF 32-bit LSB pie executable, ARM, EABI5 version 1 (SYSV), dynamically linked, interpreter /lib/ld-linux.so.3, for GNU/Linux 4.1.0, stripped
```
去下载一个版本最接近的kernel [https://www.kernel.org/](https://www.kernel.org/)
这里我下载的是4.1.1的内核,解压并进入内核源码目录
```bash
tar -zxvf linux-4.1.1.tar.gz
cd linux-4.1.1/
```
另外，还需要一个低版本的gcc交叉编译工具，从这里可以下载低版本gcc编译工具链：[https://toolchains.bootlin.com/](https://toolchains.bootlin.com/)
我下载的版本为：
![1.png](https://www.iotsec-zone.com/api/image/v2/20250524/da4ag8ebypbxxmsk1c.png)
将下载的交叉编译工具解压到某个目录下即可使用其编译我们的kernel了
```bash
#清除原先make产生得文件
make mrproper
#查看内核配置文件里面支持哪些开发板
#vexpress_defconfig vexpress 是一种常见的ARM开发板，通常用于QEMU模拟。这个配置文件应适用于QEMU的ARMv7架构
#realview_defconfig realview 也是一种常见的ARM开发板，适合模拟ARMv7架构的设备。如果您使用的是较早的QEMU ARM板，realview配置也可能适用。
ls arch/arm/configs

export ARCH=arm
export CROSS_COMPILE=/home/iotsec-zone/Desktop/kernel/armv7-eabihf--glibc--stable/bin/arm-buildroot-linux-gnueabihf-
export PATH=$PATH:/home/iotsec-zone/Desktop/kernel/armv7-eabihf--glibc--stable/bin

#我的环境在执行make vexpress_defconfig时缺乏依赖 
#sudo apt-get install bison 
#sudo apt-get install flex
make vexpress_defconfig
make menuconfig 
# System Type -> Enable the L2x0 outer cache controller 取消，会导致仿真失败起不来
#然后需要勾选的 当时大概好像是下面这样勾选的
#System Type-> Enable the L2x0 outer cache controller ，或
#Device Drivers -> Network device support -> Dummy net driver support
#Networking support -> Wireless -> cfg80211 - wireless configuration API 
#Networking support -> Networking options 中 勾选 802.1d Ethernet Bridging, The IPv6 protocol, IP: advanced router, IP: multicasting, IP: multicast routing
make -j 8

```
编译过程中会发生报错，如下图
![2.png](https://www.iotsec-zone.com/api/image/v2/20250524/da4alxp36vv6smzhhp.png)
这个错误表明在链接过程中，符号 yylloc 的重复定义。
解决方案：修改源码，如我修改了scripts/dtc/dtc-parser.tab.c中的yylloc为yylloc_即可解决报错。

![3.png](https://www.iotsec-zone.com/api/image/v2/20250524/da4anq5965fu3xmpie.png)

然后重新编译内核。

![4.png](https://www.iotsec-zone.com/api/image/v2/20250524/da4ao1hxhdeusvmaos.png)
此时可以使用qemu模拟进行测试了
```bash
#此命令在linux源码中测试执行，其中所需的内核镜像和设备树文件都在对应的目录下，后续会用到
qemu-system-arm -M vexpress-a9 -m 512M -kernel ./arch/arm/boot/zImage -dtb ./arch/arm/boot/dts/vexpress-v2p-ca9.dtb -nographic -append "console=ttyAMA0"
```
但是由于我们只编译了linux内核，所以qemu会在文件系统那里停住，这是因为没有添加文件系统无法加载根目录。

## 使用busybox创建根文件系统
下面来利用busybox制作根文件系统。
安装busybox
```bash
git clone git://busybox.net/busybox.git && cd busybox
export ARCH=arm
export CROSS_COMPILE=arm-linux-gnueabihf-

make defconfig
make menuconfig
#   勾选 Setting-> Build Options-> [*] Build static binary (no shared libs)
# 因为模拟环境下无法使用动态库方式
#确认勾选Networking Utilities -> brctl (bridge control)

make -j 8
make install
#busybox 默认安装到,._install/bin/目录下
```

进入busybox源码目录下，找到examples/bootfloppy/etc/inittab文件，替换
```bash
# etc/inittab
::sysinit:/etc/init.d/rcS
::askfirst:-/bin/sh
::ctrlaltdel:/sbin/reboot
::shutdown:/sbin/swapoff -a
::shutdown:/bin/umount -a -r
::restart:/sbin/init
```
examples/bootfloppy/etc/init.d/rcS 文件，替换为下面内容。并且给文件 777 的权限
```bash
#!/bin/sh
/bin/mount -a
/bin/mkdir -p /dev/pts
/bin/mount -t devpts devpts /dev/pts
/bin/echo /sbin/mdev > /proc/sys/kernel/hotplug
/sbin/mdev -s
```
替换 examples/bootfloppy/etc/fstab 文件内容
```bash
# <file system>    <mount point>    <type>    <options>    <dump>    <pass>     
proc                  /proc          proc     defaults       0         0
sysfs                 /sys           sysfs    defaults       0         0
tmpfs                 /tmp           tmpfs    defaults       0         0
tmpfs                 /dev           tmpfs    defaults       0         0
```
替换 examples/bootfloppy/etc/profile 文件，写入下面内容。
```bash
export HOSTNAME=zy
export USER=root
export HOME=/root
export PS1="[$USER@$HOSTNAME:\$PWD]\# "    
export PATH=/bin:/sbin:/usr/bin:/usr/sbin
export LD_LIBRARY_PATH=/lib:/usr/lib:$LD_LIBRARY_PATH
```
最后执行制作文件系统的脚本，会生成一个名为"a9rootfs.ext3"的文件
```bash
# 本脚本用于生成文件系统，需要在busybox目录下执行
#!/bin/sh
base=`pwd`
tmpfs=/_tmpfs

sudo rm -rf rootfs
sudo rm -rf ${tmpfs}
sudo rm -f a9rootfs.ext3
sudo mkdir rootfs
sudo cp _install/*  rootfs/ -raf

#sudo mkdir -p rootfs/{lib,proc,sys,tmp,root,var,mnt}
cd rootfs && sudo mkdir -p lib proc sys tmp root var mnt && cd ${base}

# 根据自己的实际路径, 拷贝 arm-gcc 中的 libc中的所有.so 库
sudo cp -arf /usr/arm-linux-gnueabihf/lib/*so*  rootfs/lib

sudo cp examples/bootfloppy/etc rootfs/ -arf
sudo sed -r  "/askfirst/ s/.*/::respawn:-\/bin\/sh/" rootfs/etc/inittab -i
sudo mkdir -p rootfs/dev/
sudo mknod rootfs/dev/tty1 c 4 1
sudo mknod rootfs/dev/tty2 c 4 2
sudo mknod rootfs/dev/tty3 c 4 3
sudo mknod rootfs/dev/tty4 c 4 4
sudo mknod rootfs/dev/console c 5 1
sudo mknod rootfs/dev/null c 1 3
sudo dd if=/dev/zero of=a9rootfs.ext3 bs=1M count=64
# 如果提示 "No space left on device" 证明 dd 命令中 count 的大小不够

sudo mkfs.ext3 a9rootfs.ext3
sudo mkdir -p ${tmpfs}
sudo chmod 777 ${tmpfs}
sudo mount -t ext3 a9rootfs.ext3 ${tmpfs}/ -o loop
sudo cp -r rootfs/*  ${tmpfs}/
sudo umount ${tmpfs}
```

## 使用编译的内核和制作的根文件系统qemu-system模拟
将制作的根文件系统，编译的linux kernel和设备树文件拷贝到同一目录下，然后qemu模拟
```bash
sudo qemu-system-arm -M vexpress-a9 -cpu cortex-a9 -m 1024M -dtb ./vexpress-v2p-ca9.dtb -kernel ./zImage -nographic -append "root=/dev/mmcblk0 rw console=ttyAMA0" -drive file=./a9rootfs.ext3,format=raw,if=sd -netdev tap,id=net0,ifname=tap0,script=no,downscript=no -device virtio-net-device,netdev=net0

#配置网卡
ip addr add 192.168.1.1/24 dev eth0
ip link set eth0 up
ip addr add 127.0.0.1/24 dev lo
ip link set lo up

```
宿主机中配置网卡，并将解包的固件文件系统进行打包，并启动python用于传输文件
```bash
sudo ifconfig tap0 192.168.1.101/24 up
tar -zcvf squashfs-root.gz squashfs-root
python3 -m http.server 8080
```
模拟机中，下载固件的文件系统并解包，然后进入shell环境
```bash
cd tmp
wget http://192.168.1.101:8080/squashfs-root.gz
tar -zxvf squashfs-root.gz
mount -t proc /proc/ ./squashfs-root/proc/
mount -o bind /dev/ ./squashfs-root/dev/
mount --bind /sys/ ./squashfs-root/sys/
chroot squashfs-root sh
```
OK，解决内核太旧的问题。

![5.png](https://www.iotsec-zone.com/api/image/v2/20250524/da4aybzcg25q5udoxm.png)
## 获取nvram.ini 
NetGear里面有非常多的数据都是来自nvram（非易失性随机访问存储器），一般来说nvram是在运行后才有。
在网上说libnvarm.so中会有一些默认的配置在里面，但是网上并没有给出方便提取的插件（也可能是我没找到）
为了方便起见，我自己写了一个获取nvram.ini的ida插件（注意：本人ida使用的是7.7，因此版本太高或者太低都可能不支持） 
插件链接[GetNvramIni.py](https://github.com/emt-emt/Iot/blob/main/Tools/GetNvramIni.py)
放在IDA的Plugins目录下即可使用，快捷键为Ctrl+Alt+N
其会将提取到的配置自动保存至与打开的efl文件同目录下
此固件中的一些默认配置在/usr/lib/libacos_nvram.so中。
![6.png](https://www.iotsec-zone.com/api/image/v2/20250524/da4b47pmeazmbwq5yu.png)
局限性：有些配置是动态生成的，但此插件只能获取一些存在lib中的默认值，需要自己找到数据所在。

## 开始模拟
可以从该github中下载nvram.so进行hook：[custom_nvram](https://github.com/therealsaumil/custom_nvram)
将获取的nvarm.so和生成的nvarm.ini都拷贝近ubuntu虚拟机待用。
```bash
mkdir /var/tmp
mkdir -p /var/run
wget http://192.168.1.101:8080/nvram.so
wget http://192.168.1.101:8080/nvram.ini
chmod 755 nvram.so
mv nvram.ini tmp/

#方便调试启动 utelnetd
/usr/sbin/utelnetd -l /bin/sh &

#启动httpd
LD_PRELOAD="./nvram.so" /usr/sbin/httpd -S -E /usr/sbin/ca.pem /usr/sbin/httpsd.pem &
```
浏览器访问一下，可以看到，httpd已经被正常执行起来了，但是由于NetGear的尿性，要给它联网才能正常访问它的管理界面，我的模拟环境并没有给它配备网络。（给序列号是没有用滴，之前我有个实机的NetGear就是，必须要给网才行）

![7.png](https://www.iotsec-zone.com/api/image/v2/20250524/da4bbxd8hsx8pgixct.png)
还可以将它的upnpd服务也开启
```
LD_PRELOAD="./nvram.so" /usr/sbin/upnpd
```
该upnp的tcp绑定端口默认为56688

![8.png](https://www.iotsec-zone.com/api/image/v2/20250524/da4bcuvq4riwosxczg.png)

![9.png](https://www.iotsec-zone.com/api/image/v2/20250524/da4bcy9nwqqshmivle.png)

好啦，环境搭建到此结束啦。

### 参考文章
[dp7crb#google_vignette](https://geekdaxue.co/read/barret@xhw7bc/dp7crb#google_vignette)
[可恶，这次我一定要编译出Linux内核](https://zikh26.github.io/posts/ba98f82e.html)
[为 QEMU ARM 仿真器编译 Linux 内核：QEMU 模拟 ARM 环境](https://blog.csdn.net/song_lee/article/details/105815237)
[https://cool-y.github.io/2021/01/08/nvram-config/](https://cool-y.github.io/2021/01/08/nvram-config/)
