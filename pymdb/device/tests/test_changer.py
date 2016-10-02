from twisted.trial import unittest
    
from pymdb.device.changer import Changer
from pymdb.device import changer


class TestChanger(unittest.TestCase):

    def setUp(self):
        self.proto = ProtoStub()
        self.coins = {}
        for i in range(changer.COIN_TYPE_COUNT):
            self.coins[i] = i + 1
        self.changer = Changer(self.proto, self.coins)
        self.changer._set_online(True)

    def tearDown(self):
        pass

    def test_coin_mask_0(self):
        coins = {0 : 10}
        changer = Changer(self.proto, coins)
        self.assertEqual('\x00\x01', changer.coin_mask)

    def test_coin_mask_1(self):
        coins = {1 : 10}
        changer = Changer(self.proto, coins)
        self.assertEqual('\x00\x02', changer.coin_mask)

    def test_coin_mask_2(self):
        coins = {2 : 10}
        changer = Changer(self.proto, coins)
        self.assertEqual('\x00\x04', changer.coin_mask)

    def test_coin_mask_3(self):
        coins = {3 : 10}
        changer = Changer(self.proto, coins)
        self.assertEqual('\x00\x08', changer.coin_mask)

    def test_coin_mask_4(self):
        coins = {4 : 10}
        changer = Changer(self.proto, coins)
        self.assertEqual('\x00\x10', changer.coin_mask)

    def test_coin_mask_5(self):
        coins = {5 : 10}
        changer = Changer(self.proto, coins)
        self.assertEqual('\x00\x20', changer.coin_mask)

    def test_coin_mask_6(self):
        coins = {6 : 10}
        changer = Changer(self.proto, coins)
        self.assertEqual('\x00\x40', changer.coin_mask)

    def test_coin_mask_7(self):
        coins = {7 : 10}
        changer = Changer(self.proto, coins)
        self.assertEqual('\x00\x80', changer.coin_mask)

    def test_coin_mask_8(self):
        coins = {8 : 10}
        changer = Changer(self.proto, coins)
        self.assertEqual('\x01\x00', changer.coin_mask)

    def test_coin_mask_9(self):
        coins = {9 : 10}
        changer = Changer(self.proto, coins)
        self.assertEqual('\x02\x00', changer.coin_mask)

    def test_coin_mask_10(self):
        coins = {10 : 10}
        changer = Changer(self.proto, coins)
        self.assertEqual('\x04\x00', changer.coin_mask)

    def test_coin_mask_11(self):
        coins = {11 : 10}
        changer = Changer(self.proto, coins)
        self.assertEqual('\x08\x00', changer.coin_mask)

    def test_coin_mask_12(self):
        coins = {12 : 10}
        changer = Changer(self.proto, coins)
        self.assertEqual('\x10\x00', changer.coin_mask)

    def test_coin_mask_13(self):
        coins = {13 : 10}
        changer = Changer(self.proto, coins)
        self.assertEqual('\x20\x00', changer.coin_mask)

    def test_coin_mask_14(self):
        coins = {14 : 10}
        changer = Changer(self.proto, coins)
        self.assertEqual('\x40\x00', changer.coin_mask)

    def test_coin_mask_15(self):
        coins = {15 : 10}
        changer = Changer(self.proto, coins)
        self.assertEqual('\x80\x00', changer.coin_mask)

    def test_coin_mask_all(self):
        coins = {
                 0 : 10,
                 1 : 10,
                 2 : 10,
                 3 : 10,
                 4 : 10,
                 5 : 10,
                 6 : 10,
                 7 : 10,
                 8 : 10,
                 9 : 10,
                 10 : 10,
                 11 : 10,
                 12 : 10,
                 13 : 10,
                 14 : 10,
                 15 : 10
                 }
        changer = Changer(self.proto, coins)
        self.assertEqual('\xff\xff', changer.coin_mask)

    def test_get_amount_exchange_1(self):
        '''
        check that changer.get_amount_exchange() return empty result for any
        amount if changer contains no coins
        '''
        self.changer._coin_count = [0] * changer.COIN_TYPE_COUNT
        self.assertEqual({}, self.changer.get_amount_exchange(-1))
        self.assertEqual({}, self.changer.get_amount_exchange(0))
        for coin_type in self.coins:
            self.assertEqual({},
                     self.changer.get_amount_exchange(self.coins[coin_type]))

    def test_get_amount_exchange_2(self):
        '''
        check that changer.get_amount_exchange() return correct coin types with
        count if changer contains enough coins
        '''
        for coin_type in self.coins:
            self.changer._coin_count[coin_type] = 1

        self.assertEqual({}, self.changer.get_amount_exchange(-1))
        self.assertEqual({}, self.changer.get_amount_exchange(0))
        for coin_type in self.coins:
            self.assertEqual({coin_type: 1}, 
                     self.changer.get_amount_exchange(self.coins[coin_type]))

    def test_get_amount_exchange_3(self):
        '''
        check that changer.get_amount_exchange() return correct coin types with
        count if changer contains enough coins
        '''
        for coin_type in self.coins:
            self.changer._coin_count[coin_type] = 1

        amount = 0
        for coin_type in self.coins:
            amount += self.coins[coin_type]
            
        expected_coins = {}
        for coin_type in self.coins:
            expected_coins[coin_type] = 1
            
        self.assertEqual(expected_coins, 
                         self.changer.get_amount_exchange(amount))

    def test_get_amount_exchange_4(self):
        '''
        check that changer.get_amount_exchange() return correct coin types with
        count if changer contains enough coins
        '''
        for coin_type in self.coins:
            self.changer._coin_count[coin_type] = coin_type + 1

        amount = 0
        for coin_type in self.coins:
            amount += self.coins[coin_type] * (coin_type + 1)
            
        expected_coins = {}
        for coin_type in self.coins:
            expected_coins[coin_type] = coin_type + 1
            
        self.assertEqual(expected_coins, 
                         self.changer.get_amount_exchange(amount))

    def test_get_amount_exchange_5(self):
        '''
        check that changer.get_amount_exchange() return available coin types
        with count if changer contains not enough coins
        '''
        for i in range(changer.COIN_TYPE_COUNT):
            expected_coins = {}
            for coin_type in self.coins:
                self.changer._coin_count[coin_type] = 1
                expected_coins[coin_type] = 1
            
            for j in range(i + 1):
                self.changer._coin_count[j] = 0
                del expected_coins[j]
    
            amount = 0
            for coin_type in self.coins:
                amount += self.coins[coin_type]
                
            self.assertEqual(expected_coins, 
                             self.changer.get_amount_exchange(amount))

    def test_get_amount_exchange_6(self):
        '''
        check that changer.get_amount_exchange() return available coin types
        with count if changer contains not enough coins
        '''
        for i in range(changer.COIN_TYPE_COUNT):
            expected_coins = {}
            for coin_type in self.coins:
                self.changer._coin_count[coin_type] = 2
                expected_coins[coin_type] = 2
            
            for j in range(i + 1):
                self.changer._coin_count[j] = 1
                expected_coins[j] = 1
    
            amount = 0
            for coin_type in self.coins:
                amount += 2 * self.coins[coin_type]
                
            self.assertEqual(expected_coins, 
                             self.changer.get_amount_exchange(amount))

    def test_get_amount_exchange_7(self):
        '''
        check that changer.get_amount_exchange() return available coin types
        with count if changer contains not enough coins
        '''
        for coin_type in self.coins:
            self.changer._coin_count = [0] * changer.COIN_TYPE_COUNT
            expected_coins = {}
            self.changer._coin_count[coin_type] = 1
            expected_coins[coin_type] = 1
            amount = 2 * self.coins[coin_type]
            
            self.assertEqual(expected_coins, 
                             self.changer.get_amount_exchange(amount))

    def test_get_amount_exchange_8(self):
        '''
        check that changer.get_amount_exchange() return available coin types
        with count if changer contains not enough coins
        '''
        for coin_type in range(changer.COIN_TYPE_COUNT - 1):
            self.changer._coin_count = [0] * changer.COIN_TYPE_COUNT
            expected_coins = {}
            self.changer._coin_count[coin_type] = 1
            expected_coins[coin_type] = 1
            amount = self.coins[coin_type + 1]
            
            self.assertEqual(expected_coins, 
                             self.changer.get_amount_exchange(amount))

    def test_get_amount_exchange_9(self):
        '''
        check that changer.get_amount_exchange() return available coin types
        with count if changer contains not enough coins
        '''
        for coin_type in range(changer.COIN_TYPE_COUNT - 1):
            self.changer._coin_count = [0] * changer.COIN_TYPE_COUNT
            self.changer._coin_count[coin_type + 1] = 1
            amount = self.coins[coin_type]
            
            self.assertEqual({}, self.changer.get_amount_exchange(amount))

    def test_can_dispense_amount_1(self):
        '''
        check that changer.can_dispense_amount() return False for any
        amount if changer contains no coins (expect when amount is 0)
        '''
        self.changer._coin_count = [0] * changer.COIN_TYPE_COUNT
        self.assertFalse(self.changer.can_dispense_amount(-1))
        self.assertTrue(self.changer.can_dispense_amount(0))
        for coin_type in self.coins:
            self.assertFalse(self.changer.can_dispense_amount(
                                                      self.coins[coin_type]))

    def test_can_dispense_amount_2(self):
        '''
        check that changer.can_dispense_amount() return True if changer
        contains enough coins
        '''
        for coin_type in self.coins:
            self.changer._coin_count[coin_type] = 1

        self.assertFalse(self.changer.can_dispense_amount(-1))
        self.assertTrue(self.changer.can_dispense_amount(0))
        for coin_type in self.coins:
            self.assertTrue(self.changer.can_dispense_amount(
                                                     self.coins[coin_type]))

    def test_can_dispense_amount_3(self):
        '''
        check that changer.can_dispense_amount() return True if changer
        contains enough coins
        '''
        for coin_type in self.coins:
            self.changer._coin_count[coin_type] = 1

        amount = 0
        for coin_type in self.coins:
            amount += self.coins[coin_type]
            
        self.assertTrue(self.changer.can_dispense_amount(amount))

    def test_can_dispense_amount_4(self):
        '''
        check that changer.can_dispense_amount() return True if changer
        contains enough coins
        '''
        for coin_type in self.coins:
            self.changer._coin_count[coin_type] = coin_type + 1

        amount = 0
        for coin_type in self.coins:
            amount += self.coins[coin_type] * (coin_type + 1)
            
        self.assertTrue(self.changer.can_dispense_amount(amount))

    def test_can_dispense_amount_5(self):
        '''
        check that changer.can_dispense_amount() return False if changer
        contains not enough coins
        '''
        for i in range(changer.COIN_TYPE_COUNT):
            for coin_type in self.coins:
                self.changer._coin_count[coin_type] = 1
            
            for j in range(i + 1):
                self.changer._coin_count[j] = 0
    
            amount = 0
            for coin_type in self.coins:
                amount += self.coins[coin_type]
                
            self.assertFalse(self.changer.can_dispense_amount(amount))

    def test_can_dispense_amount_6(self):
        '''
        check that changer.can_dispense_amount() return False if changer
        contains not enough coins
        '''
        for i in range(changer.COIN_TYPE_COUNT):
            for coin_type in self.coins:
                self.changer._coin_count[coin_type] = 2
            
            for j in range(i + 1):
                self.changer._coin_count[j] = 1
    
            amount = 0
            for coin_type in self.coins:
                amount += 2 * self.coins[coin_type]
                
            self.assertFalse(self.changer.can_dispense_amount(amount))

    def test_can_dispense_amount_7(self):
        '''
        check that changer.can_dispense_amount() return False if changer
        contains not enough coins
        '''
        for coin_type in self.coins:
            self.changer._coin_count = [0] * changer.COIN_TYPE_COUNT
            self.changer._coin_count[coin_type] = 1
            amount = 2 * self.coins[coin_type]
            
            self.assertFalse(self.changer.can_dispense_amount(amount))

    def test_can_dispense_amount_8(self):
        '''
        check that changer.can_dispense_amount() return False if changer
        contains not enough coins
        '''
        for coin_type in range(changer.COIN_TYPE_COUNT - 1):
            self.changer._coin_count = [0] * changer.COIN_TYPE_COUNT
            self.changer._coin_count[coin_type] = 1
            amount = self.coins[coin_type + 1]
            
            self.assertFalse(self.changer.can_dispense_amount(amount))

    def test_can_dispense_amount_9(self):
        '''
        check that changer.can_dispense_amount() return False if changer
        contains not enough coins
        '''
        for coin_type in range(changer.COIN_TYPE_COUNT - 1):
            self.changer._coin_count = [0] * changer.COIN_TYPE_COUNT
            self.changer._coin_count[coin_type + 1] = 1
            amount = self.coins[coin_type]
            
            self.assertFalse(self.changer.can_dispense_amount(amount))

    def test_can_dispense_amount_10(self):
        '''
        check that changer.can_dispense_amount() return False if changer
        contains enough coins but is in state Offline
        '''
        self.changer._set_online(False)
        for coin_type in self.coins:
            self.changer._coin_count[coin_type] = 1

        self.assertFalse(self.changer.can_dispense_amount(-1))
        self.assertFalse(self.changer.can_dispense_amount(0))
        for coin_type in self.coins:
            self.assertFalse(self.changer.can_dispense_amount(
                                                     self.coins[coin_type]))

class ProtoStub():
    pass
