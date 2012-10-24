# coding=utf-8
import mechanize
from system.yaml_loader import *

class plugin(object):
    """
    Play russian roulette, the safe way!
    """

    commands = {
        "urltitle": "url_options",
        "fetchtitle": "fetch_title",
    }

    hooks = {
        "connectionLost": "save",
        "signedOn": "load",
        "privmsg": "privmsg"
    }

    # Extensions the page title parser shouldn't parse
    notParse = ["png", "jpg", "jpeg", "tiff", "bmp", "ico", "gif", "iso", "bin", "pub", "ppk", "doc", "docx", "xls",
                "xlsx", "ppt", "pptx", "svg"]

    def __init__(self, irc):
        self.irc = irc
        self.settings = yaml_loader(True, "urltitlefetcher")

        self.channels = {}

        self.help = {
            "urltitle": "Toggle url title fetching for the current channel.\n" +
                        ("Usage: %surltitle [all|on|off]\n" % self.irc.control_char) +
                        "all = all users, on = voiced and up, off = no-one",
            "fetchtitle": "Fetch the title of a given URL.\n" +
                     ("Usage: %sfetchtitle <url>\n" % self.irc.control_char) +
                     "NOTE: If title fetching is off in the current channel, this will notice the user rather than message the channel if they are not voiced or above.",
        }

    def load(self):
        self.channels = self.settings.load("channels")

    def save(self, data=None):
        self.settings.save_data("channels", {"channels": self.channels})

    def privmsg(self, data):
        user = data['user']
        channel = data['channel']
        message = data['message']

        if channel not in self.channels:
            self.channels[channel] = "on"

        if self.channels[channel] == "all" or (self.channels[channel] == "on" and (self.irc.is_voice(channel, user) or self.irc.is_op(channel, user))):
            title, domain = self.pagetitle(message)
            if title is None:
                self.irc.sendmsg(channel, "Error while fetching title")
            else:
                self.irc.sendmsg(channel, "\"%s\" at %s" % (title, domain))

    def url_options(self, user, channel, arguments):
        if len(arguments) == 1:
            if channel not in self.channels:
                self.channels[channel] = "on"
            self.irc.sendnotice(user, "URL title fetching for this channel is %s" % (self.channels[channel]))
        elif len(arguments) == 2:
            arguments[1] = arguments[1].lower()
            if arguments[1] == "on" or arguments[1] == "true":
                self.channels[channel] = "on"
            elif arguments[1] == "off" or arguments[1] == "false":
                self.channels[channel] = "off"
            elif arguments[1] == "all":
                self.channels[channel] = "all"
            else:
                self.irc.sendnotice(user, "Invalid option given for title matching")
                return
            self.irc.sendnotice(user, "URL title fetching for this channel has been set to %s" % (self.channels[channel]))


    def fetch_title(self, user, channel, arguments):
        if len(arguments) == 2:
            title, domain = self.pagetitle(arguments[1])
            if title is None:
                self.irc.sendnotice(user, "Error while fetching title")
            else:
                if self.channels[channel] == "all" or (self.channels[channel] == "on" and (self.irc.is_voice(channel, user) or self.irc.is_op(channel, user))):
                    self.irc.sendmsg(channel, "\"%s\" at %s" % (title, domain))
                else:
                    self.irc.sendnotice(user, "\"%s\" at %s" % (title, domain))
        else:
            #TODO Show usage
            pass

    def pagetitle(self, url):
        if not url.split(".")[-1] in self.notParse:
            domain = ""
            try:
                if url.lower().startswith("http://"):
                    domain = url.split("http://")[1].split("/")[0]
                elif url.lower().startswith("https://"):
                    domain = url.split("https://")[1].split("/")[0]
                br = mechanize.Browser()
                br.addheaders = [('User-agent',
                              'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9-1.fc9 Firefox/3.0.1')]
                br.set_handle_robots(False)
                br.open(url)
                return br.title(), domain
            except Exception as e:
                return None, None

    name = "URL Title Fetcher"
