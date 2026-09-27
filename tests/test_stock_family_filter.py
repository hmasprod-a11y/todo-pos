import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'todo'))
import database
from services.inventory import stock_products

class StockFamilyFilterTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.old=database.DB_PATH
        database.DB_PATH=Path(self.tmp.name)/'db.sqlite';database.init_db()
        with database.connect() as c:
            self.cat1=c.execute("INSERT INTO categories(name) VALUES('Boissons')").lastrowid
            self.cat2=c.execute("INSERT INTO categories(name) VALUES('Snacks')").lastrowid
            self.p1=c.execute("INSERT INTO products(name,category_id,stock_qty,alert_qty) VALUES('Eau',?,5,2)",(self.cat1,)).lastrowid
            self.p2=c.execute("INSERT INTO products(name,category_id,stock_qty,alert_qty) VALUES('Chips',?,-1,0)",(self.cat2,)).lastrowid
            c.execute("INSERT OR IGNORE INTO product_categories(product_id,category_id) VALUES(?,?)",(self.p1,self.cat2))
    def tearDown(self):
        database.DB_PATH=self.old;self.tmp.cleanup()
    def test_family_filter_honors_secondary_category(self):
        names=[r['name'] for r in stock_products('',self.cat2,'all')]
        self.assertEqual(names,['Chips','Eau'])
    def test_family_filter_combines_with_stock_state(self):
        names=[r['name'] for r in stock_products('',self.cat2,'negative')]
        self.assertEqual(names,['Chips'])
        alerts=[r['name'] for r in stock_products('',self.cat1,'alerts')]
        self.assertEqual(alerts,[])

if __name__=='__main__':unittest.main()
