# SaTC自动化漏洞分析和实例测试
> GroundCTL2MajorTom
> 来源：https://www.iotsec-zone.com/article/476

    ### SaTC自动化漏洞分析和实例测试

#### 自动化漏洞挖掘

自动化漏洞挖掘分为动态测试和静态测试

##### 动态测试

```
iot设备Fuzz，简单来说就是针对物联网设备进行模糊测试。它利用自动化工具，向设备发送大量随机或变异的数据，以发现潜在的安全漏洞。
```

###### AFL++

`American Fuzzy Lop plus plus (afl++)`是一个由社区驱动的开源工具，它结合了最新的模糊研究，使研究具有可比性，可重复性，可组合性。它提供了多种新功能，例如，`Custom Mutator API` （传统的突变API）能够**增加模糊测试处理策略**，**特定目标的变异**也可以由经验丰富的安全测试人员编写。具体细节可以参阅[AFL++ : Combining Incremental Steps of Fuzzing Research](https://www.usenix.org/conference/woot20/presentation/fioraldi)。

[https://github.com/AFLplusplus/AFLplusplus](https://github.com/AFLplusplus/AFLplusplus)

###### Boofuzz

**Boofuzz**是一个基于生成（generation-based）的协议Fuzz工具，它通过python语言来描述协议的格式，是经典模糊测试框架**Sulley**的继承者，除了众多的bug修复之外，boofuzz还致力于扩展性。Boofuzz对协议的模糊测试有着良好的支持，且其代码开源，目前被广泛使用。物联网设备中设计到了大量的协议，常见的如tcp,udp,mqtt,upnp等等，还有一些各个厂商自己设计的协议等等，而boofuzz则是一款对于协议模糊测试效果非常出众的模糊测试框架。

[https://github.com/jtpereyda/boofuzz](https://github.com/jtpereyda/boofuzz)

###### **现有fuzz工具的不足**

​        路由器通常为终端用户提供基于web的界面来配置系统。底层固件包含web服务器、各种前端文件和后端二进制程序。web服务器接受来自前端的HTTP请求，并调用后端二进制文件来处理它们。在这种情况下，攻击者可能会在前端构建恶意输入，以破坏相应的后端二进制文件。

​        现有的方法无法有效分析嵌入式系统中的服务以检测漏洞。动态方法如模糊测试和仿真，只能到达程序所有可能状态的一小部分，导致很高的误报率。静态方法如KARONTE依赖前后端之间的通用进程间通信(IPC)来定位处理输入数据的代码，并执行集中测试，但这些方法可能会导致许多误报。从嵌入式系统发现bug的关键点是使用web前端用户提供的数据来定位后端处理该数据的代码。

​       尽管传统fuzz在通用平台上能对程序进行有效的测试，但因为fuzz对硬件配置有较高的要求，所以AFL对iot设备fuzz的适配性有限，比如：提取一个固件并找到一个应用程序，然后使用AFL对此程序进行fuzz，AFL难以模拟物联网设备的复杂交互场景，例如设备发现、连接、数据传输等，正常情况下fuzz会失败。他主要针对二进制文件进行模糊测试，对网络协议的支持也有限。

##### 污点分析

​      静态测试中的污点分析由三部分组成：污点源（source）、污点汇集点（sink）和数据流处理（processor）

- **source 即污点源**，代表直接引入不受信任的数据或者机密数据到系统中
- **sink 即污点汇聚点**，代表直接产生安全敏感操作（违反数据完整性）或者泄露隐私数据到外界（违反数据保密性）
- **processor 即数据流处理**，代表整个数据传输和处理的过程（例如加密、编码处理），外部输入的数据经过processor处理后会得到一个适合软件核心模块处理的数据形式.

![0.png](https://www.iotsec-zone.com/api/image/v2/20240906/d3yyitcdj4gctnop0e.png)
#### SaTC简介

SaTC代码：[https://github.com/NSSL-SJTU/SaTC/tree/py2_env](https://github.com/NSSL-SJTU/SaTC/tree/py2_env)

数据集 [https://drive.google.com/file/d/1rOhjBlmv3jYmkKhTBJcqJ-G56HoHBpVX/view?usp=sharing](https://drive.google.com/file/d/1rOhjBlmv3jYmkKhTBJcqJ-G56HoHBpVX/view?usp=sharing)

论文 [https://www.usenix.org/system/files/sec21fall-chen-libo.pdf](https://www.usenix.org/system/files/sec21fall-chen-libo.pdf)

```
SaTC（Sharing More and Checking Less）是一个创新的开源工具，专为检测嵌入式系统的漏洞设计。其核心理念是利用共同的输入关键词，以更高效的方式识别潜在的漏洞，如命令注入和缓冲区溢出问题。SaTC提供了强大的自动化分析功能，大大简化了固件的安全审计工作。
```

​      他基于Ghidra逆向工程框架，通过定制的Ghidra脚本，如ref2sink_cmdi和ref2sink_bof，自动追踪可能的风险路径。这些脚本能够挖掘命令注入和缓冲区溢出类漏洞的源码路径。此外，ref2share和share2sink脚本组合使用，可以探测到共享输入数据导致的问题。工具还集成了污点分析，增强了对潜在风险的识别能力。

**工作流程图**

![1.png](https://www.iotsec-zone.com/api/image/v2/20240906/d3yyj2zuyiv6ioqjud.png)

​       通过跟踪前端和后端之间用户输入的数据流，以精确检测安全漏洞。处理用户输入的后端函数通常与相应的前端文件共享一个关键字：在前端，用户输入被标记为关键字并编码在数据包中；在后端，使用相同或相似的关键字从数据包中提取用户输入。因此，可以使用共享关键字来标识前端和后端之间的连接，并在后端找到用户输入的入口。

#### SaTC实例测试

**安装**

SaTC安装参见**[Github](https://github.com/NSSL-SJTU/SaTC)**

也可以直接docker镜像拉取

```shell
# 拉取docker镜像
docker pull smile0304/satc
# 进入docker环境
docker run -it smile0304/satc:V1.0
# 安装pip requirement
pip install -r requirement.txt
```

这里以tenda ac15为例，测试/bin/httpd是否存在命令注入漏洞

固件版本：US_AC15V1.0BR_V15.03.05.19_multi_TD01

将解包后的squashfs-root目录docker cp复制到docker中的SaTC目录（也可以用-v作目录映射）

```shell
iot@research:~/gujian/tenda/_US_AC15V1.0BR_V15.03.05.19_multi_TD01.bin.extracted/squashfs-root$ docker cp ./squashfs-root/ 9d85e744e75e:/home/satc/SaTC/tendaac15
```

测试httpd中是否存在命令注入漏洞

```shell
python satc.py -d /home/satc/SaTC/tendaac15/squashfs-root/ -o /home/satc/SaTC/res_ac15 --ghidra_script=ref2sink_cmdi -b httpd --taint_check
```

这里指定了只寻找httpd的命令执行漏洞

```shell
optional arguments:
  -h, --help            查看帮助
  -d /root/path/_ac18.extracted, --directory /root/path/_ac18.extracted
                        指定从固件中提取出的文件系统
  -o /root/output, --output /root/output
                        指定结果输出位置
  --ghidra_script {ref2sink_cmdi,ref2sink_bof,share2sink,ref2share,all}
                        (可选) 指定要使用的 Ghidra 脚本。 如果使用`all`命令，`ref2sink_cmdi`、`ref2sink_bof`和`ref2share`三个脚本将同时运行
  --ref2share_result /root/path/ref2share_result  (可选) 运行`share2sink` Ghidra脚本时，需要使用该参数指定`ref2share`脚本的输出结果
  --save_ghidra_project (可选) 是否保存程序运行时产生的ghidra工程路径
  --taint_check         (可选) 指定是否启用污点分析
  -b /var/ac18/bin/httpd, --bin /var/ac18/bin/httpd
                        (可选) 用于指定需要分析的程序，如果不指定，SaTC将使用内置算法确认需要分析的程序
  -l 3, --len 3         (可选) 根据分析结果分析可能为边界的前N个程序，默认为3
```

Ghidra Script介绍

```shell
ref2sink_cmdi : 该脚本从给定的字符串的引用中找到命令注入类型sink函数的路径。
ref2sink_bof : 改脚本从给定的字符串的引用中找到缓冲区溢出类型sink函数的路径。
ref2share: 此脚本用来查找输入等字符串中被写入共享函数等参数，例如:nvram_set, setenv等函数。需要与share2sink来配合使用
share2sink: 此脚本与ref2share功能类似。需要与ref2share来配合使用；使用此脚本的输入为ref2share脚本的输出
```

![2.png](https://www.iotsec-zone.com/api/image/v2/20240906/d3yyj8u0svjr1qrepg.png)

​       开始了从Ghidra decompiler到keyword finding的过程，找到共享的关键字，基于这个关键字开展污点分析，然后再进行一步步的筛选。这里需要一定时间才能跑完。

result目录结构如下
![3.png](https://www.iotsec-zone.com/api/image/v2/20240906/d3yyje3urdtyvccgzn.png)

```shell
|-- ghidra_extract_result # ghidra寻找函数调用路径的分析结果, 启用`--ghidra_script`选项会输出该目录
|   |-- httpd # 每个被分析的bin都会生成一个同名文件夹
|       |-- httpd # 被分析的bin
|       |-- httpd_ref2sink_bof.result # 定位bof类型的sink函数路径
|       |-- httpd_ref2sink_cmdi.result # 定位cmdi类型的sink函数路径
|-- keyword_extract_result  # 关键字提取结果
|   |-- detail  # 前端关键字提取结果(详细分析结果)
|   |   |-- API_detail.result # 提取的API详细结果
|   |   |-- API_remove_detail.result # 被过滤掉的API信息
|   |   |-- api_split.result  # 模糊匹配的API结果
|   |   |-- Clustering_result_v2.result # 详细分析结果(不关心其他过程关心此文件即可)
|   |   |-- File_detail.result  # 记录了从单独文件中提取的关键字
|   |   |-- from_bin_add_para.result # 在二进制匹配过程中新增的关键字
|   |   |-- from_bin_add_para.result_v2 # 同上,V2版本
|   |   |-- Not_Analysise_JS_File.result # 未被分析的JS文件
|   |   |-- Prar_detail.result # 提取的Prar详细结果
|   |   |-- Prar_remove_detail.result # 被过滤掉的Prar结果
|   |-- info.txt  # 记录前端关键字提取时间等信息
|   |-- simple  # 前端关键字提取结果, 比较简单
|       |-- API_simple.result # 在全部二进制中出现的全部API名称
|       |-- Prar_simple.result  # 在全部二进制中出现等的全部Prar
|-- result-httpd-ref2sink_cmdi-ctW8.txt # 污点分析结果,启用`--taint-check` 和 `--ghidra_script`选项才会生成该文件
```

最终污点分析结果存储在了`result-httpd-ref2sink_cmdi-6MIi.txt`中

~~~shell
binary: /home/satc/SaTC/tendaac15/squashfs-root/bin/httpd
configfile: /home/satc/SaTC/res_ac15/ghidra_extract_result/httpd/httpd_ref2sink_cmdi.result-alter2
0xef168 0xa1808   not found
0xf1f24 0xa5560   not found
0xefa70 0xa1d20   not found
```
0xf2208 0xa6890   found : 0xa68f8
```
0xefb24 0xa2994   not found
total cases: 85
find cases: 1
~~~

从结果中看到，httpd的0xa68f8位置疑似存在命令执行，并且该位置的命令执行在sink函数路径文件中也有体现污点传播过程。

```shell
ghidra_extract_result/httpd/httpd_ref2sink_cmdi.result:[Param "deviceName"(0x000f2208), Referenced at formsetUsbUnload : 0x000a68c4] >> 0x000a68f4 -> doSystemCmd
```

IDA打开httpd，jump到0xa68f8

![4.png](https://www.iotsec-zone.com/api/image/v2/20240906/d3yyjvfz5uzrtze8mr.png)

v3获取了deviceName的值，并传递给doSystemCmd，显然这里的doSystemCmd是能够命令注入的。

formsetUsbUnload这个函数很眼熟，deviceName为用户可控的注入点，查了一下cve编号为**cve-2020-10987**

​       根据上海交通大学的论文给出的原理，deviceName（results中0xf2208位置对应其data段）映射为前端用户可控的关键字，先获取了前端可控key-value，后端以相同或相似的关键字从二进制或cgi中进行了提取。

​       share的关键字连接了前端后端，在污点传播的过程中选择数据流，跟踪不受信任的输入并识别危险函数，最终发现了该漏洞。

![5.png](https://www.iotsec-zone.com/api/image/v2/20240906/d3yyjyo7uoykzgp5jx.png)

**查找前端对应点**：由于在污点传播过程中deviceName是前后端的 shared key-Value

在文件结构web目录中查找deviceName即可找到对应的前端页面然后进行手工验证

```shell
$ grep -ir "devicename"|awk -F ":" '{print($1)}'|grep -E 'html|js'|sort|uniq
......
status_usb.html
status_usb.js
```

至此 SaTC就为我们找到了命令注入点，大大提高了iot漏洞的挖掘效率

#### 手工确认实例-cve-2020-10987

固件下载 [https://www.tenda.com.cn/download/detail-2680.html](https://www.tenda.com.cn/download/detail-2680.html)

**固件模拟**

这里使用了qemu-system模拟，模拟的详情可见IOTsec-Zone文章 [qemu固件模拟、网卡分析---我与br0的爱恨情仇 - IOTsec-Zone](https://www.iotsec-zone.com/article/451)

进入qemu虚拟机后启动httpd

![6.png](https://www.iotsec-zone.com/api/image/v2/20240906/d3yyk4qx0lyi6g9scj.png)

进入status_usb.html页面，这里由于js文件的设置，无法显示Unmount button

在浏览器的Network中禁用了[http://192.168.0.3/goform/GetUsbCfg*后可以显示出来](http://192.168.0.3/goform/GetUsbCfg*后可以显示出来)。

![7.png](https://www.iotsec-zone.com/api/image/v2/20240906/d3yyk6dgk9xwuf4tcw.png)

查看该页面的js文件，正常这里就是一个usb插拔的操作，SaTC应该就是在这里帮助我们枚举到了deviceName

![8.png](https://www.iotsec-zone.com/api/image/v2/20240906/d3yyk98hw5woohazpr.png)
点击Unmount按钮抓包

![9.png](https://www.iotsec-zone.com/api/image/v2/20240906/d3yykipkc0slvo2jt2.png)

看到了前后端共享的key-Value值deviceName=xxx，那么这里就是我们的命令注入点

**POC**

![10.png](https://www.iotsec-zone.com/api/image/v2/20240906/d3yykkeypwh5krioh0.png)
