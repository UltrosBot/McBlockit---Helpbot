# coding=utf-8
import pprint
import json

from system.yaml_loader import *
from system.decorators import *

from twisted.internet import reactor
from twisted.web.server import Site
from twisted.web.resource import Resource, NoResource

def print_request(request):
    headers = request.requestHeaders

    if "x-forwarded-for" in headers:
        ips = headers["x-forwarded-for"]
    elif "x-real-ip" in headers:
        ips = headers["x-real-ip"]
    else:
        ips = [request.getClientIP()]
    for ip in ips:
        print "[WEB] %s %s: %s" % (ip, request.method, request.uri)

class plugin(object):

    """
    This is a webserver. It provides access to the bot using
    a variety of JSON APIs, as well as supporting various
    external services via webhooks.

    Oh boy, are we excited about /this/ plugin!
    """

    hooks = {}

    name = "Webserver"

    commands = {
#        "test": "test"
    }

    def __init__(self, irc):
        self.irc = irc
        self.help = {
#            "test": "You must be really bored, eh?\nUsage: %stest" % self.irc.control_char
        }

        self.settings_handler = yaml_loader(True, "web")
        self.settings = self.settings_handler.load("settings")

        resource = BaseResource(irc)
        factory = Site(resource)
        reactor.listenTCP(8080, factory)
#        reactor.run()

class BaseResource(Resource):

    isLeaf = False

    children = {}

    def __init__(self, irc):
        Resource.__init__(self)
        self.irc = irc
        self.children = {"api": ApiResource(irc), "test": TestResource(irc), "": self}

    def render_GET(self, request):
        print_request(request)
        return "This is the base resource. Check out <a href=\"test\">/test</a> and <a href=\"api\">/api</a> for more."

    def getChild(self, path, request):
        print "[WEB] Error: Resource not found"
        if path not in self.children.keys():
            return NoResource()


class ApiResource(Resource):

    isLeaf = False

    children = {}

    def __init__(self, irc):
        Resource.__init__(self)
        self.irc = irc
        self.children = {"github": GithubResource(irc), "": self}

    def render_GET(self, request):
        print_request(request)
#        if "messages" in request.args.keys():
#            for msg in request.args["messages"]:
#                self.irc.sendmsg("#mcblockit-test", msg)
        return "Grats, you found the API resource! Nothing here yet, though.."

    def getChild(self, path, request):
        if path not in self.children.keys():
            print "[WEB] Error: Resource not found"
            return NoResource()

class GithubResource(Resource):

    isLeaf = True
    def __init__(self, irc):
        Resource.__init__(self)
        self.irc = irc
        settings_handler = yaml_loader(True, "web")
        settings = settings_handler.load("github")
        self.repos = settings["projects"]

    def render_GET(self, request):
        print_request(request)
        return "Grats, you found the API resource! Nothing here yet, though.."

    def render_POST(self, request):
        print_request(request)
        settings_handler = yaml_loader(True, "web")
        settings = settings_handler.load("github")
        self.repos = settings["projects"]
        try:
            for payload in request.args["payload"]:
                payload = json.loads(payload)
                repo = payload["repository"]
                head = payload["head_commit"]

                author = head["author"]["name"]
                repo_name = repo["name"]
                added = len(head["added"])
                modified = len(head["modified"])
                removed = len(head["removed"])
                message = head["message"]
                commits = len(payload["commits"])

                if repo_name in self.repos:
                    for channel in self.repos[repo_name]:
                        self.irc.sendmsg(channel, "%s pushed a commit to %s (%sa/%sm/%sd) - \"%s\" [Total: %s commits]" %
                                                  (author, repo_name, added, modified, removed, message, commits))
                else:
                    print "[WEB] Alert - Recieved data for a repo we don't follow: \"%s\"" % repo_name
                    return json.dumps({"result": "error", "error": "Not following that repo!"})
        except Exception as e:
            print "[WEB] Error: %s" % e
            return json.dumps({"result": "error", "error": str(e)})
        else:
            return json.dumps({"result": "success"})

class TestResource(Resource):

    isLeaf = True
    def __init__(self, irc):
        Resource.__init__(self)
        self.irc = irc

    def render_GET(self, request):
        print_request(request)
        return "Request: %s<br/><br/>"\
               "Path: %s<br/><br/>"\
               "Args: %s<br/><br/>"\
               "Headers: %s<br /><br />"\
               "IRC: %s" % (str(request).replace("<", "&lt;").replace(">", "&gt;"),
                                request.path, request.args, request.requestHeaders, pprint.pformat(self.irc.chanlist, 2).replace(" ", "&nbsp;").replace("\n", "<br />"))