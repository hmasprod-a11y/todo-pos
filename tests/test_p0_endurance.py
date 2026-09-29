"""P0 endurance coverage for the offline barcode, sale, and cash-closure path."""
import os
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "todo"))
_temp = tempfile.TemporaryDirectory()
os.environ["TODO_DB_PATH"] = str(Path(_temp.name) / "p0-endurance.db")

from database import connect, init_db
from services.bootstrap import ensure_defaults
from services.cash import close_session, open_session
from services.catalog import scan_barcode
from services.sales import complete_sale
from services.security import current_user


class P0EnduranceTests(unittest.TestCase):
    """Keep high-volume transactional work deterministic and database-isolated."""

    @classmethod
    def setUpClass(cls):
        init_db()
        ensure_defaults()
        with connect() as conn:
            cls.user_id = conn.execute(
                "SELECT id FROM users WHERE active=1 ORDER BY id LIMIT 1"
            ).fetchone()["id"]
            product_id = conn.execute(
                "INSERT INTO products(name,sale_price_cents,stock_qty,active) "
                "VALUES(?,?,?,1)",
                ("P0 endurance barcode product", 250, 2500),
            ).lastrowid
            cls.barcode_id = conn.execute(
                "INSERT INTO product_barcodes(product_id,barcode,qty_multiplier) "
                "VALUES(?,?,1)",
                (product_id, "P0-ENDURANCE-001"),
            ).lastrowid
            cls.product_id = product_id

    def setUp(self):
        self._user_token = current_user.set(self.user_id)

    def tearDown(self):
        current_user.reset(self._user_token)

    def test_scans_sales_and_cash_closures_remain_consistent(self):
        # Count relative to the isolated test database state: another endurance
        # case can legitimately close an empty session before this one runs.
        with connect() as conn:
            sales_before = conn.execute(
                "SELECT COUNT(*) AS n FROM sales WHERE sale_no LIKE 'V-%'"
            ).fetchone()["n"]
            closures_before = conn.execute(
                "SELECT COUNT(*) AS n FROM cash_sessions WHERE status='CLOSED'"
            ).fetchone()["n"]

        # Barcode lookup is intentionally exercised at release-gate volume before
        # the repeated checkout/closure loop starts.
        for _ in range(1000):
            matches = scan_barcode("P0-ENDURANCE-001")
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0]["id"], self.product_id)

        for _ in range(50):
            session_id = open_session(self.user_id, 0)
            for _ in range(2):
                sale = complete_sale(
                    session_id,
                    self.user_id,
                    [{
                        "product_id": self.product_id,
                        "barcode_id": self.barcode_id,
                        "barcode": "P0-ENDURANCE-001",
                        "qty": 1,
                        "unit_price_cents": 250,
                        "discount_cents": 0,
                    }],
                    "CASH",
                    250,
                )
                self.assertEqual(sale["total_cents"], 250)
                self.assertEqual(sale["change_cents"], 0)

            expected, difference, totals = close_session(session_id, 500)
            self.assertEqual(expected, 500)
            self.assertEqual(difference, 0)
            self.assertEqual(totals["cash_sales"], 500)

        with connect() as conn:
            sales = conn.execute(
                "SELECT COUNT(*) AS n FROM sales WHERE sale_no LIKE 'V-%'"
            ).fetchone()["n"]
            closures = conn.execute(
                "SELECT COUNT(*) AS n FROM cash_sessions WHERE status='CLOSED'"
            ).fetchone()["n"]
        self.assertEqual(sales, sales_before + 100)
        self.assertEqual(closures, closures_before + 50)

    def test_sale_failure_rolls_back_without_partial_cash_or_stock(self):
        # Simulate a mid-sale device/process failure.  The transactional boundary
        # must leave no partial receipt, cash movement, or inventory mutation.
        from services import sales as sales_service

        with connect() as conn:
            sales_before = conn.execute("SELECT COUNT(*) AS n FROM sales").fetchone()["n"]
            stock_before = conn.execute(
                "SELECT stock_qty FROM products WHERE id=?", (self.product_id,)
            ).fetchone()["stock_qty"]

        session_id = open_session(self.user_id, 0)
        line = {
            "product_id": self.product_id,
            "barcode_id": self.barcode_id,
            "barcode": "P0-ENDURANCE-001",
            "qty": 1,
            "unit_price_cents": 250,
            "discount_cents": 0,
        }
        with patch.object(
            sales_service, "apply_stock_movement", side_effect=OSError("simulated interruption")
        ):
            with self.assertRaisesRegex(OSError, "simulated interruption"):
                complete_sale(session_id, self.user_id, [line], "CASH", 250)

        with connect() as conn:
            sales_after = conn.execute("SELECT COUNT(*) AS n FROM sales").fetchone()["n"]
            stock_after = conn.execute(
                "SELECT stock_qty FROM products WHERE id=?", (self.product_id,)
            ).fetchone()["stock_qty"]
        self.assertEqual(sales_after, sales_before)
        self.assertEqual(stock_after, stock_before)
        self.assertEqual(close_session(session_id, 0)[:2], (0, 0))

    def test_disconnected_serial_devices_raise_recoverable_errors(self):
        # CI cannot depend on physical peripherals.  A refused COM connection must
        # give callers a normal, catchable error rather than hang the cashier loop.
        from services import customer_serial_display, rfid, scale

        class OfflineSerial:
            def __init__(self, *args, **kwargs):
                raise OSError("device unavailable")

        offline_serial = SimpleNamespace(Serial=OfflineSerial)
        with patch.dict(sys.modules, {"serial": offline_serial}):
            with self.assertRaisesRegex(OSError, "Balance COM99"):
                scale.read_weight(port="COM99", timeout_ms=100)
            with self.assertRaisesRegex(OSError, "device unavailable"):
                rfid.read_tag(port="COM99", timeout_ms=100)
            with self.assertRaisesRegex(OSError, "device unavailable"):
                customer_serial_display.write_lines(
                    "ARTICLE", "TOTAL", port="COM99", timeout_ms=100
                )


if __name__ == "__main__":
    unittest.main()
