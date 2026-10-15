# 记一次固件解密学习--X软路由
> ch0ing
> 来源：https://www.iotsec-zone.com/article/218

# 记一次固件解密学习--X软路由

## 定位加密

官网直接提供这么多格式的系统下载

![0.png](https://www.iotsec-zone.com/images/MdImg/987d0acc072e66390ed8e3bfe577fe2b.png)

直接下载的bin文件`binwalk`梭哈不开。

下一个ISO回来装成虚拟机，咱还收拾不了你了吗。

用7-zip打开`.vmdk`文件。

rootfs脱出来解不开。啊这，不按套路出牌啊。

![1.png](https://www.iotsec-zone.com/images/MdImg/51a19cb53fb48e9acc9de362042108f3.png)
初步怀疑是grub 或者vmlinuz被厂商进行了修改，加入了解密操作。

grub配置关键代码

```
menuentry "xxxxxi RouterOS" "$ikversion" "$uuid" "$default" {
	linux /boot/vmlinuz root=/dev/ram0 crashkernel=128M@64M rootfstype=ext4 rootwait console=tty0 bootguide=hd intel_idle.max_cstate=0 processor.max_cstate=0 ikversion=$2 diskuuid=$3 grub_menu_id=0 grub_default=$4
	initrd /boot/rootfs
}

```

从磁盘文件中解出grub和vmlinuz看一下

![2.png](https://www.iotsec-zone.com/images/MdImg/37c49511ab97bd3f1696e5ed3c9b186a.png)
好吧，看起来就是像大雄同学对内核加了一些逻辑。然后来解密rootfs。

## 分析加密

分析思路为对着linux的内核代码，看反编译中添加了什么代码逻辑来解密。

常规套路，要想分析，先搞点报错字符串出来。

将vmdk挂载到ubantu，rootfs内容随便改改,然后启动，可以抓到报错关键字."Invaild rootfs"

有了关键字就好办了。

使用工具

[https://github.com/torvalds/linux/blob/master/scripts/extract-vmlinux](https://github.com/torvalds/linux/blob/master/scripts/extract-vmlinux)

将bzImage提取为vmlinux文件。

然后搜索关键字找到调用点，通过函数中其他得打印字符串定位加密逻辑就在在`populate_rootfs`函数中

![3.png](https://www.iotsec-zone.com/images/MdImg/09f19bdee5b1e49c252b2b84c7a445cc.png)

通过开源代码还原代码中的变量名，变量类型。

[https://github.com/torvalds/linux/blob/v3.18/init/initramfs.c](https://github.com/torvalds/linux/blob/v3.18/init/initramfs.c)
![4.png](https://www.iotsec-zone.com/images/MdImg/6db955466da4f65af3da248e53e54dce.png)
![5.png](https://www.iotsec-zone.com/images/MdImg/3e14ca64ddbdfe66625b179f9a8e91b6.png)

可以看到，在do_while循环中通过16位key_16数组生成1024位key_1024数组。

![6.png](https://www.iotsec-zone.com/images/MdImg/c049520f6a43f9085bd2aceb19cf8d6c.png)
![7.png](https://www.iotsec-zone.com/images/MdImg/b9845b709c7983229bc0172be510d615.png)

然后再for循环中通过key_1024运算解密。

![8.png](https://www.iotsec-zone.com/images/MdImg/df5b75d002715260ddaf33af1e6544ef.png)

## 解密

依据上边得分析，将伪代码还原为C代码,核心代码如下。

```C
do {
	key_1024[key_index] = key_16[key_index & 0xf] + 19916032 * ((int32_t)key_index + 1) / 131u;
	++key_index;
} while (key_index != 1024);

for (iter = 0;
     initrd_real_size > (uint32_t)iter;
     initrd_start[iter - 1] = ((initrd_start[iter - 1] - (uint8_t)tmp_var) << ((uint8_t)tmp_var % 7u + 1)) | ((int32_t)(uint8_t)(initrd_start[iter - 1] - tmp_var) >> (8 - ((uint8_t)tmp_var % 7u + 1)))) {
	tmp_var = var_0 + iter++;
	*(uint8_t*)&tmp_var = (uint8_t)(initrd_size_low_byte + key_1024[tmp_var % 1024u] * var_1);
}
```

编写编译c代码,成功解密。丢到binwalk 得到固件，虽然系统不是很完整。仅仅有几个目录，但是web相关的lua代码已经拿到了，可以找一个rce漏洞获取shell，再进行进一步研究

![9.png](https://www.iotsec-zone.com/images/MdImg/821a8a86defcefeb61f32221c8acddea.png)

![10.png](https://www.iotsec-zone.com/images/MdImg/b38a3b2a10b3e0a72ec3f6dea385f16d.png)

![11.png](https://www.iotsec-zone.com/images/MdImg/6e6299211e2b4167f8b017281cf31b20.png)
