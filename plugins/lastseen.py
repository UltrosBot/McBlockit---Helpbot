# coding=utf-8
class plugin(object):

    """
    This is a test plugin to show exactly how
    the plugin system works. Feel free to use
    this as a base for your other plugins.
    """

    hooks = {}

    name = "Lastseen"

    commands = {
        "lastseen": "lastseen"
    }

    def __init__(self, irc):
        self.irc = irc
        self.help = {
            "lastseen": "Check when the bot last saw activity from a user\nUsage: %slastseen <username>" % self.irc.control_char
        }
    
    def lastseen(self, user, channel, arguments):
        self.irc.sendnotice(user, "Test.")


