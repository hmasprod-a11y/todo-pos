import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class CashCountUiTests(unittest.TestCase):
    def test_cash_count_shows_cash_and_card(self):
        text=(ROOT/'todo'/'screens'/'cashdesk.py').read_text(encoding='utf-8')
        self.assertIn('Ventes cash',text)
        self.assertIn('Ventes carte',text)
if __name__=='__main__':unittest.main()
