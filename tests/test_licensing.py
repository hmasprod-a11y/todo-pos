import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"todo"))
import database
from services.licensing import LocalLicenseProvider,MicrosoftStoreLicenseProvider
class LicenseProviderTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.previous=database.DB_PATH;database.DB_PATH=Path(self.temp.name)/"todo.db";database.init_db()
 def tearDown(self): database.DB_PATH=self.previous;self.temp.cleanup()
 def test_local_provider_defaults_to_free(self): self.assertEqual(LocalLicenseProvider().plan(),"FREE")
 def test_store_provider_uses_cached_entitlement_offline(self):
  database.set_setting("commercial_plan","FREE");database.set_setting("store_cached_plan","PRO")
  self.assertEqual(MicrosoftStoreLicenseProvider().plan(),"PRO")
if __name__=="__main__":unittest.main()
