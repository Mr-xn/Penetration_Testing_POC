# AI 渗透初探：从零开始的实战赋能记录
> QIANXIN Team
> 来源：https://forum.butian.net/share/4944

## 我的AI测试方法论

我并没有对`AI`做过深入研究，更多是在实战中慢慢摸索出一些提效的小思路，主要用来简化信息收集和业务理解的时间。大部分场景下，也就寥寥几句`Prompt`，用来梳理业务逻辑、提取全量`JS`接口、扒路由表，以及做接口参数追踪和`Fuzz`构造。

初次渗透时，我会先让`AI`宏观地去收集网站的整体信息架构，尽量发挥`AI`本身的渗透能力，同时给它设定好行为边界和明确目标，让它在规则之内无限推理。与此同时我也会同步进行人工测试，一旦发现可疑的攻击面，再引导`AI`针对性落地测试，效果往往更好。尤其是接口参数缺失导致的未授权访问和信息泄露这类问题，AI的识别效率已经远超人工，`JS`接口的追踪能力更是堪称恐怖。

再懒人一点的打法，就是创建场景化的`Skill`并设定好边界红线。以登录框为例，其实可测的点非常多：经典的`JS`接口提取加爆破、业务接口`Fuzz`、响应字段`AB`复用、`Vue`路由守卫查找、`React`路由表查找、空白页面的`base`地址探测……黑盒测试下，只要自身的攻击思路越丰富，写出来的`Skill`就越细致。这种方法对我来说，更像是把自己的经验蒸馏成可复用的逻辑，而不是简单地套报告模板，本质上是把测试`Toolist`完整走了一遍。虽然这样会限制`AI`的泛化能力，但好处也很明显——不需要过多干涉，给个域名就能无脑完整跑一遍 (

### 设定边界行为

边界可以用法律来形容，禁止去踩红线，去越过红线，在这一点，`AI`渗透，攻防是必不可少的一步。我们可以去写一个`prompt`，比如客户下发的攻击方手册当中的**攻击方行为规范**这一部分内容（做好脱敏），去写成`prompt`，去约束他做一些测试

![image.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-69d8975fd291de199964e3c0ff48d48a7f5a3352.png)

也可以去利用上述思路做成一个`skills`。如果不知道怎么写`skills`，可以将**约束思路**喂给`AI`，让他去写一个`skills`，然后自己去审查，看有无漏掉的东西，或者未做好约束的部分，然后循环往复的去解决即可

### 设定一个目标，规则内，无限推理

此思路来源于前段时间**腾讯云黑客松智能渗透挑战赛** 当中的某位师傅的作品：**Cairn AI**

作者：淚笑，大家可以去关注他的公众号去学习

![image.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-2a823e6c60f24d202db267d4448c9fa7dde27e33.png)

![image.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-237d2603a59144e8ad9d33cc5974df3b169cb79b.png)

他的一个大致设计思路就是：给出一个目标，给出一个任务，然后无限去推理，最终达成目标

当下，我认为大部分模型的推理能力去做渗透已经完全够用，`AI`的思路是丰富的，所以，在测试过程中我们不必去给他去说怎么对一个**点**去进行测试，而是给他一个任务，给他一个目标，去做出一步步的推理，最终完成目标。

## 非预期漏洞挖掘

对应标题，什么是非预期漏洞挖掘？一个点，在我们进行人工测试之后，然后就得出结论：渗透结束，非常安全！现在有了`AI`，我们就可以做到：人工一步---->`AI`一步---->人工判断---->分析总结，但在`AI`这步往往能发现更多人工没有注意的信息，再配合`AI`本身庞大的知识面使用部分非预期方法对设立的目标无限推理直至完成

### `code`报错导致接管

通过对资产进行信息搜集拿到一个小程序,功能点需要内部账户才可使用，尝试对小程序进行反编译，获取`page`路由和接口

![image.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-c90cb0d0a9cbafb6c586afa6dede546b4ddc42d5.png)

拿到源码后对泄露接口进行审计分析，发现此接口\*\*`/wechat/miniapp/getTokenByWechat`\*\* 对业务敏感的师傅一眼可以认出这是拿到某个`token`

![image.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-7d0d32cc2943865883d25ee4815d3932f8d5719a.png)

通过`AI`进行源码审计，寻找`Base`地址构造接口和所需参数

`{"appid":"wx4eb5","code":"xxxxxxxxxxxx"}`,人工该接口值进行模糊测试，但无果

![image.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-e65182d818ec709a61127ae305e8cf9686fd6e02.png)

最终交给`AI`做模糊测试提示词目标是找出可用的`code`值获取小程序`token`，`AI`将`code`改为：`x\n\r`，类似于让某个参数后端报错，最终获取`access_token,secret`

![image.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-f24530164a73e4b7529c67c4fbaf5772215e98f8.png)

后利用深情哥的小程序`access_token`测试工具，进行测试,证明`access_token`有效，从而进行小程序接管，我原以为会正常按`fuzz`思路找出正确的值从而接管，但它却另辟蹊径通过报错来让目标达成，使用了非预期方式达成目标

![image.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-02c96e83e367e11d5475875ab019f27ff56cdab1.png)

### `credentials`认证缺陷接管

某个`Web`系统，经典的登录框，无注册口，无凭证，通过`AI`进行庞大的`JS`搜集，接口清晰与与测试处理，检索此接口 `/auth/oauth2/token`，以往对该接口的了解，是`oauth`登录获取`token`的接口；该接口往往在之前测试，我的知识面下，我只了解于`oauth`的`1click`劫持`code`与`state`打到的任意用户登录。但将此接口提示给`AI` 它则有不一样的的理解，给出非预期知识（对个人而言陌生的知识）

```Markdown
Oauth2有四种授权模式：

password

authorization.code

client.credentials

inplicit
```

![image.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-41203c376b106ad6808493b977eb936ea8057a7a.png)

其中第三种`client`.`credentials`模式，由于其本身可能存在缺陷，他是一种服务端对接服务端的一种授权

> `client_credentials` 模式关键特点：不需要用户参与，客户端自己就是主体。拿到 `client_id` + `client_secret` 就等于拿到了客户端身份，可以直接拿 `access_token`，而`client_id + client_secret`，往往在系统当中存在弱口令

通过传入指定的授权模式，比如：`grant_type=client_credentials`,然后对`Authorization`进行 `client_id + client_secret base64`编码后的内容爆破弱口令测试

![image.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-e941955ca1c09f7147956e56b835fba2e488e3f5.png)

通过后续给出的知识发现，`client_id + client_secret` 一般都是默认对称的，比如`app:app`

![image.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-60725f14086348274026bddee42114c70c7dd002.png)

既然是通过弱口令经过`base64`编码过的，在此攻击面上让`AI`批量做成了一个弱口令字典落地测试

![image.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-2810bdd9cc19decc58b785cd3bb8eaac3266bbe3.png)

最终爆破成功，获取有效token

![image.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-ddcbfe6922c1ff98742768b311950613bf1764de.png)

利用获取到的凭证，复用到`JS`收集的其他接口，最终获取后台管理员账号密码

![image.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-0507a5d97bbe44ef902e9fbcfee6458a61972a2e.png)

由于该密码加密，`AI`调用工具解密（如`hashcat`），最终拿到明文密码，接管后台

![image.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-aff5b0607281a0bf8d0634ffcd3209aa1d523c51.png)

### 存储桶原生端点`Fuzz`

设定目标无限推理,反复引导或者会挖出意向不到的漏洞, 正常文件上传至存储桶`cdn`地址，逐层删除目标发现桶遍历无法`PUT`覆盖 最初想法是翻一翻敏感文件提升危害

![image.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-d946b258efa36a07826f57f8dad78b0f7bc5c717.png)

![image.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-c37297b8faacb809125f76f1171d0f06745c0c30.png)

使用一些存储桶工具想尝试进行翻页,发现均翻不过去,而后手工测试了一些常见的翻页参数\*\*`list-type=2`\*\* `max-keys` 均不可行，无奈丢给了`AI` 测试结果却出乎所料，我原本给的提示词只是翻页存储桶发现更多敏感信息泄露，最开始第一次尝试翻页以失败告终，但我仍是不断给出提示词，类如绕过限制，`Fuzz`翻页参数等等 `prompt`，因为当时我的想法是既然可以遍历`key`没道理不能翻页看，所以一味的让其推理尝试翻页，经过几轮提示对话最终`AI`给出的解释是此为`CDN`层存储桶，阉割`API`没有翻页功能,,

![image.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-61c4b52b2be69c029c92a39d1120019d8d2510d6.png)

戏剧性开始，在我没有继续给出下一步指令下`AI`仍将翻页功能作为目标尝试各种方式进行绕过，随即对该企业进行信息收集，构造三级域名做为字典碰撞，发现原生未被`cdn`分发的真实存储桶地址，在其后拼接桶名仍可以获取桶内信息并且可以正常使用翻页功能

```text
cdn分发域名桶名为deliver
86c0d0f3e1ce0.cdn.xxxxx.com  

未被分发真实桶域名,访问deliver目录内容和86c0d0f3e1ce0.cdn.xxxxx.com一致证明未打偏
sxxxx.xxxxxxx.com/deliver   

```

![image.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-813b1a42c6c78a30c62ba3bbe4eceaff68165ed2.png)

到此并未结束，我们可以联想一下既然我们已找到该企业真实未被`cdn`分发地址，众多文件上传内容地址都会传到此域名下，只是存储桶地址不同而已，通过目录爆破思维最终发现挂载的更多存储桶

![image.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-c1c1d1419869281a00ea9e89c973958967342134.png)

不出所料挂载了非常多的桶，逐一访问发现`metrics`桶下又记录了所有桶的访问日志检索出`200`多个桶地址，统一收集桶名作为目录反复进行`Fuzz`

![image.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-29ec41989bbfc562d33ed08494084acf1d65f617.png)

最终`AI`辅助测试所有桶总结敏感信息提交报告，后续复盘下来也算是误打误撞发现的，本身没有`Skill`局限某个漏洞类型，甚至提示词只是想办法绕过翻页功能，但需要刻意去引导`AI`往既定目标发散思维，不能让他偷懒，反复鞭打直至穷尽思路，但也不能盲目的对某一处死磕,那么受伤的只是自己的`token`，所以鼓励大家用`AI`放大攻击面，如若我没有桶遍历正常是可以翻页的想法则不会反复对话几轮，一个被预编译的注入和被实体化标签的`XSS`推理能力都最强的`AI`都不能绕过

![image.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-8fa836a1bc335f8d6f02e50d5a3f3ba780c4c2ff.png)

## 业务理解辅助AI测试

### `base`文档`Fuzz`

我是认为：**给AI提供的信息越丰富，能达成的目标就越快**，比如如下案例：

通过前期被动对`base`服务下`fuzzing`测试，发现`swagger`，`heapdump` 后续下载转储文件使用工具分析，未发现在互联网下可以利用的敏感信息点，将获取的信息丢给`AI`，去测试

![image.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-af9a2fdd3aa33619ec38722d444ead86ff1d0f33.png)

大家都知道：一个后端服务多半肯定不止于一个`base`服务，可以模糊测试其他的`base`服务，这一攻击思路之前我都是去利用`OneScan` 插件将路径、参数作为字段批量`Fuzz`尝试，但是有了大模型后则可以通过几句提示词快速落地我们的思路解放双手：对小程序反编译的文件，或者小程序`host`资产加载的所有`JS`（包括异步，内嵌类型的`JS`），和对某系统业务上的理解`Fuzz`生成更多的未知模块，比如上述是/`ly-ms/application`,有可能还有其他模块`/ly-ms/user`等

![image.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-8cdc3e6cfa34e51e26a7efba3decea8d4628e438.png)

上述就是AI所作出的操作思路，最终，他通过JS分析，拿到`/api`一级`base`服务，在此base下进行模糊测试，发现隐藏其他`base`服务下的`haepdump`

![image.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-48ce0f2f359a3898175c76d59e9e548d7cff1093.png)

下载新的文件通过`heapdump`分析，拿到腾讯云`CAM`凭证，**由于该凭证权限比较大，最终拿下33台云服务器**

![image.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-c47390a2f0de968d47c855d3367adf8d046e83a4.png)

上述`AI`所发挥的作用，我们人工也可以完全替代，但消耗的时间，精力那不是一点半点，所以，给他一个点，所获取的信息，让`AI`自己去判断信息的重要性，去分析下一步的操作，这是提升效率的一步。

### 业务字段`Fuzz`

原站接口非常之少，常规测试后并未发生漏洞，观察接口存在`4`级并且末级动作路由较长盲目使用公开字典效果不会很好，古法的话一般是通过对接口分割+构造业务字典配合`Onescan` `CaA`等`Fuzz`插件尝试突破，但是这一套下来没半小时解决不了

![image.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-1f99cf9e2097949e9a1ca8548936c8a0c3f31033.png)

但有了`AI`就完全不同了，它能直接将攻击面落地。只需设定好提示词，约束行为边界，明确目标，再把攻击思路灌输给它，AI便能自动完成从业务场景构造字典、到不同`base`目录的`Fuzz`、再到各类请求方法测试，一套流程全部打通。再联动`Burp`的`MCP`服务，或在提示词中加入流量代理至`Burp`端口的指令，就能直观看到`Fuzz`的实时效果。关键还在于`AI`生成的业务接口路径是贴合真实业务逻辑的，相比一味依赖公开字典，精准度要高得多

```text
根据网站业务接口构造字典  域名xxx
提取的第一波接口xxxxxg
根据接口业务及域名生成更多接口进行Fuzz
目标是探测更多安全漏洞
........
```

![image.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-d031412fe5f8a0f87609db9d0c81e6ca77dfe9f4.png)

![image.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-53884b8c030ecb17b71d6b24f791877ef918db1f.png)

最终在一处`Fuzz`出的接口中发现一企微`token`泄露，成功调用企微功能

```text
http://xxxxxxx/qywx/api/auth/fetchAccessToken
```

![image.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-2971134e09053ee1113dcb7367ea42f84882b983.png)

![image.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-0ad1e4e53dd8b3fe4e549b3951e8ac2f02799446.png)

![image.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-7900e3cf12fe9081b74b6dedb563c4fe4346fb4e.png)

### 追踪`JS`构造接口

`AI`对于普通的未授权漏洞和接口业务的联想及参数构造能力异常强悍,只需给定足量的信息及目标无需开`burp` 只需会话即可测试，某次漏洞挖掘访问域名会跳转至`SSO` ,卡住跳转包雪瞳插件先提了一波接口,把能给到的信息都给他并设立目标

```text
分析站点业务,提取JS梳理接口,测试未授权漏洞...
域名
雪瞳接口
```

![image.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-3097eb27e4b04850345d637b54a8c3ac8550ae85.png)

未授权增删改查，我只给到了接口，参数和动态路径我是一概不知，`AI`自己根据业务语义包括接口的形式从`JS`审计构造，如此漏洞接口路径存在动态占位符`{{xxx}}` ，人工多花些时间跟踪`JS`肯定是可以定位的，但挖洞往往时间就是最宝贵，`AI`时代购买`Token`其实也就是另一种"买时间"，人工引导目标进行指挥，`AI`发现攻击面进行复现。复刻这种无脑打法走量的情况下一定是有产出的,但并通用

```text
/api/category/{{category}}/options
/api/user/{{uid}}/options
/api/publish
/api/appKey
/api/options/{{key}}
/api/options
/api/option/{{key}}
```

![image.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-db4e5ec2c5bc59704badd999b8add32bc589aa90.png)

![image.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-be29611a301bcd1bdc59970f584ecd9fc80aaf24.png)

### 注入`WAF` 绕过

以往遇到绕不过的地方习惯性的提问老师傅，但实际上`AI`也是最好的老师，人工发现攻击面`AI`无限推理；正常打开小程序正常加载一处接口数据

![image.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-f6fc47795e7ea929e53c5c2d03d3b350a6ec5370.png)

回显数据正常，被动`FIT`（内部自研参数`fuzzing`工具）检测或者手工,发现出现报错

![image.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-b659477d591fd319e9817ea67f327522b8cd897a.png)

具体去看哪个参数导致的报错，发现`sort`参数至报错，根据业务理解，这里大概率`orderby`

![image.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-47c5cdec5531be2aea29904c58653cd0c2d04bd2.png)

并且这里存在某腾`WAF`，手工绕过费时费力，直接配合`AI`前期给个注入入口：**`rand`\*\***嵌套**\*\*`EXP`** 设定提示词越是边界发散思维让其不断推理，最终成功的`Payload`

```text
payload：rand(exp(44-(crc32((database()))>=2614572253)))
```

![image.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-ba15a2169c5cb6507387719e716580b98f6d061e.png)

![image.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-f338476de7b5d78d476c7d6e4fc9a3d7326a8403.png)

每当`AI`通过未曾见过的手法或Payload发现漏洞作为白帽应当复盘整改过程，拆分此`Payloa`进行分析其中`crc32`函数作用是获取指定字符的数字编码

![image.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-3cf2703814b2e851d84614793787b8843bb8d21a.png)

`rand(exp())` 当内嵌`exp`函数超过某一数字，可利用其进行布尔二分；这里是没有具体的临界值，但可在测试过程中做`intruder`遍历得到临界值

![image.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-15bb87803d2d323bf2aed575fc7a7add28abe6f8.png)

所以可配合`rand`与`exp`，做布尔二分，发散思维，可配合`crc32`，也可直接配合`mid`如`rand(exp(44-(mid(database(),1,1)='s')))`

![image.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-a700467bdda48a04f545a9596fc668a8526e83fc.png)

## Skill

以上案例均使用简单提示词和对业务接口的理解，人工发现某个攻击面后配合`AI`落地攻击思路，设置目标让其发散思维，全程并无`Skill`参与。但关于`Skill`是否有编写的价值，如何写出好的`Skill`，完全取决于编写者自身的实战水平。只要自身在某类测试场景下的实战认知优于`AI`，针对性编写`Skill`固化优质思路，能够极大提升测试效率。这句话是认可的，各位也可以看看`K1y`师傅的文章，链接在下方

[ai与安全](https://mp.weixin.qq.com/s/QprduCLIsWhsF_Dw6KEPGw)

> 只要自身在某类测试场景的实战认知优于`AI`，针对性编写`Skill`固化优质思路，能够极大提升测试效率

![image.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-58f202c701070c432482a40dbba805881198f340.png)

将自己擅长的技能固化成`Skill`交给AI，虽然会限制它的发散思维，但也因此设定了更清晰的目标和边界。我理解的漏洞挖掘，无非是前台接口测试和功能点业务测试这两块。对于后者，通常已经具备了有效`token`，我一般不让`Skill`介入，而是人工发现可疑攻击面后，再引导`AI`去落地具体思路——本文中的多个案例也都是这么做的。但前台登录接口不同，它有一套相对固定的公式化打法，所以我把自己已知的全部思路都梳理了出来，覆盖接口、路由、`Fuzz`等方方面面，确保不遗漏任何可测试的点

```text
阶段一：系统梳理     → Ω框架识别 + 全量JS/Sourcemap/Chunk搜集 + 路由逆向 + 资源清单
阶段二：接口预处理   → 合规过滤 + 去噪去重 + 端点质量分级 + 剔除无效接口
阶段三：标准化流水线 → 固定优先级：未授权检测→越权(IDOR)→鉴权校验→敏感信息→参数注入
阶段四：AI推理拓面   → 同步全量上下文给AI → 推理架构+业务链路 → 定向弱鉴权/未授权Fuzz
阶段五：轻量化兜底   → 死循环检测+自动终止+Token预算控制+不确定场景限轮次退出
```

![image.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-edef1db6f4d58558ffab87a731321fa8dd28ec7a.png)

我并没有直接拿现成的报告去蒸馏，而是让`AI`根据我的测试习惯、目标导向以及引导方式，结合上下文提示词，逐步生成针对前台漏洞的测试方案。随着思路不断更迭，最终这份Skill居然涨到了`4000`多行。后续基本是解放双手，完全依赖`Skill`去测网站，相当于第二个加强版的自己在跑前台。第一次写完的完整版确实会细致入微地把所有阶段完整走一遍，也确实能挖到洞。但问题也随之而来，太全面了导致大量冗余，起初对`token`消耗没概念，后面发现烧得厉害，执行时间也拖得很久，光是关联接口业务做`Fuzz`就要耗费太多时间。后来才意识到，这东西还是得按场景触发，不能无脑全量跑

![image.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-21799bf6250164b57e94c55d02a9dd761bd029fe.png)

比如`Fuzz`接口的时候，有些网站其实只是前端空壳，并没有接入后端，无论发什么接口过去，`BP`里永远只记录`OPTIONS`请求。这种情况下还一味硬`Fuzz`，完全是在浪费时间。再比如后端其实是`Go`的话，让`Skill`去跑`Java`框架的`Swagger`文档泄露，那怎么可能找得到呢？`React`框架是没有路由守卫的，但我却在`Skill`只考虑了`Vue`路由守卫等等....这些都是容易踩坑的场景。我第一次写`Skill`的时候，只顾着吸收思路，没有引导它在什么时机该做什么事，结果跑起来就是无差别执行。

* * *

后续我将完整的`Skill`拆分成了两份：`FuzzZero.skill` 是细致版，覆盖前台接口的完整测试思路；`FuzzOne.skill` 则保留通用的前后端业务梳理和简单测试，同时设定了分阶段的触发条件。这样一来，`AI`会按照固化的`Skill`思路快速输出报告，与此同时我也正常进行人工测试。通常我这边测完一轮，`AI`那边报告也出来了，两边一对比——没有可疑端点就直接换站，一旦发现一丝可疑迹象，落地攻击面就交给`AI`在规则内无限推理人工再同步测试，必要时配合完整版的前台`Skill`兜底，确保不遗漏任何线索，但是固化的`Skill`意味着局限，适时没招使用即可，根据不同场景变换提示词其实也更加灵活

![image.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-3141cd4c2535dd5d9c048f5d741ffdcf27e5b6e9.png)

![image.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-e7c01c50cf0dfb02b8d3121c2305bcdf4497816e.png)

学习洺熙师傅的文章后，发现另一种思路也未尝不可。我原本的诉求是面面俱到地覆盖自身已有的固化测试思路，但随着`Skill`膨胀到几千行，新的问题也逐渐暴露皆在上文有指出——不同网站的架构和业务差异很大，把全部逻辑塞进同一个`Skill`，`AI`需要处理的上下文过重，执行到后面常常忘了前面的约束，顾此失彼。很多场景其实根本不需要跑完整个流程，大量无效测试白白消耗资源和时间。

既然如此，不如换一种组织方式——拆解成多个场景化的小`Skill`，针对不同业务类型或特定漏洞类型单独编写，按需触发。既能保留原有的覆盖度，又能灵活应对不同目标，避免一次性拉满带来的资源浪费和逻辑混乱。这个思路听起来可行，后续等有时间再放到实战里慢慢验证

[AI是阿拉丁神灯](https://mp.weixin.qq.com/s/39puz-wGyVf8umpURhT3hQ)

![image.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-d97ec875e8b28688cb4e56d05882c1a97eab1a92.png)

## 总结

目前我主要在探索`AI`在模糊测试中的落地深度。以`DeepSeek`为例，它在信息收集和攻击面放大上的效率确实很高，日常使用中能帮我把很多重复性、机械化的测试流程跑起来，省下不少时间。但在接口测试的具体分析上，它的判断方式相对模式化——无非是拼接后端地址、观察响应码和回显参数来判定接口是否存在、能否未授权访问。但有时，它又能挖掘出一些非预期的发散性漏洞，甚至在业务理解上更加敏锐，算是意外之喜。这种反差，或许跟使用者的提示词有很大关系——如何收拢AI的泛化推理能力、让它适配当下未知的业务场景，本身是一道需要持续摸索的课题。没有固定话术，只能在实战中反复试探、灵活调整

如何让AI在模糊测试上更进一步？我目前的思路是：通过精细化`Prompt`做行为约束，或拆成多个`Skill`做更细粒度的控制。不过这些都还在构思阶段，尚未真正实操落地，欢迎大家交流指教。毕竟我接触`AI`时间不长，观点未必成熟，只是碰巧测出了一些东西，拿出来分享一下，也是在反复试错中慢慢校正。发出来更多是抛砖引玉，希望能听到不同的声音和更优的解法。
