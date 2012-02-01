import os
import urllib2
from time import sleep

from zipfile import ZipFile
import tarfile

downloaded = {}
extracted = {}

downloads = { "yaml": [ "http://pyyaml.org/download/pyyaml/PyYAML-3.10.zip", "356KB"],
              "dnspython": ["http://www.dnspython.org/kits/1.9.4/dnspython-1.9.4.zip", "206KB"],
              "colorama": ["http://pypi.python.org/packages/source/c/colorama/colorama-0.2.4.zip", "21KB"],
              "mechanize": ["http://pypi.python.org/packages/source/m/mechanize/mechanize-0.2.5.zip", "435KB"],
              "twilio": ["https://github.com/twilio/twilio-python/zipball/master", "152KB"],
              "zope.Interface": ["http://pypi.python.org/packages/source/z/zope.interface/zope.interface-3.8.0.tar.gz", "109KB"],
              "twisted": ["http://twistedmatrix.com/Releases/Twisted/11.1/Twisted-11.1.0.tar.bz2", "2.7MB"]
}

print "Welcome to the install script for the dependencies required to run the bot."
print "Please note, this script will download some zipfiles, extract them to a temporary folder and install the contents."
print "The install scripts within may, in fact, download additional data. Please be aware of this before continuing."

print ""
print "------------------------------------------------------------------------------------------------------------------"
print ""

print "This installer REQUIRES that your python executable is in your PATH."
print "If it is not, the script WILL fail."
print ""

print "The following packages will be installed:"
print ""

for element in downloads.keys():
    print "%s (%s)" % (element, downloads[element][1])

print "\n"
data = raw_input("Continue? [Y/n] : ")

if data.lower() == "n" or data.lower() == "no":
    quit()

if not os.path.exists("temp"):
    os.mkdir("temp")

def download_file(url, size):
    filename = url.split("/")[-1]

    print "Downloading %s (%s)" % (filename, size)
    print ""

    urlfile = urllib2.urlopen(url)

    done = ""
    chunk = 4096
    while 1:
        data = urlfile.read(chunk)
        if not data:
            break
        done += data
        print "%s: Read %s bytes" % (filename, len(done))

    print "\n"
    print "Downloaded %s successfully." % filename

    fh = open("temp/%s" % filename, "wb")
    fh.write(done)
    fh.flush()
    fh.close()

    return filename

def extract_file(filename):
    print "Extracting %s..." % filename

    rpath = "./temp/" + filename
    path = "./temp/"

    if (filename.split(".")[-1] == "gz") or (filename.split(".")[-1] == "bz2"):
        fh = tarfile.open(rpath)
        fh.extractall(path)

    else:
        fh = ZipFile(rpath, "r")
        fh.extractall(path)

    print "Extracted %s successfully." % filename
    print ""

def install_modules():
    base_dir = "./temp/"
    for element in os.listdir(base_dir):
        if os.path.isdir(base_dir + element):
            print "Installing " + element + "..."
            sleep(3)
            os.system("cd temp/%s && python setup.py install" % element)
            print ""

for element in downloads.keys():
    downloaded[element] = download_file(downloads[element][0], downloads[element][1])
    print ""

for element in downloads.keys():
    extracted[element] = extract_file(downloaded[element])

print ""
print "I am about to install the modules."
print "You will see a LOT of text scroll by."
print ""
print "Sometimes the Twisted install will fail; if it does, simply copy the contents of the build/lib folder"
print "into your site-packages folder."
print ""

raw_input("Press enter to continue.")

install_modules()

print ""
print "Cleaning up..."
print ""

def rm_rf(d):
    for path in (os.path.join(d,f) for f in os.listdir(d)):
        if os.path.isdir(path):
            rm_rf(path)
        else:
            os.unlink(path)
    try:
        os.rmdir(d)
    except WindowsError:
        try:
            rm_rf_b(d)
        except:
            print "Unable to remove folder %s! Please delete the remainder of the temp folder yourself." % d

def rm_rf_b(d):
    for path in (os.path.join(d,f) for f in os.listdir(d)):
        if os.path.isdir(path):
            rm_rf_b(path)
        else:
            os.unlink(path)

rm_rf("temp")

print ""
print "By now, hopefully everything you need to run the bot is installed."
print "If so, you should configure it, and then it should work!"
print ""
print "If not, you may try installing the modules yourself."
print ""

raw_input("Press any key to exit.")