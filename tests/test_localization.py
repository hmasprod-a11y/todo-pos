import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "todo"))

from localization import (
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    Translator,
    language_direction,
    load_catalog,
    normalize_language,
)


class LocalizationTests(unittest.TestCase):
    def test_supported_catalogs_expose_the_same_required_cashier_keys(self):
        required = {
            "app.name",
            "common.cancel",
            "common.save",
            "sale.title",
            "sale.total",
            "payment.title",
        }
        for language in SUPPORTED_LANGUAGES:
            self.assertTrue(required.issubset(load_catalog(language)))

    def test_language_normalization_and_rtl_direction_are_deterministic(self):
        self.assertEqual(normalize_language("EN-us"), "en")
        self.assertEqual(normalize_language("ar_MA"), "ar")
        self.assertEqual(normalize_language("unknown"), DEFAULT_LANGUAGE)
        self.assertEqual(language_direction("ar"), "rtl")
        self.assertEqual(language_direction("fr"), "ltr")

    def test_translator_uses_key_fallback_and_never_crashes_on_missing_values(self):
        english = Translator("en")
        self.assertEqual(english("sale.title"), "Sale")
        self.assertEqual(Translator("ar").direction, "rtl")
        self.assertEqual(Translator("en")("missing.key"), "missing.key")
        self.assertEqual(english("common.save", unused="value"), "Save")


if __name__ == "__main__":
    unittest.main()
