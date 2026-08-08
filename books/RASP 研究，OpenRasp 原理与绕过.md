# RASP 研究，OpenRasp 原理与绕过
> 2025-07-12
> 来源：https://changeyourway.github.io/2025/07/12/Java%20%E5%AE%89%E5%85%A8/RASP%20%E7%A0%94%E7%A9%B6%EF%BC%8COpenRasp%20%E5%8E%9F%E7%90%86%E4%B8%8E%E7%BB%95%E8%BF%87/

## RASP 快速入门

### RASP 生成

前置知识：[基础篇 - Java Agent 详解](https://changeyourway.github.io/2024/10/23/Java%20%E5%AE%89%E5%85%A8/%E5%9F%BA%E7%A1%80%E7%AF%87-JavaAgent%E8%AF%A6%E8%A7%A3/#transform-%E6%96%B9%E6%B3%95)

仿照搭建 Java Agent 示例环境的过程，只需要将 Hook 的类改变为关键漏洞触发的类，即可实现一个简单的 RASP 。

Java 不允许在默认包中定义代理类。因此，建议为您的代理类添加包声明。

下面是我的简单 rasp 代码示例：

**Agent：**

实现了 premain 和 agentmain 两种方法，覆盖了 jvm 启动与 动态 attach 两种方式。

```
package com.miaoji;

import java.lang.instrument.Instrumentation;
import java.lang.instrument.UnmodifiableClassException;

public class MyCustomAgent {
    /**
     * jvm 参数形式启动，运行此方法
     *
     * @param agentArgs
     * @param inst
     */
    public static void premain(String agentArgs, Instrumentation inst) throws UnmodifiableClassException {
        System.out.println("premain");
        customLogic(inst);
    }

    /**
     * 动态 attach 方式启动，运行此方法
     *
     * @param agentArgs
     * @param inst
     */
    public static void agentmain(String agentArgs, Instrumentation inst) throws UnmodifiableClassException {
        System.out.println("agentmain");
        customLogic(inst);
    }

    /**
     * 打印所有已加载的类名称
     * 修改字节码
     *
     * @param inst
     */
    private static void customLogic(Instrumentation inst) throws UnmodifiableClassException {
        inst.addTransformer(new MyTransformer(), true);
        Class[] classes = inst.getAllLoadedClasses();
        for (Class cls : classes) {
            System.out.println(cls.getName());
        }

        boolean retransformClassesSupported = inst.isRetransformClassesSupported();
        System.out.println("isRetransformClassesSupported: " + retransformClassesSupported);
        boolean modifiableClass = inst.isModifiableClass(Runtime.class);
        System.out.println("isModifiableClass: " + modifiableClass);
        // 只有确认可重变形后才调用
        if (retransformClassesSupported && modifiableClass) {
			// 主动重加载以触发 transform
            inst.retransformClasses(java.lang.Runtime.class);
        } else {
            System.out.println("Runtime is NOT modifiable!");
        }

    }
}
```

**Transformer：**

Hook 了 java.lang.Runtime 类，并检查所有 exec 重载方法的参数是否包含 calc 字符串，匹配到则抛出异常。

需要注意的是，在匹配类名的时候，要将全类名的 `.` 换成 `/` ，即 java/lang/Runtime 。这是因为在 JVM 的内部表示中，类名采用斜杠（`/`）分隔。

这种设计主要源于历史原因。JVM 的类文件格式采用了类似 Unix 文件系统的路径结构，其中斜杠用于表示层级关系。由于 Java 类文件最初是直接映射到文件系统结构的，使用斜杠作为分隔符更符合文件路径的表示方式。

```
package com.miaoji;

import javassist.*;
import javassist.bytecode.AccessFlag;

import java.lang.instrument.ClassFileTransformer;
import java.lang.instrument.IllegalClassFormatException;
import java.security.ProtectionDomain;

public class MyTransformer implements ClassFileTransformer {
    @Override
    public byte[] transform(ClassLoader loader, String className, Class<?> classBeingRedefined, ProtectionDomain protectionDomain, byte[] classfileBuffer) throws IllegalClassFormatException {
        System.out.println("正在加载类：" + className);
        if (!"java/lang/Runtime".equals(className)) {
            return classfileBuffer;
        }
        try {

            ClassPool pool = ClassPool.getDefault();
            // bootstrap 类加载器需手动插入 rt.jar 路径
            if (loader == null) {
                pool.appendClassPath(new LoaderClassPath(ClassLoader.getSystemClassLoader()));
            }
            CtClass ctRuntime = pool.get("java.lang.Runtime");

            // 遍历所有 exec 方法重载
            for (CtMethod m : ctRuntime.getDeclaredMethods()) {
                if (m.getName().equals("exec") && (m.getModifiers() & AccessFlag.PUBLIC) != 0) {
                    wrapExec(m);
                }
            }
            byte[] byteCode = ctRuntime.toBytecode();
            ctRuntime.detach();
            System.out.println("[SimpleRaspAgent] java.lang.Runtime patched successfully.");
            return byteCode;

        } catch (Exception e) {
            e.printStackTrace();
        }
        return classfileBuffer;
    }

    /**
     * 给 exec 方法增加简单的安全检查逻辑
     */
    private void wrapExec(CtMethod method) throws CannotCompileException, NotFoundException {
        CtClass[] params = method.getParameterTypes();
        String paramExpr;

        if (params.length == 0) {
            paramExpr = "\"\"";           // 空参数时直接拼入空串
        } else {
            StringBuilder sb = new StringBuilder();
            for (int i = 0; i < params.length; i++) {
                sb.append("$").append(i + 1);
                if (i < params.length - 1) sb.append(" + \", \" + ");
            }
            paramExpr = sb.toString();
        }

        String src =
                "{"
                        + "  String _cmd = \"" + method.getName() + "(\" + " + paramExpr + " + \")\";"  // 始终合法
                        + "  System.out.println(\"[RASP] Attempt to exec: \" + _cmd);"
                        + "  if(_cmd.contains(\"calc\")){"
                        + "      System.out.println(\"[RASP] Blocked dangerous command: \" + _cmd);"
                        + "      throw new RuntimeException(\"Blocked by RASP\");"
                        + "  }"
                        + "}";

        method.insertBefore(src);
    }
}
```

resources\\META-INF\\MANIFEST.MF ：

```
Manifest-Version: 1.0
Created-By: miaoji
Agent-Class: com.miaoji.MyCustomAgent
Can-Redefine-Classes: true
Can-Retransform-Classes: true
Premain-Class: com.miaoji.MyCustomAgent
```

如此，一个简单的 RASP 示例项目就完成了。

但是，如果想用 mvn package 直接打包，建议用 pom.xml 的配置代替 MANIFEST.MF ，在 pom.xml 中添加如下内容：

```
<build>
        <finalName>RASP-Demo</finalName>
        <plugins>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-jar-plugin</artifactId>
                <version>3.1.0</version>
                <configuration>
                    <archive>
                        <!--自动添加META-INF/MANIFEST.MF -->
                        <manifest>
                            <addClasspath>true</addClasspath>
                        </manifest>
                        <manifestEntries>
                            <Premain-Class>com.miaoji.MyCustomAgent</Premain-Class>
                            <Agent-Class>com.miaoji.MyCustomAgent</Agent-Class>
                            <Can-Redefine-Classes>true</Can-Redefine-Classes>
                            <Can-Retransform-Classes>true</Can-Retransform-Classes>
                        </manifestEntries>
                    </archive>
                </configuration>
            </plugin>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-compiler-plugin</artifactId>
                <configuration>
                    <source>7</source>
                    <target>7</target>
                </configuration>
            </plugin>
        </plugins>
    </build>
```

xml 格式，一样的效果。

随后直接 mvn package 打包即可。

‍

### RASP 使用

要在新项目中使打包的 Java RASP Agent 生效，可以通过以下两种主要方式进行集成：

#### 方法一：在启动时通过 `-javaagent` 参数加载

这是最常见且推荐的方式，适用于大多数 Java 应用程序。缺点：需要重启。

在启动目标 Java 应用程序时，使用 `-javaagent` 参数指定 Agent JAR 文件的位置：

```bash
java -javaagent:/path/to/SimpleRaspAgent.jar -jar your-application.jar
```

请确保将 `/path/to/SimpleRaspAgent.jar` 替换为您实际的 Agent JAR 文件路径，将 `your-application.jar` 替换为您的应用程序 JAR 文件路径。

**注意事项：**

-   `-javaagent` 参数必须在 `-jar` 参数之前指定。
-   确保您的 Agent JAR 文件中包含 `MANIFEST.MF` 文件，并正确设置了 `Agent-Class` 和 `Premain-Class` 属性。或者在 pox.xml 中正确添加了这些标签。
-   如果您的 Agent 使用了 `agentmain` 方法进行动态加载，确保目标 JVM 支持动态附加（如 HotSpot JVM）。

idea 中也可以直接在运行配置中添加虚拟机选项（VM options）：

![](https://changeyourway.github.io/images/image-20250708173927-vijkl2m.png)

如果没有 虚拟机选项（VM options），点击右边修改选项（Modify options），选择添加虚拟机选项（Add VM options）：

![](https://changeyourway.github.io/images/image-20250708174103-gcdx7p9.png)

下面是测试代码与运行结果：

```
package com.miaoji;

import java.io.IOException;

public class runtimeTest {
    public static void main(String[] args) throws IOException {
        Runtime.getRuntime().exec("ipconfig & calc");
    }
}
```

![](https://changeyourway.github.io/images/image-20250708214650-ot71y0v.png)

#### 方法二：动态附加 Agent（无需重启 JVM）

如果您无法在启动时使用 `-javaagent` 参数，或者需要在运行时动态加载 Agent，可以使用 Java Attach API。

用下面的代码去实现：

```java
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
            if (vmd.displayName().equals("com.miaoji.runtimeTest")) {
                // 连接指定 JVM
                VirtualMachine virtualMachine = VirtualMachine.attach(vmd.id());
                // 加载 Agent
                virtualMachine.loadAgent("C:\\Users\\miaoj\\Documents\\Java安全代码实验\\RaspDemo\\target\\RASP-Demo.jar");
                // 断开 JVM 连接
                virtualMachine.detach();
            }

        }
    }
}
```

首先我们要获取 JVM 进程的 pid ，有多种方式，这里用全类名来查找（一般来说 vmd.displayName() 包含类名或 jar 名）。你也可以在要被 attach 的项目中用 ProcessHandle.current().pid() 来让目标程序在启动日志里打印自己的 pid ，但那样需要修改项目代码。

Windows 上，Attach API 的 `id()` 与任务管理器看到的 PID **是一致的**。

其中用到的 com.sun.tools.attach.VirtualMachine 类需要 tools.jar 依赖，IDEA 默认不会导入，我们需要手动导入：

![](https://changeyourway.github.io/images/network-asset-image-20241023173202010-20250708212736-vteva4q.png)

只要你能获取到 pid ，你可以在任何地方运行上述代码来动态 attach 。

测试代码：

```
package com.miaoji;

import java.io.IOException;
import java.util.Scanner;

public class runtimeTest {
    public static void main(String[] args) throws IOException {
        System.out.print("attach 完成后输入 unlock 解锁：");
        Scanner in = new Scanner(System.in);
        while (!"unlock".equalsIgnoreCase(in.nextLine().trim())) {
            continue;
        }
        Runtime.getRuntime().exec("ipconfig & calc");
    }
}
```

先运行测试代码，再运行 attach 代码，最后输入 unlock：

![](https://changeyourway.github.io/images/image-20250708215448-jareduh.png)

以上，我们用 Javassist 实现了一个简单的 RASP 示例，Hook 了 java.lang.Runtime 的 exec 方法，并拦截了 calc 字符串。这种示例仅展示 Rasp 的简单原理，如果想要绕过，还是很简单的，比如用 @ 占位：

```
cmd /c "set x=c@lc & echo %x:@=a% | cmd"
```

![](https://changeyourway.github.io/images/image-20250709091431-j6qdst5.png)

那拦截办法，加更多的黑名单？或者有没有办法从更底层拦截呢？显然，实际情况下的 RASP 会比这个更复杂。

‍

## OpenRasp

由**百度 OAESE** **智能终端安全生态联盟**开源的一款 RASP ，作为我们了解市面上真正应用的 RASP 的窗口。

下载链接：[https://github.com/baidu/openrasp](https://github.com/baidu/openrasp)

### rasp

刚来不太了解目录结构，定位 Premain-Class ，在 agent/java/boot/pom.xml 文件中找到了相关配置：

![](https://changeyourway.github.io/images/image-20250709100810-zd23eu3.png)

这是以 xml 格式配置的，不过看别人的分析文章是配置在 MANIFEST.MF 里，想来时代变迁，xml 配置因为适配 maven 打包而变得更流行了。

其中指示了主要的 agent 类为 com.baidu.openrasp.Agent ，直接关注其 premain 与 agentmain 方法：

![](https://changeyourway.github.io/images/image-20250709102130-jg9i5mo.png)

均调用了 init 方法，继续追踪：

![](https://changeyourway.github.io/images/image-20250709102210-2fv05bd.png)

其中 JarFileHelper.addJarToBootstrap 首先获取 agent 的 Jar 文件路径，然后调用 `inst.appendToBootstrapClassLoaderSearch` 。

在 Java Agent 里，`Instrumentation.appendToBootstrapClassLoaderSearch(JarFile jar)` 的核心作用，就是**把指定 JAR 加入到 JVM 最顶层的 bootstrap 类加载器的“兜底搜索列表”，** 其等价于运行期的 `-Xbootclasspath/a` 。

/a 与 /p 的区别：

`-Xbootclasspath/p` **把你的 JAR 或目录“放到”引导类加载器（bootstrap class loader）的最前面**，优先级甚至高于 `rt.jar`；

`-Xbootclasspath/a` **把它们追加到最后**，只有当 JDK 自己和其它 boot JAR 都没命中时才会去找。

**/p 能覆盖或“热补丁”JDK 核心类**，/a 只能让 boot loader 能看到你的新类而不会覆盖旧实现。

![](https://changeyourway.github.io/images/image-20250709102328-efdiuv9.png)

getLocalJarPath 其关键在于 `Agent.class.getProtectionDomain().getCodeSource().getLocation()` 会在**运行时**返回 `Agent` 这个类究竟是从哪儿加载进 JVM 的——通常是一个指向 `agent.jar` 的 `URL`（例如 `file:/…/agent.jar` 或 `jar:file:/…/agent.jar!/`），于是就获取了 Jar 路径：

![](https://changeyourway.github.io/images/image-20250709102649-mhtlsj7.png)

上面这种方式在 agent 中挺常见的，即

1.  `Class.getProtectionDomain().getCodeSource().getLocation()` 获取 Jar 路径
2.  `inst.appendToBootstrapClassLoaderSearch(new JarFile(localJarPath))` 将 Jar 放入 bootstrap 类加载器中，以确保能搜索到类。

于是，JarFileHelper.addJarToBootstrap 我们就看完了，接下来看 ModuleLoader.load ：

![](https://changeyourway.github.io/images/image-20250709111105-rjda278.png)

看注释，它用来加载 RASP 模块，其要求三个参数：mode、action 和 inst 。在前面阶段，premain 、agentmain 传入的 mode 分别为 “normal” 和 “attach” ，premain 传入的 action 为 “install” ，agentmain 的 action 需要在运行时手动传入：

![](https://changeyourway.github.io/images/image-20250709111232-rlygg9x.png)

ModuleLoader.load 仅对 action 为 “install” 与 “uninstall” 的调用进行处理。当为 “install” 时初始化一个 ModuleLoader 对象：

![](https://changeyourway.github.io/images/image-20250709112311-khq4hyn.png)

其中，当 mode 为 “normal” 时额外调用一个 setStartupOptionForJboss() 方法，是为了扩展其在 Jboss7 下的兼容性。对于其他 mode ，直接初始化一个 ModuleContainer 对象，并将 ENGINE\_JAR 作为参数传入，我们可以看到 ENGINE\_JAR 指代 rasp-engine.jar ：

![](https://changeyourway.github.io/images/image-20250709112558-avkcb9e.png)

来看看 ModuleContainer 的构造，**其读取 JAR 中的自定义清单，确认「模块名 + 入口类」，然后把 JAR 动态塞进系统/自定义类加载器的搜索路径，再反射加载并实例化入口类：**

![](https://changeyourway.github.io/images/image-20250709112707-8lmjv8v.png)

1 读取并校验 JAR 清单

```java
JarFile jarFile = new JarFile(originFile);
Attributes attrs = jarFile.getManifest().getMainAttributes();
this.moduleName = attrs.getValue("Rasp-Module-Name");
String moduleEnterClassName = attrs.getValue("Rasp-Module-Class");
```

-   **`JarFile`** **+** **`Manifest`** 用来解析 `META-INF/MANIFEST.MF`（或者说 pom.xml 中的配置项）；这里约定了两条私有属性：`Rasp-Module-Name` 和 `Rasp-Module-Class`，只有两者都非空才算合法模块。
-   读完立即 `jarFile.close()`，防止文件句柄泄漏。

2 判断运行时环境：系统加载器是不是 `URLClassLoader`

2.1 传统 JDK 8- 及以下 —— `URLClassLoader` 分支

```java
if (ClassLoader.getSystemClassLoader() instanceof URLClassLoader) {
    Method m = URLClassLoader.class.getDeclaredMethod("addURL", URL.class);
    m.setAccessible(true);
    m.invoke(moduleClassLoader, originFile.toURI().toURL());
    m.invoke(ClassLoader.getSystemClassLoader(), originFile.toURI().toURL());
}
```

-   **核心点：反射调用受保护的** **`addURL(URL)`** **方法**——这是在运行时把新 JAR 塞进 `URLClassLoader` 的经典“黑科技”。
-   既往 JVM 把 **系统加载器（AppClassLoader）** 也实现成 `URLClassLoader`，所以这种方式在 JDK 8- 时代可行。
-   代码既把 JAR 加进 **专用的** **`moduleClassLoader`**（给模块自身用），也加进 **系统加载器**（给其它类直接引用）。

2.2 JDK 9+ 或自定义加载器 —— `appendToClassPathForInstrumentation` 分支

```java
else if (ModuleLoader.isCustomClassloader()) {
    Method m = sysLoader.getClass()
        .getDeclaredMethod("appendToClassPathForInstrumentation", String.class);
    m.setAccessible(true);
    m.invoke(sysLoader, originFile.getCanonicalPath());
}
```

-   从 Java 9 开始，系统加载器不再继承 `URLClassLoader`，`addURL` 不复存在；JVM 改为**保留一条私有的 fallback 钩子**——`appendToClassPathForInstrumentation(String)`，专门给 **Java Agent/Instrumentation** 在运行期追加 classpath 用。
-   反射调用该方法即可把 JAR 挂进系统加载器的搜索列表（效果与启动参数 `-Xbootclasspath/a` 类似）。
-   `ModuleLoader.isCustomClassloader()` 用来探知当前 JVM 是否启用了 OpenRASP 自己的特殊加载器；若返回 true，就走这一分支。

3 加载并实例化模块入口类

```java
moduleClass = moduleClassLoader.loadClass(moduleEnterClassName);
module = (Module) moduleClass.newInstance();
```

-   反射加载清单里声明的 **模块入口类**，并强转为 OpenRASP 统一定义的 `Module` 接口/父类。
-   这样每个模块都能实现自己的逻辑，同时被主程序管理。

这段代码完成以后，会将 Rasp-Module-Class 指示的类实例化并封装进 module 属性中，后续 engineContainer.start 也就是调用 module 属性的 start 方法

![](https://changeyourway.github.io/images/image-20250709121135-q9kcwf5.png)

所以，这一部分 agent 指向了一个新的 Jar 包 rasp-engine.jar ，以及其配置文件，其中必包含两个项 Rasp-Module-Name 和 Rasp-Module-Class ，并且 Rasp-Module-Class 指向的类会被实例化，其 start 会被调用。

### rasp-engine

下载的项目里面并不直接有 rasp-engine.jar 这个文件，但我们可以找到其对应的代码在 agent/java/engine 目录下。其 pom.xml ：

![](https://changeyourway.github.io/images/image-20250709114704-qr8nyf8.png)

既然这里又指示了 com.baidu.openrasp.EngineBoot 这个类，顺藤摸瓜找到这个类，在其 Start 方法发现了一个大 logo ：

![](https://changeyourway.github.io/images/image-20250709121349-ady6xt9.png)

缺失了 com.baidu.openrasp.v8 包，导致 com.baidu.openrasp.v8.Loader 找不到，在这里下载：

[https://github.com/baidu-security/openrasp-v8/tree/4e1398d9e3de81a581c8f465b117abb8399a014d](https://github.com/baidu-security/openrasp-v8/tree/4e1398d9e3de81a581c8f465b117abb8399a014d)

不过 Loader.load() 在这里是加载了一个名为 openrasp\_v8\_java 的库，实质是一段**本地（Native）代码**，暂不关注。

loadConfig() 完成对日志（log4j、云控、Syslog）的配置，不重要。

Agent.readVersion() 从 /META-INF/MANIFEST.MF 中读取配置信息，但是项目并没有 MANIFEST.MF 文件，同样是写在 pom.xml 文件中，其在 maven 打包时会将相关信息写入 jar 的 MANIFEST.MF 文件，使得代码可以读取到这些信息：

![](https://changeyourway.github.io/images/image-20250709150930-bttpzmu.png)

JS.Initialize() 完成了 V8 的初始化还有一些设置，仍然不是很清楚：

![](https://changeyourway.github.io/images/image-20250709151737-iq02tkz.png)

跟进 V8.Initialize() ，最终调用的是一个 native 方法：

![](https://changeyourway.github.io/images/image-20250709153135-zawarx9.png)

纯初始化。

后面的 V8.SetLogger 和 V8.SetStackGetter 设置两个属性 V8.logger 和 V8.stackGetter ，暂时没有看到用法。

#### Transformer 配置

回到 EngineBoot 继续往后看，initTransformer(inst) 很关键，它果然是用来配置转换器的：

![](https://changeyourway.github.io/images/image-20250709155241-k9ppvrn.png) ![](https://changeyourway.github.io/images/image-20250709155254-gccragt.png)

这里添加的转换器是 CustomClassTransformer 自身，那么真正的 hook 代码就藏在其 transform 当中了：

![](https://changeyourway.github.io/images/image-20250709155531-m383cbb.png)

这里维护了一个要被 hook 的类的列表 hooks ，通过 addHook 可以向其中添加值。

对于 hooks 列表中的所有类，调用 hook.transformClass 去修改（通过参数 classfileBuffer 拿到类的字节码）。

![](https://changeyourway.github.io/images/image-20250709163339-m6u766d.png)

hookMethod 有 99 个实现，针对不同的执行点指定了不同的拦截方案：

![](https://changeyourway.github.io/images/image-20250709163358-vp3m416.png)

#### JNDI Hook

找一个比较熟悉的，看看 JNDIHook 中的实现：

![](https://changeyourway.github.io/images/image-20250709163554-p9al8c8.png) ![](https://changeyourway.github.io/images/image-20250709165214-aarmewh.png)

相当于把 com.baidu.openrasp.hook.JNDIHook.checkJNDILookup($1); 插入 lookup 方法开头。

这个 checkJNDILookup 又干了什么呢？

![](https://changeyourway.github.io/images/image-20250709173908-ud20gcw.png) ![](https://changeyourway.github.io/images/image-20250709174004-uhsiqmt.png) ![](https://changeyourway.github.io/images/image-20250709174100-dcaj58j.png) ![](https://changeyourway.github.io/images/image-20250709174137-zsq51zo.png) ![](https://changeyourway.github.io/images/image-20250709174202-arbm28h.png)

追到 checkParam 这里有 7 个实现：

![](https://changeyourway.github.io/images/image-20250709174303-raloso8.png)

#### V8AttackChecker

到底由哪一个 Checker 来处理 JNDI Hook 产生的检测请求，其实早就写死在 CheckParameter.Type 这个枚举里，最开始 checkJNDILookup 传入的第一个参数是 CheckParameter.Type.JNDI ，故而选择 V8AttackChecker 。

![](https://changeyourway.github.io/images/image-20250709175031-x1eh1w2.png)

V8AttackChecker 的 checkParam 方法：

![](https://changeyourway.github.io/images/image-20250709175217-rvr7k8d.png)

JS.Check：

1、将数据发送到 V8.Check 检查，并获取返回结果：

![](https://changeyourway.github.io/images/image-20250710093650-khf1wyt.png)

2、如果返回结果为空，将其对应的 hashData 加入到缓存 Config.commonLRUCache 中：

![](https://changeyourway.github.io/images/image-20250710093751-tf6f2g4.png)

这个 hashData 是来自于请求参数转化成的 json 数据，就是这串 json 数据的 hash 值（或者当 json 长度小于某个值时，直接使用 json 数据本身）：

![](https://changeyourway.github.io/images/image-20250710094003-irdmo59.png)

3、将返回结果以 json 格式提取出来：

![](https://changeyourway.github.io/images/image-20250710094623-dc0bith.png)

V8.Check 实际调用 native 方法 Java\_com\_baidu\_openrasp\_v8\_V8\_Check ，找到这个方法，在 com\_baidu\_openrasp\_v8\_V8.cc 文件中：

![](https://changeyourway.github.io/images/image-20250710095809-hj7fypz.png)

这个方法实际上依然是一个中间层，它调用 isolate->Check 检查，然后处理返回值。

对于 isolate->Check ，全局搜索 Isolate::Check ，找到方法定义在 isolate.cc 文件中：

![](https://changeyourway.github.io/images/image-20250710100422-z16ap8d.png)

真正的调用 js 方法的地方：

![](https://changeyourway.github.io/images/image-20250710112358-323odjb.png)

那我又要问了，它怎么知道要调哪个方法呢？这里面没有看到任何跟 js 文件或是方法有关的位置信息。

果真如此吗？下面来回答一下：Isolate::Check 何以调用检测脚本？

#### js 插件注册

js 插件文件在 com.baidu.openrasp.plugin.js.JS#UpdatePlugin() 中被加载，并早在 JS.Initialize() 中就被调用过。其中指示了加载 js 文件的路径，为：<rasp\_root>/plugins 。

![](https://changeyourway.github.io/images/image-20250709221558-j7jk22r.png) ![](https://changeyourway.github.io/images/image-20250709221611-grdf5ed.png)

最后调用 UpdatePlugin(scripts) 处理 js 脚本内容：  
![](https://changeyourway.github.io/images/image-20250710122345-jgmm2g2.png)

这里调用 V8.CreateSnapshot 创建 v8 快照，V8.CreateSnapshot 是一个 native 方法，我们可以找到对应的方法名为 Java\_com\_baidu\_openrasp\_v8\_V8\_CreateSnapshot ：

![](https://changeyourway.github.io/images/image-20250710124956-ijn0vs1.png)

新建一个 Snapshot 对象，这个对象将 js 插件列表封装进去了。

在 Snapshot 的构造函数 Snapshot::Snapshot 中，运行了其内建脚本 gen\_builtins 、配置脚本 config 、插件脚本 plugin\_list ：

![](https://changeyourway.github.io/images/image-20250711211838-un5z6uo.png)

其中调用 isolate->ExecScript 执行 js 脚本，可以找到其实现 Isolate::ExecScript ，在 isolate.cc 文件中：

![](https://changeyourway.github.io/images/image-20250711223818-v0qh2bo.png)

在 Isolate::ExecScript 中，代码被编译为 HeapObject（Script / SharedFunctionInfo / JSFunction），进入 Isolate 的 **JS 堆**。

后续于是 Isolate::Check 可以找到这些方法并执行（这里不再解释，如果熟悉 C++ ，可以更快理解）。

#### RASP 黑名单

最后来看看真正定义 RASP 拦截的黑名单在哪里。

<rasp\_root>/plugins，应该指的是 openrasp-master\\plugins 即根目录下的 plugins 目录，其中有一个 plugins/official/plugin.js 文件，表示官方插件。

找到 plugins/official/plugin.js 中针对 Jndi 的处理部分，或者说，针对 Java 的处理部分，主要在 validate\_stack\_java 方法中：

![](https://changeyourway.github.io/images/image-20250710092617-n3e9hfs.png)

根据栈上匹配到的类返回不同的信息。

有意思的是，它对 ysoserial.Pwner 、org.su18 、net.rebeyond.behinder 这种包名也做了匹配，并返回信息说明使用了工具：

![](https://changeyourway.github.io/images/image-20250710092805-n0sec5z.png)

## OpenRasp 绕过

这里只提出比较浅显的意见，我也只是纸上谈兵，同时结合了 Y4tacker 等前辈的一些观点。

OpenRasp 对各种漏洞类型都做了防护，防护措施同中存异，所以我们谈绕过，也应该分开的、逐个的来谈。

### 1、黑名单绕过

最容易想到的，实际情况下也是最难做到的，找出黑名单之外的类进行利用，常见于反序列化绕过：

![](https://changeyourway.github.io/images/image-20250711231228-k38vhtx.png)

这个名单看着就不太全的样子。

### 2、正则绕过

譬如命令执行这一块，最低级别的防护：

![](https://changeyourway.github.io/images/image-20250711231432-emg9fru.png)

对于 cat 命令就只拦截了 cat /etc/passwd 操作，cat 其他文件那是睁一只眼闭一只眼。或者就像 Y4tacker 师傅说的，cat 函数支持同时读多个文件，像这样操作：cat /abc/def /etc/passwd 。

### 3、业务逻辑绕过

举个例子，xxe 这块对其他协议直接拉黑，但对于 file:// 协议就只是记录日志：

![](https://changeyourway.github.io/images/image-20250711232333-2vbeczb.png)

为什么呢？可能有些正常业务它要用这个 file:// 协议。所以这就引出一个关键问题：RASP 在很底层，如果限制太多，可能正常程序都跑不起来。在兼容性要求下，RASP 就不能拦得太死。

在前面分析代码的时候，其实也遇到了这么一个地方：服务器的 cpu 使用率超过 90% ，以及云控注册成功之前，禁用全部 hook 点：

![](https://changeyourway.github.io/images/image-20250711233005-xl9mfo9.png)

这也是为业务让路的一种体现，Y4tacker 师傅专门为这个点写了示例程序，就不再赘述。

当前，前面提到的命令执行，除了正则过滤，还有一种模式是全部禁用：

![](https://changeyourway.github.io/images/image-20250711234602-rqrtiqr.png)

为什么要设置两种模式呢？低级别的防护用于兼容正常需要执行命令的系统，所以这也是一种体现。

### 4、覆盖文件

覆盖文件分为两种，一种是覆盖 js 插件文件，因为黑名单就写在插件文件里。并且我们可以看到 OpenRasp 中对于上传 html/js 文件是采取直接忽略的方式：

![](https://changeyourway.github.io/images/image-20250711233738-5fgbhuk.png)

还有一种思路就是直接覆盖 Rasp 的 jar 文件，Rasp 本质上还是 agent ，一般以 jar 文件形式生效，如果能够覆盖，那么可以直接禁掉 Rasp 。OpenRasp 中并没有对上传 jar 文件有拦截。但是可能需要服务器重启才能生效，且 Windows 下可能会因为文件正在运行，进程占用无法覆盖。

### 总结

以上几种方式，我认为利用第三种方式是最可能的，就像先前说的，RASP 处在很底层，真正要布置到实际环境中一定要考虑对程序的兼容性，不能影响程序自身的逻辑，为此，要么降低黑名单强度，要么为程序设计定制化的 RASP ，如此便削弱了其防护能力。

记得某人曾说，许多安全问题的产生都是由于要为业务让路，在这里我们也能看到同样的体现。

‍

## 参考文章

[https://www.cnblogs.com/lccsetsun/p/14000936.html](https://www.cnblogs.com/lccsetsun/p/14000936.html)

[https://stoocea.github.io/post/Rasp%E5%88%86%E6%9E%90%5B1%5D-%E7%AE%80%E5%8D%95%E6%9C%BA%E5%88%B6%E5%AD%A6%E4%B9%A0.html](https://stoocea.github.io/post/Rasp%E5%88%86%E6%9E%90%5B1%5D-%E7%AE%80%E5%8D%95%E6%9C%BA%E5%88%B6%E5%AD%A6%E4%B9%A0.html)

[https://y4tacker.github.io/2022/05/28/year/2022/5/OpenRasp%E5%88%86%E6%9E%90](https://y4tacker.github.io/2022/05/28/year/2022/5/OpenRasp%E5%88%86%E6%9E%90)

‍
