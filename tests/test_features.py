import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"todo"))
import database
from services.features import FeatureService

class FeatureServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.previous=database.DB_PATH
        database.DB_PATH=Path(self.temp.name)/"todo.db";database.init_db()
    def tearDown(self):
        database.DB_PATH=self.previous;self.temp.cleanup()
    def test_free_plan_keeps_core_pos_and_denies_pro_features(self):
        service=FeatureService()
        self.assertTrue(service.can("SALE"));self.assertTrue(service.can("LOCAL_BACKUP"))
        self.assertFalse(service.can("PROMOTIONS"));self.assertFalse(service.can("UNKNOWN"))
    def test_pro_plan_unlocks_the_central_pro_feature_set(self):
        database.set_setting("commercial_plan","PRO")
        self.assertTrue(FeatureService().can("PROMOTIONS"))
        self.assertTrue(FeatureService().can("CUSTOMER_DISPLAY"))
if __name__=="__main__":unittest.main()
