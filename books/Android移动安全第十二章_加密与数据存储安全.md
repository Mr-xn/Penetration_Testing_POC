# Android移动安全第十二章_加密与数据存储安全
> QIANXIN Team
> 来源：https://forum.butian.net/share/4879

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
> 12.  Android 加密与数据存储安全（本章）
> 13.  Android 认证与证书校验
> 14.  Android Zip Slip 路径遍历
> 15.  Android Fragment Injection
> 16.  Android SELinux 与沙箱机制

* * *

## 1\. 前言

Android 的应用沙箱机制为每个 App 分配了独立的 Linux 用户 ID（UID）和私有数据目录（`/data/data/<package_name>/`）。正常情况下，一个 App 无法读取另一个 App 的私有数据。

但沙箱不是万能的。以下场景中，App 的本地数据可能被读取：

-   设备被 root（root 用户可以访问所有文件）
-   通过 `adb backup` 导出应用数据（如果 App 允许备份）
-   通过导出的 ContentProvider 或 FileProvider 间接读取（第四章讲过）
-   设备被物理接触，通过自定义 Recovery 或芯片级读取提取数据分区
-   App 自己把数据写到了外部存储（SD 卡），外部存储对所有 App 可读

所以"数据在沙箱里就安全了"这个假设并不成立。敏感数据需要加密存储，而加密的质量取决于算法选择和密钥管理。

* * *

## 2\. 本地存储方式

### 2.1 SharedPreferences

SharedPreferences 是 Android 提供的轻量级键值对存储，底层是 XML 文件，存放在 `/data/data/<package_name>/shared_prefs/` 目录下。

```java
SharedPreferences prefs = getSharedPreferences("config", MODE_PRIVATE);
SharedPreferences.Editor editor = prefs.edit();
editor.putString("auth_token", "eyJhbGciOiJIUzI1NiJ9...");
editor.putString("user_password", "plaintext_password");
editor.apply();
```

生成的 XML 文件内容：

```xml
<?xml version='1.0' encoding='utf-8' standalone='yes' ?>
<map>
    <string name="auth_token">eyJhbGciOiJIUzI1NiJ9...</string>
    <string name="user_password">plaintext_password</string>
</map>
```

通过 ADB 可以直接读取（需要 root 或 `run-as`）：

```bash
adb shell run-as com.target.app \
    cat shared_prefs/config.xml
```

SharedPreferences 本身不提供任何加密能力。存进去什么，文件里就是什么。

另一个常见问题是 `MODE_WORLD_READABLE`。这个模式在 Android 4.2 之前允许其他 App 读取 SharedPreferences 文件。虽然在 Android 7.0 之后使用这个模式会直接抛出 SecurityException，但一些老旧的 App 或 SDK 可能仍然在用。

### 2.2 SQLite 数据库

SQLite 数据库文件存放在 `/data/data/<package_name>/databases/` 目录下。和 SharedPreferences 一样，默认不加密。

```java
SQLiteDatabase db = openOrCreateDatabase("users.db", MODE_PRIVATE, null);
db.execSQL("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, " +
    "username TEXT, password TEXT, token TEXT)");
db.execSQL("INSERT INTO users VALUES (1, 'admin', 'P@ssw0rd', 'secret_token')");
```

通过 ADB 提取数据库文件后，可以用任何 SQLite 工具打开：

```bash
adb shell run-as com.target.app \
    cat databases/users.db > /tmp/users.db
sqlite3 /tmp/users.db "SELECT * FROM users;"
```

### 2.3 文件存储

App 可以在私有目录下创建任意文件：

```java

FileOutputStream fos = openFileOutput("secret.txt", MODE_PRIVATE);
fos.write("sensitive data".getBytes());
fos.close();


File cacheFile = new File(getCacheDir(), "temp_token.txt");
```

### 2.4 外部存储

外部存储（SD 卡或模拟的外部存储）是一个公共区域。Android 10 之前，任何持有 `READ_EXTERNAL_STORAGE` 权限的 App 都可以读取外部存储中的所有文件。

```java

File file = new File(Environment.getExternalStorageDirectory(), "backup.json");
FileWriter writer = new FileWriter(file);
writer.write("{\"token\": \"secret\", \"password\": \"123456\"}");
writer.close();
```

Android 10 引入了分区存储（Scoped Storage），限制了 App 对外部存储的访问范围。但 App 仍然可以访问自己创建的文件，且通过 `MANAGE_EXTERNAL_STORAGE` 权限可以访问所有文件。

### 2.5 adb backup

`adb backup` 命令可以导出 App 的私有数据（SharedPreferences、数据库、文件）。如果 App 的 Manifest 中 `android:allowBackup="true"`（这是默认值），数据就可以被导出：

```bash
adb backup -f backup.ab com.target.app
```

导出的 `.ab` 文件可以用工具转换为 tar 格式后解压，获取 App 的所有私有数据。

Android 12 开始，`adb backup` 默认不再包含 App 数据（即使 `allowBackup="true"`），但通过 `android:debuggable="true"` 或特定的备份代理配置仍然可能导出。

* * *

## 3\. 常见的加密问题

### 3.1 硬编码密钥

最常见的加密问题是密钥硬编码在代码中：

```java

private static final String SECRET_KEY = "MySecretKey12345";

public String encrypt(String data) {
    SecretKeySpec keySpec = new SecretKeySpec(
        SECRET_KEY.getBytes(), "AES");
    Cipher cipher = Cipher.getInstance("AES/ECB/PKCS5Padding");
    cipher.init(Cipher.ENCRYPT_MODE, keySpec);
    return Base64.encodeToString(cipher.doFinal(data.getBytes()), Base64.DEFAULT);
}
```

反编译 APK 后，硬编码的密钥一目了然。即使做了混淆，字符串常量通常不会被混淆（ProGuard/R8 默认不混淆字符串）。

常见的硬编码位置：

-   Java/Kotlin 源码中的 `static final` 常量
-   `BuildConfig` 中的自定义字段
-   `res/values/strings.xml` 中的字符串资源
-   `assets/` 目录下的配置文件
-   `AndroidManifest.xml` 中的 `<meta-data>`
-   native so 库中的字符串（稍难提取，但通过 `strings` 命令或逆向工具仍然可以找到）

### 3.2 不安全的加密模式

AES 加密有多种工作模式，选择不当会严重削弱加密强度：

ECB（Electronic Codebook）模式——每个数据块独立加密，相同的明文块产生相同的密文块。这意味着密文中保留了明文的模式信息：

```java

Cipher cipher = Cipher.getInstance("AES/ECB/PKCS5Padding");
```

CBC（Cipher Block Chaining）模式——每个数据块的加密依赖前一个密文块，需要一个初始化向量（IV，Initialization Vector，一个随机的初始数据块，用于确保相同的明文每次加密产生不同的密文）。但如果 IV 是固定的或可预测的，CBC 的安全性也会下降：

```java

byte[] iv = "1234567890123456".getBytes();
IvParameterSpec ivSpec = new IvParameterSpec(iv);
Cipher cipher = Cipher.getInstance("AES/CBC/PKCS5Padding");
cipher.init(Cipher.ENCRYPT_MODE, keySpec, ivSpec);
```

GCM（Galois/Counter Mode）模式——提供加密和完整性校验，是目前推荐的模式。但 GCM 要求每次加密使用不同的 nonce（一次性数字），重复使用 nonce 会导致密钥泄露：

```java

byte[] nonce = new byte[12];
new SecureRandom().nextBytes(nonce);  
GCMParameterSpec gcmSpec = new GCMParameterSpec(128, nonce);
Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
cipher.init(Cipher.ENCRYPT_MODE, keySpec, gcmSpec);
```

### 3.3 弱哈希算法

密码存储通常使用哈希算法（单向函数，无法从哈希值反推出原始数据）。但一些 App 使用了已被证明不安全的哈希算法：

```java

MessageDigest md = MessageDigest.getInstance("MD5");
byte[] hash = md.digest(password.getBytes());


MessageDigest md = MessageDigest.getInstance("SHA-1");


String hash = sha256(password);
```

MD5 和 SHA-1 的碰撞攻击已经被实际演示过，不应该用于安全场景。即使使用 SHA-256，如果不加盐（salt，一个随机字符串，和密码拼接后再哈希，确保相同密码产生不同的哈希值），也容易被彩虹表（预计算的哈希值对照表）攻击。

### 3.4 自定义加密算法

一些开发者会实现自己的"加密"算法，比如简单的 XOR、字符替换、Base64 编码等：

```java

String "encrypted" = Base64.encodeToString(data.getBytes(), Base64.DEFAULT);


byte[] encrypt(byte[] data, byte key) {
    byte[] result = new byte[data.length];
    for (int i = 0; i < data.length; i++) {
        result[i] = (byte)(data[i] ^ key);
    }
    return result;
}
```

Base64 不是加密，它是一种编码方式，任何人都可以解码。XOR 加密如果密钥只有一个字节（256 种可能），暴力破解几乎是瞬间完成的。

* * *

## 4\. Android KeyStore

### 4.1 概述

Android KeyStore 是系统提供的密钥管理机制，从 Android 4.3（API 18）开始可用。它的核心特性是：密钥存储在系统级的安全容器中，App 可以使用密钥进行加密/解密操作，但无法导出密钥本身。

在支持硬件安全模块的设备上（大多数 Android 8.0+ 设备），KeyStore 的密钥存储在 TEE（Trusted Execution Environment，可信执行环境，一个独立于主操作系统的安全区域）或专用安全芯片（如 Titan M）中。即使设备被 root，也无法提取密钥。

### 4.2 基本使用

```java

KeyGenerator keyGen = KeyGenerator.getInstance(
    KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore");
keyGen.init(new KeyGenParameterSpec.Builder(
    "my_key_alias",
    KeyProperties.PURPOSE_ENCRYPT | KeyProperties.PURPOSE_DECRYPT)
    .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
    .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
    .build());
SecretKey key = keyGen.generateKey();


Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
cipher.init(Cipher.ENCRYPT_MODE, key);
byte[] iv = cipher.getIV();  
byte[] encrypted = cipher.doFinal(plaintext.getBytes());


KeyStore keyStore = KeyStore.getInstance("AndroidKeyStore");
keyStore.load(null);
SecretKey storedKey = (SecretKey) keyStore.getKey("my_key_alias", null);
Cipher decryptCipher = Cipher.getInstance("AES/GCM/NoPadding");
decryptCipher.init(Cipher.DECRYPT_MODE, storedKey, new GCMParameterSpec(128, iv));
byte[] decrypted = decryptCipher.doFinal(encrypted);
```

### 4.3 KeyStore 的安全属性

KeyGenParameterSpec 提供了多个安全相关的配置：

| 属性 | 说明 |
| --- | --- |
| setUserAuthenticationRequired(true) | 使用密钥前需要用户认证（指纹/PIN） |
| setUserAuthenticationValidityDurationSeconds(30) | 认证后 30 秒内可以使用密钥 |
| setInvalidatedByBiometricEnrollment(true) | 新增指纹后密钥失效 |
| setIsStrongBoxBacked(true) | 要求密钥存储在专用安全芯片中 |
| setUnlockedDeviceRequired(true) | 只有设备解锁时才能使用密钥 |

`setUserAuthenticationRequired(true)` 是一个比较有用的特性——即使攻击者拿到了设备并获得了 root 权限，如果不知道用户的 PIN/密码或没有用户的指纹，也无法使用密钥解密数据。

### 4.4 KeyStore 的局限

KeyStore 不是万能的：

-   密钥绑定设备：KeyStore 中的密钥无法导出，也无法在其他设备上使用。如果用户换设备，用 KeyStore 加密的数据无法迁移
-   依赖硬件支持：没有 TEE 或安全芯片的设备上，KeyStore 的密钥存储在软件层面，安全性较低
-   不防止内存读取：密钥在使用时会被加载到进程内存中，通过内存 dump 理论上可以提取（但需要 root 权限且时机要准确）

* * *

## 5\. EncryptedSharedPreferences

### 5.1 概述

Jetpack Security 库（`androidx.security:security-crypto`）提供了 EncryptedSharedPreferences，它是 SharedPreferences 的加密包装。key 和 value 都会被加密后存储。

```java
MasterKey masterKey = new MasterKey.Builder(context)
    .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
    .build();

SharedPreferences encryptedPrefs = EncryptedSharedPreferences.create(
    context,
    "encrypted_config",
    masterKey,
    EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
    EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM);


encryptedPrefs.edit()
    .putString("auth_token", "eyJhbGciOiJIUzI1NiJ9...")
    .apply();
```

生成的 XML 文件中，key 和 value 都是加密后的 Base64 字符串，无法直接读取。

### 5.2 底层机制

EncryptedSharedPreferences 使用 Google 的 Tink 加密库，密钥管理基于 Android KeyStore：

-   Master Key 存储在 Android KeyStore 中（不可导出）
-   每个 SharedPreferences 文件有独立的数据加密密钥（DEK，Data Encryption Key）
-   DEK 用 Master Key 加密后存储在 SharedPreferences 文件中
-   key 使用 AES-SIV（确定性加密，相同的 key 名称总是产生相同的密文，便于查找）
-   value 使用 AES-GCM（随机化加密，相同的 value 每次产生不同的密文）

* * *

## 6\. 日志泄露

### 6.1 Log 输出

Android 的 `Log` 类输出的日志可以被同一设备上的其他 App 读取（Android 4.1 之前），或者通过 ADB 读取：

```java

Log.d("Auth", "User token: " + authToken);
Log.i("Payment", "Card number: " + cardNumber);
Log.e("Login", "Password: " + password);
```

```bash
adb logcat -s Auth Payment Login
```

Android 4.1（API 16）之后，App 只能读取自己的日志，不能读取其他 App 的日志（除非持有 `READ_LOGS` 权限，这是 signature 级别权限）。但通过 ADB 仍然可以读取所有日志。

Release 版本的 App 应该移除所有包含敏感数据的日志输出。ProGuard/R8 可以配置移除 `Log.d()` 和 `Log.v()` 调用，但 `Log.i()`、`Log.w()`、`Log.e()` 通常会保留。

### 6.2 WebView 控制台日志

WebView 中 JavaScript 的 `console.log()` 输出也会出现在 Android 的 logcat 中：

```javascript
console.log("User session: " + sessionToken);
```

```bash
adb logcat -s chromium
```

如果 WebView 加载的页面中有调试日志输出敏感信息，通过 ADB 就能看到。

### 6.3 崩溃日志

App 崩溃时，系统会在 logcat 中输出完整的堆栈跟踪（stack trace）。如果崩溃发生在处理敏感数据的代码路径上，堆栈跟踪中可能包含敏感信息（如 URL 中的 token、异常消息中的用户数据）。

* * *

## 7\. 剪贴板

### 7.1 剪贴板泄露

Android 的剪贴板（ClipboardManager）是一个全局共享的机制。App 复制到剪贴板的内容可以被其他 App 读取：

```java
ClipboardManager clipboard = (ClipboardManager)
    getSystemService(CLIPBOARD_SERVICE);
ClipData clip = ClipData.newPlainText("password", "MyP@ssw0rd");
clipboard.setPrimaryClip(clip);

```

Android 10 开始，只有当前处于前台的 App 或默认输入法才能读取剪贴板内容。后台 App 调用 `getPrimaryClip()` 会返回空。Android 12 进一步增加了剪贴板访问的 Toast 提示，用户可以看到哪个 App 读取了剪贴板。

但在 Android 10 之前的设备上，任何 App 都可以在后台静默读取剪贴板。用户复制的密码、验证码、银行卡号等都可能被恶意 App 窃取。

* * *

## 8\. 总结

数据存储安全的核心问题是：沙箱保护不等于数据安全。root、备份导出、ContentProvider 泄露、外部存储等多种途径都可能绕过沙箱。

回顾一下：

-   SharedPreferences 和 SQLite 默认不加密，敏感数据以明文存储
-   硬编码密钥是最常见的加密问题，反编译后一目了然
-   ECB 模式、固定 IV、弱哈希算法都会削弱加密强度
-   Android KeyStore 提供了硬件级的密钥保护，密钥不可导出
-   EncryptedSharedPreferences 基于 KeyStore 和 Tink，是 SharedPreferences 的加密替代方案
-   日志输出和剪贴板是容易被忽视的数据泄露渠道
-   `allowBackup="true"` 允许通过 ADB 导出应用数据

下一章讲 Android 认证与证书校验。HTTPS 通信的安全性依赖于证书校验，如果 App 禁用了证书校验或实现了自定义的 TrustManager，中间人攻击就变得可行。
