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

    def test_sale_photo_visibility_is_explicit_and_barcode_independent(self):
        products=(ROOT/'todo'/'screens'/'products.py').read_text(encoding='utf-8')
        catalog=(ROOT/'todo'/'services'/'catalog.py').read_text(encoding='utf-8')
        database=(ROOT/'todo'/'database.py').read_text(encoding='utf-8')
        self.assertIn('Afficher dans les photos de vente',products)
        self.assertIn('show_in_sale_photos',products)
        self.assertIn("p.show_in_sale_photos=1",catalog)
        self.assertNotIn("NOT EXISTS(SELECT 1 FROM product_barcodes",catalog)
        self.assertIn("show_in_sale_photos INTEGER NOT NULL DEFAULT 0",database)

    def test_product_editor_exposes_persisted_tax_settings(self):
        text=(ROOT/'todo'/'screens'/'products.py').read_text(encoding='utf-8')
        self.assertIn('new_product_tax_defaults',text)
        self.assertIn('Taxe (%)',text)
        self.assertIn('tax_rate_basis_points',text)
        self.assertIn('tax_included',text)
        self.assertIn('tax_class',text)
        self.assertIn("'STANDARD','REDUCED','ZERO'",text)

if __name__=='__main__':unittest.main()
