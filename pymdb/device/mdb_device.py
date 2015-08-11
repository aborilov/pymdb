import logging

from ..protocol.mdb import log_result
from ..protocol.mdb import encode

logger = logging.getLogger()


class MDBDevice(object):

    def __init__(self, proto):
        self.proto = proto

    @log_result
    def reset(self):
        request = encode(self.commands['reset'])
        return self.proto.call(request)

    @log_result
    def poll(self):
        request = encode(self.commands['poll'])
        return self.proto.call(request)
