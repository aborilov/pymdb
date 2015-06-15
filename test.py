#!/usr/bin/env python2

import logging
import logging.handlers

from twisted.internet import reactor, defer, task
from twisted.internet.serialport import SerialPort
from twisted.internet.protocol import Factory, Protocol

from serial import PARITY_NONE, PARITY_EVEN, PARITY_ODD
from serial import STOPBITS_ONE, STOPBITS_TWO
from serial import FIVEBITS, SIXBITS, SEVENBITS, EIGHTBITS

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
handler = logging.handlers.RotatingFileHandler(
    'kiosk.log', maxBytes=1028576, backupCount=10)
form = logging.Formatter(
    '%(asctime)s %(name)-12s %(levelname)s:%(message)s')
handler.setFormatter(form)
logger.addHandler(handler)

print('hello work')
logger.debug('Hello')

class MDB(Protocol):

    sent = False

    def __init__(self):
        self.req = None
        self.lock = defer.DeferredLock()

    def connectionMade(self):
        print "Connected"
        print "writing"
        self.transport.write('\x02\x85\x0A')
        # self.transport.write('\x02\x88\x08')
        # self.transport.write('\x02\x88\x30')
        # self.transport.write('\x02\x88\x0A')
        # self.transport.write('\x02\x88\x0B')
        # self.transport.write('\x02\x88\x0C\xFF\xFF\xFF\xFF')

    def dataReceived(self, data):
        # if self.req:
            # str_data = ' '.join(["0x%0.2X"%ord(c) for c in data])
            # self.defer.callback(str_data)
        # print "data received: {}".format(str_data)
        str_data = ' '.join(["0x%0.2X"%ord(c) for c in data])
        print "data received: {}".format(str_data)

        # if not self.sent:
            # print "coin type"
            # self.transport.write('\x06\x88\x0C\xFF\xFF\xFF\xFF')
            # self.transport.write('\x03\x88\x0D\x01')
            # self.sent = True
        # else:
        self.transport.write('\x02\x88\x0B')
        # self.transport.write('\x02\x88\x33')

    def payout(self):
        self.transport.write('\x03\x88\x0D\x12')
        # self.transport.write('\x03\x88\x35\x00')

    def payin(self):
        self.transport.write('\x06\x88\x0C\xFF\xFF\xFF\xFF')
        # self.transport.write('\x06\x88\x34\xFF\xFF\xFF\xFF')

    timeout = 0.3

    def call(self, req):
        return self.lock.run(self._call, req)

    @defer.inlineCallbacks
    def _call(self, req):
        d = defer.Deferred()
        self.defer = d
        if self.req:
            raise ValueError(
                "call %s while %s request in progress" % (req, self.req))
        self.req = req

        timedefer = reactor.callLater(
            self.timeout, lambda d: d.errback(
                ValueError("No answer after %ss" % self.timeout)), d)
        # packet = self.dec.encode(req)
        self.transport.write(req)
        results = yield self.defer
        timedefer.cancel()
        self.req = None
        defer.returnValue(results)

    def charger_init(self):
        return self.call('\x02\x85\x0A')

    @defer.inlineCallbacks
    def charger_poll(self):
        result = yield self.call('\x02\x88\x0B')
        print "Polling: {}".format(result)
        defer.returnValue(result)

    def charger_payin(self):
        return self.call('\x06\x88\x0C\xFF\xFF\xFF\xFF')


    @defer.inlineCallbacks
    def work(self):
        result = yield self.charger_init()
        print "init result: {}".format(result)

        # loop = task.LoopingCall(self.charger_poll)
        # loop.start(0.5)
        while True:
            yield self.charger_poll()


        # result = yield self.charger_poll()
        # print "poll result: {}".format(result)

        result = yield self.charger_payin()
        print "payin result: {}".format(result)




proto = MDB()
SerialPort(
    proto, '/dev/ttyUSB0', reactor,
    baudrate='38400', parity=PARITY_NONE,
    bytesize=EIGHTBITS, stopbits=STOPBITS_ONE)
# reactor.callLater(1, proto.work)
# reactor.callLater(3, proto.payin)
# reactor.callLater(4, proto.payout)
print "run reactor"
reactor.run()


