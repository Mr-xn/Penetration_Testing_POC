# 基础篇 - Tomcat 架构
> 2024-09-26
> 来源：https://changeyourway.github.io/2024/09/26/Java%20%E5%AE%89%E5%85%A8/%E5%9F%BA%E7%A1%80%E7%AF%87-Tomcat%E6%9E%B6%E6%9E%84/

## Tomcat 介绍

Tomcat 是 Apache 软件基金会开发的一个开源 Java Servlet 容器，用于运行 Java Web 应用程序。它实现了多个 Java EE 规范，如 Servlet、JSP（Java Server Pages）和 WebSocket 等，主要用于处理动态网页请求。作为一个轻量级的应用服务器，Tomcat 常用于开发和测试环境中，同时也适用于生产环境中的中小型应用。

## Tomcat 架构

在 Tomcat Server 中，核心架构主要由三个组件组成：**Service**、**Connector** 和 **Container**。它们共同构成了 Tomcat 的请求处理和应用管理机制。

![](https://changeyourway.github.io/images/Tomcat-2.png)

以下是对这三个组件的介绍：

### Service (服务)

-   **功能**：`Service` 是 Tomcat 中用于组织和管理多个 `Connector` 和一个 `Container` 的组件。它负责协调客户端连接和容器之间的关系。
-   **结构**：一个 `Service` 包含一个 `Container`（通常是 `Engine`）和多个 `Connector`。`Service` 的目的是在多个客户端请求和后端的 Web 应用之间建立桥梁。
-   **工作机制**：当请求通过 `Connector` 接入时，`Service` 会负责将这些请求分发给 `Container` 处理。`Service` 也是多个连接器共享一个 `Container` 的桥梁。

### Connector (连接器)

-   **功能**：`Connector` 负责处理客户端和 Tomcat 服务器之间的通信。它将客户端的请求转换成 Tomcat 可以理解的请求对象，并将响应返回给客户端。
-   **协议支持**：Connector 支持多种协议，如 HTTP、HTTPS 和 AJP 。常见的连接器包括：
    -   **HTTP Connector**：用于处理标准的 HTTP 请求。
    -   **AJP Connector**：用于在 Tomcat 和其他 Web 服务器（如 Apache HTTP Server）之间使用 AJP 协议进行通信。
-   **工作机制**：`Connector` 接受客户端的网络连接请求，然后将这些请求传递给 `Service` 中的 `Container` 进行进一步处理。

### Container (容器)

-   **功能**：`Container` 是 Tomcat 中用于处理请求的核心组件。它负责解析和处理通过 `Connector` 接收到的请求，并生成相应的响应。
-   **层级结构**：Container 包含四种子容器（Engine、Host、Context 和 Wrapper）：
    -   **Engine**：最顶层的容器，表示整个 Servlet 引擎。它负责处理通过 `Connector` 接收到的所有请求。一个 Tomcat 实例通常只包含一个 `Engine`，它在接受请求后将其分发到相应的 `Host`。
    -   **Host**：表示一个虚拟主机。一个 `Host` 代表一个能够承载多个应用的虚拟主机，通常与一个域名相对应。它允许 Tomcat 在同一台服务器上支持多个域名（虚拟主机）。
    -   **Context**：代表单个 Web 应用，管理该应用的生命周期。所有的 Servlet、过滤器、监听器等都运行在 `Context` 中。
    -   **Wrapper**：包装一个具体的 Servlet，处理最终的请求。

![](https://changeyourway.github.io/images/20220217164552.png)

-   **工作机制**：当 `Container` 接收到 `Connector` 传递的请求时，它会逐级解析请求，最终将请求交给正确的 `Servlet` 进行处理。

## Tomcat Context

Tomcat 中有三种 Context ：ServletContext、StandardContext、ApplicationContext

### ServletContext

-   接口：`ServletContext` 是一个接口，提供了访问和管理 web 应用程序共享资源的能力。它为所有 servlets 提供全局的视图。
-   获取方式：通过 `request.getServletContext()` 可以获取到 `ApplicationContextFacade` 对象，它是 `ServletContext` 的一个实现类的包装器，用于保护实际的 `ServletContext` 实现不被直接操作。
-   共享性：`ServletContext` 是在 web 容器启动时为每个 web 应用创建的，它在应用的生命周期内有效，并且在同一应用的所有 servlets 之间共享。因此，它代表当前 web 应用，可以访问应用的资源和设置。

### ApplicationContext

-   实现类：`ApplicationContext` 是 `ServletContext` 接口的一个具体实现类。在 Tomcat 中，`ApplicationContext` 被封装在 `ApplicationContextFacade` 中，主要用于提供对 `ServletContext` 的安全访问。
-   功能：`ApplicationContext` 实现了 `ServletContext` 中的方法，因此，它可以管理 web 应用的全局资源、配置初始化参数以及共享属性。
-   作用：实际上，`ApplicationContext` 是对 `StandardContext` 的进一步封装，`ApplicationContext` 中的方法会调用 `StandardContext` 中的对应方法，形成对 web 应用的实际管理。

### StandardContext

-   核心实现：`StandardContext` 是 Tomcat 中 `org.apache.catalina.Context` 接口的默认实现类。它表示一个完整的 web 应用，并且是 Tomcat 用于管理应用生命周期、配置、加载和运行的实际 `Context` 实现。
-   功能与作用：
    -   负责管理整个 web 应用的生命周期（启动、停止、重载等）。
    -   管理应用的所有 servlets、filters、listeners 等组件。
    -   提供对应用的资源路径、JNDI 资源、会话管理等功能的支持。
-   关系：`StandardContext` 是 Tomcat 内部的核心组件，负责实现 `Context` 接口的所有功能，并为 `ApplicationContext` 提供实际的支持。`ApplicationContext` 调用的很多方法最终都会映射到 `StandardContext` 的实现中。

## Tomcat 管道机制

**Tomcat 管道机制（Pipeline Mechanism）** 是 Tomcat 内部的请求处理模型之一，它提供了一种灵活的、可扩展的处理请求和响应的方式。管道机制允许在请求和响应处理过程中插入多个可配置的处理器（Valve），这些处理器按顺序执行，形成一个请求处理的链条。

### Pipeline 和 Valve 的关系

在 Tomcat 中，**Pipeline（管道）** 是容器（如 `Engine`、`Host`、`Context` 等）的一个组件，用来组织多个 **Valve（阀门）**。Valve 是一个个的请求处理器，而 Pipeline 负责管理这些 Valve 的顺序调用。

Tomcat 中，管道就像一个请求处理的通道，而 Valve 是放在管道中的处理站。每个请求进入 Tomcat 时，会沿着这个管道依次经过各个 Valve，直到最终处理完成。

-   **Pipeline**：是一个容器，它维护一系列的 Valve，形成一个处理链。
-   **Valve**：是管道中的节点，执行特定的请求处理逻辑。

### Pipeline 结构

Tomcat 的 Pipeline 由以下两部分组成：

-   **基本 Valve**（Basic Valve）：每个管道都必须有一个基本 Valve，它是管道中最后一个被调用的 Valve，负责实际的请求处理（如转发请求给某个特定的 Servlet）。如果没有其他的自定义 Valve 进行拦截或修改，最终的请求会由基本 Valve 处理。
-   **普通 Valve**：可以在基本 Valve 之前插入多个普通的 Valve，这些 Valve 按照配置的顺序依次执行。

![](https://changeyourway.github.io/images/20220218104446-17273329294125.png)

### 工作原理

当请求进入 Tomcat 时，经过容器（如 `Engine`、`Host`、`Context` 等）的 Pipeline，Pipeline 中的 Valve 会按顺序执行，处理请求并决定是否传递给下一个 Valve。如果某个 Valve 拦截了请求并处理完成，可能会终止后续 Valve 的调用。

**执行过程**：

1.  请求进入某个容器的 Pipeline。
2.  Pipeline 从第一个 Valve 开始，依次调用每个 Valve 的 `invoke()` 方法。
3.  每个 Valve 处理请求并决定是否传递给下一个 Valve。如果需要传递，调用 `getNext().invoke(request, response)`。
4.  如果没有下一个 Valve，最终由 Basic Valve 处理请求。

Tomcat 每个层级的容器（Engine、Host、Context、Wrapper），都有基础的 Valve 实现（StandardEngineValve、StandardHostValve、StandardContextValve、StandardWrapperValve），他们同时维护了一个 Pipeline 实例（StandardPipeline），也就是说，我们可以在任何层级的容器上针对请求处理进行扩展。这四个 Valve 的基础实现都继承了 ValveBase。这个类帮我们实现了生命接口及 MBean 接口，使我们只需专注阀门的逻辑处理即可。

**参考文章**

[Tomcat 架构与 Context 分析](https://myzxcg.com/2021/10/Tomcat-%E6%9E%B6%E6%9E%84%E4%B8%8EContext%E5%88%86%E6%9E%90/#%E4%B8%89%E7%A7%8Dcontext%E7%9A%84%E8%81%94%E7%B3%BB%E4%B8%8E%E5%8C%BA%E5%88%AB)

[Java 安全学习 —— Tomcat 架构浅析](https://goodapple.top/archives/1359)
