#! -*- coding:utf-8 -*-

'''
传入：baidu_link  输出：真实网站url
'''
import requests
import re

res_baidu=r"window\.location\.replace\(\"([^\"]*)\"\)"


class anbaidulink:
	headers={'User-Agent':'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.1.6) Gecko/20091201 Firefox/3.5.6',
			 'Referer':'http://www.baidu.com/link?url='}
	def __init__(self):
		pass

	def run(self,url,one_proxy=""):
		'''
		入口函数，接受baidu_link以及代理地址，默认为""，代理地址要是http://xx.xx.xx.xx:xx格式
		'''
		if "&eqid=" in url:
			url=self.have_eqid(url,one_proxy)
		else:
			url=self.noeqid(url,one_proxy)

		return url

	def noeqid(self,url,one_proxy):
		'''
		针对baidu_link中没有eqid参数
		'''
		try:
			h=requests.head(url,proxies={'http':one_proxy},headers=anbaidulink.headers,timeout=5).headers  #
		except Exception,e:
			print e
		else:
			url=h["location"]

		return url
				
			
	def have_eqid(self,url,one_proxy):
		'''
		针对baidu_link中存在eqid参数
		'''
		try:
			body=requests.get(url,proxies={'http':one_proxy},headers=anbaidulink.headers,timeout=5).content  #
		except Exception,e:
			print e
		else:
			p=re.compile(res_baidu)
			url=p.findall(body)
			if len(url)>0:
				url=url[0]

		return url




if __name__=="__main__":
	cur=anbaidulink()
	url_1=cur.run(url='https://www.baidu.com/link?url=1qIAIIh_2N7LUQpI0AARembLK2en4QpGjaRqKZ3BxYtzoZYevC5jA2jq6XMwgEKF&wd=&eqid=9581fbec0007eae00000000458200ad4',one_proxy="")
	#url_2=cur.run(url='http://www.baidu.com/link?url=1qIAIIh_2N7LUQpI0AARembLK2en4QpGjaRqKZ3BxYtzoZYevC5jA2jq6XMwgEKF',one_proxy="")
	print url_1
	#print url_2