from math import *
import urllib, urllib2, re, hashlib, random, time

class evalFunctions(object):

    def __init__(self, bot):
        self.bot = bot

    def seval(self, command, cinfo):
        user = cinfo["user"]
        host = cinfo["hostmask"]
        origin = cinfo["origin"]
        message = cinfo["message"]
        target = cinfo["target"]

        md5 = self.md5
        wget = self.wget
        randint = self.randint
        msg = self.msg
        notice = self.notice

        del self
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

    def wget(self, url):
        return urllib.urlopen(url).read()

    def msg(self, target, message, flag=False):
        try:
            self.bot.sendmsg(target, message)
        except:
            if flag:
                return "Couldn't send message!"
            else:
                return ""
        else:
            if flag:
                return "Message sent!"
            else:
                return ""

    def notice(self, target, message, flag=False):
        try:
            self.bot.sendnotice(target, message)
        except:
            if flag:
                return "Couldn't send notice!"
            else:
                return ""
        else:
            if flag:
                return "Message sent!"
            else:
                return ""

    def join(self, channel, flag=False):
        return "Not implemented!"

    def part(self, channel, message="Leaving", flag=False):
        return "Not implemented!"

    def kick(self, channel, target, message, flag=False):
        return "Not implemented!"

    def mode(self, channel, modes, flag=False):
        return "Not implemented!"