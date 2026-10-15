# 物联网安全之qiling框架初探
> Pachimker
> 来源：https://www.iotsec-zone.com/article/391

# 背景
Qiling Framework是一个基于Python的二进制分析、模拟和虚拟化框架。它可以用于动态分析和仿真运行不同操作系统、处理器和体系结构下的二进制文件。除此之外，Qiling框架还提供了易于使用的API和插件系统，方便使用者进行二进制分析和漏洞挖掘等工作。其创始人是一名IoT Hacker，创建qiling的初衷便是解决在研究IoT时遇到的种种问题，这也是为什么上一小节说qiling框架比unicorn框架更加适合IoT研究初学者。

# qiling使用基础

qiling框架和AFLplusplus安装

```
sudo apt-get update
sudo apt-get install -y build-essential python3-dev automake cmake git flex bison libglib2.0-dev libpixman-1-dev python3-setuptools cargo libgtk-3-dev
sudo apt-get install -y lld-14 llvm-14 llvm-14-dev clang-14
sudo apt-get install -y gcc-$(gcc --version|head -n1|sed 's/\..*//'|sed 's/.* //')-plugin-dev libstdc++-$(gcc --version|head -n1|sed 's/\..*//'|sed 's/.* //')-dev
pip3 install qiling
git clone https://github.com/AFLplusplus/AFLplusplus
make -C AFLplusplus
cd AFLplusplus/unicorn_mode
./build_unicorn_support.sh

```

### 程序仿真

首先我们需要克隆qiling仓库，仓库中一些实例脚本可供我们学习。

```
git clone --recurse-submodules https://github.com/qilingframework/qiling.git

```

  一个简单的示例：

```
#include <stdio.h>
#include <stdlib.h>
# gcc test.c -o test
# 注意：编译程序的主机libc需要与rootfs glibc版本(libc-2.7.so)相对应，其他架构同理
int main(){
   printf("hello world!");
   return 0;
}

```

使用qiling编写一个简单的仿真脚本。

```
from qiling import *
from qiling.const import QL_VERBOSE
# 导入qiling模块和qiling.const模块中的QL_VERBOSE常量

if __name__ == "__main__":
   #创建Qiling对象，实例中三个参数分别为：path(仿真程序路径)、rootfs(仿真程序文件系统目录)和verbose(输出信息参数),除此外还可以设置env和log_plain参数。
  ql = Qiling(["./x8664_linux_symlink/test"], "./x8664_linux_symlink",verbose=QL_VERBOSE.DEBUG)
   #运行Qiling对象的run()方法，开始执行仿真程序
  ql.run()

```

这里的verbose(输出信息参数)有如下级别及其作用:

![0.png](https://www.iotsec-zone.com/images/MdImg/62539577cbdedb4ee828e6b06a23202b.png)

![1.png](https://www.iotsec-zone.com/images/MdImg/1acf135b7398c7ca0cb402d387c0f84c.png)

### VFS劫持

  x86_fetch_urandom程序的作用为打开/dev/urandom文件，生成随机数。当qiling仿真x86_fetch_urandom程序时，环境需要用到仿真文件系统，我们就需要用到VFS劫持，这样就可以模拟修改文件系统。下面的代码中为仿真虚拟路径 "/dev/urandom" 会被映射到宿主系统上的现有"/dev/urandom"文件。当模拟程序将访问 /dev/random 时，将改为访问映射文件。

```
from qiling import Qiling

if __name__ == "__main__":
  ql = Qiling(["x86_linux/bin/x86_fetch_urandom"], "x86_linux")

  ql.add_fs_mapper(r'/dev/urandom', r'/dev/urandom')
  ql.verbose=0
  ql.run()
```

![2.png](https://www.iotsec-zone.com/images/MdImg/baf48e00590ea094438d4f034ab79029.png)

如果我们想要控制虚拟文件'/dev/urandom'的交互结果，可以继承QlFsMappedObject类，并可自定义read、write、fstat、ioctl、readline等方法。

```
from qiling import Qiling
from qiling.os.mapper import QlFsMappedObject

class FakeUrandom(QlFsMappedObject):
  def read(self, size: int) -> bytes:
      return b"\x01" #可以修改读取返回结果

  def fstat(self) -> int:
      return -1

  def close(self) -> int:
      return 0

if __name__ == "__main__":
  ql = Qiling(["x86_linux/bin/x86_fetch_urandom"], "x86_linux")
  ql.add_fs_mapper(r'/dev/urandom', FakeUrandom())
  ql.run()

```

![3.png](https://www.iotsec-zone.com/images/MdImg/0334f49ca58d445a96ec8f4331e53643.png)

### 函数hook

下面示例中，我们给str1和str2俩个变量内存中分别复制"abcdef"和"ABCDEF"字符串。正常执行完毕后会打印出"str1 大于 str2"。我们可以使用qiling框架劫持strcmp实现为hook strcmp函数的效果，使其执行到不同分支的结果。

```
#include <stdio.h>
#include <string.h>

//cd ./x8664_linux/
//gcc demo.c -o test

int main ()
{
  char str1[15];
  char str2[15];
  int ret;

  strcpy(str1, "abcdef");
  strcpy(str2, "ABCDEF");
  ret = strcmp(str1, str2);

  if(ret < 0)
  {
     printf("str1 小于 str2");
  }
  else if(ret > 0)
  {
     printf("str1 大于 str2");
  }
  else
  {
     printf("str1 等于 str2");
  }
  return(0);
}

```

 以下代码为hook strcmp函数，并通过修改rax寄存器改变执行流程。

```
from qiling import *
from qiling.const import *

# 自定义strcmp hook函数。当程序执行strcmp函数退出时，会调用此函数，并且在比较完毕后，将 rax 寄存器的值修改为 0，表示相等。
def hook_strcmp(ql,*args):
# qiling框架的寄存器取值为ql.arch.reg.xxx
  rax = ql.arch.regs.rax
  print("hook_addr_rax:",hex(rax))
  ql.arch.regs.eax = 0 # 0:等于; -1:小于 ;1:大于

# 使用 ql.os.set_api 函数为 strcmp 设置hook函数，第一个参数为要hook的函数名，第二个参数为自定义hook函数，第三个参数为hook类型，这里为退出时触发hook函数。
def hook_func(ql):
  ql.os.set_api('strcmp',hook_strcmp,QL_INTERCEPT.EXIT) # 也可以使用ql.hook_address()函数进行hook，使用方法为ql.hook_address(hook_strcmp,0xXXXXXXXX)

if __name__ == "__main__":
  ql = Qiling(["./x8664_linux/test"],"./x8664_linux",verbose=QL_VERBOSE.DEBUG)
  hook_func(ql)
  #ql.debugger = "gdb:0.0.0.0:12345"
  ql.run()
```

![4.png](https://www.iotsec-zone.com/images/MdImg/bca60416103466356ba25118e1f03fd0.png)

定义hook函数时hook类型参数有以下三种：

![5.png](https://www.iotsec-zone.com/images/MdImg/a4120f29049ba4ee37547b518d237cc6.png)

# qiling使用实例

### 使用qiling解密CTF赛题

   当我们掌握了最基础的三个用法后，我们可以测试一个简单的例子来加深对qiling框架的理解。以上一小节中unicorn解密ctf题目为例，我们先简单写一个运行脚本。这里的ql.debugger="gdb:0.0.0.0:12345"为开启gdbserver服务，我们可以使用ida或者gdb进行调试。

![6.png](https://www.iotsec-zone.com/images/MdImg/5c4aeab00c3a1c3743c38901d52fa176.png)

 简单运行后发现程序和上一小节中unicorn的运行状况类似。由于这里我设置了multithead为True，所以这里会比上一小节中unicorn的解密速度快不少。但是还是在有限时间内只输出4个字符。

![7.png](https://www.iotsec-zone.com/images/MdImg/81607077d6c0e6ce4217ef375928fba5.png)

  当我们将verbose设置为QL_VERBOSE.DISASM便可观察模拟执行的汇编指令，根据汇编指令我们明显看到程序在call 0x400670处进行了递归调用(或使用调试器调试查看)，导致解密时间非常长。所以我们需要进行代码优化，思路为使用栈空间来保存一个不同输入参数以及对应计算结果的字典来避免重复计算。

![8.png](https://www.iotsec-zone.com/images/MdImg/ba6fc03c9bcd699f24d0bf35133b2e8c.png)

这里qiling由于是由unicorn开发而来，所以很多用法和unicorn相似。

```
from qiling import *
from qiling.const import *
from pwn import *

def hook_start(ql):
    arg0 = ql.arch.regs.rdi
    r_rsi = ql.arch.regs.rsi
    arg1 = u32(ql.mem.read(r_rsi,4))
    if (arg0,arg1) in direct:
        (ret_rax,ret_ref) = direct[(arg0,arg1)]
        ql.arch.regs.rax = ret_rax
        ql.mem.write(r_rsi,p32(ret_ref))
        ql.arch.regs.rip = 0x400582
    else:
        ql.arch.stack_push(r_rsi)
        ql.arch.stack_push(arg1)
        ql.arch.stack_push(arg0)

def hook_end(ql):
    arg0 = ql.arch.stack_pop()
    arg1 = ql.arch.stack_pop()
    r_rsi = ql.arch.stack_pop()
    ret_rax = ql.arch.regs.rax
    ret_ref = u32(ql.mem.read(r_rsi,4))
    direct[(arg0,arg1)] = (ret_rax,ret_ref)

def solve(ql):
    start_address = 0x400670
    end_address = 0x4006f1
    end_address2 = 0x400709
    ql.hook_address(hook_start,start_address)
    ql.hook_address(hook_end,end_address)
    ql.hook_address(hook_end,end_address2)

if __name__ == '__main__':
    path = ["./x8664_linux_symlink/test"]
    rootfs = "./x8664_linux_symlink"
    direct = {}
    ql = Qiling(path, rootfs,verbose=QL_VERBOSE.DEFAULT)
    solve(ql)
    ql.run()

```

运行后便会打印出解密结果。

![9.png](https://www.iotsec-zone.com/images/MdImg/d6eeef9836d9ffbd65a3900540097645.png)

  除了上一小节中的ctf题目掌握qiling的使用外，我们还可通过qilinglab来加深对qiling框架的使用。qilingLab是由11个小挑战组成的二进制程序，用来帮助新手快速熟悉和掌握 Qiling 框架的基本用法。官方提供了aarch64程序的解题方法，我们根据这个作为参考解密一下x86_64架构的练习程序。

  x86_64程序下载(https://www.shielder.com/attachments/qilinglab-x86_64)

   首先运行程序，给我们提示，challenges会造成程序崩溃，只有当我们解出相应challenge后才会显示信息。

![10.png](https://www.iotsec-zone.com/images/MdImg/110c7a06b587ef8f41f73e88e31c2a6a.png)

我们可以通过ida逆向以及编写qiling脚本进行动态调试来完成这些challenge。

![11.png](https://www.iotsec-zone.com/images/MdImg/88f2ad6868e1594d882cb3fc2ca5c8f4.png)

最终的解密脚本如下：

```
from qiling import *
from pwn import *
from qiling.const import *
from qiling.os.mapper import QlFsMappedObject
import os
import struct

def hook_cpuid(ql, address, size):
    if ql.mem.read(address, size) == b'\x0F\xA2':
        regs = ql.arch.regs
        regs.ebx = 0x696C6951
        regs.ecx = 0x614C676E
        regs.edx = 0x20202062
        regs.rip += 2

def challenge11(ql):
    begin, end = 0, 0
    for info in ql.mem.map_info:
        #print("=====")
        #print(info)
        #print("=====")
        if info[2] == 5 and 'qilinglab-x86_64' in info[3]:
            begin, end = info[:2]
            #print("begin_addr",begin)
            #print("end_addr",end)
    ql.hook_code(hook_cpuid, begin=begin, end=end)

class cmdline(QlFsMappedObject):
    def read(self, expected_len):
        return b'qilinglab'

    def close(self):
        return 0

def challenge10(ql):
    ql.add_fs_mapper('/proc/self/cmdline', cmdline())

def hook_tolower(ql):
    return 0

def challenge9(ql):
    ql.os.set_api('tolower', hook_tolower)

def find_and_patch(ql, *args, **kw):
    MAGIC = 0x3DFCD6EA00000539
    magic_addrs = ql.mem.search(p64(MAGIC))
    #print("magic_address:",hex(magic_addrs))

    for magic_addr in magic_addrs:
        malloc1_addr = magic_addr - 8
        malloc1_data = ql.mem.read(malloc1_addr, 24)
        string_addr, _ , check_addr = struct.unpack("QQQ",malloc1_data)

        if ql.mem.string(string_addr) == "Random data":
            ql.mem.write(check_addr, b"\x01")
            break

def challenge8(ql):
    base_addr = ql.mem.get_lib_base(os.path.split(ql.path)[-1])
    #print("base_addr",hex(base_addr))
    ql.hook_address(find_and_patch, base_addr+0xFB5)

def hook_sleep(ql):
    return 0

def challenge7(ql):
    ql.os.set_api('sleep',hook_sleep)

def hook_rax(ql):
    ql.arch.regs.rax = 0

def challenge6(ql):
    base_addr = ql.mem.get_lib_base(os.path.split(ql.path)[-1])
    #print("base_addr",hex(base_addr))
    hook_addr = base_addr + 0xF16
    ql.hook_address(hook_rax, hook_addr)

def hook_rand(ql):
    ql.arch.regs.rax = 0

def challenge5(ql):
    ql.os.set_api('rand',hook_rand)

def enter_forbidden_loop_hook(ql):
    ql.arch.regs.eax = 1

def challenge4(ql):
    base = ql.mem.get_lib_base(os.path.split(ql.path)[-1])
    hook_addr = base + 0xE43
    print("qiling binary hookaddr:",hex(hook_addr))
    ql.hook_address(enter_forbidden_loop_hook, hook_addr)

class FakeUrandom(QlFsMappedObject):
    def read(self, size: int) -> bytes:
        if size == 1:
            return b"\x42"
        else:
            return b"\x41" * size

    def close(self) -> int:
        return 0

def hook_getrandom(ql, buf, buflen, flags):
    if buflen == 32:
        data = b'\x41' * buflen # b'\x41' = A
        ql.mem.write(buf, data)
        ql.os.set_syscall_return(buflen)
    else:
        ql.os.set_syscall_return(-1)

def challenge3(ql):
    ql.add_fs_mapper(r'/dev/urandom', FakeUrandom())
    ql.os.set_syscall("getrandom", hook_getrandom)

def my_uname_on_exit_hook(ql, *args):
    rdi = ql.arch.regs.rdi
    print(f"utsname address: {hex(rdi)}")
    ql.mem.write(rdi, b'QilingOS\x00')
    ql.mem.write(rdi + 65 * 3, b'ChallengeStart\x00')

def challenge2(ql):
    ql.os.set_api("uname", my_uname_on_exit_hook, QL_INTERCEPT.EXIT)

def challenge1(ql):
    ql.mem.map(0x1000, 0x1000, info='challenge1')
    ql.mem.write(0x1337, p16(1337))
 
if __name__ == '__main__':
    path = ["./x8664_linux/qilinglab-x86_64"]
    rootfs = "./x8664_linux"
    ql = Qiling(path, rootfs,verbose=QL_VERBOSE.OFF)
    challenge1(ql)
    challenge2(ql)
    challenge3(ql)
    challenge4(ql)
    challenge5(ql)
    challenge6(ql)
    challenge7(ql)
    challenge8(ql)
    challenge9(ql)
    challenge10(ql)
    challenge11(ql)
    #ql.debugger = "gdb:0.0.0.0:12345"
    ql.run()

```

运行后，所有的challenge都会显示SOLVED。

![12.png](https://www.iotsec-zone.com/images/MdImg/05addf9867de3939c6c86cdb63c52c41.png)

### qiling设备仿真

 qiling提供了路由器仿真案例，该脚本路径为qiling/example路径下

```
#!/usr/bin/env python3
# 1. Download AC15 Firmware from https://down.tenda.com.cn/uploadfile/AC15/US_AC15V1.0BR_V15.03.05.19_multi_TD01.zip
# 2. unzip
# 3. binwalk -e US_AC15V1.0BR_V15.03.05.19_multi_TD01.bin
# 4. locate squashfs-root
# 5. rm -rf webroot && mv webroot_ro webroot
#
# notes: we are using rootfs in this example, so rootfs = squashfs-root
#
import os, socket, threading
import sys
sys.path.append("../../../")
from qiling import Qiling
# 从qiling.const中导入QL_VERBOSE，指定qiling的日志输出级别
from qiling.const import QL_VERBOSE

# 定义patcher函数，用于跳过网卡信息检测。在前面小节我们仿真tenda路由器时，路由器httpd程序在初始化网络时会检查网卡名称是否为br0。这里脚本直接将代码执行前内存中的br0字符串替换成了lo，从而跳过检查。
def patcher(ql: Qiling):
    br0_addr = ql.mem.search("br0".encode() + b'\x00')
    for addr in br0_addr:
        ql.mem.write(addr, b'lo\x00')

# 定义nvram_listener函数，使用该函数监听Unix套接字，并在收到消息时返回数据。
def nvram_listener():
    server_address = 'rootfs/var/cfm_socket'
    data = ""
    try:
        os.unlink(server_address)
    except OSError:
        if os.path.exists(server_address):
            raise

    sock = socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
    sock.bind(server_address)
    sock.listen(1)
    while True:
        connection, _ = sock.accept()
        try:
            while True:
                data += str(connection.recv(1024))
                if "lan.webiplansslen" in data:
                    connection.send('192.168.170.169'.encode())
                else:
                    break
                data = ""
        finally:
            connection.close()

# 定义myvfork函数，仿真程序在执行系统调用vfork时被调用，返回值0。
def myvfork(ql: Qiling):
    regreturn = 0
    ql.log.info("vfork() = %d" % regreturn)
    return regreturn
# 仿真主函数，生成qiling实例和添加VFS映射。
def my_sandbox(path, rootfs):
    print("path:",path)
    print("rootfs",rootfs)
    ql = Qiling(path, rootfs, verbose=QL_VERBOSE.DEBUG)
    print("ql:",ql)
    ql.add_fs_mapper("/dev/urandom","/dev/urandom")
    ql.hook_address(patcher, ql.loader.elf_entry)
    ql.debugger = False
    if ql.debugger == True:
        ql.os.set_syscall("vfork", myvfork) # vfork函数返回0时，debugger可正常调试。
    ql.run()

if __name__ == "__main__":
  # 创建后台运行的线程并执行，以便收到Unix套接字的消息时进行响应。
    nvram_listener_therad = threading.Thread(target=nvram_listener, daemon=True)
    nvram_listener_therad.start()
  # 运行仿真实例
    my_sandbox(["rootfs/bin/httpd"], "rootfs")

```

当我们运行脚本后，会显示路由器的ip和端口，当我们发现本地的8080正在监听时，说明设备已经仿真成功。

![13.png](https://www.iotsec-zone.com/images/MdImg/60ebb5889646ccc79d213b3f722c6bdf.png)

 仿真成功后可访问[http://localhost:8080查看效果：](http://localhost:8080查看效果：)

![14.png](https://www.iotsec-zone.com/images/MdImg/d322577de445c6ed85f5a075283ddbfa.png)

 在后面的小节中，我们会学习对仿真路由器设备进行fuzz。其中最为重要的一步便是编写仿真脚本，后续在我们分析好固件程序中要fuzz地址范围后，只有仿真设备可以顺利触发保存快照的功能，才可保证fuzz的正确性。

### qiling fuzz

  qiling框架可以使用AFLplusplus对arm架构程序进行fuzz测试，测试代码如下：

```
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
// Program that will crash easily.
#define SIZE (10)

int fun(int i)
{
    char *buf = malloc(SIZE);
    char buf2[SIZE];
    
    while ((*buf = getc(stdin)) == 'A')
    {
        buf[i++] = *buf;
    }
    strncpy(buf2, buf, i);
    puts(buf2);
    return 0;
}

int main(int argc, char **argv)
{
    return fun(argc);
}

```

qiling提供的fuzz脚本如下：

```
#!/usr/bin/env python3
"""
Simple example of how to use Qiling together with AFLplusplus.
This is tested with the recent Qiling framework (the one you cloned),
afl++ from https://github.com/AFLplusplus/AFLplusplus

After building afl++, make sure you install `unicorn_mode/setup_unicorn.sh`

Then, run this file using afl++ unicorn mode with
afl-fuzz -i ./afl_inputs -o ./afl_outputs -m none -U -- python3 ./fuzz_x8664_linux.py @@
"""
                                                                                                                                                                                              
# No more need for importing unicornafl, try ql.afl_fuzz instead!

import sys, os
from binascii import hexlify
sys.path.append("../../..")
from qiling import *
from qiling.extensions import pipe
from qiling.extensions.afl import ql_afl_fuzz

def main(input_file, enable_trace=False):
    ql = Qiling(["./arm_fuzz"], "../../rootfs/arm_qnx", console=enable_trace)
    # 设置ql的标准输入为进程的标准输入
    ql.os.stdin = pipe.SimpleInStream(sys.stdin.fileno())
  # 如果没有启用控制台追踪，则将标准输出和标准错误流设置为Null
    if not enable_trace:
        ql.os.stdout = pipe.NullOutStream(sys.stdout.fileno())
        ql.os.stderr = pipe.NullOutStream(sys.stderr.fileno())

    def place_input_callback(ql: Qiling, input: bytes, _: int):
      # 设置fuzz输入点
        ql.os.stdin.write(input)
        return True

    def start_afl(_ql: Qiling):
      # 设置fuzz实例
        ql_afl_fuzz(_ql, input_file=input_file, place_input_callback=place_input_callback, exits=[ql.os.exit_point])

  # 获取libc的基地址
    LIBC_BASE = int(ql.profile.get("OS32", "interp_address"), 16)
    # 设置hook函数，用于处理SignalKill信号
    ql.hook_address(callback=lambda x: os.abort(), address=LIBC_BASE + 0x38170)
    # main函数地址
    main_addr = 0x08048aa0
    # 设置hook函数，在main函数运行时调用start_afl函数
    ql.hook_address(callback=start_afl, address=main_addr)
  
  # 若启用控制台追踪，则将设置相关信息输出
    if enable_trace:
        # The following lines are only for `-t` debug output
        md = ql.arch.disassembler
        count = [0]
        def spaced_hex(data):
            return b' '.join(hexlify(data)[i:i+2] for i in range(0, len(hexlify(data)), 2)).decode('utf-8')

        def disasm(count, ql, address, size):
            buf = ql.mem.read(address, size)
            try:
                for i in md.disasm(buf, address):
                    return "{:08X}\t{:08X}: {:24s} {:10s} {:16s}".format(count[0], i.address, spaced_hex(buf), i.mnemonic,
                                                                        i.op_str)
            except:
                import traceback
                print(traceback.format_exc())

        def trace_cb(ql, address, size, count):
            rtn = '{:100s}'.format(disasm(count, ql, address, size))
            print(rtn)
            count[0] += 1

        ql.hook_code(trace_cb, count)

    # okay, ready to roll.
    # try:
    ql.run()
    # except Exception as ex:
    # # Probable unicorn memory error. Treat as crash.
    # print(ex)
    # os.abort()
    os._exit(0) # that's a looot faster than tidying up.
                                                                                                                                                                                              

if __name__ == "__main__":
    if len(sys.argv) == 1:
        raise ValueError("No input file provided.")
    if len(sys.argv) > 2 and sys.argv[1] == "-t":
        main(sys.argv[2], enable_trace=True)
    else:
        main(sys.argv[1])

```

AFLplusplus执行脚本如下：

```
#!/usr/bin/sh
AFL_AUTORESUME=1 AFL_PATH="$(realpath ../../../AFLplusplus)" PATH="$AFL_PATH:$PATH" afl-fuzz -i afl_inputs -o afl_outputs -U -- python3 ./fuzz_arm_qnx.py @@

```

 运行后fuzz.sh后，便会出现afl++ 运行界面，等待几秒后便出现crash。

![15.png](https://www.iotsec-zone.com/images/MdImg/b110793b6c49f8eec9963f829f9ff01b.png)

  crash的变异数据存放在afl_outputs目录下，我们可以使用xxd id:000000,xxxxxx命令查看变异数据。

```
#xxd id:000000,sig:06,src:000000,time:4112,execs:1077,op:havoc,rep:8 
00000000: 4141 4141 4141 4141 4141 4141 ff7f 4241 AAAAAAAAAAAA..BA
00000010: 4141 4145 4141 be41 4dff 0000 0041 4141 AAAEAA.AM....AAA
00000020: 41

```

——The  End——

# 总结

在这一小节中，我们简单学习了qiling框架，我们使用ctf例题以及qilinglab的11个闯关题目进行练习，熟练掌握了qiling框架的基础使用。后面的小节中，我们将使用qiling框架对仿真设备进行实例fuzz测试。
