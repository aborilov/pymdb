from twisted.internet import reactor, defer, task

from louie import dispatcher

from mdb_device import MDBDevice
from ..protocol.mdb import log_result, encode, ACK

import logging

logger = logging.getLogger('pymdb')

STATUS_ESCROW_REQUEST = '\x01'
STATUS_CHANGER_PAYOUT_BUSY = '\x02'
STATUS_NO_CREDIT = '\x03'
STATUS_DEFECTIVE_TUBE_SENSOR = '\x04'
STATUS_DOUBLE_ARRIVAL = '\x05'
STATUS_ACCEPTOR_UNPLUGGED = '\x06'
STATUS_TUBE_JAM = '\x07'
STATUS_ROM_CHECKSUM_ERROR = '\x08'
STATUS_COIN_ROUTING_ERROR = '\x09'
STATUS_CHANGER_BUSY = '\x0A'
STATUS_CHANGER_RESET = '\x0B'
STATUS_COIN_JAM = '\x0C'
STATUS_POSSIBLE_CREDITED_COIN_REMOVAL = '\x0D'

ERROR_CODE_DEFECTIVE_TUBE_SENSOR = STATUS_DEFECTIVE_TUBE_SENSOR
ERROR_CODE_TUBE_JAM = STATUS_TUBE_JAM
ERROR_CODE_ROM_CHECKSUM_ERROR = STATUS_ROM_CHECKSUM_ERROR
ERROR_CODE_COIN_JAM = STATUS_COIN_JAM

STATUS = {
    STATUS_ESCROW_REQUEST: 'Escrow request1',
    STATUS_CHANGER_PAYOUT_BUSY: 'Changer Payout Busy2',
    STATUS_NO_CREDIT: 'No Credit1',
    STATUS_DEFECTIVE_TUBE_SENSOR: 'Defective Tube Sensor1',
    STATUS_DOUBLE_ARRIVAL: 'Double Arrival1',
    STATUS_ACCEPTOR_UNPLUGGED: 'Acceptor Unplugged2',
    STATUS_TUBE_JAM: 'Tube Jam1',
    STATUS_ROM_CHECKSUM_ERROR: 'ROM checksum error1',
    STATUS_COIN_ROUTING_ERROR: 'Coin Routing Error1',
    STATUS_CHANGER_BUSY: 'Changer Busy2',
    STATUS_CHANGER_RESET: 'Changer was Reset1',
    STATUS_COIN_JAM: 'Coin Jam1',
    STATUS_POSSIBLE_CREDITED_COIN_REMOVAL: 'Possible Credited Coin Removal1'
}


ERROR_NAMES = {
    ERROR_CODE_DEFECTIVE_TUBE_SENSOR: STATUS[ERROR_CODE_DEFECTIVE_TUBE_SENSOR],
    ERROR_CODE_TUBE_JAM: STATUS[ERROR_CODE_TUBE_JAM],
    ERROR_CODE_ROM_CHECKSUM_ERROR: STATUS[ERROR_CODE_ROM_CHECKSUM_ERROR],
    ERROR_CODE_COIN_JAM: STATUS[ERROR_CODE_COIN_JAM]
}

_STATE_NAMES = {
    STATUS_CHANGER_PAYOUT_BUSY: 'payout_busy',
    STATUS_ACCEPTOR_UNPLUGGED: 'acceptor_unplugged',
    STATUS_CHANGER_BUSY: 'changer_busy'
}

STATES = {
    _STATE_NAMES[STATUS_CHANGER_PAYOUT_BUSY]: False, #'Changer Payout Busy2',
    _STATE_NAMES[STATUS_ACCEPTOR_UNPLUGGED]:  False, #'Acceptor Unplugged2',
    _STATE_NAMES[STATUS_CHANGER_BUSY]:        False  #'Changer Busy2'
}

COINT_ROUTING = {
    0: "Cash box",
    1: "Tubes",
    2: "Not used",
    3: "Reject"
}

COIN_TYPE_COUNT = 0x10
DISPENSED_COIN_MAX_COUNT = 0x0f

class Changer(MDBDevice):
    
    _started = False;
    mdb_init_delay = 1
    reset_timeout = 10
    request_status_delay = 0.5
    
    waiters = []

    commands = {
        'reset': '\x08',
        'tube_status': '\x0A',
        'poll': '\x0B',
        'coin_type': '\x0C',
        'dispense': '\x0D'
    }

    def __init__(self, proto, coins):
        super(Changer, self).__init__(proto)
        self._coin_count = [0] * COIN_TYPE_COUNT
        self._coins = coins
        mask = 0
        for c in coins:
            mask |= 0x01 << c
        self.coin_mask = hex(mask)[2:].zfill(4).decode('hex')

    def get_coin_count(self, coin):
        return self._coin_count[coin]

    def get_coin_amount(self, coin):
        if coin not in self._coins:
            return 0
        return self._coins[coin]

    def start_accept(self):
        return self.coin_type(coins=self.coin_mask)

    def stop_accept(self):
        return self.coin_type(coins='\x00\x00')

    def coin_count_in_amount(self, coin_type, amount):
        if amount <= 0:
            return 0
        coin_amount = self.get_coin_amount(coin_type)
        if coin_amount == 0:
            return 0
        return amount // coin_amount

#     def dispense_amount(self, amount):
#         if amount <= 0:
#             return
#         balance = amount
#         logger.debug("dispense_amount: start_balance={}".format(balance))
#         for coin_type in range(COIN_TYPE_COUNT - 1,-1,-1):
#             coin_amount = self.get_coin_amount(coin_type)
#             if (coin_amount <= 0):
#                 continue
#             coin_count = self.coin_count_in_amount(coin_type, balance)
#             actual_coin_count = self.get_coin_count(coin_type)
#             if coin_count > actual_coin_count:
#                 coin_count = actual_coin_count
#             logger.debug("dispense_amount: {} coins({}) in amount {}"
#                          .format(coin_count, coin_amount, balance))
#             if coin_count > 0:
#                 try:
#                     balance -= coin_amount * coin_count
#                     self._dispense_amount_impl(coin_type, coin_count)
#                 except Exception as e:
#                     logger.exception("While dispense amount")
#         logger.debug("dispense_amount: end_balance={}".format(balance))
    def dispense_amount(self, amount):
        if amount <= 0:
            return
        exchange = self.get_amount_exchange(amount)
        for coin_type in exchange:
            try:
                self._dispense_amount_impl(coin_type, exchange[coin_type])
            except Exception as e:
                logger.exception("While dispense amount")
        self.amount_dispensed(amount)

    def _dispense_amount_impl(self, coin, count):
        logger.debug("_dispense_amount_impl: need dispense {} coins({})"
                     .format(count, coin))
        dispense_count = count
        while dispense_count > 0:
            coin_count = dispense_count \
            if dispense_count <= DISPENSED_COIN_MAX_COUNT \
            else DISPENSED_COIN_MAX_COUNT
            logger.debug("_dispense_amount_impl: need dispense {} coins({})"
                         .format(coin_count, coin))
            # TODO wait change dispense end
            self.dispense(coin=coin, count=coin_count)
            dispense_count -= coin_count
        
    def can_dispense_amount(self, amount):
        if not self._online:
            return False
        exchange = self.get_amount_exchange(amount)
        exchanged_amount = 0
        for coin_type in exchange:
            coin_amount = self.get_coin_amount(coin_type)
            exchanged_amount += coin_amount * exchange[coin_type]
        
        return exchanged_amount == amount

    def get_amount_exchange(self, amount):
        if (amount <= 0):
            return {}
        rv = {}
        balance = amount
        logger.debug("get_amount_exchange: start_balance={}".format(balance))
        for coin_type in range(COIN_TYPE_COUNT - 1,-1,-1):
            coin_amount = self.get_coin_amount(coin_type)
            if (coin_amount <= 0):
                continue
            coin_count = self.coin_count_in_amount(coin_type, balance)
            actual_coin_count = self.get_coin_count(coin_type)
            if coin_count > actual_coin_count:
                coin_count = actual_coin_count
            logger.debug("get_amount_exchange: {} coins({}) in amount {}"
                         .format(coin_count, coin_amount, balance))
            if coin_count > 0:
                balance -= coin_amount * coin_count
                rv[coin_type] = coin_count
        logger.debug("get_amount_exchange: end_balance={}".format(balance))
        return rv

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
    
    @log_result
    def coin_type(self, coins):
        request = encode(self.commands['coin_type'], coins+"\x00\x00")
        return self.call(request)

    @log_result
    def tube_status(self):
        request = encode(self.commands['tube_status'])
        return self.call(request)

    @defer.inlineCallbacks
    def _define_coin_count(self):
        result = yield self.tube_status()
        for i in range(2, len(result)):
            self._coin_count[i - 2] = ord(result[i])
        #logger.debug("_coin_count:  0x%0.2X" % self._coin_count[2])

    @defer.inlineCallbacks
    def _request_status(self):
        yield self._define_coin_count()
        self.initialized()
 
    @defer.inlineCallbacks
    def poll(self):
        result = ''
        try: 
            result = yield super(Changer, self).poll()
        except Exception:
            return
        
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
        
        status_offset = 0        
        # payin or payout+
        if len(result) >= 2:
            coin_in_tube = ord(result[1])
            data = result[0]
            if (ord(data) & ord('\x80')) >> 7:
                logger.debug("Coin dispensed")
                coin_count = (ord(data) & ord('\x70'))
                coin = (ord(data) & ord('\x0F'))
                # TODO for testing -->
#                 self._coin_count[coin] = coin_in_tube
#                 self.dispensed(coin, coin_count, in_tube=coin_in_tube)
                # TODO for testing <--
                status_offset = 2
            elif (ord(data) & ord('\xC0')) >> 6:
                routing = (ord(data) & ord('\x30')) >> 4
                coin = (ord(data) & ord('\x0F'))
                self._coin_count[coin] = coin_in_tube
                self.deposited(coin, routing, in_tube=coin_in_tube)
                status_offset = 2

        self._parse_status(result, status_offset)
        # just status
#         if len(result) == 1:
#             if result in STATUS:
#                 logger.debug("Status: {}".format(STATUS[result]))

                
    def _parse_status(self, response, status_offset):
        if not response:
            return

        if response == ACK:
            return
        
        for i in range(status_offset, len(response)):
            r = response[i]
            if r in STATUS:
                logger.debug("Status: {}".format(STATUS[r]))
                if r in _STATE_NAMES:
                    self._set_state(_STATE_NAMES[r], True)
                    
#                 if r == '\x01':
#                     self.escrow_request1(r)
#                 elif r == '\x02':
#                     self.changer_payout_busy2(r)
#                 elif r == '\x03':
#                     self.no_credit1(r)
#                 elif r == '\x04':
#                     self.defective_tube_sensor1(r)
#                 elif r == '\x05':
#                     self.double_arrival1(r)
#                 elif r == '\x06':
#                     self.acceptor_unplugged2(r)
#                 elif r == '\x07':
#                     self.tube_jam1(r)
#                 elif r == '\x08':
#                     self.rom_checksum_error1(r)
#                 elif r == '\x09':
#                     self.coin_routing_error1(r)
#                 elif r == '\x0A':
#                     self.changer_busy2(r)
#                 elif r == '\x0B':
                if r == STATUS_CHANGER_RESET:
                    self.changer_was_reset1(r)
#                 elif r == '\x0C':
#                     self.coin_jam1(r)
#                 elif r == '\x0D':
#                     self.possible_credited_coin_removal1(r)
                
                if r in ERROR_NAMES:
                    self.error(r, ERROR_NAMES[r])
        

    def _set_state(self, state_name, state_value):
        if state_name in STATES:
            STATES[state_name] = state_value

            
    def _get_state(self, state_name):
        if state_name in STATES:
            return STATES[state_name]
        else:
            return False

    @defer.inlineCallbacks
    def dispense(self, coin, count):
        data = chr((count << 4) + coin)
        logger.debug("try to dispense with data 0x%0.2X" % ord(data))
        request = encode(self.commands['dispense'], data)
        yield self.call(request)
        waiter = defer.Deferred()
        self.waiters.append(waiter)
        yield waiter
        #             TODO for testing -->
        self._coin_count[coin] -= count
        #             TODO for testing <--


    def go_online(self):
        self.online()

    def go_offline(self):
        self.offline()
        self._start_init()

    def online(self):
        logger.debug("changer online")
        dispatcher.send_minimal(
            sender=self, signal='online')

    def offline(self):
        logger.debug("changer offline")
        dispatcher.send_minimal(
            sender=self, signal='offline')

    def initialized(self):
        logger.debug("changer initialized")
        dispatcher.send_minimal(
            sender=self, signal='initialized')

    def error(self, error_code, error_text):
        logger.debug("changer error({}): {}".format(error_code, error_text))
        dispatcher.send_minimal(
            sender=self,
            signal='error', error_code=error_code, error_text=error_text)

#     def dispensed(self, coin, count, in_tube=None):
#         coin_amount = self.get_coin_amount(coin)
#         logger.debug(
#             "Coin dispensed({}): {}".format(count, coin_amount))
#         if (count > 0) and (coin_amount > 0):
#             amount = count * coin_amount
#             dispatcher.send_minimal(
#                 sender=self, signal='coin_out', amount=amount)

    def amount_dispensed(self, amount):
        logger.debug("Amount dispensed: {}".format(amount))
        if (amount > 0):
            dispatcher.send_minimal(
                sender=self, signal='coin_out', amount=amount)

    def deposited(self, coin, routing=1, in_tube=None):
        amount = self.get_coin_amount(coin)
        logger.debug(
            "Coin deposited({}): {}".format(COINT_ROUTING[routing], amount))
        if (routing == 1) and (amount > 0):
            dispatcher.send_minimal(
                sender=self, signal='coin_in', amount=amount)

    def escrow_request1(self, status_code):
        pass

    def changer_payout_busy2(self, status_code):
        pass

    def no_credit1(self, status_code):
        pass

    def defective_tube_sensor1(self, status_code):
        pass

    def double_arrival1(self, status_code):
        pass

    def acceptor_unplugged2(self, status_code):
        pass

    def tube_jam1(self, status_code):
        pass

    def rom_checksum_error1(self, status_code):
        pass

    def coin_routing_error1(self, status_code):
        pass

    def changer_busy2(self, status_code):
        pass

    def changer_was_reset1(self, status_code):
        reactor.callLater(self.request_status_delay, self._request_status)

    def coin_jam1(self, status_code):
        pass

    def possible_credited_coin_removal1(self, status_code):
        pass

    #######################
    ## Public Methods
    #######################

    def get_total_amount(self):
        amount = 0
        for coin_type in self._coins:
            coin_amount = self.get_coin_amount(coin_type)
            if (coin_amount <= 0):
                continue
            coin_count = self.get_coin_count(coin_type)
            amount += coin_amount * coin_count
        
        return amount
