from twisted.internet import defer
from mdb_device import MDBDevice
from ..protocol.mdb import log_result, encode

import logging

logger = logging.getLogger()
STATUS = {
    '\x01': 'Escrow request1',
    '\x02': 'Changer Payout Busy2',
    '\x03': 'No Credit1',
    '\x04': 'Defective Tube Sensor1',
    '\x05': 'Double Arrival1',
    '\x06': 'Acceptor Unplugged2',
    '\x07': 'Tube Jam1',
    '\x08': 'ROM checksum error1',
    '\x09': 'Coin Routing Error1',
    '\x0A': 'Changer Busy2',
    '\x0B': 'Changer was Reset1',
    '\x0C': 'Coin Jam1',
    '\x0D': 'Possible Credited Coin Removal1'
}

COINT_ROUTING = {
    0: "Cash box",
    1: "Tubes",
    2: "Not used",
    3: "Reject"
}


class Changer(MDBDevice):

    commands = {
        'reset': '\x08',
        'poll': '\x0B',
        'coin_type': '\x0C',
        'dispense': '\x0D'
    }

    @log_result
    def coin_type(self, coins):
        request = encode(self.commands['coin_type'], coins+"\x00\x00")
        return self.proto.call(request)

    @defer.inlineCallbacks
    def poll(self):
        result = yield super(Changer, self).poll()
        #  if result == mdb.ACK:
        #      defer.returnValue(result)
        # just status
        if len(result) == 1:
            if result in STATUS:
                logger.debug("Status: {}".format(STATUS[result]))
        # payin or payout
        if len(result) == 2:
            coin_in_tube = ord(result[1])
            data = result[0]
            if (ord(data) & ord('\x80')) >> 7:
                logger.debug("Coin dispensed")
            elif (ord(data) & ord('\xC0')) >> 6:
                routing = (ord(data) & ord('\x30')) >> 4
                coin = (ord(data) & ord('\x0F'))
                self.deposited(coin, routing, in_tube=coin_in_tube)

    def dispensed(self, coin, count, in_tube=None):
        pass

    def deposited(self, coin, routing=1, in_tube=None):
        pass

    def escrow_request1(self):
        pass

    def changer_payout_busy2(self):
        pass

    def no_credit1(self):
        pass

    def defective_tube_sensor1(self):
        pass

    def double_arrival1(self):
        pass

    def acceptor_unplugged2(self):
        pass

    def tube_jam1(self):
        pass

    def rom_checksum_error1(self):
        pass

    def coin_routing_error1(self):
        pass

    def changer_busy2(self):
        pass

    def changer_was_reset1(self):
        pass

    def coin_jam1(self):
        pass

    def possible_credited_coin_removal1(self):
        pass
