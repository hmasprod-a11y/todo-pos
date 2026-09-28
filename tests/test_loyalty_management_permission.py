import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class LoyaltyManagementPermissionTests(unittest.TestCase):
    def test_manual_loyalty_adjustment_uses_management_permission(self):
        text=(ROOT/'todo'/'services'/'loyalty.py').read_text(encoding='utf-8')
        self.assertNotIn('require_admin(conn)',text)
        self.assertIn("require_permission('MANAGEMENT', conn)",text)

if __name__=='__main__':unittest.main()
