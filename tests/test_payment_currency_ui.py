import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class PaymentCurrencyUiTests(unittest.TestCase):
    def test_payment_keypad_uses_the_selected_currency(self):
        text=(ROOT/'todo'/'screens'/'payment.py').read_text(encoding='utf-8')
        self.assertIn("currency=None", text)
        self.assertIn("self.currency = currency or get_setting('currency', 'DH')", text)
        self.assertIn("text=f'{value:g} {self.currency}'", text)
        self.assertNotIn("text=f'{value:g} DH'", text)

if __name__=='__main__':
    unittest.main()
