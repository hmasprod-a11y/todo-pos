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

if __name__=='__main__':unittest.main()
