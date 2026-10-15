# 2022 祥云杯 Misc super_electric WriteUp
> 0431物联卫士实验室
> 来源：https://www.iotsec-zone.com/article/299

拿到题目，是个流量分析题，先看下流量分布。

![0.png](https://www.iotsec-zone.com/images/MdImg/50730825f7f0031717eadd816e9a7ece.png)

可以看出来，`IPv4-TCP-MMS`几乎占了绝大部分，而其他的协议占比也没有超出合理范围，那么这个流量包是让分析`MMS`协议基本上是板上钉钉的事了。

> mms协议主要应用在工控领域，属于是专业对口了。

那就筛选一下`mms`。

![1.png](https://www.iotsec-zone.com/images/MdImg/b1fbbaba95710439dd4ae1c90038e1f6.png)

发现从头到尾都有好多的`confirmed-RequestPDU`（这个消息类型的过滤器是`mms.confirmedServiceRequest`），而其他的几个消息类型又一般是没啥用的那种（用`mms && !mms.confirmedServiceRequest`过滤后可以看出确实没啥有用信息）。

> mms协议主要有`initiate-RequestPDU`、`confirmed-RequestPDU`、`initiate-ResponsePDU`、`confirmed-ResponsePDU`四种消息类型，其中`confirmed-RequestPDU`相对来说比较重要。

那就过滤一下`mms.confirmedServiceRequest`呗。

![2.png](https://www.iotsec-zone.com/images/MdImg/ad72cb1f07d2a6fc0d97921d593415d3.png)

发现除了开头那条是`LLN0$CO$FunEna1$SBOw`，后续不是`LLN0$CO$FunEna2$Oper`就是`LLN0$CO$FunEna1$Oper`，那目标已经很明确了，肯定是后两者咯。

先是`mms.itemId == "LLN0$CO$FunEna2$Oper"`看了下，发现从头到尾一直在传同一个值：`172.20.1.23`。

![3.png](https://www.iotsec-zone.com/images/MdImg/66fa210644b79a4f2ec5e337ad0cd059.png)

所以`LLN0$CO$FunEna2$Oper`大概是没啥用了，那就去看`LLN0$CO$FunEna1$Oper`呗。

![4.png](https://www.iotsec-zone.com/images/MdImg/42d2cf959f6ad84e2ebf15863f84696c.png)

这熟悉的`4d5a9000`开头，这不`exe`吗？那就`tshark`提取一下呗（还是老老实实用`cmd`跑`tshark`比较好，`pwsh`不知道为啥一直会报`tshark: "$" was unexpected in this context.`）。

```shell
tshark -r .\super_electric.pcapng -Y "mms.itemId == \"LLN0$CO$FunEna1$Oper\"" -T fields -e "mms.octet_string" > data.txt
```

![5.png](https://www.iotsec-zone.com/images/MdImg/789e5e84cb0ed304c580af682c50e43d.png)

提取结果是`hex`的：

![6.png](https://www.iotsec-zone.com/images/MdImg/ef337e2c1b730271f60519c691f983b0.png)

那么写个脚本输出成`exe`吧。

```python
data = b""
with open('data.txt', 'r') as f:
    for line in f:
        data += bytes.fromhex(line.strip())
with open("test.exe", 'wb') as f:
    f.write(data)
```

![7.png](https://www.iotsec-zone.com/images/MdImg/55a0c6240bb6a4ba7568d7e884a17a40.png)

那就开始逆向呗。

打开发现有窗口，那就找一下文本先。

![8.png](https://www.iotsec-zone.com/images/MdImg/1b7b571beeb999b574113d7278288db0.png)

![9.png](https://www.iotsec-zone.com/images/MdImg/0d545d20d00e675b56dc05d71c25d5cd.png)

发现有反调试相关函数名，不过应该问题不大，先去看看`crackme`那块有啥调用吧。

![10.png](https://www.iotsec-zone.com/images/MdImg/0accd11950f72c770e98c4c3be384b3f.png)

![11.png](https://www.iotsec-zone.com/images/MdImg/82bdd463ae386cabc229e4b2195fbd21.png)

应该是在创建窗口或者应用啥的，那么上面的`sub_43CB50`应该就是主函数了，跟过去看看。

![12.png](https://www.iotsec-zone.com/images/MdImg/bfa3201094dd0cf7eff278536d4d2bb8.png)

有个`aC96f278c370c43`常量，好像上面看字符串的时候见过，跟回去看看附近还有没有啥。

![13.png](https://www.iotsec-zone.com/images/MdImg/081d345b02a491c5c403f60f0bda087b.png)

有一堆不知道是啥的常量，直接`A`一下发现就是窗口上的各种文本和消息。（有些文本被ida解析成函数了，需要`U`一下然后`A`）

![14.png](https://www.iotsec-zone.com/images/MdImg/3a74e84cc19808e2c4b958ce5c6cc38f.png)

那就回去看看哪里触发了那个`恭喜`。

![15.png](https://www.iotsec-zone.com/images/MdImg/4210ab509483cb24b306120f0ff6e85a.png)

所以关键还是那个`C96F278C370C43299F1EE98257CCBD8A`，只不过这边`dword_449CB0`函数没解析出来是啥，过去看看定义发现应该是`Win32 Api`。

![16.png](https://www.iotsec-zone.com/images/MdImg/3c74c82332b55d1326c2df34c2520b63.png)

那就`x32dbg`调试一下看看，因为这玩意我记得能识别`Win32 Api`。

到调用点`43ccbd`看看，发现这个函数其实是`memcmp`。

![17.png](https://www.iotsec-zone.com/images/MdImg/ce57efca35fb79fcc2653de84e066bc3.png)

那有没有可能，输入的就是这一串，因为上面没见到啥复杂的处理逻辑或者其他调用。

于是输入了看看，发现确实是。

![18.png](https://www.iotsec-zone.com/images/MdImg/ced465283fbbea8569dfafc15442ebdf.png)

但是点`确定`之后就退出了，有点离谱...

于是命令行启动看看，猜测会不会是在`STDOUT`输出了东西。

结果输入完点`确定`后发现，根本不是正常退出，是异常了...

![19.png](https://www.iotsec-zone.com/images/MdImg/dcf618987f26e6ad4c501d877afe3edf.png)

去看了下系统日志，是`VC14`翻车了，啥情况啊。然后想起来之前打绿城杯线下有一题也是这个类似的情况（不过那题不是`VC14`翻的，但是都是最后环节过几秒钟异常）。

![20.png](https://www.iotsec-zone.com/images/MdImg/b814a7134c406317b06717c309b01c46.png)

绿城杯那题是因为作者写了个按条件触发的自解压的壳，然后因为我电脑环境问题好像触发了空指针。这题也是触发了空指针，难道这题也是自己写的壳？结合上面`pdb`路径里面带了个`upacker`，感觉真有可能。

不过当时为了保险起见，这种出现了异常的情况，肯定是先问问赛务比较靠谱。

![21.png](https://www.iotsec-zone.com/images/MdImg/3eb03a599bc1578478d3f68e982a370c.png)

结果赛务这回答，当时刚开始觉得好有道理，然后管理员运行、兼容性运行都给试了一遍，还是问题依旧。

然后突然醒悟，这回答不是命令行逆向题的标准回答吗？把我当小白了...赛务果然不靠谱。

然后后来我又小怼了一下，看出来回复确实才变成出题人的回复了。

![22.png](https://www.iotsec-zone.com/images/MdImg/2802d30b68437d12b78cae36ee0d1587.png)

但是看这意思是，出题人觉得正常情况下，点完确认是可以到下一阶段开始命令行交互的，然后大概会有在`STDOUT`写东西然后马上关闭？

那我这属于是环境问题导致完全不知道有下一阶段呗...搁这耽误了快两个小时是真离谱。

算了算了，确认有壳就行，找脱壳点吧。回到上面那个`恭喜`逻辑。

![23.png](https://www.iotsec-zone.com/images/MdImg/803490d097aa80f06f5242f3b7f13bb9.png)

相比于没输入正确，多了个调用，那就去`x32dbg`看看是啥函数的调用。

![24.png](https://www.iotsec-zone.com/images/MdImg/e8cc173fe6a83f1b7aea26e90e499bce.png)

是个`SendMessageA`，然后消息是`16`，这不是`WM_CLOSE`嘛...

那看来这个窗口应该是没啥脱壳逻辑了，往上追调用堆栈看看后续有没有吧。

然后一路追直接到了`start`函数。

![25.png](https://www.iotsec-zone.com/images/MdImg/f59576fd579e49bb4c3d9637cef425b1.png)

其中`sub_43CD50`是创建窗体的函数，那么下面还一堆内存处理的，咋看咋像脱壳，然后最后有个内存块当函数调用的，就更像是脱壳完后的入口地址了。

于是懒得看脱壳逻辑了，直接跑到最后这个调用点`43d4a6`然后`Scylla`一键脱了吧。

![26.png](https://www.iotsec-zone.com/images/MdImg/dab5a5142611b916542b86f75dce505a.png)

结果压根没跑到这个地方，触发啥异常了，应该是哪个地方有反调试插桩。那就从`sub_43CD50`的调用结束后下个断点然后单步跟呗。

结果连`sub_43CD50`还没结束就触发反调试了。

那就只能把这个异常给过滤掉了。

![27.png](https://www.iotsec-zone.com/images/MdImg/fd336b1ce2b2bb4b4cf5879336f457fd.png)

然后发现在调用`43d2a0`会触发另一个异常。

![28.png](https://www.iotsec-zone.com/images/MdImg/69fbaf5af556243f4cb9e4d6137597ca.png)

上ida一看，发现是个反调试，直接nop。

![29.png](https://www.iotsec-zone.com/images/MdImg/f4547e87103fa3a9cf7212c932771a81.png)

![30.png](https://www.iotsec-zone.com/images/MdImg/86f44ffb86d726379b118d8c609a54ca.png)

然后跟过去发现真有代码。

![31.png](https://www.iotsec-zone.com/images/MdImg/9be0d0f2b31cb3723d9cf4ed9ac85b91.png)

直接`Scylla`一把梭。

![32.png](https://www.iotsec-zone.com/images/MdImg/86a8caec3a16f5771f4f44f37d06514b.png)

![33.png](https://www.iotsec-zone.com/images/MdImg/8ba255cf30844d3a749d0e57b05102de.png)

不过无论是dump后的还是修复后的都依旧跑不起来，感觉还是踩到那个环境问题了。

不过无所谓，ida直接找到了真实的main函数，这就方便多了。

![34.png](https://www.iotsec-zone.com/images/MdImg/dfa39e310a9a9d9e0781ac72e4ebb13b.png)

似乎是需要输入什么东西然后异或`0x89`后和`byte_42D624`比较，但是这个输入的后续就没有使用了，而且咱们跑不起来，也就无所谓需要输入啥了，反正没地方输入。

然后下面开始循环异或下标，范围是`[0, 717)`，那就写个脚本看看这里解出来的结果是啥。

![35.png](https://www.iotsec-zone.com/images/MdImg/441f923595c8de73899441f6f7803bb2.png)

![36.png](https://www.iotsec-zone.com/images/MdImg/14720b247671b502b10c45aa0169c7bf.png)

```python
b = bytearray(bytes.fromhex("66736D6E2446747E787D65254F647E677563327A796579656C395B5E4F177772504E505704474F49495A494245274742405E4047145D574450555359365B4C502D612A2B2C652F2A3826383F6C2B222E375B332027302423783F363A3B06646A3D415F5E4442000B090E114C4C0C000B50171E12132E5B4642245A46415D5902A78BE9E6FDA5BBA7EAAEBEEFB5ECB9BFA0A1A3A3A0A6A1BDB2B3BD91F0BDA3BFCCC4CC8BCFC0DF8EA2C4CFD8DFCCC9CA908C92D193F1D997C1D6CF9BD9CBDBCDE0A7A7A6A8E9E6A1ADACA6EBBFA2EEBFB1A1B7A1F4A1BEBEB6F5FA97B5B6BBFF81C18A8C919683C7878FCA888D9F8A9CDCD1BD9D91D5949B978EDA9D8E9293DF6360746A6A62266E662E2A202C6F67617162717A7D3B6379707C6277757B67374840514B484C44095B414B19191B064455481B1D5C504E53515E5F48481517161B7B7373194F2F3168746A2D202C2914656B7F62095F3B322B2A3B3C397D637F0D041110050203474349081218081D47581D525E5419131950141F080F1C191AA9A1A7A3E8ACA6ADA8EAE2F9A4E1AEA2B0FDF7FDBCF8F3E4EBF8FDFEB5BDBBBFCC888E83C1CBC5C8CCC0C4CC8C908E88C5C5D49E8C929FBDD9DCC99B819DFFFA93EFACA6B3EDADA2B1E5EA8A899EE0829F95978C979795FBF8B0ACF2D6ADACB68E95CA818D8B87948B8083C58488968399978BDB959085D99D979989858D8AD76D6471706562632E21200028262724253A3B38393E3F3C3D32333031363734350A0B08090E0F0C0D02030001060704051A1B18191E1F1C1D12131011161714156A6B68696E6F6C6D62636061666764657A7B78797E7F7C7D72737071767774754A4B48494E4F4C4D42434041464744455A5B58595E5F5C5D5253505156575455AAABA8A9AEAFACADA2A3A0A1A6A7A4A5BABBB8B9BEBFBCBDB2B3B0B1B6B7B4B58A8B91C5C6C49093C9CD9DC99B95989886D4868580868F828980838F8E898D8FF2A3F0F2A6F7A4F6FFADA8F9C6"))
for i in range(len(b)):
    b[i] = 0xff & (b[i] ^ i)
print(b)
```

![37.png](https://www.iotsec-zone.com/images/MdImg/d74dce3afa9a16129504823e69494214.png)

发现蹦出来个`python`代码，这就是上面说的`You Got it!\nNow, try to resolve this crypto...\n`？这套娃...

![38.png](https://www.iotsec-zone.com/images/MdImg/e8012d0341302e42e12b3d37f8c8d0cc.png)

这已知`key`高位，然后`key`又被`sha256`了一波扔到`m`结尾去了，然后`message = message + bytes((l - len(message) % l) * chr(l - len(message) % l), encoding = 'utf-8')`就是`padding`操作，最后flag当成`iv`用，加密结果只告诉了低位。

这就是[ezAES](https://ctftime.org/writeup/23237)这题改的。

所以咱就按照这个wp的思路来。

首先`AES/CBC/PKCS7Padding`的特性有：
1. 分段加密，每段16字节，上一段的加密结果会当作下一段的`iv`去使用
2. 用来填充的数据每字节内容和其长度相等，如`01`、`0202`、`030303`这种

那么咱们就可以将加密结果的最后16字节和倒数第二个16字节取出来，即`78676e464395199424302b21b2b17db2`和`**********************3fba64ad7b`。

然后将`**********************3fba64ad7b`当成`iv`去解密`78676e464395199424302b21b2b17db2`，至于`key`，爆破就完事。

至于爆破是否正确的判断，当然是利用`padding`特性了，根据题目的加密脚本我们可以知道`m`的长度是`84+10=94`，也就是说需要填充`0202`，那咱们拿上面wp里的脚本改改就行：

```python
import binascii
from Crypto.Cipher import AES

def decrypt(message, passphrase, iv):
    aes = AES.new(passphrase, AES.MODE_CBC, iv)
    return aes.decrypt(message)

def find_key():
    keytmp = '4d9a700010437{}{}{}'
    for c1 in "0123456789abcdef":
        for c2 in"0123456789abcdef":
            for c3 in "0123456789abcdef":
                tmp = decrypt(
                    binascii.unhexlify('78676e464395199424302b21b2b17db2'),
                    keytmp.format(c1, c2, c3).encode('utf8'),
                    binascii.unhexlify('0' * 22 + '3fba64ad7b'),
                )
                if 2 == tmp[-1] == tmp[-2]:
                    print(keytmp.format(c1, c2, c3))

find_key()
```

![39.png](https://www.iotsec-zone.com/images/MdImg/4713f5b0decb7ee38392caf197f6d4fe.png)

所以`key`大概率就是`4d9a7000104376fe`了。

然后已知`m`和`key`求`iv`这个属于是密码学题目基本操作了，抄一下上面wp的脚本稍微改一下就行：

```python
import binascii
import hashlib
from Crypto.Cipher import AES

def encrypt(message,passphrase,iv):
    aes = AES.new(passphrase, AES.MODE_CBC, iv)
    return aes.encrypt(message)

def decrypt(message, passphrase, iv):
    aes = AES.new(passphrase, AES.MODE_CBC, iv)
    return aes.decrypt(message)

key = b"4d9a7000104376fe"
message = b"Do you ever feel, feel so paper thin, Like a house of cards, One blow from caving in"\
          + binascii.unhexlify(hashlib.sha256(key).hexdigest())[:10]\
          + b"\x02\x02"
IV = b'yellow_submarine'

arbitrary = binascii.hexlify(encrypt(message, key, IV))
encrypted = '******************************************************************************************************************************************************3fba64ad7b78676e464395199424302b21b2b17db2'.replace('*', '0')
encrypted = [encrypted[i:i+32] for i in range(0, len(encrypted), 32)]
arbitrary = [arbitrary[i:i+32] for i in range(0, len(arbitrary), 32)]

def guess_block(flag_block, correct_block, correct_iv):
    c1 = decrypt(binascii.unhexlify(flag_block), key, binascii.unhexlify(b'0' * 32))
    c2 = decrypt(binascii.unhexlify(correct_block), key, binascii.unhexlify(correct_iv))
    result = b''
    for i in range(16):
        result += bytes([c1[i] ^ c2[i]])
    return binascii.hexlify(result)

for i in range(1, len(arbitrary) + 1):
    if i == len(arbitrary):
        e2 = binascii.hexlify(IV)
    else:
        e2 = arbitrary[-i - 1]
    tmp = guess_block(encrypted[-i], arbitrary[-i], e2)
    if i == len(arbitrary):
        flag = binascii.unhexlify(tmp)
    else:
        encrypted[-i - 1] = tmp

print(flag.decode('utf8'))
```

所以最后flag就出来了。

![40.png](https://www.iotsec-zone.com/images/MdImg/ba77c1737232a6d45c5c8cd4002b5641.png)

> `flag{72713126e9b90eab}`
