# Linksys EA6100 固件解密分析
> 大中午啊
> 来源：https://www.iotsec-zone.com/article/13

# 0x01 前言

这一次来分享一个对固件解密的文章
在一次分析固件的过程中，看到了Linksys EA6100 的一款固件，很不幸，这款固件被加密了，这里接下来将固件解密的过程来做个梳理。

 

# 0x02 固件信息
首先在固件的下载界面查看固件的版本，这里有两个版本，先不管那么多，全都下载下来，拿到固件 “ FW_EA6100_1.1.6.181939_prod.gpg.img “ ，我看到固件名字，感觉很奇怪，第一次到固件以 “ .gpg.img” 为结尾的固件包，正常的固件包是以 “img”、“bin”、“chk” 为结尾。bing 搜索，发现只能搜到gpg的的相关信息，在了解完了gpg信息后，知道了这是一个为文件生成签名、管理密钥以及验证签名的工具。因此固件很有可能是使用GPG生成的密钥进行加密的。

 

# 0x03 判断是否被加密

这里介绍以下判断固件是否加密的一种方式。
我们使用的是binwalk来分析
根据binwalk的熵分析，可以看到固件处于加密的状态。

熵是用于表达混乱程度的名词，熵值可以表达系统中蕴含的能量，也可用于表达信息中的不确定性。

根据下面的图形可以了解到，“ FW_EA6100_1.1.6.181939_prod.gpg.img ” 固件的熵值几乎为1，属于高熵，说明固件处于被加密的状态。

![0.png](https://www.iotsec-zone.com/images/MdImg/7450b6db96d6d5ef78910e31f0e67c0c.png)

如下图所示，这是一个没有加密的NetGear WiFi拓展器的固件，可以看到熵值在有一个小片段有剧烈的上下波动，说明这部分的固件并没有被加密。

![1.png](https://www.iotsec-zone.com/images/MdImg/01f999dddd282aff62046123240f269f.png)
 

0x04 固件分析
使用binwalk 看一下固件的信息，因为固件被加密了，所以啥都看不到。

![2.png](https://www.iotsec-zone.com/images/MdImg/5de3101581296f4995fbd1fe1a7f56d5.png)

同时万能的 file 也识别不出来

![3.png](https://www.iotsec-zone.com/images/MdImg/4e4db2b24167fa264ca24f290faaee7a.png)

当我正在思考下一步该怎么做的时候，发现了下载固件页面中有这么一段话。

```
IMPORTANT: It is highly recommended to upgrade the firmware of your router using the Auto Update feature. However, if you prefer to do manual updates and your router is on 1.1.5.162431 or older, YOU MUST download & update your router using firmware version 1.1.5.172244 first before loading the latest firmware.
```

在更新最新固件的时候，需要先下载 Ver. 1.1.5 (Build 172244) 作为中间件，来升级到最新的固件，这个设备的最新固件就是Ver. 1.1.6，但是这个固件是加密的，一般来说，需要中间件的情况是用于提供密钥来解密最新的固件，并且FW_EA6100_1.1.5.172244_prod.img 中是没有 “gpg” 后缀的，说明这个固件并没有被加密，这样一来就说的通了。

根据实际的分析情况来看，这个固件确实没有被加密，可以识别出来文件系统是用 jffs2 压缩方式进行压缩的。
查看固件的组成结构

![4.png](https://www.iotsec-zone.com/images/MdImg/080bd8e7771f3a843ff0cf1df73fa5ba.png)

计算固件熵值

![5.png](https://www.iotsec-zone.com/images/MdImg/9e746ce1afd00498ce4edb2b66179ab6.png)

file 查看

![6.png](https://www.iotsec-zone.com/images/MdImg/5ae37b6d12fe880bf99bab57cfdfd747.png)

接下来我们直接使用 binwlk -Me 来提取固件jffs2-root 文件系统。

![7.png](https://www.iotsec-zone.com/images/MdImg/ed98c84b4572e28459926dc9038b9731.png)

我们将 Ver. 1.1.5 (Build 172244) 的固件成功解开了，在这里，我们先了解一下gpg 生成密钥的形式是什么样的。

![8.png](https://www.iotsec-zone.com/images/MdImg/c5900ab2be9eddec14a2587d5e329e5b.png)

然后我就在固件中包含pub 、rsa 字符串的文件，很不幸，一无所获，找到的都是一些无关的文件。
于是我开始检索一些其他的密钥保存的格式之后，一般都是下面的这种方式

```
——-BEGIN RSA PRIVATE KEY——- # 私钥内容
… (private key in base64 encoding) …
——-END RSA PRIVATE KEY——-
——-BEGIN CERTIFICATE——- # 证书信息
… (certificate in base64 PEM encoding) …
——-END CERTIFICATE——-
```

于是顺着这个思路，我终于找到了类似 gpg 密钥的文件了，幸运的 “ keydata ” 文件

![9.png](https://www.iotsec-zone.com/images/MdImg/e68917a4ec096a9c3c277fe61ffe625d.png)

首先将keydata 加载到 系统中的 gpg 中，然后再进行对固件包解密

![10.png](https://www.iotsec-zone.com/images/MdImg/e401c2eb06058a64a63d6f81a5d7636d.png)

我们成功的得到了解密后的文件，使用binwalk 识别一下固件的信息。

![11.png](https://www.iotsec-zone.com/images/MdImg/03f98abbc2b7e134746848623ce9a399.png)

现在用binwalk 就可以完全的解开固件包了

![12.png](https://www.iotsec-zone.com/images/MdImg/dd355873ab687e53b0584262edf27452.png)

 

# 0x05总结
本片文章主要是讲解对固件如何解密的一种方法，这种固件就是以前的固件没有加密，但是后面的固件加密了，在需要解密的情况下，就需要一个中间过渡版本的固件，这个过渡版本的固件中带有解密程序，然后对最新的固件进行解密。

这里还对固件的文件系统进行了简单的分析，虽然没有发现显著的漏洞，但是这里也简单描述一下。
在/etc/init.d/service_httpd.sh 文件中了解到了lighttpd是设备web组件，以及web组件启动的过程。
lighttpd 文件是在/usr/sbin/中
/etc/init.d/中包含了设备启动初始化所有的启动文件，并且包含一些密钥信息。
/www/ui/cgi/ 文件夹中有一些cgi 文件，但是经过分析，并没有发现有异常的风险点。
/www/ui/local 文件夹中主要包含的是路由器设备的前端的html一些文件。
逆向分析了一下lighttpd，并没有发现一些风险点，可能是对lighttpd 框架了解的不多，等拜读一下源码，了解那里是二次开发的地方，再来分析这个组件。
