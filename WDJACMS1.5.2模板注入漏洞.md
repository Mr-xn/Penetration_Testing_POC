## WDJACMS1.5.2模板注入漏洞  

### 根据官网啊的漏洞公告和GitHub提交记录对比  

[WDJA1.5.2漏洞公告](https://www.wdja.cn/news/?type=detail&id=3):  
在会员中心的地址管理中添加地址未进行过滤,会造成任意文件写入漏洞.  

[github提交记录](https://github.com/shadoweb/wdja/commit/eda57d4b803da920d0569eafd9abbddecb73ae65):  
可以看到注意改动文件为`php/passport/address/common/incfiles/manage_config.inc.php` 和 `php/passport/address/common/incfiles/module_config.inc.php` 文件都加了 `ii_htmlencode`函数进行过滤。  

### 审计流程大致可以看这里(来自合天智汇公众号作者-Xiaoleung)：[WDJA1.5.2网站内容管理系统模板注入漏洞](%E3%80%90%E4%BB%A3%E7%A0%81%E5%AE%A1%E8%AE%A1%E3%80%91WDJA1.5.2%E7%BD%91%E7%AB%99%E5%86%85%E5%AE%B9%E7%AE%A1%E7%90%86%E7%B3%BB%E7%BB%9F%E6%A8%A1%E6%9D%BF%E6%B3%A8%E5%85%A5%E6%BC%8F%E6%B4%9E.pdf)  