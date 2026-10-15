# 物联网安全从零开始-BIG-IP CVE漏洞分析
> Pachimker
> 来源：https://www.iotsec-zone.com/article/334

# 背景
2022年11月16日，F5官方公布了F5 BIG-IP和BIG-IQ设备中的多个安全漏洞。其中高危漏洞（CVE-2022-41622，CVSS评分8.8）是iControl SOAP跨站点请求伪造，可允许未经身份验证的远程代码执行攻击。高危漏洞（CVE-2022-41800，CVSS评分8.7）为iControl REST远程代码执行漏洞，允许经过身份验证的管理员用户通过RPM注入执行任意代码。

![0.png](https://www.iotsec-zone.com/images/MdImg/21a64c11eae0ddac173a5a796ead3bb4.png)

受CVE-2022-41622影响的版本为：

```
BIG-IP:17.0.0
BIG-IP:16.1.0-16.1.3
BIG-IP:15.1.0-15.1.8
BIG-IP:14.1.0-14.1.5
BIG-IP:13.1.0-13.1.5
BIG-IQ:8.0.0-8.2.0
BIG-IQ:7.1.0

```
受CVE-2022-41800影响的版本为：

```
BIG-IP:17.0.0
BIG-IP:16.1.0-16.1.3
BIG-IP:15.1.0-15.1.8
BIG-IP:14.1.0-14.1.5
BIG-IP:13.1.0-13.1.5

```
BIG-IP 设备默认有俩个用户(终端用户和web用户)，在配置设备信息时由于系统对web端用户的密码没有什么严格要求(如必须数字、字母组合、特殊符号等等)，可能会导致攻击者可以爆破出web端用户密码，加上今年5月刚爆出的CVE-2022-1388未授权绕过漏洞几乎为同型号设备，这就使得俩个web用户导致的pre-auth漏洞很容易被利用。

# 环境搭建

本小节使用的漏洞环境固件为BIG-IP，漏洞版本号为16.1.0。在靶场中调用BIG-IP后，BIG-IP会自动分配出mgmt口的IP地址。

![1.png](https://www.iotsec-zone.com/images/MdImg/f3a852e91ca491ec61013e2a6a9f9906.png)

在浏览器端使用(admin/admin)登录后，如下图所示：

![2.png](https://www.iotsec-zone.com/images/MdImg/9140dc9f120b7e4654bea7c981f4df3a.png)

# 漏洞分析

BIG-IP的管理模式有多种，包括web页面，tmsh命令行，rest api，以及soap api。soap api数据交换格式为soap/xml。rest api数据交换格式使用http/json。soap api为比较旧的技术，在版本11.6中已经放弃维护，目前支持正常使用，rest api目前官方一直在推荐用户使用和开发。cve-2022-41622为csrf漏洞，漏洞本身危害不大，但是由于在漏洞利用过程中可以使用soap api接口进行操作从而rce。cve-2022-41800为iControl rest容易受到rpm注入攻击导致rce。

明白了漏洞利用的方法，下面我们开始分析。进入BIG-IP终端，BIG-IP默认开启ssh服务，我们可以使用"scp -r root@ip:/* ./"命令将BIG-IP的所有文件拷贝到本地进行分析。BIG-IP中程序运行的httpd服务为apache

![3.png](https://www.iotsec-zone.com/images/MdImg/49efb2b3057dd826a219c853156fa91a.png)

### CVE-2022-41800

我们在"etc"目录简单查看一下，在"init.d"目录下发现了httpd启动服务的httpd脚本，脚本注明为apache server并且配置文件的位置为"/etc/httpd/conf/httpd.conf"。

![4.png](https://www.iotsec-zone.com/images/MdImg/3ecdb2144a28bae9b400b7d69ea58279.png)

查看一下配置文件，我们发现httpd接受请求，并将请求转发到不同端口的服务上完成对应的处理。下图中AuthPAM开启，说明调用了httpd的某个".so" 文件进行预先的认证，并且将所有向 /mgmt 发送的请求都转发到了 "http://localhost:8100/mgmt/"。

![5.png](https://www.iotsec-zone.com/images/MdImg/397d1a404b56679accd3ba2d8963e366.png)

在16.1.0的官方文档中，简单翻阅我们得知所有REST API的uri中都是含有 "mgmt" 的。

![6.png](https://www.iotsec-zone.com/images/MdImg/518f8f338a8276161c0e9ad52fca19c7.png)

查看一下8100端口的服务，发现有java服务在监听

![7.png](https://www.iotsec-zone.com/images/MdImg/c282e6f182028fad773d2e339c5062d7.png)

查看一下pid信息，发现java的"-classpath"参数后为"usr/share/java/rest"和"usr/share/java/rest/libs"目录下的所有jar包，且"--port"参数为8100。

![8.png](https://www.iotsec-zone.com/images/MdImg/754755cb40671f5ec6b044763e0b1d21.png)

如果要动态调试java程序，我们可以修改"etc/bigstart/scripts/restjavad"，在jvm_options后附加"-agentlib:jdwp=transport=dt_socket,address=1043,server=y,suspend=n"选项，并且使用Idea配置好ip、port后进行远程调试。

    注意：防火墙默认策略为禁止，动态调试需要放行调试端口

![9.png](https://www.iotsec-zone.com/images/MdImg/3f3962f5f6372bfc46183f66251f8068.png)

RestServerServlet 是整个 iControle REST 的入口，在其"service"方法中"RestServerServlet" 异步执行，注册了一个 "ReadListener"。而且会在处理请求时，为每一个请求创建了一个 "RestOperation"，并且后续处理将以回调的方式执行。

![10.png](https://www.iotsec-zone.com/images/MdImg/291c0b1a728f2e1247dc76ff2f737ae1.png)

 这里会检测请求中是否包含相关认证，并将其设置到 "RestOperation" 中。

![11.png](https://www.iotsec-zone.com/images/MdImg/1fc83a8863c981fc35a4413de1c54416.png)

调用setIdentityFromBasicAuth方法后，并且basic认证的value不为空便会进入setIdentityData，在比较userName和userReference都不为空时，最后在completeEvaluatePermission中比较完成后完成身份认证过程。

![12.png](https://www.iotsec-zone.com/images/MdImg/f505d694c6833005725eede349366f99.png)

随后"trySendInProcess" 中会根据请求端口来寻找相关的 "RestWorker" 。在 findWorker() 方法中，将以请求路径为查询条件，匹配 RestServer 的 pathToWarkerMap 。之后便会执行 worker.onRequest() 方法，将worker添加到 RestServer.readyWorkerSet 中。后面会以该 Set 为消费者队列，并执行各个worker。

![13.png](https://www.iotsec-zone.com/images/MdImg/3bee860e2cf432c37b07837242db47ed.png)

"RestServer" 中主要工作是维护队列，并执行相关的worker。入口点为其构造方法：

![14.png](https://www.iotsec-zone.com/images/MdImg/8f18a0a005f413fbee958cc91fa145f4.png)

processQueueRequests后面运行到 "callDerivedRestMethod" 方法，这里便会调用对应worker的处理方法并完成对应的链调用。

![15.png](https://www.iotsec-zone.com/images/MdImg/6cc8733509ea70afc35e51fe7b9e127e.png)

在官方文档中，有开发编写worker的例子，流程如下，在worker中我们发现WORKER_URI_PATH为uri中/mgmt/"后面的的地址。

![16.png](https://www.iotsec-zone.com/images/MdImg/de99779dbe45459f9c599527523c70e0.png)

 根据"WORKER_URI_PATH"字符串，我们可以简单搜索一下系统中的worker，结果如下图所示。这里WORKER_URI_PATH为"shared/iapp/rpm-spec-creator"就是生成spec文件的worker

![17.png](https://www.iotsec-zone.com/images/MdImg/49f2c2db3c230d14cfc0fdf889718b5e.png)

打开"iAppRpmSpecFileCreatorWorker.js"worker的文件，发现加载了"../infrastructure/specFileCreator"模块，并使用SpecWriter变量调用，随后new了一个specWriter

![18.png](https://www.iotsec-zone.com/images/MdImg/6a5d80f34201b90ed3d3c010fa63b7ee.png)

 java中的onPost方法传进来的restOperation，先getBody获取内容，并且调用_validate进行判断，随后使用specWriter.render进行格式化，最后调用getFs().writeFile生成".spec"文件

![19.png](https://www.iotsec-zone.com/images/MdImg/b7a541244a8741c9eb95ecbf78f50674.png)

 生成spec文件的名字如下。

![20.png](https://www.iotsec-zone.com/images/MdImg/0d791074e7e1b6a59d5b14e6b179ffb7.png)

_validate对传进来的内容进行判断，如判断body是否为空，header是否存在"application/json"，取出specFileData的json内容并进行判断，判断是否有name、summary、version、release、description、srcBasePath字符等等。这里便是漏洞点，漏洞成因便是没有对用户传来的json数据进行判断，导致攻击者可以通过"\n"特殊字符进行绕过。

![21.png](https://www.iotsec-zone.com/images/MdImg/5e7b189428f18a8333bd164075182f67.png)

在进行格式化时，使用specFileCreator.js模块。这里使用了doT.js模板，模板path为"./resources"。doT.js 灵感来源于搜寻基于 V8 和 Node.js ，强调性能，最快速最简洁的 JavaScript 模板函数。它在 Node.js 和浏览器两端都彰显出卓越的性能。下图中specFileData调用specTemplate格式化json数据

![22.png](https://www.iotsec-zone.com/images/MdImg/4506ae447e70b7944dea0eb416c41c2a.png)

doT.js模板如下，当攻击者传来的数据"description"后面跟着"\n"是，spec文件就变得攻击者可控，可随意添加恶意数据，如调用"%check\n'command'"执行系统命令。

![23.png](https://www.iotsec-zone.com/images/MdImg/b2983761ea7a589b5f7b98ce619230ff.png)

当我们再次通过rest api进行build-package 时，就会执行spec文件中的恶意命令

![24.png](https://www.iotsec-zone.com/images/MdImg/f093d0dfd67a4dfc742b577f7f0ad91c.png)

### CVE-2022-41622

  CVE-2022-41622为CSRF漏洞，CSRF漏洞的成因是网站的已认证通过信息在浏览器中一段时间内不会过期，以后只要是访问这个网站，会默认用你已经通过的认证信息来进行，所以不用再次登录。如果攻击者发送了构造好的CSRF脚本或包含CSRF脚本的链接，管理者点击后可能会执行恶意操作（比如是添加账号、获取信息等）。

漏洞程序为 "/iControl/iControlPortal.cgi"，并且该程序为suid权限。

![25.png](https://www.iotsec-zone.com/images/MdImg/1e8c83668301c86e8976913cfa1e73d0.png)

csrf漏洞本身的成因比较简单，没有对Content-Type以及Referer进行验证，以及Token机制不完善。

![26.png](https://www.iotsec-zone.com/images/MdImg/3bb632137109b5cedc319f75957cee55.png)

下面说一下漏洞利用。在前面我们已经分析了CVE-2022-41800漏洞，这里的CVE-2022-41622与前面的利用过程类似，这里只不过是利用soap api进行发送soap请求。当我们在http中用soap方式发送xml数据去调用一个服务时，我们只知道通用的http协议的传参方式还是不够的，我们仍然需要知道目标服务的接口文档。在soap中每个服务都有的接口文档就是一个用wsdl规范编写的wsdl文档，当程序接收到soap请求后根据wsdl文档进行解析执行。

![27.png](https://www.iotsec-zone.com/images/MdImg/7769b2f01488dd8f0736a9338cd65e66.png)

下图为添加用户请求的wsdl文件为"Management.UserManagement.wsdl"

![28.png](https://www.iotsec-zone.com/images/MdImg/d4c1a6bd06d20e73818971ac03273c60.png)

这样我们在pre-auth的情况下就可以发送创建用户的请求来创建用户，当然我们也可以构造其他的请求（如上传文件）

![29.png](https://www.iotsec-zone.com/images/MdImg/e19efb19cd16223bd13ce42e289ea8be.png)

# 漏洞复现

### CVE-2022-41800

  使用rest api调用rpm-spec-creator创建spec文件并查看。

![30.png](https://www.iotsec-zone.com/images/MdImg/e80f2f24763b1bac5e1538ff712205fd.png)

使用"nc -lvp 4444"命令监听4444端口

![31.png](https://www.iotsec-zone.com/images/MdImg/7d60bf633ec9eff4997b2b0c7525c7f7.png)

使用rest api调用build-package 构建package包裹。

![32.png](https://www.iotsec-zone.com/images/MdImg/2fc655a3bb58cfd4399fa7a35109154d.png)

此时已经获到shell，并且是root权限。

![33.png](https://www.iotsec-zone.com/images/MdImg/3710c104aac5c6433f3401c2b9659971.png)

### CVE-2022-41622

将csrf.html目录使用python启动http服务

![34.png](https://www.iotsec-zone.com/images/MdImg/c42b96291d769a9f75c1640eafdb9cff.png)

假设管理员使用账号密码登录BIG-IP web管理页面，此时点击了我们启动http服务的链接，链接自动跳转到"https://192.168.141.152/iControl/iControlportal.cgi"并提交soap请求

![35.png](https://www.iotsec-zone.com/images/MdImg/39b974ad836de0f1e42db8f9f39ba755.png)

用户已经添加成功

![36.png](https://www.iotsec-zone.com/images/MdImg/a5bce7aa8f2317bfe4aefbdbd2008228.png)

 使用我们设置好的用户名和密码进行登录。

![37.png](https://www.iotsec-zone.com/images/MdImg/112065007d67903c9ab60605ae4b0291.png)

# 总结

这一小节，我们简单分析了F5设备的俩个pre-auth漏洞，了解了rpm注入和csrf漏洞产生原因。并且在此过程中我们简单学习F5设备中 soap接口和rest接口的区别以及利用。
