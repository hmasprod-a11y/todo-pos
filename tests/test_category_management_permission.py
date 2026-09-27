import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class CategoryManagementPermissionTests(unittest.TestCase):
    def test_product_category_creation_uses_management_permission(self):
        text=(ROOT/'todo'/'screens'/'products.py').read_text(encoding='utf-8')
        start=text.index('    def add_category(self):')
        end=text.index('    def refresh_categories',start)
        block=text[start:end]
        self.assertIn("require_permission('MANAGEMENT', conn)",block)
        self.assertNotIn('require_admin(conn)',block)

    def test_category_editor_save_uses_management_permission(self):
        text=(ROOT/'todo'/'screens'/'settings.py').read_text(encoding='utf-8')
        start=text.index('class CategoryEditor')
        end=text.index('class SettingsFrame',start)
        block=text[start:end]
        self.assertIn("require_permission('MANAGEMENT', conn)",block)
        self.assertNotIn('require_admin(conn)',block)

if __name__=='__main__':unittest.main()
