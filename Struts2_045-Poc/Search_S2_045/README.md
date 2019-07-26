
通过搜索引擎获取网站存在的.action、.do链接，并调用s2_045检测模块对这些链接进行批量检测。

### Usage
#### 运行流程
* 填写url.txt
* python search_url.py 检测url.txt文件中域名生成result_all.txt文件
* python s2_045_judge.py 检测result_all.txt文件中url生成result.txt文件

#### 文件说明
* url.txt为待检测网站域名（不用http,也不用目录端口）
* result_all.txt为检测网站所有.action/.do地址
* result.txt为最终存在漏洞的url地址文件 

