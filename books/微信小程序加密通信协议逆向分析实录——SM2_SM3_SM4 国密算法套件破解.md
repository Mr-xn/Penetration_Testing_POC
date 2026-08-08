# 微信小程序加密通信协议逆向分析实录——SM2/SM3/SM4 国密算法套件破解
> 来源：https://xz.aliyun.com/news/92572

声明：本文仅用于技术研究与安全交流，所有内容已做脱敏处理。涉及资产已获得授权测试，请勿用于非法用途。  
  

## 一、概述

  
在移动应用安全评估中，微信小程序因其庞大的用户基数和敏感的业务场景（支付、身份认证、金融交易），一直是安全研究的热点。与普通 App 不同，小程序代码经过 wxapkg 打包、混淆、虚拟化等多重保护，加之国密算法（SM2/SM3/SM4）的广泛应用，使得渗透测试流量分析难度大幅提升。  
  
本文完整记录了对某金融类微信小程序 HTTPS 通信中 SM2/SM3/SM4 国密算法套件的逆向分析过程，从源码反编译、加密协议还原、密钥恢复机制设计，到最终实现 Burp Suite 透明加解密 Hook 的全链路技术细节。  
  
关键词：微信小程序安全、国密算法、SM2/SM3/SM4、Burp Suite、中间人攻击、WebSocket Hook  
  

## 二、前期侦察与源码反编译

  

### 2.1 小程序包提取

  
使用微信小程序逆向工具对目标小程序的 wxapkg 包进行提取和反编译，获得主包 `__APP__.wxapkg` 以及若干分包（`_pages_inspection_`、`_pages_toPay_`、`_pages_marketing_` 等）。反编译后得到 `app-service.js`（约 1.6MB）及多个子包 JS 文件。  
  

![image.png](https://i.im.ge/QMKm3AD/p2m-9d9446174e.png)

  
  

![image-20260722110308818.png](https://i.im.ge/QMKmxaY/p2m-793680a8c5.png)

  
  

### 2.2 webpack 模块系统分析

  
反编译产物采用 webpack 打包，通过 `wx.webpackJsonp.push([[chunkId], {moduleId: function(require, exports, module){...}}])` 机制注册模块。使用 CDP（Chrome DevTools Protocol）通过 `wx.webpackJsonp` 可枚举所有 chunk 及模块 ID：  
  
●Chunk 3 → 模块 10（请求加密编排函数）  
  
●Chunk 1 → 模块 63（SM2/SM3/SM4 封装层）  
  
● Chunk 1 → 模块 144（`{sm2: n(834), sm3: n(838), sm4: n(839)}`）  
●Chunk 1 → 模块 834（SM2 国密公钥加密实现）  
  
●Chunk 1 → 模块 838（SM3 哈希与 HMAC 实现）  
  
●Chunk 1 → 模块 839（SM4 国密对称加密实现）  
  

### 2.3 加密协议逆向

  
通过分析模块 63 的导出函数，还原出完整的加密通信协议：  
  

```javascript
// 模块 63 关键导出函数
function i(t, e) { return n.sm2.doEncrypt(t, e, 0) }  // SM2 加密
function o(t) { return Object(n.sm3)(t) }              // SM3 哈希
function s(t, e, r) { return n.sm4.encrypt(t, e, {mode:"cbc", iv:r}) }  // SM4-CBC 加密
function a(t, e, r) { return n.sm4.decrypt(t, e, {mode:"cbc", iv:r}) }  // SM4-CBC 解密
function u() {    // ShareKey 生成：32个随机十六进制字符
    for(var t="", e="0123456789abcdef", r=e.length, n=0; n<32; n++)
        t += e.charAt(Math.floor(Math.random()*r));
    return t;
}
```

协议流程如下：  
  

```
客户端生成 shareKey (32 hex chars via Math.random)
  ↓
SM2 公钥加密 shareKey → secretKey (带 04 前缀，258 hex chars)
  ↓
SM4-CBC 加密业务 JSON 体 → data (hex)
  ↓
SM3("data=<data>&secretKey=<secretKey>&shareKey=<shareKey>") → smSign
  ↓
POST {secretKey, data, smSign} → 服务端
  ↓
服务端 SM2 私钥解密 secretKey → 恢复 shareKey
  ↓
服务端 SM4-CBC 解密 data → 业务请求体
  ↓
服务端 SM3 验签 → 处理业务
  ↓
服务端 SM4-CBC 加密响应体 → retData
  ↓
服务端 SM3("retData=<retData>&shareKey=<shareKey>") → retSign
  ↓
响应 {retData, retSign} → 客户端
```

![image-20260722111302636.png](https://imglink.cc/cdn/ExnHJ8xnO-.png)

  
  

## 三、核心技术挑战与突破

  

### 3.1 ShareKey 恢复——Math.random 劫持

  
这是整个方案最关键的切入点。shareKey 由 32 次 `Math.random()` 调用生成，每次取 `"0123456789abcdef"[floor(random*16)]`。由于 `Math.random()` 在 V8 引擎中并非密码学安全随机数（使用 XorShift128+ 算法），只要捕获到足够多的连续 `Math.random()` 输出，就能精确推算出 shareKey。  
  
实现方案：通过 MCP（MiniProgram Control Protocol）向小程序 appservice 上下文注入 hook：  
  

```javascript
var origRandom = Math.random;
Math.random = function() {
    var val = origRandom();
    state.randomLog.push(val);  // 记录所有 random() 返回值
    return val;
};
```

在请求到达时，从日志中提取最后 32 个 random 值，重构 shareKey 候选值。由于 `Math.random()` 生成双精度浮点数（53 位精度），需将其映射回 0-15 的整数索引：  
  
● `Math.floor(Math.random() * 16)` → 直接取 `floor(val * 16)` 即可得到 0-15 的索引  
性能优化：初始版本遍历 `randomLog` 全部 5000 条记录，耗时长（约 36s+）。优化为从末尾向前搜索最后 50 个候选，时间降至 <1s。  
  

### 3.2 SM4-CBC 加解密

  
从模块 839 和模块 63 提取出 SM4 参数：  
  
●模式：CBC  
  
● IV：从本地存储 `SM_ENC_DATA` 中读取  
●密钥：shareKey（32 hex chars = 16 bytes）  
  
●填充：PKCS#7（gmssl 内部自动处理）  
  
使用 Python gmssl 库实现：  
  

```python
def sm4_cbc_encrypt(key_hex, iv_hex, plaintext):
    key = bytes.fromhex(key_hex)
    iv = bytes.fromhex(iv_hex)
    crypt = CryptSM4()
    crypt.set_key(key, SM4_ENCRYPT)
    ct = crypt.crypt_cbc(iv, plaintext.encode("utf-8"))
    return ct.hex().lower()
```

验证通过：对同一明文加密两次得到相同密文，确认 SM4-ECB 模式下加密确定性。  
  

### 3.3 SM2 公钥加密——最曲折的环节

  
模块 834 的 `doEncrypt(plaintext, publicKey, mode)` 函数签名：  
  

```javascript
doEncrypt: function(t, e, n=1) {
    t = s.hexToArray(s.utf8ToHex(t));  // shareKey → UTF-8 bytes → hex → byte array
    e = s.getGlobalCurve().decodePointHex(e);  // 解析公钥
    // C1 = k*G (随机密钥对)
    // (x2, y2) = k*P (共享点)
    // C3 = SM3(x2 || M || y2)
    // KDF: SM3(x2 || y2 || counter)
    // C2 = M ⊕ KDF
    return n===0 ? C1 + C2 + C3 : C1 + C3 + C2;
}
```

参数含义：  
  
● `plaintext`：shareKey 字符串的 UTF-8 编码（非 hex 解码！）  
● `publicKey`：带 "04" 前缀的 130 hex chars 公钥  
● `mode=0`：C1C2C3 格式  

#### 3.3.1 坑点 1：公钥前缀处理

  
Python gmssl 的 `CryptSM2.__init__` 中使用 `public_key.lstrip("04")` 去除 "04" 前缀。但 `lstrip("04")` 将 "04" 视为字符集合而非前缀，对于以 `0AE4...` 开头的公钥会错误地剥离 `0`：  
  

```python
"040AE4C7...".lstrip("04") → "AE4C7..."  # 错误！丢失了 0
"040AE4C7..."[2:] → "0AE4C7..."  # 正确
```

当公钥 X 坐标以 `7` 开头时两者结果恰好一致，掩盖了此 bug。  
  

#### 3.3.2 坑点 2：SM3 签名字符串大小写

  
数据密文 `data` 的 hex 大小写直接影响 SM3 签名结果。原始客户端输出小写 hex，而 Python `bytes.hex()` 默认大写，导致 `SM3("data=<DATA>&secretKey=<SK>&shareKey=<SK>")` 不匹配。修复：统一使用小写 hex。  
  

#### 3.3.3 坑点 3：C3 计算中的 KDF 输入

  
gmssl 的 `sm3_kdf` 接收 `xy.encode("utf8")` 后内部做 `bytes.fromhex(xy_hex_str)` 得到 64 字节的 x2||y2 原始字节，再拼接计数器进行 SM3 迭代。JavaScript 端也采用完全相同的逻辑，二者 KDF 输出一致。  
  
最终确认双方 SM2 算法实现等价，但服务端兼容性问题导致必须绕过 SM2 重新加密环节，改用在请求体未变更时复用原始 secretKey 的策略。  
  

### 3.4 MCP 注入与 WebSocket 通信

  
通过微信开发者工具的 CDP 接口建立 WebSocket 连接，在 `appservice` 上下文（context\_id=4）中执行 JavaScript 注入代码。  
  
MCP SSE 端点：`http://127.0.0.1:4554/sse`  
  
注入时机：在 `wx.request` 被调用前完成 `Math.random` 和 `wx.request` 的双重 Hook。  
  

## 四、Galaxy Hook 架构设计

  

### 4.1 整体流程分析清楚后，直接开始ai赋能编写脚本

  
```
小程序 → wx.request → Galaxy 拦截 → hookRequestToBurp（解密展示）
                                         ↓
                                    Burp 中可修改解密后内容
                                         ↓
                                  hookRequestToServer（重新加密）
                                         ↓
                                    真实服务端
                                         ↓
                        响应 → hookResponseToBurp（解密展示）
                                         ↓
                              hookResponseToClient（重新加密）
                                         ↓
                                    小程序客户端

                                    
```

                                    

![image.png](https://i.im.ge/QMKmc1C/p2m-540570b632.png)

  
  

![image.png](https://i.im.ge/QMKmYH4/p2m-110d6b89c1.png)

  
  

### 4.2 关键决策点

  
请求加密：  
  
●优先尝试完整的重新加密（SM4 + SM2 + SM3）  
  
●当请求体未变化时，复用原始 secretKey 避免 SM2 服务端兼容问题  
  
响应解密：使用从请求恢复的 shareKey 直接解密 `retData`  
  
响应重加密：SM4-CBC + SM3 重新计算 `retSign`  
  

### 4.3 数据流标记系统

  
使用 `_jmWx7e16` 标记字段防止递归 Hook：  
  

```python
MARKER = "_jmWx7e16"
marked = {
    MARKER: {"app": "...", "direction": "request", "shareKey": key_hex},
    "_decrypted": decrypted_obj,   # 解密后的业务 JSON
    "_original": body_text,        # 原始密文字符串
}
```

## 五、最终成果验证

  
成功实现 Burp Suite 中透明展示解密后的明文请求/响应，并可修改后自动重新加密发送。核心指标：  
  

| 指标 | 数值 |
| --- | --- |
| shareKey 恢复成功率 | ~100%（候选 #1） |
| shareKey 恢复耗时 | <2s |
| 请求解密正确率 | 100% |
| 响应解密正确率 | 100% |
| 响应重加密客户端验签通过率 | 100% |

  

![](D:\desktop\待发布的文章\assets\image-20260723090124121.png)

![image-20260723090124121.png](https://i.im.ge/QMKmgwq/p2m-d7330404ea.png)

  
  

## 六、经验总结

  
1 Math.random 不安全：使用 `Math.random()` 生成密钥是致命设计缺陷。应使用 `crypto.getRandomValues()` 或 `wx.getRandomValues()` 等密码学安全随机数生成器。  
2 国密算法实现差异：不同语言/库的 SM2 实现在公钥格式、C1C2C3/C1C3C2 模式、ASN.1 编码等细节上存在大量差异，跨语言实现时需逐字节验证。  
3 CDP + MCP 是利器：微信开发者工具的 CDP 接口为小程序安全评估提供了巨大的便利，WebSocket MCP SSE 端点可动态注入任意 JavaScript。  
4 多层防御思维：仅加密传输层远远不够，密钥管理、随机数质量、服务端校验、频率限制等环节缺一不可。  
附录：\[本次使用到的工具如下，感谢如下开源作者\]  
  
[https://github.com/Spade-sec/First](https://github.com/Spade-sec/First)  
  
[https://github.com/outlaws-bai/Galaxy](https://github.com/outlaws-bai/Galaxy)  
  
[https://github.com/TideSec/TscanPlus](https://github.com/TideSec/TscanPlus)
