# 配置篇 - Maven 手动下载与导入依赖
> 2024-05-10
> 来源：https://changeyourway.github.io/2024/05/10/Java%20%E5%AE%89%E5%85%A8/%E9%85%8D%E7%BD%AE%E7%AF%87-Maven%E6%89%8B%E5%8A%A8%E4%B8%8B%E8%BD%BD%E4%B8%8E%E5%AF%BC%E5%85%A5%E4%BE%9D%E8%B5%96/

遇到 maven 无法自动导入的依赖怎么办，本文介绍了如何手动下载与导入 maven 依赖

## 遇到 maven 无法自动导入的依赖怎么办

推荐博客：[maven 项目手动导入 jar 包依赖](https://blog.csdn.net/weixin_44455388/article/details/100926697)

### 第一步，在网上下载依赖 jar 包

比较推荐 nowjava （时代java）这个网站。

比如我要下载 javax.el-api-3.0.0.jar ，那么访问网址 [https://nowjava.com/jar/detail/m03040939/javax.el-api-3.0.0.jar.html](https://nowjava.com/jar/detail/m03040939/javax.el-api-3.0.0.jar.html) 即可，往下翻，有下载 jar 包的链接：

![](https://changeyourway.github.io/images/image-20240428112425221.png)

下载好之后复制文件路径：”C:\\Users\\miaoj\\Downloads\\javax.el-api-3.0.0.jar” 。

### 第二步，idea 中导入 jar 包

file => project Structure => modules => Dependencies => 点击加号 => 选择第一项 JARs or Directories

![](https://changeyourway.github.io/images/image-20240428112831198.png)

将文件地址粘贴进去，确定即可。

### 第三步，将 jar 包手动添加到 maven 本地仓库中

打开 idea 的 Terminal 终端进入 Windows 命令提示符，输入以下命令：

```
mvn install:install-file -Dfile="C:\Users\miaoj\Downloads\javax.el-api-3.0.0.jar" -DgroupId=javax.el -DartifactId=javax.el-api -Dversion=3.0.0 -Dpackaging=jar
```

\-DgroupId：pom 文件中的 groupId

\-DartifactId：pom 文件中的 artifactId

\-Dversion：pom 文件中的 version

\-Dpackaging：导入包的类型，这里是 jar 类型

\-Dfile：jar 包所在路径

在执行结果中可以看到 jar 包已被导入 maven 本地仓库：

![](https://changeyourway.github.io/images/image-20240428113523947.png)

完成之后，查看 pom.xml 文件可以发现原来的依赖不再爆红：

```
<dependency>
      <groupId>javax.el</groupId>
      <artifactId>javax.el-api</artifactId>
      <version>3.0.0</version>
</dependency>
```
