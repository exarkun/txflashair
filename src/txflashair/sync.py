from __future__ import unicode_literals, print_function

from sys import argv

from twisted.python.url import URL
from twisted.python.usage import Options
from twisted.internet.task import react
from twisted.python.filepath import FilePath

import treq
from treq import collect

from .txflashair import visit, download_file, remove_file


class Options(Options):
    optParameters = [
        ("device-url", None, "http://192.168.0.1/", "The location of the FlashAir device."),
        ("device-root", None, "/", "The root of the directory tree on the device from which to sync."),
        ("local-root", None, None, "The local directory to which to sync."),
    ]

    optFlags = [
        ("remove", None, "Remove files from the device once there is a local copy."),
    ]



def save_to(response, path):
    fobj = path.open("wb")
    d = collect(response, fobj.write)
    d.addBoth(lambda passthrough: (fobj.close(), passthrough)[1])
    return d



def remote_to_local_name(local_root, device_root, file_name):
    return local_root.child(file_name.basename())



def remove_remote(ignored, treq, f):
    return remove_file(treq, f)



def passthrough(value, treq, f):
    return value



@react
def main(reactor):
    o = Options()
    o.parseOptions(argv[1:])

    flashair = URL.fromText(o["device-url"].decode("ascii"))
    device_root = FilePath(o["device-root"].decode("ascii"))
    local_root = FilePath(o["local-root"].decode("ascii"))
    if o["remove"]:
        remove = remove_remote
    else:
        remove = passthrough

    def maybe_sync(f):
        destination = remote_to_local_name(local_root, device_root, f.name)
        if destination.exists() and destination.getsize() == f.size:
            print(destination.path, "already exists.")
        else:
            print(destination.path, "sync'ing.")
            d = download_file(treq, flashair, f.name)
            d.addCallback(save_to, destination)
            d.addCallback(remove, treq, f)
            return d

    return visit(
        treq,
        flashair,
        device_root,
        maybe_sync,
    )
