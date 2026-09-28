import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class PartyManagementPermissionTests(unittest.TestCase):
    def test_supplier_save_uses_management_permission(self):
        text=(ROOT/'todo'/'services'/'suppliers.py').read_text(encoding='utf-8')
        self.assertIn("require_permission('MANAGEMENT', conn)",text)
        self.assertNotIn('require_admin(conn)',text)

    def test_client_master_data_uses_management_but_payment_stays_admin(self):
        text=(ROOT/'todo'/'services'/'clients.py').read_text(encoding='utf-8')
        self.assertEqual(text.count("require_permission('MANAGEMENT', conn)"),2)
        self.assertIn('uid=require_admin(conn)',text)

if __name__=='__main__':unittest.main()
