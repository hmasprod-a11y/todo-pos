import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "todo"))

import database
from services import backup

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

    def test_wal_backup_restore_round_trip_creates_safety_copy(self):
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
                with closing(sqlite3.connect(live_db)) as conn:
                    conn.executescript(SCHEMA)
                    conn.execute("PRAGMA journal_mode=WAL")
                    conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", ("shop_name", "WAL shop"))
                    conn.commit()
                    self.assertEqual(conn.execute("PRAGMA journal_mode").fetchone()[0].lower(), "wal")

                snapshot = backup.create_backup()
                self.assertTrue(snapshot.is_file())
                with closing(sqlite3.connect(live_db)) as conn:
                    conn.execute("UPDATE settings SET value=? WHERE key=?", ("Changed shop", "shop_name"))
                    conn.commit()

                safety = backup.restore_backup(snapshot)
                self.assertTrue(safety.is_file())
                with closing(sqlite3.connect(live_db)) as conn:
                    restored = conn.execute("SELECT value FROM settings WHERE key='shop_name'").fetchone()[0]
                    self.assertEqual(restored, "WAL shop")
                    self.assertEqual(conn.execute("PRAGMA integrity_check").fetchone()[0], "ok")
                    self.assertFalse(conn.execute("PRAGMA foreign_key_check").fetchone())
            finally:
                database.DB_PATH = old_database_path
                backup.DB_PATH = old_backup_path
                backup.BASE = old_backup_base


if __name__ == "__main__":
    unittest.main()
