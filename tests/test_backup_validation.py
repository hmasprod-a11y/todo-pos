import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "todo"))

import database
from database import SCHEMA
from services import backup
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

    def test_backup_restore_round_trip_preserves_shop_data(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            live_db = root / "todo.db"
            old_database_path = database.DB_PATH
            old_backup_path = backup.DB_PATH
            old_backup_base = backup.BASE
            try:
                database.DB_PATH = live_db
                backup.DB_PATH = live_db
                backup.BASE = root
                with sqlite3.connect(live_db) as conn:
                    conn.executescript(SCHEMA)
                    conn.execute(
                        "INSERT INTO settings(key,value) VALUES(?,?)",
                        ("shop_name", "Original shop"),
                    )
                    conn.commit()

                snapshot = backup.create_backup()
                self.assertTrue(snapshot.is_file())

                with sqlite3.connect(live_db) as conn:
                    conn.execute(
                        "UPDATE settings SET value=? WHERE key=?",
                        ("Mutated shop", "shop_name"),
                    )
                    conn.commit()

                safety = backup.restore_backup(snapshot)
                self.assertTrue(safety.is_file())
                with sqlite3.connect(live_db) as conn:
                    restored = conn.execute(
                        "SELECT value FROM settings WHERE key='shop_name'"
                    ).fetchone()[0]
                    self.assertEqual(restored, "Original shop")
                    self.assertEqual(conn.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            finally:
                database.DB_PATH = old_database_path
                backup.DB_PATH = old_backup_path
                backup.BASE = old_backup_base


if __name__ == "__main__":
    unittest.main()
