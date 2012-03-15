import random
from system.yaml_loader import *
from twisted.internet import reactor

class plugin(object):
    """
    Random lyrics <3
    """
    
    name = "lyrics"
    
    commands = {
        "sing": "singCommand",
        "reloadlyrics": "loadconfigs",
    }

    hooks = {
        "userJoined": "userJoined"
    }
    
    def __init__(self, irc):
        self.irc = irc
        self.loadconfigs()
        self.singing = False
    
    def loadconfigs(self, user=False, *args):
        if (not user) or (user in self.irc.authorized.keys()):
            self.settings_handler = yaml_loader(True, "lyrics")
            self.settings = self.settings_handler.load("settings")
            self.lyrics = self.settings_handler.load("lyrics")
            if user: self.irc.send_raw("NOTICE " + user + " :" + 'Lyrics reloaded!')
        else:
            if user: self.irc.send_raw("NOTICE " + user + " :" + "You're not autorized to use this command")
    
    def userJoined(self, data):
        #Do I feel like singing? :L
        if random.randint(1, self.settings["possibility"]) == 1:
            self.sing(data["channel"], data["user"])
        
    def singCommand(self, user, channel, arguments):
        self.sing(channel, user)
    
    def sing(self, channel, user, songID=''):
        #Check if I'm not singing already
        #And if I'm in a channel where I can sing
        if (not self.singing) and (channel in self.settings["channels"]):
            self.singing = True
            #If no argument was provided, randomly select a song
            print len(self.lyrics)
            if songID == '': songID = random.randint(1, len(self.lyrics))
            
            #Get the lyrics
            self.song = self.lyrics[songID]["song"].split("\n")
            self.song.insert(0,"A song just for you, " + user + " <3 (" + self.lyrics[songID]["link"] + ")")
            
            #Get the delay, and channel
            self.songdelay = self.lyrics[songID]["delay"]
            self.songchan = channel
            
            #Initialize the variable
            self.line = 0
            
            #Start singing
            self.singLines(channel)
    
    def singLines(self, channel):
        if self.line < len(self.song):
            #Print blank lines too
            if self.song[self.line] != '':
                self.irc.send_raw("PRIVMSG " + channel + " :" + self.song[self.line])
            
            self.line += 1
            
            #Delay
            reactor.callLater(self.songdelay, self.singLines, channel)
        else:
            #Song is up!
            self.irc.send_raw("PRIVMSG " + channel + " :" + "\o/")
            self.singing = False
