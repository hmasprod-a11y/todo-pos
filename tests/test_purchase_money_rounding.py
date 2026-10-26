"""Purchases must use the same decimal half-up policy as POS sales."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'todo'))
import database as db
from services.bootstrap import ensure_defaults
from services.security import current_user
from services.suppliers import save_supplier
from services.purchases import receive_purchase, create_purchase_order, list_purchase_orders
from services.supplier_returns import create_supplier_return, purchase_returnable_lines
from services.supplier_payments import supplier_credit_statement


class PurchaseMoneyRoundingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = db.DB_PATH
        db.DB_PATH = Path(self.tmp.name) / 'purchase.db'
        db.init_db(); ensure_defaults()
        with db.connect() as conn:
            uid = conn.execute('SELECT id FROM users ORDER BY id LIMIT 1').fetchone()[0]
            self.pid = conn.execute("INSERT INTO products(name,allow_fraction) VALUES('Fractional goods',1)").lastrowid
        self.token = current_user.set(uid)
        self.supplier = save_supplier('Supplier')

    def tearDown(self):
        current_user.reset(self.token)
        db.DB_PATH = self.old
        self.tmp.cleanup()

    def test_receipt_rounds_each_decimal_line_half_up_and_reconciles_debt(self):
        # 0.29 * 50 becomes 14.499999... with binary floats; 0.5 * 1
        # is an exact half, where Python's round would choose the even zero.
        lines = [dict(product_id=self.pid, qty=qty, unit_cost_cents=cost)
                 for qty, cost in ((.29, 50), (.5, 1), (.5, 5))]
        order = create_purchase_order(self.supplier, lines)
        self.assertEqual(next(r['total_cents'] for r in list_purchase_orders() if r['id']==order), 19)
        purchase, total = receive_purchase(self.supplier, 'HALF-UP', lines, order_id=order)
        self.assertEqual(total, 19)
        with db.connect() as conn:
            values = conn.execute('SELECT line_total_cents FROM purchase_items WHERE purchase_id=? ORDER BY id', (purchase,)).fetchall()
            self.assertEqual([r[0] for r in values], [15, 1, 3])
            self.assertEqual(conn.execute('SELECT total_cents FROM purchases WHERE id=?',(purchase,)).fetchone()[0], sum(r[0] for r in values))
        self.assertEqual(supplier_credit_statement()[0]['balance_cents'], 19)

    def test_partial_returns_round_cumulatively_and_preserve_final_residual(self):
        purchase, total = receive_purchase(self.supplier, 'PARTIAL', [dict(product_id=self.pid, qty=1, unit_cost_cents=1)])
        item = purchase_returnable_lines(purchase)[0]['purchase_item_id']
        first = create_supplier_return(purchase, [(item, .5)], 'First half')[1]
        second = create_supplier_return(purchase, [(item, .5)], 'Final half')[1]
        self.assertEqual((first, second), (1, 0))
        self.assertEqual(first + second, total)
        self.assertEqual(supplier_credit_statement(), [])
        with db.connect() as conn:
            self.assertEqual(conn.execute('SELECT stock_qty FROM products WHERE id=?',(self.pid,)).fetchone()[0], 0)
            self.assertEqual(conn.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            self.assertEqual(conn.execute('PRAGMA foreign_key_check').fetchall(), [])


if __name__ == '__main__':
    unittest.main()
