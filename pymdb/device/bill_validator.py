from mdb_device import MDBDevice
from ..protocol.mdb import encode, log_result


class BillValidator(MDBDevice):

    commands = {
        'reset': '\x30',
        'poll': '\x33',
        'bill_type': '\x34',
        'escrow': '\x35',
        'stacker': '\x36'
    }

    @log_result
    def bill_type(self):
        request = encode(self.commands['bill_type'], '\xFF\xFF\xFF\xFF')
        return self.proto.call(request)

    @log_result
    def escrow(self):
        request = encode(self.commands['escrow'], '\x00')
        return self.proto.call(request)
