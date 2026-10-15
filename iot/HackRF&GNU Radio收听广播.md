# HackRF&GNU Radio收听广播
> yichen
> 来源：https://www.iotsec-zone.com/article/432

安装 GNU Radio 直接在 github 下载 release 版本即可，我选择了 windows 版本的
[https://github.com/ryanvolz/radioconda/releases](https://github.com/ryanvolz/radioconda/releases)
安装完成后会有一个快捷方式 ，点击打开即可
打开后界面如下，右边是各种组件，后面所有组件都可以通过 ctrl+f 打开搜索框直接搜索名字，可以直接拖拽到左侧的流程图进行连线与配置

![0.png](https://www.iotsec-zone.com/api/image/v2/20240224/czdbidf4iyfsjvce0w.png)

首先我们找到 osmocom Source，在新款的 GNU Radio 在 OsmoSDR 这个折叠目录下，osmocom Source 可以让我们与各种软件定义无线电设备进行通信

![1.png](https://www.iotsec-zone.com/api/image/v2/20240224/czdbil2dtifwl35ipy.png)

将其直接拖拽到流程图界面，它作为一个 Source 会生成数据给后面的模块继续处理，这个模块的实际工作是通知 HackRF 工作于接收模式，采样获得的数据流从 HackRF 中流出，通过 USB 接口流入后面的模块

![2.png](https://www.iotsec-zone.com/api/image/v2/20240224/czdbisjcz3lyy4yl6q.png)

然后我们选择一个 QT GUI Frequency Sink 来采用一组浮点数据流绘制信号的功率谱密度PSD，将其拖拽到流程图区域

![3.png](https://www.iotsec-zone.com/api/image/v2/20240224/czdbizvjed9pazmswv.png)

点击 osmocom source 的 out 再点击 QT GUI Frequency Sink 的 in 就可以把两个模块连接起来，同时因为满足了输入输出的条件，这两个模块由原本的红色标题变为了黑色

![4.png](https://www.iotsec-zone.com/api/image/v2/20240224/czdbja14nnjqoenqwu.png)

同时可以注意到两个模块都有一个共同的值 32k，如果右键模块选择 Properties 查看模块属性

![5.png](https://www.iotsec-zone.com/api/image/v2/20240224/czdbjkxr1ttwq03im9.png)

会发现他们其实是用的是变量的名字

![6.png](https://www.iotsec-zone.com/api/image/v2/20240224/czdbjueijlk0373oqt.png)

当我们修改变量的时候，他们就会随之改变

![7.png](https://www.iotsec-zone.com/api/image/v2/20240224/czdbk1er043wvrceop.png)

接下来修改一下 Ch0: Frequency（Hz），这一步可以先用手机自带的收音机搜索一下你附近比较清晰的广播，然后再在这里设置

![8.png](https://www.iotsec-zone.com/api/image/v2/20240224/czdbk8zjukm0vbgllo.png)

然后把 osmocom source 的 RF Gain 设置为 0 即关闭天线旁边的前端放大器，这个东西一般在接收微小信号时用到，其他的暂时保持默认，把 QT GUI Frequency Sink 的 Average 打开，新版本有高中低选项，我选了个中
然后 ctrl+s 保存一下这个流程图，点击导航栏的开始摁扭即可运行

![9.png](https://www.iotsec-zone.com/api/image/v2/20240224/czdbkgl3zvzjdakgki.png)

这里可以看到下面的 Frequency 表示的是与我们设定的 101.1 的偏移，接下来我们通过创建一个变量的方式让他直接显示频率

![10.png](https://www.iotsec-zone.com/api/image/v2/20240224/czdbko41aiwecth92r.png)

修改 Center Frequency（Hz）为想要起的变量名，这里为 center_freq，此时这里变红了，因为我们还没有设置这个变量，他没有找到

![11.png](https://www.iotsec-zone.com/api/image/v2/20240224/czdbkvp5t1ywfghwad.png)

接下来新建一个变量

![12.png](https://www.iotsec-zone.com/api/image/v2/20240224/czdbl3lzz5zyenwjbn.png)
然后设置为 101.1e6 同时把 Ch0: Frequency（Hz）也改成这个变量

![13.png](https://www.iotsec-zone.com/api/image/v2/20240224/czdbl9ag5lt10zbo2a.png)

再次运行，可以看到，下面的频率已经变化了！！

![14.png](https://www.iotsec-zone.com/api/image/v2/20240224/czdblf7ti9e633vhuc.png)
我们一开始就选择了一个准确的频率，但是原教程讲了一个进行偏移的方法（他嗅探到了好多个广播频道，但没有在正中间的）我们故意把 center_freq 改为其他的使用偏移的方式让最终的频率中心点在 101.1 上（这一改不要紧，为啥我的在选定的那里这么高啊，待解决的疑惑 Orz）

![15.png](https://www.iotsec-zone.com/api/image/v2/20240224/czdbllig6w90l3b4yw.png)
新建一个变量，设置为想要的那一个频率

![16.png](https://www.iotsec-zone.com/api/image/v2/20240224/czdblr3rckr6kkl5ra.png)

然后产生一个新的信号，这个新的信号使用 Signal Source 模块通过 CPU 生成

![17.png](https://www.iotsec-zone.com/api/image/v2/20240224/czdblz96re7vid36ru.png)

并设置频率为 center_freq - channel_freq

![18.png](https://www.iotsec-zone.com/api/image/v2/20240224/czdbm61gjsq5q3aonw.png)

然后找到 Multiply 模块，他的作用是点对点乘法，把一个信号乘以另一个信号

![19.png](https://www.iotsec-zone.com/api/image/v2/20240224/czdbmc4mhd87k9hoit.png)
这里我们把他的两个输入信号分别设置为 HackRF 捕获的和 CPU 生成的

![20.png](https://www.iotsec-zone.com/api/image/v2/20240224/czdbmiugh932yjtoic.png)
接下来我们复制一个 QT GUI Frequency Sink 并且把 Center Frequency（Hz）改为 channel_freq

![21.png](https://www.iotsec-zone.com/api/image/v2/20240224/czdbmqq1at19x5tfte.png)

再次运行流程图，可以看到两个，上面这个是我们处理后的，下面那个是 HackRF 捕获到的

![22.png](https://www.iotsec-zone.com/api/image/v2/20240224/czdbmx57z28mfcypnx.png)
接下来解调信号转为音频信号，首先要过滤一下，因为我们要的是 0Hz 附近的信号，找到 filter 中的 Low Pass Filter，然后把 Multiply 的输出输入到 Low Pass Filter 设置 Cutoff Freq 为 75e3，Transition Width 为 25e3

![23.png](https://www.iotsec-zone.com/api/image/v2/20240224/czdbn47pj8gkseowjp.png)

同时可以通过修改 Low Pass Filter 的 Decimation 降低采样率，降低多少倍取决于我们信号的带宽，我们现在带宽太大了，同时采样了多个广播。为了计算 Decimation 我们添加一个变量 channel_freq，表示带宽，FM电台的带宽是 200kHz，即 channel_freq 值应为 200e3，然后设置 Decimation 为 int(samp_rate/channel_width)
整个过程是把每秒 10M 的采样点 Low Pass Filter，Low Pass Filter 会把采样率降低 50 倍，输出 200k 每秒的采样点

![24.png](https://www.iotsec-zone.com/api/image/v2/20240224/czdbnc92ommflijekt.png)

接下来添加一个 Rational Resam pler ，对采样点乘上一个 12/5 的比值，我们这么做的原因是 12/5 不是一个整数而 Low Pass Filter 只能接收整数参数，但是我们需要使用非整数参数修改采样率

![25.png](https://www.iotsec-zone.com/api/image/v2/20240224/czdbnj8adi6plzjl0q.png)

设置好之后添加一个 FM 解调器 WBFM Receive，把 FM 无线电信号（复数基带信号）转为实数音频信号，设置 WBFM 带宽调频，这是 FM 广播的调试方式，他只需要两个参数，输入采样率 Quadrature Rate：200k*12/5 = 480k，Audio Decimation 填写进一步降低的采样率倍数，这里填个 10
一开始采样率是 10M，经过 Low Pass Filter 之后采样率变为 480k，再经过 WBFM Receive 降低 10 倍，最终输出 48k 每秒的数据给声卡

![26.png](https://www.iotsec-zone.com/api/image/v2/20240224/czdbnrd8dgzz4hxl5x.png)
那么接下来我们加个声卡 Audio Sink，把他的采样率改为 48k，然后点击执行流程图即可收听到 92.3M 的广播了

![27.png](https://www.iotsec-zone.com/api/image/v2/20240224/czdbnxx009dojjyczl.png)

接下来再给我们的收音机增加一个调节音量的选项，我们通过在 Audio Sink 之前乘以一个量来实现，需要把它的 IO Type 改为 float

![28.png](https://www.iotsec-zone.com/api/image/v2/20240224/czdbo4fwpj33r2uyoc.png)

我们还可以增加一个 QT GUI Range，以便通过滑动模块调节音量，这里如果设置调节的值大了就起不到调节音量的作用了，还会影响收听效果出现杂音，start、stop、step 这些含义很明显了，Widget 表示调节摁扭的效果，有滑动（Slider）、数值（Counter）、摁扭（Knob）等等

![29.png](https://www.iotsec-zone.com/api/image/v2/20240224/czdbof375jsqlkubq1.png)

同时设置 Multiply Const 的值为 QT GUI Range 变量名

![30.png](https://www.iotsec-zone.com/api/image/v2/20240224/czdbom0tl7b0tm6hr8.png)
最终流程图如下：

![31.png](https://www.iotsec-zone.com/api/image/v2/20240224/czdbososkdj8dcivbn.png)

效果如下

![32.png](https://www.iotsec-zone.com/api/image/v2/20240224/czdboxz3rd1aiwk8fe.png)
