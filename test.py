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


def pretty(data):
    return ' '.join(["0x%0.2X"%ord(c) for c in data])

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


class Changer(object):

    def __init__(self, proto):
        self.proto = proto

    commands = {
        'reset': '\x08',
        'poll': '\x0B',
        'coin_type': '\x0C',
        'dispense': '\x0D'
    }

    @log_result
    def reset(self):
        request = encode(self.commands['reset'])
        return self.proto.call(request)

    @log_result
    def poll(self):
        request = encode(self.commands['poll'])
        return self.proto.call(request)

    @log_result
    def coin_type(self):
        request = encode(self.commands['coin_type'], "\xFF\xFF\xFF\xFF")
        return self.proto.call(request)


class BillValidator(object):

    def __init__(self, proto):
        self.proto = proto

    commands = {
        'reset': '\x30',
        'poll': '\x33',
        'bill_type': '\x34',
        'escrow': '\x35',
        'stacker': '\x36'
    }

    @log_result
    def reset(self):
        request = encode(self.commands['reset'])
        return self.proto.call(request)

    @log_result
    def poll(self):
        request = encode(self.commands['poll'])
        return self.proto.call(request)

    @log_result
    def bill_type(self):
        request = encode(self.commands['bill_type'], '\xFF\xFF\xFF\xFF')
        return self.proto.call(request)

    @log_result
    def escrow(self):
        request = encode(self.commands['escrow'], '\x00')
        return self.proto.call(request)



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
    def changer_init(self):
        return self.call('\x02\x85\x0A')

    @defer.inlineCallbacks
    def work(self):
        yield self.charger_init()
        yield self.mdb_reset()
        while True:
            try:
                yield self.charger_poll()
            except Exception:
                logger.exception('Error while polling')


class Kiosk(object):

    def __init__(self, proto):
        self.proto = proto
        self.changer = Changer(proto)
        self.bill = BillValidator(proto)

    @defer.inlineCallbacks
    def loop(self):
        yield self.proto.changer_init()
        yield self.changer.reset()
        # yield self.bill.reset()
        # yield self.bill.bill_type()
        # yield self.bill.escrow()
        while True:
            try:
                yield self.changer.poll()
                # yield self.bill.poll()
            except Exception:
                logger.exception('Error while polling')

if __name__ == '__main__':
    proto = MDB()
    SerialPort(
        proto, '/dev/ttyUSB0', reactor,
        baudrate='38400', parity=PARITY_NONE,
        bytesize=EIGHTBITS, stopbits=STOPBITS_ONE)
    kiosk = Kiosk(proto)
    reactor.callLater(1, kiosk.loop)
    logger.debug("run reactor")
    reactor.run()
