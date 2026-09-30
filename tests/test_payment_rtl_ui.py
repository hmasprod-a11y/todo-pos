import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class PaymentRtlUiTests(unittest.TestCase):
 def test_payment_mirrors_payment_choices_and_summary_for_arabic(self):
  source=(ROOT/"todo"/"screens"/"payment.py").read_text(encoding="utf-8")
  self.assertIn("self.rtl=self.lang=='ar'",source)
  self.assertIn("side='right' if self.rtl else 'left'",source)
if __name__=="__main__":unittest.main()
