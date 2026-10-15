# 2022河南工业互联网安全大赛复赛-工控Writeup
> IOTsec-Zone
> 来源：https://www.iotsec-zone.com/article/307

## HNGK-流量分析
打开过滤mms，然后直接搜索flag发现有个列目录的返回结果。
![0.png](https://www.iotsec-zone.com/images/MdImg/19294178515b31910416094f27d4d5a5.png) 

再往下找有个fileOpen的操作。
![1.png](https://www.iotsec-zone.com/images/MdImg/bca06713a840ba65e03c9167640ddea8.png)

继续往后找也是上面这俩个操作，那么就过滤一下fileOpen的操作去拿打开后的标识符然后看看用哪了。

有4次打开操作。

![2.png](https://www.iotsec-zone.com/images/MdImg/58c879e9e87f2fd842b92c2d33ea1426.png)

那就过滤出这几个的返回包，拿到标识符。

![3.png](https://www.iotsec-zone.com/images/MdImg/5d52a7f96da78f17a3ab83caced43371.png)

不过有个返回包没解析出来，先不管，看看能不能用过滤出来的三个标识符找到其fileFead操作。

![4.png](https://www.iotsec-zone.com/images/MdImg/c152fc36e91a09e669126ac6a4275e16.png)

成功找到，那就看看这个请求的响应是什么。

结果没过滤出来东西。

![5.png](https://www.iotsec-zone.com/images/MdImg/24468502aebd0c7ca148a71b128122f0.png)
猜测是wireshark没解析成功，那就去掉过滤看看下一个包是什么，这个流量包里的请求和响应都是挨在一起的。

![6.png](https://www.iotsec-zone.com/images/MdImg/b28b4b8c260e1279083ce7d769b0693f.png)

似乎是因为长度没解析对。

反正看见base64格式的图片了，先提取出来。

发现图片内容就是flag。

![7.png](https://www.iotsec-zone.com/images/MdImg/a18f1b2f60814688f8178e4842dc34e8.png)

flag{ICS-mms104}

HNGK-MMS
拿到流量包后发现打不开，扔到010发现其实是个压缩包，于是再解压一次。

![8.png](https://www.iotsec-zone.com/images/MdImg/c22fc1c7392665a7c92d9fccc0767acf.png) 

遍历一遍mms，发现有两条请求的item比较奇怪。

![9.png](https://www.iotsec-zone.com/images/MdImg/2060138d18f3d977dcfca124bddae5af.png)

而66正好是f的ascii。

所以猜测可能是有位移，但是十六进制的字母必然不可能有ij这种东西，所以猜测可能是先把字母往小移，但是不知道具体偏移是多少，那就一个一个试过去，然后移完之后解一下hex看看能出来啥。

先从偏移为4开始，因为至少要4才能让ij移到ef这种合理的hex。

```python
import string
​
flag = bytearray(b"666i5250356j4249"b"616732557968356j")
for i in range(len(flag)):
    if flag[i] in string.ascii_lowercase.encode():
        flag[i] -= 4
print(flag)
print(bytes.fromhex(flag.decode()))
```
![10.png](https://www.iotsec-zone.com/images/MdImg/7c584ec1bfa5475942b8bee0cfe1046f.png)
但是好像没啥规律，继续尝试到偏移为6的时候发现fl和ag。

![11.png](https://www.iotsec-zone.com/images/MdImg/bcbd719c426ef1e254eea752205a4818.png)
尝试将前后半段每两字节拼接，得到`flagRP2U5myhBI5m`，拼上括号提交发现正确。

flag{RP2U5myhBI5m}

## HNGK-modbus
这题筛选modbus之后发现function是有规律循环的：17, 109, 65, 1, 1, 3, 3, 67。

![12.png](https://www.iotsec-zone.com/images/MdImg/6a3303ae122f121217c6ea1bbbef0055.png)

于是尝试提取发送方所有的func_code和帧id，然后跑一轮看看有没有多了或者少了的。

```
tshark -r .\modbus.pcap -Y "modbus && ip.src==172.31.14.123" -T fields -e "frame.number" -T fields -e "modbus.func_code" > data.txt
```
发现1648帧多了个1。

```
data = []
with open("data.txt", 'r') as f:
    for line in f:
        data.append(line.strip().split('\t'))
​
base = ['17', '109', '65', '1', '1', '3', '3', '67']
p = 0
for i in data:
    if i[1] != base[p % len(base)]:
        print(i)
    p += 1
```

![13.png](https://www.iotsec-zone.com/images/MdImg/5d6ee44647dd0d1e95afdc96ecbecc6a.png)

过去看了下发现确实是多了个1，不过上下对比一下发现实际上多出来的是1642数据包，因为这个1541在其他地方没出现过。

而1642数据包在提取结果里是539条，直接忽略这条再跑一遍看看还有没有异常的。
```
data = []
with open("data.txt", 'r') as f:
    for line in f:
        data.append(line.strip().split('\t'))
​
base = ['17', '109', '65', '1', '1', '3', '3', '67']
p = 0
for i in data:
    if p == 539:
        continue
    if i[1] != base[p % len(base)]:
        print(i)
    p += 1
```
直接跑完没有异常。

![14.png](https://www.iotsec-zone.com/images/MdImg/6b049d46c1eb19f59064e7f8b9377cb1.png)

尝试提交flag{1642}或者flag{1642+1643}但是都不对。

于是怀疑可能数据包异常点不是func而是其内容。

那么只能挨个func的数据筛选过去看看有没有异常了。

先把17给发送和返回过滤一遍：`(modbus.func_code == 17) && !(!modbus.data) && !(modbus.data == 06:00:00)`。

![15.png](https://www.iotsec-zone.com/images/MdImg/e19b6cdf65b9f5a7ca60ea79b838573d.png)

发现没有异常的，那就再看109的：`((modbus.func_code == 109) && !(modbus.data == 54)) && !(modbus.data == 00)`。

![16.png](https://www.iotsec-zone.com/images/MdImg/bac84fd9d00d2974ef132e75f3b3b202.png)

发现也没有，再看65的：((modbus.func_code == 65) && !(modbus.data == a8:b9:09:00:0c:01:06:02:06:03:06:04:06:05:06:06:06:07:06:00:06)) && !(modbus.data == 02:fe:00)。

![17.png](https://www.iotsec-zone.com/images/MdImg/8b0d46a2be3cdca4235e56038a5c5156.png)

还是没有，再看1的：`((((modbus.func_code == 1) && !(modbus.reference_num == 0)) && !(modbus.reference_num == 1536)) && !(frame[63] == 00)) && !(frame[63] == fe)`。

![18.png](https://www.iotsec-zone.com/images/MdImg/c3a8c4b1a928f0e054c89b34df08470a.png)

发现两对数据包有异常，比之前找的多了一对，所以实际上异常是多了一个和改了一个。

尝试提交flag{1642+5485}，发现正确。

flag{1642+5485}

## HNGK-奇怪的工控协议
看了下协议分布，最主要的modbus，不过`iec60870_104`和`iec60870_asdu`也不算少。

![19.png](https://www.iotsec-zone.com/images/MdImg/c9ceee2e6f79a0263c055cfe8f5f10b7.png)
在modbus里面翻了半天也没看到啥有用的东西，然后去iec60870_104翻了下直接发现了flag。

![20.png](https://www.iotsec-zone.com/images/MdImg/a34ff1aa2606b20b7d46239e57960ffd.png)

flag{sort__104}

 
