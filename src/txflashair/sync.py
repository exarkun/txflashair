from __future__ import unicode_literals, print_function

from sys import argv
from fnmatch import fnmatchcase
from functools import partial

import attr
from attr.validators import instance_of

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
        ("include", None, "*", "Sync only files whose base name matches given glob."),
        ("download-timeout", None, 180, "Number of seconds to wait for a single file to download before giving up on it (on a particular iteration).", float),
    ]

    optFlags = [
        ("remove", None, "Remove files from the device once there is a local copy."),
    ]



def passthrough_callback(f):
    def cb(passthrough):
        f()
        return passthrough
    return cb



def save_to(response, path):
    fobj = path.open("wb")
    d = collect(response, fobj.write)
    d.addBoth(lambda passthrough: (fobj.close(), passthrough)[1])
    return d



def remote_to_local_name(local_root, device_root, file_name):
    return local_root.child(file_name.basename())



def remove_remote(ignored, treq, root, f):
    return remove_file(treq, root, f)



def passthrough(value, treq, root, f):
    return value



@attr.s(frozen=True)
class IncludeGlob(object):
    glob = attr.ib(validator=instance_of(unicode))

    def matches(self, name):
        return fnmatchcase(name, self.glob)



def sync_options(o):
    flashair = URL.fromText(o["device-url"].decode("ascii"))
    device_root = FilePath(o["device-root"].decode("ascii"))
    local_root = FilePath(o["local-root"].decode("ascii"))
    include = IncludeGlob(o["include"].decode("ascii"))
    download_timeout = o["download-timeout"]

    if o["remove"]:
        maybe_remove = remove_remote
    else:
        maybe_remove = passthrough

    return dict(
        flashair=flashair,
        device_root=device_root,
        local_root=local_root,
        include=include,
        maybe_remove=maybe_remove,
        download_timeout=download_timeout,
    )



def sync(reactor, flashair, device_root, local_root, include, maybe_remove, download_timeout):
    def maybe_sync(f):
        destination = remote_to_local_name(local_root, device_root, f.name)
        if not include.matches(f.name.basename()):
            print(f.name.basename(), "does not match include filter.")
        elif destination.exists() and destination.getsize() == f.size:
            print(destination.path, "already exists.")
            return maybe_remove(None, treq, flashair, f)
        else:
            print(destination.path, "sync'ing.")
            partial_destination = destination.siblingExtension(u".partial")
            d = download_file(treq, flashair, f.name)
            d.addCallback(save_to, partial_destination)
            d.addCallback(passthrough_callback(
                partial(partial_destination.moveTo, destination)
            ))
            d.addCallback(maybe_remove, treq, flashair, f)
            d.addTimeout(download_timeout, reactor)
            return d

    return visit(
        treq,
        flashair,
        device_root,
        maybe_sync,
    )



def _sync(reactor):
    o = Options()
    o.parseOptions(argv[1:])

    return sync(reactor, **sync_options(o))


def main():
    return react(_sync, [])
