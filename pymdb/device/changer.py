from twisted.internet import reactor, defer, task

from mdb_device import MDBDevice
from ..protocol.mdb import log_result, encode, ACK

import logging

logger = logging.getLogger('pymdb')

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

_ERROR_NAMES = {
    '\x03': 'No Credit1',
    '\x04': 'Defective Tube Sensor1',
    '\x07': 'Tube Jam1',
    '\x08': 'ROM checksum error1',
    '\x0C': 'Coin Jam1'
}

_STATE_NAMES = {
    '\x02': 'payout_busy',
    '\x06': 'acceptor_unplugged',
    '\x0A': 'changer_busy'
}

STATES = {
    'payout_busy':         False, #'Changer Payout Busy2',
    'acceptor_unplugged':  False, #'Acceptor Unplugged2',
    'changer_busy':        False  #'Changer Busy2'
}

COINT_ROUTING = {
    0: "Cash box",
    1: "Tubes",
    2: "Not used",
    3: "Reject"
}


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

    _coin_count = [0] * 0x10
    
    def __init__(self, proto, coins):
        super(Changer, self).__init__(proto)
        self._coins = coins

    def get_coin_count(self, coin):
        return self._coin_count[coin]

    def get_coin_amount(self, coin):
        if coin not in self._coins:
            return 0
        return self._coins[coin]

    def start_accept(self):
        # TODO формировать маску в зависимости от поддерживаемых монет
        return self.coin_type(coins='\xFF\xFF')

    def stop_accept(self):
        return self.coin_type(coins='\x00\x00')

    def coin_count_in_amount(self, coin_type, amount):
        if amount <= 0:
            return 0
        coin_amount = self.get_coin_amount(coin_type)
        if coin_amount == 0:
            return 0
        return amount // coin_amount
    
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
        
        status_offset = 0        
        # payin or payout+
        if len(result) >= 2:
            coin_in_tube = ord(result[1])
            data = result[0]
            if (ord(data) & ord('\x80')) >> 7:
                logger.debug("Coin dispensed")
                coin_count = (ord(data) & ord('\x70'))
                coin = (ord(data) & ord('\x0F'))
                self._coin_count[coin] = coin_in_tube
                self.dispensed(coin, coin_count, in_tube=coin_in_tube)
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
                if r == '\x0B':
                    self.changer_was_reset1(r)
#                 elif r == '\x0C':
#                     self.coin_jam1(r)
#                 elif r == '\x0D':
#                     self.possible_credited_coin_removal1(r)
                
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

    @defer.inlineCallbacks
    def dispense(self, coin, count):
        data = chr((count << 4) + coin)
        logger.debug("try to dispense with data 0x%0.2X" % ord(data))
        request = encode(self.commands['dispense'], data)
        yield self.call(request)
        waiter = defer.Deferred()
        self.waiters.append(waiter)
        yield waiter

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

    def dispensed(self, coin, count, in_tube=None):
        pass

    def deposited(self, coin, routing=1, in_tube=None):
        pass

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
