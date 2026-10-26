import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'todo'))
import database as db
from services.security import current_user,hash_pin
from services.catalog import link_product_variant,top_up_product,scan_barcode

class SharedStockEntryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.old=db.DB_PATH;db.DB_PATH=Path(self.tmp.name)/'db.sqlite';db.init_db()
        with db.connect() as c:
            self.uid=c.execute("INSERT INTO users(username,display_name,pin_hash,role) VALUES('admin','Admin',?,'admin')",(hash_pin('fixture'),)).lastrowid
            self.ids=[c.execute('INSERT INTO products(name,sale_price_cents,stock_qty,allow_fraction) VALUES(?,?,10,?)',(name,price,frac)).lastrowid for name,price,frac in [('Large',1000,0),('Small',800,1),('Other',700,0)]]
            c.executemany("INSERT INTO product_barcodes(product_id,barcode) VALUES(?,'001234')",[(pid,) for pid in self.ids])
        self.token=current_user.set(self.uid)
    def tearDown(self):current_user.reset(self.token);db.DB_PATH=self.old;self.tmp.cleanup()
    def test_top_up_only_changes_selected_stock_and_ledger(self):
        self.assertEqual(top_up_product(self.ids[0],3),13)
        with db.connect() as c:
            self.assertEqual([tuple(r) for r in c.execute('SELECT stock_qty,sale_price_cents FROM products ORDER BY id')],[(13,1000),(10,800),(10,700)])
            self.assertEqual(tuple(c.execute('SELECT product_id,qty_delta,old_qty,stock_after FROM stock_movements').fetchone()),(self.ids[0],3,10,13))
    def test_variant_links_identity_without_combining_stock(self):
        with db.connect() as c:link_product_variant(c,self.ids[1],self.ids[0]);link_product_variant(c,self.ids[2],self.ids[1])
        with db.connect() as c:self.assertEqual([r[0] for r in c.execute('SELECT parent_product_id FROM product_variants ORDER BY product_id')],[self.ids[0],self.ids[0]])
        self.assertEqual(len(scan_barcode('001234')),3)
    def test_cycle_is_rejected(self):
        with db.connect() as c:
            link_product_variant(c,self.ids[1],self.ids[0])
            with self.assertRaises(ValueError):link_product_variant(c,self.ids[0],self.ids[1])
    def test_topup_rejects_invalid_or_fractional_whole_product(self):
        for qty in (0,-1,float('nan'),float('inf'),1.5):
            with self.assertRaises(ValueError):top_up_product(self.ids[0],qty)
        self.assertEqual(top_up_product(self.ids[1],1.5),11.5)
    def test_manual_stock_policy_and_right_are_enforced(self):
        db.set_setting('manual_stock_edit_enabled','0')
        with self.assertRaises(PermissionError):top_up_product(self.ids[0],1)
        db.set_setting('manual_stock_edit_enabled','1')
        with db.connect() as c:c.execute("INSERT INTO user_permissions VALUES(?,'STOCK_EDIT',0)",(self.uid,));c.execute("UPDATE users SET role='cashier' WHERE id=?",(self.uid,))
        with self.assertRaises(PermissionError):top_up_product(self.ids[0],1)
