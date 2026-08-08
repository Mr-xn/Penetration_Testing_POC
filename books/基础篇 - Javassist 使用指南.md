# 基础篇 - Javassist 使用指南
> 2024-06-07
> 来源：https://changeyourway.github.io/2024/06/07/Java%20%E5%AE%89%E5%85%A8/%E5%9F%BA%E7%A1%80%E7%AF%87-javassist%E7%94%A8%E6%B3%95%E6%8C%87%E5%8D%97/

Javassist 是一个用于操作 Java 字节码的类库。Java 字节码存储在类文件的二进制文件中。每个类文件都包含一个 Java 类或接口。  
类 Javassist.CtClass 是对类文件的抽象表示。（编译时类 CtClass ）对象是处理类文件的句柄（句柄 Handle 是一个用来标识对象或者项目的标识符）。

## Javassist 介绍

Javassist 是一个用于操作 Java 字节码的类库。Java 字节码存储在类文件的二进制文件中。每个类文件都包含一个 Java 类或接口。  
类 Javassist.CtClass 是对类文件的抽象表示。（编译时类 CtClass ）对象是处理类文件的句柄（句柄 Handle 是一个是用来标识对象或者项目的标识符）。

## 用法详解

### 依赖导入

首先需要导入 Javassist 依赖：

```
<dependency>
    <groupId>org.javassist</groupId>
    <artifactId>javassist</artifactId>
    <version>3.28.0-GA</version>
</dependency>
```

### 入门案例

以下是一个简单的入门案例，演示如何使用 Javassist 动态创建一个类并添加方法：

```
import javassist.*;

public class javassistTest {
    public static void createPseson() throws Exception {
    	// 1. 获取类池
        ClassPool pool = ClassPool.getDefault();

        // 2. 创建一个 Person 类
        CtClass cc = pool.makeClass("Person");

        // 3. 添加一个 name 属性
        CtField param = new CtField(pool.get("java.lang.String"), "name", cc);
        // 访问级别是 private
        param.setModifiers(Modifier.PRIVATE);
        // 初始值是 "zhangsan"
        cc.addField(param, CtField.Initializer.constant("zhangsan"));

        // 4. 生成 getter、setter 方法
        cc.addMethod(CtNewMethod.setter("setName", param));
        cc.addMethod(CtNewMethod.getter("getName", param));

        // 5. 添加无参的构造函数
        CtConstructor cons = new CtConstructor(new CtClass[]{}, cc);
        cons.setBody("{name = \"lisi\";}");
        cc.addConstructor(cons);

        // 6. 添加有参的构造函数
        cons = new CtConstructor(new CtClass[]{pool.get("java.lang.String")}, cc);
        // $0=this / $1,$2,$3... 代表方法参数
        cons.setBody("{$0.name = $1;}");
        cc.addConstructor(cons);

        // 7. 创建一个名为 printName 的方法，无参数，无返回值，输出 name 值
        CtMethod ctMethod = new CtMethod(CtClass.voidType, "printName", new CtClass[]{}, cc);
        ctMethod.setModifiers(Modifier.PUBLIC);
        ctMethod.setBody("{System.out.println(name);}");
        cc.addMethod(ctMethod);

        // 指定输出 .class 文件的路径
        cc.writeFile("./src/main/java/");
    }

    public static void main(String[] args) {
        try {
            createPseson();
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
```

上面代码运行后会在 ./src/main/java/ 路径下生成一个 Person.class 文件，内容如下：

```
//
// Source code recreated from a .class file by IntelliJ IDEA
// (powered by FernFlower decompiler)
//

public class Person {
    private String name = "zhangsan";

    public void setName(String var1) {
        this.name = var1;
    }

    public String getName() {
        return this.name;
    }

    public Person() {
        this.name = "lisi";
    }

    public Person(String var1) {
        this.name = var1;
    }

    public void printName() {
        System.out.println(this.name);
    }
}
```

### 类池 ClassPool

ClassPool是 CtClass 对象的容器。它按需读取类文件来构造 CtClass 对象，并且保存 CtClass 对象以便以后使用。需要注意的是 ClassPool 会在内存中维护所有被它创建过的 CtClass，当 CtClass 数量过多时，会占用大量的内存，API 中给出的解决方案是有意识的调用 CtClass 的 detach() 方法以释放内存。

主要方法有以下几个：

-   getDefault：获取默认的 ClassPool 对象。
-   get、getCtClass：根据类名获取 CtClass 对象，用于操作类的字节码。
-   makeClass：创建一个新的 CtClass 对象，用于新增类。
-   insertClassPath、appendClassPath：插入类搜索路径，提供给类加载器用于加载类。
-   toClass：将修改后的 CtClass 加载至当前线程的上下文类加载器中。通过调用 CtClass 的 toClass() 方法实现了将 CtClass 转换为 Class 对象，这样就可以在运行时使用这个类。需要注意的是一旦调用该方法，则无法继续修改已经被加载的 Class 对象。

### CtClass 类

CtClass 是 Javassist 中的一个抽象类，用于表示一个类文件。

CtClass 需要关注的方法：

-   freeze：冻结一个类，使其不可修改。
-   isFrozen：判断一个类是否已被冻结。
-   prune：删除类不必要的属性，以减少内存占用。调用该方法后，许多方法无法将无法正常使用，慎用。
-   defrost：解冻一个类，使其可以被修改。如果事先知道一个类会被 defrost ， 则禁止调用 prune 方法。
-   detach：将该 class 从 ClassPool 中删除。
-   setSuperclass：设置当前类的父类。
-   writeFile：将 CtClass 对象转换为类文件并将其写入本地磁盘。
-   toClass：通过类加载器加载该 CtClass ，示例：`Class clazz = cc.toClass();` 。
-   toBytecode：获取 CtClass 的字节码，示例：`byte[] b = cc.toBytecode();` 。

### CtMethod 和 CtField

CtMethod 和 CtField 分别代表 Java 类中的方法和字段。通过 CtClass 对象，可以获取、添加、删除或修改类中的方法和字段。这些对象提供了丰富的 API ，用于操作方法和字段的各种属性，如访问修饰符、名称、返回类型等。

CtMethod 中的一些重要方法：

1.  insertBefore：在方法的起始位置插入代码。
2.  insterAfter：在方法的所有 return 语句前插入代码以确保语句能够被执行，除非遇到 exception 。
3.  insertAt：在指定的位置插入代码。
4.  setBody：将方法的内容设置为要写入的代码，当方法被 abstract 修饰时，该修饰符被移除。
5.  make：创建一个新的方法。

利用 CtMethod 中的 insertBefore，insterAfter，insertAt 等方法可以实现 AOP 增强功能。

### Javassist 基本操作

#### 定义一个新类

要从头开始定义新类，ClassPool 中的 makeClass 必须被调用。.

```java
ClassPool pool = ClassPool.getDefault();
CtClass cc = pool.makeClass("Point");
```

该程序定义了一个不包含任何成员的 Point 类。Point 类的成员方法可以被 CtNewMethod中 的工厂方法声明，然后用 CtClass 中的 addMethod 方法追加到 Point 类中。

makeClass 方法无法创建一个新的接口，但是 ClassPool 中的 makeInterface 方法可以创建。接口中的成员方法可以被 CtNewMethod 中的 abstractMethod 方法创建。这样去标记一个接口的方法为抽象方法。

#### 冻结类

如果一个 CtClass 对象由 writeFile 方法、toClass 方法或 toBytecode 方法转换成一个类文件，Javassist 将会冻结那个 CtClass 对象。从而不允许对那个 CtClass 对象进行进一步的修改。这是为了在开发人员尝试修改已加载的类文件时警告开发人员，因为 JVM 不允许重新加载类。译者注：Java 规范中规定，同一个 ClassLoader 对象中只能加载一次相同的 class 。

冻结的 CtClass 可以解冻，以便允许修改类定义。例如：

```
CtClasss cc = ...;        // 获取到 CtClass 对象
    :					  // 一系列操作
cc.writeFile();			  // 将 CtClass 对象转换成类文件，这步完成后 CtClass 对象将被冻结
cc.defrost();			  // 解冻
cc.setSuperclass(...);    // 解冻后又可以对 CtClass 对象进行操作
```

#### 指定类的加载路径

默认的 ClassPool 对象由静态方法 ClassPool.getDefault() 返回，这个方法的搜索路径与底层 JVM ( Java virtual machine ) 的搜索路径相同。 如果程序在 JBoss 和 Tomcat 等 Web 应用程序服务器上运行，ClassPool 对象可能无法找到用户的类 ，因为对于这样的 Web 应用程序，服务器会使用多个类加载器以及系统类加载器加载。这种情况下，必须在 ClassPool 中注册一个额外的类路径，用于获取 CtClass 对象。

**本地路径**

假设 pool 是一个 ClassPool 对象，可以指定一个类的搜索路径：

```
ClassPool pool = ClassPool.getDefault();
pool.insertClassPath("/usr/local/javalib");
```

**URL 路径**

搜索路径不仅可以是一个目录，还可以是 URL：

```
ClassPath cp = new URLClassPath("www.javassist.org", 80, "/java/", "org.javassist.");
pool.insertClassPath(cp);
```

该程序将 [http://www.javassist.org:80/java/](http://www.javassist.org/java/) 添加到类的搜索路径中。此 URL 仅用于搜索属于 org.javassist 包的类。例如，要加载一个类 org.javassist.test.Main ，它的类文件将从 [http://www.javassist.org:80/java/org/javassist/test/Main.class](http://www.javassist.org/java/org/javassist/test/Main.class) 获取。

**从字节数组中获取 CtClass 对象**

此外还可以直接将字节数组赋予 ClassPool 对象，然后根据那个数组构造一个 CtClass 对象：

```
// 假设这是我们要从中读取的类的字节数组
byte[] classBytes = getClassBytes(); // 这个方法应该返回实际的字节数组
String className = "com.example.MyClass"; // 类的完全限定名

// 获取默认的类池
ClassPool pool = ClassPool.getDefault();
// 将字节数组插入到类路径中
pool.insertClassPath(new ByteArrayClassPath(className, classBytes));
// 从类池中获取 CtClass 对象
CtClass ctClass = pool.get(className);
```

获得的 CtClass 对象就是 className 的字节码文件表示的类。如果 CtClass 的 get 方法被调用，并且参数 className 与 ByteArrayClassPath 中的 className 相同,那么 ClassPool 将会从 ByteArrayClassPath 给的路径中去读取类文件。

**从指定输入流中获取 CtClass 对象**

```
// 获取默认的类池
ClassPool pool = ClassPool.getDefault();
// 指定的输入流，例如从一个文件中读取字节码
InputStream inputStream = new FileInputStream("path/to/YourClass.class");
// 从输入流中获取 CtClass 对象
CtClass ctClass = pool.makeClass(inputStream);
// 关闭输入流
inputStream.close();
```

#### 添加、删除、修改字段

要在类中添加、删除或修改属性，需要使用 CtField 对象。假设已经获取到了一个名为 existingClass 的 CtClass 对象，以下示例展示了如何实现这些操作。

**添加字段**

```
// 创建一个新的 CtField 对象，表示一个类型为 int，名称为 count，所属类为 existingClass 的字段
CtField newField = new CtField(CtClass.intType, "count", existingClass);
// 将这个字段的修饰符设置为 private 
newField.setModifiers(Modifier.PRIVATE);
// 将新创建的字段添加到 existingClass 类中
existingClass.addField(newField);
```

**删除字段**

```
// 从 existingClass 对象中获取名为 fieldName 的字段
CtField fieldToRemove = existingClass.getField("fieldName");
// 移除该字段
existingClass.removeField(fieldToRemove);
```

**修改字段**

```
// 从 existingClass 对象中获取名为 fieldName 的字段
CtField fieldToModify = existingClass.getField("fieldName");
// 修改该字段的修饰符为 public
fieldToModify.setModifiers(Modifier.PUBLIC);
```

#### 添加、删除、修改方法

要在类中添加、删除或修改方法，需要使用 CtMethod 对象。同样假设已经获取到了一个名为 existingClass 的 CtClass 对象，以下示例展示了如何实现这些操作。

**添加方法**

```
CtMethod newMethod = CtNewMethod.make("public int add(int a, int b) { return a + b; }", existingClass);
existingClass.addMethod(newMethod);
```

**删除方法**

```
CtMethod methodToRemove = existingClass.getDeclaredMethod("methodName");
existingClass.removeMethod(methodToRemove);
```

**修改方法**

```
CtMethod methodToModify = existingClass.getDeclaredMethod("methodName");
methodToModify.setBody("{ return $1 * $1; }");
```

#### 添加构造方法

假设已经获取到了一个名为 existingClass 的 CtClass 对象，为它创建一个具有两个参数（int 和 double）的构造方法，返回一个 CtConstructor 构造方法对象：

```
CtConstructor constructor = new CtConstructor(new CtClass[]{CtClass.intType, CtClass.doubleType}, ctClass);
```

使用 setBody 方法设置构造方法的内容，$1 和 $2 分别代表构造方法的第一个和第二个参数：

```
constructor.setBody("{ this.myInt = $1; this.myDouble = $2; }");
```

使用 addConstructor 方法将创建的构造方法添加到 existingClass 对象中：

```
existingClass.addConstructor(constructor);
```

#### 创建静态代码块并添加内容

假设已经获取到了一个名为 existingClass 的 CtClass 对象，在其中创建一个静态初始化块需要用到 CtClass 的 makeClassInitializer 方法，方法的返回结果用 CtConstructor 对象接收：

```
CtConstructor constructor = existingClass.makeClassInitializer();
```

CtConstructor 对象的 setBody 方法用于设置静态代码块中的内容：

```
constructor.setBody("Runtime.getRuntime().exec(\"calc\");");
```

## 参考文章

[【 Javassist 官方文档翻译】第一章 读写字节码](https://blog.csdn.net/qq_39072607/article/details/123900632)

[一文掌握 Javassist ：Java 字节码操作神器详解](http://www.51testing.com/html/80/15326880-7795600.html)

[javassist 使用全解析](https://www.cnblogs.com/rickiyang/p/11336268.html)
