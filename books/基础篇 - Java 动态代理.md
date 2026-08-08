# 基础篇 - Java 动态代理
> 2024-05-11
> 来源：https://changeyourway.github.io/2024/05/11/Java%20%E5%AE%89%E5%85%A8/%E5%9F%BA%E7%A1%80%E7%AF%87-Java%E5%8A%A8%E6%80%81%E4%BB%A3%E7%90%86/

在 Java 动态代理中，代理对象能够通过调用 invoke 方法来增强被代理对象的原始方法。

## Java 动态代理

### 程序为什么需要代理？代理长什么样？

对象如果嫌身上干的事太多，可以通过代理来转移部分职责。对象有什么方法想被代理，代理就一定要有对应的方法。

### 下面通过一个简单的例子来了解动态代理

现有一个类 BigStar 需要被代理，如何让代理类知道 BigStar 的哪些方法需要被代理呢？那么需要定义一个接口，这个接口将会声明 BigStar 中需要被代理的方法，再让代理类实现这个接口好了。同样，出于代理的规范，BigStar 类也需要实现这个接口。

**需要被代理的 BigStar 类：**

```
public class BigStar implements Star{
    private String name;

    public BigStar(String name) {
        this.name = name;
    }

    public String Sing(String name){
        System.out.println(this.name + "正在唱" + name);
        return "谢谢大家！";
    }

    public void Dance(){
        System.out.println(this.name + "正在跳舞");
    }
}
```

**Star 接口中声明了 BigStar 类需要被代理的方法 Sing 和 Dance ：**

```
public interface Star {
    String Sing(String name);
    public void Dance();
}
```

接下来我们要获取代理对象，通常用到 Proxy 类的 newProxyInstance() 方法。

### Proxy.newProxyInstance() 方法

其定义是这样的：

```
@CallerSensitive
public static Object newProxyInstance(ClassLoader loader, Class<?>[] interfaces, InvocationHandler h)
```

-   返回类型为 Object
    
-   第一个参数用于指定类加载器，开发里都是用当前类的类加载器，这里即 ProxyUtil.class.getClassLoader() 。
    
-   第二个参数需要传入一个接口数组，用于指定生成的代理对象继承哪些接口，包含哪些方法。
    
-   第三个参数需要传入一个 InvocationHandler 接口的对象，由于接口不能直接实例化对象，所以我们这里需要用到 InvocationHandler 接口的匿名对象。
    

具体代码如下：

```
Star starProxy = (Star) Proxy.newProxyInstance(
                // 指定类加载器
                ProxyUtil.class.getClassLoader(),
                // 传入接口的Class对象
                new Class[]{Star.class},
                // 传入InvocationHandler接口的匿名对象
                new InvocationHandler() {
                    @Override
                    public Object invoke(Object proxy, Method method, Object[] args) throws Throwable {
                        return null;
                    }
                }
        );
```

在使用 idea 创建 InvocationHandler 的匿名内部类时我们会发现这里自动生成了一个重写的 invoke() 方法，划重点，这个 invoke() 方法很重要。

### InvocationHandler 类的 invoke() 方法

代理对象需要做的增强功能（或者说要做的事情），就定义在这个方法里。

我们来看它的定义：

```
public Object invoke(Object proxy, Method method, Object[] args)
```

这三个参数的含义是什么呢？

我们知道，我们获取到的这个代理对象 starProxy 中是有 Sing 和 Dance 两个方法的，而且将来会被调用，就像这样：

```
starProxy.Sing("爱我中华")
```

那么此时第一个参数 proxy 获取到的就是对象 starProxy ，第二个参数 method 获取到的就是方法 Sing ，第三个参数 args 获取到的就是参数数组 Object\[\]{“爱我中华”} ，应该明白了吧。

那么接下来我们可以完善这个 invoke 方法：

```
// 新建一个 BigStar 对象
BigStar bigStar = new BigStar("张三");
// 创建代理对象
Star starProxy = (Star) Proxy.newProxyInstance(
                // 指定类加载器
                ProxyUtil.class.getClassLoader(),
                // 传入接口的Class对象
                new Class[]{Star.class},
                // 传入InvocationHandler接口的匿名对象
                new InvocationHandler() {
                    @Override
                    public Object invoke(Object proxy, Method method, Object[] args) throws Throwable {
                        // 当调用 Sing 方法时，打印 "收钱，准备唱歌场地"
                        if (method.getName().equals("Sing")) {
                            System.out.println("收钱，准备唱歌场地");
                        // 当调用 Dance 方法时，打印 "收钱，准备跳舞场地"
                        } else if (method.getName().equals("Dance")) {
                            System.out.println("收钱，准备跳舞场地");
                        }
                        // 最后一定调用 bigStar 的原始方法，并将结果返回
                        return method.invoke(bigStar, args);
                    }
                }
        );
```

最后调用代理类的 Sing 和 Dance 方法测试：

```
String sing = starProxy.Sing("爱我中华");
System.out.println(sing);
starProxy.Dance();
```

返回结果如下：

![](/images/image-20240511191727576.png)

最后我们再梳理一遍执行流程：

```
starProxy.Sing("爱我中华") -> InvocationHandler 的 invoke 方法（打印 "收钱，准备唱歌场地"） -> bigStar.Sing("爱我中华")（并将返回值返回）
```

starProxy.Dance() 同理：

```
starProxy.Dance() -> InvocationHandler 的 invoke 方法（打印 "收钱，准备跳舞场地"） -> bigStar.Dance()（无返回）
```

至此，我们对动态代理有了大概的了解。

不过，实际开发中，我们通常会自定义一个 ProxyUtil 工具类来获取代理对象：

```
public class ProxyUtil {
    public static Star createProxy(BigStar bigStar) {
        Star starProxy = (Star) Proxy.newProxyInstance(
                // 指定类加载器
                ProxyUtil.class.getClassLoader(),
                // 传入接口的Class对象
                new Class[]{Star.class},
                // 传入InvocationHandler接口的匿名对象
                new InvocationHandler() {
                    @Override
                    public Object invoke(Object proxy, Method method, Object[] args) throws Throwable {
                        // 当调用 Sing 方法时，打印 "收钱，准备唱歌场地"
                        if (method.getName().equals("Sing")) {
                            System.out.println("收钱，准备唱歌场地");
                        // 当调用 Dance 方法时，打印 "收钱，准备跳舞场地"
                        } else if (method.getName().equals("Dance")) {
                            System.out.println("收钱，准备跳舞场地");
                        }
                        // 最后一定调用 bigStar 的原始方法
                        return method.invoke(bigStar, args);
                    }
                }
        );
        return starProxy;
    }
}
```

如此一来，我们的测试类中就可以这样写：

```
public class Test {
    public static void main(String[] args) {
        // 获取代理对象
        Star starProxy = ProxyUtil.createProxy(new BigStar("张三"));
        String sing = starProxy.Sing("爱我中华");
        System.out.println(sing);
        starProxy.Dance();
    }
}
```

这样就简洁很多了。
