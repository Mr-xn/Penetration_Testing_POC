# 漏洞复现到简单0day漏洞挖掘
> splash
> 来源：https://www.iotsec-zone.com/article/139

# 漏洞复现到简单0day漏洞挖掘
## 漏洞信息
漏洞通告链接：[https://nvd.nist.gov/vuln/detail/CVE-2022-26258](https://nvd.nist.gov/vuln/detail/CVE-2022-26258)
IOTsec-zone社区漏洞复现：[https://iotsec-zone.com/article?id=123](https://iotsec-zone.com/article?id=123)
固件下载地址：[http://www.dlinktw.com.tw/techsupport/download.ashx?file=2663](http://www.dlinktw.com.tw/techsupport/download.ashx?file=2663)
## 漏洞分析
大佬已经分析过漏洞成因，[https://iotsec-zone.com/article?id=123](https://iotsec-zone.com/article?id=123)
下面是我自己复现分析的入手点
由漏洞信息得知，在路由的处理程序中`/lan.asp`，参数的值`Device Name`可以注入命令
知道漏洞触发位置，自行分析寻找漏洞点，匹配到ncc2二进制文件
![0.png](https://www.iotsec-zone.com/images/MdImg/1beb79dda98c07d525955f300070a92a.png)

放入IDA分析，搜索device
![1.png](https://www.iotsec-zone.com/images/MdImg/fb84fa0d4462e9158085277ef71c06d6.png)
_system()函数第四个参数，执行了拼接后的命令，而在前有hasInjectionString()过滤，在文件系统搜索相应字符串![2.png](https://www.iotsec-zone.com/images/MdImg/5bdf1e6ca91ea59110bb6f33633683fb.png)
![3.png](https://www.iotsec-zone.com/images/MdImg/428ac322db6aafd24566edd50ddb3e41.png)
分析libleopard.so，过滤了一些截断符，但是并没有过滤换行符


![4.png](https://www.iotsec-zone.com/images/MdImg/c6fa99884a75a4af268bdfa08b83ef79.png)
## 漏洞复现
使用FirmAe仿真固件
![5.png](https://www.iotsec-zone.com/images/MdImg/9fd2415c256dbf517713b44aabc01273.png)
可以成功复现漏洞，这里不贴图了，上述链接老哥有详细的复现过程
## 新漏洞挖掘
### 命令注入：
已知过滤函数没有过滤完全，通过查看hasInjectionString()函数引用寻找其他输入点

在nc22中，获取输入的ping_addr值，经过不完全的过滤，拼接后的字符串使用popen()执行，存在命令注入
![6.png](https://www.iotsec-zone.com/images/MdImg/9b2f53e069aa4fa462bd182a17726936.png)
对ping功能抓包，经测试，ping test和ipv6 ping test都存在命令注入，将ping_addr参数修改为%0Atelnetd%20-l%20%2Fbin%2Fsh%20-p%204444%0A，这个数据包cookie是比较简单的参数为1就行，经实际测试，无需最后的165参数（可能是时间戳）也可实现命令注入
![7.png](https://www.iotsec-zone.com/images/MdImg/fe7a710c910109cd41d2c3c42fcad1e3.png)
使用telnet连接目标4444端口，连接成功，获取设备shell，搜了一下，好像没有被提交过，算是捡的漏洞吧。
![8.png](https://www.iotsec-zone.com/images/MdImg/f2ed058b84a5bb64e3e67204001fd206.png)
### 拒绝服务：
由上可知已知get_entry_value_by_name()函数功能为获取用户输入
获取多个参数后未经长度判断，使用sprintf()拼接字符串，发送超长字符串即可造成溢出
![9.png](https://www.iotsec-zone.com/images/MdImg/974588c7e9bf8fdd1c9a7b29d7be21c4.png)
![10.png](https://www.iotsec-zone.com/images/MdImg/f5b4dbab9a26144520ad819d2d19c7b0.png)
![11.png](https://www.iotsec-zone.com/images/MdImg/4749732c64f9c343ec48792584f273b5.png)
此时已经无法登陆，由于是ncc2崩溃，也就是处理请求的二进制文件崩溃，http服务还正常，但已经不能处理请求了
## 总结
1、在找到命令注入漏洞后，存在过滤函数，说明开发者考虑到了注入风险，那么既然过滤不严格，其他输入点可能也存在过滤不严格的可能，此时通过查看过滤函数的引用去寻找其他可控输入点，会有可能发现更多的漏洞。
2、在确认获取用户输入的函数名后，通过查看引用，可以找到更多系统处理用户输入的路径，可能会发现其他参数的漏洞。


















