# 网络设备分析实战之Sophos UTM 固件反编译 Perl  源码
> 饭否
> 来源：https://www.iotsec-zone.com/article/5

# 网络设备分析实战之Sophos UTM 固件反编译 Perl  源码

## 一. 题记：

​	网络设备或其他IoT设备提取到固件之后进行安全分析和漏洞挖掘工作，对 Sophos UTM 进行安全分析时，发现其具体提供Web 功能的是一个Linux 文件，并没有发现web功能实现的html代码，通过 Burp Suite 抓包Web 请求发现所有web页面的请求展示都是通过该Linux 文件实现，自然必须对其进行解析才行继续分析，但难度非常大，一度束手无策，经过几天的详细排查分析，最终得以解决。

​	由于国内外资料网站均没有对Sophos UTM 固件文件的反编译资料，故梳理成文，分享给大家。

## 二. 开始分析

UTM 是Unified Threat Management的缩写 ，简称为统一威胁管理，各个安全厂商都有自己的 UTM 产品，比较出名的是 Fortinet、WatchGuard、Sophos等等，此次需要进行安全分析的产品就是 Sophos UTM，官方网站为：

[https://www.sophos.com/en-us/products/unified-threat-management.aspx](https://www.sophos.com/en-us/products/unified-threat-management.aspx)

获取到的固件文件为一个完整打包好的 ISO 光盘文件，使用 VmWare Workstation 安装之后，  就可以进入到UTM 页面中。

本地访问的地址是 [https://192.168.21.100:4444/](https://192.168.21.100:4444/)

![0.png](https://www.iotsec-zone.com/images/MdImg/8aeb234c6f4b42ecf10ed9832c5f67ed.png)

一般来说获取一个ssh shell 将会非常有助于安全分析，比完全从Web 入手难度就要下降几个等级，下面就先来获取命令行shell。

### 1. 获取ssh shell & root shell

Sophos UTM 默认情况下不允许使用ssh shell，必须在web页面中开启，Management-System Settings-Shell Acess 开启shell 功能。

![1.png](https://www.iotsec-zone.com/images/MdImg/a85f19b1abbd7b9e3fa4ed52e4dee2eb.png)

注意要选择 "Allow password authentication"，否则要使用证书验证，比较麻烦，不方便分析。

接着输入 `root` 和 `loginuser` 两个用户的密码，并使用 `loginuser` ssh 登录。

```bash
a@DESKTOP-22L12IV:$ ssh loginuser@192.168.21.100
loginuser@192.168.21.100's password:
Last login: Mon Nov  9 05:34:23 2020 from 192.168.21.1

Sophos UTM
(C) Copyright 2000-2014 Sophos Limited and others. All rights reserved.
Sophos is a registered trademark of Sophos Limited and Sophos Group.
All other product and company names mentioned are trademarks or registered
trademarks of their respective owners.

For more copyright information look at /doc/astaro-license.txt
or http://www.astaro.com/doc/astaro-license.txt

NOTE: If not explicitly approved by Sophos support, any modifications
      done by root will void your support.

loginuser@test:/home/login > su
Password:
test:/home/login # id
uid=0(root) gid=0(root) groups=0(root),890(xorp)
test:/home/login # uname -a
Linux test 3.8.13.27-0.176377654.gd7350fc-smp64 #1 SMP Wed Sep 17 10:45:23 UTC 2014 x86_64 x86_64 x86_64 GNU/Linux
test:/home/login # cat /proc/version
Linux version 3.8.13.27-0.176377654.gd7350fc-smp64 (abuild@axgbuild) (gcc version 4.3.4 [gcc-4_3-branch revision 152973] (SUSE Linux) ) #1 SMP Wed Sep 17 10:45:23 UTC 2014
test:/home/login # cat /etc/version
 9.208008
test:/home/login #
```

###  2. 登录抓包 

接下来就是登录抓包进行登录验证分析，使用的工具是`Burp Suite Pro`，正确配置之后，就可以有完整的登录验证包。

```json
POST /webadmin.plx HTTP/1.1
Host: 192.168.21.100:4444
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:80.0) Gecko/20100101 Firefox/80.0
Accept: text/javascript, text/html, application/xml, text/xml, */*
Accept-Language: zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2
Accept-Encoding: gzip, deflate
X-Requested-With: XMLHttpRequest
X-Prototype-Version: 1.5.1.1
Content-type: application/x-www-form-urlencoded; charset=UTF-8
Content-Length: 287
Origin: https://192.168.21.100:4444
Connection: close
Referer: https://192.168.21.100:4444/

{"objs": [{"elements": {"login_username": "admin", "login_password": "test0011"}, "FID": "login_process"}], "SID": "0", "browser": "gecko", "backend_version": -1, "loc": "english", "_cookie": null, "wdebug": 0, "RID": "1604979704552_0.8572369473251601", "current_uuid": "", "ipv6": true}
```

发现登陆是使用 `json` 格式进行网络请求，方法是 `POST` ，请求的的接口文件是 `webadmin.plx`，同时登陆之后的页面请求和展示都是通过`webadmin.plx`进行数据交互，接下来就是对`webadmin.plx`进行解析分析。

## 三. 疑难问题

截止到此处，还没有遇到无法解决的问题，但深入文件分析时却给了沉重的一击，先来看`webadmin.plx`的文件属性：

```bash
test:/var/sec/chroot-httpd/var/webadmin # file webadmin.plx
webadmin.plx: ELF 32-bit LSB executable, Intel 80386, version 1 (SYSV), for GNU/Linux 2.2.5, dynamically linked (uses shared libs), stripped
```

32位可执行文件，没有异常，但是当使用 GDB 调试的时候提示：

![2.png](https://www.iotsec-zone.com/images/MdImg/5d68bc611ea265db8904350ed6d5e2f4.png)

GDB 提示文件格式不正确，事实是该文件可以执行：

```bash
test:/var/sec/chroot-httpd/var/webadmin # ./webadmin.plx
[19370] WARN: Use of uninitialized value $ENV{"REQUEST_METHOD"} in string eq at /</var/sec/chroot-httpd/var/webadmin/webadmin.plx>wfe/asg/modules/asg_fcgi.pm line 59.
test:/var/sec/chroot-httpd/var/webadmin #
```

有正常的错误返回，说明`webadmin.plx`文件正常，执行正常。

又发现该文件没有任何的 `Section`:

```
a@DESKTOP-22L12IV:$ readelf -S webadmin.plx
There are no sections in this file.
```

IDA Pro 又能够正常解析elf 文件，只有 `LOAD`节。

![3.png](https://www.iotsec-zone.com/images/MdImg/4986ea7aa44f81ce5cd6af0a6bed9987.png)

两眼一抓瞎，这可怎么办？

GDB  调试进程，失败。

尝试使用GDB 附加调试进程，失败+1,`not in executable format: File format not recognized`。

尝试GDB 附加父进程，然后调试子进程，失败+1，`not in executable format: File format not recognized`。

尝试GDB dumps内存，失败+1，`not in executable format: File format not recognized`。

GDB Server 远程调试，失败+1，`not in executable format: File format not recognized`。

获取两个不同版本的`webadmin.plx`文件，进行补丁对比，无差别，失败+1。

查找分析 ELF 反调试手段，失败+1。

最后得出结论，GDB 调试无效，继续接着找其他办法。

梳理一下目前得到的信息：

1. `webadmin.plx`负责处理UTM 系统登录，页面交互处理等等工作，是一个主体处理文件。
2. ELF 可执行程序，32位。
3. 可正常执行。
4. GDB 调试无效
5. 无反调试
6. 补丁对比无效

若进行安全分析和漏洞挖掘，就必须剁掉`webadmin.plx`，接着分析吧。

## 四. 确认Perl 编译器

认认真真的分析 `webadmin.plx`，查找ELF 中的字符串，其中几个字段尤为可疑：

```asm
a@DESKTOP-22L12IV:Sophos_UTM$ strings webadmin.plx |grep Perl     
psym_Perl_newSVpv                                                                       
psym_Perl_stack_grow                                                                    
psym_Perl_Itmps_floor_ptr                                                               
psym_Perl_sv_setiv                                                                      
psym_Perl_markstack_grow                                                                
psym_Perl_Iexit_flags_ptr                                                               
psym_Perl_save_int                                                                      
psym_Perl_push_scope                                                                    
psym_Perl_Isv_no_ptr                                                                    
psym_Perl_call_sv                                                                       
psym_Perl_Imarkstack_max_ptr                                                            
psym_Perl_Istack_base_ptr                                                               
psym_Perl_Gop_mutex_ptr                                                                 
psym_Perl_eval_pv                                                                       
psym_Perl_Gthr_key_ptr                                                                  
psym_Perl_call_list                                                                     
psym_Perl_Icurstackinfo_ptr                                                             
psym_Perl_get_context                                                                   
psym_Perl_Guse_safe_putenv_ptr                                                          
psym_Perl_IXpv_ptr                                                                      
psym_Perl_pop_scope    
```

很明显，跟Perl有很大的关系。

![4.png](https://www.iotsec-zone.com/images/MdImg/eedb62a5990ca22e4e2e5df214586d2e.png)

IDA 中也显示同样的结果，怀疑该`webadmin.plx`是由Perl 编译出来的，接下来就是验证自己的想法。

搜索引擎中查找资料，发现主流有三款程序可以从 Perl 代码编译成 ELF 软件：PerlAPP，PerlCC，Perl2EXE，而针对 Perl ELF 反编译就只有52破解网站上有一份PerlAPP 在Windows 下的资料，Linux 下的资料一无所有，也是奇葩，Perl 越混越差了。

从IDA对`webadmin.plx`的反编译代码中分析查找，找到一处关键字：

```c++
 v1 = *(_DWORD *)psym_Perl_Istack_sp_ptr(a1);
  v2 = (int **)psym_Perl_Imarkstack_ptr_ptr(a1);
  v3 = **v2;
  --*v2;
  v4 = (v1 - (*(_DWORD *)psym_Perl_Istack_base_ptr(a1) + 4 * v3)) >> 2;
  v18 = sub_804E6EC();
  v33 = a1;
  v34 = psym_Perl_get_hv(a1, "PerlApp::lic", 1); //PerlApp::lic,此处为关键字
  if ( v4 )
    v19 = *(_DWORD *)(*(_DWORD *)psym_Perl_Istack_base_ptr(a1) + 4 * (v3 + 1));
  else
    v19 = psym_Perl_Isv_undef_ptr(a1);
  v20 = *(int **)(v18 + 48);
  licFree(*(_DWORD *)(v18 + 56));
  *(_DWORD *)(v18 + 56) = 0;
```

从`PerlApp::lic`关键字来分析，基本可以确认 `webadmin.plx`是使用 `PerlAPP` 编译而成的ELF文件。 

## 五. 问题复现

`webadmin.plx`确认是由 `PerlAPP`工具编译而来，接下来就来验证一下，在Linux 环境下搭建一套PerlAPP环境。

PerlAPP的全称是 `Perl Dev Kit(PDK)`，有ActiveState 公司开发，但是其已经在2016年不再进行更新维护，在2020年10月份正式终止软件生命周期。

![5.png](https://www.iotsec-zone.com/images/MdImg/84948d4de25b7e90c0b3b082e682b340.png)

[https://www.activestate.com/blog/perl-dev-kit-pdk-now-end-of-life/](https://www.activestate.com/blog/perl-dev-kit-pdk-now-end-of-life/)

软件终止更新还好，影响不大，但网络上Linux 版本的PerlAPP非常难找，最终是在一个不起眼的小网站上下载到了低版本的安装包（这又是一个辛酸的故事），进行安装测试。

PerlApp安装需要 32位`Active Perl`（必须），而非操作系统自带的perl，又下载了一个低版本的`Active Perl`，才算完成PDK的安装（一把辛酸泪）。

![6.png](https://www.iotsec-zone.com/images/MdImg/faceb2a84e23be8c5bd772767496ebe1.png)

最后拿一个最简单的 perl 示例代码来进行测试：

```bash
[test@192 Desktop]$ cat test.pl 
#!/usr/bin/perl 
 
print "Hello, World!\n";
[test@192 Desktop]$ perl test.pl 
Hello, World!
[test@192 Desktop]$ 
```

 使用PerlApp进行编译测试：

![7.png](https://www.iotsec-zone.com/images/MdImg/da21b1bbe0b9ff280834afaca05b8b47.png)

shell中也能够正常执行：

```bash
[test@192 Desktop]$ ./test 
Hello, World! # 正常执行
[test@192 Desktop]$ 
```

使用GDB 调试编译好的程序：

```bash
[test@192 Desktop]$ gdb test
GNU gdb (GDB) Red Hat Enterprise Linux 7.6.1-119.el7
Copyright (C) 2013 Free Software Foundation, Inc.
License GPLv3+: GNU GPL version 3 or later <http://gnu.org/licenses/gpl.html>
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.  Type "show copying"
and "show warranty" for details.
This GDB was configured as "x86_64-redhat-linux-gnu".
For bug reporting instructions, please see:
<http://www.gnu.org/software/gdb/bugs/>...
"/home/test/Desktop/test": not in executable format: File format not recognized # 同样的报错提示
(gdb) 
```

好吧，同样的`not in executable format: File format not recognized`报错提示，完美复刻`webadmin.plx`遇到的问题。

## 六. 反编译  Perl  源码

现在来梳理一下目前的信息：

1. `webadmin.plx`是使用 `PerlApp`编译而成的ELF 文件
2. 不能使用GDB 调试，GDB Server也不行
3. 网络上没有 Linux 反编译Perl 的资料

在团队小伙伴 ztop（此处应该有掌声）的帮助下，发现使用 IDA 的 `linux_server`，结合IDA 远程调试，就可以完美绕过 GDB  无法调试的问题。在Centos 7 中无法使用IDA 远程调试，不知道具体原因是什么，遂放弃，选择使用 Kali 2018 R4，IDA的主机为Windows。

```bash
root@kali:~# chmod +x linux_server
root@kali:~# ./linux_server
IDA Linux 32-bit remote debug server(ST) v1.22. Hex-Rays (c) 2004-2017
Listening on 0.0.0.0:23946...
=========================================================
[1] Accepting connection from 192.168.21.1...
Warning: Section header string table index 26 is out of bounds
Hello, World!
Looking for GNU DWARF file at "/usr/lib32/2651bcf6f5569acd1dba629eaaaa5f002af684.debug"... no.
Looking for GNU DWARF file at "/usr/lib32/.debug/2651bcf6f5569acd1dba629eaaaa5f002af684.debug"... no.
[1] Closing connection from 192.168.21.1...
==========================================================
```

linux_server 的监听23946端口，需要在宿主机进行配置。

![8.png](https://www.iotsec-zone.com/images/MdImg/ff1621c86737782397d0726fa2b1215c.png)!

`webadmin.plx`的`main`函数中：

```c++
signed int __cdecl paperl_main(int a1, int a2, int a3, _DWORD *a4, int (__cdecl *a5)(int))
{
  signed int v5; // ebx
  int v7; // [esp+10h] [ebp-8h]

  v7 = dword_805B4F8;
  v5 = paperl_create((int ***)&v7, a1, a2, a3, a4, a5, 1); //此函数内部进行perl 代码执行。
  paperl_destruct(v7);
  return v5;
}
```

进入到 `paperl_create()`函数内部：

```c++
      ptr = sub_804C370(**v43, "*SCRIPTNAME", (int)"scriptname");
        if ( ptr )
        {
          v27 = (int *)sub_804C370(**v43, ptr, (int)"script"); //此函数对perl代码进行初始化
          v43[9] = v27;
          if ( !v27 || (v28 = (char *)sub_804C2D0(strlen(ptr) + 14, (int)"hashline"), (v43[8] = (int *)v28) == 0) )
```

找到关键代码位置：

```asm
LOAD:0804E224 jz      loc_804E32E
LOAD:0804E22A mov     eax, [edi]
LOAD:0804E22C mov     ecx, offset aScript             ; "script"
LOAD:0804E231 mov     edx, [ebp+ptr]
LOAD:0804E237 mov     eax, [eax]
LOAD:0804E239 call    sub_804C370					; 函数执行后，解密出perl代码
LOAD:0804E23E mov     [edi+24h], eax
LOAD:0804E241 test    eax, eax
LOAD:0804E243 jz      loc_804E517
LOAD:0804E249 mov     edx, [ebp+ptr]
LOAD:0804E24F cld
LOAD:0804E250 mov     ecx, 0FFFFFFFFh
LOAD:0804E255 xor     eax, eax
```

经过一系列的仔细调试和分析，最终发现 `0804E239 call    sub_804C370`函数执行后，eax 指向堆的内存中出现了 `#!/usr/bin/perl`字符，

![9.png](https://www.iotsec-zone.com/images/MdImg/55b7d3d55c48846a70eb40ff7ad7c248.png)

验证它：

![10.png](https://www.iotsec-zone.com/images/MdImg/41e73bbf82e05996020a65ac980b1d0f.png)

很明显都是明文字符，dump 出来进行校验，获取到完整的`webadmin.plx`功能的 perl 源码：

```perl
# setting line discipline to utf8 --------------------------
binmode( STDOUT, ':utf8' );
binmode( STDIN, ':utf8' );

# getting our paths
my ( $apppath, $appname ) = &get_path_and_appname();

# load core config ------------------------------------------
die '[' . $$ . '] DIED: core configuration could not be found' unless -e $RealBin . '/core/res/config.ph';
my $config_basic = read_ph( $RealBin . '/core/res/config.ph' );
die "Could not read core config in [$RealBin/core/res/config.ph]!" unless $config_basic;

# fetching application config ------------------------------
die '[' . $$ . '] DIED: application configuration could not be found' unless -l $RealBin . '/config';
my $config_app = read_ph( $RealBin . '/config' );
die "Could not read config for [" . $appname . "] in [" . $RealBin . "/config]!" unless $config_app;

# initialize Astaro::Logdispatcher -------------------------
Astaro::Logdispatcher->init({
  syslogname      => 'webadmin',
  myname          => 'webadmin',
  redirect_stdout => 0,
  redirect_stderr => 0,
  configfile      => 'core/res/core-log.conf',
  configset       => {
    logvars         => {
      logbitmask       => 7,
      syslogmtypeinfo  => 1,
      syslogcallerinfo => 1,
      tofilehandle     => 0
    }
  },
  logfiler        => [
    '+ .',
  ],
  printfile       => '/dev/null'
});
```

至此完整的获取到 Sophos UTM webadmin 功能的perl 源代码，剩余的工作就是基础的代码审计和漏洞挖掘。

## 七. 梳理总结

​	Perl 编译的ELF 文件在执行时，会在`/tmp/`目录下生成`libperl.so` 文件，perl 代码通过调用so文件接口j来执行，本次调试释放路径是

`/tmp/pdk-root/757fcfe556133c27007d41e4e52f4425/libperl.so` ，也可以通过hook so 的函数来达到获取perl 源码的目的。

​	Perl 语言编译的ELF文件，如何进行反编译，网络上没有任何有价值的信息，之前对python 和go 编译的ELF 文件都有过反编译经验，按道理来说同样是能够通过反编译来获取源代码，但是GDB 无法调试 ELF 困扰了很长时间，动态获取源码相对于静态去逆向解密算法要简单很多，虽然最后也并不简单。

​	其中的工作并没有去逆向解密算法，理清楚算法的情况下，可以编写脚本静态还原perl 源代码，但以安全分析或漏洞挖掘为目标，算是告一段落了，后续工作也可以编写IDA 的python 脚本，动态提取源代码。

## 八. 资料索引

### 1. demo

[https://utm.trysophos.com/](https://utm.trysophos.com/)

### 2. 从PDK打包的可执行程序里面解出完整的Perl源码

[https://www.52pojie.cn/thread-317216-1-1.html](https://www.52pojie.cn/thread-317216-1-1.html)

## 九. 注意事项

1. VmWare Workstation 安装固件 ISO 需要选择低版本的兼容性，否则无法安装。
2. Active Perl 要选择 X32位安装包，X64的安装包无法安装 PDK
