### Windows空格替换  

```
%COMMONPROGRAMFILES:~23,-5%
%ProgramFiles:~10,-5%
%CommonProgramFiles:~10,-18%
%COMMONPROGRAMFILES:~23,1%
%ProgramFiles:~10,1%
%CommonProgramFiles:~10,1%
%path:~10,1%
%PROCESSOR_IDENTIFIER:~7,1%

```
> 可通过 echo查看环境变量，然后找有空格的，从而造成其他命令通用的替换  

![](../img/windowsapce.png)

---------

还有另一种：形如这种`n^e^t^ u^s^e^r`  
![](../img/windowschar.png)

