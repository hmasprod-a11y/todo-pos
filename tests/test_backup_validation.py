import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "todo"))

from database import SCHEMA
from services.backup import validate


class BackupValidationTests(unittest.TestCase):
    def test_complete_schema_passes_backup_validation(self):
        with sqlite3.connect(":memory:") as conn:
            conn.executescript(SCHEMA)
            validate(conn)

    def test_missing_required_table_is_rejected(self):
        with sqlite3.connect(":memory:") as conn:
            conn.execute("CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT)")
            with self.assertRaisesRegex(ValueError, "base ToDo complète"):
                validate(conn)


if __name__ == "__main__":
    unittest.main()
