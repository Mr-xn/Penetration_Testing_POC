# 不猜参数，让目标自己告诉你：基于错误反馈的API参数自动发现
> 来源：https://xz.aliyun.com/news/92561

## 0x00 参数字典的困局

  
Web 漏洞扫描的第一步是搞清楚接口接受哪些参数。现有一共三种办法：  
  
● 爬 HTML/JS：从 `<input name="...">` 和 `fetch("...")` 里提取——SPA 应用里基本没用  
● 字典爆破：准备一个参数名字典（uid、user\_id、userId...），逐个试——慢，而且命中率依赖字典质量  
● 抓包：从浏览器 Network 面板里看——手动操作，不能自动化  
三种办法都没有利用一个重要信息源：后端 API 自己的错误反馈。  
  
大多数后端框架在处理参数缺失或格式错误时，会在响应里明确告诉调用方缺了什么：  
  

```
parameter[user_code] is missing.
Field 'mobile_phone' is required.
user_id 不能为空
缺少参数 account_email
```

这些错误信息本质上是后端免费送给你的接口文档。参数名、是否必填、格式要求——全部写在错误信息里。  
  

## 0x01 核心逻辑

  
思路很简单：发一个故意缺参数的请求，从错误信息里提取参数名，填上后再发，循环直到没有新参数出现。  
  

```
Step 1: POST /api/user/update  (空参数)
  → {"err_msg":"parameter[mobile_phone] is missing."}
  → 提取: mobile_phone

Step 2: POST /api/user/update  (mobile_phone=13800000000)
  → {"err_msg":"parameter[account_email] is missing."}
  → 提取: account_email

Step 3: POST /api/user/update  (mobile_phone=xxx, account_email=test@x.com)
  → {"err_code":"00000"}
  → 完成: [mobile_phone, account_email]
```

这个过程完全自动、不需要字典、不依赖前端 JS。目标自己的输入校验逻辑帮你做参数发现。  
  

![屏幕截图 2026-07-22 222633.png](https://i.im.ge/QMKmzAW/p2m-eabcab2ad8.png)

  
  

## 0x02 错误模式匹配

  
后端错误信息的格式千奇百怪，但语义是固定的。核心是识别几种错误类型：  
  

| 错误类型 | 匹配模式 | 示例 |
| --- | --- | --- |
| 参数缺失(英文) | parameter["x"] is missing / Field 'x' is required | Spring Boot, Django, Laravel |
| 参数缺失(中文) | 缺少参数x / 参数x不能为空 / x为必填项 | 国产框架、政务系统 |
| JSON Schema | requires property 'x' / required property 'x' | JSON Schema 校验 |
| 格式错误 | Invalid x / x format is error / x格式不正确 | 手机号、邮箱校验 |
| 长度错误 | x length must be / x长度必须 | 密码、验证码 |

  
引擎内置了 10 组正则模式覆盖这些错误类型。每次收到响应先尝试 JSON 解析——因为很多 API 的错误信息在 `err_msg` 或 `message` 字段里——解析成功后再对 `err_msg` 的值做模式匹配，失败就直接对原始响应体做匹配。  
  

## 0x03 迭代终止条件

  
不是所有接口都会把所有参数一次性暴露。有些接口在第一个参数缺失时就返回错误了，后面的参数要在第一个参数被满足后才会被校验到。  
  
所以需要循环迭代。每次迭代：把已发现的参数填上测试值 → 发请求 → 解析新错误 → 有新参数就继续，没有就终止。最多 3 轮（防止某些接口永远返回错误导致死循环）。  
  
测试值的生成也做了一点智能化：看到 `phone` 或 `mobile` 自动填 `13800138000`，看到 `mail` 或 `email` 自动填 `test@example.com`，看到 `code` 或 `id` 自动填 `1`。这不影响准确性，但能确保参数值通过格式校验，让后端继续往下检查其他参数。  
  

## 0x04 实测数据

  
在几个已知参数的接口上做对照测试：  
  

| 接口 | 真实参数 | 错误驱动发现 | 字典爆破(1000词) |
| --- | --- | --- | --- |
| /api/user/modify | mobile_phone, account_email | 2/2 (2轮) | 1/2 (仅命中 email) |
| /api/auth/login | username, password, captcha | 3/3 (3轮) | 2/3 (captcha 不在通用字典) |
| /api/apply/save | user_code, biz_type_id, reason | 1/3 (user_code) | 0/3 |

  
错误驱动发现的覆盖率不是 100%——有些接口的参数校验逻辑不是逐字段报错的，而是一次性校验所有参数后统一返回"参数不完整"，这种情况下只能提取第一个触发校验的参数。但相比字典爆破，它有两个明显优势：  
  
1 零字典依赖：完全靠目标自己的反馈，不会因为参数名在字典外就漏掉  
2 发现的参数一定是真实有效的：不是猜出来的，是目标告诉你的  

## 0x05 局限和适用场景

  
这个方法对以下情况无效：  
  
● 生产环境关闭了详细错误：只返回 `{"error":"invalid request"}` 的系统，错误信息里没有参数名  
● 前端校验拦截了所有错误请求：后端永远收不到缺参数的请求，自然也不会返回错误  
● 参数名校验加了前缀或混淆：比如 `parameter[enc_user_code]` 实际参数是 `user_code`  
● 一次性校验所有参数：后端把所有缺失参数合并成一条错误信息 `"参数不完整"`，不逐个暴露  
但国内大量高校、政府、企业的内部系统不关详细错误——很多运营人员依赖错误信息来调试接口。我在一个月内对四个不同教育机构的测试中，三个的系统都返回了带参数名的错误信息。这个比例说明它不是个例。  
  

## 0x06 总结

  
"不猜参数，让目标自己告诉你"——这个思路本质上是一次视角切换。传统扫描器把错误信息当成"失败的请求"扔掉，但错误信息本身就是最有价值的信息源之一。一个接口为了告诉你"你漏了参数 x"，实际上也就是告诉了你"这个接口接受参数 x"。至于怎么用这个信息，是攻击者的问题，不是接口的问题。  
  
引擎源码已开源，文中代码为简化示例。
