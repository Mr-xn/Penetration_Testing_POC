# 基础篇 - RMI 协议详解
> 2024-07-08
> 来源：https://changeyourway.github.io/2024/07/08/Java%20%E5%AE%89%E5%85%A8/%E5%9F%BA%E7%A1%80%E7%AF%87-RMI%E8%BF%9C%E7%A8%8B%E6%96%B9%E6%B3%95%E8%B0%83%E7%94%A8%E5%8D%8F%E8%AE%AE/

RMI 入门案例及源码分析

## RMI 协议介绍

RMI（Remote Method Invocation，远程方法调用）是 Java 编程语言中用于实现分布式计算的一种技术。RMI 允许一个 JVM上的对象调用另一台 JVM 上的对象的方法，就像调用本地对象的方法一样，从而实现跨网络的远程调用。

## RMI 入门案例

先来实现一个最简单的 RMI ：服务器会提供一个 sayHello 服务，这个服务有一个方法名为 function ，它的功能是将输入的字符串返回。

首先我们需要一个接口 SayHelloInterface ，这个接口将会被服务器和客户端共享，Java 的 RMI 规定此接口必须派生自 java.rmi.Remote ，并在每个方法声明抛出 RemoteException ：

```
import java.rmi.Remote;
import java.rmi.RemoteException;

public interface SayHelloInterface extends Remote {
    String function(String input) throws RemoteException;
}
```

服务器需要编写一个接口的实现类 SayHelloImpl ，这个实现类需要实现方法功能：

```
import java.rmi.RemoteException;

public class SayHelloImpl implements SayHelloInterface{
    @Override
    public String function(String input) throws RemoteException {
        return input;
    }
}
```

最后，服务端注册这个 RMI 服务，使其开放在公网上：

```
import java.rmi.RemoteException;
import java.rmi.registry.LocateRegistry;
import java.rmi.registry.Registry;
import java.rmi.server.UnicastRemoteObject;

public class Server {
    public static void main(String[] args) throws RemoteException {
        // 获取服务端代理对象
        SayHelloInterface skeleton = (SayHelloInterface) UnicastRemoteObject.exportObject(new SayHelloImpl(), 0);
        // 创建注册中心，端口为 1099
        Registry registry = LocateRegistry.createRegistry(1099);
        // 将服务端代理对象注册到注册表，服务名为 "SayHello"
        registry.rebind("SayHello", skeleton);
    }
}
```

服务端代码至此就完成了。

接下来是客户端，要想实现远程调用，服务端和客户端需要共享一个接口，所以客户端要将服务端的 SayHelloInterface.java 从服务端复制过来：

```
import java.rmi.Remote;
import java.rmi.RemoteException;

public interface SayHelloInterface extends Remote {
    String function(String input) throws RemoteException;
}
```

最后在客户端实现 RMI 调用：

```
import java.rmi.NotBoundException;
import java.rmi.RemoteException;
import java.rmi.registry.LocateRegistry;
import java.rmi.registry.Registry;

public class RMIClientTest {
    public static void main(String[] args) throws RemoteException, NotBoundException {
        // 连接到服务器 localhost ，端口 1099 :
        Registry registry = LocateRegistry.getRegistry("localhost", 1099);
        // 查找名称为 "SayHello" 的服务并强制转型为 SayHelloInterface 类型:
        SayHelloInterface sayHello = (SayHelloInterface) registry.lookup("SayHello");
        // 正常调用接口方法:
        String output = sayHello.function("Hello, RMI");
        // 打印输出结果
        System.out.println(output);
    }
}
```

先运行服务器，再运行客户端。运行结果是在客户端控制台上输出：” Hello, RMI “ 。

除了上面的这种方式以外，RMI 还有另一种实现方式，即服务器在编写接口的实现类时，让这个实现类继承 java.rmi.server.UnicastRemoteObject 类，同时必须为这个实现类提供一个构造函数并且抛出 RemoteException 。那么 SayHelloImpl 实现类可以这样改：

```
import java.rmi.RemoteException;
import java.rmi.server.UnicastRemoteObject;

public class SayHelloImpl extends UnicastRemoteObject implements SayHelloInterface  {
    protected SayHelloImpl() throws RemoteException {
    }

    @Override
    public String function(String input) throws RemoteException {
        return input;
    }
}
```

此时在服务端只需要新建 SayHelloImpl 对象就会自动调用 UnicastRemoteObject 的 exportObject 方法，而不需要再手动调用，服务端 Server 类改成这样：

```
import java.rmi.RemoteException;
import java.rmi.registry.LocateRegistry;
import java.rmi.registry.Registry;

public class Server {
    public static void main(String[] args) throws RemoteException {
        // 获取服务端代理对象
        SayHelloInterface skeleton = new SayHelloImpl();
        // 将 RMI 服务注册到 1099 端口
        Registry registry = LocateRegistry.createRegistry(1099);
        // 将服务端代理对象注册到注册表，服务名为 "SayHello"
        registry.rebind("SayHello", skeleton);
    }
}
```

同样是可以正常运行的。

客户端只有接口，并没有实现类，客户端获得的接口方法返回值实际上是通过网络从服务器端获取的。因为 RMI 服务的默认端口是 1099 ，所以上面的实验也使用 1099 端口。

Java 的 RMI 严重依赖序列化和反序列化，而这种情况下可能会造成严重的安全漏洞，因为 Java 的序列化和反序列化不但涉及到数据，还涉及到二进制的字节码，即使使用白名单机制也很难保证 100% 排除恶意构造的字节码。因此，使用 RMI 时，双方必须是内网互相信任的机器，不要把 1099 端口暴露在公网上作为对外服务。

此外，Java 的 RMI 调用机制决定了双方必须是 Java 程序，其他语言很难调用 Java 的 RMI 。如果要使用不同语言进行 RPC 调用，可以选择更通用的协议，例如 [gRPC](https://grpc.io/) 。

## RMI 原理解析

RMI 交互图（来自网图）：

![](https://changeyourway.github.io/images/image-20240611090617906.png)

为了屏蔽网络通信的复杂性，RMI 引入了两个概念，分别是 Stubs（客户端存根） 以及 Skeletons（服务端骨架），当客户端（Client）试图调用一个在远端的 Object 时，实际调用的是客户端本地的一个代理类（Proxy），这个代理类就称为 Stub，而在调用远端（Server）的目标类之前，也会经过一个对应的远端代理类，就是 Skeleton，它从 Stub 中接收远程方法调用并传递给真实的目标类。Stubs 以及 Skeletons 的调用对于 RMI 服务的使用者来讲是隐藏的，我们无需主动的去调用相关的方法。但实际的客户端和服务端的网络通信是通过 Stub 和 Skeleton 来实现的。

## RMI 动态类加载

如果客户端在调用时，传递了一个可序列化对象，这个对象在服务端不存在，则在服务端会抛出 ClassNotFound 的异常，但是 RMI 支持动态类加载，如果设置了 `java.rmi.server.codebase`，则会尝试从其中的地址获取 `.class` 并加载及反序列化。

### 什么是 codebase

codebase 是用于指定 Java RMI（远程方法调用）应用程序中类的字节码位置的属性。这个属性告诉 RMI 服务器和客户端在哪里可以找到所需的类文件。设置 codebase 有助于确保客户端能够动态加载服务器上不存在的类。

### 如何开启 RMI 动态类加载

###### 一、设置 codebase

有两种办法：

1.  在代码中使用 System.setProperty 方法可以动态设置 codebase ：

```
System.setProperty("java.rmi.server.codebase", "http://127.0.0.1:9999/");
```

2.  用命令行启动 Java 程序，设置 -Djava.rmi.server.codebase 参数：

```
java -Djava.rmi.server.codebase="http://127.0.0.1:9999/" RMIServer
```

###### 二、配置安全策略文件

例如，policyfile.txt ：

```
grant {
    permission java.security.AllPermission;
};
```

这个策略文件授予了所有权限，这是最宽松的配置。

###### 三、启动时指定安全策略文件

需要设置 java.security.policy ，同样可以用代码和命令行两种方式。

1.  在代码中使用 System.setProperty 方法可以动态设置 policy：

```
System.setProperty("java.security.policy", RemoteServer.class.getClassLoader().getResource("policyfile.txt").toString());
```

2.  用命令行启动 Java 程序，设置 -Djava.security.policy 参数：

```
java -Djava.security.policy=policyfile.txt -Djava.rmi.server.codebase="http://127.0.0.1:9999/" RemoteServer
```

## RMI 源码分析

本次实验 JDK 版本为 8u71 。

### 远程对象导出 - UnicastRemoteObject#exportObject

如果服务端的实现类继承了 UnicastRemoteObject ，那么在实例化获取服务端代理对象的时候，会调用 UnicastRemoteObject 的构造方法，无参构造调用有参构造，最终会调用 UnicastRemoteObject 的 exportObject 方法：

![](https://changeyourway.github.io/images/image-20240612110437282.png)

如果服务端的实现类没有继承 UnicastRemoteObject ，则需要手动调用 UnicastRemoteObject 的 exportObject 方法。那么这个 exportObject 方法到底实现了什么功能呢？

跟进 exportObject 方法：

![](https://changeyourway.github.io/images/image-20240612111357495.png)

跟进后发现它又调用了另一个 exportObject 方法，继续跟进：

![](https://changeyourway.github.io/images/image-20240612111453130.png)

这里调用了 sref 的 exportObject 方法，sref 是一个 UnicastServerRef 对象。

继续跟进 UnicastServerRef 的 exportObject 方法：

![](https://changeyourway.github.io/images/image-20240612111906524.png)

这其中使用 sun.rmi.server.Util#createProxy() 方法创建了一个代理对象，且最终返回的就是这个代理对象。

继续跟进 Util 的 createProxy() 方法：

![](https://changeyourway.github.io/images/image-20240612112048849.png)

可以看到，这里用 RemoteObjectInvocationHandler 创建了一个代理对象。

接下来回到 exportObject 方法：

![](https://changeyourway.github.io/images/image-20240612160346393.png)

然后会新建一个 Target 对象，这个 Target 对象中封装了返回的代理对象 var5 。之后调用 this.ref 的 exportObject 方法，并将这个 Target 对象传入。

this.ref 是一个 LiveRef 对象，我们跟进它的 exportObject 方法：

![](https://changeyourway.github.io/images/image-20240612161232621.png)

这里又调用 this.ep 的 exportObject 方法，当程序运行起来时，会发现 this.ep 实际上是一个 TCPEndpoint 对象：

![](https://changeyourway.github.io/images/image-20240612161839874.png)

于是跟进 TCPEndpoint 的 exportObject 方法：

![](https://changeyourway.github.io/images/image-20240612161958983.png)

发现它又调用 TCPTransport 的 exportObject 方法。

继续跟进 TCPTransport 的 exportObject 方法：

![](https://changeyourway.github.io/images/image-20240612162513179.png)

TCPTransport 的 exportObject 方法其实干了两件事，一是调用它自己的 listen() 方法开启监听，二是调用它父类 Transport 的 exportObject 方法。

TCPTransport 的 listen() 方法：

```
private void listen() throws RemoteException {
    assert Thread.holdsLock(this);

    TCPEndpoint var1 = this.getEndpoint();
    int var2 = var1.getPort();
    if (this.server == null) {
        if (tcpLog.isLoggable(Log.BRIEF)) {
            tcpLog.log(Log.BRIEF, "(port " + var2 + ") create server socket");
        }

        try {
            this.server = var1.newServerSocket();
            Thread var3 = (Thread)AccessController.doPrivileged(new NewThreadAction(new AcceptLoop(this.server), "TCP Accept-" + var2, true));
            var3.start();
        } catch (BindException var4) {
            throw new ExportException("Port already in use: " + var2, var4);
        } catch (IOException var5) {
            throw new ExportException("Listen failed on port: " + var2, var5);
        }
    } else {
        SecurityManager var6 = System.getSecurityManager();
        if (var6 != null) {
            var6.checkListen(var2);
        }
    }

}
```

这个方法实现了一个用于监听 TCP 连接的功能。它首先检查当前线程是否持有对象锁，并获取端点的端口号。如果服务器套接字尚未创建，它会创建一个新的服务器套接字并启动一个新的线程进行接受循环（AcceptLoop），以处理传入连接；如果端口已被占用，则抛出 BindException ，否则抛出 IOException 。如果服务器套接字已经存在，则检查当前安全管理器并验证监听权限。

Transport 的 exportObject 方法：

```
public void exportObject(Target var1) throws RemoteException {
    var1.setExportedTransport(this);
    ObjectTable.putTarget(var1);
}
```

这里调用了两个方法，其中 var1.setExportedTransport 只是做了一个简单的赋值：

```
void setExportedTransport(Transport var1) {
    if (this.exportedTransport == null) {
        this.exportedTransport = var1;
    }

}
```

ObjectTable 的 putTarget 方法则是将一个远程对象（目标对象 Target ）添加到对象表和实现表中，以便进行远程方法调用和垃圾回收管理：

```
static void putTarget(Target var0) throws ExportException {
    ObjectEndpoint var1 = var0.getObjectEndpoint();
    WeakRef var2 = var0.getWeakImpl();
    if (DGCImpl.dgcLog.isLoggable(Log.VERBOSE)) {
        DGCImpl.dgcLog.log(Log.VERBOSE, "add object " + var1);
    }

    synchronized(tableLock) {
        if (var0.getImpl() != null) {
            if (objTable.containsKey(var1)) {
                throw new ExportException("internal error: ObjID already in use");
            }

            if (implTable.containsKey(var2)) {
                throw new ExportException("object already exported");
            }

            objTable.put(var1, var0);
            implTable.put(var2, var0);
            if (!var0.isPermanent()) {
                incrementKeepAliveCount();
            }
        }

    }
}
```

总之，ObjectTable 的 putTarget 方法负责管理远程对象的导出和注册，以支持远程调用，并确保对象不被重复导出或使用相同的对象标识符。

那么总结一下：UnicastRemoteObject 的 exportObject 方法经过一系列调用后最终开启了监听（默认参数是 0 ，表示系统将选择一个空闲的端口来进行监听，而不是指定一个固定的端口），以及将传入的目标对象导出到对象表和实现表，并返回一个代理对象。

#### 调用栈总结

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

### 动态代理创建 - RemoteObjectInvocationHandler#invoke

前面 Util.createProxy() 方法在创建代理对象的时候就用到了 RemoteObjectInvocationHandler 这个类，那么当代理对象的任意方法被调用，RemoteObjectInvocationHandler 的 invoke 方法就会被调用。

RemoteObjectInvocationHandler 的 invoke 方法：

![](https://changeyourway.github.io/images/image-20240612172302872.png)

如果代理对象调用的方法是从 Object 类继承的方法，那么将会调用 invokeObjectMethod 方法；如果方法名是 finalize 且参数数量为 0，并且 allowFinalizeInvocation 标志为 false ，那么返回 null，表示忽略 finalize 方法的调用；对于其他方法，则调用 invokeRemoteMethod 方法来处理。

接着来看 RemoteObjectInvocationHandler 的 invokeRemoteMethod 方法：

```
private Object invokeRemoteMethod(Object proxy,
                                  Method method,
                                  Object[] args)
    throws Exception
{
    try {
        if (!(proxy instanceof Remote)) {
            throw new IllegalArgumentException(
                "proxy not Remote instance");
        }
        // 实际处理逻辑
        return ref.invoke((Remote) proxy, method, args,
                          getMethodHash(method));
    } catch (Exception e) {
        if (!(e instanceof RuntimeException)) {
            Class<?> cl = proxy.getClass();
            try {
                method = cl.getMethod(method.getName(),
                                      method.getParameterTypes());
            } catch (NoSuchMethodException nsme) {
                throw (IllegalArgumentException)
                    new IllegalArgumentException().initCause(nsme);
            }
            Class<?> thrownType = e.getClass();
            for (Class<?> declaredType : method.getExceptionTypes()) {
                if (declaredType.isAssignableFrom(thrownType)) {
                    throw e;
                }
            }
            e = new UnexpectedException("unexpected exception", e);
        }
        throw e;
    }
}
```

实际上就是调用了 ref 的 invoke 方法来处理。ref 在定义中是 RemoteRef 类型，实际调用时调用的是 RemoteRef 的子类 UnicastRef 的 invoke 方法。

UnicastRef 的 invoke 方法：

```
public Object invoke(Remote var1, Method var2, Object[] var3, long var4) throws Exception {
    if (clientRefLog.isLoggable(Log.VERBOSE)) {
        clientRefLog.log(Log.VERBOSE, "method: " + var2);
    }

    if (clientCallLog.isLoggable(Log.VERBOSE)) {
        this.logClientCall(var1, var2);
    }

    Connection var6 = this.ref.getChannel().newConnection();
    StreamRemoteCall var7 = null;
    boolean var8 = true;
    boolean var9 = false;

    Object var13;
    try {
        if (clientRefLog.isLoggable(Log.VERBOSE)) {
            clientRefLog.log(Log.VERBOSE, "opnum = " + var4);
        }

        var7 = new StreamRemoteCall(var6, this.ref.getObjID(), -1, var4);

        Object var11;
        try {
            ObjectOutput var10 = var7.getOutputStream();
            this.marshalCustomCallData(var10);
            var11 = var2.getParameterTypes();

            for(int var12 = 0; var12 < ((Object[])var11).length; ++var12) {
                marshalValue((Class)((Object[])var11)[var12], var3[var12], var10);
            }
        } catch (IOException var41) {
            clientRefLog.log(Log.BRIEF, "IOException marshalling arguments: ", var41);
            throw new MarshalException("error marshalling arguments", var41);
        }

        var7.executeCall();

        try {
            Class var49 = var2.getReturnType();
            if (var49 == Void.TYPE) {
                var11 = null;
                return var11;
            }

            var11 = var7.getInputStream();
            Object var50 = unmarshalValue(var49, (ObjectInput)var11);
            var9 = true;
            clientRefLog.log(Log.BRIEF, "free connection (reuse = true)");
            this.ref.getChannel().free(var6, true);
            var13 = var50;
        } catch (IOException var42) {
            clientRefLog.log(Log.BRIEF, "IOException unmarshalling return: ", var42);
            throw new UnmarshalException("error unmarshalling return", var42);
        } catch (ClassNotFoundException var43) {
            clientRefLog.log(Log.BRIEF, "ClassNotFoundException unmarshalling return: ", var43);
            throw new UnmarshalException("error unmarshalling return", var43);
        } finally {
            try {
                var7.done();
            } catch (IOException var40) {
                var8 = false;
            }

        }
    } catch (RuntimeException var45) {
        if (var7 == null || ((StreamRemoteCall)var7).getServerException() != var45) {
            var8 = false;
        }

        throw var45;
    } catch (RemoteException var46) {
        var8 = false;
        throw var46;
    } catch (Error var47) {
        var8 = false;
        throw var47;
    } finally {
        if (!var9) {
            if (clientRefLog.isLoggable(Log.BRIEF)) {
                clientRefLog.log(Log.BRIEF, "free connection (reuse = " + var8 + ")");
            }

            this.ref.getChannel().free(var6, var8);
        }

    }

    return var13;
}
```

总的来说，UnicastRef 的 invoke 方法实现了一个远程方法调用（RMI）的核心逻辑。

它通过 `this.ref.getChannel().newConnection()` 创建一个新的连接，使用 `StreamRemoteCall` 创建一个新的远程调用对象，将方法参数序列化并发送给远程对象，执行远程方法调用后，根据方法的返回类型反序列化返回值，并返回给调用者。

其中，反序列化在 UnicastRef 的 unmarshalValue 方法中实现：

```
protected static Object unmarshalValue(Class<?> var0, ObjectInput var1) throws IOException, ClassNotFoundException {
    if (var0.isPrimitive()) {
        if (var0 == Integer.TYPE) {
            return var1.readInt();
        } else if (var0 == Boolean.TYPE) {
            return var1.readBoolean();
        } else if (var0 == Byte.TYPE) {
            return var1.readByte();
        } else if (var0 == Character.TYPE) {
            return var1.readChar();
        } else if (var0 == Short.TYPE) {
            return var1.readShort();
        } else if (var0 == Long.TYPE) {
            return var1.readLong();
        } else if (var0 == Float.TYPE) {
            return var1.readFloat();
        } else if (var0 == Double.TYPE) {
            return var1.readDouble();
        } else {
            throw new Error("Unrecognized primitive type: " + var0);
        }
    } else {
        return var1.readObject();
    }
}
```

#### 调用栈总结

```
RemoteObjectInvocationHandler#invoke(Object, Method, Object[])
RemoteObjectInvocationHandler#invokeRemoteMethod(Object, Method, Object[])
UnicastRef#invoke(Remote, Method, Object[], long)
UnicastRef#unmarshalValue(Class<?>, ObjectInput) # 反序列化
```

### 注册中心创建 - LocateRegistry#createRegistry

LocateRegistry 的 createRegistry 方法：

![](https://changeyourway.github.io/images/image-20240613110247306.png)

这里实际是调用 RegistryImpl 的构造方法 new 了一个 RegistryImpl 对象。

RegistryImpl 的构造方法：

![](https://changeyourway.github.io/images/image-20240613110830043.png)

这边新建了一个 LiveRef 对象，将这个 LiveRef 对象作为参数又新建了 UnicastServerRef 对象，最后调用 setup 进行配置。

跟进 RegistryImpl 的 setup 方法：

![](https://changeyourway.github.io/images/image-20240613111357223.png)

这边依旧是调用了 UnicastServerRef 的 exportObject 方法来导出远程对象，只不过这次 export 的是 RegistryImpl 这个对象。

跟进 UnicastServerRef 的 exportObject 方法：

![](https://changeyourway.github.io/images/image-20240614091049086.png)

再进入 Util 的 createProxy 方法：

![](https://changeyourway.github.io/images/image-20240614085655284.png)

这里在创建代理对象之前其实有一个判断：

```
var2 || !ignoreStubClasses && stubClassExists(var3)
```

Java 中 && 运算符的优先级高于 || 运算符，即 && 会先计算，因此这个判断等同于：

```
var2 || (!ignoreStubClasses && stubClassExists(var3))
```

所以大概意思就是如果 stub 存在且不忽视，或者强制使用，那么直接创建 Stub 。

具体来看 Util 的 stubClassExists 方法：

![](https://changeyourway.github.io/images/image-20240614091618479.png)

这里其实就是在判断传入的 var0 是否在本地有一个存根类，即 var0 的名称后面加上 “\_Stub” 的类。梳理整个逻辑，会发现 var0 的值是

getRemoteClass(RegistryImpl.getClass())，最终，var0.getName() 获取到的值是 sun.rmi.registry.RegistryImpl ：

![](https://changeyourway.github.io/images/image-20240614093409294.png)

这里返回 true ，就说明存在 RegistryImpl\_Stub 这个类，搜一下其实也搜得到：

![](https://changeyourway.github.io/images/image-20240614093815544.png) ![](https://changeyourway.github.io/images/image-20240614093836838.png)

RegistryImpl\_Stub 实现了 bind/list/lookup/rebind/unbind 等 Registry 定义的方法，其中用一些序列化方法来实现：

![](https://changeyourway.github.io/images/image-20240614102729976.png)

好的，回到先前的判断 `var2 || !ignoreStubClasses && stubClassExists(var3)` ，这个判断的结果应当为真，并执行 createStub 方法：

![](https://changeyourway.github.io/images/image-20240614103417153.png)

createStub 方法的执行结果其实就是返回了 RegistryImpl\_Stub 对象：

![](https://changeyourway.github.io/images/image-20240614103812744.png)

那么现在 Util.createProxy 分析完了，回到 UnicastServerRef 的 exportObject 方法，接下来将会调用 setSkeleton 方法：

![](https://changeyourway.github.io/images/image-20240614104133467.png)

UnicastServerRef 的 setSkeleton 方法判断如果 withoutSkeletons 不存在这个 key ，则调用 Util.createSkeleton 创建 Skeleton ：

![](https://changeyourway.github.io/images/image-20240614105112083.png)

Util 的 createSkeleton 方法：

![](https://changeyourway.github.io/images/image-20240614105442446.png)

这里的参数 var0 是一个 RegistryImpl 对象，所以 var1 依旧是 getRemoteClass(RegistryImpl.getClass()) ，这个方法最终返回一个 RegistryImpl\_Skel 对象。

RegistryImpl\_Skel 对象方法不多，主要方法是 dispatch ：

![](https://changeyourway.github.io/images/image-20240614111625118.png)

其中主要的逻辑就是根据不同的情况调用不同的方法，比如 rebind/unbind 之类。

#### 调用栈总结

```
LocateRegistry#createRegistry(int)
RegistryImpl#RegistryImpl(int)
RegistryImpl#setup(UnicastServerRef)
UnicastServerRef#exportObject(Remote, Object, boolean)
	-> Util#createProxy(Class<?>, RemoteRef, boolean)
	   Util#createStub(Class<?>, RemoteRef) # 返回 RegistryImpl_Stub 对象
	-> UnicastServerRef#setSkeleton(Remote)
	   Util#createSkeleton(Remote) # 返回 RegistryImpl_Skel 对象
```

### 服务端获取 Registry 代理对象

rebind 或者 bind 都可以，这里用 bind 和 rebind 的区别在于：bind 方法用于将一个远程对象绑定到指定的名称上，如果该名称已经被绑定过，则会抛出 AlreadyBoundException 异常。rebind 方法用于将一个远程对象绑定到指定的名称上。如果该名称已经被绑定过，则会重新绑定，即覆盖旧的绑定，而不会抛出异常。

#### 情况一：Server 和 Registry 在同一端

当 Server 和 Registry 在同一端时，Server 端通过本地调用获取 Registry 对象。此时，Server 端获取到的 Registry 对象是 RegistryImpl 类的实例，这是 RMI 的默认实现类。服务器大多数情况下与注册中心 Registry 在同一端。

这里的 registry 就是 RegistryImpl 对象：

![](https://changeyourway.github.io/images/image-20240628161323912.png)

于是跟进 RegistryImpl 的 rebind 方法：

![](https://changeyourway.github.io/images/image-20240628162405443.png)

这里直接将远程对象放入了 RegistryImpl 内部的 HashTable 集合中。

#### 情况二：Server 和 Registry 在不同端

当 Server 和 Registry 在不同端时，Server 端通过网络获取 Registry 对象。此时，Server 端获取到的 Registry 对象是 RegistryImpl\_Stub 类的实例。这个类是 RMI 生成的代理类，代表远程的注册表对象。

下面给出在此情况下服务器获取 Registry 对象的代码：

```
String registryHost = "remote-registry-host"; // 远程 Registry 主机名或 IP
int registryPort = 1099; // 远程 Registry 端口号

// 在远程 Registry 上绑定服务
Registry registry = LocateRegistry.getRegistry(registryHost, registryPort);
registry.rebind("Hello", obj);
```

可以看到此时获取的是 RegistryImpl\_Stub 对象：

![](https://changeyourway.github.io/images/image-20240628172346590.png)

跟进 RegistryImpl\_Stub 的 rebind 方法：

![](https://changeyourway.github.io/images/image-20240704133850976.png)

调试起来可以看到：这里的 super.ref 是 UnicastRef 对象，接下来会接连调用 UnicastRef 的 newCall 方法、invoke 方法和 done 方法。

UnicastRef 的 newCall 方法返回一个 RemoteCall 对象，用来给 invoke 方法提供参数。

跟进 UnicastRef 的 newCall 方法：

![](https://changeyourway.github.io/images/image-20240704135020575.png)

可以看到，这里的操作是建立通信，然后 new 了一个 StreamRemoteCall 对象并将其返回，且其中还调用了 UnicastRef 的 marshalCustomCallData 方法。

但奇怪的是 marshalCustomCallData 方法并没有进行任何操作：

![](https://changeyourway.github.io/images/image-20240704140246926.png)

接下来看 UnicastRef 的 invoke 方法：

![](https://changeyourway.github.io/images/image-20240704134416503.png)

执行的是 RemoteCall 的实现类 StreamRemoteCall 的 executeCall 方法。

总的来说，就是服务端通过调用 RegistryImpl\_Stub 的 rebind 方法，将参数序列化发送到 Registry 端，来完成将服务接口绑定到注册表的操作。

#### Registry 端处理逻辑

当 Server 和 Registry 在不同端时，在 Registry 端，由 sun.rmi.transport.tcp.TCPTransport#handleMessages 来处理请求，调用 serviceCall 方法处理：

![](https://changeyourway.github.io/images/image-20240705113118978.png)

这里实际调用的是 Transport 的 serviceCall 方法，跟进 Transport 的 serviceCall 方法：

![](https://changeyourway.github.io/images/image-20240705113259512.png)

disp 获取到的是 UnicastServerRef 对象，这里会调用 UnicastServerRef 的 dispatch 方法，跟进 UnicastServerRef 的 dispatch 方法：

![](https://changeyourway.github.io/images/image-20240705113446620.png)

dispatch 方法又调用 UnicastServerRef 自身的 oldDispatch 方法，跟进 UnicastServerRef 的 oldDispatch 方法：

![](https://changeyourway.github.io/images/image-20240705113637011.png)

最终调用 RegistryImpl\_Skel 的 dispatch 方法，来看看 RegistryImpl\_Skel 的 dispatch 方法：

![](https://changeyourway.github.io/images/image-20240705114000367.png)

RegistryImpl\_Skel 的 dispatch 方法根据流中写入的不同的操作类型分发给不同的方法处理，例如 0 代表着 bind 方法，则从流中读取对应的内容，反序列化，然后调用 RegistryImpl 的 bind 方法进行绑定。

我用的是 rebind ，对应的是 3 ：

![](https://changeyourway.github.io/images/image-20240705114905739.png)

以上就是 Registry 端的处理逻辑。

### Client 端服务调用

客户端获取 Registry 对象的方法与服务端远程获取 Registry 的方法一样：

```
Registry registry = LocateRegistry.getRegistry("localhost", 1099);
```

客户端获取到的也是 RegistryImpl\_Stub 对象：

![](https://changeyourway.github.io/images/image-20240708135731555.png)

客户端调用 RegistryImpl\_Stub 的 lookup 方法，跟进 RegistryImpl\_Stub 的 lookup 方法：

![](https://changeyourway.github.io/images/image-20240708140409880.png)

与 rebind 方法相同，调用 UnicastRef 的 newCall、invoke、done 方法建立通信，将参数序列化发送到 Registry 端，再将返回结果反序列化。

同样来关注 Registry 端的处理逻辑，与 Server 端调用 rebind 方法时 Registry 端的处理逻辑相同，最终都是调用 RegistryImpl\_Skel 的 dispatch 方法来处理。

lookup 方法对应的是 RegistryImpl\_Skel 的 dispatch 方法中的 2 号处理逻辑：

![](https://changeyourway.github.io/images/image-20240708141025817.png)

最后客户端通过 lookup 方法获取到服务的代理对象：

![](https://changeyourway.github.io/images/image-20240708141810878.png)

代理对象的任意方法被调用，都会触发 RemoteObjectInvocationHandler 的 invoke 方法。前面分析过了， RemoteObjectInvocationHandler 的 invoke 方法最终其实是调用 RemoteRef 的实现类 UnicastRef 的 invoke 方法。UnicastRef 中保存了服务端的地址和端口信息，这些信息是在服务端导出远程对象时设置的。因此 Client 端直接与 Server 端进行通信。

Server 端由 UnicastServerRef 的 dispatch 方法来处理客户端的请求，然后将结果序列化给 Client 端，Client 端拿到结果反序列化，完成整个调用的过程。

### 总结

这里引用素十八师傅的原图：

![](https://changeyourway.github.io/images/image-20240708141810879.png)

## 参考文章

[RMI](https://javasec.org/javase/RMI/)

[RMI 远程调用](https://www.liaoxuefeng.com/wiki/1252599548343744/1323711850348577)

[RMI 原理浅析以及调用流程](https://blog.csdn.net/Shadow_Light/article/details/105587008)

[素十八 - Java RMI 攻击由浅入深](https://su18.org/post/rmi-attack/)
