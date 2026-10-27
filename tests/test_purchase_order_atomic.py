import sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'todo'))
import database as db
from services.bootstrap import ensure_defaults
from services.security import current_user
from services.suppliers import save_supplier
from services.purchases import create_purchase_order,receive_purchase,purchase_order_lines,mark_purchase_order_received

class PurchaseOrderAtomicTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.old=db.DB_PATH;db.DB_PATH=Path(self.tmp.name)/'db.sqlite';db.init_db();ensure_defaults()
        with db.connect() as c:
            self.uid=c.execute('SELECT id FROM users LIMIT 1').fetchone()[0]
            self.pid=c.execute("INSERT INTO products(name) VALUES('Product')").lastrowid
        self.token=current_user.set(self.uid);self.sid=save_supplier('Supplier');self.lines=[dict(product_id=self.pid,qty=5,unit_cost_cents=500)];self.order=create_purchase_order(self.sid,self.lines)
    def tearDown(self):current_user.reset(self.token);db.DB_PATH=self.old;self.tmp.cleanup()
    def state(self):
        with db.connect() as c:return tuple(c.execute('SELECT stock_qty,(SELECT COUNT(*) FROM purchases),(SELECT COUNT(*) FROM stock_movements),(SELECT status FROM purchase_orders WHERE id=?) FROM products WHERE id=?',(self.order,self.pid)).fetchone())
    def test_full_receipt_is_linked_and_cannot_repeat_even_without_invoice(self):
        purchase,total=receive_purchase(self.sid,'',self.lines,order_id=self.order)
        self.assertEqual(self.state(),(5,1,1,'RECEIVED'))
        with db.connect() as c:self.assertEqual(c.execute('SELECT purchase_id FROM purchase_order_receipts WHERE order_id=?',(self.order,)).fetchone()[0],purchase)
        with self.assertRaises(ValueError):receive_purchase(self.sid,'',self.lines,order_id=self.order)
        self.assertEqual(self.state(),(5,1,1,'RECEIVED'))
    def test_failure_before_commit_rolls_back_receipt_and_order(self):
        with patch('services.purchases.audit',side_effect=RuntimeError('fixture')):
            with self.assertRaises(RuntimeError):receive_purchase(self.sid,'',self.lines,order_id=self.order)
        self.assertEqual(self.state(),(0,0,0,'OPEN'))
    def test_partial_receipt_keeps_remainder_open_until_final_delivery(self):
        first=[dict(product_id=self.pid,qty=3,unit_cost_cents=500)]
        second=[dict(product_id=self.pid,qty=2,unit_cost_cents=550)]
        first_id,total=receive_purchase(self.sid,'',first,order_id=self.order)
        self.assertEqual(total,1500)
        self.assertEqual(self.state(),(3,1,1,'OPEN'))
        self.assertEqual(purchase_order_lines(self.order)[0]['qty'],2)
        with self.assertRaises(ValueError):mark_purchase_order_received(self.order)
        second_id,total=receive_purchase(self.sid,'',second,order_id=self.order)
        self.assertEqual(total,1100)
        self.assertEqual(self.state(),(5,2,2,'RECEIVED'))
        self.assertEqual(purchase_order_lines(self.order),[])
        with db.connect() as c:
            links=c.execute('SELECT purchase_id FROM purchase_order_receipts WHERE order_id=? ORDER BY purchase_id',(self.order,)).fetchall()
            self.assertEqual([r[0] for r in links],[first_id,second_id])
        with self.assertRaises(ValueError):receive_purchase(self.sid,'',second,order_id=self.order)

    def test_partial_overdelivery_rolls_back_all_ledgers(self):
        receive_purchase(self.sid,'',[dict(product_id=self.pid,qty=3,unit_cost_cents=500)],order_id=self.order)
        before=self.state()
        with self.assertRaises(ValueError):
            receive_purchase(self.sid,'',[dict(product_id=self.pid,qty=3,unit_cost_cents=500)],order_id=self.order)
        self.assertEqual(self.state(),before)
        self.assertEqual(purchase_order_lines(self.order)[0]['qty'],2)

    def test_unordered_product_is_rejected_before_stock_writes(self):
        with db.connect() as c:other=c.execute("INSERT INTO products(name) VALUES('Unordered')").lastrowid
        with self.assertRaises(ValueError):
            receive_purchase(self.sid,'',[dict(product_id=other,qty=1,unit_cost_cents=500)],order_id=self.order)
        self.assertEqual(self.state(),(0,0,0,'OPEN'))

    def test_duplicate_product_order_lines_use_aggregate_remainder(self):
        order=create_purchase_order(self.sid,[dict(product_id=self.pid,qty=2,unit_cost_cents=500),dict(product_id=self.pid,qty=3,unit_cost_cents=550)])
        receive_purchase(self.sid,'',[dict(product_id=self.pid,qty=4,unit_cost_cents=525)],order_id=order)
        self.assertEqual([r['qty'] for r in purchase_order_lines(order)],[1])
        receive_purchase(self.sid,'',[dict(product_id=self.pid,qty=1,unit_cost_cents=550)],order_id=order)
        with db.connect() as c:self.assertEqual(c.execute('SELECT status FROM purchase_orders WHERE id=?',(order,)).fetchone()[0],'RECEIVED')
    def test_other_supplier_cannot_consume_order(self):
        other=save_supplier('Other')
        with self.assertRaises(ValueError):receive_purchase(other,'',self.lines,order_id=self.order)
        self.assertEqual(self.state(),(0,0,0,'OPEN'))
