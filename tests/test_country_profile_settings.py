import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "todo"))

import database
from services.globalization import current_country_profile, select_country_profile


class CountryProfileSettingsTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.previous_path = database.DB_PATH
        database.DB_PATH = Path(self.tempdir.name) / "todo.db"
        database.init_db()

    def tearDown(self):
        database.DB_PATH = self.previous_path
        self.tempdir.cleanup()

    def test_profile_selection_is_persisted_and_updates_only_future_defaults(self):
        self.assertEqual(current_country_profile().code, "MA")
        selected = select_country_profile("us")
        self.assertEqual((selected.code, selected.currency_symbol), ("US", "$"))
        with database.connect() as conn:
            self.assertEqual(database.get_setting("country_code", conn=conn), "US")
            self.assertEqual(database.get_setting("currency", conn=conn), "$")
            self.assertEqual(database.get_setting("tax_label", conn=conn), "Sales tax")
            self.assertEqual(database.get_setting("tax_default_rate_basis_points", conn=conn), "0")
            self.assertEqual(database.get_setting("tax_default_included", conn=conn), "0")


if __name__ == "__main__":
    unittest.main()
