# Qiling Fuzz实例分析
> Pachimker
> 来源：https://www.iotsec-zone.com/article/394

# 背景

在上一小节中，介绍了qiling框架的背景和基础使用，并以相关的CTF和qilinglab实例进行练习加深对qiling框架的使用，后续并简单介绍了qiling fuzz的功能。

在这一小节，我们将对qiling fuzz iot设备进行测试以及以实例的方式对其进行学习。

# qiling fuzz 基础

qiling和AFL++环境的搭建在前面的小节中已经说过，这里就不再演示。我们进入到qiling的qiling/example/fuzzing目录下，qiling框架官方库提供了几个fuzz的example供我们学习和测试。我们先对tenda ac15进行测试。

![0.png](https://www.iotsec-zone.com/images/MdImg/4ce18a6c1c99c46e6e4a1929da101cbc.png)

根据README文档中的介绍，我们首先需要提取tenda ac 15文件系统并放置于脚本同级目录中，操作步骤如下：

```
1. wget https://down.tenda.com.cn/uploadfile/AC15/US_AC15V1.0BR_V15.03.05.19_multi_TD01.zip
2. unzip US_AC15V1.0BR_V15.03.05.19_multi_TD01.zip
3. binwalk -e US_AC15V1.0BR_V15.03.05.19_multi_TD01.bin
4. mv xxx/squashfs-root ./rootfs;cd rootfs
5. rm -rf webroot;mv webroot_ro webroot
6. mv etc_ro etc

```

随后我们需要运行saver_tendaac15_httpd.py

![1.png](https://www.iotsec-zone.com/images/MdImg/f9f1d18aca59e40a23e4319f864833f3.png)

使用netstat -pantl查看监听端口，当发现python3程序正在监听8080端口时，说明tenda ac仿真成功。

![2.png](https://www.iotsec-zone.com/images/MdImg/0a6a3a828e63d68aa278bc5593eaee7f.png)

此时我们运行./addressNet_overflow.sh生成snapshot.bin文件。

![3.png](https://www.iotsec-zone.com/images/MdImg/3aaf21181e7f4556fa1485529be1e1e9.png)

运行./fuzz_tendaac15_httpd.sh进行fuzz，经过10分钟左右出现了crash。

![4.png](https://www.iotsec-zone.com/images/MdImg/0d3b2d20f790a4c9b8bafd2b05125a49.png)

产生的crash文件内容如下

![5.png](https://www.iotsec-zone.com/images/MdImg/13fb56555f858f4577da203af2dc3766.png)

这样我们就完成对实例中tenda ac15的fuzz复现。官方提供demo的saver和fuzz脚本如下，现在我们对其进行简单分析并学习。

![6.png](https://www.iotsec-zone.com/images/MdImg/2794183aa04999d8b3e7a6062acaac89.png)

![7.png](https://www.iotsec-zone.com/images/MdImg/0b4323752c4dab4edf08d11773f3a067.png)

通过上一小节中对qiling基础的学习，我们可以对两个脚本中的函数功能进行拆分。

##### saver.py

### 保存快照

```
def save_context(ql, *args, **kw):
    ql.save(cpu_context=False, snapshot="snapshot.bin")

```

### 替换网卡名称

```
def patcher(ql):
    br0_addr = ql.mem.search("br0".encode() + b'\x00')
    for addr in br0_addr:
        ql.mem.write(addr, b'lo\x00')

```

### 检查停止地址

```
def check_pc(ql):
    print("=" * 50)
    print("Hit fuzz point, stop at PC = 0x%x" % ql.arch.regs.arch_pc)
    print("=" * 50)
    ql.emu_stop()

```
### 网络设置

```
def nvram_listener():
    server_address = 'rootfs/var/cfm_socket'
    data = ""
    
    try:
        os.unlink(server_address)
    except OSError:
        if os.path.exists(server_address):
            raise  

    sock = socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
    sock.bind(server_address)
    sock.listen(1)
  
    while True:
        connection, client_address = sock.accept()
        try:
            while True:
                data += str(connection.recv(1024))
        
                if "lan.webiplansslen" in data:
                    connection.send('192.168.170.169'.encode())
                else:
                    break  
                data = ""
        finally:
                connection.close()

```

### 仿真流程

```
def my_sandbox(path, rootfs):
    ql = Qiling(path, rootfs, verbose=QL_VERBOSE.DEBUG)
    ql.add_fs_mapper("/dev/urandom","/dev/urandom")
    ql.hook_address(save_context, 0x10930)
    ql.hook_address(patcher, ql.loader.elf_entry)
    ql.hook_address(check_pc, 0x7a0cc)
    ql.run()

```

##### fuzz.py

### 替换网卡名称

```
def patcher(ql):
    br0_addr = ql.mem.search("br0".encode() + b'\x00')
    for addr in br0_addr:
        ql.mem.write(addr, b'lo\x00')

```

### fuzz流程

```
def main(input_file, enable_trace=False):
    # 生成qiling实例
    ql = Qiling(["rootfs/bin/httpd"], "rootfs", verbose=QL_VERBOSE.DEBUG, console = True if enable_trace else False)

    # 恢复快照内容
    ql.restore(snapshot="snapshot.bin")

    # 变异数据地址点定位
    fuzz_mem=ql.mem.search(b"CCCCAAAA")
    target_address = fuzz_mem[0]

    # target_address为fuzz变异点，place_input_callback函数通过afl++对数据进行变异
    def place_input_callback(_ql: Qiling, input: bytes, _):
        _ql.mem.write(target_address, input)
    # fuzz函数定义
    def start_afl(_ql: Qiling):
        ql_afl_fuzz(_ql, input_file=input_file, place_input_callback=place_input_callback, exits=[ql.os.exit_point])

    ql.hook_address(callback=start_afl, address=0x10930+8)

    # qiling实例运行
    try:
        ql.run(begin = 0x10930+4, end = 0x7a0cc+4)
        os._exit(0)
    except:
        if enable_trace:
            print("\nFuzzer Went Shit")
        os._exit(0)

```

通过功能的拆分以及我们的分析，可以知道fuzz大致流程是：

1.运行saver.py生成qiling实例仿真运行，此时运行addressNet_overflow.sh触发相关执行流程，当pc寄存器运行到0x10930地址时，触发保存快照功能。

2.fuzz.sh会调用afl++并执行fuzz.py脚本对其input输入进行数据变异。

3.fuzz.py脚本中，首先会恢复快照状态，并在内容中寻找数据变异点，并接受afl++的变异数据将其写入数据变异点进行fuzz。

了解了大致fuzz流程，我们可能存在几点疑虑：

1.saver.py脚本中如何知道在哪个地址触发保存快照功能?在仿真的httpd程序触发执行addressNet_overflow.sh执行流程后，程序将变异数据存储至内存完成后，就可以触发快照保存功能。 

2.addressNet_overflow.sh脚本中为什么定义page为CCCCAAAA？CCCCAAAA为poc的溢出标识，以便后续我们进行查找定位。

3.fuzz.py脚本中为什么先要替换br0？tenda ac15路由器设备启动时会检测br0网卡状态，我们本地没有这个网卡所以替换成了lo。

4.fuzz.py脚本中如何知道ql.run的起始和结束地址?起始地址是保存快照后面的指令，需要保证执行流程的连贯性(保存寄存器状态除外)，结束地址便是漏洞函数可以触发crash后的函数结束地址。

这里1、4还是不太清楚，带着疑问我们接着往下分析：
根据addressNet_overflow.sh脚本中的poc，我们使用ida进行定义，发现漏洞函数如下，产生漏洞的原因便是没有对用户发送post包data数据中的entrys、mitInterface、page参数进行过滤，并使用sprintf危险函数进行了写入。

![8.png](https://www.iotsec-zone.com/images/MdImg/7c4797479d6c89d191d3bc0316c1691c.png)

那么我们要fuzz的函数就是formAddressNat函数了，首先第1点saver.py脚本中该如何定位保存地址点，这里其实当v1=sprintf(xxx)执行完毕后，已经将用户参数数据保存到v6中时，就已经可以保存快照了(后续fuzz.py也要进行相应修改)。这里作者定位的是0x10930，那么后续fuzz的起始地址和结束地址分别就是0x10930执行流程的后面下一条指令和formAddressNet函数的结束地址。

![9.png](https://www.iotsec-zone.com/images/MdImg/fd9851d1e594509c3c7f66ecc199bfce.png)

在分析的过程中，我们可以打开QL_VERBOSE.DISASM来清楚的查看汇编指令的执行流程和对应指令的寄存器信息。

分析完tenda ac同理example中的dir815实例也是同样的流程，只不过dir815的fuzz脚本并没有使用保存快照功能，而是直接使用ql.mem.search进行查找变异数据点以及使用ql.mem.write对变异数据进行写入。

![10.png](https://www.iotsec-zone.com/images/MdImg/a1502ea6e230ceb6201aa17014d48a64.png)

![11.png](https://www.iotsec-zone.com/images/MdImg/a298169db01ca24cd40988b9d540775c.png)

分析完上面的流程后，我们对fuzz的流程有了大概理解。后面我们以dlink dir645路由器中的两个栈溢出实例进行fuzz测试。

# qiling fuzz 实例

以经典的dir645栈溢出为例，我们使用qiling框架对两个栈溢出漏洞进行fuzz测试。

首先下载固件并使用binwalk -Me 固件名进行提取，简单查看后发现本次分析的程序hedwig.cgi和authentication.cgi均为软链接(链接到htdocs/cgibin)，qiling对软连接的处理不是很友好，建议将所有软连接替换为源文件。

##### hedwig.cgi栈溢出

我们首先将cgibin拖入ida进行简单分析，进入main函数后发现，main程序根据传入参数与相关"*.cgi"进行比较，随后进入相关的cgi_main函数中，那我们先分析一下hedwig.cgi触发的栈溢出

![12.png](https://www.iotsec-zone.com/images/MdImg/12cd4d9ab078332a43e5917bfc68749d.png)

fuzz的第一步就是摸清楚程序的执行流程，我们先简单编写仿真程序的脚本，随后将其改为fuzz脚本。该仿真脚本定义了俩个hook函数，当程序执行执行地址处后会执行该hook函数，并打印出"Hit at xxx func"。

![13.png](https://www.iotsec-zone.com/images/MdImg/745e72465fb297a09d9f5cd313caf54d.png)

执行仿真脚本，发现我们定义的俩个hook都被触发，说明我们简单分析后的执行流程确实没错，并且调试信息后续还打印出了一下回应信息。

![14.png](https://www.iotsec-zone.com/images/MdImg/62437cb07bb202283864fe88a0e011fc.png)

我们继续在ida中查找定位该信息，发现是LABEL_25中的处理，根据交叉引用，我们追踪该信息产生的原因是env中没有REQUEST_METHOD

![15.png](https://www.iotsec-zone.com/images/MdImg/162e6ab4d989fcd0627e3c4eed0032c9.png)

![16.png](https://www.iotsec-zone.com/images/MdImg/ade543ff74c8459a5591754bdec22512.png)

那么我们在env中设置该环境变量然后传入给qiling实例就可以了，接着往下分析发现程序的溢出点位于sess_get_uid中，并通过QL_VERBOSE.DISASM信息，我们理清楚了大概的产生漏洞流程。定位了栈溢出地址后，那么我们根据漏洞产生流程设置相关的env参数数据并传入qiling实例中，随后我们使用mem.search()替换成为变异数据，程序仿真时就会取出环境变量中的值进行处理从而产生栈溢出。

注：由于程序是从env中读取变量的值，所以也就不存在前面提到的拷贝到内存中然后触发保存快照功能指定流程，这里可以直接触发保存快照的功能。

[https://mmbiz.qpic.cn/mmbiz_png/WGegAIkTRic8U2XKftb9ib9uoMvsibhNQJagLaNqSVZaicosbjfJGhP2aHgODOuWM6SCQ9Lq2AicqicKbrby5uKIzIaA/640?wx_fmt=png&tp=wxpic&wxfrom=5&wx_lazy=1&wx_co=1](https://mmbiz.qpic.cn/mmbiz_png/WGegAIkTRic8U2XKftb9ib9uoMvsibhNQJagLaNqSVZaicosbjfJGhP2aHgODOuWM6SCQ9Lq2AicqicKbrby5uKIzIaA/640?wx_fmt=png&tp=wxpic&wxfrom=5&wx_lazy=1&wx_co=1)

最终编写saver.py脚本如下：

```
import ctypes, os, pickle, socket, sys, threading
sys.path.append("..")
from qiling import *
from qiling.const import QL_VERBOSE

MAIN = 0x402770
HEDWIGCGI_MAIN = 0x40bfc0
SESSION_UID = 0x4083f0
SAVE_ADDRESS = 0x40c070

def test_print1(ql: Qiling)->None:
    print("Hit at main func")

def test_print2(ql: Qiling)->None:
    print("Hit at hedwig func")

def test_print3(ql: Qiling)->None:
    print("Hit at session uid func")

def saver(ql: Qiling):
    print('[!] Hit Saver 0x%X'%(ql.arch.regs.arch_pc))
    ql.save(cpu_context=False, snapshot='./context.bin')

def my_sandbox(path, rootfs):
    env_vars = {
            "REQUEST_METHOD": "POST",
            "REQUEST_URI": "/hedwig.cgi",
            "CONTENT_TYPE": "application/x-www-form-urlencoded",
            "REMOTE_ADDR": "127.0.0.1",
            "HTTP_COOKIE": "uid=AAAABBBB"
    }
    ql = Qiling(path, rootfs,env=env_vars,verbose=QL_VERBOSE.DEBUG)
    ql.hook_address(test_print1, MAIN)
    ql.hook_address(test_print2, HEDWIGCGI_MAIN)
    ql.hook_address(test_print3, SESSION_UID)
    ql.hook_address(saver, SAVE_ADDRESS)
    ql.run()

if __name__ == "__main__":
    my_sandbox(["rootfs/htdocs/web/hedwig.cgi"], "rootfs")

```
执行后，保存的快照为context.bin，我们可以使用strings定位栈溢出标识字符串。

![17.png](https://www.iotsec-zone.com/images/MdImg/c8aa2cf73e77fd79e57ceb543a6f2131.png)

![18.png](https://www.iotsec-zone.com/images/MdImg/561270d4377a8b0d423d50e313e222b6.png)

接下来我们编写fuzz.py，前面我们触发快照的地址为getenv("REQUEST_METHOD") 执行后的一条指令，那么我们在编写fuzz.py中ql.run的起始地址时就应该为下一条指令，这里为了方便我直接让其跳过if判断直接从cgibin_parse_request处开始执行(0x40c0a4)。结束地址呢，这里直接指定hedwigcgi_main函数的结尾就可以(0x40c598)，因为有溢出数据时程序执行到函数最后一定会触发crash。

![19.png](https://www.iotsec-zone.com/images/MdImg/79ab6547a9c6c8808508f9d6af9c27f9.png)

最终hedwig.cgi栈溢出fuzz.py的脚本如下：

```
import os, pickle, socket, sys, threading
sys.path.append("../../../")
from qiling import *
from qiling.const import QL_VERBOSE
from qiling.extensions.afl import ql_afl_fuzz

def main(input_file, enable_trace=False):
    ql = Qiling(["rootfs/htdocs/web/hedwig.cgi"], "rootfs", verbose=QL_VERBOSE.DEBUG)
    ql.restore(snapshot="context.bin")
    fuzz_mem=ql.mem.search(b"AAAABBBB")
    target_address = fuzz_mem[0]

    def place_input_callback(_ql: Qiling, input: bytes, _):
        _ql.mem.write(target_address, input)

    def start_afl(_ql: Qiling):
        ql_afl_fuzz(_ql, input_file=input_file, place_input_callback=place_input_callback, exits=[ql.os.exit_point])

    ql.hook_address(callback=start_afl, address=0x40c0a4)
    
    try:
        ql.run(begin = 0x40c0a4, end = 0x40c598)
        os._exit(0)
    except:
        if enable_trace:
            print("\nFuzzer Went Shit")
        os._exit(0)

if __name__ == "__main__":
    if len(sys.argv) == 1:
        raise ValueError("No input file provided.")

    if len(sys.argv) > 2 and sys.argv[1] == "-t":
        main(sys.argv[2], enable_trace=True)
    else:
        main(sys.argv[1])

```

不到1分钟就fuzz到了crash，还是比较快的。

![20.png](https://www.iotsec-zone.com/images/MdImg/c8b0ac996adca11b61a2e8fce46ac144.png)

##### authentication.cgi栈溢出

和上面的分析同理，我们首先跟一下程序的执行流程，authentication.cgi的处理函数为authenticationcgi_main函数。

![21.png](https://www.iotsec-zone.com/images/MdImg/273df40a0b9825b17072f109aff4a4ed.png)

进入到authenticationcgi_main函数后，我们发现和上面的hedwig类似，也是同样获取env中的变量进行处理。

![22.png](https://www.iotsec-zone.com/images/MdImg/af40b6457aea60783e451bd23f4f3716.png)

那么我们将前面的脚本进行修改，这里直接将HEDWIGCGI_MAIN改为0x40afcc。

![23.png](https://www.iotsec-zone.com/images/MdImg/26441871ef29e48ecdddf942a6872653.png)

运行后发现执行触发了俩个hook函数，说明确实执行到了authenticationcgi_main函数中。

![24.png](https://www.iotsec-zone.com/images/MdImg/ae9c223d3de64cdc5df2d4a12f020239.png)

authentication.cgi触发栈溢出的执行流程为REQUEST METHOD方法为POST，并且需要设置"CONTENT_TYPE"和"CONTENT_LENGTH"环境变量。

![25.png](https://www.iotsec-zone.com/images/MdImg/782fd8967c23309ef820dda0c7b3220c.png)

那么我们在env变量中设置如下参数并传入qiling实例。

注：CONTENT_LENGTH中的999在程序执行时还没有溢出，v73定义的1024字节。

![26.png](https://www.iotsec-zone.com/images/MdImg/d84cf44625a9370689f8c045a2b56e3b.png)

行后发现已经执行我们想要其执行的流程了，并且需要我们输入一些信息才可执行后面的流程。

![27.png](https://www.iotsec-zone.com/images/MdImg/d7b5f5c39d2dd008d6d0ce8e828754a5.png)

![28.png](https://www.iotsec-zone.com/images/MdImg/8d7ba5aeca0af2aa1f2413aed3a34683.png)

input中含有的内容如下，需要包含"id=xxx&password=xxx"

![29.png](https://www.iotsec-zone.com/images/MdImg/72ec945a80307268e974e85c79c29b92.png)

![30.png](https://www.iotsec-zone.com/images/MdImg/f65e1922452af9be4a405f19c1079b9c.png)

再次执行，输入"id=1&password=123"后，程序正常执行。那么我们的fuzz思路如下：

传入env环境变量，使其按照漏洞触发流程进行执行，随后在程序赋值content_length时，进行hook，将需要用到的寄存器修改成afl++变异数据的大小(其实这里应该取出所有header的字节，不过这里不是很影响)，随后进行调用start_afl进行fuzz。写入栈溢出标识地址的content格式为：b"id=1&password="+input　

![31.png](https://www.iotsec-zone.com/images/MdImg/e3293d3149090c4f56c75bec424c6ebf.png)

根据上面的信息，我们编写的fuzz.py如下：

```
import ctypes, os, pickle, socket, sys, threading
sys.path.append("../../../")
from qiling import *
from qiling.const import QL_VERBOSE
from qiling.extensions import pipe
from qiling.extensions.afl import ql_afl_fuzz

MAIN = 0x402770
AUTHENTICATION_MAIN = 0x40afcc
CONTENT_LENGTH = 0x40b48c
CONTENT_SIZE = 0x40b4b4
size = 0

def test_print1(ql: Qiling)->None:
    print("Hit at main func")

def test_print2(ql: Qiling)->None:
    print("Hit at authentication func")

def test_print3(ql: Qiling):
    print("address:",hex(ql.arch.regs.s0))

def test_print4(ql: Qiling):
    print("Hit at exit func")

def test_size(ql: Qiling):
    global size
    ql.arch.regs.s0 = size
    ql.arch.regs.a2 = size
    print("Hit at test_size func")

def main(input_file, enable_trace=False):
    env_vars = {
            "REQUEST_METHOD": "POST",
            "REQUEST_URI": "/authentication.cgi",
            "CONTENT_TYPE": "application/x-www-form-urlencoded",
            "REMOTE_ADDR": "127.0.0.1",
            "CONTENT_LENGTH": "100"
    }
    ql = Qiling(["rootfs/htdocs/web/authentication.cgi"], "rootfs",env=env_vars,verbose=QL_VERBOSE.DEBUG)
    ql.os.stdin = pipe.SimpleInStream(0)
    if not enable_trace:
        ql.os.stdout = pipe.NullOutStream(sys.stdout.fileno())
        ql.os.stderr = pipe.NullOutStream(sys.stderr.fileno())

    def place_input_callback(ql: Qiling, input: bytes, _: int):
        global size
        content = b"id=1&password="+input
        size = len(content)
        ql.os.stdin.write(content)
        ql.hook_address(test_size,CONTENT_SIZE)

    def start_afl(_ql: Qiling):
        ql_afl_fuzz(_ql, input_file=input_file, place_input_callback=place_input_callback, exits=[ql.os.exit_point])

    ql.hook_address(test_print1, MAIN)
    ql.hook_address(test_print2, AUTHENTICATION_MAIN)
    ql.hook_address(test_print3, CONTENT_LENGTH)
    ql.hook_address(test_print4,address=0x40bc90)

    ql.hook_address(callback=start_afl, address=AUTHENTICATION_MAIN)

    try:
        ql.run()
        os._exit(0)
    except:
        if enable_trace:
            print("\nFuzzer Went Shit")
        os._exit(0)

if __name__ == "__main__":
    if len(sys.argv) == 1:
        raise ValueError("No input file provided.")
    if len(sys.argv) > 2 and sys.argv[1] == "-t":
        main(sys.argv[2], enable_trace=True)
    else:
        main(sys.argv[1])

```

运行后发现，afl++给到的变异数据确实传入了进去。

但是fuzz了一会儿发现没crash，原来是read(fd=0x0,buf=0x7ff3c940,length=0x64)，这里读取的length还是100，也就是说afl++不管变异多少数据都只读取100字节，这说明我们的hook有问题。

![32.png](https://www.iotsec-zone.com/images/MdImg/6dfe59ece46226dc14701b3e595985ca.png)

打开QL_VERBOSE.DUMP模式，查看read时寄存器变量的值，确实hook没生效。那么我们直接在其调用read函数时hook，使其寄存器变成我们变异数据的长度就可以了。

![33.png](https://www.iotsec-zone.com/images/MdImg/6f3ce680215d67ea0432635c2b13c2c6.png)

![34.png](https://www.iotsec-zone.com/images/MdImg/699fa770a640268ff697a109a2336bf4.png)

重新改正脚本
```
import ctypes, os, pickle, socket, sys, threading
sys.path.append("../../../")
from qiling import *
from qiling.const import QL_VERBOSE
from qiling.extensions import pipe
from qiling.extensions.afl import ql_afl_fuzz

MAIN = 0x402770
AUTHENTICATION_MAIN = 0x40afcc
CONTENT_LENGTH = 0x40b48c
CONTENT_SIZE = 0x40b4a8
size = 1000

def test_print1(ql: Qiling)->None:
    print("Hit at main func")

def test_print2(ql: Qiling)->None:
    print("Hit at authentication func")

def test_print3(ql: Qiling):
    print("address:",hex(ql.arch.regs.s0))

def test_print4(ql: Qiling):
    print("Hit at exit func")

def test_size(ql: Qiling):
    global size
    ql.arch.regs.s0 = size
    ql.arch.regs.a1 = size
    print("Hit at test_size func")

def main(input_file, enable_trace=False):
    global size
    env_vars = {
            "REQUEST_METHOD": "POST",
            "REQUEST_URI": "/authentication.cgi",
            "CONTENT_TYPE": "application/x-www-form-urlencoded",
            "REMOTE_ADDR": "127.0.0.1",
            "CONTENT_LENGTH": "100"
    }
    ql = Qiling(["rootfs/htdocs/web/authentication.cgi"], "rootfs",env=env_vars,verbose=QL_VERBOSE.DEBUG)

    ql.os.stdin = pipe.SimpleInStream(0)
    if not enable_trace:
        ql.os.stdout = pipe.NullOutStream(sys.stdout.fileno())
        ql.os.stderr = pipe.NullOutStream(sys.stderr.fileno())

    def place_input_callback(ql: Qiling, input: bytes, _: int):
        global size
        content = b"id=1&password="+input
        size = len(content)
        ql.os.stdin.write(content)

    def start_afl(_ql: Qiling):
        ql_afl_fuzz(_ql, input_file=input_file, place_input_callback=place_input_callback, exits=[ql.os.exit_point])

    ql.hook_address(test_print1, MAIN)
    ql.hook_address(test_print2, AUTHENTICATION_MAIN)
    ql.hook_address(test_print3, CONTENT_LENGTH)
    ql.hook_address(test_print4,address=0x40bc90)
    ql.hook_address(callback=start_afl, address=AUTHENTICATION_MAIN)
    ql.hook_address(test_size,CONTENT_SIZE)

    try:
        ql.run()
        os._exit(0)
    except:
        if enable_trace:
            print("\nFuzzer Went Shit")
        os._exit(0)

if __name__ == "__main__":
    if len(sys.argv) == 1:
        raise ValueError("No input file provided.")
    if len(sys.argv) > 2 and sys.argv[1] == "-t":
        main(sys.argv[2], enable_trace=True)
    else:
        main(sys.argv[1])

```

运行后，3分钟左右fuzz出crash。

![35.png](https://www.iotsec-zone.com/images/MdImg/49d544d3aca699beef1ad705fa13e84c.png)

![36.png](https://www.iotsec-zone.com/images/MdImg/57e0a264bbcf55874e3fd7773e7312ee.png)

综上，我们以实例的方式分析并fuzz了dir645路由器的俩个栈溢出漏洞，可能很多人觉得在fuzz时已经知道了漏洞点和执行流程，使用qiling进行fuzz有点多余。但是对于我们没有实体设备或者qemu不能完全仿真时，即使我们知道了漏洞点，我们也没法去简单测试或验证，那么这时qiling框架就是一个比较好的选择。这个小节中qiling 的fuzz思路像是在验证漏洞而且比较基础，而在真正fuzz漏洞时，也许我们可以hook危险函数并进行fuzz，又或者其他思路，这些就靠大家的思维拓展了。

# 总结

在这小节中，我们使用qiling框架分析并测试了tenda ac15、dir 815以及dir 645实例设备的栈溢出漏洞，掌握了在分析fuzz时的基础思路。熟练掌握qiling框架的使用，对于后续我们的漏洞测试方面还是有很多的帮助。
