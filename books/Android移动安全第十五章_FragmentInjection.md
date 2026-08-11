# Android移动安全第十五章_FragmentInjection
> QIANXIN Team
> 来源：https://forum.butian.net/share/4946

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
> 13.  Android 认证与证书校验
> 14.  Android Zip Slip 路径遍历
> 15.  Android Fragment Injection（本章）
> 16.  Android SELinux 与沙箱机制

* * *

## 1\. 前言

Fragment 是 Android 3.0（API 11）引入的 UI 组件。一个 Activity 可以包含多个 Fragment，每个 Fragment 管理自己的布局和生命周期。典型的使用场景是设置页面——左侧是分类列表，右侧根据选择加载不同的 Fragment 显示对应的设置项。

Android 提供了 PreferenceActivity 来简化设置页面的开发。PreferenceActivity 支持通过 Intent 的 extra 参数指定要加载的 Fragment 类名：

```java
Intent intent = new Intent(this, SettingsActivity.class);
intent.putExtra(":android:show_fragment", "com.example.NetworkSettingsFragment");
startActivity(intent);
```

PreferenceActivity 收到这个 Intent 后，会用反射实例化指定的 Fragment 并显示。问题在于，如果 SettingsActivity 是导出的（设置页面通常需要导出，因为系统设置、快捷方式等需要跳转到它），外部 App 也可以通过这个参数指定任意 Fragment 类名。

* * *

## 2\. 漏洞原理

### 2.1 PreferenceActivity 的 Fragment 加载机制

PreferenceActivity 在 `onCreate()` 中检查 Intent 是否包含 `:android:show_fragment` 这个 extra。如果有，就调用 `Fragment.instantiate()` 用反射创建该 Fragment 实例并加载到界面中：

```java

String fragmentName = intent.getStringExtra(":android:show_fragment");
if (fragmentName != null) {
    Bundle args = intent.getBundleExtra(":android:show_fragment_args");
    Fragment f = Fragment.instantiate(this, fragmentName, args);
    getFragmentManager().beginTransaction()
        .replace(android.R.id.content, f)
        .commit();
}
```

`Fragment.instantiate()` 内部用 `Class.forName(fragmentName)` 加载类，然后调用无参构造函数创建实例。只要类名存在于 App 的 ClassLoader 中，就能被实例化。

### 2.2 攻击效果

App 内部可能有一些 Fragment 不打算对外暴露，比如：

-   调试信息 Fragment（显示内部日志、设备信息）
-   账户管理 Fragment（修改密码、绑定手机号）
-   高级设置 Fragment（开发者选项、隐藏功能开关）
-   数据导出 Fragment（导出用户数据）

这些 Fragment 本身没有导出的概念（Fragment 不是四大组件，不在 Manifest 中声明），它们的访问控制完全依赖于宿主 Activity。如果宿主 Activity 是导出的 PreferenceActivity，且没有校验 Fragment 类名，攻击者就能加载这些内部 Fragment。

攻击命令：

```bash
adb shell am start -n com.target.app/.SettingsActivity \
    --es ":android:show_fragment" "com.target.app.internal.DebugFragment"
```

### 2.3 Fragment 参数注入

除了 `:android:show_fragment`，PreferenceActivity 还支持 `:android:show_fragment_args` 参数，用于向 Fragment 传递 Bundle 参数。Fragment 通过 `getArguments()` 获取这些参数：

```java
public class DataExportFragment extends Fragment {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        Bundle args = getArguments();
        if (args != null) {
            String exportPath = args.getString("export_path");
            
        }
    }
}
```

攻击者不仅能指定加载哪个 Fragment，还能控制传给 Fragment 的参数。

* * *

## 3\. isValidFragment() 校验

### 3.1 Android 4.4 的修复

这个漏洞在 2013 年被公开（CVE-2014-1710 是其中一个相关编号）。Android 4.4（API 19）在 PreferenceActivity 中添加了 `isValidFragment()` 方法作为修复：

```java

protected boolean isValidFragment(String fragmentName) {
    
    if (getApplicationInfo().targetSdkVersion >= Build.VERSION_CODES.KITKAT) {
        throw new RuntimeException(
            "Subclasses of PreferenceActivity must override isValidFragment(String)"
            + " to verify that the Fragment class is valid!"
            + " " + this.getClass().getName()
            + " has not checked if fragment " + fragmentName + " is valid.");
    }
    return true;
}
```

PreferenceActivity 在加载 Fragment 之前会调用 `isValidFragment(fragmentName)`。如果 App 的 targetSdk >= 19，默认实现直接抛异常，强制开发者重写这个方法来校验 Fragment 类名。

### 3.2 正确的重写方式

```java
public class SettingsActivity extends PreferenceActivity {
    @Override
    protected boolean isValidFragment(String fragmentName) {
        return GeneralSettingsFragment.class.getName().equals(fragmentName)
            || NetworkSettingsFragment.class.getName().equals(fragmentName)
            || DisplaySettingsFragment.class.getName().equals(fragmentName);
    }
}
```

白名单方式——只允许加载预期的 Fragment 类。

### 3.3 常见的错误实现

实际审计中，经常看到开发者为了消除异常而直接返回 true：

```java
@Override
protected boolean isValidFragment(String fragmentName) {
    return true;  
}
```

或者用包名前缀做粗粒度校验：

```java
@Override
protected boolean isValidFragment(String fragmentName) {
    return fragmentName.startsWith("com.example.settings.");
    
    
}
```

这两种写法都没有真正解决问题。

* * *

## 4\. 不依赖 PreferenceActivity 的 Fragment Injection

### 4.1 自定义的 Fragment 加载逻辑

不只是 PreferenceActivity，任何根据外部输入动态加载 Fragment 的代码都可能存在 Fragment Injection：

```java

public class ContainerActivity extends Activity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_container);

        String fragmentClass = getIntent().getStringExtra("fragment_class");
        if (fragmentClass != null) {
            Fragment f = Fragment.instantiate(this, fragmentClass);
            getFragmentManager().beginTransaction()
                .replace(R.id.container, f)
                .commit();
        }
    }
}
```

如果 ContainerActivity 是导出的，攻击者可以通过 `fragment_class` 参数加载任意 Fragment。

### 4.2 通过 Deep Link 触发

第七章讲过 Deep Link 的安全问题。如果 App 的 Deep Link 处理逻辑中包含 Fragment 加载：

```java

Uri uri = getIntent().getData();
String fragmentName = uri.getQueryParameter("fragment");
if (fragmentName != null) {
    Fragment f = Fragment.instantiate(this, fragmentName);
    
}
```

攻击者可以构造恶意链接诱导用户点击，触发 Fragment Injection。

### 4.3 AndroidX Navigation 组件

使用 AndroidX Navigation 组件的 App，如果 NavGraph 中的 deep link 配置不当，也可能导致类似问题。Navigation 组件根据 URI 匹配 destination（目标 Fragment），如果 URI 模式过于宽泛：

```xml
<fragment
    android:id="@+id/settingsFragment"
    android:name="com.example.SettingsFragment">
    <deepLink app:uri="myapp://fragment/{name}" />
</fragment>
```

这里 `{name}` 是路径参数，传给 Fragment 作为 argument。虽然 Navigation 组件不会根据参数动态切换 Fragment 类（destination 是固定的），但参数值仍然是攻击者可控的，可能影响 Fragment 内部逻辑。

* * *

## 5\. 版本演进

| 版本 | 变化 |
| --- | --- |
| Android 3.0 (API 11) | 引入 Fragment 和 PreferenceActivity 的 Fragment 加载机制 |
| Android 4.4 (API 19) | 添加 isValidFragment()，targetSdk >= 19 时默认抛异常 |
| Android 9.0 (API 28) | PreferenceActivity 被标记为 deprecated，推荐使用 AndroidX Preference |
| Android 13+ | AndroidX PreferenceFragmentCompat 成为主流，不存在 isValidFragment 问题 |

Android 4.4 的修复覆盖了 PreferenceActivity 的场景，但自定义的 Fragment 加载逻辑不受此保护。随着 AndroidX Preference 库的普及，PreferenceActivity 的使用在减少，但老应用和系统预装 App 中仍然常见。

AndroidX 的 PreferenceFragmentCompat 不使用 `:android:show_fragment` 机制，Fragment 的加载由 NavGraph 或代码显式控制，从架构上避免了这个问题。

* * *

## 6\. 总结

Fragment Injection 的本质是信任了外部输入的类名。PreferenceActivity 的 `:android:show_fragment` 参数是最经典的入口，但任何根据外部输入动态实例化 Fragment 的代码都有同样的风险。

回顾一下：

-   PreferenceActivity 根据 Intent extra 中的类名用反射加载 Fragment
-   Android 4.4 添加了 isValidFragment() 校验，但开发者可能直接返回 true
-   自定义的 Fragment 加载逻辑不受 isValidFragment() 保护
-   Fragment 没有独立的导出控制，访问控制完全依赖宿主 Activity

下一章讲 Android SELinux 与沙箱机制。SELinux 是 Linux 内核的强制访问控制模块，Android 从 4.3 开始引入，用于限制进程的权限范围。即使 App 获得了 root 权限，SELinux 策略仍然可以阻止它访问特定资源。
