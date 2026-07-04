# jboss-_CVE-2017-12149

![72DC2C8058A7B3711A5D0446692D4BDA](./截图.jpg)



verify_CVE-2017-12149.jar提供命令行模式下验证漏洞,如果漏洞存在返回特征字符串,只需要执行命令:

```shell
$ java -jar verify_CVE-2017-12149.jar http://xxx:8080

#成功返回:
vuln6581362514513155613jboss
```

![截图2](./截图2.png)