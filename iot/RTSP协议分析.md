# RTSP协议分析
> 0431物联卫士实验室
> 来源：https://www.iotsec-zone.com/article/418

## RTSP协议分析
> 实时流协议( RTSP )是一种应用级网络协议，旨在通过适当的传输协议对多媒体传输流（例如交互式媒体、视频和音频）进行复用和打包 。RTSP 在娱乐和通信系统中用于控制流媒体服务器。该协议用于建立和控制端点之间的媒体会话。媒体服务器的客户端发出播放、录制等命令 暂停，以便于实时控制从服务器到客户端（视频点播）或从客户端到服务器（录音）的媒体流。

### RTSP协议
RTSP协议在某些方面与HTTP类似，但 RTSP 定义了可用于控制多媒体播放的控制序列。HTTP 是无状态的，而 RTSP 有状态；当需要跟踪并发会话时使用标识符。与 HTTP 一样，RTSP 使用 TCP 来维护端到端连接，虽然大多数 RTSP 控制消息由客户端发送到服务器，但某些命令会沿另一个方向传播（即从服务器到客户端）。

这里介绍的是基本的 RTSP 请求。一些典型的HTTP 请求（例如 OPTIONS 请求）也可用。TCP和UDP的默认传输层端口号都是 554 ，后者很少用于控制请求。

RTSP分为服务器与客户端，RTSP协议定义了服务器-客户端之间的接口，主要有OPTIONS，DESCRIBE，SETUP，PLAY，TEARDOWN，RECOED，ANNOUNCE。RTSP并不包括具体数据的传输，该功能一般由RTP与RTCP协议来实现，并可以通过TCP或UDP两种底层传输方式进行。
 
* RTSP，对流媒体提供诸如播放、暂停、快进等操作
* RTP，负责对流媒体数据进行封包并实现媒体流的实时传输
* RTCP，提供流量控制和拥塞控制等

下面我将分别介绍一下几个接口

C->S代表客户端向服务端发送

S->C代表服务端向客户端发送

####  OPTIONS
> 客户端向服务端发送option请求，询问服务端有哪些指令可用。服务端返回可用的指令。
```
C->S:  OPTIONS rtsp://example.com/media.mp4 RTSP/1.0
       CSeq: 1
       Require: implicit-play
       Proxy-Require: gzipped-messages

S->C:  RTSP/1.0 200 OK
       CSeq: 1
       Public: DESCRIBE, SETUP, TEARDOWN, PLAY, PAUSE

```

#### DESCRIBE
> 客户端向服务端发送descripe请求，向服务端请求会话描述信息（一般是SDP），在Content-Type字段中可以得知会话描述信息类型

```
C->S: DESCRIBE rtsp://example.com/media.mp4 RTSP/1.0
      CSeq: 2

S->C: RTSP/1.0 200 OK
      CSeq: 2
      Content-Base: rtsp://example.com/media.mp4
      Content-Type: application/sdp
      Content-Length: 460

      m=video 0 RTP/AVP 96
      a=control:streamid=0
      a=range:npt=0-7.741000
      a=length:npt=7.741000
      a=rtpmap:96 MP4V-ES/5544
      a=mimetype:string;"video/MP4V-ES"
      a=AvgBitRate:integer;304018
      a=StreamName:string;"hinted video track"
      m=audio 0 RTP/AVP 97
      a=control:streamid=1
      a=range:npt=0-7.712000
      a=length:npt=7.712000
      a=rtpmap:97 mpeg4-generic/32000/2
      a=mimetype:string;"audio/mpeg4-generic"
      a=AvgBitRate:integer;65790
      a=StreamName:string;"hinted audio track"
```
SDP(Session Description Protocol)描述会话协议，它只是一种信息格式的描述标准，本身不属于传输协议，但是可以被其他传输协议用来交换必要的信息，用于两个会话实体之间的媒体协商。
SDP的内容格式基本上是  <类型>=<值>。

#### SETUP
SETUP 请求指定必须如何传输单个媒体流。而且因为RTSP是有状态的，所以SETUP请求完成后才能进行下一步。客户端请求中Transport字段包含两个客户端的端口，分别是RTP和RTCP的端口，这两个端口我们在上面说过。同时，在服务端返回的时候也有两个RTP和RTCP对等的端口，并且还返回了一个Session，用于接下来的对话。这个命令主要是协助RTP传输视频流的，在这里我们可以选RTP/AVP和RTP/AVP/TCP，因此我们说视频的推流方式是看客户端的。
```
C->S: SETUP rtsp://example.com/media.mp4/streamid=0 RTSP/1.0
      CSeq: 3
      Transport: RTP/AVP;unicast;client_port=8000-8001

S->C: RTSP/1.0 200 OK
      CSeq: 3
      Transport: RTP/AVP;unicast;client_port=8000-8001;server_port=9000-9001;ssrc=1234ABCD
      Session: 12345678
```

#### PLAY
> play请求将会播放一个媒体流，服务器返回一个RTP的链接，这个RTP就是视频流
```
C->S: PLAY rtsp://example.com/media.mp4 RTSP/1.0
      CSeq: 4
      Range: npt=5-20
      Session: 12345678

S->C: RTSP/1.0 200 OK
      CSeq: 4
      Session: 12345678
      RTP-Info: url=rtsp://example.com/media.mp4/streamid=0;seq=9810092;rtptime=3450012
```

#### PAUSE
> PAUSE 请求会暂时停止一个或所有媒体流，以便稍后可以通过 PLAY 请求恢复。

```
C->S: PAUSE rtsp://example.com/media.mp4 RTSP/1.0
      CSeq: 5
      Session: 12345678

S->C: RTSP/1.0 200 OK
      CSeq: 5
      Session: 12345678
```

#### ANNOUNCE
> 这个步骤主要还是传输SDP，一般来说有两种用途(1)C->S：客户端向服务器端发布URL指定的媒体信息描述；(2) S->C：实时更新对话描述。若媒体表示中新增了一个媒体流，例如在直播过程中，则整个媒体表示的description都要被重新发送，而不是只发送新增部分。
```
C->S: ANNOUNCE rtsp://example.com/media.mp4 RTSP/1.0
      CSeq: 7
      Date: 23 Jan 1997 15:35:06 GMT
      Session: 12345678
      Content-Type: application/sdp
      Content-Length: 332

      v=0
      o=mhandley 2890844526 2890845468 IN IP4 126.16.64.4
      s=SDP Seminar
      i=A Seminar on the session description protocol
      u=http://www.cs.ucl.ac.uk/staff/M.Handley/sdp.03.ps
      e=mjh@isi.edu (Mark Handley)
      c=IN IP4 224.2.17.12/127
      t=2873397496 2873404696
      a=recvonly
      m=audio 3456 RTP/AVP 0
      m=video 2232 RTP/AVP 31

S->C: RTSP/1.0 200 OK
      CSeq: 7
```
#### GET_PARAMETER
> GET_PARAMETER请求用于设置指定媒体流的参数。
```
S->C: GET_PARAMETER rtsp://example.com/media.mp4 RTSP/1.0
      CSeq: 9
      Content-Type: text/parameters
      Session: 12345678
      Content-Length: 15

      packets_received
      jitter

C->S: RTSP/1.0 200 OK
      CSeq: 9
      Content-Length: 46
      Content-Type: text/parameters

      packets_received: 10
      jitter: 0.3838
```
#### TEARDOWN
> TEARDOWN 请求用于终止会话。它会停止所有媒体流并释放服务器上所有与会话相关的数据。
```
C->S: TEARDOWN rtsp://example.com/media.mp4 RTSP/1.0
      CSeq: 8
      Session: 12345678

S->C: RTSP/1.0 200 OK
      CSeq: 8
```

以上就是几个比较重要的请求选项了

### 抓包实测

> 工具是使用Wireshark和VLC视频播放工具

![0.png](https://www.iotsec-zone.com/api/image/v2/20230915/cvj9414h47dpjs1a5c.png)

#### OPTION

C->S

![1.png](https://www.iotsec-zone.com/api/image/v2/20230915/cvj947j1pykgzi4uuk.png)
S->C

![2.png](https://www.iotsec-zone.com/api/image/v2/20230915/cvj94jtoccb9jwxhnx.png)

#### DESCRIBE

C->S

![3.png](https://www.iotsec-zone.com/api/image/v2/20230915/cvj94m8agxrl34mtkb.png)

S->C

![4.png](https://www.iotsec-zone.com/api/image/v2/20230915/cvj94ns4gq29yaa2ud.png)

#### SETUP

C->S

![5.png](https://www.iotsec-zone.com/api/image/v2/20230915/cvj94ppz23cnrk06gh.png)

S->C

![6.png](https://www.iotsec-zone.com/api/image/v2/20230915/cvj94rsyppan4vzvdo.png)

C->S

![7.png](https://www.iotsec-zone.com/api/image/v2/20230915/cvj94wvnshvvgulti2.png)

S->C

![8.png](https://www.iotsec-zone.com/api/image/v2/20230915/cvj94yk3ejwgdw25y4.png)

#### PLAY

C->S

![9.png](https://www.iotsec-zone.com/api/image/v2/20230915/cvj94ulukme9qtyudb.png)

S->C

![10.png](https://www.iotsec-zone.com/api/image/v2/20230915/cvj950pfi20i2duj0h.png)

#### 接下来服务端通过RTP协议往客户端发送视频流了

![11.png](https://www.iotsec-zone.com/api/image/v2/20230915/cvj953306zgx1dk98y.png)

#### GET_PARAMETER

![12.png](https://www.iotsec-zone.com/api/image/v2/20230915/cvj954xli8it81z0zx.png)

![13.png](https://www.iotsec-zone.com/api/image/v2/20230915/cvj9571bu7yr30bu7v.png)

#### TEARDOWN

![14.png](https://www.iotsec-zone.com/api/image/v2/20230915/cvj959i9t8oazqnssi.png)

![15.png](https://www.iotsec-zone.com/api/image/v2/20230915/cvj95b3cejxl4rcrd1.png)

### RTSP认证
这里介绍一下需要认证登录的RTSP

![16.png](https://www.iotsec-zone.com/api/image/v2/20230915/cvj95en58bgm8lzgja.png)

![17.png](https://www.iotsec-zone.com/api/image/v2/20230915/cvj95hyrwvhe7exlme.png)

![18.png](https://www.iotsec-zone.com/api/image/v2/20230915/cvj95jk675p8wpsjli.png)

这里我们可以看见，我们首先发送DESCRIBE请求，然后服务端返回401未认证，提示客户端需要密码验证，包中携带了realm和nonce参数。客户端输入账号密码后，客户端再次发送一个DESCRIBE请求，携带了username和response信息。而response包含密码信息，他的计算方式是` response=md5(md5(username:realm:password):nonce:md5(public_method:url)); ` 认证成功后服务端返回SDP。

### shodan搜索设备
我们去shodan搜索引擎上使用 ` port:554 has_screenshot:true ` 搜索

![19.png](https://www.iotsec-zone.com/api/image/v2/20230915/cvj95mnv57nfzplhkw.png)
然后打开VLC视频工具

![20.png](https://www.iotsec-zone.com/api/image/v2/20230915/cvj95odgtxy5lepplh.png)
打开网络串流

![21.png](https://www.iotsec-zone.com/api/image/v2/20230915/cvj95pzgqey6es0hrj.png)
输入shodan搜到的ip和端口
然后点击播放（可能会有一些不能播放，需要多试几次）

![22.png](https://www.iotsec-zone.com/api/image/v2/20230915/cvj98x8skv3nau8zgx.png)
