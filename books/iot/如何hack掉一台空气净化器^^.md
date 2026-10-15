# 如何hack掉一台空气净化器^^
> heiyu
> 来源：https://www.iotsec-zone.com/article/462

![0.png](https://www.iotsec-zone.com/api/image/v2/20240820/d3ks9bo0jjonyxxrbf.png)

# 介绍

最近，我有点着迷于将我家里的任何东西都连接到 Home Assistant。将一切连接并自动化在一个应用程序中是如此令人满足；我终于可以忘记为不同品牌的智能产品而下载的每个随机移动应用程序。

但是我拥有的一个产品固执地只与自己的移动应用程序连接，与其他任何东西都不连接。这是一款时尚的空气净化器，不幸的是，它的令人失望的应用程序让人失望。

在我的业余时间里，我一直在着手一个项目，该项目可以像这样从智能设备中去除云依赖性。如此多的现代产品依赖于互联网连接和云账户进行基本功能，谁知道它们收集了什么不必要的数据或者给家庭网络增加了什么技术漏洞呢？

我想像控制我的其他智能设备一样控制这台昂贵的空气净化器。这标志着这段具有挑战性但无疑有趣的旅程的开始。

**是时候黑掉一个空气净化器了！** 😆

# 计划
如果我们要将这个设备黑客成由定制软件控制，我们需要了解它当前的功能，并计划一个攻击点，以最少的工作量来实现我们的目标。

该设备已经支持使用自己的移动应用进行远程控制，令人讨厌的是需要一个云账户才能使用。通过切换手机的蓝牙、WiFi 和 5G，我确认该应用需要互联网连接才能控制设备。无法通过蓝牙或 WiFi 在本地进行远程控制。

这意味着移动应用程序和设备必须连接到云服务器，才能实现远程控制。因此，在网络中的某个地方，设备和其云服务器之间的数据必须是风扇速度和应用程序控制的其他所有内容。

所以，这就是我们的攻击点：

- 如果我们能拦截设备的网络流量并更改这些值，我们就可以控制设备。
- 如果我们能够模拟所有服务器响应，我们就可以控制设备，而不依赖于互联网连接和其云服务器。

# 移动应用分析

我调查的第一件事之一是遥控移动应用程序。这可以是快速收集一些信息的方法，因为 Android 应用程序相对简单易懂。

Android 上的应用程序存储为 `.apk` 文件。通过快速在线搜索，您可以找到一个网站来下载特定应用程序的最新 `.apk` 。如果您不知道， `.apk` 的格式在技术上是一个 `.zip` 文件！您可以简单地提取它们以浏览应用程序的内容。

Android 应用程序包括已编译的 Java 可执行文件，通常命名为 `classes.dex` 。您可以使用 dex2jar 将其转换为 `.jar` 文件，并使用 jd-gui 浏览内容，查看重建的源代码。

定位应用程序 `MainActivity.class` 发现它是使用 React Native 构建的！

```
1. package com.smartdeviceapp;
2. 
3. import com.facebook.react.ReactActivity;
4. 
5. public class MainActivity extends ReactActivity {
6. protected String getMainComponentName() {
7. return "SmartDeviceApp";
8. }
9. }
```

对于使用 React Native 构建的 Android 应用程序，您可以在 `assets/index.android.bundle` 中找到 JavaScript 捆绑包。

应用程序包的快速扫描显示它使用了安全的 WebSocket 连接

```
1. self.ws = new WebSocket("wss://smartdeviceapi.---.com");
```
这个安卓应用程序在这里并没有太多的兴趣；正如预期的那样，它连接到他们的云服务器，以便远程控制智能设备。由于获取一些可读的源代码的简单性，它值得快速查看。我们可以随时参考这个捆绑包，看看是否可以找到任何共享值或逻辑。

# 网络检查
接下来，是时候看一下设备和其云服务器之间的网络流量了；这就是我们试图拦截并理想情况下模拟的内容。

我在本地使用 Pi-hole，这是一个 DNS 服务器，可以阻止跟踪和一些广告，但它还有一个有用的功能，可以按设备浏览 DNS 查询。通过导航到 `Tools>Network` 页面并选择设备的本地网络地址，我们可以看到它正在查询 DNS 服务器以获取云服务器域名的地址：

![1.png](https://www.iotsec-zone.com/api/image/v2/20240820/d3ksd9q59d5oohy4ds.png)

openinfull

所以现在我们知道云服务器连接到的域，我们可以使用 `LocalDNS` 功能将该网络流量发送到我的本地工作站（ `192.168.0.10` ）而不是他们的云服务器：

![2.png](https://www.iotsec-zone.com/api/image/v2/20240820/d3ksdpfnvdsvoqvoy9.png)

openinfull

我们可以使用 Wireshark 来查看来自智能设备的流量。我们可以通过监视工作站网络接口，并使用过滤器 `ip.addr==192.168.0.61` （智能设备地址）来实现这一点。

通过这样做，我能够看到从智能设备发送到工作站端口 `41014` 的 UDP 数据包！

# 数据包分析

所以，我们知道智能设备使用 UDP 与其云服务器进行通信。但现在，它正在尝试与我的工作站通信，并期望它像云服务器一样做出响应。

我们可以为我们的工作站使用一个简单的 UDP 代理，以充当智能设备和其云服务器之间的中继。

我使用了 Cloudflare 的 DNS 解析器（ `1.1.1.1` ）来查找他们云服务器的真实 IP 地址（因为我的 Pi-hole DNS 只会解析到我的工作站的本地 IP 地址）。然后我使用 node-udp-forwarder 作为一个简单的方法来中继流量到他们的云服务器：

```
1. udpforwarder \
2. --destinationPort 41014 --destinationAddress X.X.X.X \
3. --protocol udp4 --port 41014
```

`X.X.X.X` 是他们云服务器的真实 IP 地址。

再次查看 Wireshark，我们可以看到智能设备和其云服务器之间的所有网络流量！

启动设备时，它会向服务器发送一个包含如下数据的数据包：

```
1. Hex View 00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F
2. 
3. 00000000 55 00 31 02 01 23 45 67 89 AB CD EF FF 00 01 EF U.1..#Eg........
4. 00000010 1E 9C 2C C2 BE FD 0C 33 20 A5 8E D6 EF 4E D9 E3 ..,....3 ....N..
5. 00000020 6B 95 00 8D 1D 11 92 E2 81 CA 4C BD 46 C9 CD 09 k.........L.F...
6. 00000030 0E   
```

服务器将会以以下方式回应：

```
1. Hex View 00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F
2. 
3. 00000000 55 00 2F 82 01 23 45 67 89 AB CD EF FF 37 34 9A U./..#Eg.....74.
4. 00000010 7E E6 59 7C 5D 0D AF 71 A0 5F FA 88 13 B0 BE 8D ~.Y|]..q._......
5. 00000020 ED A0 AB FA 47 ED 99 9A 06 B9 80 96 95 C0 96 ....G..........
```
所有在此之后的数据包似乎具有相似的结构。它们不包含任何可读的字符串，但充满了看起来是随机数据字节；这可能是指向加密的雪崩效应。

我搜索了一下，看看这个数据包结构是否是一种现有的协议。我读到 DTLS 被一些智能设备使用，并且它是基于 UDP 的。

然而，Wireshark 确实支持检测 DTLS 数据包，但将此数据包列为 UDP，这意味着它无法从数据中确定基于 UDP 的协议。我再次检查了 DTLS 规范，但描述的头部格式与我们在数据包中看到的不同，因此我们知道这里没有使用 DTLS。

在这一点上，我们遇到了一个阻碍；我们不理解这些数据包中的数据是如何格式化的，这意味着我们还不能操纵或模拟任何东西。

如果使用一个文档完备的协议，这将会容易得多，但是这样做哪里有乐趣呢？

# 物理拆解

我们知道有两个应用程序能够理解如何读取这个数据包数据：智能设备和它的云服务器。嗯，我没有他们的云服务器，所以是时候看看智能设备里面了！

它很容易拆卸，只需拧下几颗易于取下的螺丝。内部是包含微控制器的主 PCB 板，连接到风扇的端口，以及连接到前面控制面板的带状电缆。

![3.png](https://www.iotsec-zone.com/api/image/v2/20240820/d3ksfuy9gc5d9xwnmf.png)

openinfull

主控制器标记为 `ESP32-WROOM-32D` 。这款微控制器通常用于智能设备，具有 WiFi 和蓝牙功能。

我偶然发现了 ESP32-reversing GitHub 仓库，其中包含了一份不错的与 ESP32 相关的逆向工程资源列表。

# 串行连接

ESP32 包含一个闪存芯片，其中最有可能存储固件和应用逻辑。

ESP32 的制造商提供了一个名为 esptool 的实用程序，用于与 ESP32 中的 ROM 引导加载程序进行通信。使用这个工具，可以从闪存中读取数据，但首先，我们必须建立一个串行连接！

参考 ESP32 数据表，我们可以找到引脚布局图：

![4.png](https://www.iotsec-zone.com/api/image/v2/20240820/d3ksgaea7fadabasrp.png)

openinfull

这里，我们可以看到 `TXD0` （35）和 `RXD0` （34）引脚。我们需要连接一根导线到这两个引脚和一个地引脚用于串行连接。

设备的 PCB 上有几个引脚孔，通常连接到用于调试和闪存的引脚；我能够通过目视追踪这两个串行引脚到这些孔！这使我能够轻松地焊接断开头，然后暂时插入跳线。否则，我可能会小心地直接焊接到芯片引脚。

使用设置为连续性模式的万用表，我能够通过参考 ESP32 上的 `GND` （38）引脚来确定哪个孔是地线。

现在，我们需要一个端口来处理这个 UART 串行通信。我使用了我的 Flipper Zero，它在 `GPIO` 类别下有一个方便的 `USB-UARTBridge` 应用程序。

使用 3 根跳线将它们连接在一起：

- Flipper Zero `TX` <--> `RX` ESP32
- Flipper Zero `RX` <--> `TX` ESP32
- Flipper Zero `GND` <--> `GND` ESP32

info 注意

`TX` 和 `RX` 线在这里被故意交叉；我们想要将数据传输到另一设备的接收线！

在 Windows 设备管理器中，在 `Ports(COM&LPT)` 类别下，我发现我的 Flipper Zero UART 设备显示为 `COM7` 。使用配置为串行连接的 Putty，在 `COM7` 上以 `115200` 速度，我成功地连接到了 Flipper Zero。在搜索过程中，我发现这个速度经常用于 ESP32，所以我决定在这里使用它。

当启动智能设备时，我注意到从串行输出中看到了一堆日志数据：

```
1. rst:0x1 (POWERON_RESET),boot:0x13 (SPI_FAST_FLASH_BOOT)
2. configsip: 0, SPIWP:0xee
3. clk_drv:0x00,q_drv:0x00,d_drv:0x00,cs0_drv:0x00,hd_drv:0x00,wp_drv:0x00
4. mode:DIO, clock div:2
5. load:0x3fff0030,len:4476
6. ho 0 tail 12 room 4
7. load:0x40078000,len:13512
8. ho 0 tail 12 room 4
9. load:0x40080400,len:3148
10. entry 0x400805f0
11. ********************************
12. ** Starting SmartDevice **
13. ********************************
14. This is esp32 chip with 2 CPU
core
(s), WiFi/BT/BLE, silicon revision1, 4MB external
flash
15. Minimum free heap size: 280696 bytes
16. nvs_flash_init ret: 0
17. Running app from: factory
18. Mounting FAT filesystem
19. csize: 1
20. 122 KiB total drive space.
21. 0 KiB available.
22. FAT filesystem mounted
23. SERIAL GOOD
24. CapSense Init
25. Opening[rb]: /spiflash/serial
26. Serial Number: 0123456789abcdefff
27. Opening[rb]: /spiflash/dev_key.key
28. Device key ready
29. Base64 Public Key: **REDACTED**
30. Opening[rb]: /spiflash/SmartDevice-root-ca.crt
31. Opening[rb]: /spiflash/SmartDevice-signer-ca.crt
32. Addtimeout: 10000, id: 0
33. RELOAD FALSE
34. Opening[rb]: /spiflash/server_config
35. MP PARSE DONE
36. Server: smartdeviceep.---.com:41014
```

我们可以从这个输出中挑选出一些有用的信息：
- 该设备配备了一颗 4MB 的闪存芯片。
- 应用程序从 `factory` 运行，这是工厂预装应用程序的常见分区名称。
- FAT 文件系统已挂载。
- 应用程序读取文件：
- 序列号
- 设备密钥
- 两个 CA 证书（根证书和签发者）
- 服务器配置

# 倾倒闪存
太棒了，现在我们有一个正常工作的串行连接，我们可以专注于转储闪存，希望它包含有关如何读取这些数据包的信息！

为了读取闪存，我们需要以不同模式启动 ESP32，具体来说，它称之为 `DownloadBoot` 模式。这在数据表的 `StrappingPins` 部分有技术解释。简而言之，我在 Flipper Zero 上从 `GND` 端口拉了一根跳线到 ESP32 的 `IO0` （25）引脚上，当它启动时。

使用 Putty 检查串行输出，我们可以看到这成功地将智能设备引导到 `DownloadBoot` 模式：

```
1. rst:0x1 (POWERON_RESET),boot:0x3 (DOWNLOAD_BOOT(UART0/UART1/SDIO_REI_REO_V2))
2. waiting for download
```

```
1. esptool -p COM7 -b 115200 read_flash 0 0x400000 flash.bin
```

我多次转储闪存，以确保我有一个良好的读取，并在备份它们，以防我们意外砖块某些东西，因为那样我们可以刷回转储。

info 注意

为了成功使用 Flipper Zero 读取闪存，我不得不更改其配置，将波特率指定为 `115200` 而不是 `Host` 。

# 快速分析

我们已经将 ESP32 闪存转储到一个单一的二进制文件中，现在我们需要理解它。我发现 esp32knife 是处理这个问题的最佳工具。

它读取闪存文件并提取一堆有用的信息。它还是唯一一个成功将这个转储文件重新格式化为带有正确映射虚拟内存的 ELF 格式的实用程序，但稍后再详细讨论！让我们看看我们能找到什么：

```
1. python esp32knife.py --chip=esp32 load_from_file ./flash.bin
```
这会记录大量信息并将输出数据保存到一个 `./parsed` 文件夹中。

这里感兴趣的第一个文件是 `partitions.csv` ，这个表将闪存中的数据区域映射到

```
1. # ESP-IDF Partition Table
2. # Name, Type, SubType, Offset, Size, Flags
3. nvs, data, nvs, 0x9000, 16K,
4. otadata, data, ota, 0xd000, 8K,
5. phy_init, data, phy, 0xf000, 4K,
6. factory, app, factory, 0x10000, 768K,
7. ota_0, app, ota_0, 0xd0000, 768K,
8. ota_1, app, ota_1, 0x190000, 768K,
9. storage, data, fat, 0x250000, 1M,
```

这里，我们可以看到一些有趣的条目：

- 有三个应用程序分区。两个标记为 `ota` ，用于写入空中固件更新。另一个标记为 `factory` ，我们从引导期间的串行输出中知道，这是当前正在使用的应用程序分区。
- 该 `storage` 分区具有 FAT 类型，这很可能是我们在串行输出中看到的 FAT 文件系统。
- `nvs` 是一个键值存储分区，这里可能有一些有用的数据。

📌更新

其他读者提到，如果设备启用了闪存加密（在这种情况下并没有），这个闪存转储可能已经受到保护。

# 设备存储

我最初很好奇看看 `nvs` 键值存储分区中有什么数据。

这些数据的最新状态已提取到 `part.0.nvs.cvs` ，我能看到的唯一有趣的数据是我的 WiFi SSID 和密码。但我还发现了 `part.0.nvs.txt` 中值的完整历史更改日志，揭示了一些先前使用过的 WiFi 凭据；什么！？有人在我之前使用过这个东西吗？😆

随后，是时候查看 FAT `storage` 分区的内容了。我发现 OSFMount 是一个很棒的 Windows 应用程序；它将文件系统映像挂载为虚拟磁盘，并允许对其进行写入！

这揭示了一些有趣的文件，我们之前从串行输出中看到的

```
1. dev_info
2. dev_key.key
3. serial
4. server_config
5. SmartDevice-root-ca.crt
6. SmartDevice-signer-ca.crt
7. wifi_config
```

我检查了这些文件的内容，发现：

- `dev_info` - 一个带有标签 `firmware` 的 UUID，可能是已安装的版本
- `dev_key.key` - 256 位私钥（prime256v1），其公钥已打印到标记为 Devicekey 的串行输出！
- `serial` - 序列号
- `server_config` - 我们之前找到的地址和端口号
- `SmartDevice-root-ca.crt` - 具有 256 位公钥（prime256v1）的 CA 证书
- `SmartDevice-signer-ca.crt` - 具有 256 位公钥（prime256v1）和根证书作为其 CA（证书颁发机构）的 CA 证书
- `wifi_config` - 我的 WiFi SSID 和密码
`dev_key.key` 文件以 `-----BEGINEC PRIVATE KEY-----` 开头，这是一个椭圆曲线私钥；我使用 openssl 进行验证：

```
1. openssl ec -in dev_key.key -text -noout
```

两个 `.crt` 文件以 `-----BEGINCERTIFICATE-----` 开头，我也使用 openssl 进行了验证：

```
1. openssl x509 -in ./SmartDevice-root-ca.crt -text -noout
2. openssl x509 -in ./SmartDevice-signer-ca.crt -text -noout
```
将证书和设备密钥存储在设备上强烈表明它们用于加密 UDP 网络数据包。

# 初始静态分析

现在我们已经看了存储，是时候看看运行在设备上的应用程序了。

我们知道它正在运行 `factory` 分区，所以我在 Ghidra CodeBrowser 中打开了 `part.3.factory` 文件。Ghidra 是来自 NSA 的免费开源逆向工程工具套件；它是付费 IDA Pro 的替代品。

我们正在打开的这个文件是直接来自闪存的分区镜像；它由多个数据段组成，每个数据段都映射到 ESP32 上的不同虚拟内存区域。例如，在分区镜像中偏移 `0x17CC4` 处的数据实际上映射到设备虚拟内存中的 `0x40080ce0` 处，因此，尽管该文件包含了所有应用逻辑和数据，但 Ghidra 目前无法理解如何解析任何绝对内存引用。稍后会有更多内容！

ESP32 微处理器使用 Xtensa 指令集，Ghidra 最近已经增加了对此的支持！在加载图像时，您可以选择语言 `TensilicaXtensa32-bit little-endian` 。我们可以运行自动分析；尽管目前它不会给我们很好的结果，但我们仍然可以查看它能够找到的任何定义的字符串。

# 弦理论
编译应用程序中的文本字符串是在逆向工程时快速定位和理解逻辑的方法；它们可以揭示应用程序的许多信息。

因为这个编译文件只包含处理器的字节码指令，没有函数名称、数据类型或参数。最初看起来像一团庞大的无意义，但一旦你看到像 `Failedto read wifi config file` 这样的字符串引用，你就可以开始拼凑出逻辑在做什么。逆向工程编译应用程序可能很困难，但肯定是一个有益的挑战。

因此，我在 Ghidra 的 `DefinedStrings` 窗口中查看了一下，看看我能找到什么，注意到了所有在串行输出中看到的字符串，比如：

```
1. 000031c4 "Serial Number: %s\r\n"
2. 000031fc "Device key ready\r"
3. 00003228 "Base64 Public Key: %s\r\n"
```

预期地，地址是分区图像中字符串的位置。理想情况下，这应该是在 ESP32 上运行时虚拟内存中的地址；这样，我们就可以看到引用该字符串的任何字节码。我们很快就会解决这个问题！

在这些字符串附近还有一些其他有趣的字符串：

```
1. 000030d0 "Message CRC error\r"
2. 00003150 "Seed Error: %d\r\n"
3. 000031c4 "Serial Number: %s\r\n"
4. 000031fc "Device key ready\r"
5. 00003228 "Base64 Public Key: %s\r\n"
6. 00003240 "Error reading root cert!!!!\r"
7. 00003260 "Error reading signer cert!!!!\r"
8. 00003280 "PRNG fail\r"
9. 0000328c "ECDH setup failed\r"
10. 000032a0 "mbedtls_ecdh_gen_public failed\r"
11. 000032c0 "mbedtls_mpi_read_binary failed\r"
12. 000032e0 "Error copying server key to ECDH\r"
13. 00003304 "mbedtls_ecdh_compute_shared failed: 0x%4.4X\r\n"
14. 00003334 "Error accessing shared secret\r"
15. 00003354 "####### MBED HKDF failed: -0x%4.4X ########\r\n"
16. 00003384 "Sign failed\n ! mbedtls_ecp_group_copy returned 0x%4.4X\n"
17. 000033c0 "Sign failed\n ! mbedtls_ecp_copy returned 0x%4.4X\n"
18. 000033f4 "Sign failed: 0x%4.4X\r\n"
19. 3f403d30 "Write ECC conn packet\r\n"
```

我们可以从这些字符串中提取出很多有用的信息。即使不阅读汇编代码，我们也可以开始推断它正在对数据做什么。

这是我注意到的：
- CRC 错误代码：这是一种校验和算法，可能是数据包的一部分。
- mbedtls 是一个实现加密原语、X509 证书操作以及 SSL/TLS 和 DTLS 协议的开源库。
- ECDH 和 HKDF 原始函数直接从 mbedtls 中使用。我们已经知道它没有使用 DTLS 协议，所以我们可以假设它们用于实现自定义协议。
- 我们也可以假设附近提到的文件也是相关的
- 序列号
- 设备密钥
- 根证书
- 签名者证书
- 客户端发送了一个“ECC 连接数据包”; 这是 ECDH 密钥交换过程的一部分; 我们稍后也会讨论到这个！

# Ghidra 设置
好的，现在是时候配置 Ghidra 以更好地分析这个 ESP32 应用程序了。

首先，esp32knife 支持将应用程序的二进制分区映像重新格式化为 ELF 格式，这样 Ghidra 可以更好地理解。我不得不进行了一些小的调整，以便支持 `RTC_DATA` 段，我已经将其推送到了我的 GitHub 分支上：feat: add support for RTC_DATA image segment.

我们可以导入更有用的 `part.3.factory.elf` 而不是 `part.3.factory` 二进制分区映像。

但是这次导入时，我们希望在运行自动分析之前做一些事情，所以现在选择不这样做。

接下来，我们可以使用 SVD-Loader-Ghidra 脚本从官方的 esp32.svd 文件中导入外设结构和内存映射。

我们还可以使用内置的 `SymbolImportScript` 脚本来加载所有 ROM 函数的标签。我已经发布了一个包含 ESP32 所有 ROM 函数标签的文件，可以在这里找到：ESP32ROMLABELS.txt。这将帮助我们识别常见的 ROM 函数，比如 `printf` 。

最后，我们从菜单栏运行自动分析 `Analysis>AutoAnalyze` 。

让我们看看这对我们之前找到的字符串有什么影响：

```
1. 3f4031c4 "Serial Number: %s\r\n"
2. 3f4031fc "Device key ready\r"
3. 3f403228 "Base64 Public Key: %s\r\n"
```
我们现在可以看到相同的字符串被正确映射到它们的虚拟内存地址，这意味着分析将检测到引用它们的任何指针或指令！

info 注意

ESP32 有多个版本，例如 `ESP32c2` 和 `ESP32s2` 。我链接的 ROM 标签和 `.svd` 文件是默认 `ESP32.` 的，如果您有不同版本，您需要导入特定 `.svd` 并按照我的 gist 中的 README 创建特定的 ROM 标签。

# 固件修改
到目前为止，我把 PCB 笨拙地放置在那里，以保持风扇和控制面板连接。因此，我想看看如果它们被拔掉后是否仍然能正常工作。不幸的是，它没有；串行记录如下：

```
1. I2C read reg fail1
2. No Cap device found!
3. REGuru Meditation Error: Core 0
panic
'ed (IllegalInstruction). Exception was
unhandled.
4. Memory dump at 0x400da020
```
现在我们已经很好地配置了 Ghidra，我查看了日志中提到的地址；它是在一个 `NoCapdevice found!` 字符串的引用旁边的汇编代码，并且在函数的开头，它记录了 `"CapSense Init\r"` 。这一定是用于使用电容感应输入的控制面板！

我在 Ghidra 中将此功能命名为 `InitCapSense` ：

```
1. void InitCapSense()
2. { 
3. FUN_401483e0("CapSense Init\r");
4. // ... CapSense logic
5. }
```

我随后跟踪了这个函数的引用，回溯到另一个看起来是作为任务/服务启动的函数；我将这个函数重命名为 `StartCapSenseService:`

```
1. void StartCapSenseService()
2. {
3. _DAT_3ffb2e2c = FUN_40088410(1, 0, 3);
4. FUN_4008905c(InitCapSense, &DAT_3f40243c, 0x800, 0, 10, 0, 0x7fffffff);
5. return;
6. }
```

再次，我跟踪了函数引用，并找到调用 `StartCapSenseService` 的函数。使用 Ghidra 的 Patch Instruction 功能，我用 `nop` （无操作）指令替换了 `call` 指令，以移除函数调用。

```
1. // Original
2. 400d9a28 25 63 af call8 FUN_4008905c
3. 400d9a2b 65 31 00 call8 StartCapSenseService
4. 400d9a2e e5 37 00 call8 FUN_400d9dac
5. 
6. // Patched
7. 400d9a28 25 63 af call8 FUN_4008905c
8. 400d9a2b f0 20 00 nop
9. 400d9a2e e5 37 00 call8 FUN_400d9dac
```

我们想要将这个更改刷写到 ESP32，所以我替换了被修改的字节，不是在这个 ELF 文件中，而是在 `part.3.factory` 二进制分区映像中，因为它是直接从闪存中获取的原始格式，所以写回会很容易。我使用十六进制编辑器查找和替换字节：

```
1. 2564af 653100 e53700` -> `2563af f02000 e53700
```
然后，我将这个修改后的图像写入到 ESP32 闪存的偏移量 `0x10000` 处，即从工厂分区的分区表偏移量开始：

```
1. esptool -p COM7 -b 115200 write_flash 0x10000 ./patched.part.3.factory
```
但是在尝试启动时，我们从串行输出中收到一个错误：

```
1. E (983) esp_image: Checksum failed. Calculated 0xc7 read 0x43
2. E (987) boot: Factory app partition is not bootable
```
好的，所以有一个校验和。幸运的是，esptool 内部的代码知道如何计算这个校验和，所以我写了一个快速的脚本来修复应用程序分区镜像的校验和：功能：添加图像校验和修复脚本。

现在，我们可以使用这个工具来修复校验和并刷写修复后的镜像：

```
1. python esp32fix.py --chip=esp32 app_image ./patched.part.3.factory
2. 
3. esptool -p COM7 -b 115200 write_flash 0x10000 ./patched.part.3.factory.fixed
```
我再次尝试启动设备而不使用控制面板；现在一切都正常工作！我们刚刚成功修改了智能设备的固件！

# 数据包头
让我们重新专注于数据包。我们知道数据包不遵循一个众所周知的协议，这意味着我们必须自己弄清楚结构。

我捕获了设备多次启动时的数据包，并将它们相互比较。我注意到前十三个字节与其他数据包相似，而数据包的其余部分似乎是加密的。

这是在启动之间从服务器接收的第一个数据包；您可以看到数据匹配直到偏移 `0x0D` ：

```
1. Hex View 00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F
2. 
3. 00000000 55 00 2F 82 01 23 45 67 89 AB CD EF FF 37 34 9A U./..#Eg.....74.
4. 00000010 7E E6 59 7C 5D 0D AF 71 A0 5F FA 88 13 B0 BE 8D ~.Y|]..q._......
5. 00000020 ED A0 AB FA 47 ED 99 9A 06 B9 80 96 95 C0 96 ....G..........
6. 
7. Hex View 00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F
8. 
9. 00000000 55 00 2F 82 01 23 45 67 89 AB CD EF FF 81 85 3F U./..#Eg.......?
10. 00000010 8A 10 F5 02 A5 F0 BD 28 73 C2 8C 05 71 6E E4 A3 .......(s...qn..
11. 00000020 A6 36 FD 5C E0 D5 AC 3E 1A D5 C5 88 99 86 28 .6.\...>......(
```
找出前几个值并不太困难，然后我注意到剩下的九个字节与设备串行输出的序列号匹配，这样我们就得到了数据包头格式：

```
1. 55 // magic byte to identity the protocol
2. 00 31 // length of the packet in bytes
3. 02 // message identifier
4. 01 23 45 67 89 AB CD EF FF // device serial
```

- 一个魔术字节通常用于唯一标识特定格式中的一段数据。
- 一个与大小相关的字节和消息 ID 在这样的数据包中是非常常见的。

首次发送和接收的数据包的格式与随后的数据包略有不同；客户端数据包的头部后始终有 `0001` 字节，并且它是唯一一个带有消息 ID `0x02` 的数据包。

与其他数据包相比，我注意到消息 ID 中存在一种模式：

- `0x02` - 智能设备发送的第一个数据包
- `0x82` - 从云服务器接收到的第一个数据包
- `0x01` - 所有其他从智能设备发送的数据包
- `0x81` - 从云服务器接收的所有其他数据包

您可以看到此值中的高位表示它是客户端请求（ `0x00` ）还是服务器响应（ `0x80` ）。而低位在第一次交换（ `0x02` ）和所有其他数据包（ `0x01` ）之间是不同的。

# 数据包校验和

我们早些时候在应用程序中注意到一个字符串，其中说 `"Message CRC error\r"` ，这暗示数据包中有一个 CRC 校验和。知道数据中是否有校验和将有助于避免干扰任何解密尝试。

我跟随引用到这个字符串，并且一个函数引用它。

让我们来看看该函数的反编译代码：

```
1. // ...
2. iVar1 = FUN_4014b384(0, (char *)(uint)_DAT_3ffb2e40 + 0x3ffb2e42);
3. iVar2 = FUN_400ddfc0(&DAT_3ffb2e44, _DAT_3ffb2e40 - 2);
4. if (iVar1 == iVar2) {
5. if (DAT_3ffb2e47 == '\x01') {
6. FUN_400db5c4(0x3ffb2e48, _DAT_3ffb2e40 - 6);
7. }
8. else if (DAT_3ffb2e47 == '\x02') {
9. FUN_401483e0(s_Connection_message_3f4030e4);
10. }
11. pcVar3 = (char *)0x0;
12. _DAT_3ffb3644 = (char *)0x0;
13. }
14. else {
15. FUN_401483e0(s_Message_CRC_error_3f4030d0);
16. pcVar3 = (char *)0x0;
17. _DAT_3ffb3644 = (char *)0x0;
18. }
19. // ...
```
我们可以看到 `s_Message_CRC_error` 标签被用在 `else` 块中，所以 `if` 语句必须验证消息的 CRC 数据。

此逻辑比较了 2 个函数 `FUN_4014b384` 和 `FUN_400ddfc0` 的结果。如果这是验证数据包的校验和，则必须为数据包数据生成校验和，另一个必须从数据包中读取校验和值。

我们可以利用这些论点来帮助我们决定哪个是哪个，但让我们来看看两者：

```
1. uint FUN_4014b384(int param_1, byte *param_2)
2. {
3. uint uVar1;
4. 
5. if (param_1 == 0) {
6. uVar1 = (uint)*param_2 * 0x100 + (uint)param_2[1];
7. }
8. else {
9. uVar1 = (uint)*param_2 + (uint)param_2[1] * 0x100;
10. }
11. return uVar1 & 0xffff;
12. }
```
这看起来不像一个 CRC 函数。实际上看起来更像是一个可以配置字节序的读取 16 位无符号整数的函数；原因如下：

- 将一个值乘以 `0x100` （256）相当于左移 8 位（16 位值的一半），因此 `0x37` 变为 `0x3700` 。第一个 `if` 代码块中的逻辑将其添加到索引[1]处的字节；这是内存中它之后的下一个字节，因此基本上是从 `param_2` 指针读取一个大端 uint16。
- `else` 代码块的逻辑类似，但是移动第二个字节而不是第一个字节，因此读取一个小端 uint16。因此， `param_1` 参数配置了结果的字节顺序。
- 返回语句对返回值使用按位与（ `&` ）运算符与 `0xFFFF` ，这将通过将任何更高位清零来限制值为 16 位数据。

```
1. uint FUN_400ddfc0(byte *param_1, uint param_2)
2. {
3. uint uVar1;
4. uint uVar2;
5. byte *pbVar3;
6. 
7. pbVar3 = param_1 + (param_2 & 0xffff);
8. uVar1 = 0xffff;
9. for (; pbVar3 != param_1; param_1 = param_1 + 1) {
10. uVar1 = (uint)*param_1 << 8 ^ uVar1;
11. uVar2 = uVar1 << 1;
12. if ((short)uVar1 < 0) {
13. uVar2 = uVar2 ^ 0x1021;
14. }
15. uVar1 = uVar2 & 0xffff;
16. }
17. return uVar1;
18. }
```

现在，这看起来更像是一个校验和函数；里面有一个 `for` 循环，里面有一堆位运算符。

我打开其中一个捕获的数据包到 ImHex，这是一个供逆向工程师使用的十六进制编辑器。它具有一个方便的功能，可以显示当前选定数据的校验和。

由于另一个函数读取了一个 16 位的无符号整数，我选择了 CRC-16，并开始选择可能被散列的字节区域，留下了 2 个未选择的字节，我认为 16 位哈希可能在那里。

到目前为止还没有运气，但后来我注意到你可以在 ImHex 中配置 CRC-16 参数。所以，我尝试了一个简单的捷径，并设置了 ImHex 来使用在反编译函数中找到的值，计算一堆不同参数组合的 CRC-16 校验和。

成功！数据包的最后 2 个字节原来是数据包中所有其他数据的 CRC 校验和，具体来说是使用 CRC-16 算法，多项式为 `0x1021` ，初始值为 `0xFFFF` 。我用其他数据包进行了检查，它们都通过了校验。

现在我们知道每个数据包的最后 2 个字节是 CRC-16 校验和，可以将其从任何解密尝试中排除！

# 密钥交换

早些时候，我们注意到 `mbedtls` 个原语被标记为 ECDH 和 HKDF。那么，它们究竟是什么？

ECDH（椭圆曲线 Diffie-Hellman 密钥交换）是一种密钥协商协议，允许两个方（如智能设备和其云服务器），每个方都有一个椭圆曲线公私钥对，通过一个不安全的通道（UDP）建立一个共享秘密。我在《面向开发人员的实用密码学》中找到了更详细的解释：ECDH 密钥交换。

基本上，如果智能设备和服务器生成一个 EC 密钥对并交换它们的公钥，它们可以使用对方的公钥和自己的私钥来计算一个共享的秘密密钥。这个共享的秘密密钥可以用来加密和解密数据包！即使它们在不安全的网络上交换公钥，你仍然需要其中一个私钥才能计算出共享密钥。

这对于保护像这样的数据包是理想的，客户端发送的第一个数据包实际上在日志中被命名为 `ECC conn packet` ：

```
1. UDP Connect: smartdeviceep.---.com
2. smartdeviceep.---.com = 192.168.0.10
3. UDP Socket created
4. UDP RX Thread Start
5. Write ECC conn packet
```
这是很大的进步；我们知道第一个数据包交换很可能是交换 EC 公钥，以建立 ECDH 密钥协议来加密所有其他数据包。

如果我们忽略数据包头部（从开头算起的 13 个字节）和校验和（结尾的 2 个字节），我们可以看到这个潜在密钥交换的数据包内容都是 32 字节（256 位），这对于公钥来说是一个有效的大小。尽管客户端请求的开头有 `0001` ，我们可以假设这是一些不重要的数据描述符，因为它在启动之间不会改变值。

```
1. // Client request packet contents:
2. 
3. Hex View 00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F
4. 
5. 00000000 00 01 D1 C2 B3 41 70 17 75 12 F7 69 25 17 50 4A .....Ap.u..i%.PJ
6. 00000010 C5 DD D4 98 06 FE 24 6B 96 FD 56 14 4A 70 7E 51 ......$k..V.Jp~Q
7. 00000020 55 57 UW
8. 
9. // Server response packet contents:
10. 
11. Hex View 00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F
12. 
13. 00000000 07 A8 02 73 52 42 1F 1F C1 41 B4 E4 5B D9 A9 9A ...sRB...A..[...
14. 00000010 5A DD 0F 94 F1 AB 9E E8 86 C7 99 7E 08 68 52 C5 Z..........~.hR.
```
好的，那么 HKDF 是什么？那是基于 HMAC 的密钥派生。它可以用来将从 Diffie-Hellman 计算得到的共享密钥转换为适用于加密的密钥材料。哇，这很有道理；它很可能正在做这个来派生一个用于加密和解密其他数据包的密钥。

# 密码学分析
为了能够解密这些数据包，我们需要准确了解加密密钥是如何生成的。这包括任何可能的输入数据以及可配置选项。

可以肯定 ECDH 和 HKDF 函数用于数据包数据，因此专注于密钥生成过程，我总结了我们需要理解的变量：

- ECDH:
- 公钥
- 私钥
- HKDF
- 哈希方法
- 输出密钥大小
- 可选的盐
- 可选信息

智能设备及其云服务器在我们假设的密钥交换过程中交换了 256 位数据。但请记住，智能设备固件还从存储中加载以下密钥：

- 256 位设备密钥对（私钥和公钥）
- 256 位云服务器 `"root"` 公钥
- 256 位云服务器 `"signer"` 公钥

这里有很多可能性，所以我再次查看了 Ghidra 中的应用程序。通过跟踪错误字符串，我找到了生成此密钥的函数！我通过将汇编与 mbedtls 源代码进行比较，逐步标记函数和变量，成功简化并注释为以下伪代码：

```
1. int GenerateNetworkKey(uchar *outputKey, uchar *outputRandomBytes)
2. {
3. // Generate an ECDH key pair
4. char privateKey1 [12];
5. char publicKey1 [36];
6. mbedtls_ecdh_gen_public(
7. ecpGroup,
8. privateKey1,
9. publicKey1,
10. (char *)mbedtls_ctr_drbg_random,
11. drbgContext
12. );
13. 
14. // Overwrite generated private key?
15. mbedtls_mpi_read_binary(privateKey1, (uchar *)(_DAT_3ffb3948 + 0x7c), 1);
16. 
17. // Overwrite generated public key?
18. mbedtls_ecp_copy(publicKey1, (char *)(_DAT_3ffb3948 + 0x88));
19. 
20. // Load another public key?
21. char publicKey2 [36];
22. mbedtls_ecp_copy(publicKey2, (char *)(_DAT_3ffb38cc + 0x88));
23. 
24. // Compute shared secret key using privateKey1 and publicKey 2
25. char computedSharedSecret [100];
26. uchar binarySharedSecret [35];
27. mbedtls_ecdh_compute_shared(
28. ecpGroup,
29. computedSharedSecret,
30. publicKey2,
31. privateKey1,
32. (char *)mbedtls_ctr_drbg_random,
33. drbgContext
34. );
35. mbedtls_mpi_write_binary(computedSharedSecret, binarySharedSecret, 0x20);
36. 
37. // Generate random bytes
38. mbedtls_ctr_drbg_random(globalDrbgContext, outputRandomBytes, 0x20);
39. 
40. // Derive key
41. mbedtls_md_info_t *md = mbedtls_md_info_from_type(MBEDTLS_MD_SHA256);
42. uchar* deviceSerialNumber = (uchar *)GetDeviceSerialNumber();
43. mbedtls_hkdf(
44. md,
45. binarySharedSecret, // salt
46. 0x20,
47. outputRandomBytes, // input
48. 0x20,
49. deviceSerialNumber, // info
50. 9,
51. outputKey,
52. 0x10
53. );
54. }
```
能够解释 Ghidra 中的汇编甚至反编译代码肯定是一种独特的技能；我想强调这需要一段时间来弄清楚，中间有很多休息时间！

这个函数做了一些不寻常的事情；以下是我们可以从中学到的东西：

- 生成的 ECDH 密钥对被丢弃，并被从内存中其他地方加载的密钥替换，这很奇怪。因为 ECDH 密钥对生成函数在应用程序的其他地方没有被使用，很可能这些密钥是我们之前在固件存储中看到的文件。
- 用于 HKDF 的算法是 `SHA-256` 。
- 计算得到的共享密钥被用作 HKDF `salt` 。
- 随机字节被生成为 HKDF `input` 。
- 设备序列号用作 HKDF `info` 。
- HKDF 输出密钥大小为 `0x10` （16 字节/128 位）。

我们现在对智能设备如何生成潜在的加密密钥有了更好的理解。

请记住，他们的云服务器也必须生成这个密钥，这意味着它需要具有与 HKDF 相同的所有输入变量。

了解这一点，我们可以回顾一下 HKDF 函数的三个动态输入，并了解服务器也将拥有它们：

- `salt` - 共享密钥：服务器必须能够访问用于 ECDH 共享密钥计算的相同私钥和公钥，或者使用我们的公钥到我们的私钥，以及我们的私钥到我们的公钥。
- `input` - 随机字节：服务器必须能够访问智能设备上生成的这些随机字节；我们要么将这些字节发送到服务器，要么从技术上讲，服务器可以重新创建使用的伪随机数生成方法。然而，生成的字节大小为 `0x20` （32 字节/256 位），恰好与密钥交换数据包中发送的数据大小相匹配，因此我们很可能会将其发送到那里！
- `info` - 设备序列号：我们已经知道设备序列号是数据包头的一部分，因此服务器很容易访问到这个值。

好奇地想知道应用程序对这些随机生成的字节做了什么，我检查了调用函数对它们做了什么：

```
1. stack[0] = 0x00;
2. stack[1] = 0x01;
3. GenerateNetworkKey(&KeyOutput, stack[2]);
4. log(2, 2, "Write ECC conn packet\r\n");
5. SendPacket((int)param_1, 2, stack[0], 0x22);
```
我们可以看到来自 `GenerateNetworkKey` 的随机字节被写入堆栈，更好的是， `0001` 字节被写入堆栈就在它之前，然后所有 `0x22` 字节都被发送到数据包中。这正好符合我们在密钥交换数据包中看到的格式！

# 记录关键数据

通过静态分析已经取得了很大进展，我们需要计算解密密钥的最终值是共享秘钥。

在逆向工程的这一点上，我还没有像这篇博客文章中展示的那样干净地反转功能，并且想尝试直接从设备动态获取密钥。

通过 JTAG 调试在这里是明智的选择。然而，我没有注意到 PCB 上这些引脚的断点，我也想避免直接焊接到 ESP32 引脚，所以我想挑战自己来修改固件，通过串行打印输出！

CapSense 服务仍然被禁用，所以我想写一个函数来打印出共享密钥，并在计算完成后立即调用它！

所以，用伪代码规划，我想要将我的函数调用添加到 `GenerateNetworkKey` 函数中。就在它生成密钥之后。

```
1. int GenerateNetworkKey(uchar *outputKey, uchar *outputRandomBytes)
2. {
3. // ... 
4. 
5. // Add my function call:
6. print_key(binarySharedSecret);
7. }
8. 
9. // Custom function saved over unused logic:
10. void print_key(char *key)
11. {
12. for (int i = 0; i < 32; i++) {
13. log("%2.2x", key[i]);
14. }
15. }
```

在参考 Xtensa 指令集架构手册时，我组装了一些类似这样的汇编代码：

```
1. // Original
2. 400dbf2d 25 4b 6c call8 GetDeviceSerialNumber
3. 
4. // Patched
5. 400dbf2d e5 ff fd call8 print_key
6. 
7. // print_key:
8. 400d9f2c 36 41 00 entry a1, 0x20
9. 400d9f3b 42 c2 20 addi a4, a2, 0x20
10. 400d9f3e 52 a0 02 movi a5, 0x2
11. 400d9f41 61 ea db l32r a6, PTR_s_%2.2x // "%2.2x"
12. 400d9f44 d2 02 00 l8ui a13, a2, 0x0
13. 400d9f47 60 c6 20 mov a12, a6
14. 400d9f4a 50 b5 20 mov a11, a5
15. 400d9f4d 50 a5 20 mov a10, a5
16. 400d9f50 22 c2 01 addi a2, a2, 0x1
17. 400d9f53 25 ed 05 call8 log
18. 400d9f56 27 94 ea bne a4, a2, LAB_400d9f44
19. 400d9f59 22 a0 00 movi a2, 0x0
20. 400d9f5c 90 00 00 retw
```

我们在 `GetDeviceSerialNumber` 函数调用之后打补丁，因为这是在生成共享密钥之后直接进行的，密钥的指针仍然在寄存器 `a2` 中。

我刷了修改过的固件，启动了设备，并检查了串行输出：

```
1. Write ECC conn packet
2. e883eaed93c63d2c09cddebce6bb15a7f4cb5cedf00c1d882b8b292796254c9c
```

成功！我们已经打印出共享的密钥！

我多次重新启动设备，以查看密钥是否更改，但它仍然保持不变。它很可能是使用固件存储中的密钥计算的，但现在我们有了计算出的静态值，就不需要再反向计算过程了。

# 数据包解密

好的，我们现在了解了推导解密密钥的方法，并且已经获得了所有输入值；它看起来像这样：

```
1. const hkdfOutputKey = hkdf({
2. method: 'SHA-256',
3. salt: Buffer.from(
4. 'e883eaed93c63d2c09cddebce6bb15a7f4cb5cedf00c1d882b8b292796254c9c', 'hex'
5. ),
6. input: randomBytesFromDeviceKeyExchangePacket,
7. info: deviceSerialNumber,
8. outputKeySize: 0x10,
9. });
```

为了安全起见，我又写了一个固件补丁来打印 HKDF 调用的关键输出，并尝试从捕获的数据包中重新创建密钥。它有效！这证实我们已经正确地反向工程了密钥生成函数，并能够在我们自己的应用程序中复制密钥生成逻辑。

但现在我们需要找出使用的加密算法。我回顾了格式化数据包的函数，并找到了调用加密函数的地方：

```
1. char randomBytes [16];
2. 
3. // Write device serial
4. memcpy(0x3ffb3ce0, deviceSerialNumber, 9);
5. 
6. // Generate and write random bytes
7. mbedtls_ctr_drbg_random(globalDrbgContext, randomBytes, 0x10)
8. memcpy(0x3ffb3ce9, randomBytes, 0x10);
9. 
10. // Write packet data
11. memcpy(0x3ffb3cf9, data, dataSize);
12. 
13. // Pad with random bytes
14. mbedtls_ctr_drbg_random(globalDrbgContext dataSize + 0x3ffb3cf9, paddingSize);
15. 
16. // Run encryption on the data + padding
17. FUN_400e2368(0x3ffb3cf9, dataSize + paddingSize, &HKDFOutputKey, randomBytes);
```

我注意到在设备序列号被复制到数据包之后，会生成 16 个随机字节并直接复制到其后。这些字节也会提供给加密函数。因此，我们知道它们是加密算法的输入变量。

我们知道密钥是 128 位，另外还有 128 位额外的随机数据。

我查看了加密函数，由于一堆位操作的循环，这与加密有关，我注意到了一个静态数据块的引用。

这些数据始于 `63 7C 77 7B F2 6B 6F C5` ，在 mbedtls 源代码中搜索发现它是 AES 正向 S-盒！

我决定直接尝试对捕获的数据包进行 AES 解密，并成功解密了一个数据包！！🎉

```
1. Hex View 00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F
2. 
3. 00000000 00 00 65 00 53 00 82 A4 74 79 70 65 AF 6D 69 72 ..e.S...type.mir
4. 00000010 72 6F 72 5F 64 61 74 61 5F 67 65 74 A4 64 61 74 ror_data_get.dat
5. 00000020 61 85 A9 74 69 6D 65 73 74 61 6D 70 CF 00 00 01 a..timestamp....
6. 00000030 8D 18 05 31 FB A9 46 41 4E 5F 53 50 45 45 44 00 ...1..FAN_SPEED.
7. 00000040 A5 42 4F 4F 53 54 C2 A7 46 49 4C 54 45 52 31 00 .BOOST..FILTER1.
8. 00000050 A7 46 49 4C 54 45 52 32 00 07 07 07 07 07 07 07 .FILTER2........
```

算法是 `AES-128-CBC` ，额外的随机数据被用作 `IV` （初始化向量）。

# 中间人攻击

我们现在可以创建一种不需要任何固件修补的中间人攻击（MITM）。这是因为设备的私钥现在已知，密钥派生逻辑已被逆向工程，任何所需的动态数据都暴露在不安全的网络上。

如果正确实现了 ECDH，智能设备将拥有一个不会暴露的独特私钥，我们最简单的攻击途径将是生成我们自己的服务器密钥对并进行任何固件修改，以便设备接受我们的自定义公钥。

但由于他们自定义协议的设计，我们可以编写一个中间人脚本，可以拦截、解密和可能修改网络通信，而无需对智能设备进行任何修改。所以，这就是我们要做的事情！

目前的主要目标是尽可能解密和记录尽可能多的数据；然后，我们可以参考这些数据编写一个本地服务器端点，完全取代他们的云服务器。

我匆忙地拼凑了一个快速的 Node.js 脚本来完成这个任务：

```
1. const dns = require("dns");
2. const udp = require("dgram");
3. const crypto = require("crypto");
4. const hkdf = require("futoin-hkdf");
5. const fs = require("fs");
6. 
7. // Key Gen
8. 
9. const sharedSecretKey = Buffer.from(
10. "e883eaed93c63d2c09cddebce6bb15a7f4cb5cedf00c1d882b8b292796254c9c",
11. "hex"
12. );
13. 
14. function calculateAesKey(deviceSerialNumber, inputData) {
15. return hkdf(inputData, 16, {
16. salt: sharedSecretKey,
17. info: deviceSerialNumber,
18. hash: "SHA-256",
19. });
20. }
21. 
22. // Packet Parsing
23. 
24. let latestAesKey = null;
25. let packetCounter = 0;
26. const proxyLogDir = path.join(__dirname, "decrypted-packets");
27. 
28. function decryptPacket(data, deviceSerial) {
29. const IV = data.subarray(0xd, 0x1d);
30. const encryptedBuffer = data.subarray(0x1d, data.length - 2);
31. const decipher = crypto.createDecipheriv(
32. "aes-128-cbc",
33. latestAesKey,
34. parsed.IV
35. );
36. decipher.setAutoPadding(false);
37. return Buffer.concat([decipher.update(encryptedBuffer), decipher.final()]);
38. }
39. 
40. function logPacket(data) {
41. const messageId = data.readUInt8(3);
42. const deviceSerial = data.subarray(4, 4 + 9);
43. 
44. if (messageId === 2) {
45. // Key Exchange
46. const randomlyGeneratedBytes = data.subarray(0xf, data.length - 2);
47. latestAesKey = calculateAesKey(deviceSerial, randomlyGeneratedBytes);
48. } else {
49. // Encrypted Packets
50. fs.writeFileSync(
51. path.join(proxyLogDir, `packet-${id}.bin`),
52. decryptPacket(data)
53. );
54. }
55. }
56. 
57. // Networking
58. 
59. dns.setServers(["1.1.1.1", "[2606:4700:4700::1111]"]);
60. 
61. const PORT = 41014;
62. const cloudIp = dns.resolve4("smartdeviceep.---.com")[0];
63. const cloud = udp.createSocket("udp4");
64. let latestClientIp = null;
65. let latestClientPort = null;
66. 
67. cloud.on("message", function (data, info) {
68. logPacket(data);
69. local.send(data, latestClientIp, latestClientPort);
70. });
71. 
72. const local = udp.createSocket("udp4");
73. local.bind(PORT);
74. 
75. local.on("message", function (data, info) {
76. logPacket(data);
77. latestClientIp = info.address;
78. latestClientPort = info.port;
79. cloud.send(data, PORT, cloudIp);
80. });
```

在这里，我们结合所有的研究来实施中间人攻击。

就像我们第一次捕获数据包时一样，我们配置 Node.js 使用 Cloudflare 的 DNS 解析器来绕过我们的本地 DNS 服务器。

我们在本地创建一个 UDP 套接字来接收来自智能设备的数据包，并且还创建一个套接字与云服务器进行通信。

- 我们从智能设备接收到的任何内容，我们都会记录并发送到云服务器
- 我们从云服务器接收到的任何内容，我们都会记录并发送到智能设备

我们将 `messageId` 为 2 的数据包视为密钥交换数据包，智能设备向服务器发送随机字节，然后我们计算用于解密未来数据包的 AES 密钥。

在捕获过程中，我使用他们的移动应用远程控制智能设备，这样我们就可以参考日志并自行复制逻辑。

# 数据交换格式
# 

我们现在有解密的数据包数据，但数据仍然以序列化的二进制格式存在：

```
1. Hex View 00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F
2. 
3. 00000000 01 00 64 00 29 00 82 A4 74 79 70 65 A7 63 6F 6E ..d.)...type.con
4. 00000010 6E 65 63 74 A8 66 69 72 6D 77 61 72 65 C4 10 00 nect.firmware...
5. 00000020 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 83 ................
```

我的思绪深陷于逆向工程的世界，我设法逆向解析所有数据包的结构，并拼凑了一些 JavaScript 代码，将数据转换为 JSON 格式。

标题非常简单，再次只是一些 ID 和长度，但是采用小端序：

- `01 00` 数据包 ID
- `64 00` 交易 ID
- `29 00` 序列化数据长度

经过一些调整，我弄清了序列化格式：

- `82` 地图
- `A4` 长度为 4 的字符串
- `A7` 长度为 7 的字符串

这是有趣的反向操作，因为打字更多地以比特描述，但对于这些简单情况，从字节中清晰可读。

回顾这一点，我不确定为什么我没有寻找与这个序列化二进制数据格式匹配的现有解决方案；我当时期望一切都是定制解决方案。但现在搜索一下，这只是 MessagePack，所以我想我只是反向工程并编写了一个部分的 msgpack 实现 😆

切换到一种流行的实现方式，我们可以看到数据很容易解压缩为 JSON：

```
1. const { unpack, pack } = require('msgpackr');
2. 
3. const packedData = Buffer.from(
4. '82A474797065A7636F6E6E656374A86669726D77617265C41000000000000000000000000000000000',
5. 'hex'
6. );
7. 
8. const unpackedData = unpack(packedData);
9. 
10. // unpackedData:
11. {
12. type: 'connect',
13. firmware: <Buffer 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00>
14. }
```

# 网络日志分析

为了为智能设备编写定制本地服务器做准备，让我们看一下我们捕获的解包网络日志：

🔑 密钥交换数据包:

智能设备向服务器发送随机字节，用于在 HKDF 中使用。

```
1. // Smart Device Request
2. D1C2B34170177512F7692517504AC5DDD49806FE246B96FD56144A707E515557
3. 
4. // Server Response
5. 00000000000000000000000000000000
```

获取设备状态:

智能设备在启动时从服务器获取其初始状态。

```
1. // Smart Device Request
2. { type: 'mirror_data_get' }
3. 
4. // Server Response
5. {
6. type: 'mirror_data_get',
7. data: {
8. timestamp: 1705505010171n,
9. FAN_SPEED: 0,
10. BOOST: false,
11. FILTER1: 0,
12. FILTER2: 0
13. }
14. }
```

🔗 在连接时:

当智能设备连接到服务器时，它会发送其当前的固件 UUID。服务器会回复可能用于固件或配置更新的 UUID，可以被下载。

```
1. // Smart Device Request
2. {
3. type: 'connect',
4. firmware: <Buffer 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00>
5. }
6. 
7. // Server Response
8. {
9. type: 'connect',
10. server_time: 1706098993961n,
11. firmware: <Buffer ab cd ef ab cd ef ab cd ef ab cd ef ab cd ef ab>,
12. config: <Buffer 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00>,
13. calibration: <Buffer 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00>,
14. conditioning: <Buffer 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00>,
15. server_address: 'smartdeviceep.---.com',
16. server_port: 41014,
17. rtc_sync: { ss: 13, mm: 23, hh: 12, DD: 24, MM: 1, YYYY: 2024, D: 3 }
18. }
```

⤵️ 服务器更新智能设备状态:

当服务器想要更新智能设备的状态时，它会发送这样的数据包。

```
1. // Server Request
2. {
3. type: 'mirror_data',
4. data: {
5. FAN_SPEED: 1,
6. BOOST: false
7. }
8. }
```

⤴️ 智能设备更新服务器状态:

智能设备在每次状态更改时向服务器发送其最新状态。

```
1. // Smart Device Request
2. {
3. type: 'mirror_data',
4. data: {
5. timestamp: 1706105072142n,
6. FAN_SPEED: 1,
7. BOOST: false,
8. FILTER1: 0,
9. FILTER2: 0
10. }
11. }
12. 
13. // Server Response
14. { type: 'mirror_data' }
```

🛜 保持连接：

智能设备经常向服务器发送保持活动的数据包，以便服务器可以潜在地利用开放的连接发送状态更新。

```
1. // Smart Device Request
2. {
3. type: 'keep_alive',
4. stats: {
5. rssi: -127n,
6. rtt: 684,
7. pkt_drop: 1,
8. con_count: 1,
9. boot_str: '',
10. uptime: 100080
11. }
12. }
13. 
14. // Server Response
15. { type: 'keep_alive' }
```

# MQTT 桥接

我们需要一种方法将 Home Assistant 连接到我们的自定义服务器，该服务器处理智能设备的网络连接。MQTT 非常适合这个用途；它是一种专为物联网消息设计的协议，并且可以在 Home Assistant 中轻松配置。为此，我为 Home Assistant 设置了 Mosquitto 插件，这是一个开源的 MQTT 代理，将所有内容连接在一起。

连接链将如下所示：

```HomeAssistant<--> MQTTBroker <--> CustomServer <--> SmartDevice``` 。

伪代码中的自定义服务器逻辑大致如下：

```
1. function HandleSmartDeviceRequest(req) {
2. switch (req.type) {
3. case 'mirror_data_get': {
4. // Device wants state, send latest MQTT state or default fallback
5. device.send({ fan_speed: mqtt.get('fan_speed') || 0 });
6. return;
7. }
8. case 'mirror_data': {
9. // Device state has changed, publish and retain in MQTT broker
10. mqtt.publish('fan_speed', req.fan_speed, { retain: true });
11. return;
12. }
13. }
14. }
15. 
16. function HandleMQTTMessage(topic, msg) {
17. switch (topic) {
18. case 'set_fan_speed': {
19. // MQTT wants to change state, forward to device
20. device.send({ fan_speed: msg.fan_speed });
21. return;
22. }
23. }
24. }
```

这种逻辑似乎相当简洁，但经过精心设计。最新状态保留在 MQTT 代理中。然而，状态更新的真相始终是设备，这意味着除非设备通过自定义服务器更新它，否则状态永远不会在 MQTT 代理中更新。这涵盖了一些边缘情况：

- 如果状态更新失败，我们不应该显示状态已更新。
- 如果智能设备通过其物理控制面板进行更新，则状态更新应通过 MQTT 代理反映。

我们在这里支持的三个主要案例是：

- 当智能设备启动并最初连接到自定义服务器时，它会请求最新状态；我们可以尝试从 MQTT 代理的保留值中获取这个状态，或者退回到默认状态。
- 当 Home Assistant 想要更新状态时，它会向 MQTT 代理发送命令。我们可以从自定义服务器订阅此命令主题，并将请求转发给智能设备。
- 当智能设备的状态因任何原因而更改时，它会发送 `mirror_data` 数据包来更新服务器状态；我们将此值发送到 MQTT 代理以更新状态，并告诉它保留数据作为最新值。

我在我的小型家庭自动化服务器上与 Mosquitto 和 Home Assistant 一起运行这个自定义服务器。然后配置了我的 Pi-hole 本地 DNS，将云服务器的域名解析到我的自定义服务器。

# 家庭助手集成

这个过程的最后一步是配置 Home Assistant 将 MQTT 主题映射到设备类型。对于我的空气净化器，最接近的集成是一个 MQTT 风扇；在我的 `configuration.yaml` 中，我添加了类似这样的内容：

```
1. mqtt:
2. fan:
3. - name: "Air Purifier"
4. unique_id: "air_purifier.main"
5. state_topic: "air_purifier/on/state"
6. command_topic: "air_purifier/on/set"
7. payload_on: "true"
8. payload_off: "false"
9. percentage_state_topic: "air_purifier/speed/state"
10. percentage_command_topic: "air_purifier/speed/set"
11. speed_range_min: 1
12. speed_range_max: 4
```

我添加了主题来控制风扇速度并打开关闭设备。

一切正常！我现在已经运行了几周，一切都很顺利，没有任何问题！我甚至设置了一点自动化，所以如果我的独立空气监测器的 PM2.5 或 VOC 水平过高，它会让空气净化器运行一段时间！

![5.png](https://www.iotsec-zone.com/api/image/v2/20240820/d3ktqbdexhxj8xhkul.png)
openinfull

# 技术回顾
出于好坏考虑，该服务背后的工程师决定不实施像 DTLS 这样的标准协议。他们创建了一种自定义解决方案，这给系统带来了一些不利因素：

- 我们不确定每个设备是否有自己独特的私钥，但无论如何，两者都有缺点：
- 如果所有设备共享相同的固件私钥，攻击者只需对单个设备进行逆向工程即可对其他设备进行中间人攻击。
- 然而，如果每个设备都有自己独特的私钥，服务器必须保留一个数据存储，将设备序列号映射到每个设备的密钥。因此，在任何数据丢失的情况下，服务器将完全失去响应任何设备通信的能力；这对企业来说是一个可怕的想法。除非有一个不安全的网络备用方案，同样令人担忧且耗时开发。
- 由于固件包含一个静态的私钥，攻击者只需要一个固件转储来获取密钥并执行中间人攻击。相反，如果在运行时生成了一个 EC 私钥，则需要写入权限才能修补服务器公钥或应用程序固件，这可以通过其他方式保护。

此外，移动应用在应用商店上有一个一星评价。这让我想知道意外的定制技术实现和异常糟糕的最终用户应用体验之间是否存在相关性。构建一个定制系统远不止于最初的开发；系统需要支持，bug 需要修复。

总的来说，从安全的角度来看，这并不是一个糟糕的实施方式；您仍然需要物理访问来攻击设备；每件事情都有利弊和我们视角中看不到的变量。

自定义实现增加了网络通信的模糊性。然而，通过模糊性来确保安全只是一种短期的胜利。虽然它可能会阻止对标准技术实现的一般攻击。但从更大的角度来看，这只是对攻击者来说烦人但可以通过的障碍。

最近我有几次关于工程师为什么要从零开始构建而不使用已被证明的标准进行讨论。这是一个非常有趣的话题；我会把它留到另一篇帖子中！

声明：文章中涉及的程序(方法)可能带有攻击性，仅供安全研究与技术交流之用，读者将其信息做其他用途，由用户承担全部法律及连带责任，文章作者不承担任何法律及连带责任。  
```
