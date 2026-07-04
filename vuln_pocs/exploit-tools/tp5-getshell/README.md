tp5-getshell.py - thinkphp5 rce漏洞检测工具
==

-----------------------


# 概述 


控制器过滤不严导致rce,漏洞详情参考

[thinkphp5 RCE漏洞重现及分析](demo/lsablog.com-ThinkPHP5%20RCE漏洞重现及分析.pdf)

<br/>
本工具支持单url/批量检测，有phpinfo模式、cmd shell模式、getshell(写一句话)模式，批量检测直接使用getshell模式。

<br/>

-----------------------




# 需求


python2.7

<br/>
pip install -r requirements.txt 

<br/>

-----------------------



# 快速开始


python tp5-getshell.py -h<br/>

![](demo/p4.png)<br/>
<br/>
单url检测（phpinfo模式）<br/>

使用4种poc-phpinfo检测<br/>

python tp5-getshell.py -u http://www.xxx.com:8888/think5124/public/<br/>
![](demo/p3.png)<br/>
<br/>

单url检测（getshell模式）<br/>

使用3种exp进行getshell，遇到先成功的exp就停止，防止重复getshell<br/>

python tp5-getshell.py -u http://www.xxx.com:8888/think5124/public/ –exploit<br/>

![](demo/p2.png)<br/>
<br/>

单url检测（cmd shell模式）<br/>

python tp5-getshell.py -u http://www.xxx.com/ –cmdshell<br/>

![](demo/p1.png)<br/>
<br/>

批量检测（getshell）<br/>

使用3种exp进行getshell，遇到先成功的exp就停止，防止重复getshell<br/>

python tp5-getshell.py -f urls.txt -t 2 -s 10<br/>
![](demo/p0.png)<br/>
<br/>

----------------------

# 反馈

博客： http://www.lsablog.com/<br/>
gmail: lsasguge196@gmail.com<br/>
qq: 2894400469@qq.com<br/>
issues: https://github.com/theLSA/tp5-getshell/issues
