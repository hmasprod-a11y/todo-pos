import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class CustomerDisplayEnglishSettingsTests(unittest.TestCase):
 def test_receipt_and_customer_display_options_have_english(self):
  s=(ROOT/"todo"/"screens"/"settings.py").read_text(encoding="utf-8")
  for x in ("Receipt options","Customer display","Serial customer display","Displayed content"):self.assertIn(x,s)
if __name__=="__main__":unittest.main()
