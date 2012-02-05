class plugin(object):

    """
    Play russian roulette, the safe way!
    """

    commands = {
        "rroulette": "shoot"
    }

    def __init__(self, irc):
        self.irc = irc
        self.help = {
            "rroulette": "Take a shot\nUsage: %srroulette" % self.irc.control_char
        }
        self.chambersLeft = 6

    def shoot(self, user, channel, arguments):
        if random.randint(1, self.chambersLeft) == 1:
            #BANG
            if self.irc.is_op(channel, self.irc.nickname):
                self.sendLine("KICK %s %s :Bang!" % (channel, user))
            else:
                self.irc.sendmsg(channel, "BANG")
            self.irc.sendmsg(channel, self.irc.ctcp + "ACTION reloads the gun" + self.irc.ctcp)
            self.chambersLeft = 6
            self.irc.sendmsg(channel, 'There are %s new chambers. You have a %.2f chance of dying.' % (self.chambersLeft, 100.0/self.chambersLeft))
        else:
            #click
            self.irc.sendmsg(channel, '*click* You\'re safe for now. There are %s chambers left. You have a %.2f chance of dying.' % (self.chambersLeft, 100.0/self.chambersLeft))

    hooks = {}

    name = "Russian Roulette"
