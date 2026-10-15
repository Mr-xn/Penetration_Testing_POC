# 固件CGI分析手法（二）
> Ayaka
> 来源：https://www.iotsec-zone.com/article/195

#[前文回顾](https://www.iotsec-zone.com/article?id=194)
我们跟随cgi执行流程来到了label 47，然后分析了cJSON_Parse和websGetVar函数的功能
![0.png](https://www.iotsec-zone.com/images/MdImg/005bea28c03a8c711befa4d050774a3c.png)

接下来我们继续分析cgi是如何在这里分发路由器web界面众多按钮对应的众多功能的

#正文

首先我们看这部分结构，通过strstr函数来判断v27中是否包含get字样

![1.png](https://www.iotsec-zone.com/images/MdImg/066932b8d13212d05c6e06f1ae5dd92c.png)

这里的v27来自于json数据中的topicurl字段，即执行的函数名
![2.png](https://www.iotsec-zone.com/images/MdImg/4648ad6c878effe3560cd968a7d9b9f8.png)

如果要执行的函数名中带有get字样，则会进入一个while循环，不断的在一个函数表结构中去对比函数名和函数表中的字符串，如果相等则跳转到函数表中对应的函数地址去

![3.png](https://www.iotsec-zone.com/images/MdImg/59080ad9f0fa363d6e9e8da78004563c.png)

接下来我们道函数表中查看一下结构如何：
![4.png](https://www.iotsec-zone.com/images/MdImg/cefad521a10f2506756b24f75378ff68.png)
可以看到函数表中充斥着这种一块一块的数据，通过之前的分析我们得到的结论是程序会在一个while循环中不停的把topicurl参数和函数表中的函数名做比较，如果比较成功则选择到对应的函数地址并跳转过去，所以函数表中应该存有两个东西，一个是函数名一个是函数地址，只不过IDA中并没有恢复出来，所以我们看到的是单字节的数据，可以通过快捷键d手工的改变一下数据类型来恢复出结构
![5.png](https://www.iotsec-zone.com/images/MdImg/83bf7a36eb17c7215f78f3ae49d74fa3.png)

恢复完的效果如上，而类似的函数表结构共有三个，分别代表了路由器函数中的三大类：
* **get类函数族**
![6.png](https://www.iotsec-zone.com/images/MdImg/c0482a7c9e2e7ad2db2af7d730d79feb.png)

* **set类函数族**
![7.png](https://www.iotsec-zone.com/images/MdImg/1924279427be1f32b8c1077a16d4c16a.png)

* **del类函数族以及杂项函数**
![8.png](https://www.iotsec-zone.com/images/MdImg/2c20a6142be32daae820dbae09491065.png)

首先来分析一下get类函数的运行机制，从最基本的函数getInitCfg入手，首先我们要清楚这个函数在什么情况下会被调用：
![9.png](https://www.iotsec-zone.com/images/MdImg/a54c2d3c3411184958cbbc8e1779b676.jpg)

当我们进入到路由器的基本设置的首页时，会发现这里显示了很多路由器的基本设置信息，比如固件版本，运行时间，MAC地址等等，那么这些信息是如何从固件中传到web界面来的呢？我们抓个包试试

```
POST /cgi-bin/cstecgi.cgi HTTP/1.1
Host: 192.168.0.1
Content-Length: 25
Accept: application/json, text/javascript, */*; q=0.01
X-Requested-With: XMLHttpRequest
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36
Content-Type: application/x-www-form-urlencoded; charset=UTF-8
Origin: http://192.168.0.1
Referer: http://192.168.0.1/basic/index.html?time=1660284636980
Accept-Encoding: gzip, deflate
Accept-Language: en-US,en;q=0.9
Cookie: SESSION_ID=2:1591951493:2
Connection: close

{"topicurl":"getInitCfg"}
```

可以看到，程序通过POST请求，向cstecgi程序提交了一个请求，其中函数名参数topicurl为getInitCfg，再来看看响应包中有什么信息：
![10.png](https://www.iotsec-zone.com/images/MdImg/0e4200de4e737e6ef759b3bad4eb3902.jpg)

可以看懂啊响应包中有一个json格式的数据，其中包含了大量的路由器基本信息，也就是说我们在web界面看到的信息，经历了这样一个流程：

用户点击首页，web界面设置好所用方法以及正确的参数，构造请求包，发给cgi程序，cgi程序接收到请求之后，通过topicurl,确定要执行的函数，执行对应的函数后，构造响应包产生响应，给前端提供所需信息。

接下来我们来分析getInitCfg是如何执行的：
![11.png](https://www.iotsec-zone.com/images/MdImg/f76106e978cb503fbb7305aa03b8d974.png)

首先程序调用了cJSON_CreateObject创建了一个json对象，这个函数具体在哪实现如何实现，上篇文章已经说过了如何看，有兴趣的话可以看看。

然后初始化了几个字符串变量，接下来的几乎所有字符串都通过它来处理
![12.png](https://www.iotsec-zone.com/images/MdImg/3aba5c51849e7ea73d5ddc9f02623d0a.png)

然后通过apmib_get函数获取所需数据到指定变量中

接下来通过cJSON_CreateString函数和cJSON_AddItemToObject函数将装有指定数据的字符串添加到json对象中
```
cJSON_AddItemToObject(Object, "model", String)
```
可以通过参数很明显的看出来，第一个参数应该是要添加到哪个json对象中，第二个参数则是添加的item的key，第三个参数则是item的value

![13.png](https://www.iotsec-zone.com/images/MdImg/9d695ba0f1765df5c6699454a9a1431f.png)

一个变量用过之后可能会通过memset函数重复使用
![14.png](https://www.iotsec-zone.com/images/MdImg/6f5145cbf16182544c0b27b3cb0249a8.png)

getInitCfg函数不断的重复上述过程，将所有所需数据形成一个json对象，这就是我们在响应包里看到的这个东西
![15.png](https://www.iotsec-zone.com/images/MdImg/5e75a38cae28bebfc730155ee23b405a.png)

分析到这里其实我们可以发现，所有get族的函数，其实都是在获取信息，那么意味着什么？我们可操作的空间很小，即用户的数据基本无法对这些get族的函数产生什么影响，所以漏洞一般来说很少发生在get族的函数中，接下来我们看看set族的函数又是如何做的

这里选择一个短小精悍的修改密码功能：
![16.png](https://www.iotsec-zone.com/images/MdImg/ee4989297dc604d82f3be4c41839def4.png)

通过抓包来分析一下请求包结构：
```
POST /cgi-bin/cstecgi.cgi HTTP/1.1
Host: 192.168.0.1
Content-Length: 80
Accept: application/json, text/javascript, */*; q=0.01
X-Requested-With: XMLHttpRequest
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36
Content-Type: application/x-www-form-urlencoded; charset=UTF-8
Origin: http://192.168.0.1
Referer: http://192.168.0.1/advance/changepwd.html?time=1660289682741
Accept-Encoding: gzip, deflate
Accept-Language: en-US,en;q=0.9
Cookie: SESSION_ID=2:1591956512:2
Connection: close

{
"admuser":"admin",
"admpass":"bbb",
"origPass":"aaa",
"topicurl":"setPasswordCfg"
}
```
这里发现，其实请求包只有用户名，原密码，新密码以及执行函数名，并没有前端页面中所谓的确认密码，所以可以看出来这里的确认密码部分是由前端来完成的。

然后来看看setPasswordCfg函数长什么样：
![17.png](https://www.iotsec-zone.com/images/MdImg/0723f7556123d1d3e3fa787756db58b9.png)

可以看到程序首先通过websGetVar函数获取请求包json数据中的各个变量，然后通过apmib_get函数获取存储在后端的密码，放到v9变量里，然后比较一下用户在前端输入的origPass，是否能和后端存储的密码匹配上，如果不匹配说明用户输入了错误的原密码，所以跳到else的逻辑中，创建一个json对象，添加一个item，其key为success，value是false，这里我们可以来试一下是不是我们分析的这样，首先随便输入个原密码和新密码，然后获取响应包：
![18.png](https://www.iotsec-zone.com/images/MdImg/2265cc65b3f4554922874a2d1b2595d8.jpg)

和我们分析的结果一致，然后再来看看当输入的原密码和存在本地的密码匹配上之后，程序做了什么：
![19.png](https://www.iotsec-zone.com/images/MdImg/e4ae9fc43e83f589f81dc491e78088a7.png)

程序通过apmib_set函数，将用户名和新的密码写入到本地，然后调用了一个函数，点进去可以看到实际上调用的是apmib_update：
![20.png](https://www.iotsec-zone.com/images/MdImg/55c884cd91bcd7fa19027ba0d19afe48.jpg)

到这里已经成功更新了admin用户的密码，接下来是构造响应包：
![21.png](https://www.iotsec-zone.com/images/MdImg/600cf6bb6c47f1f86a48adbe6a9c3dd7.png)

所以可以看到，set族的函数是受到用户输入影响比较大的，同时也意味着是比较容易出现各类溢出以及命令注入等漏洞的，笔者从买来这款路由器到现在两周左右的时间，已经上报了十余个漏洞，涵盖溢出，信息泄露，命令注入等等方面，基本上都是出现在set族函数中。

del族的函数以及杂类的函数就不再展开分析了，除了具体的处理逻辑之外整体上的分析方法和上面两种区别不太大，留给读者自行尝试，下一篇文章将拿出一部分我上报的漏洞，从固件分析入门走向漏洞挖掘实战。
