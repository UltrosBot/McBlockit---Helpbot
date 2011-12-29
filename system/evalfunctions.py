from math import *
import urllib, urllib2, re, hashlib, random

def wget(url):
    return urllib.urlopen(url).read()

def seval(command):
    return str(eval(command), {"quit": None, "input": None, "raw_input": None, "exit": None, "__import__": None})

def randint(lo, hi):
    return random.randint(lo, hi)

def md5(data):
    return hashlib.md5(data).hexdigest()