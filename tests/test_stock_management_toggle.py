import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'todo'))
import database
from services import backup
from services.bootstrap import ensure_defaults
from services.security import current_user
from services.cash import open_session
from services.sales import complete_sale,create_return

class StockManagementToggleTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.old=database.DB_PATH
        database.DB_PATH=Path(self.tmp.name)/'db.sqlite';backup.DB_PATH=database.DB_PATH;backup.BASE=Path(self.tmp.name)
        database.init_db();ensure_defaults()
        with database.connect() as c:
            self.uid=c.execute("SELECT id FROM users WHERE username='admin'").fetchone()[0]
            self.pid=c.execute("INSERT INTO products(name,sale_price_cents,stock_qty) VALUES('No Track',1000,2)").lastrowid
        self.token=current_user.set(self.uid);self.session=open_session(self.uid,0)
    def tearDown(self):
        current_user.reset(self.token);database.DB_PATH=self.old;self.tmp.cleanup()
    def test_sale_without_stock_management_does_not_touch_stock_or_block(self):
        database.set_setting('stock_management_enabled','0')
        database.set_setting('allow_negative_stock','0')
        database.set_setting('block_insufficient_stock','1')
        sale=complete_sale(self.session,self.uid,[dict(product_id=self.pid,qty=5,unit_price_cents=1000)],'CASH',5000)
        self.assertFalse(sale['stock_tracked'])
        with database.connect() as c:
            stock=c.execute("SELECT stock_qty FROM products WHERE id=?",(self.pid,)).fetchone()[0]
            item=c.execute("SELECT id FROM sale_items WHERE sale_id=?",(sale['id'],)).fetchone()[0]
        self.assertEqual(stock,2)
        database.set_setting('stock_management_enabled','1')
        create_return(sale['id'],self.session,self.uid,[(item,1)],'Retour test')
        with database.connect() as c:
            stock2=c.execute("SELECT stock_qty FROM products WHERE id=?",(self.pid,)).fetchone()[0]
        self.assertEqual(stock2,2)
    def test_tracked_sale_still_updates_stock(self):
        sale=complete_sale(self.session,self.uid,[dict(product_id=self.pid,qty=1,unit_price_cents=1000)],'CASH',1000)
        self.assertTrue(sale['stock_tracked'])
        with database.connect() as c:stock=c.execute("SELECT stock_qty FROM products WHERE id=?",(self.pid,)).fetchone()[0]
        self.assertEqual(stock,1)

if __name__=='__main__':unittest.main()
