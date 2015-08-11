#!/usr/bin/env python2

import logging
import logging.handlers

from twisted.internet import reactor, defer
from twisted.internet.serialport import SerialPort

from serial import PARITY_NONE
from serial import STOPBITS_ONE
from serial import EIGHTBITS

from pymdb.protocol.mdb import MDB
from pymdb.device.changer import Changer

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
        self.changer = Changer(proto)
        #  self.bill = BillValidator(proto)

    @defer.inlineCallbacks
    def loop(self):
        yield self.proto.mdb_init()
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
        #  proto, '/dev/ttyUSB0', reactor,
        proto, '/dev/ttyS0', reactor,
        baudrate='38400', parity=PARITY_NONE,
        bytesize=EIGHTBITS, stopbits=STOPBITS_ONE)
    kiosk = Kiosk(proto)
    reactor.callLater(1, kiosk.loop)
    logger.debug("run reactor")
    reactor.run()
