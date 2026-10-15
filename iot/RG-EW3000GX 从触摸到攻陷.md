# RG-EW3000GX 从触摸到攻陷
> 皮皮先生
> 来源：https://www.iotsec-zone.com/article/558

# 基本信息概述

**产品**：AX3000 双频WI-Fi6无线路由器

**产品型号**：RG-EW3000GX

**固件版本**：ReyeeOS 1.380.2222;EW_3.0(1)B11P380,Release(12222219)

# UART固件提取

## 前期准备

首先摸到真机先暴力拆掉，然后焊接杜邦线  GND TX RX 

配合USB 转 TTL 串口模块进行串口调试 ，那么本次就使用最新研发的 **iot多功能调试板** 其中的UART调试功能

![0.png](https://www.iotsec-zone.com/api/image/v2/20260819/dksre85782okye155a.png)

非常的贴心，还准备了网卡功能，对于我这轻薄本没有网口接口太友好了。

以往我们在遇到板子上面没有显示TX RX 又或者还得边插边调，他这个有个特别好用的点，你不用管谁接TX,谁接RX ，直接俩根线连URAT0或URAT1就可以了

![1.png](https://www.iotsec-zone.com/api/image/v2/20260819/dksreglkxl8b7rkdti.png)

本次就插UART0进行串口调试

手动工作做好后，现在用MobaXterm 进行串口调试

![2.png](https://www.iotsec-zone.com/api/image/v2/20260819/dksrelw3yyv1suat5s.png)

因为无脑插上去的，因为RX和TX没有对上，没有输出日志信息

![3.png](https://www.iotsec-zone.com/api/image/v2/20260819/dksreova2an9hcv4zr.png)

**连接规则**

```
GND  --------------->  GND
TX   --------------->  RX
RX   --------------->  TX
```

这个时候只需要按一下UART0 交换按钮 ，他会自动切换RX TX,按一下马上就对上了，真的特别简单好用

![4.png](https://www.iotsec-zone.com/api/image/v2/20260819/dksrethat9ruvtaafh.png)

![5.png](https://www.iotsec-zone.com/api/image/v2/20260819/dksrew6xvq6kyvnsfk.png)

已经打印信息了

## 启动信息分析

MTD分区信息

![6.png](https://www.iotsec-zone.com/api/image/v2/20260819/dksrf11f1pyc4fuxe1.png)

观察启动信息其中就有选项 0 可以进入u-boot

![7.png](https://www.iotsec-zone.com/api/image/v2/20260819/dksrf3x6qkw3sglnlj.png)

最后正常执行会到登录认证

![8.png](https://www.iotsec-zone.com/api/image/v2/20260819/dksrf7cv7elfziiqhu.png)

但是我又不知道设置的啥密码，弱口令又进不去

先进入u-boot 再观察观察，重新上电 狂按0进入

![9.png](https://www.iotsec-zone.com/api/image/v2/20260819/dksrfdez12zdb59fup.png)

按help 看看有没有可用指令

![10.png](https://www.iotsec-zone.com/api/image/v2/20260819/dksrfhnlb3wrzhszmy.png)

其实像tftpboot bootm md 等可利用的命令都挺多的，但是我们直接暴力绕过u-boot进入shell 才更方便，这里我们的思路是把u-boot传给内核系统执行的启动参数 bootargs 加个init=/bin/sh 绕过

简单描述下绕过流程

```
bootargs 是 U-Boot（引导程序）传给 Linux 内核的启动参数
u-boot --> 把内核加载到内存 --> 其中把bootargs传给内核读取执行 --> 执行init=/bin/sh --> shell
```

## 绕过u-boot改密码

```
setenv bootargs 'console=ttyS0,115200n8 init=/bin/sh'
mtkboardboot
```

![11.png](https://www.iotsec-zone.com/api/image/v2/20260819/dksrfnohi1262dkzct.png)

进入shell ，接下来我们要做几件事

```
#挂载虚拟文件系统
mount -t sysfs sysfs /sys
mount -t tmpfs tmpfs /dev

#喂看门狗，不喂的话过了30秒就会重启后面挂载一系列操作就会白搞，所以先搞这个
#查看看门狗设备号
cat /sys/class/watchdog/watchdog0/dev
```

![12.png](https://www.iotsec-zone.com/api/image/v2/20260819/dksrfrp1tt16wt8fuh.png)

拿到251:0

```
mknod /dev/watchdog c 251 0
```

挂载 /proc 定位 rootfs_data 可写数据分区

```
mount -t proc proc /proc
cat /proc/mtd
```

![13.png](https://www.iotsec-zone.com/api/image/v2/20260819/dksrfxf1w8r1abb1fu.png)

找到对应的 mtd9 ,接下来 手动挂载 Overlay 文件系统并 chroot 进入真实系统环境

```
mount -t tmpfs tmpfs /tmp
mkdir -p /tmp/ov /tmp/root

# 创建 mtdblock9 设备节点并挂载 rootfs_data 分区（jffs2）到 /tmp/ov
mknod /dev/mtdblock9 b 31 9 
mount -t jffs2 /dev/mtdblock9 /tmp/ov

#挂载 OverlayFS
mount -t overlay overlay -o lowerdir=/,upperdir=/tmp/ov/upper,workdir=/tmp/ov/work /tmp/root

chroot /tmp/root /bin/sh
```

![14.png](https://www.iotsec-zone.com/api/image/v2/20260819/dksrg19wh5mn4ntmjw.png)

```
sync && umount /tmp/root && umount /tmp/ov && sync
reboot -f
```

把内存中的缓存数据写入flash，然后卸载 前面挂载的俩个文件系统，然后再次同步写入flash 确保保存成功

# 提取固件

![15.png](https://www.iotsec-zone.com/api/image/v2/20260819/dksrg5cri9yvnbop2c.png)

临时关闭内核日志输出，不然太烦了

```
echo 0 > /proc/sys/kernel/printk
```

## 配置网络

```
ip addr
```

![16.png](https://www.iotsec-zone.com/api/image/v2/20260819/dksrg8lmua7v16oukt.png)

可以看到网桥 br-wan 也就是  10.44.77.254  ，拿到路由器ip ，那么接下来根据10.44.77.0网段 去配置ip

windows主机

![17.png](https://www.iotsec-zone.com/api/image/v2/20260819/dksrgbr1chv2kolt3z.png)

虚拟机

sudo ifconfig ens33 10.44.77.200/24 up

![18.png](https://www.iotsec-zone.com/api/image/v2/20260819/dksrgf4ghuvl4dwgy5.png)

测试连通

![19.png](https://www.iotsec-zone.com/api/image/v2/20260819/dksrgi8c2cjccnoq0q.png)

## 查找固件

```
mount -t proc proc /proc	
cat /proc/mtd
```

![20.png](https://www.iotsec-zone.com/api/image/v2/20260819/dksrglr9kadojdfmlw.png)

可以看到 我们需要的 mtd6 "firmware" 分区 15KB左右 ，接下来就是对这个分区

查看可使用的命令

```
ls /bin
```

![21.png](https://www.iotsec-zone.com/api/image/v2/20260819/dksrgp2qy8xlbt2qjq.png)

有dd命令 配合 nc 传

```
dd if=/dev/mtd6 of=/tmp/firmware.bin bs=1M

#虚拟机
nc -l -p 1314 > firmware.bin
#路由器
nc 10.44.77.200 1314 < /tmp/firmware.bin
```

![22.png](https://www.iotsec-zone.com/api/image/v2/20260819/dksrgvd0fv63gdkzqd.png)

没毛，接下里binwalk 提取下文件系统

```
binwalk -Me firmware.bin
```

![23.png](https://www.iotsec-zone.com/api/image/v2/20260819/dksrgybtr51ppz2xcj.png)

# 启动项分析

老规矩先从 /**etc/inittab** 看

![24.png](https://www.iotsec-zone.com/api/image/v2/20260819/dksrh2h546wnjrc9tm.png)

系统初始化最先执行 /etc/init.d/rcS ，没有找到该文件再往下找/etc/rc.common

![25.png](https://www.iotsec-zone.com/api/image/v2/20260819/dksrh4yut4ii2nie4w.png)

 /etc/rc.d/S*，紧跟查看

**/etc/rc.d/S50lighttpd** 

![26.png](https://www.iotsec-zone.com/api/image/v2/20260819/dksrh7r067un7q50jo.png)

这里就能很明显发现前端是 /usr/sbin/lighttpd ,对应的配置文件是 /etc/lighttpd/lighttpd.conf

启动的方法是/usr/sbin/lighttpd -D -f /etc/lighttpd/lighttpd.conf ,这里都明确说明

再看下 **/etc/lighttpd/lighttpd.conf**

![27.png](https://www.iotsec-zone.com/api/image/v2/20260819/dksrhgwm72vn6z5zas.png)

开始这部分 加载功能模块其中 **mod_unifyframe** 就是锐捷自定义模块，定义了网站根目录 /www/ ,包括默认首页

这里定义了 CGI 映射关系，当url匹配到 /cgi-bin/luci 默认 走 /www/cgi-bin/luci 执行 ,匹配到.lua 就交给 /usr/bin/lua 去解释执行。

当匹配到 路径单独匹配到 uri.path 和 requst.pathinfo 同时满足的话就由`mod_unifyframe` 模块接管处理。

现在针对 自定义模块进行查找下 

![28.png](https://www.iotsec-zone.com/api/image/v2/20260819/dksrhllopkqjpn2lcu.png)

init.d下面unifyframe-sgi

![29.png](https://www.iotsec-zone.com/api/image/v2/20260819/dksrhpkc6ilb7roo6w.png)

USE_PROCD=1 表示它运行在 procd 下，procd依赖 ubusd 总线 ，还得启动  ./sbin/ubusd

 /usr/sbin/unifyframe-sgi.elf 后端主程序,建 socket

/usr/sbin/uf_ubus_call.elf ubus 代理

启动锐捷 Web 后端服务（unifyframe-sgi.elf + uf_ubus_call.elf），建立 socket 通信并支持 ubus 调用。

# 漏洞挖掘

直接真机测试

![30.png](https://www.iotsec-zone.com/api/image/v2/20260819/dksrhtczs8zaol2clu.png)

![31.png](https://www.iotsec-zone.com/api/image/v2/20260819/dksrhx2nfmx7d59jsx.png)

## 漏洞一

`unifyframe-sgi.elf` 内置插件模块 `configChange` 的 `cc_set`(0x414D58)→ `uf_get_url_config` 把用户提交的 `data.url`存在命令注入

把 /usr/sbin/unifyframe-sgi.elf 丢进ida，定位函数  *module_init_configChange* 

![32.png](https://www.iotsec-zone.com/api/image/v2/20260819/dksri25a2uyzqykrqu.png)

这里看几个关键动作，它设置模块名为configChange ，然后绑定的是 **sub_414D58** ，双击进入

![33.png](https://www.iotsec-zone.com/api/image/v2/20260819/dksri5me5q6vdf9kxa.png)

获取三个参数 url ,module , function 的值 ，其中url的值给到string

![34.png](https://www.iotsec-zone.com/api/image/v2/20260819/dksrifed5hd8q6b6gr.png)
这里往下走其实还是做了一丢丢检测 ，检查 `string` 是否包含 `$(` 或反引号。然后通过snprintf 进行拼接，最后交给ufm_popen也就是popen执行命令

```http
POST /cgi-bin/luci/api/cmd?auth=这里填认证后的token HTTP/1.1
Host: 10.44.77.254
Content-Length: 202
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36
Accept: application/json, text/plain, */*
Content-Type: application/json;charset=UTF-8
Origin: http://10.44.77.254
Accept-Encoding: gzip, deflate, br
Accept-Language: zh-CN,zh;q=0.9
Connection: keep-alive

暂不公开
```

执行

![35.png](https://www.iotsec-zone.com/api/image/v2/20260819/dkssvgtdq22b7kevk6.png)

## 漏洞二

**dev_config user_list_note 模块 name 字段命令注入**

首先先定位没有安全检测的

```
grep -c "param_safety_check" usr/local/lua/dev_config/*.lua
```

![36.png](https://www.iotsec-zone.com/api/image/v2/20260819/dksrioriqo0vexj3ht.png)

主要就是先看这些为0的，然后再结合是否有相关危险函数的

```
grep -n "os.execute\|io.popen\|luci.sys.exec\|luci.sys.call\|forkExec" \
       usr/local/lua/dev_config/dev_mode.lua \
       usr/local/lua/dev_config/hwnat.lua \
       usr/local/lua/dev_config/mesh.lua \
       usr/local/lua/dev_config/repeater_config.lua \
       usr/local/lua/dev_config/repeater_hostrouter.lua \
       usr/local/lua/dev_config/user_list_note.lua
```

![37.png](https://www.iotsec-zone.com/api/image/v2/20260819/dksris8r0baguult3m.png)

这里其实就是找可控参数，像dev_mode.lua 几乎就是全是固定字符串的execute ，我们进一步缩小到比如 os.execute(cmd) 类似可控的位置去做分析，比如该漏洞 user_list_note.lua  

```
gedit usr/local/lua/dev_config/user_list_note.lua
```

![38.png](https://www.iotsec-zone.com/api/image/v2/20260819/dksriw9nwnm9ifnayn.png)

这里就有很明显命令注入的特征了，接下里就是着重去看下sync_list 也就是 child_data ，接着往上翻分析child_guard_packaged_data

![39.png](https://www.iotsec-zone.com/api/image/v2/20260819/dksriz4m2tbbyaoz0b.png)

这里就是说存在相同的mac 才 存入 child_data ,这样才满足能执行到下面 child_guard_sync 里面的 os.execute(cmd),那么就可以利用可控参数name进行注入。

接下里整个思路就是先注册一个儿童mac，然后利用相同的mac，进行name注入。现在第一步就需要去知道怎么注册

```
gedit ./usr/local/lua/dev_config/child_guard.lua
```

请求入口

![40.png](https://www.iotsec-zone.com/api/image/v2/20260819/dksrj2k99ofljszobg.png)

![41.png](https://www.iotsec-zone.com/api/image/v2/20260819/dksrj5917o8wzufmhn.png)

![42.png](https://www.iotsec-zone.com/api/image/v2/20260819/dksrjak7k6n9pl6kfj.png)

这里有说明如果是已存在的mac只能注册一次只能改字段，不存在就table.inset 重新设置 ，

最好会生成写入到配置文件里 持久化

![43.png](https://www.iotsec-zone.com/api/image/v2/20260819/dksrjfzc3qz5vumegu.png)

废话不多说先上exp

先注册

```http
POST /cgi-bin/luci/api/cmd?auth=这里填认证后的token  HTTP/1.1
Host: 10.44.77.254
Content-Length: 122
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36
Accept: application/json, text/plain, */*
Content-Type: application/json;charset=UTF-8
Origin: http://10.44.77.254
Accept-Encoding: gzip, deflate, br
Accept-Language: zh-CN,zh;q=0.9
Connection: keep-alive

暂不公开
```

后利用

```http
POST /cgi-bin/luci/api/cmd?auth=这里填认证后的token HTTP/1.1
Host: 10.44.77.254
Content-Length: 157
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36
Accept: application/json, text/plain, */*
Content-Type: application/json;charset=UTF-8
Origin: http://10.44.77.254
Accept-Encoding: gzip, deflate, br
Accept-Language: zh-CN,zh;q=0.9
Connection: keep-alive

暂不公开
```

![44.png](https://www.iotsec-zone.com/api/image/v2/20260819/dksswrdov1fviwbazv.png)
