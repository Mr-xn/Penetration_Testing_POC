# 记一次酒店wifi设备分析
> buggart
> 来源：https://www.iotsec-zone.com/article/158

# 记一次酒店wifi设备分析

出差住酒店，连了酒店wifi，全酒店都覆盖，信号还挺不错，忍不住想看看是啥设备。想办法给自己开个不限速的wifi，解决一下网络问题。

# 探测分析

1.1.1.1进入登陆界面。
![0.png](https://www.iotsec-zone.com/images/MdImg/aa55748ac229d8629a6e3235f1b0b3a2.png)
Ruijie AC无限控制器，不过这个系列没接触过，按照之前调NBR系列的经验，先试试能不能通过信息泄露看到版本。

![1.png](https://www.iotsec-zone.com/images/MdImg/3eca9452d9eccceb7415eac85a2cde9a.png)



![2.png](https://www.iotsec-zone.com/images/MdImg/d916cd0494856bf0c70af4e51b5cd8d5.png)


根据泄漏的信息，可以看到设备的型号为`ws5308或ws6108`，固件版本为`AC_RGOS_11.9(0)B7`

此外，还有序列号，系统版本，硬件版本等...

上官网下载固件`AC_RGOS11.9(2)B2P8_G2C6-01_08130419_install.bin`

```
$binwalk -Me AC_RGOS11.9(2)B2P8_G2C6-01_08130419_install.bin
~/_AC_RGOS11.9(2)B2P8_G2C6-01_08130419_install.bin.extracted/_7EA.extracted/cpio-root$ ls
Config-2.6.32.6a7b55fef5c97b  System.map-2.6.32.6a7b55fef5c97b
kernel.ubi                    vmlinux-2.6.32.6a7b55fef5c97b
rootfs.ubi
```

使用`binwalk -Me`进行解包后，没有得到文件系统，但看到了`kernel.ubi`和`rootfs.ubi`。

使用nmap探测开放端口。

```
$ nmap 1.1.1.1

Starting Nmap 7.01 ( https://nmap.org ) at 2022-06-23 09:15 PDT
Nmap scan report for one.one.one.one (1.1.1.1)
Host is up (0.0067s latency).
Not shown: 994 closed ports
PORT     STATE SERVICE
23/tcp   open  telnet
80/tcp   open  http
443/tcp  open  https
4001/tcp open  newoak
4002/tcp open  mlchat-proxy
8081/tcp open  blackice-icecap
```

# 固件解包

解包之后发现的五个文件，我们来挨个分析一下。

```
$ ls -lh
total 69M
-rwxr-xr-x 1 vincent vincent  35K Jun 23 02:31 Config-2.6.32.6a7b55fef5c97b
-rwxr-xr-x 1 vincent vincent 4.4M Jun 23 02:31 kernel.ubi
-rwxr-xr-x 1 vincent vincent  62M Jun 23 02:31 rootfs.ubi
-rwxr-xr-x 1 vincent vincent 912K Jun 23 02:31 System.map-2.6.32.6a7b55fef5c97b
-rwxr-xr-x 1 vincent vincent 2.2M Jun 23 02:31 vmlinux-2.6.32.6a7b55fef5c97b
```

## Config-2.6.32.6a7b55fef5c97b

```
$ file Config-2.6.32.6a7b55fef5c97b 
Config-2.6.32.6a7b55fef5c97b: Linux make config build file (old)
```

查看文件类型以及内容。

```
#
# Automatically generated make config: don't edit
# Linux kernel version: 2.6.32.13
# Wed Nov 18 12:55:05 2015
#
CONFIG_MIPS=y

#
# Machine selection
#
# CONFIG_MACH_ALCHEMY is not set
# CONFIG_AR7 is not set
# CONFIG_BASLER_EXCITE is not set
# CONFIG_BCM47XX is not set
# CONFIG_BCM63XX is not set
# CONFIG_MIPS_COBALT is not set
# CONFIG_MACH_DECSTATION is not set
# CONFIG_MACH_JAZZ is not set
# CONFIG_LASAT is not set
# CONFIG_MACH_LOONGSON is not set
  ......
```

从文件头和内容格式上来看是linux内核编译配置文件。在内核编译过程中，通过配置文件中的信息构造得到未压缩的内核vmlinux。

## System.map-2.6.32.6a7b55fef5c97b

```
ffffffff80100000 A _text
ffffffff80100400 T __copy_user_inatomic
ffffffff80100400 T _stext
ffffffff80100420 T memcpy
ffffffff80100424 T __copy_user
ffffffff80100424 t __memcpy
ffffffff80100428 t __copy_user_common
ffffffff8010050c t cleanup_both_aligned
ffffffff8010056c t less_than_8units
ffffffff801005a8 t less_than_4units
ffffffff80100604 t src_unaligned
ffffffff80100650 t cleanup_src_unaligned
ffffffff8010067c t copy_bytes_checklen
ffffffff80100684 t copy_bytes
ffffffff801006f4 t done
ffffffff801006fc t l_exc_copy
ffffffff80100718 t l_exc
ffffffff80100750 t s_exc_p16u
ffffffff80100758 t s_exc_p15u
ffffffff80100760 t s_exc_p14u
......
```

在内核编译过程中，make程序调用nm命令生产System.map，是内核符号表文件。

## vmlinux-2.6.32.6a7b55fef5c97b

```
$ file vmlinux-2.6.32.6a7b55fef5c97b 
vmlinux-2.6.32.6a7b55fef5c97b: gzip compressed data, last modified: Mon Jan  4 11:25:07 2021, max compression, from Unix
```

这是压缩后的vmlinux映像，只有2.2M，里面包含了自解压的代码，存放着压缩的内核映像数据。



## kernel.ubi和rootfs.ubi	

使用file命令查看文件类型

```
$ file kernel.ubi 
rootfs.ubi: UBI image, version 1
$ file rootfs.ubi 
rootfs.ubi: UBI image, version 1
```

ubi文件系统，全称（Unsorted Block Image File System,UBIFS）无排序区块镜像文件系统，一般用于固态存储设备上，是作为jffs2的后继文件系统之一。

安装ubi_read

```
sudo pip install ubi_reader
```

解压对应文件

```
$ sudo ubireader_extract_files kernel.ubi 
Extracting files to: ubifs-root/920657746/kernel
$ sudo ubireader_extract_files rootfs.ubi 
Extracting files to: ubifs-root/709668666/rootfs
```

`kernel.ubi`解开后还是内核编译的文件内容。

```
~/_AC_RGOS11.9(2)B2P8_G2C6-01_08130419_install.bin.extracted/_7EA.extracted/cpio-root/ubifs-root/920657746/kernel$ ls -lh
total 3.1M
-rw-rw-r-- 1 vincent vincent  35K Dec 30  2020 Config-2.6.32.6a7b55fef5c97b
-rw-rw-r-- 1 vincent vincent 912K Jan  4  2021 System.map-2.6.32.6a7b55fef5c97b
-rw-rw-r-- 1 vincent vincent 2.2M Jan  4  2021 vmlinux-2.6.32.6a7b55fef5c97b
```

但`rootfs.ubi`解压成功得到了文件系统

```
~/_AC_RGOS11.9(2)B2P8_G2C6-01_08130419_install.bin.extracted/_7EA.extracted/cpio-root/ubifs-root/709668666/rootfs$ ls
bin   bootloader  dev  home  lib64    mnt   rg_cfg  rootfs  sys  usr
boot  data        etc  lib   linuxrc  proc  root    sbin    tmp  var
```



# 逻辑分析

grep命令搜索`index.htm`来追一下设备前端登陆的逻辑，寻找绕过认证或者获取用户密码的方法。

```
$ grep -r "index.htm"
Binary file bin/busybox matches
etc/rc.d/init.d/functions:#		http://winterdrache.de/linux/newboot/index.html
etc/patch_scripts/functions:#		http://winterdrache.de/linux/newboot/index.html
etc/httpd.conf:    "index":"index.htm",
Binary file sbin/http_client.elf matches
Binary file sbin/httpd.elf matches
......
```

主要关注`/etc/httpd.conf`以及`httpd`二进制文件。

## /etc/httpd.conf

```
{
    "header_append":"Content-Security-Policy: \r\nX-Frame-Options: SAMEORIGIN\r\nX-Content-Type-Options: nosniff\r\nX-XSS-Protection: 1;mode=block\r\n",
    "index":"index.htm",
    "document_root": "/tmp/html/web/views/",
    "page_404": "pub/error/404.txt",
    "fcgi_config": [
        {
            "fcgi_ext": ".lua",
            "fcgi_sock": "oam/http_fpm/http_fpm.sock",
            "fcgi_root": "/tmp/html/"
        },
        {
            "fcgi_ext": ".lp",
            "fcgi_sock": "oam/http_fpm/http_fpm.sock",
            "fcgi_root": "/tmp/html/"
        },
        {
            "fcgi_ext": ".php",
            "fcgi_sock": "/tmp/php5-fpm.sock",
            "fcgi_root": "/tmp/html/"
        }
    ],
    "cgi_ext": ".cgi",
    "cgi_root": "/tmp/html/"
}
```

我们看到主要处理文件都在"/tmp/html/"，可/tmp目录下并没有发现这个文件夹。怀疑跟Ruijie NBR系列一样，需要启动后解包。

## web包解压

```
$ grep -r "/tmp/html"
etc/httpd.conf:    "document_root": "/tmp/html/web/views/",
etc/httpd.conf:            "fcgi_root": "/tmp/html/"
etc/httpd.conf:            "fcgi_root": "/tmp/html/"
etc/httpd.conf:            "fcgi_root": "/tmp/html/"
etc/httpd.conf:    "cgi_root": "/tmp/html/"
sbin/web.gz.sh:# force to remove /tmp/html then decompress
sbin/web.gz.sh:if [ "${FORCE}" = "true" ]&&[ -d /tmp/html ]; then
sbin/web.gz.sh:    #echo "remove /tmp/html ..."
sbin/web.gz.sh:    rm -rf /tmp/html
sbin/web.gz.sh:if [ -n "${web_gz}" ]&&[ -e ${web_gz} ]&&[ ! -d /tmp/html ]; then
sbin/web.gz.sh:if [ "${RECOVER_CHECK}" = "true" ]&&[ -e ${web_gz_bak} ]&&[ ! -d /tmp/html/web ]; then
Binary file sbin/httpd.elf matches
```

`web.gz.sh`看上去很像是处理解web包的脚本。

```
$ cat ./sbin/web.gz.sh 
#!/bin/sh
#
#web.gz decompress 

PKT=web.gz
web_gz=/var/web.gz
web_gz_bak=/sbin/web.gz.bak
FORCE=false
RECOVER_CHECK=false
BACKUP=false
......
if [ -n "${web_gz}" ]&&[ -e ${web_gz} ]&&[ ! -d /tmp/html ]; then
    #echo "decompress ${web_gz}..."
    tar -zxf ${web_gz} -C /tmp
    if [ -n "${web_patch_gz}" ]; then
        #echo "web patch decompress..."
        tar -zxf ${web_patch_gz} -C /tmp
    fi
fi

if [ "${RECOVER_CHECK}" = "true" ]&&[ -e ${web_gz_bak} ]&&[ ! -d /tmp/html/web ]; then
    #echo "decompress failed, recover web packet"
    tar -zxf ${web_gz_bak} -C /tmp
```

脚本通过`tar -zxf ${web_gz} -C /tmp`来解包，而web_gz=/var/web.gz，我们手动输入命令进行web包解压。

```
~/.../rootfs$ sudo tar -zxf ./var/web.gz -C ./tmp
```

现在能看到web包展开的内容了。

```
~/.../rootfs/tmp/html/web$ ls
conf  init.cgi  init.lua  lib  routers  views  web_version.txt
```



## 初始化脚本init.lua

`/tmp/html/web`下有两个文件比较值得关注。

`init.cgi`

```
#!/bin/sh
script=${0%.*}".lua"
exec lua /sbin/cgilua.cgi $script
```

`${0%.*}`将$0即文件名`init.cgi`匹配`.*`删去`.cgi`后缀后获得`init`字符串。

即运行/sbin/cgilua.cgi init.lua。

来看一下cgilua.cgi是个啥。

```
#!/usr/bin/env lua

-- CGILua (SAPI) launcher, extracts script to launch
-- either from the command line (use #!cgilua in the script)
-- or from SCRIPT_FILENAME/PATH_TRANSLATED
 
pcall(require, "luarocks.require")
 
local common = require "wsapi.common"
local cgi = require "wsapi.cgi"
 
local sapi = require "wsapi.sapi"
 
local arg_filename = (...)
 
local function sapi_loader(wsapi_env)
  common.normalize_paths(wsapi_env, arg_filename, "cgilua.cgi")
  return sapi.run(wsapi_env)
end 
 
cgi.run(sapi_loader)
```

这是一个lua脚本的启动器，所以上面的意思就是通过启动器来运行init.lua。

那看一下`init.lua`

```
--唯一入口
GLOBAL_IN = true
local CONFIG = require("conf.appconfig");
local cgilua = require("cgilua");
local dispatcher = require"cgilua.dispatcher";
local log = require("web.lib.logger").log;
local errorPages = require("web.lib.error");
--local web_mom_util_init = require("web.lib.web_mom_util");
--global_mom_util = web_mom_util_init.new();
CGILUA_CONF = CONFIG.cgilua_conf; --lua 配置文件目录

local permission = require("web.lib.permission_map");
permission_map = permission.permission_map;
permission_onlyAdmin = permission.onlyAdmin;
permission_acOnlyAdmin = permission.acOnlyAdmin;
permission_manage = permission.getAcPermissionManage(); --是否开启分级分权 Disable or Enable
permission_id = setmetatable(permission_id or {},{ __index = permission.userPermissions()});

--[[设置异常时的日志输出]]
cgilua.seterroroutput(function(msg)
    if type(msg) ~= "string" and type(msg) ~= "number" then
		msg = format ("bad argument #1 to 'error' (string expected, got %s)", type(msg));
    end
    if(string.find(msg,"Missing page parameters") ~= nil) then
        errorPages.forward400(); 
    else
        errorPages.forward500(); 
    end
    msg = "remote addr:"..cgilua.servervariable("REMOTE_ADDR")..",error msg:\n"..msg;
    log:error(msg); --记录日志   
end)

--[[
    获取路由信息，动态调用页面模块
    /fcgi/web/intf/getIntf 解析为/fcgi-bin/web/intf/intf.lua的 getIntf方法
--]]
local handle= function(map)
    local controller = map.controller;
    local action = map.action,page ;

    if(string.find(controller,"%.%.")) then -- 禁止路径回溯
        log:error("module forbidden:"..controller..",action:"..action) ;
        errorPages.forward403() ;
        return;
    end
    local ret ,err = pcall(function()
         page = require("web.routers."..controller);
    end)  
   
   if(not ret or page == nil or page[action] == nil) then
     log:error("route not found,controller:"..controller..",action:"..action..",err:"..(err or "")) ;
     errorPages.forward404();
     return;        
   end  
   --未登录
   local execRet,execErr = pcall(function()
        --[[if(not page.beforeAction(page, controller)) then
            errorPages.forward403();
            return;
        end]]
       local res = page.beforeAction(page, controller);
       if(res == 1) then
           errorPages.forwardLoginTimeout();
           return;
       elseif (res == 2) then
           errorPages.forward403();
           return;
       end
        page[action](page);  
        page.afterAction(page);   
   end)
   if(not execRet) then
        errorPages.forward500(); 
        log:error(execErr or "");        
   end
end

dispatcher.route{"/$controller/$action", handle};

--global_mom_util.run();

GLOBAL_IN = false
```

下面来简单分析一下这个lua脚本。

**1part**

```
--唯一入口
GLOBAL_IN = true
local CONFIG = require("conf.appconfig");   -- /tmp/html/web/conf/appconfig.lua
local cgilua = require("cgilua");    --  /usr/local/lib/lua/5.3/cgilua.lua
local dispatcher = require"cgilua.dispatcher";  -- /usr/local/lib/lua/5.3/cgilua/dispatcher.lua
local log = require("web.lib.logger").log;    -- /tmp/html/web/lib/logger.lua
local errorPages = require("web.lib.error");  -- /tmp/html/web/lib/error.lua
--local web_mom_util_init = require("web.lib.web_mom_util");  -- /tmp/html/web/lib/web_mom_util.lua
--global_mom_util = web_mom_util_init.new();
CGILUA_CONF = CONFIG.cgilua_conf; --lua 配置文件目录
```

首先通过require()来加载模块。

要注意这里有几个不同的加载目录，已在注释中标注出位置。

```
$ ls ./usr/local/lib/lua/5.3/cgilua
authentication.lua  dispatcher.lua  lp.lua    post.lua       serialize.lua  urlcode.lua
cookies.lua         loader.lua      mime.lua  readuntil.lua  session.lua
```

`/tmp/html/web/conf/appconfig.lua`

```
if(not GLOBAL_IN) then  return;   end
local logging = require("logging");
local lfs = require("lfs");
--全局配置
local config = {
    debug           = true,                     --是否开发模式
    cgi_path        = "/tmp/html",              --web cgi目录
    sess_timeout    = 60*30,                    --默认session超时时间30分钟
    log_path        ="/tmp/web_logs/",          --日志目录
    log_file        = "cgilua.log",             --日志文件名
    log_maxsize     = 1024*1024,                --日志最多存放1M
    log_index       = 1                         --日志文件备份数量
};
--local file,err=io.open(config.log_path);
if(not lfs.attributes(config.log_path)) then
    os.execute("mkdir "..config.log_path);
end
config.log_level = config.debug and logging.DEBUG or logging.ERROR ;   --日志保存等级
config.cgilua_conf  = c.cgi_path .. "/web/conf";   --cgilua 配置文件目录
package.path = package.path ..";".. config.cgi_path.."/?.lua;"..config.cgi_path.."/?/init.lua";
return config;
```

所以CGILUA_CONF 为 `/tmp/html/web/conf`

**2part**

```
local permission = require("web.lib.permission_map"); --  /tmp/html/web/lib/permission_map.lua
permission_map = permission.permission_map;
permission_onlyAdmin = permission.onlyAdmin;
permission_acOnlyAdmin = permission.acOnlyAdmin;
permission_manage = permission.getAcPermissionManage(); --是否开启分级分权 Disable or Enable
permission_id = setmetatable(permission_id or {},{ __index = permission.userPermissions()});
```

设置用户权限访问的页面。

**3part**

```
--[[设置异常时的日志输出]]
cgilua.seterroroutput(function(msg)
    if type(msg) ~= "string" and type(msg) ~= "number" then
		msg = format ("bad argument #1 to 'error' (string expected, got %s)", type(msg));
    end
    if(string.find(msg,"Missing page parameters") ~= nil) then
        errorPages.forward400(); 
    else
        errorPages.forward500(); 
    end
    msg = "remote addr:"..cgilua.servervariable("REMOTE_ADDR")..",error msg:\n"..msg;
    log:error(msg); --记录日志   
end)
```

注意这里cgilua的成员seterroroutput是从cgilua.lua模块中获取的：

```
function M.seterroroutput (f)
	local tf = type(f)
	if tf == "function" then
		_erroroutput = f
	else
		error (format ("Invalid type: expected `function', got `%s'", tf))
	end
end
```

通过这个成员，我们设定function来进行日志输出。

如果传入的msg不是字符串和数字，输出错误信息，提示需要string类型。

如果msg中包含"Missing page parameters"，则报错页面400；否则，报错页面500。

将msg规范格式后，记录日志。

**4part**

接下来看防路径穿越部分的代码。

```
local handle= function(map)
    local controller = map.controller;
    local action = map.action,page ;

    if(string.find(controller,"%.%.")) then -- 禁止路径回溯
        log:error("module forbidden:"..controller..",action:"..action) ;
        errorPages.forward403() ;
        return;
    end
    local ret ,err = pcall(function()
         page = require("web.routers."..controller);
    end)  
   
   if(not ret or page == nil or page[action] == nil) then
     log:error("route not found,controller:"..controller..",action:"..action..",err:"..(err or "")) ;
     errorPages.forward404();
     return;        
   end  
   --未登录
   local execRet,execErr = pcall(function()
       local res = page.beforeAction(page, controller);
       if(res == 1) then
           errorPages.forwardLoginTimeout();
           return;
       elseif (res == 2) then
           errorPages.forward403();
           return;
       end
        page[action](page);  
        page.afterAction(page);   
   end)
   if(not execRet) then
        errorPages.forward500(); 
        log:error(execErr or "");        
   end
end
```

通过string.find检查’controller‘中是否包含`..`来防路径穿越。

通过require包含需要的页面传递给page成员。

如果page为nil或者page对应action为nil则报错404。

其中page的beforAction方法在`/tmp/html/web/lib/page.lua`中定义

```
function M.beforeAction(self, controller)
    if (self.auth) then
        --[[session.open()+
         local sessData = session.getSessionData()
         if(not sessData.username) then
              return false
         end]]
        --未登录 unauthenticate.unauthenticate.lua文件不登录可以访问
        if(controller == "unauthenticate.unauthenticate") then
            return true;
        end
        M.currentUser = cgilua.servervariable("WEBMASTER_USER") or "";
        if (M.currentUser == "") then
            return 1;
        end
        local list = Utils.StringUtil.split(controller, "%.");
        local id = list[table.maxn(list)];
        local permission_user = permission_id[M.currentUser];
        if (M.currentUser ~= "admin" and (permission_onlyAdmin[id] or not permission_user)) then --无超级用户的权限 or 用户没有配置访问页面
            return 2;
        end
        if (M.currentUser ~= "admin" and permission_manage ~= "Disable" and permission_acOnlyAdmin[id]) then --无超级用户的权限 or 用户没有配置访问页面
            return 2;
        end
        if (not permission_map[id] or permission_user=="all" or  M.currentUser == "admin") then
            return true
        end
        if (type(permission_map[id])=="string" and permission_user[permission_map[id]]) then
            return true
        elseif (type(permission_map[id])=="table") then
            for k, v in pairs(permission_map[id]) do
                if permission_user[v] then
                    return true;
                end
            end
            return 2;
        else
            return 2;
        end
    end
    return true;
end

```

主要是鉴定权限，打开session。page的beforAction主要是关闭session。

```
function M.afterAction(self)
    if (self.auth) then
        -- session.close(self.updateSess)
    end
end
```

所以这一部分代码就是鉴权，对应超时401和forbidden403告警。

如果返回1则是超时401，返回2，则是禁止访问403。

在error.js中，如果403错误则跳转到index.htm。

**5part**

```
dispatcher.route{"/$controller/$action", handle};

--global_mom_util.run();

GLOBAL_IN = false
```

dispatcher的route在`/usr/local/lib/lua/5.3/cgilua/dispatcher.lua`

```
-- Defines the routing using a table of URLs maps or a single map
-- a map defines a URL mask using $name to extract parameters,
-- a function to be called with the extracted parameters and
-- a name for the map when used with route_url
-- @param table of maps or a single map
local function route(URLs)
	URLs = URLs or {}
	if type(URLs[1]) == "string" then
		-- accepts a single map as the only entry in a map table
		URLs = {URLs}
	end
    route_URLs = URLs
    local f, args = route_map(cgilua.script_vpath)

    if f then
        return f(args)
    else
        error("Missing page parameters")
    end
end
```

dispatcher的`router_url`也在这里定义。

```
-- Returns an URL for a named route
-- @param map_name Name associated with the map in the routed URL table.
-- @param params Table of named parameters used in the URL map
-- @param queryargs Optional table of named parameters used for the QUERY part of the URL
local function route_url(map_name, params, queryargs)
	local queryparams = ""
	if queryargs then
		queryparams = "?"..urlcode.encodetable(queryargs)
	end
	for i, v in ipairs(route_URLs) do
        local pattern, f, name = unpack(v)
        if name == map_name then
            local url = string.gsub(pattern, "$([%w_-]+)", params)
            url = cgilua.urlpath.."/"..cgilua.app_name..url..queryparams
            return url
        end
    end
end
```

## 尝试绕过认证

认证部分逻辑比较清晰，尝试看看能不能绕过认证。

针对路径穿越，可以尝试使用'\0'进行分割，这样`string.find()`方法就检测不到'..'

```
> url="index.htm/.\0./.\0./.\0./etc/passwd"
> return print(url)
index.htm/../../../etc/passwd
> return print (string.find(url,"%.%."))
nil
```

定位index.htm所在位置，确定web的根目录。

```
~/AC_11.9(2)B2P8/tmp/html/web/views$ ls
ac      error.htm  keeplive.htm  pub           robots.txt         timestamp.txt
common  images     main.htm      rgos_web.xml  test_update1.html  web_version.txt
css     index.htm  product.js    rg_web.xml    test_update.html   wlan_common
```

尝试访问`web_version.txt`等静态文件，成功访问，这样就能确定web的目录确实为`/tmp/html/web/views`

通过构造url，访问静态资源进行路径穿越，尝试绕过认证直接访问`main.htm`。

通过多次尝试，访问失败，不仅如此构造访问本来就可以访问的`index.htm`也失败了。

大概率是在别的地方也有过滤，后面确人在httpd.elf中对点号进行了处理。





## 部分js脚本分析

搜索两个数据包的url，主要关注一下`base.dao.js`和`sbin/httpd.elf`

```
$ grep -r -l "login.do"
tmp/html/web/views/ac/js/dilatation/dilatation.js
tmp/html/web/views/common/js/sysset/sysset.reset.js
tmp/html/web/views/common/js/sysset/sysset.reload.js
tmp/html/web/views/common/js/update/update.local.js
tmp/html/web/views/pub/dao/base.dao.js
sbin/httpd.elf
$ grep -r -l "web_config.do"
tmp/html/web/views/common/js/config/common.sea.config.js
tmp/html/web/views/pub/dao/base.dao.js
sbin/httpd.elf
```

`base.dao.js`主要是提供了一系列的功能接口，作为一个提供各种操作方法的库。

主要关注`authUser`方法，在`login.js`中进行调用。

```
pubDao.authUser(username, password, (function (result)
                {
                    $btnSubmit.prop("disabled", false).html(Resource["login.loginText"]);
                    if (result.code == 0)
                    {
                        $.cookie("oid", result.oid);
												......
                    }
                    else if (result.code ==- 1) {
                        $loginAuthTip.html(Resource["login.loginNetError"]).show();
                        return false
                    }
                    else
                    {
                        if (result.code == 11) {
                            that._setLoginTip("username", Resource["pub.loginrestriction"])
                        }
                        else {
                            that._setLoginTip("username", Resource["login.loginError"])
                        }
  											......
                    }
                }))
```

在点击登陆按钮之后触发，让我们看一下在`base.dao.js`中`authUser`的实现。

```
authUser : function (name, psw, callback)
        {
            var auth = this._makeAuth(name, psw);
            var reqParam = 
            {
                timeout : 3e3, actionUrl : "login.do", returnType : "String", auth : auth, errorFun : function (authResult) {}
            };
            if (callback)
            {
                this.request("url", "auth=" + auth + "\r\n", function (authResult)
                {
                    res = delauth(authResult);
                    callback && callback(res)
                }, reqParam)
            }
            else
            {
                var authResult = this.request("url", "auth=" + auth + "\r\n", false, reqParam);
                return delauth(authResult)
            }
            var self = this;
            ......
        }
```

通过`request`方法发送请求。

```
request : function (strCLIMode, strCLICommand, callBack, params)
        {
        		......
            if (strCLIMode == "config" || strCLIMode == "conf") {
                cliPostData = {
                    command : strCLICommand, mode_url : "config"
                }
            }
            else if (strCLIMode == "url")
            {
                if (!Util.isEmpty(params.actionUrl)) {
                    servUrl = params.actionUrl
                }
                cliPostData = strCLICommand
            }
            else if (strCLIMode === "action")
            {
               ......
            }
            else if (strCLIMode === "shell")
            {
               ......
            }
            else {
               ......
            }
            ......
            $.ajax(
            {
                url : "/" + servUrl, type : params.method, async : isAsy, timeout : params.timeout, dataType : params.dataType, 
                data : cliPostData, cache : false,
                success : function (data)
                {
                    data = data.replace(/Running this command may take some time, please wait\./g, "");
                    if (params.returnType === "Array") {
                        result = self.parseResult(data, params.trim, params.returnType)
                    }
                    else {
                        result = data
                    }
                    if (Util.isFunction(callBack)) {
                        callBack(result)
                    }
                },
								......
            });
						......
        }
```

在request方法中根据`strCLIMode`的不同进行不同的操作，最后通过`ajax`来发送请求。

在js中定义的post方法可以通过`ajax`发送对`lua`脚本调用的需求。

```javascript
this.postCli("/web/init.cgi/common.common.common/write", {
                    isDelay : JSON.stringify(isDelay), doNotDealError : true
                },function () {})
```

以上代码来调用`/tmp/html/web/routers/common/common/common.lua`脚本中的`write`方法。

```lua
/tmp/html/web/routers/common/common$ cat common.lua 
local cgilua = require("cgilua")
local Page = require("web.lib.page")
local Utils = require("web.lib.utils");
local log = require("web.lib.logger").log;
local json = require('cjson');
local errorPages = require("web.lib.error");
local M = setmetatable({},{ __index = Page })

function M.write(self)
    local params = cgilua.POST
    local isDelay = false;
    local cmd = "";
    if (next(params) ~= nil) then
         isDelay = params["isDelay"];
    end
    cmd = "delay-write\r\n";
    if isDelay then
        cmd = "write\r\n";
    end
    local cli_sess = require("rgcli").new(self.currentUser)
    cli_sess:exec(cmd)
    cli_sess:free()
    self.jsonOutPut(cli_sess.output or "");
end

return M;
```

进一步分析`http.elf`来理解其数据包处理逻辑。

## http.elf分析

**文件类型**

```
$ file ./sbin/httpd.elf 
./sbin/httpd.elf: ELF 64-bit MSB executable, MIPS, MIPS64 rel2 version 1 (SYSV), dynamically linked, interpreter /lib64/ld.so.1, for GNU/Linux 2.6.10, stripped
```

Mips64位的程序，使用IDA反编译失败，换用ghidra即可，我这里用ghidra9.2没成功，换成最新的ghidra10就可以了，我一般结合着IDA一起看。

搜索`login.do`定位其所在地址，搜索`12004ACA8`地址，定位url请求表。

```
.rodata:000000012004AC50 aOther:         .ascii "other"<0>
.rodata:000000012004AC56                 .align 3
.rodata:000000012004AC58 aLogoutDo:      .ascii "logout.do"<0>
.rodata:000000012004AC62                 .align 3
.rodata:000000012004AC68 aGetuserDo:     .ascii "getuser.do"<0>
.rodata:000000012004AC73                 .align 3
.rodata:000000012004AC78 aGetsessionidDo:.ascii "getsessionid.do"<0>
.rodata:000000012004AC88 aDownloadDo_0:  .ascii "download.do"<0>
.rodata:000000012004AC94                 .align 3
.rodata:000000012004AC98 aUploadDo_0:    .ascii "upload.do"<0>
.rodata:000000012004ACA2                 .align 3
.rodata:000000012004ACA8 aLoginDo:       .ascii "login.do"<0>
.rodata:000000012004ACB1                 .align 3
.rodata:000000012004ACB8 aWebConfigDo:   .ascii "web_config.do"<0>
.rodata:000000012004ACC6                 .align 3
.rodata:000000012004ACC8 aWebActionDo:   .ascii "web_action.do"<0>
.rodata:000000012004ACD6                 .align 3
.rodata:000000012004ACD8 aWebCliDo:      .ascii "web_cli.do"<0>
.rodata:000000012004ACE3                 .align 3
.rodata:000000012004ACE8 aAppCliDo:      .ascii "app_cli.do"<0>
.rodata:000000012004ACF3                 .align 3
.rodata:000000012004ACF8 aCgi_1:         .ascii "cgi/"<0>
.rodata:000000012004ACFD                 .align 5
.rodata:000000012004AD00 aFcgi:          .ascii "fcgi/"<0>
.rodata:000000012004AD06                 .align 3
```

每八个字节一个成员，均为对应字符串所在地址，通过`http_uri_enum_string`这个表来访问。

```
.data:0000000120065170                 .globl http_uri_enum_string
.data:0000000120065170 http_uri_enum_string:.dword aOther       # DATA XREF: LOAD:00000001200026C8↑o
.data:0000000120065170                                          # http_profiler_show+16C↑o ...
.data:0000000120065170                                          # "other"
.data:0000000120065178                 .dword aLogoutDo         # "logout.do"
.data:0000000120065180                 .dword aGetuserDo        # "getuser.do"
.data:0000000120065188                 .dword aGetsessionidDo   # "getsessionid.do"
.data:0000000120065190                 .dword aDownloadDo_0     # "download.do"
.data:0000000120065198                 .dword aUploadDo_0       # "upload.do"
.data:00000001200651A0                 .dword aLoginDo          # "login.do"
.data:00000001200651A8                 .dword aWebConfigDo      # "web_config.do"
.data:00000001200651B0                 .dword aWebActionDo      # "web_action.do"
.data:00000001200651B8                 .dword aWebCliDo         # "web_cli.do"
.data:00000001200651C0                 .dword aAppCliDo         # "app_cli.do"
.data:00000001200651C8                 .dword aCgi_1            # "cgi/"
.data:00000001200651D0                 .dword aFcgi             # "fcgi/"
```

在`http_uri_enum_string`的引用中，锁定函数`sub_120027B04`

在函数`FUN_120027b04`中对uri进行处理解析。

```c++
undefined8
FUN_120027b04(longlong param_1)

{
  undefined4 extraout_v0_hi;
  char *uri_path;
  size_t action_len;
  int iVar3;
  longlong lVar2;
  char *action_str;
  uint local_70;
  char *local_68;
  int index;
  char *local_48;
  char *path;
  undefined8 result;
  
  for (path = *(char **)(param_1 + 0x248); uri_path = path, *path == ' ';
      path = path + 1) {
  }
  local_48 = path;
  for (; ((*path != ' ' && (*path != '?')) && (*path != '\0')); path = path + 1)
  {
  }
  if (*path == '\0') {
    http_debug_bug_msg(3,"parse url fail");
    result = 0xffffffffffffffff;
  }
  else {
    *(undefined8 *)(param_1 + 0x120) = 0;
    if (*path == '?') {
      *path = '\0';
      path = path + 1;
      *(char **)(param_1 + 0x120) = path;
      for (; (*path != ' ' && (*path != '\0')); path = path + 1) {
      }
      *path = '\0';
    }
    else {
      *path = '\0';
    }
    path = path + 1;
    *(char **)(param_1 + 0x248) = path;
    uri_path = strstr(uri_path,"http://");
    if (uri_path != (char *)0x0) {
      local_48 = uri_path + 7;
    }
    uri_path = strchr(local_48,'/');
    if (uri_path != (char *)0x0) {
      local_48 = uri_path + 1;
    }
    *(char **)(param_1 + 0x108) = local_48;
    for (index = 1; index < 0xd; index = index + 1) {
      uri_path = *(char **)(param_1 + 0x108);
      action_str = *(http_uri_enum_string[index]);
      action_len = strlen(*(http_uri_enum_string[inedx]));
      iVar3 = strncmp(uri_path,action_str,action_len);
      if (iVar3 == 0) {
        *(int *)(param_1 + 0x1a8) = index;
        break;
      }
    }
    uri_path = strchr(*(char **)(param_1 + 0x108),'.');
    if (uri_path != (char *)0x0) {
      local_68 = strchr(uri_path,'/');
      if (local_68 == (char *)0x0) {
        local_70 = strlen(uri_path);
        local_68 = uri_path + (int)local_70;
      }
      else {
        local_70 = (int)local_68 - (int)uri_path;
      }
      lVar2 = (longlong)(int)local_70;
      uri_path = http_strnrchr(uri_path,'.',local_70);
      if (uri_path == (char *)0x0) {
        http_debug_bug_msg(3,"should not reach here",lVar2);
      }
      else {
        local_70 = (int)local_68 - (int)uri_path;
        if (9 < local_70) {
          local_70 = 9;
        }
        strncpy((char *)(param_1 + 0x2b8),uri_path,local_70);
      }
    }
    result = 0;
  }
  return result;
}
```

在`http_protocol_parse_request`函数中调用了上述函数，

对于登录流程，在`FUN_12003c2ac`函数中通过调用`http_protocol_parse_auth`获取auth字符串。

```c++
auth_str = (byte *)http_protocol_parse_auth
                                 (pcVar1,pcVar8,lVar7,pcVar9,param_5,param_6,param_7,param_8);
      if (auth_str == (byte *)0x0) {
        http_fun_free(pcVar1);
        *(undefined4 *)(local_28 + 0x148) = 10;
        iVar5 = http_protocol_response_psimple
                          (local_30,(longlong)local_28,lVar7,pcVar9,param_5,param_6,param_7,param_8)
        ;
      }
      else {
        memset(acStack120,0,0x20);
        uVar  3 = http_web_auth(auth_str,acStack120,(longlong)local_28,pcVar9,param_5,param_6,param_7,
                              param_8);
        ......
           }
```

成功解析auth字符串后，传入`http_web_auth`进行认证

```c++
while( true ) {
  password = puVar4 + -0x22;
  prefetch(*puVar4,6);
  if (puVar4 == (undefined8 *)(&DAT_1200685a0 + (longlong)index * 0x10)) break;
  iVar6 = strcmp((char *)password,(char *)psw);
  if (CONCAT44(extraout_v0_hi_01,iVar6) == 0) {
		......
    iVar6 = strcmp((char *)((longlong)puVar4 + -0x8f),(char *)loucal_auth);
    if (CONCAT44(extraout_v0_hi_02,iVar6) != 0) {
      ......//login fail process
      return 10;
    }
    *(undefined4 *)(puVar4 + 6) = 0;
    clock_gettime(1,(timespec *)(puVar4 + 2));
    pthread_mutex_unlock((pthread_mutex_t *)&DAT_120068560);
    iVar6 = strcmp((char *)(local_30 + 0x21),(char *)username);
    if (CONCAT44(extraout_v0_hi_03,iVar6) != 0) {
      printk_syslog_ext(5,"HTTPD","LOGIN",1,"User (%s@%s) login from eweb.",username,
                        local_30 + 0x48);
    }
    strncpy(loucal_buff,(char *)username,0x1f);
    return 0;
```

通过`prefetch()`获取密钥信息，然后通过`strcmp`去做比对，比较有特点是先比较密码再比较用户名。

# 登录和抓包分析

对登陆等一系列数据包进行抓包分析。

通过一些方法

登陆包。

```
POST /login.do HTTP/1.1
Host: 1.1.1.1
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:100.0) Gecko/20100101 Firefox/100.0
Accept: text/plain, */*; q=0.01
Accept-Language: zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2
Accept-Encoding: gzip, deflate
Content-Type: application/x-www -form-urlencoded; charset=UTF-8
X-Requested-With: XMLHttpRequest
Content-Length: 21
Origin: http://1.1.1.1
Connection: close
Referer: http://1.1.1.1/index.htm
Cookie: LOCAL_LANG_COOKIE=zh; UI_LOCAL_COOKIE=zh

auth=YWRtaW46YWRtaW4=
```

通过对`login.do`进行POST请求。

auth字段为前段`用户名：密码`的base64加密。

另外通过`web_config.do`进行POST请求。

```
POST /web_config.do HTTP/1.1
Host: 1.1.1.1
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:100.0) Gecko/20100101 Firefox/100.0
Accept: */*
Accept-Language: zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2
Accept-Encoding: gzip, deflate
Content-Type: application/x-www-form-urlencoded
Content-Length: 46
Origin: http://1.1.1.1
Connection: close
Referer: http://1.1.1.1/index.htm
Cookie: LOCAL_LANG_COOKIE=zh; UI_LOCAL_COOKIE=zh

command=show web-api custom_info&mode_url=exec
```



```
POST /web_config.do HTTP/1.1
Host: 1.1.1.1
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:101.0) Gecko/20100101 Firefox/101.0
Accept: text/plain, */*; q=0.01
Accept-Language: zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2
Accept-Encoding: gzip, deflate
Content-Type: application/x-www-form-urlencoded; charset=UTF-8
X-Requested-With: XMLHttpRequest
Content-Length: 34

command=show+version&mode_url=exec
```



```
HTTP/1.1 200 OK
Date: Mon, 06 Jun 2022 01:13:15 GMT
Content-Security-Policy: 
X-Frame-Options: SAMEORIGIN
X-Content-Type-Options: nosniff
X-XSS-Protection: 0
Content-Type: text/xml
Connection: Keep-Alive
Content-Length: 757

<?xml version="1.0" encoding="utf-8"?>
<webcli-print>
    <content><![CDATA[System description      : Ruijie Gigabit Wireless Switch(WS6108) By Ruijie Networks.
System start time       : 2022-05-06 13:58:50
System uptime           : 30:11:14:25
System hardware version : 1.14
System software version : AC_RGOS 11.9(0)B7, Release(05203023)
System patch number     : NA
System serial number    : G1M71LX000598
System boot version     : 1.2.11
Module information:
  Slot 0 : WS6108
    Hardware version    : 1.14
    Boot version        : 1.2.11
    Software version    : AC_RGOS 11.9(0)B7, Release(05203023)
    Serial number       : G1M71LX000598
]]></content>
    <return-code>0</return-code>
    <return-desc>Success</return-desc>
</webcli-print>
```



# 命令执行

lua脚本执行命令的语句一般出现在`os.excute()`和`io.popen()`

可以找到。

```shell
$ grep -r "io.popen"
web/lib/utils.lua:    local t = io.popen(cmd);
tmp/html/web/lib/utils.lua:    local t = io.popen(cmd);
sbin/ping.lua:io.popen('rg-tech-cli.elf \"exec\" \"debug arp ip '..destip..'\"')
sbin/ping.lua:local t1 = io.popen('rg-tech-cli.elf \"exec\" \"show arp '..destip..'\"')
sbin/auto_route/routelib.lua:    local cli_out = io.popen(input_cli)
sbin/auto_route/auto_update.lua:    local cli_out = io.popen("mkdir -p "..g_update_path)
......
$ grep -r "os.execute"
web/conf/appconfig.lua:    os.execute("mkdir "..config.log_path);
sbin/rglib.lua:    os.execute("sleep "..n)
......
```

`Utils.IoUtil.execShell()`也是能够执行命令。

```shell
$ grep -r "Utils.IoUtil.execShell"
tmp/html/web/routers/ac/system/system.lua:     Utils.IoUtil.execShell(cmd);
tmp/html/web/routers/ac/system/feature.lua:    ret.data = Utils.IoUtil.execShell(cmd)
tmp/html/web/routers/ac/system/acsystem.lua:     Utils.IoUtil.execShell(cmd);
tmp/html/web/routers/ac/feature.lua:    ret.data = Utils.IoUtil.execShell(cmd)
tmp/html/web/routers/ac/packet/capture.lua:    local rest = Utils.IoUtil.execShell(cmd);
tmp/html/web/routers/ac/sumng.lua:    local rest = Utils.IoUtil.execShell(cmd);
tmp/html/web/routers/common/system/reset.lua:        local rest = Utils.IoUtil.execShell("mv /data/.rgos/vsd/0/oam/"..filename.." /data/"..filename);
tmp/html/web/routers/common/download/download.lua:    Utils.IoUtil.execShell(cmd);
tmp/html/web/routers/common/update/update.lua:    local rest = Utils.IoUtil.execShell(cmd);
tmp/html/web/routers/common/detect/ping.lua:       ret.data = Utils.IoUtil.execShell(cmd);
tmp/html/web/routers/common/log/log.lua:    Utils.IoUtil.execShell(cmd);
tmp/html/web/routers/sw/update/update.lua:                Utils.IoUtil.execShell(cmd);
......
```

这边的命令注入漏洞不少，这部具体分析就不放在这了。





# 总结

这款设备跟其它锐捷的设备差不多，都是认证机制做的比较好，但认证后的命令注入的洞有不少，不过也是我分析的第一款lua脚本设备。

登录上去看到后台。

![3.png](https://www.iotsec-zone.com/images/MdImg/265c7c927d2a494188aa7a939473c37f.png)

![4.png](https://www.iotsec-zone.com/images/MdImg/eb5533a061cead9c62c5fc2230c65a1c.png)


![5.png](https://www.iotsec-zone.com/images/MdImg/61800b8e761afbf915bf730925ac40a5.png)

出差结束的时候打上去试了一下。所幸没把设备搞坏。
