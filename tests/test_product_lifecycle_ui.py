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
    def test_product_editor_save_uses_management_permission(self):
        text=(ROOT/'todo'/'screens'/'products.py').read_text(encoding='utf-8')
        start=text.index('    def save(self):')
        end=text.index('\nclass ProductsFrame',start)
        save=text[start:end]
        self.assertIn("require_permission('MANAGEMENT', c)",save)
        self.assertNotIn('require_admin(c)',save)
    def test_duplicate_barcode_warning_distinguishes_same_vs_different_product(self):
        text=(ROOT/'todo'/'screens'/'products.py').read_text(encoding='utf-8')
        self.assertIn('Barcode déjà utilisé',text)
        self.assertIn('MÊME article',text)
        self.assertIn('AUTRE article, format, taille ou marque',text)
        self.assertIn('AND p.id<>?',text)
        self.assertIn('current_codes',text)

if __name__=='__main__':unittest.main()
