# D-Link固件运行环境修复与调试
> ChaMd5
> 来源：https://www.iotsec-zone.com/article/444

# DLink固件运行环境修复与调试

在进行路由器固件分析的时候往往需要将固件模拟运行，通常firmAE和FAP等集成模拟工具是很好的选择，但是并不是所有的固件都可以模拟成功，部分固件运行依赖硬件，这就需要修复固件的运行环境，实现固件的模拟。

以dlink dir619l为例,使用firmAE和FAP模拟均未成功。所以这里采用qemu对此固件进行模拟。

qemu user mode:

首先使用binwalk解包固件，将qemu-mips-static拷贝过来。

![0.png](https://www.iotsec-zone.com/api/image/v2/20240617/d22bvy160zu7yrxwdw.png)

尝试运行程序，报MIB错误

![1.png](https://www.iotsec-zone.com/api/image/v2/20240617/d22bw4rvnr9a2vhfew.png)

ida找到字符串的引用，分析这部分代码逻辑

![2.png](https://www.iotsec-zone.com/api/image/v2/20240617/d22bwc7hwuogku4x4a.png)

apmib_init这个函数是从flash中读取mib值到RAM中，模拟环境没有flash硬件，所以应该会读取失败。apmib_init读取数据失败返回0，赋值给v0，然后bnez命令对v0进行检测，若为0，则回显初始化失败，报错退出。

这里采用hook的方式，编写动态库劫持。

![3.png](https://www.iotsec-zone.com/api/image/v2/20240617/d22bxv4hwks39iecdv.png)

使用qemu加载动态库执行，依旧报错了

![4.png](https://www.iotsec-zone.com/api/image/v2/20240617/d22by1zubxigfy04mc.png)

重新断点运行，输出到这里没有崩溃

![5.png](https://www.iotsec-zone.com/api/image/v2/20240617/d22by7odyfz1gm8tdg.png)

这里会报错

![6.png](https://www.iotsec-zone.com/api/image/v2/20240617/d22bycnv8h3ckytgyj.png)

可以看到是由于apmib_get报错，在脚本中添加以下代码hook此函数

![7.png](https://www.iotsec-zone.com/api/image/v2/20240617/d22byj49sssxepe9lq.png)

可以看到服务成功启动

![8.png](https://www.iotsec-zone.com/api/image/v2/20240617/d22byqce8koj0leax5.png)

但是访问web页面又报错了

![9.png](https://www.iotsec-zone.com/api/image/v2/20240617/d22bywjbdhasrrrqu6.png)

看一下Wizard_Easy_LangSelect.asp，试图从硬件读取信息

![10.png](https://www.iotsec-zone.com/api/image/v2/20240617/d22bz2r093kccnhjdy.png)

查看first.asp，应该是进入了else分支

![11.png](https://www.iotsec-zone.com/api/image/v2/20240617/d22bz8wlaik5jnqnwz.png)

将逻辑改为无论如何都进入Welcome.asp

![12.png](https://www.iotsec-zone.com/api/image/v2/20240617/d22bzey6zru52lkcsd.png)

访问成功

![13.png](https://www.iotsec-zone.com/api/image/v2/20240617/d22bzlu8yzn3a5il7d.png)

至此模拟成功，发送poc进行测试，但是还没有命中漏洞点就又崩溃了

![14.png](https://www.iotsec-zone.com/api/image/v2/20240617/d22bzrpsy1q5w7cnib.png)

![15.png](https://www.iotsec-zone.com/api/image/v2/20240617/d22bzutwd99itfwsyo.png)

看一下v1寄存器的值

![16.png](https://www.iotsec-zone.com/api/image/v2/20240617/d22c01fpbi2cs31l9n.png)

可以看到$v1的值为0x5b59，但是根据sb指令的用法此处应该是一个内存地址，所以使用gdb将v1的值改为有效内存地址或者跳过此条指令继续执行可成功控制返回地址

![17.png](https://www.iotsec-zone.com/api/image/v2/20240617/d22c0aqc0j3eykug5w.png)

![18.png](https://www.iotsec-zone.com/api/image/v2/20240617/d22c0dhathepeem64n.png)

qemu system mode:

由于user mode 模拟并不能获取程序的基地址，所以真正的调试还需在system mode下进行

下载qemu-system需要的kernel和虚拟硬盘文件,此设备为mips大端

```
wget https://people.debian.org/~aurel32/qemu/mips/vmlinux-3.2.0-4-4kc-malta
wget https://people.debian.org/~aurel32/qemu/mips/debian_wheezy_mips_standard.qcow2
```
安装虚拟网络设备tun

```
sudo apt-get install uml-utilities
```
为root用户添加网卡tap0

```
sudo tunctl -t tap0 -u root
```
设置IP地址

```
sudo ifconfig tap0 192.168.100.2/24
```
查看一下我们设置的IP地址

```
ifconfig
```

![19.png](https://www.iotsec-zone.com/api/image/v2/20240617/d22c2d2xgey0l9e6qu.png)

使用如下命令启动

```
sudo sudo qemu-system-mips -M malta -kernel vmlinux-3.2.0-4-4kc-malta -hda debian_wheezy_mips_standard.qcow2 -append "root=/dev/sda1 console=tty0" -nographic  -netdev tap,id=tapnet,ifname=tap0,script=no -device rtl8139,netdev=tapnet
```

启动成功后登录使用root/root登录

之后将dir619l的文件系统上传到qemu虚拟机，可以同gdbserver一并上传

```
scp -r squashfs-root-0/ root@192.168.100.3:/root/
```

在”squashfs-root-0/“目录运行下面脚本,配置虚拟机网卡，启动boa程序

```
#!/bin/sh
echo "add ip addr ..."
ifconfig eth0 192.168.100.3/24 up
echo "hook ..."
LD_PRELOAD=/apmib-ld.so
export LD_PRELOAD
echo "run boa ..."
chroot . ./bin/boa
```
可以看到服务已经运行成功了

![20.png](https://www.iotsec-zone.com/api/image/v2/20240617/d22c3ffokr5tnmpino.png)

接下来就是gdbserver 附加调试

另起一个终端ssh连接qemu虚拟机

```
ssh root@192.168.100.3
```

查看服务pid

![21.png](https://www.iotsec-zone.com/api/image/v2/20240617/d22c3vc2vuvqmadgni.png)

gdbserver 附加调试

![22.png](https://www.iotsec-zone.com/api/image/v2/20240617/d22c40snfxa77iytcg.png)

发送poc,发现在下图这个跳转不知为何报错了

![23.png](https://www.iotsec-zone.com/api/image/v2/20240617/d22c46ose6oha8w9a0.png)

修改当前pc为下一条指令地址运行即可成功触发崩溃控制pc也可以查看程序的内存映射,现在可以进行后续研究

![24.png](https://www.iotsec-zone.com/api/image/v2/20240617/d22c4clnrowuhwwxak.png)

![25.png](https://www.iotsec-zone.com/api/image/v2/20240617/d22c4fzm14gd26pvnx.png)

- END -
