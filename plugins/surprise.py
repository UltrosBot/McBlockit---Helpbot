# coding=utf-8
class plugin(object):

    """
    Surprise!
    """

    def __init__(self, irc):
        self.irc = irc
        self.help = {
            "surprise": "Surprise buttsecks!\nUsage: %ssurprise <username>(:channel)" % self.irc.control_char
        }

    commands = {
        "surprise": "surprise",
        "rape": "surprise"
    }
    
    def surprise(self, user, channel, arguments):
        if not (user.lower() in ["peach", "peaches", "ruef"]):
            self.irc.send_raw("PRIVMSG " + channel + " :Who the heck are you? Get off my lawn! >:U")
            return
        if len(arguments) > 1:
            target = arguments[1]
        else:
            self.irc.send_raw("PRIVMSG " + channel + " :Read the help, fool!")
            return
        target_user = arguments[1]
        target_channel = channel
        if ":" in target:
            target_user = target.split(":", 1)[0]
            target_channel = target.split(":", 1)[1]
        if target_user.lower() == self.irc.nickname.lower():
            self.irc.send_raw("PRIVMSG " + target_channel + " :" + "I hate surprises. >:3")
            return
        mstring = "SURPRISE BUTTSECKS!"
        kstring = "You've been Peached. C:<"
        self.irc.send_raw("PRIVMSG " + target_channel + " :" + mstring)
        if (self.irc.is_op(target_channel, user) or user in self.irc.authorized.keys()) and self.irc.is_op(channel, self.irc.nickname):
            self.irc.send_raw("KICK %s %s :%s" % (target_channel, target_user, kstring))
        else:
            self.irc.send_raw("PRIVMSG %s :%s" % (target_channel, kstring))

    hooks = {}

    name = "Rape"
