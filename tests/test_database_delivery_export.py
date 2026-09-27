import sys,tempfile,unittest,zipfile,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'todo'))
import database
from services.database_admin import export_schema_sql,export_database_bundle

class DatabaseDeliveryExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.old=database.DB_PATH
        database.DB_PATH=Path(self.tmp.name)/'todo.db';database.init_db()
        with database.connect() as c:
            c.execute("INSERT INTO categories(name) VALUES('Export Test')")
            c.execute("INSERT INTO products(name,sale_price_cents,stock_qty) VALUES('Article Export',1234,2)")
    def tearDown(self):
        database.DB_PATH=self.old;self.tmp.cleanup()
    def test_schema_export_contains_application_tables_and_triggers(self):
        out=export_schema_sql(Path(self.tmp.name)/'schema.sql')
        text=out.read_text(encoding='utf-8')
        self.assertIn('CREATE TABLE products',text)
        self.assertIn('CREATE TABLE sales',text)
        self.assertIn('PRAGMA foreign_keys=ON',text)
        self.assertNotIn('sqlite_sequence',text)
    def test_bundle_contains_manifest_schema_and_csv_data(self):
        out=export_database_bundle(Path(self.tmp.name)/'delivery.zip')
        with zipfile.ZipFile(out) as z:
            names=set(z.namelist())
            self.assertIn('schema.sql',names);self.assertIn('manifest.json',names)
            self.assertIn('tables/products.csv',names)
            manifest=json.loads(z.read('manifest.json'))
            self.assertEqual(manifest['format'],'todo-database-export')
            self.assertEqual(manifest['integrity'],'ok')
            product_info=next(x for x in manifest['tables'] if x['table']=='products')
            self.assertGreaterEqual(product_info['rows'],1)
            csv_text=z.read('tables/products.csv').decode('utf-8-sig')
            self.assertIn('Article Export',csv_text)

if __name__=='__main__':unittest.main()
