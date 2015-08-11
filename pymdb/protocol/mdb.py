import logging

from twisted.internet import defer, reactor
from twisted.protocols.basic import LineReceiver

logger = logging.getLogger()


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
        result = yield f(self, *args, **kwargs)
        str_data = pretty(result)
        logger.debug("{}.{} <- {}".format(clazz, f.func_name, str_data))
        defer.returnValue(result)
    return pretty_log


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

    def call(self, req):
        return self.lock.run(self._call, req)

    def _call(self, req):
        self.data = ''
        d = defer.Deferred()
        if self.req:
            raise ValueError(
                "call %s while %s request in progress" % (
                    pretty(req), pretty(self.req)))
        self.req = req

        def timeout(d):
            if self.data:
                self.req = None
                d.callback(self.data)
                self.data = ''
            else:
                logger.debug("Timeout")
        self.transport.write(req)
        reactor.callLater(self.timeout, timeout, d)
        return d

    @log_result
    def mdb_init(self):
        return self.call('\x02\x85\x0A')
