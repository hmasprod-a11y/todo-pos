import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "todo"))

import database


class TaxSnapshotSchemaTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.previous_path = database.DB_PATH
        database.DB_PATH = Path(self.tempdir.name) / "todo.db"
        database.init_db()

    def tearDown(self):
        database.DB_PATH = self.previous_path
        self.tempdir.cleanup()

    def test_fresh_database_has_country_and_immutable_tax_snapshot_fields(self):
        with database.connect() as conn:
            product_columns = {row["name"] for row in conn.execute("PRAGMA table_info(products)")}
            sale_columns = {row["name"] for row in conn.execute("PRAGMA table_info(sales)")}
            item_columns = {row["name"] for row in conn.execute("PRAGMA table_info(sale_items)")}
            self.assertTrue({"tax_rate_basis_points", "tax_included"}.issubset(product_columns))
            self.assertTrue({"country_code", "tax_label_snapshot", "tax_total_cents"}.issubset(sale_columns))
            self.assertTrue({"tax_net_cents", "tax_amount_cents", "tax_gross_cents"}.issubset(item_columns))
            self.assertEqual(database.get_setting("country_code", conn=conn), "MA")
            self.assertEqual(database.get_setting("tax_label", conn=conn), "Tax")
            conn.execute("INSERT INTO products(name) VALUES('Taxable item')")
            row = conn.execute("SELECT tax_rate_basis_points,tax_included FROM products").fetchone()
            self.assertEqual((row["tax_rate_basis_points"], row["tax_included"]), (0, 1))
            self.assertIsNone(conn.execute("SELECT 1 FROM tax_profiles").fetchone())


if __name__ == "__main__":
    unittest.main()
