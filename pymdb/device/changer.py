from mdb_device import MDBDevice
from ..protocol.mdb import log_result, encode


class Changer(MDBDevice):

    commands = {
        'reset': '\x08',
        'poll': '\x0B',
        'coin_type': '\x0C',
        'dispense': '\x0D'
    }

    @log_result
    def coin_type(self):
        request = encode(self.commands['coin_type'], "\xFF\xFF\xFF\xFF")
        return self.proto.call(request)
