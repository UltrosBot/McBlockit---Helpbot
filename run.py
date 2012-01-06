from system.irc import *
from system.utils import *
import sys

sys.path.append("./depends")
sys.path.append("./depends/colorama")

settings = ConfigParser()
settings.read("settings.ini")
factory = BotFactory()
reactor.connectTCP(settings.get("server", "server"), settings.getint("server", "port"), factory, 120)
del settings
colprint("12Starting 4reactor..0\n")
reactor.run()
colprint("0\n")