import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class ProductsTaxEnglishTests(unittest.TestCase):
 def test_tax_promotion_and_catalog_actions_have_english(self):
  s=(ROOT/"todo"/"screens"/"products.py").read_text(encoding="utf-8")
  for x in ("Tax (%)","Promotions and quantity pricing","Import Excel","Export catalog"):self.assertIn(x,s)
if __name__=="__main__":unittest.main()
