import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'todo'))
import database
from services import backup
from services.bootstrap import ensure_defaults
from services.security import current_user
from services.cash import open_session
from services.sales import complete_sale
from services.inventory import apply_stock_movement
from services.payment_methods import save_payment_method,set_payment_method_active,list_payment_methods,payment_icon

class PaymentMethodTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.old=database.DB_PATH
        database.DB_PATH=Path(self.tmp.name)/'db.sqlite';backup.DB_PATH=database.DB_PATH;backup.BASE=Path(self.tmp.name)
        database.init_db();ensure_defaults()
        with database.connect() as c:
            self.uid=c.execute("SELECT id FROM users WHERE username='admin'").fetchone()[0]
            self.pid=c.execute("INSERT INTO products(name,sale_price_cents,purchase_price_cents) VALUES('Pay Item',1000,300)").lastrowid
        self.token=current_user.set(self.uid)
        with database.connect() as c:
            apply_stock_movement(c,self.pid,5,'OPENING',300,'product',self.pid,'Initial')
        self.session=open_session(self.uid,0)
    def tearDown(self):
        current_user.reset(self.token);database.DB_PATH=self.old;self.tmp.cleanup()
    def test_custom_method_is_real_checkout_method(self):
        mid=save_payment_method('CHEQUE','Chèque','شيك','📝')
        cheque=next(r for r in list_payment_methods(True) if r['code']=='CHEQUE')
        self.assertEqual(cheque['icon'],'📝')
        self.assertEqual(payment_icon('CHEQUE'),'📝')
        result=complete_sale(self.session,self.uid,[dict(product_id=self.pid,qty=1,unit_price_cents=1000)],'CHEQUE',0)
        with database.connect() as c:
            row=c.execute("SELECT payment_method,amount_cents FROM sale_payments WHERE sale_id=?",(result['id'],)).fetchone()
        self.assertEqual((row['payment_method'],row['amount_cents']),('CHEQUE',1000))
        save_payment_method('CHEQUE','Chèque bancaire','شيك بنكي','🏦',method_id=mid)
        self.assertEqual(payment_icon('CHEQUE'),'🏦')
        set_payment_method_active(mid,False)
        with self.assertRaises(ValueError):
            complete_sale(self.session,self.uid,[dict(product_id=self.pid,qty=1,unit_price_cents=1000)],'CHEQUE',0)

if __name__=='__main__':unittest.main()
