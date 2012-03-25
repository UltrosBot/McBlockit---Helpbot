# coding=utf-8
from system.irc import *
from system.utils import *
import sys

sys.path.append("./depends")

settings = ConfigParser()
settings.read("config/settings.ini")
factory = BotFactory()
reactor.connectTCP(settings.get("server", "server"), settings.getint("server", "port"), factory, 120)
del settings
colprint("|= Starting up..")
reactor.run()
colprint("0\n")