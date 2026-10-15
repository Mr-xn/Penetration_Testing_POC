# 模拟固件下的patch与hook
> 0431物联卫士实验室
> 来源：https://www.iotsec-zone.com/article/202

# 0、前言
在模拟固件的时候通常需要我们自己对二进制文件进行patch和hook，但无论是patch还是hook，都是通过修改（劫持）二进制文件的执行流程来达到固件顺利启动的目的。本篇文章我会好好的详细说明学会这些技巧的重要性以及如何掌握这些技巧。
# 1、引入LD_PRELOAD
逻辑很简单 -- 输入密码然后比较密码是否正确：

```c
// gcc -g test1.c -o test1
#include <stdio.h>
#include <string.h>
#include <unistd.h>

void init(){
    setbuf(stdin,NULL);
    setbuf(stdout,NULL);
    setbuf(stderr,NULL);
}
int main(){
    init();
    char* password = "cyberangel";
    char buffer[0x10] = "";
    printf("plz input your password!\n");
    read(0,buffer,0x10);
    printf("Your input is %s",buffer);
    if (!strncmp(password,buffer,strlen(buffer)-1)){    		// strlen(buffer)-1 去掉最后的\n
       printf("\033[0;32;32mYour password is Correct!\n\033[m");
    } else {
        printf("\033[0;32;31mYour password is Wrong!\n\033[m");
    }
    return 0;
}
```
![0.png](https://www.iotsec-zone.com/images/MdImg/9e58bccf869d8c8eb6e6e9f31897f631.png)
让我看看谁经常把angel（天使）打成angle（角度）
使用LD_PRELOAD加载如下动态链接库：
```c
// gcc -g -shared -fPIC hook.c -o hook.so
#include <stdlib.h>
#include <stdio.h>

int strncmp(const char *__s1, const char *__s2, size_t __n){
    // Dynamic Link Library have't main fucntion
    // We want to hook strncmp
    // int strncmp(const char *__s1, const char *__s2, size_t __n)
    if(getenv("LD_PRELOAD") != NULL){
        printf("\033[0;32;32mSuccess hook strncmp\n\033[m");
        unsetenv("LD_PRELOAD");         			// 必须清除LD_PRELOAD环境变量，否则会陷入hook的死循环。
    } else {
        printf("\033[0;32;31mFail to hook strncmp!\n\033[m");
    }
    return 0;                       				// return 0
}
```
![1.png](https://www.iotsec-zone.com/images/MdImg/72e9b26049ecf6c85234b95d76013342.png)
此时无论输入什么都显示的是密码正确，可以使用gdb来看下gdb --args env LD_PRELOAD=$PWD/hook.so ./test1
LD_PRELOAD后gdb无法b main，因此我直接对main的起始地址下断点：b *(0x555555554000+0x91D)
![2.png](https://www.iotsec-zone.com/images/MdImg/4e08d8b4e1e7b8150bba1b8143b35692.png)
![3.png](https://www.iotsec-zone.com/images/MdImg/39ad3e3c0ba4c0326f7e44350f765081.png)
got表也表明此时的strcmp为我们自己的：
![4.png](https://www.iotsec-zone.com/images/MdImg/0f4cf18774b1e21812a155d62b8934fe.png)
Full RELRO
`export LD_PRELOAD=$PWD/hook.so 和 ./test1与LD_PRELOAD=$PWD/hook.so ./test1等价`
# 2、一道开胃小菜（Bin 100）
以2014年的Hack In The Box Amsterdam: Bin 100逆向题作为小菜，hook方法之一的LD_PRELOAD开始在本题中崭露头角：
![5.png](https://www.iotsec-zone.com/images/MdImg/9c44c5946d59015293e1665b0aa4ba4d.png)
赋予可执行权限之后尝试运行，如下图所示；可以看到程序似乎一直在打印出英语句子，并且句子的大小写错乱：
![6.png](https://www.iotsec-zone.com/images/MdImg/3ab9f94d7ffe760bdb2c869664fa26b2.png)
在IDA中可以直接看到这些句子的原样，很明显程序在输出时会对句子的部分字母按照一定的规则进行大小写变换：
![7.png](https://www.iotsec-zone.com/images/MdImg/749c86c9f3bf3b4a5bdadd0e49bf45f9.png)
main函数的第一部分伪代码如下，首先调用qmemcpy函数将加密的数据encode复制到栈上得到encodestring，25到30行是将char randomNum[36]的数组清空：
![8.png](https://www.iotsec-zone.com/images/MdImg/7ce0213fa8d0cf568ae6bd2db12f04db.png)
第二部分如下，这是一个十分重要的循环，它的功能包括：
● 根据timeSecs2与timeSecs1的差值调用srand生成随机数种子。
● 保存rand()生成的随机数到randomNum数组。
● 内层while循环打印变换后的句子。
需要注意到每打印一行句子就要sleep(1)，即，要想在人不干预的前提下结束此循环最少需要201527*36 == 7254972秒（程序执行的时间可以忽略不计，大致84天左右吧）：
![9.png](https://www.iotsec-zone.com/images/MdImg/709486716e570fef4d57b31fee187828.png)
外层的do...while循环结束后会进入到第3部分的代码：
![10.png](https://www.iotsec-zone.com/images/MdImg/3b194d12508d6c01573185223cf046c9.png)
根据程序的流程，最后程序生成的flagchar取决于encodestring和randomNum，encodestring是不会变的，所以唯一的变量为最后一次循环中得到的随机数组randomNum：
![11.png](https://www.iotsec-zone.com/images/MdImg/a8f48a4bd64d978767b6fede7f49b56b.png)
对核心代码简化后得到：
```c
 count = 201527;
 timeSecs1 = time(0LL); 
 do
  {
    for ( loop = 0LL; loop != 36; ++loop )
    {
      char_loop = 0LL;
      timeSecs2 = time(0LL);
      srand(0xDEFACED - timeSecs1 + timeSecs2); // srand(0xDEFACED + timeSecs2 - timeSecs1);
      tmp = randomNum[loop];
      randomNum[loop] = rand() ^ tmp;           // rand生成的随机数为伪随机数
      // ......（代码省略）
      sleep(1u);                                // sleep
    }
    --count;
  }
  while ( count );
```
抛开sleep(1)不谈，剩下代码执行所占的时间几乎可以忽略不计，所以timeSecs2 - timeSecs1的差值会以每秒的时间递增1，所以想简单粗暴的直接nop掉sleep()的现在就可以洗洗睡了，否则最终得到的flag肯定是错误的。仔细想想看，既然每一次for循环（每秒）timeSecs2变量递增，那我们能不能在nop的前提下“欺骗”程序已经睡眠1s了？答案是可以的，进一步讲，调用sleep的最终目的是为了timeSecs2的增加而非真的要等待1s。有了这个想法之后我们可以按照如下思路来做。
在动态链接库中重新定义time和sleep这两个函数，通过LD_PRELOAD的预先加载功能达到hook这两个函数的目的，具体操作为每次for循环直接对时间变量timeSecs2自增1并nop掉sleep，从而将程序的休眠时间去掉，所以有如下代码：
```c
// 编译命令：gcc -shared -fPIC hook_time.c -o hook_time.so
static int t = 0;		// t变量也就是timeSecs2,该值可以为任意值，因为重点在于时间差（timeSecs2 - timeSecs1）而非某个时刻

void sleep(int sec) {
    t += sec;			// count = count + sec
}						// 每循环一次，count加1

int time() {
    return t;
}
// 源码的srand(0xDEFACED + timeSecs2 - timeSecs1);中的timeSecs2 - timeSecs1表示程序已经启动的时间。
```
printf到最终在屏幕显示所耗费的时间不会拖延程序执行代码的时间，就算是程序在短时间内打印出大量数据，则打印出某一数据时该printf肯定早已完成执行（屏幕的显示与printf的执行并不同步）。
堆在一起打印到屏幕上极费时间，在这里我将程序的输出重定向到tmp文件，以便快速得到结果。LD_PRELOAD=$PWD/hook_time.so ./hitb_bin100.elf > tmp结束后查看flag：
![12.png](https://www.iotsec-zone.com/images/MdImg/bca7f5c6e5e941c29c5fba0f7c66f1e7.png)
flag：p4ul_1z_d34d_1z_wh4t_th3_r3c0rd_s4ys
# 3、Cisco RV160W固件模拟（qemu-system）
使用的固件全称：RV16X_26X-v1.0.01.01-2020-08-17-11-09-01-AM.img，下载链接：
[https://software.cisco.com/download/home/286316464/type/282465789/release/1.0.01.01](https://software.cisco.com/download/home/286316464/type/282465789/release/1.0.01.01)
![13.png](https://www.iotsec-zone.com/images/MdImg/df869e542009d48a70b848623c1cbb2f.png)
一条直线表示固件没有加密，直接binwalk 解压binwalk -Me RV16X_26X-v1.0.01.01-2020-08-17-11-09-01-AM.img。文件系统如下图所示：
![14.png](https://www.iotsec-zone.com/images/MdImg/cba31939d4284c6691324c3b6a523f6f.png)
采用的架构为ARM：
![15.png](https://www.iotsec-zone.com/images/MdImg/a156ba2f05f8fa6c4f20a04d8ce54eac.png)
这里我使用qemu-system模拟：
![16.png](https://www.iotsec-zone.com/images/MdImg/0eb0b060fc882ef14bdf78dfb7bd36ba.png)

```c
// 虚拟机----------------------------------------------------------------------------
$ sudo tunctl -t tap0
$ sudo ifconfig tap0 192.168.2.1/24
$ sudo qemu-system-arm -M vexpress-a9 -kernel vmlinuz-3.2.0-4-vexpress -initrd initrd.img-3.2.0-4-vexpress -drive if=sd,file=debian_wheezy_armhf_standard.qcow2 -append "root=/dev/mmcblk0p2" -net nic -net tap,ifname=tap0,script=no,downscript=no -nographic
// qemu内部-------------------------------------------------------------------------
$ ifconfig eth0 192.168.2.2
$ service ssh start
// 虚拟机----------------------------------------------------------------------------
$ tar czf rooltfs.tar.gz ./rootfs
$ scp ./rootfs.tar.gz root@192.168.2.2:/root/
// qemu内部-------------------------------------------------------------------------
$ tar -zxvf ./rootfs.tar.gz
$ chmod -R 777 ./rootfs
$ mount -o bind /dev ./rootfs/dev && mount -t proc /proc ./rootfs/proc
$ chroot ./rootfs sh
```
该路由器的http服务由mini_httpd提供，但是无法直接运行：
![17.png](https://www.iotsec-zone.com/images/MdImg/ea0a9c3d8ea2406a7c8bbb8825f5b351.png)
IDA交叉引用字符串到sub_145C4：
![18.png](https://www.iotsec-zone.com/images/MdImg/3f54641d1f62f45a7120911bc00c4670.png)
错误原因是setsockopt函数在设置有关套接字的选项时由于参数不合法导致函数返回值小于0，但其实hook掉该函数影响也不是很大，只要保证关键的服务能跑起来就行。安装编译ARM所需要的依赖：

```c
$ sudo apt install libncurses5-dev gcc-arm-linux-gnueabi build-essential synaptic gcc-aarch64-linux-gnu
```
gcc-arm-linux-gnueabi所采用的是glibc，如下图所示：
![19.png](https://www.iotsec-zone.com/images/MdImg/c6af528989a3d4d0752c5acc06d94367.png)
而Cisco RV160W则采用的是eglibc：
● cp $(which qemu-arm-static) ./
● sudo chroot . ./qemu-arm-static /lib/libc.so.6
![20.png](https://www.iotsec-zone.com/images/MdImg/b743536a7b4e5b015626174b5bb219de.png)
不过没关系，glibc与eglibc编译得到的可执行程序相互兼容，至于我为什么要说到这一点，在稍后的Netgear模拟中会体现到。hook的代码中让setsockopt一直返回true就行：

```c
// 编译命令：arm-linux-gnueabi-gcc -shared -fPIC hook.c -o hook.so
#include <sys/socket.h>
 
int setsockopt(int sockfd, int level, int optname, const void *optval, socklen_t optlen){
    return 1;
}
```
上传qemu：scp ./hook.so root@192.168.2.2:/root/rootfs/
![21.png](https://www.iotsec-zone.com/images/MdImg/64d3e49753ac9ced5c5955b6a0a747c9.png)
hook mini_httpd，LD_PRELOAD=./hook.so mini_httpd：
![22.png](https://www.iotsec-zone.com/images/MdImg/5db6ee4ecbdc4207532f600a2baa9490.png)
![23.png](https://www.iotsec-zone.com/images/MdImg/b44f27c08642f84ff613de0132dd006e.png)
它调用了sub_1B5F0导致程序退出：
![24.png](https://www.iotsec-zone.com/images/MdImg/ce07fb100a80e98304ca419e31b050d8.png)
直接简单粗暴的将BL sub_1B5F0改为NOP：
![25.png](https://www.iotsec-zone.com/images/MdImg/c178dda2c156d722b8e6e5a345081a41.png)
![26.png](https://www.iotsec-zone.com/images/MdImg/c9212456d01047811b86046f485e730d.png)
保存导出为mini_httpd_patch，上传qemu：scp ./mini_httpd_patch root@192.168.2.2:/root/rootfs/usr/sbin，备份替换原来的文件、赋予其可执行：
![27.png](https://www.iotsec-zone.com/images/MdImg/41768b2a333de14d96d13aa10b207b74.png)
执行：LD_PRELOAD=./hook.so mini_httpd（记得先杀死原来的进程）
![28.png](https://www.iotsec-zone.com/images/MdImg/c55746292a6e215d3e6b6f4a038e37ec.png)
界面有点不太正常，没显示全：
![29.png](https://www.iotsec-zone.com/images/MdImg/dcca624bf3d8ac2c65480825cf33d6b5.png)
回到文件系统寻找原因，搜索mini_httpd字符串grep -r "mini_httpd" ./，得到与之有关的./etc/scripts/mini_httpd/mini_httpd.sh 和./etc/init.d/mini_httpd.init：
![30.png](https://www.iotsec-zone.com/images/MdImg/5453a0cb533fcd0dfe34d1c27feeb0d2.png)
尝试启动mini_httpd.init服务：
![31.png](https://www.iotsec-zone.com/images/MdImg/60f159c66dd93c95bd60822d2126ca69.png)
刷新网页后就正常了：
![32.png](https://www.iotsec-zone.com/images/MdImg/140bde5d619b7150789bf61d855808a0.png)
# 4、Netgear  R8300固件模拟（qemu-user）
## ①、准备文件系统
固件全称为R8300-V1.0.2.130_1.0.99.chk，下载链接：[http://www.downloads.netgear.com/files/GDC/R8300/R8300-V1.0.2.130_1.0.99.zip](http://www.downloads.netgear.com/files/GDC/R8300/R8300-V1.0.2.130_1.0.99.zip)
检查固件是否加密：
![33.png](https://www.iotsec-zone.com/images/MdImg/d9f846592cf5fe4d52583df9233d8d42.png)
也是一段光滑的直线，没有加密。binwalk -Me ./R8300-V1.0.2.130_1.0.99.chk对固件解压。我们的目标现在是有关于upnp服务的/usr/sbin/upnpd可执行文件，相关信息如下：
![34.png](https://www.iotsec-zone.com/images/MdImg/19c7891d62c7871715edd10611176ae3.png)
也是ARM架构。对于该固件我采用qemu-user模拟，尝试运行upnpd：

```c
cyberangel@cyberangel:【路径省略】/squashfs-root/usr/sbin$ cd ../../
cyberangel@cyberangel:【路径省略】/squashfs-root$ cp $(which qemu-arm-static) . 
cyberangel@cyberangel:【路径省略】squashfs-root$ sudo chroot . ./qemu-arm-static ./usr/sbin/upnpd
```
![35.png](https://www.iotsec-zone.com/images/MdImg/c6898069c62ac1a66884336d5b51b8db.png)
好家伙，没回显是吧？strace跟踪一下，sudo chroot . ./qemu-arm-static -strace ./usr/sbin/upnpd：
![36.png](https://www.iotsec-zone.com/images/MdImg/d849c99d34f37a03a517007aa52957d0.png)
原来是没有/var/run/upnpd.pid文件，注意到
![37.png](https://www.iotsec-zone.com/images/MdImg/dcd969c16e9e3adec57ee2325dfd171a.png)
var链接到tmp/var的软链接无效，我们自己给他重新建立一个（无需自己创建upnpd.pid文件）：
1. mkdir -p ./tmp/var/run
2. rm ./var
3. ln -s ./tmp/var/ ./var
![38.png](https://www.iotsec-zone.com/images/MdImg/b075a1e4fc3f005fb247dc2ddae8a0a7.png)
再次运行，sudo chroot . ./qemu-arm-static ./usr/sbin/upnpd：
```c
cyberangel@cyberangel:【路径省略】/squashfs-root$ sudo chroot . ./qemu-arm-static ./usr/sbin/upnpd
[sudo] password for cyberangel: 
cyberangel@cyberangel:【路径省略】/squashfs-root$ /dev/nvram: No such file or directory	
/dev/nvram: No such file or directory
	/*...【省略重复内容“No such file or directory”，下同】*/
	/dev/nvram: No such file or directory
open: No such file or directory
/dev/nvram: No such file or directory
/dev/nvram: No such file or directory
open: No such file or directory
/dev/nvram: No such file or directory
/dev/nvram: No such file or directory
open: No such file or directory
/dev/nvram: No such file or directory
/dev/nvram: No such file or directory
cyberangel@cyberangel:【路径省略】/squashfs-root$ 
```
看来还得修改可执行文件啊。
## ②、准备编译环境（uClibc）
我们来看一下该固件依赖的libc：
![39.png](https://www.iotsec-zone.com/images/MdImg/4bfe9c469e78cc8ae1cd76c660c34880.png)
是uClibc，该种libc是面向嵌入式Linux系统的小型的C标准库，所以不能使用glibc或eglibc编译器去编译该类型的动态链接库文件。我在网上找到了一个现成的编译器：[https://github.com/RMerl/am-toolchains（git](https://github.com/RMerl/am-toolchains（git) clone [https://github.com/RMerl/am-toolchains.git](https://github.com/RMerl/am-toolchains.git)），在此小节中只需要用到am-toolchains/brcm-arm-sdk的hndtools-arm-linux-2.6.36-uclibc-4.5.3：
![40.png](https://www.iotsec-zone.com/images/MdImg/01ea6241ed70989361c5e077cfd36c24.png)
我将该hndtools放在了/home/cyberangel/Desktop文件夹中，具体的编译方法为：
1. export LD_LIBRARY_PATH="$PWD/hndtools-arm-linux-2.6.36-uclibc-4.5.3/lib"
2. ./hndtools-arm-linux-2.6.36-uclibc-4.5.3/bin/arm-uclibc-gcc -c -O2 -fPIC -Wall 【待编译的文件.c】 -o 【目标文件.o】
3. ./hndtools-arm-linux-2.6.36-uclibc-4.5.3/bin/arm-uclibc-gcc -shared -nostdlib 【目标文件.o】 -o 【动态链接库文件.so】
在编译的时候可能会出现cc1: error while loading shared libraries: libelf.so.1: cannot open shared object file: No such file or directory，执行sudo apt install libelf-dev:i386 命令就可以了。
## ③、hook与patch
①、使用nvram-faker
● github链接：[https://github.com/zcutlip/nvram-faker](https://github.com/zcutlip/nvram-faker)
网络上有人已经写好了基于nvram-faker的Netgear libnvram.so的hook：[https://github.com/therealsaumil/custom_nvram/blob/master/custom_nvram_r6250.c](https://github.com/therealsaumil/custom_nvram/blob/master/custom_nvram_r6250.c)，虽然针对的型号为Netgear 6250/6400，但是对我们的R8300仍然适用，源码如下：

```c
/* custom_nvram.c
 *
 * Emulates the Netgear 6250/6400's nvram functions
 * by reading key=value pairs from /tmp/nvram.ini
 *
 * by Saumil Shah
 * @therealsaumil
 */

#define _GNU_SOURCE

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <dlfcn.h>

// ./buildroot-2016.11.2/output/host/usr/bin/arm-buildroot-linux-uclibcgnueabi-gcc -shared -fPIC -o nvram.so nvram.c

#define NVRAM_FILE      "/tmp/nvram.ini"
#define NVRAM_ENTRIES   2000
#define NVRAM_KEYLEN    128
#define NVRAM_LINE      256

static int counter = 0;
static int nvram_init = 0;
static int nvram_entries = 0;

// inefficient and crude key value pair array
static char key[NVRAM_ENTRIES][NVRAM_KEYLEN];
static char value[NVRAM_ENTRIES][NVRAM_KEYLEN];

// function declarations
static int custom_nvram_init();
int read_nvram();
static int (*real_system)(const char *command) = NULL;
static FILE *(*real_fopen)(const char *filename, const char *mode) = NULL;
static int (*real_open)(const char *pathname, int flags) = NULL;

// function will be called only once when any of the acosNvram_* functions get
// invoked
static int custom_nvram_init()
{
   nvram_init = 1;
   printf("custom_nvram initialised\n");
   nvram_entries = read_nvram();
   printf("Read %d entries from %s\n", nvram_entries, NVRAM_FILE);
}

// function to read the nvram.ini file into
// a global array
int read_nvram()
{
   int i = 0;
   FILE *fp;
   char line[NVRAM_LINE], *k, *v;

   fp = fopen(NVRAM_FILE, "r");
   if(fp == (FILE *) NULL) {
      printf("Cannot open %s\n", NVRAM_FILE);
      exit(-1);
   }

   while(!feof(fp)) {
      fgets(line, NVRAM_LINE, fp);
      k = strtok(line, "=");
      v = strtok(NULL, "\n");
      memset(key[i], '\0', NVRAM_KEYLEN);
      memset(value[i], '\0', NVRAM_KEYLEN);
      if(k != NULL)
         strncpy(key[i], k, NVRAM_KEYLEN - 1);
      if(v != NULL)
         strncpy(value[i], v, NVRAM_KEYLEN - 1);

      printf("[nvram %d] %s = %s\n", i, key[i], value[i]);
      i++;

      if(i >= NVRAM_ENTRIES) {
         printf("** WARNING: nvram entries exceeds %d\n", NVRAM_ENTRIES);
         break;
      }
   }

   fclose(fp);
   return(i);
}

char *nvram_get(char *k)
{
   char *v = "";
   int i;

   for(i = 0; i < nvram_entries; i++) {
      if(strcmp(key[i], k) == 0) {
         //v = strdup(value[i]);
         v = value[i];
         break;
      }
   }
   return(v);
}

int nvram_set(char *k, char *v)
{
   int i;

   for(i = 0; i < nvram_entries; i++) {
      if(strcmp(key[i], k) == 0) {
         strncpy(value[i], v, NVRAM_KEYLEN - 1);
         break;
      }
   }
   return(i);
}

// hook system()
int system(const char *command)
{
   int r;
   printf("[0x%08x] ", __builtin_return_address(0));  // get caller's address
   real_system = dlsym(RTLD_NEXT, "system");
   r = real_system(command);
   printf("system('%s') = %d\n", command, r);
   return(r);
}

// hook fopen()
FILE *fopen(const char *filename, const char *mode)
{
   FILE *fp;
   printf("[0x%08x] ", __builtin_return_address(0));  // get caller's address
   real_fopen = dlsym(RTLD_NEXT, "fopen");
   fp = real_fopen(filename, mode);
   printf("fopen('%s', '%s') = 0x%08x\n", filename, mode, (unsigned int) fp);
   return(fp);
}

// hook open()
int open(const char *pathname, int flags)
{
   int r;
   printf("[0x%08x] ", __builtin_return_address(0));  // get caller's address
   real_open = dlsym(RTLD_NEXT, "open");
   r = real_open(pathname, flags);
   printf("open('%s', %d) = %d\n", pathname, flags, r);
   return(r);
}

/* intercepted libnvram.so functions */
char *acosNvramConfig_get(char *k)
{
   char *v = "";

   printf("[0x%08x] ", __builtin_return_address(0));  // get caller's address

   if(!nvram_init)
      custom_nvram_init();

   v = nvram_get(k);

   printf("acosNvramConfig_get('%s') = '%s'\n", k, v);
   return(v);
}

int acosNvramConfig_set(char *k, char *v) {
   int i;

   printf("[0x%08x] ", __builtin_return_address(0));  // get caller's address

   if(!nvram_init)
      custom_nvram_init();

   i = nvram_set(k, v);

   printf("[nvram %d] acosNvramConfig_set('%s', '%s')\n", i, k, v);
   return(0);
}

void acosNvramConfig_read(char *k, char *r, int len) {
   char* v = "";

   printf("[0x%08x] ", __builtin_return_address(0));  // get caller's address

   if(!nvram_init)
      custom_nvram_init();

   v = nvram_get(k);

   strncpy(r, v, len);
   printf("acosNvramConfig_read('%s', '%s', %d)\n", k, r, len);
}

int acosNvramConfig_match(char *k, char *v) {
   // return 0 (False) by default
   int r = 0;
   char *s;

   printf("[0x%08x] ", __builtin_return_address(0));  // get caller's address

   if(!nvram_init)
      custom_nvram_init();

   s = nvram_get(k);

   if(strcmp(s, v) == 0)
      r = 1;

   printf("acosNvramConfig_match('%s', '%s') = %d\n", k, v, r);
   return(r);
}

/* intercepted other libacos_shared.so functions */

int agApi_fwServiceAdd(char *k, int a, int b, int c) {
   printf("[0x%08x] ", __builtin_return_address(0));  // get caller's address
   counter++;
   printf("agApi_fwServiceAdd('%s', %d, %d, %d) = %d\n", k, a, b, c, counter);
   return(counter);
}

int agApi_fwURLFilterEnableTmSch_Session2(int x) {
   printf("[0x%08x] ", __builtin_return_address(0));  // get caller's address
   printf("agApi_fwURLFilterEnableTmSch_Session2(%d) = 0\n", x);
   return(0);
}

int agApi_fwURLFilterEnable_Session2(int x) {
   printf("[0x%08x] ", __builtin_return_address(0));  // get caller's address
   printf("agApi_fwURLFilterEnable_Session2(%d) = 0\n", x);
   return(0);
}

int agApi_tmschDelConf(char *k) {
   printf("[0x%08x] ", __builtin_return_address(0));  // get caller's address
   printf("agApi_tmschDelConf('%s') = 0\n", k);
   return(0);
}

int agApi_tmschAddConf(char *a, char *b, char *c, char *d, char *e, int f, int g, int h) {
   printf("[0x%08x] ", __builtin_return_address(0));  // get caller's address
   printf("agApi_tmschAddConf('%s', '%s', '%s', '%s', '%s', %d, %d, %d)\n", a, b, c, d, e, f, g, h);
   return(0);
}

int agApi_tmschDelConf_Session2(char *k) {
   printf("[0x%08x] ", __builtin_return_address(0));  // get caller's address
   printf("agApi_tmschDelConf_Session2('%s') = 0\n", k);
   return(0);
}

int agApi_tmschAddConf_Session2(char *a, char *b, char *c, char *d, char *e, int f, int g, int h) {
   printf("[0x%08x] ", __builtin_return_address(0));  // get caller's address
   printf("agApi_tmschAddConf_Session2('%s', '%s', '%s', '%s', '%s', %d, %d, %d)\n", a, b, c, d, e, f, g, h);
   return(0);
}

int agApi_fwBlkServModAction(char *k) {
   printf("[0x%08x] ", __builtin_return_address(0));  // get caller's address
   printf("agApi_fwBlkServModAction('%s') = 0\n", k);
   return(0);
}

int agApi_fwBlkServModAction_Session2(char *k) {
   printf("[0x%08x] ", __builtin_return_address(0));  // get caller's address
   printf("agApi_fwBlkServModAction('%s') = 0\n", k);
   return(0);
}

int agApi_fwEchoRespSet(int x) {
   printf("[0x%08x] ", __builtin_return_address(0));  // get caller's address
   printf("agApi_fwEchoRespSet(%d) = 1\n", x);
   return(1);
}

int agApi_fwURLFilterEnable(int x) {
   printf("[0x%08x] ", __builtin_return_address(0));  // get caller's address
   printf("agApi_fwURLFilterEnable(%d) = 0\n", x);
   return(0);
}

int agApi_fwURLFilterEnableTmSch() {
   printf("[0x%08x] ", __builtin_return_address(0));  // get caller's address
   printf("agApi_fwURLFilterEnableTmSch() = 0\n");
   return(0);
}

int agApi_fwGetAllServices(char *k, int a) {
   printf("[0x%08x] ", __builtin_return_address(0));  // get caller's address
   printf("agApi_fwGetAllServices('%s', %d) = %d\n", k, a, counter);
   return(counter);
}

void agApi_fwDelTriggerConf2(char *k) {
   printf("[0x%08x] ", __builtin_return_address(0));  // get caller's address
   printf("agApi_fwDelTriggerConf2('%s')\n", k);
}

int agApi_fwGetNextTriggerConf(int a) {
   printf("[0x%08x] ", __builtin_return_address(0));  // get caller's address
   printf("agApi_fwGetNextTriggerConf(0x%08x) = 1\n", a);
   return(1);
}
```
切换到Desktop目录下进行编译：
1. export LD_LIBRARY_PATH="$PWD/hndtools-arm-linux-2.6.36-uclibc-4.5.3/lib"
2. ./hndtools-arm-linux-2.6.36-uclibc-4.5.3/bin/arm-uclibc-gcc -c -O2 -fPIC -Wall /home/cyberangel/Desktop/模拟固件下的patch与hook/Netgear_R8300/nvram-faker/nvram-faker_hook.c -o /home/cyberangel/Desktop/模拟固件下的patch与hook/Netgear_R8300/nvram-faker/nvram-faker_hook.o
3. ./hndtools-arm-linux-2.6.36-uclibc-4.5.3/bin/arm-uclibc-gcc -shared -nostdlib /home/cyberangel/Desktop/模拟固件下的patch与hook/Netgear_R8300/nvram-faker/nvram-faker_hook.o -o /home/cyberangel/Desktop/模拟固件下的patch与hook/Netgear_R8300/nvram-faker/nvram-faker_hook.so
● 第二步编译生成的警告不用管，我懒的改源码了...
![41.png](https://www.iotsec-zone.com/images/MdImg/d8d78be96e32b0873e35009f4b4c8410.png)
hook前需要向/tmp/nvram.ini文件中写入待hook的变量，当然，也有人写好了，直接拿来用：

```c
upnpd_debug_level=9
lan_ipaddr=10.211.55.11
hwver=R8500
friendly_name=R8300
upnp_enable=1
upnp_turn_on=1
upnp_advert_period=30
upnp_advert_ttl=4
upnp_portmap_entry=1
upnp_duration=3600
upnp_DHCPServerConfigurable=1
wps_is_upnp=0
upnp_sa_uuid=00000000000000000000
lan_hwaddr=AA:BB:CC:DD:EE:FF
```
![42.png](https://www.iotsec-zone.com/images/MdImg/4933a09bd91616da968b09cc1be858d8.png)
● lan_ipaddr：qemu-user对应虚拟机ip，qemu-system对应qemu的ip
将其保存到固件文件系统的tmp目录下，hook启动sudo chroot . ./qemu-arm-static -E LD_PRELOAD="./nvram-faker_hook.so" /usr/sbin/upnpd:
![43.png](https://www.iotsec-zone.com/images/MdImg/82b2ccfd24eb5027291e0c0d12e0ed21.png)
没有找到dlsys符号，这是因为源文件中分别对system、fopen、open等函数进行了hook，其中就用到了dlsys函数：
![44.png](https://www.iotsec-zone.com/images/MdImg/7529ae9d27234be34c908f8777e48764.png)
在动态链接库/lib/libdl.so.0可找到dlsys的定义，修改命令为sudo chroot . ./qemu-arm-static -E LD_PRELOAD="./nvram-faker_hook.so ./lib/libdl.so.0" /usr/sbin/upnpd:

```c
cyberangel@cyberangel:~/Desktop/模拟固件下的patch与hook/Netgear_R8300/_R8300-V1.0.2.130_1.0.99.chk.extracted/squashfs-root$ [0x00026460] fopen('/var/run/upnpd.pid', 'wb+') = 0x000e4008
[0x0002648c] custom_nvram initialised
[0xff758b0c] fopen('/tmp/nvram.ini', 'r') = 0x000e4008
[nvram 0] upnpd_debug_level = 9
[nvram 1] lan_ipaddr = 10.211.55.11
[nvram 2] hwver = R8500
[nvram 3] friendly_name = R8300
[nvram 4] upnp_enable = 1
[nvram 5] upnp_turn_on = 1
[nvram 6] upnp_advert_period = 30
[nvram 7] upnp_advert_ttl = 4
[nvram 8] upnp_portmap_entry = 1
[nvram 9] upnp_duration = 3600
[nvram 10] upnp_DHCPServerConfigurable = 1
[nvram 11] wps_is_upnp = 0
[nvram 12] upnp_sa_uuid = 00000000000000000000
[nvram 13] lan_hwaddr = AA:BB:CC:DD:EE:FF
[nvram 14] lan_hwaddr = 
Read 15 entries from /tmp/nvram.ini
acosNvramConfig_get('upnpd_debug_level') = '9'
[0x0002652c] acosNvramConfig_get('upnpd_debug_level') = '9'
set_value_to_org_xml:1149()
[0x0000e1e8] fopen('/www/Public_UPNP_gatedesc.xml', 'rb') = 0x000e4008
[0x0000e220] fopen('/tmp/upnp_xml', 'wb+') = 0x000e4008
data2XML()
[0x0000f520] acosNvramConfig_get('lan_ipaddr') = '10.211.55.11'
xmlValueConvert()
[0xff691838] acosNvramConfig_get('hwrev') = ''
[0x0000b40c] acosNvramConfig_get('hwver') = 'R8500'
[0x0000b428] acosNvramConfig_get('hwver') = 'R8500'
[0xff691838] acosNvramConfig_get('hwrev') = ''
[0x0000b478] acosNvramConfig_get('hwver') = 'R8500'
[0x0000b494] acosNvramConfig_get('hwver') = 'R8500'
[0x0000f4ec] acosNvramConfig_get('friendly_name') = 'R8300'
xmlValueConvert()
[0x0000f4b0] acosNvramConfig_get('friendly_name') = 'R8300'
xmlValueConvert()
[0xff691838] acosNvramConfig_get('hwrev') = ''
[0xff6917f4] acosNvramConfig_match('hwver', 'R8500') = 1
xmlValueConvert()
[0x0000f014] acosNvramConfig_get('friendly_name') = 'R8300'
xmlValueConvert()
[0xff691838] acosNvramConfig_get('hwrev') = ''
[0x00026b0c] acosNvramConfig_get('hwver') = 'R8500'
[0xff6917f4] acosNvramConfig_match('hwver', 'R8500') = 1
xmlValueConvert()
[0xff692b64] open('/dev/mtdblock4', 0) = -1
open: No such file or directory
xmlValueConvert()
upnp_uuid_generator:421()
[0x0000da1c] acosNvramConfig_get('lan_hwaddr') = 'AA:BB:CC:DD:EE:FF'
upnp_uuid_generator:421()
[0x0000da1c] acosNvramConfig_get('lan_hwaddr') = 'AA:BB:CC:DD:EE:FF'
xmlValueConvert()
[0x0000f47c] acosNvramConfig_get('lan_ipaddr') = '10.211.55.11'
xmlValueConvert()
[0x0000f4b0] acosNvramConfig_get('friendly_name') = 'R8300'
xmlValueConvert()
[0xff691838] acosNvramConfig_get('hwrev') = ''
[0xff6917f4] acosNvramConfig_match('hwver', 'R8500') = 1
xmlValueConvert()
[0x0000f014] acosNvramConfig_get('friendly_name') = 'R8300'
xmlValueConvert()
[0xff691838] acosNvramConfig_get('hwrev') = ''
[0x00026b0c] acosNvramConfig_get('hwver') = 'R8500'
[0xff6917f4] acosNvramConfig_match('hwver', 'R8500') = 1
xmlValueConvert()
[0xff692b64] open('/dev/mtdblock4', 0) = -1
open: No such file or directory
xmlValueConvert()
upnp_uuid_generator:421()
[0x0000da1c] acosNvramConfig_get('lan_hwaddr') = 'AA:BB:CC:DD:EE:FF'
upnp_uuid_generator:421()
[0x0000da1c] acosNvramConfig_get('lan_hwaddr') = 'AA:BB:CC:DD:EE:FF'
xmlValueConvert()
[0x0000f47c] acosNvramConfig_get('lan_ipaddr') = '10.211.55.11'
xmlValueConvert()
[0x0000f4b0] acosNvramConfig_get('friendly_name') = 'R8300'
xmlValueConvert()
[0xff691838] acosNvramConfig_get('hwrev') = ''
[0xff6917f4] acosNvramConfig_match('hwver', 'R8500') = 1
xmlValueConvert()
[0x0000f014] acosNvramConfig_get('friendly_name') = 'R8300'
xmlValueConvert()
[0xff691838] acosNvramConfig_get('hwrev') = ''
[0x00026b0c] acosNvramConfig_get('hwver') = 'R8500'
[0xff6917f4] acosNvramConfig_match('hwver', 'R8500') = 1
xmlValueConvert()
[0xff692b64] open('/dev/mtdblock4', 0) = -1
open: No such file or directory
xmlValueConvert()
upnp_uuid_generator:421()
[0x0000da1c] acosNvramConfig_get('lan_hwaddr') = 'AA:BB:CC:DD:EE:FF'
upnp_uuid_generator:421()
[0x0000da1c] acosNvramConfig_get('lan_hwaddr') = 'AA:BB:CC:DD:EE:FF'
xmlValueConvert()
[0x0000f47c] acosNvramConfig_get('lan_ipaddr') = '10.211.55.11'
xmlValueConvert()
parse_root_device_description:619()
[0x0000ce5c] fopen('/tmp/upnp_xml', 'rb') = 0x000e4008
findtok:519()
parse_root_device_description:644(), findtok(URLBase)
parse_root_device_description:681(), device_type0 = InternetGatewayDevice
findtok:519()
parse_root_device_description:752(), findtok(SCPDURL)
parse_root_device_description:780(): find EventSub URL
parse_root_device_description:795(): find </service>
parse_root_device_description:806(): assign the rest value of the service structure
[0x0000d3b4] acosNvramConfig_get('upnp_duration') = '3600'
parse_root_device_description:836(): assign the rest value of the device structure
[0x0000d454] acosNvramConfig_get('upnp_duration') = '3600'
emb_num = 0, max_layer = 1, layer = 1parse_root_device_description:687(), device_type0 = WANDevice
findtok:519()
parse_root_device_description:752(), findtok(SCPDURL)
parse_root_device_description:780(): find EventSub URL
parse_root_device_description:795(): find </service>
parse_root_device_description:806(): assign the rest value of the service structure
[0x0000d568] acosNvramConfig_get('upnp_duration') = '3600'
parse_root_device_description:836(): assign the rest value of the device structure
[0x0000d664] acosNvramConfig_get('upnp_duration') = '3600'
emb_num = 1, max_layer = 2, layer = 2parse_root_device_description:687(), device_type1 = WANConnectionDevice
findtok:519()
parse_root_device_description:752(), findtok(SCPDURL)
parse_root_device_description:780(): find EventSub URL
parse_root_device_description:795(): find </service>
parse_root_device_description:806(): assign the rest value of the service structure
[0x0000d568] acosNvramConfig_get('upnp_duration') = '3600'
findtok:519()
parse_root_device_description:752(), findtok(SCPDURL)
parse_root_device_description:780(): find EventSub URL
parse_root_device_description:795(): find </service>
parse_root_device_description:806(): assign the rest value of the service structure
[0x0000d568] acosNvramConfig_get('upnp_duration') = '3600'
findtok:519()
parse_root_device_description:752(), findtok(SCPDURL)
parse_root_device_description:780(): find EventSub URL
parse_root_device_description:795(): find </service>
parse_root_device_description:806(): assign the rest value of the service structure
[0x0000d568] acosNvramConfig_get('upnp_duration') = '3600'
parse_root_device_description:836(): assign the rest value of the device structure
[0x0000d664] acosNvramConfig_get('upnp_duration') = '3600'
emb_num = 2, max_layer = 3, layer = 3[0x00026504] [nvram 8] acosNvramConfig_set('upnp_portmap_entry', '0')
upnp_main:751()
[0x0001d084] acosNvramConfig_match('upnp_turn_on', '1') = 1
upnp_main: 763()
[0x0001d0a8] acosNvramConfig_match('lan_ipaddr', '0.0.0.0') = 0
create_received_scoket:158()
upnp_sockeInit:964()
[0x0001c4c4] acosNvramConfig_get('lan_ipaddr') = '10.211.55.11'
create_submit_scoket: 199()
create_received_scoket:158()
upnp_sockeInit:964()
get_if_addr(946): Can't get IP from br0.
[0x0001d16c] acosNvramConfig_get('upnp_duration') = '3600'
upnp_duration is 3600
ssdp_discovery_advertisement(568):
rootDeviceOK(68):
ssdp_discovery_send(511):
ssdp_root_device_discovery_send(244):
igd_ssdp_root_device_discovery(84)
ssdp_packet(98):
[0x000247bc] acosNvramConfig_get('upnp_duration') = '3600'
http_mu_send:1041()
[0x0001dac8] acosNvramConfig_get('upnp_advert_ttl') = '4'
[0x0001dafc] acosNvramConfig_get('lan_ipaddr') = '10.211.55.11'
Unsupported setsockopt level=0 optname=32
UPNP: error to use LAN IP to be the interface of sending mulitcast datagram!
ssdp_UUID_discovery_send(477):
igd_ssdp_UUID_discovery(100)
ssdp_packet(98):
[0x000247bc] acosNvramConfig_get('upnp_duration') = '3600'
http_mu_send:1041()
[0x0001dac8] acosNvramConfig_get('upnp_advert_ttl') = '4'
[0x0001dafc] acosNvramConfig_get('lan_ipaddr') = '10.211.55.11'
Unsupported setsockopt level=0 optname=32
UPNP: error to use LAN IP to be the interface of sending mulitcast datagram!
ssdp_schemas_discovery_send(495):
igd_ssdp_schemas_discovery(125)
ssdp_packet(98):
[0x000247bc] acosNvramConfig_get('upnp_duration') = '3600'
http_mu_send:1041()
[0x0001dac8] acosNvramConfig_get('upnp_advert_ttl') = '4'
[0x0001dafc] acosNvramConfig_get('lan_ipaddr') = '10.211.55.11'
Unsupported setsockopt level=0 optname=32
UPNP: error to use LAN IP to be the interface of sending mulitcast datagram!
[0x0001d1a0] acosNvramConfig_get('upnp_advert_period') = '30'
[0x0001d200] acosNvramConfig_match('upnp_turn_on', '1') = 1
```
看起来是启动了，upnp的服务为1900端口：
![45.png](https://www.iotsec-zone.com/images/MdImg/6c414242d3dc1da380e9be0c99e03b6f.png)
因为该版本的upnp有Stack Overflow，尝试着让其崩溃：

```c
import socket

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(('10.211.55.11', 1900))               
s.send(0x1000*b'a')
s.close()          
```
![46.png](https://www.iotsec-zone.com/images/MdImg/ce00540a19b4f6e763e52a95d843fb80.png)
![47.png](https://www.iotsec-zone.com/images/MdImg/9bf3b0d9a554f753d8faa28c2d0cda26.png)
程序崩溃，成功！
②、使用libnvram
正常模拟
下面我们使用firmadyne的libnvram进行hook，整个过程可能有“亿点点”波折...
● [https://github.com/firmadyne/libnvram（git](https://github.com/firmadyne/libnvram（git) clone [https://github.com/firmadyne/libnvram.git](https://github.com/firmadyne/libnvram.git)）
![48.png](https://www.iotsec-zone.com/images/MdImg/e929096e3cc95a0399c14268c84f4f4b.png)
你可别见到Makefile就直接make，直接make编译出来的是x86的：
![49.png](https://www.iotsec-zone.com/images/MdImg/6f6679ff989736e53d46500edb1fe812.png)
但是我们可以得到编译该动态链接库的命令：
1. 【编译器】 -c -O2 -fPIC -Wall nvram.c -o nvram.o
2. 【编译器】 -shared -nostdlib nvram.o -o libnvram.so
现在我们直接编译，挂载到固件中看会出现什么错误：
1. cd /home/cyberangel/Desktop/
2. export LD_LIBRARY_PATH="$PWD/hndtools-arm-linux-2.6.36-uclibc-4.5.3/lib"
3. ./hndtools-arm-linux-2.6.36-uclibc-4.5.3/bin/arm-uclibc-gcc -c -O2 -fPIC -Wall /home/cyberangel/Desktop/模拟固件下的patch与hook/Netgear_R8300/libnvram-master/nvram.c -o /home/cyberangel/Desktop/模拟固件下的patch与hook/Netgear_R8300/libnvram-master/firmadyne_nvram.o
4. ./hndtools-arm-linux-2.6.36-uclibc-4.5.3/bin/arm-uclibc-gcc -shared -nostdlib /home/cyberangel/Desktop/模拟固件下的patch与hook/Netgear_R8300/libnvram-master/firmadyne_nvram.o -o /home/cyberangel/Desktop/模拟固件下的patch与hook/Netgear_R8300/libnvram-master/firmadyne_libnvram.so
![50.png](https://www.iotsec-zone.com/images/MdImg/1aa493241693772ce55d0c92ff3866c4.png)
当出现隐式声明函数时，并且这个函数又是GNU标准实现的函数的话，在编译libnvram时可能会出现警告；比如warning: implicit declaration of function ‘strndup’。可以试着将如下宏定义到加到nvram.c开头就能解决警告的问题了：

```c
#define _GNU_SOURCE
```
![51.png](https://www.iotsec-zone.com/images/MdImg/5fc9851e1723018013e6ad5d0e8e166d.png)
不会再出现警告
运行一下看会出现什么报错：sudo chroot . ./qemu-arm-static -E LD_PRELOAD="/firmadyne_libnvram.so" ./usr/sbin/upnpd
![52.png](https://www.iotsec-zone.com/images/MdImg/a3f201e106f59917b0422782db499ee0.png)
报了两种错误：
● nvram_init: Unable to mount tmpfs on mount point /firmadyne/libnvram/!
● qemu: uncaught target signal 11 (Segmentation fault) - core dumped
第一种错误是由于nvram.c的nvram_init函数导致的：

```c
int nvram_init(void) {
    // ...(代码省略)
    if (mount("tmpfs", MOUNT_POINT, "tmpfs", MS_NOEXEC | MS_NOSUID | MS_SYNCHRONOUS, "") == -1) {
        sem_unlock();
        PRINT_MSG("Unable to mount tmpfs on mount point %s!\n", MOUNT_POINT);
        return E_FAILURE;
    }
    // ...(代码省略)
    return nvram_set_default();
}
```
需要我们手动创建/firmadyne/libnvram文件夹并将tmpfs内存虚拟硬盘挂载到文件系统的/firmadyne/libnvram目录下：
● mkdir -p ./firmadyne/libnvram
● sudo mount -t tmpfs -o size=10M tmpfs ./firmadyne/libnvram
再次执行，我摘取了其中一部分的日志，如下面代码框所示：
```c
cyberangel@cyberangel:~/Desktop/模拟固件下的patch与hook/Netgear_R8300/_R8300-V1.0.2.130_1.0.99.chk.extracted/squashfs-root$ nvram_get_buf: upnpd_debug_level
sem_lock: Triggering NVRAM initialization!
nvram_init: Initializing NVRAM...
...
nvram_get_buf: Unable to open key: /firmadyne/libnvram/upnpd_debug_level!
qemu: uncaught target signal 11 (Segmentation fault) - core dumped

cyberangel@cyberangel:~/Desktop/模拟固件下的patch与hook/Netgear_R8300/_R8300-V1.0.2.130_1.0.99.chk.extracted/squashfs-root$ 
```
由于路由器固件在模拟启动时缺少upnpd_debug_level参数，导致程序崩溃，看来还是需要像nvram-faker一样配置一些参数才行，对libnvram的config.h文件中NVRAM_DEFAULTS宏定义进行配置：

**此处的完整log(查看附件《第一次hook日志》）**

![53.png](https://www.iotsec-zone.com/images/MdImg/f7870061b0bd8bb6b32b8f83219aed66.png)

根据nvram-faker的nvram.ini修改为：

```c
// Default values for NVRAM.
#define NVRAM_DEFAULTS \
    /* Linux kernel log level, used by "WRT54G3G_2.11.05_ETSI_code.bin" (305) */ \
    ENTRY("console_loglevel", nvram_set, "7") \
    /* Reset NVRAM to default at bootup, used by "WNR3500v2-V1.0.2.10_23.0.70NA.chk" (1018) */ \
    ENTRY("restore_defaults", nvram_set, "1") \
    ENTRY("sku_name", nvram_set, "") \
    ENTRY("wla_wlanstate", nvram_set, "") \
    ENTRY("lan_if", nvram_set, "br0") \
    ENTRY("lan_ipaddr", nvram_set, "192.168.0.50") \
    ENTRY("lan_bipaddr", nvram_set, "192.168.0.255") \
    ENTRY("lan_netmask", nvram_set, "255.255.255.0") \
    /* Set default timezone, required by multiple images */ \
    ENTRY("time_zone", nvram_set, "EST5EDT") \
    /* Set default WAN MAC address, used by "NBG-416N_V1.00(USA.7)C0.zip" (12786) */ \
    ENTRY("wan_hwaddr_def", nvram_set, "01:23:45:67:89:ab") \
    /* Attempt to define LAN/WAN interfaces */ \
    ENTRY("wan_ifname", nvram_set, "eth0") \
    ENTRY("lan_ifnames", nvram_set, "eth1 eth2 eth3 eth4") \
    /* Used by "TEW-638v2%201.1.5.zip" (12898) to prevent crash in 'goahead' */ \
    ENTRY("ethConver", nvram_set, "1") \
    /* Used by "Firmware_TEW-411BRPplus_2.07_EU.zip" (13649) to prevent crash in 'init' */ \
    ENTRY("lan_proto", nvram_set, "dhcp") \
    ENTRY("wan_ipaddr", nvram_set, "0.0.0.0") \
    ENTRY("wan_netmask", nvram_set, "255.255.255.0") \
    ENTRY("wanif", nvram_set, "eth0") \
    /* Used by "DGND3700 Firmware Version 1.0.0.17(NA).zip" (3425) to prevent crashes */ \
    ENTRY("time_zone_x", nvram_set, "0") \
    ENTRY("rip_multicast", nvram_set, "0") \
    ENTRY("bs_trustedip_enable", nvram_set, "0")\
    /* For Netgear R8300 Router  -- Written By Cyberangel */ \
    ENTRY("upnpd_debug_level", nvram_set, "9")\
    ENTRY("lan_ipaddr", nvram_set, "10.211.55.11")\
    ENTRY("hwver", nvram_set, "R8500")\
    ENTRY("friendly_name", nvram_set, "R8300")\
    ENTRY("upnp_enable", nvram_set, "1")\
    ENTRY("upnp_turn_on", nvram_set, "1")\
    ENTRY("upnp_advert_period", nvram_set, "30")\
    ENTRY("upnp_advert_ttl", nvram_set, "4")\
    ENTRY("upnp_portmap_entry", nvram_set, "1")\
    ENTRY("upnp_duration", nvram_set, "3600")\
    ENTRY("upnp_DHCPServerConfigurable", nvram_set, "1")\
    ENTRY("wps_is_upnp", nvram_set, "0")\
    ENTRY("upnp_sa_uuid", nvram_set, "00000000000000000000")\
    ENTRY("lan_hwaddr", nvram_set, "AA:BB:CC:DD:EE:FF")\
    
#endif
        
/*
    upnpd_debug_level=9
    lan_ipaddr=10.211.55.11
    hwver=R8500
    friendly_name=R8300
    upnp_enable=1
    upnp_turn_on=1
    upnp_advert_period=30
    upnp_advert_ttl=4
    upnp_portmap_entry=1
    upnp_duration=3600
    upnp_DHCPServerConfigurable=1
    wps_is_upnp=0
    upnp_sa_uuid=00000000000000000000
    lan_hwaddr=AA:BB:CC:DD:EE:FF
*/ 
```
重新编译后运行（注意下面命令中的文件名与之前的不同）：

```c
$ cd /home/cyberangel/Desktop/
$ export LD_LIBRARY_PATH="$PWD/hndtools-arm-linux-2.6.36-uclibc-4.5.3/lib"
$ ./hndtools-arm-linux-2.6.36-uclibc-4.5.3/bin/arm-uclibc-gcc -c -O2 -fPIC -Wall /home/cyberangel/Desktop/模拟固件下的patch与hook/Netgear_R8300/libnvram-master/nvram.c -o /home/cyberangel/Desktop/模拟固件下的patch与hook/Netgear_R8300/libnvram-master/firmadyne_nvram_version_1.o
$ ./hndtools-arm-linux-2.6.36-uclibc-4.5.3/bin/arm-uclibc-gcc -shared -nostdlib /home/cyberangel/Desktop/模拟固件下的patch与hook/Netgear_R8300/libnvram-master/firmadyne_nvram_version_1.o -o /home/cyberangel/Desktop/模拟固件下的patch与hook/Netgear_R8300/libnvram-master/firmadyne_libnvram_version_1.so
```
![54.png](https://www.iotsec-zone.com/images/MdImg/c36599bb70bd2eaaaa5027b6b80d94c6.png)

**此处的完整log（查看附件《第二次hook日志》）**

嗯？为什么还是缺少文件，这不应该啊，前面的nvram-faker都没有报错啊？注意到日志中对每一个变量的hook都有如下规律：
![55.png](https://www.iotsec-zone.com/images/MdImg/62964db9d220b68bfe5faf071882d514.png)
根据Setting built-in default values!我们能找到libnvram的关键hook代码：
![56.png](https://www.iotsec-zone.com/images/MdImg/08ed801da5a3b88d7bd60dea1b8cecac.png)
宏定义ENTRY就是我们自定义的的如ENTRY("upnpd_debug_level", nvram_set, "9")，就相当于nvram_set("upnpd_debug_level", "9")了：
![57.png](https://www.iotsec-zone.com/images/MdImg/c9056db53140d2ebb521a9a85008cc58.png)
从上面代码中可以看出，当我们没有设置某一个值时会打印出错误提示，然后返回E_FAILURE（#define E_FAILURE  0），最后任由程序崩溃不做任何处理。再来看nvram-faker的处理：
![58.png](https://www.iotsec-zone.com/images/MdImg/b815ac1bb2340f711aefe425ac78741b.png)
找不到就直接设置为了空字符串可还行，对应的代码为：
![59.png](https://www.iotsec-zone.com/images/MdImg/240c12b9b6cbf2292f73747c0fd1f744.png)
相较而言两种方式互有优劣，nvram-fake找不到字符串就设置为""，这样有可能导致漏掉一些重要的参数，重新配置时只需要更改nvram.ini即可；libnvram找不到参数就崩溃（崩溃的前提是被hook的程序不做任何处理），每一个参数都得自己设置并重新编译so文件，还是自己决定用哪种方式吧...
得，老老实实添加hwrev参数吧：
![60.png](https://www.iotsec-zone.com/images/MdImg/eae51014be7063ca4d87f3c3c92361d2.png)
重新编译（firmadyne_nvram_version_2.so）：

```c
$ cd /home/cyberangel/Desktop/
$ export LD_LIBRARY_PATH="$PWD/hndtools-arm-linux-2.6.36-uclibc-4.5.3/lib"
$ ./hndtools-arm-linux-2.6.36-uclibc-4.5.3/bin/arm-uclibc-gcc -c -O2 -fPIC -Wall /home/cyberangel/Desktop/模拟固件下的patch与hook/Netgear_R8300/libnvram-master/nvram.c -o /home/cyberangel/Desktop/模拟固件下的patch与hook/Netgear_R8300/libnvram-master/firmadyne_nvram_version_2.o
$ ./hndtools-arm-linux-2.6.36-uclibc-4.5.3/bin/arm-uclibc-gcc -shared -nostdlib /home/cyberangel/Desktop/模拟固件下的patch与hook/Netgear_R8300/libnvram-master/firmadyne_nvram_version_2.o -o /home/cyberangel/Desktop/模拟固件下的patch与hook/Netgear_R8300/libnvram-master/firmadyne_libnvram_version_2.so
```
执行sudo chroot . ./qemu-arm-static -E LD_PRELOAD="/firmadyne_libnvram_version_2.so" ./usr/sbin/upnpd，有：
![61.png](https://www.iotsec-zone.com/images/MdImg/54f6469a4981a4f23b0d46ce8a9df1c0.png)

**此处的完整log（查看附件《第三次hook日志》）**

这咋还是报错呢？而且报了一个nvram从来没有出现过的错误。注意到上图中lan_ipaddr的值似乎是192.168.1.1？确认下：
![62.png](https://www.iotsec-zone.com/images/MdImg/3de1ceb02ff624b6d9977faa99edadb1.png)
？？？，怎么被设置为这个ip了？另外为什么会有这么多文件：
![63.png](https://www.iotsec-zone.com/images/MdImg/10951382b95b11785023cb8b30362039.png)

**此处的完整log（查看附件《libnvram文件夹下所有的文件(ls -al)》）**

算了，先不管了，将电脑ip设置为192.168.1.1（拍摄快照）
![64.png](https://www.iotsec-zone.com/images/MdImg/e8799cee07a798a8790ae01d5f1e8eda.png)
sudo ifconfig enp0s5 192.168.1.1/24：
![65.png](https://www.iotsec-zone.com/images/MdImg/bed8aa76b217c7dbb27e1539bfb54c09.png)
再次执行sudo chroot . ./qemu-arm-static -E LD_PRELOAD="/firmadyne_libnvram_version_2.so" ./usr/sbin/upnpd：
![66.png](https://www.iotsec-zone.com/images/MdImg/d0b4a06edd71fd45a2d4b108d9ec32c7.png)

此处的完整log（查看附件《第四次hook日志》）

似乎是成功了，进行验证：
![67.png](https://www.iotsec-zone.com/images/MdImg/1dc9f7bd19cdbe5e9814b5fca4468eda.png)
同样来一下exp：

```c
import socket

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(('192.168.1.1', 1900))         # 改ip为192.168.1.1
s.send(0x1000*b'a')
s.close()          
```
![68.png](https://www.iotsec-zone.com/images/MdImg/a7544210ab6fcf03e49a0e689d2863a5.png)
恢复刚才备份的快照，下面我们来钻研一下问题的根因。
**研究问题**
我一开始想的是是不是环境变量的传递出现了问题，导致LD_PRELOAD的hook失败，但是考虑到前面我们已经见到了libnvram的部分变量的成功，肯定不是这个问题。经过我一番摸索，将firmadyne_libnvram_version_2.so重命名为libnvram.so并移动到到/usr/lib/目录下（记得将原来的/usr/lib/libnvram.so备份），再次尝试：

```c
$ sudo chroot . ./qemu-arm-static ./usr/sbin/upnpd
```
![69.png](https://www.iotsec-zone.com/images/MdImg/f5273887ddaa599d741803d085bb28c8.png)

**此处的完整log（查看附件《第五次hook日志》）**

启动成功了，现在我们将范围缩小到了LD_PRELOAD和libnvram的身上，但究竟是谁的问题？正好，qemu有自带的strace功能，在第五次hook的基础上我们将命令改为：

```c
$ sudo chroot . ./qemu-arm-static ./usr/sbin/upnpd
```
**此处的完整log（查看附件《第六次hook日志》）**

kill掉该进程后，将原版的libnvram换回去，执行：

```c
$ sudo chroot . ./qemu-arm-static -E LD_PRELOAD=/firmadyne_libnvram_version_2.so ./usr/sbin/upnpd
```

**此处的完整log（查看附件《第七次hook日志》）**

第七次的hook日志要比第六次的长很多，使用vscode比较发现，前半部分和后半部分执行结果基本上相同：
![70.png](https://www.iotsec-zone.com/images/MdImg/30c10f9421862a6328eedadd696e82b6.png)
前半部分
![71.png](https://www.iotsec-zone.com/images/MdImg/052d988d63e4c73b1925b1cc2e99ecdd.png)
后半部分
但是中间却缺失了一大片：
![72.png](https://www.iotsec-zone.com/images/MdImg/cdf90d13f523a60f33ad39ece2c6b0e9.png)
我们可以得出几个结论：
1. LD_PRELOAD加载的libnvram的确是hook成功了
2. hook着hook着就从firmadyne_libnvram_version_2.so跑到了/usr/lib/libnvram.so了，最后又回到了firmadyne_libnvram_version_2.so：
![73.png](https://www.iotsec-zone.com/images/MdImg/86e75053007d1dc297977091f4fb1484.png)
![74.png](https://www.iotsec-zone.com/images/MdImg/ff8998d8af68574320902cba0fc825e3.png)
再说了，我都指定动态链接库了，程序怎么会跑到原有的动态链接库身上？？？
到此处我下定决心调试一下upnpd运行的全过程：

```c
$ sudo chroot . ./qemu-arm-static -g 1234 -E LD_PRELOAD=/firmadyne_libnvram_version_2.so ./usr/sbin/upnpd
```
![75.png](https://www.iotsec-zone.com/images/MdImg/1f637aafb1c769cfee73656fe70e3e3d.png)
当程序执行完main的daemon函数后，程序就会直接跑飞，我们将该函数NOP掉：
![76.png](https://www.iotsec-zone.com/images/MdImg/497853842f9bef6cf428e793d6724595.png)
绿色部分的指令需要全部被NOP
![77.png](https://www.iotsec-zone.com/images/MdImg/ed8c4c1612da98ef1bc4d173846eefd6.png)
NOP之后
导出为可执行文件，将原来的upnpd备份后替换，重新调试：
![78.png](https://www.iotsec-zone.com/images/MdImg/bac48ade7dfb4ee76a584c275836de9a.png)
单步过该函数之后发现程序已经执行完了原来的libnvram，看来问题出在了acosNvramConfig_get：
![79.png](https://www.iotsec-zone.com/images/MdImg/6fd97ac792f18760361005b307ba2476.png)
对应到了libnvram源码中的alias.c:
![80.png](https://www.iotsec-zone.com/images/MdImg/89fafc9b0596d731d2cbaea3e838c56b.png)
开始调用该函数的地址为0x26484：
![81.png](https://www.iotsec-zone.com/images/MdImg/f78eaf860aa3568252a9f6a07604ee7d.png)
为了直观，尝试采用gdb调试：gdb-multiarch -x ./gdb_script

```c
file ./_R8300-V1.0.2.130_1.0.99.chk.extracted/squashfs-root/firmadyne_libnvram_version_2.so
b *0x26484
target remote :1234
c
```
进入该函数中执行到upnpd的plt表，解析函数真实地址：
![82.png](https://www.iotsec-zone.com/images/MdImg/3676fb19b136ede51a219c3d7b93ce4b.png)
两者机器码相同
我尝试着使用gdb调试，但是一旦进入到其他的动态链接库文件中就很容易迷失方向（IDA甚至连指令都无法显示），并且虽然可以直接对某个指定的函数下断点，但是似乎是由于qemu的原因并断不下来。换一种思路，因为多出来了的日志处于nvram_set_default: Checking for symbol "router_defaults"...与Loading from native built-in table之间，如下面两张图所示：
![83.png](https://www.iotsec-zone.com/images/MdImg/071658edcdbbdfcfc4f8e20a19a570ce.png)
![84.png](https://www.iotsec-zone.com/images/MdImg/14f20550d4d1bdfe460799f1c021d1bd.png)
定位到源码：
![85.png](https://www.iotsec-zone.com/images/MdImg/a608a2c7919fefba58dd6ea5b9e947c5.png)
看来似乎是nvram_set_default_table函数的问题，进入其中，插入第631行的代码，我们来看看数组tbl是什么东西：
![86.png](https://www.iotsec-zone.com/images/MdImg/02df7280bb2b33fb43a5ed1a45ff1188.png)
重新编译：

```c
$ cd /home/cyberangel/Desktop/
$ export LD_LIBRARY_PATH="$PWD/hndtools-arm-linux-2.6.36-uclibc-4.5.3/lib"
$ ./hndtools-arm-linux-2.6.36-uclibc-4.5.3/bin/arm-uclibc-gcc -c -O2 -fPIC -Wall /home/cyberangel/Desktop/模拟固件下的patch与hook/Netgear_R8300/libnvram-master/nvram.c -o /home/cyberangel/Desktop/模拟固件下的patch与hook/Netgear_R8300/libnvram-master/firmadyne_nvram_version_3.o
$ ./hndtools-arm-linux-2.6.36-uclibc-4.5.3/bin/arm-uclibc-gcc -shared -nostdlib /home/cyberangel/Desktop/模拟固件下的patch与hook/Netgear_R8300/libnvram-master/firmadyne_nvram_version_3.o -o /home/cyberangel/Desktop/模拟固件下的patch与hook/Netgear_R8300/libnvram-master/firmadyne_libnvram_version_3.so
```
执行：sudo chroot . ./qemu-arm-static -E LD_PRELOAD=/firmadyne_libnvram_version_3.so ./usr/sbin/upnpd

**此处的完整log（查看附件《第八次hook日志》）**

注意日志中有：
![87.png](https://www.iotsec-zone.com/images/MdImg/c43ac075010c247e3c4f85dd01e6f1cd.png)
哦，原来那个数组是存放对于我们来说"多余"的值的（比如os_name）【这不是废话吗？看到了上面图中第632行的nvram_set函数了吗...】。看来问题就出现在这里。根据router_defaults字符串，关于它在源码中只有一处，即在config.h中：
![88.png](https://www.iotsec-zone.com/images/MdImg/751ee81af70a105c187d966821861778.png)
因为该动态链接库中没有定义该变量，却在运行时能打印出来，它一定是从外部引入的。经过一番寻找在原版的libnvram.so中发现：
![89.png](https://www.iotsec-zone.com/images/MdImg/0ee2436013f0966bbb7dc5a5d664d215.png)
绝，难怪会导致问题，因为router_defaults在原版的libnvram.so中被定义出导出，虽然我们hook了该动态链接库，但是我们的so文件中未定义router_defaults，所以程序会尝试去其他动态链接库（包括原版的libnvram.so）中寻找使用：
![90.png](https://www.iotsec-zone.com/images/MdImg/a1d0fbea1bab08bb4de1eb0ae2dc5add.png)
要想解决这个问题，只需要将TABLE(router_defaults)这一行代码删掉即可：
![91.png](https://www.iotsec-zone.com/images/MdImg/05ed6b2ac2b9c0ffe8af6083588ef6d7.png)
重新编译：

```c
$ cd /home/cyberangel/Desktop/
$ export LD_LIBRARY_PATH="$PWD/hndtools-arm-linux-2.6.36-uclibc-4.5.3/lib"
$ ./hndtools-arm-linux-2.6.36-uclibc-4.5.3/bin/arm-uclibc-gcc -c -O2 -fPIC -Wall /home/cyberangel/Desktop/模拟固件下的patch与hook/Netgear_R8300/libnvram-master/nvram.c -o /home/cyberangel/Desktop/模拟固件下的patch与hook/Netgear_R8300/libnvram-master/firmadyne_nvram_version_4.o
$ ./hndtools-arm-linux-2.6.36-uclibc-4.5.3/bin/arm-uclibc-gcc -shared -nostdlib /home/cyberangel/Desktop/模拟固件下的patch与hook/Netgear_R8300/libnvram-master/firmadyne_nvram_version_4.o -o /home/cyberangel/Desktop/模拟固件下的patch与hook/Netgear_R8300/libnvram-master/firmadyne_libnvram_version_4.so
```
`sudo chroot . ./qemu-arm-static -E LD_PRELOAD=/firmadyne_libnvram_version_4.so ./usr/sbin/upnpd`

```c
cyberangel@cyberangel:~/Desktop/模拟固件下的patch与hook/Netgear_R8300/_R8300-V1.0.2.130_1.0.99.chk.extracted/squashfs-root$ sudo chroot . ./qemu-arm-static -E LD_PRELOAD=/firmadyne_libnvram_version_4.so ./usr/sbin/upnpd
[sudo] password for cyberangel: 
nvram_get_buf: upnpd_debug_level
sem_lock: Triggering NVRAM initialization!
nvram_init: Initializing NVRAM...
sem_get: Key: 41420002
sem_get: Key: 41430002
Cyberangel tells you: nvram_set_default is 0xff7d2e18
nvram_set_default_builtin: Setting built-in default values!
nvram_set: console_loglevel = "7"
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_set: restore_defaults = "1"
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_set: sku_name = ""
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_set: wla_wlanstate = ""
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_set: lan_if = "br0"
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_set: lan_ipaddr = "192.168.0.50"
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_set: lan_bipaddr = "192.168.0.255"
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_set: lan_netmask = "255.255.255.0"
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_set: time_zone = "EST5EDT"
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_set: wan_hwaddr_def = "01:23:45:67:89:ab"
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_set: wan_ifname = "eth0"
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_set: lan_ifnames = "eth1 eth2 eth3 eth4"
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_set: ethConver = "1"
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_set: lan_proto = "dhcp"
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_set: wan_ipaddr = "0.0.0.0"
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_set: wan_netmask = "255.255.255.0"
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_set: wanif = "eth0"
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_set: time_zone_x = "0"
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_set: rip_multicast = "0"
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_set: bs_trustedip_enable = "0"
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_set: upnpd_debug_level = "9"
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_set: lan_ipaddr = "10.211.55.11"
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_set: hwver = "R8500"
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_set: friendly_name = "R8300"
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_set: upnp_enable = "1"
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_set: upnp_turn_on = "1"
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_set: upnp_advert_period = "30"
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_set: upnp_advert_ttl = "4"
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_set: upnp_portmap_entry = "1"
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_set: upnp_duration = "3600"
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_set: upnp_DHCPServerConfigurable = "1"
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_set: wps_is_upnp = "0"
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_set: upnp_sa_uuid = "00000000000000000000"
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_set: lan_hwaddr = "AA:BB:CC:DD:EE:FF"
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_set: lan_hwaddr = "AA:BB:CC:DD:EE:FF"
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_set: hwrev = ""
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_set_default: Loading built-in default values = 1!
nvram_set_default: Checking for symbol "Nvrams"...
nvram_set_default_image: Copying overrides from defaults folder!
sem_get: Key: 41430002
sem_get: Key: 41430002
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "9"
nvram_get_buf: upnpd_debug_level
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "9"
set_value_to_org_xml:1149()
data2XML()
nvram_invmatch: upnp_turn_on ~?= "1"
nvram_get_buf: upnp_turn_on
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "1"
nvram_match: upnp_turn_on (1) ?= "1"
nvram_match: true
nvram_invmatch: upnp_turn_on ~?= "1"
nvram_get_buf: upnp_turn_on
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "1"
nvram_match: upnp_turn_on (1) ?= "1"
nvram_match: true
nvram_get_buf: lan_ipaddr
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "10.211.55.11"
xmlValueConvert()
nvram_invmatch: upnp_turn_on ~?= "1"
nvram_get_buf: upnp_turn_on
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "1"
nvram_match: upnp_turn_on (1) ?= "1"
nvram_match: true
nvram_get_buf: hwrev
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = ""
nvram_get_buf: hwver
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "R8500"
nvram_get_buf: hwver
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "R8500"
nvram_get_buf: hwrev
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = ""
nvram_get_buf: hwver
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "R8500"
nvram_get_buf: hwver
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "R8500"
nvram_invmatch: upnp_turn_on ~?= "1"
nvram_get_buf: upnp_turn_on
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "1"
nvram_match: upnp_turn_on (1) ?= "1"
nvram_match: true
nvram_get_buf: friendly_name
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "R8300"
xmlValueConvert()
nvram_invmatch: upnp_turn_on ~?= "1"
nvram_get_buf: upnp_turn_on
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "1"
nvram_match: upnp_turn_on (1) ?= "1"
nvram_match: true
nvram_get_buf: friendly_name
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "R8300"
xmlValueConvert()
nvram_invmatch: upnp_turn_on ~?= "1"
nvram_get_buf: upnp_turn_on
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "1"
nvram_match: upnp_turn_on (1) ?= "1"
nvram_match: true
nvram_get_buf: hwrev
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = ""
nvram_get_buf: hwver
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "R8500"
nvram_match: hwver (R8500) ?= "R8500"
nvram_match: true
xmlValueConvert()
nvram_invmatch: upnp_turn_on ~?= "1"
nvram_get_buf: upnp_turn_on
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "1"
nvram_match: upnp_turn_on (1) ?= "1"
nvram_match: true
nvram_get_buf: friendly_name
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "R8300"
xmlValueConvert()
nvram_invmatch: upnp_turn_on ~?= "1"
nvram_get_buf: upnp_turn_on
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "1"
nvram_match: upnp_turn_on (1) ?= "1"
nvram_match: true
nvram_get_buf: hwrev
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = ""
nvram_get_buf: hwver
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "R8500"
nvram_get_buf: hwver
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "R8500"
nvram_match: hwver (R8500) ?= "R8500"
nvram_match: true
xmlValueConvert()
nvram_invmatch: upnp_turn_on ~?= "1"
nvram_get_buf: upnp_turn_on
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "1"
nvram_match: upnp_turn_on (1) ?= "1"
nvram_match: true
open: No such file or directory
xmlValueConvert()
nvram_invmatch: upnp_turn_on ~?= "1"
nvram_get_buf: upnp_turn_on
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "1"
nvram_match: upnp_turn_on (1) ?= "1"
nvram_match: true
upnp_uuid_generator:421()
nvram_get_buf: lan_hwaddr
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "AA:BB:CC:DD:EE:FF"
upnp_uuid_generator:421()
nvram_get_buf: lan_hwaddr
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "AA:BB:CC:DD:EE:FF"
xmlValueConvert()
nvram_invmatch: upnp_turn_on ~?= "1"
nvram_get_buf: upnp_turn_on
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "1"
nvram_match: upnp_turn_on (1) ?= "1"
nvram_match: true
nvram_get_buf: lan_ipaddr
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "10.211.55.11"
xmlValueConvert()
nvram_invmatch: upnp_turn_on ~?= "1"
nvram_get_buf: upnp_turn_on
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "1"
nvram_match: upnp_turn_on (1) ?= "1"
nvram_match: true
nvram_get_buf: friendly_name
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "R8300"
xmlValueConvert()
nvram_invmatch: upnp_turn_on ~?= "1"
nvram_get_buf: upnp_turn_on
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "1"
nvram_match: upnp_turn_on (1) ?= "1"
nvram_match: true
nvram_get_buf: hwrev
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = ""
nvram_get_buf: hwver
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "R8500"
nvram_match: hwver (R8500) ?= "R8500"
nvram_match: true
xmlValueConvert()
nvram_invmatch: upnp_turn_on ~?= "1"
nvram_get_buf: upnp_turn_on
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "1"
nvram_match: upnp_turn_on (1) ?= "1"
nvram_match: true
nvram_get_buf: friendly_name
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "R8300"
xmlValueConvert()
nvram_invmatch: upnp_turn_on ~?= "1"
nvram_get_buf: upnp_turn_on
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "1"
nvram_match: upnp_turn_on (1) ?= "1"
nvram_match: true
nvram_get_buf: hwrev
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = ""
nvram_get_buf: hwver
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "R8500"
nvram_get_buf: hwver
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "R8500"
nvram_match: hwver (R8500) ?= "R8500"
nvram_match: true
xmlValueConvert()
nvram_invmatch: upnp_turn_on ~?= "1"
nvram_get_buf: upnp_turn_on
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "1"
nvram_match: upnp_turn_on (1) ?= "1"
nvram_match: true
open: No such file or directory
xmlValueConvert()
nvram_invmatch: upnp_turn_on ~?= "1"
nvram_get_buf: upnp_turn_on
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "1"
nvram_match: upnp_turn_on (1) ?= "1"
nvram_match: true
upnp_uuid_generator:421()
nvram_get_buf: lan_hwaddr
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "AA:BB:CC:DD:EE:FF"
upnp_uuid_generator:421()
nvram_get_buf: lan_hwaddr
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "AA:BB:CC:DD:EE:FF"
xmlValueConvert()
nvram_invmatch: upnp_turn_on ~?= "1"
nvram_get_buf: upnp_turn_on
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "1"
nvram_match: upnp_turn_on (1) ?= "1"
nvram_match: true
nvram_get_buf: lan_ipaddr
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "10.211.55.11"
xmlValueConvert()
nvram_invmatch: upnp_turn_on ~?= "1"
nvram_get_buf: upnp_turn_on
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "1"
nvram_match: upnp_turn_on (1) ?= "1"
nvram_match: true
nvram_get_buf: friendly_name
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "R8300"
xmlValueConvert()
nvram_invmatch: upnp_turn_on ~?= "1"
nvram_get_buf: upnp_turn_on
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "1"
nvram_match: upnp_turn_on (1) ?= "1"
nvram_match: true
nvram_get_buf: hwrev
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = ""
nvram_get_buf: hwver
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "R8500"
nvram_match: hwver (R8500) ?= "R8500"
nvram_match: true
xmlValueConvert()
nvram_invmatch: upnp_turn_on ~?= "1"
nvram_get_buf: upnp_turn_on
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "1"
nvram_match: upnp_turn_on (1) ?= "1"
nvram_match: true
nvram_get_buf: friendly_name
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "R8300"
xmlValueConvert()
nvram_invmatch: upnp_turn_on ~?= "1"
nvram_get_buf: upnp_turn_on
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "1"
nvram_match: upnp_turn_on (1) ?= "1"
nvram_match: true
nvram_get_buf: hwrev
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = ""
nvram_get_buf: hwver
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "R8500"
nvram_get_buf: hwver
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "R8500"
nvram_match: hwver (R8500) ?= "R8500"
nvram_match: true
xmlValueConvert()
nvram_invmatch: upnp_turn_on ~?= "1"
nvram_get_buf: upnp_turn_on
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "1"
nvram_match: upnp_turn_on (1) ?= "1"
nvram_match: true
open: No such file or directory
xmlValueConvert()
nvram_invmatch: upnp_turn_on ~?= "1"
nvram_get_buf: upnp_turn_on
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "1"
nvram_match: upnp_turn_on (1) ?= "1"
nvram_match: true
upnp_uuid_generator:421()
nvram_get_buf: lan_hwaddr
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "AA:BB:CC:DD:EE:FF"
upnp_uuid_generator:421()
nvram_get_buf: lan_hwaddr
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "AA:BB:CC:DD:EE:FF"
xmlValueConvert()
nvram_invmatch: upnp_turn_on ~?= "1"
nvram_get_buf: upnp_turn_on
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "1"
nvram_match: upnp_turn_on (1) ?= "1"
nvram_match: true
nvram_get_buf: lan_ipaddr
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "10.211.55.11"
xmlValueConvert()
parse_root_device_description:619()
findtok:519()
parse_root_device_description:644(), findtok(URLBase)
parse_root_device_description:681(), device_type0 = InternetGatewayDevice
findtok:519()
parse_root_device_description:752(), findtok(SCPDURL)
parse_root_device_description:780(): find EventSub URL
parse_root_device_description:795(): find </service>
parse_root_device_description:806(): assign the rest value of the service structure
nvram_get_buf: upnp_duration
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "3600"
parse_root_device_description:836(): assign the rest value of the device structure
nvram_get_buf: upnp_duration
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "3600"
emb_num = 0, max_layer = 1, layer = 1parse_root_device_description:687(), device_type0 = WANDevice
findtok:519()
parse_root_device_description:752(), findtok(SCPDURL)
parse_root_device_description:780(): find EventSub URL
parse_root_device_description:795(): find </service>
parse_root_device_description:806(): assign the rest value of the service structure
nvram_get_buf: upnp_duration
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "3600"
parse_root_device_description:836(): assign the rest value of the device structure
nvram_get_buf: upnp_duration
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "3600"
emb_num = 1, max_layer = 2, layer = 2parse_root_device_description:687(), device_type1 = WANConnectionDevice
findtok:519()
parse_root_device_description:752(), findtok(SCPDURL)
parse_root_device_description:780(): find EventSub URL
parse_root_device_description:795(): find </service>
parse_root_device_description:806(): assign the rest value of the service structure
nvram_get_buf: upnp_duration
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "3600"
findtok:519()
parse_root_device_description:752(), findtok(SCPDURL)
parse_root_device_description:780(): find EventSub URL
parse_root_device_description:795(): find </service>
parse_root_device_description:806(): assign the rest value of the service structure
nvram_get_buf: upnp_duration
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "3600"
findtok:519()
parse_root_device_description:752(), findtok(SCPDURL)
parse_root_device_description:780(): find EventSub URL
parse_root_device_description:795(): find </service>
parse_root_device_description:806(): assign the rest value of the service structure
nvram_get_buf: upnp_duration
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "3600"
parse_root_device_description:836(): assign the rest value of the device structure
nvram_get_buf: upnp_duration
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "3600"
nvram_set: upnp_portmap_entry = "0"
sem_get: Key: 41430002
sem_get: Key: 41430002
emb_num = 2, max_layer = 3, layer = 3upnp_main:751()
nvram_get_buf: upnp_turn_on
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "1"
nvram_match: upnp_turn_on (1) ?= "1"
nvram_match: true
upnp_main: 763()
nvram_get_buf: lan_ipaddr
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "10.211.55.11"
nvram_match: lan_ipaddr (10.211.55.11) ?= "0.0.0.0"
nvram_match: false
create_received_scoket:158()
upnp_sockeInit:964()
nvram_get_buf: lan_ipaddr
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "10.211.55.11"
create_submit_scoket: 199()
create_received_scoket:158()
upnp_sockeInit:964()
get_if_addr(946): Can't get IP from br0.
nvram_get_buf: upnp_duration
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "3600"
upnp_duration is 3600
ssdp_discovery_advertisement(568):
rootDeviceOK(68):
ssdp_discovery_send(511):
ssdp_root_device_discovery_send(244):
igd_ssdp_root_device_discovery(84)
ssdp_packet(98):
nvram_get_buf: upnp_duration
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "3600"
http_mu_send:1041()
nvram_get_buf: upnp_advert_ttl
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "4"
nvram_get_buf: lan_ipaddr
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "10.211.55.11"
Unsupported setsockopt level=0 optname=32
UPNP: error to use LAN IP to be the interface of sending mulitcast datagram!
ssdp_UUID_discovery_send(477):
igd_ssdp_UUID_discovery(100)
ssdp_packet(98):
nvram_get_buf: upnp_duration
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "3600"
http_mu_send:1041()
nvram_get_buf: upnp_advert_ttl
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "4"
nvram_get_buf: lan_ipaddr
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "10.211.55.11"
Unsupported setsockopt level=0 optname=32
UPNP: error to use LAN IP to be the interface of sending mulitcast datagram!
ssdp_schemas_discovery_send(495):
igd_ssdp_schemas_discovery(125)
ssdp_packet(98):
nvram_get_buf: upnp_duration
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "3600"
http_mu_send:1041()
nvram_get_buf: upnp_advert_ttl
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "4"
nvram_get_buf: lan_ipaddr
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "10.211.55.11"
Unsupported setsockopt level=0 optname=32
UPNP: error to use LAN IP to be the interface of sending mulitcast datagram!
nvram_get_buf: upnp_advert_period
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "30"
nvram_get_buf: upnp_turn_on
sem_get: Key: 41430002
sem_get: Key: 41430002
nvram_get_buf: = "1"
nvram_match: upnp_turn_on (1) ?= "1"
nvram_match: true
```
![92.png](https://www.iotsec-zone.com/images/MdImg/60b98dafd87fb7bcb5ce7370fc54a8ae.png)
收工！
# 5、反思
别人的代码不要上来就拿来就用，如果实在是对宏定义感到厌烦或压根不想花那么多的精力看代码，直接在IDA里看编译出来的伪代码吧，这样更直观；另外，printf是个好东西。虽然网上也有人碰到过这个问题，但并没有深入思考，直接放那里了：
![93.png](https://www.iotsec-zone.com/images/MdImg/2b05f3247c276c7e281fba83a927c3fb.png)
