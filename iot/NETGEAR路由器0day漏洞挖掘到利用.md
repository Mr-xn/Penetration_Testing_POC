# NETGEAR路由器0day漏洞挖掘到利用
> 偏有宸机
> 来源：https://www.iotsec-zone.com/article/200

 # 前言
 为避免造成不必要的影响就不在文字中公布设备的具体型号与利用脚本，仅供学习交流
 
# 漏洞发现
再研究中发现由uhttpd二进制程序所支持的web服务中，当设置QoS优先级规则时
![0.png](https://www.iotsec-zone.com/images/MdImg/7df75e149bbd929d42537eb3ec06a174.png)
设置qos的Online Gaming参数aaps可以产生缓冲区溢出漏洞
![1.png](https://www.iotsec-zone.com/images/MdImg/ecadbba0a2328451093139c3420cdebb.png)
再gdb中观察可控制的寄存器如下
![2.png](https://www.iotsec-zone.com/images/MdImg/3e82da3cfc76f1beac0a21d11feccb6b.png)
poc执行前uhttpd进程pid，与执行后uhttpd进程pid对比后，可以确认uhttpd程序崩溃后便导致服务进行重新启动
![3.png](https://www.iotsec-zone.com/images/MdImg/f5e596018067d70006fe2d68d0e1aa85.png)

**系统中无法使用wget和tftp传输文件的解决方法**
这里我我使用的真机在测试过程中，发现通过ttl串口连接上路由器后，系统中存在的wget和tftp程序，也就无法进一步对程序进行动态调试
对此可以通过[http://192.168.1.1/BRS_index.htm](http://192.168.1.1/BRS_index.htm) 页面恢复路由器配置文件功能，修改功能完善的busybox后缀名为.cfg便可以绕过上传限制
![4.png](https://www.iotsec-zone.com/images/MdImg/fbd871a266e2ae00500f425ad68127ac.png)
上传完成后，进一步分析httpd程序的restore恢复配置文件过程中发现保存在了tmp目录下并被重命名为configs-restore.lrp
![5.png](https://www.iotsec-zone.com/images/MdImg/9ddb889b0df7e4302c97d7750b89c01c.png)
md5值确认过后，修改文件权限执行
![6.png](https://www.iotsec-zone.com/images/MdImg/1d56eb194ea8f2069ab918ed8cf6d73b.png)
 
# 漏洞利用

## 获取timestamp
由于前面构造的请求只能请求一次便会过期，因此猜测和post后的timestamp有关，在ida中进一步分析发现其值也是随机生成的，通过get_timestamp便可以直接得到，但是在我们使用python进行request请求时如何得到呢？
![7.png](https://www.iotsec-zone.com/images/MdImg/4ebd249e503ed9686e604cdf41407a14.png)
对此我们分析QOS_rule页面的请求链接发现，在我们对QOS_online进行get请求的时候便能获取到timestamp值，只要稍加处理，就可以用对apply.cgi的QOS_rule进行请求，执行poc
![8.png](https://www.iotsec-zone.com/images/MdImg/f09331fef2e82b1aef5cebee575de3d2.png)
通过python脚本实现
![9.png](https://www.iotsec-zone.com/images/MdImg/176cb9c18b4ad89caf98c76a94ce1dba.png)
 
## 构造Exp
在可以控制相关寄存器且拥有一定的调试环境后，便可以尝试构造EXP来进行漏洞利用
由于uhttpd程序的保护为全关状态，因此可以直接以ret2libc的方式来进行利用
![10.png](https://www.iotsec-zone.com/images/MdImg/a47ba0073e2b8d641faba3d2694290b0.png)
首先是在gdb中的vmmap确认程序的libc库加载基址为 0x2ab24000
 
在通过ida中的mipsrop插件来寻常构造rop所需的gadget
先是gadget1 通过`mipsrop.find("add $s0")`找到
```
0x00031228  |  addiu $s0,1   |  jalr  $s1     
```
通过该代码段我们可以看到将会对寄存器进行大量的传参过程，对此可以方便我们对寄存器进一步的控制
![11.png](https://www.iotsec-zone.com/images/MdImg/d83eb4f4474c38b9800bb323165243cf.png)
再然后寻找gadget2用来控制程序跳转跳转到我们想要执行的system
对此可以通过`mipsrop.stackfinders() `进行查找
```
0x000441E0  |  addiu $s2,$sp,0x50+var_1C |  jalr  $s3   
```
这个gadget的作用也很简单，控制前面布置好的s0到a0寄存器中，及前面布置好的s3（system函数）为t9，最后进行跳转至行
![12.png](https://www.iotsec-zone.com/images/MdImg/3931f3549abb2763050be6e2172b22f7.png)
这样大致所需要的gadget便已经备齐，对payload的构造便是如下
![13.png](https://www.iotsec-zone.com/images/MdImg/304d9c9de05b4ed86bc34db8436c96d5.png)
 
但需要注意的一点是，即我们要执行的bash命令字符串的地址，为了方便我将字符串放到了post请求的priority 参数里。
在测试过程中发现使用栈中的地址进行执行时，该地址会产生变化，导致寻找不到字符串
![14.png](https://www.iotsec-zone.com/images/MdImg/ce4fe13521cb400a2233b468730626e9.png)
对此我发现程序会将我们的请求内容数据同时保存在 libconfig.so文件中，且该地址也不会产生任何变化，因此直接使用该地址即可
![15.png](https://www.iotsec-zone.com/images/MdImg/42302f25bdf8200e80af517d79073105.png)
 
运行结果
![16.png](https://www.iotsec-zone.com/images/MdImg/6880dc3f6b9fc111cd5973a89ff84bf0.png)

 
