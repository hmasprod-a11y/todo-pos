import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class SettingsEnglishSectionsTests(unittest.TestCase):
 def test_price_payment_and_printing_sections_have_english(self):
  s=(ROOT/"todo"/"screens"/"settings.py").read_text(encoding="utf-8")
  for x in ("Price lists","Payment methods","Printing","Refresh printers"):self.assertIn(x,s)
if __name__=="__main__":unittest.main()
