# https://flashair-developers.com/en/documents/api/

from __future__ import unicode_literals, print_function

import attr
from attr.validators import and_, instance_of

from constantly import FlagConstant, Flags

from twisted.python.url import URL
from twisted.python.filepath import FilePath

from twisted.internet.defer import inlineCallbacks

from twisted.web.http import OK
from twisted.web.client import PartialDownloadError, readBody

class FileAttributes(Flags):
    READONLY = FlagConstant()
    HIDDEN = FlagConstant()
    SYSTEM = FlagConstant()
    VOLUME = FlagConstant()
    DIRECTLY = FlagConstant()
    ARCHIVE = FlagConstant()



@attr.s(frozen=True)
class File(object):
    name = attr.ib(validator=instance_of(FilePath))
    size = attr.ib(validator=instance_of(int))
    attributes = attr.ib(
        validator=lambda self, attr, value: (
            value in FileAttributes.iterconstants()
        ),
    )
    date = attr.ib(validator=instance_of(int))
    time = attr.ib(validator=instance_of(int))



def has_attribute(which):
    def validator(self, attr, file):
        value = file.attributes
        if value & which:
            return
        raise ValueError(
            "{} missing required attribute {}".format(value, which)
        )
    return validator



@attr.s(frozen=True)
class DeleteFile(object):
    file = attr.ib(
        validator=and_(
            instance_of(File),
            has_attribute(FileAttributes.ARCHIVE),
        ),
    )


    def uri(self):
        return URL(
            path=["upload.cgi"],
            query=[
                ("DEL", self.file.name.path),
            ],
        )


    def headers(self):
        return None


    def body(self):
        return None


    def process_response(self, response):
        d = readBody(response)
        def read(body):
            if response.code != OK:
                raise Exception(
                    "Unexpected response code {}:\n{}".format(response.code, body)
            )
            return None
        d.addCallback(read)
        return d



@attr.s(frozen=True)
class GetFileList(object):
    opcode = 100
    minimum_version = "1.00.03"
    directory = attr.ib(validator=instance_of(FilePath))


    def uri(self):
        return URL(
            path=["command.cgi"],
            query=[
                ("op", "{}".format(self.opcode)),
                ("DIR", self.directory.path),
            ],
        )


    def headers(self):
        return None


    def body(self):
        return None


    def process_response(self, response):
        d = readBody(response)
        def read(body):
            if response.code != OK:
                raise Exception(
                    "Unexpected response code {}:\n{}".format(response.code, body)
                )
            lines = body.decode("utf-8").split("\r\n")
            if lines[0] == "WLANSD_FILELIST": # XXX???
                lines = lines[1:-1]
            else:
                raise Exception("Whuat? {}".format(lines))
            for line in lines:
                parts = line.split(",")
                if len(parts) != 6:
                    raise Exception("Uauaua {}".format(parts))
                yield File(
                    name=FilePath(parts[0] or "/").child(parts[1]),
                    size=int(parts[2]),
                    attributes=lookupByValue(FileAttributes, int(parts[3])),
                    date=int(parts[4]),
                    time=int(parts[5]),
                )
        d.addErrback(lambda reason: reason.check(PartialDownloadError) and reason.value.args[2])
        d.addCallback(read)
        return d



def lookupByValue(constants, flags):
    result = None
    for flag in constants.iterconstants():
        if flag.value & flags:
            if result is None:
                result = flag
            else:
                result |= flag
    if result is None:
        raise ValueError("File attribute unknown: {}".format(flags))
    return result



def get_file_list(treq, root, path):
    return execute(treq, root, GetFileList(directory=path))



def download_file(treq, root, path):
    uri = root.replace(path=path.segmentsFrom(FilePath(b"/")))
    url = uri.asURI().asText().encode("ascii")
    return treq.get(url)



def remove_file(treq, root, file):
    return execute(treq, root, DeleteFile(file=file))



def execute(treq, root, operation):
    uri = operation.uri().replace(
        scheme=root.scheme,
        host=root.host,
        port=root.port,
    )
    headers = operation.headers()

    url = uri.asURI().asText().encode("ascii")
    print("Getting", url)
    d = treq.get(
        url,
        headers,
    )
    d.addCallback(operation.process_response)
    return d



@inlineCallbacks
def visit(treq, root_uri, root_directory, visitor):
    work = [root_directory]

    while work:
        path = work.pop()
        files = yield get_file_list(treq,  root_uri, path)
        for f in files:
            if f.attributes & FileAttributes.DIRECTLY:
                work.append(f.name)
            else:
                yield visitor(f)
