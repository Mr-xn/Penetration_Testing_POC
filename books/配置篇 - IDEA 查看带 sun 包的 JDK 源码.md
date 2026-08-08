# 配置篇 - IDEA 查看带 sun 包的 JDK 源码
> 2024-05-12
> 来源：https://changeyourway.github.io/2024/05/12/Java%20%E5%AE%89%E5%85%A8/%E9%85%8D%E7%BD%AE%E7%AF%87-idea%E6%9F%A5%E7%9C%8BJDK%E5%92%8C%E4%BE%9D%E8%B5%96%E7%9A%84%E6%BA%90%E7%A0%81/

前言：前面在分析初始版本 CC1 链的时候，查看 sun 包里的 AnnotationInvocationHandler 类的源码，发现变量名全都是 var 开头，非常不便于阅读，接下来将介绍如何使用 IDEA 查看带 sun 包的 JDK 源码，以及导入的依赖源码，这里的源码指的是 .java 文件。

## IDEA 查看带 sun 包的 JDK 源码

ref：[JAVA CC1分析](https://quan9i.top/post/Java%20CC1/)

原始的 JDK 中的 src.zip 是没有 sun 包的，我们需要自己下载包含 sun 包的源码。

以 JDK8u65 版本为例，前往 openjdk 网站下载的链接为：[http://hg.openjdk.java.net/jdk8u/jdk8u/jdk/rev/af660750b2f4](http://hg.openjdk.java.net/jdk8u/jdk8u/jdk/rev/af660750b2f4)

点击左侧的 zip 即可下载压缩包：

![](https://changeyourway.github.io/images/image-20240512103415395.png)

下载的压缩包名为 jdk-af660750b2f4.zip ，将其解压后，在 `jdk-af660750b2f4\jdk-af660750b2f4\src\share\classes` 路径下即可找到 sun 包：

![](https://changeyourway.github.io/images/image-20240512103638591.png)

在我们之前的 JDK 文件夹下有一个 src.zip 压缩包，将其解压后，将上面的 sun 包复制进来：

![](https://changeyourway.github.io/images/image-20240512103849057.png)

这时候就可以在 idea 中添加资源文件了。

打开 idea -> ProJect Structure -> SDKs 选择上方的 Classpath ，点击加号，将 src 路径导入进去：

![](https://changeyourway.github.io/images/image-20240512104333634.png)

添加完 Classpath 之后，还要添加 Sourcepath ：

![](https://changeyourway.github.io/images/image-20240512104500613.png)

这样就算完成了。

这时就可以写个程序验证是否添加成功：

![](https://changeyourway.github.io/images/image-20240512104723731.png)

Ctrl + 鼠标左键进入源码：

![](https://changeyourway.github.io/images/image-20240512104759127.png)

可以发现此时进入的是 .java 文件而不再是 .class 文件了，说明添加成功。

## IDEA 查看依赖包的 Java 源码

ref：[idea 查看 Java 源码，而不是编译后的 class 文件](https://blog.csdn.net/qq_41937438/article/details/102633266)

以 CC 依赖为例：

```
<dependencies>
    <dependency>
        <groupId>commons-collections</groupId>
        <artifactId>commons-collections</artifactId>
        <version>3.2.1</version>
    </dependency>
</dependencies>
```

首先打开设置，找到红框所示路径，勾选 Sources 和 Documentation ：

![](https://changeyourway.github.io/images/image-20240512105017896.png)

点击 Apply 应用和 OK 退出。

接着打开右侧 Maven 图标，按照图示步骤 Download Sources ：

![](https://changeyourway.github.io/images/image-20240512105304562.png)

到这一步就添加完成了。
