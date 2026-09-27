import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'todo'))
import database
from services.bootstrap import ensure_defaults
from services.security import current_user
from services.cash import open_session,close_session

class CashClosureTraceabilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.old=database.DB_PATH
        database.DB_PATH=Path(self.tmp.name)/'db.sqlite';database.init_db();ensure_defaults()
        with database.connect() as c:
            self.uid=c.execute("SELECT id FROM users WHERE username='admin'").fetchone()[0]
        self.token=current_user.set(self.uid)
    def tearDown(self):
        current_user.reset(self.token);database.DB_PATH=self.old;self.tmp.cleanup()
    def test_closure_records_user_and_timestamp(self):
        sid=open_session(self.uid,1000)
        close_session(sid,1000)
        with database.connect() as c:
            row=c.execute("SELECT closed_at,closed_by_user_id,status FROM cash_sessions WHERE id=?",(sid,)).fetchone()
            audit=c.execute("SELECT user_id FROM audit_log WHERE action='CASH_CLOSE' AND document=?",(str(sid),)).fetchone()
        self.assertEqual(row['status'],'CLOSED')
        self.assertIsNotNone(row['closed_at'])
        self.assertEqual(row['closed_by_user_id'],self.uid)
        self.assertEqual(audit['user_id'],self.uid)

if __name__=='__main__':unittest.main()
