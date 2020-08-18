# -*- coding:utf-8 -*- -
import os
import re
import psutil
import yara
import sys

HOST_IP = input('\033[1;34m请输入本机IP：\033[0m')
####################先来一个帅气的banner#############################
banner = """\033[1;34m
   ____    ____  __       ___      .__   __.      _______. _______   ______ 
   \   \  /   / |  |     /   \     |  \ |  |     /       ||   ____| /      |
    \   \/   /  |  |    /  ^  \    |   \|  |    |   (----`|  |__   |  ,----'
     \_    _/   |  |   /  /_\  \   |  . `  |     \   \    |   __|  |  |     
       |  |     |  |  /  _____  \  |  |\   | .----)   |   |  |____ |  `----.
       |__|     |__| /__/     \__\ |__| \__| |_______/    |_______| \______|

          linux自动化巡检工具                             Version：1.0
          Company:宁波壹安信息科技有限公司                Author：说书人\033[0m
"""
print(banner)


####################开局先检查权限和判断系统#############################
print('\033[1;36m本机IP:{0}开始巡检\033[0m'.format(HOST_IP))
# 检查是否root运行
def checkroot():
    if os.popen("whoami").read() != 'root\n':
        print('当前为非root权限，部分功能可能受限')
        c = input('是否继续？（y/N）:')
        if c == 'y':
            pass
        else:
            exit()


def ostype():  # 判断系统类型和版本
    try:
        print('不要在意下面那行出现的command not found')
        a = os.popen("lsb_release -a").read()
        b = os.popen("cat /etc/redhat-release").read()
        os_info = a + b
        sysnum = int(re.findall(r' (\d+?)\.', os_info, re.S)[0])  # 取出版本号
        system = ''
        try:
            system = re.search('CentOS', os_info).group()
        except:
            pass
        try:
            system = re.search('Ubuntu', os_info).group()
        except:
            pass
        try:
            system = re.search('openSUSE', os_info).group()
        except:
            pass
        try:
            system = re.search('Red Hat', os_info).group()
        except:
            pass
        try:
            system = re.search('Debian', os_info).group()
        except:
            pass
    except:
        print('\033[1;33m提示：系统类型获取失败，请手动输入系统类型和版本号\033[0m')
        print("\033[1;33m系统类型只能'CentOS'，'Ubuntu'，'openSUSE'，'Red Hat'，'Debian' 其中一个，注意空格和大小写，输入其他无效\033[0m")
        print("\033[1;33m版本号请输入整数，如：6\033[0m")
        system = input('系统类型：')
        sysnum = input('版本号：')
    return system, sysnum


####################系统基本信息#############################
def cpu():  # cpu使用率
    cpu = 'CPU使用率：{}{}\n'.format(str(psutil.cpu_percent(1)), '%')
    return cpu


def mem():  # 内存使用率
    mem = '内存使用率：{}{}\n'.format(str(psutil.virtual_memory()[2]), '%')
    return mem


def disk():  # 磁盘使用率
    disk = '磁盘使用率：{}{}'.format(psutil.disk_usage('/')[3], '%')
    return disk


def network():  # 获取对外网络连接情况
    addr_list = str(psutil.net_connections()).split('sconn')
    banner = '{0}  {1:^35}  {2}'.format('远程IP', '远程端口', '进程PID')
    net = ''
    for addr in addr_list:
        try:
            if re.findall(r'raddr', addr) != []:  # 如果存在远程地址，就取出来
                remote = addr.split('raddr')[-1]
                ip = re.findall(r'ip=\'(.+?)\'', remote)[0]
                port = re.findall(r'port=(.+?)\)', remote)[0]
                pid = re.findall(r'pid=(.+?)\)', remote)[0]
                remote_info = '{0:^15}  {1:^17}  {2:^30}'.format(ip, port, pid)
                net = net + remote_info + '\n'
        except:
            pass

    network = '{0}\n{1}'.format(banner, net)
    return network


###################################################################


def account_check():  # 检查账户情况
    account_list = []
    cmd = os.popen("cat /etc/shadow").read()
    user_list = re.split(r'\n', cmd)
    for i in user_list:
        try:
            c = re.search(r'\*|!', i).group()
        except:
            try:
                ok_user = re.findall(r'(.+?):', i)[0]
                account_list.append(ok_user)
            except:
                pass
    anonymous_account = os.popen("awk -F: 'length($2)==0 {print $1}' /etc/shadow").read()
    account = '存在的账户：\n{0}\n空口令用户：\n{1}\n'.format(account_list, anonymous_account)
    return account


def process():  # 列出在当前环境中运行的进程

    process = os.popen("ps -ef").read()
    return process


def service(system, sysnum):  # 列出开启的服务
    service = ''
    if system == 'Ubuntu' or system == 'Debian':
        service = os.popen("service --status-all | grep +").read()
    elif system == 'openSUSE':
        service = os.popen("service --status-all | grep running").read()
    elif system == 'CentOS' or system == 'Red Hat':
        if sysnum < 7:
            service1 = os.popen("chkconfig --list |grep 2:启用").read()
            service2 = os.popen("chkconfig --list |grep 2:on").read()
            service = service1 + '\n' + service2
        else:
            service = os.popen("systemctl list-units --type=service --all |grep running").read()
    return service


def startup(system, sysnum):  # 列出启动项
    startup = ''
    if system == 'CentOS' or system == 'Red Hat':
        if sysnum < 7:
            startup = os.popen("cat /etc/rc.d/rc.local").read()
        else:
            startup = os.popen("systemctl list-unit-files | grep enabled").read()
    elif system == 'Ubuntu' or system == 'Debian':
        if sysnum < 14:
            startup1 = os.popen("chkconfig |grep on").read()
            startup2 = os.popen("chkconfig |grep 启用").read()
            startup = startup1 + startup2
        else:
            startup = os.popen("systemctl list-unit-files | grep enabled").read()
    elif system == 'openSUSE':
        startup1 = os.popen("chkconfig |grep on").read()
        startup2 = os.popen("chkconfig |grep 启用").read()
        startup = startup1 + startup2
    return startup


def timingtask():  # 列出定时任务
    timingtask = []
    cmd = os.popen("cat /etc/shadow").read()
    user_list = re.split(r'\n', cmd)
    for i in user_list:
        try:
            c = re.search(r'\*|!', i).group()
        except:
            try:
                ok_user = re.findall(r'(.+?):', i)[0]
                task = os.popen("crontab -l -u " + ok_user).read()
                timingtask.append(task)
            except:
                pass
    return timingtask


def seclog_time():  # 登录日志存留时间
    cmd = os.popen("cat /etc/logrotate.conf").read()
    try:
        seclog = ''
        cycle = re.findall(r'# rotate log files weekly\n(.+?)\n', cmd, re.S)[0]  # 周期
        num = re.findall(r'\d+', str(re.findall(r'# keep 4 weeks worth of backlogs\n(.+?)\n', cmd, re.S)))[0]  # 次数
        if cycle == 'weekly':
            if int(num) < 26:
                seclog = '\033[1;31m日志存留不足180天\033[0m'
            else:
                seclog = '\033[1;32m日志存留时间符合要求\033[0m'
        elif cycle == 'monthly':
            if int(num) < 6:
                seclog = '\033[1;31m日志存留不足180天\033[0m'
            else:
                seclog = '\033[1;32m日志存留时间符合要求\033[0m'
        elif cycle == 'quarterly':
            if int(num) < 2:
                seclog = '\033[1;31m日志存留不足180天\033[0m'
            else:
                seclog = '\033[1;32m日志存留时间符合要求\033[0m'
        return seclog
    except:
        seclog = '\033[1;31m日志轮转配置读取出错\033[0m'
        return seclog


def seclog_login(system):  # 登录ip记录
    succeed = failed = ''
    if system == 'CentOS' or system == 'Red Hat':
        succeed = '\n成功登录：\n' + os.popen(
            "cat /var/log/secure*|awk '/Accepted/{print $(NF-3)}'|sort|uniq -c|awk '{print $2\"|次数=\"$1;}'").read()
        failed = '\n失败登录：\n' + os.popen(
            "cat /var/log/secure*|awk '/Failed/{print $(NF-3)}'|sort|uniq -c|awk '{print $2\"|次数=\"$1;}'").read()
    elif system == 'Ubuntu' or system == 'Debian':
        succeed = os.popen(
            "cat /var/log/auth.log|awk '/Accepted/{print $(NF-3)}'|sort|uniq -c|awk '{print $2\"|次数=\"$1;}'").read()
        failed = os.popen(
            "cat /var/log/auth.log|awk '/authentication failure/{print $(NF-1)}'|sort|uniq -c|awk '{print $2\"|次数=\"$1;}'").read()
        succeed = '\n成功登录：\n' + re.sub("rhost=\|次数=\d|ruser=\|次数=\d|rhost=", "", succeed)
        failed = '\n失败登录：\n' + re.sub("rhost=\|次数=\d|ruser=\|次数=\d|rhost=", "", failed)
    elif system == 'openSUSE':
        succeed = '\n成功登录：\n' + os.popen(
            "cat /var/log/messages|awk '/Accepted/{print $(NF-3)}'|sort|uniq -c|awk '{print $2\"|次数=\"$1;}'").read()
        failed = '\n失败登录：\n' + os.popen(
            "cat /var/log/messages|awk '/failure/{print $(NF)}'|sort|uniq -c|awk '{print $2\"|次数=\"$1;}'").read()
    seclog_login = succeed + '\n' + failed
    return seclog_login


def seclog_user(system):  # 用户（组）增删改日志审计
    whichlog = ''
    if system == 'CentOS' or system == 'Red Hat':
        whichlog = 'secure*'
    elif system == 'Ubuntu' or system == 'Debian':
        whichlog = 'auth.log'
    elif system == 'openSUSE':
        whichlog = 'messages'
    group_add = os.popen("cat /var/log/{0}|grep \"new group\"".format(whichlog)).read()
    group_change = os.popen("cat /var/log/{0}|grep -E \"to group|to shadow\"".format(whichlog)).read()
    group_del = os.popen("cat /var/log/{0}|grep group|grep removed".format(whichlog)).read()
    user_add = os.popen("cat /var/log/{0}|grep \"new user\"".format(whichlog)).read()
    user_del = os.popen("cat /var/log/{0}|grep \"delete user\"".format(whichlog)).read()
    seclog_user = '增加用户：\n{0}\n删除用户：\n{1}\n增加组：\n{2}\n删除组：\n{3}\n变更组：\n{4}\n'.format(user_add, user_del, group_add,
                                                                                     group_del, group_change)
    return seclog_user


def firewall(system, sysnum):  # 查看防火墙状态
    firewall = ''
    if system == 'CentOS' or system == 'Red Hat':
        if sysnum < 7:
            firewall = os.popen("service iptables status").read()
        else:
            firewall = os.popen("systemctl status firewalld").read()
    elif system == 'Ubuntu' or system == 'Debian':
        firewall = os.popen("ufw status").read()
    elif system == 'openSUSE':
        firewall = os.popen("service SuSEfirewall2_setup status").read()
    if re.findall(r'not running|inactive|dead|unused', firewall, re.S) != []:
        firewall_status = '\033[1;31m防火墙未开启\033[0m'
    else:
        firewall_status = '\033[1;32m防火墙已开启\033[0m'
    return firewall_status


def file_scan():  # 文件静态检测扫描模块
    print('\033[1;36m【11】文件扫描\033[0m')
    rule = yara.compile(filepath=r'rules/index.yar')
    print('\033[1;34m-----【11.1】读取待检测文件中...\033[0m')
    all = os.popen(
        "find /usr /home /root /tmp \( -path /usr/share/doc -o -path /root/.bash_history \) -prune -o -print").read().split(
        '\n')
    file_list = []  # 过滤后的文件列表
    warning_all = ''  # 全部告警信息
    print('\033[1;32m-----【11.2】读取完毕，开始过滤...\033[0m')
    for file in all:  # 过滤掉部分文件
        filter = re.findall(
            r'\.zip|\.rar|\.7z|\.tar|\.gz|\.xz|\.bz2|\.ttf|\.bmp|\.jpg|\.jpeg|\.png|\.svg|\.icon|\.gif|\.txt|\.yar|\.yara', file)
        if filter == []:
            file_list.append(file)
    print('\033[1;32m-----【11.3】过滤完毕，开始扫描...\033[0m')
    for i in range(len(file_list)):
        sys.stdout.write('\033[K' + '\r')
        print('\r', '[{0}/{1}]检测中：{2}'.format(str(i), str(len(file_list)), file_list[i]), end=' ', flush=True)
        try:
            with open(file_list[i], 'rb') as f:
                matches = rule.match(data=f.read())
        except:
            pass
        try:
            if matches != []:
                warning = ('\033[1;31m\n告警：检测到标签{0}，文件位置{1}\033[0m'.format(matches, file_list[i]))
                warning_all = warning_all + '\n' + warning
                print(warning)
        except:
            pass

    print('\033[1;32m\n-----【11.4】扫描完成\033[0m')
    return warning_all


############################以上为函数部分#############################
sys_tup=ostype()
system = sys_tup[0]
sysnum = sys_tup[1]
ssr_cpu = cpu()  # cpu
ssr_mem = mem()  # 内存
ssr_disk = disk()  # 磁盘
ssr_network = network()  # 对外连接
print('\033[1;36m【1】系统状态获取完毕\033[0m\n{0}   {1}   {2}\n{3}'.format(ssr_cpu, ssr_mem, ssr_disk, ssr_network))
ssr_account = account_check()  # 账户情况
print('\n\033[1;36m【2】账户情况获取完毕\033[0m\n{0}'.format(ssr_account))
ssr_process = process()  # 获取所有进程详细
print('\033[1;36m【3】进程信息获取完毕(报告中显示)\033[0m')
ssr_service = service(system, sysnum)  # 获取开启的服务
print('\033[1;36m【4】开启的服务获取完毕(报告中显示)\033[0m')
ssr_startup = startup(system, sysnum)  # 获取启动项
print('\033[1;36m【5】启动项获取完毕(报告中显示)\033[0m')
ssr_timingtask = ''  # 定时任务
print('\033[1;36m【6】定时任务获取完毕\033[0m')
for timingtask in timingtask():
    print(timingtask)
    ssr_timingtask = ssr_timingtask + '\n' + timingtask
ssr_seclog_time = seclog_time()  # 日志存留合规检查
print('\033[1;36m【7】日志存留合规检查完毕\033[0m\n{0}'.format(ssr_seclog_time))
ssr_seclog_login = seclog_login(system)  # 登录日志审计
print('\033[1;36m【8】登录日志审计完毕(报告中显示)\033[0m')
ssr_seclog_user = seclog_user(system)  # 账户操作日志审计
print('\033[1;36m【9】账户操作日志审计完毕(报告中显示)\033[0m')
ssr_firewall = firewall(system, sysnum)  # 防火墙状态
print('\033[1;36m【10】防火墙状态获取完毕：\033[0m\n{0}'.format(ssr_firewall))
ssr_file_scan = file_scan()  # 文件静态检测扫描

############################导出txt报告#############################

with open("{0}巡检报告.txt".format(HOST_IP), "a") as f:
    f.write(
        "【系统状态】:\n{0}\n{1}\n{2}\n{3}\n【账户情况】:\n{4}\n【进程信息】:\n{5}\n【开启的服务】:\n{6}\n【启动项】:\n{7}\n【定时任务】:\n{8}\n【日志存留合规检查】:\n{9}\n【登录日志审计】:\n{10}\n【账户操作日志审计】:\n{11}\n【防火墙状态】:\n{12}\n【文件扫描告警结果】:\n{13}".format(ssr_cpu,ssr_mem,ssr_disk,ssr_network,ssr_account,ssr_process,ssr_service,ssr_startup,ssr_timingtask,ssr_seclog_time,ssr_seclog_login,ssr_seclog_user,ssr_firewall,ssr_file_scan))

print('\033[1;36m【12】{0}巡检报告导出完毕，位于程序所在目录！\033[0m'.format(HOST_IP))