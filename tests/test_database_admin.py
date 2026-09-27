import sys,tempfile,unittest,csv
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'todo'))
import database
from services import backup
from services.bootstrap import ensure_defaults
from services.security import current_user
from services.database_admin import table_inventory,export_table_csv,import_reference_csv,integrity_status

class DatabaseAdminTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.old_db=database.DB_PATH;self.old_base=backup.BASE
        database.DB_PATH=Path(self.tmp.name)/'todo.db';backup.DB_PATH=database.DB_PATH;backup.BASE=Path(self.tmp.name)
        database.init_db();ensure_defaults()
        with database.connect() as c:
            self.uid=c.execute("SELECT id FROM users WHERE username='admin'").fetchone()[0]
            c.execute("INSERT INTO suppliers(name,phone,notes,active) VALUES('Existing','1','',1)")
        self.token=current_user.set(self.uid)
    def tearDown(self):
        current_user.reset(self.token);database.DB_PATH=self.old_db;backup.DB_PATH=self.old_db;backup.BASE=self.old_base;self.tmp.cleanup()
    def test_inventory_export_and_integrity(self):
        names={r['name'] for r in table_inventory()}
        self.assertIn('products',names);self.assertIn('sales',names);self.assertNotIn('product_search_data',names)
        out=Path(self.tmp.name)/'suppliers.csv';export_table_csv('suppliers',out)
        text=out.read_text(encoding='utf-8-sig');self.assertIn('Existing',text)
        self.assertTrue(integrity_status()['ok'])
    def test_safe_reference_import_creates_backup_and_ignores_source_id(self):
        src=Path(self.tmp.name)/'clients.csv'
        with src.open('w',newline='',encoding='utf-8-sig') as fh:
            w=csv.writer(fh);w.writerow(['id','name','phone','notes','active','created_at']);w.writerow([999,'Client CSV','0600','N',1,'2026-01-01 00:00:00'])
        result=import_reference_csv('clients',src)
        self.assertEqual(result['rows'],1);self.assertTrue(Path(result['safety']).exists())
        with database.connect() as c:
            row=c.execute("SELECT id,name FROM clients WHERE name='Client CSV'").fetchone()
        self.assertIsNotNone(row);self.assertNotEqual(row['id'],999)
    def test_transaction_tables_cannot_be_imported(self):
        src=Path(self.tmp.name)/'sales.csv';src.write_text('sale_no\nX\n',encoding='utf-8')
        with self.assertRaises(ValueError):import_reference_csv('sales',src)

if __name__=='__main__':unittest.main()
