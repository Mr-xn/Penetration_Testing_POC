# HWS华为第一届硬件安全大赛SCA-AES writeup分享
> mikro
> 来源：https://www.iotsec-zone.com/article/29

# **前言**

**好**久没写技术文章了，水一篇今年年初参加的硬件安全比赛的赛题，争取以后多多投稿，www.iotsec-zone.com开张，安全大牛悉数亮相，东北老乡前来捧场，希望社区做大做强，再创辉煌！

*扯犊子完毕开始整活*

# 正文开始

**题目：输入明文，输出密文，pin8拉一次触发**

### 用到的示波器

*PICO 3206D*
![0.png](https://www.iotsec-zone.com/images/MdImg/b8641919963f03ee5ff1044617f32913.jpg)

### 用到的电路板

*OSR-2560*
![1.png](https://www.iotsec-zone.com/images/MdImg/1c48dd1b3c7accb3d6a9dfa7f90f711e.jpg)

### 参数

![2.png](https://www.iotsec-zone.com/images/MdImg/b56f9074eaeaa085230aadd2b98dff81.jpg)

 **做**题之前了解了下CPA 是相关能量分析（Correlation Power Analysis）的缩写，工作原理是侧信道曲线每个点求其相关性，b站有相关视频介绍原理和实战[旁路攻击之CPA，破解AES128密码](https://www.bilibili.com/video/BV1Ng4y167cr?from=search&seid=5493098516502060279&spm_id_from=333.337.0.0)

**思路：发送随机明文，根据返回对应的密文，抓取10轮trace（通过对抓取到的trace CPA分析，如果结果不准确后面可以再增加攻击次数）**

**首**先连接板子与pc，可以建立正常通信之后将AES.hex按照题目附件提供的烧写流程进行烧写，执行./avrdude.exe -C avrdude.conf -v -patmega2560 -cwiring -PCOM3 -b115200 -D -Uflash:w:story.hex:i（这里有点小坑之前在我的Mac下载的附件打开文件目录变成._avrdube.exe，迁移过去导致windows无法运行。在比赛设备这台重新下载附件就好了，文件系统格式问题emm）

参照课程培训演示环节，打开串口工具发送16个字节测试下返回查看通信正常
![3.png](https://www.iotsec-zone.com/images/MdImg/a575bcc384af6dfef17f985dc58b1b41.png)

**连接**示波器与开发板子采集波形，连接方法也是参照的是老师之前上课演示的视频，退出picoscope打开jupyter lab并打开附件中的CPA_Example.ipynb，配置示波器参数 ChA通道用于触发（题目为了降低难度用代码触发），B通道用于采集输出信号，调整为200mv波形稳定，采集波形的数量是根据采样率，电路工作频率，示波器显示的timebase来共同决定的，所以参数要调整不然一个是采到的波形不好看，另一个原因是执行到后面会报错（这里的Post trigger要大于10000）
![4.png](https://www.iotsec-zone.com/images/MdImg/d0bb5efd6f04ebdac2b25686e1580de7.png)

**接下来**就是通过调试解决报错（参数设置不对会有python执行报错，示波器的报错，端口占用）然后调试来一步一步执行攻击脚本~

**与**TOA建立通信并获取到meta数据
![5.png](https://www.iotsec-zone.com/images/MdImg/49003eb0ed70e495fda22634600a5413.png)

**采集**到了波形图，这里是触发10次，至少要抓10轮，否则可能由于一些随机噪声导致攻击错误，这里可以看到噪声分布图，看到尖峰说明此时cpu在执行AES操作的处理（采集数据plt.plot(trs[0][0].T)输出波形观察）
![6.png](https://www.iotsec-zone.com/images/MdImg/693cce7e2da271cdf16df31d21e49efc.png)

**继续**往下走，执行CPA攻击，攻击脚本里面selection_functions选择为scared中封装好的FirstSubBytes
![7.png](https://www.iotsec-zone.com/images/MdImg/46ee99111d48c0444450f971ea42f715.jpg)
也可通过自定义函数来破解密钥
![8.png](https://www.iotsec-zone.com/images/MdImg/b7ac3b9ffd736238d3b2592e21fce35e.png)

得到flag，验证通过
![9.png](https://www.iotsec-zone.com/images/MdImg/a5fb4a983529f545f17cfe6b790c257f.png)

签到成功!

# 扩展知识

[SCAred](https://github.com/eshard/scared)
[基于无保护AES芯片的 CPA攻击](https://blog.csdn.net/wlmnzf/article/details/83110344)
[培训材料和决赛赛题 提取码: 9asv](https://pan.baidu.com/s/1j2WN_H6jJsy8ttr0spsbBg)
