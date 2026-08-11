# Android移动安全第十三章_认证与证书校验
> QIANXIN Team
> 来源：https://forum.butian.net/share/4880

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
> 12.  Android 加密与数据存储安全
> 13.  Android 认证与证书校验（本章）
> 14.  Android Zip Slip 路径遍历
> 15.  Android Fragment Injection
> 16.  Android SELinux 与沙箱机制

* * *

## 1\. 前言

HTTPS 在 HTTP 的基础上加了一层 TLS（Transport Layer Security，传输层安全协议）。TLS 握手过程中，服务器会向客户端出示自己的数字证书，客户端验证这个证书是否由受信任的 CA（Certificate Authority，证书颁发机构）签发、是否过期、域名是否匹配。验证通过后，双方协商出一个对称加密密钥，后续通信用这个密钥加密。

如果客户端跳过了证书校验，TLS 握手仍然会完成，通信仍然是加密的——但客户端无法确认对方是谁。攻击者可以在客户端和服务器之间插入自己（中间人攻击，MITM），用自己的证书和客户端建立 TLS 连接，再用服务器的真实证书和服务器建立另一个 TLS 连接，两边都以为在和对方直接通信。

本章讲 Android App 中证书校验被绕过的各种方式，以及证书固定（Certificate Pinning）的实现和绕过。

* * *

## 2\. TLS 证书校验基础

### 2.1 证书链

TLS 证书通常不是由根 CA 直接签发的，而是通过一个证书链（Certificate Chain）：

```php
根 CA 证书（Root CA）
  └── 中间 CA 证书（Intermediate CA）
        └── 服务器证书（Server Certificate）
```

客户端验证时，从服务器证书开始，逐级向上验证签名，直到找到一个本地信任的根 CA 证书。Android 系统预装了一组受信任的根 CA 证书，存放在 `/system/etc/security/cacerts/` 目录下。

### 2.2 Android 的信任模型

Android 区分两类 CA 证书：

-   系统 CA：预装在系统分区中，所有 App 默认信任
-   用户 CA：用户手动安装的证书，存放在 `/data/misc/user/0/cacerts-added/`

不同 Android 版本对用户 CA 的信任策略不同：

| 版本 | 默认信任用户 CA |
| --- | --- |
| Android 6.0 及之前 | 是，所有 App 信任用户 CA |
| Android 7.0+（targetSdk >= 24） | 否，App 默认不信任用户 CA |
| Android 7.0+（targetSdk < 24） | 是，仍然信任用户 CA |

Android 7.0 的这个改动对安全审计有直接影响——要用 Burp Suite、mitmproxy 等工具抓包，需要把代理的 CA 证书安装为系统 CA（需要 root），或者修改 App 的 Network Security Config 让它信任用户 CA。

* * *

## 3\. 禁用证书校验

### 3.1 自定义 TrustManager

最常见的证书校验绕过方式是实现一个空的 TrustManager（信任管理器，Java 中负责验证服务器证书的接口）：

```java

TrustManager[] trustAllCerts = new TrustManager[]{
    new X509TrustManager() {
        @Override
        public void checkClientTrusted(X509Certificate[] chain, String authType) {
            
        }

        @Override
        public void checkServerTrusted(X509Certificate[] chain, String authType) {
            
        }

        @Override
        public X509Certificate[] getAcceptedIssuers() {
            return new X509Certificate[0];
        }
    }
};

SSLContext sslContext = SSLContext.getInstance("TLS");
sslContext.init(null, trustAllCerts, new SecureRandom());


HttpsURLConnection.setDefaultSSLSocketFactory(sslContext.getSocketFactory());
```

`checkServerTrusted()` 方法是证书校验的核心。如果这个方法的实现是空的（不抛出 CertificateException），就意味着接受任何证书，包括攻击者自签名的证书。

这种代码通常是开发阶段为了方便调试（跳过证书校验可以用自签名证书的测试服务器）而加的，但忘了在发布前移除。

### 3.2 自定义 HostnameVerifier

除了证书本身的校验，TLS 还需要验证证书中的域名是否和请求的域名匹配。HostnameVerifier（主机名验证器）负责这个检查：

```java

HostnameVerifier allHostsValid = (hostname, session) -> true;
HttpsURLConnection.setDefaultHostnameVerifier(allHostsValid);
```

即使证书校验是正常的，如果 HostnameVerifier 返回 true，攻击者可以用任何有效域名的证书（比如 `attacker.com` 的合法证书）来冒充目标服务器。

### 3.3 OkHttp 中的禁用

OkHttp 是 Android 中最常用的 HTTP 客户端库。在 OkHttp 中禁用证书校验：

```java

OkHttpClient client = new OkHttpClient.Builder()
    .sslSocketFactory(trustAllSslSocketFactory, trustAllCerts[0])
    .hostnameVerifier((hostname, session) -> true)
    .build();
```

一些第三方库或 SDK 可能在内部创建了自己的 OkHttpClient 实例并禁用了证书校验，App 开发者可能不知道自己引入的依赖中存在这个问题。

### 3.4 WebView 中的禁用

WebView 加载 HTTPS 页面时遇到证书错误会回调 `onReceivedSslError()`。默认行为是取消加载，但开发者可以选择忽略错误继续加载：

```java
webView.setWebViewClient(new WebViewClient() {
    @Override
    public void onReceivedSslError(WebView view, SslErrorHandler handler,
            SslError error) {
        handler.proceed();  
    }
});
```

Google Play 的审核会检测这种模式，如果 App 中存在无条件调用 `handler.proceed()` 的代码，可能会被拒绝上架。但非 Google Play 渠道分发的 App（如厂商预装 App、企业内部 App）不受此限制。

* * *

## 4\. 证书固定

### 4.1 概念

标准的证书校验依赖 CA 信任链——只要证书是由系统信任的 CA 签发的，就接受。但 CA 体系本身存在风险：如果某个 CA 被入侵或被政府强制签发证书，攻击者就能获得任何域名的合法证书。

证书固定（Certificate Pinning）是在 CA 信任链之上增加的一层校验：App 在代码或配置中预先指定服务器证书的公钥哈希（pin），连接时不仅验证 CA 信任链，还验证服务器证书的公钥是否匹配预设的 pin。即使攻击者拿到了 CA 签发的合法证书，只要公钥不匹配，连接就会被拒绝。

### 4.2 OkHttp 实现

OkHttp 内置了证书固定支持：

```java
CertificatePinner pinner = new CertificatePinner.Builder()
    .add("api.example.com",
        "sha256/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=")  
    .add("api.example.com",
        "sha256/BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB=")  
    .build();

OkHttpClient client = new OkHttpClient.Builder()
    .certificatePinner(pinner)
    .build();
```

pin 的值是证书公钥的 SHA-256 哈希的 Base64 编码。可以通过 openssl 命令获取：

```bash
openssl s_client -connect api.example.com:443 -servername api.example.com \
    < /dev/null 2>/dev/null | \
    openssl x509 -pubkey -noout | \
    openssl pkey -pubin -outform der | \
    openssl dgst -sha256 -binary | \
    openssl enc -base64
```

### 4.3 Network Security Config 实现

第十一章提到的 Network Security Config 也支持证书固定：

```xml
<network-security-config>
    <domain-config>
        <domain includeSubdomains="true">api.example.com</domain>
        <pin-set expiration="2026-01-01">
            <pin digest="SHA-256">AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=</pin>
            <pin digest="SHA-256">BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB=</pin>
        </pin-set>
    </domain-config>
</network-security-config>
```

Network Security Config 的证书固定有一个 `expiration` 属性。过期后固定失效，回退到标准的 CA 信任链校验。这是为了防止 App 长期不更新导致证书轮换后无法连接。

### 4.4 固定的层级

证书固定可以固定证书链中不同层级的证书：

| 固定层级 | 优点 | 缺点 |
| --- | --- | --- |
| 叶子证书（服务器证书） | 最严格，只接受特定证书 | 证书续期后必须更新 App |
| 中间 CA 证书 | 允许同一 CA 签发的新证书 | CA 更换后需要更新 |
| 根 CA 证书 | 最宽松，允许该 CA 签发的所有证书 | 安全性较低 |

实际中通常固定中间 CA 或叶子证书，并配置至少一个备份 pin（对应备用证书或备用 CA），防止主证书出问题时 App 完全无法连接。

* * *

## 5\. 证书固定的绕过

### 5.1 Frida / Xposed Hook

在 root 设备上，可以使用 Frida（一个动态代码注入框架，可以在运行时修改 App 的行为）或 Xposed（一个 Android 系统级的 Hook 框架）来绕过证书固定。

Frida 的常见做法是 Hook `TrustManager.checkServerTrusted()` 和 `CertificatePinner.check()` 方法，让它们直接返回而不抛出异常：

```javascript

Java.perform(function() {
    var CertificatePinner = Java.use('okhttp3.CertificatePinner');
    CertificatePinner.check.overload('java.lang.String', 'java.util.List')
        .implementation = function(hostname, peerCertificates) {
            
            return;
        };
});
```

社区维护的 `frida-ssl-pinning-bypass` 和 `objection` 工具集成了常见网络库的证书固定绕过脚本，覆盖了 OkHttp、HttpsURLConnection、Volley、Retrofit 等。

### 5.2 重打包

不需要 root 的绕过方式是重打包 APK：

1.  反编译 APK（使用 apktool）
2.  修改 Network Security Config，添加信任用户 CA 的配置
3.  或者修改 smali 代码，将证书固定的检查逻辑替换为空实现
4.  重新打包并签名

```xml

<network-security-config>
    <base-config>
        <trust-anchors>
            <certificates src="system" />
            <certificates src="user" />  
        </trust-anchors>
    </base-config>
</network-security-config>
```

这种方式的限制是：如果服务器端做了签名校验（检查 App 的签名证书是否和预期一致），重打包后的 App 签名会变化，可能被服务器拒绝。

### 5.3 Magisk 模块

在 root 设备上，可以通过 Magisk 模块将代理的 CA 证书注入到系统 CA 目录中，而不需要修改 App。这样 App 看到的是一个"系统级"的 CA 证书，标准的证书校验会通过。但证书固定仍然会阻止连接，因为固定检查的是公钥哈希而不是 CA 信任链。

* * *

## 6\. 客户端证书

### 6.1 双向 TLS

标准的 TLS 是单向认证——客户端验证服务器的身份。双向 TLS（mTLS，mutual TLS）在此基础上增加了服务器验证客户端身份的步骤：客户端也需要向服务器出示自己的证书。

```java

KeyStore clientKeyStore = KeyStore.getInstance("PKCS12");
clientKeyStore.load(getAssets().open("client.p12"), "password".toCharArray());

KeyManagerFactory kmf = KeyManagerFactory.getInstance(
    KeyManagerFactory.getDefaultAlgorithm());
kmf.init(clientKeyStore, "password".toCharArray());

SSLContext sslContext = SSLContext.getInstance("TLS");
sslContext.init(kmf.getKeyManagers(), null, null);
```

### 6.2 客户端证书的安全问题

客户端证书通常打包在 APK 的 `assets/` 或 `res/raw/` 目录中，密码硬编码在代码里。反编译 APK 后可以提取证书和密码：

```bash

unzip app.apk -d extracted/
ls extracted/assets/*.p12
ls extracted/res/raw/*.bks
```

提取到客户端证书后，攻击者可以用它来冒充合法客户端和服务器通信。

更安全的做法是将客户端证书存储在 Android KeyStore 中（第十二章讲过），而不是打包在 APK 里。但这需要一个安全的证书分发机制（如首次登录时从服务器下载并导入 KeyStore）。

* * *

## 7\. 版本演进

### 7.1 Android 7.0（API 24）：Network Security Config

引入了 Network Security Config，允许 App 以声明式方式配置网络安全策略。同时，targetSdk >= 24 的 App 默认不信任用户安装的 CA 证书。

### 7.2 Android 8.0（API 26）：SSLSocket 默认行为变化

Android 8.0 修改了 `SSLSocket` 的默认行为，禁用了 SSLv3 和一些弱密码套件。同时，`HttpsURLConnection` 默认使用 SNI（Server Name Indication，服务器名称指示，TLS 扩展，允许客户端在握手时告知服务器自己要访问的域名）。

### 7.3 Android 9.0（API 28）：默认禁止明文流量

第十一章讲过，targetSdk >= 28 的 App 默认禁止明文 HTTP 流量。

### 7.4 Android 10（API 29）：TLS 1.3 默认启用

Android 10 默认启用了 TLS 1.3。TLS 1.3 相比 1.2 减少了握手往返次数，移除了不安全的密码套件，整体安全性更高。

### 7.5 Android 14（API 34）：系统 CA 证书更新

Android 14 将系统 CA 证书的更新从系统 OTA 升级中分离出来，通过 Google Play 系统更新（Mainline 模块）独立更新。这意味着 CA 证书可以更快地被添加或撤销，不需要等待设备厂商推送系统更新。

* * *

## 8\. 总结

证书校验是 HTTPS 安全的基础。禁用证书校验等于把 HTTPS 降级为明文通信——数据仍然是加密的，但攻击者可以在中间解密、查看、篡改后再加密转发。

回顾一下：

-   空的 TrustManager 和返回 true 的 HostnameVerifier 是最常见的证书校验绕过
-   WebView 的 `onReceivedSslError` 中调用 `handler.proceed()` 同样危险
-   Android 7.0 之后 App 默认不信任用户 CA，提高了中间人攻击的门槛
-   证书固定在 CA 信任链之上增加了公钥哈希校验，可以通过 OkHttp 或 Network Security Config 实现
-   Frida Hook 和 APK 重打包是绕过证书固定的常用手段
-   客户端证书打包在 APK 中可以被提取，应该使用 KeyStore 存储

下一章讲 Android Zip Slip 路径遍历。App 解压 ZIP 文件时如果不校验文件名中的 `../`，可能导致文件被写入沙箱外的任意位置。
