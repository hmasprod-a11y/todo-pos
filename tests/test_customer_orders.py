import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'todo'))
import database
from services.bootstrap import ensure_defaults
from services.security import current_user
from services.clients import save_client
from services.cash import open_session
from services.customer_orders import create_customer_order,list_customer_orders,order_cart,set_customer_order_status
from services.sales import complete_sale

class CustomerOrderTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.old=database.DB_PATH;database.DB_PATH=Path(self.tmp.name)/'db.sqlite'
        database.init_db();ensure_defaults()
        with database.connect() as c:
            self.uid=c.execute("SELECT id FROM users").fetchone()[0]
            self.pid=c.execute("INSERT INTO products(name,sale_price_cents,stock_qty,active) VALUES('Order Product',1200,10,1)").lastrowid
        self.token=current_user.set(self.uid);self.cid=save_client('Order Client','0600')
    def tearDown(self):
        current_user.reset(self.token);database.DB_PATH=self.old;self.tmp.cleanup()
    def test_order_does_not_touch_stock_and_completes_with_sale(self):
        oid,total=create_customer_order(self.cid,[dict(product_id=self.pid,qty=2)],'Home','Call first')
        self.assertEqual(total,2400)
        with database.connect() as c:self.assertEqual(c.execute("SELECT stock_qty FROM products WHERE id=?",(self.pid,)).fetchone()[0],10)
        set_customer_order_status(oid,'READY');payload=order_cart(oid);self.assertEqual(payload['order']['status'],'READY')
        session=open_session(self.uid,0)
        result=complete_sale(session,self.uid,payload['cart'],'CASH',2400,client_id=self.cid,customer_order_id=oid)
        self.assertEqual(result['total_cents'],2400)
        row=list_customer_orders()[0];self.assertEqual(row['status'],'COMPLETED');self.assertEqual(row['sale_id'],result['id'])
        with database.connect() as c:self.assertEqual(c.execute("SELECT stock_qty FROM products WHERE id=?",(self.pid,)).fetchone()[0],8)
    def test_cancelled_order_cannot_load(self):
        oid,_=create_customer_order(self.cid,[dict(product_id=self.pid,qty=1)])
        set_customer_order_status(oid,'CANCELLED')
        with self.assertRaises(ValueError):order_cart(oid)

if __name__=='__main__':unittest.main()
