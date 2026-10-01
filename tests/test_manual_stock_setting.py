import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'todo'))
import database
from services import backup
from services.bootstrap import ensure_defaults
from services.security import current_user
from services.inventory import apply_stock_movement

class ManualStockSettingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.old=database.DB_PATH
        database.DB_PATH=Path(self.tmp.name)/'db.sqlite';backup.DB_PATH=database.DB_PATH;backup.BASE=Path(self.tmp.name)
        database.init_db();ensure_defaults()
        with database.connect() as c:
            self.uid=c.execute("SELECT id FROM users WHERE username='admin'").fetchone()[0]
            self.pid=c.execute("INSERT INTO products(name,stock_qty) VALUES('Stock Toggle',5)").lastrowid
        self.token=current_user.set(self.uid)
    def tearDown(self):
        current_user.reset(self.token);database.DB_PATH=self.old;self.tmp.cleanup()
    def test_manual_adjustments_can_be_disabled_without_blocking_operational_movements(self):
        database.set_setting('manual_stock_edit_enabled','0')
        with database.connect() as c:
            with self.assertRaises(PermissionError):
                apply_stock_movement(c,self.pid,2,'ADJUSTMENT',note='manual')
            with self.assertRaises(PermissionError):
                apply_stock_movement(c,self.pid,1,'INVENTORY',note='count')
            apply_stock_movement(c,self.pid,-1,'OUT',note='casse')
            stock=c.execute("SELECT stock_qty FROM products WHERE id=?",(self.pid,)).fetchone()[0]
        self.assertEqual(stock,4)
    def test_manual_adjustment_default_stays_enabled(self):
        with database.connect() as c:
            apply_stock_movement(c,self.pid,2,'ADJUSTMENT',note='correction')
            stock=c.execute("SELECT stock_qty FROM products WHERE id=?",(self.pid,)).fetchone()[0]
        self.assertEqual(stock,7)

    def test_opening_and_adjustment_movements_rebuild_stock_with_audit_context(self):
        with database.connect() as c:
            pid=c.execute("INSERT INTO products(name,stock_qty) VALUES('Ledger Product',0)").lastrowid
            apply_stock_movement(c,pid,5,'OPENING',note='opening count')
            apply_stock_movement(c,pid,-1,'ADJUSTMENT',note='cycle count')
            rows=c.execute("SELECT movement_type,qty_delta,user_id,note FROM stock_movements WHERE product_id=? ORDER BY id",(pid,)).fetchall()
            stock=c.execute("SELECT stock_qty FROM products WHERE id=?",(pid,)).fetchone()[0]
        self.assertEqual([(r['movement_type'],r['qty_delta']) for r in rows],[('OPENING',5),('ADJUSTMENT',-1)])
        self.assertEqual(sum(r['qty_delta'] for r in rows),stock)
        self.assertEqual(stock,4)
        self.assertTrue(all(r['user_id']==self.uid and r['note'] for r in rows))

if __name__=='__main__':unittest.main()
