# Fuzzing101全实践 -- （三）
> 有毒
> 来源：https://www.iotsec-zone.com/article/245

### 6. Fuzzing101 - 6 GIMP

#### 1. 目标环境配置

本次的目标程序是一个带有GUI的可交互的程序，在构建编译上会比之前的软件稍微有一丢丢复杂。

首先要安装gimp会使用到的 GEGL 0.2(Generic Graphics Library)，尝试使用源码编译：

```shell
# install  dependencies
sudo apt install build-essential libatk1.0-dev libfontconfig1-dev libcairo2-dev libgudev-1.0-0 libdbus-1-dev libdbus-glib-1-dev libexif-dev libxfixes-dev libgtk2.0-dev python2.7-dev libpango1.0-dev libglib2.0-dev zlib1g-dev intltool libbabl-dev

# download and uncompress
wget https://download.gimp.org/pub/gegl/0.2/gegl-0.2.0.tar.bz2
tar xvf gegl-0.2.0.tar.bz2 && cd gegl-0.2.0

# modify the source code
sed -i 's/CODEC_CAP_TRUNCATED/AV_CODEC_CAP_TRUNCATED/g' ./operations/external/ff-load.c
sed -i 's/CODEC_FLAG_TRUNCATED/AV_CODEC_FLAG_TRUNCATED/g' ./operations/external/ff-load.c

# build and install
./configure --enable-debug --disable-glibtest  --without-vala --without-cairo --without-pango --without-pangocairo --without-gdk-pixbuf --without-lensfun --without-libjpeg --without-libpng --without-librsvg --without-openexr --without-sdl --without-libopenraw --without-jasper --without-graphviz --without-lua --without-libavformat --without-libv4l --without-libspiro --without-exiv2 --without-umfpack
make -j$(nproc)
sudo make install
```

这里对于 GEGL 这个图形库的编译安装我们不做过多介绍，这不是我们的重点，可以明确告知的是上面的库在编译时大概率会编译报错，导致一些库文件编译失败。所以，对于Ubuntu 20.04以上版本（我使用的是22.04）可以直接 `sudo apt install libgegl-0.4-0` 来安装这个0.4版本的库。（尽量不在非fuzz阶段浪费时间）

然后，下载 GIMP 2.8.16，并进行编译安装：

```shell
# download 
cd ..
wget https://mirror.klaus-uwe.me/gimp/pub/gimp/v2.8/gimp-2.8.16.tar.bz2
tar xvf gimp-2.8.16.tar.bz2 && cd gimp-2.8.16/

# build and install
CC=afl-clang-lto CXX=afl-clang-lto++ PKG_CONFIG_PATH=$PKG_CONFIG_PATH:/usr/local/lib/pkgconfig CFLAGS="-fsanitize=address" CXXFLAGS="-fsanitize=address" LDFLAGS="-fsanitize=address" ./configure --disable-gtktest --disable-glibtest --disable-alsatest --disable-nls --without-libtiff --without-libjpeg --without-bzip2 --without-gs --without-libpng --without-libmng --without-libexif --without-aa --without-libxpm --without-webkit --without-librsvg --without-print --without-poppler --without-cairo-pdf --without-gvfs --without-libcurl --without-wmf --without-libjasper --without-alsa --without-gudev --disable-python --enable-gimp-console --without-mac-twain --without-script-fu --without-gudev --without-dbus --disable-mp --without-linux-input --without-xvfb-run --with-gif-compression=none --without-xmc --with-shm=none --enable-debug  --prefix="$HOME/Desktop/Fuzz/training/fuzzing_gimp/gimp-2.8.16/install"
AFL_USE_ASAN=1 make -j$(nproc)
AFL_USE_ASAN=1 make install
```

这里的编译选项有点多，第一次的时候尽可能保持一致，避免出错，如果要进行优化和改进，可根据实际需求来增删编译选项。

编译完成后检查软件是否可以正常运行，命令行和图形界面都检查一下。

#### 2. AFL++编译target

##### 1. Persistent Mode

Persistent Mode 是 AFL 提供的一种可以加快fuzz 执行速度的功能，详细原理我们在源码解析的文章中已经进行了深入的介绍[https://www.iotsec-zone.com/article?id=197](https://www.iotsec-zone.com/article?id=197)，这里大家只需要简单理解成无需每次都进行 fork 操作，而只是在程序的某一特定位置进行循环 fuzz。

##### 2. 修改源码

我们需要在源码中找合适的位置插入 persistent mode 的执行代码，对于本例而言，有两处可以插入。第一处是 `app.c` 文件：

![0.png](https://www.iotsec-zone.com/images/MdImg/ebb62e762556521ac0ca28647a3f3aa2.png)

第二处是 `xcf.c` 文件：

![1.png](https://www.iotsec-zone.com/images/MdImg/3abbb005dc231875d393d9274d8dbbab.png)

至于为什么选择这两个地方进行 fuzz ，就看大家对软件流程和功能的理解程度了。

我们这里执行时，两种方案都测试一下。第二种方案，通过打补丁的方式来修改源码，补丁如下：

```c
--- ../xcf.c	2014-08-20 08:27:58.000000000 -0700
+++ ./app/xcf/xcf.c	2021-10-11 13:02:42.800831192 -0700
@@ -277,6 +277,10 @@
 
   filename = g_value_get_string (&args->values[1]);
 
+#ifdef __AFL_COMPILER
+  while(__AFL_LOOP(10000)){
+#endif
+
   info.fp = g_fopen (filename, "rb");
 
   if (info.fp)
@@ -366,6 +370,12 @@
   if (success)
     gimp_value_set_image (&return_vals->values[1], image);
 
+#ifdef __AFL_COMPILER
+  }
+#endif
+
+  exit(0);
+
   gimp_unset_busy (gimp);
 
   return return_vals;
```

需要注意的是，最后的 `exit(0);` 一定要有，否在程序会在 console 模式下卡住，导致 fuzz 的 test 都超时。

进行patch：

```shell
patch gimp-2.8.16/app/xcf/xcf.c -i persistent.patch
```

#### 3. 执行fuzz

测试用例我们用一个最简单的：

```shell
mkdir afl_in && cd afl_in
wget https://github.com/antonio-morales/Fuzzing101/blob/main/Exercise%206/SampleInput.xcf
```

这里还要注意，删除掉 gimp 的插件，这些插件可能会导致 gimp 运行失败：

```shell
rm ./install/lib/gimp/2.0/plug-ins/*
```

最后开启 fuzz：

```shell
ASAN_OPTIONS=detect_leaks=0,abort_on_error=1,symbolize=0 afl-fuzz -i './afl_in' -o './afl_out' -D -t 200 -M master -- ./gimp-2.8.16/install/bin/gimp-console-2.8 --verbose -d -f @@
ASAN_OPTIONS=detect_leaks=0,abort_on_error=1,symbolize=0 afl-fuzz -i './afl_in' -o './afl_out' -D -t 200 -S slave1 -- ./gimp-2.8.16/install/bin/gimp-console-2.8 --verbose -d -f @@
```

第一种方案的执行：

![2.png](https://www.iotsec-zone.com/images/MdImg/25dcf4509539c421ca7161260442e422.png)

第二种方案的执行：

![3.png](https://www.iotsec-zone.com/images/MdImg/b0c1e0bfc7392b9e62d2a19d3898bb65.png)

这里存在的一个问题是 fuzz 的速度不稳定，截图中的速度是偶尔出此案的这种几十的速率，一般情况下我的机器可以保持在300～500。

>思考
>
>第一种方案和第二种方案的对比，前者范围较广，相对而言程序的功能还是比较宽泛；后者具体到具体的格式的处理过程- xcf，所以更为精细，在进行fuzz时理论上也会效率更好、效果更好。这些是在使用 Persistent Mode 的基本前提下，如果只是对一个并不是很了解其内部功能和特性的目标进行 fuzz ，先“广撒网”也许更有帮助。

#### 4. crash分析

直接使用目标程序处理 crashes 目录下的文件即可。

#### 5. 总结

我们在这个例子主要是介绍 Persistent Mode 的使用，在AFL源码分析中我们详细介绍了该模式的实现方式，结合上其实际的使用方式，就可以更好地理解它的运作原理。在我们只想针对程序的某一部分进行fuzz时，可以选择这种方式。

### 7. Fuzzing101 - 7 Adobe Reader

之前我们都是针对有源码的程序进行 fuzz，这个例子将对纯二进制文件进行fuzz，需要使用到 AFL 的 qemu-mode。对于 AFL 的qemu-mode的详细介绍，可以查看 AFL 的官方文档的 qemu-mode 的部分。

#### 1. 目标环境配置

##### 1. 构建afl-qemu-trace

```shell
sudo apt install ninja-build libc6-dev-i386
cd ~/Desktop/v4ler1an/Fuzz/AFLplusplus/qemu_mode/
CPU_TARGET=i386 ./build_qemu_support.sh
```

检查一下是否可用：

![4.png](https://www.iotsec-zone.com/images/MdImg/59f3d5b2a4a311068235b62cfa8040d2.png)

##### 2. 构建 Adobe Reader

```shell
# install dependencies
sudo apt-get install libxml2:i386

# download and uncompress 
wget ftp://ftp.adobe.com/pub/adobe/reader/unix/9.x/9.5.1/enu/AdbeRdr9.5.1-1_i386linux_enu.deb

# install
sudo dpkg -i AdbeRdr9.5.1-1_i386linux_enu.deb
```

检查是否安装成功：

```shell
/opt/Adobe/Reader9/bin/acroread
```

![5.png](https://www.iotsec-zone.com/images/MdImg/f69598162a51b1429519b3ee1d01bfca.png)

![6.png](https://www.iotsec-zone.com/images/MdImg/39a0a3288e3f4bc8ad8cb627bf3ad285.png)

#### 2. AFL++ fuzz准备

从 SafeDocs “Issue Tracker” 下载语料，或者从[这里](https://www.pdfa.org/a-new-stressful-pdf-corpus/)使用更多的 PDF 语料。

```shell
# download and uncompress 
wget https://corpora.tika.apache.org/base/packaged/pdfs/archive/pdfs_202002/libre_office.zip
unzip libre_office.zip -d extracted
```

这里因为 PDF 格式的文件一般会比较大，所以我们先筛选小于 2KB 的文件来加快 fuzz 速度：

```shell
mkdir -p $HOME/Desktop/Fuzz/training/fuzzing_adobereader/afl_in
find ./extracted -type f -size -2k \
    -exec cp {} $HOME/Desktop/Fuzz/training/fuzzing_adobereader/afl_in \;
```

#### 3. 执行 fuzz

这里在执行 fuzz 时，有两种方式：

第一种是直接使用 `-Q` 选项开启 QEMU mode。

这里有一个需要注意的问题，因为前面运行的 `/opt/Adobe/Reader9/bin/acroread` 是一个 shell 脚本，并不是实际的二进制文件。真正的二进制文件是 `/opt/Adobe/Reader9/Reader/intellinux/bin/acroread`。这里需要设置一下两个环境变量：`ACRO_INSTALL_DIR` 和 `ACRO_CONFIG`。然后， 通过 `LD_LIBRARY_PATH` 指定加载共享库的路径。所以最终执行的 fuzz 命令如下：

```shell
ACRO_INSTALL_DIR=/opt/Adobe/Reader9/Reader ACRO_CONFIG=intellinux LD_LIBRARY_PATH=$LD_LIBRARY_PATH:'/opt/Adobe/Reader9/Reader/intellinux/lib' afl-fuzz -Q -i ./afl_in/ -o ./afl_out/ -t 2000 -- /opt/Adobe/Reader9/Reader/intellinux/bin/acroread -toPostScript @@
```

![7.png](https://www.iotsec-zone.com/images/MdImg/ee5a9cc95ccd39071cf2cd23b6c60249.png)

但是这种方式很慢，我们需要想办法提升 fuzz 速度。

第二种就是使用 AFL 的 persistent 模式。这种模式可以用在有源码的情况下，也可以用在只有二进制文件的情况下。在有源码时，我们可以直接在源码的合适的位置插入如下代码来实现 persistent 模式：

```c
while(__AFL_LOOP(10000)){
	/* Read input data. */
    /* Call library code to be fuzzed. */
    /* Reset state. */
}
```

而对于只有二进制文件的情况，整体思路上是一样的，也是找到合适的位置设置循环。分析二进制文件的函数地址可以使用常规的 IDA 等工具进行反编译来获取，这里使用一种简单的工具 —— valgrind。我们使用其中的 `callgrind` 来分析程序运行的时间和调用过程，来判断合适的位置：

```shell
sudo apt-get install valgrind
sudo apt-get install kcachegrind
```

然后，使用下面的命令来生成一个 callgrind report

```shell
ACRO_INSTALL_DIR=/opt/Adobe/Reader9/Reader ACRO_CONFIG=intellinux LD_LIBRARY_PATH=/opt/Adobe/Reader9/Reader/intellinux/lib valgrind --tool=callgrind /opt/Adobe/Reader9/Reader/intellinux/bin/acroread -toPostScript [samplePDF]
```

![8.png](https://www.iotsec-zone.com/images/MdImg/64ac2e1f66151add08651cb14ea380e9.png)
上述命令会在当前目录下生成一个 `callgrind.out` 文件，然后使用 `kcachegrind` 来读取：

```shell
kcachegrind callgrind.out.7658
```

![9.png](https://www.iotsec-zone.com/images/MdImg/48de595c68e1402e82f9427fa928690f.png)

这里我们选择地址 `0x08546a00` 。选择的原则是尽可能选择那些只执行了一次，并且可以使得 AFL++ 的 stability 值能在 90% 以上的地址。所以使用的命令为：

```shell
AFL_QEMU_PERSISTENT_GPR=1 AFL_QEMU_PERSISTENT_ADDR=0x08546a00 ACRO_INSTALL_DIR=/opt/Adobe/Reader9/Reader ACRO_CONFIG=intellinux LD_LIBRARY_PATH=$LD_LIBRARY_PATH:'/opt/Adobe/Reader9/Reader/intellinux/lib' afl-fuzz -Q -i ./afl_in/ -o ./afl_out/ -t 2000 -- /opt/Adobe/Reader9/Reader/intellinux/bin/acroread -toPostScript @@
```

我们指定了变量 `AFL_QEMU_PERSISTENT_ADDR` 为上面选择的地址。这次的fuzz速度会有提升（但是跟source code模式下对比，还是慢的可怜）：

![10.png](https://www.iotsec-zone.com/images/MdImg/4202c9bb73306539a95777f75fd19ac7.png)

![11.png](https://www.iotsec-zone.com/images/MdImg/e475ba2afa552582533e10d987a87bc5.png)

而且可以看到，随着 fuzz 的进行，速度逐渐变慢，并且 stability 值一直往下掉，这说明这个 fuzz 还存在优化空间。

#### 4. crash 分析

在发生 crash 之后，使用 afl-qemu-trace来查看最终的crash信息：

```shell
ACRO_INSTALL_DIR=/opt/Adobe/Reader9/Reader ACRO_CONFIG=intellinux LD_LIBRARY_PATH=opt/Adobe/Reader9/Reader/intellinux/lib /usr/local/bin/afl-qemu-trace -- /opt/Adobe/Reader9/Reader/intellinux/bin/acroread -toPostScript [crashFilePath] 
```

直接按照上面的常规的命令来执行 trace，会报页错误。所以我们使用另外一种方法—— [QASAN](https://github.com/andreafioraldi/qasan)

```shell
AFL_USE_QASAN=1 ACRO_INSTALL_DIR=/opt/Adobe/Reader9/Reader ACRO_CONFIG=intellinux LD_LIBRARY_PATH=opt/Adobe/Reader9/Reader/intellinux/lib /usr/local/bin/afl-qemu-trace -- /opt/Adobe/Reader9/Reader/intellinux/bin/acroread -toPostScript [crashFilePath] 
```

#### 5. 总结

这是我们第一次对纯二进制文件进行 fuzz ，使用的是 AFL 的qemu-mode，本身它开发出来就是用来 fuzz 无源码目标的。其实其基本逻辑还是借助qemu的虚拟能力，在虚拟过程中加入插桩和反馈来实现与有源码情况下类似的 fuzz 结果。在进行 crash 分析的时候，我们也不能像之前一样使用 ASan 这类工具，需要使用 afl-qemu-trace 来记录输出函数追踪信息和崩溃现场信息，这些信息的获取得益于 qemu 模拟时的插桩。

不管白和黑盒，AFL 都可以进行 fuzz，虽然具体实现上不太一样，但是思想是一样的：在代码实现中插入一些记录功能的代码，在发生崩溃时执行记录信息的功能。
