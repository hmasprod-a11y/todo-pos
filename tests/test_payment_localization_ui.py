import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class PaymentLocalizationUiTests(unittest.TestCase):
 def test_payment_keeps_explicit_english_for_total_change_and_confirmation(self):
  source=(ROOT/"todo"/"screens"/"payment.py").read_text(encoding="utf-8")
  for label in ("TOTAL DUE","Amount received","Change due","CONFIRM","Split payment must cover"):
   self.assertIn(label,source)
if __name__=="__main__":unittest.main()
