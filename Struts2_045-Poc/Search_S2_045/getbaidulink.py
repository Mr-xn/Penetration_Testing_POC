#! -*- coding:utf-8 -*-

'''
通过百度搜索，搜索关键词，获取baidu_link
'''
__Date__="20170224"
__author__="nMask"
__Blog__="http://thief.one"

import requests
import urllib
import re

url="http://www.baidu.com/s?wd="
res=r"data-tools=[^,]*,\"url\":\"([^\"]*)\"\}\'"   ##正则

class getbaidulink:
	
	url_pc=["http://tousu.baidu.com/webmaster/add#4"]  ##要排除的url
	headers={'User-Agent':'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.1.6) Gecko/20091201 Firefox/3.5.6',
			'Referer':'http://www.baidu.com/link?url'}
	timeout=3

	def __init__(slef):
		pass


	def run(self,keyword,page="0",one_proxy=""):
		'''
		接收keyword,page,one_proxy参数
		* keyword  搜索的关键词
		* page     搜索结果第几页
		* one_proxy 代理地址
		'''

		list_url=[]
		urls=url+urllib.quote(keyword)+"&pn="+str(int(page)*10)
		try:
			r=requests.get(urls,proxies={'http':one_proxy},headers=getbaidulink.headers,timeout=getbaidulink.timeout)
			body=r.content
			# print body
			# print type(body)
		except Exception,e:
			print e
			list_url="error"
		else:
			if 'charset="gb2312"' in body:
				list_url="error"
				print body
			else:
				p=re.compile(res)
				list_url=p.findall(body)

				for i in getbaidulink.url_pc:
					if i in list_url:
						list_url.remove(i)

		return list_url #返回列表，如果访问出错，则返回的列表为空
		


if __name__=="__main__":
	cur=getbaidulink()
	list_url=cur.run(keyword='inurl:".action"',page=0,one_proxy="")
	print list_url
