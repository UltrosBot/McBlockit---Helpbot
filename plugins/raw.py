class plugin(object):

    """
    This plugin is used to look up
    users in the MCBans staff list.
    It uses urllib2 to handle http errors.
    """

    commands = {
        "raw": "send_raw"
    }

    def __init__(self, irc):
        self.irc = irc
        self.help = {
            "raw": "Send raw data to the IRC server\nUsage: %sraw <data>\nNOTE: Requires you to be logged in" % self.irc.control_char
        }

    def send_raw(self, user, channel, arguments):
        if user in self.irc.authorized.keys():
            if arguments[1:]:
                self.irc.send_raw(" ".join(arguments[1:]))
                self.irc.sendnotice(user, "Done!")
            else:
                self.irc.sendnotice(user, "Usage: %sraw <data>" % self.irc.control_char)
        else:
            self.irc.sendnotice(user, "You do not have access to this command.")

    hooks = {}

    name = "Send raw plugin"
