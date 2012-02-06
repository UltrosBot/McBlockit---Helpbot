import yaml, sys

from system.constants import *

class yaml_loader(object):

    def __init__(self, plugin=False):
        self.plugin = plugin
        self.data = {}

    def load(self, filename):
        if self.plugin:
            self.data = yaml.load(file("plugins/data/%s.yml" % filename))
        else:
            self.data = yaml.load(file(filename))
        return self.data

    def save(self, filename):
        done = [False, ""]
        try:
            if self.plugin:
                fh = open("plugins/data/%s.yml" % filename, "w")
                fh.write(yaml.dump(self.data))
                fh.flush()
                fh.close()
            else:
                fh = open(filename, "w")
                fh.write(yaml.dump(self.data))
                fh.flush()
                fh.close()
        except:
            done = [False, sys.exc_info()[0]]
        else:
            done = [True, ""]
        return done

    def __getitem__(self, item):
        return self.data[item]

    def __setitem__(self, key, value):
        self.data[key] = value

    def __delitem__(self, key):
        del self.data[key]

    def __contains__(self, item):
        return item in self.data

    def __iter__(self):
        return self.iterkeys()

    def __len__(self):
        return len(self.data)

    def iterkeys(self):
        return self.data.iterkeys()

    def keys(self):
        return self.data.keys()

