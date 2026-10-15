# uart提取固件合集 MW325R PT926G
> KDEV
> 来源：https://www.iotsec-zone.com/article/487

# 0x00 UART简介：
### 什么是UART？
通用异步接收器/发送器（Universal Asynchronous Receiver/Transmitter），通常称为UART，是一种广泛应用于嵌入式领域的串行、异步、全双工通信协议。
Uart在嵌入式开发中有很广泛的应用，其中之一就是开发板的固件烧录功能。
在常见的一些IOT设备中，它的作用主要是厂商预留的一些调试接口，一般可以通过跳线的方式连接这些uart串口，实现IOT设备的日志输出，固件升级降级等功能，有些还会开放根目录与u-boot的访问权限。
### 什么是u-boot
U-Boot是一款开源的引导加载程序（Bootloader），可用于嵌入式系统中。它由德国的DENX公司开发，支持多种处理器架构，包括ARM，MIPS，PowerPC等。 
由于其对各种架构处理器的支持，可裁剪等特点，是目前嵌入式领域应用最广泛的boot loader。
u-boot支持使用命令行操作，一般来说，未裁剪的u-boot有很多操作flash与内存的指令，允许用户读取或者写入内存或Flash，此外，u-boot还支持通过tftp启动代码的功能。
本文中就用到了一些u-boot指令用来提取固件。
# 0x01 水星MW325R固件提取
用USB-TTL模块连接水星路由器上的uart接口，由于板子上的串口并没有标出哪个是TX，RX，GND，所以这里我们用万用表来根据电器特性找出哪个是TX，RX。
根据电气特性，GND和3V3都比较好判断，电压表调到Beep档，将电源的地引脚与其中的几个引脚相连，阻值为0或者导通状态即可判断GND，RX是接收引脚，对地电压为0，TX是输出引脚，对地电压 一般为3.3V，还有一个3V3引脚，这里就是通过经验判断了，通常，大部分厂商在设计uart原理图的时候，它的引脚分布一般都是
```
VCC   或者    VCC
TX            GND
RX            TX
GND           RX
```
这样或者类似的顺序，TX和RX往往都是挨在一起，所以一般只要确定了GND和RX，就能试出来TX引脚是哪个。
最后我测出图中这里灰色是3V3，红色是GND，黄色是TX，橙色是RX

![0.png](https://www.iotsec-zone.com/api/image/v2/20250108/d6vywg34upwdggb8ei.png)
然后用下面这张图的方式将它和TTL模块上的引脚连接在一起。3V3可以不连

![1.png](https://www.iotsec-zone.com/api/image/v2/20250108/d6vywo0ljoszndxyec.png)
进入MobaXterm，选择Serial连接，串口号COM7，波特率57600，
上电之后查看串口的输出发现设备会自动跳转到u-boot命令行
```
Version = 2.0.
Task name = tCmdTask, pri = 8, stack size = 10240, max command entry num = 64.

command     description
--------------------------------------------------------------------
?           print all commands.
help        print all commands.
mem         show memory part, pools, and dump memory.
task        show task info and manage system task.
tftp        download or upload files by tftp protocol.
ifconfig    Interface config, please reference to -help command.
route       Show route table, delete/add special route entry.
arp         Show all arp entries, delete/add special arp entry.
net         Show net runtimes.
track       Show conntrack runtimes, modify conntrack environments.
register    register show.
packet      packet show.
flash       Print flash layout, read/write/erase specify flash.
port        manage all udp/tcp packet ports.
mcb         Show mcb pools or blocks.
bridge      Show all bridge stations.
nat         Show nat runtimes.
system      reboot, reset or firmware.
wioctl      Wlan command line utility.
iwpriv      MTK Wlan command line utility.
wpkt        MTK WiFi Tx mem pool monitor utility.
--------------------------------------------------------------------
#

```
输入help，根据输出结果可以看到这是一个阉割版的u-boot命令行
如果有md命令，则可以用md显示出内存的数据从而提取出固件来
但是这里没有md命令，我们可以用flash 和mem -dunmp来获取固件
先用`flash -layout`获取flash 表的偏移量，得到固件位置位于`0xd000`到`0xfa000`这一区间
```
# flash -layout

Version: 2.0
Name: FlashIo
Total Size(K): 1024
Erase Sector Size(K): 4
Block Num: 6.
==================================================
Flash Layout:
|------------------------| 0x00000000(0K)
|                        |
|                        |
|BOOTIMG(52K)            |
|                        |
|                        |
|------------------------| 0x0000d000(52K)
|                        |
|                        |
|FIRMWARE(948K)          |
|                        |
|                        |
|------------------------| 0x000fa000(1000K)
|CONFIG(8K)              |
|------------------------| 0x000fc000(1008K)
|EXPLOG(8K)              |
|------------------------| 0x000fe000(1016K)
|PROFILE(4K)             |
|------------------------| 0x000ff000(1020K)
|RADIO(4K)               |
|------------------------| 0x00100000(1024K)
#
```

然后再内存中找一片空白的区域作为缓冲区
`mem -show` 得到内存的排布表
```
# mem -show

FREE LIST:
   num    addr       size
  ---- ---------- ----------
     1 0x801f57a0      15984
     2 0x807f3810      22304
     3 0x807f3690         96
     4 0x801fb980         48
     5 0x8017a820     503344
     6 0x806eb0c0        176
     7 0x805d0520         16
     8 0x8046eac0         80
     9 0x801f56a0         80

SUMMARY:
 status    bytes     blocks   avg block  max block
 ------ ---------- --------- ---------- ----------
current
   free     542128         9      60236     503344
  alloc    6296064       935       6733          -
cumulative
  alloc   20584576     18500       1112          -
#
```
这里我们看到0x801f57a0这里有一个大小为15984 B的内存块，我们先用mem -dump查看这一块的内存内容。
```
# mem -dump 0x801f57a0 100
801F57A0:  50 57 1F 80 38 1F 00 80 - 18 38 7F 80 00 00 00 00      PW..8... ......
801F57B0:  00 00 00 00 00 01 00 00 - 00 00 00 00 00 00 00 00      ........ ........
801F57C0:  C3 42 C3 83 F4 9B 14 80 - 00 FE 7F 80 00 00 00 00      .B...... ......
801F57D0:  00 00 00 00 00 C3 C3 C3 - 00 00 00 00 82 B2 C1 C3      ........ ........
801F57E0:  C3 C3 5A CB F0 57 1F 80 - F8 57 1F 80 83 C3 C3 C3      ..Z..W.. .W......
801F57F0:  C1 C2 C3 83 D3 93 C3 C2 - C3 C3 C3 C3 C3 CB D1 C1      ........ ........
801F5800:  A0 57 1F 80 08 1F 00 00 - C3 C3 43 C3 4B C3 D3 C3      .W...... ..C.K...
801F5810:  77 6C 61 6E 49 6E 69 74 - 00 EE EE EE EE EE EE EE      wlanInit ........
801F5820:  EE EE EE EE EE EE EE EE - EE EE EE EE EE EE EE EE      ........ ........
801F5830:  EE EE EE EE EE EE EE EE - EE EE EE EE EE EE EE EE      ........ ........
801F5840:  EE EE EE EE EE EE EE EE - EE EE EE EE EE EE EE EE      ........ ........
801F5850:  EE EE EE EE EE EE EE EE - EE EE EE EE EE EE EE EE      ........ ........
801F5860:  EE EE EE EE EE EE EE EE - EE EE EE EE EE EE EE EE      ........ ........
801F5870:  EE EE EE EE EE EE EE EE - EE EE EE EE EE EE EE EE      ........ ........
801F5880:  EE EE EE EE EE EE EE EE - EE EE EE EE EE EE EE EE      ........ ........
801F5890:  EE EE EE EE EE EE EE EE - EE EE EE EE EE EE EE EE      ........ ........
#
```
这里我们看到从0x801F57A0一直到0x801F5810都存有内容，但是从0x801F5820开始就没有了，为了防止我们覆盖掉的内容可能会影响到板子正常运行，我们可以用801F5820这个位置开始作为缓冲区
即缓冲区的地址为0x801f5820。
然后用`flash -read 0xd000 3000 0x801f5820`将flash中的固件内容写入内存，这里一次只读取3000个字节的数据
这里flash命令的用法为
```
# flash -layout
# flash -erase off len
# flash -read off len buffer
# flash -write off len buffer
# off              Offset of flash.                    #flash rom的位置
# len              Length of specify flash segment.    #需要读取或者写入的长度
# buffer           Buffer write from or read to.       #需要读取或写入的内存位置
```
执行`flash -read 0xd000 3000 0x801f5820`拷贝到内存
再`mem -dump 0x801f5820 3000`让串口打印3k的数据
这里我们先取100看看\
```
# mem -dump 0x801f5820 100
801F5820:  49 4D 47 30 00 0E D0 80 - 03 25 14 04 00 00 00 01      IMG0.... .%......
801F5830:  5A 02 02 04 00 00 00 00 - 00 00 00 00 00 00 00 00      Z....... ........
801F5840:  00 00 00 01 00 00 00 00 - 00 00 00 00 00 00 00 00      ........ ........
801F5850:  00 00 00 00 00 00 00 00 - 00 00 00 00 00 00 00 00      ........ ........
801F5860:  00 0A 30 00 00 04 95 AD - 00 00 00 00 00 00 00 00      ..0..... ........
801F5870:  00 00 00 80 00 0A 26 16 - 00 00 00 00 00 00 00 00      ......&. ........
801F5880:  00 0E D0 00 00 00 00 80 - 00 00 00 00 00 00 00 00      ........ ........
801F5890:  00 00 00 00 00 00 00 00 - 00 00 00 00 00 00 00 00      ........ ........
801F58A0:  6E 00 00 80 00 A0 C9 14 - 00 00 00 00 00 00 00 2C      n....... .......,
801F58B0:  00 F3 BC CB 28 1B 3F 3F - 89 C4 BF C5 EA A4 68 59      ....(.?? ......hY
801F58C0:  AA F1 81 51 49 C9 AE 4F - 65 EE 47 2D 5F 98 E4 48      ...QI..O e.G-_..H
801F58D0:  AC 1F 0C 1D 03 8A 2D 6C - F0 47 18 86 0F 78 D6 32      ......-l .G...x.2
801F58E0:  2A 7A 0C 5A ED B4 BA 17 - 81 12 BF A7 C3 CF 49 3F      *z.Z.... ......I?
801F58F0:  67 86 A4 EC 46 A2 CF C0 - 67 6C 35 EE 33 B0 20 F9      g...F... gl5.3. .
801F5900:  69 AF 57 61 7E 85 B3 41 - 76 FA DA 71 74 18 66 68      i.Wa~..A v..qt.fh
801F5910:  96 A2 7E 5A C5 76 8D 6C - 41 F5 59 35 B0 48 D8 FE      ..~Z.v.l A.Y5.H..
#
```
这里可以看到固件的开头IMG0，不过之前看到固件在flash中的大小为948KB，如果像我们这样一次3k 3k的读，至少要来回读取948K/3K = 316次才行，还得将读取的内容转换为16进制字节流格式写入文件，这显然人工提取速度实在太慢了。这里我们就编写一个Python脚本来读取。先用serial库创建一个Serial对象
`serial.Serial(serial_port, baud_rate, timeout=2) as ser:`
然后用while循环判断是否读取完毕，用ser.write(command)发送flash -read指令和mem -dump指令
再用ser.readline()接收mem -dump输出的字符流。
用re库创建一个对象来对字符串进行匹配，因为我们接收到的字符串是这个样子的
`801F5910:  96 A2 7E 5A C5 76 8D 6C - 41 F5 59 35 B0 48 D8 FE      ..~Z.v.l A.Y5.H..`
所以对应的正则表达式为：
```py
match = re.search('([0-9A-F]{2}\s*[0-9A-F]{2}\s*[0-9A-F]{2}\s*[0-9A-F]{2}\s*[0-9A-F]{2}\s*[0-9A-F]{2}\s*[0-9A-F]{2}\s*[0-9A-F]{2})\s*-\s*([0-9A-F]{2}\s*[0-9A-F]{2}\s*[0-9A-F]{2}\s*[0-9A-F]{2}\s*[0-9A-F]{2}\s*[0-9A-F]{2}\s*[0-9A-F]{2}\s*[0-9A-F]{2})', line)
```
这个正则表达式将实际内容匹配为两个部分，中间被“-”截断分隔开了，分别用match.group(1).replace(' ', '')和match.group(2).replace(' ', '')获取并且过滤掉空格，最后将它们以十六进制比特流的格式写入文件中，然后完成这一轮循环，current_address 增加chunk_size，再发送command和command2继续读取并且写入，直到读取到目标地址为结束。
以下是完整的py脚本：
```python
import serial
import time
import re
def dump_memory_test(start_address, end_address, chunk_size, serial_port,
    baud_rate, output_file,buffer):
        with serial.Serial(serial_port, baud_rate, timeout=2) as ser:
            with open(output_file, 'wb') as f:
                current_address = start_address
                while current_address < end_address:
                    #command = f"md {current_address:X} {chunk_size //4:X}\n".encode('utf-8')
                    command = f"flash -read {current_address:X} {chunk_size} {buffer}\n".encode('utf-8')
                    command2= f"mem -dump {buffer} {chunk_size}\n".encode('utf-8')
                    ser.write(command)
                    print(command)
                    time.sleep(1)
                    ser.write(command2)
                    print(command2)
                    time.sleep(0.1)
                    raw_output = b''
                    while True:
                        line = ser.readline().decode('utf-8').strip()
                        print(line)
                        if line == '':
                            break
                        #match = re.search(r'^[0-9a-fA-F]{8}:  ([0-9a-fA-F]{8} - [0-9a-fA-F]{8}', line)
                        match = re.search('([0-9A-F]{2}\s*[0-9A-F]{2}\s*[0-9A-F]{2}\s*[0-9A-F]{2}\s*[0-9A-F]{2}\s*[0-9A-F]{2}\s*[0-9A-F]{2}\s*[0-9A-F]{2})\s*-\s*([0-9A-F]{2}\s*[0-9A-F]{2}\s*[0-9A-F]{2}\s*[0-9A-F]{2}\s*[0-9A-F]{2}\s*[0-9A-F]{2}\s*[0-9A-F]{2}\s*[0-9A-F]{2})', line)
                        #match = re.search(r'(?<=\s{2})((?:[0-9A-F]{2}\s){8})(?=\s-\s)', line)
                        if match:
                            hex_data = match.group(1).replace(' ', '')
                            raw_output += bytes.fromhex(hex_data)
                            hex_data = match.group(2).replace(' ', '')
                            raw_output += bytes.fromhex(hex_data)

                            #print(raw_output)
                    if raw_output:
                        f.write(raw_output)
                        print(f"读取地址: 0x{current_address:X}, 数据保存至 {output_file}") 
                    current_address += chunk_size 

if __name__ == '__main__':
    start_address = int(input("请输入起始地址（16进制）："), 16)
    end_address = int(input("请输入结束地址（16进制）："), 16)
    chunk_size = int(input("请输入块大小（字节）："))
    serial_port = input("请输入串口号（例如COM3）：") 
    baud_rate = int(input("请输入波特率（例如115200）："))
    output_file = input("请输入输出文件名（例如md.bin）：")
    buffer = input("请输入缓冲区位置：")
    dump_memory_test(start_address, end_address, chunk_size, serial_port, baud_rate, output_file,buffer)
```
尝试运行该脚本，用秒表掐一下时间，在我的电脑上，如果每次读取1000B的数据，读取一次要8秒钟，948K全部读完就是948 X 8 =7584 秒，也就是126分钟
如果每次读3000的数据，读取一次需要16秒，算下来需要84分钟才能读取完毕，这么长的时间跟波特率有关系，因为这个板子定义的波特率只有57600，本身传输速度有限，再加上mem -dump需要一定的时间，所以脚本里加了几秒的延时。

![2.png](https://www.iotsec-zone.com/api/image/v2/20250108/d6vywzxrmijgxswz11.png)
真的跑了好久好久，才得到我们要的固件md.bin，把它给binwalk解一下看看

![3.png](https://www.iotsec-zone.com/api/image/v2/20250108/d6vyxkw3scmsmppus1.png)
得到了一堆文件，由于这是vxworks的固件，没有文件名，不过文件内容是正常的。

# 0x02 友华PT926G 固件提取
拆开PT926G的外壳，可以看到电路板上存在两个uart调试接口，用杜邦线焊接其中的一组，然后把它连接到USB-TTL模块上

![4.png](https://www.iotsec-zone.com/api/image/v2/20250108/d6vyxv2l9kyxwfj60o.png)
打开MobaXterm，串口号选择COM7，波特率选择115200。这里的波特率是用XCom一步一步试出来的，因为波特率不正确的情况下，显示的内容是一团乱码，反复调整波特率，直到输出显示正常，即可得到板子的波特率为115200

![5.png](https://www.iotsec-zone.com/api/image/v2/20250108/d6vyy103yet4tzfqqn.png)

![6.png](https://www.iotsec-zone.com/api/image/v2/20250108/d6vyy5qn4nub4lai7s.png)
成功连接uart命令行接收到调试信息

![7.png](https://www.iotsec-zone.com/api/image/v2/20250108/d6vyy9qlwa9fprvtxa.png)
命令行输出了一长串系统启动的指令，停在最后提示要输入用户名和密码验证登录
获取密码的方式有两种，一种是连接上该路由器的网口，然后访问
`http://192.168.1.1:8080/cgi-bin/cgic_systeminfo.cgi`
就能获取到该路由器的密码，另一种方式就是直接看路由器外壳底部的贴纸，上面会记录该路由器的默认密码

![8.png](https://www.iotsec-zone.com/api/image/v2/20250108/d6vyyr05vbqgjncacf.png)
输入useradmin回车，fnrx6回车，成功进入路由器的Busybox界面

![9.png](https://www.iotsec-zone.com/api/image/v2/20250108/d6vyyvmfnud4fltdgw.png)
这里可以直接看到路由器的根目录，尝试了几个指令，发现有cp ,tar，mv等常用的文件拷贝指令，同时PT926G还有一个USB接口，插入U盘后系统还会自动挂载U盘到/mnt/usb 下，这样我们就可以尝试把根目录全部拷贝到U盘中。
这里我准备了一个足够大的U盘，插入路由器
一开始我想的是先用tar -cvf 打包根目录下所有文件，再cp到mnt/usb中，结果发现除了tmp和mnt目录，其他目录都只有只读权限
```
#ls
bin      etc      image    mnt      overlay  sbin     tmp      usr
dev      home     lib      opt      proc     sys      userfs   var
#

#touch 1.c
touch: 1.c: Read-only file system
#
```
然后尝试在tmp目录下拷贝所有文件，结果拷贝到etc文件的时候就提示没有足够的空间了
```
#cd tmp
#tar -cvf a.tar.gz /
...
etc/province/config_AH_926.xml
tar: write error: No space left on device
#cp: write error: No space left on device
cp: write error: No space left on device
cp: write error: No space left on device
cp: write error: No space left on device
cp: write error: No space left on device
cp: write error: No space left on device
cp: write error: No space left on device
cp: write error: No space left on device
cp: write error: No space left on device
cp: write error: No space left on device
```
看来只能在u盘里面tar，用tar直接在/mnt/usb/目录下生成tar 文件，一开始我想的是直接打包根目录，就输入了
`tar -cvf a.tar.gz /`
结果前面打包正常，但是打包到mnt的时候，我发现它把mnt/usb里面的文件，也就是我U盘里本来就存在的文件也进行了打包，由于里面还有其他的大文件，结果就是卡在了一个大文件那里
最后没办法了，只能按文件夹一个一个打包忽略掉mnt文件夹
```
cd /mnt/usb1.2
tar -cvf bin.tar.gz  /bin
tar -cvf etc.tar.gz  /etc
tar -cvf image.tar.gz  /image
tar -cvf overlay.tar.gz  /overlay
tar -cvf sbin.tar.gz  /sbin
tar -cvf tmp.tar.gz  /tmp
tar -cvf usr.tar.gz  /usr
tar -cvf dev.tar.gz  /dev
tar -cvf home.tar.gz  /home
tar -cvf lib.tar.gz  /lib
tar -cvf opt.tar.gz  /opt
tar -cvf proc.tar.gz  /proc
tar -cvf sys.tar.gz  /sys
tar -cvf userfs.tar.gz  /userfs
tar -cvf var.tar.gz  /var
```

![10.png](https://www.iotsec-zone.com/api/image/v2/20250108/d6vyz2op2iy3ogrgwq.png)
最后就得到了这些压缩包，将他们全部解压缩，就能拿到所有的固件内容了

![11.png](https://www.iotsec-zone.com/api/image/v2/20250108/d6vyz6gtdpfoe0ntav.png)
