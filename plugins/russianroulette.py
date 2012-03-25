# coding=utf-8
import random
from system.yaml_loader import *

from system.decorators import *

class plugin(object):
    """
    Play russian roulette, the safe way!
    """

    commands = {
        "rroulette": "play",
        "rstats": "getstats",
        "shoot": "shoot"
    }

    hooks = {
        "connectionLost": "save",
        "signedOn": "load",
        "channelJoined": "newChannel"
    }

    def __init__(self, irc):
        self.irc = irc
        self.guns_handler = yaml_loader(True, "rroulette")
        self.stats_handler = yaml_loader(True, "rroulette")
        self.guns = self.guns_handler.load("guns")["guns"]
        self.stats = self.stats_handler.load("stats")

        self.channels = {}
        self.users = {}

        self.help = {
            "rroulette": "Bite the bullet.. or not?\nUsage: %srroulette" % self.irc.control_char,
            "shoot": "Shoot someone.\n" +
                     ("Usage: %sshoot <user>[:channel]\n" % self.irc.control_char) +
                     "NOTE: If opped and you are a voice or higher, this will kick the user.",
            "rstats": "Get stats about people and channels using this plugin.\n" +
                     "Usage: " + self.irc.control_char + "rstats <user/channel> <username/channelname> [stat]\n" +
                     "Valid stats: all, shots, deaths, players (Channel only), chambers (Channel only), games (User only)\n" +
                     "NOTE: If no stat is included, all stats will be returned."
        }

    def newChannel(self, data):
        channel = data["channel"]
        element = channel

        if element not in self.channels.keys():
            players = []
            curplayers = []
            shots = 0
            deaths = 0
            chambers = 6

            data = {"players": players, "shots": shots, "deaths": deaths, "chambers": chambers,
                    "curplayers": curplayers}

            self.channels[element] = data

    def load(self):
        self.guns = self.guns_handler.load("guns")["guns"]
        self.stats = self.stats_handler.load("stats")

        if self.stats:
            if self.stats["channels"]:
                for element in self.stats["channels"].keys():
                    data = self.stats["channels"][element]
                    self.channels[element] = data

            if self.stats["users"]:
                for element in self.stats["users"].keys():
                    data = self.stats["users"][element]
                    self.users[element] = data

        for element in self.irc.channels:
            channel = element
            if channel not in self.channels.keys():
                players = []
                curplayers = []
                shots = 0
                deaths = 0
                chambers = 6

                data = {"players": players, "shots": shots, "deaths": deaths, "chambers": chambers,
                        "curplayers": curplayers}

                self.channels[channel] = data

                for user in self.irc.chanlist[element].keys():
                    if user not in self.users.keys():
                        games = 0
                        shots = 0
                        deaths = 0

                        stuff = {"games": games, "shots": shots, "deaths": deaths}
                        self.users[user] = stuff

    def save(self, data=None):
        stuff = {"channels": self.channels, "users": self.users}
        self.stats_handler.save_data("stats", stuff)

    def getstats(self, user, channel, arguments):
        if len(arguments) > 2:
            type = arguments[1]
            about = arguments[2]
            stat = "all"
            if len(arguments) > 3:
                stat = arguments[3]
            possible_stats = ["all", "shots", "deaths", "players", "games", "chambers"]
            possible_types = ["user", "channel"]
            if type not in possible_types:
                self.irc.sendnotice(user, "Invalid type: %s - See %shelp rstats" % (type, self.irc.control_char))
            elif stat not in possible_stats:
                self.irc.sendnotice(user, "Invalid stat: %s - See %shelp rstats" % (stat, self.irc.control_char))
            elif stat in ["players", "chambers"] and type == "user":
                self.irc.sendnotice(user, "Invalid stat (%s) for type (%s) - See %shelp rstats" % (stat, type, self.irc.control_char))
            elif stat == "deaths" and type == "channel":
                self.irc.sendnotice(user, "Invalid stat (%s) for type (%s) - See %shelp rstats" % (stat, type, self.irc.control_char))
            else:
                if stat == "shots":
                    if type == "channel":
                        if about in self.channels.keys():
                            self.irc.sendnotice(user, "Shots in %s: %s" % (about, self.channels[about]["shots"]))
                        else:
                            self.irc.sendnotice(user, "There is no information for %s" % about)
                    else:
                        if about in self.users.keys():
                            self.irc.sendnotice(user, "Shots fired for %s: %s" % (about, self.users[about]["shots"]))
                        else:
                            self.irc.sendnotice(user, "There is no information for %s" % about)
                elif stat == "deaths":
                    if type == "channel":
                        if about in self.channels.keys():
                            self.irc.sendnotice(user, "Deaths in %s: %s" % (about, self.channels[about]["deaths"]))
                        else:
                            self.irc.sendnotice(user, "There is no information for %s" % about)
                    else:
                        if about in self.users.keys():
                            self.irc.sendnotice(user, "Deaths for %s: %s" % (about, self.users[about]["deaths"]))
                        else:
                            self.irc.sendnotice(user, "There is no information for %s" % about)
                elif stat == "players":
                    if about in self.channels.keys():
                        self.irc.sendnotice(user, "Total players in %s: %s" % (about, len(self.channels[about]["players"])))
                        if len(self.channels[about]["curplayers"]) > 0:
                            self.irc.sendnotice(user, "Current players in %s: (%s) %s" % (about, len(self.channels[about]["curplayers"]), ", ".join(self.channels[about]["curplayers"])))
                        else:
                            self.irc.sendnotice(user, "Nobody is currently playing in %s" % about)
                    else:
                        self.irc.sendnotice(user, "There is no information for %s" % about)
                elif stat == "chambers":
                    if about in self.channels.keys():
                        self.irc.sendnotice(user, "Chambers remaining for %s: %s" % (about, self.channels[about]["chambers"]))
                    else:
                        self.irc.sendnotice(user, "There is no information for %s" % about)
                elif stat == "games":
                    if about in self.users.keys():
                        self.irc.sendnotice(user, "Games %s has played in: %s" % (about, self.users[about]["games"]))
                    else:
                        self.irc.sendnotice(user, "There is no information for %s" % about)
                elif stat == "all":
                    if type == "channel":
                        if about in self.channels.keys():
                            self.irc.sendnotice(user, "Listing all stats for %s" % about)
                            self.irc.sendnotice(user, "Shots in %s: %s" % (about, self.channels[about]["shots"]))
                            self.irc.sendnotice(user, "Deaths in %s: %s" % (about, self.channels[about]["deaths"]))
                            self.irc.sendnotice(user, "Total players in %s: %s" % (about, len(self.channels[about]["players"])))
                            self.irc.sendnotice(user, "Chambers remaining for %s: %s" % (about, self.channels[about]["chambers"]))
                            if len(self.channels[about]["curplayers"]) > 0:
                                self.irc.sendnotice(user, "Current players in %s: (%s) %s" % (about, len(self.channels[about]["curplayers"]), ", ".join(self.channels[about]["curplayers"])))
                            else:
                                self.irc.sendnotice(user, "Nobody is currently playing in %s" % about)
                        else:
                            self.irc.sendnotice(user, "There is no information for %s" % about)
                    else:
                        if about in self.users.keys():
                            self.irc.sendnotice(user, "Listing all stats for %s" % about)
                            self.irc.sendnotice(user, "Shots fired for %s: %s" % (about, self.users[about]["shots"]))
                            self.irc.sendnotice(user, "Deaths for %s: %s" % (about, self.users[about]["deaths"]))
                            self.irc.sendnotice(user, "Games %s has played in: %s" % (about, self.users[about]["games"]))
                        else:
                            self.irc.sendnotice(user, "There is no information for %s" % about)
        else:
            self.irc.sendnotice(user, "Usage: %srstats <user/channel> <username/channelname> [stat]" % self.irc.control_char)

    def shoot(self, user, channel, arguments):
        if len(arguments) > 1:
            target = arguments[1]
            target_user = arguments[1]
            target_channel = channel
            if ":" in target:
                target_user = target.split(":", 1)[0]
                target_channel = target.split(":", 1)[1]
            self.irc.send_raw("PRIVMSG " + target_channel + " :" + self.irc.ctcp + "ACTION shoots " + target_user + self.irc.ctcp)
            if (self.irc.is_voice(target_channel, user) or self.irc.is_op(target_channel, user) or user in self.authorized.keys()) and self.irc.is_op(channel, self.irc.nickname):
                self.irc.send_raw("KICK %s %s :Bang!" % (target_channel, target_user))
            else:
                self.irc.send_raw("PRIVMSG %s :Bang!" % target_channel)

    def play(self, user, channel, arguments):
        chambers_left = self.channels[channel]["chambers"]

        if user not in self.users.keys():
            games = 0
            shots = 0
            deaths = 0

            stuff = {"games": games, "shots": shots, "deaths": deaths}
            self.users[user] = stuff

        if user not in self.channels[channel]["players"]:
            self.channels[channel]["players"].append(user)

        if user not in self.channels[channel]["curplayers"]:
            self.channels[channel]["curplayers"].append(user)
            self.users[user]["games"] += 1

        self.users[user]["shots"] += 1
        self.channels[channel]["shots"] += 1
        random.seed()

        if random.randint(1, chambers_left) == 1:
            #BANG
            if self.irc.is_op(channel, self.irc.nickname):
                self.irc.send_raw("KICK %s %s :Bang!" % (channel, user))
            else:
                self.irc.send_raw("PRIVMSG " + channel +" :BANG")
            self.irc.send_raw("PRIVMSG " + channel + " :" + self.irc.ctcp + "ACTION reloads the gun" + self.irc.ctcp)
            chambers_left = 6
            self.irc.send_raw(
                "PRIVMSG " + channel + " :" + 'There are %s new chambers. You have a %s%% chance of dying.' % (
                chambers_left, int(100.0 / chambers_left)))

            self.users[user]["deaths"] += 1
            self.channels[channel]["curplayers"] = []
            self.channels[channel]["deaths"] += 1
        else:
            #click
            chambers_left -= 1
            self.irc.sendmsg(channel,
                '*click* You\'re safe for now. There are %s chambers left. You have a %s%% chance of dying.' % (
                    chambers_left, int(100.0 / chambers_left)))
        self.channels[channel]["chambers"] = chambers_left
        self.save()

    name = "Russian Roulette"
