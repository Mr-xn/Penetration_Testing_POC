# 基础篇 - Java 的类加载与反射
> 2024-05-10
> 来源：https://changeyourway.github.io/2024/05/10/Java%20%E5%AE%89%E5%85%A8/%E5%9F%BA%E7%A1%80%E7%AF%87-Java%E7%9A%84%E7%B1%BB%E5%8A%A0%E8%BD%BD%E4%B8%8E%E5%8F%8D%E5%B0%84/

本文介绍了 Java 的类加载与反射机制，概括了获得 Class 对象的几种方式，以及总结了反射获取类信息的方法。

## 类加载机制

### 概述

class 文件由类装载器装载后，在 JVM 中将形成一份描述 Class 结构的元信息对象，通过该元信息对象可以获知 Class 的结构信息：如构造函数，属性和方法等，Java 允许用户借由这个 Class 相关的元信息对象间接调用 Class 对象的功能。

虚拟机把描述类的数据从 class 文件加载到内存，并对数据进行校验，转换解析和初始化，最终形成可以被虚拟机直接使用的 Java 类型，这就是虚拟机的类加载机制。

### 类加载器

ClassLoader ：Java 中的一个抽象类，位于 `java.lang` 包中，用于实现类的加载机制。

在 Java 中，有三种主要的类加载器：

1.  **Bootstrap ClassLoader（启动类加载器）：** 这是 Java 虚拟机（JVM）自身的一部分，负责加载 Java 的核心类库，如 `java.lang` 等。它是用本地代码实现的，无法直接在 Java 代码中访问。
2.  **Extension ClassLoader（扩展类加载器）：** 这个类加载器负责加载 Java 的扩展库，位于 `$JAVA_HOME/lib/ext` 目录下的 JAR 文件中的类。它是由 `sun.misc.Launcher$ExtClassLoader` 类实现的。
3.  **System ClassLoader 或 Application ClassLoader（系统类加载器或应用程序类加载器）：** 这个类加载器负责加载应用程序的类路径（Classpath）中指定的类，包括用户自定义的类。它是由 `sun.misc.Launcher$AppClassLoader` 类实现的。

### 类的生命周期

类从被加载到虚拟机内存中开始到卸载出内存为止，它的整个生命周期可以简单概括为 7 个阶段：：加载（Loading）、验证（Verification）、准备（Preparation）、解析（Resolution）、初始化（Initialization）、使用（Using）和卸载（Unloading）。其中，验证、准备和解析这三个阶段可以统称为连接（Linking）。

这 7 个阶段的顺序为：

加载 -> 验证 -> 准备 -> 解析 -> 初始化 -> 使用 -> 卸载

其中，类加载过程包含上述从加载到初始化的五个阶段，即：

加载 -> 验证 -> 准备 -> 解析 -> 初始化

有时候也将验证，准备，解析三个阶段看作一个阶段，叫连接阶段，所以类加载过程又可以描述为：

加载 -> 连接 -> 初始化

### 获得 Class 对象的四种方式

比如现在有一个类 com.newer.test.Student ，获取该类的 class 对象有以下四种方式：

1.  通过类名.class

```abnf
Class c1 = Student.class;
```

2.  通过对象的 getClass() 方法，stu 是 Student 类的对象

```abnf
Class c2 = stu.getClass();
```

3.  通过类加载器获得 class 对象

```abnf
ClassLoader classLoader = ClassLoader.getSystemClassLoader();
Class c3 = classLoader.loadClass("com.newer.test.Student");
```

值得注意的是，通过类加载器获得 class 对象的这段代码只会经过类加载的五个阶段中的前四个阶段，而不会经过初始化阶段。而类中的静态代码块是在类加载过程中的初始化阶段执行的，所以如果想通过这种方式让类中的静态代码块执行，即触发类的初始化，可以补充以下代码：

```
c3.newInstance();
```

4.  通过 Class.forName() 获得 Class 对象

```abnf
Class c4 =  Class.forName("com.newer.test.Student");
```

## 反射机制

### 概述

反射（Reflection） 是 Java 程序开发语言的特征之一，它允许运行中的 Java 程序对自身进行检查，或者说“自审”，并能直接操作程序的内部属性和方法。

### 通过反射调用方法的流程

反射调用一般分为 3 个步骤：

-   得到要调用类的 Class 对象
-   得到要调用的类的方法（Method）
-   方法调用（invoke）

代码示例：

1.  加载 “com.newer.test.Student” 类，并返回对应的 Class 对象：

```
Class cls = Class.forName("com.newer.test.Student");  
```

2.  获取名为 “hi”、参数类型为 int 和 String 的方法，并返回对应的 Method 对象：

```
Method m = cls.getDeclaredMethod("hi",new Class[]{int.class,String.class});  
```

3.  调用之前获取到的方法：

```
m.invoke(cls.newInstance(),18,"zhangsan");
```

invoke() 方法接收两个参数，第一个参数是要调用方法的对象实例，第二个参数是方法的参数列表。

cls.newInstance() 创建了一个 com.newer.test.Student 的实例，然后调用该实例的 “hi” 方法，传递了参数 18 和 “zhangsan”。

### 反射获取类的信息

###### 获取类构造器

-   `Connstructor<T> getConstructor(Class<?>...parameterTypes)`：返回此 Class 对象对应类的带指定形参的 **public** 构造方法
-   `Constructor<?>[] getConstructors()`：返回此 Class 对象对应类的所有 **public** 构造方法
-   `Constructor<T>[] getDeclaredConstructor(Class<?>...parameterTypes)`：返回此 Class 对象对应类的带指定参数的构造方法，所有声明的构造方法均可访问。
-   `Constructor<?>[] getDeclaredConstructors()`：返回此 Class 对象对应类的所有声明的构造方法

###### 获取类成员方法

-   `Method getMethod(String name,Class<?>...parameterTypes)`：返回此 Class 对象对应类的带指定形参的 public 方法
-   `Method[] getMethods()`：返回此 Class 对象对应类的所有 public 方法
-   `Method getDeclaredMethod(string name,Class<?>...parameterTypes)`：返回此 Class 对象对应类的带指定形参的方法
-   `Method[] getDeclaredMethods()`:返回此 Class 对象对应类的全部方法

###### 获取类成员变量

-   `Field getField(String name)`：返回此 Class 对象对应类的指定名称的 public 成员变量
-   `Field[] getFields()`：返回此 Class 对象对应类的所有 public 成员变量
-   `Field getDeclaredField(String name)`：返回此 Class 对象对应类的指定名称的成员变量，与成员变量访问权限无关
-   `Field[] getDeclaredFields()`：返回此 Class 对象对应类的全部成员变量，与成员变量的访问权限无关

###### 获取类注解

-   `<A extends Annotation>A getAnnotation(Class<A>annotationClass)`：尝试获取该 Class 对象对应类上的指定类型的 Annotation ，如果该类型注解不存在，则返回 null
-   `<A extends Annotation>A getDeclaredAnnotation(Class<A>annotationClass)`：这是 Java 8 中新增的，该方法获取直接修饰该 Class 对象对应类的指定类型的 Annotation ，如果不存在，则返回 null
-   `Annotation[] getAnnotations()`：返回修饰该 Class 对象对应类上存在的所有 Annotation ，包括从父类继承而来的注解，但是不能获取到私有方法或字段上的注解
-   `Annotation[] getDeclaredAnnotations()`：返回修饰该 Class 对象对应类上存在的所有 Annotation ，不包括从父类继承的注解，可以获取到私有方法或字段上的注解
-   `<A extends Annotation>A[] getAnnotationByType(Class<A>annotationClass)`：该方法的功能与前面介绍的 getAnnotation() 方法基本相似，但由于 Java8 增加了重复注解功能，因此需要使用该方法获取修饰该类的指定类型的多个 Annotation
-   `<A extends Annotation>A[] getDeclaredAnnotationByType(Class<A>annotationClass)`：该方法的功能与前面介绍的 getDeclaredAnnotations() 方法相似，也是因为 Java8 的重复注解的功能，需要使用该方法获取直接修饰该类的指定类型的多个 Annotation

###### 获取该类内部类

-   `Class<?>[] getDeclaredClasses()`：返回该 Class 队形对应类里包含的全部内部类

###### 获取该类对象所在的外部类

-   `Class<?> getDeclaringClass()`：返回该 Class 对象对应类所在的外部类

###### 获取该类对象对应类所实现的接口

-   `Class<?>[] getInterfaces()`：返回该 Class 对象对应类所实现的全部接口

###### 获取该类对象对应类所继承的父类

-   `Class<? super T> getSuperclass()`：返回该 Class 对象对应类的超类的 Class 对象

###### 获取该类对象对应类的修饰符、所在包、类名等基本信息

-   `int getModifiers()`：返回此类或接口的所有修饰符，修饰符由 public 、protected 、private 、final 、static 、abstract 等对应的常量组成，返回的整数应使用 Modifier 工具类的方法来解码，才可以获取真的修饰符
-   `Package getPackage()`：获取该类的包
-   `String getName()`：以字符串形式返回此 Class 对象所表示的类的简称
