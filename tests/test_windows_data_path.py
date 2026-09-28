import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'todo'))
import database

class WindowsDataPathTests(unittest.TestCase):
    def test_frozen_runtime_prefers_programdata(self):
        root=database.runtime_base_dir(True,r'C:\\Program Files\\ToDo POS\\ToDo.exe',{'PROGRAMDATA':r'C:\\ProgramData'})
        self.assertEqual(str(root),str(Path(r'C:\\ProgramData')/'ToDo POS'))

    def test_legacy_migration_copies_shop_data_without_overwriting_existing_target(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td);legacy=base/'legacy';target=base/'programdata'
            (legacy/'data').mkdir(parents=True);(legacy/'assets'/'products').mkdir(parents=True)
            (legacy/'data'/'todo.db').write_bytes(b'old-db')
            (legacy/'data'/'license.json').write_text('license',encoding='utf-8')
            (legacy/'assets'/'products'/'p.jpg').write_bytes(b'image')
            self.assertTrue(database.migrate_legacy_frozen_data(legacy,target,force=True))
            self.assertEqual((target/'data'/'todo.db').read_bytes(),b'old-db')
            self.assertEqual((target/'data'/'license.json').read_text(encoding='utf-8'),'license')
            self.assertEqual((target/'assets'/'products'/'p.jpg').read_bytes(),b'image')
            (legacy/'data'/'todo.db').write_bytes(b'new-old-db')
            self.assertFalse(database.migrate_legacy_frozen_data(legacy,target,force=True))
            self.assertEqual((target/'data'/'todo.db').read_bytes(),b'old-db')

if __name__=='__main__':unittest.main()
