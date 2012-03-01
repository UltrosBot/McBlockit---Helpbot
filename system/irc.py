import os, random, time, math, traceback
import thread, socket, htmlentitydefs
import mechanize
import dns.resolver as resolver

from ConfigParser import RawConfigParser as ConfigParser
from twisted.internet import reactor, protocol
from twisted.internet.protocol import Factory
from twisted.words.protocols import irc
from colours import *

from utils import *

from system.constants import *
from system import faq

from depends import mcbans_api as mcbans
from depends.maskchecker import *

class Bot(irc.IRCClient):
    # Extensions the page title parser shouldn't parse
    notParse = ["png", "jpg", "jpeg", "tiff", "bmp", "ico", "gif", "iso", "bin", "pub", "ppk", "doc", "docx", "xls",
                "xlsx", "ppt", "pptx", "svg"]

    # Plugins!
    plugins = {}
    hooks = {}
    commands = {}

    # Channels
    joinchans = []
    channels = []
    stfuchans = []
    norandom = []

    lookedup = []

    chanlist = {}
    banlist = {}

    firstjoin = 1

    # Message queues
    messagequeue = []
    noticequeue = []
    rawqueue = []

    # Quit quotes
    quotes = []

    # Random emote objects
    emoteobjects = []

    # User system
    authorized = {}
    users = {}
    kicked = []

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
        self.logfile.write("%s\n" % (colstrip(msg)))
        self.flush()

    def parseObjects(self):
        try:
            self.prnt("|= Reading in objects from objects.txt...")
            file = open("objects.txt", "r")
            data = file.read()
            self.emoteobjects = data.split("\n")
            self.prnt("|= Read %s objects." % len(self.quotes))
        except:
            return False
        else:
            return True

    def parseQuotes(self):
        try:
            self.prnt("|= Reading in quit quotes from quotes.txt...")
            file = open("quotes.txt", "r")
            data = file.read()
            self.quotes = data.split("\n")
            self.prnt("|= Read %s quotes." % len(self.quotes))
        except:
            return False
        else:
            return True

    def parseSettings(self):
        try:
            self.prnt("|= Reading in settings from settings.ini...")
            oldchans = self.joinchans
            settings = ConfigParser()
            settings.read("config/settings.ini")
            channels = settings.items("channels")
            perform = open("perform.txt", "r").readlines()
            for element in perform:
                self.send_raw(element.strip("\n").strip("\r"))
            for element in self.joinchans:
                self.joinchans.remove(element)
            for element in channels:
                self.joinchans.append(element)
                if not element in oldchans and not self.firstjoin == 1:
                    self.send_raw("JOIN #%s" % element[0])
            for element in oldchans:
                if element not in self.joinchans and not self.firstjoin == 1:
                    self.send_raw("PART #%s Configuration changed" % element[0])
            self.password = settings.get("info", "password")
            if not self.firstjoin == 1:
                self.sendmsg("nickserv", "IDENTIFY %s" % self.password)
            self.loginpass = settings.get("info", "loginpass")
            self.control_char = settings.get("info", "control_character")
            self.data_dir = settings.get("info", "data_folder")
            self.api_key = settings.get("mcbans", "api_key")
            self.r_emotes = settings.getboolean("other", "emotes")
            self.use_antispam = settings.getboolean("other", "antispam")
            self.autokick = settings.getboolean("other", "autokick")
        except Exception:
            return [False, traceback.format_exc()]
        else:
            self.prnt("|= Done!")
            return [True, ""]

    def runHook(self, hook, data=None):
        """Used to run hooks for plugins"""
        # print hook, data
        finaldata = []
        if hook in self.hooks.keys():
            for element in self.hooks[hook]:
            #         print element
                if data:
                    value = element[1](data)
                else:
                    value = element[1]()
                if value is not None:
                    finaldata.append(value)
        if finaldata is []:
            finaldata = True
        return {"result": True, "data": finaldata} # Stupid workaround, need to fix

    def loadPlugins(self):
        files = []
        self.hooks = {} # Clear the list of hooks
        self.commands = {} # Clear the list of commands
        for element in os.listdir("plugins"): # List the plugins
            ext = element.split(".")[-1]
            file = element.split(".")[0]
            if element == "__init__.py": # Skip the initialiser
                continue
            elif ext == "py": # Check if it ends in .py
                files.append(file)
        self.prnt("|= Loading %s plugins.. " % len(files))
        i = 0
        while i < len(files):
            element = files[i]
            reloaded = False
            if not "plugins.%s" % element in sys.modules.keys(): # Check if we already imported it
                try:
                    __import__("plugins.%s" % element) # If not, import it
                except Exception: # Got an error!
                    self.prnt("|! Unable to load plugin from %s.py!" % element)
                    self.prnt("|! Error: %s" % traceback.format_exc())
                    i += 1
                    continue
                else:
                    try:
                        mod = sys.modules["plugins.%s" % element].plugin(self)
                        name = mod.name # What's the name?
                        mod.irc = self
                        if hasattr(mod, "gotIRC"):
                            mod.gotIRC()
                    except Exception:
                        self.prnt("|! Unable to load server plugin from %s" % (element + ".py"))
                        self.prnt("|! Error: %s" % traceback.format_exc())
                        i += 1
                        continue
            else: # We already imported it
                del self.plugins[element][0]
                del self.plugins[element]
                del sys.modules["plugins.%s" % element] # Unimport it by deleting it
                try:
                    __import__("plugins.%s" % element) # import it again
                except Exception: # Got an error!
                    self.prnt("|! Unable to load plugin from %s.py!" % element)
                    self.prnt("|! Error: %s" % traceback.format_exc())
                    i += 1
                    continue
                else:
                    try:
                        mod = sys.modules["plugins.%s" % element].plugin(self)
                        name = mod.name # get the name
                    except Exception:
                        self.prnt("|! Unable to load plugin from %s" % (element + ".py"))
                        self.prnt("|! Error: %s" % traceback.format_exc())
                        i += 1
                        del sys.modules["plugins.%s" % filename]
                        continue
                reloaded = True # Remember that we reloaded it
            mod.filename = element
            self.plugins[name] = mod # Put it in the plugins list
            if not reloaded:
                self.prnt("|= Loaded plugin: %s" % name)
            else:
                self.prnt("|= Reloaded plugin: %s" % name)
            i += 1
        for plugin in self.plugins.values(): # For every plugin,
            if hasattr(plugin, "hooks"):
                for element, fname in plugin.hooks.items(): # For every hook in the plugin,
                    if element not in self.hooks.keys():
                        self.hooks[element] = [] # Make a note of the hook in the hooks dict
                    self.hooks[element].append([plugin, getattr(plugin, fname)])
            if hasattr(plugin, "commands"):
                for element, data in plugin.commands.items():
                    if element in self.commands.keys():
                        self.prnt("|! Command %s is already registered. Overriding." % element)
                    self.commands[element] = getattr(plugin, data)
            if hasattr(plugin, "finishedLoading"):
                plugin.finishedLoading()

    def isPluginLoaded(self, name):
        return name in self.plugins.keys()

    def loadPlugin(self, filename):
        for element in self.plugins.keys():
            if filename == self.plugins[element].filename:
                return False
        try:
            __import__("plugins.%s" % filename)
        except Exception: # Got an error!
            self.prnt("|! Unable to load plugin from %s.py!" % filename)
            self.prnt("|! Error: %s" % traceback.format_exc())
            return False
        else:
            try:
                mod = sys.modules["plugins.%s" % filename].plugin(self)
                name = mod.name # What's the name?
                mod.irc = self
                if hasattr(mod, "gotIRC"):
                    mod.gotIRC()
            except Exception:
                self.prnt("|! Unable to load server plugin from %s" % (filename + ".py"))
                self.prnt("|! Error: %s" % traceback.format_exc())
                del sys.modules["plugins.%s" % filename]
                return False
            mod.filename = filename
            self.plugins[name] = mod # Put it in the plugins list
            self.prnt("|= Loaded plugin: %s" % name)

            if hasattr(mod, "hooks"):
                for element, fname in mod.hooks.items(): # For every hook in the plugin,
                    if element not in self.hooks.keys():
                        self.hooks[element] = [] # Make a note of the hook in the hooks dict
                    self.hooks[element].append([mod, getattr(mod, fname)])
            if hasattr(mod, "commands"):
                for element, data in mod.commands.items():
                    if element in self.commands.keys():
                        self.prnt("|! Command %s is already registered. Overriding." % element)
                    self.commands[element] = getattr(mod, data)

            return True

    def unloadPlugin(self, name):
        if self.isPluginLoaded(name):
            mod = self.plugins[name]
            if hasattr(mod, "hooks"):
                for element, fname in mod.hooks.items(): # For every hook in the plugin,
                    if element in self.hooks.keys():
                        self.hooks[element].remove([mod, getattr(mod, fname)])
            if hasattr(mod, "commands"):
                for element, data in mod.commands.items():
                    if element in self.commands.keys():
                        del self.commands[element]
            if hasattr(self.plugins[name], "pluginUnloaded"):
                self.plugins[name].pluginUnloaded()
            filename = self.plugins[name].filename

            name = mod.name

            del mod
            del self.plugins[name].filename
            del self.plugins[name]
            del sys.modules["plugins.%s" % filename] # Unimport it by deleting it

            self.hooks = {}
            for plugin in self.plugins.values(): # For every plugin,
                if hasattr(plugin, "hooks"):
                    for element, fname in plugin.hooks.items(): # For every hook in the plugin,
                        if element not in self.hooks.keys():
                            self.hooks[element] = [] # Make a note of the hook in the hooks dict
                        self.hooks[element].append([plugin, getattr(plugin, fname)])
                if hasattr(plugin, "commands"):
                    for element, data in plugin.commands.items():
                        if element in self.commands.keys():
                            self.prnt("|! Command %s is already registered. Overriding." % element)
                        self.commands[element] = getattr(plugin, data)

            self.prnt("|= Unloaded plugin: %s" % name)

            return True
        return False


    def __init__(self):
        # What's the name of our logfile?
        self.logfile = open("output.log", "a")

        stuff = self.parseSettings()

        if not(stuff[0]):
            self.prnt("|! Unable to parse settings. Does settings.ini and perform.txt exist?")
            self.prnt("|! Error: %s" % stuff[1])
            reactor.stop()
            exit()
        if not(self.parseQuotes()):
            self.prnt("|! Unable to parse quotes.txt. Does it exist? Bot will now quit.")
            reactor.stop()
            exit()
        if not(self.parseObjects()):
            self.prnt("|! Unable to parse objects.txt. Does it exist? Bot will now quit.")
            reactor.stop()
            exit()
        self.loadPlugins()
        self.faq = faq.FAQ(self.data_dir, self)
        self.faq.listentries()
        self.mcb = mcbans.McBans(self.api_key)

    def flush(self):
        self.logfile.flush()

    def connectionLost(self, reason):
        # We lost connection. GTFO tiem.
        self.runHook("connectionLost", {"reason": reason})
        self.prnt("|= Shutting down!")
        self.flush()

    @property
    def nickname(self):
        return self.factory.nickname

    def signedOn(self):
        # OK, we logged on successfully.
        # Log that we signed on.
        self.prnt("|= Signed on as %s." % self.nickname)
        # Log in with NickServ.
        self.sendmsg("NickServ", "IDENTIFY %s" % self.password)
        #Start the three loops for sending messages and notices and raw lines
        self.messageLoop()
        self.noticeLoop()
        self.rawLoop()
        for element in self.joinchans:
            reactor.callLater(5.0, self.join, ("#%s" % element[0]))
        self.flush() # Flush the log
        self.runHook("signedOn")

    def joined(self, channel):
        # We joined a channel
        self.prnt("|+ Joined %s" % channel)
        self.channels.append(channel)
        if self.firstjoin == 1:
            self.firstjoin = 0
            # Flush the logfile
        self.who(channel)
        self.send_raw("MODE %s b" % channel)
        if self.r_emotes:
            reactor.callLater(5, thread.start_new_thread, self.randmsg, (channel,))
        self.flush()
        self.runHook("channelJoined", {"channel": channel})

    def is_op(self, channel, user):
        if channel in self.chanlist.keys():
            if user in self.chanlist[channel].keys():
                return self.chanlist[channel][user]["op"]
            return False
        return False

    def is_voice(self, channel, user):
        if channel in self.chanlist.keys():
            if user in self.chanlist[channel].keys():
                return self.chanlist[channel][user]["voice"]
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
                    self.chanlist[channel][user]["voice"] = data
        else:
            raise ValueError("'data' must be either True or False")

    def randmsg(self, channel):
        if self.r_emotes:
            if channel not in self.norandom:
                messages = [self.ctcp + "ACTION paws at ^ruser^" + self.ctcp, # Oh look, we did need it
                            self.ctcp + "ACTION curls up in ^ruser^'s lap" + self.ctcp,
                            self.ctcp + "ACTION stares at ^ruser^" + self.ctcp,
                            self.ctcp + "ACTION jumps onto the ^robject^" + self.ctcp + "\no3o",
                            self.ctcp + "ACTION rubs around ^ruser^'s leg" + self.ctcp + "\n" + self.ctcp + "ACTION purrs" + self.ctcp
                    ,
                            "Mewl! o3o",
                            "Meow",
                            ":3",
                            "Mreewww.."
                ]
                self.norandom.append(channel)
                random.seed()
                msg = messages[random.randint(0, len(messages) - 1)]
                random.seed()
                if channel in self.chanlist.keys():
                    msg = msg.replace("^ruser^",
                        self.chanlist[channel].keys()[random.randint(0, len(self.chanlist[channel].keys()) - 1)])
                else:
                    msg = msg.replace("^ruser^", "someone")
                random.seed()
                msg = msg.replace("^robject^", self.emoteobjects[random.randint(0, len(self.emoteobjects) - 1)])
                self.sendmsg(channel, msg)
            reactor.callLater(3600, thread.start_new_thread, self.randmsg, (channel,))


    def privmsg(self, user, channel, msg):
        if channel in self.norandom:
            self.norandom.remove(channel)
            # We got a message.
        # Define the userhost
        userhost = user
        user = user.split("!", 1)[0]

        self.runHook("privmsg", {"user": user, "host": userhost, "channel": channel, "message": msg})

        # Get the username
        send = self.sendnotice
        if channel == self.nickname:
            send = self.sendmsg
            channel = user
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
        if self.use_antispam:
            msg_time = float(time.time())
            if not (authorized or self.is_voice(user, channel)) and channel.startswith("#"):
                difference = msg_time - self.chanlist[channel][user]["last_time"]
                if difference < 0.15:
                    # User is a dirty spammer!
                    if self.is_op(channel, self.nickname):
                        if not user in self.kicked:
                            self.sendLine("KICK %s %s :%s is a dirty spammer!" % (channel, user, user))
                            self.prnt("|! Kicked %s from %s for spamming." % (user, channel))
                            self.kicked.append(user)
                            return

                        else:
                            self.sendLine(
                                "MODE %s +bbb *!%s@* %s!*@* *!*@%s" % (
                                    channel, userhost.split("@")[0].split("!")[1], user, userhost.split("@")[1]))
                            self.sendLine("KICK %s %s :%s is a dirty spammer!" % (channel, user, user))
                            self.prnt("|! Banned %s from %s for spamming." % (user, channel))
                            return

                if difference > 5.00:
                    if self.is_op(channel, self.nickname):
                        if msg.startswith("#") and len(msg.split(" ")) == 1:
                            # Random channel
                            self.sendLine(
                                "KICK %s %s :Don't do that! ( Did you mean: \"/join %s\"? )" % (channel, user, msg))
                            self.prnt(
                                "|! Kicked %s from %s for randomly typing a channel on its own." % (user, channel))
                            self.kicked.append(user)
                            return

        if channel.startswith("#"):
            if channel in self.chanlist.keys():
                self.chanlist[channel][user]["last_time"] = float(time.time())
        if msg.startswith("http://") or msg.startswith("https://"):
            if self.is_voice(channel, user) or self.is_op(channel, user):
                thread.start_new_thread(self.pagetitle, (channel, msg.split(" ")[0]))
        elif msg.startswith(self.control_char) or channel == self.nickname:
            command = msg.split(" ")[0].replace(self.control_char, "", 1)
            arguments = msg.split(" ")
            if command == "help":
                if len(arguments) < 2:
                    send(user, "Syntax: %shelp <topic>" % self.control_char)
                    send(user, "Available topics: about, login, logout, lookup")
                    if authorized:
                        send(user, "Admin topics: quit")
                    done = []
                    for element in self.plugins.keys():
                        try:
                            for element in self.plugins[element].help.keys():
                                done.append(element)
                        except:
                            self.prnt("|! Plugin %s has no help object!" % element.name)

                    send(user, ", ".join(sorted(done)))
                else:
                    if arguments[1] == "about":
                        send(user, "I'm the MCBans IRC helper bot.")
                        send(user, "Created by gdude2002, helped by rakiru.")
                        send(user, "I was designed for #mcbans on irc.freenode.net")
                    elif arguments[1] == "auth":
                        send(user,
                            "Auth is managed with %slogin and %slogout." % (self.control_char, self.control_char))
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
                        send(user,
                            "Type is optional, but it can be local, global, minimal or all. If it is missing, it is presumed to be minimal.")
                    elif arguments[1] == "ping":
                        send(user, "Syntax: %sping <ip>" % self.control_char)
                        send(user, "Retrieves the server information from a Beta/Release server.")
                        send(user, "Can be useful to check if a server is accepting connections.")
                    elif user in self.authorized.keys():
                        if arguments[1] == "quit":
                            send(user, "Syntax: %squit [message]" % self.control_char)
                            send(user, "Makes the bot quit, with an optional user-defined message.")
                            send(user, "If no message is defined, uses a random quote.")
                    else:
                        sent = 0
                        for element in self.plugins.keys():
                            try:
                                if arguments[1] in self.plugins[element].help.keys():
                                    helptxt = self.plugins[element].help[arguments[1]]
                                    if "\n" in helptxt:
                                        for element in helptxt.split("\n"):
                                            send(user, element)
                                    else:
                                        send(user, helptxt)
                                    sent = 1
                                    break
                            except:
                                self.prnt("|! Plugin %s has no help object!" % element)
                        if not sent:
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
                    send(user,
                        "You were never logged in. Please note that you are logged out automatically when you nick.")
            elif command == "quit":
                if authorized and authtype > 1:
                    if len(arguments) < 2:
                        self.squit()
                    else:
                        self.squit(" ".join(arguments[1:]))
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
                                            send(user, "%s: %s" % (server, reason.decode('string_escape')))
                                    else:
                                        send(user, "No global bans.")
                            elif type == "minimal":
                                if authorized:
                                    self.sendmsg(channel,
                                        "Reputation for %s: %.2f/10" % (arguments[1], data["reputation"]))
                                    self.sendmsg(channel, "Total bans: %s" % data["total"])
                                else:
                                    send(user, "Reputation for %s: %.2f/10" % (arguments[1], data["reputation"]))
                                    send(user, "Total bans: %s" % data["total"])
                            elif type == "all":
                                if authorized:
                                    self.sendmsg(channel, "Listing everything for %s..." % arguments[1])
                                    self.sendmsg(channel,
                                        "Reputation for %s: %.2f/10" % (arguments[1], data["reputation"]))
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
                                    self.sendmsg(channel,
                                        "Reputation for %s: %.2f/10" % (arguments[1], data["reputation"]))
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
                            s = socket.socket()
                            s.settimeout(5.0)
                            s.connect((server, port))
                            ntiming = time.time()
                            elapsed = ntiming - timing
                            msec = math.floor(elapsed * 1000.0)
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
                                    self.sendmsg(channel, "Server info: %s (%s/%s) [Latency: %smsec]" % (
                                        finished[0], finished[1], finished[2], msec))
                                else:
                                    send(user, "Server info: %s (%s/%s) [Latency: %smsec]" % (
                                        finished[0], finished[1], finished[2], msec))
                            else:
                                if authorized:
                                    self.sendmsg(channel,
                                        "That doesn't appear to be a Minecraft server. [Latency: %smsec]" % msec)
                                else:
                                    send(user, "That doesn't appear to be a Minecraft server. [Latency: %smsec]" % msec)
                        except Exception:
                            error = str(traceback.format_exc()).split("\n")
                            if '' in error:
                                error.remove('')
                            if ' ' in error:
                                error.remove(' ')
                            error = error[-1]
                            if authorized:
                                self.sendmsg(channel, error)
                            else:
                                send(user, error)
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
            elif command.lower() in self.commands.keys():
                try:
                    self.commands[command.lower()](user, channel, arguments)
                except Exception as e:
                    send(user, "Error: %s" % e)
        elif msg.startswith("??") or msg.startswith("?!"):
            cinfo = {"user": user, "hostmask": userhost.split("!", 1)[1], "origin": channel, "message": msg,
                     "target": channel}
            parts = msg.split(" ")
            if len(parts) > 1:
                if parts[0] == "??": # Check in channel
                    if len(parts) > 1:
                        data = self.faq.get(parts[1].lower(), cinfo)
                        if data[0]:
                            for element in data[1]:
                                if not element.strip() == "":
                                    if "\n" in element:
                                        for part in element.split("\n"):
                                            self.sendmsg(channel, "(%s) %s" % (parts[1].lower(), part))
                                    else:
                                        self.sendmsg(channel, "(%s) %s" % (parts[1].lower(), element))
                        else:
                            if data[1] is ERR_NO_SUCH_ENTRY:
                                send(user, "No such entry: %s" % parts[1].lower())
                            else:
                                send(user, "Unable to load entry: %s" % parts[1].lower())
                    else:
                        send(user, "Please provide a help topic. For example: ?? help")
                elif parts[0] == "?!": # Check in channel without eval
                    if len(parts) > 1:
                        data = self.faq.get_noeval(parts[1].lower(), cinfo)
                        if data[0]:
                            for element in data[1]:
                                if not element.strip() == "":
                                    self.sendmsg(channel, "(%s) %s" % (parts[1].lower(), element))
                        else:
                            if data[1] is ERR_NO_SUCH_ENTRY:
                                send(user, "No such entry: %s" % parts[1].lower())
                            else:
                                send(user, "Unable to load entry: %s" % parts[1].lower())
                    else:
                        send(user, "Please provide a help topic. For example: ?! help")
                elif parts[0] == "??>": # Check in channel with target
                    if len(parts) > 2:
                        cinfo = {"user": user, "hostmask": userhost.split("!", 1)[1], "origin": channel, "message": msg,
                                 "target": parts[1]}
                        data = self.faq.get(parts[2].lower(), cinfo)
                        if data[0]:
                            for element in data[1]:
                                if not element.strip() == "":
                                    if "\n" in element:
                                        for part in element.split("\n"):
                                            self.sendmsg(channel, "%s: (%s) %s" % (parts[1], parts[2].lower(), part))
                                else:
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
                        cinfo = {"user": user, "hostmask": userhost.split("!", 1)[1], "origin": channel, "message": msg,
                                 "target": parts[1]}
                        data = self.faq.get(parts[2].lower(), cinfo)
                        if data[0]:
                            for element in data[1]:
                                if not element.strip() == "":
                                    if "\n" in element:
                                        for part in element.split("\n"):
                                            self.sendmsg(parts[1], "(%s) %s" % (parts[2].lower(), part))
                                    else:
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
                        cinfo = {"user": user, "hostmask": userhost.split("!", 1)[1], "origin": channel, "message": msg,
                                 "target": user}
                        data = self.faq.get(parts[1].lower(), cinfo)
                        if data[0]:
                            for element in data[1]:
                                if not element.strip() == "":
                                    if "\n" in element:
                                        for part in element.split("\n"):
                                            send(user, "(%s) %s" % (parts[1].lower(), part))
                                    else:
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
                            send(user,
                                "Please provide a help topic and some data to append. For example: ??+ help This is what you do..")
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
                            send(user,
                                "Please provide a help topic and some data to use. For example: ??~ help This is what you do..")
                    else:
                        send(user, "You do not have access to this command.")
                elif parts[0] == "??-": # Remove topic
                    if authorized:
                        if len(parts) > 1:
                            data = self.faq.set(parts[1].lower(), '', MODE_REMOVE)
                            self.faq.listentries()
                            if data[0]:
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
        if channel.startswith("#"):
            self.prnt("| <%s:%s> %s" % (user, channel, msg))
        else:
            self.prnt("|< %s %s" % (channel, msg))

    def dnslookup(self, channel, user):
        """Looks up users on several DNS blacklists and kicks them if the bot is op"""
        if self.is_op(channel, self.nickname):
            ip = socket.gethostbyname(self.chanlist[channel][user]["host"])
            if not ip in self.lookedup:
                r_ip = ip.split(".")
                r_ip.reverse()
                r_ip = ".".join(r_ip)
                blacklists = ["dnsbl.swiftbl.org", "dnsbl.ahbl.org", "ircbl.ahbl.org", "rbl.efnet.org",
                              "dnsbl.dronebl.org", "dnsbl.mcblacklist.com"]
                for bl in blacklists:
                    self.prnt("|= Checking user %s on blacklist %s..." % (user, bl))
                    try:
                        resolver.query(r_ip + "." + bl, "A")
                    except resolver.NXDOMAIN:
                        self.prnt("|= User %s is clean." % user)
                        pass
                    else:
                        self.prnt("|! User %s is blacklisted!" % user)
                        try:
                            answer = resolver.query(r_ip + "." + bl, "TXT")
                            reason = answer[0]
                        except:
                            reason = bl
                        self.sendLine("KICK %s %s :%s" % (channel, user, reason))
                        self.sendLine("MODE %s +b %s" % ip)
                self.lookedup.append(ip)

    def pagetitle(self, target, url):
        if not target in self.stfuchans:
            if not url.split(".")[-1] in self.notParse:
                isHTTPS = 0
                domain = ""
                try:
                    if url.startswith("http://"):
                        domain = url.split("http://")[1].split("/")[0]
                        isHTTPS = 0
                    elif url.startswith("https://"):
                        domain = url.split("https://")[1].split("/")[0]
                        isHTTPS = 1
                    br = mechanize.Browser()
                    br.addheaders = [('User-agent',
                                      'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9-1.fc9 Firefox/3.0.1')]
                    br.set_handle_robots(False)
                    br.open(url)
                    self.sendmsg(target, "\"%s\" at %s" % (br.title(), domain))
                except Exception as e:
                    self.sendmsg(target, "Error: %s" % e)

    def squit(self, reason=""):
        if not reason == "":
            self.sendLine("QUIT :" + reason)
        else:
            random.seed()
            quitmsg = self.quotes[random.randint(0, len(self.quotes) - 1)].strip("\r")
            self.sendLine("QUIT :%s" % quitmsg)
        self.prnt("|= QUITTING!")

    def left(self, channel):
        # We left a channel.
        self.prnt("|= Left %s" % channel)
        # Flush the logfile
        self.flush()
        self.runHook("channelLeft", channel)

    def ctcpQuery(self, user, me, messages):
        name = user.split("!", 1)[0]
        # It's a CTCP query!
        if messages[0][0].lower() == "action":
            actions = {"pets": self.ctcp + "ACTION purrs" + self.ctcp,
                       "strokes": self.ctcp + "ACTION purrs" + self.ctcp,
                       "feeds": self.ctcp + "ACTION noms ^user^'s food" + self.ctcp + "\n=^.^="
            }
            for element in actions.keys():
                action = element + " " + self.nickname
                act = action.lower().strip()
                if messages[0][1].lower().strip() == act:
                    message = actions[element]
                    message = message.replace("^user^", user.split("!")[0])
                    message = message.replace("^hostmask^", user.split("!")[1])
                    message = message.replace("^host^", user.split("@")[1])
                    message = message.replace("^me^", me)
                    self.sendmsg(me, message)
        elif messages[0][0].lower() == "version":
            self.ctcpMakeReply(name, [(messages[0][0], "A Python bot written for #mcbans. See .help about")])
            self.prnt("|< %s [CTCP VERSION]" % user)
            self.prnt("|> %s [CTCP VERSION REPLY] A Python bot written for #mcbans. See .help about" % user)
        elif messages[0][0].lower() == "finger":
            self.ctcpMakeReply(name, [(messages[0][0], "No. Just, no.")])
            self.prnt("|< %s [CTCP FINGER]" % user)
            self.prnt("|> %s [CTCP FINGER REPLY] No. Just, no." % user)
        else:
            self.prnt("|< %s [CTCP %s] %s" % (user, messages[0][0].upper(), " ".join(messages[0])))
            # Flush the logfile
        self.flush()

        self.runHook("ctcpQuery", {"user": name, "host": user.split("!", 1)[1], "target": me, "type": messages[0][0],
                                   "message": messages[0][1]})

    def checkban(self, channel, banmask, owner):
        if self.autokick:
            if self.is_op(channel, self.nickname):
                for element in self.chanlist[channel].keys():
                    hostmask = self.chanlist[channel][element]["hostmask"]
                    user = element
                    if not self.is_op(channel, user) or self.is_voice(channel, user):
                        if checkbanmask(banmask, hostmask):
                            self.send_raw("KICK %s %s :Matched ban mask %s by %s" % (channel, user, banmask, owner))


    def modeChanged(self, user, channel, set, modes, args):
        # Mode change.
        userhost = user
        user = user.split("!", 1)[0]
        self.runHook("modechanged", {"user": user, "host": userhost, "channel": channel, "set": set, "modes": modes,
                                     "args": args})
        try:
            if set:
                self.prnt("|= %s sets mode %s +%s %s" % (user, channel, modes, " ".join(args)))
                i = 0
                for element in modes:
                    if element == "o":
                        self.set_op(channel, args[i], True)
                        if args[i].lower() == self.nickname.lower():
                            if channel in self.banlist.keys():
                                stuff = self.banlist[channel].keys()
                                stuff.remove("done")
                                stuff.remove("total")

                                for element in stuff:
                                    self.checkban(channel, element, self.banlist[channel][element]["owner"])
                    elif element == "v":
                        self.set_voice(channel, args[i], True)
                    elif element == "b":
                        if args[i] == "*!*@*":
                            if self.is_op(channel, self.nickname):
                                self.send_raw("KICK %s %s :Do not set such ambiguous bans!" % (channel, user))
                                self.send_raw("MODE %s -b *!*@*" % channel)
                                self.send_raw("MODE %s +b *!*@%s" % (channel, userhost.split("@")[1]))
                        else:
                            self.checkban(channel, args[i], user)
                            #if args[i].lower() == self.nickname.lower():
                        #    for element in self.chanlist[channel].keys():
                    #        self.dnslookup(channel, element)
                    i += 1
            else:
                self.prnt("|= %s sets mode %s -%s %s" % (user, channel, modes, " ".join(args)))
                i = 0
                for element in modes:
                    if element == "o":
                        self.set_op(channel, args[i], False)
                    elif element == "v":
                        self.set_voice(channel, args[i], False)
                    i += 1
        except:
            pass
            # Flush the logfile
        self.flush()

    def kickedFrom(self, channel, kicker, message):
        self.runHook("kickedBot", {"channel": channel, "kicker": kicker, "message": message})
        # Onoes, we got kicked!
        self.prnt("|= Kicked from %s by %s: %s" % (channel, kicker, message))
        # Flush the logfile
        self.flush()

    def nickChanged(self, nick):
        self.runHook("nickedBot", {"oldnick": self.nickname, "newnick": nick})
        # Some evil muu changed MY nick!
        self.prnt("|= Nick changed to %s" % nick)
        self.factory.nickname = nick
        # Flush the logfile
        self.flush()

    def userJoined(self, user, channel):
        self.runHook("userJoined", {"user": user, "channel": channel})
        # Ohai, welcome to mah channel!
        self.prnt("|+ %s joined %s" % (user, channel))
        self.who(channel)
        # Flush the logfile
        self.flush()

    def userLeft(self, user, channel):
        self.runHook("userParted", {"user": user, "channel": channel})
        # Onoes, bai!
        self.prnt("|- %s left %s" % ((user.split("!")[0]), channel))
        # Flush the logfile
        self.flush()

    def userKicked(self, kickee, channel, kicker, message):
        # Mwahahaha, someone got kicked!
        kickee = kickee.split("!", 1)[0]
        kicker = kicker.split("!", 1)[0]

        if kickee in self.chanlist[channel].keys():
            del self.chanlist[channel][kickee]

        self.runHook("userKicked", {"kickee": kickee, "kicker": kicker, "channel": channel, "message": message})
        self.prnt("|- %s was kicked from %s by %s [%s]" % (kickee, channel, kicker, message))
        # Flush the logfile
        self.flush()

    def irc_QUIT(self, user, params):
        # Someone quit.
        userhost = user.split('!')[1]
        user = user.split('!')[0]
        quitMessage = params[0]
        for element in self.chanlist.keys():
            if user in self.chanlist[element].keys():
                del self.chanlist[element][user]
        self.runHook("userQuit", {"user": user, "host": userhost, "message": quitMessage})
        self.prnt("|- %s has left irc: %s" % (user, quitMessage))
        # Flush the logfile
        self.flush()

    def topicUpdated(self, user, channel, newTopic):
        # Topic was changed. Also called on a channel join.
        userhost = user
        user = user.split("!")[0]
        self.runHook("topicChanged", {"user": user, "host": userhost, "topic": newTopic, "channel": channel})
        self.prnt("|= %s set topic %s to \"%s%s15\"" % (user, channel, newTopic, self.col))
        # Flush the logfile
        self.flush()

    def irc_NICK(self, prefix, params):
        # Someone changed their nick.
        oldnick = prefix.split("!", 1)[0]
        newnick = params[0]
        self.runHook("userNicked", {"oldnick": oldnick, "nick": newnick})
        self.prnt("|= %s is now known as %s" % (oldnick, newnick))
        if oldnick in self.authorized.keys():
            self.sendnotice(newnick,
                "You have been logged out for security reasons. This happens automatically when you change your nick.")
            del self.authorized[oldnick]
        for element in self.chanlist.keys():
            if oldnick in self.chanlist[element].keys():
                self.chanlist[element][newnick] = self.chanlist[element][oldnick]
                del self.chanlist[element][oldnick]
                # Flush the logfile
        self.flush()

    def messageLoop(self, wut=None):
        self.m_protect = 0
        while self.m_protect < 5:
            user = ""
            message = ""
            try:
                item = self.messagequeue.pop(0).split(":", 1)
                user = item[0]
                message = item[1]
                if len(message) > 300:
                    self.sendmessage(user, message[:300] + "...")
                else:
                    self.sendmessage(user, message)
            except IndexError:
                break
            except Exception:
                try:
                    print("|! Failed to send message! Error: %s" % traceback.format_exc())
                    print("|! " + user + " -> " + message)
                except:
                    pass
            self.m_protect += 1
        reactor.callLater(2.5, self.messageLoop, ())

    def rawLoop(self, wut=None):
        self.r_protect = 0
        while self.r_protect < 5:
            item = ""
            try:
                item = self.rawqueue.pop(0)
                self.sendLine(item)
                print("|> server: %s" % item)
            except IndexError:
                break
            except Exception:
                try:
                    print("|! Failed to send raw data to server! Error: %s" % traceback.format_exc())
                    print("|! " + item)
                except:
                    pass
            self.r_protect += 1
        reactor.callLater(2.5, self.rawLoop, ())

    def noticeLoop(self, wut=None):
        self.n_protect = 0
        while self.n_protect < 5:
            user = ""
            message = ""
            try:
                item = self.noticequeue.pop(0).split(":", 1)
                user = item[0]
                message = item[1]
                if len(message) > 300:
                    self.sendntc(user, message[:300] + "...")
                else:
                    self.sendntc(user, message)
            except IndexError:
                break
            except Exception:
                try:
                    print("|! Failed to send notice! Error: %s" % traceback.format_exc())
                    print("|! " + user + " -> " + message)
                except:
                    pass
            self.n_protect += 1
        reactor.callLater(2.5, self.noticeLoop, ())

    def who(self, channel):
        """List the users in 'channel', usage: client.who('#testroom')"""
        self.send_raw('WHO %s' % channel)

    def irc_RPL_WHOREPLY(self, *nargs):
        """Receive WHO reply from server"""
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

        hostmask = nick + "!" + ident + "@" + host

        if not channel in self.chanlist.keys():
            self.chanlist[channel] = {}

        done = {"ident": ident, "host": host, "server": server, "realname": gecos.split(" ")[1], "op": False,
                "voice": False, "oper": False, "away": False, "last_time": float(time.time() - 0.25),
                "hostmask": hostmask}
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
        """Called when WHO output is complete"""
        # ('eldridge.esper.net', ['McPlusPlus_Testing', '#mc++', 'End of /WHO list.'])
        server = nargs[0]
        data = nargs[1]
        my_nick = data[0]
        channel = data[1]
        message = data[2]

        ops = 0
        voices = 0
        opers = 0
        aways = 0

        for element in self.chanlist[channel]:
            if element["voice"]:
                voices += 1
            if element["op"]:
                ops += 1
            if element["oper"]:
                opers += 1
            if element["away"]:
                aways += 1
        print("|= %s users on %s (%s voices, %s ops, %s opers, %s away)" % (
        len(self.chanlist[channel]), channel, voices, ops, opers, aways))

    def irc_unknown(self, prefix, command, params):
        """Print all unhandled replies, for debugging."""

        # Prefix: asimov.freenode.net
        # Command: RPL_BANLIST
        # Params: ['MCBans_Testing', '#mcbans-test', 'a!*@*', 'gdude2002!g@unaffiliated/gdude2002', '1330592882']

        if command == "RPL_BANLIST":
            me = params[0]
            channel = params[1]
            mask = params[2]
            owner = params[3]
            time = params[4]
            server = prefix

            if channel not in self.banlist.keys():
                done = {"done": False, "total": 1}
                banmask = {"owner": owner.split("!")[0], "ownerhost": owner, "time": time, "mask": mask,
                           "channel": channel}
                done[mask] = banmask
                self.banlist[channel] = done

            else:
                if not self.banlist[channel]["done"]:
                    banmask = {"owner": owner.split("!")[0], "ownerhost": owner, "time": time, "mask": mask,
                               "channel": channel}
                    self.banlist[channel][mask] = banmask
                    self.banlist[channel]["total"] += 1

                else:
                    done = {"done": False, "total": 1}
                    banmask = {"owner": owner.split("!")[0], "ownerhost": owner, "time": time, "mask": mask,
                               "channel": channel}
                    done[mask] = banmask
                    self.banlist[channel] = done

        elif command == "RPL_ENDOFBANLIST":
            me = params[0]
            channel = params[1]
            message = params[2]
            server = prefix

            if channel in self.banlist.keys():
                self.banlist[channel]["done"] = True
            else:
                self.banlist[channel] = {"done": True, "total": 0}

            self.prnt("|= Got %s bans for %s." % (self.banlist[channel]["total"], channel))

            if self.is_op(channel, self.nickname):
                stuff = self.banlist[channel].keys()
                stuff.remove("done")
                stuff.remove("total")

                for element in stuff:
                    if stuff == "*!*@*":
                        self.send_raw("KICK %s %s :Do not set such ambiguous bans!" % (
                        self.banlist[channel][element]["owner"], user))
                        self.send_raw("MODE %s -b *!*@*" % channel)
                        self.send_raw(
                            "MODE %s +b *!*@%s" % (channel, self.banlist[channel][element]["ownerhost"].split("@")[1]))
                    else:
                        self.checkban(channel, element, self.banlist[channel][element]["owner"])


                        # elif command != "RPL_NAMREPLY" and command != "RPL_ENDOFNAMES":
                        #     self.prnt("Prefix: %s" % prefix)
                        #     self.prnt("Command: %s" % command)
                        #     self.prnt("Params: %s" % params)


    #-#################################-#
    #                                   |
    #       UTILITY   #   FUNCTIONS     #
    #                                   |
    #-#################################-#

    def cmsg(self, message):
        # Send a message to all joined channels
        for element in self.joinchans:
            self.sendmsg("#" + element[0], message.encode('ascii', 'ignore'))

    def cnotice(self, message):
        # Notice all channels
        for element in self.joinchans:
            self.sendnotice("#" + element[0], message.encode('ascii', 'ignore'))

    # Don't use this directy, use sendmsg
    def sendmessage(self, user, message):
        if user == "NickServ":
            self.prnt("|> <%s> %s" % (user, ("*" * len(message))))
        else:
            self.prnt("|> <%s> %s" % (user, message))
        self.msg(user, message)
        # Flush the logfile
        self.flush()

    def send_raw(self, data):
        self.rawqueue.append(str(data))

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
        self.prnt("|> -%s- %s" % (user, message))
        self.notice(user, message)
        # Flush the logfile
        self.flush()

    def sendmsg(self, user, message):
        self.messagequeue.append(str(user) + ":" + str(message))

    def sendnotice(self, user, message):
        self.noticequeue.append(str(user) + ":" + str(message))

    def senddescribe(self, user, message):
        self.prnt("|> * %s: %s" % (user, message))
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
        settings.read("config/settings.ini")
        self.nickname = settings.get("info", "nickname")
        del settings

    def prnt(self, msg):
        colprint(msg)
        self.logfile = open("output.log", "a")
        self.logfile.write("%s\n" % (colstrip(msg)))
        self.logfile.flush()
        self.logfile.close()

    def clientConnectionLost(self, connector, reason):
        # We died. Onoes!
        self.prnt("Lost connection: %s" % reason)

    def clientConnectionFailed(self, connector, reason):
        # Couldn't connect. Daww!
        self.prnt("Could not connect: %s" % reason)
