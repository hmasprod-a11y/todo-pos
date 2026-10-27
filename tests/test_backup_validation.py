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

    def test_version_127_backup_without_new_journals_is_supported(self):
        with sqlite3.connect(':memory:') as conn:
            conn.executescript(SCHEMA)
            for table in ('checkout_requests','product_variants','purchase_order_receipts'):conn.execute(f'DROP TABLE {table}')
            conn.execute('PRAGMA user_version=127')
            validate(conn)

    def test_version_128_backup_must_include_request_journal(self):
        with sqlite3.connect(':memory:') as conn:
            conn.executescript(SCHEMA);conn.execute('PRAGMA user_version=128');conn.execute('DROP TABLE checkout_requests')
            with self.assertRaises(ValueError):validate(conn)

    def test_version_128_receipt_link_migrates_without_losing_purchase(self):
        with tempfile.TemporaryDirectory() as td:
            old_path=database.DB_PATH
            database.DB_PATH=Path(td)/'shop.db'
            try:
                database.init_db()
                with database.connect() as conn:
                    supplier=conn.execute("INSERT INTO suppliers(name) VALUES('Supplier')").lastrowid
                    order=conn.execute("INSERT INTO purchase_orders(supplier_id,status) VALUES(?,'RECEIVED')",(supplier,)).lastrowid
                    purchase=conn.execute("INSERT INTO purchases(supplier_id) VALUES(?)",(supplier,)).lastrowid
                    conn.execute('DROP TABLE purchase_order_receipts')
                    conn.execute("""CREATE TABLE purchase_order_receipts (
                        order_id INTEGER PRIMARY KEY REFERENCES purchase_orders(id),
                        purchase_id INTEGER NOT NULL UNIQUE REFERENCES purchases(id)
                    )""")
                    conn.execute('INSERT INTO purchase_order_receipts(order_id,purchase_id) VALUES(?,?)',(order,purchase))
                    conn.execute('PRAGMA user_version=128')
                with database.connect() as conn:validate(conn)
                database.init_db()
                with database.connect() as conn:
                    self.assertEqual(conn.execute('PRAGMA user_version').fetchone()[0],129)
                    self.assertEqual(conn.execute('SELECT order_id FROM purchase_order_receipts WHERE purchase_id=?',(purchase,)).fetchone()[0],order)
                    pk={r['name'] for r in conn.execute('PRAGMA table_info(purchase_order_receipts)') if r['pk']}
                    self.assertEqual(pk,{'purchase_id'})
                    validate(conn)
                self.assertEqual(len(list((Path(td)/'migration_backups').glob('before_129_*.db'))),1)
            finally:
                database.DB_PATH=old_path

    def test_version_129_rejects_old_one_receipt_schema(self):
        with sqlite3.connect(':memory:') as conn:
            conn.executescript(SCHEMA)
            conn.execute('DROP TABLE purchase_order_receipts')
            conn.execute('CREATE TABLE purchase_order_receipts(order_id INTEGER PRIMARY KEY,purchase_id INTEGER UNIQUE)')
            conn.execute('PRAGMA user_version=129')
            with self.assertRaisesRegex(ValueError,'purchase_order_receipts'):
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
