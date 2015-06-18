#!/usr/bin/env python2

import logging
import logging.handlers

from twisted.internet import reactor, defer, task
from twisted.internet.serialport import SerialPort
from twisted.internet.protocol import Factory, Protocol
from twisted.protocols.basic import LineReceiver

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

class MDB(LineReceiver):

    sent = False

    def __init__(self):
        self.req = None
        self.setRawMode()
        self.lock = defer.DeferredLock()
        self.data = ''

    def connectionMade(self):
        print "Connected"
        print "writing"
        self.transport.write('\x02\x85\x0A')
        # self.transport.write('\x02\x88\x08')
        # self.transport.write('\x02\x88\x30')
        # self.transport.write('\x02\x88\x0A')
        # self.transport.write('\x02\x88\x0B')
        # self.transport.write('\x02\x88\x0C\xFF\xFF\xFF\xFF')

    def rawDataReceived(self, data):
        str_data = ' '.join(["0x%0.2X"%ord(c) for c in data])
        # print "data received: {}".format(str_data)
        if self.req:
            self.data = self.data + data
            if self.req[1]=='\x88' and len(self.data)<2:
                # print 'data too small: {}'.format(data)
                return
            str_data = ' '.join(["0x%0.2X"%ord(c) for c in self.data])
            self.defer.callback(str_data)
        # str_data = ' '.join(["0x%0.2X"%ord(c) for c in data])
        # print "data received: {}".format(str_data)

        # if not self.sent:
            # print "coin type"
            # self.transport.write('\x06\x88\x0C\xFF\xFF\xFF\xFF')
            # self.transport.write('\x03\x88\x0D\x01')
            # self.sent = True
        # else:
        # self.transport.write('\x02\x88\x0B')
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
        try:
            results = yield self.defer
        except Exception as e:
            print e

        timedefer.cancel()
        self.req = None
        self.data = ''
        defer.returnValue(results)

    def charger_init(self):
        print 'send init'
        return self.call('\x02\x85\x0A')

    def mdb_reset(self):
        print 'send reset'
        return self.call('\x02\x88\x08')

    @defer.inlineCallbacks
    def charger_poll(self):
        # print "start poll"
        result = yield self.call('\x02\x88\x0B')
        print "Polling: {}".format(result)
        # print "end poll"
        defer.returnValue(result)

    def charger_payin(self):
        return self.call('\x06\x88\x0C\xFF\xFF\xFF\xFF')


    @defer.inlineCallbacks
    def work(self):
        result = yield self.charger_init()
        print "init result: {}".format(result)
        # result = yield self.mdb_reset()
        # print "reset result: {}".format(result)

        # loop = task.LoopingCall(self.charger_poll)
        # loop.start(1.5)
        while True:
            yield self.charger_poll()


        # result = yield self.charger_poll()
        # print "poll result: {}".format(result)

        # result = yield self.charger_payin()
        # print "payin result: {}".format(result)




proto = MDB()
SerialPort(
    proto, '/dev/ttyUSB0', reactor,
    baudrate='38400', parity=PARITY_NONE,
    bytesize=EIGHTBITS, stopbits=STOPBITS_ONE)
reactor.callLater(1, proto.work)
reactor.callLater(3, proto.charger_payin)
# reactor.callLater(4, proto.payout)
print "run reactor"
reactor.run()


