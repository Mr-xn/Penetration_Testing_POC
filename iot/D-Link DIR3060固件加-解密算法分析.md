# D-Link DIR3060固件加/解密算法分析
> 21Gun5
> 来源：https://www.iotsec-zone.com/article/17

# D-Link DIR3060固件加/解密算法分析

[TOC]

## 00-简介

- 文章概要：D-Link DIR3060加解密算法以及固件结构的分析
- PS：手头没啥现成的文章，找了一篇自己的学习笔记，当时初入iot大坑，记录的比较详细，按照自己的理解，对原文做了一定补充和总结，算是半翻译半原创，希望可以帮助到新人，还望大家不吝指教。

- 结合原文食用更佳：
    - [Breaking the D-Link DIR3060 Firmware Encryption - Recon - Part 1](https://0x434b.dev/breaking-the-d-link-dir3060-firmware-encryption-recon-part-1/)
    - [Breaking the D-Link DIR3060 Firmware Encryption - Static analysis of the decryption routine - Part 2.1](https://0x434b.dev/breaking-the-d-link-dir3060-firmware-encryption-static-analysis-of-the-decryption-routine-part-2-1/)
    - [Breaking the D-Link DIR3060 Firmware Encryption - Static analysis of the decryption routine - Part 2.2](https://0x434b.dev/breaking-the-d-link-dir3060-firmware-encryption-static-analysis-part-2/)

## 01-逆向分析

- lwl, lwr：未对齐内存的访问

- 大小端问题

    ```
    $v0:
              ↓
    00000000: 5348 5253 00d1 d9a6 00d1 d9b0 67c6 6973  SHRS........g.is
    00000010: 51ff 4aec 29cd baab f2fb e346 fda7 4d06  Q.J.)......F..M.
    [...]
    
    lwl $v1 11($v0):
                                          ↓
    00000000: 5348 5253 00d1 d9a6 00d1 d9b0 67c6 6973  SHRS........g.is
    00000010: 51ff 4aec 29cd baab f2fb e346 fda7 4d06  Q.J.)......F..M.
    [...]
    --> $v1 = b0d9
    ```

- python实现字节转整数

    ```python
    # 1
    int.from_bytes(b'\xb0\xd9\xd1\x00', byteorder='little', signed=False)
    13752752
    # 2
    from socket import htonl
    htonl(0xb0d9d100)
    13752752
    ```

- wc -c DIR_882_FW120B06.BIN：-c, --bytes

- xargs命令的作用，是将标准输入转为命令行参数

    ```shell
    > wc -c DIR_882_FW120B06.BIN | cut -d' ' -f1 | xargs printf '0x%x\n'     
    0xd1f247
    ```

- SHA512_Init, SHA512_Update, SHA512_Final，计算hash值的一组函数，最终 return a pointer to the hash value

- hexdump

    ```sh
    > hd DIR_882_FW120B06.BIN -s 0x9c -n 64
    0000009c  68 bf e5 30 a0 49 b9 e8  5d a0 bb 81 71 87 05 cd  |h..0.I..]...q...|
    000000ac  70 25 18 f2 8f af d6 21  35 05 31 7e fd af 60 56  |p%.....!5.1~..`V|
    000000bc  d8 ed e7 71 6c 39 d1 68  0d a7 13 f4 04 41 87 58  |...ql9.h.....A.X|
    000000cc  e9 97 36 73 99 78 8b 01  10 ee 12 d6 b6 3b 69 ec  |..6s.x.......;i.|
    000000dc
    
    > hd DIR_882_FW120B06.BIN -s 0x9c -n 64 -e '156/1 "%x" "\n"' | cut -d$'\n' -f2
    68bfe530a049b9e85da0bb8171875cd702518f28fafd621355317efdaf6056d8ede7716c39d168da713f44418758e997367399788b110ee12d6b63b69ec
    # -s，skip
    # -n，length
    # -e，format
    ```
    
- mips函数调用：多于四个参数，其他参数保存在栈中，看对a0操作的前面有没有sw保存到栈的操作，一般就是多出的

- AES

    - 高级加密标准、对称加密算法
    - 只有一个密钥，这个密钥既用来加密，也用于解密
    - 加密方式有五种：**ECB**, **CBC**, CTR, CFB, OFB（从安全性角度推荐CBC加密方法
    - CBC加密需要一个十六位的key(密钥)和一个十六位iv(偏移量)、ECB加密不需要iv
    - Google：python 利用Crypto进行AES解密&加密文件

- AES_cbc_encrypt

    - (const unsigned char *in, unsigned char *out, size_t length, const AES_KEY *key, unsigned char *ivec, const int enc);
    - If enc is non-zero, AES_cbc_encrypt() encrypts len bytes at in to out using the 128 bit key and the 128 bit initialization vector ivec in CBC mode. 
    - If enc is 0, AES_cbc_encrypt() performs the corresponding decryption.

- 一般情况下：解密、获取解密文件hash、hash对比来判断正确与否

- 两个差不多大的数值，一个是真正长度，另一个是为对齐而增加后的长度

    - （AES为了安全考虑，每个块是16字节
    - 文中关于datalen_1和2的分析还是有些乱

- hexdump中出现*号，表示一堆0

- RSA_verify

    - (int type, const unsigned char *m, unsigned int m_len, unsigned char *sigbuf, unsigned int siglen, RSA *rsa);
    - verifies that the signature **sigbuf** of size **siglen** matches a given message digest **m** of size **m_len**. 
    - **type** denotes the message digest algorithm that was used to generate the signature. 
    - **rsa** is the signer's public key.
    - returns 1 on successful verification, 0 otherwise.

- RSA_verify，type=0x2A2=674，openssl/obj_mac.h中，#define NID_SHA512 674，说明是sha512，是一种hash算法

- AES+RSA常结合使用：前者对称，后者非对称

- unlink

    - (const char* pathname);
    - 删除一个名字（某些情况下删除这个名字所指向的文件）
    - 从文件系统中中删除一个名字，若这个名字是指向这个文件的最后一个链接，并且没有进程处于打开这个文件的状态，则删除这个文件，释放这个文件占用的空间
    - 如果这个名字是指向这个文件的最后一个链接，但有某个进程处于打开这个文件的状态，则暂时不删除这个文件，要等到打开这个文件的进程关闭这个文件的文件描述符后才删除这个文件

## 02-流程梳理

###  1-main

1. 是否有“decrypt”字符串？
2. 加密or解密

### 2-decrypt_firmware

1. 参数个数
    1. 小于2（1），打印帮助信息
    2. 大于2（3），pem为指定的文件
    3. 等于2，pem为默认的"/tmp/public.pem"
2. check_cert获取密钥，用于后面数字签名的验证，pem文件中存储着rsa的密钥（公/私）
    1. OPENSSL_add_all_algorithms_noconf、RSA_new、PEM_read_RSAPublicKey、RSA_free
    2. fopen/fclose打开/关闭pem文件
    3. （目前遇到rsa两种情况：RSA解密aes的密钥、RSA解密用于验证数字签名
3. call_aes_cbc_encrypt调用aes_cbc_encrypt：aes-cbc解密得到key，后面真正解密固件时用到
    1. AES_set_decrypt_key (userKey, bits, key)：通过userkey进一步获取key，可以理解为用户提供的密钥userkey不能直接用于解密，需要做进一步处理
    2. AES_cbc_encrypt(in, out, length, key, ivec, enc)：加/解密通过enc指定、cbc是aes的一种模式，cbc需要ivec而ebc不需要
    3. in、key、ivec都是硬编码在二进制程序中的，in输入为加密的aes密钥，解密后用于后面aes解密固件
4. 打印上面解密出来的key：
    1. 有两次aes解密，第一次解密aes密钥（用于第二次），第二次解密固件
    2. 第一次解密的密钥来自硬编码，第二次解密的密钥来自第一次的解密结果
5. actual_decryption：真正的解密固件的函数，前面都是准备工作
    1. 选择pem文件：自己指定还是用默认的
    2. 从pem中获取rsa密钥：用于后面验证数字签名
    3. aes解密：获取后面aes解密的密钥

### 3-actual_decryption

0. 传参：待解密的固件、 临时文件"/tmp/.firmware.orig"、前面解密获得的key
1. 映射到内存等准备工作
    1. memset准备两块内存空间（0填充
    2. stat获取加密固件的文件状态，成功则open打开，再成功则mmap映射到内存
    3. 打开tmp下的临时文件，成功则lseek将文件指针移动到最后，并添加1个0，随后close关闭文件，来保存修改、
    4. open再次打开tmp下临时文件，并mmap映射到内存
2. 检查标记：将加密固件传入check_magic来检查标记，其memcmp查看是否以“SHRS”开头
3. 小端转大端：从文件偏移4、8处取出数据，htonl将主机字节序转为网络字节序，得到两个值：v1和v2
    1. htonl：host、network、unsigned long 
    2. 主机序一般为小端，网络为大端，htonl也就是将小端转为大端
    3. 小端符合人思维（倒序），大端直观（正序），也就是将内存中倒着的数据正过来，好计算
4. calc_SHA512_digest第一次验证完整性
    1. 传入：加密固件、值v2，
    2. 其SHA512_Init、SHA512_Update、SHA512_Final，一看就是计算hash，
    3. memcmp比较文件偏移0x9c处和hash值
5. aes_cbc_encrypt解密固件：
    1. in输入：加密的固件，从偏移6dc处开始而非文件开头
    2. out输出：tmp下的临时文件，可见这个文件的作用就是接收解密后的固件，为其提供空间（类似字符数组存放返回结果，在此只不过换成了文件
    3. len长度：前面htonl获取的值v2
    4. key密钥：第一次aes解密后的结果
    5. ivec初始化向量：硬编码在加密固件中（第一次的iv硬编码在二进制程序中
6. calc_SHA512_digest第二次验证完整性
    1. 传入：解密后的固件、值v1
    2. memcmp比较文件偏移0x5c处和hash值
7. calc_SHA512_digest第三次验证完整性
    1. 传入：解密后的固件、值v1、第一次aes解密获取到的aes_key
    2. 同上2次没本质区别，只不过hash的对象为固件+key，SHA512_Update多调用一次即可
    3. memcmp比较文件偏移0x1c处和hash值
8. SHA512_checker调用RSA_verify验证数字签名：
    1. RSA_verify(type, m, m_len, sigbuf, siglen,rsa)
    2. type摘要算法类型：指定生成签名的hash算法，0x2a2表示SHA512
    3. rsa密钥：前面从pem文件中获取到的
    4. m消息，sigbuf签名：用rsa解密sigbuf，type计算m的散列值，对比二者来验证签名
    5. 前后调用两次：第一次（m=0x5c，sigbuf=0x2dc），第二次（m=0x9c，sigbuf=0x4dc）
9. 扫尾：munmap、close、解密成功返回0

### 4-扫尾

1. unlink删除加密的固件
2. rename将tmp下的临时文件重命名为加密固件的名字，此时临时文件就是解密后的固件
3. RSA_free释放rsa结构体，结束

## 03-代码编写

- 通过汇编写C
- 通过C写python

- [https://github.com/0xricksanchez/dlink-decrypt（暂不自己动手了](https://github.com/0xricksanchez/dlink-decrypt（暂不自己动手了)，有类似需求时当做参考

## 04-固件结构

![image-20200918161124445](https://note-1252764528.cos.ap-chengdu.myqcloud.com/2020-09-18-085343.jpg)


### 0-3
- 4字节：53 48 52 53
- SHRS，加密固件的标记

### 4-7、8-B
- 各4字节：00 D1 D9 A6/00 D1 D9 B0
- 处理
    - 汇编中通过lwr/lwl逆序取出：0xA6D9D100
    - 通过htonl：将主机字节序转为网络字节序，也就是再倒一次变成0x00D1D9A6，十进制为13752742
    - （不知为何这样，可能汇编中只能倒着取出，所以逼不得已再倒一次变正常
    - 得到两个数：13752742/13752752（可见二者仅差了10
    - 加密固件大小：0xD1F247=13759047（并非二者，但都是1375
- 分析value2
    - value2=13752752，传入了calc_SHA512_digest第一次验证完整性和aes_cbc_encrypt第二次解密，一同传入的还有加密固件的0x6DC偏移，0xD1F247-0x6DC=13757291，也不对
    - value1=13752742，传入了calc_SHA512_digest第二次和第三次验证完整性，注意此时一同传入的是解密后的固件了，获取解密后固件（已经有解密脚本了）的大小为D1D9B0=13752752，正是value2的值（注意而不是value1
    - 因此：value2为解密后固件大小
- 分析value1
    - 由上分析1是与解密后的固件相关的，1仅比2小了10，即解密固件大小比1多了10，多的10是什么？
    - 查看解密后固件最后10字节，发现全是0，大胆猜想：莫非是填充？
    - value1=13752742 % 16 = 6，value2=13752745 % 16 = 0，1取余为6，填充16-6=10正好凑16整数
    - 填充到16整数也是由aes决定的，参考[https://tools.ietf.org/html/rfc3602#section-2.4（Block](https://tools.ietf.org/html/rfc3602#section-2.4（Block) Size and Padding
    - 因此：value1为原始固件大小
- 综上：1原始解密后固件大小，2在1基础上填充后的

### C-1B
- 16字节：67 C6 69 73 51 FF 4A EC 29 CD BA AB F2 FB E3 46
- 第二次aes解密（解密固件）的ivec向量

### 1C-5B
- 64字节：FD A7 4D 06 A4 66 E6 AD BF C4 9D 13 F3 F7 D1 12 98 6B 2A 35 1D 0E 90 85 B7 83 F7 4D 3A 2A 25 5A B8 13 0C FB 2A 17 7A B2 99 04 60 66 EB C2 58 98 82 74 08 E3 54 1E E2 51 44 42 E8 D6 8E 46 6E 2C
- 第三次calc_SHA512_digest验证完整性时（传入解密后固件+解密后的aes_key），64字节的消息摘要

### 5C-9B
- 64字节：16 57 D3 0B 07 D7 7C 9E 11 EC 72 1D FB 87 A2 5B 18 EC 53 82 85 B9 84 39 B6 B4 DD 85 DE F0 28 3D 36 0E BE AA D0 9D 71 B0 BA 3E 26 40 E8 C5 4C 0E 0B 32 EB 00 E8 F7 21 D7 3A AA 0D 14 D5 F7 E8 72
- 第二次calc_SHA512_digest验证完整性时（仅传入解密后固件），64字节的消息摘要

### 9C-DB
- 65字节：68 BF E5 30 A0 49 B9 E8 5D A0 BB 81 71 87 05 CD 70 25 18 F2 8F AF D6 21 35 05 31 7E FD AF 60 56 D8 ED E7 71 6C 39 D1 68 0D A7 13 F4 04 41 87 58 E9 97 36 73 99 78 8B 01 10 EE 12 D6 B6 3B 69 EC
- 第一次calc_SHA512_digest验证完整性时（仅传入加密固件），64字节的消息摘要

### DC-2DB
- 512个0字节
- 填充用的？还是用来保存后续产生的数据？

### 2DC-4DB、4DC-6DB
- 各512个字节
- 两次RSA_verify验证所用的签名

### 6DC-
- 第二次aes解密（解密固件），传入加密固件的6dc偏移
- 真正的加密数据

### 小结
- 0-6DB：头部，总大小1756，提供附加数据
    - 0-DB：meta checks元数据，用于解密或验证
    - DC-2DB：512空字节，填充？保留空间？
    - 2DC-4DB、4DC-6DB：各512字节，两次RSA_verify验证所用的签名
    - 6DC-：真正的加密数据
