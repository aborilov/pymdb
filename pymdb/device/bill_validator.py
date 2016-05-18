from twisted.internet import reactor, defer, task

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

_ERROR_NAMES = {
    '\x01': 'Defective Motor3',
    '\x02': 'Sensor Problem3',
    '\x04': 'ROM Checksum Error3',
    '\x05': 'Validator Jammed3'
}

_STATE_NAMES = {
    '\x03': 'validator_busy',
    '\x09': 'validator_disabled'
}

STATES = {
    'validator_busy':      False, #'Validator Busy2',
    'validator_disabled':  False  #'Validator Disabled2',
}

BILL_ROUTING = {
    0: "Bill stacked",
    1: "Escrow position",
    2: "Bill returned",
    3: "Bill to recycler",
    4: "Disabled bill rejected",
    5: "Bill to recycler - manual fill",
    6: "Manual dispense",
    7: "Transferred from recycler to cashbox"
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
    
    _started = False;
    mdb_init_delay = 1
    reset_timeout = 10
    request_status_delay = 0.5

    def __init__(self, proto, bills):
        super(BillValidator, self).__init__(proto)
        self._bills = bills


    def start_device(self):
        if self._started:
            return
        self._started = True
        self._start_init()

    def stop_device(self):
        if not self._started:
            return
        self._started = False
        self.stop_polling()
        
    def _start_init(self):
        reactor.callInThread(self._start_reset_loop)

    @defer.inlineCallbacks
    def _start_reset_loop(self):
        self.stop_polling()
        try_num = 0
        while self._started:
            # mdb initialization
            try:
                result = yield self.proto.mdb_init()
            except Exception as e:
                yield task.deferLater(reactor, self.mdb_init_delay, defer.passthru, None)
                continue
            
            # reset and start polling    
            try:
                result = yield self.reset()
                self.start_polling()
                break
            
            except Exception as e:
                try_num += 1
                if try_num > 1:
                    # sleep for timeout
                    yield task.deferLater(reactor, self.reset_timeout, defer.passthru, None)


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
    def _request_status(self):
        #yield self._define_coin_count()
        #TODO request validator status
        self.initialized()

#     @defer.inlineCallbacks
#     def poll(self):
#         result = yield super(BillValidator, self).poll()
#         if result == ACK:
#             while self.waiters:
#                 waiter = self.waiters.pop()
#                 waiter.callback(None)
#         # just status
#         if len(result) == 1:
#             if result in STATUS:
#                 logger.debug("Status: {}".format(STATUS[result]))

    @defer.inlineCallbacks
    def poll(self):
        result = ''
        try: 
            result = yield super(BillValidator, self).poll()
        except Exception as e:
            return;
        
        if not result:
            return
        
        if result == ACK:
            while self.waiters:
                waiter = self.waiters.pop()
                waiter.callback(None)
        else:
            for r in _STATE_NAMES:
                if r not in result:
                    self._set_state(_STATE_NAMES[r], False)
        
        if result != ACK and len(result) > 0:
            data = result[0]
            if (ord(data) & ord('\x80')) >> 7:
                logger.debug("Bill routing")
                bill_route = (ord(data) & ord('\x70'))
                bill_type = (ord(data) & ord('\x0F'))
                self._bill_routing(bill_route, bill_type)
        self._parse_status(result)
                
    def _bill_routing(self, bill_route, bill_type):
        #TODO parse message
        return
        
    def _parse_status(self, response):
        if not response:
            return

        if response == ACK:
            return
        
        for i in range(len(response)):
            r = response[i]
            if r in STATUS:
                logger.debug("Status: {}".format(STATUS[r]))
                if r in _STATE_NAMES:
                    self._set_state(_STATE_NAMES[r], True)
                if r == '\x06':
                    self.validator_was_reset1(r)
                
                if r in _ERROR_NAMES:
                    self.error(r, _ERROR_NAMES[r])
        

    def _set_state(self, state_name, state_value):
        if state_name in STATES:
            STATES[state_name] = state_value

            
    def _get_state(self, state_name):
        if state_name in STATES:
            return STATES[state_name]
        else:
            return False

    def go_online(self):
        self.online()

    def go_offline(self):
        self.offline()
        self._start_init()

    def online(self):
        pass

    def offline(self):
        pass

    def initialized(self):
        pass

    def error(self, error_code, error_text):
        pass

    def validator_was_reset1(self, status_code):
        reactor.callLater(self.request_status_delay, self._request_status)