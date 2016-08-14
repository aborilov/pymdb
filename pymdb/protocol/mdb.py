import logging

from twisted.internet import defer, reactor, task
from twisted.protocols.basic import LineReceiver

from exceptions import TimeoutException

logger = logging.getLogger('pymdb')


def pretty(data):
    return ' '.join(["0x%0.2X" % ord(c) for c in data])


def encode(command, data=''):
    return chr(len(data)+2) + '\x88' + command + data


def log_result(f):

    @defer.inlineCallbacks
    def pretty_log(self, *args, **kwargs):
        clazz = ''
        if self.__class__:
            clazz = self.__class__.__name__
        logger.debug("{}.{} ->".format(clazz, f.func_name))
        try:
            result = yield f(self, *args, **kwargs)
            str_data = pretty(result)
            logger.debug("{}.{} <- {}".format(clazz, f.func_name, str_data))
            defer.returnValue(result)
        except Exception as e:
            logger.error("pretty_log error: " + str(e))
            raise e
    return pretty_log

ACK = '\x01\x00'
MODEBIT = '/x01'

class MDB(LineReceiver):

    timeout = 0.3


    def __init__(self):
        self.req = None
        self.setRawMode()
        self.lock = defer.DeferredLock()
        self.data = ''

    def connectionMade(self):
        logger.debug("Connected")

    def rawDataReceived(self, data):
        self.data = self.data + data

    @log_result
    def call(self, req):
        return self.lock.run(self._call, req)

    @defer.inlineCallbacks
    def _call(self, req):
        self.data = ''
        if self.req:
            raise ValueError(
                "call %s while %s request in progress" % (
                    pretty(req), pretty(self.req)))
        self.req = req
        try:
            self.transport.write(req)
        except Exception as e:
            logger.exception("Error while write to transport")
            self.req = None
            raise e
        # sleep for timeout
        yield task.deferLater(reactor, self.timeout, defer.passthru, None)
        self.req = None
#         try:
        if self.data:
            # return as is for ACK, NAK and RET
            if len(self.data) == 2:
                defer.returnValue(self.data)
            # check if send command with mode bit
            # and remove all garbage if needed
            command = req[1]
            if command == '\x88':
                data = self.data[1::2]
                modebits = self.data[::2]
                if modebits[-1] == MODEBIT:
                    raise ValueError('No modebit at the end')
                data = self.checksum(data)
                defer.returnValue(data)

        else:
            raise TimeoutException("Timeout")
#         except Exception as e:
#             raise e
        defer.returnValue(self.data)

    def checksum(self, data):
        chk = data[-1]
        data = data[:-1]
        if sum(map(ord, data)) == ord(chk):
            return data
        raise ValueError('Wrong checksum, data:{}, chk:{}'.format(data, chk))

    @log_result
    def mdb_init(self):
        return self.call('\x02\x85\x0A')
