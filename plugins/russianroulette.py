import random

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
                self.irc.send_raw("KICK %s %s :Bang!" % (channel, user))
            else:
                self.irc.sendmsg(channel, "BANG")
            self.irc.send_raw(channel +" :" + self.irc.ctcp + "ACTION reloads the gun" + self.irc.ctcp)
            self.chambersLeft = 6
            self.irc.send_raw(channel +" :" + 'There are %s new chambers. You have a %s%% chance of dying.' % (self.chambersLeft, int(100.0/self.chambersLeft)))
        else:
            #click
            self.chambersLeft -= 1
            self.irc.sendmsg(channel, '*click* You\'re safe for now. There are %s chambers left. You have a %s%% chance of dying.' % (self.chambersLeft, int(100.0/self.chambersLeft)))

    hooks = {}

    name = "Russian Roulette"
