# 物联网MQTT协议分析
> f10w3rdanc3
> 来源：https://www.iotsec-zone.com/article/219

#MQTT协议简介
MQTT（Message Queuing Telemetry Transport，消息队列遥测传输协议），由IBM在1999年发布，是一种基于发布/订阅（publish/subscribe）模式的“轻量级”通讯协议，该协议构建于TCP/IP协议上。
MQTT协议的优点：**低开销，低带宽占用**。正是因为这个特性，其在物联网、小型设备、移动应用等方面有较广泛的应用。

#一、MQTT服务器搭建：

**引入mosquitto仓库并更新**、
（在开始引入仓库之前可以先update一下系统）
`sudo apt-add-repository ppa:mosquitto-dev/mosquitto-ppa`、

**安装mosquitto服务器和客户端**
	`sudo apt-get install mosquitto   #服务端`
	`sudo apt-get install mosquitto-clients  #客户端（想在windows下测试可以下一个chrome的mqttbox插件）`

**开启/停止mosquitto服务**
`sudo service mosquitto start`
`sudo service mosquitto stop`

**添加用户**
`sudo mosquitto_passwd -c /etc/mosquitto/passwd test`

![0.png](https://www.iotsec-zone.com/images/MdImg/b5fa74e60dd6874610aa14c32473b6a7.png)

**对服务器进行配置**
`sudo nano /etc/mosquitto/conf.d/default.conf`

执行命令后会打开一个新的文件，粘贴以下内容：
```shell
allow_anonymous false
password_file /etc/mosquitto/passwd
```
之后使用 Ctrl+O，Enter 和 Ctrl+X 保存并退出文本编辑器,再重启Mosquitto 服务器

`sudo systemctl restart mosquitto`

**查看mosquitto服务状态**
执行完以上命令之后就可以查看服务器状态了
`sudo service mosquitto status`

![1.png](https://www.iotsec-zone.com/images/MdImg/5bbe789eac0acce3ec98345a47e81f40.png)

#二、MQTT建立通信
在成功搭建服务器之后，我们就可以建立通信了，因为我们在第一部分把client端也下载了，所以可以打开两个终端作为订阅方和发布方，如下图所示：
使用`mosquitto_sub -t "test" -u "test" -P "password"`和`mosquitto_pub -t "test" -m "message from mosquitto_pub client"`来相互通信

![2.png](https://www.iotsec-zone.com/images/MdImg/580219999b24fd43e42563e8a31c4f11.png)
这里的*-t*参数是指**主题（topic）**，作为双方匹配的依据
同时我们也可以在本机上使用软件进行通信（在这里我们使用的是MQTTX作为订阅方）
![3.png](https://www.iotsec-zone.com/images/MdImg/a0f7d6bed2b91de5831d020c751dbe22.png)
连接成功后可以进行通信（前提是主机和服务器之间是连通的）
![4.png](https://www.iotsec-zone.com/images/MdImg/e105bbb174156bbfbaae2d0ed40e519b.png)
在成功建立通信后，我们就可以抓取流量了

#三、MQTT协议格式解析
##MQTT基本特点
![5.png](https://www.iotsec-zone.com/images/MdImg/8bfa8892353c37272385f733d65b279d.png)
在通讯过程中，MQTT协议中有三种身份：发布者（Publish）、代理（Broker,服务器）、订阅者（Subscribe）。其中，消息的发布者和订阅者都是客户端，消息代理是服务器，消息发布者可以同时是订阅者。
MQTT传输的消息分为：主题（Topic）和负载（payload）两部分：
（1）Topic，可以理解为消息的类型，订阅者订阅（Subscribe）后，就会收到该主题的消息内容（payload）；
（2）Payload，可以理解为消息的内容，是指订阅者具体要使用的内容

###基本概念
**MQTT 客户端**
一个使用 MQTT 协议的设备、应用程序等，它总是建立到服务器的网络连接，具有以下功能：
- 可以发布信息，其他客户端可以订阅该信息
- 订阅其它客户端发布的消息
- 退订或删除应用程序的消息
- 断开与服务器连接

**MQTT 服务器**
MQTT 服务器也称为 Broker（消息代理），以是一个应用程序或一台设备。它是位于消息发布者和订阅者之间，具有以下功能：
- 接受来自客户端的网络连接
- 接受客户端发布的应用信息
- 处理来自客户端的订阅和退订请求
- 向订阅的客户转发应用程序消息

**主题（Topic）**
连接到一个应用程序消息的标签，该标签与服务器的订阅相匹配。服务器会将消息发送给订阅所匹配标签的每个客户端。
- 要订阅的主题。一个主题可以有多个级别，级别之间用斜杠字符分隔。例如，/world 和 emq/emqtt/emqx 是有效的主题。
- 订阅者的Topic name支持通配符#和+ ：
- -  '#'支持一个主题内任意级别话题
- - '+'只匹配一个主题级别的通配符
- 客户端成功订阅某个主题后，代理会返回一条 SUBACK 消息，其中包含一个或多个 returnCode 参数

**筛选器（Topic Filter）**
一个对主题名通配符筛选器，在订阅表达式中使用，表示订阅所匹配到的多个主题。
**QoS（消息传递的服务质量水平）**
服务质量，标志表明此主题范围内的消息传送到客户端所需的一致程度，其中值表示如下：
- 值 0：不可靠，消息基本上仅传送一次，如果当时客户端不可用，则会丢失该消息。
- 值 1：消息应传送至少 1 次。
- 值 2：消息仅传送一次。

**会话（Session）**
每个客户端与服务器建立连接后就是一个会话，客户端和服务器之间有状态交互。会话存在于一个网络之间，也可能在客户端和服务器之间跨越多个连续的网络连接。

**订阅（Subscription）**
订阅包含主题筛选器（Topic Filter）和最大服务质量（QoS）。订阅会与一个会话（Session）关联。一个会话可以包含多个订阅。每一个会话中的每个订阅都有一个不同的主题筛选器。
- 客户端在成功建立TCP连接之后，发送CONNECT消息，在得到服务器端授权允许建立彼此连接的CONNACK消息之后，客户端会发送SUBSCRIBE消息，订阅感兴趣的Topic主题列表（至少一个主题） 
- 订阅的主题名称采用UTF-8编码，然后紧跟着对应的QoS值

**发布（publish）**
控制报文是指从客户端向服务端或者服务端向客户端传输一个应用消息，MQTT 客户端发送消息请求，发送完成后返回应用程序线程。

**负载（Payload）**
消息订阅者所具体接收的内容

##MQTT协议中的方法
消息订阅者所具体接收的内容，MQTT协议中定义了一些方法（也被称为动作），来于表示对确定资源所进行操作。这个资源可以代表预先存在的数据或动态生成数据，这取决于服务器的实现。通常来说，资源指服务器上的文件或输出。主要方法有：
1)	Connect。等待与服务器建立连接。
2)	Disconnect。等待MQTT客户端完成所做的工作，并与服务器断开TCP/IP会话。
3)	Subscribe。等待完成订阅。
4)	UnSubscribe。等待服务器取消客户端的一个或多个topics订阅。
5)	Publish。MQTT客户端发送消息请求，发送完成后返回应用程序线程。
![6.png](https://www.iotsec-zone.com/images/MdImg/fbce2105c25fe9a55b65d56000529216.png)

##MQTT协议数据包结构
在MQTT协议中，一个MQTT数据包由：固定头（Fixed header）、可变头（Variable header）、消息体（payload）三部分构成。
1)	**固定头（Fixed header）**。存在于所有MQTT数据包中，表示数据包类型及数据包的分组类标识。协议版本3定义了14种MQTT报文，用于建立/断开连接、发布消息、订阅消息和维护连接。固定报头的第一字节的4-7位的值指定了报文类型，其取值如下表。0和15为系统保留值；0-3位为标志位，依照报文类型有不同的含义，事实上，除了PUBLISH报文以外，其他报文的标志位均为系统保留。如果收到报文的标志位无效，代理应断开连接
![7.png](https://www.iotsec-zone.com/images/MdImg/7212877da5527f86b9a9e5fb9916d1bc.png)

2)	**可变头（Variable header）**。某些控制报文包含可变报头，它在固定报头（Fixed header）和有效载荷（Payload）之间。每个协议的可变报头都不一样。其中大多数协议都会有的字段是报文标识符。可变报头在各个控制报文的详细内容中再展开讲解
3)	**消息体（Payload）**。有效载荷是除控制报文格式以外的有效信息，CONNECT、PUBLISH、SUBSCRIBE等需要传递有效信息的协议帧都需要。。
后续将会以下表固定头部的报文类型进行展开分析

报文类型	值	描述
CONNECT	0x10	客户端向代理发起连接请求
CONNACK	0x20	连接确认
PUBLISH	0x30	发布消息
PUBACK	0x40	发布确认
PUBREC	0x50	发布收到（QoS2）
PUBREL	0x60	发布释放（QoS2）
PUBCOMP	0x70	发布完成（QoS2）
SUBSCRIBE	0x80	客户端向代理发起订阅请求
SUBACK	0x90	订阅确认
UNSUBSCRIBE	0xA2	取消订阅
UNSUBACK	0xB0	取消订阅确认
PINGREQ	0xC0	PING请求
PINGRESP	0xD0	PING响应
DISCONNECT	0xE0	断开连接

###CONNECT	0x10
CONNECT 协议是客户端建立连接的第一个报文，通常都要带有鉴权的字段，一个CONNECT报文都会对应一个服务端的CONNACK报文，如下图所示
![8.png](https://www.iotsec-zone.com/images/MdImg/5435422a1fb993218b10bf1213a11711.png)
**固定头**
固定头主要分为两个部分，前四位代表消息类型，后四位代表保留值，除UNSUBSCRIBE之外，其余的保留值都为0.
![9.png](https://www.iotsec-zone.com/images/MdImg/65b1373358c1ebe5703a6875220cca4b.png)

**可变头**
可变头的结构如下：

|1-2|  Protocol Name Length，协议名称的长度 |
| ------------ | ------------ |
|3-6|  Protocol Name，协议名称 |
|7| Version, MQTT版本号  |
|8| Connect Flags, 连接的标志（下文会细讲）  |
|9-10| Keep Alive, 表示为心跳间隔  |
![10.png](https://www.iotsec-zone.com/images/MdImg/7c7b1647bd8bf7c767cd26637be4568c.png)

对于byte 8，其结构如下：
- User Name Flag：用户名标志位，1表示启用用户名，有效载荷中必须包含用户名字段；0表示不启用用户名，有效载荷中不能包含用户名字段。正常都传用户名。如果不启用用户名时，密码也不能启用
- Password Flag：密码标志位，1表示启用密码，有效载荷中必须包含密码字段；0表示不启用密码，有效载荷中不能包含密码字段。正常都传密码
- Will Retain：遗嘱保留标志位，1表示启用遗嘱保留，0表示关闭遗嘱保留。 遗嘱标志位关闭时，强制为0
- Qos Level：表示遗嘱Qos，遗嘱标志位关闭时，强制填00，遗嘱标志位启用时，可以为00（qos0）、01（qos1）、10（qos2）
- Will Flag：遗嘱标志位，1表示启用遗嘱功能，0则表示关闭遗嘱功能。启用时，连接标志中的Will Qos（第3、4位），Will Retain （第5位）会被使用，有效载荷中必须包含 遗嘱topic（Will Topic）、遗嘱消息（Will Message）字段；未启用时，连接标志中的Will Qos（第3、4位），Will Retain （第5位）必须为0，。一般选用0
- Clean Session Flag：会话清理标志， 1表示每次建立连接，要求服务端重新开启会话；0则表示服务端会话持久化。一般选用1
- Reserved: 此位为保留位，固定为0
![11.png](https://www.iotsec-zone.com/images/MdImg/d325e342dd0ccef971c112f730931c80.png)

其中的Qos Level参考上文中的基本概念。
关于遗嘱相关概念如下：
当客户端启用遗嘱功能时，在CONNECT协议包的可变报头的连接标志中，必须打开遗嘱标志（byte8的第2位），并在有效载荷中传递遗嘱主题和遗嘱消息。当服务端判断客户端异常断开时，服务端会向遗嘱主题发送遗嘱消息。遗嘱消息发布的条件，包括但不限于：
- 服务端检测到了一个I/O错误或者网络故障。
- 客户端在保持连接（Keep Alive）的时间内未能通讯。
- 客户端没有先发送DISCONNECT报文直接关闭了网络连接。
- 由于协议错误服务端关闭了网络连接。
当启用遗嘱时，在标志位中可以设置遗嘱消息的Qos
当启用遗嘱保留标志时，表示遗嘱消息在发布时需要保留。 说人话的意思就是，启动遗嘱保留时，服务端要持久化该遗嘱消息（仅仅保留最新一条），其他人后订阅该遗嘱主题时，能收到最后一次的遗嘱消息。

**消息体**
消息体的结构如下:
- Client ID Length：标识符的长度
- Client ID：连接时的唯一标识符
- User Name Length：用户名的长度
- User Name：用户名
- Password Length：密码的长度
- Password：用户输入的密码
![12.png](https://www.iotsec-zone.com/images/MdImg/6a9e030eaaf08e0268a01662fc1caac8.png)

###CONNACK	0x20
建立连接的响应包，报文内容会返回连接成功标志。
**固定头**
![13.png](https://www.iotsec-zone.com/images/MdImg/19932e5995af1d3d072800b4c009f559.png)

**可变头**
第1个字节是连接确认标志，位7-1是保留位且必须设置为0。 第0 (SP)位 是当前会话（Session Present）标志。当服务端建立连接时，会话是新创建的时，SP返回0；会话是之前持久化的会话，且客户端传的清理会话标志没有开启时，SP返回1。第2个字节为连接返回码
![14.png](https://www.iotsec-zone.com/images/MdImg/90cd48f5d620a99d7db08c6298e15133.png)

返回码类型如下：

|  值 |  返回码响应 |  描述 |
| ------------ | ------------ | ------------ |
| 0  |  0x00 连接已接受 |  连接已被服务端接受 |
| 1  |  0x01 连接已拒绝，不支持的协议版本 | 服务端不支持客户端请求的 MQTT 协议级别  |
|  2 |  0x02 连接已拒绝，不合格的客户端标识符 | 客户端标识符是正确的 UTF-8 编码，但服务 端不允许使用  |
|  3 |  0x03 连接已拒绝，服务端不可用 |  网络连接已建立，但 MQTT 服务不可用 |
| 4  |  0x04 连接已拒绝，无效的用户名或密码 | 用户名或密码的数据格式无效  |
|  5 |  0x05 连接已拒绝，未授权 | 客户端未被授权连接到此服务器  |
|  6-255 |   |  保留 |

###PUBLISH	0x30
Publish控制报文是指从客户端向服务端或者服务端向客户端传输一个应用消息。
**固定头**
![15.png](https://www.iotsec-zone.com/images/MdImg/74e94af298c196f7cd3ffb203b692e3d.png)

DUP Flag：重发标志，如果 DUP 标志被设置为 0，表示这是客户端或服务端第一次请求发送这个 PUBLISH 报文。如果 DUP 标志被设置为 1，表示这可能是一个早前报文请求的重发。客户端或服务端请求重发一个 PUBLISH 报文时，必须将 DUP 标志设置为 1。对于 QoS 0 的消息，DUP 标志必须设置为 0 。服务端发送 PUBLISH 报文给订阅者时，收到（入站）的 PUBLISH 报文的 DUP 标志的值不会被传播。发送（出站）的 PUBLISH 报文与收到（入站）的 PUBLISH 报文中的 DUP 标志是独立设置的，它的值必须单独的根据发送（出站）的 PUBLISH 报文是否是一个重发来确定
**可变头**
![16.png](https://www.iotsec-zone.com/images/MdImg/1ad514ffcb0cd6e974a968a4c9a90528.png)

**消息体**
有效载荷包含将被发布的应用消息。数据的内容和格式是应用特定的。有效载荷的长度这样计算：用固定报头中的剩余长度字段的值减去可变报头的长度。包含零长度有效载荷的 PUBLISH 报文是合法的。
Message Identifier：类似于消息的标识符

![17.png](https://www.iotsec-zone.com/images/MdImg/7e1cb2308f8e85466f5c686616104fbe.png)
![18.png](https://www.iotsec-zone.com/images/MdImg/d60e394d109e1db1e142c6fe7bffaf8e.png)

###PUBACK	0x40
PUBACK 报文是对 QoS 1 等级的 PUBLISH 报文的响应。
**固定头**
![19.png](https://www.iotsec-zone.com/images/MdImg/769a39262d48e549a5f0282e19241533.png)

**消息体**
![20.png](https://www.iotsec-zone.com/images/MdImg/4a471fd55a5ee332d1244762f06f1163.png)

###PUBREC	0x50– 发布收到（QoS 2，第一步）
PUBREC 报文是对 QoS 等级 2 的 PUBLISH 报文的响应。它是 QoS 2 等级协议交换的第二个报文。
**固定头**
![21.png](https://www.iotsec-zone.com/images/MdImg/5857a7e4af15f669d2131ef2834d2183.png)

**可变头**
![22.png](https://www.iotsec-zone.com/images/MdImg/6cf206a53b217d323e58dfa14ecc85c4.png)

###PUBREL	0x60– 发布释放（QoS 2，第二步）
PUBREL 报文是对 PUBREC 报文的响应。它是 QoS 2 等级协议交换的第三个报文。
**固定头**
![23.png](https://www.iotsec-zone.com/images/MdImg/be1f4f24e42f26f373437295b841efd3.png)

**可变头**
![24.png](https://www.iotsec-zone.com/images/MdImg/2258229a11636b2e73182ce4ea47099f.png)

###PUBCOMP	0x70-发布完成（QoS 2，第三步）
PUBCOMP 报文是对 PUBREL 报文的响应。它是 QoS 2 等级协议交换的第四个也是最后一个报文。
**固定头**
![25.png](https://www.iotsec-zone.com/images/MdImg/869a5ebba19c6b604ea685072f3b20f2.png)

**可变头**
![26.png](https://www.iotsec-zone.com/images/MdImg/edc6503dd03d3fd9026cc15ca23ad621.png)

###SUBSCRIBE	0x80
客户端向服务端发送 SUBSCRIBE 报文用于创建一个或多个订阅。每个订阅注册客户端关心的一个或多个主题。为了将应用消息转发给与那些订阅匹配的主题，服务端发送 PUBLISH 报文给客户端。SUBSCRIBE报文也（为每个订阅）指定了最大的 QoS 等级，服务端根据这个发送应用消息给客户端。
**固定头**
SUBSCRIBE 控制报固定报头的第 3,2,1,0 位是保留位，必须分别设置为 0,0,1,0。服务端必须将其它的任何值都当做是不合法的并关闭网络连接。
![27.png](https://www.iotsec-zone.com/images/MdImg/2b4d19acd68d96e5bce967b8c0e9a221.png)

**可变头**
![28.png](https://www.iotsec-zone.com/images/MdImg/3cf43266db9fd434a712cf981f5cf063.png)

**消息体**
SUBSCRIBE报文的有效载荷包含了一个主题过滤器列表，它们表示客户端想要订阅的主题，每一个过滤器后面跟着一个字节，这个字节被叫做服务质量要求（Requested QoS）。它给出了服务端向客户端发送应用消息所允许的最大 QoS 等级。
![29.png](https://www.iotsec-zone.com/images/MdImg/30cbfd9bfa93c4d6d6de753f82a5b482.png)

###SUBACK	0x90
服务端收到客户端发送的一个 SUBSCRIBE 报文时，必须使用 SUBACK 报文响应。SUBACK 报文必须和等待确认的 SUBSCRIBE 报文有相同的报文标识符。
**固定头**
![30.png](https://www.iotsec-zone.com/images/MdImg/df1c9b86bbc05253bdc9c82885811514.png)

**可变头**
![31.png](https://www.iotsec-zone.com/images/MdImg/255ee54fefb448e770eaadddedbacf9c.png)

**消息体**
有效载荷包含一个返回码清单。每个返回码对应等待确认的 SUBSCRIBE 报文中的一个主题过滤器。返回码的顺序必须和 SUBSCRIBE 报文中主题过滤器的顺序相同。
![32.png](https://www.iotsec-zone.com/images/MdImg/3e808afc15be5004177fc38dd8b3e0be.png)

###UNSUBSCRIBE	0xA2
客户端发送 UNSUBSCRIBE 报文给服务端，用于取消订阅主题
**固定头**
![33.png](https://www.iotsec-zone.com/images/MdImg/46fcbfbd19c23d21680de4116e7c42e8.png)

**可变头**
可变报头包含一个报文标识符
![34.png](https://www.iotsec-zone.com/images/MdImg/5b543c1f0e408a107503e6a4c67700de.png)

**消息体**
UNSUBSCRIBE 报文的有效载荷包含客户端想要取消订阅的主题过滤器列表，UNSUBSCRIBE 报文的有效载荷必须至少包含一个消息过滤器。
![35.png](https://www.iotsec-zone.com/images/MdImg/dd387114324956e2d4cd4119bcc51211.png)

###UNSUBACK	0xB0–取消订阅确认
服务端发送 UNSUBACK 报文给客户端用于确认收到 UNSUBSCRIBE 报文。
**固定头**
![36.png](https://www.iotsec-zone.com/images/MdImg/33a6f40dd1ff818194f70cd6b0d2147d.png)

**可变头**
可变报头包含等待确认的 UNSUBSCRIBE 报文的报文标识符
![37.png](https://www.iotsec-zone.com/images/MdImg/1d7882a7d36693e558f93af6141cd26b.png)

###PINGREQ	0xC0
客户端发送 PINGREQ 报文给服务端的。用于：
1. 在没有任何其它控制报文从客户端发给服务的时，告知服务端客户端还活着。
2. 请求服务端发送 响应确认它还活着。
3. 使用网络以确认网络连接没有断开。
保持连接（Keep Alive）处理中用到这个报文

**固定头**
![38.png](https://www.iotsec-zone.com/images/MdImg/2fa0a132a6835aa4ec9d800833d55d40.png)

**可变头**
PINGREQ 报文没有可变报头
**消息体**
PINGREQ 报文没有有效载荷

###PINGRESP	0xD0
服务端发送 PINGRESP 报文响应客户端的 PINGREQ 报文。表示服务端还活着。
保持连接（Keep Alive）处理中用到这个报文

**固定头**
![39.png](https://www.iotsec-zone.com/images/MdImg/2a842de23ad4ecc03bd0ae371731509b.png)

**可变头**
PINGRESP 报文没有可变报头
**消息体**
PINGRESP 报文没有有效载荷

###DISCONNECT	0xE0
DISCONNECT 报文是客户端发给服务端的最后一个控制报文。表示客户端正常断开连接。
**固定头**
![40.png](https://www.iotsec-zone.com/images/MdImg/254baa9b1a0ce9b3fe5235a645c3cb75.png)

**消息体**
DISCONNECT 报文没有有效载荷

#四、MQTT协议相关安全性研究

##相关学术论文研读
今年研读了一篇徐绘凯学长在S&P2022中发表的一篇安全文章（Trampoline Over the Air: Breaking in IoT Devices Through MQTT Brokers），并有幸能和团队中的一位学长交流分享心得。
这篇文章针对设备处理未授权的MQTT信息时，并未对消息的内容进行判断，很容易产生命令执行等高危漏洞。针对这种情况，文章设计了一个威胁模型（Trampoline Over the Air Attack），并设计了模糊测试工具ShadowFuzzer。
![41.png](https://www.iotsec-zone.com/images/MdImg/472868df6a3e65bc040181e1a9f968d2.png)

![42.png](https://www.iotsec-zone.com/images/MdImg/6517ea829ce2a0f00999cc2f34c17af3.png)

#参考链接
MQTT协议解析参考博客：
**[https://github.com/mcxiaoke/mqtt](https://github.com/mcxiaoke/mqtt)
[https://www.cnblogs.com/jiangzhaowei/p/8779715.html](https://www.cnblogs.com/jiangzhaowei/p/8779715.html)
[https://zhuanlan.zhihu.com/p/164930347](https://zhuanlan.zhihu.com/p/164930347)
[https://zhuanlan.zhihu.com/p/443746027](https://zhuanlan.zhihu.com/p/443746027)
[https://zhuanlan.zhihu.com/p/429891532**](https://zhuanlan.zhihu.com/p/429891532**)
MQTT-PWN：
[https://github.com/akamai-threat-research/mqtt-pwn](https://github.com/akamai-threat-research/mqtt-pwn)
文章链接：
[https://ieeexplore.ieee.org/abstract/document/9797386](https://ieeexplore.ieee.org/abstract/document/9797386)、
[https://github.com/ReAbout/ShadowFuzzer](https://github.com/ReAbout/ShadowFuzzer)
