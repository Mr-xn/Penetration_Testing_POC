# boofuzz 源码笔记（一）
> Ayaka
> 来源：https://www.iotsec-zone.com/article/322

# boofuzz的安装和基本用法
**Boofuzz**是一个基于生成（generation-based）的协议Fuzz工具，它通过python语言来描述协议的格式，是经典模糊测试框架**Sulley**的继承者，除了众多的bug修复之外，boofuzz还致力于扩展性。Boofuzz对协议的模糊测试有着良好的支持，且其代码开源，目前被广泛使用。

为什么boofuzz对物联网设备有着非常良好的模糊测试效果呢？究其原因其实是因为物联网设备中设计到了大量的协议，常见的如tcp,udp,mqtt,upnp等等，还有一些各个厂商自己设计的协议等等，而boofuzz则是一款对于协议模糊测试效果非常出众的模糊测试框架。

boofuzz还有一个非常出众的地方，由于它是全python代码，所以可以直接通过一条命令来安装：
```bash
pip install boofuzz
```

在开始使用boofuzz之前，先来了解一下boofuzz的基本语法,boofuzz的一些比较常用的原语如下：
**静态和随机的原始类型**
* s_static():最简单的原始类型，它向请求中添加一个静态的，任意长度的未变异的值，别名：s_dunno(),s_raw(),s_unknown()
* s_binary():它可以接收多种格式来表示的二进制数据
* s_random()：它被用来生成不同长度的随机数据

**整数类型**
* 单字节：s_byte()或s_char()
* 双字节：s_word()或s_short()
* 四字节：s_dword(),s_long(),s_int()
* 八字节：s_qword()或s_double()
每个整数类型至少接收一个参数当做整数值，还可以指定以下参数：
* endian：默认为'<'，即大小端序
* format：可以指定为binary或ascii，默认为binary，控制整数的显示格式，ascii则显示100，binary则显示\x64
* signed：默认false,控制数字显示的时候是有符号还是无符号，只有当format为ascii的时候这个设置才生效
* fuzzable：默认为True，即是否对该原始类型进行模糊测试
* name：默认是None，指定名字就可以在整个请求中直接访问该原始类型

**字符串和分隔符**
模糊测试的过程中必然会涉及到很多字符串，比如邮件地址，主机名，用户名， 密码等等都是字符串
- s_string()用来表示字符串原始类型，至少有一个参数作为有效值，也可以指定如下额外关键字参数
- size()：默认值为-1，表示该字符串的静态大小，如果是动态代销则为-1
- Padding():用于补足字符串，如果size被指定，且生成的字符串小于该大小，则用padding里的参数补足字符串，默认\x00
- fuzzable():用于指定是否进行变异
- name():指定一个label用于访问

session对象是fuzz的核心，创建session时，会传递一个target对象，该对象接收一个connection对象，例如
```python
session = Session(
    target=Target(
        connection=SocketConnection("127.0.0.1", 8021, proto='tcp')))
```

如果要写一个简单的fuzzing，首先写好一个session,然后使用s_initialize初始化一个请求
```python
s_initialize("new request")
```
然后新建一个块，添加各个所需字段：
```python
with s_block("Request-Line"):
        s_group("Method", ['GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'CONNECT', 'OPTIONS', 'TRACE'])
        s_delim(" ", name='space-1')
        s_string("/index.html", name='Request-URI')
        s_delim(" ", name='space-2')
        s_string('HTTP/1.1', name='HTTP-Version')
        s_static("\r\n", name="Request-Line-CRLF")
```
最后调用
```python
session.fuzz()
```
开始模糊测试

其中涉及到的具体就session，block这些东西暂且不深究，拿到后面的源码分析里说。

运行起来以后，可以看到
![0.png](https://www.iotsec-zone.com/images/MdImg/4aff0219441aedd3b5d3d27e3e5c8470.png)
发送了大量的经过变异后的数据，并且可以通过 localhost:26000 的可视化界面查看fuzzing进度。

上面的例子是随意一个tcp协议都可以跑的，如果要针对路由器的某个功能进行针对性的fuzzing，则需要抓包以后对数据包中的各个有效字段进行设置，例如我要fuzzing D-link公司的某款路由器的某个功能，可以写出如下代码：
```python
#!/usr/bin/env python
# Designed for use with boofuzz v0.0.9
from boofuzz import *

def main():
    session = Session(
        target=Target(
            connection=SocketConnection("192.168.0.1", 80, proto='tcp')
        ),
    )
    s_initialize(name="Request")
    with s_block("Request-header"):
        #line1
        s_static("GET",name='method')
        s_static(" ", name='space-1-1')
        s_static("/setup.php", name='Request-URI')
        s_static(" ", name='space-1-2')
        s_static('HTTP/1.1', name='HTTP-Version')
        s_static("\r\n", name="Request-Line-CRLF")

        #line2
        s_static("Host:")
        s_static(" ",name='space-2-1')
        s_static("192.168.0.1",name='ip')
        s_static('\r\n')

        #line3
        s_static("Upgrade-Insecure-Requests:")
        s_static(" ")
        s_static("1")
        s_static("\r\n")
        #line4
        s_static("User-Agent:")
        s_static(" ")
        s_static("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36")
        s_static("\r\n")
        #line5
        s_static("Accept:")
        s_static(" ")
        s_static("text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9")
        s_static("\r\n")
        #line6
        s_static("Referer:")
        s_static(" ")
        s_static("http://192.168.0.1/adv_app.php")
        s_static("\r\n")
        #line7
        s_static("Accept-Encoding:")
        s_static(" ")
        s_static("gzip, deflate")
        s_static("\r\n")
        #line8
        s_static("Accept-Language:")
        s_static(" ")
        s_static("en-US,en;q=0.9")
        s_static("\r\n")
        #line 9 important
        s_static("Cookie:")
        s_static(" ")
        s_static("SESSION_ID=")
        s_string("2:1420071526:2;",fuzzable=True)
        s_static(" ")
        s_static("uid=")
        s_string("j0pRtxh7sf",fuzzable=True)
        s_static("\r\n")
        #line10
        s_static("Connection:")
        s_static(" ")
        s_static("close")
        s_static("\r\n")
    s_static("\r\n", "Request-CRLF")

    session.connect(s_get("Request"))

    session.fuzz()

if __name__ == "__main__":
    main()

'''
GET /setup.php HTTP/1.1
Host: 192.168.0.1
Upgrade-Insecure-Requests: 1
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9
Referer: http://192.168.0.1/adv_app.php
Accept-Encoding: gzip, deflate
Accept-Language: en-US,en;q=0.9
Cookie: SESSION_ID=2:1420071526:2; uid=j0pRtxh7sf
Connection: close
'''
```

到这里已经简要的说明了boofuzz的安装和基本的使用方法，接下来开始逐步深入boofuzz的内部

# boofuzz的代码结构
先来看一张源码结构图
![1.png](https://www.iotsec-zone.com/images/MdImg/6c17af2c85a00812b036e27fd8190d71.png)

有一些模块的代码从源码分析的角度上来说意义并不是非常大或者优先级并不高，对整体fuzzing框架逻辑影响不明显的，就没有在思维导图中展开说明，比如web中的代码是为了构建我们在 localhost:26000 中所看到的可视化界面，utils中的代码则是一些通用性比较高的单元工具，connnections则是因为更适合当成一个整体来说，所以没有对内部的代码结构进行分析。

除了上述结构的代码之外，boofuzz还有一些核心代码，如sessions.py,fuzzers.py等等，后面将逐步进行分析。

# boofuzz的源码分析
从这里开始进入真正的源码分析，既然是源码分析，那总要有一个顺序，或者说以什么为指导去进行源码分析，首先肯定要满足简单和普适的原则，至少要讲boofuzz的基本功能涵盖进去。思来想去，与其自己写一个，不如直接用官方给的。

本系列文章将首先以官方给出的fuzzing tcp协议的小案例为指导，逐步分析boofuzz源代码。之后会继续深入boofuzz的其他功能以及进行框架的扩展。

首先来看看官方给出的案例：

```python
from boofuzz import *

def main():
    session = Session(
        target=Target(
            connection=SocketConnection("127.0.0.1", 80, proto='tcp')
        ),
    )

    s_initialize(name="Request")
    with s_block("Request-Line"):
        s_group("Method", ['GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'CONNECT', 'OPTIONS', 'TRACE'])
        s_delim(" ", name='space-1')
        s_string("/index.html", name='Request-URI')
        s_delim(" ", name='space-2')
        s_string('HTTP/1.1', name='HTTP-Version')
        s_static("\r\n", name="Request-Line-CRLF")
    s_static("\r\n", "Request-CRLF")

    session.connect(s_get("Request"))

    session.fuzz()

if __name__ == "__main__":
    main()
```

来逐行分析main函数中的代码

首先是这句代码：
```python
Session(
        target=Target(
            connection=SocketConnection("127.0.0.1", 80, proto='tcp')
        ),
```

一个三层嵌套的构造，最外层构建了一个Session类，接收一个target参数，是一个Target类，这个类还接收了一个connection参数，是一个SocketConnection，在分析的时候采用从里到外的方式分析，先来看看SocketConnection是个什么东西：

在/
```python
def SocketConnection(
    host,
    port=None,
    proto="tcp",
    bind=None,
    send_timeout=5.0,
    recv_timeout=5.0,
    ethernet_proto=None,
    l2_dst=b"\xFF" * 6,
    udp_broadcast=False,
    server=False,
    sslcontext=None,
    server_hostname=None,
):
    """ITargetConnection implementation using sockets.

    Supports UDP, TCP, SSL, raw layer 2 and raw layer 3 packets.

    .. note:: SocketConnection is deprecated and will be removed in a future version of Boofuzz.
        Use the classes derived from :class:`BaseSocketConnection <boofuzz.connections.BaseSocketConnection>` instead.

    .. versionchanged:: 0.2.0
        SocketConnection has been moved into the connections subpackage.
        The full path is now boofuzz.connections.socket_connection.SocketConnection

    .. deprecated:: 0.2.0
        Use the classes derived from :class:`BaseSocketConnection <boofuzz.connections.BaseSocketConnection>` instead.

    Examples::

        tcp_connection = SocketConnection(host='127.0.0.1', port=17971)
        udp_connection = SocketConnection(host='127.0.0.1', port=17971, proto='udp')
        udp_connection_2_way = SocketConnection(host='127.0.0.1', port=17971, proto='udp', bind=('127.0.0.1', 17972)
        udp_broadcast = SocketConnection(host='127.0.0.1', port=17971, proto='udp', bind=('127.0.0.1', 17972),
                                         udp_broadcast=True)
        raw_layer_2 = (host='lo', proto='raw-l2')
        raw_layer_2 = (host='lo', proto='raw-l2',
                       l2_dst='\\xFF\\xFF\\xFF\\xFF\\xFF\\xFF', ethernet_proto=socket_connection.ETH_P_IP)
        raw_layer_3 = (host='lo', proto='raw-l3')

    Args:
        host (str): Hostname or IP address of target system, or network interface string if using raw-l2 or raw-l3.
        port (int): Port of target service. Required for proto values 'tcp', 'udp', 'ssl'.
        proto (str): Communication protocol ("tcp", "udp", "ssl", "raw-l2", "raw-l3"). Default "tcp".
            raw-l2: Send packets at layer 2. Must include link layer header (e.g. Ethernet frame).
            raw-l3: Send packets at layer 3. Must include network protocol header (e.g. IPv4).
        bind (tuple (host, port)): Socket bind address and port. Required if using recv() with 'udp' protocol.
        send_timeout (float): Seconds to wait for send before timing out. Default 5.0.
        recv_timeout (float): Seconds to wait for recv before timing out. Default 5.0.
        ethernet_proto (int): Ethernet protocol when using 'raw-l3'. 16 bit integer.
            Default ETH_P_IP (0x0800) when using 'raw-l3'. See "if_ether.h" in Linux documentation for more options.
        l2_dst (str): Layer 2 destination address (e.g. MAC address). Used only by 'raw-l3'.
            Default '\xFF\xFF\xFF\xFF\xFF\xFF' (broadcast).
        udp_broadcast (bool): Set to True to enable UDP broadcast. Must supply appropriate broadcast address for send()
            to work, and '' for bind host for recv() to work.
        server (bool): Set to True to enable server side fuzzing.
        sslcontext (ssl.SSLContext): Python SSL context to be used. Required if server=True or server_hostname=None.
        server_hostname (string): server_hostname, required for verifying identity of remote SSL/TLS server.

    """

    warnings.warn(
        "SocketConnection is deprecated and will be removed in a future version of Boofuzz. "
        "Use the classes derived from BaseSocketConnection instead.",
        FutureWarning,
    )
    if proto not in _PROTOCOLS:
        raise exception.SullyRuntimeError("INVALID PROTOCOL SPECIFIED: %s" % proto)

    if proto in _PROTOCOLS_PORT_REQUIRED and port is None:
        raise ValueError("__init__() argument port required for protocol {0}".format(proto))

    if proto == "udp":
        return udp_socket_connection.UDPSocketConnection(
            host, port, send_timeout, recv_timeout, server, bind, udp_broadcast
        )
    elif proto == "tcp":
        return tcp_socket_connection.TCPSocketConnection(host, port, send_timeout, recv_timeout, server)
    elif proto == "ssl":
        return ssl_socket_connection.SSLSocketConnection(
            host, port, send_timeout, recv_timeout, server, sslcontext, server_hostname
        )
    elif proto == "raw-l2":
        return raw_l2_socket_connection.RawL2SocketConnection(host, send_timeout, recv_timeout)
    elif proto == "raw-l3":
        if ethernet_proto is None:
            ethernet_proto = raw_l3_socket_connection.ETH_P_IP

        return raw_l3_socket_connection.RawL3SocketConnection(host, send_timeout, recv_timeout, ethernet_proto, l2_dst)
```

从源码中可以看到，所谓的SocketConnection，更像是一个wrapper或者说分发器，根据用户传入的proto字段，进行函数的选择，如果选择的是tcp，则会去调用connection目录下实现的tcp_socket_connection,如果选择的是udp，则会去调用udp_socket_connection，而其他的参数如host,port,timeout类的参数则会原封不动的传递给细化的connection实现函数。

boofuzz中实现了一部分的协议，如果遇到一些非主流协议也可以自行设计一个socket_connection函数，然后添加到上面去，根据proto字段进行选择，这也是为什么说boofuzz的可扩展性很强，代码之间耦合度较低，可以很方便的进行模块开发，对于boofuzz已经实现了的协议，我们来挑选一个最主流的tcp协议深入进去学习一下：
```python
from __future__ import absolute_import

import errno
import socket
import sys

from future.utils import raise_

from boofuzz import exception
from boofuzz.connections import base_socket_connection

class TCPSocketConnection(base_socket_connection.BaseSocketConnection):
    """BaseSocketConnection implementation for use with TCP Sockets.

    .. versionadded:: 0.2.0

    Args:
        host (str): Hostname or IP adress of target system.
        port (int): Port of target service.
        send_timeout (float): Seconds to wait for send before timing out. Default 5.0.
        recv_timeout (float): Seconds to wait for recv before timing out. Default 5.0.
        server (bool): Set to True to enable server side fuzzing.

    """

    def __init__(self, host, port, send_timeout=5.0, recv_timeout=5.0, server=False):
        super(TCPSocketConnection, self).__init__(send_timeout, recv_timeout)

        self.host = host
        self.port = port
        self.server = server
        self._serverSock = None

    def close(self):
        super(TCPSocketConnection, self).close()

        if self.server:
            self._serverSock.close()

    def open(self):
        self._open_socket()
        self._connect_socket()

    def _open_socket(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # call superclass to set timeout sockopt
        super(TCPSocketConnection, self).open()

    def _connect_socket(self):
        if self.server:
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                self._sock.bind((self.host, self.port))
            except socket.error as e:
                if e.errno == errno.EADDRINUSE:
                    raise exception.BoofuzzOutOfAvailableSockets()
                else:
                    raise

            self._serverSock = self._sock
            try:
                self._serverSock.listen(1)
                self._sock, addr = self._serverSock.accept()
            except socket.error as e:
                # When connection timeout expires, tear down the server socket so we can re-open it again after
                # restarting the target.
                self.close()
                if e.errno in [errno.EAGAIN]:
                    raise exception.BoofuzzTargetConnectionFailedError(str(e))
                else:
                    raise
        else:
            try:
                self._sock.connect((self.host, self.port))
            except socket.error as e:
                if e.errno == errno.EADDRINUSE:
                    raise exception.BoofuzzOutOfAvailableSockets()
                elif e.errno in [errno.ECONNREFUSED, errno.EINPROGRESS, errno.ETIMEDOUT]:
                    raise exception.BoofuzzTargetConnectionFailedError(str(e))
                else:
                    raise

    def recv(self, max_bytes):
        """
        Receive up to max_bytes data from the target.

        Args:
            max_bytes (int): Maximum number of bytes to receive.

        Returns:
            Received data.
        """
        data = b""

        try:
            data = self._sock.recv(max_bytes)
        except socket.timeout:
            data = b""
        except socket.error as e:
            if e.errno == errno.ECONNABORTED:
                raise_(
                    exception.BoofuzzTargetConnectionAborted(socket_errno=e.errno, socket_errmsg=e.strerror),
                    None,
                    sys.exc_info()[2],
                )
            elif (e.errno == errno.ECONNRESET) or (e.errno == errno.ENETRESET) or (e.errno == errno.ETIMEDOUT):
                raise_(exception.BoofuzzTargetConnectionReset(), None, sys.exc_info()[2])
            elif e.errno == errno.EWOULDBLOCK:  # timeout condition if using SO_RCVTIMEO or SO_SNDTIMEO
                data = b""
            else:
                raise

        return data

    def send(self, data):
        """
        Send data to the target. Only valid after calling open!

        Args:
            data: Data to send.

        Returns:
            int: Number of bytes actually sent.
        """
        num_sent = 0

        try:
            num_sent = self._sock.send(data)
        except socket.error as e:
            if e.errno == errno.ECONNABORTED:
                raise_(
                    exception.BoofuzzTargetConnectionAborted(socket_errno=e.errno, socket_errmsg=e.strerror),
                    None,
                    sys.exc_info()[2],
                )
            elif e.errno in [errno.ECONNRESET, errno.ENETRESET, errno.ETIMEDOUT, errno.EPIPE]:
                raise_(exception.BoofuzzTargetConnectionReset(), None, sys.exc_info()[2])
            else:
                raise

        return num_sent

    @property
    def info(self):
        return "{0}:{1}".format(self.host, self.port)

```

可以看到其实TCPSocketConnection是socket的一层wrapper，在socket库的基础上包装了send和recv等函数，将ip和port等信息传入到socket库中并调用一系列函数进行连接的建立。同时针对连接失败的情况做出了详细的错误抛出。

到这里我们可以直观的理解为，SocketConnection("127.0.0.1", 80, proto='tcp')就是和指定的ip和port做了一个proto协议的连接，除此之外还可以添加timeout等额外参数。并且整个connection目录都是为了这个目标所服务的。

接下来我们分析第二层的Target类，先来看看作者对Target的描述：
```
Takes an ITargetConnection and wraps send/recv with appropriate
    FuzzDataLogger calls.

    Encapsulates pedrpc connection logic.

    Contains a logger which is configured by Session.add_target().

    Example:
        tcp_target = Target(SocketConnection(host='127.0.0.1', port=17971))

    Args:
        connection (itarget_connection.ITargetConnection): Connection to system under test.
        monitors (List[Union[IMonitor, pedrpc.Client]]): List of Monitors for this Target.
        monitor_alive: List of Functions that are called when a Monitor is alive. It is passed
                          the monitor instance that became alive. Use it to e.g. set options
                          on restart.
        repeater (repeater.Repeater): Repeater to use for sending. Default None.
        procmon: Deprecated interface for adding a process monitor.
        procmon_options: Deprecated interface for adding a process monitor.
```

由于后续的代码会越来越长，所以不再将所有代码全部放上来，而是挑出其中逻辑密集值得分析的部分。

来看看Target类的init参数：
```python
def __init__(
        self,
        connection,
        monitors=None,
        monitor_alive=None,
        max_recv_bytes=10000,
        repeater=None,
        procmon=None,
        procmon_options=None,
        **kwargs
    ):
        self._fuzz_data_logger = None

        self._target_connection = connection
        self.max_recv_bytes = max_recv_bytes
        self.repeater = repeater
        self.monitors = monitors if monitors is not None else []
```
其中connection是必选的，并且会在后续的处理中给到_target_connection属性

除了connection之外，还可以设置监视器（monitors），最大接收字节数，repeater等等。对于其他功能我们后续逐步解锁，现在我们依然遵循这官方样例进行，更多的关注_target_connection参与了怎样的逻辑过程。

Target也注册了属于自己的send和recv，这和connection所定义的区别在哪里呢，来看看源码怎么说：
```python
def recv(self, max_bytes=None):
        """
        Receive up to max_bytes data from the target.

        Args:
            max_bytes (int): Maximum number of bytes to receive.

        Returns:
            Received data.
        """
        if max_bytes is None:
            max_bytes = self.max_recv_bytes

        if self._fuzz_data_logger is not None:
            self._fuzz_data_logger.log_info("Receiving...")

        data = self._target_connection.recv(max_bytes=max_bytes)

        if self._fuzz_data_logger is not None:
            self._fuzz_data_logger.log_recv(data)

        return data
```

嗯所以其实这个Target层面定义的send和recv，是connection所定义的send和recv的一个wrapper，传了一个max_bytes参数，并且在调用connection之前和之后增加了logger的逻辑，用来打印日志。

Target的用处更多的是体现在了repeater和monitor上，所以这里不必多做停留，继续分析上层的session，在源码笔记（一）和（二）中我们致力于研究明白官方案例就好。

```python
def __init__(
        self,
        session_filename=None,
        index_start=1,
        index_end=None,
        sleep_time=0.0,
        restart_interval=0,
        web_port=constants.DEFAULT_WEB_UI_PORT,
        keep_web_open=True,
        console_gui=False,
        crash_threshold_request=12,
        crash_threshold_element=3,
        restart_sleep_time=5,
        restart_callbacks=None,
        restart_threshold=None,
        restart_timeout=None,
        pre_send_callbacks=None,
        post_test_case_callbacks=None,
        post_start_target_callbacks=None,
        fuzz_loggers=None,
        fuzz_db_keep_only_n_pass_cases=0,
        receive_data_after_each_request=True,
        check_data_received_each_request=False,
        receive_data_after_fuzz=False,
        ignore_connection_reset=False,
        ignore_connection_aborted=False,
        ignore_connection_issues_when_sending_fuzz_data=True,
        ignore_connection_ssl_errors=False,
        reuse_target_connection=False,
        target=None,
        db_filename=None,
    ):
```

session涉及到的东西非常之多，并且target此时也并不是一个必选参数了。
在init逻辑中有这样几行代码：
```python
if target is not None:

            def apply_options(monitor):
                monitor.set_options(crash_filename=self._crash_filename)

                return

            target.monitor_alive.append(apply_options)

            try:
                self.add_target(target)
            except exception.BoofuzzRpcError as e:
                self._fuzz_data_logger.log_error(str(e))
                raise
```
session类实例化的时候会去检测是否传入了target参数，如果传入了的话则调用add_target函数，这个函数是session类中所实现的一个函数，来看看怎么写的：
```python
def add_target(self, target):
        """
        Add a target to the session. Multiple targets can be added for parallel fuzzing.

        Args:
            target (Target): Target to add to session
        """

        # pass specified target parameters to the PED-RPC server.
        target.monitors_alive()
        target.set_fuzz_data_logger(fuzz_data_logger=self._fuzz_data_logger)

        if self._callback_monitor not in target.monitors:
            target.monitors.append(self._callback_monitor)

        # add target to internal list.
        self.targets.append(target)
```
作者将其描述为，添加一个目标到session中，并且允许添加多个target去进行并行化的fuzzing。而self.targets则是在init函数中所初始化的一个列表数据结构
```python
self.mutant_index = 0  # index within currently mutating element
        self.num_cases_actually_fuzzed = 0
        self.fuzz_node = None  # Request object currently being fuzzed
        self.current_test_case_name = ""
        self.targets = []
        self.monitor_results = {}  # map of test case indices to list of crash synopsis strings (failed cases only)
        # map of test case indices to list of supplement captured data (all cases where data was captured)
        self.monitor_data = {}
        self.is_paused = False
        self.crashing_primitives = {}
```

所以对于这行代码：
```python
session = Session(
        target=Target(
            connection=SocketConnection("127.0.0.1", 80, proto='tcp')
        ),
    )
```
我们已经给出了完整的解释，即首先通过设置proto为tcp，调用SocketConnection，从而调用内部的tcp_socket_connection函数最终调用socket库完成accept,bind等一系列操作完成连接的构建。而后调用Target进行实例化，不设置repeater和moniter，只设定了connection，得到了一个进一步包装了send,recv等函数的对象。
最后调用Session，并将Target所返回的object作为target参数，将target加入到Session实例好的target_list列表中，准备进行后续的fuzz。

设置好session之后，继续分析下一行代码
```python
s_initialize("new request")
```

其源码存在于整个boofuzz代码结构的根路径下的init文件中：
```python
def s_initialize(name):
    """
    Initialize a new block request. All blocks / primitives generated after this call apply to the named request.
    Use s_switch() to jump between factories.

    :type  name: str
    :param name: Name of request
    """
    if name in blocks.REQUESTS:
        raise exception.SullyRuntimeError("blocks.REQUESTS ALREADY EXISTS: %s" % name)

    blocks.REQUESTS[name] = Request(name)
    blocks.CURRENT = blocks.REQUESTS[name]
```
用作者的话来说，s_initialize，函数初始化了一个新的request，所有的blocks或者primitives都需要先进行s_initialize，它接收一个单独的name参数，然后判断name是否在blocks.REQUESTS中存在，如果已经存在则抛出异常，如果不存在则执行下面两行语句。首先来看blocks.REQUESTS是什么：

```python
from .aligned import Aligned
from .block import Block
from .checksum import Checksum
from .repeat import Repeat
from .request import Request
from .size import Size

__all__ = ["Block", "Checksum", "Repeat", "Request", "Size", "REQUESTS", "Aligned"]

REQUESTS = {}
CURRENT = None
```
可以看出blocks.REQUESTS是一个字典结构

所以其实就是每次调用s_initialize，都会将一个新的request加入到字典中，并且切换当前正在工作的request为新建的这个。即调用s_initialize之后，在没有新的s_initialize或者s_switch去切换当前工作request之前，所有的原语都是在操作这个新建的request。

接下来是新建块以及一系列的原语操作：
```python
with s_block("Request-Line"):
        s_group("Method", ['GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'CONNECT', 'OPTIONS', 'TRACE'])
        s_delim(" ", name='space-1')
        s_string("/index.html", name='Request-URI')
        s_delim(" ", name='space-2')
        s_string('HTTP/1.1', name='HTTP-Version')
        s_static("\r\n", name="Request-Line-CRLF")
    s_static("\r\n", "Request-CRLF")
```

有关原语的参数含义，在文章开头已经有了详细的描述，接下里我们说说s_block()
老样子先看源码：
```python
def s_block(name=None, group=None, encoder=None, dep=None, dep_value=None, dep_values=None, dep_compare="=="):
    """
    Open a new block under the current request. The returned instance supports the "with" interface so it will
    be automatically closed for you::

        with s_block("header"):
            s_static("\\x00\\x01")
            if s_block_start("body"):
                ...
```
作者将此函数描述为，在当前request下打开一个新的block，并且支持with操作，即无需手动关闭。

```python
block = s_block_start(
        name,
        request=blocks.CURRENT,
        group=group,
        encoder=encoder,
        dep=dep,
        dep_value=dep_value,
        dep_values=dep_values,
        dep_compare=dep_compare,
    )
```
block本身有一个必选的name参数，用来唯一标识block。在起类内部定义了大量的原语函数，比如s_group,s_string,s_static等等，我们挑出其中几个来看看：

```python
def s_static(value=None, name=None):
    """
    Push a static value onto the current block stack.

    :see: Aliases: s_dunno(), s_raw(), s_unknown()

    :type  value: Raw
    :param value: Raw static data
    :type  name:  str
    :param name:  (Optional, def=None) Specifying a name gives you direct access to a primitive
    """

    blocks.CURRENT.push(Static(name=name, default_value=value))
```
注释有很多，说明了其功能和特性等等，真正的代码只有一句，即实例化了一个Static类并通过push方法加入到当前blocks.CURRENT中，而Static类实现在了primitives中，这个目录下面包含了所有原语的具体实现，从文章开头语法介绍那里可以了解到各种常用原语所需参数以及特性。

在源码笔记（二）中会挑出其中几个重点和常用的原语，进一步分析其具体实现源码，以及最后的session.fuzz()逻辑，源码笔记（一）就到这里。
