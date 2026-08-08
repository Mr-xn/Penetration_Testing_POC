# 从Webpack到攻击链：SPA应用自动化攻击面发现实践
> 来源：https://xz.aliyun.com/news/92560

## 0x00 为什么 SPA 让扫描器变成了瞎子

  
传统的 Web 扫描器靠两样东西发现接口：HTML 里的 `<a>` 和 `<form>` 标签，以及字典爆破常见路径。这套打法在服务端渲染的时代勉强够用。  
  
但在 SPA（单页应用）面前，这两招全部失效。  
  
一个典型的 Angular 应用，所有路由和 API 端点都打包在 webpack 产出的 `main.xxx.js` 里——一个 1.4MB 到 6MB 不等的压缩文件。HTML 里只有一个 `<app-root></app-root>`，没有链接，没有表单。字典爆破更没用——API 路径不是 `/api/user` 这种可猜的模式，而是 `/app-ws/ws/app-service/student/user/modify-contact-info` 这种嵌套路径，靠字典永远撞不到。  
  
这个问题直到我自己在挖一个职业学院的移动端时碰上了才真正意识到严重性。PC 端的教务系统是传统 JSP，URL 一眼看穿。移动端是 Angular SPA，我打开 F12 看 Network 面板——几十个 API 请求，路径全在 webpack 打包后的 `main.js` 里，URL 格式完全不是常见的 RESTful 风格。  
  
手工搜了 20 分钟，从 1.4MB 的压缩 JS 里捞出了 150+ 个 API 端点——包括修改邮箱、重置密码、切换角色这些高危操作。这些端点在 HTML 里一个链接都没有，字典爆破也不可能命中。但它们在 webpack 的 `apiUrlKey` 映射对象里写得明明白白。  
  
后面我把这个手工过程写成了自动化引擎。  
  

## 0x01 apiUrlKey —— webpack 给扫描器留的后门

  
webpack 在打包 Angular 应用时，会把所有 API 路径配置放在一个叫 `apiUrlKey` 的对象里。这不是安全漏洞，是框架约定。但这个约定恰好给扫描器留了一扇门：  
  

```javascript
// 从 main.js 中提取到的真实数据
apiUrlKey = {
  login: "/login",
  check_token: "/check-token",
  user_reset_passwd: "/user/reset-passwd",
  user_change_role: "/user/change-role",
  user_modify_contact_info: "/user/modify-contact-info",
  user_get_base_info: "/user/get-base-info",
  course_schedule_lesson_get_students: "/course/schedule/lesson/get-students",
  // ... 后面还有 140+ 条
};
```

这里的 key 是内部标识符，value 是实际的 URL 路径。URL 拼接规则由另一个变量定义：  
  

```javascript
baseUrl = "https://easm.gzvti.com/app-ws";
commonUrl = "/ws/app-service";

getWholeUrl = function(key) {
  return baseUrl + commonUrl + apiUrlKey[key];
};
```

![屏幕截图 2026-07-22 222520.png](https://i.im.ge/QMKwE0G/p2m-f0c114f2b0.png)

  
  
这三个变量——`baseUrl`、`commonUrl`、`apiUrlKey`——就是完整 API 清单的拼图。扫描器只需要：  
  
1下载 JS 文件  
  
2用正则提取这三个变量的值  
  
3拼接出完整 URL  
  
4 自动推断 HTTP 方法（`save`/`modify`/`delete`/`reset` 结尾的 key → POST，其他 → GET）  
整个过程不到 100 行 Python。  
  

## 0x02 实际效果：比传统 JS 解析器多发现 60% 的端点

  
已有的 JS 解析器（如 LinkFinder、Burp 的 JS analysis）靠识别 `fetch("...")`、`axios.get("...")` 这些调用模式来提取 URL。但在 webpack 压缩后的代码里，这些调用经过模块化封装后变成了 `this.httpClientService.post(e, n, {token: t})`，URL 是通过 `getWholeUrl` 在运行时拼接的，静态分析抓不到。  
  
我做了一个对比测试：拿同一个 webpack 产物，用传统 JS 解析器能提取 5 个端点，用 SPA 解析器能提取 8 个——多了 60%。这 3 个额外发现的端点里有两个是 POST 修改接口（`modify-contact`、`reset-passwd`），恰好是最危险的那类。  
  
在另一个目标（OA 系统）的模块配置里，解析出了 5 个管理端接口，包括教师列表、认证登录、OA 自动登录。传统解析器一个都没抓到——因为 URL 不是通过 fetch/axios 调用的，而是存在 `moduleConfig` 对象里通过 `spellWholeUrl()` 动态加载的。  
  

## 0x03 不只是端点——顺手提取硬编码密钥

  
webpack 打包时，`.env` 里的配置变量会被内联到 JS 中。最常见的模式是 `Secret = "some_value"`：  
  

```javascript
// EAS 移动端 main.js 中提取
Secret = "supwisdom_eams_app_secret"
```

这个值是后端签名校验的关键材料，但直接以明文躺在 JS 里。SPA 解析器搜 `Secret\s*[=:]\s*"([^"]+)"` 这个模式就能自动提取。  
  
在 B/S 架构里这不是设计失误——密钥在前端存放本身就有问题，但工程现实是大量系统都这么做。既然它会出现在 JS 里，扫描器就应该能自动捡起来。  
  
另外，webpack 产物的 interceptor 代码也值得关注——`intercept(request)` 这种函数通常负责给请求自动加签。如果能识别出 interceptor 的存在，就知道这个目标很可能有自定义签名体系，后续可以接签名检测模块。  
  

## 0x04 输入信息够了，接下来是参数从哪来

  
拿到 URL 只是第一步。怎么知道参数叫什么？  
  
传统的办法是参数字典爆破。这个方法有两个问题：一是慢，二是命中率取决于字典质量。  
  
SPA 里其实有更好的信息来源——错误信息。  
  
很多后端 API 在参数缺失时会返回明确的错误提示：  
  
错误信息本身就包含了参数名。我把这个思路做成了 Error-Driven 参数发现引擎：  
  
1用空参数发一个请求  
  
2解析响应里的错误信息，提取参数名  
  
3把发现的参数填上测试值，再发一次  
  
4新的错误可能暴露更多参数  
  
5循环直到没有新参数名出现  
  
这个过程不需要字典、不需要爬前端、不需要看 JS 源码。它利用的是后端自己的输入校验逻辑——你把"错误信息"当成了"API 文档"来读。  
  
实测中，一个修改联系方式的接口，第一次空请求返回 `parameter[mobile_phone] is missing`，填上 `mobile_phone` 后再发，返回 `parameter[account_email] is missing`。两次迭代拿到了完整参数表。  
  

## 0x05 从端点到攻击链——参数关系图

  
有了接口和参数，下一步是理解它们之间的关系。  
  
接口不是孤立的。`/course/lesson/students` 返回 `code`（学号），`/user/modify-contact` 接受 `user_code` 参数——这两个字段语义匹配，存在数据流关系。  
  
参数关系图自动追踪这种关系：  
  
1 记录输出：每个接口返回了哪些字段，字段的值长什么样（数字串？手机号？邮箱？）  
2 记录输入：每个接口接受哪些参数  
3 匹配边：输出字段名和输入参数名做语义匹配——`code`↔`user_code`、`account_email`↔`email`  
4 推导攻击链：BFS 搜索从"能访问的端点"到"能修改他人数据的端点"的最短路径  
这个思路在真实目标上自动推导出了一条 3 步攻击链：  
  
这和手工花了三天才拼出来的攻击链完全一致。  
  

![屏幕截图 2026-07-22 222554.png](https://i.im.ge/QMKwYMa/p2m-ab4daca180.png)

  
  

## 0x06 总结

  
从 webpack 产物到攻击链，整条链路的关键节点：  
  
● `apiUrlKey` 对象 → 完整端点清单  
●错误信息 → 参数表  
  
●参数关系图 → 攻击链路  
  
这三步都不依赖字典、不爬前端、不需要 Swagger 文档。它们利用的是 SPA 应用本身的架构特征和 API 的错误反馈机制。对于现代前端框架的 Web 应用，这套方法比传统扫描器的覆盖面要宽得多。  
  
引擎源码已开源，文中代码为简化示例。（链接在本账号第一篇文章）
