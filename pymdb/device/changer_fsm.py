import logging

from twisted.internet import reactor, defer

from louie import dispatcher

from transitions import Machine

from changer import Changer, COINT_ROUTING

logger = logging.getLogger('pymdb')

class ChangerFSM(Machine):

    def __init__(self, changer):
        # TODO проверить состояние приемника перед переходом в ready
        
        states = ["offline", "online", "error", "ready",
                  "wait_coin", "check_coin", "dispense_amount"]
        transitions = [
            # trigger,                 source,            dest,              conditions,     unless,          before,           after
            ['signal_online',          'offline',         'online',           None,           None,            None,            '_after_online'     ],
            ['signal_initialized',     'online',          'ready',            None,           None,            None,            '_after_init'       ],
            ['signal_start_accept',    'ready',           'wait_coin',        None,           None,            None,            '_start_accept'     ],
            ['signal_dispense_amount', 'ready',           'dispense_amount',  None,           None,            None,            '_start_dispense'   ],
            ['signal_coin_in',         'wait_coin',       'check_coin',       None,           None,            None,            '_check_coin'       ],
            ['signal_stop_accept',     'wait_coin',       'ready',            None,           None,           '_stop_accept',    None               ],
            ['signal_valid_coin',      'check_coin',      'wait_coin',        None,           None,           '_add_amount',     None               ],
            ['signal_invalid_coin',    'check_coin',      'wait_coin',        None,           None,           '_discard_coin',   None               ],
            ['signal_stop_accept',     'check_coin',      'ready',            None,           None,           '_stop_accept',   '_discard_coin'     ],
            ['signal_coin_out',        'dispense_amount', 'dispense_amount',  None,          '_is_dispensed', '_remove_amount',  None               ],
            ['signal_coin_out',        'dispense_amount', 'ready',           '_is_dispensed', None,           '_remove_amount', '_amount_dispensed' ],
            ['signal_stop_dispense',   'dispense_amount', 'ready',            None,           None,            None,            '_amount_dispensed' ],
            
            ['signal_coin_in',         'ready',           'ready',            None,           None,           '_discard_coin',   None               ],
            ['signal_coin_in',         'check_coin',      'check_coin',       None,           None,           '_discard_coin',   None               ],
            
            ['signal_error',           'online',          'error',            None,           None,            None,            '_after_error'      ],
            ['signal_error',           'ready',           'error',            None,           None,            None,            '_after_error'      ],
            ['signal_error',           'wait_coin',       'error',            None,           None,            None,            '_after_error'      ],
            ['signal_error',           'check_coin',      'error',            None,           None,            None,            '_after_error'      ],
            ['signal_error',           'dispense_amount', 'error',            None,           None,            None,            '_after_error'      ],
            ['signal_offline',         'online',          'offline',          None,           None,            None,            '_after_offline'    ],
            ['signal_offline',         'ready',           'offline',          None,           None,            None,            '_after_offline'    ],
            ['signal_offline',         'error',           'offline',          None,           None,            None,            '_after_offline'    ],
            ['signal_offline',         'wait_coin',       'offline',          None,           None,            None,            '_after_offline'    ],
            ['signal_offline',         'check_coin',      'offline',          None,           None,            None,            '_after_offline'    ],
            ['signal_offline',         'dispense_amount', 'offline',          None,           None,            None,            '_after_offline'    ],
            
        ]
        super(ChangerFSM, self).__init__(
            states=states, transitions=transitions, initial='offline')
        self.changer = changer
        dispatcher.connect(self.signal_online, sender=changer, signal='signal_online')
        dispatcher.connect(self.signal_initialized, sender=changer, signal='signal_initialized')
        dispatcher.connect(self.signal_start_accept, sender=self, signal='signal_start_accept')
        dispatcher.connect(self.signal_dispense_amount, sender=self, signal='signal_dispense_amount')
        dispatcher.connect(self.signal_stop_dispense, sender=self, signal='signal_stop_dispense')
        dispatcher.connect(self.signal_coin_in, sender=changer, signal='signal_coin_in')
        dispatcher.connect(self.signal_stop_accept, sender=self, signal='signal_stop_accept')
        dispatcher.connect(self.signal_valid_coin, sender=self, signal='signal_valid_coin')
        dispatcher.connect(self.signal_invalid_coin, sender=self, signal='signal_invalid_coin')
        dispatcher.connect(self.signal_coin_out, sender=changer, signal='signal_coin_out')
        dispatcher.connect(self.signal_error, sender=changer, signal='signal_error')
        dispatcher.connect(self.signal_offline, sender=changer, signal='signal_offline')
        
        # init parameters
        self._dispensed_amount = 0
        self._check_coin_amount = 0
        self._accepted_amount = 0

    def start(self):
        self.changer.start_device()

    def stop(self):
        # TODO сбросить автомат
        self.changer.stop_device()

    def start_accept(self):
        #TODO обработать MachineError
        logger.debug('start accept')
        dispatcher.send_minimal(sender=self, signal='signal_start_accept')

    def stop_accept(self):
        #TODO обработать MachineError
        logger.debug('stop accept')
        dispatcher.send_minimal(sender=self, signal='signal_stop_accept')

    def dispense_amount(self, amount):
        #TODO обработать MachineError
        logger.debug('dispense amount: {}'.format(amount))
        if (amount <= 0):
            return
        dispatcher.send_minimal(sender=self, signal='signal_dispense_amount', amount=amount)

    def stop_dispense_amount(self):
        #TODO обработать MachineError
        logger.debug('stop dispense amount')
        dispatcher.send_minimal(sender=self, signal='signal_stop_dispense')

    def valid_coin(self, amount):
        #TODO обработать MachineError
        logger.debug('valid coin: {}'.format(amount))
        dispatcher.send_minimal(sender=self, signal='signal_valid_coin', amount=amount)

    def invalid_coin(self, amount):
        #TODO обработать MachineError
        logger.debug('invalid coin: {}'.format(amount))
        dispatcher.send_minimal(sender=self, signal='signal_invalid_coin', amount=amount)

    def can_dispense_amount(self, amount):
        return self._can_dispense_amount(amount)

    def check_coin(self, amount):
        pass

    def amount_dispensed(self, amount):
        #TODO remove method?
        pass

    def amount_accepted(self, amount):
        #TODO remove method?
        return

    def _after_online(self):
        logger.debug("_after_online")

    def _after_offline(self):
        logger.debug("_after_offline")

    def _after_init(self):
        logger.debug("_after_init")

    def _after_error(self, error_code, error_text):
        logger.debug("_after_error({}): {}".format(ord(error_code), error_text))
        #TODO handle exception
        self._stop_accept()

    def _start_accept(self):
        logger.debug("_start_accept")
        self._accepted_amount = 0
        self.changer.start_accept()

    def _stop_accept(self):
        logger.debug("_stop_accept")
        self.changer.stop_accept()

    def _start_dispense(self, amount):
        logger.debug("_start_dispense")
        self._dispensed_amount = amount
        reactor.callLater(0, self._dispense_amount_impl, amount=amount)
 
    #TODO отдельно выделить и оптимизировать алгоритм определения возможности выдачи сдачи
    
    def _dispense_amount_impl(self, amount):
        balance = amount
        logger.debug("_dispense_amount_impl: start_balance={}".format(balance))
        for coin_type in range(0x0f,-1,-1):
            coin_amount = self.changer.get_coin_amount(coin_type)
            if (coin_amount <= 0):
                continue
            coin_count = self.changer.coin_count_in_amount(coin_type, balance)
            actual_coin_count = self.changer.get_coin_count(coin_type)
            if coin_count > actual_coin_count:
                coin_count = actual_coin_count
            logger.debug("_dispense_amount_impl: {} coins({}) in amount {}".format(coin_count, coin_amount, balance))
            if coin_count > 0:
                try:
                    balance -= coin_amount * coin_count
                    #self.changer.dispense(coin=coin_type, count=coin_count)
                    self.__dispense_amount_impl(coin_type, coin_count)
                except Exception as e:
                    logger.exception("While dispense amount")
        logger.debug("_dispense_amount_impl: end_balance={}".format(balance))

    def __dispense_amount_impl(self, coin, count):
        logger.debug("__dispense_amount_impl: need dispense {} coins({})".format(count, coin))
        dispense_count = count
        while dispense_count > 0:
            coin_count = dispense_count if dispense_count <= 0xf else 0xf
            logger.debug("__dispense_amount_impl: need dispense {} coins({})".format(coin_count, coin))
            # TODO ожидать выполнения предыдущей операции (разобраться, почему не всегда выдает необходимую сумму)
            self.changer.dispense(coin=coin, count=coin_count)
            dispense_count -= coin_count
        
    def _can_dispense_amount(self, amount):
        balance = amount
        logger.debug("_can_dispense_amount: start_balance={}".format(balance))
        for coin_type in range(0x0f,-1,-1):
            coin_amount = self.changer.get_coin_amount(coin_type)
            if (coin_amount <= 0):
                continue
            coin_count = self.changer.coin_count_in_amount(coin_type, balance)
            actual_coin_count = self.changer.get_coin_count(coin_type)
            if coin_count > actual_coin_count:
                coin_count = actual_coin_count
            logger.debug("_can_dispense_amount: {} coins({}) in amount {}".format(coin_count, coin_amount, balance))
            if coin_count > 0:
                balance -= coin_amount * coin_count
        logger.debug("_can_dispense_amount: end_balance={}".format(balance))
        return balance <= 0
        
    def _add_amount(self, amount):
        logger.debug("_add_amount: {}".format(amount))
        self._accepted_amount += amount
        self.amount_accepted(amount)

    def _remove_amount(self, amount):
        logger.debug("_remove_amount: {}".format(amount))
        self._dispensed_amount -= amount

    def _discard_coin(self, amount=-1):
        if amount < 0:
            amount = self._check_coin_amount
        logger.debug("_discard_coin: {}".format(amount))
        reactor.callLater(0, self._dispense_amount_impl, amount=amount)

    def _is_dispensed(self, amount):
        logger.debug("_is_dispensed: {}".format(amount))
        return self._dispensed_amount - amount <= 0

    def _check_coin(self, amount):
        logger.debug("_check_coin: amount={}".format(amount))
        self._check_coin_amount = amount
        self.check_coin(amount)

    def _amount_dispensed(self, amount):
        logger.debug("_amount_dispensed: {}".format(self._dispensed_amount))
        #self.amount_dispensed(self._dispensed_amount)


class ChangerWrapper(Changer):

    def __init__(self, proto, coins):
        super(ChangerWrapper, self).__init__(proto, coins)

    def online(self):
        #TODO обработать MachineError
        logger.debug("changer online")
        dispatcher.send_minimal(
            sender=self, signal='signal_online')

    def offline(self):
        #TODO обработать MachineError
        logger.debug("changer offline")
        dispatcher.send_minimal(
            sender=self, signal='signal_offline')

    def initialized(self):
        #TODO обработать MachineError
        logger.debug("changer initialized")
        dispatcher.send_minimal(
            sender=self, signal='signal_initialized')

    def error(self, error_code, error_text):
        #TODO обработать MachineError
        logger.debug("changer error({}): {}".format(ord(error_code), error_text))
        dispatcher.send_minimal(
            sender=self, signal='signal_error', error_code=error_code, error_text=error_text)

    def deposited(self, coin, routing=1, in_tube=None):
        #TODO обработать MachineError
        amount = self.get_coin_amount(coin)
        logger.debug(
            "Coin deposited({}): {}".format(COINT_ROUTING[routing], amount))
        if (routing == 1) and (amount > 0):
            dispatcher.send_minimal(
                sender=self, signal='signal_coin_in', amount=amount)

    def dispensed(self, coin, count, in_tube=None):
        #TODO обработать MachineError
        amount = self.get_coin_amount(coin)
        logger.debug(
            "Coin dispensed({}): {}".format(count, amount))
        if (count > 0) and (amount > 0):
            dispatcher.send_minimal(
                sender=self, signal='signal_coin_out', count=count, amount=amount)
