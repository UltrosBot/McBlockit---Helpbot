from math import *
import urllib, urllib2, re, hashlib, random

def wget(url):
    return urllib.urlopen(url).read()

def seval(command):
    try:
        value = str(eval(command), {"quit": None, "input": None, "raw_input": None, "exit": None, "__import__": None})
    except Exception as e:
        value = str(e)
    except SystemExit as e:
        value = "ERROR: Tried to call a SystemExit!"
    return value

def randint(lo, hi):
    return random.randint(lo, hi)

def md5(data):
    return hashlib.md5(data).hexdigest()