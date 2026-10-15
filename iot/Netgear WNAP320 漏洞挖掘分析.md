# Netgear WNAP320 漏洞挖掘分析
> chan
> 来源：https://www.iotsec-zone.com/article/449

## 启动项分析

rcS 启动项中先去执行了/etc/generic_include.sh脚本；
然后遍历启动了init.d目录下以S开头的脚本和二进制文件；

![0.png](https://www.iotsec-zone.com/api/image/v2/20240801/d34k0bkazj0y4igkhv.png)
其中init.d下重点关注S045lighttpd.sh;

![1.png](https://www.iotsec-zone.com/api/image/v2/20240801/d34k1edjbzs8udi1au.png)
lighttpd.sh下主要说明了 服务开启支持的参数和携带的配置；

![2.png](https://www.iotsec-zone.com/api/image/v2/20240801/d34k1tao8xcwxibxly.png)

下面找到lighttpd.conf配置信息；
```
server.modules加载模块，这里加载了access和cgi模块；
server.document-root 表示定义的web服务访问的路径；
server.eerrorlog 定义的错误日志保存路径；
server.upload-dirs 定义允许上传文件的临时目录；
server.network-backend 指定了服务器使用的网络数据传输后端；
server.indexfiles  索引请求的文件；
```

![3.png](https://www.iotsec-zone.com/api/image/v2/20240801/d34k4zu1aoz19gudnt.png)

cgi.assign 根据请求的文件扩展名，选择对应的解析方式；

![4.png](https://www.iotsec-zone.com/api/image/v2/20240801/d34k5il7qsq1mtbt1z.png)

该配置表明https 访问启用 SSL 加密及证书路径；

![5.png](https://www.iotsec-zone.com/api/image/v2/20240801/d34k5u84ua46ny63m6.png)

通过分析了启动项和web的配置信息对web服务的流程有了一定的了解；
接下来就是对lighttpd的分析和漏洞挖掘；

固件模拟前用firmwalker扫了一遍，看看又没有敏感信息；
可以看到下面的默认账号密码明文；
然后把将前端页面整理成字典丢burp上去跑看看有无未授权界面；

![6.png](https://www.iotsec-zone.com/api/image/v2/20240801/d34k6j4sb3npqocexj.png)

## 固件模拟：
FirmAE模拟固件

![7.png](https://www.iotsec-zone.com/api/image/v2/20240801/d34k72vj8ux0sh974c.png)

访问下界面成功；

![8.png](https://www.iotsec-zone.com/api/image/v2/20240801/d34k7o1688igprpecf.png)

## 漏洞分析
需要授权登录，顺着错误信息去追踪，因为有些固件password存在设备目录下，还是明文；
追踪到只存在common.php文件当中并通过checkPassword 这个函数去校验密码，

![9.png](https://www.iotsec-zone.com/api/image/v2/20240801/d34k8gg6e23hcblkce.png)

继续去追踪checkPassword这个函数是在哪里定义的，发现这个函数也是在common.php中定义的，

![10.png](https://www.iotsec-zone.com/api/image/v2/20240801/d34k9exid13jvqpnad.png)

上面看出password是从getPassword和getDefaultPassword这2个函数中去获取的，继续往下走发现

![11.png](https://www.iotsec-zone.com/api/image/v2/20240801/d34k9rfido8dlxozxs.png)
getDefaultPassword是直接从/etc/default-config或configSave.cfg这2个文件去获取password的，
default-config 文件下还保存了设备的默认配置信息；

![12.png](https://www.iotsec-zone.com/api/image/v2/20240801/d34kace76sgo6gismm.png)

getPassword是通过调用conf_get去获取password ;到这里conf_get追踪下去基本都是调用，同时发现它在二进制文件当中，它应该是一个封装在二进制里面的函数，

![13.png](https://www.iotsec-zone.com/api/image/v2/20240801/d34kb4bnuzvtnzqlho.png)

跟踪到最后还是无果，但是根据前面的分析password确实是保存在文件当中，这里先暂时放一下，
先去分析web上的信息

接下来burp抓下包，随便爆破下未授权登录界面；
看来不简单，很多状态码都是200；也没有好方法，觉得一个个去看也不是不行；

![14.png](https://www.iotsec-zone.com/api/image/v2/20240801/d34kdn60ch281fmhey.png)

发现了有个交互界面，先copy下url，继续往下翻翻；

![15.png](https://www.iotsec-zone.com/api/image/v2/20240801/d34kdy46ppzb6mtpvs.png)

又出现一个，感觉有点东西；再继续往下看看；

![16.png](https://www.iotsec-zone.com/api/image/v2/20240801/d34ke6h82nqw0hxkci.png)

后面在help页面也能看见默认密码：
往后看完没有发现什么可控的页面；

![17.png](https://www.iotsec-zone.com/api/image/v2/20240801/d34keii69vokpmerle.png)

现在回头看前面的交互界面，习惯性的echo了一串字符，页面直接报错；

![18.png](https://www.iotsec-zone.com/api/image/v2/20240801/d34kew53lxx8qnmtbh.png)

接下来跟进到boardDataWW.php文件，分析后发现里面是一段PHP和html的代码；

![19.png](https://www.iotsec-zone.com/api/image/v2/20240801/d34kfsbclgubew8vom.png)

上面php代码，主要是处理`macAddress` 和 `reginfo` 参数，通过exec执行系统调用；
这里就直接命令注入；
通过分析代码这里对macAddress值和reginfo的值做了判断；
这里ereg的大致意思是正则表达0-9,a-f.A-F,取12位判断，如果匹配是过滤的内容就返回true，
这里貌似没有校验长度，只校验了12位，那么12位后面的内容是否可以作为命令执行；

![20.png](https://www.iotsec-zone.com/api/image/v2/20240801/d34kic0p7zeuqvjhgd.png)

接着看html部分的代码，看名字是一个对mac的检查功能的一个前端界面；
大致意思就是只能输入12位，否则就会提示：
但是对发包静默请求的话并不会因此受到限制，

最后是一个表单提交的方式和位置，以及下面页面按钮Submit时候调用checkMAC 检查；

![21.png](https://www.iotsec-zone.com/api/image/v2/20240801/d34kj144s16lx7igbc.png)

![22.png](https://www.iotsec-zone.com/api/image/v2/20240801/d34kjapnfadvyeyj5r.png)

通过上面对php分析只要前12位匹配，后面的就可以构造执行命令；
接下来开始构造post请求测试；
结果成功注入；

![23.png](https://www.iotsec-zone.com/api/image/v2/20240801/d34kk6uhs3bfgqwpzu.png)
![24.png](https://www.iotsec-zone.com/api/image/v2/20240801/d34kkg1dvivwvszuhb.png)

通过上面php代码分析boarDataNA.php也同样存在命令执行；
经过测试也成功写入；

![25.png](https://www.iotsec-zone.com/api/image/v2/20240801/d34kl1z6dse9qlyma8.png)
![26.png](https://www.iotsec-zone.com/api/image/v2/20240801/d34kl65irgvqanrnnh.png)

最后还是没分析出password存放的位置，通过经验判断也可能存在临时文件里面，抱着试试的心态去看了下临时文件存放的东西，最后定位了unique这个可疑文件；

![27.png](https://www.iotsec-zone.com/api/image/v2/20240801/d34km4z7vslbdmdswe.png)

通过命令执行去查看了里面的内容，设备的配置信息包括账号密码全保存在这里；

![28.png](https://www.iotsec-zone.com/api/image/v2/20240801/d34kmnjvq576oqnhdh.png)

最后是找到了账户信息，但是自己还是没有能通过分析去定位到为什么在这个文件；
有分析过的大佬可以分享下，学习学习；

## 总结：
这是一个直接php的命令注入，漏洞可以单纯的通过做信息收集的时候发现；
该漏洞点主要在php代码中`ereg("[0-9a-fA-F]{12,12}", $_REQUEST['macAddress'],$regs)`
这段代码，{12,12} 表示前面的字符集必须恰好重复12次，并没有限制长度所导致；

## 修复方案：
对$_REQUEST['macAddress']的长度进行判断长度超过12直接failed处理

```php
$macAddress = $_REQUEST['macAddress'];
if (strlen($macAddress) <= 12) {
    if (preg_match("/^[0-9a-fA-F]{12}$/", $macAddress, $regs)) {
        echo "MAC地址有效：$macAddress";
    } else { 
        echo "MAC地址无效：$macAddress";
    }
} else {
    echo "MAC地址长度超过12个字符";
}
```
