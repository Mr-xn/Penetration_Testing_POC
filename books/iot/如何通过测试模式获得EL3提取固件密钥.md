# 如何通过测试模式获得EL3提取固件密钥
> 0431物联卫士实验室
> 来源：https://www.iotsec-zone.com/article/296

几个月前，我把注意力转向了我的光纤网关。所以我在 ebay 上订购了相同的型号，拆焊并转储 nand，经过大量工作，从引导加载程序到用户空间，我设法清楚地了解了系统。

基本上，引导加载程序检查内核镜像的签名，使用引导加载程序存储的密钥解密内核镜像，然后解密 rootfs 镜像。

```
[YYYY] / # ls

README  dev  lib  opt  sbin  usr

bin  etc  media  proc  sys  var

config  exports  mnt  root  tftpboot

ctmp  home  nonexisting  run   tm

[YYYY] / # cat README

If you can read this, congratulations !

Feel free to drop me an email,xxxx@yyyy.zz
```

###  串行输出

在引导期间探测 pcb 上未填充的连接器足迹并没有导致任何结果。但我终于设法在一个电阻上找到了串行信号。

沿着轨道，它通过一些小 IC 通向 USB-C 电源连接器。在 USB-C 连接器的 SBU 引脚上添加一个上拉电阻，我们在 USB-C 连接器上直接有引导日志：

```
----

BTRM

V1.2

L1CD

MMUI

MMUA

DATA

ZBBS

MAIN

OTP?

REF?

REFP

RTF?

RTFP

OTPP

FSBT

EMMC

IMG?

IMGL

UHD?

UHDP

RLO?

RLOP

AHD?

ROT?

ROTA

MID?

MIDP

AHDP

SBI?

SBIA

PASS

HELO

5.0206-1.0.38-42.42

CPU0

L1CD

MMUI

MMUB

ZBBS

MAIN

xxx8a cfe decompressor (ROM).

DDR test done successfully

  - Decompressing ...

  - Decompression OK Load 1fc00000, Entry Point 1fc00000.

Base: 5.02_06

CFE version 1.0.38-163.180 for BCM963158 (64bit,SP,LE)

Build Date: Fri Dec  6 19:01:14 CET 2019 (xxxx@yyyy)

Copyright (C) 2000-2015 Broadcom Corporation.

XXX Version: 1.0

.text:   000000001fc00000-000000001fc2ea00

.rodata: 000000001fc2f000-000000001fd253f8

.data:   000000001fd26000-000000001fd26fc0

.bss:    000000001fd26fc0-000000001fd2c3f8

.stack:  000000001fd2e000-000000001fd6e000

.heap:   000000001fd6e000-000000001ff8e000

CPU Started with slow freq strap.

POR CPU frequency: 400 Mhz

CPU frequency set to 1675MHz

Boot Strap Register: 0x3fffff77

Chip ID: BCM63153_B1, Broadcom B53 Quad Core: 1675MHz

Total Memory: 536870912 bytes (512MB)

Enabling CCI500 coherency ... Done.

pmc_init:PMC using DQM mode

MMC: bus setup with width 8, sdr

SDHCI MMC init done.

i2c-gpio: using gpio24 (sda) gpio25 (scl).

i2c-gpio: using gpio15 (sda) gpio16 (scl).

fb0: SSD1320 frame buffer device (160x80 screen)

Serial: xxxx-xx-x-(xx)xx-xx-xxxxx / 0

Mac:    xx:xx:xx:xx:xx:xx

Bundle: xxxxxxxxxxxxxxxx

## Booting in standard mode.

 - Trying to load new bank0: no bank0 to flash, read fail

Loading firmware from 'emmc0:bank1': 31432192 bytes in 0.707 seconds.

ATF partition at offset 0000000011801000, size 11956

 - Validation stage 1.

 - Validation stage 2.

 - Kernel signature OK!

 - Decrypting kernel.

OP-TEE partition at offset 0000000011804000, size 129524

 - Validation stage 1.

 - Validation stage 2.

 - Kernel signature OK!

 - Decrypting kernel.

kernel partition at offset 0000000011824000, size 4574388

 - Validation stage 1.

 - Validation stage 2.

 - Kernel signature OK!

 - Decrypting kernel.

dtb partition at offset 0000000011c81000, size 21940

 - Validation stage 1.

 - Validation stage 2.

 - Kernel signature OK!

 - Decrypting kernel.

NOTICE:  BL31: v1.4(release):42d1e692

NOTICE:  BL31: Built : 18:19:32, Oct  2 2019

I/TC:

I/TC: OP-TEE version: 3.7.0-110-g6ba85038 (gcc version 8.3.0 )

                       #1 Tue Jan 28 13:57:39 UTC 2020 aarch64

I/TC: rng200_rng_init ...

I/TC: RNG200 init done.

I/TC: Initialized

ATF returned in EL2.

E/LD:  init_elf:259 sys_open_ta_bin(7011a688-ddde-4053-a5a9-

7b3c4ddf13b8)

E/TC:? 0 init_with_ldelf:229 ldelf failed with res: 0xffff000e

E/TC:? 0 tee_ta_open_session:727 Failed. Return error 0xffff000e
```

Arm Trusted Firmware, Op-tee, 所有签名和加密...

### 测试模式

在我对以前的型号进行工作期间，我发现通过短接 pcb 上一个连接器的两个引脚，电路板以所谓的测试模式启动。此模式在自定义网络身份验证后，允许在网络加载的固件映像上启动而无需签名检查。

所以我需要做两件事：

· 在新型号上触发测试模式

· 做网络认证

我们可以在 /sys/class 中找到一些有趣的东西

```
[YYYY] / # ls /sys/class/xxxgpio/boot-eth

data_in    data_out   device     direction  pin_num    subsystem  uevent
```

boot-eth引导。

```
[YYYY] / # while true; do

> cat /sys/class/xxxgpio/boot-eth/data_in

> sleep 0.1

> done

0

0

0
```

然后开始围绕所有测试点戳，直到我们看到 1 出现。

似乎在一个测试点上注入 3.3v 时，gpio 值在 0 和 1 之间交替。但是在启动时在正确的时间注入 3.3v 让我们直接得到 1。

我觉得“boot-eth”可以由适当的usb-pd命令/响应触发，测试点来自usb-pd芯片的gpio输出。

![0.png](https://www.iotsec-zone.com/images/MdImg/4e578d3986fb49408da2ff78ef6c6104.png)

我决定解决这个问题，而不是寻找更多。因为我可以使用这种被诅咒的方法轻松触发测试模式。

###  测试模式认证

在这里，我在以前的型号上的工作再次得到了帮助。基本上，在测试模式下，电路板发送一个 udp 数据包一次，该数据包必须使用每个设备特定的密钥进行散列并发送回。这样，该板确保它位于供应商的开发者拥有的网络上。

密钥是从主密钥派生的。综上所述，每个设备都有一个主键，可以通过计算大致推导出key0、key1。

```
rc4(md5(key_index + primary_key))
```

每个键索引都有特定的用途，对于测试模式，我们需要 key1

在以前的型号中，primary_key 存储在 nand 中（除了 mac 地址和其他每个设备的东西）。但是在这个设备上，我们没有加密的访问权限。

但是，由于我们是 root，设备需要能够为自己的目的获取密钥索引，除非所有加密都在安全世界中完成。

But we are lucky:

```
[YYYY] /root # xxxkeys

usage: xxxkeys [OPTS]

Where OPTS is one of:

   -b      base64 output

   -h      hexadecimal ouput (default)

   -n      fail when lock

[YYYY] /root # xxxkeys 1 16

ab553c48d5ade7426929c4c5b7f03aa
```

使用该密钥，我们能够验证我们的网络，以便设备以测试模式启动。

### 关于固件映像的说明

固件镜像格式与之前的型号大致相同，所以我重用了我写的脚本：

```
xilokar@xilokar:~$ Tools/parse_tag.py -i image-xxxxx8r_bank1_4.2.9

crc:     ce46779a

magic:   3658382b

version: 00000002

len:     01e28000

tag version

Build the 2021-02-08 18:38:30 by yyy@zzzzzzz

5 partitions present

partition 0

     crc:    0cf4403a

     offset: 00001000

     size:   00002eb4 (end=00003eb4)

     type:   00000002

     flags:  00000005

             skrypted

             xz

     name:   

Computed crc: 0cf4403a

partition 1

     crc:    349f1619

     offset: 00004000

     size:   0001f9f4 (end=000239f4)

     type:   00000004

     flags:  00000005

             skrypted

             xz

     name:   

Computed crc: 349f1619

partition 2

     crc:    64bde3c9

     offset: 00024000

     size:   0045cf94 (end=00480f94)

     type:   00000000

     flags:  00000005

             skrypted

             xz

     name:   

Computed crc: 64bde3c9

partition 3

     crc:    3bea7801

     offset: 00481000

     size:   000055b4 (end=004865b4)

     type:   00000003

     flags:  00000001

             skrypted

     name:   

Computed crc: 3bea7801

partition 4

     crc:    d7c8c9d2

     offset: 00487000

     size:   019a1000 (end=01e28000)

     type:   00000001

     flags:  00000001

             loaded in ram

     name:   

Computed crc: d7c8c9d2

Tag md5: cc6b4289d689c0b713e8afe7825022b8
```

它由一堆封装的二进制文件组成，每个都有一个类型和标志。

· xz 表示分区被压缩

· skrypted 表示分区已加密和签名

### 提取bootloader

实际上，我在进入测试模式之前就这样做了，但这没关系。

重复使用与我对brcm61650的攻击相同的方法，内核模块转储正确的内存空间，有了转储，让我们看看固件是如何加载的。

```
ulonglong probably_load_partition

     (partition_info *param_1,char *name,char load_mode,

      void *suggested_load_addr, int param_5)

{

ulonglong uVar1;

ulonglong uVar2;

memmap_entry *pmVar3;

uchar *local_18;

ulonglong local_10;

undefined8 local_8;

print("s_%s_partition_at_offset_, _size_%" ,name,

      param_1->addr,param_1->len);

if (load_mode == '�') {

    if ((*(uint *)¶m_1->flags & 1) == 0) goto LAB_1fc06ec4;

}

else {

    if ((*(uint *)¶m_1->flags & 1) == 0) {

       print("%s_partition_must_be_skrypted",name);

       maybe_update_load_status(0xf4);

       return 0xffffffff;

    }

}

...
```

```
uVar3 = probably_load_partition(&atf_part,"ATF",1,&LAB_10000000,0);

iVar1 = (int)uVar3;

if (iVar1 == 0) {

  ATF_pointer = atf_part.addr;

 uVar3 = probably_load_partition(&optee_part,"OP-TEE",

                                 1,(void *)0x10800000,0);

iVar1 = (int)uVar3;

if (iVar1 == 0) {

  uVar3 = probably_load_partition, (&kernel_part,

                                  "kernel",mode != 2,

                                   (void *)0x80000,1);

  iVar1 = (int)uVar3;

  if (iVar1 == 0) {

    uVar3 = probably_load_partition,(&dtb_part,"dtb",

                                     mode != 2,

                                     (void *)0x1fb70000,1);

    iVar1 = (int)uVar3;
```

我们看到，即使在测试模式下，内核（和 dtb）不需要被 skrypted，但 ATF 和 OP-TEE 必须。

让我们看看unskrypt_image函数是如何定义的。

```
ulonglong unskrypt_image(void *in,ulonglong in_len,void *out,

                         ulonglong *out_len,int type)

{

  int iVar1;

  uint cipher_index;

  ulonglong uVar2;

  ulonglong uVar3;

  undefined *key;

  int local_24bc;

  char hash_sha256 [32];

  undefined session_key [32];

  rsa_key public_key;

  undefined auStack9264 [272];

  skrypt_header local_2320;

  uint cbc_ctx [2162];

  memcpy(<m_desc,&PTR_s_LibTomMath_1fd1f800,0x198);

  crypt_register_cipher(&PTR_s_aes_1fd1f558);

  crypt_register_hash(&PTR_s_sha256_1fd1f658);

  memcpy(&local_2320,in,0x154);

  iVar1 = again_swap_bytes((ulonglong)local_2320.magic);

  if (iVar1 != 0x534b5259) {

    print("bad_magic");

    return 0xffffffff;

  }

  iVar1 = again_swap_bytes((ulonglong)local_2320.version);

  if (iVar1 != 3) {

    print("bad_version.");

    return 0xffffffff;

  }

  if (3 < local_2320.key_index) {

  print("%i:_key_number_too_big",(ulonglong)local_2320.key_index);

  return 0xffffffff;

  /* ...*/

  iVar1 = get_public_key(local_2320.key_index,&public_key,type);

  if (iVar1 < 0) {

  print("unable_to_get_public_key_!");

    return 0xffffffff;

  }

  if (support_decrypt_kernel == '�') {

   print("-_Validation_stage_1?";

  }

  else {

  if (type == 0) {

    key = (&PTR_aes_key_0_0_1fd27028)[local_2320.key_index];

  }

  else {

    key = (&PTR_aes_key_1_0_1fd27048)[local_2320.key_index];

  }
```

```
ulonglong unskrypt_image(void *in,ulonglong in_len,void *out,

                         ulonglong *out_len,int type)

{

  int iVar1;

  uint cipher_index;

  ulonglong uVar2;

  ulonglong uVar3;

  undefined *key;

  int local_24bc;

  char hash_sha256 [32];

  undefined session_key [32];

  rsa_key public_key;

  undefined auStack9264 [272];

  skrypt_header local_2320;

  uint cbc_ctx [2162];

  memcpy(<m_desc,&PTR_s_LibTomMath_1fd1f800,0x198);

  crypt_register_cipher(&PTR_s_aes_1fd1f558);

  crypt_register_hash(&PTR_s_sha256_1fd1f658);

  memcpy(&local_2320,in,0x154);

  iVar1 = again_swap_bytes((ulonglong)local_2320.magic);

  if (iVar1 != 0x534b5259) {

    print("bad_magic");

    return 0xffffffff;

  }

  iVar1 = again_swap_bytes((ulonglong)local_2320.version);

  if (iVar1 != 3) {

    print("bad_version.");

    return 0xffffffff;

  }

  if (3 < local_2320.key_index) {

  print("%i:_key_number_too_big",(ulonglong)local_2320.key_index);

  return 0xffffffff;

  /* ...*/

  iVar1 = get_public_key(local_2320.key_index,&public_key,type);

  if (iVar1 < 0) {

  print("unable_to_get_public_key_!");

    return 0xffffffff;

  }

  if (support_decrypt_kernel == '�') {

   print("-_Validation_stage_1?";

  }

  else {

  if (type == 0) {

    key = (&PTR_aes_key_0_0_1fd27028)[local_2320.key_index];

  }

  else {

    key = (&PTR_aes_key_1_0_1fd27048)[local_2320.key_index];

  }
```
我们可能有一个指向 aes 键的指针！

```
void * probably_clear_sensitive_data(void)

{

  longlong lVar1;

  void *pvVar2;

  undefined **ppuVar3;

  undefined **ppuVar4;

  int iVar5;

  if (support_decrypt_kernel != '�') {

   iVar5 = 4;

   ppuVar3 = &PTR_aes_key_1_0_1fd27048;

   ppuVar4 = &PTR_aes_key_0_0_1fd27028;

   do {

     zeromem(*ppuVar4,0x20);

     maybe_dma_sync(*ppuVar4,0x20,0);

     zeromem(*ppuVar3,0x20);

     maybe_dma_sync(*ppuVar3,0x20,0);

     iVar5 = iVar5 + -1;

     ppuVar3 = ppuVar3 + 1;

     ppuVar4 = ppuVar4 + 1;

   } while (iVar5 != 0);

  }

  lVar1 = probably_get_board_serial_info();

  zeromem(lVar1 + 0x26,0x20);

  pvVar2 = (void *)maybe_dma_sync(lVar1 + 0x26,0x20,0);

  return pvVar2;

}
```

在句柄传递给ATF之前调用它：

```
pvVar4 = probably_clear_sensitive_data();

probably_run_atf(pvVar4,(ulonglong)info);

uVar3 = cRead_8(currentel);

print("ATF_returned_in_EL%d",uVar3 >> 2 & 3);

uVar3 = cRead_8(currentel);

if (((uint)(uVar3 >> 2) & 3) == 3) {

  panic("Secure_OS_left_at_EL3!");

}
```

因此，没有机会从启动后内存转储中获取用于解密固件的 AES密钥。

通过进一步查看，我们可以看到固件 aes 密钥是从加密分区加载的。分区使用每个设备的密钥加密，只有在 EL3 中才能访问。

###  返回测试模式

让我们看看在测试模式下我们可以做什么。

ATF和OP-TEE必须是 skrypted。

所以专注于内核（或 dtb）。

xz标志非常有趣。如果未设置，则将分区复制到默认位置。但是xz标志会加载带有目标加载目标的标头。

考虑到这一点，也许我们可以尝试用我们自己的代码重载ATF？但是每个加载的分区都会填充一个 memory_map 条目，并且不允许覆盖。

```
[00010000-0001ffff pmc.boot]

[00080000-00d0a807 kernel]

[10000000-10007027 ATF]

[10800000-108543af OP-TEE]

[11800000-11db4fff imagetag]

[1fb80000-1fbfffff cfe.mmu]

[1fc00000-1fffffff cfe]
```
我在加载代码中发现了一个故障，它允许通过包装地址来覆盖某些代码，但发现它无法利用。

```
Exception Class: Data Abort From Current EL

Fault address:

Fault status: Translation fault, level 0
```

请记住，ATF分区必须是 skrypted。所以它的签名被检查，然后被解密。

让我们再看一点。这是skrypted分区的格式：

```
struct {

   unsigned int magic; // "SKRY"

   unsigned int version;

   unsigned int data_offset;

   unsigned int data_len;

   unsigned int key_index;

   unsigned char signature[256];

   unsigned char iv[32];

   unsigned char session_key_crypted[32];

};
```

在处理解密的代码处：

```
print("Kernel_signature_OK");

if (support_decrypt_kernel == 0) {

  iVar1 = xmemcmp((char *)skr_header.iv,&zero__1fd27068,0x20);

  if ((iVar1 != 0) ||

     (iVar1 = xmemcmp((char *)skr_header.session_key_crypted

                      ,&zero__1fd27068,0x20),

      iVar1 != 0)) {

     print("kernel seems encrypted, which is unsupported");

     return 0xffffffff;

  }

} else {

  iVar1 = xmemcmp((char *)skr_header.iv,&zero__1fd27068,0x20);

  if ((iVar1 != 0) ||

      (iVar1 = xmemcmp((char *)skr_header.session_key_crypted,

                       &zero__1fd27068,0x20),

       iVar1 != 0)) {

       print(" - Decrypting_kernel");

       cipher_index = crypt_find_cipher(s_aes_1fc2f862);

       cbc_start(cipher_index,skr_header.iv,

                 session_key,0x20,0,cbc_ctx);

       if (cipher_index != 0) {

         print("unable_to_setup_aes_cbc");

         return 0xffffffff;

       }

       iVar1 = decrypt_aes_cbc(in,out,uVar3,cbc_ctx);

       if (iVar1 != 0) {

         print("unable_to_decipher_kernel");

         return 0xffffffff;

       }

  }

}

memcpy(out,in,cipher_index);

*out_len = uVar3;

return uVar2 & 0xffffffff;
```

为了决定它是否会使用 session_key 解密分区，unskrypt 函数检查iv和encrypted_session_key是否不全为零。

因此，我们可以注入加密的ATF二进制文件，而不是未加密的ATF二进制文件。当然，我们不能修改这个固件。

因此，让我们获取所有我们可以找到的签名ATF分区并 objdump 加密的有效负载。

```
$ ./Tools/parse_skrypt.py ---dump atf.bin

magic:   534b5259

version: 00000003

offset:  00000154

len:     00002d60

key_id:  00000000

iv:  b'20c4f...a83c56c9492063d761bf17108d'

encrypted_session_key:  b'd1be...3aa0a87f1a1f'

Dumping to

$ objdump -D -b binary -m aarch64 atf.bin.ciphered

atf.bin.ciphered:     file format binary

Disassembly of section .data:

0000000000000000 <.data>:

0:       301752cf        adr     x15, 0x2ea59

4:       d07e50fe        adrp    x30, 0xfca1e000

8:       b530904a        cbnz    x10, 0x61210
```

加密的ATF分区之一解码为三个有效指令，第三个是跳转到非保留 memory_maped 区域（因为atf在0x10000000加载并且跳转是相对的，它给我们0x10061210，在ATF和OP-之间三通）！

如果我们省略xz标志，加密数据将按原样复制到默认的ATF memmap。

所以现在，让我们开始吧。

构建一个我们在跳转位置xz的“内核”镜像，用 skrypted ATF镜像打包它，iv和key设置为000...00，然后繁荣，我们在EL3处执行代码。

然后我们只需要重新跳转到处理分区解密的代码，我们就可以转储共享固件 aes 密钥......

```
void (*bl_printf)(char *str, ...) = (void *)0x1fc2d7f4;

void hexdump(char *prefix, void *p, int len) {

     unsigned char *c = p;

     int i,j;

     for(i=0; i< len; i+=16) {

             bl_printf("DUMP_%s_: %16x: ", prefix, c + i);

             for(j=0; j<16 && j+i<len; j++)="" {<="" div="">

                     bl_printf("%02x ", c[i+j]);

             }

             bl_printf("n");

     }

}

void (*load_bootinfo)(void) = (void*)0x1fc0e768;

void dump_keys(void) {

     load_bootinfo();

     hexdump("AES_0", (void*)0x1fd2be70, 32);

     hexdump("AES_1", (void*)0x1fd2bdf0, 32);

};
```

```
ENTRY(_Reset)

SECTIONS

{

     . = 0x10061210;

     .startup . : { startup64.o(.text) }

     .text : { *(.text) }

     .data : { *(.data) }

     .bss : { *(.bss COMMON) }

     . = ALIGN(8);

     . = . + 0x10000;

     stack_top = .;

}
```

```
DUMP_AES_0: 000000001fd2be70: a1 ... 33

DUMP_AES_1: 000000001fd2bdf0: d8 ... c4

```
### 绕过rootfs签名

要绕过包含在新发布的内核中的 rootfs 签名，只需加载以前的（签名的）内核（不检查 rootfs 签名，只需解密它），然后在新的（修改的）内核上加载一个模仿 kexec 的特制模块精心制作的rootfs。

### 结论 

“安全启动”设备上的自定义固件。

引导加载程序本身也使用 OTP 密钥进行签名/加密，该密钥在 ROM 执行引导加载程序之前设置为不可读。绕过它可能需要硬件故障注入攻击，但这超出了我的能力。
