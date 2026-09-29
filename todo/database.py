from pathlib import Path
import os, shutil, sqlite3, sys

def runtime_base_dir(frozen=None, executable=None, environ=None):
    """Writable application-data root.

    Installed/frozen Windows builds keep mutable shop data out of Program Files.
    Source/development runs keep the historical repository-local layout.
    """
    if frozen is None:frozen=getattr(sys,'frozen',False)
    if not frozen:return Path(__file__).resolve().parent
    env=os.environ if environ is None else environ
    root=env.get('PROGRAMDATA') or env.get('LOCALAPPDATA')
    if root:return Path(root)/'ToDo POS'
    return Path(executable or sys.executable).resolve().parent/'todo'

BASE_DIR = runtime_base_dir()
DEFAULT_DB = BASE_DIR / "data" / "todo.db"
DB_PATH = Path(os.environ.get("TODO_DB_PATH", str(DEFAULT_DB)))

def _copy_missing_tree(source, destination):
    source=Path(source);destination=Path(destination)
    if not source.exists():return
    for item in source.rglob('*'):
        relative=item.relative_to(source);target=destination/relative
        if item.is_dir():
            target.mkdir(parents=True,exist_ok=True)
        elif not target.exists():
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(item,target)

def migrate_legacy_frozen_data(legacy_base=None,target_base=None,force=False):
    """Copy legacy <exe>/todo data once into the writable Windows data root.

    Existing target databases always win; migration never merges two shops.
    """
    if not force:
        if not getattr(sys,'frozen',False) or os.environ.get('TODO_DB_PATH'):return False
    legacy=Path(legacy_base) if legacy_base is not None else Path(sys.executable).resolve().parent/'todo'
    target=Path(target_base) if target_base is not None else BASE_DIR
    legacy_db=legacy/'data'/'todo.db';target_db=target/'data'/'todo.db'
    if target_db.exists() or not legacy_db.exists() or legacy.resolve()==target.resolve():return False
    target.mkdir(parents=True,exist_ok=True)
    for relative in ('data','assets/products','customer_media','backups'):
        _copy_missing_tree(legacy/relative,target/relative)
    return target_db.exists()

migrate_legacy_frozen_data()

SCHEMA = r"""
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    pin_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'cashier',
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_permissions (
    user_id INTEGER NOT NULL,
    permission TEXT NOT NULL,
    allowed INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY(user_id,permission),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    sort_order INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS suppliers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT NOT NULL DEFAULT '',
    name TEXT NOT NULL,
    category_id INTEGER,
    purchase_price_cents INTEGER NOT NULL DEFAULT 0,
    sale_price_cents INTEGER NOT NULL DEFAULT 0,
    stock_qty REAL NOT NULL DEFAULT 0,
    alert_qty REAL NOT NULL DEFAULT 0,
    image_path TEXT NOT NULL DEFAULT '',
    show_in_sale_photos INTEGER NOT NULL DEFAULT 0,
    allow_fraction INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(category_id) REFERENCES categories(id)
);

CREATE TABLE IF NOT EXISTS product_barcodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    barcode TEXT NOT NULL,
    label TEXT NOT NULL DEFAULT '',
    qty_multiplier REAL NOT NULL DEFAULT 1,
    price_override_cents INTEGER,
    FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_barcodes_barcode ON product_barcodes(barcode);
CREATE INDEX IF NOT EXISTS idx_barcodes_product ON product_barcodes(product_id);
CREATE INDEX IF NOT EXISTS idx_products_sku ON products(sku);
CREATE INDEX IF NOT EXISTS idx_products_active_name ON products(active,name,id);

CREATE TABLE IF NOT EXISTS quantity_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    min_qty REAL NOT NULL,
    unit_price_cents INTEGER NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_quantity_prices_product ON quantity_prices(product_id, min_qty);

CREATE TABLE IF NOT EXISTS price_grids (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    active INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS product_grid_prices (
    product_id INTEGER NOT NULL,
    grid_id INTEGER NOT NULL,
    unit_price_cents INTEGER NOT NULL,
    PRIMARY KEY(product_id,grid_id),
    FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE,
    FOREIGN KEY(grid_id) REFERENCES price_grids(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS rfid_tags (
    tag TEXT PRIMARY KEY,
    target_type TEXT NOT NULL,
    target_id INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_rfid_target ON rfid_tags(target_type,target_id);

CREATE TABLE IF NOT EXISTS payment_methods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name_fr TEXT NOT NULL,
    name_ar TEXT NOT NULL DEFAULT '',
    icon TEXT NOT NULL DEFAULT '',
    active INTEGER NOT NULL DEFAULT 1,
    system INTEGER NOT NULL DEFAULT 0,
    sort_order INTEGER NOT NULL DEFAULT 0
);
INSERT OR IGNORE INTO payment_methods(code,name_fr,name_ar,icon,active,system,sort_order) VALUES
('CASH','Espèces','نقداً','💵',1,1,10),
('CARD','Carte','بطاقة','💳',1,1,20);

CREATE TABLE IF NOT EXISTS cash_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    opened_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    closed_at TEXT,
    opening_cash_cents INTEGER NOT NULL DEFAULT 0,
    expected_cash_cents INTEGER NOT NULL DEFAULT 0,
    workstation_code TEXT NOT NULL DEFAULT '01',
    actual_cash_cents INTEGER,
    difference_cents INTEGER,
    closed_by_user_id INTEGER,
    status TEXT NOT NULL DEFAULT 'OPEN',
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(closed_by_user_id) REFERENCES users(id)
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_one_open_session
ON cash_sessions(status) WHERE status='OPEN';

CREATE TABLE IF NOT EXISTS sellers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tax_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    rate_basis_points INTEGER NOT NULL DEFAULT 0,
    tax_included INTEGER NOT NULL DEFAULT 1,
    active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_no TEXT NOT NULL UNIQUE,
    session_id INTEGER NOT NULL,
    cashier_user_id INTEGER NOT NULL,
    subtotal_cents INTEGER NOT NULL,
    discount_cents INTEGER NOT NULL DEFAULT 0,
    total_cents INTEGER NOT NULL,
    payment_method TEXT NOT NULL DEFAULT 'CASH',
    paid_cents INTEGER NOT NULL,
    change_cents INTEGER NOT NULL DEFAULT 0,
    client_ticket_no INTEGER,
    workstation_code TEXT NOT NULL DEFAULT '01',
    stock_tracked INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'COMPLETED',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(session_id) REFERENCES cash_sessions(id),
    FOREIGN KEY(cashier_user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS sale_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_id INTEGER NOT NULL,
    payment_method TEXT NOT NULL,
    amount_cents INTEGER NOT NULL,
    FOREIGN KEY(sale_id) REFERENCES sales(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_sale_payments_sale ON sale_payments(sale_id);

CREATE TABLE IF NOT EXISTS sale_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    barcode_used TEXT NOT NULL DEFAULT '',
    name_snapshot TEXT NOT NULL,
    qty REAL NOT NULL,
    unit_price_cents INTEGER NOT NULL,
    cost_price_cents INTEGER NOT NULL DEFAULT 0,
    discount_cents INTEGER NOT NULL DEFAULT 0,
    line_total_cents INTEGER NOT NULL,
    FOREIGN KEY(sale_id) REFERENCES sales(id) ON DELETE CASCADE,
    FOREIGN KEY(product_id) REFERENCES products(id)
);

CREATE TABLE IF NOT EXISTS quotations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER,
    status TEXT NOT NULL DEFAULT 'OPEN',
    valid_until TEXT,
    notes TEXT NOT NULL DEFAULT '',
    total_cents INTEGER NOT NULL DEFAULT 0,
    sale_id INTEGER,
    created_by INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    converted_at TEXT,
    FOREIGN KEY(client_id) REFERENCES clients(id),
    FOREIGN KEY(sale_id) REFERENCES sales(id),
    FOREIGN KEY(created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS quotation_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quotation_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    name_snapshot TEXT NOT NULL,
    qty REAL NOT NULL,
    unit_price_cents INTEGER NOT NULL,
    line_total_cents INTEGER NOT NULL,
    FOREIGN KEY(quotation_id) REFERENCES quotations(id) ON DELETE CASCADE,
    FOREIGN KEY(product_id) REFERENCES products(id)
);
CREATE INDEX IF NOT EXISTS idx_quotations_status ON quotations(status,id);

CREATE TABLE IF NOT EXISTS customer_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'OPEN',
    delivery_address TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    total_cents INTEGER NOT NULL DEFAULT 0,
    sale_id INTEGER,
    created_by INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT,
    FOREIGN KEY(client_id) REFERENCES clients(id),
    FOREIGN KEY(sale_id) REFERENCES sales(id),
    FOREIGN KEY(created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS customer_order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    name_snapshot TEXT NOT NULL,
    qty REAL NOT NULL,
    unit_price_cents INTEGER NOT NULL,
    line_total_cents INTEGER NOT NULL,
    FOREIGN KEY(order_id) REFERENCES customer_orders(id) ON DELETE CASCADE,
    FOREIGN KEY(product_id) REFERENCES products(id)
);
CREATE INDEX IF NOT EXISTS idx_customer_orders_status ON customer_orders(status,id);

CREATE TABLE IF NOT EXISTS held_sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    label TEXT NOT NULL DEFAULT '',
    cashier_user_id INTEGER NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(cashier_user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS inventory_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    label TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'OPEN',
    created_by INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    validated_by INTEGER,
    validated_at TEXT,
    FOREIGN KEY(created_by) REFERENCES users(id),
    FOREIGN KEY(validated_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS inventory_session_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    product_name TEXT NOT NULL,
    theory_qty REAL NOT NULL,
    counted_qty REAL,
    unit_cost_cents INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY(session_id) REFERENCES inventory_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY(product_id) REFERENCES products(id)
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_inventory_session_product ON inventory_session_items(session_id,product_id);

CREATE TABLE IF NOT EXISTS stock_movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    movement_type TEXT NOT NULL,
    qty_delta REAL NOT NULL,
    stock_after REAL NOT NULL,
    unit_cost_cents INTEGER NOT NULL DEFAULT 0,
    ref_type TEXT NOT NULL DEFAULT '',
    ref_id INTEGER,
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(product_id) REFERENCES products(id)
);
CREATE INDEX IF NOT EXISTS idx_stock_movements_product ON stock_movements(product_id, id);

CREATE TABLE IF NOT EXISTS purchases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id INTEGER,
    supplier_invoice TEXT NOT NULL DEFAULT '',
    total_cents INTEGER NOT NULL DEFAULT 0,
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(supplier_id) REFERENCES suppliers(id)
);

CREATE TABLE IF NOT EXISTS purchase_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'OPEN',
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    received_at TEXT,
    FOREIGN KEY(supplier_id) REFERENCES suppliers(id)
);

CREATE TABLE IF NOT EXISTS purchase_order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    qty REAL NOT NULL,
    unit_cost_cents INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY(order_id) REFERENCES purchase_orders(id) ON DELETE CASCADE,
    FOREIGN KEY(product_id) REFERENCES products(id)
);

CREATE TABLE IF NOT EXISTS purchase_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    purchase_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    qty REAL NOT NULL,
    unit_cost_cents INTEGER NOT NULL,
    line_total_cents INTEGER NOT NULL,
    FOREIGN KEY(purchase_id) REFERENCES purchases(id) ON DELETE CASCADE,
    FOREIGN KEY(product_id) REFERENCES products(id)
);

CREATE TABLE IF NOT EXISTS supplier_returns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id INTEGER NOT NULL,
    purchase_id INTEGER NOT NULL,
    reason TEXT NOT NULL DEFAULT '',
    total_cents INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER,
    FOREIGN KEY(supplier_id) REFERENCES suppliers(id),
    FOREIGN KEY(purchase_id) REFERENCES purchases(id),
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS supplier_return_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_return_id INTEGER NOT NULL,
    purchase_item_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    qty REAL NOT NULL,
    unit_cost_cents INTEGER NOT NULL,
    line_total_cents INTEGER NOT NULL,
    FOREIGN KEY(supplier_return_id) REFERENCES supplier_returns(id) ON DELETE CASCADE,
    FOREIGN KEY(purchase_item_id) REFERENCES purchase_items(id),
    FOREIGN KEY(product_id) REFERENCES products(id)
);

CREATE TABLE IF NOT EXISTS returns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    return_no TEXT NOT NULL UNIQUE,
    sale_id INTEGER NOT NULL,
    session_id INTEGER NOT NULL,
    cashier_user_id INTEGER NOT NULL,
    total_cents INTEGER NOT NULL,
    refund_method TEXT NOT NULL DEFAULT 'CASH',
    reason TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(sale_id) REFERENCES sales(id),
    FOREIGN KEY(session_id) REFERENCES cash_sessions(id),
    FOREIGN KEY(cashier_user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS return_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    return_id INTEGER NOT NULL,
    payment_method TEXT NOT NULL,
    amount_cents INTEGER NOT NULL,
    FOREIGN KEY(return_id) REFERENCES returns(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_return_payments_return ON return_payments(return_id);

CREATE TABLE IF NOT EXISTS return_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    return_id INTEGER NOT NULL,
    sale_item_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    qty REAL NOT NULL,
    unit_price_cents INTEGER NOT NULL,
    line_total_cents INTEGER NOT NULL,
    FOREIGN KEY(return_id) REFERENCES returns(id) ON DELETE CASCADE,
    FOREIGN KEY(sale_item_id) REFERENCES sale_items(id),
    FOREIGN KEY(product_id) REFERENCES products(id)
);

CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    label TEXT NOT NULL,
    amount_cents INTEGER NOT NULL,
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(session_id) REFERENCES cash_sessions(id),
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS cash_movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    movement_type TEXT NOT NULL,
    amount_cents INTEGER NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(session_id) REFERENCES cash_sessions(id),
    FOREIGN KEY(user_id) REFERENCES users(id)
);


CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS loyalty_movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    points_delta INTEGER NOT NULL,
    reason TEXT NOT NULL DEFAULT '',
    ref_type TEXT NOT NULL DEFAULT '',
    ref_id INTEGER,
    user_id INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(client_id) REFERENCES clients(id),
    FOREIGN KEY(user_id) REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS idx_loyalty_client ON loyalty_movements(client_id,id);

CREATE TABLE IF NOT EXISTS client_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    sale_id INTEGER,
    amount_cents INTEGER NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(client_id) REFERENCES clients(id),
    FOREIGN KEY(sale_id)   REFERENCES sales(id)
);
CREATE INDEX IF NOT EXISTS idx_client_payments_client ON client_payments(client_id);


CREATE TABLE IF NOT EXISTS product_categories (
    product_id  INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    PRIMARY KEY(product_id, category_id),
    FOREIGN KEY(product_id)  REFERENCES products(id)  ON DELETE CASCADE,
    FOREIGN KEY(category_id) REFERENCES categories(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_product_categories_cat ON product_categories(category_id);
CREATE INDEX IF NOT EXISTS idx_product_categories_product ON product_categories(product_id,category_id);


CREATE TABLE IF NOT EXISTS supplier_payments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id INTEGER NOT NULL,
    purchase_id INTEGER,
    amount_cents INTEGER NOT NULL,
    note        TEXT NOT NULL DEFAULT '',
    payment_method TEXT NOT NULL DEFAULT 'CARD',
    session_id  INTEGER REFERENCES cash_sessions(id),
    user_id     INTEGER REFERENCES users(id),
    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(supplier_id) REFERENCES suppliers(id),
    FOREIGN KEY(purchase_id) REFERENCES purchases(id)
);
CREATE INDEX IF NOT EXISTS idx_supplier_payments_sup ON supplier_payments(supplier_id);

INSERT OR IGNORE INTO settings(key,value) VALUES
('shop_name','ToDo'),
('currency','DH'),
('country_code','MA'),
('tax_label','Tax'),
('allow_negative_stock','1'),
('manual_stock_edit_enabled','1'),
('stock_management_enabled','1'),
('receipt_footer','Merci pour votre visite'),
('custom_shortcuts','calculator,held,drawer'),
('backup_on_close','1'),
('loyalty_enabled','0'),
('loyalty_earn_every_cents','1000'),
('loyalty_point_value_cents','50'),
('printer_receipt_name',''),
('printer_report_name',''),
('printer_addition_name',''),
('printer_kitchen_c1_name',''),
('printer_kitchen_c2_name',''),
('printer_kitchen_c3_name',''),
('printer_kitchen_c4_name',''),
('receipt_template','FR_3C'),
('scale_enabled','0'),
('scale_port',''),
('scale_baudrate','9600'),
('scale_timeout_ms','800'),
('email_enabled','0'),
('smtp_host','smtp.gmail.com'),
('smtp_port','587'),
('smtp_user',''),
('smtp_app_password',''),
('smtp_from_name','ToDo'),
('rfid_enabled','0'),
('rfid_mode','HID'),
('rfid_port',''),
('rfid_baudrate','9600'),
('rfid_timeout_ms','800'),
('customer_serial_enabled','0'),
('customer_serial_port',''),
('customer_serial_baudrate','9600'),
('customer_serial_timeout_ms','500'),
('customer_serial_width','20'),
('receipt_show_payment','1'),
('receipt_show_ticket_no','1'),
('receipt_show_sale_mode','1'),
('receipt_show_barcode','0'),
('receipt_next_client_ticket','1'),
('workstation_code','01'),
('license_enforced','0'),
('license_public_key_b64','');
"""

class Connection(sqlite3.Connection):
    def __exit__(self, *args):
        try:
            return super().__exit__(*args)
        finally:
            self.close()


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=15, factory=Connection)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn

def init_db():
    with connect() as conn:
        if conn.execute("SELECT 1 FROM sqlite_master WHERE name='products'").fetchone() and conn.execute('PRAGMA user_version').fetchone()[0] < 121:
            from datetime import datetime
            backup_dir=DB_PATH.parent / 'migration_backups'
            backup_dir.mkdir(parents=True,exist_ok=True)
            destination=sqlite3.connect(backup_dir / f"before_121_{datetime.now():%Y%m%d_%H%M%S_%f}.db")
            try:
                conn.backup(destination)
            finally:
                destination.close()
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(SCHEMA)
        migrate(conn)
        conn.commit()

def get_setting(key, default="", conn=None):
    if conn is None:
        with connect() as db:
            return get_setting(key, default, db)
    r = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return r["value"] if r else default

def set_setting(key, value):
    with connect() as conn:
        conn.execute(
            "INSERT INTO settings(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(value))
        )
        conn.commit()


def migrate(conn):
    # Agreed shop policy: keep checkout available when stock counts lag behind.
    # Apply once to existing installations; subsequent explicit settings survive.
    if not conn.execute("SELECT 1 FROM settings WHERE key='negative_stock_policy_v1'").fetchone():
        conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('allow_negative_stock','1')")
        conn.execute("INSERT INTO settings(key,value) VALUES('negative_stock_policy_v1','1')")
    additions = {
        'quantity_prices': {'pricing_mode': "TEXT NOT NULL DEFAULT 'UNIT'"},
        'products': {'supplier_code': "TEXT NOT NULL DEFAULT ''", 'alias': "TEXT NOT NULL DEFAULT ''", 'is_misc': 'INTEGER NOT NULL DEFAULT 0', 'preferred_supplier_id': 'INTEGER REFERENCES suppliers(id)', 'show_in_sale_photos': 'INTEGER NOT NULL DEFAULT 0', 'tax_rate_basis_points': 'INTEGER NOT NULL DEFAULT 0', 'tax_included': 'INTEGER NOT NULL DEFAULT 1'},
        'stock_movements': {'user_id': 'INTEGER REFERENCES users(id)', 'old_qty': 'REAL'},
        'sale_items': {'net_total_cents': 'INTEGER', 'qty_multiplier': 'REAL NOT NULL DEFAULT 1', 'pricing_mode': "TEXT NOT NULL DEFAULT 'UNIT'", 'tax_rate_basis_points': 'INTEGER NOT NULL DEFAULT 0', 'tax_included': 'INTEGER NOT NULL DEFAULT 1', 'tax_net_cents': 'INTEGER NOT NULL DEFAULT 0', 'tax_amount_cents': 'INTEGER NOT NULL DEFAULT 0', 'tax_gross_cents': 'INTEGER NOT NULL DEFAULT 0'},
        'held_sales': {'discount_cents': 'INTEGER NOT NULL DEFAULT 0', 'client_id': 'INTEGER REFERENCES clients(id)', 'seller_id': 'INTEGER REFERENCES sellers(id)', 'price_grid_id': 'INTEGER REFERENCES price_grids(id)', 'payment_method': "TEXT NOT NULL DEFAULT 'CASH'"},
        'returns': {'refund_paid_cents': 'INTEGER'},
        'client_payments': {'session_id': 'INTEGER REFERENCES cash_sessions(id)', 'user_id': 'INTEGER REFERENCES users(id)', 'payment_method': "TEXT NOT NULL DEFAULT 'CASH'"},
        'supplier_payments': {'session_id': 'INTEGER REFERENCES cash_sessions(id)', 'user_id': 'INTEGER REFERENCES users(id)', 'payment_method': "TEXT NOT NULL DEFAULT 'CARD'"},
        'sales': {'client_id': 'INTEGER REFERENCES clients(id)', 'seller_id': 'INTEGER REFERENCES sellers(id)', 'client_ticket_no': 'INTEGER', 'workstation_code': "TEXT NOT NULL DEFAULT '01'", 'stock_tracked': 'INTEGER NOT NULL DEFAULT 1', 'country_code': "TEXT NOT NULL DEFAULT 'MA'", 'tax_label_snapshot': "TEXT NOT NULL DEFAULT 'Tax'", 'tax_total_cents': 'INTEGER NOT NULL DEFAULT 0'},
        'cash_sessions': {'workstation_code': "TEXT NOT NULL DEFAULT '01'", 'closed_by_user_id': 'INTEGER REFERENCES users(id)'},
        'categories': {'color': "TEXT NOT NULL DEFAULT '#2563EB'", 'icon': "TEXT NOT NULL DEFAULT ''"},
    }
    for table, fields in additions.items():
        existing = {r['name'] for r in conn.execute(f'PRAGMA table_info({table})')}
        for name, declaration in fields.items():
            if name not in existing:
                conn.execute(f'ALTER TABLE {table} ADD COLUMN {name} {declaration}')
    conn.execute('UPDATE stock_movements SET old_qty=stock_after-qty_delta WHERE old_qty IS NULL')
    conn.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('country_code','MA')")
    conn.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('tax_label','Tax')")
    if not conn.execute("SELECT 1 FROM settings WHERE key='tax_snapshot_v1'").fetchone():
        # Preserve historical receipt values as zero-tax snapshots before tax is enabled.
        conn.execute('UPDATE sale_items SET tax_net_cents=COALESCE(net_total_cents,line_total_cents), tax_amount_cents=0, tax_gross_cents=COALESCE(net_total_cents,line_total_cents)')
        conn.execute("INSERT INTO settings(key,value) VALUES('tax_snapshot_v1','1')")
    conn.execute("CREATE TABLE IF NOT EXISTS audit_log (id INTEGER PRIMARY KEY, user_id INTEGER, action TEXT NOT NULL, document TEXT NOT NULL, details TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
    conn.execute('CREATE INDEX IF NOT EXISTS idx_products_active_name ON products(active,name)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_products_sku ON products(sku)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_barcodes_product ON product_barcodes(product_id)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_returns_sale_item ON return_items(sale_item_id)')
    conn.execute("INSERT OR IGNORE INTO settings VALUES('search_limit','60')")
    # Allocate historical ticket discounts deterministically, without altering old receipts.
    from services.money import allocate
    for sale in conn.execute('SELECT * FROM sales WHERE id IN (SELECT sale_id FROM sale_items WHERE net_total_cents IS NULL)').fetchall():
        rows=conn.execute('SELECT id,line_total_cents FROM sale_items WHERE sale_id=? ORDER BY id',(sale['id'],)).fetchall()
        nets=allocate(sale['total_cents'], [r['line_total_cents'] for r in rows])
        conn.executemany('UPDATE sale_items SET net_total_cents=? WHERE id=?',[(n,r['id']) for r,n in zip(rows,nets)])
    try:
        if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='product_search'").fetchone():
            conn.execute("CREATE VIRTUAL TABLE product_search USING fts5(name,sku,alias,supplier_code,content='products',content_rowid='id',tokenize='trigram')")
            conn.execute("INSERT INTO product_search(product_search) VALUES('rebuild')")
        conn.executescript("""
        CREATE TRIGGER IF NOT EXISTS products_search_insert AFTER INSERT ON products BEGIN
          INSERT INTO product_search(rowid,name,sku,alias,supplier_code) VALUES(new.id,new.name,new.sku,new.alias,new.supplier_code);
        END;
        CREATE TRIGGER IF NOT EXISTS products_search_delete AFTER DELETE ON products BEGIN
          INSERT INTO product_search(product_search,rowid,name,sku,alias,supplier_code) VALUES('delete',old.id,old.name,old.sku,old.alias,old.supplier_code);
        END;
        CREATE TRIGGER IF NOT EXISTS products_search_update AFTER UPDATE OF name,sku,alias,supplier_code ON products BEGIN
          INSERT INTO product_search(product_search,rowid,name,sku,alias,supplier_code) VALUES('delete',old.id,old.name,old.sku,old.alias,old.supplier_code);
          INSERT INTO product_search(rowid,name,sku,alias,supplier_code) VALUES(new.id,new.name,new.sku,new.alias,new.supplier_code);
        END;
        """)
    except sqlite3.OperationalError as error:
        if 'no such module' not in str(error) and 'no such tokenizer' not in str(error):
            raise
    if not conn.execute("SELECT 1 FROM settings WHERE key='categories_junction_v1'").fetchone():
        conn.execute('INSERT OR IGNORE INTO product_categories(product_id,category_id) SELECT id,category_id FROM products WHERE category_id IS NOT NULL')
        conn.execute("INSERT INTO settings(key,value) VALUES('categories_junction_v1','1')")
    conn.executescript("""
        CREATE TRIGGER IF NOT EXISTS product_primary_category_insert AFTER INSERT ON products
        WHEN new.category_id IS NOT NULL BEGIN
          INSERT OR IGNORE INTO product_categories VALUES(new.id,new.category_id);
        END;
        CREATE TRIGGER IF NOT EXISTS product_primary_category_update AFTER UPDATE OF category_id ON products
        WHEN old.category_id IS NOT new.category_id BEGIN
          DELETE FROM product_categories WHERE product_id=new.id AND category_id=old.category_id;
          INSERT OR IGNORE INTO product_categories SELECT new.id,new.category_id WHERE new.category_id IS NOT NULL;
        END;
    """)
    # Backfill one payment row for legacy sales; new sales write their split directly.
    conn.execute("INSERT INTO sale_payments(sale_id,payment_method,amount_cents) SELECT s.id,s.payment_method,CASE WHEN s.payment_method='CASH' THEN s.paid_cents-s.change_cents ELSE s.paid_cents END FROM sales s WHERE NOT EXISTS (SELECT 1 FROM sale_payments sp WHERE sp.sale_id=s.id)")
    conn.execute("INSERT INTO return_payments(return_id,payment_method,amount_cents) SELECT r.id,r.refund_method,COALESCE(r.refund_paid_cents,r.total_cents) FROM returns r WHERE r.refund_method IN ('CASH','CARD') AND NOT EXISTS (SELECT 1 FROM return_payments rp WHERE rp.return_id=r.id)")
    conn.execute('PRAGMA user_version=124')
