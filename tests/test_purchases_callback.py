import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class PurchasesCallbackTests(unittest.TestCase):
 def test_purchase_enter_callback_accepts_missing_tk_event(self):
  source=(ROOT/"todo"/"screens"/"purchases.py").read_text(encoding="utf-8")
  self.assertIn('self.prod.bind("<Return>",lambda e=None:self.addline())',source)
if __name__=="__main__":unittest.main()
