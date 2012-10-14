# coding=utf-8
from system.irc import *
from system.yaml_loader import *
import sys

sys.path.append("./depends")

settings = yaml_loader().load("config/settings.yml")
factory = BotFactory()
reactor.connectTCP(
    settings["connection"]["host"],
    settings["connection"]["port"],
    factory, 120)
del settings
colprint("|= Starting up..")
reactor.run()
colprint("0\n")