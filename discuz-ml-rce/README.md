dz-ml-rce.py ：discuz ml RCE 漏洞检测工具
==
----------------


# 概述
<br/>
漏洞在于cookie的language可控并且没有严格过滤，导致可以远程代码执行，详情参考

[discuz ml RCE漏洞重现及分析](http://www.lsablog.com/networksec/penetration/discuz-ml-rce-analysis/)

<br/>
本工具支持单url和批量检测，有判断模式（只判断有无该漏洞）、cmdshell模式（返回简单的cmd shell）和getshell模式（写入一句话木马）。


----------------

# 需求
<br/>
python2.7<br/>
pip -r requirements.txt
<br/><br/>

**使用时加上漏洞PHP页面（如forum.php,portal.php），直接写域名可能会重定向导致误报!**

----------------

# 快速开始
<br/>
使用帮助<br/>
python dz-ml-rce.py -h<br/>

![](demo/dzmlrce06.png)

<br/>
判断模式<br/>
python dz-ml-rce.py -u "http://www.xxx.cn/forum.php" <br/>

![](demo/dzmlrce02.png)

<br/>
cmdshell模式<br/>
python dz-ml-rce.py -u "http://www.xxx.cn/forum.php" --cmdshell<br/>

![](demo/dzmlrce03.png)

<br/>
getshell模式<br/>
python dz-ml-rce.py -u "http://www.xxx.cn/forum.php" --getshell<br/>

![](demo/dzmlrce04.png)

<br/>
批量检测<br/>
python dz-ml-rce.py -f urls.txt<br/>

![](demo/dzmlrce01.png)

<br/>
批量getshell<br/>
python dz-ml-rce.py -f urls.txt --getshell<br/>

![](demo/dzmlrce09.png)


----------------


# TODO
有空会做各种优化。


----------------

# 反馈
[issus](https://github.com/theLSA/discuz-ml-rce/issues)
<br/>
博客：http://www.lsablog.com/networksec/penetration/discuz-ml-rce-analysis/
<br/>
gmail：lsasguge196@gmail.com
<br/>
qq：2894400469@qq.com

