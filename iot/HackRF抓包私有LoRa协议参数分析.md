# HackRF抓包私有LoRa协议参数分析
> 常乐
> 来源：https://www.iotsec-zone.com/article/542

# HackRF抓包私有LoRa协议参数分析
首先了解一下LoRa是什么， **LoRa**（Long Range 的缩写）是一种**长距离、低功耗的无线通信技术**。它是专为物联网（IoT）设备设计的，主要用于让散布在各地的传感器和智能设备进行长距离、低数据量的无线通信。它主要体现在大型城市基础设施，例如停车场，工业设备预测性维护，供应链资产管理，无线烟感与消防等方向，本次实验用到的方向是酒店系统的门锁管理。

简单的来说，LoRa（Long Range）是一种物理层调制技术，而**私有LoRa协议**和**LoRaWAN协议**是构建在它之上的两种组网方案。它们的核心区别在于**开放性和标准化程度**。

- **LoRaWAN（标准协议）**
  采用标准的**星型网络**架构。终端节点不直接通信，所有数据必须经由网关转发至网络服务器，再由服务器分发给应用。管理由网络服务器（如ChirpStack、TTN）统一负责。
- **私有LoRa协议**
  网络拓扑**完全自定**，可以是点对点、星型或复杂的Mesh（网状网）中继。设备之间可以直接通信，或通过自己制定的规则组网，没有标准的网络服务器概念。
  
**射频底层参数**
这部分两者都是基于Semtech的LoRa芯片，参数名相同，但限制程度不同。
| 参数             | 私有LoRa协议                                            | LoRaWAN协议                                                  |
| :--------------- | :------------------------------------------------------ | :----------------------------------------------------------- |
| **扩频因子(SF)** | 可**完全自定义**，常固定为SF12追求距离，或SF7追求速率。 | **自适应数据速率(ADR)**，网络服务器会根据信号情况，动态指示节点调整SF。 |
| **带宽(BW)**     | 选择灵活，常用62.5kHz、125kHz、250kHz、500kHz等。       | **严格限定**，通常为125kHz、250kHz（部分地区用500kHz）。     |
| **编码率(CR)**   | 可自由选择4/5到4/8。                                    | 在ADR控制下，通常是固定的4/5，以最大化效率。                 |
| **发送功率**     | 可手动设为最大（如+20dBm），需自行注意法规。            | 由网络服务器控制，节点必须遵守最大功率和功率调整指令。       |
| **频点与信道**   | 可手动设置任意频点，信道计划完全自定义。                | **必须严格遵守**对应地区的LoRaWAN信道计划（如CN470、EU868），信道是预定义的。 |

因此我们在分析私有LoRa协议的抓包过程中，看的最重要的底层射频参数的选择，只有发送端和接收端的关键参数匹配，接收端才能正确解调，我们也就能获取到数据包。
既然参数这么重要，我们可以使用我们的工具HackRF One，去获取到LoRa 设备的 IQ 文件，通过软件，对 IQ 文件进行分析，估算出私有协议的射频参数。

![0.png](https://www.iotsec-zone.com/api/image/v2/20260716/djzyqy4q1tu6dnom3z.png)

**软硬件设备准备**

我们这个实验用到的硬件设备有：

- LoRa网关
- LoRa节点
- HackRF One
- 需要参数的LoRa抓包工具

软件设备有：

- Gqrx：用于观察频谱/瀑布图，确认门锁发包时中心频率
- HackRF 工具链：用于抓取 IQ 文件
- Python：numpy / scipy / matplotlib依赖库

### LoRa协议分层

LoRa协议分层架构如图

![1.png](https://www.iotsec-zone.com/api/image/v2/20260716/djzyrmtaledrnfsibl.png)

#### 私有 LoRa 协议分层

私有 LoRa 协议通常是厂商在 LoRa 物理层之上自行设计的一套通信协议。它没有固定的标准帧格式，具体字段、加密方式、校验逻辑和业务流程都由设备厂商决定。

**应用层：** 私有 LoRa 协议承载具体业务功能。例如在门锁系统中，应用层可能包括远程开锁、查询门锁状态、电量上报、设备绑定、网关管理等操作。这一层关注的是“业务要做什么”。

**私有协议层：** 厂商会定义自己的数据帧格式。常见字段可能包括设备 ID、命令字、序号、滚动码、时间戳、数据长度和业务载荷。

**安全与校验层：** 私有 LoRa 可能使用 CRC、校验和、MAC、滚动码、自定义加密或简单混淆。

**模块控制层：** 主控芯片通过串口或 SPI 配置 LoRa 模块，设置频率、带宽、扩频因子、编码率、发射功率、同步字等参数。这一层决定了设备能否和另一端“对上参数”。

**LoRa PHY 物理层：** 数据会被组织成空口帧，通常包含 Preamble、SyncWord、Header、Payload 和 CRC 等部分。随后通过 CSS Chirp 调制发送到空中。

#### LoRaWAN 协议分层

LoRaWAN 是建立在 LoRa 物理层之上的标准化广域网协议。它不仅规定无线调制方式，还规定了 MAC 帧格式、入网流程、密钥体系、设备类别、网关转发和网络服务器处理流程。

**应用层：** LoRaWAN 也承载业务数据，例如传感器数据、控制命令、状态上报等。但 LoRaWAN 的应用载荷通常由 AppSKey 加密，网络服务器一般只能转发和管理网络层信息，不能直接理解应用层明文内容。

**LoRaWAN MAC 层：** 协议字段是标准化的。典型字段包括 MHDR、FHDR、DevAddr、FCnt、FOpts、FPort 和 MIC。DevAddr 用于标识终端设备，FCnt 是帧计数器，可用于防止重放，MIC 用于完整性校验。相比私有 LoRa，LoRaWAN 的优势是结构清晰、标准统一，但分析时也必须遵循 LoRaWAN 的字段定义。

**安全层：** LoRaWAN 采用标准密钥体系。设备入网时会使用 AppKey，并派生出网络层和应用层相关密钥，例如 NwkSKey 和 AppSKey。网络层负责完整性校验和设备身份验证，应用层数据则通过应用密钥加密。

**网络管理层：** LoRaWAN 引入了网关和网络服务器。终端节点并不是直接和业务后台通信，而是先把 LoRa 空口数据发送给网关，再由网关转发到网络服务器。LoRaWAN 还定义了 Class A、Class B、Class C 三种设备类别，以及 ADR 自适应数据速率机制，用于在功耗、延迟和通信效率之间做权衡。

**物理层：** LoRaWAN 仍然使用 LoRa PHY。它同样依赖频率、BW、SF、CR、前导码等参数完成无线传输。因此从频谱或瀑布图上看，私有 LoRa 和 LoRaWAN 都可能表现为类似的 LoRa Chirp 信号。真正的区别需要在解调后的帧结构和上层协议字段中体现。

#### 两者区别

私有 LoRa 和 LoRaWAN 的共同点是：二者底层都可以使用 LoRa 物理层调制，也就是通过 CSS Chirp 扩频方式在空口中传输数据。因此它们都依赖中心频率、带宽 BW、扩频因子 SF、编码率 CR、前导码、同步字等参数。只要这些物理层参数不匹配，接收端就无法正确解调数据包。

二者的主要区别在于上层协议是否标准化。私有 LoRa 是厂商基于 LoRa 物理层自行设计的通信协议，设备 ID、命令字、序号、滚动码、时间戳、载荷格式、校验方式和加密方式都由厂商自己定义。因此私有 LoRa 的灵活性较高，但协议兼容性、安全性和可分析性都取决于具体实现。

LoRaWAN 则是在 LoRa 物理层之上定义的一套标准化广域网协议。它规定了 MAC 帧格式、入网流程、设备地址、帧计数器、MIC 完整性校验、密钥体系、设备类别、网关转发和网络服务器处理流程。相比私有 LoRa，LoRaWAN 的结构更规范，安全机制更完整，也更适合大规模物联网网络部署。

从通信架构上看，私有 LoRa 通常是终端、网关或上位机之间的厂商私有通信，网关可能直接解析业务数据；LoRaWAN 则采用终端、网关、网络服务器、应用服务器的分层架构，网关主要负责转发，网络服务器负责 MAC 层管理和安全校验，应用服务器处理加密后的业务数据。

从安全角度看，私有 LoRa 的安全能力不固定，可能只是简单 CRC，也可能加入滚动码、时间戳、自定义加密或 MAC 校验；LoRaWAN 则使用标准密钥体系，例如 AppKey、NwkSKey、AppSKey，并通过帧计数器和 MIC 防止伪造与重放。

因此，私有 LoRa 可以概括为“厂商自定义协议 + LoRa 物理层”，LoRaWAN 可以概括为“标准化 MAC、安全和网络架构 + LoRa 物理层”。本实验分析的门锁通信属于私有 LoRa 场景，所以重点是先估算并匹配物理层参数，再进一步分析厂商自定义的数据帧、滚动码和校验逻辑。

#### 私有LoRa设备工作流程

![2.png](https://www.iotsec-zone.com/api/image/v2/20260716/djzysi26vxiy9qwiy0.png)

### 抓取LoRa数据包并分析参数

本实验的目标是搭建一套完整的 LoRa 门锁通信环境，并在设备正常工作的基础上，对 LoRa 空口通信过程进行监听和参数分析。实验中主要包含 LoRa 网关、门锁节点、管理后台、小程序以及抓包分析设备等部分。

#### LoRa 网关接入网络

首先将 LoRa 网关接入实验网络环境。网关通过网线连接到路由器 LAN 口，使其能够访问互联网和厂商管理平台。网关上线后，后续才能通过网页后台或小程序对门锁设备进行绑定、管理和远程操作。

![3.png](https://www.iotsec-zone.com/api/image/v2/20260716/djzysukqq2rlghf0el.png)

该步骤的作用是让 LoRa 网关成为门锁节点和云端管理平台之间的中继设备。门锁节点本身通过 LoRa 与网关通信，网关再通过以太网或互联网与后台服务器通信。

在小程序端将网关和门锁节点绑定后，门锁节点、LoRa 网关和管理后台之间形成完整链路。门锁作为 LoRa 节点，负责接收开锁、查询状态等指令；网关负责转发门锁与平台之间的数据；后台则负责下发管理操作。在浏览器中打开管理后台地址，可以查看已绑定的门锁信息、网关状态以及可执行的管理操作。

点击后台中的远程开锁按钮，如果门锁发出开锁声音或状态发生变化，说明门锁节点、LoRa 网关、云端后台之间的通信链路已经搭建成功。此时设备已经具备正常 LoRa 通信条件。

#### LoRa 通信触发过程

当后台点击开锁、查询状态等操作时，后台服务器会先把控制指令发送给 LoRa 网关。网关收到指令后，将其封装成对应的私有 LoRa 数据帧，并通过 LoRa 空口发送给门锁节点。

门锁节点收到 LoRa 数据包后，会根据自身配置的频率、带宽、扩频因子、同步字等参数进行接收和解调。解调成功后，门锁会进一步校验设备 ID、命令字、滚动码、CRC/MAC 等字段。如果校验通过，则执行对应操作，例如开锁或状态上报；如果校验失败，则丢弃该数据包。

![4.png](https://www.iotsec-zone.com/api/image/v2/20260716/djzyt7s2lhojuiu58v.png)

#### 使用 HackRF 观察空口信号并抓取iq文件进行参数分析

在后台触发开锁或查询操作时，同时使用 HackRF、Gqrx 或其他频谱观察工具查看 410 MHz 到 470 MHz 频段内是否出现 LoRa 信号。通过瀑布图中突然出现的高亮 Chirp 信号，可以初步判断设备的工作频段在435.804014 MHz附近。

![5.png](https://www.iotsec-zone.com/api/image/v2/20260716/djzytktmoxfkhmjawn.png)

#### 参数估算与抓包工具配置

使用 `hackrf_transfer` 工具对 LoRa 信号进行采集，抓取 IQ 数据的命令如下：

```bash
hackrf_transfer -r capture_436000_4m_lowgain.iq -f 436000000 -s 4000000 -a 1 -l 8 -g 8
```

其中，`-r` 用于指定保存的 IQ 文件名；`-f 436000000` 表示中心频率设置为 436 MHz；`-s 4000000` 表示采样率为 4 MS/s；`-a 1` 表示开启天线供电或相关射频配置；`-l 8` 表示 LNA 增益；`-g 8` 表示 VGA 增益。

获得 IQ 数据后首先要对数据进行解析，从真实电磁波到数字信号。这是 SDR 的起点。HackRF 的 ADC（模数转换器）将模拟射频信号采样并量化为交替存储的 8 位有符号 I/Q 数据。`I` 代表同相分量，`Q` 代表正交分量。二者结合成一个复数 `I + jQ`，能够保留后续基带处理所需的瞬时幅度和相位信息，这是后续频谱分析、时频分析和解调处理的基础。

```python
raw = np.fromfile("capture_436000_4m_lowgain.iq", dtype=np.int8)  #把 .iq 文件里的每个字节按顺序读到内存，按 int8 的规则翻译成 -128 到 127 之间的一个数，把所有数字装进一个叫 raw 的 NumPy 数组缓冲区里
raw = raw[:(raw.size // 2) * 2]                                   #对 raw 这个数组本身做一个微调，确保它的长度是偶数，然后把调整后的结果重新赋值给 raw，因为 IQ 数据是成对出现的：一个 I 必须搭配一个 Q。如果文件里总共有奇数个数字，说明最后一个 Q 或者 I 丢失了。在下一个步骤分离 I/Q 时，用 raw[0::2] 和 raw[1::2] 要求两路长度一致，否则会报错。
x = raw[0::2].astype(np.float32) / 128.0 \
  + 1j * raw[1::2].astype(np.float32) / 128.0  #将数据内的I/Q分离，从索引0开始，每隔两个取一个，取出偶数位置的元素I，从索引I开始，每隔两个取出一个，取出奇数位置的索引元素Q，再将这些整数转成32位浮点数确保精度，因为后续所有信号处理算法，都需要在 -1.0 到 1.0 之间的标准浮点数，所以需要`/128.0`,让信号从“原始 ADC 整数”变成“算法可用的标准浮点信号”。这样即防止计算溢出，与物理意义解耦，也是算法库的通用约定。最后再用 I + 1j * Q 合成复数信号，赋给变量 x，它就是最终可以用来做 FFT、频谱分析、解调的信号。
 ```
 
 由此，我们完成了对 LoRa IQ 数据的解析和预处理。

##### 频谱分析

**1. 找信号最强的一段时间窗口**

```python
def pick_strong_window(x: np.ndarray, fs: float, block_ms: float, window_s: float):  #x 就是我们之前解析出来的信号 fs 就是采样率4MHz block_ms 控制检测粒度 window_s 决定最终取多长一段给后续频谱分析用。
    block_size = int(fs * block_ms / 1000.0)   #把信号切成小块
    nblocks = len(x) // block_size             #计算有多少个完整的块，len(x)：信号的总采样点数，block_size：每小块包含的采样点数，//：整除

    energies = np.empty(nblocks, dtype=np.float64) #创建一个空数组准备装结果，np.empty(nblocks)：创建一个长度为 nblocks（比如 1000）的一维数组，dtype=np.float64：数组里的每个元素是 64 位浮点数
    #np.empty 只分配内存空间，不初始化里面的值，所以比 np.zeros 快一点点。因为后面的循环会依次给每个位置赋值，初始值是什么无所谓，用 np.empty 就够了。
    
    #计算每一块的能量
    for i in range(nblocks):
        block = x[i * block_size : (i + 1) * block_size]
        block = block - np.mean(block)        #去直流，避免直流偏移影响能量计算；直流偏移，简单说就是整个信号波形在纵轴方向上，整体向上或向下平移了一段固定的距离，没有围绕零点上下对称。
        energies[i] = np.mean(np.abs(block) ** 2)  #np.abs(block) ** 2：每个采样点的瞬时功率（I² + Q²），np.mean(...)：这一小块的平均功率

    #找到能量最大的块
    best_block = int(np.argmax(energies))     #np.argmax(energies)：找出 energies 数组里最大值的索引号，也就是第几块能量最高。使用int确保整数类型，
    best_time = best_block * block_size / fs  #best_time：把这个索引号换算成时间。
    
    window_len = int(window_s * fs)           #确定分析窗口的长度
    start = max(0, best_block * block_size - window_len // 3) #计算窗口的起始位置；best_block * block_size：能量最强块在文件里的采样点索引；- window_len // 3：把窗口起始点往前挪 1/3 窗口长度。这样最强块就落在窗口的前 1/3 处，而不是正中间。最强块通常是数据包中间的某个高能量部分。把窗口往前多留一点，就能把前导码也框进来。前导码在数据包的最前面，如果窗口从最强块才开始，很可能会把前导码截掉，导致后续解调失败；max(0, ...)：防止起始点小于 0（文件开头）
    end = min(len(x), start + window_len)     #计算窗口的结束位置并修正
    start = max(0, end - window_len)

    return x[start:end], start / fs, best_time, energies #返回四个结果：x[start:end]	裁剪出的最强信号片段；start / fs	这个片段在文件里的起始时间；best_time	能量最高块对应的时间；energies	所有块的能量数组
  ```
  
这段代码就是为了将我们真正有用的信号（最强的信号）从漫长的噪声中提取出来，并把这个信号框起来，作为后续分析的输入。

**2. 对这一段做平均频谱 PSD**

上一步我们得到了信号的时域，这个阶段，我们要把这段时域变成频域。也就是傅里叶变换，就是把“随时间变化的波形”变成“各个频率上的能量分布”。

```python
#seg np.ndarray	裁剪好的复数 IQ 信号片段	pick_strong_window 的第一个返回值；fs float	采样率（Hz）	采集时的设置；nfft	int	每次 FFT 的点数；hop	int	滑动步长（采样点数）
def averaged_psd(seg: np.ndarray, fs: float, nfft: int, hop: int):
    window = np.hanning(nfft).astype(np.float32)   #np.hanning(nfft)：生成长度为 nfft 的汉宁窗数组，减少频谱泄漏；.astype(np.float32)：转成 32 位浮点数，节省内存，加快后续乘法速度。
    acc = np.zeros(nfft, dtype=np.float64)         #用 nfft 创建累加器，准备存放平均功率谱：创建一个长度等于 nfft 的全零数组，用 64 位浮点数；后续每次 FFT 算出的功率谱 |FFT|² 会累加到这个数组里。
    count = 0                                      #统计一共做了多少次 FFT，最后求平均用 acc / count。

    for pos in range(0, len(seg) - nfft + 1, hop): #按步长滑动窗口：pos 是每一小段的起始位置（采样点索引）；range(开始, 结束, 步长)：从 0 开始，每次往后跳 hop 个点，直到 len(seg) - nfft 为止；len(seg) - nfft + 1：确保最后一段刚好能取满 nfft 个点，不会超出信号范围。这样做可以让最终的频谱更平滑。
        s = seg[pos : pos + nfft]                   #从 seg 里取出从 pos 开始、长度为 nfft 的一小段复数信号。
        s = s - np.mean(s)                          #减去这一段的平均值，把直流偏移消除，让信号以零为中心。
        fft = np.fft.fftshift(np.fft.fft(s * window)) #s * window：把信号 s 乘上之前准备好的window。信号两端被压到接近零，减少频谱泄漏；np.fft.fft(...)：执行 FFT，输出是复数频谱（每个频率点的幅度和相位）np.fft.fftshift(...)：把频谱的 0 Hz 移到正中间，让负频率在左边、正频率在右边，方便观察。
        acc += np.abs(fft) ** 2                     #np.abs(fft)：取复数的模，即每个频率分量的幅度；** 2：平方，得到功率（幅度² = 功率）；acc += ...：把这次算出的功率谱加到累加器 acc 里。
        count += 1                                  #做完一次 FFT，计数器加 1。循环结束后 acc / count 就是平均功率谱。

    power = 10.0 * np.log10(acc / max(count, 1) + 1e-20) #(acc / max(count, 1) + 1e-20):之前循环累加的所有 FFT 功率谱之和（线性功率，单位是幅度²），除以次数，得到平均线性功率,加上1e-20防止任何一个频率点的平均功率恰好为 0 时，log10(0) 算出负无穷大（-inf）；10.0 * np.log10把线性功率转成 dB（分贝）刻度
    freq = np.fft.fftshift(np.fft.fftfreq(nfft, 1.0 / fs))#生成 FFT 每个 bin 对应的频率值；把频率轴重新排列成：[负频率, ..., 0, ..., 正频率]
    return freq, power                              #freq p.ndarray	频率轴，单位 Hz，0 Hz 居中；power	np.ndarray平均功率谱，单位 dB，和 freq 一一对应
#这两个数组可以直接用来画频谱图（plt.plot(freq, power)），也可以交给下一步 find_signal_bands 去自动识别信号频段。
```

**3. 根据门限找主信号频段**

```python
def find_signal_bands(freq, power, threshold_db, dc_guard_hz, min_width_hz):
    # 估算噪声基底：取功率谱的第20百分位，避免信号峰拉高噪声估计
    noise_floor = float(np.percentile(power, 20))
    # 动态门限 = 噪声底 + 人工设定的偏移量（如15dB）
    threshold = noise_floor + threshold_db

    # 标记"活跃"频率点：功率超门限 且 不在直流保护区（0Hz附近）内
    active = (power > threshold) & (np.abs(freq) > dc_guard_hz)

    bands = []          # 存放所有检测到的信号频段
    i = 0
    # 遍历 active 数组，找连续为 True 的段（连通域检测）
    while i < len(active):
        # 当前点是噪声，跳过
        if not active[i]:
            i += 1
            continue

        # 找到一段连续活跃区域：从 i 到 j-1
        j = i + 1
        while j < len(active) and active[j]:
            j += 1

        # 计算这段的频率宽度
        width = freq[j - 1] - freq[i]
        # 宽度太小视为噪声毛刺，过滤掉
        if width >= min_width_hz:
            # 找到这段里功率最大的频率点
            peak_idx = i + int(np.argmax(power[i:j]))

            # 用信号强度做权重，计算加权中心频率（能量重心）
            weights = np.maximum(power[i:j] - noise_floor, 0.0)  # 噪声底以下归零
            weighted_center = float(np.sum(freq[i:j] * weights) / np.sum(weights))

            # 把这段信号的所有属性打包成字典，存入列表
            bands.append({
                "low_off": float(freq[i]),            # 低边界频率偏移（Hz）
                "high_off": float(freq[j - 1]),       # 高边界频率偏移（Hz）
                "width": float(width),                # 带宽（Hz）
                "center_off": weighted_center,        # 加权中心频率偏移（Hz）
                "peak_off": float(freq[peak_idx]),    # 峰值频率偏移（Hz）
                "peak_power": float(power[peak_idx]), # 峰值功率（dB）
            })

        i = j   # 跳到这段末尾，继续扫描后面的频率

    # 按信号强度和带宽降序排列，最强的排最前面
    bands.sort(key=lambda b: (b["peak_power"], b["width"]), reverse=True)
    return bands, noise_floor, threshold
   ```
   
   **4. 最后换算成真实频率和 LoRa 标准带宽**
   
   ```python
   selected = bands[0]                                      # 取列表中信号最强（峰值功率最大）的那一组频段数据
f_low = args.center + selected["low_off"]                # 换算真实低频：采集中心频率 + 该频段的低边界偏移量
f_high = args.center + selected["high_off"]              # 换算真实高频：采集中心频率 + 该频段的高边界偏移量
f_center = args.center + selected["center_off"]          # 换算真实中心：采集中心频率 + 该频段能量加权的中心偏移量
width = selected["width"]                                # 该频段的实际占用带宽（Hz），数值可能略大于标准值
standard_bw = nearest_lora_bw(width)                     # 将实际带宽就近映射为 LoRa 标准带宽（125 kHz/250 kHz/500 kHz）
```

总结下来，首先通过`read_hackrf_iq`函数将交替存储的int8类型IQ数据转换为复数信号，完成从原始字节到数学可处理格式的转换。接着使用`pick_strong_window`函数将信号按时间切分成小块并计算每块的能量，找到能量最强的块后以它为中心裁剪出一段固定长度的分析窗口，从而从长时间的噪声背景中精准提取出包含有效信号的那段时域数据。然后调用`averaged_psd`函数对这段信号进行平均功率谱估计，通过滑动窗口逐段做FFT并累加求平均，将时域信号转换为一条平滑的频域功率谱曲线，使信号峰突出、噪声基底平坦。随后由`find_signal_bands`函数在这条频谱上自动识别信号频段，它先根据功率谱的第20百分位估算噪声基底并设定动态门限，再排除直流保护区内的尖峰、过滤掉宽度不足的毛刺干扰，最后通过连通域检测找出所有连续超过门限的频率段，并对每个有效频段计算其频率边界和能量加权的中心频率。最后从检测结果中选取峰值功率最强的那个频段，将其相对于采集中心频率的偏移量加上中心频率得到真实的低边界、高边界和中心频率，同时根据实测带宽映射到最接近的LoRa标准带宽值，从而完成中心频率和带宽这两项物理层核心参数的估算。最终实测主信号占用带宽约为 129.15 kHz。考虑到 LoRa 使用标准带宽档位，且实际测量会受到门限、噪声和频偏影响，因此将其归一到最接近的 LoRa 标准带宽 125 kHz。

##### 扩频因子

**扩频因子**，就是 LoRa 技术里一个核心的可调参数，它的作用一句话说就是：**用传输速度换接收灵敏度**。扩频因子越高，信号就能传得越远、抗干扰能力越强，但代价是传得更慢，发同样多的数据需要更长的空中时间，也会消耗更多电量。

已知LoRa符号周期公式是
    
```text
Tsym = 2^SF / BW
```

已知BW=125kHz，各 SF 对应符号周期为：

```text
SF7:  128 / 125000 = 1.024 ms
SF8:  256 / 125000 = 2.048 ms
SF9:  512 / 125000 = 4.096 ms
SF10: 1024 / 125000 = 8.192 ms
SF11: 2048 / 125000 = 16.384 ms
SF12: 4096 / 125000 = 32.768 ms
```

所以说，我们只要能测出Tsym（**符号周期**）就能知道SF是多少。最开始都要对数据进行复数处理和最高频信号处理，再带入我们上一步得到的真实带宽。

**1.搬频到基带 + 降采样**

```python
# 计算信号真实中心频率与 HackRF 接收中心频率之间的偏移量
freq_offset = args.signal_center - args.rx_center
# 生成与信号片段等长的时间索引序列
n = np.arange(len(seg), dtype=np.float64)

# 通过复指数乘法实现频率搬移，将信号中心频率移至 0 Hz（基带）
y = seg * np.exp(-2j * np.pi * freq_offset * n / args.fs)
# 去除搬频后信号中可能存在的直流分量
y = y - np.mean(y)

# 降采样：通过分组取均值的方式降低采样率，减少后续 STFT 的计算量
if args.decim > 1:
    # 将信号长度截断为降采样因子的整数倍，确保可均匀分组
    usable = (len(y) // args.decim) * args.decim
    y = y[:usable]
    # 重塑为二维数组，每行包含 decim 个采样点，对每行取均值
    y = y.reshape(-1, args.decim).mean(axis=1)
    # 更新等效采样率
    fs_plot = args.fs / args.decim
else:
    # 不降采样时保持原始采样率
    fs_plot = args.fs
```

**2.生成 Chirp 瀑布图**

```python
# 创建画布，设置图像尺寸（宽 14 英寸，高 7 英寸）
plt.figure(figsize=(14, 7))
# 调用 matplotlib 内置的频谱图函数，执行 STFT 并绘制瀑布图
plt.specgram(
    y,                       # 输入：已搬频至基带的复数 IQ 信号
    NFFT=args.nfft,          # FFT 窗口长度，决定频率分辨率
    Fs=fs_plot,              # 降采样后的等效采样率
    noverlap=args.noverlap,  # 相邻窗口的重叠采样点数，值越大时间轴越平滑
    mode="magnitude",        # 显示模式：幅度谱
    scale="dB",              # 幅度转换为分贝刻度
    cmap="viridis",          # 颜色映射方案
)

# 将纵轴显示范围限制在信号带宽附近的区间，避免远端噪声干扰图像对比度
ylim_hz = args.ylim_khz * 1000.0
plt.ylim(-ylim_hz, ylim_hz)

# 标注横轴（时间，以信号片段起始时刻为参考零点）
plt.xlabel(f"Time (s from {seg_start_s:.3f}s)")
# 标注纵轴（频率偏移，相对于信号中心频率的差值，单位 Hz）
plt.ylabel(f"Offset from {args.signal_center / 1e6:.6f} MHz (Hz)")
# 设置图表标题
plt.title("LoRa Chirp Spectrogram")
# 添加颜色条，标注 dB 刻度
plt.colorbar(label="dB")
# 自动调整子图布局，避免标签被裁剪
plt.tight_layout()
# 将图像保存为 PNG 文件，设置输出分辨率为 180 DPI
plt.savefig(args.out, dpi=180)
```

对原始 IQ 数据进行频率搬移与降采样预处理，利用短时傅里叶变换生成 LoRa 信号的时频瀑布图。

![6.png](https://www.iotsec-zone.com/api/image/v2/20260716/djzyyixh6ngikyfukd.png)

图中约 15 ms 的时间窗口内可见约 14 ~ 15 个完整 chirp，因此单个 chirp 的周期约为 1.0~1.1 ms。结合前面频谱分析得到的带宽 BW=125 kHz，根据 LoRa 符号周期公式 Tsym=2^SF/BW，可得：2^SF ≈ 0.001024 × 125000 ≈ 128。因此 SF≈7。

##### 前导码、同步字

在完成中心频率、带宽和扩频因子的估算后，还需要进一步确定 LoRa 数据包的前导码长度和同步字。前导码用于接收端进行包检测、时间同步和频偏估计；同步字用于区分不同 LoRa 网络或私有系统。如果同步字不匹配，即使频率、带宽和扩频因子正确，接收端也可能无法正常输出数据包。

**1. 构造本地 LoRa upchirp**

```python
def make_upchirp(fs: float, bw: float, sf: int):
    # 根据 LoRa 符号周期公式计算一个符号包含多少个采样点。
    # Tsym = 2^SF / BW
    # 本实验中 fs=4_000_000，bw=125_000，sf=7，
    # Tsym = 128 / 125000 = 0.001024 s，
    # n = fs * Tsym = 4000000 * 0.001024 = 4096 点。
    n = int(round(fs * (2**sf / bw)))

    # 构造一个符号周期内的时间轴。
    # t[0] = 0，t[1] = 1/fs，直到一个符号周期结束。
    t = np.arange(n, dtype=np.float64) / fs

    # k 表示扫频斜率，单位 Hz/s。
    # upchirp 会在一个符号周期内从 -BW/2 扫到 +BW/2，
    # 总共扫过 BW Hz，因此 k = BW / Tsym。
    k = bw / (n / fs)

    # 计算 upchirp 的相位。
    # 频率随时间线性变化：f(t) = -BW/2 + k*t
    # 对频率积分得到相位：
    # phase(t) = 2π * [(-BW/2)*t + 0.5*k*t^2]
    phase = 2.0 * np.pi * ((-bw / 2.0) * t + 0.5 * k * t * t)

    # 将相位转换成复数 IQ 信号：exp(j*phase) = cos(phase) + j*sin(phase)。
    # 返回的就是一个理想 LoRa upchirp 参考信号。
    return np.exp(1j * phase).astype(np.complex64)
```

这一步生成的是一个理想参考波形。本实验参数下，该参考 upchirp 长度为 4096 个采样点，持续时间约为 1.024 ms，频率从 `-62.5 kHz` 扫到 `+62.5 kHz`。后续 dechirp 就是把真实信号和这个参考信号进行比较。

**2. 对每个符号进行 dechirp + FFT**

```python
def dechirp_sequence(y: np.ndarray, fs: float, bw: float, sf: int, offset: int):
    # 生成本地理想 upchirp。
    upchirp = make_upchirp(fs, bw, sf)

    # n 是一个 LoRa 符号的采样点数，本实验中为 4096。
    n = len(upchirp)

    # 取 upchirp 的共轭，作为 dechirp 参考信号。
    # 如果真实符号是 upchirp，与共轭 upchirp 相乘后，扫频会被抵消。
    ref = np.conj(upchirp)

    bins = []     # 保存每个符号 dechirp 后 FFT 峰值所在的 bin
    ratios = []   # 保存峰值与中位数的比值，单位 dB，用于判断该符号是否足够明显
    peaks = []    # 保存峰值幅度

    # 从 offset 开始，每次取一个符号长度 n 的数据进行分析。
    for pos in range(offset, len(y) - n + 1, n):
        # 取出一个符号长度的 IQ 数据。
        sym = y[pos : pos + n]

        # dechirp：真实符号乘以本地 upchirp 的共轭。
        # 如果该符号是标准 upchirp，乘完后会变成接近单频信号。
        z = sym * ref

        # 对 dechirp 后的符号做 FFT。
        spec = np.fft.fft(z)
        mag = np.abs(spec)

        # 找到 FFT 能量最大的 bin。
        peak_bin = int(np.argmax(mag))
        peak = float(mag[peak_bin])

        # 用峰值除以中位数，判断该符号是否有明显单频峰值。
        median = float(np.median(mag) + 1e-12)
        ratio_db = 20.0 * np.log10(peak / median)

        bins.append(peak_bin)
        ratios.append(ratio_db)
        peaks.append(peak)

    return np.array(bins), np.array(ratios), np.array(peaks)
```

这段代码的作用是把每个 LoRa 符号转换成一个 FFT 峰值。如果某一串符号的 `ratio_db` 很高，并且 `peak_bin` 基本不变，就说明这一串符号很像 LoRa 前导码。因为 LoRa 前导码本质上就是多个连续稳定的 upchirp。

**3. 搜索连续稳定的前导码区域**

```python
def find_best_preamble(y: np.ndarray, fs: float, bw: float, sf: int,
                       min_ratio_db: float, bin_tolerance: int):
    # 计算一个符号的采样点数。
    n = len(make_upchirp(fs, bw, sf))
    best = None
    # 因为真实包的符号边界不一定刚好从第 0 个采样点开始，
    # 所以要尝试多个 offset，寻找最合适的切片起点。
    for offset in range(0, n, max(1, n // 64)):
        bins, ratios, peaks = dechirp_sequence(y, fs, bw, sf, offset)
        i = 0
        while i < len(bins):
            # 如果当前符号峰值不够强，说明不像有效 chirp，跳过。
            if ratios[i] < min_ratio_db:
                i += 1
                continue
            # 以当前符号的 peak bin 作为前导码候选基准 bin。
            base = bins[i]
            j = i + 1
            # 向后寻找连续符号：要求峰值足够强，并且 bin 和 base 足够接近。
            while j < len(bins):
                diff = min((bins[j] - base) % n, (base - bins[j]) % n)
                if ratios[j] >= min_ratio_db and diff <= bin_tolerance:
                    j += 1
                else:
                    break
            # run_len 表示连续稳定符号数量。
            run_len = j - i
            # 记录最长的连续稳定区域，作为最佳前导码候选。
            if best is None or run_len > best["run_len"]:
                best = {
                    "offset": offset,
                    "symbol_index": i,
                    "run_len": run_len,
                    "base_bin": int(base),
                    "bins": bins,
                    "ratios": ratios,
                }
            i = max(j, i + 1)
    return best
```

这一步的判断标准有两个：第一，符号 dechirp 后的峰值要足够明显，也就是 `ratio_db` 要高于 `min_ratio_db`；第二，连续多个符号的峰值 bin 要稳定，也就是 bin 之间的偏差不能超过 `bin_tolerance`。满足这两个条件的一长串符号，就可以视为前导码。

本实验生成的图中，绿色区域就是脚本找到的稳定前导码区域。可以看到连续约 20 个符号的 dechirp peak bin 基本稳定在 4095 附近，并且峰值/中位数比值约为 50 dB，高于 42 dB 门限。因此判断本次 LoRa 数据包中的前导码长度为：

```text
前导码长度：20 个 upchirp
前导码基准 bin：4095
```

**4. 根据前导码后的两个 sync symbol 计算同步字**

前导码结束后，紧跟着会出现同步字相关的符号。脚本会取前导码后面的两个符号作为 sync symbol，并计算它们相对于前导码基准 bin 的循环偏移。

```python
def estimate_sync(best):
    bins = best["bins"]                   # 所有符号 dechirp 后的 peak bin 序列
    ratios = best["ratios"]               # 每个符号的峰值/中位数比值，用于绘图显示
    n = best["symbol_samples"]            # 一个 LoRa 符号的采样点数，本实验为 4096
    base = best["base_bin"]               # 前导码区域的基准 bin，本实验约为 4095

    # sync1_idx 和 sync2_idx 分别表示前导码后面的两个同步符号位置。
    sync1_idx = best["symbol_index"] + best["run_len"]
    sync2_idx = sync1_idx + 1

    # 若同步符号超出分析范围，则无法估算同步字。
    if sync2_idx >= len(bins):
        return None

    # 计算两个 sync symbol 相对于前导码基准 bin 的循环偏移。
    rel1 = (bins[sync1_idx] - base) % n
    rel2 = (bins[sync2_idx] - base) % n

    # LoRa 同步字映射关系：
    # 高 4 bit << 3 对应第一个 sync symbol；
    # 低 4 bit << 3 对应第二个 sync symbol。
    nibble1 = round(rel1 / 8) & 0x0F
    nibble2 = round(rel2 / 8) & 0x0F
    sync_word = (nibble1 << 4) | nibble2

    return {
        "idx": (sync1_idx, sync2_idx),
        "bins": (bins[sync1_idx], bins[sync2_idx]),
        "ratios": (ratios[sync1_idx], ratios[sync2_idx]),
        "relative": (rel1, rel2),
        "sync_word": sync_word,
    }
```

图中红色点就是前导码后的两个 sync symbol。脚本识别到：

```text
前导码基准 bin ≈ 4095
第一个 sync symbol bin ≈ 7
第二个 sync symbol bin ≈ 15
```

计算相对前导码基准 bin 的循环偏移：

```text
(7  - 4095) mod 4096 = 8
(15 - 4095) mod 4096 = 16
```

根据 LoRa 同步字映射关系：

```text
高 4 bit << 3 = 第一个 sync symbol 相对偏移
低 4 bit << 3 = 第二个 sync symbol 相对偏移
```

因此：

```text
8  = 1 << 3
16 = 2 << 3
```

最终得到 LoRa 单字节同步字：

```text
LoRa SyncWord = 0x12
```

需要注意的是，本实验使用的串口 LoRa 抓包工具显示的是模块寄存器风格的同步字格式。在该工具中，LoRa SyncWord `0x12` 对应填写为：

```text
同步字：0x1424
```

![7.png](https://www.iotsec-zone.com/api/image/v2/20260716/djzyzblr0394hrgakf.png)

由此，结合前面已经估算出的中心频率、带宽和扩频因子，可以得到本实验最终用于抓包工具的参数：

| 参数          | 估算结果       | 抓包工具填写                       |
| :------------ | :------------- | :--------------------------------- |
| 中心频率      | 435.803014 MHz | 435.803014 MHz 或 435.804 MHz 附近 |
| 带宽          | 125 kHz        | 125 kHz                            |
| 扩频因子      | SF7            | 7                                  |
| 前导码        | 20 个 upchirp  | 20                                 |
| LoRa SyncWord | 0x12           | 1424                               |

将上述参数填入 LoRa 抓包工具后，持续触发门锁发包，观察工具是否能够稳定输出数据帧。

#### 抓取数据包

将上述估算参数填写进抓包工具。

![8.png](https://www.iotsec-zone.com/api/image/v2/20260716/djzz1zm3nctq5or5we.png)

![9.png](https://www.iotsec-zone.com/api/image/v2/20260716/djzyzsi1oqw9s7shx4.png)

一次远程开锁操作会触发三帧 LoRa 数据交互。第一帧为下行控制帧，由网关发送至门锁，用于触发远程开锁；第二帧和第三帧为上行状态/结果回传帧，长度均为 34 字节，由门锁返回，用于上报门锁状态变化、执行结果和操作确认。

由于该设备使用滚动码和 AES-128 加密，抓到的旧数据包不能直接用于重放。也就是说，物理层参数匹配只能保证我们能够接收到 LoRa Payload，但是否能够被门锁接受，还取决于私有协议层中的滚动码、加密载荷和完整性校验。旧包在再次发送时，通常会因为滚动码过期、计数器不匹配或 MAC/CRC 校验失败而被丢弃。

后续分析重点应从 LoRa 物理层转向私有协议层和安全校验层。可以连续抓取多组同类命令数据包，对比固定字段和变化字段，进一步推测设备 ID、命令字、滚动码、AES 密文载荷和校验字段的位置。滚动码可能作为明文字段参与校验，也可能作为 AES 的 IV、Nonce、计数器或 MAC 计算输入，因此需要结合多包对比和固件/网关侧逻辑进一步验证。
