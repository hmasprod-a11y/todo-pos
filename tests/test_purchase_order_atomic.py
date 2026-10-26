import sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'todo'))
import database as db
from services.bootstrap import ensure_defaults
from services.security import current_user
from services.suppliers import save_supplier
from services.purchases import create_purchase_order,receive_purchase

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
    def test_partial_receipt_is_not_silently_marked_complete(self):
        self.lines[0]['qty']=3
        with self.assertRaises(ValueError):receive_purchase(self.sid,'',self.lines,order_id=self.order)
        self.assertEqual(self.state(),(0,0,0,'OPEN'))
    def test_other_supplier_cannot_consume_order(self):
        other=save_supplier('Other')
        with self.assertRaises(ValueError):receive_purchase(other,'',self.lines,order_id=self.order)
        self.assertEqual(self.state(),(0,0,0,'OPEN'))
