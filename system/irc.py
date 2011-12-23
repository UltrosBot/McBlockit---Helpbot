import sys, os, random, time, math
import thread, socket, re, htmlentitydefs
import urllib2 as urllib

from utils import *

from ConfigParser import RawConfigParser as ConfigParser
from twisted.internet import reactor, protocol
from twisted.internet.protocol import Factory
from twisted.words.protocols import irc
from colours import *

from system.constants import *
from system import faq

from depends import mcbans_api as mcbans

class Bot(irc.IRCClient):

    # Extensions the page title parser shouldn't parse
    notParse = ["png", "jpg", "jpeg", "tiff", "bmp", "ico", "gif"]

    # Channels
    joinchans = []
    channels = []
    stfuchans = []
    
    chanlist = {}
    
    firstjoin = 1

    # Message queues
    messagequeue = []
    noticequeue = []
    
    # Quit quotes
    quotes = []
    
    # User system
    authorized = {}
    users = {}

    # Special IRC chars
    col = "" # Colour code
    bold = "" # Bold code
    under = "" # Underline code
    ital = "" # Italics code
    reverse = "" # Reverse code
    ctcp = "\1" # CTCP code, as if we'll ever need this
    
    def prnt(self, msg):
        msg = string.replace(msg, self.bold, "")
        msg = string.replace(msg, self.under, "")
        msg = string.replace(msg, self.ital, "")
        msg = string.replace(msg, self.reverse, "")
        colprint(msg)
        self.logfile.write("%s\n" %(colstrip(msg)))
        self.flush()
        
    def parseQuotes(self):
        try:
            self.prnt("Reading in quit quotes from quits.txt...")
            file = open("quotes.txt", "r")
            data = file.read()
            self.quotes = data.split("\n")
            self.prnt("Read %s quotes." % len(self.quotes))
        except:
            return False
        else:
            return True
    
    def parseSettings(self):
        try:
            self.prnt("Reading in settings from settings.ini...")
            oldchans = self.joinchans
            settings = ConfigParser()
            settings.read("settings.ini")
            channels = settings.items("channels")
            for element in self.joinchans:
                self.joinchans.remove(element)
            for element in channels:
                self.joinchans.append(element)
                if not element in oldchans and not self.firstjoin == 1:
                    self.join("#%s" % element[0])
            for element in oldchans:
                if element not in self.joinchans and not self.firstjoin == 1:
                    self.part("#%s" % element[0])
            self.password = settings.get("info", "password")
            if not self.firstjoin == 1:
                self.sendmsg("nickserv", "IDENTIFY %s" % self.password)
            self.loginpass = settings.get("info", "loginpass")
            self.control_char = settings.get("info", "control_character")
            self.data_dir = settings.get("info", "data_folder")
            self.index_file = settings.get("info", "index_file")
            self.api_key = settings.get("mcbans", "api_key")
        except:
            return False
        else:
            self.prnt("Done!")
            return True
    
    def __init__(self):
        # What's the name of our logfile?
        self.logfile = open("output.log", "a")
        
        if not(self.parseSettings()):
            self.prnt("Unable to parse settings.ini. Does it exist? Bot will now quit.")
            reactor.stop()
            exit()
        if not(self.parseQuotes()):
            self.prnt("Unable to parse quotes.txt. Does it exist? Bot will now quit.")
            reactor.stop()
            exit()
        self.faq = faq.FAQ(self.data_dir)
        self.faq.listentries()
        self.mcb = mcbans.McBans(self.api_key)
        #Start the two loops for sending messages and notices
        self.messageLoop()
        self.noticeLoop()
    
    def flush(self):
        self.logfile.flush()
    
    def connectionLost(self, reason):
        # We lost connection. GTFO tiem.
        self.prnt("***Shutting down!***")
        self.flush()
    
    @property
    def nickname(self):
        return self.factory.nickname

    def signedOn(self):
        # OK, we logged on successfully.
        # Log that we signed on.
        self.prnt("***Signed on as %s.***" % self.nickname)
        # Log in with NickServ.
        self.sendmsg("NickServ", "IDENTIFY %s" % self.password)
        # Join all the channels in the file, as parsed earlier.
        for element in self.joinchans:
            self.join(element[0])
        # Flush the logfile - so we can read it.
        self.flush()

    def joined(self, channel):
        # We joined a channel
        self.prnt("***Joined %s***" % channel)
        self.channels.append(channel)
        if self.firstjoin == 1:
            self.firstjoin = 0
        # Flush the logfile
        self.who(channel)
        self.flush()
    
    def is_op(self, channel, user):
        if channel in self.chanlist.keys():
            if user in self.chanlist[channel].keys():
                return self.chanlist[channel][user]["op"]
            return False   
        return False
    
    def is_voice(self, channel, user):
        if channel in self.chanlist.keys():
            if user in self.chanlist[channel].keys():
                return self.chanlist[channel][user]["op"]
            return False   
        return False
    
    def set_op(self, channel, user, data):
        if isinstance(data, bool):
            if channel in self.chanlist.keys():
                if user in self.chanlist[channel].keys():
                    self.chanlist[channel][user]["op"] = data
        else:
            raise ValueError("'data' must be either True or False")
    
    def set_voice(self, channel, user, data):
        if isinstance(data, bool):
            if channel in self.chanlist.keys():
                if user in self.chanlist[channel].keys():
                    self.chanlist[channel][user]["op"] = data
        else:
            raise ValueError("'data' must be either True or False")
                    
    def privmsg(self, user, channel, msg):
        # We got a message.
        # Define the userhost
        userhost = user
        # Get the username
        send = self.sendnotice
        if channel == self.nickname:
            send = self.sendmsg
        user = user.split("!", 1)[0]
        authorized = False
        authtype = 0
        if self.is_op(channel, user) and user in self.authorized.keys():
            authorized = True
            authtype = 3
        elif self.is_op(channel, user):
            authorized = True
            authtype = 1
        elif user in self.authorized.keys():
            authorized = True
            authtype = 2
        if msg.startswith("http://") or msg.startswith("https://"):
            thread.start_new_thread(self.pagetitle, (channel, msg.split(" ")[0]))
        elif msg.startswith(self.control_char) or channel == self.nickname:
            command = msg.split(" ")[0].replace(self.control_char, "", 1)
            arguments = msg.split(" ")
            if command == "help":
                if len(arguments) < 2:
                    send(user, "Syntax: %shelp <topic>" % self.control_char)
                    send(user, "Available topics: about, login, logout, lookup")
                    if authorized:
                        send(user, "Admin topics: raw, quit")
                else:
                    if arguments[1] == "about":
                        send(user, "I'm the #MCBans IRC helper bot.")
                        send(user, "I live in #mcbans on irc.esper.net")
                    elif arguments[1] == "auth":
                        send(user, "Auth is managed with %slogin and %slogout." % (self.control_char, self.control_char))
                        send(user, "If you change your nick, you will be logged out automatically.")
                        send(user, "Channel ops also have some access.")
                    elif arguments[1] == "login":
                        send(user, "Syntax: %slogin <password>" % self.control_char)
                        send(user, "Logs you into the bot using a password set by the bot owner.")
                        send(user, "See %shelp auth for more information." % self.control_char)
                    elif arguments[1] == "logout":
                        send(user, "Syntax: %slogout" % self.control_char)
                        send(user, "Logs you out of the bot, provided you were already logged in.")
                        send(user, "See %shelp auth for more information." % self.control_char)
                    elif arguments[1] == "lookup":
                        send(user, "Syntax: %slookup <user> [type]" % self.control_char)
                        send(user, "Used to make a lookup on the MCBans site, using the v2 API.")
                        send(user, "Type is optional, but it can be local, global, minimal or all. If it is missing, it is presumed to be minimal.")
                    elif arguments[1] == "ping":
                        send(user, "Syntax: %sping <ip>" % self.control_char)
                        send(user, "Retrieves the server information from a Beta/Release server.")
                        send(user, "Can be useful to check if a server is accepting connections.")
                    elif user in self.authorized.keys():
                        if arguments[1] == "raw":
                            send(user, "Syntax: %sraw <data>" % self.control_char)
                            send(user, "Sends raw data to the server.")
                        elif arguments[1] == "quit":
                            send(user, "Syntax: %squit [message]" % self.control_char)
                            send(user, "Makes the bot quit, with an optional user-defined message.")
                            send(user, "If no message is defined, uses a random quote.")
                    else:
                        send(user, "Unknown help topic: %s" % arguments[1])
            elif command == "login":
                if len(arguments) < 2:
                    send(user, "Syntax: %slogin <password>" % self.control_char)
                    send(user, "The password is set by the owner of the bot.")
                else:
                    passw = arguments[1]
                    if passw == self.loginpass:
                        self.authorized[user] = userhost.split("!", 1)[1]
                        send(user, "You have been logged in successfully.")
                        self.prnt("%s logged in successfully." % user)
                    else:
                        send(user, "Incorrect password! Check for case and spacing!")
                        self.prnt("%s tried to log in with an invalid password!" % user)
                    self.flush()
                    return
            elif command == "logout":
                if user in self.authorized.keys():
                    del self.authorized[user]
                    send(user, "You have been logged out successfully.")
                else:
                    send(user, "You were never logged in. Please note that you are logged out automatically when you nick.")
            elif command == "quit":
                if authorized and authtype > 1:
                    if len(arguments) < 2:
                        self.squit()
                    else:
                        self.squit(" ".join(arguments[1:]))
                else:
                    send(user, "You do not have access to this command.")
            elif command == "raw":
                if authorized and authtype > 1:
                    if not len(arguments) < 2:
                        send(user, "Done!")
                        self.sendLine(" ".join(arguments[1:]))
                    else:
                        send(user, "Syntax: %sraw <data>" % self.control_char)
                else:
                    send(user, "You do not have access to this command.")
            elif command == "lookup":
                if len(arguments) > 1:
                    data = self.mcb.lookup(arguments[1], user)
                    try:
                        error = data["error"]
                        if authorized:
                            self.sendmsg(channel, "Error: %s" % data["error"])
                        else:
                            send(user, "Error: %s" % data["error"])
                    except:
                        if len(arguments) > 2:
                            type = arguments[2]
                            if type == "local":
                                if authorized:
                                    self.sendmsg(channel, "Listing local bans for %s..." % arguments[1])
                                    if len(data["local"]) > 0:
                                        for element in data["local"]:
                                            server = element.split(" .:. ")[0].encode("ascii", "ignore")
                                            reason = element.split(" .:. ")[1].encode("ascii", "ignore")
                                            self.sendmsg(channel, "%s: %s" % (server, reason.decode('string_escape')))
                                    else:
                                        self.sendmsg(channel, "No local bans.")
                                else:
                                    send(user, "Listing local bans for %s..." % arguments[1])
                                    if len(data["local"]) > 0:
                                        for element in data["local"]:
                                            server = element.split(" .:. ")[0].encode("ascii", "ignore")
                                            reason = element.split(" .:. ")[1].encode("ascii", "ignore")
                                            send(user, "%s: %s" % (server, reason.decode('string_escape')))
                                    else:
                                        send(user, "No local bans.")
                            elif type == "global":
                                if authorized:
                                    self.sendmsg(channel, "Listing global bans for %s..." % arguments[1])
                                    if len(data["global"]) > 0:
                                        for element in data["global"]:
                                            server = element.split(" .:. ")[0].encode("ascii", "ignore")
                                            reason = element.split(" .:. ")[1].encode("ascii", "ignore")
                                            self.sendmsg(channel, "%s: %s" % (server, reason.decode('string_escape')))
                                    else:
                                        self.sendmsg(channel, "No global bans.")
                                else:
                                    send(user, "Listing global bans for %s..." % arguments[1])
                                    if len(data["global"]) > 0:
                                        for element in data["global"]:
                                            server = element.split(" .:. ")[0].encode("ascii", "ignore")
                                            reason = element.split(" .:. ")[1].encode("ascii", "ignore")
                                            send(channel, "%s: %s" % (server, reason.decode('string_escape')))
                                    else:
                                        send(user, "No global bans.")
                            elif type == "minimal":
                                if authorized:
                                    self.sendmsg(channel, "Reputation for %s: %.2f/10" % (arguments[1], data["reputation"]))
                                    self.sendmsg(channel, "Total bans: %s" % data["total"])
                                else:
                                    send(user, "Reputation for %s: %.2f/10" % (arguments[1], data["reputation"]))
                                    send(user, "Total bans: %s" % data["total"])
                            elif type == "all":
                                if authorized:
                                    self.sendmsg(channel, "Listing everything for %s..." % arguments[1])
                                    self.sendmsg(channel, "Reputation for %s: %.2f/10" % (arguments[1], data["reputation"]))
                                    self.sendmsg(channel, "Total bans: %s" % data["total"])
                                    self.sendmsg(channel, "Listing local bans for %s..." % arguments[1])
                                    if len(data["local"]) > 0:
                                        for element in data["local"]:
                                            server = element.split(" .:. ")[0].encode("ascii", "ignore")
                                            reason = element.split(" .:. ")[1].encode("ascii", "ignore")
                                            self.sendmsg(channel, "%s: %s" % (server, reason.decode('string_escape')))
                                    else:
                                        self.sendmsg(channel, "No local bans.")
                                    self.sendmsg(channel, "Listing global bans for %s..." % arguments[1])
                                    if len(data["global"]) > 0:
                                        for element in data["global"]:
                                            server = element.split(" .:. ")[0].encode("ascii", "ignore")
                                            reason = element.split(" .:. ")[1].encode("ascii", "ignore")
                                            self.sendmsg(channel, "%s: %s" % (server, reason.decode('string_escape')))
                                    else:
                                        self.sendmsg(channel, "No global bans.")
                                else:
                                    send(user, "Listing everything for %s..." % arguments[1])
                                    send(user, "Listing everything for %s..." % arguments[1])
                                    send(user, "Reputation for %s: %.2f/10" % (arguments[1], data["reputation"]))
                                    send(user, "Total bans: %s" % data["total"])
                                    send(user, "Listing local bans for %s..." % arguments[1])
                                    if len(data["local"]) > 0:
                                        for element in data["local"]:
                                            server = element.split(" .:. ")[0].encode("ascii", "ignore")
                                            reason = element.split(" .:. ")[1].encode("ascii", "ignore")
                                            send(user, "%s: %s" % (server, reason.decode('string_escape')))
                                    else:
                                        send(user, "No local bans.")
                                    send(user, "Listing global bans for %s..." % arguments[1])
                                    if len(data["global"]) > 0:
                                        for element in data["global"]:
                                            server = element.split(" .:. ")[0].encode("ascii", "ignore")
                                            reason = element.split(" .:. ")[1].encode("ascii", "ignore")
                                            send(user, "%s: %s" % (server, reason.decode('string_escape')))
                                    else:
                                        send(user, "No global bans.")
                            else:
                                if authorized:
                                    self.sendmsg(channel, "Reputation for %s: %.2f/10" % (arguments[1], data["reputation"]))
                                    self.sendmsg(channel, "Total bans: %s" % data["total"])
                                else:
                                    send(user, "Reputation for %s: %.2f/10" % (arguments[1], data["reputation"]))
                                    send(user, "Total bans: %s" % data["total"])
                        else:
                            if authorized:
                                self.sendmsg(channel, "Reputation for %s: %.2f/10" % (arguments[1], data["reputation"]))
                                self.sendmsg(channel, "Total bans: %s" % data["total"])
                            else:
                                send(user, "Reputation for %s: %.2f/10" % (arguments[1], data["reputation"]))
                                send(user, "Total bans: %s" % data["total"])
                else:
                    send(user, "Syntax: %slookup <user> [type]" % self.control_char)
            elif command == "ping":
                derp = 0
                if len(arguments) > 1:
                    ip = arguments[1]
                    if ":" in ip:
                        server, port = ip.split(":", 1)
                        try:
                            port = int(port)
                        except:
                            if authorized:
                                self.sendmsg(channel, "%s is an invalid port number." % port)
                            else:
                                send(user, "%s is an invalid port number." % port)
                            derp = 1
                    else:
                        server, port = ip, 25565
                    if derp is 0:
                        try:
                            timing = time.time()
                            s = socket.socket(
                                socket.AF_INET, socket.SOCK_STREAM)
                            s.settimeout(5.0)
                            s.connect((server, port))
                            ntiming = time.time()
                            elapsed = ntiming - timing
                            msec = math.floor(elapsed * 1000.0 )
                            s.send("\xFE")
                            data = s.recv(1)
                            
                            if data.startswith("\xFF"):
                                data = s.recv(255)
                                s.close()
                                data = data[3:]
                                finlist = data.split("\xA7")

                                finished = []

                                for element in finlist:
                                    donestr = ""
                                    for character in element:
                                        if ord(character) in range(128) and not ord(character) == 0:
                                            donestr = donestr + character.encode("ascii", "ignore")
                                    finished.append(donestr.strip("\x00"))
                            
                                if authorized:
                                    self.sendmsg(channel, "Server info: %s (%s/%s) [Latency: %smsec]" % (finished[0], finished[1], finished[2], msec))
                                else:
                                    send(user, "Server info: %s (%s/%s) [Latency: %smsec]" % (finished[0], finished[1], finished[2], msec))
                            else:
                                if authorized:
                                    self.sendmsg(channel, "That doesn't appear to be a Minecraft server.")
                                else:
                                    send(user, "That doesn't appear to be a Minecraft server.")
                        except Exception as e:
                            if authorized:
                                self.sendmsg(channel, "Error: %s" % e)
                            else:
                                send(user, "Error: %s" % e)
            elif command == "stfu":
                if authorized:
                    if not channel in self.stfuchans:
                        self.stfuchans.append(channel)
                        send(user, "No longer parsing page titles in %s ." % channel)
                    else:
                        send(user, "Already stfu'd in %s ." % channel)
                else:
                    send(user, "You do not have access to this command.")
            elif command == "speak":
                if authorized:
                    if channel in self.stfuchans:
                        self.stfuchans.remove(channel)
                        send(user, "Parsing page titles in %s again." % channel)
                    else:
                        send(user, "Already parsing page titles in %s ." % channel)
                else:
                    send(user, "You do not have access to this command.")
        elif msg.startswith("??"):
            parts = msg.split(" ")
            if len(parts) > 1:
                if parts[0] == "??": # Check in channel
                    if len(parts) > 1:
                        data = self.faq.get(parts[1].lower())
                        if data[0]:
                            for element in data[1]:
                                self.sendmsg(channel, "(%s) %s" % (parts[1].lower(), element))
                        else:
                            if data[1] is ERR_NO_SUCH_ENTRY:
                                send(user, "No such entry: %s" % parts[1].lower())
                            else:
                                send(user, "Unable to load entry: %s" % parts[1].lower())
                    else:
                        send(user, "Please provide a help topic. For example: ?? help")
                elif parts[0] == "??>": # Check in channel with target
                    if len(parts) > 2:
                        data = self.faq.get(parts[2].lower())
                        if data[0]:
                            for element in data[1]:
                                self.sendmsg(channel, "%s: (%s) %s" % (parts[1], parts[2].lower(), element))
                        else:
                            if data[1] is ERR_NO_SUCH_ENTRY:
                                send(user, "No such entry: %s" % parts[2].lower())
                            else:
                                send(user, "Unable to load entry: %s" % parts[2].lower())
                    else:
                        send(user, "Please provide a help topic and target user. For example: ??> helpme help")
                elif parts[0] == "??>>": # Check in message to target
                    if len(parts) > 2:
                        data = self.faq.get(parts[2].lower())
                        if data[0]:
                            for element in data[1]:
                                self.sendmsg(parts[1], "(%s) %s" % (parts[2].lower(), element))
                            send(user, "Topic '%s' has been sent to %s." % (parts[2].lower(), parts[1]))
                        else:
                            if data[1] is ERR_NO_SUCH_ENTRY:
                                send(user, "No such entry: %s" % parts[2].lower())
                            else:
                                send(user, "Unable to load entry: %s" % parts[2].lower())
                    else:
                        send(user, "Please provide a help topic and target user. For example: ??>> helpme help")
                elif parts[0] == "??<": # Check in message to self
                    if len(parts) > 1:
                        data = self.faq.get(parts[1].lower())
                        if data[0]:
                            for element in data[1]:
                                send(user, "(%s) %s" % (parts[1].lower(), element))
                        else:
                            if data[1] is ERR_NO_SUCH_ENTRY:
                                send(user, "No such entry: %s" % parts[1].lower())
                            else:
                                send(user, "Unable to load entry: %s" % parts[1].lower())
                    else:
                        send(user, "Please provide a help topic. For example: ??< help")
                elif parts[0] == "??+": # Add or append to a topic
                    if authorized:
                        if len(parts) > 2:
                            data = self.faq.set(parts[1].lower(), " ".join(parts[2:]), MODE_APPEND)
                            self.faq.listentries()
                            if data[0]:
                                send(user, "Successfully added to the topic: %s" % parts[1].lower())
                            else:
                                send(user, "Unable to add to the topic: %s" % parts[1].lower())
                                if data[1] is ERR_NO_SUCH_ENTRY:
                                    send(user, "Entry does not exist.")
                                else:
                                    send(user, "Please report this to the MCBans staff.")
                        else:
                            send(user, "Please provide a help topic and some data to append. For example: ??+ help This is what you do..")
                    else:
                        send(user, "You do not have access to this command.")
                elif parts[0] == "??~": # Add or replace topic
                    if authorized:
                        if len(parts) > 2:
                            data = self.faq.set(parts[1].lower(), " ".join(parts[2:]), MODE_REPLACE)
                            self.faq.listentries()
                            if data[0]:
                                send(user, "Successfully replaced topic: %s" % parts[1].lower())
                            else:
                                send(user, "Unable to replace the topic: %s" % parts[1].lower())
                                if data[1] is ERR_NO_SUCH_ENTRY:
                                    send(user, "Entry does not exist.")
                                else:
                                    send(user, "Please report this to the MCBans staff.")
                        else:
                            send(user, "Please provide a help topic and some data to use. For example: ??~ help This is what you do..")
                    else:
                        send(user, "You do not have access to this command.")
                elif parts[0] == "??-": # Remove topic
                    if authorized:
                        if len(parts) > 1:
                            data = self.faq.set(parts[1].lower(), '', MODE_REMOVE)
                            self.faq.listentries()
                            if(data[0]):
                                send(user, "Successfully removed the topic: %s" % parts[1].lower())
                            else:
                                send(user, "Unable to remove the topic: %s" % parts[1].lower())
                                if data[1] is ERR_NO_SUCH_ENTRY:
                                    send(user, "Entry does not exist.")
                                else:
                                    send(user, "Please report this to the MCBans staff.")
                        else:
                            send(user, "Please provide a help topic to remove. For example: ??- help")
                    else:
                        send(user, "You do not have access to this command.")
        # Flush the logfile
        self.flush()
        # Log the message
        self.prnt("<%s:%s> %s" % (user, channel, msg))

    def pagetitle(self, target, url):
        if not target in self.stfuchans:
            try:
                if not url.split(".")[-1] in self.notParse:
                    isHTTPS = 0
                    domain = ""
                    if url.startswith("http://"):
                        domain = url.split("http://")[1].split("/")[0]
                        isHTTPS = 0
                    elif url.startswith("https://"):
                        domain = url.split("https://")[1].split("/")[0]
                        isHTTPS = 1
                    try:
                        request = urllib.Request(url, "", {"User-Agent": "Mozilla/5.0 (X11; U; Linux i686) Gecko/20071127 Firefox/2.0.0.11"})
                        response = urllib.urlopen(request)
                        html = response.read()
                        title = html.split("<title>")[1].split("</title>")[0]
                        data = string.replace(title, "\n", "")
                        data = string.replace(data, "\t\t\t", "\t")
                        data = string.replace(data, "\t\t", "\t")
                        data = string.replace(data, "\t", " ")
                        while "  " in data:
                            data = string.replace(data, "  ", " ")
                        while data.startswith(" "):
                            data = data[1:]
                        data = string.replace(self.unescape(data), "  ", " ")
                        if not isHTTPS == 1:
                            self.sendmsg(target, ("\"%s\" at %s" % (data, domain)))
                        else:
                            self.sendmsg(target, ("\"%s\" (Secure) at %s" % (data, domain)))
                    except urllib.HTTPError as error:
                        if str(error) == "HTTP Error 405: Method Not Allowed":
                            try:
                                response = urllib.urlopen(url)
                                html = response.read()
                                title = html.split("<title>")[1].split("</title>")[0]
                                data = string.replace(title, "\n", "")
                                data = string.replace(data, "\t\t\t", "\t")
                                data = string.replace(data, "\t\t", "\t")
                                data = string.replace(data, "\t", " ")
                                while "  " in data:
                                    data = string.replace(data, "  ", " ")
                                while data.startswith(" "):
                                    data = data[1:]
                                data = string.replace(self.unescape(data), "  ", " ")
                                if not isHTTPS == 1:
                                    self.sendmsg(target, ("\"%s\" at %s" % (data, domain)))
                                else:
                                    self.sendmsg(target, ("\"%s\" (Secure) at %s" % (data, domain)))
                            except urllib.HTTPError as error:
                                self.sendmsg(target, ("%s (%s)" % (error, domain)))
                            except IndexError:
                                self.prnt("URL %s has no title. Parse?" % url)
                        else:
                            self.sendmsg(target, ("%s (%s)" % (error, domain)))
                    except IndexError:
                        self.prnt("URL %s has no title. Parse?" % url)
            except Exception as e:
                # self.sendmsg(target, "Error: %s" % e)
                print "Error: %s" % e
        
    def squit(self, reason = ""):
        if not reason == "":
            self.sendLine("QUIT :"+reason)
        else:
            quitmsg = self.quotes[random.randint(0, len(self.quotes))].strip("\r")
            self.sendLine("QUIT :%s" % quitmsg)
        self.prnt("***QUITTING!***")
        data = open("quitted", "w")
        data.write("1")
        data.flush()
        data.close()
    
    def left(self, channel):
        # We left a channel.
        self.prnt("***Left %s***" % channel)
        # Flush the logfile
        self.flush()
    
    def ctcpQuery(self, user, me, messages):
        name = user.split("!", 1)[0]
        self.prnt("[%s] %s" % (user, messages))
        # It's a CTCP query!
        if messages[0][0].lower() == "version":
            self.ctcpMakeReply(name, [(messages[0][0], "A Python bot written for #mcbans")])
        elif messages[0][0].lower() == "finger":
            self.ctcpMakeReply(name, [(messages[0][0], "No. Just, no.")])
        # Flush the logfile
        self.flush()
    # [gdude2002|away!colesgaret@86-41-192-29-dynamic.b-ras1.lmk.limerick.eircom.net:NotchBot [('CLIENTINFO', None)]]
    
    def modeChanged(self, user, channel, set, modes, args):
        # Mode change.
        userhost = user
        user = user.split("!", 1)[0]
        try:
            if set:
                self.prnt("***%s sets mode %s +%s %s***" % (user, channel, modes, " ".join(args)))
                i = 0
                for element in modes:
                    if element is "o":
                        self.set_op(channel, args[i], True)
                    if element is "v":
                        self.set_op(channel, args[i], True)
                    i += 1
            else:
                self.prnt("***%s sets mode %s -%s %s***" % (user, channel, modes, " ".join(args)))
                i = 0
                for element in modes:
                    if element is "o":
                        self.set_op(channel, args[i], False)
                    if element is "v":
                        self.set_op(channel, args[i], False)
                    i += 1
        except Exception:
            pass
        # Flush the logfile
        self.flush()
    
    def kickedFrom(self, channel, kicker, message):
        # Onoes, we got kicked!
        self.prnt("***Kicked from %s by %s: %s***" % (channel, kicker, message))
        # Flush the logfile
        self.flush()
    
    def nickChanged(self, nick):
        # Some evil muu changed MY nick!
        self.prnt("***Nick changed to %s***" % nick)
        # Flush the logfile
        self.flush()
    
    def userJoined(self, user, channel):
        # Ohai, welcome to mah channel!
        self.prnt("***%s joined %s***" % (user, channel))
        # Flush the logfile
        self.flush()
    
    def userLeft(self, user, channel):
        # Onoes, bai!
        self.prnt("***%s left %s***" % ((user.split("!")[0]), channel))
        # Flush the logfile
        self.flush()
    
    def userKicked(self, kickee, channel, kicker, message):
        # Mwahahaha, someone got kicked!
        kickee = kickee.split("!", 1)[0]
        kicker = kicker.split("!", 1)[0]
        self.prnt("***%s was kicked from %s by %s [%s]***" % (kickee, channel, kicker, message))
        # Flush the logfile
        self.flush()

    def action(self, user, channel, data):
        # Someone did /me.
        userhost = user
        user = user.split("!", 1)[0]
        self.prnt("* %s:%s %s" % (user, channel, data))
        # Flush the logfile
        self.flush()

    def irc_QUIT(self, user, params):
        # Someone quit.
        userhost = user
        user = user.split('!')[0]
        quitMessage = params[0]
        self.prnt("***%s has left irc: %s***" % (user, quitMessage))
        # Flush the logfile
        self.flush()
    
    def topicUpdated(self, user, channel, newTopic):
        # Topic was changed. Also called on a channel join.
        userhost = user
        user = user.split("!")[0]
        self.prnt("***%s set topic %s to \"%s%s15\"***" % (user, channel, newTopic, self.col))
        # Flush the logfile
        self.flush()
    
    def irc_NICK(self, prefix, params):
        # Someone changed their nick.
        oldnick = prefix.split("!", 1)[0]
        newnick = params[0]
        self.prnt("***%s is now known as %s***" % (oldnick, newnick))
        if oldnick in self.authorized.keys():
            self.sendnotice(newnick, "You have been logged out for security reasons. This happens automatically when you change your nick.")
            del self.authorized[oldnick]
        for element in self.chanlist.keys():
            if oldnick in self.chanlist[element].keys():
                oldpart = self.chanlist[element][oldnick]
                self.chanlist[element][newnick] = oldpart
                del self.chanlist[element][oldnick]
        # Flush the logfile
        self.flush()
                        
    def messageLoop(self, wut=None):
        self.m_protect = 0
        while self.m_protect < 5:
            try:
                item = self.messagequeue.pop(0).split(":", 1)
                user = item[0]
                message = item[1]
                self.sendmessage(user, message)
            except IndexError:
                pass
            except:
                try:
                    print("Failed to send message!")
                    print(user+" -> "+message)
                except:
                    pass
            self.m_protect = self.m_protect + 1
        reactor.callLater(2.5, self.messageLoop, ())
            
    def noticeLoop(self, wut=None):
        self.n_protect = 0
        while self.n_protect < 5:
            try:
                item = self.noticequeue.pop(0).split(":", 1)
                user = item[0]
                message = item[1]
                self.sendntc(user, message)
            except IndexError:
                pass
            except:
                try:
                    print("Failed to send notice!")
                    print(user+" -> "+message)
                except:
                    pass
            self.n_protect = self.n_protect + 1
        reactor.callLater(2.5, self.noticeLoop, ())
        
    def who(self, channel):
        "List the users in 'channel', usage: client.who('#testroom')"
        self.sendLine('WHO %s' % channel)

    def irc_RPL_WHOREPLY(self, *nargs):
        "Receive WHO reply from server"
        # ('apocalypse.esper.net', ['McPlusPlus_Testing', '#minecraft', 'die', 'inafire.com', 'apocalypse.esper.net', 'xales|gone', 'G*', '0 xales'])
        
        our_server = nargs[0]
        data = nargs[1]
        
        our_nick = data[0]
        channel = data[1]
        ident = data[2] # Starts with a ~ if there's no identd present
        host = data[3]
        server = data[4]
        nick = data[5]
        status = data[6] # H - not away, G - away, * - IRCop, @ - op, + - voice
        gecos = data[7] # Hops, realname
        
        if not channel in self.chanlist.keys():
            self.chanlist[channel] = {}
        
        done = {}
        done["ident"] = ident
        done["host"] = host
        done["server"] = server
        done["realname"] = gecos.split(" ")[1]
        done["op"] = False
        done["voice"] = False
        done["oper"] = False
        done["away"] = False
        for char in status:
            if char is "@":
                done["op"] = True
            if char is "+":
                done["voice"] = True
            if char is "*":
                done["oper"] = True
            if char is "G":
                done["away"] = True
        self.chanlist[channel][nick] = done

    def irc_RPL_ENDOFWHO(self, *nargs):
        "Called when WHO output is complete"
        # ('eldridge.esper.net', ['McPlusPlus_Testing', '#mc++', 'End of /WHO list.'])
        server = nargs[0]
        data = nargs[1]
        my_nick = data[0]
        channel = data[1]
        message = data[2]
        print("%s users on %s" % (len(self.chanlist[channel]), channel))

    def irc_unknown(self, prefix, command, params):
        "Print all unhandled replies, for debugging."
        # if command == "RPL_NAMREPLY":
            # ['McPlusPlus_Testing', '@', '#hollow_testing', 'McPlusPlus_Testing @DerpServ @g']
            # print ("Users on %s: %s" % (params[2], params[3]))
        # if command == "RPL_ENDOFNAMES":
            # print ("Name list for %s is finished." % (params[1]))



#-#################################-#
#                                   |
#       UTILITY   #   FUNCTIONS     #
#                                   |
#-#################################-#

    def cmsg(self, message):
        # Send a message to all joined channels
        for element in self.joinchans:
            self.sendmsg("#"+element[0], message.encode('ascii','ignore'))
    
    def cnotice(self, message):
        # Notice all channels
        for element in self.joinchans:
            self.sendnotice("#"+element[0], message.encode('ascii','ignore'))
    
    # Don't use this directy, use sendmsg
    def sendmessage(self, user, message):
        if user == "NickServ":
            self.prnt("--> <%s> %s" % (user, ("*" *len(message))))
        else:
            self.prnt("--> <%s> %s" % (user, message))
        self.msg(user, message)
        # Flush the logfile
        self.flush()

    def unescape_charref(self, ref):
        name = ref[2:-1]
        base = 10
        if name.startswith("x"):
            name = name[1:]
            base = 16
        return unichr(int(name, base))

    def replace_entities(self, match):
        ent = match.group()
        if ent[1] == "#":
            return self.unescape_charref(ent)

        repl = htmlentitydefs.name2codepoint.get(ent[1:-1])
        if repl is not None:
            repl = unichr(repl)
        else:
            repl = ent
        return repl

    def unescape(self, data):
        return re.sub(r"&#?[A-Za-z0-9]+?;", self.replace_entities, data)

        # Don't use this directy, use sendnotice
    def sendntc(self, user, message):
        self.prnt("--> -%s- %s" % (user, message))
        self.notice(user, message)
        # Flush the logfile
        self.flush()
    
    def sendmsg(self, user, message):
        self.messagequeue.append(str(user)+":"+str(message))
    
    def sendnotice(self, user, message):
        self.noticequeue.append(str(user)+":"+str(message))
    
    def senddescribe(self, user, message):
        self.prnt("--> * %s: %s" % (user, message))
        self.describe(user, message)
        # Flush the logfile
        self.flush()

    def identify(self):
        self.sendmsg("NickServ", "IDENTIFY %s" % self.password)

class BotFactory(protocol.ClientFactory):
    protocol = Bot

    def __init__(self):
        # Initialize!
        settings = ConfigParser()
        settings.read("settings.ini")
        self.nickname = settings.get("info", "nickname")

    def prnt(self, msg):
        colprint(msg)
        self.logfile = open("output.log", "a")
        self.logfile.write("%s\n" %(colstrip(msg)))
        self.logfile.flush()
        self.logfile.close()
        
    def clientConnectionLost(self, connector, reason):
        # We died. Onoes!
        self.prnt("Lost connection: %s" % (reason))

    def clientConnectionFailed(self, connector, reason):
        # Couldn't connect. Daww!
        self.prnt("Could not connect: %s" % (reason))