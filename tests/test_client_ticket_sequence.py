import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'todo'))
import database
from services import backup
from services.bootstrap import ensure_defaults
from services.security import current_user
from services.cash import open_session
from services.sales import complete_sale

class ClientTicketSequenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.old=database.DB_PATH
        database.DB_PATH=Path(self.tmp.name)/'db.sqlite';backup.DB_PATH=database.DB_PATH;backup.BASE=Path(self.tmp.name)
        database.init_db();ensure_defaults()
        with database.connect() as c:
            self.uid=c.execute("SELECT id FROM users WHERE username='admin'").fetchone()[0]
            self.pid=c.execute("INSERT INTO products(name,sale_price_cents,stock_qty) VALUES('T',100,5)").lastrowid
        self.token=current_user.set(self.uid);self.session=open_session(self.uid,0)
    def tearDown(self):
        current_user.reset(self.token);database.DB_PATH=self.old;self.tmp.cleanup()
    def test_sequence_is_atomic_and_persisted(self):
        database.set_setting('receipt_next_client_ticket','40')
        a=complete_sale(self.session,self.uid,[dict(product_id=self.pid,qty=1,unit_price_cents=100)],'CASH',100)
        b=complete_sale(self.session,self.uid,[dict(product_id=self.pid,qty=1,unit_price_cents=100)],'CASH',100)
        self.assertEqual((a['client_ticket_no'],b['client_ticket_no']),(40,41))
        with database.connect() as c:
            rows=[r['client_ticket_no'] for r in c.execute("SELECT client_ticket_no FROM sales ORDER BY id")]
        self.assertEqual(rows,[40,41])

if __name__=='__main__':unittest.main()
