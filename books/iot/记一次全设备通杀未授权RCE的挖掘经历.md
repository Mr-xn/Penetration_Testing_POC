# 记一次全设备通杀未授权RCE的挖掘经历
> winmt
> 来源：https://www.iotsec-zone.com/article/381

# 记一次全设备通杀未授权RCE的挖掘经历

## 前言

想来上一次挖洞还在一年前的大一下，然后就一直在忙活写论文，感觉挺枯燥的（可能是自己不太适合弄学术吧QAQ），所以年初1~2月的时候，有空的时候就又会挖一挖国内外各大知名厂商的设备，拿了几份思科、小米等大厂商的公开致谢，也分配到了一些`CVE`和`CNVD`编号，之后就没再挖洞，继续忙活论文了QAQ。

某捷算是国内挺大的厂商了，我对其某系统进行了漏洞挖掘，并发现了**一个可远程攻击的未授权命令执行漏洞，可以通杀使用该系统的所有路由器、交换机、中继器、无线接入点`AP`以及无线控制器`AC`等众多设备**，危害还是相当严重的。

根据厂商的要求，在修补后的固件未发布前，我对该漏洞细节进行了保密。如今新版本固件都已经发布，在这里给大家分享一下这一次的漏洞挖掘经历（包括**固件解密、仿真模拟、挖掘思路**等），希望能给各位师傅带来些许启发（大师傅们请绕道QAQ）。

**声明：**本文仅供用于安全技术的交流与学习，文中涉及到的敏感内容都进行了删减或脱敏处理，仅分析了漏洞链。若读者将本文内容用作其他用途，由读者承担全部法律及连带责任，文章作者不承担任何法律及连带责任。

## 时间线

2023-02-27：发现漏洞，并将该漏洞上报给了厂商
2023-02-28：厂商确认了漏洞，并启动了应急响应，开始修补并内测
2023-03-06：厂商给予了一定的奖励（不过有点少QAQ）
2023-05-24：厂商修复了所有影响的设备并发布了安全通告及致谢

安全通告：[https://www.ruijie.com.cn/gy/xw-aqtg-gw/91389/](https://www.ruijie.com.cn/gy/xw-aqtg-gw/91389/ "https://www.ruijie.com.cn/gy/xw-aqtg-gw/91389/")
CVSS 3.1评分：9.8（严重，CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H）

## 固件解密

可以从厂商官网下载到最新固件，然而可以发现其中的固件大多都是加密的，用`binwalk`是无法解开的：

![0.png](https://www.iotsec-zone.com/images/MdImg/287a51cd94803382b2b0dd735694ead5.png)

这大概是想要分析该固件所需迈过的第一道坎了，不过好在还是比较容易解密的。原因在于，只是大部分固件都被加密了，但是仍有少部分固件（或过渡版本的固件）并未加密，很容易想到这些固件升级的过程中肯定也会使用到解密的程序，因此可以**通过解开这些未加密固件，找到解密程序，并逆向分析出相关算法**，这也是固件解密最常用的一种手段。并且，一般一个厂商的固件加密算法都是相同的，故这样所有的固件我们都能够解开了。

此时，我们惊喜地发现`xxx`系列产品的`xxx`型号固件并没有被加密，可以成功解开。然而，如何找到固件的解密程序呢？显然，固件的解密操作肯定是在刷固件之前进行的，因此我们可以**查找`OpenWrt`中用于刷固件的`mtd`命令进行定位**：

![1.png](https://www.iotsec-zone.com/images/MdImg/f039d8464e860db1488e663a8ae49937.png)

很显然，此处的`rg-upgrade-crypto`自然就是我们所要找到固件解密程序，并找到它的路径`/usr/sbin/rg-upgrade-crypto`，对其逆向分析。

**（由于该加解密算法仍然被广泛应用于某捷的各类核心产品中，故这里不放出具体逆向分析的过程，此处省略xxx字........）**

因此，我们只需要根据`rg-upgrade-crypto`写出解密脚本，即可成功解开固件了：

![2.png](https://www.iotsec-zone.com/images/MdImg/1121338c7eb251f3fe76bf403a4bff29.png)

![3.png](https://www.iotsec-zone.com/images/MdImg/446188febdc7aa78fe80dd4fd3d50dbe.png)

之后，解开不同类别、不同型号设备的固件，可以发现众多设备均使用的是该系统，因此只要挖出一个洞，就可通杀所有设备了。由于授权洞的实际影响并不算太大，所以我们期望挖出**未授权远程命令执行漏洞**。

## 漏洞分析

此部分以`xxx`固件为例进行分析，该固件是`aarch64`架构的。其他固件也许架构或部分字段的偏移不同，但均存在该漏洞。

### 找到无鉴权的API接口

显然，此类固件的`cgi`部分是用`Lua`所写的。我们既然想要挖未授权的漏洞，那么首先就要找到无鉴权的`API`接口，定位到`/usr/lib/lua/luci/controller/eweb/api.lua`文件。

可以看到，**只有对`/cgi-bin/luci/api/auth`发送请求的时候，不需要权限验证**：

```lua
entry({"api", "auth"}, call("rpc_auth"), nil).sysauth = false
```

根据调用的`rpc_auth`函数，可见此处对应的处理文件是`/usr/lib/lua/luci/modules/noauth.lua`：

```lua
function rpc_auth()
    ...
    local _tbl = require "luci.modules.noauth"
    ...
    ltn12.pump.all(jsonrpc.handle(_tbl, http.source()), http.write)
end
```

进一步分析`/usr/lib/lua/luci/utils/jsonrpc.lua`中的`handle`及其相关函数，可以得知这里**通过`JSON`数据的`method`字段定位并调用`noauth.lua`中对应的函数，同时将`Json`数据的`params`字段内容作为参数传入**（由于与该漏洞原理关系不大，此处不展开分析）。

### 寻找可能存在漏洞的入口

在`noauth.lua`中，有`login`，`singleLogin`，`merge`和`checkNet`四个方法。其中，`singleLogin`函数无可控制的参数，不用看；`checkNet`函数中参数可控的字段只有`params.host`，并拼接入了命令字符串执行，但是在之前有`tool.checkIp(params.host)`对其的合法性进行了检查，无法绕过。

再来看到`login`登录验证函数，这里可控的字段乍一看比较多，比如`params.password`，`params.encry`，`params.limit`等字段。其中，对`params.password`字段用`tool.includeXxs`函数过滤了危险字符，故大概率之后会有相关的命令执行点。

```lua
function login(params)
    ...
    if params.password and tool.includeXxs(params.password) then
        tool.eweblog("INVALID DATA", "LOGIN FAILED")
        return
    end
    ...
    local checkStat = {
        password = params.password,
        username = "admin", -- params.username,
        encry = params.encry,
        limit = params.limit
    }
    local authres, reason = tool.checkPasswd(checkStat)
    ...
end
```

再来看到继续调用的`tool.checkPasswd`函数（在`/usr/lib/lua/luci/utils/tool.lua`中），其中检测了传入的`encry`和`limit`字段的真假值，并在这两个字段中写入了相应的固定字符串，`checkStat.username`又是传入的固定用户名`admin`，因此**真正可控的只有`password`字段**，并调用了`cmd.devSta.get`函数进一步处理。

```lua
function checkPasswd(checkStat)
    ...
    local _data = {
        type = checkStat.encry and "enc" or "noenc",
        password = checkStat.password,
        name = checkStat.username,
        limit = checkStat.limit and "true" or nil
    }
    local _check = cmd.devSta.get({module = "adminCheck", device = "pc", data = _data})
    ...
end
```

然而，虽然`password`字段用`includeXxs`函数（同样在`tool.lua`中）过滤了危险字符，但是**并没有过滤`\n`这个命令分隔符**。因此，若之后当真存在命令执行点的话，似乎还是有希望完成命令注入的。

```lua
function includeXxs(str)
    local ngstr = "[`&$;|]"
    return string.match(str, ngstr) ~= nil
end
```

继续往下看到`/usr/lib/lua/luci/modules/cmd.lua`，`devSta.get`对应着如下处理函数，其中`opt[i]`循环匹配到`get`方式，会通过`doParams`函数对传入的`Json`参数进行解析，将其中的`data`等字段分离出来，传入`fetch`函数做进一步处理。

```lua
devSta[opt[i]] = function(params)
local model = require "dev_sta"
params.method = opt[i]
params.cfg_cmd = "dev_sta"
local data, back, ip, password, shell = doParams(params)
return fetch(model.fetch, shell, params, opt[i], params.module, data, back, ip, password)
```

然而，注意到`doParams`函数中对`data`字段进行提取的时候，用到了`luci.json.encode`函数。这里的`data`字段就是上述`checkPasswd`函数中传入`devSta.get`作为`Json`参数的`_data`的内容，我们的疑似注入点`password`字段就在其中。**此处的`luci.json.encode`函数会对`\n`（即`\u000a`）类字符进行转义，也就不会被解析成换行符了**，不论我们后续再如何传参，这个疑似的漏洞点已经被封堵住了。

```lua
if params.data then
	data = luci.json.encode(params.data)
	_shell = _shell .. " '" .. data .. "'"
end
```
因此，我们只能将目光聚焦于`noauth.lua`中最后一个可能的入口`merge`方法了。这个函数比较简单，**调用了`devSta.set`函数，其`Json`参数中的`data`字段就是传入的`POST`报文中`params`的内容**。

```lua
function merge(params)
    local cmd = require "luci.modules.cmd"
    return cmd.devSta.set({device = "pc", module = "networkId_merge", data = params, async = true})
end
```

这里`merge`方法的入口处没有任何过滤，不过之后是否存在字符过滤和命令执行点还需要进一步分析。

### 进一步分析参数传递过程

在`noauth.lua`的`merge`函数中，调用了`devSta.set`函数，同样是对应着`cmd.lua`中的如下位置，此时`opt[i]`循环到了`set`方式。此时，由于之前**没有任何过滤**，无需使用换行符作为命令分隔符，最简单的分号、反引号之类的即可，故`doParams`函数中的`encode`不会造成影响。

```lua
devSta[opt[i]] = function(params)
local model = require "dev_sta"
params.method = opt[i]
params.cfg_cmd = "dev_sta"
local data, back, ip, password, shell = doParams(params)
return fetch(model.fetch, shell, params, opt[i], params.module, data, back, ip, password)
```

接着，我们可控的`data`字段将被传入`cmd.lua`的`fetch`函数中。其中，会将从第四个开始的参数（包括`data`字段），均传递到第一个参数所指向的函数中，即**`/usr/lib/lua/dev_sta.lua`中的`fetch`函数**。

```lua
local function fetch(fn, shell, params, ...)
    ...
    local _res = fn(...)
    ...
end
```

在`/usr/lib/lua/dev_sta.lua`的`fetch`函数中，这里的`cmd`是`set`方式，`module`是`networkId_merge`，而此处的`param`就是我们可控的`data`字段（即最初`POST`报文中`params`的内容）。可见，对一些字段赋予了真假值后，**最终将参数都传递给了`/usr/lib/lua/libuflua.so`中的`client_call`函数**。接下来，就是对二进制文件逆向分析并寻找是否存在命令执行点了。

```lua
function fetch(cmd, module, param, back, ip, password, force, not_change_configId, multi)
    local uf_call = require "libuflua"
    ...
    local stat = uf_call.client_call(ctype, cmd, module, param, back, ip, password, force, not_change_configId, multi)
    ...
end
```

然而，分析`libuflua.so`可以发现，`Lua`中所调用的`client_call`函数，其实是**`uf_client_call`函数**，这是在其他共享库中定义的函数。查找对比一下，不难发现这个函数定义在`/usr/lib/libunifyframe.so`中。

![4.png](https://www.iotsec-zone.com/images/MdImg/63aabcd7ed4fd37a457c9dff6c74f59c.png)

在**`/usr/lib/libunifyframe.so`的`uf_client_call`函数**中，先将传入的`data`等字段转为`Json`格式的数据，作为`param`字段的内容。然后将`Json`数据**通过`uf_socket_msg_write`用`socket`套接字（分析可知，此处采用的是本地通信的方式）进行数据传输**。

```C
      json_object_object_add(v22, "data", v35);
LABEL_82:
      ...
      json_object_object_add(v5, "params", v22);
      v44 = (const char *)json_object_to_json_string(v5);
      ...
      v45 = uf_socket_client_init(0LL);
      ...
      v51 = strlen(v44);
      uf_socket_msg_write(v45, v44, v51);
```

既然这里采用`uf_socket_msg_write`进行数据发送，那么肯定有某个地方**会使用`uf_socket_msg_read`进行数据接收**，再进一步处理。匹配一下，一共三个文件，很容易锁定`/usr/sbin/unifyframe-sgi.elf`文件。又发现在初始化脚本`/etc/init.d/unifyframe-sgi`中，启动了`unifyframe-sgi.elf`，即**说明`unifyframe-sgi.elf`一直挂在进程中**。因此，我们可以确定`unifyframe-sgi.elf`就是接收`libunifyframe.so`所发数据的文件（这里采用了`Ubus`总线进行进程间通信）。

![5.png](https://www.iotsec-zone.com/images/MdImg/ff045e9bfe148e39d1d2d9660ffc6f88.png)

```
$ cat etc/init.d/unifyframe-sgi

...
PROG=/usr/sbin/unifyframe-sgi.elf
...

if [ -f "$IPKG_INSTROOT/lib/functions/procd.sh" ]; then
    ...
else
    ...
    start() {
        ...
        echo "Starting $PROG ..."
        service_start $PROG
        ...
    }

    stop() {
        ...
    }
fi
```

接下来就是最核心的部分，对`unifyframe-sgi.elf`二进制文件进行逆向分析并寻找命令执行点了。

### 逆向分析并寻找命令执行点

> 由于篇幅限制，笔者无法对所有细节都做到详细分析，故建议读者在复现此部分内容之前，自己先逆向分析一遍，体会一下。

在`unifyframe-sgi.elf`中，**对`uf_socket_msg_read`函数交叉引用**，找到`socket`数据接收点。如下方代码段，`v6 = 0x432000`，简单计算一下，可知`v57`即为`uf_socket_msg_read`函数，其中**接收到的数据存储在`v56[1]`中**。接收到的`Json`数据形如**`{"method":"devSta.set", "params":{"module":"networkId_merge", "async":true, "data":"xxx"}}`**（可结合上文，自行分析得出），其中`data`字段可控。

```C
v6 = 0x432000uLL;
...
v57 = *(__int64 (__fastcall **)(__int64, unsigned int **))(v6 + 1784); // uf_socket_msg_read
v58 = *v46;
*v56 = v46;
v59 = v57(v58, v56 + 1);
```

接下来就是根据调试等级向日志写入相关信息的部分，不需要管。之后，会调用`parse_content`函数，从这个名字就可以看出是对`v56`中的`Json`数据进行解析的。解析成功后，就会将处理后的`v56`作为参数传入`add_pkg_cmd2_task`函数。

```C
if ( !(*(unsigned int (__fastcall **)(unsigned int **))(v6 + 3328))(v56) ) // 0x432D00 parse_content
{
    ...
    if ( !(*(unsigned int (__fastcall **)(unsigned int **))(v6 + 1776))(v56) ) // 0x4326F0 add_pkg_cmd2_task
    ...
}
```

我们先来看`parse_content`函数，显然`method`字段不包含`cmdArr`，因此进入`else`分支，其中调用`parse_obj2_cmd`函数进行数据解析。

```C
if ( (unsigned int)json_object_object_get_ex(v4, "method", &v15) == 1 )
{
    v6 = (const char *)json_object_get_string(v15);
    ...
    if ( strstr(v6, "cmdArr") )
    {
        ...
    }
    else
    {
        *(_DWORD *)(a1 + 60) = 1;
        v13 = malloc_cmd();
        if ( v13 )
        {
            v14 = parse_obj2_cmd(v4, string);
            ...
        }
        else
        {
            ...
        }
    }
```

在`parse_obj2_cmd`函数中，需要注意记录一下各字段存储位置的偏移，后续逆向过程需要用到。这里暂且只记录两个，**`from_url`字段的偏移为`81`，我们可控的`data`字段的偏移为`24`**（`v5`是`QWORD`类型，八字节）。

```C
if ( (unsigned int)json_object_object_get_ex(v42, "from_url", &v43) == 1 )
{
    v21 = (const char *)sub_4069B8(v43);
    v22 = (char *)v21;
    if ( v21 )
    {
        if ( *v21 == 49 || !strcmp(v21, "true") )
            *((_BYTE *)v5 + 81) = 1;
        free(v22);
    }
```

```C
_QWORD *v5; // x20
...
if ( (unsigned int)json_object_object_get_ex(v42, "data", &v43) == 1
    && (unsigned int)json_object_get_type(v43) - 4 <= 2 )
{
    if ( json_object_get_string(v43) )
    {
        v31 = ((__int64 (*)(void))strdup)();
        v5[3] = v31;
        if ( !v31 )
        {
            v10 = 561LL;
            goto LABEL_11;
        }
    }
}
```

此外，当`async`字段为`false`的时候，偏移`76`和`77`的位置都为`1`。但这里的`async`字段为`true`，故**这两个偏移处均为初始值`0`**。

```C
if ( (unsigned int)json_object_object_get_ex(v42, "async", &v43) == 1 )
{
    v15 = (const char *)sub_4069B8(v43);
    v16 = (char *)v15;
    if ( v15 )
    {
        if ( *v15 == 48 || !strcmp(v15, "false") )
        {
            *((_BYTE *)v5 + 76) = 1;
            *((_BYTE *)v5 + 77) = 1;
        }
        ...
    }
}
```

再来看到`add_pkg_cmd2_task`函数，前面部分是一些检查和无关操作，就不仔细分析了。很容易发现最后调用了一个很敏感的函数`uf_cmd_call`，看名字应该是命令执行相关的。

```C
if ( (unsigned int)uf_cmd_call(*v4, v4 + 1) )
    v13 = 2;
else
    v13 = 1;
```

在`uf_cmd_call`函数中，乍一看，貌似有一个命令执行点，这里的`v20`是偏移`24`的位置，也就是`data`字段内容，之后将`data`字段中的数据转成`Json`格式存入`v24`，然后从中提取`url`字段的内容拼接入命令字符串中，并用`popen`执行。

```C
v20 = *((_QWORD *)a1 + 3);
...
v24 = json_tokener_parse(v20);
...
v26 = json_object_object_get(v24, "url");
v27 = v26;
...
v28 = (const char *)json_object_get_string(v27);
...
v33 = snprintf(v30, v32 + 127, "curl -m 5 -s -k -X GET \"%s", v28);
...
while ( 1 )
{
    ufm_popen(v30, v84);
```

然而，仔细分析一番，就会发现这是空欢喜一场。因为`v20`是偏移`81`的`from_url`字段，这是我们**不可控的**。若是该字段为假，**会将`data`字段内容传给`v85[19]`**（`v85`是`int64`类型，八字节），并**直接跳转到`LABEL_96`处，也就无法执行到上方的程序片段了**。

```C
v19 = *((unsigned __int8 *)a1 + 81);
...
if ( !v19 )
{
    v85[19] = *((_QWORD *)a1 + 3);
    goto LABEL_96;
}
```

从`LABEL_96`处开始是一堆字段的提取，存放入`v85`数组中，还有一些关于`v85`数组中数据的处理。这里需要关注的是：**`v85`偏移`8`和`9`的位置为`a1`偏移`77`和`76`的位置（上文分析过，此时这两个偏移的值均为`0`）**。

```C
LOBYTE(v85[1]) = *((_BYTE *)a1 + 77);
BYTE1(v85[1]) = *((_BYTE *)a1 + 76);
```

既然从`LABEL_96`开始都是对`v85`数组进行操作的，**那么`v85`指针肯定会作为参数传递给下一个调用的函数**，以这个思路，就很容易定位到下面的`ufm_handle(v85)`了。

```C
v8 = ufm_handle(v85);
pthread_mutex_unlock((pthread_mutex_t *)(v85[23] + 152));
pthread_cleanup_pop(v84, 0LL);
```

在`ufm_handle`函数中，由于我们是`set`方式，因此会调用到`sub_410140`函数。

```C
if ( strcmp((const char *)v6, "get") )
{
    v1 = "uniframe_sgi/error.log";
    if ( !strcmp((const char *)v6, "set")
        || !strcmp((const char *)v6, "add")
        || !strcmp((const char *)v6, "del")
        || !strcmp((const char *)v6, "update") )
    {
        v33 = sub_410140(v3);
```

进入`sub_410140`函数，首先`sn`字段为空的条件满足，跳转到`LABEL_36`。

```C
v6 = json_object_object_get(a1[22], "sn");
if ( !v6 )
    goto LABEL_36;
```

接着，会调用到`sub_40DA38`函数。

```C
LABEL_36:
  ...
  v5 = sub_40DA38(a1, a1 + 21, 0LL, 0LL);
```

在`sub_40DA38`函数中，显然前面的部分无关紧要，不过需要注意一下`v5`和`v6`分别是`a3`和`a4`，根据传入的值，均为零。因此，进入`else`分支，这里会将`data`字段的内容（前文分析过，此处偏移`19*8`的位置也被赋为了`data`字段的内容）拼接入两个单引号内。此处`v4`字符串形如**`/usr/sbin/module_call set networkId_merge 'xxx'`**（可自行分析得出），很显然是一个命令，并且单引号内的内容我们可控，所以我们只需要**左右分别闭合单引号，中间注入恶意命令，并用分隔符隔开**即可完成命令注入。不过，这里还没到命令执行点，由于不确定之后是否会有过滤，我们需要接着往下看。

```C
LODWORD(v5) = a3;
v6 = a4;
...
if ( (_DWORD)v5 )
{
    ...
}
else if ( v6 )
{
    ...
}
else
{
    v84 = snprintf(
        v4,
        v75,
        "/usr/sbin/module_call %s %s",
        *((const char **)v7 + 5),
        (const char *)(*((_QWORD *)v7 + 23) + 16LL));
    v85 = &v4[v84];
    v86 = (const char *)*((_QWORD *)v7 + 19);
    if ( v86 )
        v85 += snprintf(&v4[v84], v75, " '%s'", v86); // data字段拼接入单引号内
    ...
}
```

接着，由之前的分析，此处`v7`偏移`8`的位置为`0`（`async`不是`false`），故进入`else`分支，其中会将`v4`传入`ufm_commit_add`函数，作为第二个参数。

```C
if ( (!v79 || !strcmp(v78, "commit") || (_DWORD)v5) && v7[8] )
{
    ...
}
else
{
    ...
    v13 = ufm_commit_add(0LL, v4, 0LL, a2);
}
```

然后，继续进入`async_cmd_push_queue`函数。

```C
__int64 __fastcall ufm_commit_add(__int64 a1, __int64 a2, unsigned __int8 a3, const char **a4)
{
    ...
    v6 = async_cmd_push_queue(a1, a2, a3);
```

此处，`a1`为`0`，**将`a2`存入`v4`偏移`6*8`字节处**，然后跳转到`LABEL_28`的位置。

```C
if ( !a1 )
{
    if ( a2 )
    {
        v23 = strdup(a2);
        v4[6] = v23;
        if ( v23 )
            goto LABEL_28;
        ...
    }
```

在`LABEL_28`处，注意到最后使用`sem_post`的原子操作，将信号量加上了`1`。因此，应该**会有其他地方在检测到信号量发生改变后，对数据进行处理**。

```C
LABEL_28:
  ...
  *((_BYTE *)v4 + 56) = v7;
  dword_4336B8 = v22 + 1;
  if ( !v7 )
    sem_init((sem_t *)((char *)v4 + 60), 0, 0);
  pthread_mutex_unlock((pthread_mutex_t *)&stru_433670[1]);
  sem_post(stru_433670);
```

通过**对此处的信号量`stru_433670`交叉引用**，可以定位到`sub_419584`函数。这里偏移`56`的位置即为上述代码段中的`v7`，对应传入的第三个参数，根据上文分析，其值为`0`。因此，会将`6*8`字节偏移处的数据（上文分析过，该偏移位置存放着命令字符串）作为`popen`的参数执行，且没有任何过滤。此处采用的是**异步执行**的方式。

```C
v11 = *((_QWORD *)v5 + 6);
if ( !*((_BYTE *)v5 + 56) )
{
    v10 = ufm_popen(v11, v5 + 24);
    goto LABEL_18;
}
```

至此，该未授权`RCE`漏洞的调用链分析完毕。

### PoC

> 由于该漏洞影响较大，`Poc`暂不公开。各位师傅可根据上文分析，自行复现。

```
暂不公开
```

### 真机演示

对某远程测试靶机攻击后，无需身份验证即得到了该设备的最高控制权：

![6.png](https://www.iotsec-zone.com/images/MdImg/866931a4b05345cff696ec5cb3169788.png)

## 仿真模拟

此部分仿真采用的是`xxx`型号的固件，因为这款是`mipsel`架构的，仿真起来方便一些。

由于目前没有很完美的仿真工具，比较常用的`FirmAE`，`EMUX`，`firmware-analysis-plus`等也都存在各种问题（至少直接仿真大多数设备都是不太行的），所以笔者一般都采用`qemu-system`自行仿真模拟，再者该系统的固件不涉及到`nvram`，采用的是`uci`命令完成类似的效果，故也不需要用上述仿真工具来`hook`相关函数了。

首先从`https://people.debian.org/~aurel32/qemu/mipsel`下载`vmlinux-3.2.0-4-4kc-malta`内核与`debian_squeeze_mipsel_standard.qcow2`文件系统，这里提供的文件虽然是比较老的了（较新版可以在`https://pub.sergev.org/unix/debian-on-mips32`下载），但不影响我们使用。

下面直接给出`qemu`的启动脚本：

```Shell
#!/bin/bash

sudo qemu-system-mipsel \
	-cpu 74Kf \
	-M malta \
	-kernel vmlinux-3.2.0-4-4kc-malta \
	-hda debian_squeeze_mipsel_standard.qcow2 \
	-append "root=/dev/sda1 console=tty0" \
	-net nic,macaddr=00:16:3e:00:00:01 \
	-net tap \
	-nographic
```

需要特别注意的是，**这里设定了`cpu`为`74kf`，因为若不特别说明，默认是`24Kc`，而该固件需要较高版本的`cpu`，不然在之后`chroot`切换根目录的时候就会出现`Illegal instruction`（非法指令）错误**。可用`qemu-system-mipsel -cpu help`命令查看`qemu-system-mipsel`所有支持的`cpu`版本。

在正式开始仿真前，需要先进行网络配置。用`ip addr`或`ifconfig`命令查看一下主机的`ip`，如下图为`eth0`（或`ens33`）对应的`192.168.192.129`，若是没有，手动用`sudo ifconfig eth0 xx.xx.xx.xx`分配一下即可。

![7.png](https://www.iotsec-zone.com/images/MdImg/10beca63d01bb6e4579f858f65d23cbb.png)

然后，用上面的脚本启动`qemu-system`（先需要配置一下`/etc/qemu-ifup`），初始账号密码`root/root`。在`qemu`中，也需要给网卡分配一下`ip`，这样主机和`qemu`间就能通信了（可以互相`ping`通）。

![8.png](https://www.iotsec-zone.com/images/MdImg/6ea684626a05ba67a23789b81ada4b91.png)

我们将固件打包成`rootfs.tar.gz`，再通过`scp rootfs.tar.gz root@192.168.192.135:/root/rootfs`传输给`qemu`虚拟机，然后在`qemu`虚拟机中`tar zxvf rootfs.tar.gz`解压即可（打包之后传输更快）。接着，在`qemu`中依次执行以下命令：

```Shell
cd rootfs
chmod -R 777 ./
mount --bind /proc proc
mount --bind /dev dev
chroot . /bin/sh
```

解释一下，这里`chmod`给全部文件都赋予所有权限，是为了方便在仿真过程中不用再考虑权限问题的影响了。之后使用`mount`将`rootfs`中的`proc`和`dev`目录挂载到`/proc`和`/dev`系统目录（显然仿真系统的这两个目录也需要用`qemu`虚拟机的系统目录），最后用`chroot`将`rootfs`切换为根目录，完成准备工作。

以上都是些用`qemu`对设备仿真模拟的基本操作，接下来正式开始对这款设备的固件进行仿真。首先，对于`OpenWRT`来说，内核加载完文件系统后，**首先会启动`/sbin/init`进程**，其中会进一步执行`/etc/preinit`和`/sbin/procd`，进行初步初始化。这当然也是仿真模拟的第一步，在启动`/sbin/init`后，会卡住挂在进程中，我们可以再`ssh`开一个新窗口进行后续操作，也可以用**`/sbin/init &`**将其作为后台进程执行。

![9.png](https://www.iotsec-zone.com/images/MdImg/4313fe983bdae9c52656dcb9dba29d70.png)

接着，真实系统会根据`/etc/inittab`中按编号次序执行`/etc/rc.d`中的初始化脚本，而`/etc/rc.d`中的文件都是`/etc/init.d`中对应文件的软链接。虽然说真实系统会依次执行所有的初始化脚本，但我们此处的仿真只是为了验证我们的漏洞，因此只需要部分仿真即可。

显然，**我们最开始肯定是需要启动`httpd`服务的，对应`/etc/init.d/lighttpd`初始化脚本**。用`/etc/init.d/lighttpd start`命令启动服务后，发现缺少了`/var/run/lighttpd.pid`文件：

![10.png](https://www.iotsec-zone.com/images/MdImg/48a914b05c34c670fd2dc1a5e2b60e5e.png)

这是因为我们是部分仿真的，没有按照次序，故之前没有创建这个文件，而通过查看该初始化脚本，可以发现此处`/rom/etc/lighttpd/lighttpd.conf`的缺失并无影响。因此，**创建`/var/run/lighttpd.pid`文件后，再次`/etc/init.d/lighttpd start`启动服务**即可。

可以看到，此时进程中已经成功执行`lighttpd`程序，并且通过浏览器可以正常访问该漏洞入口的`api`。

![11.png](https://www.iotsec-zone.com/images/MdImg/62d91c7aa52e82d678c5608b2f82ece9.png)

![12.png](https://www.iotsec-zone.com/images/MdImg/647dd720854df48c33cb5ac94138f64b.png)

接着，**我们需要启动`unifyframe-sgi.elf`了，对应`/etc/init.d/unifyframe-sgi`的初始化脚本**。用`/etc/init.d/unifyframe-sgi start`直接启动后，报错`Failed to connect to ubus`：

![13.png](https://www.iotsec-zone.com/images/MdImg/7cb8728b0b5d117d38087178422e8885.png)

这是**因为`unifyframe-sgi.elf`中用到了`ubus`总线进行进程间通信**，因此**需要先执行`/sbin/ubusd`启动`ubus`通信，才能启动`uf_ubus_call.elf`，继而才能再启动`unifyframe-sgi.elf`**。

按照上述步骤启动后，可以发现进程中有了`uf_ubus_call.elf`，但是仍然没有`unifyframe-sgi.elf`，同时`procd`守护进程收到了一个`Segmentation fault`段错误的信号，意味着**启动`unifyframe-sgi.elf`的时候出现了段错误**。

![14.png](https://www.iotsec-zone.com/images/MdImg/321c44a54f03469cb52bfd4720d1acc6.png)

接下来，我们需要分析`unifyframe-sgi.elf`为何会出现段错误，大概率是由于缺少一些文件或目录所导致的。首先，发现此时`/tmp/uniframe_sgi`中已经存在`record`文件夹，但并未创建`sgi.log`日志文件，进入`unifyframe-sgi.elf`的主函数，容易定位到`reserve_core`函数，其中**需要打开`/tmp/coredump`目录，但这个目录此时是不存在的，因此造成了段错误**。

![15.png](https://www.iotsec-zone.com/images/MdImg/3b5190e07b5a3d76d8b61b1944d48706.png)

创建`/tmp/coredump`目录后，运行`/usr/sbin/unifyframe-sgi.elf`程序，因**缺少`/tmp/rg_device/rg_device.json`文件**报错：

![16.png](https://www.iotsec-zone.com/images/MdImg/2a386ab63ee03dfcfa8b129da15eb889.png)

这里的`rg_device.json`大概率是在某前置操作中从其他位置复制过来的，故搜索同名文件，不过有很多：

![17.png](https://www.iotsec-zone.com/images/MdImg/a20f213a9c03a6d1efba8e0f168a8c63.png)

为了确定是哪一个，我们定位到`ufm_init`函数中，发现此处之后**会从`rg_device.json`中读取`dev_type`字段**的内容。

![18.png](https://www.iotsec-zone.com/images/MdImg/8d6641552185f7d69d8d1a2ca6f5b208.png)

可以发现除了`/sbin/hw/default/rg_device.json`中都有此字段，这里**随便复制一个`/sbin/hw/60010081/rg_device.json`到`/tmp/rg_device`目录下**。之后再执行`/usr/sbin/unifyframe-sgi.elf`程序，就发现没有新的报错，执行成功了。

![19.png](https://www.iotsec-zone.com/images/MdImg/2135fb577a7036e69d2c6747cd471288.png)

此时进程中也有`/usr/sbin/unifyframe-sgi.elf`程序在运行。

![20.png](https://www.iotsec-zone.com/images/MdImg/cbc1e3b5de8f854c64714c40e2ebb117.png)

最后，我们利用该漏洞注入`telnetd`命令启动相应服务，可以看到**代表`telnet`服务的`23`号端口被成功开启**。

![21.png](https://www.iotsec-zone.com/images/MdImg/ff22ec4f7e1d4ef60914a2594feabad0.png)

至此，利用仿真模拟的环境对该漏洞的验证完成，总体来说对该设备的仿真还是比较容易的。

## 补丁分析
### 补丁1

遗憾的是，部分型号设备的固件在第一次修补之后仍存在漏洞，笔者已上报给厂商并修复。这里以`xxx`固件为例，使用`Diaphora`对新旧版本的`unifyframe-sgi.elf`文件进行二进制对比分析。

容易发现，在新版固件的`unifyframe-sgi.elf`文件中新增了`stringtojson`和`is_independ_format`函数：

![22.png](https://www.iotsec-zone.com/images/MdImg/26cf43367c348a9794fa0f728bebd354.png)

在`stringtojson`函数中，调用了`is_independ_format`函数，判断是否存在**单引号和反引号**。若不存在就返回，而**返回的内容无法通过单引号闭合**，也就无法执行任意命令。

```C
__int64 __fastcall stringtojson(__int64 a1)
{
    ...
    v2 = 0x433000uLL;
    v3 = 0x433000uLL;
    if ( !a1 )
        goto LABEL_2;
    while ( 2 )
    {
        v5 = (_BYTE *)a1;
        if ( !(*(unsigned __int8 (**)(void))(v2 + 2968))() // is_independ_format
            || ... )
        {
        LABEL_2:
            v1 = 0LL;
            goto LABEL_3; // -> return xxx;
        }
```

```C
bool __fastcall is_independ_format(const char *a1)
{
  if ( !a1 )
    return 0LL;
  if ( strchr(a1, '`') )
    return 1LL;
  return strchr(a1, '\'') != 0LL;
}
```

若是存在单引号，且前面没有转义符，则对其**`Unicode`编码**，即`\\u0027`。反引号也同理。

```C
while ( 1 )
{
    v13 = (unsigned __int8)*v11;
    if ( !*v11 )
        break;
    v15 = v11 + 1;
    if ( v13 == '\'' )
        goto LABEL_22;
    ...
LABEL_22:
    if ( v11 != (_BYTE *)1 )
    {
        v13 = 'u';
        v16 = *(v11 - 1) != '\\';
        if ( (unsigned __int64)v11 <= v10 )
            goto LABEL_24; // mark
        goto LABEL_38;
    }
    goto LABEL_19;
    ...
LABEL_24:
    if ( !v16 )
        goto LABEL_40;
    v17 = (__int64 *)v22;
    LOBYTE(v22[1]) = v13; // mark
LABEL_26:
    if ( v13 == 'u' )
    {
        (*(void (__fastcall **)(__int64, const char *, _QWORD))(v3 + 3680))( // sprintf
            (__int64)v17 + v16 + 4,
            "%02x",
            (unsigned __int8)*(v15 - 1)); // mark
        v18 = (unsigned int)(v16 + 6);
    }
```

进一步交叉引用，在`sub_40DB48`函数中，对可控的数据用`stringtojson`函数进行了过滤。然而，这里的过滤并不严谨，接着往下看。

![23.png](https://www.iotsec-zone.com/images/MdImg/824671294e0054ca6f58a3eadc797d78.png)

由上述可知，若这里的`v74`不为空，则存放着`stringtojson`函数过滤后的内容，否则说明不存在单引号或反引号，也就未通过`stringtojson`函数进行过滤。又由于`stringtojson`函数处理后会**带有双引号**，故若包含了单引号或反引号，**该命令在新版固件中实际为`/usr/sbin/module_call set networkId_merge "{...}"`**。虽然由于`JSON`数据中双引号得是`\"`才行（`stringtojson`函数也会将双引号编码为`\\u0022`），无法闭合绕过双引号，但是在双引号内是**可以用反引号或`$()`执行命令**的，而这里只过滤了反引号，并**未过滤`$()`**，也就给了攻击者可趁之机。

![24.png](https://www.iotsec-zone.com/images/MdImg/77eb8ae4e6b3116dd5e0bbe68c0c0654.png)

不过，在新版本固件中，也在其他方面加强了一定的安全检查和防护，例如在初始化脚本`/etc/init.d/factory`中通过`rm usr/sbin/telnetd`命令**删除了`telnetd`程序**，也就无法通过开启远程登录而控制设备了。但是，不难想到还可以通过**反弹`shell`**获取设备权限，这里笔者采用的是**`telnet`反弹**的方式。

**请求报文：**

```
暂不公开
```

**演示效果：**

![25.png](https://www.iotsec-zone.com/images/MdImg/bd2fdf83841fd2c758fc5c199f4120ff.png)

### 补丁2

其实，只要在`noauth.lua`的`merge`函数中对传入的`params`加个过滤即可，如下：

```lua
function merge(params)
    local cmd = require "luci.modules.cmd"
    local tool = require("luci.utils.tool")
    local _strParams = luci.json.encode(params)

    if tool.includeXxs(_strParams) or tool.includeQuote(_strParams) then -- 过滤危险字符和单引号
        tool.eweblog(_strParams, "MERGE FAILED INVALID DATA")
        return 'INVALID DATA'
    end

    return cmd.devSta.set({device = "pc", module = "networkId_merge", data = params, async = true})
end
```
此处，通过`includeXxs`函数过滤了各种危险字符，以及用`includeQuote`函数过滤了单引号：

```lua
function includeXxs(str)
    local ngstr = "[\n`&$;|]"
    return string.match(str, ngstr) ~= nil
end
```
```lua
function includeQuote(str)
    return string.match(str, "(['])") ~= nil
end
```
可见，在新版本固件中，将换行符`\n`也过滤了，提高了安全性。

## 总结

这篇文章是在挖到这个`0day`挺久之后写的了。依稀记得当时刚挖到这个漏洞的时候，有着些许兴奋，但更多的是感到不易，因为我当时觉得这条调用链还挺深的，里面也牵涉到了不少东西。但是，当我如今再梳理这个漏洞的相关细节的时候，我觉得这条调用链其实也就那样吧，整个挖掘思路和利用思路都不算难，抛开影响范围，并算不上品相多好的洞QAQ。

在挖这个洞的时候，我遇到的最大挑战就是逆向分析了，我觉得这里的逆向难度还是比较大的（当然我逆向水平也很菜）。在实际逆向分析的过程中，并没有文章中写的那么流畅，当时的挖掘思路也不可能是完全按照文章的流程来的，比如需要多考虑一些东西（例如，文章中一直都在找命令注入的洞，但其实也有可能是可控的`params`字段造成的缓冲区溢出等等，这些在初次挖掘的时候也都需要考虑），当然也走了不少弯路，但好在最终是坚持下来了。

当时，我只知道`params`字段是可控的，而`params`内也是`Json`的格式，于是猜测是其中的某个特定的字段可能会造成命令注入或缓冲区溢出等问题，因此就一路挖到底了。不过如今再看来，其实就这个洞而言，是否采用自动化的方式会更简单呢（当然就工业界来说，`IoT`的全自动化漏扫我并没有看到过实际效果很好的工具，基本都是半自动化提高效率）？

进一步地从宏观上来看二进制漏洞的挖掘思路，无非就是从危险函数出发和从交互入口出发两种方式，显然前者在筛掉明显无法利用的危险函数点之后，所涉及的支路会更少，挖起来也会更容易，而后者基本是要从交互入口一路挖到中断点甚至挖到底的。然而，该漏洞却是采用后者的思路进行挖掘的，当时主要是考虑到只有一个可能的未授权入口，因此很自然地采用了后者的思路。现在想来，这里若是采用前者的思路，可能并不会那么容易地挖到此漏洞。如何更好地结合上述两种思路，特别是对于自动化漏扫来说，我觉得仍是值得思考的问题。

说了些自己粗浅的理解和感受，就说到这里吧。希望这篇文章能给各位像我一样刚入门`IoT`漏洞挖掘的师傅带来些启发，也欢迎各位大师傅与我交流。最后，希望我在不久的将来能挖到在挖掘思路和利用手法上都有所创新的高质量`0day`吧。
