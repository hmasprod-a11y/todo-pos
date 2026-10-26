"""Checkout stock policy across multiple barcode/pack lines of one product."""
import importlib.util
import pathlib
import sys
import tempfile
import unittest
from decimal import Decimal

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'todo'))
import database
from services.security import current_user,hash_pin
from services.cash import open_session
from services import sales as candidate

class StockGuardTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory(prefix='todo-w01-')
        database.DB_PATH=pathlib.Path(self.folder.name)/'fixture.db'
        database.init_db()
        with database.connect() as c:
            self.user=c.execute("INSERT INTO users(username,display_name,pin_hash,role) VALUES(?,?,?,?)",('audit','Audit',hash_pin('fixture'),'admin')).lastrowid
            self.product=c.execute("INSERT INTO products(name,stock_qty,sale_price_cents,purchase_price_cents,allow_fraction) VALUES('A',10,1000,300,1)").lastrowid
            self.other=c.execute("INSERT INTO products(name,stock_qty,sale_price_cents,purchase_price_cents,allow_fraction) VALUES('B',10,2000,400,1)").lastrowid
            self.code_a=c.execute("INSERT INTO product_barcodes(product_id,barcode) VALUES(?,'0612345678901')",(self.product,)).lastrowid
            self.code_b=c.execute("INSERT INTO product_barcodes(product_id,barcode) VALUES(?,'SECOND')",(self.product,)).lastrowid
            c.execute("INSERT INTO product_barcodes(product_id,barcode) VALUES(?,'0612345678901')",(self.other,))
        self.token=current_user.set(self.user)
        self.session=open_session(self.user,0)
    def tearDown(self):
        current_user.reset(self.token);self.folder.cleanup()
    def policy(self,block,negative,tracked=True):
        for key,value in [('block_insufficient_stock',block),('allow_negative_stock',negative),('stock_management_enabled',tracked)]:database.set_setting(key,'1' if value else '0')
    def stock(self,p=None):
        with database.connect() as c:return c.execute('SELECT stock_qty FROM products WHERE id=?',(p or self.product,)).fetchone()[0]
    def snapshot(self):
        with database.connect() as c:
            return ([tuple(r) for r in c.execute('SELECT id,stock_qty FROM products ORDER BY id')],*[c.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in ['sales','sale_items','sale_payments','stock_movements']],database.get_setting('receipt_next_client_ticket','',c))
    def lines(self,a=6,b=6):
        return [dict(product_id=self.product,qty=a,barcode_id=self.code_a),dict(product_id=self.product,qty=b,barcode_id=self.code_b)]
    def sell(self,lines):
        return candidate.complete_sale(self.session,self.user,lines,'CASH',10000000)
    def test_block_overrides_negative_with_two_barcodes(self):
        self.policy(True,True);before=self.snapshot()
        with self.assertRaisesRegex(ValueError,'Stock insuffisant'):self.sell(self.lines())
        self.assertEqual(self.snapshot(),before)
    def test_policy_matrix(self):
        for block,negative in [(False,False),(False,True),(True,False),(True,True)]:
            with self.subTest(block=block,negative=negative):
                with database.connect() as c:c.execute('UPDATE products SET stock_qty=10 WHERE id=?',(self.product,))
                self.policy(block,negative)
                before=self.snapshot()
                if negative and not block:
                    self.sell(self.lines());self.assertEqual(self.stock(),-2)
                else:
                    with self.assertRaises(ValueError):self.sell(self.lines())
                    self.assertEqual(self.snapshot(),before)
    def test_exact_boundary(self):
        self.policy(True,True)
        r=self.sell(self.lines(4,6));self.assertEqual(self.stock(),0);self.assertEqual(r['total_cents'],10000)
    def test_fractional_boundary(self):
        self.policy(True,True)
        with database.connect() as c:c.execute('UPDATE products SET stock_qty=0.3 WHERE id=?',(self.product,))
        self.sell(self.lines(0.1,0.2));self.assertAlmostEqual(self.stock(),0,places=10)
    def test_fractional_excess(self):
        self.policy(True,True)
        with database.connect() as c:c.execute('UPDATE products SET stock_qty=0.3 WHERE id=?',(self.product,))
        before=self.snapshot()
        with self.assertRaises(ValueError):self.sell(self.lines(0.2,0.2))
        self.assertEqual(self.snapshot(),before)
    def test_shared_barcode_different_products_are_independent(self):
        self.policy(True,True)
        self.sell([dict(product_id=self.product,qty=8),dict(product_id=self.other,qty=8)])
        self.assertEqual([self.stock(self.product),self.stock(self.other)],[2,2])
    def test_all_rollback_before_any_write(self):
        self.policy(True,True);before=self.snapshot()
        with self.assertRaises(ValueError):self.sell([dict(product_id=self.other,qty=1),*self.lines()])
        self.assertEqual(self.snapshot(),before)
    def test_stock_tracking_disabled_preserves_stock(self):
        self.policy(True,False,tracked=False)
        r=self.sell(self.lines());self.assertEqual(self.stock(),10);self.assertFalse(r['stock_tracked'])
    def test_misc_product_does_not_consume_stock(self):
        self.policy(True,False)
        with database.connect() as c:p=c.execute("INSERT INTO products(name,is_misc,sale_price_cents,stock_qty) VALUES('Divers',1,0,0)").lastrowid
        self.sell([dict(product_id=p,qty=99,name='Divers test',unit_price_cents=50)])
        self.assertEqual(self.stock(p),0)
    def test_pack_lines_use_base_units(self):
        self.policy(True,True)
        with database.connect() as c:
            c.execute('UPDATE products SET stock_qty=30 WHERE id=?',(self.product,))
            pack=c.execute("INSERT INTO product_barcodes(product_id,barcode,qty_multiplier,price_override_cents) VALUES(?,'PACK6',6,4500)",(self.product,)).lastrowid
        before=self.snapshot()
        with self.assertRaises(ValueError):self.sell([dict(product_id=self.product,qty=18,barcode_id=pack),dict(product_id=self.product,qty=18,barcode_id=self.code_a)])
        self.assertEqual(self.snapshot(),before)
    def test_single_line_still_blocks(self):
        self.policy(True,True);before=self.snapshot()
        with self.assertRaises(ValueError):self.sell([dict(product_id=self.product,qty=11)])
        self.assertEqual(self.snapshot(),before)
    def test_zero_negative_nonfinite_quantities_rejected(self):
        self.policy(True,True)
        for quantity in [0,-1,float('nan'),float('inf')]:
            with self.subTest(quantity=quantity):
                before=self.snapshot()
                with self.assertRaises(ValueError):self.sell([dict(product_id=self.product,qty=quantity)])
                self.assertEqual(self.snapshot(),before)

if __name__=='__main__':unittest.main(verbosity=2)
