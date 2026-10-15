# 固件安全-函数劫持以及patch
> s3cana
> 来源：https://www.iotsec-zone.com/article/153

在针对固件的模拟过程中可能会遇到因为固件中函数依赖于硬件的问题导致无法正常对固件进行模拟，这个时候往往需要对固件中的函数进行劫持或者patch ,本文总结了以下四种可用方式，其中LD_PRELOAD目前已经有大量材料进行介绍，不作为主要内容。本文主要介绍了后三种的劫持思路,不足之处欢迎大家指正。
● LD_PRELOAD
● dl_open
● LD_LIBRARY_PATH
● 直接针对二进制文件的patch
## 通过LD_PRELOAD实现劫持
● 在《揭秘家用路由器0day漏洞利用挖掘技术》一书中，第3.1.2节中介绍了通过LD_PRELOAD来劫持apmib_init函数，从而修复在漏洞挖掘过程中固件函数导致的崩溃问题。该书中内容完全可以复现，不做过多陈述。
● 但是通过LD_PRELOAD的劫持当在编译uclibc的时候，一旦关闭了LD_PRELOAD选项，该劫持方式便不再适用。本文通过后续的三种方案，来实现在LD_PRELOAD失效的时候提供一种固件劫持的思路。
## 通过dlopen的劫持
以下的两种方案可以通过不借助LD_PRELOAD，使用dlopen做wrapper来实现对原函数的劫持
### 方案一
● dlopen函数可以打开.so的动态链接库文件，并返回库函数的句柄信息，实际上是通过wrapper实现。
● 首先将原apmib.so重命名为 libapmib_orig.so
![0.png](https://www.iotsec-zone.com/images/MdImg/1902127c203b016c3bfea1d9353f56e3.png)
● 在lib目录下，新建apmib.c 文件，代码内容如下
```
#include<stdio.h>
#define MIB_HW_VER 0x250
#define MIB_IP_ADDR 170
#define MIB_CAPTCHA 0x2C1
#include <dlfcn.h>
static void* lib_handle = NULL;
__attribute__((constructor)) _init_apmib()
{
lib_handle = dlopen("libapmib_orig.so",RTLD_NOW | RTLD_GLOBAL);  // 注意：已经改名字了
}

__attribute__((destructor)) void _fini_apmib()
{
dlclose(lib_handle);
}
//libapmib_orig
int apmib_init(void){
	printf("helllo");
	return 1;
}
int fork(void){
	return 0;
}
void apmib_get(int code,int *value){
	switch(code){
		case MIB_HW_VER:
			*value = 1;
			break;
		case MIB_IP_ADDR:
			*value = 1;
			break;
		case MIB_CAPTCHA:
			*value = 1;
			break;
	}
	return;
}
```
* 注意这里的编译过程，对dlopen以及dlclose的链接要使用提取的文件系统中的libdl.so.0，在实际的测试过程中，为保证链接正确我将libdl.so.0拷贝后，重命名为libdln.so。
![1.png](https://www.iotsec-zone.com/images/MdImg/a7b5e4fabcb58282259ac82b88772f26.png)
* 将apmib.c重新编译为apmib.so
```
mips-linux-gcc -shared  -fPIC apmib.c -o apmib.so  -ldln -lapmib_orig -L /home/kali/Downloads/d-link/DIR605A/_DIR605/squashfs-root-0/
```
* 通过qemu-static-mips进行测试,实现劫持
```
sudo chroot ./ ./qemu-mips-static ./bin/boa
```
![2.png](https://www.iotsec-zone.com/images/MdImg/e854cd24e936b9076bce7de9bb9e1ad8.png)
### 方案二
* 新建文件 apmib_2.c
```
#include <stdio.h>
int apmib_init(void){
	printf("helllo2");
	return 1;
}
int fork(void){
	return 0;
}
void apmib_get(int code,int *value){
	switch(code){
		case MIB_HW_VER:
			*value = 1;
			break;
		case MIB_IP_ADDR:
			*value = 1;
			break;
		case MIB_CAPTCHA:
			*value = 1;
			break;
	}
	return;
}
```
* mips-linux-gcc进行编译
```
mips-linux-gcc -shared -fPIC -o apmib.so -ldln -lapmib_orig  -L. -D_GNU_SOURCE   apmib_2.c
```
* 对编译后的apmib.so进行测试
```
sudo chroot ./ ./qemu-mips-static ./bin/boa
```
![3.png](https://www.iotsec-zone.com/images/MdImg/c76d3585b77be0d863cdb2eb017e7f72.png)
### 总结
* 以上两种方法的根本是将原有的apmib.so 库文件重命名后再编译可控的apmib.so 库文件，新编译的apmib.so库文件依赖于原有的apmib.so库文件，并在新的apmib.c文件中查找到原有的函数即可实现调用
* 如参考文章中所述，以上的两种方式也有一定的限制条件，
  ○ 比如方案二仅仅适用于GNU的系统 ，两者都仅对弱符号劫持可用
  ○ 优点是我们只需要知道部分需要劫持的函数原型即可。
* 通过以上两种方式，我们后续在编译链接的过程中也可以学习在进行动态链接编译的时候，我们具备已有的.so文件，即可通过gcc 的 -l 编译参数进行链接即可。
## 通过DYNAMIC Segment的劫持
### 方案
* 利用dynamic和elf_hash之间的空余区域，在该区域伪造出新的dynamic的一个数组。如下图，不修改二进制文件大小，伪造增添ibcjson.so,使得二进制文件加载 ibcjson.so。在ibcjson.so中编写对应的劫持函数。
![4.png](https://www.iotsec-zone.com/images/MdImg/a3e9b9f2be9a4124e89236025aada4e0.png)
* 思路： 将原有的Elf32_Dyn数组元素依次后移，并在该数组的首部添加伪造的ibcjson.so，该lib的命名可以选用string table中的任一字符串即可。
![5.png](https://www.iotsec-zone.com/images/MdImg/d4dce5ec433d149ad258a777847cb5ab.png)
* 核心移动代码，将Elf32_Dyn中的元素依次后移一个，dynamic段 dynamic[0]元素作为要伪造填充的数据，在本文的实验中，将dynamic[0]中的value值加1。由于在MIPS下存在大小端两种架构，在小端机器上的代码解决大端架构的填充伪造时要注意大小端的转换问题。
### 测试
* TOTOLink N210RE中boa程序，劫持函数参考DIR605A，劫持apmib_init以及apmib_get
* 该固件的ld，关闭了LD_PRELOAD程序选项，未提供/etc/ld.preload
* 劫持函数代码，采用了《揭秘家用路由器漏洞挖掘》提供的示例代码如下,在原有的基础上，增加printf来查看显示是否劫持成功。
```
#include<stdio.h>
#define MIB_HW_VER 0x250
#define MIB_IP_ADDR 170
#define MIB_CAPTCHA 0x2C1
int apmib_init(void){
        printf("helllo");
        return 1;
}
int fork(void){
        return 0;
}
void apmib_get(int code,int *value){
        switch(code){
                case MIB_HW_VER:
                        *value = 1;
                        break;
                case MIB_IP_ADDR:
                        *value = 1;
                        break;
                case MIB_CAPTCHA:
                        *value = 1;
                        break;
        }
        return;
}
//mips-linux-gcc -Wall -fPIC -shared apmib.c -o ibcjson.so
```
* 通过如下代码，给原有的boa二进制文件添加一个dynamic

```
#include<stdio.h>
#include <stdio.h>
#include <stdlib.h>

#include "elf.h"
#define PATCH "boa_patch"
int b2l(int be)
{
    return ((be >> 24) &0xff ) 
        | ((be >> 8) & 0xFF00) 
        | ((be << 8) & 0xFF0000) 
        | ((be << 24));    
}
char* buf = NULL;
int l2b(int le) {

    return (le & 0xff) << 24 
            | (le & 0xff00) << 8 
            | (le & 0xff0000) >> 8 
            | (le >> 24) & 0xff;
}
static char *_get_interp(char *buf)
{
   int x;

   // Check for the existence of a dynamic loader
   Elf_Ehdr *hdr = (Elf_Ehdr *)buf;
   Elf_Phdr *phdr = (Elf_Phdr * )(buf + l2b(hdr->e_phoff));   
   printf("the phdr address is: 0x%x 0x%x 0x%x 0x%x\n",phdr,l2b(hdr->e_phoff),buf,sizeof(hdr->e_phoff));
   for(x = 0; x < hdr->e_phnum; x++){
      if(l2b(phdr[x].p_type) == PT_DYNAMIC){
         // There is a dynamic loader present, so load it
         return buf + l2b(phdr[x].p_offset);
      }
   }

   return NULL;
}
int mem_cpy(char* src,char* dst,int len){
    printf("the src addr is %x , %x\n",src-buf,dst-buf);
    for(int x=0;x<len;x++){
        dst[x]=src[x];
    }
    return 0;
}
/*
1 2 3 4

temp = 2
strcpy(1,2)
1 2
strcpy()

*/
void move_dynamic(char* buf){
    int x = 0;
    Elf32_Dyn* dyn = (Elf32_Dyn *)buf;
    //Elf32_Dyn tmp_dyn;
    //mem_cpy()
    while(1){
        if(dyn[x].d_tag == 0 && dyn[x].d_un.d_ptr == 0){
            printf("the x is %d\n",x);
            break;
        }
        x++;
        if(x>100) {
            printf("Error break\n");
            break;
        }
    }
    while(x--){
        //printf("the index x is %x\n",x);
        mem_cpy(&dyn[x],&dyn[x+1],8);
    }
    dyn[x+1].d_un.d_val = b2l(l2b(dyn[x+1].d_un.d_val) + 1);
    //FILE* fw = fopen("")
}
void analyse(char* buf){
    char* phdr_address = NULL;
    phdr_address = _get_interp(buf);
    printf("phdr address:  0x%x\n",phdr_address-buf);
    move_dynamic(phdr_address);

}
void save_binary(char* buf,int size){
    FILE* fw = fopen(PATCH,"wb");
    fwrite(buf,size,1,fw);
    fclose(fw);
}
int main(int argc,char *argv[],char* envp[]){
    if(argc < 2){
        printf("not enough argc\n");
    }
    FILE* fp = fopen(argv[1],"rb");

    fseek(fp,0,SEEK_END);
    int size = ftell(fp);
    fseek(fp, 0L, SEEK_SET);
    buf = malloc(size);
    fread(buf,size,1,fp);
    analyse(buf);
    save_binary(buf,size);
    free(buf);
    return 0;

}
```
* Makefile如下
```
all: elf.h analyse_ph.c
	gcc analyse_ph.c -m32 -g3 -o analyse
	./analyse boa_real_n210
```
* 针对N210RE 的测试截图如下，通过export LD_LIBRARY_PATH使得程序加载ibcjson.so，成功劫持boa，输出helllo
![6.png](https://www.iotsec-zone.com/images/MdImg/4fe6434dc35e9a68756426e86940d989.png)
### 总结
* 该方案直接对二进制文件的DYNAMIC  Segment段进行修改，利用dynamic和elf_hash之间的空余区域，在其上伪造dynamic的数组，该方案的主要限制点在于dynamic和elf_hash之间的空余区域的大小。
## 函数Patch
以上两种方式均是针对对应的函数进行劫持，使得程序在跳转到对应函数时，对其进行劫持，针对函数的patch则是在原函数上，针对函数指令进行更改。
### 方案一 指令patch
* 一个简单的patch 脚本，针对函数调用直接在对应位置上打\x00 patch绕过一些会使得程序崩溃的函数。
* 在分析出具体需要patch的位置上，通过\x00来直接进行patch

``````
patch_file = "bin/sysconf"
f = open(patch_file,'rb')
data = f.read()
patch_file_p = patch_file + '_patch.bak'
fi = open(patch_file_p,'wb')
fi.write(data)
def patch(poi,content):
    fi.seek(poi)
    fi.write(content)

if __name__ == "__main__":
    base =0x400000
    poi = 0x0401B20 - 0x0400000
    patch(poi,b'\x10')
    #poi = 0x77F96EB4 - base
    poi = 0x401B60 - base
    patch(poi,b'\x00\x00\x00\x00')
    poi = 0x0401E88 - base
    patch(poi,b'\x00\x00\x00\x00')
    poi = 0x401E90 - base
    patch(poi,b'\x00\x00\x00\x00')
``````

### 方案二 函数patch
* 通过mips-linux-gcc 编译要劫持的函数

```
#include<stdio.h>
#include<stdlib.h>
#define MIB_HW_VER 0x250
#define MIB_IP_ADDR 170
#define MIB_CAPTCHA 0x2C1
int apmib_init(void){
	return 1;
}
int fork(int a, int b,int c, int d){
	///int k = a + b +c +d;
	//printf("%d",k);
	if(a+b+c+d==-1) return 1;
	return 0;
}
void apmib_get(int code,int *value){
	switch(code){
		case MIB_HW_VER:
			*value = 1;
			break;
		case MIB_IP_ADDR:
			*value = 1;
			break;
		case MIB_CAPTCHA:
			*value = 1;
			break;
	}
	return;
}
//mips-linux-gcc -fPIC -shared -o apmib-ld.so apmib.c
```
● 通过angr对apmib-ld.so进行分析，并提取出对应函数的字节码并patch到原apmib.so上
● get_func_offset 函数从要patch的链接库上提取指定函数的偏移
● get_patch_func_code 函数从编译后的apmib-ld.so上提取patch的字节码
● patch函数对原链接库进行patch
● 以下是patch的整个流程

```
import angr
from sqlalchemy import all_
from capstone import *
from capstone.mips import *

class PatchMachaine():
    def __init__(self,hk_fi_na:str,pt_fi_na:str) -> None:
        self.hook_file = hk_fi_na
        self.patch_file = pt_fi_na
        self.hook_project = angr.Project(self.hook_file,load_options={"auto_load_libs": False})
        self.patch_project = angr.Project(self.patch_file,load_options={"auto_load_libs": False})
        self.hook_function = []
        self.patch_file_fi = open(pt_fi_na+"_patch","wb")
        self.hook_file_fi = open(pt_fi_na,"rb")
        self.binary = self.hook_file_fi.read()
        self.patch_file_fi.write(self.binary)
    def add_hook_function(self,func_name:str):
        self.hook_function.add(func_name)
    def print_insn_detail(self,insn):
    # print address, mnemonic and operands
        print( ''.join(format(x, '02x') for x in insn.bytes))
        print("0x%x:\t%s\t%s" % (insn.address, insn.mnemonic, insn.op_str))

    # "data" instruction generated by SKIPDATA option has no detail
        if insn.id == 0:
            return
    def view_disasm(self,func_name:str):
        MIPS_CODE = self.get_patch_func_code(func_name)
        all_tests = ((CS_ARCH_MIPS, CS_MODE_MIPS32 + CS_MODE_BIG_ENDIAN, MIPS_CODE, "MIPS-32 (Big-endian)"),)
        for (arch, mode, code, comment) in all_tests:
            print("*" * 16)
            print("Platform: %s" % comment)
            #print("Code: %s" % to_hex(code))
            print("Disasm:")
            try:
                md = Cs(arch, mode)
                md.detail = True
                for insn in md.disasm(code, 0x688):
                    self.print_insn_detail(insn)
                print("0x%x:\n" % (insn.address + insn.size))
            except CsError as e:
                print("ERROR: %s" % e)
    def get_patch_func_code(self,func_name:str):
        cfg_func = self.hook_project.analyses.CFG(normalize=True)
        func = cfg_func.functions.function(name=func_name)
        all_bytes = b''
        for x in sorted(func.blocks,key=lambda s:s.addr):
            all_bytes += x.bytes
        return all_bytes
    def get_func_offset(self,func_name):
        cfg_func = self.patch_project.analyses.CFG(normalize=True)
        func = cfg_func.functions.function(name=func_name)
        #Todo get tht patch file function size
        return func.offset,func.size
    def patch(self,func_name):
        
        poi,size = self.get_func_offset(func_name)
        self.patch_file_fi.seek(poi)
        self.patch_file_fi.write(self.get_patch_func_code(func_name).ljust(size,b"\x00"))
        pass
    def fi_close(self):
        self.patch_file_fi.close()

dir605_machine = PatchMachaine("apmib-ld.so",'lib/apmib.so')  
dir605_machine.patch("apmib_init")
dir605_machine.patch("apmib_get")
dir605_machine.fi_close()
#dir605_machine.view_disasm("apmib_get")
libc_machine = PatchMachaine("apmib-ld.so",'lib/libc.so.0')
libc_machine.patch('fork')
libc_machine.fi_close()
```
### 测试
* 针对该方案的patch，使用qemu-user以及mips虚拟机运行分别如下
* 在mips虚拟机中patch三个函数，可以正常运行boa程序
![7.png](https://www.iotsec-zone.com/images/MdImg/4c9ba91e91775e798b55b636c4daf8a8.png)
* 不patch fork的情况下，通过qemu-user在可以正常运行，但是log显示不一致,没有出现sh: can't ....后续的日志
![8.png](https://www.iotsec-zone.com/images/MdImg/d7d7c36283540c856f872fb4b20bfc5e.png)
### 总结
* 直接针对函数的patch，可以实现特定函数的劫持，但是该方式的patch下，无法加入一些动态库函数来输出，比如apmib_init原有劫持的过程中添加了printf("helllo")等
* 针对fork函数的patch，在实际qemu-user运行的过程中会导致程序异常退出
