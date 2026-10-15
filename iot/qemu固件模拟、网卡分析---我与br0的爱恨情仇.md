# qemu固件模拟、网卡分析---我与br0的爱恨情仇
> GroundCTL2MajorTom
> 来源：https://www.iotsec-zone.com/article/451

固件包名：tenda US_AC15V1.0BR_V15.03.05.19_multi_TD01.bin

- 型号：AC15
- 版本：V1.0BR_V15.03.05.19
- 官网：[https://www.tenda.com/](https://www.tenda.com/)
- 测试环境：Ubuntu 18.04

binwalk -Me 解包
![0.png](https://www.iotsec-zone.com/api/image/v2/20240802/d35d9g55yaxrgrbzr1.png)
firmwalker
```shell
***Firmware Directory***
/home/iot/gujian/_US_AC15V1.0BR_V15.03.05.19_multi_TD01.bin.extracted/squashfs-root
.........
***Search for password files***
##################################### passwd
t/etc_ro/passwd
t/usr/bin/passwd

##################################### shadow
t/etc_ro/shadow

***Search for patterns in files***
-------------------- upgrade --------------------
t/bin/cfmd
t/bin/httpd

-------------------- admin --------------------
t/etc_ro/passwd
t/etc_ro/smb.conf
t/webroot_ro/login.html
t/webroot_ro/samba.html
t/webroot_ro/default.cfg
t/webroot_ro/js/samba.js
t/webroot_ro/lang/zh/translate.json
t/webroot_ro/lang/cn/translate.json
t/webroot_ro/index.html

-------------------- pwd --------------------
t/bin/busybox
t/bin/multiWAN
t/bin/cfmd
t/lib/libc.so.0
t/lib/libpal_vendor.so
t/lib/libcloud.so
t/lib/libtpi.so

***Search for web servers***
##################################### httpd
t/bin/httpd
.........
```
file、checksec查看httpd文件
![1.png](https://www.iotsec-zone.com/api/image/v2/20240802/d35dad7d4pdfg32ebd.png)
架构：arm小段

NX保护开启，栈不可执行

服务为httpd启动，其接口的形式为`gofrom/`，根据文件结构，推测为goahead服务器

![2.png](https://www.iotsec-zone.com/api/image/v2/20240802/d35db4k60q70srajee.png)

```
关于 GoAhead 和 HTTPD 的关系：

GoAhead 作为 HTTPD 的一种实现：

HTTPD （HyperText Transfer Protocol Daemon）是一般用于指代 HTTP 服务器软件的术语。在广义上，任何实现了 HTTP 协议并能够处理 HTTP 请求的软件都可以称为 HTTPD。
GoAhead 实际上是一种 HTTPD 的具体实现，它以 C 语言编写，专注于嵌入式设备和嵌入式系统中提供 Web 服务的功能。
特点和用途：

轻量级和高效：GoAhead 被设计为小巧、高效的 Web 服务器，适用于嵌入式设备和其他资源受限的环境。
易于集成和定制：由于其轻量级和开放源代码的特性，开发人员可以相对容易地将 GoAhead 集成到他们的嵌入式系统中，并根据需要进行定制。
应用场景：

GoAhead 在嵌入式系统中广泛应用，例如网络路由器、工业控制系统、物联网设备等，这些设备需要提供 Web 界面或远程管理功能，但受限于资源需求而不能使用较为复杂的 Web 服务器软件。
```

webroot目录为空，web文件在webroot_ro目录下

因此在一会儿的模拟中要注意web目录是否正确

```shell
rcS:
cp -rf /etc_ro/* /etc/
cp -rf /webroot_ro/* /webroot/
```

### 启动项分析

![3.png](https://www.iotsec-zone.com/api/image/v2/20240802/d35dcqr9x4lvutriqb.png)

cat etc_ro/init.d/rcS

```shell
#!/bin/sh

PATH=/sbin:/bin:/usr/sbin:/usr/bin/
export PATH

# 挂载ramfs到/var/
mount -t ramfs none /var/

# 创建必要的目录
mkdir -p /var/etc
mkdir -p /var/media
mkdir -p /var/webroot
mkdir -p /var/etc/iproute
mkdir -p /var/run

# 从只读目录复制内容到可写目录
cp -rf /etc_ro/* /etc/
cp -rf /webroot_ro/* /webroot/

# 创建额外的目录
mkdir -p /var/etc/upan

# 挂载/etc/fstab中指定的所有文件系统
mount -a

# 挂载devpts以支持伪终端
mount -t devpts devpts /dev/pts

# 在/var/etc/upan上挂载tmpfs，并设置大小为2MB
mount -t tmpfs none /var/etc/upan -o size=2M

# 启动mdev以处理热插拔事件
mdev -s

# 再次创建必要的目录（重复的命令）
mkdir /var/run

# 配置热插拔事件触发mdev
echo '/sbin/mdev' > /proc/sys/kernel/hotplug

# 配置mdev规则以处理特定设备动作
echo 'wds*.* 0:0 0660 */etc/wds.sh $ACTION $INTERFACE' > /etc/mdev.conf
echo 'sd[a-z][0-9] 0:0 0660 @/usr/sbin/usb_up.sh $MDEV $DEVPATH' >> /etc/mdev.conf
echo '-sd[a-z] 0:0 0660 $/usr/sbin/usb_down.sh $MDEV $DEVPATH' >> /etc/mdev.conf
echo 'sd[a-z] 0:0 0660 @/usr/sbin/usb_up.sh $MDEV $DEVPATH' >> /etc/mdev.conf
echo '.* 0:0 0660 */usr/sbin/IppPrint.sh $ACTION $INTERFACE' >> /etc/mdev.conf

# 创建ppp目录
mkdir -p /var/ppp

# 加载内核模块
insmod /lib/modules/fastnat.ko 
insmod /lib/modules/bm.ko
insmod /lib/modules/mac_filter.ko 
insmod /lib/modules/privilege_ip.ko
insmod /lib/modules/qos.ko
insmod /lib/modules/url_filter.ko
insmod /lib/modules/loadbalance.ko
insmod /lib/modules/jnl.ko
insmod /lib/modules/ufsd.ko
insmod /lib/modules/fastnat_configure.ko

# 减少内核日志的冗余输出
echo "0 0 0 0" > /proc/sys/kernel/printk

# 启动必要的服务
cfmd &
echo '' > /proc/sys/kernel/hotplug
udevd &
logserver &
tendaupload &

# 检查nginx_init.sh是否存在并执行
if [ -e /etc/nginx/conf/nginx_init.sh ]; then
    sh /etc/nginx/conf/nginx_init.sh
fi

# 启动moniter服务
moniter &

# 启动telnet服务
telnetd &
```

奇怪的是并没有启动web服务的字段，猜测应该是在某个二进制文件里启动的

```shell
# 启动必要的服务
cfmd &
echo '' > /proc/sys/kernel/hotplug
udevd &
logserver &
tendaupload &
```

把cfmd拽到ida，查找httpd字符串

![4.png](https://www.iotsec-zone.com/api/image/v2/20240802/d35dd16g01kkdnkqts.png)

这里发现创建了一个子进程来执行 `httpd` 命令，并将其标准输出重定向到 `/dev/console`

### 固件模拟

#### 用户模拟

```
用户级模拟是 QEMU 的一种轻量级仿真模式，通常用于运行与主机架构不同的用户空间程序，而不需要完全模拟整个操作系统或硬件平台。
```

##### Welcome to问题

```shell
sudo chroot . ./qemu-arm-static --strace ./bin/httpd
```

![5.png](https://www.iotsec-zone.com/api/image/v2/20240802/d35dddrq27uodehnn2.png)

打印Welcome to...后报错

ida中搜索 Welcome to

下断点动态调试后发现

![6.png](https://www.iotsec-zone.com/api/image/v2/20240802/d35de36cim9sjfmue1.png)

这里进入了死循环，所以我们要进行patch

![7.png](https://www.iotsec-zone.com/api/image/v2/20240802/d35de87oqf3lo4blie.png)

在后续的判断中，R0的值为1，和0作比较，如果正常流程，肯定会走向红线，显示connect cfm failed!，所以这里也要patch。

![8.png](https://www.iotsec-zone.com/api/image/v2/20240802/d35deengjx8aya0cgk.png)

##### 255.255.255.255问题

patch后运行继续报错，ip显示255.255.255.255

![9.png](https://www.iotsec-zone.com/api/image/v2/20240802/d35delkjdl8b5yzqvi.png)

IDA搜索字符串listen ip

![10.png](https://www.iotsec-zone.com/api/image/v2/20240802/d35der98p2zw6yvije.png)

![11.png](https://www.iotsec-zone.com/api/image/v2/20240802/d35det5w31vwfeq2ty.png)

inet_ntoa函数的作用

```
inet_ntoa 是一个用于将 IPv4 地址从网络字节顺序转换为点分十进制字符串表示形式的函数。具体来说，它的作用是将 struct in_addr 类型的 IPv4 地址转换成一个以点分十进制表示的字符串。
```

这里可以看出listen ip取决于a1

```
a1-->&s.sa_data[2]-->v8-->listen ip
```

打开ghidra查看此处伪代码，

```c
int FUN_0001b84c(char *param_1,int param_2,undefined4 param_3,uint param_4)

........
      local_30._2_2_ = htons((uint16_t)param_2);  // 将param_2转换为网络字节序，并填充到local_30的第3、4字节
      if (param_1 == (char *)0x0) {
        local_30._4_4_ = 0;  // 如果param_1为空指针，将local_30的第5至8字节置为0
      }
      else {
        local_30._4_4_ = inet_addr(param_1);  // 如果param_1不为空，将param_1解析为网络地址并填充到local_30的第5至8字节
      }
........   
      if (iVar3 < 0) {
          FUN_0001b2f0(local_14);  // 调用一个处理函数
          local_14 = -1;  // 将local_14设为-1
        }
        else {
          pcVar2 = inet_ntoa((in_addr)local_30._4_4_);  // 将local_30的第5至8字节转换为点分十进制的IP地址，并返回字符串指针
          uVar1 = ntohs(local_30._2_2_);  // 将local_30的第3、4字节从网络字节序转换为主机字节序
          printf("httpd listen ip = %s port = %d\n", pcVar2, (uint)uVar1);  // 打印IP地址和端口号
          if (local_20 == 0) {  // 如果local_20为0
            iVar3 = listen(*(int *)(local_18 + 0xb0), 0x80);  // 监听套接字，设置最大连接数为0x80
            if (iVar3 < 0) {
              FUN_0001b2f0(local_14);  // 调用一个处理函数
              return -1;  // 返回-1
            }
........
```

由此可知255.255.255.255的输出取决于函数的传参param_1

![12.png](https://www.iotsec-zone.com/api/image/v2/20240802/d35df3xd0o275a6tc2.png)

向上查看本函数的引用共有三处、两个函数

FUN_0001ea08

```c
undefined4 FUN_0001ea08(void)
{
  int iVar1;
  int iVar2;
  undefined4 uVar3;
  
  iVar1 = sslport;  // 从全局变量 sslport 中获取端口号
  iVar2 = FUN_000c9054();  // 调用一个函数 FUN_000c9054()，可能是初始化或其他设置，返回值存储在 iVar2 中
  if (iVar2 < 0) {
    fwrite("matrixSslOpen failed, exiting...", 1, 0x20, stderr);  // 如果初始化失败，向 stderr 输出错误信息
  }
  
  // 读取 SSL 证书和私钥
  iVar2 = thunk_FUN_000d5404(&DAT_00101a24, s_/webroot/pem/certSrv.crt_000ffe60,
                             s_/webroot/pem/privkeySrv.pem_000ffe44, 0, 0);
  if (iVar2 < 0) {
    // 如果读取证书失败，向 stderr 输出错误信息，并进行一些清理工作
    fwrite("failed to read certificates in websSSLOpen\n", 1, 0x2b, stderr);
    thunk_FUN_000d4ea0(DAT_00101a24);
    FUN_000c9098();
    uVar3 = 0xffffffff;  // 返回错误码 0xffffffff
  }
  else {
    // 成功读取证书后，根据 sslport 的值调用 FUN_0001b84c() 来开启 SSL 套接字
    if (iVar1 == 0) {
      DAT_000ffe40 = FUN_0001b84c(0, 0x1bb, websSSLAccept, 0x80);
    }
    else {
      DAT_000ffe40 = FUN_0001b84c(0, iVar1, websSSLAccept, 0x80);
    }
    
    if (DAT_000ffe40 < 0) {
      // 如果开启 SSL 套接字失败，向 stderr 输出错误信息
      fprintf(stderr, "SSL: Unable to open SSL socket on port <%d>!\n", iVar1);
      uVar3 = 0xffffffff;  // 返回错误码 0xffffffff
    }
    else {
      uVar3 = 0;  // 成功开启 SSL 套接字，返回 0 表示成功
    }
  }
  
  return uVar3;  // 返回函数结果
}
这个函数的主要作用是初始化 SSL/TLS 相关的环境，并尝试在指定的端口上启动一个 SSL 套接字。具体的函数调用和逻辑流程如下：

获取全局变量 sslport 中的端口号。
调用 FUN_000c9054() 进行初始化或其他设置，检查返回值，如果小于 0，则输出错误信息。
调用 thunk_FUN_000d5404() 来读取 SSL 证书和私钥。如果读取失败，输出错误信息并进行清理工作。
根据 sslport 的值调用 FUN_0001b84c() 来开启 SSL 套接字。
如果开启 SSL 套接字失败，输出相应的错误信息。
返回适当的错误码或成功状态码。
这段代码的核心功能是在指定端口上启动一个 SSL 套接字，并处理可能出现的错误情况。
```

FUN_00029818

```c
int FUN_00029818(int param_1, int param_2)
{
  undefined4 local_2c;
  undefined4 local_28;
  undefined4 local_24;
  undefined4 local_20;
  int local_1c;
  undefined1 *local_18;
  int local_14;
  
  local_18 = (undefined1 *)0x0;  // 初始化 local_18 为 NULL
  local_2c = 0;
  local_28 = 0;
  local_24 = 0;
  local_20 = 0;
  memset(&local_2c, 0, 0x10);  // 清空局部变量 local_2c ~ local_20，总共16个字节
  
  local_18 = g_lan_ip;  // 将全局变量 g_lan_ip 赋值给 local_18
  local_14 = 0;  // 初始化 local_14 为 0
  local_1c = param_1;  // 将 param_1 赋值给 local_1c
  
  // 使用循环尝试在不同端口上监听，直到成功或达到指定的尝试次数 param_2
  while (local_14 <= param_2 && (DAT_00101a7c = FUN_0001b84c(local_18, param_1, websAccept, 0), DAT_00101a7c < 0)) {
    local_14 = local_14 + 1;  // 更新尝试次数
  }
  
  if (param_2 < local_14) {  // 如果尝试次数超过了 param_2，则监听失败
    printf("%s %d: Couldn\'t open a socket on ports %d\n", "websOpenListen", 0xfd, local_1c);
    param_1 = -1;  // 返回错误码 -1
  } else {
    // 监听成功
    websPort = param_1;  // 设置全局变量 websPort 为监听的端口号
    FUN_00010988(websHostUrl);  // 调用一个函数，清理 websHostUrl
    FUN_00010988(websIpaddrUrl);  // 调用一个函数，清理 websIpaddrUrl
    websHostUrl = 0;  // 置空 websHostUrl
    websIpaddrUrl = 0;  // 置空 websIpaddrUrl
    
    if (param_1 == 0x50) {  // 如果监听端口为 80（0x50）
      websHostUrl = FUN_000109b4(websHost);  // 根据 websHost 设置 websHostUrl
      websIpaddrUrl = FUN_000109b4(websIpaddr);  // 根据 websIpaddr 设置 websIpaddrUrl
    } else {
      // 否则，根据 websHost 和 param_1 格式化 websHostUrl，根据 websIpaddr 和 param_1 格式化 websIpaddrUrl
      FUN_0001837c(&websHostUrl, 0x1050, "%s:%d", websHost, param_1);
      FUN_0001837c(&websIpaddrUrl, 0x1050, "%s:%d", websIpaddr, param_1);
    }
    
    // 输出监听信息
    FUN_000204f8(0, "webs: Listening for HTTP requests at address %s\n", websIpaddrUrl);
  }
  
  return param_1;  // 返回监听的端口号或错误码 -1
}
这段代码的主要功能是尝试在指定的端口上启动 HTTP 服务监听。它会尝试多次调用 FUN_0001b84c() 来监听端口，直到成功或者尝试次数达到 param_2。如果监听失败，会输出错误信息并返回 -1；如果监听成功，会设置全局变量 websPort，清理相关变量，并输出监听地址的信息。
```

通过对比，定位到FUN_00029818函数，查看FUN_0001b84函数的调用位置

```c
  local_18 = g_lan_ip;  // 将全局变量 g_lan_ip 赋值给 local_18
  local_14 = 0;  // 初始化 local_14 为 0
  local_1c = param_1;  // 将 param_1 赋值给 local_1c
  
  // 使用循环尝试在不同端口上监听，直到成功或达到指定的尝试次数 param_2
  while (local_14 <= param_2 && (DAT_00101a7c = FUN_0001b84c(local_18, param_1, websAccept, 0), DAT_00101a7c < 0)) {
    local_14 = local_14 + 1;  // 更新尝试次数
  }
```

这里可以看出param1的参数来自于全局变量 g_lan_ip

向上查看全局变量g_lan_ip的引用

![13.png](https://www.iotsec-zone.com/api/image/v2/20240802/d35dfcao0ryfaedfg1.png)

定位到两个函数FUN_0002e9ec和FUN_0002e420

FUN_0002e9ec

```c
...............
  // 执行系统命令，设置 TCP 时间戳
  doSystemCmd("echo 0 > /proc/sys/net/ipv4/tcp_timestamps");
  
  // 调用一个名为 FUN_0001b6d4 的函数
  FUN_0001b6d4();
  
  // 将字符串形式的 IPv4 地址转换为 in_addr 结构体
  inet_aton(g_lan_ip, &local_18);
  
  // 将 DAT_00100048 字符串复制到 acStack_118 数组中
  strcpy(acStack_118, DAT_00100048);
  
  // 调用一个名为 FUN_00012530 的函数，处理 acStack_118 数组
  FUN_00012530(acStack_118);
  
  // 将本地 IP 地址转换为字符串形式，保存在 local_14 中
  local_14 = inet_ntoa(local_18);
  
  // 计算 local_14 字符串的长度
  sVar1 = strlen(local_14);
...............
inet_aton作用：

```

FUN_0002e420

```c
...............
    
    //这段代码的主要功能是获取本地的IP地址并存储在全局变量 g_lan_ip 中
    // 获取本地IP地址，关键！
    uVar4 = getLanIfName();
    // 调用 getLanIfName() 函数，获取本地网络接口名称，结果存储在 uVar4 中

    iVar1 = getIfIp(uVar4, &local_c8);
    // 调用 getIfIp() 函数，传入本地网络接口名称 uVar4 和指向 local_c8 的指针，获取本地IP地址信息，并将结果存储在 local_c8 中

    if (iVar1 < 0) {
      // 如果获取IP地址失败
      GetValue("lan.ip", acStack_98);
      // 调用 GetValue() 函数，读取配置项 "lan.ip" 的值，并将结果存储在 acStack_98 中

      strcpy(g_lan_ip, acStack_98);
      // 将 acStack_98 中的字符串复制到全局变量 g_lan_ip 中

      memset(local_128, 0, 0x50);
      // 清空 local_128 数组的前 0x50（80）个字节

      iVar1 = tpi_lan_dhcpc_get_ipinfo_and_status(local_128);
      // 调用 tpi_lan_dhcpc_get_ipinfo_and_status() 函数，传入 local_128，并获取IP信息和状态，结果存储在 local_128 中

      if ((iVar1 == 0) && (local_128[0] != '\0')) {
        // 如果获取IP信息和状态成功，并且 local_128 不为空
        vos_strcpy(g_lan_ip, local_128);
        // 使用 vos_strcpy() 函数将 local_128 中的字符串复制到全局变量 g_lan_ip 中
      }
    } else {
      // 如果获取IP地址成功
      vos_strcpy(g_lan_ip, &local_c8);
      // 使用 vos_strcpy() 函数将 local_c8 中的字符串复制到全局变量 g_lan_ip 中
    }
    }
    memset(&local_d4,0,9);
    iVar2 = inet_addr(g_lan_ip);
    local_d4 = local_d4 & 0xff | iVar2 << 8;
    local_d0 = (undefined)(iVar2 >> 0x18);
    tpi_talk_to_kernel(5,&local_d4,&local_d8,0,0,0);
    FUN_0002ed58(1);
    FUN_0002ed58(0);
    _Var3 = getpid();
    doSystemCmd("echo %d > %s",_Var3,"/etc/httpd.pid");
    iVar1 = FUN_0002e9ec();//调用FUN_0002e9ec()
    
.....................
```

```
FUN_0002e420调用getLanIfName()、getIfIp()获取接口名称和ip给到了全局变量g_lan_ip
```

向上查看发现了FUN_0002e420函数调用了FUN_0002e9ec()函数，调用链完整。

![14.png](https://www.iotsec-zone.com/api/image/v2/20240802/d35dfiwc7wh3cpoa3y.png)

![15.png](https://www.iotsec-zone.com/api/image/v2/20240802/d35dfp5ueqi8atdckw.png)

**想知道全局变量ip是怎么来的就要分析这两个外部函数的调用**

在lib/中查找这两个EXETERNAL函数

getIfip这里应该是网络编程中getIfIp函数获取到ip地址

在库中查找该函数

![16.png](https://www.iotsec-zone.com/api/image/v2/20240802/d35dfzzld6of4gq8ap.png)

```
readelf -d xxx | grep NEEDED 
这条命令的作用是用来查看 ELF 格式的可执行文件或共享库（例如动态链接库）的动态依赖项。
```

打开libcommon.so,查找函数getIfIp

```c
int __fastcall getIfIp(const char *a1, char *a2)
{
  char *v3; // 存放转换后的IP地址字符串指针
  char dest[20]; // 存放接口名称的缓冲区
  struct in_addr v8; // 存放IP地址结构体
  int fd; // socket文件描述符

  // 创建一个AF_INET（IPv4）、SOCK_DGRAM（数据报套接字）、协议为0（自动选择）的套接字
  fd = socket(2, 2, 0);
  if ( fd < 0 )
    return -1; // 如果创建失败，返回-1

  // 将参数a1（接口名称）拷贝到本地缓冲区dest，最多拷贝0x10（16）字节
  strncpy(dest, a1, 0x10u);

  // 使用ioctl系统调用来获取指定接口的IP地址
  if ( ioctl(fd, 0x8915u, dest) >= 0 )
  {
    // ioctl调用成功，将结果存储在v8结构体中的in_addr类型的变量中
    v3 = inet_ntoa(v8); // 将IP地址结构体转换为点分十进制字符串形式
    strcpy(a2, v3); // 将转换后的IP地址字符串拷贝到a2参数指向的缓冲区
    close(fd); // 关闭套接字
    return 0; // 返回成功
  }
  else
  {
    close(fd); // 关闭套接字
    return -1; // 返回失败
  }
}

ioctl 调用:
使用 ioctl(fd, 0x8915u, dest) 发起系统调用，目的是获取指定网络接口的IP地址。
如果 ioctl 返回值大于等于0，表示获取IP地址成功。
```

libcommon.so中查找getLanIfName()函数，可以看到get_eth_name 和getLanIfName存在调用关系

![17.png](https://www.iotsec-zone.com/api/image/v2/20240802/d35dggbltfo5f3zqa6.png)

![18.png](https://www.iotsec-zone.com/api/image/v2/20240802/d35dgiymmvvv4z2t50.png)

这里可以看出传入参数为0

grep -r 搜索get_eth_name

![19.png](https://www.iotsec-zone.com/api/image/v2/20240802/d35dgqnn5jui4ccmbu.png)

这里定位到了libChipApi.so库，放到ida里搜索该函数

```c
const char *__fastcall get_eth_name(int a1)
{
  const char *v1; // r3

  switch ( a1 )
  {
    case 0:
      v1 = "br0";
      break;
    case 1:
      v1 = "br1";
      break;
    case 6:
      v1 = "vlan1";
      break;
    case 10:
      v1 = "vlan2";
      break;
    case 11:
      v1 = "vlan3";
      break;
    case 12:
      v1 = "vlan4";
      break;
    case 13:
      v1 = "vlan5";
      break;
    case 23:
      v1 = "eth1";
      break;
    case 24:
      v1 = "wl0.1";
      break;
    case 27:
      v1 = "eth2";
      break;
    case 28:
      v1 = "wl1.1";
      break;
    case 51:
      v1 = "br10";
      break;
    case 55:
      v1 = "br20";
      break;
    default:
      v1 = (const char *)&unk_66C8;
      break;
  }
  return v1;
}
```

**前面传入的参数是0 ，所以要设置br0网卡，否则服务是无法访问的！！！！！！**

自己画了个流程图方便大家理解

![20.png](https://www.iotsec-zone.com/api/image/v2/20240802/d35dgzlu7jk6fhqmeo.png)

设置网卡br0：

```shell
sudo brctl addbr br0

sudo ifconfig br0 192.168.0.3
```

成功启动web

![21.png](https://www.iotsec-zone.com/api/image/v2/20240802/d35dh7h2911yxhjbwf.png)

#### 系统模拟

```
系统级模拟是 QEMU 的完整虚拟化模式，它可以模拟整个硬件平台和操作系统环境，使得在虚拟机中能够运行完整的操作系统。
```

宿主机启动虚拟机脚本

```shell
#!/bin/sh
qemu-system-arm \
    -M vexpress-a9 \
    -kernel /home/iot/tools/qemu-images/armhf/vmlinuz-3.2.0-4-vexpress \
    -initrd /home/iot/tools/qemu-images/armhf/initrd.img-3.2.0-4-vexpress \
    -drive if=sd,file=/home/iot/tools/qemu-images/armhf/debian_wheezy_armhf_standard.qcow2 \
    -append "root=/dev/mmcblk0p2 console=ttyAMA0" \
    -net nic -net tap,ifname=tap0,script=no,downscript=no \
    -nographic
```

```shell
-M vexpress-a9 \

指定虚拟机的机器类型为 vexpress-a9，这是一个 ARM 开发板模型。
-kernel /home/iot/tools/qemu-images/armhf/vmlinuz-3.2.0-4-vexpress \

指定虚拟机使用的内核镜像文件的路径和文件名。
-initrd /home/iot/tools/qemu-images/armhf/initrd.img-3.2.0-4-vexpress \

指定虚拟机使用的 initrd（初始化 RAM 磁盘）镜像文件的路径和文件名。
-drive if=sd,file=/home/iot/tools/qemu-images/armhf/debian_wheezy_armhf_standard.qcow2 \

定义一个虚拟硬盘驱动器，使用 qcow2 格式的镜像文件作为虚拟机的根文件系统。
-append "root=/dev/mmcblk0p2 console=ttyAMA0" \

向内核传递的启动参数，指定根文件系统的位置和控制台设备。
-net nic -net tap,ifname=tap0,script=no,downscript=no \

配置虚拟网络接口：
-net nic：创建一个虚拟网络接口卡。
-net tap,ifname=tap0,script=no,downscript=no：连接到 tap0 设备，禁用启动和关闭脚本。
-nographic
使用非图形化的控制台模式启动虚拟机，所有的输入输出都将通过控制台进行。
```

虚拟机配置网卡

```shell
ip link add br0 type dummy
ip: 这是 Linux 系统中用于配置网络接口的命令行工具。
link: 表示进行网络接口相关的操作。
add: 指示要添加一个新的网络接口。
br0: 是要创建的虚拟网络接口的名称。在这里，br0 是一个常见的命名约定，通常用于桥接接口的命名。
type dummy: 指定创建的接口类型为 dummy。dummy 接口是一种虚拟的、无实际数据传输功能的接口，它的主要用途是占位符或者协议测试。
ifconfig eth0 192.168.0.2/24
ifconfig br0 192.168.0.3/24
```

虚拟机挂载

```shell
mount --bind /proc/ proc/
mount --bind /sys/ sys/
mount --bind /dev/ dev/
```

tar命令压缩、scp传送压缩包、解压...  

这里压缩打包时注意要打包**patch过后的httpd**

得到文件结构

![22.png](https://www.iotsec-zone.com/api/image/v2/20240802/d35dhhjl5eik60pphu.png)

设置根目录

```shell
chroot . sh
/bin/httpd
```

![23.png](https://www.iotsec-zone.com/api/image/v2/20240802/d35dhnu0fsbenjhrfb.png)
直接启动了
