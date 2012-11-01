# coding=utf-8
import mechanize
from system.yaml_loader import *

class plugin(object):
    """
    URL parser; used to fetch titles for URLs pasted in IRC.
    """

    commands = {
        "urltitle": "url_options",
        "title": "fetch_title",
    }

    hooks = {
        "connectionLost": "save",
        "signedOn": "load",
        "privmsg": "privmsg"
    }

    # Extensions the page title parser shouldn't parse
    notParse = ["png", "jpg", "jpeg", "tiff", "bmp", "ico", "gif", "iso", "bin", "pub", "ppk", "doc", "docx", "xls",
                "xlsx", "ppt", "pptx", "svg"]

    channels = {}

    def __init__(self, irc):
        self.irc = irc
        self.settings = yaml_loader(True, "urltitlefetcher")

        self.channels = {}

        self.help = {
            "urltitle": "Toggle url title fetching for the current channel.\n" +
                        ("Usage: %surltitle [all|on|off]\n" % self.irc.control_char) +
                        "all = all users, on = voiced and up, off = no-one",
            "title": "Fetch the title of a given URL.\n" +
                     ("Usage: %stitle <url>\n" % self.irc.control_char) +
                     "NOTE: If title fetching is off in the current channel, this will notice the user rather than message the channel if they are not voiced or above.",
        }

    def load(self):
        self.channels = self.settings.load("channels")
        if not self.channels:
            self.channels = {}

    def save(self, data=None):
        self.settings.save_data("channels", self.channels)

    def privmsg(self, data):
        user = data['user']
        channel = data['channel']
        message = data['message']

        if not self.channels.has_key(channel):
            self.channels[channel] = {"status": "on", "last": None}

        if not isinstance(self.channels[channel], dict):
            self.channels[channel] = {"status": self.channels[channel], "last": None}

        if self.channels[channel]["status"] == "all" or (self.channels[channel]["status"] == "on" and (self.irc.is_voice(channel, user) or self.irc.is_op(channel, user))):
            title, domain = self.pagetitle(message, channel)
            if not title is None:
                self.irc.sendmsg(channel, "\"%s\" at %s" % (title, domain))

    def url_options(self, user, channel, arguments):
        if len(arguments) == 1:
            if not self.channels.has_key(channel):
                self.channels[channel]["status"] = "on"
            if not isinstance(self.channels[channel], dict):
                self.channels[channel] = {"status": self.channels[channel], "last": None}
            self.irc.sendnotice(user, "URL title fetching for this channel is %s" % (self.channels[channel]["status"]))
        elif len(arguments) == 2:
            arguments[1] = arguments[1].lower()
            if arguments[1] == "on" or arguments[1] == "true":
                self.channels[channel]["status"] = "on"
            elif arguments[1] == "off" or arguments[1] == "false":
                self.channels[channel]["status"] = "off"
            elif arguments[1] == "all":
                self.channels[channel]["status"] = "all"
            else:
                self.irc.sendnotice(user, "Invalid option given for title matching")
                return
            self.irc.sendnotice(user, "URL title fetching for this channel has been set to %s" % (self.channels[channel]["status"]))


    def fetch_title(self, user, channel, arguments):
        if not self.channels.has_key(channel):
            self.channels[channel]["status"] = "on"
        if not isinstance(self.channels[channel], dict):
            self.channels[channel] = {"status": self.channels[channel], "last": None}
        if len(arguments) == 2:
            title, domain = self.pagetitle(arguments[1], channel)
            if title is None:
                self.irc.sendnotice(user, "No title or not a URL")
            else:
                if self.channels[channel]["status"] == "all" or (self.channels[channel]["status"] == "on" and (self.irc.is_voice(channel, user) or self.irc.is_op(channel, user))):
                    self.irc.sendmsg(channel, "\"%s\" at %s" % (title, domain))
                else:
                    self.irc.sendnotice(user, "\"%s\" at %s" % (title, domain))
        elif not self.channels[channel]["last"] == None:
            title, domain = self.pagetitle(self.channels[channel]["last"], channel)
            if title is None:
                self.irc.sendnotice(user, "No title or not a URL")
            else:
                if self.channels[channel]["status"] == "all" or (self.channels[channel]["status"] == "on" and (self.irc.is_voice(channel, user) or self.irc.is_op(channel, user))):
                    self.irc.sendmsg(channel, "\"%s\" at %s (%s)" % (title, domain, self.channels[channel]["last"]))
                else:
                    self.irc.sendnotice(user, "\"%s\" at %s (%s)" % (title, domain, self.channels[channel]["last"]))

    def pagetitle(self, url, channel):
        if not url.split(".")[-1] in self.notParse:
            domain = ""
            try:
                if url.lower().startswith("http://"):
                    domain = url.split("http://")[1].split("/")[0]
                elif url.lower().startswith("https://"):
                    domain = url.split("https://")[1].split("/")[0]
                else:
                    return None, None
                self.channels[channel]["last"] = url
                br = mechanize.Browser()
                br.addheaders = [('User-agent',
                              'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9-1.fc9 Firefox/3.0.1')]
                br.set_handle_robots(False)
                br.open(url)
                return br.title(), domain
            except Exception as e:
                if not str(e).lower() == "not viewing html":
                    return str(e), domain
                return None, None

    name = "URL Title Fetcher"
