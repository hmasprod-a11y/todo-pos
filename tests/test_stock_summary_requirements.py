import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'todo'))
import database
from services.inventory import stock_summary

class StockSummaryRequirementTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.old=database.DB_PATH
        database.DB_PATH=Path(self.tmp.name)/'db.sqlite';database.init_db()
        with database.connect() as c:
            p1=c.execute("INSERT INTO products(name,purchase_price_cents,sale_price_cents,stock_qty,alert_qty) VALUES('A',100,200,5,2)").lastrowid
            p2=c.execute("INSERT INTO products(name,purchase_price_cents,sale_price_cents,stock_qty,alert_qty) VALUES('B',300,500,-1,0)").lastrowid
            c.execute("INSERT INTO quantity_prices(product_id,min_qty,unit_price_cents,active) VALUES(?,?,?,1)",(p1,2,150))
            c.execute("INSERT INTO quantity_prices(product_id,min_qty,unit_price_cents,active) VALUES(?,?,?,0)",(p2,2,400))
    def tearDown(self):
        database.DB_PATH=self.old;self.tmp.cleanup()
    def test_stock_footer_includes_active_promotions_and_both_values(self):
        s=stock_summary()
        self.assertEqual(s['articles'],2)
        self.assertEqual(s['alerts'],1)
        self.assertEqual(s['negative'],1)
        self.assertEqual(s['active_promotions'],1)
        self.assertEqual(s['purchase_value_cents'],200)
        self.assertEqual(s['sale_value_cents'],500)

if __name__=='__main__':unittest.main()
