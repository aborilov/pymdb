import logging

from twisted.internet import reactor, defer

from louie import dispatcher

from transitions import Machine

from bill_validator import BillValidator, BILL_ROUTING

logger = logging.getLogger('pymdb')

class BillValidatorFSM(Machine):

    def __init__(self, validator):
        # TODO проверить состояние приемника перед переходом в ready
        
        states = ["offline", "online", "error", "ready",
                  "wait_bill", "check_bill"]
        transitions = [
            # trigger,                 source,            dest,              conditions,     unless,          before,           after
            ['signal_online',          'offline',         'online',           None,           None,            None,            '_after_online'     ],
            ['signal_initialized',     'online',          'ready',            None,           None,            None,            '_after_init'       ],
            ['signal_start_accept',    'ready',           'wait_bill',        None,           None,            None,            '_start_accept'     ],
            ['signal_bill_in',         'wait_bill',       'check_bill',       None,           None,            None,            '_check_bill'       ],
            ['signal_stop_accept',     'wait_bill',       'ready',            None,           None,           '_stop_accept',    None               ],
            ['signal_valid_bill',      'check_bill',      'wait_bill',        None,           None,           '_add_amount',     None               ],
            ['signal_invalid_coin',    'check_bill',      'wait_bill',        None,           None,           '_discard_bill',   None               ],
            ['signal_stop_accept',     'check_bill',      'ready',            None,           None,           '_stop_accept',   '_discard_bill'     ],
            
            ['signal_bill_in',         'ready',           'ready',            None,           None,           '_discard_bill',   None               ],
            ['signal_bill_in',         'check_bill',      'check_bill',       None,           None,           '_discard_bill',   None               ],
            
            ['signal_error',           'online',          'error',            None,           None,            None,            '_after_error'      ],
            ['signal_error',           'ready',           'error',            None,           None,            None,            '_after_error'      ],
            ['signal_error',           'wait_bill',       'error',            None,           None,            None,            '_after_error'      ],
            ['signal_error',           'check_bill',      'error',            None,           None,            None,            '_after_error'      ],
            ['signal_offline',         'online',          'offline',          None,           None,            None,            '_after_offline'    ],
            ['signal_offline',         'ready',           'offline',          None,           None,            None,            '_after_offline'    ],
            ['signal_offline',         'error',           'offline',          None,           None,            None,            '_after_offline'    ],
            ['signal_offline',         'wait_bill',       'offline',          None,           None,            None,            '_after_offline'    ],
            ['signal_offline',         'check_bill',      'offline',          None,           None,            None,            '_after_offline'    ],
            
        ]
        super(BillValidatorFSM, self).__init__(
            states=states, transitions=transitions, initial='offline')
        self.validator = validator
        dispatcher.connect(self.signal_online, sender=validator, signal='signal_online')
        dispatcher.connect(self.signal_initialized, sender=validator, signal='signal_initialized')
        dispatcher.connect(self.signal_start_accept, sender=self, signal='signal_start_accept')
        dispatcher.connect(self.signal_bill_in, sender=validator, signal='signal_bill_in')
        dispatcher.connect(self.signal_stop_accept, sender=self, signal='signal_stop_accept')
        dispatcher.connect(self.signal_valid_bill, sender=self, signal='signal_valid_bill')
        dispatcher.connect(self.signal_invalid_coin, sender=self, signal='signal_invalid_coin')
        dispatcher.connect(self.signal_error, sender=validator, signal='signal_error')
        dispatcher.connect(self.signal_offline, sender=validator, signal='signal_offline')
        
        # init parameters
        self._check_coin_amount = 0
        self._accepted_amount = 0

    def start(self):
        self.validator.start_device()

    def stop(self):
        # TODO сбросить автомат
        self.validator.stop_device()

    def start_accept(self):
        #TODO обработать MachineError
        logger.debug('start accept')
        dispatcher.send_minimal(sender=self, signal='signal_start_accept')

    def stop_accept(self):
        #TODO обработать MachineError
        logger.debug('stop accept')
        dispatcher.send_minimal(sender=self, signal='signal_stop_accept')

    def valid_bill(self, amount):
        #TODO обработать MachineError
        logger.debug('valid bill: {}'.format(amount))
        dispatcher.send_minimal(sender=self, signal='signal_valid_bill', amount=amount)

    def invalid_bill(self, amount):
        #TODO обработать MachineError
        logger.debug('invalid bill: {}'.format(amount))
        dispatcher.send_minimal(sender=self, signal='signal_invalid_bill', amount=amount)

    def check_bill(self, amount):
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
        self.validator.start_accept()

    def _stop_accept(self):
        logger.debug("_stop_accept")
        self.validator.stop_accept()
        
    def _add_amount(self, amount):
        logger.debug("_add_amount: {}".format(amount))
        self._accepted_amount += amount
        self.amount_accepted(amount)

    def _discard_bill(self, amount=-1):
        #TODO discard bill
        return
#         if amount < 0:
#             amount = self._check_coin_amount
#         logger.debug("_discard_coin: {}".format(amount))
#         reactor.callLater(0, self._dispense_amount_impl, amount=amount)

    def _check_bill(self, amount):
        #TODO
        return
#         logger.debug("_check_bill: amount={}".format(amount))
#         self._check_coin_amount = amount
#         self.check_coin(amount)


class ValidatorWrapper(BillValidator):

    def __init__(self, proto, bills):
        super(ValidatorWrapper, self).__init__(proto, bills)

    def online(self):
        #TODO обработать MachineError
        logger.debug("validator online")
        dispatcher.send_minimal(
            sender=self, signal='signal_online')

    def offline(self):
        #TODO обработать MachineError
        logger.debug("validator offline")
        dispatcher.send_minimal(
            sender=self, signal='signal_offline')

    def initialized(self):
        #TODO обработать MachineError
        logger.debug("validator initialized")
        dispatcher.send_minimal(
            sender=self, signal='signal_initialized')

    def error(self, error_code, error_text):
        #TODO обработать MachineError
        logger.debug("validator error({}): {}".format(ord(error_code), error_text))
        dispatcher.send_minimal(
            sender=self, signal='signal_error', error_code=error_code, error_text=error_text)

    def deposited(self, coin, routing=1, in_tube=None):
        #TODO обработать MachineError
        #TODO реализация
        return
#         amount = self.get_coin_amount(coin)
#         logger.debug(
#             "Coin deposited({}): {}".format(COINT_ROUTING[routing], amount))
#         if (routing == 1) and (amount > 0):
#             dispatcher.send_minimal(
#                 sender=self, signal='signal_coin_in', amount=amount)
