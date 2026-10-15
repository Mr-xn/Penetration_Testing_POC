# Linux Kernel 0.12（4-3-1）--main.c终端初始化（前奏）
> 0431物联卫士实验室
> 来源：https://www.iotsec-zone.com/article/155

# 1、终端发展史

```c
本小节使用到的参考资料
https://www.zhihu.com/question/20388511
https://www.zhihu.com/question/21711307
https://www.zhihu.com/question/65280843
https://taoshu.in/tty.html
```

提到终端就不得不提到与其概念相近的控制台（console）了，事实上现在我们经常用这两个概念表示相同的东西，即都是黑色背景下能执行命令的东西：
![0.png](https://www.iotsec-zone.com/images/MdImg/8b583c7d662a7f570b064a21dcaa4cef.png)
现在的一些数控设备（比如数控机床）的控制箱，通常会被称为控制台：顾名思义，控制台就是一个直接控制设备的面板，上面有很多控制按钮。 相应的，在计算机的早期时代这两个概念的确指的是不同的东西，在计算机刚刚诞生的时候，一台电脑的体积非常的大，上面分布着许多的按钮，它们用来"直接控制"主机，这些按钮的集合我们可以称之为控制台（console）；一台主机可以支持多个用户同时使用，每个用户使用的设备被称为终端（Terminal），每台终端需要使用物理线缆与控制台相连：
![1.png](https://www.iotsec-zone.com/images/MdImg/0ea5015029cef4a16ad73a410e15e68f.png)
可以将上面这张图抽象为终端设备 -- 物理线缆 -- 控制台：
![2.png](https://www.iotsec-zone.com/images/MdImg/ef3d0fb36c03358cf9c114b5594024a8.png)
注：现在每个人离不开的手机可以被称为移动终端设备。
上图展示了类似于"带有显示器"的终端设备 -- 视频显示终端（Video Display Terminal），在它之前采用的是电传打字机（teletype），简称tty：
![3.png](https://www.iotsec-zone.com/images/MdImg/284752bdb22ed5f8cc5e76055b0e39b1.png)
它的工作原理大致如下面代码框的图所示：

````c
                                                                      +----------+ 
+----------+   +-------+     Physical Line     +-------+   +------+   |          |
| teletype |<->| Modem |<--------------------->| Modem |<->| UART |<->| Computer |
+----------+   +-------+                       +-------+   +------+   |          |
                                                                      +----------+
// 注：上图里是"Computer（计算机）"而非"console(控制台)"
````

简单的说明下：左边的电传打印机连接着"调制解调器"（Modem、Modulator-demodulator的缩写），也就是我们常说的“猫”；UART可以简单的理解为将teletype的信号转换成计算机能识别的信号的设备。下面是电传打印机作为终端的演示视频，附上链接：https://www.youtube.com/watch?v=MikoF6KZjm0；
当然了，更早的电传打印机在二战之前就已经有了，当时只是单纯的用于传输消息而已，还没有出现控制台（console）这个东西：
![4.png](https://www.iotsec-zone.com/images/MdImg/31092423267e0b36df82f25a575e9325.png)
1929年的teletype广告
在网上搜索资料的时候猛然发现有一篇文章写的挺好的，在这篇文章中简要的概括了计算机的发展史和硬件的演化，感兴趣可以看看：https://blog.csdn.net/heyc861221/article/details/80129426

# 2、Linux下终端核心概念

## ①、关于RS-232串行接口标准

串行端口（Serial port）简称"串口"，这种物理接口可以实现计算机与各种外围设备（调试解调器、终端、鼠标、键盘、路由器等）进行通信。串行串口与并行端口最大的区别就是后者可以同时传送多个bit位。现在的消费级个人电脑（PC）已经使用USB接口取代了串行端口，但是在自动化工业系统、嵌入式设备中仍然存在。
● 早期的计算机（实体）终端是通过串口RS-232与主机通信的，不过现在大多数已经被虚拟化了。
RS-232是美国电子工业联盟（EIA-Electronic Industry Association）指定的串口数据通信接口标准，该标准的全称为：数据终端设备（DTE）和数据通讯设备（DCE）之间串行二进制数据交换接口技术标准，它的原始编号为EIA RS-232，其中：
● RS（Recommended Standard）表示推荐标准
● 232是标识号
● 末尾可以再跟一个字母，字母C表示RS-232的第三次修改（1969年），在这之前还有RS-232B、RS-232A
因为RS-232C的重大影响，目前已几乎不再使用RS-232中规定的25针脚而是使用9针脚，因此现在谈到RS-232时一般指的是RS-232C，如下所示：
![5.png](https://www.iotsec-zone.com/images/MdImg/5b060fd884a3c9c69e5e6f7a554bea6b.png)
9针脚串行端口注意要和传输视频信号的VGA接口区别开来，这两个长的比较像：
![6.png](https://www.iotsec-zone.com/images/MdImg/f60534d754030633ebcef5d5417d1717.png)
在ebay上仍可搜索到使用这种古老连接方式的鼠标和键盘：
![7.png](https://www.iotsec-zone.com/images/MdImg/f35b9444f6df99291147c86eec0883fa.png)

## ②、关于Linux的字符设备

字符设备（Character Device）是指在I/O传输过程中以字符为单位进行传输的设备，键盘就是个典型的字符设备，它可以很好的说明"流"这种抽象的概念：当我们在键盘上按下一串按键时，数据会以"流"的形式"流动"到计算机中，然后应用数据读取这一串连续的数据流就可以将用户输入的字符显示到屏幕上。还有，Linux将所有连接到计算机的物理设备都映射成设备文件（Device File）来处理，应用程序可以像操作普通文件一样对硬件设备进行操作；根据类别的不同可以将这些设备划分为字符设备、块设备和网络设备三类。
Linux下万物皆文件
ubuntu 18.04中键盘与鼠标的字符设备文件如下所示：
![8.png](https://www.iotsec-zone.com/images/MdImg/1f77f5bc2c450bd94e7e6e714f13252d.png)
![9.png](https://www.iotsec-zone.com/images/MdImg/66659933d4b53db0af0192a61af7c374.png)
键盘监视程序执行效果
除了键盘与鼠标属于字符设备之外，在稍后篇幅中出现的Linux的tty也属于字符设备，这里就拿tty中的ttyS看下吧：
![10.png](https://www.iotsec-zone.com/images/MdImg/492f8f3365cd562903ad0d2b051ae337.png)
主设备号与次设备号在bootsect.S一文中有所说明，如下图所示：
![11.png](https://www.iotsec-zone.com/images/MdImg/2ab598fced145609aad26a591287e148.png)
主设备号、次设备号的概念
若只需要查看系统中存在的主设备号和与之对应的设备文件，执行cat /proc/devices即可：
![12.png](https://www.iotsec-zone.com/images/MdImg/1d83890f5fe8ee22fb0b73ad3025f214.png)

## ③、终端驱动程序的3种模式的展示

要让终端正常工作就离不开终端驱动程序。在kernel 0.12中，相关程序包括终端输入输出程序tty_io.c和终端控制程序tty_ioctl.c。**终端驱动程序用于控制终端设备，在终端设备和进程之间传输数据，并对所传输的数据进行一定的处理。用户在键盘上键入的原始数据（Raw data）在通过终端程序处理后，被传送到相应的进程；而进程向终端发送的数据，在终端程序处理后会被显示在终端屏幕上或者通过串行线路被发送到远程终端。**
从上面这一段话可以看出，这里终端（Terminal）这个概念不再是之前的（图1），而是逐渐演化为具有更强能力和功能的软件仿真黑框框界面（图2）：
![13.png](https://www.iotsec-zone.com/images/MdImg/2dad4381ae261989aa757e1ed6617b60.png)
物理终端（图1）
![14.png](https://www.iotsec-zone.com/images/MdImg/b7edc430046b2021cbd33d2152e1cb67.png)
软件仿真终端（图2）
● 文章后面提到的终端均指"软件仿真的终端"。
**终端的工作方式有3种模式 -- 规范（canonical）模式、非规范（non-canonical）模式和原始（raw）模式。当使用前者时经过终端驱动程序的数据将被进行变换处理，然后再送出；例如把TAB字符扩展为8个空格字符， 用键入的删除字符（backspace）控制删除前面键入的字符等，此时使用的处理函数一般称为行规则（line discipline）或行规程模块。当使用后者时行规则程序仅在终端与进程之间传送数据，而不对数据进行规范模式的变换处理。（-- 来自《Linux内核完全注释》）**
注意：
● 原始（raw）模式是一种特殊的非规范模式。
● 有的环境下tab等于8个空格，也有的环境下tab等于4个空格，甚至不同的编译器也有所不同。
此篇文章我们就从表象看起吧（不深究其中的实现和原理）。在ubuntu 18.04下执行stty -a：
![15.png](https://www.iotsec-zone.com/images/MdImg/75ab656dab82f6885584fa1b09ebb60f.png)
看到上图绿框中的icanon了吗？这个flag标志着canonical规范模式的开启，即icanon表示当前终端窗口使用的是规范模式。紧接着执行cat命令，输入cyberangel：
![16.png](https://www.iotsec-zone.com/images/MdImg/ac6761bb37c4b4762974952d6d8f0cd9.png)
嘶~，多打了一个l，我们可以按下键盘上的Backspace（退格键）消除掉多打的"l"。下面执行stty -icanon以启用非规范模式（该设置仅在当前终端窗口生效）：
![17.png](https://www.iotsec-zone.com/images/MdImg/5613f2fbd58dae6114ebb3390cb2159c.png)
执行cat，依次输入cyberangel这10个字母：
![18.png](https://www.iotsec-zone.com/images/MdImg/5de50f8f3f87a1fb34fe80de435b4c3a.png)
可以发现字符都双写了，此时按下退格键会发现不起作用：
![19.png](https://www.iotsec-zone.com/images/MdImg/ed1ee8d7d40825a46d20ef116c671d2f.png)
规范模式和非规范模式的差距不止这一种，由于篇幅限制，这里就不在说了，多余的内容放到下一篇来讲。
补充：stty -echo会导致用户在输入时不会回显（也就是不能在屏幕上看到输入的内容）。
除了在现代Linux中执行stty，kernel 0.12也可：
![20.png](https://www.iotsec-zone.com/images/MdImg/54a335f5d7d4cd66d17035085ccf253b.png)
![21.png](https://www.iotsec-zone.com/images/MdImg/2a0c288eae24b1e108a98efc687cdb05.png)
与ubuntu 18.04的表现略有不同，kernel 0.12是可以使用退格键消除字符的，具体的实现细节我放在后面的源码篇幅再讲。

 ## ④、Linux的console、tty、pts、ptmx、Terminal

**由于历史的原因，现在"tty"这个名词不再指明一个具体的事物，在Linux中tty变为了一个抽象的字符设备：有时它指的是一个物理输入设备（如：前面说的串行端口），有时它指的是一个允许用户和系统交互的虚拟终端（Virtual Terminal）。但是字符设备文件/dev/ttyN与/dev/tty只是表示虚拟终端。**
下面讲述的知识可能在不同linux发行版下表现有所差异，甚至包括同一版本下纯命令行版本与桌面版本都有差异，演示的桌面版本为ubuntu 18.04。

### a、关于控制台console与终端Terminal

如果现在我们在ubuntu 18.04打开一个终端，即鼠标右键后点击“Open Terminal”就会出现一个黑框框的东西（当然在ubuntu下可能不能称作黑框框，而是叫深红色的框框，哈哈）：
![22.png](https://www.iotsec-zone.com/images/MdImg/43d55df56d0aead526b927080e290ef5.png)
现在所说的终端（Terminal）是由软件模拟的，换句话说就是终端模拟器（Terminal Emulator、或终端仿真器）【如上图所示】。随着计算机的发展已经见不到专门的终端硬件了，但是由于人们的习惯性称呼，现在仍然会将终端模拟器称之为（或简称为）“终端”，可以使用命令toe -a查看系统支持的终端类型：
![23.png](https://www.iotsec-zone.com/images/MdImg/750723b6808c45f2e53fc7f099bd57ca.png)
可以通过命令infocmp来比较两个终端的区别，比如infocmp vt100 vt220将会输出vt100和vt220的区别：
![24.png](https://www.iotsec-zone.com/images/MdImg/68911c7075327f61f4b0e591d612e526.png)
哦↗，终端演化为了软件，那么之前提到过的控制台（console）呢？答案是 -- 也变为了黑底的命令行界面，它的字符设备文件为/dev/console：
![25.png](https://www.iotsec-zone.com/images/MdImg/877f9dfabf99c7f67d26f60e18d890d0.png)
现在的控制台主要用于显示比如内核消息，后台服务消息等，比如在启动和关闭Linux系统时，一闪而过觉得很酷炫的命令界面就是控制台：
![26.png](https://www.iotsec-zone.com/images/MdImg/b88398dd1c7972c1554d9e546a3d03c4.png)
● 登录（login）到用户态后可以在root用户下执行dmesg查看这些日志。
我再啰里啰嗦的提上一嘴，在早期的计算机中，它们完全是不同的物理设备；但是现在有的时候名词“终端Terminal”和“控制台console”均表示能执行用户命令的界面，不进行任何的区分。哎呀，这些都是历史的遗留问题，具体情况具体分析吧。

### 实验1、登录ubuntu的/dev/console（登录单用户模式）

ubuntu的纯命令行（Live server）版本用户登录的是tty（使用的字符设备文件为/dev/ttyN），不是控制台（/dev/console）。登录控制台的充分必要条件是在单用户模式登录到Linux。
● ubuntu桌面版本的终端窗口使用的是/dev/pts/N，还不是tty。
首先要让ubuntu 18.04在开机时显示GNU GRUB界面，设置方法为引用自：https://www.yuque.com/cyberangel/yal5fc/koupxd：
![27.png](https://www.iotsec-zone.com/images/MdImg/091850dd8c53661609edb22a2c6c45df.png)
重启系统时会显示如下界面：
![28.png](https://www.iotsec-zone.com/images/MdImg/780765014268407f0de50180776b549d.png)
在此界面按下e，找到：
![29.png](https://www.iotsec-zone.com/images/MdImg/6229f632c9b4649e541cf20cf459c372.png)
在末尾添加rw single init=/bin/bash，然后按CTRL+x或直接按F10即可进入单用户模式，此时用户即为root用户：
![30.png](https://www.iotsec-zone.com/images/MdImg/ea9562ba3bc14bec98a7b1611ed2ff9b.png)
注：在此界面中添加的参数只会临时生效，下次重新启动后复原。
![31.png](https://www.iotsec-zone.com/images/MdImg/48ea9ca955024511ced7a913051bdcc4.png)
登录到控制台界面
在下面的情况中你可能会使用到console：
1.当你忘记密码时可以使用单用户模式重置，因为登录单用户模式不需要任何密码，前提是你能进入GNU GRUB界面。
2.用户态环境崩溃，可到控制台备份数据（因为现在的控制台由内核管理）。
网上绝大多数文章都称/dev/console是到/dev/tty0的链接，但是这样说是不确切的，根据官方的内核的文档：在kernel 2.1.71开始/dev/console由内核控制，只允许在单用户模式下登录；在此内核版本之前，/dev/console会链接到/dev/tty0或其他tty*上。
https://www.kernel.org/doc/html/latest/admin-guide/devices.html#terminal-devices

```c
The console device, /dev/console, is the device to which system messages should be sent, and on which logins should be permitted in single-user mode. Starting with Linux 2.1.71, /dev/console is managed by the kernel; for previous versions it should be a symbolic link to either /dev/tty0, a specific virtual console such as /dev/tty1, or to a serial port primary (tty*, not cu*) device, depending on the configuration of the system.
```

### b、关于ttyN（N为数字）

参考资料：[https://segmentfault.com/a/1190000009082089](https://segmentfault.com/a/1190000009082089)
毕竟/dev/console只能让一个用户操作，为了支持多用户登录和同一用户同一时刻的多任务（我猜的，因为有需求就有发明嘛），出现了名为tty的子系统【也就是/dev/ttyN字符设备文件（N为正整数）】：
![32.png](https://www.iotsec-zone.com/images/MdImg/3c00c16c4e666402b677ed3ff3202663.png)
kernel 0.12的/dev/ttyN
/dev/ttyN的大致工作原理如下：

```c
                   +-----------------------------------------+
                   |          Kernel                         |
                   |                           +--------+    |       +----------------+ 
 +----------+      |   +-------------------+   |  tty1  |<---------->| User processes |
 | Keyboard |--------->|                   |   +--------+    |       +----------------+
 +----------+      |   | Terminal Emulator |<->|  tty2  |<---------->| User processes |
 | Monitor  |<---------|                   |   +--------+    |       +----------------+
 +----------+      |   +-------------------+   |  tty3  |<---------->| User processes |
                   |                           +--------+    |       +----------------+
                   |                                         |
                   +-----------------------------------------+
```

键盘、显示器都和kernel的终端模拟器（Terminal Emulator）相连，当你在键盘上输入ctrl+alt+F1时，模拟器首先捕获到该输入，然后激活tty1，这样键盘的输入会转发到tty1，而tty1的输出会转发到显示器，同理用输入ctrl+alt+F2，就会切换到tty2。当模拟器激活tty时如果发现没有进程与之关联，意味着这是第一次打开该tty，于是会启动配置好的进程并和该tty绑定，一般该进程就是负责login的进程。

### 实验2、ubuntu切换tty实验

● 图形化界面的每个终端窗口使用的是pts伪终端，不是tty。
现在/dev/ttyN的设备号与权限如下：
![33.png](https://www.iotsec-zone.com/images/MdImg/41c350c88c7d1a2c22e794a303f09bc4.png)
大多数Linux发行版（包含桌面版本和纯命令行版本），可以键入Alt+Ctrl+Fn（n为1~6）以切换到不同的tty：

```c
● CTRL + ALT + F1 – 切换到锁屏
● CTRL + ALT + F2 – 切换图形化界面（桌面）
● CTRL + ALT + F3 – tty3（纯命令行界面）
● CTRL + ALT + F4 – tty4（纯命令行界面）
● CTRL + ALT + F5 – tty5（纯命令行界面）
● CTRL + ALT + F6 – tty6（纯命令行界面）
```

比如按下Alt+Ctrl+F3后：
![34.png](https://www.iotsec-zone.com/images/MdImg/c3d69b2141d284b235fdfcdd1b48bf14.png)
tty1和tty2呢，为什么要从tty3开始？在桌面版的ubuntu中，tty1和tty2被gnome桌面环境占据着，表现为按下CTRL + ALT + F1、CTRL + ALT + F2 会分别切换到锁屏和图形化界面（桌面），毕竟锁屏和图形化界面都是属于gnome桌面环境嘛：
![35.png](https://www.iotsec-zone.com/images/MdImg/2a74bff08915e9bcb7b035a18db28b4e.png)
gnome的tty1
![36.png](https://www.iotsec-zone.com/images/MdImg/602c0e67137635854b2803bc76dbeffb.png)
gnome的tty2
在Linux纯命令行系统中可不会这样，默认登录的终端为tty1，即tty1和tty2均用于纯命令行界面（镜像文件下载链接：[https://releases.ubuntu.com/22.04/ubuntu-22.04-live-server-amd64.iso](https://releases.ubuntu.com/22.04/ubuntu-22.04-live-server-amd64.iso)）
![37.png](https://www.iotsec-zone.com/images/MdImg/fb5fd84d82b03765824b1c9a75572764.png)
ubuntu 22.04的live server版本
ubuntu 18.04桌面版本中，按下Alt+Ctrl+F2后即可切回图形界面。有意思的是，输入账号密码登录到tty3后该字符设备文件/dev/tty3的所属的用户权限会发生变化，不再是root而是属于登录后的用户：
![38.png](https://www.iotsec-zone.com/images/MdImg/dbb1bce72e60d7a559a6998042cd3f86.png)
登录后可以使用who或w命令查看登录的用户：
![39.png](https://www.iotsec-zone.com/images/MdImg/a2d5152c72cefdd80dbbe3becbeeb665.png)

### 实验3、修改有效启用的tty个数

还有一个有趣的点 -- 无论是ubuntu的纯命令行版本还是图形化桌面版本，如果你在键盘上按下Alt+Ctrl+F7到Alt+Ctrl+F12是没有任何反应的，因为ubuntu只能默认访问前6个tty；但是我们可以强制登录到tty7甚至是tty63：sudo chvt tty_number。比如现在我要切换到最后一个tty即tty63，执行sudo chvt 63：
![40.png](https://www.iotsec-zone.com/images/MdImg/3a95a11138e880212e0be2b1c959eae0.png)
啊？为什么切换后只有一个光标在不断的闪烁，就像死机了一样？要想解决这个问题，需要了解一下配置文件/etc/systemd/logind.conf的两个参数：NAutoVTs和ReserveVT:
![41.png](https://www.iotsec-zone.com/images/MdImg/37d9a296424464b9833b58049627f63a.png)
举个例子就好理解了，现在将配置文件修改为NAutoVTs == 3 、 ReserveVT == 6：
![42.png](https://www.iotsec-zone.com/images/MdImg/9efcfa5b7d5bf708e2407ddd02a377d3.png)
重启系统或重启systemd-logind服务（systemctl restart systemd-logind.service），现在我们依次按下ctrl+alt+(F1-F6)，有：
个人建议重启系统，因为后者方式对于修改配置文件之前就访问tty来说不生效，即之前登录的tty仍然可用。
![43.png](https://www.iotsec-zone.com/images/MdImg/4b63e21a313e7a4e886d3a4ca46c6549.png)
![44.png](https://www.iotsec-zone.com/images/MdImg/dbbb7dc285635f6dc609e7bf92c56319.png)
这下就好理解那两个参数了，哈哈。那如果我非得临时使用tty63呢？执行以下命令就行了：

1. sudo systemctl start getty@tty63.service
2. sudo chvt 63
   ![45.png](https://www.iotsec-zone.com/images/MdImg/05f2f8178811dea57bc25143db6ba090.png)
   值得注意的是无论是kernel 0.12还是ubuntu 18.04，tty的设备号都是相同的，一脉相传。当我们登录任意一个ttyN后，比如tty3，依次执行：
   ![46.png](https://www.iotsec-zone.com/images/MdImg/c963d75f52fc3330a10a0cebd69eb268.png)
   如上图所示，使用echo分别向字符设备文件/dev/tty、/dev/tty3、/dev/tty0写入cyberangel，写入之后均会在屏幕上显示cyberangel字符串，所以可以得出如下结论：
   ● 当登录到任意的tty时，/dev/tty和/dev/tty0等价于当前的/dev/ttyN（相当于两个字符文件链接到了/dev/ttyN？）。
   ● 根据上图中/dev/tty的权限（crw-rw-rw-）可以知道任意用户都可以对该字符设备文件写入。
   ● 同一个用户可以同时登录到多个tty中，不会发生冲突。

登录到控制台后，使用同样的方法可以知道tty0与tty1也和console关联，但此时不存在/dev/tty设备文件：
![47.png](https://www.iotsec-zone.com/images/MdImg/5b739283753c04657c68594aa4fbdec8.png)

### 实验4、关于gmone占用的tty

在重启后且登录前按下ctrl+alt+F2会直接来到tty2的命令行界面，回到图形化界面输入账号密码登录后输入ps -ef | grep tty发现gnome占用的不再是tty2而是tty3。在略微极端的情况下比如在登录前按下ctrl+alt+F2 ~ ctrl+alt+F6，则gnome会占用tty7：
![48.png](https://www.iotsec-zone.com/images/MdImg/7c2dd9e904c53cdb11865be8e848fda6.png)
两部分gnome进程分别隶属于GDM和普通用户cyberangel

### c、关于伪终端（Pseudo-TTY、PTY）

好了，利用tty现在我们可以让多个用户同时登录计算机了，但是这还是有局限性。因为同一个用户可以同时登录多个tty以同时干不同的事情，但是能使用的tty毕竟是有限的 -- 只有64个tty（tty0 ~ tty63），而且切来切去十分的麻烦，这么多是在记不住每个tty是用来干什么的；图形化界面就能很好的解决这个问题，要想达到窗口多开而且不浪费tty的数目，伪终端（Pseudo-TTY）就应运而生（前面内容也是我猜的，个人感觉很合理）。“伪”字就很好的体现了它的特性 -- 不与任何终端硬件相关。伪终端字符设备用于通过网络登录主机时为网络服务器和登录shell程序之前提供一个终端接口，或为运行于窗口化的终端程序提供终端样式的接口：
![49.png](https://www.iotsec-zone.com/images/MdImg/f5c22daf996ff027c5f246c51e2a56de.png)

```c
// gcc -g test.c -o test
#include <stdio.h>
int main(){
    printf("Cyberangel\n");
    while(1)
        continue;
    return 0;
}
```

![50.png](https://www.iotsec-zone.com/images/MdImg/cca6781904dc465c0cee41ca82148a10.png)
测试代码效果
可以到进程2360和2319下面瞅一眼：
![51.png](https://www.iotsec-zone.com/images/MdImg/4cbcfb3a588b8a429294f0b9ee9540fa.png)
![52.png](https://www.iotsec-zone.com/images/MdImg/7aa436ac78ff9fd214ee3c4eb4f8b06d.png)
● cwd：Current Working Directory的缩写，意为当前工作目录。
● exe：所执行的可执行文件的路径。
可以看到，运行在同一个窗口的不同进程共用一个伪终端。具体来讲，"伪终端"这三个字实际上指的是伪终端从设备（Slave PTY）【下文简称为slave】，相应的肯定有伪终端主设备（Master PTY)【下文简称为master】。在现代的ubuntu 18.04，所有的slave共用一个master端/dev/ptmx。
这里就放一张图：

```c
 +----------+       +------------+
 | Keyboard |------>|            |
 +----------+       |  Terminal  |--------------------------+
 | Monitor  |<------|            |           fork           |
 +----------+       +------------+                          |
                        |   ↑                               |
                        |   |                               |
                  write |   | read                          |
                        |   |                               |
                  +-----|---|-------------------+           |
                  |     |   |                   |           ↓
                  |     ↓   |      +-------+    |       +-------+
                  |   +--------+   | pts/0 |<---------->| shell |
                  |   |        |   +-------+    |       +-------+
                  |   |  ptmx  |<->| pts/1 |<---------->| shell |
                  |   |        |   +-------+    |       +-------+
                  |   +--------+   | pts/2 |<---------->| shell |
                  |                +-------+    |       +-------+
                  |    Kernel                   |
                  +-----------------------------+
```

对于kernel 0.12来说，字符设备可能有些不同（这里就直接采用书中的表格了，因为书中的表格比较全）：
![53.png](https://www.iotsec-zone.com/images/MdImg/f1f5c85fb140063807bdbdd5e6d1bd8b.png)
master为/dev/ptyN，slave为/dev/ttypN，master与slave两两配对。但无论是哪一个内核版本，master与slave的关系就像管道（pipe）一样，可以让两个进程通过对应的字符设备进行互相交流（如bash进程和用户执行的进程）。

下面在附一个ssh的工作原理，自己看看吧：

```c
// ssh的工作原理
 +----------+       +------------+
 | Keyboard |------>|            |
 +----------+       |  Terminal  |
 | Monitor  |<------|            |
 +----------+       +------------+
                          |
                          |  ssh protocol
                          |
                          ↓
                    +------------+
                    |            |
                    | ssh server |--------------------------+
                    |            |           fork           |
                    +------------+                          |
                        |   ↑                               |
                        |   |                               |
                  write |   | read                          |
                        |   |                               |
                  +-----|---|-------------------+           |
                  |     |   |                   |           ↓
                  |     ↓   |      +-------+    |       +-------+
                  |   +--------+   | pts/0 |<---------->| shell |
                  |   |        |   +-------+    |       +-------+
                  |   |  ptmx  |<->| pts/1 |<---------->| shell |
                  |   |        |   +-------+    |       +-------+
                  |   +--------+   | pts/2 |<---------->| shell |
                  |                +-------+    |       +-------+
                  |    Kernel                   |
                  +-----------------------------+
```

### d、关于ttySN（N为数字）

![54.png](https://www.iotsec-zone.com/images/MdImg/511ce76f171ea8ba3369c2838446b9ad.png)
与/dev/ttyN不同，ttySN的"S"表示Serial（串行的），计**算机把每个串行端口都看作是一个字符设备，这些串行端口对应的字符设备文件名是/dev/ttyS0、/dev/ttyS1等，设备号依次为(4,64)、(4,65)等，分别对应于DOS系统下的COM1、COM2，通过该字符设备就可以对连接到计算机的终端设备（不一定是实体的）进行操作。**相同的，若要向一个端口发送数据，可以在命令行上把标准输出重定向到这些特殊文件名上即可。例如，在命令行提示符下键入echo test > /dev/ttyS1会把单词”test”发送到连接在ttyS1(COM2)端口的设备上。个人感觉该种字符设备文件多用于嵌入式开发和双击调试。
这里的"终端"一词不再指"能执行命令的命令行终端界面"，而是"链接到串口的终端设备"（在不同情况下具有不同含义，还是历史遗留的问题）。但是这两个含义不同的"终端"有异曲同工之妙，均由Terminal的原始含义为末端的（adj）、终点站（n）引申出。
对于每一个终端，都会对应一个ttySN与之对应，如果有多个终端连接过来，那么看起来就是这个样子的：

```c
<-------------------------------------------------------------------(从右向左看)
 （被控制的终端设备）                                                 (控制设备的用户进程)
                                  +----------------+
                                  |kernel-tty_driver|
                                  |                |
                                  |   +-------+    |      			 	+----------------+
 +-------------------+     	  		|   |       |			 <---------->	| User process A |
 | Terminal Device A |<--------->	| 		ttyS0 |    |       				+----------------+
 +-------------------+     			  |   |       |			 <---------->	| User process B |
                                  |   +-------+    |      				+----------------+
                                  |                |
                                  |   +-------+    |      				+----------------+
 +-------------------+       			|		|				|		 | <---------->	| User process C |
 | Terminal Device B |<--------->	| 	|	ttyS1 |    |       				+----------------+
 +-------------------+       			|   |	      |    | <---------->	| User process D |
                                  |   +-------+    |      			  +----------------+
                                  |                |
                                  +----------------+
```

**● 若终端设备为如嵌入式设备、工业设备的实体机，则传输数据时需要使用到RS-232串行端口，也就是与/dev/ttySN密切相关；
● 由于执行命令的终端都被虚拟化为了终端窗口，所以我个人感觉现在似乎RS-232与它好像没有什么关系了...
串行端口和串行端口设备也有可能是虚拟的（此时好像与RS-232串行端口就没什么关系了...），比如，我之前在搭建kernel双机调试的时候需要用到/dev/ttyS0：**
串行端口这个概念包含RS-232串口和类似的设备串口，该概念应当包含硬件层面上（如内部调制解调器）和软件层面上（如ISDN驱动）。【Serial ports are RS-232 serial ports and any device which simulates one, either in hardware (such as internal modems) or in software (suchas the ISDN driver.) 】

### e、其他类型

Linux系统中还存在有很多其他种类的字符设备，例如针对ISDN设备的/dev/ttyIn，这里不再赘述了。

### ⑤、关于Linux shell与tty

偷个懒，这里直接仍一篇文章：[https://segmentfault.com/a/1190000016129862：](https://segmentfault.com/a/1190000016129862：)

## 3、总结

至此我们可以有下图：
![55.png](https://www.iotsec-zone.com/images/MdImg/0bc00997abed12296dc40288f5a7ada3.png)

附件：链接: [https://pan.baidu.com/s/1a90Om42YQ7eH9kVohntT1Q](https://pan.baidu.com/s/1a90Om42YQ7eH9kVohntT1Q) 提取码: dtfs
