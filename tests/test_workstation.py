import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'todo'))
import database
from services import backup
from services.bootstrap import ensure_defaults
from services.security import current_user
from services.cash import open_session
from services.sales import complete_sale
from services.receipts import build_receipt

class WorkstationTraceabilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.old=database.DB_PATH
        database.DB_PATH=Path(self.tmp.name)/'db.sqlite';backup.DB_PATH=database.DB_PATH;backup.BASE=Path(self.tmp.name)
        database.init_db();ensure_defaults()
        with database.connect() as c:
            self.uid=c.execute("SELECT id FROM users WHERE username='admin'").fetchone()[0]
            self.pid=c.execute("INSERT INTO products(name,sale_price_cents,stock_qty) VALUES('Poste Test',500,5)").lastrowid
        self.token=current_user.set(self.uid)
    def tearDown(self):
        current_user.reset(self.token);database.DB_PATH=self.old;self.tmp.cleanup()
    def test_sale_keeps_workstation_from_open_cash_session(self):
        database.set_setting('workstation_code','02')
        session=open_session(self.uid,0)
        database.set_setting('workstation_code','03')
        sale=complete_sale(session,self.uid,[dict(product_id=self.pid,qty=1,unit_price_cents=500)],'CASH',500)
        self.assertEqual(sale['workstation_code'],'02')
        with database.connect() as c:
            cash=c.execute("SELECT workstation_code FROM cash_sessions WHERE id=?",(session,)).fetchone()[0]
            sold=c.execute("SELECT workstation_code FROM sales WHERE id=?",(sale['id'],)).fetchone()[0]
        self.assertEqual((cash,sold),('02','02'))
        self.assertIn('Poste: 02',build_receipt(sale['id']))
    def test_invalid_workstation_is_rejected_when_opening_cash(self):
        database.set_setting('workstation_code','BAD SPACE')
        with self.assertRaises(ValueError):open_session(self.uid,0)

if __name__=='__main__':unittest.main()
