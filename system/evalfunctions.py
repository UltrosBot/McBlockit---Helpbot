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
        #except SystemExit as e:
        #    value = "ERROR: Tried to call a SystemExit!"
        return value

    def randint(self, lo, hi):
        return random.randint(lo, hi)

    def md5(self, data):
        return hashlib.md5(data).hexdigest()

    def wget(self, url):
        page = urllib.urlopen(url)
        test = self.wtest(page)
        if not test[0]:
            return test[1]
        else:
            return self.rht(page.read())

    def wtest(self, message):
        info = message.info()
        typec = info["Content-Type"]
        try:
            length = int(info["Content-Length"])
        except:
            length = 0
        if message.geturl().startswith("file://"):
            return "Local file access is not allowed."
        if not (typec == "text/html" or typec == "text/plain"):
            return [False, "Content-Type " + typec + " is not allowed."]
        elif length > 51200:
            return [False, "Content is greater than 50KB in size."]
        return [True]

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

    def rht(self, data):
    # Utility, removes HTML from the input
        p = re.compile(r'<.*?>')
        try:
            return p.sub('', data.encode('ascii','ignore'))
        except:
            return "Unable to parse HTML."