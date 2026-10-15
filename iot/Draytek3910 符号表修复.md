# Draytek3910 符号表修复
> AiMiLiYa
> 来源：https://www.iotsec-zone.com/article/480

之前在社区看见好友发的一篇Draytek3910 文章十分感兴趣，也去看了看。
但是里面的shohod64.bin使用ida解析函数没有符号，让人看起来非常难受。
也是走过了很多弯路,网上也是找了一些方法和插件都没有什么用（也可能是我单纯不会用），最后还是想出来一个简单的方法去恢复。

在010中可以找到函数名（内部存在符号表）
![0.png](https://www.iotsec-zone.com/api/image/v2/20241105/d5dntpvr6xaw1oycuq.png)

首先使用readelf帮我们得到一些信息，再使用python脚本得到一个地址数据文本。
![1.png](https://www.iotsec-zone.com/api/image/v2/20241105/d5dnvpsrgs21jpj68z.png)

```python
import sys

def extract_addresses(file_content):
    results = []
    lines = file_content.strip().split('\n')
    
    # Flag to start extraction after finding '__ksymtab_strings'
    start_extraction = False
    
    for line in lines:
        parts = line.split()
        
        # Check if '___ksymtab+simple' is in the line
        if '___ksymtab+simple' in parts:
            start_extraction = True
        
        # Start extracting addresses after finding '__ksymtab_strings'
        if start_extraction:
            # Find the index of 'PROGBITS'
            if 'PROGBITS' in parts:
                progbits_index = parts.index('PROGBITS')
                # The address we want is the next element after 'PROGBITS'
                address = parts[progbits_index + 1]
                results.append(f'0x{address}')
            else:
                # Stop extraction if the line does not contain 'PROGBITS'
                break
    
    return results

def main():
    if len(sys.argv) != 2:
        print("Usage: python script.py <input_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    # Check if the input file has a .txt extension, if not, add it
    if not input_file.endswith('.txt'):
        input_file += '.txt'
    
    # Construct the output file name
    output_file = input_file.replace('.txt', '_out.txt')

    try:
        with open(input_file, 'r') as infile:
            file_content = infile.read()
    except FileNotFoundError:
        print(f"Error: File '{input_file}' not found.")
        sys.exit(1)

    extracted_data = extract_addresses(file_content)

    with open(output_file, 'w') as outfile:
        for data in extracted_data:
            outfile.write(data + '\n')

    print(f"Extracted data has been written to '{output_file}'")

if __name__ == "__main__":
    main()

```
执行脚本得到输出文件，输出内容如下。

![2.png](https://www.iotsec-zone.com/api/image/v2/20241105/d5dnwjpytkioe40bef.png)

接下来我们说明为什么要获取这样的数据，首先要知道该二进制程序为ARM64，小端序，然后使用ida跳转到随意一个获取地址处查看。
可知前此处前四个字节地址数据为0x4000C62C,后四个字节数据为0x42617100

![3.png](https://www.iotsec-zone.com/api/image/v2/20241105/d5dnww2dliseqirnbz.png)
而0x4000C62C是一个函数入口点地址

![4.png](https://www.iotsec-zone.com/api/image/v2/20241105/d5dnx5rc3upajixc0h.png)

0x42617100是一个函数名字符串地址

![5.png](https://www.iotsec-zone.com/api/image/v2/20241105/d5do3j6so4kc6syxu2.png)

那么我们就知道其实这是一个符号表，通过遍历该表即可恢复函数名。

接下来我们即可编写IDA脚本修复函数名即可了。
修复脚本：
```python
#ida 7.7 本人IDA是7.7 请注意自己版本是否兼容ida的API
import idaapi
import idc

def read_addresses(file_path):
    addresses = []
    with open(file_path, 'r') as file:
        for line in file:
            address = int(line.strip(), 16)
            addresses.append(address)
    return addresses

def fix_function_names(addresses):
    for addr in addresses:
        func_addr = idc.get_wide_dword(addr)  # 
        #print("func_addr: " + hex(func_addr))
        
        func_name_addr = idc.get_wide_dword(addr + 4)  # 读取 DWORD (4字节) 数据
        #print("func_name_addr: " + hex(func_name_addr))
        
        if func_name_addr != 0:  # 确保函数名字地址不是0
            func_name_str = idc.get_strlit_contents(func_name_addr)  # 获取函数名字符串
            
            if func_name_str:
                # 将字节字符串转换为普通字符串（仅在需要时）
                func_name_str = func_name_str.decode('utf-8') if isinstance(func_name_str, bytes) else func_name_str
                
                idc.set_name(func_addr, func_name_str, idc.SN_CHECK)  # 给函数重新命名
                print(f"Renamed function at {hex(func_addr)} to {func_name_str}")

def main():
    input_file = r'C:\Users\emt\Desktop\IDA_Pro_7.7\IDAMyPythonScript\input_file_out.txt'
    addresses = read_addresses(input_file)
    fix_function_names(addresses)
    print("Function renaming completed.")

if __name__ == "__main__":
    main()
```
执行完脚本之后查看修复效果，自我感觉良好。（可能没有修复完全，有知道的大佬请指教）
![6.png](https://www.iotsec-zone.com/api/image/v2/20241105/d5do0jpst0qq4a3uyd.png)
