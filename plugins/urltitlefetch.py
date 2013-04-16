# coding=utf-8
import json
import mechanize
import urllib
import urllib2
import urlparse
from system.yaml_loader import *

class plugin(object):
    """
    URL parser; used to fetch titles for URLs pasted in IRC.
    """

    name = "URL Title Fetcher"

    commands = {
        "urltitle": "url_options",
        "title": "fetch_title",
        "shorturl": "fetch_short_url"
    }

    hooks = {
        "connectionLost": "save",
        "signedOn": "load",
        "privmsg": "privmsg"
    }

    # Extensions the page title parser shouldn't parse
    notParse = ["png", "jpg", "jpeg", "tiff", "bmp", "ico", "gif", "iso", "bin", "pub", "ppk", "doc", "docx", "xls",
                "xlsx", "ppt", "pptx", "svg"]

    channels = {}

    def __init__(self, irc):
        self.irc = irc
        self.settings = yaml_loader(True, "urltitlefetcher")

        self.channels = {}

        self.help = {
            "urltitle": "Toggle url title fetching for the current channel.\n" +
                        ("Usage: %surltitle [all|on|off]\n" % self.irc.control_char) +
                        "all = all users, on = voiced and up, off = no-one",
            "title":    "Fetch the title of a given URL, or the last URL sent to the channel if no URL is given.\n" +
                        ("Usage: %stitle [url]\n" % self.irc.control_char) +
                        "NOTE: If title fetching is off in the current channel, this will notice the user rather than message the channel if they are not voiced or above.",
            "shorturl": "Get a short URL for a given URL, or the last URL sent to the channel if no URL is given.\n" +
                        ("Usage: %sshorturl [url]\n" % self.irc.control_char) +
                        "NOTE: If title fetching is off in the current channel, this will notice the user rather than message the channel if they are not voiced or above."
            }

        self.YOUTUBE_LOGO = irc.col + "1,0YOU" + irc.col + "0,4TUBE" + irc.col
        self.OUTPUT_YOUTUBE_VIDEO = "[" + self.YOUTUBE_LOGO + " Video] %s (%s) by %s, %s likes, %s dislikes, %s views"
        self.OUTPUT_YOUTUBE_PLAYLIST = "[" + self.YOUTUBE_LOGO + " Playlist] %s (%s videos, total %s) by %s - \"%s\""
        self.OUTPUT_YOUTUBE_CHANNEL = "[" + self.YOUTUBE_LOGO + " Channel] %s (%s subscribers, %s videos with %s total views) - \"%s\""

        self.YOUTUBE_DESCRIPTION_LENGTH = 75

    def load(self):
        self.channels = self.settings.load("channels")
        if not self.channels:
            self.channels = {}

    def save(self, data=None):
        self.settings.save_data("channels", self.channels)

    def setup_channel(self, channel):
        """
        Initialises the channel settings if they have not yet been done
        """
        if not self.channels.has_key(channel):
            self.channels[channel] = {"status": "all", "last": None}
        elif not isinstance(self.channels[channel], dict):
            #I assume this is in case an old config is loaded where there is only one option per channel, rather than a dict of options
            self.channels[channel] = {"status": self.channels[channel], "last": None}

    def privmsg(self, data):
        user = data['user']
        channel = data['channel']
        message = data['message']

        pos = message.find("http://")
        if pos > -1:
            self.setup_channel(channel)
            end = message.find(" ", pos)
            if end > -1:
                url = message[pos:end]
            else:
                url = message[pos:]
            self.channels[channel]["last"] = url
            msg = self.get_url_message(url)
            if msg is not None:
                self.send_to_right_place(msg, channel, user)

    def fetch_title(self, user, channel, arguments):
        self.setup_channel(channel)
        url = None
        if len(arguments) == 2:
            url = arguments[1]
        elif self.channels[channel]["last"] is not None:
            url = self.channels[channel]["last"]
        else:
            return
        msg = self.get_url_message(url)
        if msg is None:
            msg = "No title or not a URL"
        self.send_to_right_place(msg, channel, user)

    def url_options(self, user, channel, arguments):
        self.setup_channel(channel)
        if len(arguments) == 1:
            self.irc.sendnotice(user, "URL title fetching for this channel is %s" % (self.channels[channel]["status"]))
        elif len(arguments) == 2:
            arguments[1] = arguments[1].lower()
            if arguments[1] == "on" or arguments[1] == "true":
                self.channels[channel]["status"] = "on"
            elif arguments[1] == "off" or arguments[1] == "false":
                self.channels[channel]["status"] = "off"
            elif arguments[1] == "all":
                self.channels[channel]["status"] = "all"
            else:
                self.irc.sendnotice(user, "Invalid option given for title matching")
                return
            self.irc.sendnotice(user, "URL title fetching for this channel has been set to %s" % (self.channels[channel]["status"]))

    def fetch_short_url(self, user, channel, arguments):
        self.setup_channel(channel)
        url = None
        if len(arguments) == 2:
            url = arguments[1]
        elif self.channels[channel]["last"] is not None:
            url = self.channels[channel]["last"]
        else:
            return
        tiny = self.short_url(url)
        if tiny is None:
            tiny = "Could not get short url"
        self.send_to_right_place("Short URL %s for %s" % (tiny, url), channel, user)

    def send_to_right_place(self, message, channel, user):
        """
        Send the given message to the right place, depending on channel settings.
        If channel status is all:
            send to channel
        If channel status is on:
            If user is voice+;
                send to channel
            Else:
                notice to user
        Else:
            notice to user
        """
        if self.channels[channel]["status"] == "all" or (self.channels[channel]["status"] == "on" and (self.irc.is_voice(channel, user) or self.irc.is_op(channel, user))):
            self.irc.sendmsg(channel, message)
        else:
            self.irc.sendnotice(user, message)

    def short_url(self, url):
        """
        Returns a tinyurl.com short url
        """
        return urllib2.urlopen("http://tinyurl.com/api-create.php?url=" + urllib.quote_plus(url)).read()

    def get_url_message(self, url):
        message = self.special_domain(url)
        if message is None:
            title, domain = self.page_title(url)
            if title is None:
                return None
            message = "\"%s\" at %s" % (title, domain)
        return message

    def page_title(self, url):
        """
        Get the page title and domain
        """
        #TODO: mechanize seems expensive compared to urllib and lxml/beautifulsoup - have a look into that
        if url.split(".")[-1] in self.notParse:
            return None, None
        else:
            domain = ""
            try:
                if url.lower().startswith("http://"):
                    domain = url.split("http://")[1].split("/")[0]
                    secure = False
                elif url.lower().startswith("https://"):
                    domain = url.split("https://")[1].split("/")[0]
                    secure = True
                else:
                    return None, None
                br = mechanize.Browser()
                br.addheaders = [('User-agent',
                                  'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9-1.fc9 Firefox/3.0.1')]
                br.set_handle_robots(False)
                br.open(url)
                goturl = br.geturl()
                rtitle = goturl + "/"
                if secure:
                    rtitle = rtitle.split("https://")[1].split("/")[0]
                else:
                    rtitle = rtitle.split("http://")[1].split("/")[0]

                return br.title(), rtitle
            except Exception as e:
                if not str(e).lower() == "not viewing html":
                    return str(e), domain
                return None, None

    def special_domain(self, url):
        """
        Returns the message to be displayed if it is a special domain, or None if it should be treated regularly
        """
        parsed = urlparse.urlparse(url)
        hostname = parsed.hostname.lower()
        if hostname[:4] == "www.":
            hostname = hostname[4:]
        if hostname == "youtube.com":
            if parsed.path.lower() == "/watch":
                params = urlparse.parse_qs(parsed.query)
                if "v" in params and len(params["v"]) > 0:
                #try:
                    video_data = json.loads(urllib2.urlopen("http://gdata.youtube.com/feeds/api/videos/" + params["v"][0] + "?v=2&alt=json").read())
                    title = video_data["entry"]["media$group"]["media$title"]["$t"]
                    uploader = video_data["entry"]["media$group"]["media$credit"][0]["yt$display"]
                    time = self.seconds_to_time(int(video_data["entry"]["media$group"]["yt$duration"]["seconds"]))
                    views = video_data["entry"]["yt$statistics"]["viewCount"]
                    likes = video_data["entry"]["yt$rating"]["numLikes"]
                    dislikes = video_data["entry"]["yt$rating"]["numDislikes"]
                    return self.OUTPUT_YOUTUBE_VIDEO % (title, time, uploader, likes, dislikes, views)
                    #except:
                    pass
            elif parsed.path.lower() == "/playlist":
                params = urlparse.parse_qs(parsed.query)
                if "list" in params and len(params["list"]) > 0:
                    try:
                        playlist_data = json.loads(urllib2.urlopen("http://gdata.youtube.com/feeds/api/playlists/" + params["list"][0] + "?v=2&alt=json").read())
                        title = playlist_data["feed"]["title"]["$t"]
                        author = playlist_data["feed"]["author"][0]["name"]["$t"]
                        description = playlist_data["feed"]["subtitle"]["$t"]
                        #Limit description length
                        if len(description) > self.YOUTUBE_DESCRIPTION_LENGTH:
                            description = description[:self.YOUTUBE_DESCRIPTION_LENGTH - 3] + "..."
                        count = len(playlist_data["feed"]["entry"])
                        seconds = 0
                        for entry in playlist_data["feed"]["entry"]:
                            seconds += int(entry["media$group"]["yt$duration"]["seconds"])
                        time = self.seconds_to_time(seconds)
                        return self.OUTPUT_YOUTUBE_PLAYLIST % (title, count, time, author, description)
                    except:
                        pass
            elif parsed.path.lower().startswith("/user/"):
                parts = parsed.path.split("/")
                if len(parts) >= 3:
                    try:
                        user_data = json.loads(urllib2.urlopen("http://gdata.youtube.com/feeds/api/users/" + parts[2] + "?v=2&alt=json").read())
                        name = user_data["entry"]["title"]["$t"]
                        description = user_data["entry"]["summary"]["$t"]
                        #Limit description length
                        if len(description) > self.YOUTUBE_DESCRIPTION_LENGTH:
                            description = description[:self.YOUTUBE_DESCRIPTION_LENGTH - 3] + "..."
                        subscribers = user_data["entry"]["yt$statistics"]["subscriberCount"]
                        views = user_data["entry"]["yt$statistics"]["totalUploadViews"]
                        videos = None
                        for entry in user_data["entry"]["gd$feedLink"]:
                            if entry["rel"].endswith("#user.uploads"):
                                videos = entry["countHint"]
                                break
                        return self.OUTPUT_YOUTUBE_CHANNEL % (name, subscribers, videos, views, description)
                    except:
                        pass
        elif hostname == "osu.ppy.sh":
            parts = parsed.path.split("/")
            if len(parts) >= 3:
                if parts[1] == "b":
                    osu_map = parts[2]
                    #TODO: Get the map data and return a nice message
                elif parts[1] == "s":
                    osu_map = parts[2]
                    #TODO: Get the score data and return a nice message
                elif parts[1] == "u":
                    osu_user = parts[2]
                    #TODO: Get the user data and return a nice message
            #Not a special URL or error while processing it - the calling code can get the html title tag instead
        return None

    def seconds_to_time(self, secs):
        #There's probably a more "pythonic" way to do this, but I didn't know of one
        m, s = divmod(secs, 60)
        if m >= 60:
            h, m = divmod(m, 60)
            return "%d:%02d:%02d" % (h, m, s)
        else:
            return "%d:%02d" % (m, s)