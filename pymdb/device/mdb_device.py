from twisted.internet import task

from ..protocol.mdb import log_result
from ..protocol.mdb import encode


class MDBDevice(object):

    timeout = 0

    def __init__(self, proto):
        self.proto = proto
        self.polling = task.LoopingCall(self.poll)

    @log_result
    def reset(self):
        request = encode(self.commands['reset'])
        return self.proto.call(request)

    @log_result
    def poll(self):
        request = encode(self.commands['poll'])
        return self.proto.call(request)

    def start_polling(self):
        self.polling.start(self.timeout)

    def stop_polling(self):
        self.polling.stop()
