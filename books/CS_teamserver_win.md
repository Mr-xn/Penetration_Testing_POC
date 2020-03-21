CS的teamserver经常是在linux服务器上跑的，有小伙伴问在win server上怎么跑，所以弄了一个批处理，需要的看着改改，win上面需要装[`java JDK`](http://www.oracle.com/technetwork/java/javase/downloads/jdk8-downloads-2133151.html),win上默认没有keytool,所以需要自己去生成一个cobaltstrike.store ~  

```
@echo off   
:check_java
    java -version >nul 2>&1
    if %errorLevel% == 0 (
        goto:check_permissions
    ) else (
        echo [-] is Java installed?
        goto:eof
    )
    
:check_permissions
    echo [+] Administrative permissions required. Detecting permissions...
    set TempFile_Name=%SystemRoot%\System32\BatTestUACin_SysRt%Random%.batemp
    (echo "BAT Test UAC in Temp" >%TempFile_Name% ) 1>nul 2>nul
    if exist %TempFile_Name% (
        echo [+] Success: Administrative permissions confirmed.
	del %TempFile_Name% 1>nul 2>nul
        goto:check_certificate
    ) else (
        echo [-] Failure: Current permissions inadequate.
        goto:eof
    )

:check_certificate
    set certificate=".\cobaltstrike.store"
    if exist %certificate% (
        goto:test_arguments
    ) else (
        echo [!] Please generate the cobaltstrike.store !
        echo [!] Example: keytool -keystore ./cobaltstrike.store -storepass 123456 -keypass 123456 -genkey -keyalg RSA -alias cobaltstrike -dname "CN=Major Cobalt Strike, OU=AdvancedPenTesting, O=cobaltstrike, L=Somewhere, S=Cyberspace, C=Earth"
        goto:eof
    )
    
:test_arguments
    set argC=0
    for %%x in (%*) do Set /A argC+=1
    if %argC% LSS 2 (
        echo [-] teamserver ^<host^> ^<password^> [/path/to/c2.profile] [YYYY-MM-DD]
        echo     ^<host^> is the default IP address of this Cobalt Strike team server
        echo     ^<password^> is the shared password to connect to this server
        echo     [/path/to/c2.profile] is your Malleable C2 profile
        echo     [YYYY-MM-DD] is a kill date for Beacon payloads run from this server
        goto:eof
    ) else (
        goto:run_cobal
    )
:run_cobal
    java -XX:ParallelGCThreads=4 -Dcobaltstrike.server_port=50050 -Djavax.net.ssl.keyStore=./cobaltstrike.store -Djavax.net.ssl.keyStorePassword=123456 -server -XX:+AggressiveHeap -XX:+UseParallelGC -classpath ./cobaltstrike.jar server.TeamServer %*
```

![img](./books/img/17.png) 

