import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class ExactCahierUiTests(unittest.TestCase):
    def test_statistics_uses_top_ten_articles(self):
        text=(ROOT/'todo'/'screens'/'statistics.py').read_text(encoding='utf-8')
        self.assertIn("top_products(10",text)
        self.assertIn("Top 10 articles",text)
    def test_stock_screen_shows_active_promotions_indicator(self):
        text=(ROOT/'todo'/'screens'/'stock.py').read_text(encoding='utf-8')
        self.assertIn("Promotions actives",text)
        self.assertIn("active_promotions",text)

if __name__=='__main__':unittest.main()
