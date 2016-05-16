from twisted.internet import defer
from mdb_device import MDBDevice
from ..protocol.mdb import log_result, encode, ACK

import logging

logger = logging.getLogger('pymdb')

STATUS = {
    '\x01': 'Defective Motor3',
    '\x02': 'Sensor Problem3',
    '\x03': 'Validator Busy2',
    '\x04': 'ROM Checksum Error3',
    '\x05': 'Validator Jammed3',
    '\x06': 'Validator was reset1',
    '\x07': 'Bill Removed1',
    '\x08': 'Cash Box out of position3',
    '\x09': 'Validator Disabled2',
    '\x0A': 'Invalid Escrow request1',
    '\x0B': 'Bill Rejected1',
    '\x0C': 'Possible Credited Bill Removal1'
}

class BillValidator(MDBDevice):

    waiters = []

    commands = {
        'reset': '\x30',
        'poll': '\x33',
        'bill_type': '\x34',
        'escrow': '\x35',
        'stacker': '\x36'
    }

    @log_result
    def bill_type(self, bills):
        request = encode(self.commands['bill_type'], bills)
        return self.proto.call(request)

    @log_result
    def escrow(self):
        request = encode(self.commands['escrow'], '\x00')
        return self.proto.call(request)

    @log_result
    def stacker(self):
        request = encode(self.commands['stacker'])
        return self.proto.call(request)

    @defer.inlineCallbacks
    def poll(self):
        result = yield super(BillValidator, self).poll()
        if result == ACK:
            while self.waiters:
                waiter = self.waiters.pop()
                waiter.callback(None)
        # just status
        if len(result) == 1:
            if result in STATUS:
                logger.debug("Status: {}".format(STATUS[result]))
