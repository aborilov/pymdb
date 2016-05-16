import logging

from twisted.internet import defer, task

from ..protocol.mdb import log_result
from ..protocol.mdb import encode

logger = logging.getLogger('pymdb')

class MDBDevice(object):

    timeout = 0
    try_count = 3
    _online = False

    def __init__(self, proto):
        self.proto = proto
        self.polling = task.LoopingCall(self.poll)

    def _set_online(self, online):
        if online == self._online:
            return;
        self._online = online
        if online:
            self.go_online()
        else:
            self.go_offline()
        
    def go_online(self):
        pass

    def go_offline(self):
        pass
        
    @log_result
    def reset(self):
        request = encode(self.commands['reset'])
        return self.call(request, 1)

    @log_result
    def poll(self):
        request = encode(self.commands['poll'])
#         return self.proto.call(request)
        return self.call(request)

    def start_polling(self):
        self.polling.start(self.timeout)

    def stop_polling(self):
        try:
            self.polling.stop()
        except Exception as e:
            return
    
    @defer.inlineCallbacks
    def call(self, request, try_count=-1):
        if try_count == -1:
            try_count = self.try_count
            
        for i in range(try_count):
            try:
                result = yield self.proto.call(request)
                self._set_online(True)
                defer.returnValue(result)
            except Exception as e:
                logger.debug("call exception. i={}".format(str(i)))
                if i == try_count - 1:
                    self._set_online(False)
                    raise e

        
