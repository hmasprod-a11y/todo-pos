import sqlite3
import unittest
from unittest.mock import patch

from services.settings_reference import list_price_grids, list_sellers


class SettingsReferenceTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        for table in ("sellers", "price_grids"):
            self.connection.execute(
                f"CREATE TABLE {table} (id INTEGER PRIMARY KEY, name TEXT, active INTEGER)"
            )
            self.connection.executemany(
                f"INSERT INTO {table} (id, name, active) VALUES (?, ?, ?)",
                [(1, "zebra", 1), (2, "Alpha", 0), (3, "beta", 1)],
            )

    def tearDown(self):
        self.connection.close()

    def test_sellers_include_inactive_and_sort_by_name(self):
        with patch("database.connect", return_value=self.connection):
            rows = list_sellers()
        self.assertEqual([row["name"] for row in rows], ["Alpha", "beta", "zebra"])
        self.assertEqual([row["active"] for row in rows], [0, 1, 1])

    def test_price_grids_include_inactive_and_sort_by_name(self):
        with patch("database.connect", return_value=self.connection):
            rows = list_price_grids()
        self.assertEqual([row["name"] for row in rows], ["Alpha", "beta", "zebra"])
        self.assertEqual([row["active"] for row in rows], [0, 1, 1])


if __name__ == "__main__":
    unittest.main()
