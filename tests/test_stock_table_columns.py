import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'todo'))
import database
from services.inventory import stock_products

class StockTableColumnsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.old=database.DB_PATH
        database.DB_PATH=Path(self.tmp.name)/'db.sqlite';database.init_db()
        with database.connect() as c:
            cat=c.execute("INSERT INTO categories(name) VALUES('Boissons')").lastrowid
            self.pid=c.execute("INSERT INTO products(sku,name,category_id,purchase_price_cents,sale_price_cents,stock_qty,alert_qty) VALUES('SKU-1','Eau',?,250,400,7,2)",(cat,)).lastrowid
    def tearDown(self):
        database.DB_PATH=self.old;self.tmp.cleanup()
    def test_stock_rows_expose_cahier_columns(self):
        row=stock_products('Eau')[0]
        self.assertEqual(row['code'],'SKU-1')
        self.assertEqual(row['families'],'Boissons')
        self.assertEqual(row['purchase_price_cents'],250)
        self.assertEqual(row['sale_price_cents'],400)
        self.assertEqual(row['stock_qty'],7)

if __name__=='__main__':unittest.main()
