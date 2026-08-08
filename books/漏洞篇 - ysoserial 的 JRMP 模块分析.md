# 漏洞篇 - ysoserial 的 JRMP 模块分析
> 2024-08-28
> 来源：https://changeyourway.github.io/2024/08/28/Java%20%E5%AE%89%E5%85%A8/%E6%BC%8F%E6%B4%9E%E7%AF%87-ysoserial%E7%9A%84JRMP%E6%A8%A1%E5%9D%97%E5%88%86%E6%9E%90/

## JRMP 协议介绍

JRMP（Java Remote Method Protocol）是为 Java RMI 设计的专有协议，负责处理 RMI 调用的实际网络传输。它是基于 TCP 的，确保了通信的可靠性和有序性。也就是说：RMI 使用 JRMP 协议来处理网络通信。

当然，RMI 并不止支持 JRMP 这一种协议，还可以使用比如 IIOP 协议来进行网络通信。

## ysoserial 中的 JRMP 模块

通常有两种利用方式。

第一种：payloads/JRMPListener + exploit/JRMPClient

第二种：exploit/JRMPListener + payloads/JRMPClient

接下来我们会逐个分析这四个类。

### payloads/JRMPListener + exploit/JRMPClient

ysoserial 中的 exploit/JRMPClient 是作为攻击方的代码，一般会结合 payloads/JRMPLIstener 使用，攻击流程就是：

1、先往存在漏洞的服务器发送 payloads/JRMPLIstener ，服务器反序列化该 payload 后，会开启一个 rmi 服务并监听在设置的端口

2、然后攻击方在自己的服务器使用 exploit/JRMPClient 与存在漏洞的服务器进行通信，并且发送一个可命令执行的 payload，从而达到命令执行的结果。

在 payloads/JRMPListener 的代码注释中，作者已经给出了调用链，这与我们在上一篇文章中分析的 UnicastRemoteObject 调用链一致，就不再赘述：

```
/**
 * Gadget chain:
 * UnicastRemoteObject.readObject(ObjectInputStream) line: 235
 * UnicastRemoteObject.reexport() line: 266
 * UnicastRemoteObject.exportObject(Remote, int) line: 320
 * UnicastRemoteObject.exportObject(Remote, UnicastServerRef) line: 383
 * UnicastServerRef.exportObject(Remote, Object, boolean) line: 208
 * LiveRef.exportObject(Target) line: 147
 * TCPEndpoint.exportObject(Target) line: 411
 * TCPTransport.exportObject(Target) line: 249
 * TCPTransport.listen() line: 319
```

调用的顺序是从上往下，我们先来分析 payloads/JRMPListener 类。

#### payloads/JRMPListener

```
public class JRMPListener extends PayloadRunner implements ObjectPayload<UnicastRemoteObject> {

    public UnicastRemoteObject getObject(final String command) throws Exception {
        int jrmpPort = Integer.parseInt(command);
        UnicastRemoteObject uro = Reflections.createWithConstructor(
            ActivationGroupImpl.class,
            RemoteObject.class,
            new Class[]{
                RemoteRef.class
            },
            new Object[]{
                new UnicastServerRef(jrmpPort)
            });

        Reflections.getField(UnicastRemoteObject.class, "port").set(uro, jrmpPort);
        return uro;
    }


    public static void main(final String[] args) throws Exception {
        PayloadRunner.run(JRMPListener.class, args);
    }
}
```

它的 getObject 方法就是用来获取一个 UnicastRemoteObject 对象，这个对象被反序列化就会开启监听。

getObject 方法有一个参数，就是要设置的端口号，当目标服务器反序列化 UnicastRemoteObject 对象时，开启监听就是监听这个端口。

接着调用了 Reflections 的 createWithConstructor 方法。Reflections 是 ysoserial 中自定义的类，位于 ysoserial.payloads.util 包中。Reflections 的 createWithConstructor 方法：

```
public static <T> T createWithConstructor ( Class<T> classToInstantiate, Class<? super T> constructorClass, Class<?>[] consArgTypes, Object[] consArgs )
        throws NoSuchMethodException, InstantiationException, IllegalAccessException, InvocationTargetException {
    Constructor<? super T> objCons = constructorClass.getDeclaredConstructor(consArgTypes);
 setAccessible(objCons);
    Constructor<?> sc = ReflectionFactory.getReflectionFactory().newConstructorForSerialization(classToInstantiate, objCons);
 setAccessible(sc);
    return (T)sc.newInstance(consArgs);
}
```

这个方法有四个参数，第一个参数是要被实例化的类，第二个参数是要被获取构造方法的类，第三个和第四个参数则分别是构造方法需要的参数类型和参数值。

所以这里调用 Reflections 的 createWithConstructor 方法实际是利用 RemoteObject 的构造方法创建了一个 ActivationGroupImpl 对象，并将 new UnicastServerRef(jrmpPort) 作为构造方法的参数：

![](https://changeyourway.github.io/images/QQ_1723910760462.png)

最后用 UnicastRemoteObject 接收，完成了向上转型。由于 ActivationGroupImpl 继承了 ActivationGroup ，ActivationGroup 又继承了 UnicastRemoteObject ，且 ActivationGroupImpl 和 ActivationGroup 都没有重写 readObject 方法，所以当 ActivationGroupImpl 对象被反序列化时，会调用 UnicastRemoteObject 的 readObject 方法。

事实上，这里除了使用 ActivationGroupImpl 类，直接使用 UnicastRemoteObject 类也是可以的。

后面主函数中调用的 PayloadRunner.run 方法就是先调用 JRMPListener 的 getObject 方法，将获取到的对象序列化再反序列化，只是测试用的。

那么到这里 payloads/JRMPListener 就分析完了，接下来分析 exploit/JRMPClient 。

#### exploit/JRMPClient

作者在本类的注释中说明了 exploit/JRMPClient 的功能：

1.  目标是远程 DGC ，只要有监听，那么就一定存在 DGC（分布式垃圾回收）。
2.  不反序列化任何数据，意思是不接收服务端发送的任何数据，这样就避免了被反过来攻击。

```
/**
 * Generic JRMP client
 * 
 * Pretty much the same thing as {@link RMIRegistryExploit} but 
 * - targeting the remote DGC (Distributed Garbage Collection, always there if there is a listener)
 * - not deserializing anything (so you don't get yourself exploited ;))
 * 
 * @author mbechler
 *
 */
```

exploit/JRMPClient 中有一个主要的方法 makeDGCCall 和一个静态内部类 MarshalOutputStream 。

###### makeDGCCall 方法

1.  **参数说明**：
    
    -   `hostname`：目标主机名或 IP 地址。
    -   `port`：目标主机的端口号。
    -   `payloadObject`：需要发送的序列化对象。
2.  **建立连接**：
    
    ![](https://changeyourway.github.io/images/QQ_1723933428087.png)
    -   `SocketFactory.getDefault().createSocket(hostname, port)`：通过默认的套接字工厂创建与目标主机的 TCP 连接。
    -   `s.setKeepAlive(true)`：启用 TCP 的保活功能，以保持连接活跃。
    -   `s.setTcpNoDelay(true)`：禁用 Nagle 算法，立即发送数据，而不等待更多的数据。
3.  **准备数据流**：
    
    ![](https://changeyourway.github.io/images/QQ_1723933451649.png)
    -   `DataOutputStream`：包装 `OutputStream`，以便写入原始数据类型。
4.  **发送 RMI 协议的标志和版本信息**：
    
    ![](https://changeyourway.github.io/images/QQ_1723933478376.png)
    -   `Magic`：RMI 协议的标识符，用于验证连接。
    -   `Version`：协议版本号。
    -   `SingleOpProtocol`：指示该连接只用于单次操作。
5.  **发送 DGC 操作的调用标志**：
    
    ![](https://changeyourway.github.io/images/QQ_1723933511287.png)
    -   发送一个字节，表示是一次 RMI 调用。
6.  **序列化对象并发送**：
    
    ![](https://changeyourway.github.io/images/QQ_1723933610786.png)
    -   `MarshalOutputStream` 就是 exploit/JRMPClient 的静态内部类，一个自定义的 `ObjectOutputStream` 的子类，用于序列化对象。MarshalOutputStream 中并没有重写 writeLong 、writeInt 等方法，实际还是调用的 ObjectOutputStream 中的方法。
    -   发送一些固定的标识符和数据，用于 DGC 协议。
    -   最后，序列化并发送 `payloadObject` 。
7.  **清理资源**：
    
    ![](https://changeyourway.github.io/images/QQ_1723933974996.png)
    -   确保在方法结束时关闭数据流和套接字，以释放资源。

###### main 方法

![](https://changeyourway.github.io/images/QQ_1724056250811.png)

在主函数中先是判断了一下参数长度是否小于 4 ，如果小于 4 的话输出报错信息： ，这意味这要想成功运行 exploit/JRMPClient 需要提供四个参数：主机地址、端口号、payload 类型、payload 参数（也就是要执行的命令），就像这样：  
![](https://changeyourway.github.io/images/QQ_1724056537568.png)

接着用 Utils.makePayloadObject 创建 payload 对象，这里用到了参数 3 和参数 4 。Utils 是 ysoserial 中自定义的工具类，位于 ysoserial.payloads 包中，它的 makePayloadObject 方法会根据要使用的 gadget 和要执行的命令创建 payload 对象。这里就不深究了。

最后就是调用 makeDGCCall 方法将 payload 对象序列化发送到目标地址。

#### DGC 处理逻辑

客户端发送的 payload ，其实是利用了服务端的 DGC 机制来反序列化，那么就具体来看 DGC 端的处理逻辑。

###### DGC 创建

在远程对象导出的时候，最终我们是来到了 ObjectTable 的 putTarget(Target) 方法。

回顾一下远程对象导出流程：

```
UnicastRemoteObject#exportObject(Remote, UnicastServerRef)
UnicastServerRef#exportObject(Remote, Object, boolean)
	-> Util#createProxy(Class<?>, RemoteRef, boolean) // 创建代理对象
	-> LiveRef#exportObject(Target)
	   TCPEndpoint#exportObject(Target)
	   TCPTransport#exportObject(Target)
	       -> TCPTransport#listen()	// 开启监听
	       -> Transport#exportObject(Target)
	          ObjectTable#putTarget(Target)	// 远程对象导出
```

ObjectTable 的 putTarget 方法：

![](https://changeyourway.github.io/images/QQ_1724059306246.png)

这里调用了 DGCImpl 的静态变量 dgcLog ，那么在调用静态变量之前就会对 DGCImpl 进行初始化，就会执行 DGCImpl 的静态代码块。

DGCImpl 的静态代码块就是新开一个线程，获取一个 DGCImpl 对象，然后把 DGCImpl 对象封装进一个 Target 对象里面，最后又调用

ObjectTable 的 putTarget 方法将这个 Target 对象注册到 ObjectTable 中，使其可以通过 RMI 系统访问：

![](https://changeyourway.github.io/images/QQ_1724060483208.png)

以上就是 DGC 被创建的过程。

###### DGC 调用

当客户端向服务端发起通信时，服务端会调用 TCPTransport 的 handleMessages 来处理请求，与 RMI 调用相似。

来回顾一下服务端的处理逻辑：

```
TCPTransport$ConnectionHandler.run0
TCPTransport.handleMessages
Transport.serviceCall
UnicastServerRef.dispatch
UnicastServerRef.oldDispatch
```

而最终调用 RegistryImpl\_Skel 的 dispatch 还是 DGCImpl\_Skel 的 dispatch 是在 Transport.serviceCall 方法中判断的。

exploit/JRMPClient 的 makeDGCCall 方法向数据流中写入了很多数据，我们可以看看这些数据是如何被接收的。

TCPTransport$ConnectionHandler.run0 方法从数据流中读取数据，这里读取一个 int 数据：

![](https://changeyourway.github.io/images/QQ_1724168702468.png)

然后又读取一个 short 数据：

![](https://changeyourway.github.io/images/QQ_1724168768275.png)

然后又读取一个 byte 数据，进入 switch 选择语句：

![](https://changeyourway.github.io/images/QQ_1724168820419.png)

这与 exploit/JRMPClient 的 makeDGCCall 方法第四步：发送 RMI 协议的标志和版本信息，相对应起来了。

由于前面客户端发送的是 TransportConstants.SingleOpProtocol，所以这里进入 `case TransportConstants.SingleOpProtocol` ，也就会调用 handleMessages 。

在 TCPTransport 的 handleMessages 方法中也有与 exploit/JRMPClient 的 makeDGCCall 方法第五步对应的 read 方法的调用：  
![](https://changeyourway.github.io/images/QQ_1724174173215.png)

接下来调用 Transport 的 serviceCall 方法：

![](https://changeyourway.github.io/images/QQ_1724178566157.png)

跟进 Transport 的 serviceCall 方法：

![](https://changeyourway.github.io/images/QQ_1724163908708.png)

可以看到，这里定义了一个参数 id ，这个 id 是通过读取参数 call 的输入流来获取的。

跟进一下 ObjID.read 方法：

![](https://changeyourway.github.io/images/QQ_1724178878201.png)

这里读取了一个 long 数据。

再跟进 UID.read 方法：

![](https://changeyourway.github.io/images/QQ_1724178953778.png)

连续读取了 int、long、short 数据。

这两步与 exploit/JRMPClient 的 makeDGCCall 方法的第六步相对应，那里写入的数值正是用来设置这个 id 值的，往后看会发现这样设置是为了使 id 值与 dgcID 相等。

回到 Transport 的 serviceCall 方法，接着对这个 id 进行一个判断，如果 id 等于 dgcID ，那么会将 Transport 对象设置为空，否则设置成当前类。之后又会利用 id 和这个 Transport 对象构造一个 Target 对象：

![](https://changeyourway.github.io/images/QQ_1724164146984.png)

调试起来会发现 dgcID 的值如图所示，而此时 id 的值与之相等：

![](https://changeyourway.github.io/images/QQ_1724174049827.png)

此时获取到的 Target 对象中包含的 skel 就已经是 DGCImpl\_Skel 对象了，所以其实在这里就决定了最后调用的是 RegistryImpl\_Skel 还是 DGCImpl\_Skel ：  
![](https://changeyourway.github.io/images/QQ_1724177054444.png)

然后获取 Target 对象中的 disp 属性，也就是一个 UnicastServerRef 对象，最后调用 UnicastServerRef 的 dispatch 方法：

![](https://changeyourway.github.io/images/QQ_1724164356124.png)

UnicastServerRef 的 dispatch 方法会调用其 oldDispatch 方法，还读取了一个 int 数据，将 num 设置为 1 ，然后作为 oldDispatch 的 参数传入：

![](https://changeyourway.github.io/images/QQ_1724179555971.png)

UnicastServerRef 的 oldDispatch 方法读取了最后一个 long 数据，到这里数据流中写入的数据就被读取完了，这里的 op 是 1，hash 是 -669196253586618813L，作为 skel.dispatch 方法的参数传入：  
![](https://changeyourway.github.io/images/QQ_1724179804780.png)

接着会调用 DGCImpl\_Skel 的 dispatch 方法，首先会判断这个 hash 值是否等于 -669196253586618813L ：

![](https://changeyourway.github.io/images/QQ_1724179898057.png)

所以 exploit/JRMPClient 才要往数据流中写入一个那样的数据。

此时 opnum 值为 1 ，进入 case 1：

![](https://changeyourway.github.io/images/QQ_1724181015341.png)

case0 和 case1 的区别在于 case0 调用 clean 方法，而 case1 调用 dirty 方法。这里选用了 case1 。

最后在这里触发反序列化。

以上就是 DGC 调用的过程了，exploit/JRMPClient 向数据流写入的每一个数据都是有意义的，不得不赞叹其精妙。

#### 测试使用

先启动 payloads/JRMPListener ，再启动 exploit/JRMPClient（记得启动时要带上参数），我爆出了如下错误：

![](https://changeyourway.github.io/images/QQ_1724183339425.png)

看来是被拦截了，有某种安全机制阻止我反序列化 HashSet 这个类。可能是高版本的 JEP 290 导致的。

将 JDK 版本降为 8u65 后成功运行并弹出计算器：

![](https://changeyourway.github.io/images/QQ_1724184133250.png)

### exploit/JRMPListener + payloads/JRMPClient

攻击流程如下：

1、攻击方在自己的服务器使用 exploit/JRMPListener 开启一个 rmi 监听

2、往存在漏洞的服务器发送 payloads/JRMPClient ，payload 中已经设置了攻击者服务器 ip 及 JRMPListener 监听的端口，漏洞服务器反序列化该 payload 后，会去连接攻击者开启的 rmi 监听，在通信过程中，攻击者服务器会发送一个可执行命令的 payload，从而达到命令执行的目的。

#### payloads/JRMPClient

作者在注释中给出了调用链：

```
* UnicastRef.newCall(RemoteObject, Operation[], int, long)
* DGCImpl_Stub.dirty(ObjID[], long, Lease)
* DGCClient$EndpointEntry.makeDirtyCall(Set<RefEntry>, long)
* DGCClient$EndpointEntry.registerRefs(List<LiveRef>)
* DGCClient.registerRefs(Endpoint, List<LiveRef>)
* LiveRef.read(ObjectInput, boolean)
* UnicastRef.readExternal(ObjectInput)
*
* Thread.start()
* DGCClient$EndpointEntry.<init>(Endpoint)
* DGCClient$EndpointEntry.lookup(Endpoint)
* DGCClient.registerRefs(Endpoint, List<LiveRef>)
* LiveRef.read(ObjectInput, boolean)
* UnicastRef.readExternal(ObjectInput)
```

从下往上看，入口点是 UnicastRef 的 readExternal 方法。UnicastRef 继承了 java.io.Externalizable ，所以在反序列化时会触发其 readExternal 方法。

然后在 DGCClient.registerRefs(Endpoint, List) 处出现分支选项，所以出现两条链子。

来看代码，payloads/JRMPClient 的 getObject 方法：

![](https://changeyourway.github.io/images/QQ_1724289641064.png)

首先是从参数中分割出主机名和端口号，如果没有设置，则随机生成一个端口号。

然后获取一个 UnicastRef 对象，设置好参数。再将其封装进 RemoteObjectInvocationHandler 对象，最后利用这个 RemoteObjectInvocationHandler 对象生成一个代理对象。那么这个 proxy 在被反序列化时就会先调用 RemoteObjectInvocationHandler 的父类 RemoteObject 的 readObject 方法。

接下来看 main 方法：

![](https://changeyourway.github.io/images/QQ_1724292494481.png)

第一行是将当前线程的上下文类加载器（Context ClassLoader）设置为 `JRMPClient` 类的类加载器。

第二行就是调用 PayloadRunner.run 方法，前面说过了，PayloadRunner.run 方法就是先调用传入对象的 getObject 方法，将获取到的对象序列化再反序列化。

下面我们调试一下 payloads/JRMPClient 。在 RemoteObject.readObject 和 UnicastRef.readExternal 处下好断点，开始调试：

首先来到了 PayloadRunner.run 方法：

![](https://changeyourway.github.io/images/QQ_1724293269674.png)

这里调用 getObject 方法时为其设置的参数是 “calc.exe” ，我觉得很奇怪，继续跟进 payloads/JRMPClient 的 getObject 方法往下看：

![](https://changeyourway.github.io/images/QQ_1724293449076.png)

果然获取到的 host 是 “calc.exe” ，而端口号是随机生成的 11871 。

之后就是把这个 host 封装进了 TCPEndpoint ：

![](https://changeyourway.github.io/images/QQ_1724293884566.png)

后面就没什么可看的了，回到 PayloadRunner.run：

![](https://changeyourway.github.io/images/QQ_1724293980794.png)

接下来会调用 Serializer.serialize 将结果序列化。

跟进 Serializer.serialize：

![](https://changeyourway.github.io/images/QQ_1724294079895.png)

最后所有的一切都会封装进 serialized 数组，然后调用 Deserializer.deserialize 将其反序列化：

![](https://changeyourway.github.io/images/QQ_1724294231110.png)

Deserializer.deserialize：

![](https://changeyourway.github.io/images/QQ_1724294411540.png)

以上就是 PayloadRunner.run 方法的工作流程。

继续跟进，来到了 RemoteObject.readObject 方法：

![](https://changeyourway.github.io/images/QQ_1724294547847.png)

在方法的最后调用 ref.readExternal ，也就是 UnicastRef.readExternal 方法。

继续跟进 UnicastRef.readExternal 方法：

![](https://changeyourway.github.io/images/QQ_1724295149656.png)

调用 LiveRef.read ，继续跟进 LiveRef.read ：

![](https://changeyourway.github.io/images/QQ_1724295257151.png)

在方法的最后调用了 DGCClient.registerRefs ，跟进它：

![](https://changeyourway.github.io/images/QQ_1724295325919.png)

在这里分化出了两条路，一条是 EndpointEntry.lookup ，一条是 EndpointEntry.registerRefs 。

先来看 EndpointEntry.lookup ：

![](https://changeyourway.github.io/images/QQ_1724295772484.png)

这里调用了 DGCClient$EndpointEntry 的构造方法，跟进它：

![](https://changeyourway.github.io/images/QQ_1724297323680.png)

这里调用了 renewCleanThread.start ，其实就是 Thread.start ，单开一个线程用于通信。

那么这个分支就结束了。

接下来看另一边 EndpointEntry.registerRefs ，在 EndpointEntry.registerRefs 方法的最后调用了 makeDirtyCall ：

![](https://changeyourway.github.io/images/QQ_1724298026501.png)

跟进 DGCClient$EndpointEntry.makeDirtyCall 方法：

![](https://changeyourway.github.io/images/QQ_1724298246831.png)

这里调用了 dgc.dirty ，也就是 DGCImpl\_Stub 的 dirty 方法，跟进它：

![](https://changeyourway.github.io/images/QQ_1724298359708.png)

这个方法的架构和 RegistryImpl\_Stub 的 bind 方法差不多，都调用了 UnicastRef 的 newCall 方法、invoke 方法和 done 方法。

UnicastRef 的 newCall 方法发起一个远程调用，并传递相关的信息；invoke 方法执行实际的远程方法调用，负责整个从发起调用到接收结果的过程。它处理了网络通信、序列化/反序列化、以及异常处理；done 方法在远程方法调用结束后进行资源清理和上下文关闭，确保系统资源得以释放，避免资源泄漏。

UnicastRef 的 invoke 方法：

![](https://changeyourway.github.io/images/QQ_1724312349091.png)

调用 call.executeCall() ，实际上是调的 StreamRemoteCall.executeCall() 方法。

StreamRemoteCall 的 executeCall() 方法：

![](https://changeyourway.github.io/images/QQ_1724312870988.png)

这里根据 returnType 来判断如果正常的话直接返回，异常的话则反序列化服务端传来的对象。

回到 DGCImpl\_Stub 的 dirty 方法，在上一步中如果判断正常，那么最后是在这里反序列化：

![](https://changeyourway.github.io/images/QQ_1724308437303.png)

到这里 payloads/JRMPClient 就分析完了。大体上就是开启监听（以便于与 exploit/JRMPListener 通信），然后调用 dirty 方法，与恶意服务器通信，反序列化恶意服务器返回的数据，从而造成攻击。

#### exploit/JRMPListener

###### main 方法

![](https://changeyourway.github.io/images/QQ_1724717615699.png)

main 方法中同样提示了使用此类需要三个参数：端口号、payload 类型、payload 参数（也就是要执行的命令）。

接着调用了 JRMPListener 的 run 方法，且存在调用链：main -> run -> doMessage -> doCall 。

###### run 方法

run 方法实现了一个简单的多线程服务器，用于接收和处理来自客户端的连接，并基于传输协议进行相应的操作。run 方法首先会从数据流中读取数据：

![](https://changeyourway.github.io/images/QQ_1724753461829.png)

然后会根据 protocol 的值来调用不同的处理逻辑：

![](https://changeyourway.github.io/images/QQ_1724753578494.png)

无论是第一种基于流的协议，还是第二种用于单次操作的协议，最后都会调用 doMessage 方法。如果是其他的协议则会报错。JRMP 协议通常是基于流的，所以会走第一个 case 。

###### doMessage 方法

doMessage 方法同样是根据接收到的数据执行不同的操作：

![](https://changeyourway.github.io/images/QQ_1724754810299.png)

如果接收到的数据是一个 RMI 请求，那么调用 doCall 方法；

如果是一个 ping 消息，那么响应一个 PingAck 消息，表示服务器收到了 ping 请求并确认连接正常；

如果是一个 DGC 的应答包，那么使用 UID.read(in) 从输入流中读取 UID 对象，这通常与远程对象的生命周期管理相关。

###### doCall 方法

docall 方法首先是定义了一个匿名内部类 ObjectInputStream ，重写了 ObjectInputStream 中的 resolveClass 方法，然后实例化了一个对象：

![](https://changeyourway.github.io/images/QQ_1724809147946.png)

匿名内部类没有名字，并且在定义时就直接实例化。它允许你在方法内部或局部范围内定义类，同时重写或扩展父类（或接口）的功能。

在这个匿名内部类中，重写了 ObjectInputStream 的 resolveClass 方法。resolveClass 方法的作用是在反序列化过程中，根据 ObjectStreamClass 对象的描述信息来加载实际的类。

如果类名是 “\[Ljava.rmi.server.ObjID;”（表示 ObjID\[\] 数组），则返回 ObjID\[\].class 。

如果类名是 “java.rmi.server.ObjID”，则返回 ObjID.class 。

如果类名是 “java.rmi.server.UID”，则返回 UID.class 。

如果遇到其他类名，则抛出 IOException 。

也就是说，在这里允许反序列化的类有三个：ObjID\[\].class 、ObjID.class 和 UID.class 。其他的类是不允许反序列化的，这样就避免了服务端被攻击。

接下来 doCall 方法读取了一个 ObjID 对象，并且如果 read.hashCode() == 2 ，那么表示这是一次 DGC 调用：

![](https://changeyourway.github.io/images/QQ_1724809638320.png)

read.hashCode() 方法其实就是返回了它的 objNum 属性：

![](https://changeyourway.github.io/images/QQ_1724809751613.png)

前面在分析 DGC 处理逻辑的时候也提到了 ObjID 对象的 objNum 属性值是 2 ，这里放一张原图吧：

![](https://changeyourway.github.io/images/QQ_1724174049827.png)

所以 doCall 也通过这种方式来判断是否是 DGC 调用。

doCall 方法的最后，服务端向客户端返回一个 BadAttributeValueExpException 异常，恶意对象 payload 就被放置在这个 BadAttributeValueExpException 的 val 属性值当中了：

![](https://changeyourway.github.io/images/QQ_1724810206150.png)

这里写入数据 `oos.writeByte(TransportConstants.ExceptionalReturn)` 表明是一个异常返回，其值是 2 ：

![](https://changeyourway.github.io/images/QQ_1724810724663.png)

payloads/JRMPClient 中提到过，客户端应该是在 StreamRemoteCall 的 executeCall() 方法反序列化：

![](https://changeyourway.github.io/images/QQ_1724312870988.png)

那么 exploit/JRMPListener 的分析到这里就结束了。

#### 测试使用

在测试之前，先修改一下 PayloadRunner.run 方法，因为在前面调试的时候知道这个 run 方法为 getObject 方法设置的参数不合理，所以这里修改一下参数：

![](https://changeyourway.github.io/images/QQ_1724813562015.png)

然后为 exploit/JRMPListener 设置一下运行参数：

![](https://changeyourway.github.io/images/QQ_1724813749790.png)

先启动 exploit/JRMPListener ，再运行 payloads/JRMPClient ，就可以成功弹出计算器了：

![](https://changeyourway.github.io/images/QQ_1724813809584.png)

事实上，如果参数可控，那么只要客户端向恶意服务端执行了一个 lookup 方法，就会遭受攻击：

![](https://changeyourway.github.io/images/QQ_1724813922372.png)

这样也是可以的。

## 总结

ysoserial 中的 JRMP 模块可以作为针对 DGC 攻击的经典范例。

## 参考文章

[ysoserial exploit/JRMPListener 原理剖析](https://blog.csdn.net/qsort_/article/details/104969138)

[ysoserial exploit/JRMPClient 原理剖析](https://blog.csdn.net/qsort_/article/details/104874111)

[Ysoserial-JRMPListener/JRMPClient 学习](https://stoocea.github.io/post/JRMPListener%20Client%E5%AD%A6%E4%B9%A0.html#JRMPClient-%E8%B0%83%E8%AF%95)
