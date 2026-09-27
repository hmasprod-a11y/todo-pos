import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'todo'))
import database
from services.bootstrap import ensure_defaults
from services.security import current_user
from services.loyalty import client_points,adjust_points,loyalty_history,award_sale_points,redeem_points
from database import set_setting

class LoyaltyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.old=database.DB_PATH;database.DB_PATH=Path(self.tmp.name)/'db.sqlite'
        database.init_db();ensure_defaults()
        with database.connect() as c:
            self.uid=c.execute("SELECT id FROM users").fetchone()[0]
            self.cid=c.execute("INSERT INTO clients(name,phone) VALUES('Loyal Client','0600')").lastrowid
        self.token=current_user.set(self.uid)
    def tearDown(self):
        current_user.reset(self.token);database.DB_PATH=self.old;self.tmp.cleanup()
    def test_manual_points_and_history(self):
        adjust_points(self.cid,20,'Welcome');self.assertEqual(client_points(self.cid),20)
        adjust_points(self.cid,-5,'Correction');self.assertEqual(client_points(self.cid),15)
        self.assertEqual(len(loyalty_history(self.cid)),2)
        with self.assertRaises(ValueError):adjust_points(self.cid,-99,'Too much')
    def test_sale_award_is_idempotent_and_redeem_value(self):
        set_setting('loyalty_enabled','1');set_setting('loyalty_earn_every_cents','1000');set_setting('loyalty_point_value_cents','50')
        with database.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            self.assertEqual(award_sale_points(c,self.cid,123,2500,self.uid),2)
            self.assertEqual(award_sale_points(c,self.cid,123,2500,self.uid),0)
            c.commit()
        self.assertEqual(client_points(self.cid),2)
        with database.connect() as c:
            c.execute('BEGIN IMMEDIATE');self.assertEqual(redeem_points(c,self.cid,1,124,self.uid),50);c.commit()
        self.assertEqual(client_points(self.cid),1)

if __name__=='__main__':unittest.main()
