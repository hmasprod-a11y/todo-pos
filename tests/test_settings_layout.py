import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class SettingsLayoutTests(unittest.TestCase):
    def test_shop_settings_are_grouped_without_duplicate_primary_controls(self):
        text=(ROOT/'todo'/'screens'/'settings.py').read_text(encoding='utf-8')
        start=text.index("shop=ttk.LabelFrame(body,text=self.tr('Magasin et localisation'")
        end=text.index("ttk.Separator(body).pack",start)
        block=text[start:end]
        for section in ('Magasin et localisation','Règles de stock','Options de vente et ticket','Windows et catalogue'):
            self.assertIn(section,block)
        for control in ('self.country_combo=','variable=self.stock_management_enabled','variable=self.credit_enabled','variable=self.start_with_windows'):
            self.assertEqual(block.count(control),1,control)
        self.assertEqual(block.count("ttk.Button(body,text=self.tr('Enregistrer'"),1)

if __name__=='__main__':unittest.main()
