import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class ProductsEnglishTests(unittest.TestCase):
 def test_product_editor_and_catalog_have_english_core_labels(self):
  s=(ROOT/"todo"/"screens"/"products.py").read_text(encoding="utf-8")
  for x in ("Product image","Purchase price","Barcodes / packs","Show in sale photos","Unit price: from the stated quantity."):self.assertIn(x,s)
if __name__=="__main__":unittest.main()
