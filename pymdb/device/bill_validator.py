from twisted.internet import reactor, defer, task

from louie import dispatcher

from mdb_device import MDBDevice
from ..protocol.mdb import log_result, encode, ACK

import logging

logger = logging.getLogger('pymdb')

ESCROW_STATUS_RETURN_BILL = '0x00'
ESCROW_STATUS_STACK_BILL = '0x01'

STATUS_DEFECTIVE_MOTOR = '\x01'
STATUS_SENSOR_PROBLEM = '\x02'
STATUS_VALIDATOR_BUSY = '\x03'
STATUS_ROM_CHECKSUM_ERROR = '\x04'
STATUS_VALIDATOR_JAMMED = '\x05'
STATUS_VALIDATOR_RESET = '\x06'
STATUS_BILL_REMOVED = '\x07'
STATUS_CASH_BOX_OUT_OF_POSITION = '\x08'
STATUS_VALIDATOR_DISABLED = '\x09'
STATUS_INVALID_ESCROW_REQUEST = '\x0A'
STATUS_BILL_REJECTED = '\x0B'
STATUS_POSSIBLE_CREDITED_BILL_REMOVAL = '\x0C'

STATUS = {
    STATUS_DEFECTIVE_MOTOR: 'Defective Motor3',
    STATUS_SENSOR_PROBLEM: 'Sensor Problem3',
    STATUS_VALIDATOR_BUSY: 'Validator Busy2',
    STATUS_ROM_CHECKSUM_ERROR: 'ROM Checksum Error3',
    STATUS_VALIDATOR_JAMMED: 'Validator Jammed3',
    STATUS_VALIDATOR_RESET: 'Validator was reset1',
    STATUS_BILL_REMOVED: 'Bill Removed1',
    STATUS_CASH_BOX_OUT_OF_POSITION: 'Cash Box out of position3',
    STATUS_VALIDATOR_DISABLED: 'Validator Disabled2',
    STATUS_INVALID_ESCROW_REQUEST: 'Invalid Escrow request1',
    STATUS_BILL_REJECTED: 'Bill Rejected1',
    STATUS_POSSIBLE_CREDITED_BILL_REMOVAL: 'Possible Credited Bill Removal1'
}

_ERROR_NAMES = {
    STATUS_DEFECTIVE_MOTOR: STATUS[STATUS_DEFECTIVE_MOTOR],
    STATUS_SENSOR_PROBLEM: STATUS[STATUS_SENSOR_PROBLEM],
    STATUS_ROM_CHECKSUM_ERROR: STATUS[STATUS_ROM_CHECKSUM_ERROR],
    STATUS_VALIDATOR_JAMMED: STATUS[STATUS_VALIDATOR_JAMMED]
}

_STATE_NAMES = {
    STATUS_VALIDATOR_BUSY: 'validator_busy',
    STATUS_VALIDATOR_DISABLED: 'validator_disabled'
}

STATES = {
    _STATE_NAMES[STATUS_VALIDATOR_BUSY]:      False, #'Validator Busy2',
    _STATE_NAMES[STATUS_VALIDATOR_DISABLED]:  False  #'Validator Disabled2',
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
        self._total_amount = 0
        self._bill_count = 0
        
        mask = 0
        for b in bills:
            mask |= 0x01 << b
        self.bill_mask = (hex(mask)[2:].zfill(4) * 2).decode('hex')

    def start_accept(self):
        return self.bill_type(bills=self.bill_mask)

    def stop_accept(self):
        return self.bill_type(bills='\x00\x00\x00\x00')

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
                yield task.deferLater(reactor, 
                                      self.mdb_init_delay, 
                                      defer.passthru, 
                                      None)
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
                    yield task.deferLater(reactor, 
                                          self.reset_timeout, 
                                          defer.passthru, 
                                          None)


    def stack_bill(self):
        self.escrow(status=ESCROW_STATUS_STACK_BILL)

    def return_bill(self):
        self.escrow(status=ESCROW_STATUS_RETURN_BILL)
        
    @log_result
    def bill_type(self, bills):
        request = encode(self.commands['bill_type'], bills)
        return self.call(request)

    @log_result
    def escrow(self, status=ESCROW_STATUS_RETURN_BILL):
        request = encode(self.commands['escrow'], status)
        return self.call(request)

    @log_result
    def stacker(self):
        request = encode(self.commands['stacker'])
        return self.call(request)

    @defer.inlineCallbacks
    def _define_bill_count(self):
        result = yield self.stacker()
        data = (ord(result[0]) << 8) | ord(result[1])
        self._bill_count = data & 0x7fff

    @defer.inlineCallbacks
    def _request_status(self):
        yield self._define_bill_count()
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
        except Exception:
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
            logger.debug('Unsupported bill routing: {} (bill_type={})'.
                         format(bill_route, bill_type))
        
        
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
                if r == STATUS_VALIDATOR_RESET:
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
        logger.debug("validator error({}): {}".
                     format(error_code, error_text))
        dispatcher.send_minimal(
            sender=self, 
            signal='error', error_code=error_code, error_text=error_text)

    def fire_check_bill(self, bill_type):
        amount = self.get_bill_amount(bill_type)
        logger.debug("Check bill ({})".format(amount))
        dispatcher.send_minimal(
            sender=self, signal='check_bill', amount=amount)

    def fire_bill_in(self, bill_type):
        amount = self.get_bill_amount(bill_type)
        logger.debug("Bill accepted ({})".format(amount))
        self._total_amount += amount
        self._bill_count += 1
        dispatcher.send_minimal(
            sender=self, signal='bill_in', amount=amount)

    def fire_bill_returned(self, bill_type):
        amount = self.get_bill_amount(bill_type)
        logger.debug("Bill returned ({})".format(amount))
        dispatcher.send_minimal(
            sender=self, signal='bill_returned', amount=amount)

    def validator_was_reset1(self, status_code):
        reactor.callLater(self.request_status_delay, self._request_status)
        
    #######################
    ## Public Methods
    #######################

    def get_total_amount(self):
        return self._total_amount
    
    def set_total_amount(self, amount=0):
        self._total_amount = amount

    def get_bill_count(self):
        return self._bill_count
