# 从1day分析到0day挖掘
> ChaMd5
> 来源：https://www.iotsec-zone.com/article/372

# 前言
拿到一个iot设备，笔者比较喜欢先去看一下它的历史漏洞，也许可以从中得到一些启发。发现Cisco之前修补过这个系列设备的命令注入漏洞。

[https://sec.cloudapps.cisco.com/security/center/content/CiscoSecurityAdvisory/cisco-sa-rv-command-inject-BY4c5zd](https://sec.cloudapps.cisco.com/security/center/content/CiscoSecurityAdvisory/cisco-sa-rv-command-inject-BY4c5zd)

![0.png](https://www.iotsec-zone.com/images/MdImg/0e67d6e8aa0ba4cfa95b4c118dcbbed7.png)

# 1day分析
因为漏洞通告中有相关固件版本，于是我就去diff了一下修补前和修补后两个固件。

![1.png](https://www.iotsec-zone.com/images/MdImg/d2f2d2eb8d6f567bcd44d3e3c3a3c467.png)

在ssi.cgi这个文件当中，笔者发现修复之后的固件比修复前的固件多出了两个函数，那么大概率就是通过这两个函数对存在命令注入的地方加上了检查以修复命令注入漏洞。直接看一下修复之后的固件里的NK_CHECK_LANGUAGE函数。很明显，这个函数的作用是对参数进行了判断和设置，和我们预想的一致。那么旧版本固件中存在的命令注入漏洞大概率出现在这个函数的上层函数中。

![2.png](https://www.iotsec-zone.com/images/MdImg/85d2c19985e1ac0b542b6388ae4f3a02.png)

通过交叉引用，我们可以很轻松地找到其上层函数是NK_UiLanguageChange，我们看一下修补前的固件中的这个函数实现了什么功能。通过函数名，大体可以判断出这个函数的作用应该是切换界面的语言。这个函数首先获取了submitStatus和changelanguage的值，经过一些判断后，把changelanguage的值作为参数传进CreateFormatFile函数中。

![3.png](https://www.iotsec-zone.com/images/MdImg/780ebbb233a9d7118726980beeb81d16.png)

我们继续去看一下CreateFormatFile函数。很明显，这个函数由于传进来的参数param_1没有进过任何检查，存在一个命令注入漏洞。

![4.png](https://www.iotsec-zone.com/images/MdImg/bcf584b6311c24749ebe897b7852931c.png)

这个漏洞的修复方式也很简单，直接用NK_CHECK_LANGUAGE函数对参数进行了过滤。

# 捕获0day

**漏洞分析**

知道这个漏洞的前因后果之后，笔者就在想这个被修复之后的固件当中是否依旧可能存在一些没有过滤或者过滤不完整的地方。就去看了一些感觉可能存在漏洞的函数，后来就找到了NK_UiSetPassword这个函数，这个函数的作用是更改用户的密码。

![5.png](https://www.iotsec-zone.com/images/MdImg/803f5b91b3e5ecd85b39af44d6af4f45.png)

虽然这个函数中对参数进行了一定的过滤，但是这里对于危险字符过滤的并不是很严谨，所以这里也存在一个命令注入漏洞。

![6.png](https://www.iotsec-zone.com/images/MdImg/70e8e10efa5e869c44dcda5056c9a6ee.png)

其它地方应该也会存在不少类似的漏洞，但是笔者这里就没有继续去看了，感兴趣的师傅也许可以去找看看。Poc就帮师傅删了

### Notices

目前该漏洞已经提交给了思科厂商，思科已确认了该漏洞。[https://sec.cloudapps.cisco.com/security/center/content/CiscoSecurityAdvisory/cisco-sa-sb-rv01x_rv32x_rce-nzAGWWDD](https://sec.cloudapps.cisco.com/security/center/content/CiscoSecurityAdvisory/cisco-sa-sb-rv01x_rv32x_rce-nzAGWWDD)

![7.png](https://www.iotsec-zone.com/images/MdImg/d7bf59ebc4738a5dd7e38d46d494c535.png)
