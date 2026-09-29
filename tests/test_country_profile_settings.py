import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "todo"))

import database
from services.globalization import current_country_profile, new_product_tax_defaults, select_country_profile


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
        self.assertEqual((selected.code, selected.currency), ("US", "$"))
        with database.connect() as conn:
            self.assertEqual(database.get_setting("country_code", conn=conn), "US")
            self.assertEqual(database.get_setting("currency", conn=conn), "$")
            self.assertEqual(database.get_setting("tax_label", conn=conn), "Sales tax")
            self.assertEqual(database.get_setting("tax_default_rate_basis_points", conn=conn), "0")
            self.assertEqual(database.get_setting("tax_default_included", conn=conn), "0")
        self.assertEqual(new_product_tax_defaults(), {"tax_rate_basis_points": 0, "tax_included": 0})

    def test_country_selector_is_visible_and_explains_its_tax_default(self):
        text=(Path(__file__).resolve().parents[1] / "todo" / "screens" / "settings.py").read_text(encoding="utf-8")
        self.assertIn("self.country_combo", text)
        self.assertIn("self.sync_country_profile()", text)
        self.assertIn("textvariable=self.country_info", text)
        self.assertIn("row=3,column=2", text)
        settings_frame=text[text.index("class SettingsFrame"):]
        self.assertIn("    def sync_country_profile(self,event=None):", settings_frame)


if __name__ == "__main__":
    unittest.main()
