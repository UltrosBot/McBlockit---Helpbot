class plugin(object):

    """
    This is a test plugin to show exactly how
    the plugin system works. Feel free to use
    this as a base for your other plugins.
    """

    def __init__(self, irc):
        self.irc = irc
        self.help = {
            "test": "A test command\nUsage: %stest" % self.irc.control_char
        }

    commands = {
        "test": "test"
    }


    
    def test(self, user, channel, arguments):
        self.irc.sendnotice(user, "Success!")

    hooks = {}

    name = "Test plugin"
