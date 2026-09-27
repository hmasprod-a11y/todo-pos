import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'todo'))
import database
from services.bootstrap import ensure_defaults
from services.security import current_user
from services.suppliers import save_supplier
from services.purchases import receive_purchase
from services.supplier_returns import create_supplier_return,purchase_returnable_lines,list_supplier_returns
from services.supplier_payments import supplier_credit_statement

class SupplierReturnTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.old=database.DB_PATH;database.DB_PATH=Path(self.tmp.name)/'db.sqlite'
        database.init_db();ensure_defaults()
        with database.connect() as c:self.uid=c.execute("SELECT id FROM users").fetchone()[0]
        self.token=current_user.set(self.uid)
        self.sid=save_supplier('Return Supplier')
        with database.connect() as c:self.pid=c.execute("INSERT INTO products(name,purchase_price_cents,stock_qty,active) VALUES('Return Item',500,2,1)").lastrowid
        self.purchase_id,_=receive_purchase(self.sid,'INV-R1',[dict(product_id=self.pid,qty=5,unit_cost_cents=500)])
    def tearDown(self):
        current_user.reset(self.token);database.DB_PATH=self.old;self.tmp.cleanup()
    def test_supplier_return_reduces_stock_and_supplier_debt(self):
        line=purchase_returnable_lines(self.purchase_id)[0]
        rid,total=create_supplier_return(self.purchase_id,[(line['purchase_item_id'],2)],'Damaged')
        self.assertEqual(total,1000);self.assertEqual(list_supplier_returns()[0]['id'],rid)
        with database.connect() as c:self.assertEqual(c.execute("SELECT stock_qty FROM products WHERE id=?",(self.pid,)).fetchone()[0],5)
        statement=supplier_credit_statement();self.assertEqual(statement[0]['balance_cents'],1500)
    def test_cannot_return_more_than_purchase_remainder(self):
        line=purchase_returnable_lines(self.purchase_id)[0]
        create_supplier_return(self.purchase_id,[(line['purchase_item_id'],4)],'Bad batch')
        with self.assertRaises(ValueError):create_supplier_return(self.purchase_id,[(line['purchase_item_id'],2)],'Too much')

if __name__=='__main__':unittest.main()
