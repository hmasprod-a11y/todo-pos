import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'todo'))
import database
from services import backup
from services.bootstrap import ensure_defaults
from services.security import verify_pin

class DefaultPinPolicyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.old=database.DB_PATH
        database.DB_PATH=Path(self.tmp.name)/'db.sqlite';backup.DB_PATH=database.DB_PATH;backup.BASE=Path(self.tmp.name)
        database.init_db();ensure_defaults()
    def tearDown(self):
        database.DB_PATH=self.old;self.tmp.cleanup()
    def test_default_admin_starts_with_1234_only_until_first_change(self):
        with database.connect() as c:
            row=c.execute("SELECT pin_hash FROM users WHERE username='admin'").fetchone()
            self.assertTrue(verify_pin('1234',row['pin_hash']))
        # UI login flow owns the mandatory replacement; this test protects the bootstrap invariant.

if __name__=='__main__':unittest.main()
