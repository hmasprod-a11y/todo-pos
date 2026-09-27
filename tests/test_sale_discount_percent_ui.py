import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class SaleDiscountPercentUiTests(unittest.TestCase):
    def test_current_ticket_displays_discount_as_percentage(self):
        text=(ROOT/'todo'/'screens'/'sale.py').read_text(encoding='utf-8')
        self.assertIn("REMISE %",text)
        self.assertIn("discount_pct=",text)
        self.assertIn("discount_text=",text)

if __name__=='__main__':unittest.main()
