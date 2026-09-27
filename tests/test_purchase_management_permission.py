import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class PurchaseManagementPermissionTests(unittest.TestCase):
    def test_purchase_workflows_use_management_permission(self):
        text=(ROOT/'todo'/'services'/'purchases.py').read_text(encoding='utf-8')
        self.assertNotIn('require_admin(conn)',text)
        self.assertEqual(text.count("require_permission('MANAGEMENT', conn)"),4)

if __name__=='__main__':unittest.main()
