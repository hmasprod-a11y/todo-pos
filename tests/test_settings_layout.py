import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class SettingsLayoutTests(unittest.TestCase):
    def test_shop_and_sale_controls_do_not_overlap_on_row_16(self):
        text=(ROOT/'todo'/'screens'/'settings.py').read_text(encoding='utf-8')
        start=text.index("f=ttk.LabelFrame(self,text=self.tr('Magasin et vente'")
        end=text.index("pg=ttk.LabelFrame",start)
        block=text[start:end]
        self.assertEqual(block.count("grid(row=16"),1)
        for row in range(2,17):
            self.assertIn(f"grid(row={row}",block)

if __name__=='__main__':unittest.main()
