import os, string
import fnmatch

from evalfunctions import evalFunctions

from system.constants import *


class FAQ(object):
    def __init__(self, path, bot):
        self.path = path
        if not os.path.exists(path):
            os.mkdir(path)
        self.bot = bot
        self.evalObj = evalFunctions(bot)

    def get(self, entry, cinfo):
        entry = entry + ".txt"
        path = self.path
        epath = path + "/" + entry
        if os.path.exists(epath):
            fh = open(epath, "r")
            data = fh.read()
            fh.close()
            del fh
            rdata = data.split("\n")
            try:
                rdata.remove("")
            except:
                pass
            done = []
            for element in rdata:
                if "$(" in element and ")" in element:
                    stuff = element.split("$(", 1)
                    stuff = stuff[1].split(")")
                    del stuff[-1]
                    stuff = ")".join(stuff)
                    try:
                        result = self.evalObj.seval(stuff, cinfo)
                    except Exception as e:
                        result = str(e)
                    element = element.replace("$(%s)" % stuff, result)
                    if "\n" in element:
                        for part in element.split("\n"):
                            if part.strip() != "":
                                done.append(part)
                    else:
                        done.append(element)
                else:
                    done.append(element)

            return[True, done]
        else:
            return [False, ERR_NO_SUCH_ENTRY]

    def get_noeval(self, entry, cinfo):
        entry = entry + ".txt"
        path = self.path
        epath = path + "/" + entry
        if os.path.exists(epath):
            fh = open(epath, "r")
            data = fh.read()
            fh.close()
            del fh
            rdata = data.split("\n")
            try:
                rdata.remove("")
            except:
                pass
            return[True, rdata]
        else:
            return [False, ERR_NO_SUCH_ENTRY]

    def set(self, entry, data, mode):
        entry = entry + ".txt"
        path = self.path
        epath = path + "/" + entry
        if os.path.exists(epath):
            if mode == MODE_APPEND:
                fh = open(epath, "a")
                fh.write(data)
                fh.write("\n")
                fh.flush()
                fh.close()
                del fh
                return [True, RESULT_SUCCESS]
            elif mode == MODE_REMOVE:
                os.remove(epath)
                self.cleandirs(self.path)
                return [True, RESULT_SUCCESS]
            elif mode == MODE_REPLACE:
                fh = open(epath, "w")
                fh.write(data)
                fh.write("\n")
                fh.close()
                del fh
                return [True, RESULT_SUCCESS]
        else:
            if mode == MODE_APPEND:
                makepath = epath.split("/")
                makepath.remove(makepath[-1])
                try:
                    os.makedirs("/".join(makepath))
                except Exception:
                    pass
                fh = open(epath, "a")
                fh.write(data)
                fh.write("\n")
                fh.flush()
                fh.close()
                del fh
                return [True, RESULT_SUCCESS]
            elif mode == MODE_REMOVE:
                return [False, ERR_NO_SUCH_ENTRY]
            elif mode == MODE_REPLACE:
                makepath = epath.split("/")
                makepath.remove(makepath[-1])
                try:
                    os.makedirs("/".join(makepath))
                except Exception:
                    pass
                fh = open(epath, "w")
                fh.write(data)
                fh.write("\n")
                fh.close()
                del fh
                return [True, RESULT_SUCCESS]

    def cleandirs(self, path):
        files = os.listdir(path)
        dirs = []
        for element in files:
            if os.path.isdir(path + "/" + element):
                dirs.append(element)

        for element in dirs:
            if len(os.listdir(path + "/" + element)) is 0:
                os.rmdir(path + "/" + element)
            elif os.path.isdir(path + "/" + element):
                self.cleandirs(path + "/" + element)
                if len(os.listdir(path + "/" + element)) is 0:
                    os.rmdir(path + "/" + element)

    def listentries(self, filehname="topics.txt"):
        buffer = []
        for root, dirs, files in os.walk(self.path):
            for filename in fnmatch.filter(files, "*.txt"):
                if root is self.path:
                    buffer.append("%s" % filename.split(".txt")[0])
                else:
                    data = string.replace(root, "\\", "/")
                    data = "".join(data.split("/")[1:])
                    buffer.append("%s/%s" % (data, filename.split(".txt")[0]))
        buffer.sort(key=str.lower)
        buffer = "\n".join(buffer)
        buffer
        fh = open(filehname, "w")
        fh.write(buffer)
        fh.flush()
        fh.close()