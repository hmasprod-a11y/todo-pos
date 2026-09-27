import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'todo'))
import database
from services.bootstrap import ensure_defaults
from services.security import current_user
from services.cash import open_session,session_totals

class CashCountPaymentSplitTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.old=database.DB_PATH
        database.DB_PATH=Path(self.tmp.name)/'db.sqlite';database.init_db();ensure_defaults()
        with database.connect() as c:self.uid=c.execute("SELECT id FROM users WHERE username='admin'").fetchone()[0]
        self.token=current_user.set(self.uid)
        self.sid=open_session(self.uid,1000)
        with database.connect() as c:
            c.execute("INSERT INTO sales(sale_no,session_id,cashier_user_id,total_cents,payment_method,paid_cents,status) VALUES('S1',?,?,3000,'MIXED',3000,'COMPLETED')",(self.sid,self.uid))
            sale_id=c.execute("SELECT last_insert_rowid()").fetchone()[0]
            c.execute("INSERT INTO sale_payments(sale_id,payment_method,amount_cents) VALUES(?,?,?)",(sale_id,'CASH',1200))
            c.execute("INSERT INTO sale_payments(sale_id,payment_method,amount_cents) VALUES(?,?,?)",(sale_id,'CARD',1800))
    def tearDown(self):
        current_user.reset(self.token);database.DB_PATH=self.old;self.tmp.cleanup()
    def test_session_totals_split_cash_and_card(self):
        with database.connect() as c:t=session_totals(c,self.sid)
        self.assertEqual(t['cash_sales'],1200)
        self.assertEqual(t['card_sales'],1800)

if __name__=='__main__':unittest.main()
