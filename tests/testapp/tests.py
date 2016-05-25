from django.test import TransactionTestCase


class RegressionTestCase(TransactionTestCase):

    def test_hi(self):
        self.fail('sdf')
