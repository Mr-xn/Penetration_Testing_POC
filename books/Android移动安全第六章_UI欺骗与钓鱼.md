# Android移动安全第六章_UI欺骗与钓鱼
> QIANXIN Team
> 来源：https://forum.butian.net/share/4841

> 系列目录：
> 
> 1.  Android 组件导出安全
> 2.  Android Intent 安全
> 3.  Android Binder 服务安全
> 4.  Android ContentProvider 安全
> 5.  Android WebView 安全
> 6.  Android UI 欺骗与钓鱼（本章）
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

前几章讲的漏洞大多是"程序对程序"的——攻击者的 App 通过 Intent、ContentProvider、Binder 等机制与目标 App 交互，整个过程用户可能完全无感知。这一章不同，攻击目标是用户本人。

UI 欺骗的思路是：在用户面前显示一个伪造的界面，让用户以为自己在和合法 App 交互，实际上输入的密码、点击的按钮都被攻击者截获了。Android 上实现这个目标有几种方式：

-   利用导出组件注入 UI 内容（第一章演示过）
-   通过悬浮窗（Overlay）在其他 App 上方覆盖界面
-   利用任务栈（Task）机制把攻击者的 Activity 插入到目标 App 的任务中
-   通过 Toast 或自定义通知伪造系统提示

本章逐一展开。

* * *

## 2\. 导出组件的 UI 注入

第一章演示过，如果一个导出的 Activity 从 Intent extras 中读取字符串直接显示到 UI 上，攻击者可以注入任意内容。这里补充一些细节。

### 2.1 AlertDialog 注入

很多 App 用 AlertDialog（Android 提供的标准弹窗组件）显示提示信息。如果弹窗的标题和内容来自 Intent extras：

```java
public class NotifyActivity extends Activity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        String title = getIntent().getStringExtra("title");
        String message = getIntent().getStringExtra("message");

        new AlertDialog.Builder(this)
            .setTitle(title != null ? title : "通知")
            .setMessage(message != null ? message : "暂无内容")
            .setPositiveButton("确定", (d, w) -> finish())
            .show();
    }
}
```

攻击者可以伪造任何内容的弹窗。由于 AlertDialog 的样式和系统弹窗一致，用户很难区分这是 App 自身的提示还是外部注入的。

### 2.2 WebView 页面注入

第五章讲过，如果导出的 Activity 把 Intent 中的 URL 传给 WebView 加载，攻击者可以加载一个精心制作的钓鱼页面。这个页面运行在目标 App 的 WebView 中，地址栏不可见（WebView 默认不显示 URL），用户看到的就是目标 App 内嵌了一个"登录页面"。

这两种方式的前提都是目标 App 存在导出组件且接受外部输入，属于被动利用。下面讲的悬浮窗和任务栈劫持则是攻击者主动发起的。

* * *

## 3\. 悬浮窗覆盖（Overlay Attack）

### 3.1 原理

Android 允许 App 在其他应用上方显示内容，这个能力叫做"悬浮窗"或"Overlay"。常见的使用场景包括：聊天气泡、屏幕录制工具的控制按钮、来电显示等。

要使用悬浮窗，App 需要 `SYSTEM_ALERT_WINDOW` 权限。这个权限的获取方式随 Android 版本变化：

| Android 版本 | 获取方式 |
| --- | --- |
| < 6.0（API 23） | Manifest 声明即可，安装时自动授予 |
| 6.0 - 7.x | 需要用户手动在设置中开启"显示在其他应用上层" |
| 8.0+（API 26） | 同上，但新增了 TYPE_APPLICATION_OVERLAY 窗口类型 |
| 10+（API 29） | 同上，但系统会在状态栏显示"正在其他应用上层显示"的通知 |
| 12+（API 31） | 同上，限制更严格，某些场景下系统会自动隐藏 Overlay |

获得权限后，App 通过 WindowManager（Android 的窗口管理服务）添加一个 View，设置合适的窗口类型和标志位，就能在其他 App 上方显示内容：

```java
WindowManager wm = (WindowManager) getSystemService(WINDOW_SERVICE);
WindowManager.LayoutParams params = new WindowManager.LayoutParams(
    WindowManager.LayoutParams.MATCH_PARENT,
    WindowManager.LayoutParams.MATCH_PARENT,
    WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,  
    WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE,
    PixelFormat.TRANSLUCENT
);
wm.addView(overlayView, params);
```

### 3.2 攻击方式

#### 全屏覆盖

攻击者在目标 App 上方覆盖一个全屏的伪造界面。比如当用户打开银行 App 时，攻击者的 Overlay 显示一个一模一样的登录页面，用户输入的账号密码被攻击者截获。

这种方式需要攻击者知道用户当前在使用哪个 App。可以通过 `UsageStatsManager`（使用情况统计服务）或辅助功能（AccessibilityService）获取前台 App 信息。

#### 部分覆盖

只覆盖屏幕的一部分，比如在权限请求弹窗的"允许"按钮上方覆盖一个看起来无害的按钮（如"关闭广告"）。用户以为自己在关闭广告，实际上点击穿透到了下方的"允许"按钮，授予了攻击者请求的权限。

这种技术叫做 Tapjacking（点击劫持）。Android 提供了 `filterTouchesWhenObscured` 属性来防御——设置为 true 后，当 View 被其他窗口遮挡时会忽略触摸事件：

```xml
<Button
    android:layout_width="wrap_content"
    android:layout_height="wrap_content"
    android:filterTouchesWhenObscured="true" />
```

但这个属性需要开发者主动设置，很多 App 没有使用。

#### 透明覆盖

Overlay 可以设置为完全透明（`PixelFormat.TRANSLUCENT` + 透明背景），用户完全看不到它的存在。透明 Overlay 可以拦截触摸事件，记录用户的点击位置和滑动轨迹，用于推断用户输入的 PIN 码或手势密码。

### 3.3 演示

演示 App（com.demo.uispoof）的 OverlayDemoActivity 展示了悬浮窗覆盖的效果。启动后会请求 `SYSTEM_ALERT_WINDOW` 权限，授权后显示一个模拟的"系统安全验证"悬浮窗，覆盖在当前界面上方：

```bash
adb shell am start -n com.demo.uispoof/.OverlayDemoActivity
```

悬浮窗显示一个伪造的"系统安全验证"界面：

![demo6_overlay_active.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/03/attach-f14bedd42ce3a677092460148ba1593a7fea377e.png)

用户输入的内容会被记录到 logcat：

```bash
adb logcat -s OverlayDemo
```

* * *

## 4\. 任务栈劫持（Task Hijacking）

### 4.1 Android 任务栈机制

Android 用"任务栈"（Task）来组织 Activity。一个任务栈是一组 Activity 的堆叠，用户按返回键时从栈顶依次弹出。每个任务栈有一个 taskAffinity（任务亲和性），决定 Activity 属于哪个任务。

默认情况下，一个 App 的所有 Activity 共享同一个 taskAffinity（值为包名）。但开发者可以在 Manifest 中为 Activity 指定不同的 taskAffinity：

```xml
<activity
    android:name=".PaymentActivity"
    android:taskAffinity="com.bank.app" />
```

### 4.2 StrandHogg 攻击

StrandHogg 是 2019 年公开的一种任务栈劫持攻击。攻击者的 Activity 设置与目标 App 相同的 taskAffinity，配合 `allowTaskReparenting` 或 `FLAG_ACTIVITY_NEW_TASK`，可以把自己的 Activity 插入到目标 App 的任务栈中。

```xml

<activity
    android:name=".PhishingLoginActivity"
    android:taskAffinity="com.bank.app"
    android:allowTaskReparenting="true"
    android:exported="true" />
```

攻击流程：

1.  用户打开攻击者的 App（可能是一个看起来正常的工具类应用）
2.  攻击者的 PhishingLoginActivity 启动后，因为 taskAffinity 设置为 `com.bank.app`，系统把它放入银行 App 的任务栈
3.  用户切换到银行 App 时，看到的是攻击者的钓鱼登录页面（因为它在栈顶）
4.  用户输入账号密码，被攻击者截获

### 4.3 StrandHogg 2.0

2020 年公开的 StrandHogg 2.0（CVE-2020-0096）更进一步，不需要设置 taskAffinity，而是利用 `startActivities()` 方法的行为：攻击者可以在启动目标 App 的 Activity 之前，先把自己的 Activity 压入栈中。

这个漏洞在 Android 9 及以下版本有效，Android 10 修复了。

### 4.4 演示

演示 App 的 TaskHijackActivity 设置了与自身不同的 taskAffinity 来模拟任务栈劫持。启动后会显示一个伪造的登录页面，模拟用户切换 App 时看到钓鱼界面的场景：

```bash
adb shell am start -n com.demo.uispoof/.TaskHijackActivity
```

伪造的银行登录页面：

![demo6_task_hijack.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/03/attach-589b79f688e2f969cf073f11fa1d2f7ba1cdb8c1.png)

* * *

## 5\. Toast 与通知伪造

### 5.1 Toast 伪造

Toast 是 Android 的轻量级提示组件，显示在屏幕底部，几秒后自动消失。在 Android 11 之前，App 可以自定义 Toast 的布局，显示任意内容：

```java
Toast toast = new Toast(context);
toast.setView(customView);  
toast.setDuration(Toast.LENGTH_LONG);
toast.setGravity(Gravity.CENTER, 0, 0);  
toast.show();
```

攻击者可以用自定义 Toast 模拟系统提示，比如"您的设备已被感染，请立即安装安全补丁"，引导用户下载恶意 App。

Android 11（API 30）开始，系统禁止了自定义 Toast 布局（`setView()` 被废弃），只允许使用标准的文本 Toast。这个改动基本消除了 Toast 伪造的风险。

### 5.2 通知伪造

通知（Notification）也可以用于 UI 欺骗。攻击者可以发送一条看起来像系统通知的消息，比如模拟"系统更新"或"安全警告"，点击后跳转到钓鱼页面。

通知的图标、标题、内容都由 App 自行设置，用户很难区分是系统发的还是第三方 App 发的。Android 8.0 引入了通知渠道（Notification Channel），用户可以针对每个 App 的每个渠道单独控制通知行为，但这需要用户主动去设置。

* * *

## 6\. 辅助功能滥用（AccessibilityService）

### 6.1 原理

AccessibilityService（辅助功能服务）是 Android 为残障用户设计的，允许 App 监听和操作其他 App 的 UI 事件——读取屏幕内容、模拟点击、监听输入等。

要使用辅助功能，App 需要在 Manifest 中声明服务，用户需要在系统设置中手动开启：

```xml
<service
    android:name=".MyAccessibilityService"
    android:permission="android.permission.BIND_ACCESSIBILITY_SERVICE">
    <intent-filter>
        <action android:name="android.accessibilityservice.AccessibilityService" />
    </intent-filter>
    <meta-data
        android:name="android.accessibilityservice"
        android:resource="@xml/accessibility_config" />
</service>
```

一旦用户授权，辅助功能服务可以：

-   读取任何 App 的屏幕内容（包括输入框中的文字）
-   监听所有 UI 事件（点击、滚动、文字变化）
-   模拟用户操作（点击按钮、输入文字、滑动）
-   截取屏幕内容

### 6.2 攻击场景

辅助功能被恶意利用的场景：

| 场景 | 方式 | 危害 |
| --- | --- | --- |
| 键盘记录 | 监听 TYPE_VIEW_TEXT_CHANGED 事件 | 窃取密码、短信验证码 |
| 自动授权 | 检测到权限弹窗后模拟点击"允许" | 静默获取敏感权限 |
| 自动安装 | 在安装确认页面模拟点击"安装" | 静默安装恶意 App |
| 屏幕内容窃取 | 遍历 AccessibilityNodeInfo 树 | 读取任意 App 的显示内容 |

辅助功能的授权门槛比较高（需要用户手动在设置中开启），但恶意 App 通常会通过社会工程引导用户开启——比如伪装成"性能优化工具"或"电池管理器"，声称需要辅助功能权限才能正常工作。

### 6.3 Android 版本限制

| 版本 | 限制 |
| --- | --- |
| Android 8.0 | 辅助功能服务不能再获取指纹认证事件 |
| Android 10 | 限制辅助功能服务访问输入法窗口 |
| Android 11 | 辅助功能服务声明必须更具体（指定监听的事件类型和包名） |
| Android 13 | 侧载的 App 无法直接开启辅助功能，需要额外步骤 |

* * *

## 7\. 版本演进

### 7.1 Android 6.0（API 23）：SYSTEM\_ALERT\_WINDOW 需要手动授权

Android 6.0 之前，`SYSTEM_ALERT_WINDOW` 在 Manifest 中声明就自动授予。6.0 开始需要用户手动在设置中开启"显示在其他应用上层"。但通过 Google Play 安装的 App 在某些版本上会自动获得此权限。

### 7.2 Android 10（API 29）：Overlay 通知

Android 10 开始，当 App 使用悬浮窗时，系统会在状态栏显示一条持续通知，告知用户"某某 App 正在其他应用上层显示"。用户可以通过这条通知直接关闭悬浮窗权限。

### 7.3 Android 10：任务栈劫持修复

Android 10 修复了 StrandHogg 2.0 漏洞，限制了 `startActivities()` 的行为。但 StrandHogg 1.0（基于 taskAffinity）的利用在某些场景下仍然有效。

### 7.4 Android 11（API 30）：自定义 Toast 废弃

`Toast.setView()` 被废弃，后台 App 无法再显示自定义布局的 Toast。这基本消除了 Toast 伪造的攻击面。

### 7.5 Android 12（API 31）：Overlay 限制加强

Android 12 对悬浮窗做了进一步限制：

-   系统可以在某些场景下自动隐藏 Overlay（比如用户在进行敏感操作时）
-   `SYSTEM_ALERT_WINDOW` 权限的授予更加严格
-   不可信的触摸事件（来自 Overlay 的穿透点击）会被系统阻止

* * *

## 8\. 总结

UI 欺骗的攻击目标是用户而不是程序。

回顾一下：

-   导出组件的 UI 注入是被动利用，依赖目标 App 存在接受外部输入的导出 Activity
-   悬浮窗覆盖需要 SYSTEM\_ALERT\_WINDOW 权限，Android 10+ 会显示通知提醒用户，Android 12+ 限制更严格
-   任务栈劫持利用 taskAffinity 把钓鱼 Activity 插入目标 App 的任务中，StrandHogg 2.0 在 Android 10 被修复
-   辅助功能服务的能力很强（键盘记录、模拟点击、屏幕读取），但授权门槛也高，需要用户手动开启

下一章讲 Android Deep Link 安全。Deep Link 让 App 可以通过 URL 被唤起，这个机制和 WebView、Intent 都有交集——URL 解析、参数校验、组件跳转，每一步都可能出问题。

通过网盘分享的文件：ui欺骗演示.apk  
链接: [https://pan.baidu.com/s/1tc-tV2KH93xUomOR4XsmWA?pwd=vuvq](https://pan.baidu.com/s/1tc-tV2KH93xUomOR4XsmWA?pwd=vuvq) 提取码: vuvq
