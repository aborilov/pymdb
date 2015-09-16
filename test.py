#!/usr/bin/env python2

import logging
import logging.handlers

from twisted.internet import reactor, defer, task
from twisted.internet.serialport import SerialPort

from serial import PARITY_NONE
from serial import STOPBITS_ONE
from serial import EIGHTBITS

from pymdb.protocol.mdb import MDB
from pymdb.device.changer import Changer, COINT_ROUTING

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
handler = logging.handlers.RotatingFileHandler(
    'kiosk.log', maxBytes=1028576, backupCount=10)
form = logging.Formatter(
    '%(asctime)s %(name)-12s %(levelname)s:%(message)s')
handler.setFormatter(form)
logger.addHandler(handler)


class Kiosk(object):

    def __init__(self, proto):
        self.proto = proto
        self.changer = RUChanger(proto, self)
        self.waiter = None
        #  self.bill = BillValidator(proto)

    @defer.inlineCallbacks
    def loop(self):
        yield self.proto.mdb_init()
        yield self.changer.reset()
        self.changer.start_polling()

    @defer.inlineCallbacks
    def accept(self, amount):
        yield self.changer.start_accept()
        try:
            summ = 0
            while summ < amount:
                self.waiter = defer.Deferred()
                timedefer = reactor.callLater(10, defer.timeout, self.waiter)
                s = yield self.waiter
                if timedefer.active():
                    timedefer.cancel()
                summ += s
                logger.debug("Have summ: {}".format(summ))
            logger.debug("Final summ: {}".format(summ))
            defer.returnValue(summ)
        except Exception:
            logger.exception("While get amount")
        finally:
            yield self.changer.stop_accept()

    def deposited(self, amount):
        logger.debug("Deposited: {}".format(amount))
        if self.waiter:
            self.waiter.callback(amount)


class RUChanger(Changer):

    COINS = {
        0: 1,
        1: 2,
        2: 5,
        4: 10
    }

    def __init__(self, proto, kiosk):
        super(RUChanger, self).__init__(proto)
        self.kiosk = kiosk

    def start_accept(self):
        return self.coin_type(coins='\xFF\xFF')

    def stop_accept(self):
        return self.coin_type(coins='\x00\x00')

    def deposited(self, coin, routing=1, in_tube=None):
        logger.debug(
            "Coin deposited({}): {}".format(
                COINT_ROUTING[routing], self.COINS[coin]))
        if routing == 1:
            self.kiosk.deposited(self.COINS[coin])


if __name__ == '__main__':
    proto = MDB()
    SerialPort(
        #  proto, '/dev/ttyUSB0', reactor,
        proto, '/dev/ttyUSB0', reactor,
        baudrate='38400', parity=PARITY_NONE,
        bytesize=EIGHTBITS, stopbits=STOPBITS_ONE)
    kiosk = Kiosk(proto)
    reactor.callLater(0, kiosk.loop)
    reactor.callLater(3, kiosk.accept, 15)
    #  reactor.callLater(15, kiosk.stop_changer)
    logger.debug("run reactor")
    reactor.run()
