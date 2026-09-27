import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'todo'))
import database
from services.bootstrap import ensure_defaults
from services.security import current_user
from services.clients import save_client
from services.cash import open_session
from services.quotations import create_quotation,list_quotations,quotation_cart,cancel_quotation
from services.sales import complete_sale

class QuotationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.old=database.DB_PATH;database.DB_PATH=Path(self.tmp.name)/'db.sqlite'
        database.init_db();ensure_defaults()
        with database.connect() as c:
            self.uid=c.execute("SELECT id FROM users").fetchone()[0]
            self.pid=c.execute("INSERT INTO products(name,sale_price_cents,stock_qty,active) VALUES('Quote Product',1500,10,1)").lastrowid
        self.token=current_user.set(self.uid);self.cid=save_client('Quote Client','0600')
    def tearDown(self):
        current_user.reset(self.token);database.DB_PATH=self.old;self.tmp.cleanup()
    def test_quotation_converts_to_sale_without_pre_touching_stock(self):
        qid,total=create_quotation([dict(product_id=self.pid,qty=2,unit_price_cents=1400)],self.cid,'2030-12-31')
        self.assertEqual(total,2800)
        with database.connect() as c:self.assertEqual(c.execute("SELECT stock_qty FROM products WHERE id=?",(self.pid,)).fetchone()[0],10)
        payload=quotation_cart(qid);session=open_session(self.uid,0)
        result=complete_sale(session,self.uid,payload['cart'],'CASH',2800,client_id=self.cid,quotation_id=qid)
        self.assertEqual(result['total_cents'],2800)
        row=list_quotations()[0];self.assertEqual(row['status'],'CONVERTED');self.assertEqual(row['sale_id'],result['id'])
        with database.connect() as c:self.assertEqual(c.execute("SELECT stock_qty FROM products WHERE id=?",(self.pid,)).fetchone()[0],8)
    def test_cancelled_quotation_cannot_convert(self):
        qid,_=create_quotation([dict(product_id=self.pid,qty=1)],self.cid)
        cancel_quotation(qid)
        with self.assertRaises(ValueError):quotation_cart(qid)

if __name__=='__main__':unittest.main()
