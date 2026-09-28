import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class CustomerOrderQuotationPermissionTests(unittest.TestCase):
    def test_customer_orders_use_management_permission(self):
        text=(ROOT/'todo'/'services'/'customer_orders.py').read_text(encoding='utf-8')
        self.assertNotIn('require_admin(conn)',text)
        self.assertEqual(text.count("require_permission('MANAGEMENT', conn)"),2)

    def test_quotations_use_management_permission(self):
        text=(ROOT/'todo'/'services'/'quotations.py').read_text(encoding='utf-8')
        self.assertNotIn('require_admin(conn)',text)
        self.assertEqual(text.count("require_permission('MANAGEMENT', conn)"),2)

if __name__=='__main__':unittest.main()
