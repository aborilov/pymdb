from twisted.trial import unittest
    
from pymdb.device.bill_validator import BillValidator


class TestBillValidator(unittest.TestCase):

    def setUp(self):
        self.proto = ProtoStub()

    def tearDown(self):
        pass

    def test_bill_mask_0(self):
        bills = {0 : 10}
        validator = BillValidator(self.proto, bills)
        self.assertEqual('\x00\x01\x00\x01', validator.bill_mask)

    def test_bill_mask_1(self):
        bills = {1 : 10}
        validator = BillValidator(self.proto, bills)
        self.assertEqual('\x00\x02\x00\x02', validator.bill_mask)

    def test_bill_mask_2(self):
        bills = {2 : 10}
        validator = BillValidator(self.proto, bills)
        self.assertEqual('\x00\x04\x00\x04', validator.bill_mask)

    def test_bill_mask_3(self):
        bills = {3 : 10}
        validator = BillValidator(self.proto, bills)
        self.assertEqual('\x00\x08\x00\x08', validator.bill_mask)

    def test_bill_mask_4(self):
        bills = {4 : 10}
        validator = BillValidator(self.proto, bills)
        self.assertEqual('\x00\x10\x00\x10', validator.bill_mask)

    def test_bill_mask_5(self):
        bills = {5 : 10}
        validator = BillValidator(self.proto, bills)
        self.assertEqual('\x00\x20\x00\x20', validator.bill_mask)

    def test_bill_mask_6(self):
        bills = {6 : 10}
        validator = BillValidator(self.proto, bills)
        self.assertEqual('\x00\x40\x00\x40', validator.bill_mask)

    def test_bill_mask_7(self):
        bills = {7 : 10}
        validator = BillValidator(self.proto, bills)
        self.assertEqual('\x00\x80\x00\x80', validator.bill_mask)

    def test_bill_mask_8(self):
        bills = {8 : 10}
        validator = BillValidator(self.proto, bills)
        self.assertEqual('\x01\x00\x01\x00', validator.bill_mask)

    def test_bill_mask_9(self):
        bills = {9 : 10}
        validator = BillValidator(self.proto, bills)
        self.assertEqual('\x02\x00\x02\x00', validator.bill_mask)

    def test_bill_mask_10(self):
        bills = {10 : 10}
        validator = BillValidator(self.proto, bills)
        self.assertEqual('\x04\x00\x04\x00', validator.bill_mask)

    def test_bill_mask_11(self):
        bills = {11 : 10}
        validator = BillValidator(self.proto, bills)
        self.assertEqual('\x08\x00\x08\x00', validator.bill_mask)

    def test_bill_mask_12(self):
        bills = {12 : 10}
        validator = BillValidator(self.proto, bills)
        self.assertEqual('\x10\x00\x10\x00', validator.bill_mask)

    def test_bill_mask_13(self):
        bills = {13 : 10}
        validator = BillValidator(self.proto, bills)
        self.assertEqual('\x20\x00\x20\x00', validator.bill_mask)

    def test_bill_mask_14(self):
        bills = {14 : 10}
        validator = BillValidator(self.proto, bills)
        self.assertEqual('\x40\x00\x40\x00', validator.bill_mask)

    def test_bill_mask_15(self):
        bills = {15 : 10}
        validator = BillValidator(self.proto, bills)
        self.assertEqual('\x80\x00\x80\x00', validator.bill_mask)

    def test_bill_mask_all(self):
        bills = {
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
        validator = BillValidator(self.proto, bills)
        self.assertEqual('\xff\xff\xff\xff', validator.bill_mask)


class ProtoStub():
    pass
