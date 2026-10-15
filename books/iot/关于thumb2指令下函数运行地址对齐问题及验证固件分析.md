# 关于thumb2指令下函数运行地址对齐问题及验证固件分析
> 不爱榴莲
> 来源：https://www.iotsec-zone.com/article/285

近期，在分析Thumb2指令的一个固件文件时，发现Thumb2指令集下执行函数的运行地址不对齐？
于是，为了分析一下原因，找了手头上现有的一款基于Cortex3内核的一块板子来实际执行看一下，结合编译后的Hex文件，通过IDA来进一步验证一下Thumb2运行地址不对其的现象。

操作示例：
### 1、	固件代码
找了一个FreeRTOS的示例工程，加入几行打印函数地址的日志：
 ![0.png](https://www.iotsec-zone.com/images/MdImg/4b1854ae727319ceb96c7082265d0502.png)
### 2、	通过hex2bin将编译后的Hex文件转成二进制bin文件
执行情况：
![1.png](https://www.iotsec-zone.com/images/MdImg/be17c3898681a113510f64861e16d63a.png)
### 3、	通过ue打开bin文件备用，如下
![2.png](https://www.iotsec-zone.com/images/MdImg/8c3aebe45941aeb7c081d64805b1a09f.png)
### 4、	通过Keil-IDE加载测试代码，如下：
通过IDE debug调试后，板子reset之后在内部时序逻辑的控制下，将0x00000000地址的内容读取到SP；将0x00000004地址的内容读取到PC。此时SP中存放的是栈顶地址，PC中存放的是Reset_Handler复位处理函数地址。
![3.png](https://www.iotsec-zone.com/images/MdImg/9af0c9620b2246948fa2a022d3762f90.png)
![4.png](https://www.iotsec-zone.com/images/MdImg/453b4a9d02e7a8e4850b87ad0fba70bf.png)
### 5、	通过IDA Pro加载上述第二步生成的bin文件，配置过程如下：
![5.png](https://www.iotsec-zone.com/images/MdImg/7b54f3cf44b7c84b5f7c0643370ccb75.png)
![6.png](https://www.iotsec-zone.com/images/MdImg/3359074fda7cec7e508d236d8153e02f.png)
通过在示例工程中的配置，来定义加载到IDA中的内存及存储映射地址，如下：
![7.png](https://www.iotsec-zone.com/images/MdImg/5c197d806433ca611893a360c12fd1be.png)
![8.png](https://www.iotsec-zone.com/images/MdImg/1f1e23fa62944d67676a6e8851c483dd.png)
### 6、	ida加载后如下：
![9.png](https://www.iotsec-zone.com/images/MdImg/66dcba13835978ca0aa633d6825a7742.png)
### 7、	顺利找到程序入口地址：
![10.png](https://www.iotsec-zone.com/images/MdImg/74036a0ed71ac5e579e18ea350acddd7.png)
![11.png](https://www.iotsec-zone.com/images/MdImg/024cdf973b142bd5a68e79a4ea65ec47.png)
进而找到main函数的执行地址，发现通过ldr加载到寄存器时的地址为main函数真正地址+1；通过debug，也可以验证，如下：
![12.png](https://www.iotsec-zone.com/images/MdImg/f3730061738006ef41395f5bdfc9920b.png)
![13.png](https://www.iotsec-zone.com/images/MdImg/3173e3c7fd49c7f8ef9112ca2e1e3926.png)
通过资料了解到ARM指令是4字节对齐的，Thumb-2指令是2字节对齐的，所以这里main函数和函数Delay_nS的地址应该是2字节对齐的，但是打印出来的值却是：08000BB1和080002D9。main函数的地址和test函数的地址都成了奇数地址了。

这个问题在于有些ARM处理器即能使用ARM指令，又能兼容Thumb指令，同一个应用程序中可能同时存在ARM指令和Thumb指令，这两者的处理方式肯定是大不相同的，所以为了切换ARM状态和Thumb状态，在跳转到Thumb指令编写的代码块的时候，将程序地址的最低位置1（因为不管是ARM指令还是Thumb指令，都至少是2字节对齐的，所以最低位一定是0，所以最低位可以拿来用于区分ARM状态和Thumb状态），这样处理器识别到最低位为1的话就会切换到Thumb状态，否则则是ARM状态。Thumb2指令集也是为了兼容以前的ARM状态和Thumb状态所以这样做的。

所以编译器编译STM32F1的程序的时候，会把函数的真实地址 加上1 作为常量放在ROM空间（如果这个函数的地址有被用到的话），获取函数的指针的时候就会获取到最低位被置1的一个地址。如下图，获取Delay_nS的地址的时候，到0x08000BC4地址处读取到了0x080002D9的值，这其实就是Delay_nS的真实地址0x080002D8 + 1得到的。
![14.png](https://www.iotsec-zone.com/images/MdImg/cf4f21901df690006e2c1f1def6dd2f0.png)
程序debug，打印出的日志如下：
![15.png](https://www.iotsec-zone.com/images/MdImg/b9200a4bf15faa1d8bc27abceac1fd4e.png)
最后，在ue中固件文件中也找到了相应的Delay_nS函数的入口地址，实际在flash中的地址也是+1的，如下图：
![16.png](https://www.iotsec-zone.com/images/MdImg/c02fb974b7d81cbbdeafff93019f9380.png)
