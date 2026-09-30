import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"todo"))
import database
class CommerceSchemaTests(unittest.TestCase):
 def test_commerce_tables_are_created_offline(self):
  with tempfile.TemporaryDirectory() as directory:
   old=database.DB_PATH;database.DB_PATH=Path(directory)/"todo.db"
   try:
    database.init_db()
    with database.connect() as conn:
     names={row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
     self.assertTrue({"feature_flags","commerce_state","app_installation"}.issubset(names))
   finally: database.DB_PATH=old
if __name__=="__main__":unittest.main()
