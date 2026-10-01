import sys,tempfile,time,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'todo'))
import database
from services.catalog import search_products,scan_barcode
from screens.products import catalog_page_size

class CatalogScaleTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.old=database.DB_PATH;database.DB_PATH=Path(self.tmp.name)/'db.sqlite'
        database.init_db()
        rows=[]
        for i in range(20000):
            rows.append((f'SKU-{i:05d}',f'Produit catalogue performance {i:05d}',100+i%500,1))
        with database.connect() as c:
            c.executemany("INSERT INTO products(sku,name,sale_price_cents,active) VALUES(?,?,?,?)",rows)
            ids=[r[0] for r in c.execute("SELECT id FROM products ORDER BY id")]
            c.executemany("INSERT INTO product_barcodes(product_id,barcode) VALUES(?,?)",[(pid,f'611{i:09d}') for i,pid in enumerate(ids)])
            c.commit()
    def tearDown(self):
        database.DB_PATH=self.old;self.tmp.cleanup()
    def test_twenty_thousand_product_search_and_scan(self):
        started=time.perf_counter()
        rows=search_products('catalogue performance 19999',limit=10)
        text_elapsed=time.perf_counter()-started
        self.assertEqual([r['sku'] for r in rows],['SKU-19999'])
        started=time.perf_counter()
        exact=search_products('SKU-12345',limit=10)
        sku_elapsed=time.perf_counter()-started
        self.assertEqual(exact[0]['sku'],'SKU-12345')
        started=time.perf_counter()
        scanned=scan_barcode('611000012345')
        scan_elapsed=time.perf_counter()-started
        self.assertEqual(scanned[0]['sku'],'SKU-12345')
        # Generous CI guardrail: catches accidental full-table regressions/hangs without flaky micro-benchmarking.
        self.assertLess(text_elapsed,2.0)
        self.assertLess(sku_elapsed,1.0)
        self.assertLess(scan_elapsed,1.0)
    def test_catalog_page_size_is_configurable_and_bounded(self):
        database.set_setting('catalog_page_size', '37')
        self.assertEqual(catalog_page_size(), 37)
        database.set_setting('catalog_page_size', 'not-a-number')
        self.assertEqual(catalog_page_size(), 200)
        database.set_setting('catalog_page_size', '5')
        self.assertEqual(catalog_page_size(), 20)
        database.set_setting('catalog_page_size', '5000')
        self.assertEqual(catalog_page_size(), 1000)

    def test_indexes_required_for_large_catalog_exist(self):
        with database.connect() as c:
            names={r['name'] for r in c.execute("SELECT name FROM sqlite_master WHERE type='index'")}
        for name in ('idx_products_sku','idx_products_active_name','idx_barcodes_barcode','idx_barcodes_product','idx_product_categories_product'):
            self.assertIn(name,names)

if __name__=='__main__':unittest.main()
