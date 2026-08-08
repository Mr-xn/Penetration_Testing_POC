# 基础篇 - Java Agent 详解
> 2024-10-23
> 来源：https://changeyourway.github.io/2024/10/23/Java%20%E5%AE%89%E5%85%A8/%E5%9F%BA%E7%A1%80%E7%AF%87-JavaAgent%E8%AF%A6%E8%A7%A3/

## Java Agent 介绍

Java Agent 是一种允许开发者在 JVM 运行时通过修改类的字节码来动态增强 Java 应用程序的工具。它基于 `Instrumentation` 接口，可以使用 `ClassFileTransformer` 来拦截和修改字节码。在 Java Agent 中，`Instrumentation.addTransformer()` 可以用来添加一个字节码转换器，它将在类加载时对字节码进行操作。

我们平时接触到的很多地方都用到了这个 Java Agent ：

-   各个 Java IDE 的调试功能，例如 eclipse、IntelliJ IDEA；
-   热部署功能，例如 JRebel、XRebel、 spring-loaded；
-   各种线上诊断工具，例如 Btrace、Greys，还有阿里的 Arthas；
-   各种性能分析工具，例如 Visual VM、JConsole 等；

Java Agent 最终以 jar 包的形式存在，我们也只能以调用 jar 包的方式去调用它。

## Java Agent 快速入门

接下来就来实现一个简单的 Java Agent，基于 Java 1.8，主要实现两点简单的功能：

　　1、打印当前加载的所有类的名称；

　　2、监控一个特定的方法，在方法中动态插入简单的代码并获取方法返回值；

在方法中插入代码用到了字节码修改技术，字节码修改技术主要有 javassist、ASM。这个例子中用的是 javassist，所以需要引入相关的 依赖：

```
<dependency>
    <groupId>org.javassist</groupId>
    <artifactId>javassist</artifactId>
    <version>3.28.0-GA</version>
</dependency>
```

### 编写入口类和自定义转换器

入口类需要实现 premain 和 agentmain 两个方法。这两个方法的运行时机不一样。这要从 Java Agent 的使用方式来说了，Java Agent 有两种启动方式，一种是以 JVM 启动参数 -javaagent:xxx.jar 的形式随着 JVM 一起启动，这种情况下，会调用 premain 方法，并且是在主进程的 main 方法之前执行。另外一种是以 loadAgent 方法动态 attach 到目标 JVM 上，这种情况下，会执行 agentmain 方法。

代码实现如下：

```
package com.miaoji;

import java.lang.instrument.Instrumentation;

public class MyCustomAgent {
    /**
     * jvm 参数形式启动，运行此方法
     *
     * @param agentArgs
     * @param inst
     */
    public static void premain(String agentArgs, Instrumentation inst) {
        System.out.println("premain");
        customLogic(inst);
    }

    /**
     * 动态 attach 方式启动，运行此方法
     *
     * @param agentArgs
     * @param inst
     */
    public static void agentmain(String agentArgs, Instrumentation inst) {
        System.out.println("agentmain");
        customLogic(inst);
    }

    /**
     * 打印所有已加载的类名称
     * 修改字节码
     *
     * @param inst
     */
    private static void customLogic(Instrumentation inst) {
        inst.addTransformer(new MyTransformer(), true);
        Class[] classes = inst.getAllLoadedClasses();
        for (Class cls : classes) {
            System.out.println(cls.getName());
        }
    }
}
```

可以看到 premain 和 agentmain 两个方法都有参数 agentArgs 和 inst，其中 agentArgs 是我们启动 Java Agent 时带进来的参数，比如 `-javaagent:xxx.jar [agentArgs]` 。而参数 Instrumentation inst 是 Java 开放出来的专门用于字节码修改和程序监控的实现。我们要实现的打印已加载类和修改字节码也就是基于它来实现的。其中 inst.getAllLoadedClasses()一个方法就实现了获取所有已加载类的功能。

这里 inst.addTransformer() 方法是用来添加字节码转换器的，其中传入了一个自定义的转换器 MyTransformer 对象。

MyTransformer 类的定义如下：

```
package com.miaoji;

import javassist.ClassPool;
import javassist.CtClass;
import javassist.CtMethod;

import java.io.ByteArrayInputStream;
import java.lang.instrument.ClassFileTransformer;
import java.lang.instrument.IllegalClassFormatException;
import java.security.ProtectionDomain;

public class MyTransformer implements ClassFileTransformer {
    @Override
    public byte[] transform(ClassLoader loader, String className, Class<?> classBeingRedefined, ProtectionDomain protectionDomain, byte[] classfileBuffer) throws IllegalClassFormatException {
        System.out.println("正在加载类：" + className);
        if (!"com/miaoji/Person".equals(className)) {
            return classfileBuffer;
        }
        CtClass cl = null;
        try {
            ClassPool classPool = ClassPool.getDefault();
            cl = classPool.makeClass(new ByteArrayInputStream(classfileBuffer));
            CtMethod ctMethod = cl.getDeclaredMethod("test");
            System.out.println("获取方法名称：" + ctMethod.getName());
            ctMethod.insertBefore("System.out.println(\" 动态插入的打印语句 \");");
            ctMethod.insertAfter("System.out.println($_);");
            byte[] transformed = cl.toBytecode();
            return transformed;
        } catch (Exception e) {
            e.printStackTrace();
        }
        return classfileBuffer;
    }
}
```

以上代码的逻辑就是当碰到加载的类是 Person 的时候，在其中的 test 方法开始时插入一条打印语句，打印内容是”动态插入的打印语句”，在 test 方法结尾处，打印返回值，其中 $\_ 就是返回值，这是 javassist 里特定的标示符。

### 编写 MANIFEST.MF 配置文件

在目录 resources/META-INF/ 下创建文件名为 MANIFEST.MF 的文件，在其中加入如下的配置内容：

```
Manifest-Version: 1.0
Created-By: miaoji
Agent-Class: com.miaoji.MyCustomAgent
Can-Redefine-Classes: true
Can-Retransform-Classes: true
Premain-Class: com.miaoji.MyCustomAgent
```

### 设置打包方式

Java Agent 是以 jar 包的形式存在，所以最后一步就是将上面的内容打到一个 jar 包里。

在 pom 文件中加入以下配置：

```
<build>
        <plugins>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-assembly-plugin</artifactId>
                <configuration>
                    <archive>
                        <manifestFile>C:\Users\miaoj\Documents\Java安全代码实验\JavaAgentTest\src\main\resources\META-INF\MANIFEST.MF</manifestFile>
                    </archive>
                    <descriptorRefs>
                        <descriptorRef>jar-with-dependencies</descriptorRef>
                    </descriptorRefs>
                </configuration>
            </plugin>
        </plugins>
    </build>
```

用 manifestFile 标签指定 MANIFEST.MF 所在路径，指定打包方式为包含依赖的 jar 包：jar-with-dependencies 。

然后运行如下命令即可打包：

```
mvn assembly:assembly
```

![](https://changeyourway.github.io/images/image-20241023165440755.png)

打包成功后会在 target 目录下生成对应的 jar 包。

### 编写测试类

我们先编写一个测试类，这个测试类的逻辑就是循环不断地读取键盘输入，并在输入数字 1 的时候，调用 person.test() 方法：

```
import java.util.Scanner;

public class RunJvm {
    public static void main(String[] args){
        System.out.println("按数字键 1 调用测试方法");
        while (true) {
            Scanner reader = new Scanner(System.in);
            int number = reader.nextInt();
            if(number==1){
                Person person = new Person();
                person.test();
            }
        }
    }
}
```

以及定义一个 Person 类：

```
public class Person {
    public String test(){
        System.out.println("执行测试方法");
        return "I'm ok";
    }
}
```

### 命令行方式运行

```
java -javaagent:"C:\Users\miaoj\Documents\Java安全代码实验\JavaAgentTest\target\JavaAgentTest-1.0-SNAPSHOT-jar-with-dependencies.jar" -cp target/classes com.miaoji.RunJvm
```

输出结果：

![](https://changeyourway.github.io/images/image-20241023165652335.png) ![](https://changeyourway.github.io/images/image-20241023165704437.png)

可以看到在最开始首先执行了 premain 方法打印了 “premain” ，中间输出了很多被加载的类，在 RunJvm main 方法的前后执行了自定义转换器 MyTransformer 中的 javassist 操作。

### 动态 attach 方式运行

这是另一种运行方式，在项目运行过程中运行 Java Agent ，这会触发 agentmain 方法。

用下面的代码去实现：

```
package com.miaoji;

import com.sun.tools.attach.*;
import java.io.IOException;
import java.util.List;

public class AttachAgent {
    public static void main(String[] args) throws IOException, AttachNotSupportedException, AgentLoadException, AgentInitializationException {
        // 调用 VirtualMachine.list() 获取正在运行的 JVM 列表
        List<VirtualMachineDescriptor> list = VirtualMachine.list();
        for (VirtualMachineDescriptor vmd : list) {

            // 遍历每一个正在运行的 JVM ，如果 JVM 名称为 RunJvm 则连接该 JVM 并加载特定 Agent
            if (vmd.displayName().equals("com.miaoji.RunJvm")) {
                // 连接指定 JVM
                VirtualMachine virtualMachine = VirtualMachine.attach(vmd.id());
                // 加载 Agent
                virtualMachine.loadAgent("C:\\Users\\miaoj\\Documents\\Java安全代码实验\\JavaAgentTest\\target\\JavaAgentTest-1.0-SNAPSHOT-jar-with-dependencies.jar");
                // 断开 JVM 连接
                virtualMachine.detach();
            }

        }
    }
}
```

其中用到的 com.sun.tools.attach.VirtualMachine 类需要 tools.jar 依赖，IDEA 默认不会导入，我们需要手动导入：

![](https://changeyourway.github.io/images/image-20241023173202010.png)

导入完成后，就可以开始了。

先运行 RunJvm 主函数，接着运行 AttachAgent ，回到 RunJvm 运行结果下面输入 1 ，便可以触发相同的效果了：

![](https://changeyourway.github.io/images/image-20241023174735221.png)

### Java Agent 基本使用流程总结

1.  创建 Java Agent 类：
    -   定义一个类，包含 `premain` 方法（静态加载）和/或 `agentmain` 方法（动态加载）。
    -   这些方法是 Java Agent 的入口，用来接收传递的参数和 `Instrumentation` 对象。
2.  实现字节码转换：
    -   使用 `Instrumentation` 接口注册字节码转换器，通过 `ClassFileTransformer` 实现类加载时修改字节码的逻辑。
3.  配置 `MANIFEST.MF` 文件：
    -   在 JAR 包的 `META-INF/` 目录下的 `MANIFEST.MF` 文件中，添加 `Premain-Class`（静态加载）或 `Agent-Class`（动态加载）条目，指明 Java Agent 的入口类。
4.  打包 Java Agent：
    -   将 Java Agent 类及其依赖打包为 JAR 文件，确保 `MANIFEST.MF` 文件配置正确。
5.  加载 Java Agent：
    -   静态加载：在 JVM 启动时，通过 `-javaagent` 参数指定 Java Agent 的 JAR 文件。
    -   动态加载：使用 Attach API，附加到已经运行的 JVM 进程，动态加载 Java Agent。

## Java Agent 知识汇总

### 常用类

#### Instrumentation

java.lang.instrument.Instrumentation 是 Java Agent 的核心接口，允许 Java Agent 操作类定义，修改字节码等。它提供了操作类和监控 JVM 的各种方法。它是 premain 和 agentmain 方法的参数。

-   常用方法：
    -   `void addTransformer(ClassFileTransformer transformer)`：添加一个类文件转换器，在类加载时进行字节码修改。
        
    -   `void redefineClasses(ClassDefinition... definitions)`：允许重新定义（redefine）已经加载的类，直接用新的字节码替换现有类定义，而不会触发类的重新加载。不能改变原类的签名、父类、接口，且字段、方法的结构也必须保持一致，但可以修改方法体的具体实现。
        
    -   `void retransformClasses(Class<?>... classes)`：允许对类进行重新转换，但它会触发类加载器重新加载。同样不能改变类的结构（例如类的签名、字段、接口、父类等），但可以修改方法体的具体实现。
        
    -   `Class[] getAllLoadedClasses()`：获取 JVM 中加载的所有类。
        
    -   `long getObjectSize(Object object)`：获取某个对象的大小。
        
    -   `boolean isModifiableClass(Class<?> theClass)`：检查一个类是否可以修改。
        

#### ClassFileTransformer

java.lang.instrument.ClassFileTransformer 是用于在类加载时转换字节码的接口。通过实现这个接口，Agent 可以在类加载时对字节码进行修改。前面的自定义转换器就继承了这个类并重写了 transform 方法。

-   常用方法：
    -   `byte[] transform(ClassLoader loader, String className, Class<?> classBeingRedefined, ProtectionDomain protectionDomain, byte[] classfileBuffer)`：这个方法在类加载时调用，允许你对类的字节码进行修改，返回修改后的字节码。

#### VirtualMachine

com.sun.tools.attach.VirtualMachine 是 Java Attach API 的核心类，允许 Java Agent 动态附加到正在运行的 JVM 上。

-   常用方法：
    -   `static VirtualMachine attach(String pid)`：根据 JVM 进程 ID，附加到运行中的 JVM。
    -   `void loadAgent(String agentJar)`：加载 Java Agent JAR 文件到已附加的 JVM。
    -   `void detach()`：从目标 JVM 分离。

#### ClassDefinition

java.lang.instrument.ClassDefinition 类用于定义要重新加载的类。

-   常用方法：
    -   `ClassDefinition(Class<?> theClass, byte[] theClassFile)`：构造一个类定义，指定要重新加载的类和它的字节码。

### 常用方法

#### premain 方法

-   这是 Java Agent 在 JVM 启动时的入口方法，类似于 `main` 方法。
    
-   方法签名：
    
    ```
    public static void premain(String agentArgs, Instrumentation inst);
    ```
    
    -   `agentArgs`：传递给 Agent 的参数，可以是命令行参数等。
    -   `inst`：`Instrumentation` 对象，提供修改类字节码、获取类信息等功能。
-   **示例**：
    
    ```
    public static void premain(String agentArgs, Instrumentation inst) {
        inst.addTransformer(new MyTransformer());
    }
    ```
    

#### agentmain 方法

-   用于在 JVM 运行时动态加载 Agent，使用 Attach API 时调用。
    
-   方法签名：
    
    ```
    public static void agentmain(String agentArgs, Instrumentation inst);
    ```
    
    -   类似 `premain`，`agentmain` 方法在 JVM 运行时动态调用，允许你动态加载 Agent。

#### transform 方法

-   这是 `ClassFileTransformer` 接口中的方法，用于修改类字节码。
    
-   方法签名：
    
    ```
    public byte[] transform(ClassLoader loader, String className, Class<?> classBeingRedefined,
                            ProtectionDomain protectionDomain, byte[] classfileBuffer) throws IllegalClassFormatException;
    ```
    
    -   `classfileBuffer`：类的字节码，可以通过修改这个字节数组来改变类的行为。

### 执行流程

Java Agent 的执行流程简要为：

1.  **启动方式**：
    -   静态：JVM 启动时，调用 `premain(String agentArgs, Instrumentation inst)`。
    -   动态：JVM 运行时，调用 `agentmain(String agentArgs, Instrumentation inst)`。
2.  **注册类文件转换器**：
    -   在 `premain` 或 `agentmain` 方法中，使用 `Instrumentation#addTransformer` 注册 `ClassFileTransformer`。
3.  **类文件转换器执行**：
    -   当类加载时，`ClassFileTransformer` 的 `transform` 方法被调用，修改类的字节码。
4.  **已加载类的操作**：
    -   使用 `retransformClasses` 或 `redefineClasses` 修改已加载类的字节码（遵循类的结构限制）。

## 参考文章

[Java Agent 使用详解](https://www.cnblogs.com/huanshilang/p/12206644.html)

[Java 安全学习 —— 内存马](https://goodapple.top/archives/1355)
