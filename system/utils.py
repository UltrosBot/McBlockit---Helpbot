# coding=utf-8
import re

def rht(data):
    # Utility, removes HTML from the input
    p = re.compile(r'<.*?>')
    try:
        return p.sub('', data.encode('ascii', 'ignore'))
    except:
        return "Unable to decode in regex."