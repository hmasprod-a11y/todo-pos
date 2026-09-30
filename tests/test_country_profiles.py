import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "todo"))

from country_profiles import PROFILES, format_date, format_money, format_number, get_country_profile, normalize_country_code
from services.money import fmt


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

    def test_legacy_money_formatter_obeys_profile_when_not_overridden(self):
        self.assertEqual(fmt(1234, profile=get_country_profile('GB')), '£12.34')
        self.assertEqual(fmt(-1234, profile=get_country_profile('FR')), '-12,34 €')
        self.assertEqual(fmt(1234, '', get_country_profile('FR')), '12,34')
        self.assertEqual(format_number(1234, get_country_profile('GB')), '12.34')

    def test_date_format_uses_country_profile(self):
        self.assertEqual(format_date('2026-09-30 09:15:00', get_country_profile('MA')), '30/09/2026')
        self.assertEqual(format_date('2026-09-30 09:15:00', get_country_profile('US')), '09/30/2026')


if __name__ == "__main__":
    unittest.main()
