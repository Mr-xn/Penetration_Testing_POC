# Zyxel-NAS格式化字符串漏洞复现环境搭建
> 0431物联卫士实验室
> 来源：https://www.iotsec-zone.com/article/326

> Ubuntu虚拟机网络链接方式为“桥接”。

# 1、前言
在IoTsec-Zone社区的安全情报中看到了一个NAS的CVE（CVE-2022-34747），其漏洞类型是一直没有遇到过的格式化字符串漏洞，本篇文章我们先搭建一下环境。
![0.png](https://www.iotsec-zone.com/images/MdImg/914efa649b9a0bb922954f8e0d4c3801.png)
# 2、基本分析
访问Zyxel的Security-Advisories知道影响范围包含了型号NAS326、NAS540、NAS542：
> [https://www.zyxel.com/global/en/support/security-advisories/zyxel-security-advisory-for-format-string-vulnerability-in-nas](https://www.zyxel.com/global/en/support/security-advisories/zyxel-security-advisory-for-format-string-vulnerability-in-nas)

![1.png](https://www.iotsec-zone.com/images/MdImg/74b6021bed60caf9abe76f25a5a6b3ef.png)
该漏洞已经在该型号的最新版本固件V5.21(AAZF.12)C0中修复，查看最新版本的Release Note有如下这么两句轻描淡写的话：
![2.png](https://www.iotsec-zone.com/images/MdImg/b4ff2440e1025f4e645b8afe4817dd82.png)

对于NAS326来说，受影响的版本为V5.21(AAZF.11)C0以及之前，所以下载相应的包含漏洞的固件就好。这里我选择下载V5.21(AAZF.10)C0与最新版本V5.21(AAZF.12)C0（V5.21(AAZF.11)C0官网已经不让下载了）：
- https://download.zyxel.com/NAS326/firmware/NAS326_V5.21(AAZF.10)C0.zip【V5.21(AAZF.10)C0】
- https://download.zyxel.com/NAS326/firmware/NAS326_V5.21(AAZF.12)C0.zip【V5.21(AAZF.12)C0】
- 
对两个固件分别解压后使用BeyondCompare进行diff，如下图所示；噗，果然如更新日志说的那样，可执行文件nsuagent确实被删除了。

![3.png](https://www.iotsec-zone.com/images/MdImg/2aeb6cdff84e06683beeab75afef9901.png)
那么漏洞基本可以确定是出现在nsuagent上了，不然官方没有理由移除这个文件。既然是格式化字符串漏洞，那么我们可以使用IDA的LazyIDA插件辅助我们具体定位：
![4.png](https://www.iotsec-zone.com/images/MdImg/ae3f54d52518070be139acc54e2f2232.png)
![5.png](https://www.iotsec-zone.com/images/MdImg/d0b9c6457325d6e525b910fa261d4741.png)
双击点进去查看第一个fprintf：
![6.png](https://www.iotsec-zone.com/images/MdImg/7c538c71395ad9e504f05211416f9b46.png)
根据fprintf函数声明：int fprintf(FILE *stream, const char *format, ...)，那没跑了，如果fprintf的第二个参数s可以被控制，则可造成格式化字符串漏洞。这里需要注意，前面的vnsprintf并不存在格式化字符串漏洞，因为其格式化字符串为固定的，如："username: %s, password: %s\n"。
# 3、环境搭建
![7.png](https://www.iotsec-zone.com/images/MdImg/ad19212c5532064b1cc9a978e27749d2.png)
如果仔细看的话会发现，这两个文件系统包含的固件内容均不完整且恰好互补，所以想要顺利的模拟成功就需要手动将两个解压后的两个文件夹合并（合并后的文件夹我命名为了rootfs）。目标文件nsuagent为ARM架构，我仍然选择使用qemu-system模式进行模拟，命令如下：
```bash
# Ubuntu虚拟机--------------------------------------------------------------------------------
$ tar czf rootfs.tar.gz ./rootfs
$ sudo tunctl -t tap0
$ sudo ifconfig tap0 192.168.5.2/24
$ sudo qemu-system-arm -M vexpress-a9 -kernel vmlinuz-3.2.0-4-vexpress \
  -initrd initrd.img-3.2.0-4-vexpress \
  -drive if=sd,file=debian_wheezy_armhf_standard.qcow2 \
  -append "root=/dev/mmcblk0p2" -smp 2,cores=2 \
  -net nic -net tap,ifname=tap0,script=no,downscript=no -nographic
# qemu----------------------------------------------------------------------------------------
$ ifconfig eth0 192.168.5.1/24
# Ubuntu虚拟机--------------------------------------------------------------------------------
$ scp ./rootfs.tar.gz root@192.168.5.1:/root/
# qemu----------------------------------------------------------------------------------------
$ tar -zxvf ./rootfs.tar.gz
$ cd ./rootfs
$ chmod -R 777 ./*
$ cd ../
$ mount -o bind /dev ./rootfs/dev && mount -t proc /proc ./rootfs/proc
$ chroot ./rootfs sh
```
![8.png](https://www.iotsec-zone.com/images/MdImg/b56e21c3f23aaccff1251eca908f601c.png)
尝试直接运行/usr/sbin/nsuagent会出现报/usr/lib/libz.so.1: file too short的错误，如下图所示
![9.png](https://www.iotsec-zone.com/images/MdImg/72f2002a8f07421f6f8aecd5eea23dd5.png)
查看该动态链接库：
![10.png](https://www.iotsec-zone.com/images/MdImg/5eb5acf9b3a4e5112bc1081920b7daff.png)
寄！软链接在binwalk解压的时候好像出现了问题，其实它应该软链接到libz.so.1.2.8:
![11.png](https://www.iotsec-zone.com/images/MdImg/77739a18703644fb62445fec102218ea.png)
得，根据报错手动修复吧...
![12.png](https://www.iotsec-zone.com/images/MdImg/55b0129899a67df866fa333f9d2259d3.png)
所有需要修复的软链接如下：
```bash
$ rm ./libz.so.1
$ ln -s ./libz.so.1.2.8 ./libz.so.1
$ ls -al ./libz.so.1
lrwxrwxrwx 1 cyberangel cyberangel 15 11月 22 09:32 ./libz.so.1 -> ./libz.so.1.2.8
$ rm ./libsmbclient.so.0
$ ln -s ./libsmbclient.so.0.2.1 ./libsmbclient.so.0
$ rm ./libpam.so.0
$ ln -s ./libpam.so.0.83.1 ./libpam.so.0
$ rm ./libpthread.so.0           
$ ln -s ./libpthread-2.20-2014.11.so ./libpthread.so.0
$ rm ./libsamba-util.so.0
$ ln -s ./libsamba-util.so.0.0.1 ./libsamba-util.so.0
$ rm ./libtalloc.so.2
$ ln -s ./libtalloc.so.2.0.8 ./libtalloc.so.2
$ rm ./libndr.so.0
$ ln -s ./libndr.so.0.0.2 ./libndr.so.0
$ rm ./libndr-standard.so.0
$ ln -s ./libndr-standard.so.0.0.1 ./libndr-standard.so.0
$ rm ./libtevent.so.0
$ ln -s ./libtevent.so.0.9.18 ./libtevent.so.0
$ rm ./libwbclient.so.0
$ ln -s ./libwbclient.so.0.11 ./libwbclient.so.0
$ rm ./libsamba-credentials.so.0
$ ln -s ./libsamba-credentials.so.0.0.1 ./libsamba-credentials.so.0
$ rm ./libgensec.so.0
$ ln -s ./libgensec.so.0.0.1 ./libgensec.so.0
$ rm ./libsamba-hostconfig.so.0
$ ln -s ./libsamba-hostconfig.so.0.0.1 ./libsamba-hostconfig.so.0
$ rm ./libndr-nbt.so.0
$ ln -s ./libndr-nbt.so.0.0.1 ./libndr-nbt.so.0
$ rm ./libtevent-util.so.0
$ ln -s ./libtevent-util.so.0.0.1 ./ibtevent-util.so.0
$ rm ./ibtevent-util.so.0 
$ ln -s ./libtevent-util.so.0.0.1 ./libtevent-util.so.0
$ rm ./libcom_err.so.2
$ ln -s ./libcom_err.so.2.1 ./libcom_err.so.2
$ rm ./libdcerpc-binding.so.0
$ ln -s ./libdcerpc-binding.so.0.0.1 ./libdcerpc-binding.so.0
$ rm ./libtdb.so.1
$ ln -s ./libtdb.so.1.2.12 ./libtdb.so.1
$ rm ./libnsl.so.1
$ ln -s ./libnsl-2.20-2014.11.so ./libnsl.so.1
$ rm ./liblber-2.4.so.2
$ ln -s ./liblber-2.4.so.2.10.3 ./liblber-2.4.so.2
$ rm ./libldap-2.4.so.2
$ ln -s ./libldap-2.4.so.2.10.3 ./libldap-2.4.so.2
$ rm ./libkrb5-samba4.so.26
$ ln -s ./libkrb5-samba4.so.26.0.0 ./libkrb5-samba4.so.26
$ rm ./libgssapi-samba4.so.2
$ ln -s ./libgssapi-samba4.so.2.0.0 ./libgssapi-samba4.so.2
$ rm ./libldb.so.1
$ ln -s ./libldb.so.1.1.16 ./libldb.so.1
$ rm ./libasn1-samba4.so.8
$ ln -s ./libasn1-samba4.so.8.0.0 ./libasn1-samba4.so.8
$ rm ./libsamdb.so.0
$ ln -s ./libsamdb.so.0.0.1 ./libsamdb.so.0
$ rm ./libntdb.so.0
$ ln -s ./libntdb.so.0.9 ./libntdb.so.0
$ rm ./libattr.so.1
$ ln -s ./libattr.so.1.1.0 ./libattr.so.1
$ rm ./libresolv.so.2
$ ln -s ./libresolv-2.20-2014.11.so ./libresolv.so.2
$ rm ./libheimbase-samba4.so.1
$ ln -s ./libheimbase-samba4.so.1.0.0 ./libheimbase-samba4.so.1 
$ rm ./libroken-samba4.so.19
$ ln -s ./libroken-samba4.so.19.0.1 ./libroken-samba4.so.19
$ rm ./libhx509-samba4.so.5
$ ln -s ./libhx509-samba4.so.5.0.0 ./libhx509-samba4.so.5
$ rm ./libhcrypto-samba4.so.5
$ ln -s ./libhcrypto-samba4.so.5.0.1 ./libhcrypto-samba4.so.5
$ rm ./libwind-samba4.so.0
$ ln -s ./libwind-samba4.so.0.0.0 ./libwind-samba4.so.0
$ rm ./libndr-krb5pac.so.0
$ ln -s ./libndr-krb5pac.so.0.0.1 ./libndr-krb5pac.so.0
$ rm ./libgnutls.so.28
$ ln -s ./libgnutls.so.28.41.4 ./libgnutls.so.28
$ rm ./libgcrypt.so.20
$ ln -s ./libgcrypt.so.20.0.3 ./libgcrypt.so.20
$ rm ./libpcre.so.1
$ ln -s ./libpcre.so.1.2.4 ./libpcre.so.1
$ rm ./libnettle.so.4
$ ln -s ./libnettle.so.4.7 ./libnettle.so.4
$ rm ./libhogweed.so.2
$ ln -s ./libhogweed.so.2.5 ./libhogweed.so.2
$ rm ./libgmp.so.10
$ ln -s ./libgmp.so.10.2.0 ./libgmp.so.10
$ rm ./libpcreposix.so.0
$ ln -s ./libpcreposix.so.0.0.3 ./libpcreposix.so.0
$ rm ./libgpg-error.so.0
$ ln -s ./libgpg-error.so.0.10.0 ./libgpg-error.so.0
```
再次尝试运行：
![13.png](https://www.iotsec-zone.com/images/MdImg/f21ef0a49c743e4fdb6c0df54bab36f1.png)
emmm，程序没有任何输出。IDA逆向后发现main函数调用了daemon，导致程序启动后转入了后台运行，故我们无法查看它的状态：
![14.png](https://www.iotsec-zone.com/images/MdImg/80d963bd3667e6218a9cdbcefa750e54.png)
解决方式也很简单，nop掉main的daemon函数就可以了：
![15.png](https://www.iotsec-zone.com/images/MdImg/c9ce90afda9f28397c258b1e9fbc3f43.png)
保存导出后替换原来的nsuagent文件，再次启动却发现还是会报错：
![16.png](https://www.iotsec-zone.com/images/MdImg/764be5e6e8a15cb4e33103bd0ff105f4.png)
如上图所示，nsuagent在执行的过程中会调用脚本文件/bin/nsa400getconfig.sh，交叉引用后可以得到调用链：main -> sub_19A80 -> sub_17550：
![17.png](https://www.iotsec-zone.com/images/MdImg/97d10322d4a3640d1cab45537ae5b27e.png)
popen执行脚本后会将结果返回给v4，然后调用fread函数将结果读取到ptr中，之后程序可能会根据这个返回内容进行处理与判断。所以这个脚本关系着环境搭建的成功与否，下面我们将注意力集中到这个脚本（代码如下面代码框所示），仔细观察会发现程序的所有报错基本上都是由它引起的：
```bash
#!/bin/sh

IFCONFIG="busybox ifconfig"
ROUTE="busybox route"
AWK="/bin/awk"
CUT="/bin/cut"
GREP="/bin/grep"
CAT="/bin/cat"
HOSTNAME="/bin/hostname"
FIRMWARE_INFO_PATH=`cat /etc/settings/firmware_info_path`"/mnt/info/fwversion"
WebPort=`${CAT} /etc/service_conf/httpd_zld.conf | grep Listen | cut -d " " -f2 | sed -n '1p'`

BOND_NAME="bond0"

ETH1_NAME="egiga0"
IP1=""
MASK1=""
GATEWAY1=""
DHCP1=""

ETH2_NAME="egiga1"
IP2=""
MASK2=""
GATEWAY2=""
DHCP2=""

Bond0_linked=`cat /sys/class/net/bond0/carrier`
if [ "${Bond0_linked}" == "1" ]; then 
	BondingON="yes"
else
	BondingON="no"
fi

if [ "${BondingON}" == "yes" ]; then #Bonding on
	IP1=`${IFCONFIG} bond0 | ${GREP} "inet addr" | ${CUT} -d: -f2 | ${CUT} -d" " -f1`
	MASK1=`${IFCONFIG} bond0 | ${GREP} "inet addr" | ${CUT} -d: -f4`
	GATEWAY1=`${ROUTE} -n | ${GREP} bond0 | ${AWK} '$1 == "0.0.0.0" {print $2}'`
	DHCP1=`ps | ${GREP} dhcp | ${GREP} bond0`
	METRIC1=5;
	if [ "${DHCP1}" == "" ]; then
		DHCP1="static"
	else
		DHCP1="dhcp"
	fi

	BondingMode=`${CAT} /sys/class/net/bond0 | ${GREP} "active-backup"`

	if [ "${BondingMode}" == "" ]; then
		BondingMode=`${CAT} /sys/class/net/bond0 | ${GREP} "balancing"`
		if [ "${BondingMode}" == "" ]; then
			BondingMode="link-aggregation"
		else
			BondingMode="adaptive-load-balancing"
		fi
	else
		BondingMode="active-backup"
	fi
else
	#checks if egiga0 is up and linked
	egiga0_link=`${CAT} /sys/class/net/${ETH1_NAME}/carrier`
	if [ ${egiga0_link} -eq 1 ]; then
		IP1=`${IFCONFIG} ${ETH1_NAME} | ${GREP} "inet addr" | ${CUT} -d: -f2 | ${CUT} -d" " -f1`
		MASK1=`${IFCONFIG} ${ETH1_NAME} | ${GREP} "inet addr" | ${CUT} -d: -f4`
		GATEWAY1=`${ROUTE} -n| ${GREP} ${ETH1_NAME} | ${AWK} '$1 == "0.0.0.0" {print $2}'`
		#METRIC1=`${ROUTE} -n | ${GREP} ${ETH1_NAME} | ${AWK} '$1 == "0.0.0.0" {print $5}'`
	else
		IP1="0.0.0.0"
		MASK1="0.0.0.0"
		GATEWAY1="0.0.0.0"
		METRIC1=20
	fi
	DHCP1=`ps | ${GREP} dhcpcd_request | ${GREP} ${ETH1_NAME}`
	if [ "${DHCP1}" == "" ]; then
		DHCP1="static"
	else
		DHCP1="dhcp"
	fi

	#checks if egiga1 is up and linked
	if [ -e "/sys/class/net/${ETH2_NAME}" ]; then
		egiga1_link=`${CAT} /sys/class/net/${ETH2_NAME}/carrier`
		if [ ${egiga1_link} -eq 1 ]; then
			IP2=`${IFCONFIG} ${ETH2_NAME} | ${GREP} "inet addr" | ${CUT} -d: -f2 | ${CUT} -d" " -f1`
			MASK2=`${IFCONFIG} ${ETH2_NAME} | ${GREP} "inet addr" | ${CUT} -d: -f4`
			GATEWAY2=`${ROUTE} -n| ${GREP} ${ETH2_NAME} | ${AWK} '$1 == "0.0.0.0" {print $2}'`
			#METRIC2=`${ROUTE} -n | ${GREP} ${ETH2_NAME}| ${AWK} '$1 == "0.0.0.0" {print $5}'`
		else
			IP2="0.0.0.0"
			MASK2="0.0.0.0"
			GATEWAY2="0.0.0.0"
			METRIC2=22
		fi
		DHCP2=`ps | ${GREP} dhcpcd_request | ${GREP} ${ETH2_NAME}`
		if [ "${DHCP2}" == "" ]; then
			DHCP2="static"
		else
			DHCP2="dhcp"
		fi
	fi
fi

#The firmare later that 5.10 doesn't rely on the metric value to determine which interface is the default value. But the NSU Client have to be compatible with the older models and firmware, the gateway of which is indicated by the metric value.
default_gateway=`/usr/bin/python -c "from lib import config_api; pyconf = config_api.ConfigOperator(); print pyconf.get_conf_value('network.interface', 'default_gateway')"`
if [ "${default_gateway}" == "${ETH2_NAME}" ]; then
	METRIC1=7
	METRIC2=5
else
	METRIC1=5
	METRIC2=7
fi

Hostname=`${HOSTNAME}`
Modelname=`${CAT} /etc/modelname`

FwVersion=`${CAT} ${FIRMWARE_INFO_PATH}`

DNS_FETCH=`/usr/bin/python -c "from lib import config_api; pyconf = config_api.ConfigOperator(); print pyconf.get_conf_value('network.interface.nameserver', 'fetch')"`
if [ "${DNS_FETCH}" == "manually" ]; then
	AutoDNS="no"
else
	AutoDNS="yes"
fi

PRIDNS=`${CAT} /etc/resolv.conf | ${AWK} '/nameserver/ {print $2}' | sed -n '1p'`
SECDNS=`${CAT} /etc/resolv.conf | ${AWK} '/nameserver/ {print $2}' | sed -n '2p'`

MAC1=`${IFCONFIG} ${ETH1_NAME} | ${GREP} HWaddr | tr -s ' ' | ${CUT} -d ' '  -f5`
if [ -e "/sys/class/net/${ETH2_NAME}" ]; then
	MAC2=`${IFCONFIG} ${ETH2_NAME} | ${GREP} HWaddr | tr -s ' ' | ${CUT} -d ' '  -f5`
fi

NasID=${MAC1}

PPPoE_Enable=`ps | grep pppoe | grep -v "grep"`
if [ "${PPPoE_Enable}" == "" ]; then
	PPPoE_Enable="no"
else
	PPPoE_Enable="yes"
fi

if [ ${PPPoE_Enable} == "yes" ]; then
	PPPoE_IP=`${IFCONFIG} ppp0 | ${GREP} "inet addr" | ${CUT} -d: -f2 | ${CUT} -d" " -f1`
	PPPoE_MASK=`${IFCONFIG} ppp0 | ${GREP} "Mask" | ${CUT} -d: -f4`
	PPPoE_DNS=`${CAT} /etc/ppp/resolv.conf | ${AWK} '/nameserver/ {print $2}' | sed -n '1p'`
	PPPoE_UserID=`/usr/bin/python -c "from lib import config_api; pyconf = config_api.ConfigOperator(); print pyconf.get_conf_value('network.interface.ppp0', 'account')"`
	PPPoE_PassWd=`/usr/bin/python -c "from lib import config_api; pyconf = config_api.ConfigOperator(); print pyconf.get_conf_value('network.interface.ppp0', 'password')"`
fi

TIME_ZONE=`python -c "from models import date_time_main_model; print date_time_main_model.getTimeZone_for_nsu()"`

if [ "${IP1}" == "" ]; then
	IP1="0.0.0.0"
fi

if [ "${MASK1}" == "" ]; then
	MASK1="0.0.0.0"
fi

if [ "${GATEWAY1}" == "" ]; then
	GATEWAY1="0.0.0.0"
fi

if [ -e "/sys/class/net/${ETH2_NAME}" ]; then
	[ "${IP2}" == "" ] && IP2="0.0.0.0"
	[ "${MASK2}" == "" ] && MASK2="0.0.0.0"
	[ "${GATEWAY2}" == "" ] && GATEWAY2="0.0.0.0"
fi

if [ "${PPPoE_IP}" == "" ]; then
	PPPoE_IP="0.0.0.0"
fi

if [ "${PPPoE_MASK}" == "" ]; then
	PPPoE_MASK="0.0.0.0"
fi

if [ "${PPPoE_DNS}" == "" ]; then
	PPPoE_DNS="0.0.0.0"
fi

echo "IP type1: ${DHCP1}"
echo "IP address1: ${IP1}"
echo "netmask1: ${MASK1}"
echo "gateway1: ${GATEWAY1}"
echo "MAC address1: ${MAC1}"
echo "metric1: ${METRIC1}"

if [ "${BondingON}" == "no" ]; then
	if [ -e "/sys/class/net/${ETH2_NAME}" ]; then
		echo "IP type2: ${DHCP2}"
		echo "IP address2: ${IP2}"
		echo "netmask2: ${MASK2}"
		echo "gateway2: ${GATEWAY2}"
		echo "MAC address2: ${MAC2}"
		echo "metric2: ${METRIC2}"
	fi
fi

echo "hostname: ${Hostname}"
echo "autoDNS: ${AutoDNS}"
echo "name-server-1: ${PRIDNS}"
echo "name-server-2: ${SECDNS}"
echo "model name: ${Modelname}"
echo "fwversion: ${FwVersion}"
echo "WebGUIPort: ${WebPort}"
echo "NAS_ID: ${NasID}"
echo "Bonding Driver Setting:"
echo "  activate: ${BondingON}"
echo "  mode: ${BondingMode}"
echo "PPPoE_Enable: ${PPPoE_Enable}"
echo "PPPoE_IP: ${PPPoE_IP}"
echo "PPPoE_Mask: ${PPPoE_MASK}"
echo "PPPoE_DNS: ${PPPoE_DNS}"
echo "PPPoE_UserID: ${PPPoE_UserID}"
echo "PPPoE_PassWd: ${PPPoE_PassWd}"
echo "Time_Zone: ${TIME_ZONE}"

# get the total and used size for all volume
USED_TOTAL_SIZE=`python -c "from models import storage_main; print storage_main.MainGetAllVolSizUsed_Total()"`

# total volume size (in KB)
TOTAL_SIZE=`echo ${USED_TOTAL_SIZE} | awk -F"/" '{print $2}'`
echo "totalVolSize: ${TOTAL_SIZE}"

# total used volume size (in KB)
TOTAL_USED=`echo ${USED_TOTAL_SIZE} | awk -F"/" '{print $1}'`
echo "totalUsedSize: ${TOTAL_USED}"

# FTP port ("" means no FTP is listening now)
echo "ftpPort: `cat /var/zyxel/pure-ftpd.arg | cut -d "S" -f2 | cut -d" " -f2`"

shotID=0
hdAmount=0
sdx_array="`ls -d /sys/block/sd? | awk -F "/" '{print $4}'`"

for sdx in ${sdx_array}
do
	[ "`/sbin/intern_disk_chker -c ${sdx}`" != "yes" ] && continue

	hdAmount=$((${hdAmount}+1))
	DISK_SIZE_SECTOR=`cat /sys/block/${sdx}/size`
	DISK_SIZE_K=$((${DISK_SIZE_SECTOR}/2))

	shotID=`cat "/tmp/intern_disk.map" | grep ${sdx} | cut -c 5`
	echo "DISK${shotID}_SIZE: ${DISK_SIZE_K}"
done

# HD amount
echo "hdAmount: ${hdAmount}"

# md status
cd /i-data/sysvol
if [ "$?" != "0" ]; then
	echo "raidType:"
else
	# NOTE:
	#       this raid type is fake now! just used to determine if raid
	#       available now
	echo "raidType: JBOD"
fi

# revision
echo "revision: `cat /firmware/mnt/info/revision`"

# customer
echo "customer: ZyXEL"

# installed packages
#/usr/bin/ipkg-cl -f /etc/zyxel/pkg_conf/zypkg_conf/zy-pkg.conf -t /i-data/.system/zy-pkgs/tmp list | grep -A4 "^pkgName" > /tmp/all.lst
#PKGS="`cat /tmp/all.lst | grep -v "version:" | grep -v "description:" | grep -v "URL:"|grep -B2 -E "(Built-in)|(Enable)" | grep "pkgName" | awk -F' ' '{print $2}'`"
#echo "pkgInstalled: `echo "${PKGS}" | tr '\n' ';'`"

#because the v5.2 move the admin page to desktop, remove the shortcut for NSU
echo "pkgInstalled: "

exit 0
```
单独执行/bin/nsa400getconfig.sh，有如下日志：
```bash
/ # /bin/nsa400getconfig.sh
cat: can't open '/sys/class/net/bond0/carrier': No such file or directory
cat: can't open '/sys/class/net/egiga0/carrier': No such file or directory
sh: 1: unknown operand
cat: can't open '/firmware/mnt/info/fwversion': No such file or directory
ifconfig: egiga0: error fetching interface information: Device not found
IP type1: static
IP address1: 0.0.0.0
netmask1: 0.0.0.0
gateway1: 0.0.0.0
MAC address1: 
metric1: 5
hostname: debian-armhf
autoDNS: yes
name-server-1: 192.168.1.1
name-server-2: 
model name: NAS326
fwversion: 
WebGUIPort: 80
NAS_ID: 
Bonding Driver Setting:
  activate: no
  mode: 
PPPoE_Enable: no
PPPoE_IP: 0.0.0.0
PPPoE_Mask: 0.0.0.0
PPPoE_DNS: 0.0.0.0
PPPoE_UserID: 
PPPoE_PassWd: 
Time_Zone: 
totalVolSize: 
totalUsedSize: 
cat: can't open '/var/zyxel/pure-ftpd.arg': No such file or directory
ftpPort: 
ls: /sys/block/sd?: No such file or directory
hdAmount: 0
/bin/nsa400getconfig.sh: cd: line 255: can't cd to /i-data/sysvol
raidType:
cat: can't open '/firmware/mnt/info/revision': No such file or directory
revision: 
customer: ZyXEL
pkgInstalled: 
/ # 
```
看来报错还真的不少，我们一个一个来解决吧。前两个有关于网卡的报错都和sys有关：
- cat: can't open '/sys/class/net/bond0/carrier': No such file or directory，这里暂时先忽略。
- cat: can't open '/sys/class/net/egiga0/carrier': No such file or directory
我们退出shell去挂载一下：mount -vt sysfs sysfs ./rootfs/sys
![18.png](https://www.iotsec-zone.com/images/MdImg/25b5a78de1822d4ea838eee294a64c9a.png)

因为我们的qemu网卡是eth0，所以将脚本中的ETH1_NAME="egiga0"更改为ETH1_NAME="eth0"，再次执行就可以正常的获取网卡信息了：
![19.png](https://www.iotsec-zone.com/images/MdImg/50b1e04dfface3f8b1d83a056f022ee6.png)
针对其他报错的处理方式不再详细说明，我都写在下面了：

- cat: can't open '/firmware/mnt/info/fwversion': No such file or directory
 	- mkdir -p /firmware/mnt/info/
 	- 随便写一个就好：echo "NAS326" > /firmware/mnt/info/fwversion
- can't open '/var/zyxel/pure-ftpd.arg': No such file or directory：
	- 通常来说ftp的端口默认为21：echo 21 > /var/zyxel/pure-ftpd.arg
- can't cd to /i-data/sysvol：
	- mkdir -p /i-data/sysvol
- can't open '/firmware/mnt/info/revision': No such file or directory：
	- 随便写一个就好：echo 0 > /firmware/mnt/info/revision
- ls: /sys/block/sd?: No such file or directory：看名字可能与NAS的存储有关，这里暂不处理。

再次启动nsuagent，端口为50127的UDP：
![20.png](https://www.iotsec-zone.com/images/MdImg/c170045728596bebff1b9c34f88eb4d3.png)
![21.png](https://www.iotsec-zone.com/images/MdImg/370ce793ec2729caa92b2df465a9b15d.png)
emmm，看起来像是成功了，但是我觉得还没有模拟完全？提出这个问题的原因是我注意到脚本中还调用了python（/usr/bin/python -c [...]），可是python起不来啊：
![22.png](https://www.iotsec-zone.com/images/MdImg/b0c24b16e9dffda64ac4c92133e68da7.png)
使用strace跟踪一下系统调用看看？
![23.png](https://www.iotsec-zone.com/images/MdImg/d258c73932a9ac2bc02ccf2d0e711799.png)
Exec format error，我去，我才反应过来是软链接的问题：
![24.png](https://www.iotsec-zone.com/images/MdImg/3f1caeaebfa96d94ba675a6b4af221e0.png)
将python与python2这两个软连接修复完成之后，还需要修复如下软链接：
- ln -s /usr/lib/libutil-2.20-2014.11.so /usr/lib/libutil.so.1
- ln -s /usr/lib/libsqlite3.so.0.8.6 /usr/lib/libsqlite3.so.0

再次执行nsa400getconfig.sh，仍需我们进一步处理报错：
![25.png](https://www.iotsec-zone.com/images/MdImg/a36ea5844c8b60b8c2dbb472258d4714.png)
看来是python代码出错了，根据nsa400getconfig.sh的内容确定一下：
![26.png](https://www.iotsec-zone.com/images/MdImg/e4aecfa18d73e3c69590c8c87dc91a0f.png)
![27.png](https://www.iotsec-zone.com/images/MdImg/1b3c85d5dd995cd2d0125105b656d86e.png)
对于此固件来说，所有的python脚本均以编译后的pyc文件形式存在，要想查看它的代码只需要使用uncompyle6进行反编译即可（pip install uncompyle6）。对uncompyle6 date_time_main_model.pyc反编译后的结果如下：
```python
# uncompyle6 version 3.8.0
# Python bytecode 2.7 (62211)
# Decompiled from: Python 2.7.17 (default, Jul  1 2022, 15:56:32) 
# [GCC 7.5.0]
# Warning: this version of Python has problems handling the Python 3 byte type in constants properly.

# Embedded file name: /home/release-build/NAS326/521AAZF10B2/sysapps/web_framework/build/models/date_time_main_model.py.pre
# Compiled at: 2021-04-01 10:00:23
"""This model offers all relative functions about date_time.
"""
from lib import config_api, tools
import shlex, re, subprocess, os, time
from re import sub as re_sub
from time import sleep
import datetime
from datetime import date
from calendar import Calendar
from time import gmtime, strftime
from models.system_main_model import write_pyconf
pyconf = config_api.ConfigOperator()
DATE_TIME_PYCONF_PATH = 'system.date_time'
GET_TIME = 'date +%T'
GET_DATE = 'date +%x'
GET_TIME_S = 'date +%s'
PATH_DATE = '/bin/date'
NTPDATE_AGENT = '/usr/sbin/ntpdate_agent'
UPDATE_SCHEDULE_JOB = '/usr/bin/restart_scheduler.sh > /dev/null 2>&1 &'
YEAR_LIMIT = 2038
SYS_TO_RTC = '/sbin/rtcAccess systortc'
PATH_AUTO_DST = '/usr/sbin/dst.sh'
DST_FILE_PATH = '/i-data/.system/zoneinfo/'
ZONE_RULE_FILE = '/var/zyxel/myzone_rule'
PATH_ZIC = '/usr/sbin/zic'
ZONE_FORMAT_FILE = '/etc/MyZone'
LOCALTIME_TIME_PATH = '/etc/localtime'
MONTH_LIST = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
TIMEZONE_DICT = {'-12:00': 'Eniwetok,Kwajalein', '-11:00': 'Midway Island,Samoa', '-10:00': 'Hawaii', '-09:00': 'Alaska', '-08:00': 'Pacific Time (US & Canada)', '-07:00': 'Mountain Time (US & Canada)', '-06:00': 'Central America', 
   '-05:00': 'Indiana(East)', '-04:30': 'Caracas', '-04:00': 'Atlantic Time (Canada)', '-03:30': 'Newfoundland', '-03:00': 'Brasilia', '-02:00': 'Mid-Atlantic', '-01:00': 'Azores', 
   '+00:00': 'Casablanca', '+01:00': 'Central,West Africa', '+02:00': 'Amman', '+03:00': 'Baghdad', '+03:30': 'Tehran', '+04:00': 'Moscow,Saint Petersburg,Volgograd', '+04:30': 'Kabul', 
   '+05:00': 'Ekaterinburg', '+05:30': 'Chennai,Kolkata,Mumbai,New Delhi', '+05:45': 'Kathmandu', '+06:00': 'Yekaterinburg', '+06:30': 'Yangon (Rangoon)', '+07:00': 'Omsk', '+08:00': 'Taipei', 
   '+09:00': 'Irkutsk', '+09:30': 'Adelaide', '+10:00': 'Brisbane', '+11:00': 'Vladivostok', '+12:00': 'Magadan', '+13:00': "Nuku'alofa"}

def get_date_time_pyconf(key):
    return pyconf.get_conf_value(DATE_TIME_PYCONF_PATH, key)

def get_time():
    psPopen = subprocess.Popen(GET_TIME, shell=True, close_fds=True, stdin=None, stdout=subprocess.PIPE, stderr=None)
    time = psPopen.stdout.read().strip('\r\n')
    return {'current_time': time}

def get_date():
    psPopen = subprocess.Popen(GET_DATE, shell=True, close_fds=True, stdin=None, stdout=subprocess.PIPE, stderr=None)
    date = psPopen.stdout.read().strip('\r\n')
    date = re.split('/', date)
    year = date[2]
    mon = date[0]
    day = date[1]
    date = '20%s-%s-%s' % (year, mon, day)
    return {'current_date': date}

def set_date_time(date, time):
    date = re.split('/', date)
    year = date[2]
    mon = date[0]
    day = date[1]
    if int(year) >= YEAR_LIMIT:
        return 'year error'
    date = '%s%s0000%s' % (mon, day, year)
    cmd = '%s %s' % (PATH_DATE, date)
    cmd_set = shlex.split(cmd)
    tools.execRoot(cmd_set)
    cmd = '%s %s' % (PATH_DATE, time)
    cmd_set = shlex.split(cmd)
    tools.execRoot(cmd_set)
    cmd = '%s' % SYS_TO_RTC
    cmd_set = shlex.split(cmd)
    tools.execRoot(cmd_set)
    return 'Success'

def get_ntpstatus():
    active = get_date_time_pyconf('NTP_active')
    server = get_date_time_pyconf('NTP_server')
    last_update_time = get_date_time_pyconf('NTP_last_update_time')
    NTP_result = {'NTP_active': active, 'NTP_server': server, 'NTP_last_update_time': last_update_time}
    return {'ntp_status': NTP_result}

def set_ntpserver(ntpserver):
    pyconf.modify_conf_value(DATE_TIME_PYCONF_PATH, 'NTP_server', ntpserver)
    return 'Success'

def ntpsync(ntpserver):
    pyconf.modify_conf_value(DATE_TIME_PYCONF_PATH, 'timeServerActive', 'true')
    pyconf.modify_conf_value(DATE_TIME_PYCONF_PATH, 'timeServerAddr', ntpserver)
    cmd = '%s %s &' % (NTPDATE_AGENT, ntpserver)
    cmd_set = shlex.split(cmd)
    tools.execRoot(cmd_set)
    cmd = '%s' % SYS_TO_RTC
    cmd_set = shlex.split(cmd)
    tools.execRoot(cmd_set)
    return 'Success'

def disablentp():
    pyconf.modify_conf_value(DATE_TIME_PYCONF_PATH, 'NTP_active', 'no')
    return 'Success'

def migrate_clock_saving_interval(clock_interval):
    startMon = re.search('begin (\\w+)', clock_interval)
    begin_tmp = 'begin ' + startMon.group(1)
    startOrd = re.search(begin_tmp + ' (\\w+)', clock_interval)
    begin_tmp = begin_tmp + ' ' + startOrd.group(1)
    startWeek = re.search(begin_tmp + ' (\\w+)', clock_interval)
    begin_tmp = begin_tmp + ' ' + startWeek.group(1)
    startHour = re.search(begin_tmp + ' (\\w+)', clock_interval)
    begin_tmp = begin_tmp + ' ' + startHour.group(1)
    startMin = re.search(begin_tmp + ':(\\w+)', clock_interval)
    startMon = startMon.group(1)
    startMon = startMon[0].upper() + startMon[1:]
    startWeek = startWeek.group(1)
    startWeek = startWeek[0].upper() + startWeek[1:]
    pyconf.modify_conf_value(DATE_TIME_PYCONF_PATH, 'startMon', startMon)
    pyconf.modify_conf_value(DATE_TIME_PYCONF_PATH, 'startOrd', startOrd.group(1))
    pyconf.modify_conf_value(DATE_TIME_PYCONF_PATH, 'startWeek', startWeek)
    pyconf.modify_conf_value(DATE_TIME_PYCONF_PATH, 'startHour', startHour.group(1))
    pyconf.modify_conf_value(DATE_TIME_PYCONF_PATH, 'startMin', startMin.group(1))
    endMon = re.search('end (\\w+)', clock_interval)
    begin_tmp = 'end ' + endMon.group(1)
    endOrd = re.search(begin_tmp + ' (\\w+)', clock_interval)
    begin_tmp = begin_tmp + ' ' + endOrd.group(1)
    endWeek = re.search(begin_tmp + ' (\\w+)', clock_interval)
    begin_tmp = begin_tmp + ' ' + endWeek.group(1)
    endHour = re.search(begin_tmp + ' (\\w+)', clock_interval)
    begin_tmp = begin_tmp + ' ' + endHour.group(1)
    endMin = re.search(begin_tmp + ':(\\w+)', clock_interval)
    begin_tmp = begin_tmp + ':' + endMin.group(1) + ' '
    offset = re.split(begin_tmp, clock_interval)
    endMon = endMon.group(1)
    endMon = endMon[0].upper() + endMon[1:]
    endWeek = endWeek.group(1)
    endWeek = endWeek[0].upper() + endWeek[1:]
    pyconf.modify_conf_value(DATE_TIME_PYCONF_PATH, 'endMon', endMon)
    pyconf.modify_conf_value(DATE_TIME_PYCONF_PATH, 'endOrd', endOrd.group(1))
    pyconf.modify_conf_value(DATE_TIME_PYCONF_PATH, 'endWeek', endWeek)
    pyconf.modify_conf_value(DATE_TIME_PYCONF_PATH, 'endHour', endHour.group(1))
    pyconf.modify_conf_value(DATE_TIME_PYCONF_PATH, 'endMin', endMin.group(1))
    pyconf.modify_conf_value(DATE_TIME_PYCONF_PATH, 'offset', offset[1].strip('\r\n'))
    return 'Success'

def parse_date_time_conf(zysh_conf):
    is_ntp_active = 0
    zyconf_ntp_server = ''
    zyconf_auto_daylight_active = ''
    zyconf_clock_saving_interval = ''
    zyconf_clock_time_zone = ''
    try:
        with open(zysh_conf, 'r') as (r_file):
            for line in r_file:
                if 'ntp server' in line:
                    zyconf_ntp_server = line
                    name = line.strip('ntp ')
                    name = name.strip('server ')
                    pyconf.modify_conf_value(DATE_TIME_PYCONF_PATH, 'timeServerAddr', name.strip('\r\n'))
                if 'clock time-zone' in line:
                    zyconf_clock_time_zone = line
                if 'clock saving-interval' in line:
                    zyconf_clock_saving_interval = line
                    if migrate_clock_saving_interval(zyconf_clock_saving_interval) != 'Success':
                        print 'migrate_clock_saving_interval error'
                if 'clock daylight-saving' in line:
                    pyconf.modify_conf_value(DATE_TIME_PYCONF_PATH, 'daylightSaving', 'true')
                if 'daylight_saving start' in line:
                    zyconf_auto_daylight_active = line
                    area_path = re.search('daylight_saving start "(\\w+)', zyconf_auto_daylight_active)
                    city_path = re.search('in "(\\w+)', zyconf_auto_daylight_active)
                    if area_path:
                        daylight_path = area_path.group(1) + '/' + city_path.group(1)
                        DST_check_path = DST_FILE_PATH + daylight_path
                        if not os.path.exists(DST_check_path):
                            daylight_path = area_path.group(1)
                        pyconf.modify_conf_value(DATE_TIME_PYCONF_PATH, 'autoDaylightType', daylight_path)
                        pyconf.modify_conf_value(DATE_TIME_PYCONF_PATH, 'daylightSaving', 'true')
                        pyconf.modify_conf_value(DATE_TIME_PYCONF_PATH, 'autoDaylightStatus', 'true')
                    if zyconf_clock_time_zone:
                        time_zone = re.split('clock time-zone ', zyconf_clock_time_zone)
                        time_zone = time_zone[1]
                        time_zone = time_zone[:3] + ':' + time_zone[3:]
                        if city_path.group(1).strip('\r\n') == 'NULL':
                            city = TIMEZONE_DICT[time_zone.strip('\r\n')]
                        else:
                            city = city_path.group(1).strip('\r\n')
                        timezoneCountry = '%s/%s' % (time_zone.strip('\r\n'), city)
                        pyconf.modify_conf_value(DATE_TIME_PYCONF_PATH, 'timezoneCountry', timezoneCountry)
                    break

            with open(zysh_conf, 'r') as (r_file):
                conf = r_file.read()
                if zyconf_ntp_server:
                    zyconf_ntp_server = '!\r\n' + zyconf_ntp_server
                    conf = re_sub(zyconf_ntp_server, '', conf)
                conf = re_sub('clock time-zone \\W\\d\\d\\d\\d', '', conf)
                conf = re_sub('clock daylight-saving', '', conf)
                if zyconf_auto_daylight_active:
                    zyconf_auto_daylight_active = '!\r\n' + zyconf_auto_daylight_active
                    conf = re_sub(zyconf_auto_daylight_active, '', conf)
                conf = re_sub(zyconf_clock_saving_interval, '', conf)
            with open(zysh_conf, 'w') as (w_file):
                w_file.write(conf)
    except IOError:
        pass

    try:
        with open(zysh_conf, 'r') as (r_file):
            for line in r_file:
                if 'ntp' in line:
                    is_ntp_active = 1
                    break

        if is_ntp_active == 0:
            pyconf.modify_conf_value(DATE_TIME_PYCONF_PATH, 'NTP_active', 'no')
        if is_ntp_active == 1:
            with open(zysh_conf, 'r') as (r_file):
                conf = r_file.read()
                conf = re_sub('!\r\nntp', '', conf)
            with open(zysh_conf, 'w') as (w_file):
                w_file.write(conf)
    except IOError:
        pass

def getDateTimeStatus():
    psPopen = subprocess.Popen(PATH_DATE, shell=True, close_fds=True, stdin=None, stdout=subprocess.PIPE, stderr=None)
    time = psPopen.stdout.read().strip('\r\n')
    today = re.split(' ', str(time))
    psPopen = subprocess.Popen(GET_TIME, shell=True, close_fds=True, stdin=None, stdout=subprocess.PIPE, stderr=None)
    time = psPopen.stdout.read().strip('\r\n')
    if today[2]:
        current_time = '%s %s, %s %s' % (today[1], today[2], date.today().year, time)
    else:
        current_time = '%s %s, %s %s' % (today[1], today[3], date.today().year, time)
    timeServerActive = get_date_time_pyconf('timeServerActive')
    timeServerAddr = get_date_time_pyconf('timeServerAddr')
    timezoneCountry = get_date_time_pyconf('timezoneCountry')
    daylightSaving = get_date_time_pyconf('daylightSaving')
    autoDaylightStatus = get_date_time_pyconf('autoDaylightStatus')
    autoDaylightType = get_date_time_pyconf('autoDaylightType')
    startMon = get_date_time_pyconf('startMon')
    startOrd = get_date_time_pyconf('startOrd')
    startWeek = get_date_time_pyconf('startWeek')
    startHour = get_date_time_pyconf('startHour')
    startMin = get_date_time_pyconf('startMin')
    endMon = get_date_time_pyconf('endMon')
    endOrd = get_date_time_pyconf('endOrd')
    endWeek = get_date_time_pyconf('endWeek')
    endHour = get_date_time_pyconf('endHour')
    offset = get_date_time_pyconf('offset')
    endMin = get_date_time_pyconf('endMin')
    date_time_result = {'currentTime': current_time, 'timeServerActive': timeServerActive, 'timeServerAddr': timeServerAddr, 'timezoneCountry': timezoneCountry, 
       'daylightSaving': daylightSaving, 'autoDaylightStatus': autoDaylightStatus, 'autoDaylightType': autoDaylightType, 
       'startMon': startMon, 'startOrd': startOrd, 'startWeek': startWeek, 'startHour': startHour, 'startMin': startMin, 
       'endMon': endMon, 'endOrd': endOrd, 'endWeek': endWeek, 'endHour': endHour, 'endMin': endMin, 'offset': offset}
    return date_time_result

def setTime(time_s):
    today = re.split(' ', str(time_s))
    time = today[4]
    if MONTH_LIST.index(today[1]) + 1 < 10:
        set_date = '0%s' % (MONTH_LIST.index(today[1]) + 1)
    else:
        set_date = '%s' % (MONTH_LIST.index(today[1]) + 1)
    date = '%s/%s/%s' % (set_date, today[2], today[3])
    ret = set_date_time(date, time)
    return ret

def sync_time():
    timezoneCountry = get_date_time_pyconf('timezoneCountry')
    zone = re.split(':', timezoneCountry)
    hour = zone[0]
    if os.path.exists(ZONE_RULE_FILE) == False:
        cmd = '%s %s' % ('/bin/touch', ZONE_RULE_FILE)
        cmd_set = shlex.split(cmd)
        tools.execRoot(cmd_set)
        cmd = '%s 777 %s' % ('/bin/chmod', ZONE_RULE_FILE)
        cmd_set = shlex.split(cmd)
        tools.execRoot(cmd_set)
    else:
        cmd = '%s 777 %s' % ('/bin/chmod', ZONE_RULE_FILE)
        cmd_set = shlex.split(cmd)
        tools.execRoot(cmd_set)
    if get_date_time_pyconf('daylightSaving') == 'true' and get_date_time_pyconf('autoDaylightStatus') == 'false':
        try:
            with open(ZONE_RULE_FILE, 'w') as (w_file):
                conf = '#Rule\tNAME\tFROM\tTO\tTYPE\tIN\tON\tAT\tSAVE\tLETTER/S\n'
                w_file.write(conf)
                for years in range(4):
                    start_date = manual_get_start_date(years)
                    start_time = re.split('-', str(start_date))
                    year = int(start_time[0])
                    get_day = start_time[2]
                    get_day = re.split(' ', str(get_day))
                    day = int(get_day[0])
                    check_int = float(get_date_time_pyconf('offset'))
                    if len(get_date_time_pyconf('offset')) == 3:
                        conf = 'Rule\tMyRule\t%s\tonly\t-\t%s\t%s\t%s:%s\t%s:30\t        D\n' % (year, get_date_time_pyconf('startMon'), day, get_date_time_pyconf('startHour'), get_date_time_pyconf('startMin'), int(check_int))
                    else:
                        conf = 'Rule\tMyRule\t%s\tonly\t-\t%s\t%s\t%s:%s\t%s:0\t        D\n' % (year, get_date_time_pyconf('startMon'), day, get_date_time_pyconf('startHour'), get_date_time_pyconf('startMin'), int(check_int))
                    w_file.write(conf)
                    end_date = manual_get_end_date(years)
                    end_time = re.split('-', str(end_date))
                    year = int(end_time[0])
                    get_day = end_time[2]
                    get_day = re.split(' ', str(get_day))
                    day = int(get_day[0])
                    conf = 'Rule\tMyRule\t%s\tonly\t-\t%s\t%s\t%s:%s\t0\t        -\n\n' % (year, get_date_time_pyconf('endMon'), day, get_date_time_pyconf('endHour'), get_date_time_pyconf('endMin'))
                    w_file.write(conf)

                conf = '# Zone  NAME\tGMTOFF\tRULES/SAVE\tFORMAT  [UNTIL]\n'
                w_file.write(conf)
                conf = 'Zone    MyZone\t%s:00\tMyRule\t%s\n' % (hour, '%sGMT')
                w_file.write(conf)
        except IOError:
            print 'open %s fail' % ZONE_RULE_FILE

    else:
        try:
            with open(ZONE_RULE_FILE, 'w') as (w_file):
                conf = '#Rule\tNAME\tFROM\tTO\tTYPE\tIN\tON\tAT\tSAVE\tLETTER/S\n'
                w_file.write(conf)
                conf = 'Rule\tMyRule\t%s\tonly\t-\tJun\t1\t00:00\t0\t- \n\n' % date.today().year
                w_file.write(conf)
                conf = '# Zone  NAME\tGMTOFF\tRULES/SAVE\tFORMAT  [UNTIL]\n'
                w_file.write(conf)
                conf = 'Zone    MyZone\t%s:00\tMyRule\t%s\n' % (hour, '%sGMT')
                w_file.write(conf)
        except IOError:
            print 'open %s fail' % ZONE_RULE_FILE

    cmd = '%s -d /etc %s' % (PATH_ZIC, ZONE_RULE_FILE)
    cmd_set = shlex.split(cmd)
    tools.execRoot(cmd_set)
    cmd = '/bin/ln -s -f %s %s' % (ZONE_FORMAT_FILE, LOCALTIME_TIME_PATH)
    cmd_set = shlex.split(cmd)
    tools.execRoot(cmd_set)
    return 'Success'

def auto_daylight_run(status, country):
    if status == 'disable':
        cmd = PATH_AUTO_DST + ' disable'
        psPopen = subprocess.Popen(cmd, shell=True, close_fds=True, stdin=None, stdout=subprocess.PIPE, stderr=None)
    else:
        cmd = '%s enable %s' % (PATH_AUTO_DST, country)
        cmd_set = shlex.split(cmd)
        tools.execRoot(cmd_set)
    return 'Success'

def manual_get_start_date(year):
    start_mon = MONTH_LIST.index(get_date_time_pyconf('startMon')) + 1
    start_year = date.today().year + year
    start_time = '1 %s %s' % (get_date_time_pyconf('startMon'), start_year)
    d = time.strptime(start_time, '%d %b %Y')
    weeks = strftime('%U', d)
    start_time = '%s %s %s' % (start_year, weeks, get_date_time_pyconf('startWeek'))
    mytime = datetime.datetime.strptime(start_time, '%Y %W %a')
    this_mon = re.split('-', str(mytime))
    if start_mon > int(this_mon[1]):
        weeks = int(weeks) + 1
    if start_mon == 1:
        start_time = '%s %s %s' % (start_year, '0', 'Mon')
        mytime = datetime.datetime.strptime(start_time, '%Y %W %a')
        mytime = re.split(' ', str(mytime))
        check_week = '%s-01-01' % start_year
        if check_week == mytime[0]:
            weeks = int(weeks) + 1
    if get_date_time_pyconf('startOrd') == 'last':
        check_time = '%s %s %s' % (start_year, int(weeks) + 4, get_date_time_pyconf('startWeek'))
        mytime = datetime.datetime.strptime(check_time, '%Y %W %a')
        check_mon = re.split('-', str(mytime))
        if int(check_mon[1]) == int(this_mon[1]):
            weeks = int(weeks) + 4
        else:
            weeks = int(weeks) + 3
    else:
        weeks = int(weeks) + (int(get_date_time_pyconf('startOrd')) - 1)
    start_time = '%s %s %s' % (start_year, weeks, get_date_time_pyconf('startWeek'))
    mytime = datetime.datetime.strptime(start_time, '%Y %W %a')
    if get_date_time_pyconf('startOrd') == 'last':
        weeks = int(weeks) + 1
        start_time = '%s %s %s' % (start_year, weeks, get_date_time_pyconf('startWeek'))
        check_time = datetime.datetime.strptime(start_time, '%Y %W %a')
        check_mon = re.split('-', str(check_time))
        if int(check_mon[1]) == start_mon:
            mytime = check_time
    return mytime

def manual_get_end_date(year):
    start_mon = MONTH_LIST.index(get_date_time_pyconf('startMon')) + 1
    end_mon = MONTH_LIST.index(get_date_time_pyconf('endMon')) + 1
    if start_mon > end_mon:
        end_year = date.today().year + year + 1
    else:
        end_year = date.today().year + year
    end_time = '1 %s %s' % (get_date_time_pyconf('endMon'), end_year)
    d = time.strptime(end_time, '%d %b %Y')
    weeks = strftime('%U', d)
    end_time = '%s %s %s' % (end_year, weeks, get_date_time_pyconf('endWeek'))
    mytime = datetime.datetime.strptime(end_time, '%Y %W %a')
    this_mon = re.split('-', str(mytime))
    if end_mon > int(this_mon[1]):
        weeks = int(weeks) + 1
    if end_mon == 1:
        end_time = '%s %s %s' % (end_year, '0', 'Mon')
        mytime = datetime.datetime.strptime(end_time, '%Y %W %a')
        mytime = re.split(' ', str(mytime))
        check_week = '%s-01-01' % end_year
        if check_week == mytime[0]:
            weeks = int(weeks) + 1
    if get_date_time_pyconf('endOrd') == 'last':
        check_time = '%s %s %s' % (end_year, int(weeks) + 4, get_date_time_pyconf('endWeek'))
        mytime = datetime.datetime.strptime(check_time, '%Y %W %a')
        check_mon = re.split('-', str(mytime))
        if int(check_mon[1]) == int(this_mon[1]):
            weeks = int(weeks) + 4
        else:
            weeks = int(weeks) + 3
    else:
        weeks = int(weeks) + (int(get_date_time_pyconf('endOrd')) - 1)
    end_time = '%s %s %s' % (end_year, weeks, get_date_time_pyconf('endWeek'))
    mytime = datetime.datetime.strptime(end_time, '%Y %W %a')
    if get_date_time_pyconf('endOrd') == 'last':
        weeks = int(weeks) + 1
        end_time = '%s %s %s' % (end_year, weeks, get_date_time_pyconf('endWeek'))
        check_time = datetime.datetime.strptime(end_time, '%Y %W %a')
        check_mon = re.split('-', str(check_time))
        if int(check_mon[1]) == end_mon:
            mytime = check_time
    return mytime

def sync_date_time_status():
    timeServerActive = get_date_time_pyconf('timeServerActive')
    timeServerAddr = get_date_time_pyconf('timeServerAddr')
    daylightSaving = get_date_time_pyconf('daylightSaving')
    autoDaylightStatus = get_date_time_pyconf('autoDaylightStatus')
    autoDaylightType = get_date_time_pyconf('autoDaylightType')
    if timeServerActive == 'true':
        ntpsync(timeServerAddr)
    sync_time()
    if autoDaylightStatus == 'true' and daylightSaving == 'true':
        auto_daylight_run('enable', autoDaylightType)
    subprocess.Popen(UPDATE_SCHEDULE_JOB, shell=True, close_fds=True, stdin=None, stdout=subprocess.PIPE, stderr=None)
    return

def setTimeZone_for_nsu(city, tzData, tzValue):
    city_str_nsu2gui_map = {'Mexico City,Mounterry,Guadalajara': 'Mexico City,Monterrey,Guadalajara', 
       'Indiana (East)': 'Indiana(East)', 
       'Harare,Pitori': 'Harare,Pretoria', 
       'Islamabad,Karachi': 'Islamabad, Karachi'}
    if city_str_nsu2gui_map.has_key(city):
        city = city_str_nsu2gui_map[city]
    timezoneCountry = '%s:%s/%s' % (tzValue[:3], tzValue[3:], city)
    autoDaylightType = tzData
    setTimeZone(timezoneCountry, autoDaylightType, False)

def getTimeZone_for_nsu():
    city_str_gui2nsu_map = {'Mexico City,Monterrey,Guadalajara': 'Mexico City,Mounterry,Guadalajara', 
       'Indiana(East)': 'Indiana (East)', 
       'Harare,Pretoria': 'Harare,Pitori', 
       'Islamabad, Karachi': 'Islamabad,Karachi'}
    city = get_date_time_pyconf('timezoneCountry').split('/', 1)[(-1)]
    if city_str_gui2nsu_map.has_key(city):
        city = city_str_gui2nsu_map[city]
    return city

def setTimeZone(timezoneCountry, autoDaylightType, save_pyconf=True):
    if autoDaylightType == '':
        autoDaylightStatus = 'false'
        daylightSaving = 'false'
    else:
        autoDaylightStatus = 'true'
        daylightSaving = 'true'
    pyconf.modify_conf_value(DATE_TIME_PYCONF_PATH, 'timezoneCountry', timezoneCountry)
    pyconf.modify_conf_value(DATE_TIME_PYCONF_PATH, 'daylightSaving', daylightSaving)
    pyconf.modify_conf_value(DATE_TIME_PYCONF_PATH, 'autoDaylightType', autoDaylightType)
    pyconf.modify_conf_value(DATE_TIME_PYCONF_PATH, 'autoDaylightStatus', autoDaylightStatus)
    sync_date_time_status()
    if save_pyconf:
        write_pyconf()

def setDateTimeStatus(arguments):
    try:
        pre_daylightSaving = get_date_time_pyconf('daylightSaving')
        pre_autoDaylightStatus = get_date_time_pyconf('autoDaylightStatus')
        pyconf.modify_conf_value(DATE_TIME_PYCONF_PATH, 'timezoneCountry', arguments['timezoneCountry'])
        pyconf.modify_conf_value(DATE_TIME_PYCONF_PATH, 'daylightSaving', arguments['daylightSaving'])
        pyconf.modify_conf_value(DATE_TIME_PYCONF_PATH, 'autoDaylightType', arguments['autoDaylightType'])
        pyconf.modify_conf_value(DATE_TIME_PYCONF_PATH, 'autoDaylightStatus', arguments['autoDaylightStatus'])
        if arguments['timeServerActive'] == 'true':
            pyconf.modify_conf_value(DATE_TIME_PYCONF_PATH, 'timeServerActive', arguments['timeServerActive'])
            pyconf.modify_conf_value(DATE_TIME_PYCONF_PATH, 'timeServerAddr', arguments['timeServerAddr'])
            ret = ntpsync(arguments['timeServerAddr'])
        else:
            pyconf.modify_conf_value(DATE_TIME_PYCONF_PATH, 'timeServerActive', arguments['timeServerActive'])
            ret = setTime(arguments['manuallyTime'])
        if arguments['daylightSaving'] == 'true' and arguments['autoDaylightStatus'] == 'false':
            pyconf.modify_conf_value(DATE_TIME_PYCONF_PATH, 'startMon', arguments['startMon'])
            pyconf.modify_conf_value(DATE_TIME_PYCONF_PATH, 'startOrd', arguments['startOrd'])
            pyconf.modify_conf_value(DATE_TIME_PYCONF_PATH, 'startWeek', arguments['startWeek'])
            pyconf.modify_conf_value(DATE_TIME_PYCONF_PATH, 'startHour', arguments['startHour'])
            pyconf.modify_conf_value(DATE_TIME_PYCONF_PATH, 'startMin', arguments['startMin'])
            pyconf.modify_conf_value(DATE_TIME_PYCONF_PATH, 'endMon', arguments['endMon'])
            pyconf.modify_conf_value(DATE_TIME_PYCONF_PATH, 'endOrd', arguments['endOrd'])
            pyconf.modify_conf_value(DATE_TIME_PYCONF_PATH, 'endWeek', arguments['endWeek'])
            pyconf.modify_conf_value(DATE_TIME_PYCONF_PATH, 'endHour', arguments['endHour'])
            pyconf.modify_conf_value(DATE_TIME_PYCONF_PATH, 'endMin', arguments['endMin'])
            pyconf.modify_conf_value(DATE_TIME_PYCONF_PATH, 'offset', arguments['offset'])
        ret = sync_time()
        if arguments['daylightSaving'] == 'true':
            if arguments['autoDaylightStatus'] == 'true':
                ret = auto_daylight_run('enable', arguments['autoDaylightType'])
            elif pre_daylightSaving == 'true' and pre_autoDaylightStatus == 'true':
                ret = auto_daylight_run('disable', 'Nope')
        elif pre_daylightSaving == 'true' and pre_autoDaylightStatus == 'false':
            ret = auto_daylight_run('disable', 'Nope')
        subprocess.Popen(UPDATE_SCHEDULE_JOB, shell=True, close_fds=True, stdin=None, stdout=subprocess.PIPE, stderr=None)
    except Exception as e:
        tools.pylog(str(e))
        print 'except:%s' % e

    return ret
```
![28.png](https://www.iotsec-zone.com/images/MdImg/0577d3e6528ba856988932f34cc10e80.png)
如上图所示，来到报错函数getTimeZone_for_nsu，进一步追踪get_date_time_pyconf：
```python
def get_date_time_pyconf(key):
    return pyconf.get_conf_value(DATE_TIME_PYCONF_PATH, key)	# DATE_TIME_PYCONF_PATH = 'system.date_time'
```
另外，在此py文件的开头还需要我们注意一点，对象pyconf由config_api.ConfigOperator定义：
![29.png](https://www.iotsec-zone.com/images/MdImg/e20a5c8e093db0397f35258b01013aec.png)
即，初始化类时加载的文件为config_api.pyc，反编译它：
![30.png](https://www.iotsec-zone.com/images/MdImg/6f2afda661f15f7d7bb1db73e1318dab.png)
很明显，类ConfigOperator调用了文件/var/web_framework/py_conf，但在解包的rootfs中并未找到py_conf，而找到了两个md5值相同的py_conf_delaut：
![31.png](https://www.iotsec-zone.com/images/MdImg/8c71ee0c6a7ca048784049d5a40e8fd0.png)
我们很容易寻找到py_conf_delaut与py_conf之间的关系，后者都是由前者复制过来的：
![32.png](https://www.iotsec-zone.com/images/MdImg/1385c6efb454e2134dabe4fbe5494b7d.png)
所以随便选一个文件就行，在qemu中执行如下命令：
1. cp -a /usr/local/apache/web_framework/data/config/py_conf_default /etc/zyxel/py_conf
2. cp -a /etc/zyxel/py_conf /var/web_framework/

再执行一下脚本：
![33.png](https://www.iotsec-zone.com/images/MdImg/007b2f27a3aa5280cf246a064bda13a2.png)
看起来没有任何多余的报错了，挺好。kill掉原来的nsuagent进程，重新启动：
![34.png](https://www.iotsec-zone.com/images/MdImg/ccfc4c03f69500a0019038c8236975ab.png)
好了，回过头再来仔细看Bug fix的两句话：
- [Vulnerability] Format string vulnerability
- Remove nsuagent and do not support NAS starter utility（utility：工具）

看来移除nsuagent后就不支持NAS starter utility这个工具了。为了方便调试，我们在Windows安装NSU_2.01_1018.msi后，将安装目录下的所有文件压缩传到Ubuntu，Crossover运行之：
> NAS starter utility下载地址：[https://zyxel-nas-starter-utility.software.informer.com/download/](https://zyxel-nas-starter-utility.software.informer.com/download/)

![35.png](https://www.iotsec-zone.com/images/MdImg/16191e487d990bf121af2fd9aa477778.png)
![36.png](https://www.iotsec-zone.com/images/MdImg/9c90b8958104c8bd19a4e0ccd11ae338.png)
emmm，为什么这个软件没有发现（discovery）出我们的设备呢，如上图所示；并且注意到qemu中运行的nsuagent开始报错了：
![37.png](https://www.iotsec-zone.com/images/MdImg/ee3af2bc754e827aa1403210f93c75ed.png)
这说明软件与nsuagent是有通信流量的，识别不出来有可能还是网卡的问题，还是来到IDA的nsuagent：
![38.png](https://www.iotsec-zone.com/images/MdImg/c20b9afe6192d4f29503f3f66b0cd3c8.png)
都是硬编码的egiga，并没有我们的eth，所以可能需要将网卡名称改一下：

```bash
$ ifconfig eth0 down
$ ip link set eth0 name egiga0
$ ifconfig egiga0 up
```

修改前后的效果如下：
![39.png](https://www.iotsec-zone.com/images/MdImg/21cf761eceadf5cd4194ead0a00a5f79.png)
![40.png](https://www.iotsec-zone.com/images/MdImg/0d6d332443bb47561315b1ba2c6faf0a.png)
挺好，网络仍然是正常的：
![41.png](https://www.iotsec-zone.com/images/MdImg/9239487eda13f05a43edaabf7fdf96b8.png)
最后将脚本改回来：
![42.png](https://www.iotsec-zone.com/images/MdImg/2e051dd7d613f45e014b9673e2934803.png)
再次尝试启动nsuagent，稍等片刻之后就会出现我们的设备：
![43.png](https://www.iotsec-zone.com/images/MdImg/6a3c4bc9809916cdd518381dafd64b0e.png)
此时启动wireshark抓取tap0的流量：
![44.png](https://www.iotsec-zone.com/images/MdImg/a3b37d28d3a6f4004de98294d194987f.png)
在软件中进入NAS管理界面，注意状态一定要是Unreachable，而不是Down，如果是后者请重启软件或等待几秒钟；点击Show the directory of the NAS，随便输入账号密码后点击登录：
![45.png](https://www.iotsec-zone.com/images/MdImg/1bdb9d3a36c1600d804ec7f6ed2160f9.png)
登录时的流量包如下：
![46.png](https://www.iotsec-zone.com/images/MdImg/2bdc98d4f293ca452a4363c357c17f92.png)
搭建完成！
