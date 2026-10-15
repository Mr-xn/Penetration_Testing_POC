# Netcore NAP871固件模拟
> 李小熠
> 来源：https://www.iotsec-zone.com/article/553

今天分析固件 NAP871。

品牌：Netcore（磊科）

固件名称：_NAP871升级固件.bin（Web 页面标注 Netcore(NAP871)CN-V1.2.31207,2014.11.24，运行时 CGI 上报 V1.2.31209）

下载地址：[https://www.netcoretec.com/service-support/download/firmware/312.html](https://www.netcoretec.com/service-support/download/firmware/312.html)

## 0x00 信息收集：

先解包固件：

```bash
binwalk -Me NAP871升级固件.bin
```
![0.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklweehwl549jzqkw6.png)

![1.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklwm27lhasux9ynxy.png)

查看 busybox 架构：

```bash
file ./squashfs-root/bin/busybox
```

![2.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklweyt9kyv45xc4l4.png)

```
ELF 32-bit MSB executable, MIPS, MIPS-I version 1 (SYSV), dynamically linked,
interpreter /lib/ld-uClibc.so.0, no section header
```

得知架构是 MIPS 32 位大端，uClibc 库，ELF 无节头。

看一下 web 目录和 etc 下的配置：

![3.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklwfau1os3n72j0lq.png)

![4.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklwfmb21nrqknucgz.png)

![5.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklwg24wzbicnsz8ba.png)

![6.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklwgpckes0cwwgal7.png)

发现 Web 服务是 boa（/bin/boa，Boa/0.94.14rc21），配置文件 /etc/boa.conf，监听 80 端口，页面根目录 /web。

看启动脚本 /bin/webs，了解 Web 服务是怎么起来的：

![7.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklwh53fbhhkocek2c.png)

```bash
#!/bin/sh
...
eval `flash get SUPER_NAME`
eval `flash get SUPER_PASSWORD`
eval `flash get USER_NAME`
eval `flash get USER_PASSWORD`
echo "${USER_NAME}:${USER_PASSWORD}" > /tmp/passwd
echo "${SUPER_NAME}:${SUPER_PASSWORD}" >> /tmp/passwd
...
/bin/boa -p /web -f /etc/boa.conf &
```

关键信息：boa 是厂商补丁版，**用 /tmp/passwd 做 HTTP Basic 认证**，账号口令由 webs 脚本从 flash 读出后写入。这个文件后面模拟时要手工 mock。

/web 下只有一个 CGI：/web/cgi-bin/cgitest.cgi，strings 看一下：

![8.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklwi49kanwqwtgagd.png)

![9.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklwixrdux9ob5il3s.png)

![10.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklwjfcegbr1p0zirm.png)

导入表里有 apmib_get / apmib_set / system / exec_sh，是典型的 Realtek 方案 AP 配置 CGI，所有业务请求都走它。

前端页面全是预 gzip 的（.htm/.js 都是 gzip 文件，boa 直接返回 Content-encoding: gzip），zcat 解压后分析 JS，在 script/netcore.js 里找到前端调后端的协议：

![11.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklwkuw8jvgveqqu5g.png)

```bash
zcat netcore.js >1.txt
```

![12.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklwl9cly0evrxedha.png)

```javascript
xmlhttp.open("post", $.PATH + url + ".cgi", true);
// $.PATH = "/cgi-bin-igd/"  （script/init.js 里定义 cgi_path）
// body 形如：mode_name=<name>&key=val...
```

也就是说所有业务请求都是 `POST /cgi-bin-igd/<name>.cgi`，页面加载发 `netcore_get`，保存配置发 `netcore_set`。/cgi-bin-igd/ 这个路径在文件系统里不存在，是补丁 boa 内部做的别名。

## 0x01 固件模拟

架构是 MIPS 大端，所以用 qemu-mips-static。

```bash
cd ~/Desktop/NAP871升级固件.bin.extracted/squashfs-root
```

把 qemu 拷进文件系统，方便 chroot：

```bash
cp $(which qemu-mips-static) ./usr/bin
```

![13.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklwo2nrhyrx0ptgbk.png)

### 坑 1：binwalk 留下的坏符号链接

binwalk 解压后 tmp、sys、media 是指向 /dev/null 的坏链接，/tmp/passwd 写不进去，直接删掉重建：

![14.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklwojateu34cusm85.png)

```bash
sudo rm -f ./tmp ./sys ./media
sudo mkdir tmp sys media
```

![15.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklwozwkzdmngpv4rk.png)

mock 认证文件（默认凭证 guest:guest，后面从 CGI 返回的 JSON 里也能确认）：

```bash
printf "guest:guest\n" | sudo tee ./tmp/passwd
```

![16.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklwp8bbjdyrjhpo1m.png)

### 坑 2：/dev 设备节点缺失（can't open /dev/null）

挂上 /proc，启动 boa：

```bash
sudo mount --bind /proc ./proc
sudo chroot . /usr/bin/qemu-mips-static /bin/boa -p /web -f /etc/boa.conf
```

直接报错退出：

```
boa.c:196 (main) - can't open /dev/null: No such file or directory
```
![17.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklwrltp1kotbhqrfb.png)
binwalk 用普通用户解压，创建不了设备节点，./dev 里是空的，boa 连 /dev/null 都打不开。也不能 bind-mount 宿主机的 /dev 凑数——后端 CGI 还需要一个可写的假 /dev/mtd（见坑 4），bind-mount 会把它带进宿主机 /dev 造成污染。干脆给 chroot 自建一套 /dev，顺手把 16MB 全零假 flash 也造出来：

```bash
sudo bash -c "cd dev && mknod null c 1 3; mknod zero c 1 5; \
  mknod console c 5 1; mknod tty c 5 0; mknod urandom c 1 9; chmod 666 null zero urandom"
sudo dd if=/dev/zero of=./dev/mtd bs=1M count=16
sudo chmod 666 ./dev/mtd
```

![18.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklws1pprwg9tuogfo.png)

### 坑 3：Can't create PID file!

再次启动 boa，还是报错：

![19.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklwsedit1uqpqgopb.png)

boa 默认要写 /var/run/boa.pid，rootfs 里没有这个目录，补上再启动：

```bash
sudo mkdir -p ./var/run ./var/log/boa
sudo chroot . /usr/bin/qemu-mips-static /bin/boa -p /web -f /etc/boa.conf
```

![20.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklwtf63zhqy0ftubb.png)
这次 80 端口正常监听，静态页面能访问了：

### 坑 4：后端 CGI 段错误

前端通了，轮到后端。如果前面没有造假 /dev/mtd，cgitest.cgi 一跑就崩：

```
[flash_read:10438] ERROR: open /dev/mtd failed, No such file or directory.
[apmib_init:7134] ERROR: plese restore default(1)
qemu: uncaught target signal 11 (Segmentation fault) - core dumped
```

原因：apmib 配置库初始化必须读 flash 的硬件配置区。

用 strace 观测到 apmib 读 flash 的三个分区偏移（qemu-user 下 strace 是最可靠的观测手段）：

```
openat(AT_FDCWD, "/dev/mtd", O_RDWR) = 3
lseek(3, 24576, SEEK_SET)   # 0x6000  hw setting     硬件配置区
lseek(3, 73728, SEEK_SET)   # 0x12000 current setting 当前配置区
lseek(3, 122880, SEEK_SET)  # 0x1E000 backup setting  备份配置区
```

flash 上第一次手动跑 CGI，签名校验失败，自动走 writeDefault() 把出厂默认配置写进假 flash（往 0x6000 写 H601 头、0x12000 写 6G02、0x1E000 写 6g02）。第一次仍以段错误收尾，但配置已经落盘；**第二次再跑，签名校验全部通过，CGI 正常输出，不再崩溃**：

```bash
sudo chroot . /usr/bin/qemu-mips-static /web/cgi-bin/cgitest.cgi   # 第 1 次：写默认配置，结尾段错误是预期现象
sudo chroot . /usr/bin/qemu-mips-static /web/cgi-bin/cgitest.cgi   # 第 2 次：无任何输出 = 正常
```

这个假 /dev/mtd 不只是过初始化，还真实承担了配置持久化——后面 netcore_set 的改动都会写进这个文件。

### 前后端联调验证
带上 guest:guest 访问返回 200，welcome.htm 向导页未授权也可访问

![21.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklwzxjl6gubf3m8pi.png)
后端读链路（页面加载时前端自动发这个）：

```bash
curl -u guest:guest -X POST http://127.0.0.1/cgi-bin-igd/netcore_get.cgi \
     -d "mode_name=netcore_get&noneed=noneed"
```

返回完整配置 JSON（型号、版本 V1.2.31209、MAC、SSID NETCORE_2.4G、接口统计、系统日志等），和真机页面数据源一致：

![22.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklwv0cuf5b29s8j2t.png)

后端写链路，挑 UI 上真实存在、纯配置无副作用的"定时重启"页测（字段名从 web/config/config.js 的 Panels 定义里找）：

```bash
curl -u guest:guest -X POST http://127.0.0.1/cgi-bin-igd/netcore_set.cgi \
     -d "mode_name=netcore_set&reboot_time_enable=1&time_reboot=03&time_reboot2=30"
```

返回 ["SUCCESS","2"]，再发 netcore_get 回读，reboot_time_enable/time_reboot/time_reboot2 都变成了新值，写链路落盘成功：

![23.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklwvdh205fikztxb8.png)

### 最终效果

Windows 主机浏览器直接打开 [http://127.0.0.1](http://127.0.0.1)，弹 Basic 认证框，输 guest:guest 进管理界面，菜单、状态页、配置保存全部可用：

![24.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklww91278lucpoewg.png)

![25.png](https://www.iotsec-zone.com/api/image/v2/20260811/dklwvwrt57fbxazqgv.png)

## 0x02 总结

1. 这类老 Realtek 方案 AP 是"补丁 boa + 单 CGI"架构，前端协议全在预 gzip 的 JS 里，zcat 后 grep 就能画出调用链。
2. CGI 段错误先用 strace -e trace=openat 看缺什么硬件文件；可写的假 flash 文件能让 writeDefault 修复。
3. binwalk 解压的 rootfs 常见四个坑：tmp->/dev/null 坏链接、/dev 设备节点全缺（boa 连 /dev/null 都打不开）、缺 /var/run（boa 写不了 PID 文件）、/dev/mtd 缺失（CGI 崩）。
