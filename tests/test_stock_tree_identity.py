import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class StockTreeIdentityTests(unittest.TestCase):
    def test_stock_actions_use_product_id_not_display_code(self):
        text=(ROOT/'todo'/'screens'/'stock.py').read_text(encoding='utf-8')
        self.assertIn("iid=str(x['id'])",text)
        self.assertIn("pid=int(s[0]);q=",text)
        self.assertIn("pid=int(selection[0])",text)
        self.assertNotIn('rows=[r for r in stock_products',text)

if __name__=='__main__':unittest.main()
