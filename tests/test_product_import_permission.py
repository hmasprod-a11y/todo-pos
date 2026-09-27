import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class ProductImportPermissionTests(unittest.TestCase):
    def test_product_import_uses_management_permission(self):
        text=(ROOT/'todo'/'screens'/'products.py').read_text(encoding='utf-8')
        self.assertNotIn('require_admin(c)',text)
        self.assertIn("require_permission('MANAGEMENT', c)",text)

if __name__=='__main__':unittest.main()
