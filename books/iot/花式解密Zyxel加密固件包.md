# 花式解密Zyxel加密固件包
> 0431物联卫士实验室
> 来源：https://www.iotsec-zone.com/article/237

> 附件：链接: [https://pan.baidu.com/s/1quusIdp38y7fQdF5zZhbiw](https://pan.baidu.com/s/1quusIdp38y7fQdF5zZhbiw) 提取码: hh9p

 # 前言

在网上看到了几篇有意思的文章，感觉能和自己之前在打CTF比赛时的知识相结合，遂自己动手复现一下。

 > 参考资料：
 >
 > - [https://www.freebuf.com/articles/network/255145.html](https://www.freebuf.com/articles/network/255145.html)
 > - [https://blog.csdn.net/qq_33265520/article/details/110137117](https://blog.csdn.net/qq_33265520/article/details/110137117)
 > - [https://paper.seebug.org/1448/](https://paper.seebug.org/1448/)
 > - [https://security.humanativaspa.it/zyxel-firmware-extraction-and-password-analysis/](https://security.humanativaspa.it/zyxel-firmware-extraction-and-password-analysis/)
 > - [https://ctf.plus/archives/10093](https://ctf.plus/archives/10093)

 # 复现

## 1、准备

 打开该URL：[https://portal.myzyxel.com/my/firmwares](https://portal.myzyxel.com/my/firmwares)，发现需要登录：
 ![0.png](https://www.iotsec-zone.com/images/MdImg/670a6a00987fb8541f0afcaaf5776307.png)
 使用临时邮箱注册就可以解决问题，毕竟你也不想让自己常用的邮箱变为垃圾邮件回收站吧？注册后继续访问该网站，选择如下图所示的版本号：
 ![1.png](https://www.iotsec-zone.com/images/MdImg/f9085219a57fabec7effabfabd75ed6d.png)
 点击后面的Download下载文件，下载后对zip压缩包解压`unzip -d ./firmware firmware.zip`，可以得到：
 ![2.png](https://www.iotsec-zone.com/images/MdImg/c82d3989d705d149ac41267421f4fc52.png)
> 现在我们的目标是解压出该设备的文件系统（file-system），所以当前的目标为`470AALA0C0.bin`，使用binwalk查看信息：
 ![3.png](https://www.iotsec-zone.com/images/MdImg/514df407869a0d2bb85120552be9a1eb.png)
 基本为1，这表明该固件处于加密或压缩状态；使用`binwalk 470AALA0C0.bin`查看其状态：
 ![4.png](https://www.iotsec-zone.com/images/MdImg/88a7e4df79087b00fc8b8833cfe983a8.png)
 该bin文件实际上是处于加密状态的zip压缩包，可以使用file命令验证一下：
 ![5.png](https://www.iotsec-zone.com/images/MdImg/fcb8aa14547a533354a2221a3362214c.png)
 同样需要注意的是解压出来的不仅只有bin文件，还有一些其他文件，这些文件可能对我们之后的解密`470AALA0C0.bin`带来一些帮助：
 ![6.png](https://www.iotsec-zone.com/images/MdImg/9dba07c56b5253a3116d4ef8e75e8057.png)
 分别计算这些文件的`CRC32`校验值：
 ![7.png](https://www.iotsec-zone.com/images/MdImg/f98dc75df5e211ccd6ac231ab37918d4.png)
 将`470AALA0C0.bin`拖拽到Windows中，使用7-zip打开，逐级目录翻找，最终发现`./db/etc/zyxel/ftp/conf`目录下的`system-default.conf`与前面的`470AALA0C0.conf`校验值相同：
 ![8.png](https://www.iotsec-zone.com/images/MdImg/439a2eceddb05d5f6b1b2c1f4903a63b.png)
 这说明这两个文件完全相同，所以我采用`明文攻击`的手段来解包该加密的bin文件

 ## 2、解包方式1 -- 明文攻击

 虽说明文攻击时现在CTF中一种常见的杂项题目类型，但是在这里我还是要强调几个问题，这里就以上面加密的`system-default.conf`为例吧：
 ![9.png](https://www.iotsec-zone.com/images/MdImg/bc08be6aa3f58790b79a33e5ea9c54ec.png)
 明文攻击成功需要同时满足三个条件，缺一不可：

 1. 用户拥有压缩包中已知的明文文件（**部分或全部**）。
 1. 明文文件在攻击前需要与对应的加密文件使用相同的**压缩算法**压缩成压缩包（可以简单的认为是使用相同的压缩工具），就比如说密文`system-default.conf`使用的压缩算法为`ZipCrypto Deflate:Maximum`
 1. 密文文件的压缩算法需要是`ZipCrypto Store/ZipCrypto Deflate`
 1. 密文文件的加密方式不能是AES，即不能是`AES256-Deflate / AES256-Store`，只能是`ZipCrypto Deflate / ZipCrypto Store`.

 下面我们来说一下具体的破解过程，我一开始尝试的是之前一直在使用的`ARCHPR 4.54 Professional Edition`：
 ![10.png](https://www.iotsec-zone.com/images/MdImg/5c672707aeec23b539cf910b33e9fdfa.png)![11.png](https://www.iotsec-zone.com/images/MdImg/979fa826faf491064ac05f1a4948c71d.png)
 但是该工具无法识别，就算文件扩展名改为.zip也不行，可能因为`ARCHPR`是很老的缘故了，不支持现在使用最新算法的加密包。仔细想想我们为什么一定非要用Windows下的`ARCHPR`进行破解呢？**从加密包可以知道**`**system-default.conf**`**在Unix系统上被压缩（极有可能为Linux系统上的压缩软件）**，因此我们转而使用另外一款工具`pkcrack`：<br />安装方式如下：

 ```bash
 # pkcrack的github主页：https://github.com/keyunluo/pkcrack
 $ sudo apt install cmake
 $ git clone https://github.com/keyunluo/pkcrack
 $ mkdir pkcrack/build
 $ cd pkcrack/build
 $ cmake ..
 $ make
 ```

 为了使用方便，我们为pkcrack在`/bin`目录下创建软链接：
 ![12.png](https://www.iotsec-zone.com/images/MdImg/ec52fda2439559b8f2ebca578f7d63b0.png)![13.png](https://www.iotsec-zone.com/images/MdImg/fd37066dca0f46cb0223d6d036682458.png)

 > 注：pkcrack似乎不需要我们重新编译，因为./bin目录下已经有作者编译好的可执行文件：
 > ![14.png](https://www.iotsec-zone.com/images/MdImg/deadce6ee88e5a751acc9d84bbb0497a.png)
 > 真尴尬...

 密文`system-default.conf`文件的压缩率为`15.85162545151431%`：
 ![15.png](https://www.iotsec-zone.com/images/MdImg/edc99502e93060c61075f81d63b59948.png)
 我使用的是ubuntu 18.04和该系统自带的Zip 3.0工具：
 ![16.png](https://www.iotsec-zone.com/images/MdImg/e448461d91e2f76070519573e751190b.png)
 因为我们需要保证**明文文件的压缩率**与**密文文件的压缩率相同**，所以这里需要我们逐步尝试：
 ![17.png](https://www.iotsec-zone.com/images/MdImg/920bdacc38d4e5decfdd8853699ddbf2.png)
 这些压缩包拖入到Windows，分别使用7Zip打开：
 ![18.png](https://www.iotsec-zone.com/images/MdImg/fc7f8d1a358dccf948b43a992bdd4d6d.png)
![19.png](https://www.iotsec-zone.com/images/MdImg/33cba107ec92a829518b21c952c73110.png)
![20.png](https://www.iotsec-zone.com/images/MdImg/734f41c43818547d7efabe1d10091090.png)
![21.png](https://www.iotsec-zone.com/images/MdImg/0eb0a107fc335458c2a58a8d0e4dee78.png)
![22.png](https://www.iotsec-zone.com/images/MdImg/23adc178ac810b584a536b91e99631c2.png)
![23.png](https://www.iotsec-zone.com/images/MdImg/4a2c313b911b35af8716dd93fd6fac76.png)
![24.png](https://www.iotsec-zone.com/images/MdImg/bf8047de263eb7ab8f75b9babf994dee.png)
![25.png](https://www.iotsec-zone.com/images/MdImg/8d7ad0b6430d775c7b1c9fad146a818b.png)
![26.png](https://www.iotsec-zone.com/images/MdImg/48ebd6fa6b0694660d306e4ab5e92430.png)
![27.png](https://www.iotsec-zone.com/images/MdImg/196b1f2a77b2e3b8c51cd450cbe75ed3.png)](https://www.iotsec-zone.com/images/MdImg/4c16ab5635ab722786f8a93c97896ca9.png)

 从上面这十张图片我们可以总结出如下结论：

 1. 对于Linux自带的zip压缩软件，当`zip -number`的number越大时，压缩后的文件越小，整个压缩包越小，相应的文件压缩率越小（`压缩率 == 压缩后的文件大小 / 原文件大小`）。
 1. `zip -number`的number范围为0 ~ 9，超出9相当于number从0开始。
 1. 使用相同算法的压缩包大小可能不相同。
 1. 压缩后的CRC 32值是指未进行压缩的原来文件的CRC 32值：

 ![28.png](https://www.iotsec-zone.com/images/MdImg/4ba9ed71c3afed7b469d40b42204714b.png)

 5. 如下表格所示：

 | number              | 采用的压缩算法  |
 | ------------------- | --------------- |
 | 0                   | Store           |
 | 1 ~ 2               | Deflate:Fast    |
 | 3 ~ 7               | Deflate         |
 | 8 ~ 9               | Deflate:Maximum |
 | ...（从零开始循环） | ...             |

 在加密包中压缩后的大小为11410字节，算法为`ZipCrypto Deflate:Maximum`
 ![29.png](https://www.iotsec-zone.com/images/MdImg/55c3b9a0f37a6cb2f7409fd1a83f044d.png)
 在上面十几个压缩包中寻找最接近的，就`zip -8`或`zip -9`了：
 ![30.png](https://www.iotsec-zone.com/images/MdImg/4362d0ecf3fba24d8af707134b24fd0f.png)![31.png](https://www.iotsec-zone.com/images/MdImg/7a304be7379da52f1fb10e0ff60dd8db.png)
 执行命令：`pkcrack -C ./470AALA0C0.bin -c db/etc/zyxel/ftp/conf/system-default.conf -P ./ZIPs/470AALA0C0_ZIP_?.zip -p 470AALA0C0.conf -d ./decrypted_file.zip -a`（?表示整数0 ~ 9）

 - `-C`：要破解的目标压缩包（相对系统路径或绝对系统路径）
 - `-c`：加密压缩包中密文文件的路径（这里的路径指的是文件在压缩包中的路径，不包含系统路径）
 - `-P`：压缩后的明文文件（系统路径）
 - `-p`：明文文件压缩后在其压缩包中的路径（压缩包路径）
 - `-d`：指定文件名及所在的路径（系统路径），将解密后的zip文件输出。

 最终使用`470AALA0C0_ZIP_9.zip`破解成功：

 ```bash
 cyberangel@cyberangel:~/Desktop/Zyxel/firmware$ pkcrack -C ./470AALA0C0.bin -c db/etc/zyxel/ftp/conf/system-default.conf -P ./ZIPs/470AALA0C0_ZIP_8.zip -p 470AALA0C0.conf -d ./decrypted_file.zip -a
 Warning! Plaintext is longer than Ciphertext!
 Files read. Starting stage 1 on Sun Sep 11 16:25:43 2022
 Generating 1st generation of possible key2_11410 values...done.
 Found 4194304 possible key2-values.
 Now we're trying to reduce these...
 Lowest number: 978 values at offset 6558
 Lowest number: 970 values at offset 6507
 Lowest number: 957 values at offset 6506
 Lowest number: 854 values at offset 6504
 Lowest number: 824 values at offset 6390
 Lowest number: 820 values at offset 6387
 Lowest number: 730 values at offset 6386
 Lowest number: 674 values at offset 6383
 Lowest number: 613 values at offset 6261
 Lowest number: 562 values at offset 6260
 Lowest number: 551 values at offset 6259
 Lowest number: 454 values at offset 6256
 Lowest number: 426 values at offset 6235
 Lowest number: 408 values at offset 6234
 Lowest number: 393 values at offset 6233
 Lowest number: 377 values at offset 6232
 Lowest number: 375 values at offset 6227
 Lowest number: 365 values at offset 6226
 Lowest number: 342 values at offset 6195
 Lowest number: 322 values at offset 6193
 Lowest number: 311 values at offset 6100
 Lowest number: 299 values at offset 5847
 Lowest number: 267 values at offset 5845
 Lowest number: 266 values at offset 5763
 Lowest number: 264 values at offset 5756
 Lowest number: 252 values at offset 5718
 Lowest number: 230 values at offset 5713
 Lowest number: 219 values at offset 3825
 Lowest number: 218 values at offset 3824
 Lowest number: 209 values at offset 3822
 Lowest number: 189 values at offset 3821
Lowest number: 150 values at offset 3820
Lowest number: 149 values at offset 1409
Lowest number: 147 values at offset 1407
Lowest number: 144 values at offset 1405
Lowest number: 142 values at offset 1402
Lowest number: 128 values at offset 1379
Lowest number: 112 values at offset 1372
Lowest number: 108 values at offset 1371
Lowest number: 107 values at offset 1370
Lowest number: 105 values at offset 1361
Lowest number: 104 values at offset 1359
Lowest number: 100 values at offset 1358
Done. Left with 100 possible Values. bestOffset is 1358.
Stage 1 completed. Starting stage 2 on Sun Sep 11 16:26:03 2022
Stage 2 completed. Starting zipdecrypt on Sun Sep 11 16:26:08 2022
No solutions found. You must have chosen the wrong plaintext.
Finished on Sun Sep 11 16:26:08 2022
cyberangel@cyberangel:~/Desktop/Zyxel/firmware$ pkcrack -C ./470AALA0C0.bin -c db/etc/zyxel/ftp/conf/system-default.conf -P ./ZIPs/470AALA0C0_ZIP_9.zip -p 470AALA0C0.conf -d ./decrypted_file.zip -a
Firating 1st generation of possible key2_11409 values...done.
Found 4194304 possible key2-values.
Now we're tryinles read. Starting stage 1 on Sun Sep 11 16:26:13 2022
Geneg to reduce these...
Lowest number: 947 values at offset 3263
Lowest number: 928 values at offset 3191
Lowest number: 907 values at offset 3185
Lowest number: 815 values at offset 3184
Lowest number: 758 values at offset 3148
Lowest number: 751 values at offset 3147
Lowest number: 731 values at offset 3146
Lowest number: 705 values at offset 393
Done. Left with 705 possible Values. bestOffset is 393.
Stage 1 completed. Starting stage 2 on Sun Sep 11 16:26:34 2022
Ta-daaaaa! key0=cb49ab19, key1=32740ab6, key2=7b0c34a2
Probabilistic test succeeded for 11021 bytes.
Stage 2 completed. Starting zipdecrypt on Sun Sep 11 16:26:41 2022
Decrypting compress.img (92b1ba348cd0adda5fa43084)... OK!
Decrypting db/ (78cea9728c03c6741da84e88)... OK!
Decrypting db/etc/ (c9f335561c89163372fd4e88)... OK!
Decrypting db/etc/zyxel/ (40e1595adfd29a1f7f0f4e88)... OK!
Decrypting db/etc/zyxel/ftp/ (5468e0fad57d9a06f2bf4e88)... OK!
Decrypting db/etc/zyxel/ftp/conf/ (70f87fd5a5b0ddd6d8454e88)... OK!
Decrypting db/etc/zyxel/ftp/conf/system-default.conf (cf8192a732ab2294f19f1179)... OK!
Decrypting etc_writable/ (57923423a81be0cfdb8c5188)... OK!
Decrypting etc_writable/ModemManager/ (5e775e4dfa623d0e170c4e88)... OK!
Decrypting etc_writable/ModemManager/libmm-plugin-altair-lte.so (241184bd66634b1726628d7c)... OK!
Decrypting etc_writable/ModemManager/libmm-plugin-anydata.so (0616547a4d115790c01e8e7c)... OK!
Decrypting etc_writable/ModemManager/libmm-plugin-cinterion.so (a5d7cfd3f5a99b08e62a8c7c)... OK!
Decrypting etc_writable/ModemManager/libmm-plugin-generic.so (e24b037aa0cf8aebeb948b7c)... OK!
Decrypting etc_writable/ModemManager/libmm-plugin-gobi.so (8a6ce1e45cd8a0637dca8c7c)... OK!
Decrypting etc_writable/ModemManager/libmm-plugin-hso.so (15cb5bc1917ee96f953f8e7c)... OK!
Decrypting etc_writable/ModemManager/libmm-plugin-huawei.so (69d74f4c6dd8e28ff3428f7c)... OK!
Decrypting etc_writable/ModemManager/libmm-plugin-iridium.so (d572932db85e1ebbac698c7c)... OK!
Decrypting etc_writable/ModemManager/libmm-plugin-linktop.so (178c2254091f82e93e688e7c)... OK!
Decrypting etc_writable/ModemManager/libmm-plugin-longcheer.so (3221e05bbc65450291898f7c)... OK!
Decrypting etc_writable/ModemManager/libmm-plugin-mbm.so (cae58df6bc8c8dbe7ad9907c)... OK!
Decrypting etc_writable/ModemManager/libmm-plugin-motorola.so (06ae81073a8075d3760e8c7c)... OK!
Decrypting etc_writable/ModemManager/libmm-plugin-mtk.so (77e1169e9442347a48fb907c)... OK!
Decrypting etc_writable/ModemManager/libmm-plugin-nokia-icera.so (c1e828cd266c3ed71da78c7c)... OK!
Decrypting etc_writable/ModemManager/libmm-plugin-nokia.so (ab004e793cedb584ad8f8b7c)... OK!
Decrypting etc_writable/ModemManager/libmm-plugin-novatel-lte.so (3d03bcf6f75445c38b168d7c)... OK!
Decrypting etc_writable/ModemManager/libmm-plugin-novatel.so (59d52f4f051ead0ba8cb8d7c)... OK!
Decrypting etc_writable/ModemManager/libmm-plugin-option.so (532b4c853b21f7855f498d7c)... OK!
Decrypting etc_writable/ModemManager/libmm-plugin-pantech.so (8e2f809fef4b965d49548f7c)... OK!
Decrypting etc_writable/ModemManager/libmm-plugin-samsung.so (30b4883d09f4b418764b8d7c)... OK!
Decrypting etc_writable/ModemManager/libmm-plugin-sierra.so (ecdcb588f92a1d1f060a907c)... OK!
Decrypting etc_writable/ModemManager/libmm-plugin-simtech.so (b4c19714c0c0809f3ce08e7c)... OK!
Decrypting etc_writable/ModemManager/libmm-plugin-telit.so (83f141775e4a8082df8e907c)... OK!
Decrypting etc_writable/ModemManager/libmm-plugin-via.so (5161f9e47df19610e468907c)... OK!
Decrypting etc_writable/ModemManager/libmm-plugin-wavecom.so (781fba0eba368934ad438e7c)... OK!
Decrypting etc_writable/ModemManager/libmm-plugin-x22x.so (f00939d2d6bc018b12f38f7c)... OK!
Decrypting etc_writable/ModemManager/libmm-plugin-zte.so (51f714e3453428fe4ef18f7c)... OK!
Decrypting etc_writable/budget/ (78e1d11857c18cac58e74e88)... OK!
Decrypting etc_writable/budget/budget.conf (1b083501da0bbeff96ac297e)... OK!
Decrypting etc_writable/cloud_checksum (6ce470562625b1d53df95188)... OK!
Decrypting etc_writable/dhcp6c-script (c356fcc3d3fb802a6277cc80)... OK!
Decrypting etc_writable/firmware-upgraded (e087749684b96324bda71283)... OK!
Decrypting etc_writable/tr069ta.conf (f7b6e5c0e28f0082868eba7d)... OK!
Decrypting etc_writable/usb_modeswitch/ (14177ccd4b56b89e37f44f88)... OK!
Decrypting etc_writable/usb_modeswitch/03f0:002a (f25ddaffd9db9ad6e645077c)... OK!
Decrypting etc_writable/usb_modeswitch/0408:1000 (9a88a231516fe41ec477077c)... OK!
Decrypting etc_writable/usb_modeswitch/0408:ea17 (018fc4524d67e0796980077c)... OK!
Decrypting etc_writable/usb_modeswitch/0408:ea25 (ec1976d60529d7eccca0077c)... OK!
Decrypting etc_writable/usb_modeswitch/0408:ea43 (d090bb4018dd98c40290077c)... OK!
Decrypting etc_writable/usb_modeswitch/0408:f000 (b485a2865edfc2fe8bf8077c)... OK!
Decrypting etc_writable/usb_modeswitch/0408:f001 (5d19d7fb25bf5e1de2a9077c)... OK!
Decrypting etc_writable/usb_modeswitch/0421:060c (bf83cf12ec4e71e26d64077c)... OK!
Decrypting etc_writable/usb_modeswitch/0421:0610 (b4029c6aff4a85e4bee7077c)... OK!
Decrypting etc_writable/usb_modeswitch/0421:0618 (e2b3025f666813132f5d077c)... OK!
Decrypting etc_writable/usb_modeswitch/0421:061d (222468d75190af658065077c)... OK!
Decrypting etc_writable/usb_modeswitch/0421:0622 (0108bab639f02e1daa17077c)... OK!
Decrypting etc_writable/usb_modeswitch/0421:0627 (84d47691e41a92bfbbdb077c)... OK!
Decrypting etc_writable/usb_modeswitch/0421:062c (499f3e19f25ae082b6ba077c)... OK!
Decrypting etc_writable/usb_modeswitch/0421:0632 (5288a906beb8f994c8e4077c)... OK!
Decrypting etc_writable/usb_modeswitch/0421:0637 (b72d00e0bc1ff59284c9077c)... OK!
Decrypting etc_writable/usb_modeswitch/0471:1210:uMa=Philips (3d5badfcc1c6c0cd96f4077c)... OK!
Decrypting etc_writable/usb_modeswitch/0471:1210:uMa=Wisue (b2430b15ad43a3232e4a077c)... OK!
Decrypting etc_writable/usb_modeswitch/0471:1237 (9f4b4a3808ba204fd656077c)... OK!
Decrypting etc_writable/usb_modeswitch/0482:024d (2a544749a3a3f4db8ab9077c)... OK!
Decrypting etc_writable/usb_modeswitch/04bb:bccd (3659d853b69054ba6aac077c)... OK!
Decrypting etc_writable/usb_modeswitch/04cc:2251 (d07d17965750dde81fb9077c)... OK!
Decrypting etc_writable/usb_modeswitch/04cc:225c (5c923b3474cee6b1cd1b077c)... OK!
Decrypting etc_writable/usb_modeswitch/04cc:226e (29baa3fedf0ad31ea7a8077c)... OK!
Decrypting etc_writable/usb_modeswitch/04cc:226f (f728b457816d44a1f01b077c)... OK!
Decrypting etc_writable/usb_modeswitch/04e8:680c (fd402761651ce564b170077c)... OK!
Decrypting etc_writable/usb_modeswitch/04e8:689a (865bf5d817c7d874214d077c)... OK!
Decrypting etc_writable/usb_modeswitch/04e8:f000:sMo=U209 (86f65389e39048fad1de077c)... OK!
Decrypting etc_writable/usb_modeswitch/04fc:2140 (2e327c868fffc3534b41077c)... OK!
Decrypting etc_writable/usb_modeswitch/057c:62ff (63cd63596e10709711fc077c)... OK!
Decrypting etc_writable/usb_modeswitch/057c:84ff (de292eba342ce5f7ee3e077c)... OK!
Decrypting etc_writable/usb_modeswitch/0586:0002 (9e7792121334c830edb2077c)... OK!
Decrypting etc_writable/usb_modeswitch/0586:3441 (1495573a044d02b9c056077c)... OK!
Decrypting etc_writable/usb_modeswitch/05c6:0010 (fab743fb3a2010fd1d92077c)... OK!
Decrypting etc_writable/usb_modeswitch/05c6:1000:sVe=GT (9447365bdddede4754c7077c)... OK!
Decrypting etc_writable/usb_modeswitch/05c6:1000:sVe=Option (f750bdfbed2686769dcf077c)... OK!
Decrypting etc_writable/usb_modeswitch/05c6:1000:uMa=AnyDATA (e5ec9ae03eaae55026f0077c)... OK!
Decrypting etc_writable/usb_modeswitch/05c6:1000:uMa=CELOT (6a474d23f46b78cf827e077c)... OK!
Decrypting etc_writable/usb_modeswitch/05c6:1000:uMa=DGT (20ae144ba9da1833fdce077c)... OK!
Decrypting etc_writable/usb_modeswitch/05c6:1000:uMa=Option (2fe22d0dc4a5a2a2adb5077c)... OK!
Decrypting etc_writable/usb_modeswitch/05c6:1000:uMa=SAMSUNG (b7959d711bb1baccf4b1077c)... OK!
Decrypting etc_writable/usb_modeswitch/05c6:1000:uMa=SSE (d98b1bde30b34c9a0829077c)... OK!
Decrypting etc_writable/usb_modeswitch/05c6:1000:uMa=StrongRising (2ca56257fcf8b5a6dda2077c)... OK!
Decrypting etc_writable/usb_modeswitch/05c6:1000:uMa=Vertex (511025e141072f7e4669077c)... OK!
Decrypting etc_writable/usb_modeswitch/05c6:2000 (4057fbeaa5c05700cbfe077c)... OK!
Decrypting etc_writable/usb_modeswitch/05c6:2001 (9d4d7f43b9b6b3ac6c2f077c)... OK!
Decrypting etc_writable/usb_modeswitch/05c6:6503 (a428169ee0efc6527d8b077c)... OK!
Decrypting etc_writable/usb_modeswitch/05c6:9024 (694352f536154f341edb077c)... OK!
Decrypting etc_writable/usb_modeswitch/05c6:f000 (7c06e718c26b10ce2ac6077c)... OK!
Decrypting etc_writable/usb_modeswitch/05c7:1000 (62a8879f4f08b3330446077c)... OK!
Decrypting etc_writable/usb_modeswitch/0685:2000 (417bbcb605676f010423077c)... OK!
Decrypting etc_writable/usb_modeswitch/072f:100d (bde54f28e90c21335096077c)... OK!
Decrypting etc_writable/usb_modeswitch/07d1:a800 (476251f9b1e8803500de077c)... OK!
Decrypting etc_writable/usb_modeswitch/07d1:a804 (f6d9e52712c3eda51933077c)... OK!
Decrypting etc_writable/usb_modeswitch/0922:1001 (6952930fd82df32f748a077c)... OK!
Decrypting etc_writable/usb_modeswitch/0922:1003 (506afe229ca05865b6ef077c)... OK!
Decrypting etc_writable/usb_modeswitch/0930:0d46 (aadafc84744ef2c4e788077c)... OK!
Decrypting etc_writable/usb_modeswitch/0ace:2011 (c74acc91b4baba5c2d39077c)... OK!
Decrypting etc_writable/usb_modeswitch/0ace:20ff (a35b055a47cdb1d191d1077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:4007 (dfc5419e12b40be59dbc077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:6711 (3c34740d0bd9ce2ec8ea077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:6731 (32202cce2cfb9ab1584e077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:6751 (a0614df79646ca89f59d077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:6771 (4a9315c2ce77bf786b33077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:6791 (aa648f79c521a2687823077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:6811 (9713b1d48ad2d4501d26077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:6911 (4b2f30fbcdd64bbd3df2077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:6951 (50ef7966206a6905c483077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:6971 (69b24409caa77c4dc1e8077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:7011 (3de8b4e789a967fb847e077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:7031 (a775a02c0086e44a5614077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:7051 (41ad0c2d7c97a251cc5c077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:7071 (e1efc824e4dba9e119e3077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:7111 (78c474f4c54c8f27f403077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:7211 (305773f9a5bc9821efa8077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:7251 (13fc8d531078d408bf1e077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:7271 (735617f27c1b2baefdce077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:7301 (a94945c7c148fb31fd6d077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:7311 (900a8dba5ffbcadb95b1077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:7361 (89ff9fe909e789d6fbd1077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:7381 (eb68d2675ef1678400fc077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:7401 (3202193181a134b4c2ab077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:7501 (653c1deed851505b5024077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:7601 (46825a7977a9e0421f31077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:7701 (739004bede93316b09bd077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:7706 (79e6546a6ba4d8747fa8077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:7801 (06a0ff394b924d8140f5077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:7901 (d5c1baf2b06fbcb1547d077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:7a01 (e42e8d3337037239d367077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:7a05 (11a0f56701c4972f5cc0077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:8006 (7e9697a0ec24c742a5c3077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:8200 (39ad6a3d6302d4b6d820077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:8201 (93bcceaa4e4368090d90077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:8300 (93c577285a973049450e077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:8302 (fcc682e60af79d7ea39a077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:8304 (9cc67473b467a0e620f8077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:8400 (684f520d6d63856cad7b077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:8600 (02ae5ad8464a6e181fa4077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:8700 (39bdf3a03513dd56b1fb077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:8800 (2d37d65e33ec6d8b25a1077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:8900 (6d19f127e2ffc5025fcb077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:9000 (d20cbfd1384217a47459077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:9200 (b7c060f110a96f01eb9c077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:c031 (3bb733a8167f92db0859077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:c100 (958fb1ac4fd755112ea1077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:d001 (05d138e7115b142c23a1077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:d013 (d7fc164a4e43c54cbaff077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:d031 (ac9674937ff0dd0d7dbd077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:d033 (89bcf24d60ac94495101077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:d035 (8a25a1d62d198b54c1cf077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:d055 (95b942d0465ac80bfc52077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:d057 (1e401068c5be69482e16077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:d058 (b077de33e81f5aef38ed077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:d155 (29f3e2854e3d11db1c50077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:d157 (4a1840d8aa9057d916ab077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:d255 (dbb4d23e284406857515077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:d257 (84f5ef66d8f557616b48077c)... OK!
Decrypting etc_writable/usb_modeswitch/0af0:d357 (e0c2f3ad4b236a990420077c)... OK!
Decrypting etc_writable/usb_modeswitch/0b3c:c700 (50ddb7bc8a2e54d52818077c)... OK!
Decrypting etc_writable/usb_modeswitch/0b3c:f000 (a19e8d5eaa254f573f92077c)... OK!
Decrypting etc_writable/usb_modeswitch/0b3c:f00c (babfe3237d17c5fb2b12077c)... OK!
Decrypting etc_writable/usb_modeswitch/0b3c:f017 (ac82f91574edf90f40d5077c)... OK!
Decrypting etc_writable/usb_modeswitch/0bdb:190d (c224095ef300111e6187077c)... OK!
Decrypting etc_writable/usb_modeswitch/0bdb:1910 (85d194718ccf8ca13173077c)... OK!
Decrypting etc_writable/usb_modeswitch/0cf3:20ff (e4fa70393b97f422ec01077c)... OK!
Decrypting etc_writable/usb_modeswitch/0d46:45a1 (5cf56c1122d48920fe69077c)... OK!
Decrypting etc_writable/usb_modeswitch/0d46:45a5 (4647351f5ecf98ec049d077c)... OK!
Decrypting etc_writable/usb_modeswitch/0df7:0800 (e17a4fca215faef3bb04077c)... OK!
Decrypting etc_writable/usb_modeswitch/0e8d:0002:uPr=MT (18b4749a7af4eabf557e077c)... OK!
Decrypting etc_writable/usb_modeswitch/0e8d:0002:uPr=Product (b7f98956a81347cd2da2077c)... OK!
Decrypting etc_writable/usb_modeswitch/0e8d:7109 (da0b277bca59bbfd156a077c)... OK!
Decrypting etc_writable/usb_modeswitch/0fca:8020 (be6debf287f02fdcae1f077c)... OK!
Decrypting etc_writable/usb_modeswitch/0fce:d0cf (ba18a2566ebe2c0db55d077c)... OK!
Decrypting etc_writable/usb_modeswitch/0fce:d0df (b0ad7f9af6754b7f5bba077c)... OK!
Decrypting etc_writable/usb_modeswitch/0fce:d0e1 (e1fdcb56991bc7c6523a077c)... OK!
Decrypting etc_writable/usb_modeswitch/0fce:d103 (cfb6c181f65546210d94077c)... OK!
Decrypting etc_writable/usb_modeswitch/0fd1:1000 (b39a573d58609e097bd3077c)... OK!
Decrypting etc_writable/usb_modeswitch/1004:1000 (1008f1132f6ead4ba7c4077c)... OK!
Decrypting etc_writable/usb_modeswitch/1004:607f (d6cd77eac0264642acf6077c)... OK!
Decrypting etc_writable/usb_modeswitch/1004:613a (b36a648d76dbb93e2e15077c)... OK!
Decrypting etc_writable/usb_modeswitch/1004:613f (5db037eef8057831105a077c)... OK!
Decrypting etc_writable/usb_modeswitch/1004:614e (61fbab16ec02629fea36077c)... OK!
Decrypting etc_writable/usb_modeswitch/1004:6156 (d4961e7adc937c8bd4b9077c)... OK!
Decrypting etc_writable/usb_modeswitch/1004:6190 (33c8ad015933867a84bd077c)... OK!
Decrypting etc_writable/usb_modeswitch/1004:61aa (3b517b1b2076b5872fe4077c)... OK!
Decrypting etc_writable/usb_modeswitch/1004:61dd (d0670052c33c1d0bf9e3077c)... OK!
Decrypting etc_writable/usb_modeswitch/1004:61e7 (40f8bd88070e6376dbaa077c)... OK!
Decrypting etc_writable/usb_modeswitch/1004:61eb (717f7ded3b2b17ce6800077c)... OK!
Decrypting etc_writable/usb_modeswitch/1004:6327 (da5de6b298d0dd734d9e077c)... OK!
Decrypting etc_writable/usb_modeswitch/1033:0035 (2c82b9ba4ba9dcb6c651077c)... OK!
Decrypting etc_writable/usb_modeswitch/106c:3b03 (cfddfe6a3a30d435ab31077c)... OK!
Decrypting etc_writable/usb_modeswitch/106c:3b05 (e6c4b4d6207d1655585d077c)... OK!
Decrypting etc_writable/usb_modeswitch/106c:3b06 (f29e5a3fc6bacbdb0e2b077c)... OK!
Decrypting etc_writable/usb_modeswitch/106c:3b11 (e8c95bee0f5ab11b6659077c)... OK!
Decrypting etc_writable/usb_modeswitch/106c:3b14 (e5bfa9afffc764600030077c)... OK!
Decrypting etc_writable/usb_modeswitch/1076:7f40 (857f86dc552c6419f184077c)... OK!
Decrypting etc_writable/usb_modeswitch/109b:f009 (75b00096750f0f90dde7077c)... OK!
Decrypting etc_writable/usb_modeswitch/10a9:606f (3c4578d599ac84902a48077c)... OK!
Decrypting etc_writable/usb_modeswitch/10a9:6080 (5810a217c188eeb0e9f9077c)... OK!
Decrypting etc_writable/usb_modeswitch/1199:0fff (4df7444db3ce6c83e7bf077c)... OK!
Decrypting etc_writable/usb_modeswitch/1266:1000 (60073d4a0fa55a60f117077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:#android (6b827dd1534c70d146d4077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:#linux (23f55ddb99019dd3bf5b077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:1001 (5db3beb23f4669761460077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:1003 (60f7202b5e4a80c14609077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:1009 (f54d86f1f91109233d63077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:1010 (5894e633df773d4f9ddd077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:101e (504c543b9e603e9e8e7a077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:1030 (9cf54d0e9573fec4391b077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:1031 (23f73434e6acb555710a077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:1413 (2e1f5fe324e5506feb69077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:1414 (5770bc46821e9fd1d112077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:1446 (0d4c531c078ca766b673077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:1449 (19b55acc3fc83a1686cd077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:14ad (6773b9020f9e44baabc3077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:14b5 (520d951334d5e85a0007077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:14b7 (bf43744d2d1a48ce769f077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:14ba (821e96e5507467625ad0077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:14c1 (0218ab5c64a1a08c8f96077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:14c3 (519e06ac10ef145f2549077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:14c4 (dee3ae53d28866262275077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:14c5 (57e5effa84cdb37e7628077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:14d1 (94456db4d88728acc4c7077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:14fe (041c385bdfee72705199077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:1505 (e5051ad8bc78973c672a077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:151a (2498686c55118a3f9edd077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:1520 (3bd252c763df2012f88c077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:1521 (f98d9b6c9488a40ff09a077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:1523 (dcaac3313343a8602a55077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:1526 (82399ccd0fb3a6c90df9077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:1553 (2a975cc9de3a77aee6bf077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:1557 (527692f0200fb56350ee077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:155a (f8ddd5abc56f5d25bbdd077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:155b (d0b84d22aa28be6dd71b077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:156a (6e75987da7569468d562077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:157c (178fc7f1d8be4e5223ea077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:157d (46700abd72aeeb72024f077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:1582 (1625a2d010cc388beb75077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:1583 (fe50e23e115ba1436214077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:15ca (ff4f84d27c27ba1f103c077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:15cd (5619dc281aa20d341b40077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:15cf (7cf3d23e22d477801833077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:15e7 (b11a5a9a0936aed7f6cb077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:1805 (14c418219c234a2edf81077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:1c0b (692d2354bc3071303de8077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:1c1b (c8a8a184cc635312f356077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:1c24 (2d7dfb2ef93818ed3adf077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:1d50 (2bd22801fc66d73cb48e077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:1da1 (aed29359e5432430e4b8077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:1f01 (7230567eb907e4f9a1ad077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:1f02 (342f75996cafe4ee0267077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:1f03 (575dde8e2c90e9bfd729077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:1f07 (8aee349c7661f72e387c077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:1f09 (0dd792522e2838d408d0077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:1f11 (289829b2e80d0df9b5eb077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:1f15 (813543e304d5b9962244077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:1f16 (ab1e21477284c4307390077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:1f17 (dfa1c19894fd07988da5077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:1f18 (e2d8214e12adf965dd22077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:1f19 (f66b58a2053e0b5a7a20077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:1f1b (6b32078d12741e3aabdd077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:1f1c (9e0e187924f7643bbb16077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:1f1d (09aaf79123b421b60ef3077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:1f1e (aa7d92688423fe8f2de8077c)... OK!
Decrypting etc_writable/usb_modeswitch/12d1:380b (07c4ed8091eb3779bbe4077c)... OK!
Decrypting etc_writable/usb_modeswitch/1307:1169 (9c3040b40c9e5c5bec21077c)... OK!
Decrypting etc_writable/usb_modeswitch/1410:5010 (3244c48e5da796a3e3cf077c)... OK!
Decrypting etc_writable/usb_modeswitch/1410:5020 (dec849cc0f3e2b2ca084077c)... OK!
Decrypting etc_writable/usb_modeswitch/1410:5023 (b444308ad8e75eb1a9d0077c)... OK!
Decrypting etc_writable/usb_modeswitch/1410:5030 (2c3656956552f8b9d116077c)... OK!
Decrypting etc_writable/usb_modeswitch/1410:5031 (4e303fa2935733fe86bf077c)... OK!
Decrypting etc_writable/usb_modeswitch/1410:5041 (bb0ed0f773e3e9176cc3077c)... OK!
Decrypting etc_writable/usb_modeswitch/1410:5055 (dac897746404b6505c23077c)... OK!
Decrypting etc_writable/usb_modeswitch/1410:5059 (4745cb59bf7fd0b983d0077c)... OK!
Decrypting etc_writable/usb_modeswitch/1410:7001 (db666c1fbe23a1faf63e077c)... OK!
Decrypting etc_writable/usb_modeswitch/148e:a000 (8e2ccc36e5bda1d7fb4a077c)... OK!
Decrypting etc_writable/usb_modeswitch/148f:2578 (04e98235b7fcd45cd3fa077c)... OK!
Decrypting etc_writable/usb_modeswitch/15eb:7153 (24d0bc3b2e46024ca645077c)... OK!
Decrypting etc_writable/usb_modeswitch/1614:0800 (1d16944824fda29fbaab077c)... OK!
Decrypting etc_writable/usb_modeswitch/1614:0802 (17db2c3d3ae1a6945db9077c)... OK!
Decrypting etc_writable/usb_modeswitch/16d8:6281 (9ded6a3cb690eea50af3077c)... OK!
Decrypting etc_writable/usb_modeswitch/16d8:6803 (40c756a9e2ffd88ad65c077c)... OK!
Decrypting etc_writable/usb_modeswitch/16d8:6804 (893678a121404271e959077c)... OK!
Decrypting etc_writable/usb_modeswitch/16d8:700a (4fe3787807ad7abe051e077c)... OK!
Decrypting etc_writable/usb_modeswitch/16d8:700b (33ea2d363db666db54fb077c)... OK!
Decrypting etc_writable/usb_modeswitch/16d8:f000 (8b7e34c6f0c64489b2be077c)... OK!
Decrypting etc_writable/usb_modeswitch/1726:f00e (7db65148c1fa577d1acf077c)... OK!
Decrypting etc_writable/usb_modeswitch/1782:0003 (1b0a82b4321403e9ec0c077c)... OK!
Decrypting etc_writable/usb_modeswitch/198a:0003 (58bb7d61b3fa766133ae077c)... OK!
Decrypting etc_writable/usb_modeswitch/198f:bccd (5a7098dca39dacc20fa3077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:#linux (14391cb6528f26ae0a60077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:0003 (5e7243d792e2c46d8a07077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:0026 (39a7b2c084fa0c6cbc5a077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:0040 (ab5b9da1c4a3a896a4bf077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:0053 (19dcec96515e028f8cf3077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:0083:uPr=WCDMA (68d2de80f9120afe4309077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:0101 (3bbd8dafe408c5d203cb077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:0103 (928d5448a8a8f2d0641a077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:0110 (3be4d7cccc1f19c35612077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:0115 (3b777a09f1a57b26dd36077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:0120 (17633f736c66ee70dec6077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:0146 (170840c6219f76ce3142077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:0149 (be8a34d13125e6242445077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:0150 (12026d55305b77f4e8c2077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:0154 (d3cb146a3ed0bf3f114a077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:0166 (f8251b5577cd2fa37432077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:0169 (ce7bdfc93ce3f1ee1b31077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:0266 (7002e64e5e97ffb4ed97077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:0304 (042c23dbea1b3afa90c1077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:0318 (edc4ffacc539d3abe2bd077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:0325 (11207edcc8ece9a5032d077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:0388 (70a964ae5208ffe1f6b1077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:0413 (427f6231b4618dcfec6c077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:1001 (8a91c1d299a76948b56e077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:1007 (f6182dc6fd65207e3dba077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:1009 (93f0525d9f48a454226e077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:1013 (d43c00c67acf634b029a077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:1017 (d31ef45a4a2d9837326f077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:1030 (8867d85dda840c6231d0077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:1038 (c1b30c1c5de0e647457d077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:1171 (a9ef71a21abea7d82801077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:1175 (b74ee269167a9d5fd819077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:1179 (d0432fcec7e5afc9483d077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:1201 (21a6369bf33e4da7f5f8077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:1207 (52a3433425a4f5bcec9b077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:1210 (f6579c676544e8983123077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:1216 (f57030ab692e9f682b63077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:1219 (fe2425666415c6af6c5c077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:1224 (003ad57d7baeb1f2b181077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:1225 (29f5a0509fd1b38e6e76077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:1227 (5efa43c52108eaafa591077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:1232 (712dff3b69d9a03c4cbf077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:1233 (87f794695fc48fc3cb9e077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:1237 (86bcb6256bffb225c020077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:1238 (843efe5f78fd91febc17077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:1420 (b0b3e19ef4f2f62f3f3e077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:1511 (5ba58c68347b1d092fc6077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:1514 (b8ddd08e9fd1980e34d2077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:1517 (d2896422067eb182a310077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:1520 (b99be2dea24f06293a13077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:1523 (10243d0f7a78e2ad47d7077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:1528 (4697f5ebf5d8cfcb051f077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:1536 (0cd5af182c056bfe8ba3077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:1542 (7ca29430ed0741e8c5a9077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:1588 (4a93bb70c77ec053aa89077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:2000 (53cf7d901107431cf5c0077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:2004 (419f5b7e9b05531c4dfb077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:bccd (03a96966203719b2a982077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:ffde (8a3724135e9730af702c077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:ffe6 (9154ee157199f5523e23077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:fff5 (0d8abc30f9d949e64c2f077c)... OK!
Decrypting etc_writable/usb_modeswitch/19d2:fff6 (b41b9f17264d38dcdd59077c)... OK!
Decrypting etc_writable/usb_modeswitch/1a8d:1000 (66d382aebac41b837c02077c)... OK!
Decrypting etc_writable/usb_modeswitch/1a8d:2000 (7a6926e4e3154eedaaa5077c)... OK!
Decrypting etc_writable/usb_modeswitch/1ab7:5700 (677ef5c69187829535fa077c)... OK!
Decrypting etc_writable/usb_modeswitch/1b7d:0700 (db6a2e17e82096d7bd48077c)... OK!
Decrypting etc_writable/usb_modeswitch/1bbb:000f (2cdf0c6a2a00eae740cc077c)... OK!
Decrypting etc_writable/usb_modeswitch/1bbb:00ca (edba068f1d5155330fa0077c)... OK!
Decrypting etc_writable/usb_modeswitch/1bbb:011f (e16723e864837ee61737077c)... OK!
Decrypting etc_writable/usb_modeswitch/1bbb:022c (a97414287f741d874073077c)... OK!
Decrypting etc_writable/usb_modeswitch/1bbb:f000 (08e46acede363fc4e95d077c)... OK!
Decrypting etc_writable/usb_modeswitch/1bbb:f017 (eb299d5670a9aa10d8ff077c)... OK!
Decrypting etc_writable/usb_modeswitch/1bbb:f052 (2de14c51008fb7c32d8a077c)... OK!
Decrypting etc_writable/usb_modeswitch/1c9e:1001 (dc642ed21f0afba990fd077c)... OK!
Decrypting etc_writable/usb_modeswitch/1c9e:6000 (a13e7b9f62f3d9c81249077c)... OK!
Decrypting etc_writable/usb_modeswitch/1c9e:6061:uPr=Storage (39af52642812e249bbee077c)... OK!
Decrypting etc_writable/usb_modeswitch/1c9e:9101 (439ff59c8a2a9f74206e077c)... OK!
Decrypting etc_writable/usb_modeswitch/1c9e:9200 (6071548c941c7397ecea077c)... OK!
Decrypting etc_writable/usb_modeswitch/1c9e:9401 (b165ce8ece4b0709b357077c)... OK!
Decrypting etc_writable/usb_modeswitch/1c9e:9800 (d0f5b037463dc5fd63d0077c)... OK!
Decrypting etc_writable/usb_modeswitch/1c9e:98ff (3e9f753089612182577f077c)... OK!
Decrypting etc_writable/usb_modeswitch/1c9e:9d00 (19a2e657a12018341f9e077c)... OK!
Decrypting etc_writable/usb_modeswitch/1c9e:9e00 (9bc374de7016fcb3abbe077c)... OK!
Decrypting etc_writable/usb_modeswitch/1c9e:9e08 (29953e69723a4783d885077c)... OK!
Decrypting etc_writable/usb_modeswitch/1c9e:f000 (f84e26ceed0785aeb8ef077c)... OK!
Decrypting etc_writable/usb_modeswitch/1c9e:f000:uMa=USB_Modem (f2c20da57861dfeaffbb077c)... OK!
Decrypting etc_writable/usb_modeswitch/1d09:1000 (66a362b7f2319962b67e077c)... OK!
Decrypting etc_writable/usb_modeswitch/1d09:1021 (ae106dae104c8468bcaa077c)... OK!
Decrypting etc_writable/usb_modeswitch/1d09:1025 (f52ff2c52687e261e54a077c)... OK!
Decrypting etc_writable/usb_modeswitch/1da5:f000 (9f381e4643ae398970bb077c)... OK!
Decrypting etc_writable/usb_modeswitch/1dbc:0669 (4aa5f1eb5ad80f7d9845077c)... OK!
Decrypting etc_writable/usb_modeswitch/1dd6:1000 (2c59f277f150fe3cfc70077c)... OK!
Decrypting etc_writable/usb_modeswitch/1de1:1101 (28cb64fd4157780089d9077c)... OK!
Decrypting etc_writable/usb_modeswitch/1e0e:f000 (1c70d649b52babec4081077c)... OK!
Decrypting etc_writable/usb_modeswitch/1e89:f000 (812d79463615b3088994077c)... OK!
Decrypting etc_writable/usb_modeswitch/1edf:6003 (8819f1e91bd28b3ec2d0077c)... OK!
Decrypting etc_writable/usb_modeswitch/1ee8:0003 (0c8f9721f9cb92cd0706077c)... OK!
Decrypting etc_writable/usb_modeswitch/1ee8:0009 (89a03367bc70a04f6492077c)... OK!
Decrypting etc_writable/usb_modeswitch/1ee8:0013 (7abae82505a187319758077c)... OK!
Decrypting etc_writable/usb_modeswitch/1ee8:0018 (3ded627edaad72b2a42e077c)... OK!
Decrypting etc_writable/usb_modeswitch/1ee8:0040 (785645ee13f396d95b10077c)... OK!
Decrypting etc_writable/usb_modeswitch/1ee8:0045 (50988f210cb7fb55e512077c)... OK!
Decrypting etc_writable/usb_modeswitch/1ee8:004a (449c03e5afa29aa3ea6b077c)... OK!
Decrypting etc_writable/usb_modeswitch/1ee8:004f (5288fe1ac57dec035ea5077c)... OK!
Decrypting etc_writable/usb_modeswitch/1ee8:0054 (e6800a58e227281376d8077c)... OK!
Decrypting etc_writable/usb_modeswitch/1ee8:0060 (060dd4b7eac5f6d54ff4077c)... OK!
Decrypting etc_writable/usb_modeswitch/1ee8:0063 (d498bdf6b6276a10c71e077c)... OK!
Decrypting etc_writable/usb_modeswitch/1ee8:0068 (7b90a1c05b74f8b800b5077c)... OK!
Decrypting etc_writable/usb_modeswitch/1f28:0021 (47df139e4d42f0472bf1077c)... OK!
Decrypting etc_writable/usb_modeswitch/1fac:0032 (ab2258ee05364d1d0c04077c)... OK!
Decrypting etc_writable/usb_modeswitch/1fac:0130 (c1acd32efdfc6488aa6d077c)... OK!
Decrypting etc_writable/usb_modeswitch/1fac:0150 (8f2e24d28974934de99f077c)... OK!
Decrypting etc_writable/usb_modeswitch/1fac:0151 (49628f780fd3c33b818d077c)... OK!
Decrypting etc_writable/usb_modeswitch/2001:00a6 (29ac93fa3222ec08f5f7077c)... OK!
Decrypting etc_writable/usb_modeswitch/2001:98ff (d74ed77147e6ee0f3baa077c)... OK!
Decrypting etc_writable/usb_modeswitch/2001:a401 (42d62852a6b1f373920a077c)... OK!
Decrypting etc_writable/usb_modeswitch/2001:a403 (68208585200f64d7fc2f077c)... OK!
Decrypting etc_writable/usb_modeswitch/2001:a405 (92099543538a305729cf077c)... OK!
Decrypting etc_writable/usb_modeswitch/2001:a706 (e2c92d2d0ebaf8f03a74077c)... OK!
Decrypting etc_writable/usb_modeswitch/2001:a707 (aa7128cc665bb30ee377077c)... OK!
Decrypting etc_writable/usb_modeswitch/2001:a708 (be31ff0db4fc920ccd33077c)... OK!
Decrypting etc_writable/usb_modeswitch/2001:a805 (0192de122f830a571875077c)... OK!
Decrypting etc_writable/usb_modeswitch/2001:a80b (ba0c698651c34063e30b077c)... OK!
Decrypting etc_writable/usb_modeswitch/2001:ab00 (f6bd25d1e9c1f28a9b0a077c)... OK!
Decrypting etc_writable/usb_modeswitch/201e:1023 (3d8d7ad96140c5548fd6077c)... OK!
Decrypting etc_writable/usb_modeswitch/201e:2009 (471b3e8c1187a5795c39077c)... OK!
Decrypting etc_writable/usb_modeswitch/2020:0002 (4f1eb7d775f6310b0282077c)... OK!
Decrypting etc_writable/usb_modeswitch/2020:f00e (f58806fe7f091512a798077c)... OK!
Decrypting etc_writable/usb_modeswitch/2020:f00f (52860b8163cea7f50c93077c)... OK!
Decrypting etc_writable/usb_modeswitch/2077:1000 (6f83b6433fb7fcba0d57077c)... OK!
Decrypting etc_writable/usb_modeswitch/2077:f000 (a94dffde48464fedd9e0077c)... OK!
Decrypting etc_writable/usb_modeswitch/20a6:f00e (de028754c598b07cc333077c)... OK!
Decrypting etc_writable/usb_modeswitch/20b9:1682 (2e67ad3ca12bbf93d46e077c)... OK!
Decrypting etc_writable/usb_modeswitch/21f5:1000 (3a7b73a5196845f511cb077c)... OK!
Decrypting etc_writable/usb_modeswitch/21f5:3010 (6692abee505609f71fe6077c)... OK!
Decrypting etc_writable/usb_modeswitch/2262:0001 (d187bfff55d5f8e8aef0077c)... OK!
Decrypting etc_writable/usb_modeswitch/22de:6801 (06a29be207446fee8e2e077c)... OK!
Decrypting etc_writable/usb_modeswitch/22de:6803 (1e3b3f8653e54d1dbb9c077c)... OK!
Decrypting etc_writable/usb_modeswitch/22f4:0021 (3f9ed23875a61cbedcd0077c)... OK!
Decrypting etc_writable/usb_modeswitch/230d:0001 (5849fd374778b207e8ff077c)... OK!
Decrypting etc_writable/usb_modeswitch/230d:0003 (eb71e8a776da7d90d4ce077c)... OK!
Decrypting etc_writable/usb_modeswitch/230d:0007 (f9be4ae5e72d449c2ada077c)... OK!
Decrypting etc_writable/usb_modeswitch/230d:000b (d3b96aa270715c1c94eb077c)... OK!
Decrypting etc_writable/usb_modeswitch/230d:000d (4fe5bca72508408d3a20077c)... OK!
Decrypting etc_writable/usb_modeswitch/230d:0101 (e4190e475b2379c765b6077c)... OK!
Decrypting etc_writable/usb_modeswitch/230d:0103 (aa5da1f36a6e2b60f5c0077c)... OK!
Decrypting etc_writable/usb_modeswitch/2357:0200 (9d8028b48343b2500d1b077c)... OK!
Decrypting etc_writable/usb_modeswitch/2357:f000 (f3789e248e7df0676d5f077c)... OK!
Decrypting etc_writable/usb_modeswitch/23a2:1010 (b1b1db1d08f8ddc215f1077c)... OK!
Decrypting etc_writable/usb_modeswitch/257a:a000 (8ba15b9e30334ac5e7e1077c)... OK!
Decrypting etc_writable/usb_modeswitch/257a:b000 (eb450112359bc747a995077c)... OK!
Decrypting etc_writable/usb_modeswitch/257a:c000 (62c4db775d73104c460f077c)... OK!
Decrypting etc_writable/usb_modeswitch/257a:d000 (e24470e400dcdf75d685077c)... OK!
Decrypting etc_writable/usb_modeswitch/8888:6500 (4205c54636927dd22bc2077c)... OK!
Decrypting etc_writable/usb_modeswitch/ed09:1021 (58e3b72726fc0ad00fdf077c)... OK!
Decrypting etc_writable/wtpinfo (43a902bf6c60ccf1a6c55188)... OK!
Decrypting etc_writable/zyxel/ (1b2ef9b525d17d24b8e94f88)... OK!
Decrypting etc_writable/zyxel/conf/ (72fe9f9ae1a0936ae2d74f88)... OK!
Decrypting etc_writable/zyxel/conf/__apcoverage_default.xml (c9a25ef27089e255f09b1283)... OK!
Decrypting etc_writable/zyxel/conf/__eps_checking_default.xml (a0d4d8dbff78bdbde7101283)... OK!
Decrypting etc_writable/zyxel/conf/__firewall_default.xml (83cedd78fe00b85962f01283)... OK!
Decrypting etc_writable/zyxel/conf/__geoip_default.xml (1b2b985625f2789f0a301283)... OK!
Decrypting etc_writable/zyxel/conf/__localwtp_default.xml (28e43f6e8e79381f29b45083)... OK!
Decrypting etc_writable/zyxel/conf/__route_default.xml (853ac1a6704df072ba971283)... OK!
Decrypting etc_writable/zyxel/conf/__system_default.xml (e55f843bf6a7a8737f1f4f88)... OK!
Decrypting etc_writable/zyxel/conf/__system_default.xml-usg40 (ad5484c5a028a8caeadd1179)... OK!
Decrypting etc_writable/zyxel/conf/__system_default.xml-usg40w (506c53ed8f45e23bf7651179)... OK!
Decrypting etc_writable/zyxel/conf/__wantrunk_default.xml (6dca74247e718ad44b111283)... OK!
Decrypting etc_writable/zyxel/conf/__zwo.xml (bd81351c986bcdbcc2f52384)... OK!
Decrypting etc_writable/zyxel/coredump_script/ (d778b6749d1d1df928a84f88)... OK!
Decrypting etc_writable/zyxel/coredump_script/common.sh (98138663860939e081e88f83)... OK!
Decrypting etc_writable/zyxel/coredump_script/samples.sh (f6200856c4873fd769998f83)... OK!
Decrypting etc_writable/zyxel/coredump_script/sdwan_common.sh (10789e6f56c8037f76f08f83)... OK!
Decrypting etc_writable/zyxel/secuextender/ (3d0d687fce04315f618b4f88)... OK!
Decrypting etc_writable/zyxel/secuextender/applet.html (3b6c6e136913cc4898610b80)... OK!
Decrypting etc_writable/zyxel/secuextender/sslapp.jar (3eda78c8df9cd2df1c756a80)... OK!
Decrypting etc_writable/zyxel/selector/ (2dc39c5c32a595728177bb7d)... OK!
Decrypting filechecksum (9995316b683c48d809b95188)... OK!
Decrypting filelist (11059cc1ced7f5fa46185288)... OK!
Decrypting fwversion (fcbb724625b80dc98a6f4d88)... OK!
Decrypting kernelchecksum (7019af09f3c51a7f7c934884)... OK!
Decrypting kernelshare40.bin (345bc4ea57aa23efce004884)... OK!
Decrypting wtp_image/ (a8c18710091ea8c72b795188)... OK!
Decrypting wtp_image/cloud_checksum (4135f03c6c00d3595fc75188)... OK!
Decrypting wtp_image/nwa5123-ac (e67b3dc8998a0d453f355088)... OK!
Decrypting wtp_image/nwa5123-ac-hd (fd12464284fec51d0aad5188)... OK!
Decrypting wtp_image/wtpinfo (39e7845fd384c03c2c1f5188)... OK!
Decrypting wtpinfo (3d719af11f921b1ffe215188)... OK!
Finished on Sun Sep 11 16:26:44 2022
cyberangel@cyberangel:~/Desktop/Zyxel/firmware$ 
```

解包后的文件为`decrypted_file.zip`：
![32.png](https://www.iotsec-zone.com/images/MdImg/666d1cde06055eaf0b48f5e8612531b8.png)
当然你也可以在执行命令时不加-d参数：`pkcrack -C ./470AALA0C0.bin -c db/etc/zyxel/ftp/conf/system-default.conf -P ./ZIPs/470AALA0C0_ZIP_9.zip -p 470AALA0C0.conf`，这表示pkcrack在搜索完压缩包的三部分密钥key之后继续搜索密码password：
![33.png](https://www.iotsec-zone.com/images/MdImg/3ba1dac2da415b97bcbe6f611337c9ab.png)
这里请注意，pkcrack的破解分为对压缩文档的破解（得到key）和对压缩文档密码的破解（得到password），直接破解压缩文档只需要计算出3个关键的key，计算这3个key的效率非常高。而计算压缩文档密码则需要在算出来3个key的基础上再进行穷举，虽然比一般的非明文破解的穷举效率要高，但是根据密码的长度，计算难度呈指数级增长。所以当密码非常长的情况下，破解难度相当大。其实无论什么情况下，直接破解文档都比破解密码更划算，因为破解密码最终也还是为了拿到文件。（[https://blog.csdn.net/qq_33265520/article/details/110137117](https://blog.csdn.net/qq_33265520/article/details/110137117)）<br />除了`pkcrack`还有一个和这个工具名字比较接近的工具`bkcrack`（[https://github.com/kimci86/bkcrack](https://github.com/kimci86/bkcrack)），通过它可以使用密钥对压缩包解包：

PS：该工具到现在还在持续更新：
![34.png](https://www.iotsec-zone.com/images/MdImg/27a3a23b3cb963f0d39af008f1c82726.png) 
bkcrack-github页面
![35.png](https://www.iotsec-zone.com/images/MdImg/1ff0f3cee41b74a4077373559af085db.png)
pkcrack-github页面

- 但是吧，使用bkcrack会报错，不知道是不是我不会用：`bkcrack -C ./470AALA0C0.bin -c db/etc/zyxel/ftp/conf/system-default.conf -k cb49ab19 32740ab6 7b0c34a2 -d system-default.conf`![36.png](https://www.iotsec-zone.com/images/MdImg/7aebf3f7cb10ba13d23fa9bf91e11416.png)

Zip error: could not find end of central directory signature... 可能bkcrack不支持解压这种的zip格式文件吧...

无语...算了，接着使用`pkcrack`的`zipdecrypt`吧：
![37.png](https://www.iotsec-zone.com/images/MdImg/0085e46d079cbc44eff3cb4109147735.png)
执行：`zipdecrypt cb49ab19 32740ab6 7b0c34a2 470AALA0C0.bin tmp.zip` 以得到解密之后的压缩包：
![38.png](https://www.iotsec-zone.com/images/MdImg/7798b4424ffeccce1c77d47c3c89c622.png)![39.png](https://www.iotsec-zone.com/images/MdImg/b5695ef96a5c489dc37df5ab14a397fe.png)

另外，7-zip在对文件进行压缩时，可以对如下选项进行设置以影响最后的压缩率：
![40.png](https://www.iotsec-zone.com/images/MdImg/5d7d4ee6bccd6de01f1a6c6c02ef91b0.png)

对`tmp.zip`的`compress.img`进行binwalk解压即可得到该设备的文件系统：
![41.png](https://www.iotsec-zone.com/images/MdImg/4d17236e6269593fef357809461a78de.png)

## 3、解包方式2 -- 固件自带程序解密

除了明文攻击之外还有一种方式可以解包固件，那就是使用固件自带的程序解密。因为包含有文件系统的镜像`compress.img`存在于加密的`470AALA0C0.bin`中，所以一定有一个解密程序在其它位置，我们很容易将目标锁定到`470AALA0C0.ri`：
![42.png](https://www.iotsec-zone.com/images/MdImg/954d1e1c30e644e3149e213d76a7560e.png)
使用binwalk简单的查看一下：
![43.png](https://www.iotsec-zone.com/images/MdImg/8cdca84bf17f646eb232a757f3d5daa9.png)
有`uImage header`，`binwalk -Me`解压：
![44.png](https://www.iotsec-zone.com/images/MdImg/6b81ccbd7ee61e57e748172896115d5b.png)
在启动发现有`fsextract`字样，猜测有可能是固件的文件系统的解密程序（file system extract）。对该文件信息收集：
![45.png](https://www.iotsec-zone.com/images/MdImg/a6bb4efa9a706a93db23c594593b02ed.png)
静态链接的大端序ELF可执行程序，可以使用qemu模拟。请注意，虽然file该可执行文件显示的是`ELF 32-bit`，但是实际上其是64bit程序：
![46.png](https://www.iotsec-zone.com/images/MdImg/a93512fcf094e52cac6a1b974a1bbe18.png)
运行该类程序需要使用qemu的`mipsn32`，如下图所示：
![47.png](https://www.iotsec-zone.com/images/MdImg/ecfa2e64d9cebbe84dc734243d54038b.png)
如果使用`qemu-mips-static`运行则会出现段错误，提示`Illegal instruction`（非法指令）：
![48.png](https://www.iotsec-zone.com/images/MdImg/5f3e0fcc3666d03d3a4d6b98ca0323b1.png)
`qemu-mipsn32-static`运行：
![49.png](https://www.iotsec-zone.com/images/MdImg/6b675abee4885db359a9136181c348b9.png)
好家伙2010年的程序，这解密程序够老了...想要了解该可执行文件的使用方法，还是得回到上级目录的zyinit，看名字好像是Zyxel设备的初始化程序，并且在该程序中有`zld_fsextract`字样：
![50.png](https://www.iotsec-zone.com/images/MdImg/f7918ad7d45630a3e0da2a91a1efdfb8.png)
将zyini拖入到IDA中查看：
![51.png](https://www.iotsec-zone.com/images/MdImg/5392eff5ac7a3c75315fa6961bac6eb7.png)
对`/zyinit/zld_fsextract`程序交叉引用过去：
![52.png](https://www.iotsec-zone.com/images/MdImg/099f2e9867912ca2b47b02ee8c53f7a5.png)![53.png](https://www.iotsec-zone.com/images/MdImg/2d4c21ff47e31ed95285575464806af5.png)
结合之前了解到的内容，所以解压命令的格式应该为`./zld_fsextract 【固件名称】 ./unzip -s extract -e`，即`qemu-mipsn32-static -strace ./zld_fsextract 470AALA0C0.bin ./unzip -s extract -e`：
![54.png](https://www.iotsec-zone.com/images/MdImg/61516a9c06ae9961f6643acfb4a412a6.png)
还是段错误，总感觉-e参数后面还缺了一个什么东西，并且根据`si_addr=NULL`可以知道是由于空指针造成的段错误，还是老老实实的逆一下`zld_fsextract`程序吧，交叉引用来到：![55.png](https://www.iotsec-zone.com/images/MdImg/a03a3ad2a5558ea3a1bfc2866fcb8c48.png)对`sub_10001198`交叉引用，来到：![56.png](https://www.iotsec-zone.com/images/MdImg/21cf6cf978009a2aff2f8650ac2c45a7.png)大致看一下参数的功能吧：![57.png](https://www.iotsec-zone.com/images/MdImg/8f6cc030596e57ea4eb6b33fbd1812f1.png)上面有一个list参数，大致会列出来一些文件的信息：

```bash
cyberangel@cyberangel:~/Desktop/Zyxel/firmware/_470AALA0C0.ri.extracted/_240.extracted/cpio-root/zyinit$ qemu-mipsn32-static ./zld_fsextract 470AALA0C0.bin ./unzip -s list
name                :kernel
scope               :-f kernelshare40.bin -f kernelchecksum -D /
nc_scope            :-f kernelshare40.bin
version             :3.10.87
build_date          :2021-10-27 16:34:05
checksum            :db77009f14d2f36f0fbb73bf6655ba75
core_checksum       :582806436b89d0eefd3b20e9348482a1

name                :code
scope               :-f bmshare40.bin -f bmchecksum -f kernelshare40.bin -f kernelchecksum -d wtp_image -d db -i -D /rw
scope               :-d db/etc/zyxel/ftp/conf -D /
nc_scope            :-f fwversion -f filechecksum -f wtpinfo
version             :4.70(AALA.0)
build_date          :2021-10-27 17:02:25
checksum            :c8ad7e3bcf3f7a710d063f2154d99307
core_checksum       :35b92a6d1192fdb23c78a7324feda44c

name                :WTP_wtp_image/nwa5120
scope               :-f wtp_image/nwa5120 -D /db
nc_scope            :
version             :5.10(###.10)
build_date          :2021-01-21 10:04:56
checksum            :
core_checksum       :

name                :WTP_wtp_image/wax650
scope               :-f wtp_image/wax650 -D /db
nc_scope            :
version             :6.25(###.1)
build_date          :2021-10-04 03:22:31
checksum            :
core_checksum       :

name                :WTP_wtp_image/wac6500
scope               :-f wtp_image/wac6500 -D /db
nc_scope            :
version             :6.25(###.0)
build_date          :2021-09-17 03:42:10
checksum            :
core_checksum       :

name                :WTP_wtp_image/nwa5301
scope               :-f wtp_image/nwa5301 -D /db
nc_scope            :
version             :5.10(###.10)
build_date          :2021-01-21 10:27:30
checksum            :
core_checksum       :

name                :WTP_wtp_image/nwa5123-ac
scope               :-f wtp_image/nwa5123-ac -D /db
nc_scope            :
version             :6.10(###.10)
build_date          :2021-01-21 15:20:56
checksum            :c1695615ba4a9f462cc5af123a60d82c
core_checksum       :c1695615ba4a9f462cc5af123a60d82c

name                :WTP_wtp_image/nwa5kcn50
scope               :-f wtp_image/nwa5kcn50 -D /db
nc_scope            :
version             :5.10(###.3)
build_date          :2018-01-23 11:28:31
checksum            :
core_checksum       :

name                :WTP_wtp_image/wac500h
scope               :-f wtp_image/wac500h -D /db
nc_scope            :
version             :6.25(###.0)
build_date          :2021-09-17 08:01:37
checksum            :
core_checksum       :

name                :WTP_wtp_image/wac500
scope               :-f wtp_image/wac500 -D /db
nc_scope            :
version             :6.25(###.0)
build_date          :2021-09-17 07:16:39
checksum            :
core_checksum       :

name                :WTP_wtp_image/wac6100
scope               :-f wtp_image/wac6100 -D /db
nc_scope            :
version             :6.25(###.0)
build_date          :2021-09-17 04:16:53
checksum            :
core_checksum       :

name                :WTP_wtp_image/wax610
scope               :-f wtp_image/wax610 -D /db
nc_scope            :
version             :6.25(###.1)
build_date          :2021-10-04 01:41:11
checksum            :
core_checksum       :

name                :WTP_wtp_image/wac6300
scope               :-f wtp_image/wac6300 -D /db
nc_scope            :
version             :6.25(###.0)
build_date          :2021-09-17 03:13:45
checksum            :
core_checksum       :

name                :WTP_wtp_image/wac5300v2
scope               :-f wtp_image/wac5300v2 -D /db
nc_scope            :
version             :6.25(###.0)
build_date          :2021-09-17 08:28:21
checksum            :
core_checksum       :

name                :WTP_wtp_image/wax510
scope               :-f wtp_image/wax510 -D /db
nc_scope            :
version             :6.25(###.1)
build_date          :2021-10-04 04:12:21
checksum            :
core_checksum       :

name                :WTP_wtp_image/wac5300
scope               :-f wtp_image/wac5300 -D /db
nc_scope            :
version             :6.10(###.10)
build_date          :2021-01-21 12:16:54
checksum            :
core_checksum       :

name                :WTP_wtp_image/nwa5123-ac-hd
scope               :-f wtp_image/nwa5123-ac-hd -D /db
nc_scope            :
version             :6.25(###.0)
build_date          :2021-09-17 04:43:21
checksum            :fd5bdf5ed8a5277ee8ad3988361cd973
core_checksum       :fd5bdf5ed8a5277ee8ad3988361cd973

cyberangel@cyberangel:~/Desktop/Zyxel/firmware/_470AALA0C0.ri.extracted/_240.extracted/cpio-root/zyinit$ 
```

虽然看起来没什么用，但从经验出发，list应该是列出一些文件信息，而使用extract参数应该可以解压缩这些文件，毕竟这两个参数同处于`-s`下面，我们来试试：

- `qemu-mipsn32-static -strace ./zld_fsextract 470AALA0C0.bin ./unzip -s extract -e code `

```bash
cyberangel@cyberangel:~/Desktop/Zyxel/firmware/_470AALA0C0.ri.extracted/_240.extracted/cpio-root/zyinit$ qemu-mipsn32-static -strace ./zld_fsextract 470AALA0C0.bin ./unzip -s extract -e code 
12764 ioctl(0,21517,1082129888,1082130724,8,0) = 0
12764 ioctl(1,21517,1082129888,1082130017,8,1) = 0
12764 rt_sigaction(SIGALRM,0x407ffb50,0x407ffb70) = 0
12764 brk(NULL) = 0x10129000
12764 brk(0x1012a000) = 0x1012a000
12764 brk(0x1012d000) = 0x1012d000
12764 brk(0x10131000) = 0x10131000
12764 brk(0x10135000) = 0x10135000
12764 alarm(1,268500992,269568872,115,1082130838,1936946035) = 0
12764 open("470AALA0C0.bin",O_RDONLY) = 3
12764 ioctl(3,21517,1082129312,0,1082129948,0) = -1 errno=25 (Inappropriate ioctl for device)
12764 brk(0x10136000) = 0x10136000
12764 lseek(3,-12,2,269700192,1082129948,1) = 136920272
12764 Linux(3,1082129568,4,269700128,1082129948,1) = 4
12764 Linux(3,1082129572,4,269700128,1082129948,1) = 4
12764 brk(0x10155000) = 0x10155000
12764 lseek(3,-126604,2,269704296,1082129948,1) = 136793680
12764 Linux(3,269704304,126592,269700128,1082129948,1) = 126592
12764 brk(0x10162000) = 0x10162000
12764 brk(0x10163000) = 0x10163000
12764 brk(0x10164000) = 0x10164000
12764 brk(0x10165000) = 0x10165000
12764 brk(0x10166000) = 0x10166000
12764 brk(0x10167000) = 0x10167000
12764 brk(0x10169000) = 0x10169000
12764 close(3) = 0
12764 fork() = 12766
 = 0
12764 wait4(-1,1082108672,0,0,1082129416,2)12766 execve("./unzip",{"./unzip","-o","-q","-P","vj/LOia3/vyoiX2No0MPojOrg0Pvf3OboPyC7YI9TGzCp1be3z3tiUkPWAKBFko","470AALA0C0.bin","-d","/rw","compress.img","etc_writable/","etc_writable/ModemManager/","etc_writable/ModemManager/libmm-plugin-altair-lte.so","etc_writable/ModemManager/libmm-plugin-anydata.so","etc_writable/ModemManager/libmm-plugin-cinterion.so","etc_writable/ModemManager/libmm-plugin-generic.so","etc_writable/ModemManager/libmm-plugin-gobi.so","etc_writable/ModemManager/libmm-plugin-hso.so","etc_writable/ModemManager/libmm-plugin-huawei.so","etc_writable/ModemManager/libmm-plugin-iridium.so","etc_writable/ModemManager/libmm-plugin-linktop.so","etc_writable/ModemManager/libmm-plugin-longcheer.so","etc_writable/ModemManager/libmm-plugin-mbm.so","etc_writable/ModemManager/libmm-plugin-motorola.so","etc_writable/ModemManager/libmm-plugin-mtk.so","etc_writable/ModemManager/libmm-plugin-nokia-icera.so","etc_writable/ModemManager/libmm-plugin-nokia.so","etc_writable/ModemManager/libmm-plugin-novatel-lte.so","etc_writable/ModemManager/libmm-plugin-novatel.so","etc_writable/ModemManager/libmm-plugin-option.so","etc_writable/ModemManager/libmm-plugin-pantech.so","etc_writable/ModemManager/libmm-plugin-samsung.so","etc_writable/ModemManager/libmm-plugin-sierra.so","etc_writable/ModemManager/libmm-plugin-simtech.so","etc_writable/ModemManager/libmm-plugin-telit.so","etc_writable/ModemManager/libmm-plugin-via.so","etc_writable/ModemManager/libmm-plugin-wavecom.so","etc_writable/ModemManager/libmm-plugin-x22x.so","etc_writable/ModemManager/libmm-plugin-zte.so","etc_writable/budget/","etc_writable/budget/budget.conf","etc_writable/cloud_checksum","etc_writable/dhcp6c-script","etc_writable/firmware-upgraded","etc_writable/tr069ta.conf","etc_writable/usb_modeswitch/","etc_writable/usb_modeswitch/03f0:002a","etc_writable/usb_modeswitch/0408:1000","etc_writable/usb_modeswitch/0408:ea17","etc_writable/usb_modeswitch/0408:ea25","etc_writable/usb_modeswitch/0408:ea43","etc_writable/usb_modeswitch/0408:f000","etc_writable/usb_modeswitch/0408:f001","etc_writable/usb_modeswitch/0421:060c","etc_writable/usb_modeswitch/0421:0610","etc_writable/usb_modeswitch/0421:0618","etc_writable/usb_modeswitch/0421:061d","etc_writable/usb_modeswitch/0421:0622","etc_writable/usb_modeswitch/0421:0627","etc_writable/usb_modeswitch/0421:062c","etc_writable/usb_modeswitch/0421:0632","etc_writable/usb_modeswitch/0421:0637","etc_writable/usb_modeswitch/0471:1210:uMa=Philips","etc_writable/usb_modeswitch/0471:1210:uMa=Wisue","etc_writable/usb_modeswitch/0471:1237","etc_writable/usb_modeswitch/0482:024d","etc_writable/usb_modeswitch/04bb:bccd","etc_writable/usb_modeswitch/04cc:2251","etc_writable/usb_modeswitch/04cc:225c","etc_writable/usb_modeswitch/04cc:226e","etc_writable/usb_modeswitch/04cc:226f","etc_writable/usb_modeswitch/04e8:680c","etc_writable/usb_modeswitch/04e8:689a","etc_writable/usb_modeswitch/04e8:f000:sMo=U209","etc_writable/usb_modeswitch/04fc:2140","etc_writable/usb_modeswitch/057c:62ff","etc_writable/usb_modeswitch/057c:84ff","etc_writable/usb_modeswitch/0586:0002","etc_writable/usb_modeswitch/0586:3441","etc_writable/usb_modeswitch/05c6:0010","etc_writable/usb_modeswitch/05c6:1000:sVe=GT","etc_writable/usb_modeswitch/05c6:1000:sVe=Option","etc_writable/usb_modeswitch/05c6:1000:uMa=AnyDATA","etc_writable/usb_modeswitch/05c6:1000:uMa=CELOT","etc_writable/usb_modeswitch/05c6:1000:uMa=DGT","etc_writable/usb_modeswitch/05c6:1000:uMa=Option","etc_writable/usb_modeswitch/05c6:1000:uMa=SAMSUNG","etc_writable/usb_modeswitch/05c6:1000:uMa=SSE","etc_writable/usb_modeswitch/05c6:1000:uMa=StrongRising","etc_writable/usb_modeswitch/05c6:1000:uMa=Vertex","etc_writable/usb_modeswitch/05c6:2000","etc_writable/usb_modeswitch/05c6:2001","etc_writable/usb_modeswitch/05c6:6503","etc_writable/usb_modeswitch/05c6:9024","etc_writable/usb_modeswitch/05c6:f000","etc_writable/usb_modeswitch/05c7:1000","etc_writable/usb_modeswitch/0685:2000","etc_writable/usb_modeswitch/072f:100d","etc_writable/usb_modeswitch/07d1:a800","etc_writable/usb_modeswitch/07d1:a804","etc_writable/usb_modeswitch/0922:1001","etc_writable/usb_modeswitch/0922:1003","etc_writable/usb_modeswitch/0930:0d46","etc_writable/usb_modeswitch/0ace:2011","etc_writable/usb_modeswitch/0ace:20ff","etc_writable/usb_modeswitch/0af0:4007","etc_writable/usb_modeswitch/0af0:6711","etc_writable/usb_modeswitch/0af0:6731","etc_writable/usb_modeswitch/0af0:6751","etc_writable/usb_modeswitch/0af0:6771","etc_writable/usb_modeswitch/0af0:6791","etc_writable/usb_modeswitch/0af0:6811","etc_writable/usb_modeswitch/0af0:6911","etc_writable/usb_modeswitch/0af0:6951","etc_writable/usb_modeswitch/0af0:6971","etc_writable/usb_modeswitch/0af0:7011","etc_writable/usb_modeswitch/0af0:7031","etc_writable/usb_modeswitch/0af0:7051","etc_writable/usb_modeswitch/0af0:7071","etc_writable/usb_modeswitch/0af0:7111","etc_writable/usb_modeswitch/0af0:7211","etc_writable/usb_modeswitch/0af0:7251","etc_writable/usb_modeswitch/0af0:7271","etc_writable/usb_modeswitch/0af0:7301","etc_writable/usb_modeswitch/0af0:7311","etc_writable/usb_modeswitch/0af0:7361","etc_writable/usb_modeswitch/0af0:7381","etc_writable/usb_modeswitch/0af0:7401","etc_writable/usb_modeswitch/0af0:7501","etc_writable/usb_modeswitch/0af0:7601","etc_writable/usb_modeswitch/0af0:7701","etc_writable/usb_modeswitch/0af0:7706","etc_writable/usb_modeswitch/0af0:7801","etc_writable/usb_modeswitch/0af0:7901","etc_writable/usb_modeswitch/0af0:7a01","etc_writable/usb_modeswitch/0af0:7a05","etc_writable/usb_modeswitch/0af0:8006","etc_writable/usb_modeswitch/0af0:8200","etc_writable/usb_modeswitch/0af0:8201","etc_writable/usb_modeswitch/0af0:8300","etc_writable/usb_modeswitch/0af0:8302","etc_writable/usb_modeswitch/0af0:8304","etc_writable/usb_modeswitch/0af0:8400","etc_writable/usb_modeswitch/0af0:8600","etc_writable/usb_modeswitch/0af0:8700","etc_writable/usb_modeswitch/0af0:8800","etc_writable/usb_modeswitch/0af0:8900","etc_writable/usb_modeswitch/0af0:9000","etc_writable/usb_modeswitch/0af0:9200","etc_writable/usb_modeswitch/0af0:c031","etc_writable/usb_modeswitch/0af0:c100","etc_writable/usb_modeswitch/0af0:d001","etc_writable/usb_modeswitch/0af0:d013","etc_writable/usb_modeswitch/0af0:d031","etc_writable/usb_modeswitch/0af0:d033","etc_writable/usb_modeswitch/0af0:d035","etc_writable/usb_modeswitch/0af0:d055","etc_writable/usb_modeswitch/0af0:d057","etc_writable/usb_modeswitch/0af0:d058","etc_writable/usb_modeswitch/0af0:d155","etc_writable/usb_modeswitch/0af0:d157","etc_writable/usb_modeswitch/0af0:d255","etc_writable/usb_modeswitch/0af0:d257","etc_writable/usb_modeswitch/0af0:d357","etc_writable/usb_modeswitch/0b3c:c700","etc_writable/usb_modeswitch/0b3c:f000","etc_writable/usb_modeswitch/0b3c:f00c","etc_writable/usb_modeswitch/0b3c:f017","etc_writable/usb_modeswitch/0bdb:190d","etc_writable/usb_modeswitch/0bdb:1910","etc_writable/usb_modeswitch/0cf3:20ff","etc_writable/usb_modeswitch/0d46:45a1","etc_writable/usb_modeswitch/0d46:45a5","etc_writable/usb_modeswitch/0df7:0800","etc_writable/usb_modeswitch/0e8d:0002:uPr=MT","etc_writable/usb_modeswitch/0e8d:0002:uPr=Product","etc_writable/usb_modeswitch/0e8d:7109","etc_writable/usb_modeswitch/0fca:8020","etc_writable/usb_modeswitch/0fce:d0cf","etc_writable/usb_modeswitch/0fce:d0df","etc_writable/usb_modeswitch/0fce:d0e1","etc_writable/usb_modeswitch/0fce:d103","etc_writable/usb_modeswitch/0fd1:1000","etc_writable/usb_modeswitch/1004:1000","etc_writable/usb_modeswitch/1004:607f","etc_writable/usb_modeswitch/1004:613a","etc_writable/usb_modeswitch/1004:613f","etc_writable/usb_modeswitch/1004:614e","etc_writable/usb_modeswitch/1004:6156","etc_writable/usb_modeswitch/1004:6190","etc_writable/usb_modeswitch/1004:61aa","etc_writable/usb_modeswitch/1004:61dd","etc_writable/usb_modeswitch/1004:61e7","etc_writable/usb_modeswitch/1004:61eb","etc_writable/usb_modeswitch/1004:6327","etc_writable/usb_modeswitch/1033:0035","etc_writable/usb_modeswitch/106c:3b03","etc_writable/usb_modeswitch/106c:3b05","etc_writable/usb_modeswitch/106c:3b06","etc_writable/usb_modeswitch/106c:3b11","etc_writable/usb_modeswitch/106c:3b14","etc_writable/usb_modeswitch/1076:7f40","etc_writable/usb_modeswitch/109b:f009","etc_writable/usb_modeswitch/10a9:606f","etc_writable/usb_modeswitch/10a9:6080","etc_writable/usb_modeswitch/1199:0fff","etc_writable/usb_modeswitch/1266:1000","etc_writable/usb_modeswitch/12d1:#android","etc_writable/usb_modeswitch/12d1:#linux","etc_writable/usb_modeswitch/12d1:1001","etc_writable/usb_modeswitch/12d1:1003","etc_writable/usb_modeswitch/12d1:1009","etc_writable/usb_modeswitch/12d1:1010","etc_writable/usb_modeswitch/12d1:101e","etc_writable/usb_modeswitch/12d1:1030","etc_writable/usb_modeswitch/12d1:1031","etc_writable/usb_modeswitch/12d1:1413","etc_writable/usb_modeswitch/12d1:1414","etc_writable/usb_modeswitch/12d1:1446","etc_writable/usb_modeswitch/12d1:1449","etc_writable/usb_modeswitch/12d1:14ad","etc_writable/usb_modeswitch/12d1:14b5","etc_writable/usb_modeswitch/12d1:14b7","etc_writable/usb_modeswitch/12d1:14ba","etc_writable/usb_modeswitch/12d1:14c1","etc_writable/usb_modeswitch/12d1:14c3","etc_writable/usb_modeswitch/12d1:14c4","etc_writable/usb_modeswitch/12d1:14c5","etc_writable/usb_modeswitch/12d1:14d1","etc_writable/usb_modeswitch/12d1:14fe","etc_writable/usb_modeswitch/12d1:1505","etc_writable/usb_modeswitch/12d1:151a","etc_writable/usb_modeswitch/12d1:1520","etc_writable/usb_modeswitch/12d1:1521","etc_writable/usb_modeswitch/12d1:1523","etc_writable/usb_modeswitch/12d1:1526","etc_writable/usb_modeswitch/12d1:1553","etc_writable/usb_modeswitch/12d1:1557","etc_writable/usb_modeswitch/12d1:155a","etc_writable/usb_modeswitch/12d1:155b","etc_writable/usb_modeswitch/12d1:156a","etc_writable/usb_modeswitch/12d1:157c","etc_writable/usb_modeswitch/12d1:157d","etc_writable/usb_modeswitch/12d1:1582","etc_writable/usb_modeswitch/12d1:1583","etc_writable/usb_modeswitch/12d1:15ca","etc_writable/usb_modeswitch/12d1:15cd","etc_writable/usb_modeswitch/12d1:15cf","etc_writable/usb_modeswitch/12d1:15e7","etc_writable/usb_modeswitch/12d1:1805","etc_writable/usb_modeswitch/12d1:1c0b","etc_writable/usb_modeswitch/12d1:1c1b","etc_writable/usb_modeswitch/12d1:1c24","etc_writable/usb_modeswitch/12d1:1d50","etc_writable/usb_modeswitch/12d1:1da1","etc_writable/usb_modeswitch/12d1:1f01","etc_writable/usb_modeswitch/12d1:1f02","etc_writable/usb_modeswitch/12d1:1f03","etc_writable/usb_modeswitch/12d1:1f07","etc_writable/usb_modeswitch/12d1:1f09","etc_writable/usb_modeswitch/12d1:1f11","etc_writable/usb_modeswitch/12d1:1f15","etc_writable/usb_modeswitch/12d1:1f16","etc_writable/usb_modeswitch/12d1:1f17","etc_writable/usb_modeswitch/12d1:1f18","etc_writable/usb_modeswitch/12d1:1f19","etc_writable/usb_modeswitch/12d1:1f1b","etc_writable/usb_modeswitch/12d1:1f1c","etc_writable/usb_modeswitch/12d1:1f1d","etc_writable/usb_modeswitch/12d1:1f1e","etc_writable/usb_modeswitch/12d1:380b","etc_writable/usb_modeswitch/1307:1169","etc_writable/usb_modeswitch/1410:5010","etc_writable/usb_modeswitch/1410:5020","etc_writable/usb_modeswitch/1410:5023","etc_writable/usb_modeswitch/1410:5030","etc_writable/usb_modeswitch/1410:5031","etc_writable/usb_modeswitch/1410:5041","etc_writable/usb_modeswitch/1410:5055","etc_writable/usb_modeswitch/1410:5059","etc_writable/usb_modeswitch/1410:7001","etc_writable/usb_modeswitch/148e:a000","etc_writable/usb_modeswitch/148f:2578","etc_writable/usb_modeswitch/15eb:7153","etc_writable/usb_modeswitch/1614:0800","etc_writable/usb_modeswitch/1614:0802","etc_writable/usb_modeswitch/16d8:6281","etc_writable/usb_modeswitch/16d8:6803","etc_writable/usb_modeswitch/16d8:6804","etc_writable/usb_modeswitch/16d8:700a","etc_writable/usb_modeswitch/16d8:700b","etc_writable/usb_modeswitch/16d8:f000","etc_writable/usb_modeswitch/1726:f00e","etc_writable/usb_modeswitch/1782:0003","etc_writable/usb_modeswitch/198a:0003","etc_writable/usb_modeswitch/198f:bccd","etc_writable/usb_modeswitch/19d2:#linux","etc_writable/usb_modeswitch/19d2:0003","etc_writable/usb_modeswitch/19d2:0026","etc_writable/usb_modeswitch/19d2:0040","etc_writable/usb_modeswitch/19d2:0053","etc_writable/usb_modeswitch/19d2:0083:uPr=WCDMA","etc_writable/usb_modeswitch/19d2:0101","etc_writable/usb_modeswitch/19d2:0103","etc_writable/usb_modeswitch/19d2:0110","etc_writable/usb_modeswitch/19d2:0115","etc_writable/usb_modeswitch/19d2:0120","etc_writable/usb_modeswitch/19d2:0146","etc_writable/usb_modeswitch/19d2:0149","etc_writable/usb_modeswitch/19d2:0150","etc_writable/usb_modeswitch/19d2:0154","etc_writable/usb_modeswitch/19d2:0166","etc_writable/usb_modeswitch/19d2:0169","etc_writable/usb_modeswitch/19d2:0266","etc_writable/usb_modeswitch/19d2:0304","etc_writable/usb_modeswitch/19d2:0318","etc_writable/usb_modeswitch/19d2:0325","etc_writable/usb_modeswitch/19d2:0388","etc_writable/usb_modeswitch/19d2:0413","etc_writable/usb_modeswitch/19d2:1001","etc_writable/usb_modeswitch/19d2:1007","etc_writable/usb_modeswitch/19d2:1009","etc_writable/usb_modeswitch/19d2:1013","etc_writable/usb_modeswitch/19d2:1017","etc_writable/usb_modeswitch/19d2:1030","etc_writable/usb_modeswitch/19d2:1038","etc_writable/usb_modeswitch/19d2:1171","etc_writable/usb_modeswitch/19d2:1175","etc_writable/usb_modeswitch/19d2:1179","etc_writable/usb_modeswitch/19d2:1201","etc_writable/usb_modeswitch/19d2:1207","etc_writable/usb_modeswitch/19d2:1210","etc_writable/usb_modeswitch/19d2:1216","etc_writable/usb_modeswitch/19d2:1219","etc_writable/usb_modeswitch/19d2:1224","etc_writable/usb_modeswitch/19d2:1225","etc_writable/usb_modeswitch/19d2:1227","etc_writable/usb_modeswitch/19d2:1232","etc_writable/usb_modeswitch/19d2:1233","etc_writable/usb_modeswitch/19d2:1237","etc_writable/usb_modeswitch/19d2:1238","etc_writable/usb_modeswitch/19d2:1420","etc_writable/usb_modeswitch/19d2:1511","etc_writable/usb_modeswitch/19d2:1514","etc_writable/usb_modeswitch/19d2:1517","etc_writable/usb_modeswitch/19d2:1520","etc_writable/usb_modeswitch/19d2:1523","etc_writable/usb_modeswitch/19d2:1528","etc_writable/usb_modeswitch/19d2:1536","etc_writable/usb_modeswitch/19d2:1542","etc_writable/usb_modeswitch/19d2:1588","etc_writable/usb_modeswitch/19d2:2000","etc_writable/usb_modeswitch/19d2:2004","etc_writable/usb_modeswitch/19d2:bccd","etc_writable/usb_modeswitch/19d2:ffde","etc_writable/usb_modeswitch/19d2:ffe6","etc_writable/usb_modeswitch/19d2:fff5","etc_writable/usb_modeswitch/19d2:fff6","etc_writable/usb_modeswitch/1a8d:1000","etc_writable/usb_modeswitch/1a8d:2000","etc_writable/usb_modeswitch/1ab7:5700","etc_writable/usb_modeswitch/1b7d:0700","etc_writable/usb_modeswitch/1bbb:000f","etc_writable/usb_modeswitch/1bbb:00ca","etc_writable/usb_modeswitch/1bbb:011f","etc_writable/usb_modeswitch/1bbb:022c","etc_writable/usb_modeswitch/1bbb:f000","etc_writable/usb_modeswitch/1bbb:f017","etc_writable/usb_modeswitch/1bbb:f052","etc_writable/usb_modeswitch/1c9e:1001","etc_writable/usb_modeswitch/1c9e:6000","etc_writable/usb_modeswitch/1c9e:6061:uPr=Storage","etc_writable/usb_modeswitch/1c9e:9101","etc_writable/usb_modeswitch/1c9e:9200","etc_writable/usb_modeswitch/1c9e:9401","etc_writable/usb_modeswitch/1c9e:9800","etc_writable/usb_modeswitch/1c9e:98ff","etc_writable/usb_modeswitch/1c9e:9d00","etc_writable/usb_modeswitch/1c9e:9e00","etc_writable/usb_modeswitch/1c9e:9e08","etc_writable/usb_modeswitch/1c9e:f000","etc_writable/usb_modeswitch/1c9e:f000:uMa=USB_Modem","etc_writable/usb_modeswitch/1d09:1000","etc_writable/usb_modeswitch/1d09:1021","etc_writable/usb_modeswitch/1d09:1025","etc_writable/usb_modeswitch/1da5:f000","etc_writable/usb_modeswitch/1dbc:0669","etc_writable/usb_modeswitch/1dd6:1000","etc_writable/usb_modeswitch/1de1:1101","etc_writable/usb_modeswitch/1e0e:f000","etc_writable/usb_modeswitch/1e89:f000","etc_writable/usb_modeswitch/1edf:6003","etc_writable/usb_modeswitch/1ee8:0003","etc_writable/usb_modeswitch/1ee8:0009","etc_writable/usb_modeswitch/1ee8:0013","etc_writable/usb_modeswitch/1ee8:0018","etc_writable/usb_modeswitch/1ee8:0040","etc_writable/usb_modeswitch/1ee8:0045","etc_writable/usb_modeswitch/1ee8:004a","etc_writable/usb_modeswitch/1ee8:004f","etc_writable/usb_modeswitch/1ee8:0054","etc_writable/usb_modeswitch/1ee8:0060","etc_writable/usb_modeswitch/1ee8:0063","etc_writable/usb_modeswitch/1ee8:0068","etc_writable/usb_modeswitch/1f28:0021","etc_writable/usb_modeswitch/1fac:0032","etc_writable/usb_modeswitch/1fac:0130","etc_writable/usb_modeswitch/1fac:0150","etc_writable/usb_modeswitch/1fac:0151","etc_writable/usb_modeswitch/2001:00a6","etc_writable/usb_modeswitch/2001:98ff","etc_writable/usb_modeswitch/2001:a401","etc_writable/usb_modeswitch/2001:a403","etc_writable/usb_modeswitch/2001:a405","etc_writable/usb_modeswitch/2001:a706","etc_writable/usb_modeswitch/2001:a707","etc_writable/usb_modeswitch/2001:a708","etc_writable/usb_modeswitch/2001:a805","etc_writable/usb_modeswitch/2001:a80b","etc_writable/usb_modeswitch/2001:ab00","etc_writable/usb_modeswitch/201e:1023","etc_writable/usb_modeswitch/201e:2009","etc_writable/usb_modeswitch/2020:0002","etc_writable/usb_modeswitch/2020:f00e","etc_writable/usb_modeswitch/2020:f00f","etc_writable/usb_modeswitch/2077:1000","etc_writable/usb_modeswitch/2077:f000","etc_writable/usb_modeswitch/20a6:f00e","etc_writable/usb_modeswitch/20b9:1682","etc_writable/usb_modeswitch/21f5:1000","etc_writable/usb_modeswitch/21f5:3010","etc_writable/usb_modeswitch/2262:0001","etc_writable/usb_modeswitch/22de:6801","etc_writable/usb_modeswitch/22de:6803","etc_writable/usb_modeswitch/22f4:0021","etc_writable/usb_modeswitch/230d:0001","etc_writable/usb_modeswitch/230d:0003","etc_writable/usb_modeswitch/230d:0007","etc_writable/usb_modeswitch/230d:000b","etc_writable/usb_modeswitch/230d:000d","etc_writable/usb_modeswitch/230d:0101","etc_writable/usb_modeswitch/230d:0103","etc_writable/usb_modeswitch/2357:0200","etc_writable/usb_modeswitch/2357:f000","etc_writable/usb_modeswitch/23a2:1010","etc_writable/usb_modeswitch/257a:a000","etc_writable/usb_modeswitch/257a:b000","etc_writable/usb_modeswitch/257a:c000","etc_writable/usb_modeswitch/257a:d000","etc_writable/usb_modeswitch/8888:6500","etc_writable/usb_modeswitch/ed09:1021","etc_writable/wtpinfo","etc_writable/zyxel/","etc_writable/zyxel/conf/","etc_writable/zyxel/conf/__apcoverage_default.xml","etc_writable/zyxel/conf/__eps_checking_default.xml","etc_writable/zyxel/conf/__firewall_default.xml","etc_writable/zyxel/conf/__geoip_default.xml","etc_writable/zyxel/conf/__localwtp_default.xml","etc_writable/zyxel/conf/__route_default.xml","etc_writable/zyxel/conf/__system_default.xml","etc_writable/zyxel/conf/__system_default.xml-usg40","etc_writable/zyxel/conf/__system_default.xml-usg40w","etc_writable/zyxel/conf/__wantrunk_default.xml","etc_writable/zyxel/conf/__zwo.xml","etc_writable/zyxel/coredump_script/","etc_writable/zyxel/coredump_script/common.sh","etc_writable/zyxel/coredump_script/samples.sh","etc_writable/zyxel/coredump_script/sdwan_common.sh","etc_writable/zyxel/secuextender/","etc_writable/zyxel/secuextender/applet.html","etc_writable/zyxel/secuextender/sslapp.jar","etc_writable/zyxel/selector/","filechecksum","filelist","fwversion","wtpinfo",NULL})qemu: uncaught target signal 4 (Illegal instruction) - core dumped
 = 12766
12764 write(1,0x10127428,1). = 1
12764 open("/rw/compress.img",O_RDONLY) = -1 errno=2 (No such file or directory)
12764 fork() = 12770
12764 wait4(-1,1082108672,0,0,269668096,1) = 0
12770 execve("./unzip",{"./unzip","-o","-q","-P","vj/LOia3/vyoiX2No0MPojOrg0Pvf3OboPyC7YI9TGzCp1be3z3tiUkPWAKBFko","470AALA0C0.bin","-d","/","db/etc/zyxel/ftp/conf/","db/etc/zyxel/ftp/conf/system-default.conf",NULL})qemu: uncaught target signal 4 (Illegal instruction) - core dumped
 = 12770
12764 write(1,0x10127428,1). = 1
12764 open("//db/etc/zyxel/ftp/conf/system-default.conf",O_RDONLY) = -1 errno=2 (No such file or directory)
12764 write(1,0x10127428,2)
 = 2
12764 exit(-66)
cyberangel@cyberangel:~/Desktop/Zyxel/firmware/_470AALA0C0.ri.extracted/_240.extracted/cpio-root/zyinit$ 
```

在上面的日志中注意到：
![58.png](https://www.iotsec-zone.com/images/MdImg/deec38f7f7f0206477c792f15e33f788.png)
-P参数后紧跟的应该是压缩包的密码：`vj/LOia3/vyoiX2No0MPojOrg0Pvf3OboPyC7YI9TGzCp1be3z3tiUkPWAKBFko`，回到Windows试试：
![59.png](https://www.iotsec-zone.com/images/MdImg/c77d18832d35d6552e06f72d8aa27eea.png)
好家伙，还真是，幸好之前在明文攻击的时候没有强制破解压缩包密码，这密码长的离谱！
<a name="RVPBq"></a>

# 补充

当然了，明文攻击不仅包括攻击者知道加密压缩包中某一个被加密文件的所有内容，还包括**部分**已知的明文。比如：

- 已知部分明文：`*lag{16e3********************74f6********`
- 待猜测的密文：`flag{16e371fa-0555-47fc-b343-74f6754f6c01}`
- 【这里的密文明文长度不一样】

我使用7-zip将密文压缩为加密压缩包`flag.zip`（7zip默认参数），密码为cyberangel。破解方式如下，我们需要将已知的明文切割为两个部分：

```bash
$ echo -n "lag{16e3" plain1.txt   # 连续的明文
$ echo -n "74f6" | xxd              # 额外明文的十六进制格式，37346636
```

![60.png](https://www.iotsec-zone.com/images/MdImg/d5afbf06d598904effbc4fb78a32646c.png)
攻击：`bkcrack -C flag.zip -c flag.txt -p plain1.txt -o 1 -x 29 37346636`（得到密钥key）：`10d73eba 07e8a69e b69f719c`【花了25分钟，垃圾Mac，风扇呼呼叫】
![61.png](https://www.iotsec-zone.com/images/MdImg/56551cde0a9da9f4b9fa7ebab330cf5e.png)
解包：`bkcrack -C flag.zip -c flag.txt -k 10d73eba 07e8a69e b69f719c -d res.txt`
![62.png](https://www.iotsec-zone.com/images/MdImg/7f97aed97e1cfdc750f71b034f3a13e6.png)
>
- `bkcrack -C 【加密压缩包】 -c 【加密压缩包的目标密文】 -p 【明文1】 -o 【明文1的起始位置在加密前文件中的偏移】 -x 【明文2的起始位置在加密前文件中的偏移】 【明文2 -- 16进制】`
>
```bash
cyberangel@cyberangel:~/Desktop/Zyxel/test$ bkcrack  -h
bkcrack 1.5.0 - 2022-07-07
usage: bkcrack [options]
Crack legacy zip encryption with Biham and Kocher's known plaintext attack.

Options to get the internal password representation:
 -c, --cipher-file <file   Zip entry or file on disk containing ciphertext
     --cipher-index <index Index of the zip entry containing ciphertext
 -C, --cipher-zip <archive Zip archive containing the ciphertext entry

 -p, --plain-file <file    Zip entry or file on disk containing plaintext
     --plain-index <index  Index of the zip entry containing plaintext
 -P, --plain-zip <archive  Zip archive containing the plaintext entry
 -t, --truncate <size      Maximum number of bytes of plaintext to load
 -o, --offset <offset      Known plaintext offset relative to ciphertext
                              without encryption header (may be negative)
 -x, --extra <offset<dataAdditional plaintext in hexadecimal starting
                              at the given offset (may be negative)
     --ignore-check-byte     Do not automatically use ciphertext's check byte
                              as known plaintext

 -e, --exhaustive            Try all the keys remaining after Z reduction

     --password <password  Password from which to derive the internal password
                              representation. Useful for testing purposes and
                              advanced scenarios such as reverting the effect of
                              the --change-password command.

Options to use the internal password representation:
 -k, --keys <X<Y<Z     Internal password representation as three 32-bits
                              integers in hexadecimal (requires -d, -U,
                              --change-keys or -r)

 -d, --decipher <file      File to write the deciphered data (requires -c)
     --keep-header           Write the encryption header at the beginning of
                              deciphered data instead of discarding it

 -U, --change-password <archive<password>
        Create a copy of the encrypted zip archive with the password set to the
        given new password (requires -C)

     --change-keys <archive<X<Y<Z>
        Create a copy of the encrypted zip archive using the given new internal
        password representation (requires -C)

 -r, --recover-password <length<charset>
        Try to recover the password or an equivalent one up to the given length
        using characters in the given charset. The charset is a sequence of
        characters or shortcuts for predefined charsets listed below.
        Example: ?l?d-.@
          ?l lowercase letters
          ?u uppercase letters
          ?d decimal digits
          ?s punctuation
          ?a alpha-numerical characters (same as ?l?u?d)
          ?p printable characters (same as ?a?s)
          ?b all bytes (0x00 - 0xff)

Other options:
 -L, --list <archive       List entries in a zip archive and exit
 -h, --help                  Show this help and exit

Environment variables:
 OMP_NUM_THREADS             Number of threads to use for parallel computations
cyberangel@cyberangel:~/Desktop/Zyxel/test$ 
```

注：已知的明文长度越长，破解速度越快

本篇文章使用的固件仍然存在`CVE-2020-29583`后门漏洞，admin用户加密之后的密文如下红框中所示`$4$WliGKvFQ$yMEH/WCnH1+NXuIUp0lzpUinIyEnrHFoRgesi6NdOFytmQg8lRfsVzUUjBGY+FiS4Up6KIgoP8OMEP0L3hRYSN2kpFTDIet31GoNwlM+S7U$`（`__system_default.xml-usg40`或`__system_default.xml-usg40w`）：
>![63.png](https://www.iotsec-zone.com/images/MdImg/f304de1763f69486471cd5ee2deaf893.png)
该加密方式使用了两种 -- base64编码和AES加密，国外已经有大师傅写出了相应的解密脚本：[https://github.com/inode-/zyxel_password_decrypter](https://github.com/inode-/zyxel_password_decrypter)，我们可以将上面的那一串密文保存为txt文件，然后进行解密：
![64.png](https://www.iotsec-zone.com/images/MdImg/d16fb90f1d8aaaaa8b4c7d4b4bf2f3ce.png)

```python
'''
/*****************************************************************************
 * Zyxel password decrypter                                                  *
 *                                                                           *
 * Copyright (c) 2022, Agazzini Maurizio - maurizio.agazzini@hnsecurity.it   *
 * All rights reserved.                                                      *
 *                                                                           *
 * Redistribution and use in source and binary forms, with or without        *
 * modification, are permitted provided that the following conditions        *
 * are met:                                                                  *
 *     * Redistributions of source code must retain the above copyright      *
 *       notice, this list of conditions and the following disclaimer.       *
 *     * Redistributions in binary form must reproduce the above copyright   *
 *       notice, this list of conditions and the following disclaimer in     *
 *       the documentation and/or other materials provided with the          *
 *       distribution.                                                       *
 *     * Neither the name of @ Mediaservice.net nor the names of its         *
 *       contributors may be used to endorse or promote products derived     *
 *       from this software without specific prior written permission.       *
 *                                                                           *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS       *
 * "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT         *
 * LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR     *
 * A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT      *
 * OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,     *
 * SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED  *
 * TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR    *
 * PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF    *
 * LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING      *
 * NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS        *
 * SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.              *
 *****************************************************************************/
'''

from Crypto.Cipher import AES
import base64
import re
import binascii
import argparse

aes_key = "001200054A1F23FB1F060A14CD0D018F5AC0001306F0121C"
aes_iv = "0006001C01F01FC0FFFFFFFFFFFFFFFF"

key = binascii.unhexlify(aes_key)
iv = binascii.unhexlify(aes_iv)

parser = argparse.ArgumentParser(description='Zyxel password decrypter')

parser.add_argument('--in', dest='filename', help='configuration file', required=True)

args = parser.parse_args()

filein = args.filename
fileout = args.filename + "_decrypted"

print("Zyxel password decrypter\n")

try:
    file1 = open(filein, 'r')
except:
    print("[!] can't open " + args.filename)
    exit()

all_lines = file1.readlines()

try:
    file1 = open(fileout, 'w')
except:
    print("[!] can't open for writing " + args.filename)
    exit()

count = 0

passwords = 0

for line in all_lines:
    count += 1

    if "$4$" in line:

        pattern = "\$.*?\$(.*?)\$(.*?)\$"

        par = re.search(pattern, line)

        print("[ ] Decrypting " + str(par.group(0))[:20] + "...", end = '')

        cipher = AES.new(key, AES.MODE_CBC, iv)

        try:
            decrypted = cipher.decrypt(base64.b64decode(par.group(2)+'=='))
        except:
            print("\r[-] Decrypting " + str(par.group(0))[:20] + "... KO - Decryption failed")
            file1.writelines(line)
            continue

        if str(par.group(1)) in str(decrypted):
            clear_pass = decrypted.decode('utf-8')[len(str(par.group(1))):decrypted.decode('utf-8').find('\x00')]
            line = line.replace(par.group(0),clear_pass)

            print("\r[X] Decrypting " + str(par.group(0))[:20] + "... OK - (" + clear_pass + ")")

            passwords += 1
        else:
            print("\r[-] Decrypting " + str(par.group(0))[:20] + "... KO - Decryption failed")
        
    elif "$5$" in line:

        pattern = "\$.*?\$(.*?)\$(.*?)\$(.*?)\$"
        par = re.search(pattern, line)

        cipher = AES.new(key, AES.MODE_CBC, iv)

        print("[ ] Decrypting " + str(par.group(0))[:20] + "...", end = '')

        try:
            decrypted = cipher.decrypt(base64.b64decode(par.group(3)+'=='))
        except:
            print("\r[-] Decrypting " + str(par.group(0))[:20] + "... KO - Decryption failed")
            file1.writelines(line)
            continue

        if str(par.group(2)) in str(decrypted):

            decrypted = decrypted.decode('utf-8')[len(str(par.group(2))):decrypted.decode('utf-8').find('\x00')-1]

            cipher = AES.new(key, AES.MODE_CBC, iv)

            decrypted = cipher.decrypt(base64.b64decode(str(decrypted)+'=='))

            if str(par.group(1)) in str(decrypted):

                clear_pass = decrypted.decode('utf-8')[len(str(par.group(1))):decrypted.decode('utf-8').find('\x00')]
                line = line.replace(par.group(0),clear_pass)

                print("\r[X] Decrypting " + str(par.group(0))[:20] + "... OK - (" + clear_pass + ")")

                passwords += 1
            else:
                print("\r[-] Decrypting " + str(par.group(0))[:20] + "... KO - Decryption failed")
        else:
            print("\r[-] Decrypting " + str(par.group(0))[:20] + "... KO - Decryption failed")

    file1.writelines(line)

file1.close()

print("\nDecrypted " + str(passwords) + " passwords")
print("Decrypted config file saved at " + fileout)
```

![65.png](https://www.iotsec-zone.com/images/MdImg/42e7431b0179bce28a0ee21389f11001.png)
后门密码为`1234`，可以使用该密码登录ftp的21端口。具体的加密过程将会在下一篇文章中分析【因为我没学过AES加密，现学现卖，悲:(  】。

# 参考资料（PDF）

> [(55条消息) 使用pkcrack明文方式破解zip压缩文件密码_张东南的博客-CSDN博客_pkcrack.pdf](https://www.yuque.com/attachments/yuque/0/2022/pdf/574026/1662991846873-eee3a415-4c68-4c52-b30e-44bce66f4b1f.pdf?_lake_card=%7B%22src%22%3A%22https%3A%2F%2Fwww.yuque.com%2Fattachments%2Fyuque%2F0%2F2022%2Fpdf%2F574026%2F1662991846873-eee3a415-4c68-4c52-b30e-44bce66f4b1f.pdf%22%2C%22name%22%3A%22%2855%E6%9D%A1%E6%B6%88%E6%81%AF%29+%E4%BD%BF%E7%94%A8pkcrack%E6%98%8E%E6%96%87%E6%96%B9%E5%BC%8F%E7%A0%B4%E8%A7%A3zip%E5%8E%8B%E7%BC%A9%E6%96%87%E4%BB%B6%E5%AF%86%E7%A0%81_%E5%BC%A0%E4%B8%9C%E5%8D%97%E7%9A%84%E5%8D%9A%E5%AE%A2-CSDN%E5%8D%9A%E5%AE%A2_pkcrack.pdf%22%2C%22size%22%3A1601093%2C%22type%22%3A%22application%2Fpdf%22%2C%22ext%22%3A%22pdf%22%2C%22source%22%3A%22%22%2C%22status%22%3A%22done%22%2C%22mode%22%3A%22title%22%2C%22download%22%3Atrue%2C%22taskId%22%3A%22ubfbba54a-5268-4209-9e4c-d2680ce8693%22%2C%22taskType%22%3A%22upload%22%2C%22__spacing%22%3A%22both%22%2C%22id%22%3A%22u2bcf9cfe%22%2C%22margin%22%3A%7B%22top%22%3Atrue%2C%22bottom%22%3Atrue%7D%2C%22card%22%3A%22file%22%7D)<br />[用维阵还原 Zyxel 后门漏洞.pdf](https://www.yuque.com/attachments/yuque/0/2022/pdf/574026/1662991841180-18bebf12-8e79-4914-b357-4a784012dd97.pdf?_lake_card=%7B%22src%22%3A%22https%3A%2F%2Fwww.yuque.com%2Fattachments%2Fyuque%2F0%2F2022%2Fpdf%2F574026%2F1662991841180-18bebf12-8e79-4914-b357-4a784012dd97.pdf%22%2C%22name%22%3A%22%E7%94%A8%E7%BB%B4%E9%98%B5%E8%BF%98%E5%8E%9F+Zyxel+%E5%90%8E%E9%97%A8%E6%BC%8F%E6%B4%9E.pdf%22%2C%22size%22%3A1265985%2C%22type%22%3A%22application%2Fpdf%22%2C%22ext%22%3A%22pdf%22%2C%22source%22%3A%22%22%2C%22status%22%3A%22done%22%2C%22mode%22%3A%22title%22%2C%22download%22%3Atrue%2C%22taskId%22%3A%22ue228b354-85e5-4468-b40d-ea31548bb7b%22%2C%22taskType%22%3A%22upload%22%2C%22__spacing%22%3A%22both%22%2C%22id%22%3A%22u93c1d1e2%22%2C%22margin%22%3A%7B%22top%22%3Atrue%2C%22bottom%22%3Atrue%7D%2C%22card%22%3A%22file%22%7D)<br />[USG310 4.70 固件解密分析 - CTF+.pdf](https://www.yuque.com/attachments/yuque/0/2022/pdf/574026/1662991868252-664090e4-fa58-4b57-8ce2-b1437ed9c578.pdf?_lake_card=%7B%22src%22%3A%22https%3A%2F%2Fwww.yuque.com%2Fattachments%2Fyuque%2F0%2F2022%2Fpdf%2F574026%2F1662991868252-664090e4-fa58-4b57-8ce2-b1437ed9c578.pdf%22%2C%22name%22%3A%22USG310+4.70+%E5%9B%BA%E4%BB%B6%E8%A7%A3%E5%AF%86%E5%88%86%E6%9E%90+-+CTF%2B.pdf%22%2C%22size%22%3A3121894%2C%22type%22%3A%22application%2Fpdf%22%2C%22ext%22%3A%22pdf%22%2C%22source%22%3A%22%22%2C%22status%22%3A%22done%22%2C%22mode%22%3A%22title%22%2C%22download%22%3Atrue%2C%22taskId%22%3A%22uff9577f2-37a8-4c18-8d9c-dc31bab82e0%22%2C%22taskType%22%3A%22upload%22%2C%22__spacing%22%3A%22both%22%2C%22id%22%3A%22u957bd2c2%22%2C%22margin%22%3A%7B%22top%22%3Atrue%2C%22bottom%22%3Atrue%7D%2C%22card%22%3A%22file%22%7D)<br />[ZIP已知明文攻击深入利用 - FreeBuf网络安全行业门户.pdf](https://www.yuque.com/attachments/yuque/0/2022/pdf/574026/1662991872310-024fcffa-f3be-413c-aa72-8eccc9c76d83.pdf?_lake_card=%7B%22src%22%3A%22https%3A%2F%2Fwww.yuque.com%2Fattachments%2Fyuque%2F0%2F2022%2Fpdf%2F574026%2F1662991872310-024fcffa-f3be-413c-aa72-8eccc9c76d83.pdf%22%2C%22name%22%3A%22ZIP%E5%B7%B2%E7%9F%A5%E6%98%8E%E6%96%87%E6%94%BB%E5%87%BB%E6%B7%B1%E5%85%A5%E5%88%A9%E7%94%A8+-+FreeBuf%E7%BD%91%E7%BB%9C%E5%AE%89%E5%85%A8%E8%A1%8C%E4%B8%9A%E9%97%A8%E6%88%B7.pdf%22%2C%22size%22%3A5135173%2C%22type%22%3A%22application%2Fpdf%22%2C%22ext%22%3A%22pdf%22%2C%22source%22%3A%22%22%2C%22status%22%3A%22done%22%2C%22mode%22%3A%22title%22%2C%22download%22%3Atrue%2C%22taskId%22%3A%22u27a06524-0c91-438d-af2e-e8322753688%22%2C%22taskType%22%3A%22upload%22%2C%22__spacing%22%3A%22both%22%2C%22id%22%3A%22u18a88925%22%2C%22margin%22%3A%7B%22top%22%3Atrue%2C%22bottom%22%3Atrue%7D%2C%22card%22%3A%22file%22%7D)**【个人感觉对明文攻击总结的比较全面的文章】**<br />[Zyxel firmware extraction and password analysis - hn security.pdf](https://www.yuque.com/attachments/yuque/0/2022/pdf/574026/1662991837846-85415ff9-eacd-4327-8c40-6cb15570e7b2.pdf?_lake_card=%7B%22src%22%3A%22https%3A%2F%2Fwww.yuque.com%2Fattachments%2Fyuque%2F0%2F2022%2Fpdf%2F574026%2F1662991837846-85415ff9-eacd-4327-8c40-6cb15570e7b2.pdf%22%2C%22name%22%3A%22Zyxel+firmware+extraction+and+password+analysis+-+hn+security.pdf%22%2C%22size%22%3A1104468%2C%22type%22%3A%22application%2Fpdf%22%2C%22ext%22%3A%22pdf%22%2C%22source%22%3A%22%22%2C%22status%22%3A%22done%22%2C%22mode%22%3A%22title%22%2C%22download%22%3Atrue%2C%22taskId%22%3A%22u434c8e4d-01c2-480c-871b-54cb2cd88a9%22%2C%22taskType%22%3A%22upload%22%2C%22__spacing%22%3A%22both%22%2C%22id%22%3A%22u9ce710c4%22%2C%22margin%22%3A%7B%22top%22%3Atrue%2C%22bottom%22%3Atrue%7D%2C%22card%22%3A%22file%22%7D)
