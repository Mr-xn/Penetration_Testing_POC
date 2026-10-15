# Tenda路由器漏洞分析
> 0431物联卫士实验室
> 来源：https://www.iotsec-zone.com/article/352

## 1.Tenda路由器漏洞分析  CVE-2020-13393

（1）漏洞原理

Tenda路由器的Web服务器httpd中存在一个缓冲区溢出漏洞，在处理POST请求的参数时，数值会直接在strcpy中用于放置在堆栈上的局部变量，造成缓冲区溢出。

（2）影响版本

![0.png](https://www.iotsec-zone.com/images/MdImg/42e891f260f6d445b2cdf85d93e7b990.png)

（3）环境模拟

1.对固件进行提取

![1.png](https://www.iotsec-zone.com/images/MdImg/c8b62dd6f2b332d3b552c535b6322c17.png)

2.使用ARM架构的qemu模拟httpd运行

![2.png](https://www.iotsec-zone.com/images/MdImg/6fd06b9f59e6c55bab9855f9e9c1af0b.png)

当进行模拟的时候会报如下错误:

![3.png](https://www.iotsec-zone.com/images/MdImg/965b68dae1e2f0102d6efa1ec1fbf567.png)

3.根据模拟报错的结果进行搜索和Patch二进制文件

![4.png](https://www.iotsec-zone.com/images/MdImg/79bedde1af1b8b176c52694ab0d304ef.png)

成功启动调试，并监听9999端口

4.IDA远程调试httpd根据报错提示的字符串进行字符串搜索，根据调用，追踪到如下的位置，这里主要是模拟失败的地方

![5.png](https://www.iotsec-zone.com/images/MdImg/08a8c12d04138b1e83165b5626ca488b.png)

这里造成启动失败的原因主要是由于check_network和ConnectCfm造成启动失败，这两个函数主要检测网路用的，但是由于模拟缺失，所以只要绕过这两个函数就能成功将设备启动，这里把MOV R3, R0汇编代码Patch成MOV R3, #1及可完成指定的跳转。这里使用rasm2将汇编指令转换成opcode，使用二进制编辑器更改指定代码即可，这里也可以使用IDA自带的Patch插件。

![6.png](https://www.iotsec-zone.com/images/MdImg/a7f9c33c3953695cc22be663fca20bc3.png)

使用010Editor将0030a0e1替换成0130a0e3，完成Patch

![7.png](https://www.iotsec-zone.com/images/MdImg/9d4886b85c1fae6c0911083de16f0e65.png)

这里先配置br0虚拟网卡是得httpd应用完整启动

![8.png](https://www.iotsec-zone.com/images/MdImg/ea4ad1c888a429d32756654cb71fa292.png)

这是使用qemu模拟可以成功的启动应用

![9.png](https://www.iotsec-zone.com/images/MdImg/9943c0b1e6a23192c5a9bcffd27cf57a.png)

这里可以看到已经成功启动httpd服务

（4）漏洞分析

   1.造成漏洞的原因是对传输过来的字段没有进行长度校验直接使用strcpy函数进行拷贝造成缓冲区溢出漏洞

![10.png](https://www.iotsec-zone.com/images/MdImg/0e143a753459b6e8b6c984f0905edc88.png)

通过ida分析可以看出httpd在处理传递的参数时没有进行校验且使用危险函数进行拷贝。

（5）POC验证

   1.编写POC

![11.png](https://www.iotsec-zone.com/images/MdImg/7b219829a65550d95b96bae1d701ecde.png)

   POC对time字段进行了溢出测试

    2.IDA调试httpd

![12.png](https://www.iotsec-zone.com/images/MdImg/cdfe339246be3355ebe01f61bd1951c0.png)

配置IDA进行调试并设置相应断点

![13.png](https://www.iotsec-zone.com/images/MdImg/26d87ba5b885b75236c9094c9a1f8361.png)

 attach上对应的调试进程进行调试，F9直接启动运行

![14.png](https://www.iotsec-zone.com/images/MdImg/b3437085fe5ca5b8208d58718bc125d3.png)

执行poc脚本进行测试

![15.png](https://www.iotsec-zone.com/images/MdImg/d3ba297ed24bf9816a5fee093e2e88e2.png)

这里可以看出成功停到下断点的位置，单步进行调试，可以看到发生溢出

![16.png](https://www.iotsec-zone.com/images/MdImg/17db3ec79fee391c951fbc11b5e9fba7.png)

这里成功验证POC

## 2.Tenda路由器漏洞分析CVE-2020-13392

（1）漏洞原理

  Tenda路由器的Web服务器httpd中存在一个缓冲区溢出漏洞，在处理post请求的funcpara1的参数时，sprintf将该值直接使用到堆栈上，造成缓冲区溢出

（2）影响版本

![17.png](https://www.iotsec-zone.com/images/MdImg/ed6679a1a215d399bb24f9eaa397c599.png)

（3）漏洞分析

   获取对应的参数，传递给sub_4E9CC函数

![18.png](https://www.iotsec-zone.com/images/MdImg/efba03ec99c817fd2746aed759da7870.png)

将第一个参数传递给v6

![19.png](https://www.iotsec-zone.com/images/MdImg/64fcf976a4d58971307878e02ee4e1c5.png)

使用sprintf完成格式化输出，但没做边界检验

![20.png](https://www.iotsec-zone.com/images/MdImg/569acd6a4a0de8f05eafb3694ea4f98a.png)

![21.png](https://www.iotsec-zone.com/images/MdImg/2d50106f1da54f95160b519c14996cb2.png)

 POC

![22.png](https://www.iotsec-zone.com/images/MdImg/ffeb7fc3dba4ce2edb87a0b52cc74920.png)

## 3.Tenda路由器漏洞分析CVE-2020-13394

（1）漏洞原理

  路由器的Web服务器httpd中存在一个缓冲区溢出漏洞。在处理POST请求的/ goform/SetNetControlList列表参数时，将在strcpy中直接使用该值访问放置在堆栈上，造成缓冲区溢出

（2）影响版本

![23.png](https://www.iotsec-zone.com/images/MdImg/71741fc0dfe4b99afac5e2ca1bb4fc96.png)

（3）漏洞分析

 获取传递的结果

![24.png](https://www.iotsec-zone.com/images/MdImg/7fd27236d1e1628700693f1a9a26789b.png)

 使用strcpy函数直接将数据进行拷贝，未进行任何校验

![25.png](https://www.iotsec-zone.com/images/MdImg/816162d28ab6b571813e80fa7cc90b36.png)

POC

![26.png](https://www.iotsec-zone.com/images/MdImg/0a1a9c215e447f4d6e2ec69801f7def9.png)

## 4.Tenda路由器漏洞分析CVE-2020-13391

（1）漏洞原理

   路由器的Web服务器httpd中存在一个缓冲区溢出漏洞。在处理POST请求的/ goform/SetSpeedduizspeed_dir参数时，在sprintf中直接将值用于放置在堆栈上，造成缓冲区溢出。

（2）影响版本

![27.png](https://www.iotsec-zone.com/images/MdImg/88149f26bb104d3360cd82b9936b9b76.png)

（3）漏洞分析

   获取指定参数

![28.png](https://www.iotsec-zone.com/images/MdImg/6b70cccdf344e7ad31fd0be8da6f98f4.png)

POC

![29.png](https://www.iotsec-zone.com/images/MdImg/75067406125bf4d2e58313b88fdcd58e.png)

-end
