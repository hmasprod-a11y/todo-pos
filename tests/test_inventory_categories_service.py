import sqlite3
import unittest
from unittest.mock import patch

from services.inventory import get_active_categories, product_stock_movements


class ActiveCategoriesTests(unittest.TestCase):
    def test_returns_only_active_categories_in_existing_sort_order(self):
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        try:
            connection.execute(
                "CREATE TABLE categories (id INTEGER PRIMARY KEY, name TEXT, "
                "active INTEGER, sort_order INTEGER)"
            )
            connection.executemany(
                "INSERT INTO categories (id, name, active, sort_order) VALUES (?, ?, ?, ?)",
                [
                    (1, "Zebra", 1, 2),
                    (2, "banana", 1, 1),
                    (3, "Apple", 1, 1),
                    (4, "Hidden", 0, 0),
                ],
            )
            with patch("database.connect", return_value=connection):
                actual = get_active_categories()
            self.assertEqual(
                actual,
                [
                    {"id": 3, "name": "Apple"},
                    {"id": 2, "name": "banana"},
                    {"id": 1, "name": "Zebra"},
                ],
            )
        finally:
            connection.close()


    def test_product_movement_history_is_scoped_and_newest_first(self):
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        try:
            connection.execute(
                "CREATE TABLE stock_movements (id INTEGER PRIMARY KEY, "
                "product_id INTEGER, qty_delta REAL)"
            )
            connection.execute(
                "CREATE TABLE users (id INTEGER PRIMARY KEY, display_name TEXT)"
            )
            connection.executemany(
                "INSERT INTO stock_movements (id, product_id, qty_delta) VALUES (?, ?, ?)",
                [(1, 7, 1), (2, 8, 4), (3, 7, -1)],
            )
            with patch("database.connect", return_value=connection):
                actual = product_stock_movements(7)
            self.assertEqual([row["id"] for row in actual], [3, 1])
            self.assertTrue(all(row["product_id"] == 7 for row in actual))
            self.assertTrue(all(row["username"] is None for row in actual))
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()
