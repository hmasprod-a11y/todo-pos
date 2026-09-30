import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"todo"))
import database
from services.onboarding import is_complete,mark_complete
class OnboardingTests(unittest.TestCase):
 def test_first_run_state_is_local_and_persistent(self):
  with tempfile.TemporaryDirectory() as d:
   old=database.DB_PATH;database.DB_PATH=Path(d)/"todo.db"
   try: database.init_db();self.assertFalse(is_complete());mark_complete();self.assertTrue(is_complete())
   finally: database.DB_PATH=old
if __name__=="__main__":unittest.main()
