import re
import string
import urllib2

class plugin(object):

    """
    This plugin is used to look up
    users in the MCBans staff list.
    It uses urllib2 to handle http errors.
    """

    commands = {
        "staff": "staff"
    }

    def __init__(self, irc):
        self.irc = irc
        self.help = {
            "staff": "Get information about our staff members\nUsage: %sstaff <username>" % self.irc.control_char
        }

    def getStaff(self):
        users = urllib2.urlopen('http://www.mcbans.com/staff?getStaff').read()
        return users.split("\n")

    def getUser(self, users, user):
        for rawline in users:
            splitline = rawline.split(':')
            if splitline[0] == user or splitline[1] == user:
                return splitline
        return 'NOUSER'

    def getUserInfo(self, user, rank):
        return urllib2.urlopen('http://www.mcbans.com/staff?getInfoOn=' + user + '&staffRank=' + rank).read()

    def stripHtml(self, input):
        input = string.replace(input, '<br/>', "\n")
        p = re.compile(r'<[^<]*?/?>')
        q = re.compile(r'\n{2,}')
        output = q.sub("\n", p.sub('', input))
        output = string.replace(output, '\nPosition Title:', ' - Position Title:')
        output = string.replace(output, 'About Me:\n', 'About Me: ')
        return output

    def staff(self, user, channel, arguments):
        if len(arguments) < 2:
            self.irc.sendnotice(user, 'You must provide a username.')
            return
        users = self.getStaff()
        staffMember = self.getUser(users, arguments[1])
        if staffMember == 'NOUSER':
            self.irc.sendnotice(user, 'No staff member by this name exists.')
        self.irc.sendnotice(user, self.stripHtml(self.getUserInfo(staffMember[0], staffMember[2])))

    hooks = {}

    name = "MCBans Staff Information"
