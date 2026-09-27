import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class ProductLifecycleUiTests(unittest.TestCase):
    def test_stock_exposes_new_and_deactivate(self):
        text=(ROOT/'todo'/'screens'/'stock.py').read_text(encoding='utf-8')
        self.assertIn('+ Nouveau',text);self.assertIn('Désactiver',text)
    def test_products_exposes_deactivate(self):
        text=(ROOT/'todo'/'screens'/'products.py').read_text(encoding='utf-8')
        self.assertIn("command=self.deactivate",text)
if __name__=='__main__':unittest.main()
