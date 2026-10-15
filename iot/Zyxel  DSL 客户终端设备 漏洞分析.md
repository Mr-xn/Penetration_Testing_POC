# Zyxel  DSL 客户终端设备 漏洞分析
> Yy123
> 来源：https://www.iotsec-zone.com/article/494

# 前言

Zyxel 旗下部分旧款 DSL 客户终端设备(CPE)存在严重的安全漏洞，包括 默认凭证不安全问题 和 命令注入漏洞 ，攻击者可通过默认凭证登录 Telnet 并利用此漏洞在受影响的设备上执行任意命令。

影响型号：
VMG1312-B10A、VMG1312-B10B、VMG1312-B10E、VMG3312-B10A、VMG3313-B10A、VMG3926-B10B、VMG4325-B10A、VMG4380-B10A、VMG8324-B10A、VMG8924-B10A、SBG3300、SBG3500
# 0x1 CVE-2025-0890

描述：Zyxel VMG3312-B10A 固件版本 100AAEF4D3 中 Telnet 功能的不安全默认凭据可能允许攻击者登录管理界面。

默认凭证保存在 `/etc/default.cfg` 文件中，它是一个 XML 格式的 DSL CPE（Customer Premises Equipment）配置文件，包含了多种网络设置。
![0.png](https://www.iotsec-zone.com/api/image/v2/20250220/d7x4x8s1smsdrioco5.png)

查看并分析这个文件

![1.png](https://www.iotsec-zone.com/api/image/v2/20250220/d7x4xm5a2hzmzyzoth.png)
 
 **分析default.cfg得到**：
1. **管理员账户**：
    
    - **用户名**：`supervisor`
    - **密码**：`enlhZDEyMzQ=`
        - 这个密码是经过 Base64 编码的，解码后为：`zyad1234`。
2. **登录组（管理员组）**：
    
    - **用户名**：`admin`
    - **密码**：`MTIzNAA=`
        - 解码后的密码为：`1234`
3. **登录组（用户组）**：
    
    - **用户名**：`zyuser`
    - **密码**：`MTIzNAA=`
        - 解码后的密码为：`1234`
并且均拥有 `remoteMGMT` 远程管理功能，可以通过 `Telnet` 登录设备。

# 0x2  CVE-2024-40891

描述：Zyxel VMG3312-B10A 固件版本 100AAEF4D3 中的管理命令中存在身份验证后命令注入漏洞，可能允许经过身份验证的攻击者通过 Telnet 在受影响的设备上执行作系统 （OS） 命令。

我们进入`telnet`入口后分析如何触发命令注入漏洞。

![2.png](https://www.iotsec-zone.com/api/image/v2/20250220/d7x4xy8ykyifyy0wno.png)
`cmsDal_getNetworkAccessMode`用于检查客户端的网络访问权限，其函数定义在`lib/private/libcms_dal.so`，main通过`cmsDal_getNetworkAccessMode`后，由sub_4016c4判断是否创建`Telnet`会话。
![3.png](https://www.iotsec-zone.com/api/image/v2/20250220/d7x4y61pzhpg5yhc0r.png)
![4.png](https://www.iotsec-zone.com/api/image/v2/20250220/d7x4yfc1harpbu3cp6.png)
该函数作用是根据提供的 IP 地址（参数 `a2`）判断该地址位于局域网（LAN）还是广域网（WAN）侧。漏洞说明默认情况下禁止 `wan` 访问，所以漏洞利用前提是设备允许 `wan` 访问。

回到`telnetd`继续分析sub_4016C4函数
![5.png](https://www.iotsec-zone.com/api/image/v2/20250220/d7x4ym62neje5rb8lc.png)
该函数与创建和管理远程会话相关。它执行了一些网络通信、会话管理和子进程创建的关键操作。通过`cmsCli_authenticate`进行客户端身份验证，通过`cmsCli_run`启动命令交互环境。
![6.png](https://www.iotsec-zone.com/api/image/v2/20250220/d7x4yv5ulgqtlvfzw2.png)
![7.png](https://www.iotsec-zone.com/api/image/v2/20250220/d7x4z1tploqovzmr7f.png)
都定义在libcms_cli.so，进入IDA查看。

cmsCli_authenticate函数
![8.png](https://www.iotsec-zone.com/api/image/v2/20250220/d7x4za95xsgnw8h30d.png)
- 如果是 `unk_5A340` 用户，则权限为 `0x80`。为管理员账户`supervisor`
- 如果是 `unk_5A368` 用户，则权限为 `64`。为管理员组账户`admin`
- 如果是 `unk_5A390` 用户，则权限为 `1`。为用户组账户`zyuser`
- 否则，记录 `unrecognized user` 错误。

cmsCli_run函数
是核心执行函数，负责初始化资源、处理用户输入、执行命令并在最后进行资源清理和退出。
![9.png](https://www.iotsec-zone.com/api/image/v2/20250220/d7x4zm3jq060zg6spj.png)
通过调用sub_52A8()函数来执行

sub_52A8()函数
首先通过 `cmdedit_read_input` 读取用户输入的命令，输入命令有效，去掉换行符后，它会尝试处理命令，分别通过 `cli_processCliCmd` 和 `cli_processHiddenCmd` 来执行常规和隐藏命令。
![10.png](https://www.iotsec-zone.com/api/image/v2/20250220/d7x4zzepu29jakgidw.png)
分析`cli_processCliCmd`函数
它处理传入的命令并执行相关操作，关键在通过一个固定的数组 `off_6310C` 查找与 `v8` 相匹配的命令，遍历它的命令。
![11.png](https://www.iotsec-zone.com/api/image/v2/20250220/d7x50711uey7eryilm.png)
如果没有相匹配的命令处理函数，则使用 `prctl_runCommandInShellWithTimeout(v8)` 执行命令。
来看`prctl_runCommandInShellWithTimeout()`函数，此函数定义在`libcms_util.so`中
它通过调用 `sub_11560` 执行命令，并通过 `prctl_collectProcess` 收集进程信息
![12.png](https://www.iotsec-zone.com/api/image/v2/20250220/d7x50jbo4wt1xvjegl.png)
`sub_11560()`函数
```c
int __fastcall sub_11560(int a1)
{
  int i; // [sp+18h] [+18h]
  int v3; // [sp+1Ch] [+1Ch]
  int v4[4]; // [sp+20h] [+20h] BYREF

  v3 = fork();
  if ( v3 == -1 )
  {
    log_log(3, "runCommandInShell", 77, "fork failed!");
    return -1;
  }
  else
  {
    if ( !v3 )
    {
      for ( i = 3; i < 51; ++i )
        close(i);
      v4[0] = (int)"sh";
      v4[1] = (int)"-c";
      v4[2] = a1;
      v4[3] = 0;
      execv("/bin/sh", v4);
      log_log(3, "runCommandInShell", 98, "Should not have reached here!");
      exit(127);
    }
    return v3;
  }
}
```
通过 `fork` 和 `execv` 在子进程中执行用户提供的命令，但该函数没有筛选。因此，传递给`prctl_runCommandInShellWithTimeout()`容易受到命令注入的攻击。由于没有筛选，因此可以通过多种方式执行命令注入。如`tftp || sh`在 tftp指令执行失败后去执行sh。

## 漏洞验证
我们选择公网IP上该型号设备进行简单无危害验证
![13.png](https://www.iotsec-zone.com/api/image/v2/20250220/d7x50tzagq2841jp0j.png)

# 0x3 硬编码泄露（已提交cve）

描述：Zyxel VMG3312-B10A 固件版本 100AAEF4D3 sub_5398()函数中存在硬编码泄露。
我们根据default.cfg文件已经得知拥有 `remoteMGMT` 远程管理功能可以 `Telnet` 登录设备的账号密码。若不去通过身份验证后命令注入漏洞去执行命令，此时会回显一个“shell password”。
![14.png](https://www.iotsec-zone.com/api/image/v2/20250220/d7x516zfw1g6szk8ox.png)

回到sub_5398()函数中分析，若输入的正常命令，通过调用`cli_processHiddenCmd()`来处理命令。
![15.png](https://www.iotsec-zone.com/api/image/v2/20250220/d7x51ehldistggol7j.png)

我们可以看到又进行一次“shell password”的验证，注意strcpy(v12, "t/6RU6nc04");
首先v12存储了硬编码的正确密码，v13为大小为 16 字节的缓冲区，用于存储用户在认证尝试期间输入的密码，这个缓冲区会在用户输入时更新，v5用于临时存储 getpass获取到的用户密码，
我们直接尝试此硬编码。通过v12与v13比较进行验证登录，若密码错误，程序打印 `"Incorrect! Try again."` 提示信息。

![16.png](https://www.iotsec-zone.com/api/image/v2/20250220/d7x51mrordi617gkfx.png)
验证成功。
## 参考链接
[https://vulncheck.com/blog/zyxel-telnet-vulns](https://vulncheck.com/blog/zyxel-telnet-vulns)
