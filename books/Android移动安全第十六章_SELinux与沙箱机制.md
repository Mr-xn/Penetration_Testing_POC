# Android移动安全第十六章_SELinux与沙箱机制
> QIANXIN Team
> 来源：https://forum.butian.net/share/4947

> 系列目录：
> 
> 1.  Android 组件导出安全
> 2.  Android Intent 安全
> 3.  Android Binder 服务安全
> 4.  Android ContentProvider 安全
> 5.  Android WebView 安全
> 6.  Android UI 欺骗与钓鱼
> 7.  Android Deep Link 安全
> 8.  Android 广播安全
> 9.  Android PendingIntent 安全
> 10.  Android 系统设置安全
> 11.  Android SSRF 与网络安全
> 12.  Android 加密与数据存储安全
> 13.  Android 认证与证书校验
> 14.  Android Zip Slip 路径遍历
> 15.  Android Fragment Injection
> 16.  Android SELinux 与沙箱机制（本章）

* * *

## 1\. 前言

前面十五章讲的漏洞——组件导出、Intent 注入、WebView 加载、路径遍历等——都发生在 Android 框架层（Java/Kotlin 层）。但 Android 的安全不只依赖框架层的权限检查，底层还有 Linux 内核提供的多重隔离机制。

这些机制的设计思路是纵深防御（Defense in Depth）：即使上层的权限检查被绕过，底层的隔离仍然能限制攻击者的行为范围。比如一个 App 通过漏洞获得了代码执行能力，但 SELinux 策略可能阻止它读取其他 App 的数据目录；seccomp 过滤器可能阻止它调用某些系统调用。

本章讲解 Android 沙箱的四个层次：Linux 用户隔离、文件系统 DAC、SELinux MAC、seccomp-bpf。

* * *

## 2\. Linux 用户隔离

### 2.1 每个 App 一个 UID

Android 利用了 Linux 的多用户机制来隔离 App。每个 App 在安装时被分配一个唯一的 Linux UID（User ID），通常从 10000 开始递增。App 的进程以这个 UID 运行，App 的私有目录（`/data/data/<package>/`）的所有者也是这个 UID。

```bash

adb shell dumpsys package com.example.app | grep userId



adb shell ls -la /data/data/ | grep com.example.app

```

`u0_a156` 是 UID 10156 的用户名表示（u0 表示主用户，a156 = 10156 - 10000）。目录权限 `drwx------` 表示只有所有者可以读写执行，其他用户（包括其他 App）没有任何权限。

这是 Android 沙箱最基础的一层：不同 App 运行在不同的 Linux 用户下，通过文件系统权限互相隔离。

### 2.2 共享 UID

两个 App 可以通过在 Manifest 中声明相同的 `android:sharedUserId` 来共享 UID：

```xml
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    android:sharedUserId="com.example.shared">
```

共享 UID 的 App 运行在同一个 Linux 用户下，可以互相访问对方的私有目录。系统 App 通常使用 `android.uid.system`（UID 1000）或 `android.uid.phone`（UID 1001）等共享 UID。

共享 UID 的前提是两个 App 使用相同的签名证书。这个机制在 Android 13 中被标记为 deprecated，新 App 不应该使用。

### 2.3 特殊 UID

Android 预定义了一些特殊 UID：

| UID | 用户名 | 用途 |
| --- | --- | --- |
| 0 | root | 超级用户 |
| 1000 | system | system_server 进程 |
| 1001 | radio | 电话/RIL 相关进程 |
| 1002 | bluetooth | 蓝牙相关进程 |
| 2000 | shell | ADB shell |
| 10000+ | u0_aXXX | 第三方 App |

UID 决定了进程的基础权限边界。UID 1000（system）可以访问大量系统资源，UID 0（root）几乎不受限制（但 SELinux 仍然可以限制 root）。

* * *

## 3\. DAC：自主访问控制

### 3.1 文件系统权限

DAC（Discretionary Access Control，自主访问控制）是 Linux 传统的权限模型。每个文件和目录有所有者（owner）、所属组（group）和其他用户（others）三组权限，分别控制读（r）、写（w）、执行（x）。

Android 的关键目录权限设置：

| 路径 | 权限 | 说明 |
| --- | --- | --- |
| /data/data/\<pkg>/ | 700 (rwx------) | App 私有目录，只有 App 自身可访问 |
| /data/data/\<pkg>/shared_prefs/ | 771 (rwxrwx--x) | SharedPreferences 目录 |
| /sdcard/ | 通过 FUSE/sdcardfs 控制 | 外部存储，权限由 Android 框架管理 |
| /system/ | 755 (rwxr-xr-x) | 系统分区，只读挂载 |
| /data/local/tmp/ | 1777 (rwxrwxrwt) | 临时目录，所有用户可写 |

### 3.2 DAC 的局限

DAC 的问题在于"自主"——文件所有者可以修改权限。如果一个 App 把自己的私有目录权限改为 777（所有用户可读写），其他 App 就能访问它的数据。早期 Android 版本中，一些 App 使用 `MODE_WORLD_READABLE` 创建 SharedPreferences，导致数据泄露：

```java

SharedPreferences prefs = getSharedPreferences("config", MODE_WORLD_READABLE);
```

`MODE_WORLD_READABLE`（值为 1）会将文件权限设为其他用户可读。这个常量在 API 17 中被标记为 deprecated，在 targetSdk >= 24 时使用会抛出 SecurityException。

DAC 是"底线"级别的保护——它能阻止大部分跨 App 的直接文件访问，但无法防御 root 进程或权限配置错误的情况。SELinux 就是为了弥补这个不足。

* * *

## 4\. SELinux：强制访问控制

### 4.1 MAC 与 DAC 的区别

SELinux（Security-Enhanced Linux）实现的是 MAC（Mandatory Access Control，强制访问控制）。与 DAC 不同，MAC 的策略由系统管理员（在 Android 上是 ROM 开发者）定义，进程自身无法修改。即使进程以 root 身份运行，SELinux 策略仍然生效。

DAC 检查的是"你是谁"（UID/GID），SELinux 检查的是"你被允许做什么"（安全上下文 + 策略规则）。两者是叠加关系——一个操作必须同时通过 DAC 和 SELinux 的检查才能执行。

### 4.2 安全上下文

SELinux 为系统中的每个进程和文件分配一个安全上下文（Security Context），也叫标签（Label）。格式为：

```php
user:role:type:level
```

在 Android 上，user 固定为 `u`，role 固定为 `r`（进程）或 `object_r`（文件），实际起作用的是 type 和 level。

```bash

adb shell ps -Z | grep com.example.app



adb shell ls -Z /data/data/com.example.app/

```

第三方 App 的进程类型通常是 `untrusted_app`（或 `untrusted_app_27`、`untrusted_app_32` 等，根据 targetSdk 区分）。系统 App 的类型是 `system_app` 或 `platform_app`。

### 4.3 类型（Type）

Type 是 SELinux 策略的核心概念。Android 预定义了大量类型：

| 类型 | 适用对象 | 说明 |
| --- | --- | --- |
| untrusted_app | 第三方 App 进程 | 权限最受限 |
| platform_app | 平台签名 App 进程 | 使用平台证书签名的 App |
| system_app | 系统 App 进程 | 预装在 /system 分区的 App |
| priv_app | 特权 App 进程 | 预装在 /system/priv-app 的 App |
| system_server | system_server 进程 | Android 框架核心进程 |
| kernel | 内核 | Linux 内核 |
| app_data_file | App 私有数据文件 | /data/data/\<pkg>/ 下的文件 |
| system_file | 系统文件 | /system/ 下的文件 |
| proc | proc 文件系统 | /proc/ 下的文件 |

### 4.4 策略规则

SELinux 策略用 `allow` 语句定义哪个类型的进程可以对哪个类型的对象执行什么操作：

```php
allow source_type target_type:object_class permission;
```

例如：

```php

allow untrusted_app app_data_file:file { read write open create getattr };
allow untrusted_app app_data_file:dir { search read open getattr };



```

SELinux 的默认策略是"拒绝一切"（deny by default）。只有明确写了 allow 规则的操作才被允许。这和 DAC 的"默认允许"形成对比。

### 4.5 MLS：多级安全

Android 的 SELinux 还使用了 MLS（Multi-Level Security，多级安全）来隔离不同 App 的数据。安全上下文中的 level 字段（如 `s0:c156,c256,c512,c768`）包含了 App 特有的分类标签（category）。

每个 App 的 category 是根据 UID 计算的，不同 App 的 category 不同。即使两个 App 的进程类型都是 `untrusted_app`，SELinux 也能通过 category 区分它们，阻止 App A 访问 App B 的数据文件。

### 4.6 Enforcing 与 Permissive 模式

SELinux 有两种运行模式：

-   Enforcing：强制模式，违反策略的操作被拒绝并记录日志
-   Permissive：宽容模式，违反策略的操作只记录日志不拒绝

```bash

adb shell getenforce



adb shell seinfo -t untrusted_app
```

Android 4.3 引入 SELinux 时使用 Permissive 模式，Android 5.0 开始对所有进程启用 Enforcing 模式。正式发布的 Android 设备都应该运行在 Enforcing 模式下。

一些 root 工具会将 SELinux 切换到 Permissive 模式以绕过限制。这也是为什么一些安全敏感的 App（如银行 App）会检测 SELinux 状态——Permissive 模式通常意味着设备已被 root 或篡改。

* * *

## 5\. SELinux 在 Android 上的实际效果

### 5.1 阻止跨 App 数据访问

即使通过漏洞获得了代码执行能力，SELinux 仍然限制进程只能访问策略允许的资源：

日志中的 `avc: denied` 就是 SELinux 拒绝操作的记录。`scontext` 是源（进程）的安全上下文，`tcontext` 是目标（文件）的安全上下文。

### 5.2 限制系统调用目标

SELinux 不仅控制文件访问，还控制进程间通信、网络操作、设备访问等：

```php

neverallow untrusted_app device:chr_file { read write };


neverallow untrusted_app self:capability sys_module;


neverallow untrusted_app default_prop:property_service set;
```

`neverallow` 是比 `allow` 更强的规则——它声明某个操作永远不被允许，即使其他地方有 `allow` 规则也不行。Android CTS（Compatibility Test Suite，兼容性测试套件）会验证设备的 SELinux 策略不违反 neverallow 规则。

### 5.3 厂商自定义策略

厂商可以在 AOSP 的 SELinux 策略基础上添加自定义规则。这些规则通常在 `device/<vendor>/<device>/sepolicy/` 目录下。

厂商自定义策略是审计的重点之一。有时厂商为了让自己的系统 App 正常工作，会添加过于宽松的 allow 规则：

```php

allow platform_app system_data_file:file { read write create unlink };

```

这种宽松策略可能被利用——如果攻击者能在 platform\_app 上下文中执行代码（比如通过前面章节讲的漏洞），就能利用这些额外的权限。

* * *

## 6\. seccomp-bpf：系统调用过滤

### 6.1 原理

seccomp（Secure Computing Mode）是 Linux 内核提供的系统调用过滤机制。seccomp-bpf 允许进程安装一个 BPF（Berkeley Packet Filter）程序来过滤系统调用——只允许进程使用预定义的系统调用子集。

Android 从 8.0（API 26）开始对所有 App 进程启用 seccomp-bpf 过滤器。过滤器在 Zygote（Android 的进程孵化器，所有 App 进程都从 Zygote fork 而来）中安装，App 进程继承这个过滤器。

### 6.2 被过滤的系统调用

Android 的 seccomp 过滤器阻止了一些危险的系统调用：

| 系统调用 | 说明 | 被阻止的原因 |
| --- | --- | --- |
| swapon/swapoff | 交换分区管理 | App 不需要管理交换分区 |
| init_module/delete_module | 内核模块加载/卸载 | 防止 App 加载恶意内核模块 |
| acct | 进程记账 | App 不需要此功能 |
| kexec_load | 加载新内核 | 防止 App 替换内核 |

如果 App 尝试调用被过滤的系统调用，进程会收到 SIGSYS 信号并终止。

### 6.3 与 SELinux 的互补

seccomp-bpf 和 SELinux 从不同角度限制进程行为：

-   SELinux 控制"进程能访问哪些资源"（文件、设备、网络、其他进程）
-   seccomp-bpf 控制"进程能使用哪些系统调用"

两者互补。SELinux 策略可能允许进程打开某个文件，但如果打开文件所需的系统调用被 seccomp 过滤了，操作仍然会失败。

* * *

## 7\. App 沙箱的完整架构

把前面讲的机制组合起来，Android App 的沙箱架构从底层到上层：

```php
┌─────────────────────────────────────┐
│  Android 权限模型                    │  ← 框架层：权限声明、运行时权限
│  (Manifest permissions, runtime)     │
├─────────────────────────────────────┤
│  SELinux MAC                         │  ← 内核层：强制访问控制
│  (type enforcement, MLS categories)  │
├─────────────────────────────────────┤
│  seccomp-bpf                         │  ← 内核层：系统调用过滤
│  (syscall whitelist)                 │
├─────────────────────────────────────┤
│  Linux DAC                           │  ← 内核层：UID/GID 文件权限
│  (per-app UID, file permissions)     │
├─────────────────────────────────────┤
│  Linux Kernel                        │  ← 进程隔离、内存保护
│  (process isolation, namespaces)     │
└─────────────────────────────────────┘
```

一个操作要成功执行，必须通过所有层的检查。任何一层拒绝，操作就失败。这就是纵深防御的效果。

### 7.1 攻击者视角

从攻击者的角度看，要突破 App 沙箱需要逐层绕过：

1.  绕过 Android 权限模型：利用导出组件、Intent 重定向等（前面章节讲的内容）
2.  绕过 SELinux：需要找到策略中的漏洞（过于宽松的 allow 规则）或利用内核漏洞
3.  绕过 seccomp：需要利用允许的系统调用组合来实现目标，或利用内核漏洞
4.  绕过 DAC：需要以目标 UID 运行，或利用权限配置错误

大部分 App 层面的漏洞（本系列前面讲的内容）停留在第 1 层。要突破到第 2-4 层通常需要内核漏洞或系统级漏洞，难度显著增加。

### 7.2 实际案例中的沙箱限制

回顾前面章节的漏洞，沙箱机制对攻击效果的限制：

-   第十四章的 Zip Slip：路径遍历只能写入 App 自身的私有目录（`/data/data/<pkg>/`），因为 SELinux 的 MLS category 阻止写入其他 App 的目录
-   第四章的 ContentProvider 路径遍历：`openFile()` 返回的文件描述符受 SELinux 限制，只能读取 App 有权访问的文件
-   第一章的组件导出：即使通过 Intent 重定向启动了内部 Activity，执行的代码仍然在目标 App 的沙箱内，受其 SELinux 上下文约束

沙箱不能阻止漏洞的发生，但能限制漏洞的影响范围。

* * *

## 8\. 总结

Android 的沙箱是多层防御的组合。Linux UID 隔离提供基础的进程和文件隔离，DAC 控制文件访问权限，SELinux 在此之上添加强制访问控制，seccomp-bpf 限制可用的系统调用。

回顾一下：

-   每个 App 有独立的 Linux UID，私有目录权限 700
-   SELinux 的 type enforcement 和 MLS category 提供细粒度的强制访问控制
-   即使 root 进程也受 SELinux 策略约束（Enforcing 模式下）
-   seccomp-bpf 过滤危险的系统调用
-   厂商自定义的 SELinux 策略可能引入额外的攻击面
-   大部分 App 层漏洞的影响范围被沙箱限制在目标 App 的上下文内

这是本系列的最后一章。从第一章的组件导出到本章的沙箱机制，覆盖了 Android 客户端安全的主要技术方向。每个方向都有各自的攻击面和防御机制，实际审计中往往需要组合多个方向的知识来发现和利用漏洞。
