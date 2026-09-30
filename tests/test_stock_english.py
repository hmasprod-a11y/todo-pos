import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class StockEnglishTests(unittest.TestCase):
 def test_stock_screen_has_english_for_operational_controls(self):
  s=(ROOT/"todo"/"screens"/"stock.py").read_text(encoding="utf-8")
  for x in ("Adjust stock","Stock alerts","Reorder","Global journal","Last movement"):self.assertIn(x,s)
if __name__=="__main__":unittest.main()
