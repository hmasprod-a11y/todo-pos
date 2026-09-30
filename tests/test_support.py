import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'todo'))
import database
from services import backup
from services.support import diagnostics,diagnostic_text,documentation_paths,APP_VERSION
from services.security import hash_pin
from services.bootstrap import ensure_defaults

class SupportTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.old_db=database.DB_PATH;self.old_base=backup.BASE
        database.DB_PATH=Path(self.tmp.name)/'todo.db';backup.DB_PATH=database.DB_PATH;backup.BASE=Path(self.tmp.name)
        database.init_db();ensure_defaults();database.set_setting('shop_name','TODO TEST');database.set_setting('workstation_code','09')
    def tearDown(self):
        database.DB_PATH=self.old_db;backup.DB_PATH=self.old_db;backup.BASE=self.old_base;self.tmp.cleanup()
    def test_diagnostics_contains_safe_runtime_information(self):
        d=diagnostics()
        self.assertEqual(d['version'],APP_VERSION);self.assertEqual(d['shop'],'TODO TEST');self.assertEqual(d['workstation'],'09')
        self.assertEqual(d['integrity'],'ok');self.assertGreater(d['tables'],10);self.assertGreater(d['db_size_bytes'],0)
        self.assertTrue(d['default_admin_pin'])
        text=diagnostic_text();self.assertIn('Poste: 09',text);self.assertIn('Intégrité: ok',text)
        self.assertIn('PIN admin par défaut: À CHANGER',text);self.assertNotIn('smtp_app_password',text)
    def test_default_admin_pin_status_clears_after_change(self):
        with database.connect() as conn:
            conn.execute("UPDATE users SET pin_hash=? WHERE username='admin'",(hash_pin('9876'),));conn.commit()
        self.assertFalse(diagnostics()['default_admin_pin'])
        self.assertIn('PIN admin par défaut: OK',diagnostic_text())

    def test_document_catalog_is_complete(self):
        paths=documentation_paths()
        self.assertEqual(set(paths),{'guide_fr','guide_ar','backup','install','checklist','privacy','terms','support'})
        self.assertTrue(all(p.name.endswith('.md') for p in paths.values()))

if __name__=='__main__':unittest.main()
