import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "todo"))

from fiscal import calculate_tax


class TaxEngineTests(unittest.TestCase):
    def test_exclusive_tax_uses_integer_half_up_rounding(self):
        result = calculate_tax(10000, 2000, tax_included=False)
        self.assertEqual((result.net_cents, result.tax_cents, result.gross_cents), (10000, 2000, 12000))

    def test_included_tax_preserves_the_original_gross_amount(self):
        result = calculate_tax(12000, 2000, tax_included=True)
        self.assertEqual((result.net_cents, result.tax_cents, result.gross_cents), (10000, 2000, 12000))

    def test_zero_rate_and_fractional_rounding_are_consistent(self):
        self.assertEqual(calculate_tax(999, 0, tax_included=False).gross_cents, 999)
        result = calculate_tax(101, 500, tax_included=False)
        self.assertEqual((result.tax_cents, result.gross_cents), (5, 106))

    def test_invalid_amounts_and_rates_are_rejected(self):
        with self.assertRaises(ValueError):
            calculate_tax(-1, 2000, tax_included=False)
        with self.assertRaises(ValueError):
            calculate_tax(100, -1, tax_included=False)


if __name__ == "__main__":
    unittest.main()
