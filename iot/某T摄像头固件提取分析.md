# 某T摄像头固件提取分析
> Pachimker
> 来源：https://www.iotsec-zone.com/article/475

# 背景

本小节以某T摄像头设备为例，学习U-Boot操作以及结合前面小节中学到的知识点，对其进行SD卡固件提取，并最终配置远程访问服务。

![0.png](https://www.iotsec-zone.com/api/image/v2/20240830/d3t05hokuvz3qdacdz.png)

下载某T设备管理app，添加摄像头后，发现摄像头固件版本为1.3.4。

![1.png](https://www.iotsec-zone.com/api/image/v2/20240830/d3t066fpjy0wxtdjqt.png)

关闭自动更新选型，这里tapo 设备硬件为v3型号，固件版本为1.3.4，这里我们需要对设备固件进行降级操作才可以进行SD卡提取固件操作。

![2.png](https://www.iotsec-zone.com/api/image/v2/20240830/d3t06b8j5lg6f2dbnw.png)

通过查阅网上公开的资料发现，某T摄像头v1和v2版本，都可以使用MicroSD卡进行固件降级操作。这里v1和v2版本固件文件系统中sdcard配置路径为/dev/mmcblk0p1，也就是说只有tapo设备在出发固件升级操作时检测到/dev/mmcblk0p1存在时，才会执行firmware upgrade操作(这里为固件降级)，对SD卡里面的factory_up_boot.bin文件进行解包升级。但是网上公开的v3版本的固件都为加密固件，如果不清楚其升级原理冒然操作，设备可能会变砖。好在网上查阅资料时，发现其他研究人员提取出的未加密v3固件。下载进行解包后，发现配置文件中sdcard路径相同，那么这里我们就可以按照之前的思路进行降级操作。

![3.png](https://www.iotsec-zone.com/api/image/v2/20240830/d3t06m9vbjz5xp4ody.png)

# 固件降级

我们可以根据文章（[https://github.com/DrmnSamoLiu/Downgrading-Tapo-Cams](https://github.com/DrmnSamoLiu/Downgrading-Tapo-Cams)）中的步骤进行降级操作，以下为本小节中的简略总结：

1. 将小于等于32GB MircoSD 卡插入PC机(这里我为windows)。

2. 按Win + R并运行diskpart

3. 执行以下命令：

```
list disk
select disk 2
clean
convert gpt
create partition primary
format quick fs=fat32
```

4. 下载固件Tapo_C200v3_en_1.1.13_Build_211224_Rel.39366n__1640785939431.bin(https://github.com/tapo-firmware/Tapo_C200)

5. 将要用于降级的固件重命名为factory_up_boot.bin并复制到MicroSD卡中的根目录。

6. 此时按下摄像头重置按钮 5 秒，等待摄像头电机校准

7. 拔掉摄像头电源插头，此时将SD卡插入摄像头

8. 然后等待摄像头指示灯颜色稳定停在绿色，拔掉电源插头，取出SD卡

9. 摄像头插上电源，等待电机校准，完成固件降级。

# 提取固件

提取固件的大致流程为：

1. 按照前面小节中uart引脚的接法，将 UART 引脚连接到ttl转usb

2. 使用终端管理软件连接 UART 串口数据，波特率为115200

3. 给设备上电，此时启动日志显示文本“stop the autobooting in 3s”时，按slp键停止设备启动

4. 停止引导过程后，将可以访问U-Boot shell

5. 一旦 U-Boot shell 可以访问，我们可以使用setenv命令将init环境变量的路径更改为init=/bin/sh

6. 现在在 shell 中将bootcmd的内容作为命令运行

7. 运行 bootcmd 后，设备将正常启动并提供 root shell

8. 使用命令cat /proc/mtd查找flash芯片的 mtd 块分区

9. 将flash数据拷贝到MicroSD卡中。

具体操作流程如下：

tapo摄像头的外壳为卡扣结构，拆解较为容易。拆开摄像头外壳，一眼便发现了uart的接口注释字符Tx/Rx/GND/VCC，我们可以很快意识到这里留有uart调试接口。

![4.png](https://www.iotsec-zone.com/api/image/v2/20240830/d3t091galp5fyds4d5.png)

在网上查阅资源后，发现该设备论坛给我们提供了进入U-Boot shell的密码。在某些产品中密码为'tpl' ， 在某些情况下为'slp' 。本小节实例中为'slp'，当我们给设备插上电源后，看到"Autobooting in 1 second"字符时输入slp，可以让我们进入 U-Boot 终端 。输入help 查看U-Boot帮助命令，这里使用printenv查看U-Boot 环境变量。

![5.png](https://www.iotsec-zone.com/api/image/v2/20240830/d3t09865r1a0deolny.png)

这里我们需要重点关注一下 bootargs 变量，这里为启动Uboot时的参数 。init为初始化程序，我们将其修改为/bin/sh后将引导进程生成一个 shell 作为初始进程，从而无需身份验证即可进入 root shell。

```
setenv bootargs console=ttyS1,115200n8 mem=45M@0x0 rmem=19M@0x2d00000 root=/dev/mtdblock6 rootfstype=squashfs spdev=/dev/mtdblock7 noinitrd init=/bin/sh
```

然后执行bootcmd的命令，引导 U-Boot 继续启动。

```
sf probe;sf read 0x80700000 0x80200 0x175000; bootm 0x80700000
```

等待一段时间后，我们进入了 root shell。init程序会做一些初始化操作，由于我们用 /bin/sh 替换了 init 进程，这里部分引导过程并未执行。这里我们需要手动引导，比较重要的点为需要挂载一下 /dev 和 /proc 。挂载 /proc 后，我们就可以使用一些基本命令以及访问现有分区了。

```
mount -t proc none /proc
```

查看一下/proc/partitions中的分区名称。

![6.png](https://www.iotsec-zone.com/api/image/v2/20240830/d3t0aheuv5skabn7fi.png)

这里显示了mtdblock虚拟设备的内存映射，访问这些意味着访问闪存的内容。通常这些设备列在/dev中，由于我们通过获取 root shell 绕过了部分启动过程，因此我们需要手动创建它们，通过在挂载tmpfs来使/dev可写。

```
mount -t tmpfs tmpfs /dev -o mode=0755,size=512K
```

我们需要将每个mtdblock设备都挂载，以下为挂载命令 ：

```
mknod /dev/mtblock0 b 31 0
mknod /dev/mtblock1 b 31 1
mknod /dev/mtblock2 b 31 2
mknod /dev/mtblock3 b 31 3
mknod /dev/mtblock4 b 31 4
mknod /dev/mtblock5 b 31 5
mknod /dev/mtblock6 b 31 6
mknod /dev/mtblock7 b 31 7
mknod /dev/mtblock8 b 31 8
mknod /dev/mtblock9 b 31 9

```

现在每个虚拟设备都安装在/dev下，我们可以访问到闪存内容。tapo c200 摄像头为我们提供了 SD 卡插槽，我们将用它来转储 Flash 内容。通过查看/proc/partitions ，我们可以找到插入的MicroSD的几个分区：

![7.png](https://www.iotsec-zone.com/api/image/v2/20240830/d3t0bbhgtt6mrowhvp.png)

为它创建一个节点。

```
mknod /dev/mmcblk0p1 b 179 1
```

我们将其安装在/tmp/sdcard下。

```
mount tmpfs /tmp -t tmpfs -o size=20633600,nosuid,nodev,mode=1777  
mkdir /tmp/sdcard
mount -t vfat /dev/mmcblk0p1 /tmp/sdcard/
```
现在可以在/tmp/sdcard路径(MicroSD 卡)下写入文件了。执行下面的命令会将所有/dev/mtdblocks的内容追加写入到/tmp/sdcard/flashdump.bin中，这时便完成了flash转储。

```
cat /dev/mtdblock0 >> /tmp/sdcard/flashdump.bin
cat /dev/mtdblock1 >> /tmp/sdcard/flashdump.bin
cat /dev/mtdblock2 >> /tmp/sdcard/flashdump.bin
cat /dev/mtdblock3 >> /tmp/sdcard/flashdump.bin
cat /dev/mtdblock4 >> /tmp/sdcard/flashdump.bin
cat /dev/mtdblock5 >> /tmp/sdcard/flashdump.bin
cat /dev/mtdblock6 >> /tmp/sdcard/flashdump.bin
cat /dev/mtdblock7 >> /tmp/sdcard/flashdump.bin
cat /dev/mtdblock8 >> /tmp/sdcard/flashdump.bin
cat /dev/mtdblock9 >> /tmp/sdcard/flashdump.bin
```

完成固件提取后，取消挂载 MicroSD 卡即可。

```
umount /tmp/sdcard
```
既然固件已经提取，我们可以解包固件后根据实体设备进行调试。此时我们还需要开启远程访问服务，便于我们管理实体设备。在进行初始化操作后，我们已经可以访问系统了，现在我们需要进行远程访问。这里我们可以查看一下网络连接及服务的情况：

![8.png](https://www.iotsec-zone.com/api/image/v2/20240830/d3t0ckkac2klc85dv4.png)

发现Telnet 服务正在运行，且telnet服务绑定到地址127.0.0.1，我们无法从本地网络访问。这里我们通过浏览设备中的文件系统，发现了telnetd服务的配置启动文件。

![9.png](https://www.iotsec-zone.com/api/image/v2/20240830/d3t0csg0thrri7ehro.png)

在此脚本中，配置了telnetd服务，并使用"-b"参数绑定ip为127.0.0.1，即限制只可本机网络访问。我们删除配置文件中的"127.0.0.1"后，可以使设备中的telnet服务远程访问生效。在修改完配置文件后，需要重启telnet服务:

```
/etc/init.d/telnet restart
```

此时便可以从同一内网内的机器对某T设备进行 telnet 远程访问。

![10.png](https://www.iotsec-zone.com/api/image/v2/20240830/d3t0d8ifvjq2jeaiox.png)

# 总结
在这一小节中，我们通过固件降级的相关操作，并结合SD卡固件提取知识点，完成对某T设备的初步分析，后续小节我们将对某T设备进行固件解密以及设备协议进行分析。
