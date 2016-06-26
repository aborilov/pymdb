from twisted.internet import reactor, defer, task

from louie import dispatcher

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

BILL_ROUTE_STACKED = 0
BILL_ROUTE_ESCROW_POS = 1
BILL_ROUTE_RETURNED = 2
BILL_ROUTE_TO_RECYCLER = 3
BILL_ROUTE_REJECTED = 4
BILL_ROUTE_TO_RECYCLER_MANUAL = 5
BILL_ROUTE_DISPENSE_MANUAL = 6
BILL_ROUTE_FROM_RECYCLER_TO_CASHBOX = 7

BILL_ROUTING = {
    BILL_ROUTE_STACKED: "Bill stacked",
    BILL_ROUTE_ESCROW_POS: "Escrow position",
    BILL_ROUTE_RETURNED: "Bill returned",
    BILL_ROUTE_TO_RECYCLER: "Bill to recycler",
    BILL_ROUTE_REJECTED: "Disabled bill rejected",
    BILL_ROUTE_TO_RECYCLER_MANUAL: "Bill to recycler - manual fill",
    BILL_ROUTE_DISPENSE_MANUAL: "Manual dispense",
    BILL_ROUTE_FROM_RECYCLER_TO_CASHBOX: "Transferred from recycler to cashbox"
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

    def get_bill_amount(self, bill):
        if bill not in self._bills:
            return 0
        return self._bills[bill]

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


    def stack_bill(self):
        self.escrow(status='0x01')

    def return_bill(self):
        self.escrow(status='0x00')
        
    @log_result
    def bill_type(self, bills):
        request = encode(self.commands['bill_type'], bills)
        return self.call(request)

    @log_result
    def escrow(self, status='\x00'):
        request = encode(self.commands['escrow'], status)
        return self.call(request)

    @log_result
    def stacker(self):
        request = encode(self.commands['stacker'])
        return self.call(request)

#     @defer.inlineCallbacks
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
        if not bill_type in self._bills:
            # unsupported bill type - return bill
            reactor.callLater(0, self.return_bill)
            return
        if bill_route == BILL_ROUTE_ESCROW_POS:
            self.fire_check_bill(bill_type)
        elif bill_route == BILL_ROUTE_STACKED:
            self.fire_bill_in(bill_type)
        elif bill_route == BILL_ROUTE_RETURNED:
            self.fire_bill_returned(bill_type)
        else:
            logger.debug('Unsupported bill routing: {} (bill_type={})'.format(bill_route, bill_type))
        
        
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
        logger.debug("validator online")
        dispatcher.send_minimal(
            sender=self, signal='online')

    def offline(self):
        logger.debug("validator offline")
        dispatcher.send_minimal(
            sender=self, signal='offline')

    def initialized(self):
        logger.debug("validator initialized")
        dispatcher.send_minimal(
            sender=self, signal='initialized')

    def error(self, error_code, error_text):
        logger.debug("validator error({}): {}".format(ord(error_code), error_text))
        dispatcher.send_minimal(
            sender=self, signal='error', error_code=error_code, error_text=error_text)

    def fire_check_bill(self, bill_type):
        amount = self.get_bill_amount(bill_type)
        logger.debug("Check bill ({})".format(amount))
        dispatcher.send_minimal(
            sender=self, signal='check_bill', amount=amount)

    def fire_bill_in(self, bill_type):
        amount = self.get_bill_amount(bill_type)
        logger.debug("Bill accepted ({})".format(amount))
        dispatcher.send_minimal(
            sender=self, signal='bill_in', amount=amount)

    def fire_bill_returned(self, bill_type):
        amount = self.get_bill_amount(bill_type)
        logger.debug("Bill returned ({})".format(amount))
        dispatcher.send_minimal(
            sender=self, signal='bill_returned', amount=amount)

    def validator_was_reset1(self, status_code):
        reactor.callLater(self.request_status_delay, self._request_status)