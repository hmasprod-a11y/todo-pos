import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class CashdeskLocalizationUiTests(unittest.TestCase):
 def test_cashdesk_has_explicit_english_for_critical_cashier_controls(self):
  source=(ROOT/"todo"/"screens"/"cashdesk.py").read_text(encoding="utf-8")
  self.assertIn("Cash drawer",source);self.assertIn("Expected cash",source)
  self.assertIn("Close drawer",source);self.assertIn("No open cash drawer",source)
if __name__=="__main__":unittest.main()
