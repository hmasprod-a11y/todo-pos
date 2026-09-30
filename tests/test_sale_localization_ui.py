import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class SaleLocalizationUiTests(unittest.TestCase):
 def test_sale_has_explicit_english_for_cashier_critical_controls(self):
  source=(ROOT/"todo"/"screens"/"sale.py").read_text(encoding="utf-8")
  for label in ("SCAN / SEARCH","NET TOTAL","PAY with receipt","Current receipt","F2  CASH"):
   self.assertIn(label,source)
if __name__=="__main__":unittest.main()
