import time

from system.constants import *

class Logger(object):

    cols = []

    def __init__(self):
        for x in range(0, 16):
            for y in range(0, 16):
                self.cols.append(col + str(x).zfill(2) + "," + str(y).zfill(2) )
        print "\n".join(self.cols)

    # Internal functions

    def _getTimestamp(self):
        time.strftime("%H:%M:%S")

    def _write(self, file, message):
        fh = open("logs/" + file, "a")
        fh.write(message)
        fh.flush()
        fh.close()
        pass

    # Logging levels

    def info(self, message, toFile):
        """Log a message with the INFO warning level"""
        pass

    def warn(self, message, toFile):
        """Log a message with the WARN warning level"""
        pass

    def error(self, message, toFile):
        """Log a message with the ERROR warning level"""
        pass

    # No file-writing

    def nolog(self, message):
        """Write a message to the console without logging it to file"""
        pass

    # Section-specific logging

    def web(self, request, message):
        """Internal, logs details aboout a web request"""
        pass

    def ircPublic(self, user, channel, message):
        """Internal, log a message from a channel"""
        pass

    def ircPrivate(self, user, message):
        """Internal, log a message from a query"""
        pass

    def ircPublicAction(self, user, channel, message):
        """Internal, log an action from a channel"""
        pass

    def ircPrivateAction(self, user, message):
        """Internal, log an action from a query"""
        pass

    def ircSendMessage(self, nick, target, message):
        """Internal, log a message we sent"""
        pass

    # Logging to the admin channel

    def chanLog(self, irc, message):
        """Log a message to the admin channel"""
        pass

Logger()