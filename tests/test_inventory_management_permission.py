import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class InventoryStockEditPermissionTests(unittest.TestCase):
    def test_inventory_and_stock_exit_use_stock_edit_permission(self):
        text=(ROOT/'todo'/'screens'/'inventory.py').read_text(encoding='utf-8')
        self.assertNotIn('require_admin(conn)',text)
        self.assertEqual(text.count("require_permission('STOCK_EDIT', conn)"),2)

if __name__=='__main__':unittest.main()
