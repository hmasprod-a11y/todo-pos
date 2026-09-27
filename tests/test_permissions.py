import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'todo'))
import database
from services.bootstrap import ensure_defaults
from services.security import current_user,has_permission,require_permission,set_user_permission

class PermissionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.old=database.DB_PATH;database.DB_PATH=Path(self.tmp.name)/'db.sqlite'
        database.init_db();ensure_defaults()
        with database.connect() as c:
            self.admin=c.execute("SELECT id FROM users WHERE username='admin'").fetchone()[0]
            self.cashier=c.execute("INSERT INTO users(username,display_name,pin_hash,role) VALUES('cash','Cash','x','cashier')").lastrowid
        self.token=current_user.set(self.admin)
    def tearDown(self):
        current_user.reset(self.token);database.DB_PATH=self.old;self.tmp.cleanup()
    def test_admin_has_every_permission(self):
        for code in ('DISCOUNT','PRICE_EDIT','RETURNS','STOCK_EDIT','REPORTS','MANAGEMENT','SETTINGS'):
            self.assertTrue(has_permission(code,self.admin))
    def test_cashier_permissions_can_be_granted_and_revoked(self):
        self.assertFalse(has_permission('REPORTS',self.cashier))
        set_user_permission(self.cashier,'REPORTS',True)
        self.assertTrue(has_permission('REPORTS',self.cashier))
        current_user.set(self.cashier);require_permission('REPORTS')
        current_user.set(self.admin);set_user_permission(self.cashier,'REPORTS',False)
        current_user.set(self.cashier)
        with self.assertRaises(PermissionError):require_permission('REPORTS')

if __name__=='__main__':unittest.main()
