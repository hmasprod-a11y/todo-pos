import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class StockCahierColumnsUiTests(unittest.TestCase):
    def test_stock_screen_contains_required_columns(self):
        text=(ROOT/'todo'/'screens'/'stock.py').read_text(encoding='utf-8')
        for token in ('"Code"','"Article"','"Famille"','"PRIX_A"','"PRIX_V"','"Stock"'):
            self.assertIn(token,text)
if __name__=='__main__':unittest.main()
