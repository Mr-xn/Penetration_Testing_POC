# D-link M30固件模拟
> bashis
> 来源：https://www.iotsec-zone.com/article/528

最近在学习IOT的固件，所以找了dlink的M30固件来进行模拟，首先从官网上下载1.10版本，因为固件是加密过的，需要解密，然后再进行模拟。

## 固件解密

github上已经有了解密dlink固件的程序`[GitHub - devttys0/delink](https://github.com/devttys0/delink.git)`，下载下来，使用rust进行编译最后生成`delink`，然后解密。

```shell
./delink M30A1_FW110B02.bin m30_110_dec.bin
```

解密完成后，使用`binwalk`来提取固件。

```shell
binwalk -Me m30_110_dec.bin
```

提取成功之后，可以得到`squashfs`文件系统。

![0.png](https://www.iotsec-zone.com/api/image/v2/20260111/dflhxky6hnqtolbuc5.png)

## 固件模拟

### 固件分析

在模拟之前，需要先大概过一下这个固件的关键信息，如web服务，启动脚本等。

为了方便，我使用`firmwalker`对`squashfs-root`文件夹进行扫描。

```shell
./firmwalker.sh ./squashfs-root
```

完成之后查看扫描结果，看能否发现一些关键服务以及脚本。

![1.png](https://www.iotsec-zone.com/api/image/v2/20260111/dflhylp192vgyyofmk.png)

发现了一个关键的web服务程序`httpd`。同时需要留意一下以下几个目录：`bin`, `sbin`，`usr/bin`，`usr/sbin`，提取出来的可执行程序可能会指向不正确的链接，如`/dev/null`，需要修复一下，让它们指向`busybox`。脚本如下：

```shell
#!/bin/sh
# 批量修改 ./bin/、./sbin/、./usr/bin/、./usr/sbin/ 下指向 /dev/null 的软链接
# 定义需要处理的目录和对应的busybox路径
TARGETS="
./bin ../bin/busybox
./sbin ../bin/busybox
./usr/bin ../../bin/busybox
./usr/sbin ../../bin/busybox
"

# 遍历每一行配置
echo "$TARGETS" | while read dir busybox_link; do
    # 跳过空行
    [ -z "$dir" ] && continue

    # 检查目录是否存在
    if [ ! -d "$dir" ]; then
        echo "警告：目录 $dir 不存在，跳过该目录"
        continue
    fi

    echo "========================================"
    echo "开始处理目录：$dir（链接指向：$busybox_link）"
    # 遍历目录下所有文件
    for file in "$dir"/*; do
        # 跳过子目录
        [ -d "$file" ] && continue

        # 检查是否是指向 /dev/null 的软链接
        if [ -L "$file" ] && [ "$(readlink "$file")" = "/dev/null" ]; then
            # 删除旧链接
            rm -rf "$file"
            # 创建新链接
            ln -s "$busybox_link" "$file"
            echo "  已修改：$file -> $busybox_link"
        fi
    done
done

echo -e "\n所有目录处理完成！"
```

### 启动web服务

`httpd`是`aarch64`小端，所以我用`qemu-system-aarch64`来模拟，模拟之前先配置主机网络。

```shell
sudo tunctl -t tap0  
sudo ifconfig tap0 192.168.0.4/24 up 
```

然后启动`qemu`虚拟机

```shell
qemu-system-aarch64 \                                                                     
    -M virt -m 4G -cpu cortex-a72 -smp 2 \
    -bios QEMU_EFI.fd \
    -drive id=hd0,media=disk,if=none,file=debian-10-generic-arm64-20201207-477.qcow2 \
    -device virtio-scsi-pci \
    -device scsi-hd,drive=hd0 \
    -net nic -net tap,ifname=tap0,script=no,downscript=no -nographic
```

启动之后为虚拟机添加网卡并配置ip。

```shell
brctl addbr br0
brctl addif br0 enp0s1
ip link set enp0s1 up
ip link set br0 up
ifconfig br0 192.168.0.3/24
```

我们将`squashfs-root`文件夹打包传到虚拟机中，并启动`httpd`。

![2.png](https://www.iotsec-zone.com/api/image/v2/20260111/dflhzllt93t5gc9bq2.png)
这里报错了，我们找一下`init_csman_ipc_client`函数，发现在`libcsman.so`中。

![3.png](https://www.iotsec-zone.com/api/image/v2/20260111/dflhzwwmugm9lpk5ty.png)
将`libcsman.so`拖到ida中，查找字符串。

![4.png](https://www.iotsec-zone.com/api/image/v2/20260111/dfli0667txl8icftqo.png)
定位到函数位置。

![5.png](https://www.iotsec-zone.com/api/image/v2/20260111/dfli0hxgnsetldy7aq.png)
可以看到这里调用了一个`shmget`，返回值小于0，通过查询，我们得到如下信息：

- `shmget` 是 Linux 系统中 **System V 共享内存** 的核心函数，作用是**创建 / 获取一个共享内存段的标识符**，进程间可通过这个标识符访问同一块内存，实现高效数据通信。
  
- 参数1为共享内存的唯一标识（键值），参数2为共享内存段的大小（字节），参数3为
  
  标志位，组合使用：
  
   `IPC_CREAT`：创建新的共享内存（不存在则创建，存在则获取）；
  
   `IPC_EXCL`：配合 `IPC_CREAT` 使用，若内存已存在则报错（确保创建新内存）；
  
  权限位：如 `0666`（可读可写，和文件权限一致）。
  

这里可以看到标志位为428，八进制为0666，说明常见的标志位（如 `IPC_CREAT`、`IPC_EXCL`）未被包含，说明这段代码仅尝试获取已存在的共享内存（key=5678），若不存在则返回错误。

既然这里仅仅是尝试获取，那应该有其他地方负责创建这个共享内存，但是`libcsman.so`中只有这里一处调用了`shmget`，我们去其他地方查找。

![6.png](https://www.iotsec-zone.com/api/image/v2/20260111/dfli0vcuaow6raxhlk.png)
发现这个 csmanuds程序比较可疑，我们把它拖到ida中分析。仅仅找到一处对于shmget函数的引用。

![7.png](https://www.iotsec-zone.com/api/image/v2/20260111/dfli14wblm6ciddvbp.png)
这里我们看到第三个参数是950，等价于八进制 1666，由 IPC_CREAT（512） + 0666（438） 组成，用来创建key=5678、大小 8 字节、权限 0666 的共享内存段。

分析到这里，发现csmanuds程序应该在httpd之前执行，但是这个程序可能会需要参数。我们去firmwalker的结果中查找蛛丝马迹，并没有查到，可能是在某个启动脚本中。

![8.png](https://www.iotsec-zone.com/api/image/v2/20260111/dfli1gv5gboqhfnfia.png)
找到csman_server.sh这个脚本，查看具体内容。

![9.png](https://www.iotsec-zone.com/api/image/v2/20260111/dfli1oj95i69gxsfbh.png)
我们将这个脚本执行一下。

![10.png](https://www.iotsec-zone.com/api/image/v2/20260111/dfli1xhmbimwvgvifj.png)
我们暂时不管这些错误，启动httpd。

![11.png](https://www.iotsec-zone.com/api/image/v2/20260111/dfli281xnwvrrlar4o.png)
我们查看目录`usr/www.d`是否存在，

![12.png](https://www.iotsec-zone.com/api/image/v2/20260111/dfli2uwnkwy9xl9prz.png)
发现目录并不存在，我们去查找是否在哪个脚本中使用了`usr/www.d`。

![13.png](https://www.iotsec-zone.com/api/image/v2/20260111/dfli36mcvo06zykg8h.png)
可以看到`uitar.sh`是负责解压web主目录的，手动创建`/usr/www.d`目录，并将`/boot/www.tgz`解压到`www.d`目录下，

在之前执行`csman_server.sh`时显示`csmanuds`会访问`/tmp/csman`，所以我们也将`/usr/www.d/*dat`拷贝至`./tmp/csman/`下，

既然涉及到`csman`，那么我们重新执行`csman_server.sh`，之后执行`httpd`。

![14.png](https://www.iotsec-zone.com/api/image/v2/20260111/dfli3ibsxn9lgqkefb.png)

![15.png](https://www.iotsec-zone.com/api/image/v2/20260111/dfli3oewuhliwvzydl.png)
查看端口，80端口已经启动。

![16.png](https://www.iotsec-zone.com/api/image/v2/20260111/dfli3y9v0cogln5c2e.png)
访问web管理页面。

![17.png](https://www.iotsec-zone.com/api/image/v2/20260111/dfli455i0ch0yisl9j.png)
空密码登录之后重新设置密码再次登录。

![18.png](https://www.iotsec-zone.com/api/image/v2/20260111/dfli4gb0hm75pggwb9.png)
最后感谢SeBao老师的指导和支持，感谢IOTsec-Zone社区。

## 参考

[GitHub - devttys0/delink
