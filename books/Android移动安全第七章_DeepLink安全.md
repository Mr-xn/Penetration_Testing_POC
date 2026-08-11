# Android移动安全第七章_DeepLink安全
> QIANXIN Team
> 来源：https://forum.butian.net/share/4874

> 系列目录：
> 
> 1.  Android 组件导出安全
> 2.  Android Intent 安全
> 3.  Android Binder 服务安全
> 4.  Android ContentProvider 安全
> 5.  Android WebView 安全
> 6.  Android UI 欺骗与钓鱼
> 7.  Android Deep Link 安全（本章）
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

用户在浏览器中点击一个链接，直接跳转到了某个 App 的特定页面——这就是 Deep Link（深度链接）。它让 Web 和 App 之间建立了连接，用户不需要手动打开 App 再找到对应功能。

Android 上实现 Deep Link 有三种方式：

-   自定义 Scheme（如 `myapp://`）：最早的方式，任何 App 都可以注册任意 scheme
-   Intent URL（如 `intent://`）：第二章讲过，通过 URL 编码一个完整的 Intent
-   App Links（如 `https://example.com/path`）：Android 6.0 引入，通过域名验证确保只有域名所有者的 App 能处理对应 URL

三种方式的安全性差异很大。自定义 Scheme 没有任何归属验证，任何 App 都可以声称自己能处理 `myapp://`；App Links 通过域名验证建立了 URL 和 App 之间的绑定关系，安全性高得多。

本章围绕 Deep Link 的注册机制、参数处理、以及链接劫持展开。

* * *

## 2\. 自定义 Scheme

### 2.1 注册方式

App 通过在 Manifest 中声明 intent-filter 来注册自定义 Scheme：

```xml
<activity
    android:name=".DeepLinkActivity"
    android:exported="true">
    <intent-filter>
        <action android:name="android.intent.action.VIEW" />
        <category android:name="android.intent.category.DEFAULT" />
        <category android:name="android.intent.category.BROWSABLE" />
        <data android:scheme="myapp" android:host="open" />
    </intent-filter>
</activity>
```

`BROWSABLE` category 表示这个 Activity 可以从浏览器中被唤起。注册后，用户在浏览器中点击 `myapp://open/path?key=value` 就会启动这个 Activity。

Activity 中通过 `getIntent().getData()` 获取 URL：

```java
@Override
protected void onCreate(Bundle savedInstanceState) {
    super.onCreate(savedInstanceState);
    Uri uri = getIntent().getData();
    if (uri != null) {
        String path = uri.getPath();           
        String key = uri.getQueryParameter("key"); 
    }
}
```

### 2.2 Scheme 劫持

自定义 Scheme 没有归属验证。如果两个 App 注册了相同的 scheme，系统会弹出选择器让用户选择由哪个 App 处理。攻击者可以注册与目标 App 相同的 scheme：

```xml

<activity
    android:name=".HijackActivity"
    android:exported="true">
    <intent-filter>
        <action android:name="android.intent.action.VIEW" />
        <category android:name="android.intent.category.DEFAULT" />
        <category android:name="android.intent.category.BROWSABLE" />
        <data android:scheme="myapp" android:host="open" />
    </intent-filter>
</activity>
```

如果用户选择了攻击者的 App，URL 中携带的参数（可能包含 token、回调地址等）就被攻击者获取了。

在某些 Android 版本和厂商 ROM 上，如果只有一个 App 注册了某个 scheme，系统会直接跳转而不弹选择器。攻击者安装自己的 App 后，系统开始弹选择器，用户可能不会注意到多了一个选项。

### 2.3 OAuth 回调劫持

很多 App 使用 OAuth（开放授权协议，允许用户授权第三方 App 访问自己在某个服务上的数据，而不需要提供密码）进行第三方登录。OAuth 流程中，授权服务器会把授权码（authorization code）通过重定向发送到 App 注册的回调 URL。

如果回调 URL 使用自定义 Scheme（如 `myapp://oauth/callback?code=xxx`），攻击者注册相同的 scheme 就能截获授权码：

1.  用户在目标 App 中发起 OAuth 登录
2.  浏览器跳转到授权服务器，用户授权
3.  授权服务器重定向到 `myapp://oauth/callback?code=AUTH_CODE`
4.  系统弹出选择器，如果用户选择了攻击者的 App，授权码被截获
5.  攻击者用授权码换取 access token，获得用户账户的访问权限

这是自定义 Scheme 最常见的实际攻击场景。

* * *

## 3\. App Links

### 3.1 原理

App Links 是 Android 6.0（API 23）引入的，用于解决自定义 Scheme 的归属验证问题。它使用标准的 `https://` URL，通过域名验证确保只有域名所有者的 App 能处理对应 URL。

注册方式：

```xml
<activity
    android:name=".AppLinkActivity"
    android:exported="true">
    <intent-filter android:autoVerify="true">
        <action android:name="android.intent.action.VIEW" />
        <category android:name="android.intent.category.DEFAULT" />
        <category android:name="android.intent.category.BROWSABLE" />
        <data android:scheme="https" android:host="example.com" android:pathPrefix="/app" />
    </intent-filter>
</activity>
```

`android:autoVerify="true"` 告诉系统在安装时验证域名归属。验证方式是：系统访问 `https://example.com/.well-known/assetlinks.json`，检查其中是否声明了当前 App 的包名和签名证书。

assetlinks.json 的内容：

```json
[{
    "relation": ["delegate_permission/common.handle_all_urls"],
    "target": {
        "namespace": "android_app",
        "package_name": "com.example.app",
        "sha256_cert_fingerprints": ["AB:CD:EF:..."]
    }
}]
```

验证通过后，用户点击 `https://example.com/app/xxx` 会直接跳转到 App，不弹选择器，其他 App 无法劫持。

### 3.2 验证失败的情况

App Links 的验证可能失败：

-   服务器没有部署 assetlinks.json
-   assetlinks.json 中的包名或证书指纹不匹配
-   服务器返回非 200 状态码
-   网络不可用（安装时无法访问服务器）

验证失败后，App Links 退化为普通的 Deep Link——系统会弹出选择器，和自定义 Scheme 一样存在劫持风险。

### 3.3 验证状态检查

可以通过 ADB 检查 App Links 的验证状态：

```bash
adb shell pm get-app-links com.example.app
```

输出中 `verified` 表示验证通过，`none` 表示未验证。

* * *

## 4\. Deep Link 参数注入

### 4.1 URL 参数直接使用

很多 App 从 Deep Link URL 中读取参数后直接使用，没有做校验。常见的危险模式：

#### 加载到 WebView

```java
Uri uri = getIntent().getData();
String url = uri.getQueryParameter("url");
webView.loadUrl(url);  
```

攻击者构造 `myapp://open?url=https://evil.com`，App 的 WebView 加载攻击者的页面。第五章讲过，如果 WebView 注册了 JS Bridge，攻击者的页面就能调用 App 的原生方法。

#### 跳转到内部组件

```java
Uri uri = getIntent().getData();
String target = uri.getQueryParameter("target");
Intent intent = new Intent();
intent.setClassName(getPackageName(), target);
startActivity(intent);  
```

攻击者构造 `myapp://open?target=com.example.app.InternalActivity`，绕过 exported=false 限制启动内部组件。这和第二章讲的 Intent 重定向本质相同，只是入口从 Intent extras 变成了 URL 参数。

#### 拼接到 SQL 或文件路径

```java
String id = uri.getQueryParameter("id");
Cursor cursor = db.rawQuery("SELECT * FROM users WHERE id = " + id, null);
```

和第四章讲的 ContentProvider SQL 注入类似，只是注入点从 ContentResolver 参数变成了 URL 参数。

### 4.2 演示

演示 App（com.demo.deeplinksecurity）的 VulnDeepLinkActivity 注册了 `demoapp://` scheme，从 URL 参数中读取 `action` 和 `url`，根据 action 执行不同操作：

-   `action=webview`：把 url 参数加载到 WebView
-   `action=navigate`：把 target 参数作为组件名跳转

```bash

adb shell am start -a android.intent.action.VIEW \
    -d "demoapp://open?action=webview\&url=https://example.com"
```

App 的 WebView 加载了攻击者指定的 URL：

![demo7_deeplink_webview.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/04/attach-903b4e474aec425539fa958d725360a0598eca6d.png)

```bash

adb shell am start -a android.intent.action.VIEW \
    -d "demoapp://open?action=navigate\&target=com.demo.deeplinksecurity.InternalSecretActivity"
```

绕过 exported=false 限制，启动了内部页面：

## ![demo7_deeplink_navigate.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/04/attach-478f000250c116de370b5da2e80692499dfba7df.png)

## 5\. Deep Link 与 Intent 的交互

### 5.1 getIntent().getData() 的来源

Activity 通过 `getIntent().getData()` 获取 Deep Link URL。但这个 Intent 不一定来自浏览器——任何 App 都可以构造一个带 data 的 Intent 发送给导出的 Activity：

```java

Intent intent = new Intent(Intent.ACTION_VIEW);
intent.setData(Uri.parse("myapp://open?token=stolen"));
intent.setPackage("com.target.app");
startActivity(intent);
```

这意味着即使 Deep Link 没有从浏览器触发，攻击者仍然可以通过 Intent 直接传入恶意 URL。所以 Deep Link 的参数校验不能依赖"URL 来自可信的浏览器"这个假设。

### 5.2 intent:// URL 与 Deep Link 的结合

第二章讲过 intent:// URL 可以编码一个完整的 Intent。如果目标 App 的 WebView 支持 intent:// URL 处理，攻击者可以通过 Deep Link 先让 WebView 加载一个页面，页面中再通过 intent:// URL 触发更深层的攻击：

```php
demoapp:
```

exploit.html 中：

```html
<a href="intent://dummy#Intent;component=com.target.app/.InternalActivity;end">click</a>
```

这是一个两步攻击链：Deep Link → WebView → intent:// → 内部组件。

* * *

## 6\. 版本演进

### 6.1 Android 6.0（API 23）：App Links

引入 App Links，通过 assetlinks.json 验证域名归属。验证通过后直接跳转，不弹选择器。

### 6.2 Android 12（API 31）：App Links 行为变化

Android 12 对 App Links 做了调整：

-   未通过验证的 App Links 不再在选择器中显示，而是直接在浏览器中打开
-   用户可以在设置中手动管理每个 App 的链接处理行为
-   系统对 assetlinks.json 的验证更严格

这个改动提高了 App Links 的安全性，但也意味着如果 App 的 assetlinks.json 配置有问题，Deep Link 会完全失效（直接在浏览器打开而不是跳转到 App）。

### 6.3 Android 12：intent-filter 必须声明 exported

第一章提到过，Android 12 要求所有带 intent-filter 的组件必须显式声明 `android:exported`。Deep Link 的 Activity 必须设置 `exported="true"`，否则无法安装。这不是安全改进（Deep Link Activity 本来就需要导出），但让开发者更明确地意识到这些组件是对外暴露的。

* * *

## 7\. 总结

Deep Link 把 URL 变成了 App 的入口。

回顾一下：

-   自定义 Scheme 没有归属验证，任何 App 都可以注册相同的 scheme 进行劫持，OAuth 回调是常见的攻击目标
-   App Links 通过域名验证解决了劫持问题，但验证失败时会退化为普通 Deep Link
-   URL 参数直接传给 WebView、组件跳转、SQL 查询都是常见的注入点
-   Deep Link 的参数不能假设来自可信来源，因为任何 App 都可以通过 Intent 直接传入

下一章讲 Android 广播安全。广播是 Android 的事件通知机制，第一章简单提过广播注入和劫持，下一章会深入展开——有序广播的优先级劫持、Sticky 广播的数据残留、以及 LocalBroadcastManager 的使用场景。

通过网盘分享的文件：deeplink安全演示.apk  
链接: [https://pan.baidu.com/s/1OhxiQyFIazUmphxxBB3svA?pwd=95yg](https://pan.baidu.com/s/1OhxiQyFIazUmphxxBB3svA?pwd=95yg) 提取码: 95yg
