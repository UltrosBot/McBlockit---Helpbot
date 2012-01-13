class plugin(object):

    commands = {
        "test": "test"
    }
    
    def __init__(self, irc):
        self.irc = irc
    
    def test(self, user, channel, arguments):
        "A test command"
        self.irc.sendnotice(user, "Success!")

    hooks = {}

    name = "Test plugin"
