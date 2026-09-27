import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'todo'))
import database
from services.bootstrap import ensure_defaults
from services.security import current_user
from services.shortcuts import get_shortcuts,save_shortcuts

class CustomShortcutTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.old=database.DB_PATH
        database.DB_PATH=Path(self.tmp.name)/'db.sqlite';database.init_db();ensure_defaults()
        with database.connect() as c:self.uid=c.execute("SELECT id FROM users WHERE username='admin'").fetchone()[0]
        self.token=current_user.set(self.uid)
    def tearDown(self):
        current_user.reset(self.token);database.DB_PATH=self.old;self.tmp.cleanup()
    def test_defaults_and_persistence(self):
        self.assertEqual(get_shortcuts(),['calculator','held','drawer'])
        save_shortcuts(['duplicate','expense','keyboard'])
        self.assertEqual(get_shortcuts(),['duplicate','expense','keyboard'])
    def test_rejects_unknown_and_more_than_six(self):
        with self.assertRaises(ValueError):save_shortcuts(['unknown'])
        with self.assertRaises(ValueError):save_shortcuts(['calculator','held','drawer','duplicate','price_grid','expense','report'])

if __name__=='__main__':unittest.main()
