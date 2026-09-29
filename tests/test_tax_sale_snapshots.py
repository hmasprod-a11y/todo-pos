import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "todo"))

import database as db
from services.bootstrap import ensure_defaults
from services.cash import open_session
from services.sales import complete_sale
from services.receipts import build_receipt
from services.security import current_user


class TaxSaleSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.previous = db.DB_PATH
        db.DB_PATH = Path(self.temp.name) / "todo.db"
        db.init_db()
        ensure_defaults()
        with db.connect() as conn:
            self.user_id = conn.execute("SELECT id FROM users WHERE username='admin'").fetchone()[0]
        current_user.set(self.user_id)
        self.session_id = open_session(self.user_id, 0)

    def tearDown(self):
        current_user.set(None)
        db.DB_PATH = self.previous
        self.temp.cleanup()

    def add_product(self, name, rate, included):
        with db.connect() as conn:
            return conn.execute(
                "INSERT INTO products(name,sale_price_cents,tax_rate_basis_points,tax_included,tax_class) VALUES(?,?,?,?,?)",
                (name, 1000, rate, included, 'REDUCED'),
            ).lastrowid

    def test_included_and_exclusive_tax_are_snapshotted_and_payable(self):
        included = self.add_product("Included", 2000, 1)
        exclusive = self.add_product("Exclusive", 2000, 0)
        first = complete_sale(self.session_id, self.user_id, [dict(product_id=included, qty=1, unit_price_cents=1200)], "CASH", 1200)
        second = complete_sale(self.session_id, self.user_id, [dict(product_id=exclusive, qty=1, unit_price_cents=1000)], "CASH", 1200)
        self.assertEqual((first["total_cents"], first["tax_total_cents"]), (1200, 200))
        self.assertEqual((second["total_cents"], second["tax_total_cents"]), (1200, 200))
        with db.connect() as conn:
            one = conn.execute("SELECT tax_net_cents,tax_amount_cents,tax_gross_cents,net_total_cents,tax_class FROM sale_items WHERE sale_id=?", (first["id"],)).fetchone()
            two = conn.execute("SELECT tax_net_cents,tax_amount_cents,tax_gross_cents,net_total_cents FROM sale_items WHERE sale_id=?", (second["id"],)).fetchone()
            sale = conn.execute("SELECT country_code,tax_label_snapshot,tax_total_cents FROM sales WHERE id=?", (second["id"],)).fetchone()
        self.assertEqual(tuple(one), (1000, 200, 1200, 1200, 'REDUCED'))
        self.assertEqual(tuple(two), (1000, 200, 1200, 1200, 'REDUCED'))
        self.assertEqual(tuple(sale), ("MA", "Tax", 200))

    def test_receipt_uses_sale_tax_snapshot_breakdown(self):
        product = self.add_product("TVA product", 2000, 1)
        sale = complete_sale(self.session_id, self.user_id, [dict(product_id=product, qty=1, unit_price_cents=1200)], "CASH", 1200)
        with db.connect() as conn:
            conn.execute("UPDATE sales SET tax_label_snapshot=? WHERE id=?", ("TVA", sale["id"]))
            conn.commit()
        receipt = build_receipt(sale["id"])
        self.assertIn("TVA 20%: 2.00 DH", receipt)
        self.assertIn("TOTAL: 12.00 DH", receipt)

    def test_english_receipt_template_is_available(self):
        db.set_setting('receipt_template', 'EN_3C')
        product = self.add_product('English product', 0, 1)
        sale = complete_sale(self.session_id, self.user_id, [dict(product_id=product, qty=1, unit_price_cents=1000)], 'CASH', 1000)
        receipt = build_receipt(sale['id'])
        self.assertIn('Receipt:', receipt)
        self.assertIn('Cashier:', receipt)
        self.assertIn('Change:', receipt)


if __name__ == "__main__":
    unittest.main()
