from math import *
import urllib, urllib2, re, hashlib, random

class evalFunctions(object):

    def __init__(self, bot):
        self.bot = bot

    def wget(self, url):
        return urllib.urlopen(url).read()

    def seval(self, command):
        md5 = self.md5
        wget = self.wget
        randint = self.randint
        try:
            value = str(eval(command))
        except Exception as e:
            value = str(e)
        except SystemExit as e:
            value = "ERROR: Tried to call a SystemExit!"
        return value

    def randint(self, lo, hi):
        return random.randint(lo, hi)

    def md5(self, data):
        return hashlib.md5(data).hexdigest()