import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "todo"))

from country_profiles import PROFILES, format_money, get_country_profile, normalize_country_code


class CountryProfileTests(unittest.TestCase):
    def test_profile_registry_is_public_for_settings_selection(self):
        self.assertIn("MA", PROFILES)
        self.assertIn("US", PROFILES)

    def test_profiles_choose_explicit_presentation_defaults(self):
        self.assertEqual(get_country_profile("GB").currency, "£")
        self.assertEqual(get_country_profile("AE").tax_label, "VAT")
        self.assertEqual(get_country_profile("US").date_format, "MM/DD/YYYY")
        self.assertEqual(normalize_country_code("invalid"), "MA")

    def test_money_formatting_uses_integer_minor_units_and_profile_rules(self):
        self.assertEqual(format_money(1234, get_country_profile("GB")), "£12.34")
        self.assertEqual(format_money(-1234, get_country_profile("FR")), "-12,34 €")
        self.assertEqual(format_money(500, get_country_profile("AE")), "5.00 AED")


if __name__ == "__main__":
    unittest.main()
