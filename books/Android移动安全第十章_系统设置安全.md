# Android移动安全第十章_系统设置安全
> QIANXIN Team
> 来源：https://forum.butian.net/share/4877

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
> 10.  Android 系统设置安全（本章）
> 11.  Android SSRF 与网络安全
> 12.  Android 加密与数据存储安全
> 13.  Android 认证与证书校验
> 14.  Android Zip Slip 路径遍历
> 15.  Android Fragment Injection
> 16.  Android SELinux 与沙箱机制

* * *

## 1\. 前言

Android 的系统设置存储在一个名为 SettingsProvider 的系统级 ContentProvider 中。第四章讲过 ContentProvider 的安全问题，SettingsProvider 是其中一个比较特殊的实例——它不存储用户数据，而是存储设备配置。

SettingsProvider 对外暴露了三个命名空间（namespace），每个命名空间对应一张数据库表：

-   `Settings.System`：用户可见的基础设置，如铃声音量、屏幕亮度、字体大小
-   `Settings.Secure`：需要更高权限才能修改的设置，如定位服务开关、默认输入法、设备 ID
-   `Settings.Global`：全局设备设置，如飞行模式、移动数据开关、ADB 调试开关

读写这些设置使用的 API 很简单：

```java

String value = Settings.Secure.getString(contentResolver, "android_id");
int brightness = Settings.System.getInt(contentResolver, "screen_brightness", 128);


Settings.System.putInt(contentResolver, "screen_brightness", 255);
```

底层实际上是对 `content://settings/system`、`content://settings/secure`、`content://settings/global` 这三个 URI 的 ContentProvider 操作。

* * *

## 2\. 三个命名空间的权限模型

### 2.1 Settings.System

Settings.System 是权限要求最低的命名空间。

读取：任何 App 都可以读取，不需要任何权限。

写入：需要 `WRITE_SETTINGS` 权限。这个权限在 Android 6.0 之前是 normal 级别（声明即可获得），Android 6.0 之后改为需要用户在设置页面中手动授权（通过 `Settings.ACTION_MANAGE_WRITE_SETTINGS` 跳转）。

```java

if (Settings.System.canWrite(context)) {
    Settings.System.putInt(contentResolver, "screen_brightness", 0);
} else {
    
    Intent intent = new Intent(Settings.ACTION_MANAGE_WRITE_SETTINGS);
    intent.setData(Uri.parse("package:" + getPackageName()));
    startActivity(intent);
}
```

Settings.System 中的设置项大多是用户体验相关的，直接的安全影响有限。但有一些值得注意的项：

| 设置项 | 说明 | 潜在影响 |
| --- | --- | --- |
| screen_brightness | 屏幕亮度 | 设为 0 可以让屏幕几乎全黑，配合 UI 欺骗使用 |
| screen_off_timeout | 屏幕自动关闭时间 | 设为极大值可以防止屏幕锁定 |
| font_scale | 字体缩放比例 | 设为极端值可以破坏 UI 布局 |
| haptic_feedback_enabled | 触觉反馈 | 关闭后用户操作无反馈 |

### 2.2 Settings.Secure

Settings.Secure 的权限要求更高。

读取：任何 App 都可以读取，不需要权限。这一点容易被忽略——虽然叫"Secure"，但读取是完全开放的。

写入：需要 `WRITE_SECURE_SETTINGS` 权限。这个权限的 protectionLevel 是 `signature|privileged`，只有系统签名 App 或预装在 `/system/priv-app/` 目录下的 App 才能获得。普通第三方 App 无法获得此权限。

但通过 ADB 可以直接读写 Settings.Secure：

```bash

adb shell settings get secure android_id
adb shell settings get secure enabled_accessibility_services


adb shell settings put secure enabled_accessibility_services com.example/.MyAccessibilityService
```

Settings.Secure 中包含不少敏感信息：

| 设置项 | 说明 | 安全影响 |
| --- | --- | --- |
| android_id | 设备唯一标识符（64 位十六进制字符串） | 用户追踪 |
| enabled_accessibility_services | 已启用的无障碍服务列表 | 可以判断用户安装了哪些辅助工具 |
| enabled_notification_listeners | 已启用的通知监听服务列表 | 可以判断哪些 App 有通知访问权限 |
| default_input_method | 当前默认输入法 | 信息收集 |
| location_providers_allowed | 允许的定位提供者 | 定位状态泄露 |
| lock_screen_lock_after_timeout | 锁屏超时时间 | 了解设备锁屏策略 |
| install_non_market_apps | 是否允许安装未知来源 App | 了解设备安全策略 |

这些信息单独看可能不算严重，但组合起来可以构建出设备的安全画像——用了什么输入法、开了哪些无障碍服务、定位是否开启、是否允许侧载 App。对于定向攻击来说，这些信息很有价值。

### 2.3 Settings.Global

Settings.Global 的权限模型和 Settings.Secure 类似。

读取：任何 App 都可以读取。

写入：需要 `WRITE_SECURE_SETTINGS` 权限（和 Settings.Secure 共用同一个写入权限）。

Settings.Global 中的设置项影响整个设备：

| 设置项 | 说明 | 安全影响 |
| --- | --- | --- |
| adb_enabled | ADB 调试是否开启 | 了解设备调试状态 |
| development_settings_enabled | 开发者选项是否开启 | 了解设备调试状态 |
| airplane_mode_on | 飞行模式 | 通过 ADB 可以开启飞行模式切断网络 |
| mobile_data | 移动数据开关 | 通过 ADB 可以关闭移动数据 |
| wifi_on | Wi-Fi 开关 | 通过 ADB 可以关闭 Wi-Fi |
| install_non_market_apps | 未知来源安装（部分版本） | 通过 ADB 可以开启侧载 |
| package_verifier_enable | 安装验证 | 通过 ADB 可以关闭安装验证 |

* * *

## 3\. 读取泄露

### 3.1 android\_id

`android_id` 是 Settings.Secure 中最常被讨论的设置项。它是一个 64 位的十六进制字符串，在设备首次启动时生成，恢复出厂设置后重新生成。

```java
String androidId = Settings.Secure.getString(
    getContentResolver(), Settings.Secure.ANDROID_ID);

```

Android 8.0 之前，`android_id` 对所有 App 返回相同的值，可以用于跨 App 追踪用户。Android 8.0 之后，每个 App（按签名密钥 + 用户组合）看到的 `android_id` 不同，降低了追踪能力。但同一个 App 在同一设备上看到的值是稳定的，仍然可以用于设备指纹。

### 3.2 无障碍服务枚举

`enabled_accessibility_services` 存储了当前启用的无障碍服务列表，格式是组件名用冒号分隔：

```java
String services = Settings.Secure.getString(
    getContentResolver(), "enabled_accessibility_services");

```

任何 App 都可以读取这个值，从而知道用户启用了哪些无障碍服务。无障碍服务拥有很高的权限（可以读取屏幕内容、模拟点击），知道用户启用了哪些服务可以帮助攻击者判断设备上是否有安全工具或自动化工具在运行。

### 3.3 通知监听服务枚举

类似地，`enabled_notification_listeners` 暴露了哪些 App 有通知访问权限：

```java
String listeners = Settings.Secure.getString(
    getContentResolver(), "enabled_notification_listeners");
```

第九章讲过 NotificationListenerService 可以读取通知中的 PendingIntent。通过这个设置项，攻击者可以知道设备上是否有 App 在监听通知。

### 3.4 ADB 批量读取

通过 ADB 可以一次性列出某个命名空间下的所有设置项：

```bash

adb shell settings list secure


adb shell settings list global


adb shell settings list system
```

输出是 `key=value` 格式的列表，包含了该命名空间下所有已设置的项。在物理接触设备的场景下（如设备被借用、送修），这些信息可以被快速提取。

* * *

## 4\. 写入攻击

### 4.1 Settings.System 写入

获得 `WRITE_SETTINGS` 权限后，App 可以修改 Settings.System 中的设置项。虽然这些设置大多是用户体验相关的，但在特定场景下可以配合其他攻击使用：

```java

Settings.System.putInt(contentResolver,
    Settings.System.SCREEN_BRIGHTNESS, 0);


Settings.System.putInt(contentResolver,
    Settings.System.SCREEN_OFF_TIMEOUT, Integer.MAX_VALUE);
```

屏幕亮度设为 0 后，用户看到的是几乎全黑的屏幕，可能以为设备关机了。配合第六章讲的 UI 欺骗，可以在用户不知情的情况下在"黑屏"上显示钓鱼界面。

### 4.2 通过 ADB 修改 Secure/Global

虽然第三方 App 无法写入 Settings.Secure 和 Settings.Global，但通过 ADB 可以。在设备被物理接触或通过恶意 PC 端工具连接的场景下：

```bash

adb shell settings put global adb_enabled 1


adb shell settings put global package_verifier_enable 0


adb shell settings put secure install_non_market_apps 1


adb shell settings put secure default_input_method \
    com.malicious.keyboard/.MaliciousIME


adb shell settings put secure enabled_accessibility_services \
    com.malicious.app/.EvilAccessibilityService
```

最后两条尤其危险。修改默认输入法意味着用户的所有键盘输入都会经过恶意输入法，包括密码。启用恶意无障碍服务则赋予了恶意 App 读取屏幕内容和模拟用户操作的能力。

不过从 Android 13 开始，通过 ADB 修改 `enabled_accessibility_services` 受到了限制——系统会检查目标无障碍服务是否已安装且声明了正确的权限。

### 4.3 厂商自定义设置项

厂商定制 ROM 通常会在标准的三个命名空间之外添加自定义设置项。这些设置项的权限控制完全由厂商决定，质量参差不齐。

```bash

adb shell settings list system | grep -i miui
adb shell settings list secure | grep -i miui
adb shell settings list global | grep -i miui
```

常见的厂商自定义设置项包括：

-   游戏模式开关
-   省电策略配置
-   手势导航设置
-   广告追踪 ID
-   云服务同步开关

这些设置项可能没有经过和 AOSP 标准设置项同等级别的安全审查。

* * *

## 5\. ContentProvider 层面的访问

### 5.1 直接通过 ContentResolver 访问

Settings API 底层是对 SettingsProvider 的 ContentResolver 调用。除了使用 `Settings.Secure.getString()` 等封装方法，也可以直接通过 ContentResolver 查询：

```java

Cursor cursor = getContentResolver().query(
    Uri.parse("content://settings/secure"),
    new String[]{"value"},
    "name=?",
    new String[]{"android_id"},
    null);
if (cursor != null && cursor.moveToFirst()) {
    String androidId = cursor.getString(0);
    cursor.close();
}
```

这种方式绕过了 Settings API 的封装，直接和 ContentProvider 交互。在某些情况下，通过 ContentResolver 可以访问到 Settings API 没有暴露的设置项。

### 5.2 call() 方法

SettingsProvider 还实现了 `call()` 方法，提供了另一种访问方式：

```java
Bundle result = getContentResolver().call(
    Uri.parse("content://settings/secure"),
    "GET_secure",      
    "android_id",      
    null);             
String value = result.getString("value");
```

`call()` 方法在第四章讲过，它不受标准的 query/insert/update/delete 权限模型约束，权限检查完全由 Provider 内部实现。SettingsProvider 的 `call()` 实现中对不同命名空间有不同的权限检查逻辑。

### 5.3 URI 格式

SettingsProvider 支持多种 URI 格式：

```php
content:
content:
content:
content:
content:
```

通过 ADB 的 `content` 命令可以直接查询：

```bash

adb shell content query --uri content://settings/secure/android_id


adb shell content query --uri content://settings/secure
```

* * *

## 6\. 版本演进

### 6.1 Android 6.0（API 23）：WRITE\_SETTINGS 改为特殊权限

Android 6.0 之前，`WRITE_SETTINGS` 是 normal 级别权限，任何 App 声明即可获得。Android 6.0 将其改为需要用户手动在设置页面中授权的特殊权限（类似 `SYSTEM_ALERT_WINDOW`）。

这个改动让第三方 App 修改 Settings.System 变得更难了，但用户仍然可能在不理解后果的情况下授权。

### 6.2 Android 8.0（API 26）：android\_id 按 App 隔离

Android 8.0 之前，所有 App 读取 `android_id` 得到的是同一个值，可以用于跨 App 追踪。Android 8.0 之后，`android_id` 的值按 App 签名密钥和用户组合生成，不同 App 看到不同的值。

### 6.3 Android 10（API 29）：限制设备标识符访问

Android 10 进一步限制了设备标识符的访问。`READ_PHONE_STATE` 权限不再允许读取 IMEI、序列号等硬件标识符，只有设备所有者（Device Owner）或运营商特权 App 才能访问。但 `android_id` 不受此限制，仍然可以通过 Settings.Secure 读取。

### 6.4 Android 13（API 33）：无障碍服务限制

Android 13 对通过 ADB 启用无障碍服务增加了限制。系统会检查目标服务是否已安装、是否在 Manifest 中正确声明了 `BIND_ACCESSIBILITY_SERVICE` 权限。这降低了通过 ADB 远程启用恶意无障碍服务的风险。

### 6.5 Android 15（API 35）：设置项访问收紧

Android 15 对部分 Settings.Secure 和 Settings.Global 的设置项增加了读取限制。某些之前任何 App 都能读取的设置项，现在需要特定权限。具体受限的设置项因版本而异，但趋势是逐步收紧读取权限。

* * *

## 7\. 总结

Settings Provider 的安全问题在于读写权限的不对称——写入有较严格的权限控制，但读取几乎完全开放。Settings.Secure 和 Settings.Global 中的设置项虽然名字带"Secure"和"Global"，但任何 App 都可以读取其中的内容。

回顾一下：

-   Settings.System 的写入权限（WRITE\_SETTINGS）在 Android 6.0 后需要用户手动授权
-   Settings.Secure 和 Settings.Global 的写入需要系统签名权限，但读取对所有 App 开放
-   android\_id、无障碍服务列表、通知监听列表等敏感信息可以被任何 App 读取
-   通过 ADB 可以读写所有命名空间，包括修改默认输入法和启用无障碍服务
-   厂商自定义设置项的权限控制质量参差不齐
-   Android 各版本在逐步收紧设置项的访问权限

下一章讲 Android SSRF 与网络安全。Android App 中的网络请求如果使用了用户可控的 URL，可能被利用来访问内网资源或本地服务，这就是 SSRF（Server-Side Request Forgery，服务端请求伪造）在移动端的变体。
