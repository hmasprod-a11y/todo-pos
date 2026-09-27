import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'todo'))
import database
from services.bootstrap import ensure_defaults
from services.security import current_user
from services.catalog import deactivate_product,search_products

class ProductDeactivationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.old=database.DB_PATH
        database.DB_PATH=Path(self.tmp.name)/'db.sqlite';database.init_db();ensure_defaults()
        with database.connect() as c:
            self.uid=c.execute("SELECT id FROM users WHERE username='admin'").fetchone()[0]
            self.pid=c.execute("INSERT INTO products(name,sale_price_cents,stock_qty) VALUES('A désactiver',500,3)").lastrowid
        self.token=current_user.set(self.uid)
    def tearDown(self):
        current_user.reset(self.token);database.DB_PATH=self.old;self.tmp.cleanup()
    def test_soft_deactivation_preserves_record_and_hides_catalog(self):
        deactivate_product(self.pid)
        with database.connect() as c:
            row=c.execute("SELECT active,name FROM products WHERE id=?",(self.pid,)).fetchone()
            audit=c.execute("SELECT action FROM audit_log WHERE action='PRODUCT_DEACTIVATE' AND document=?",(str(self.pid),)).fetchone()
        self.assertEqual(row['active'],0)
        self.assertEqual(row['name'],'A désactiver')
        self.assertIsNotNone(audit)
        self.assertEqual(search_products('A désactiver'),[])
    def test_cannot_deactivate_twice(self):
        deactivate_product(self.pid)
        with self.assertRaises(ValueError):deactivate_product(self.pid)

if __name__=='__main__':unittest.main()
