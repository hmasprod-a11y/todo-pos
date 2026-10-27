import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'todo'))
import database
from services.bootstrap import ensure_defaults
from services.security import current_user
from services.inventory_sessions import create_inventory_session,list_inventory_sessions,inventory_session_lines,set_inventory_count,finalize_inventory_session

class InventorySessionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.old=database.DB_PATH;database.DB_PATH=Path(self.tmp.name)/'db.sqlite'
        database.init_db();ensure_defaults()
        with database.connect() as c:
            self.uid=c.execute("SELECT id FROM users").fetchone()[0]
            self.pid=c.execute("INSERT INTO products(name,purchase_price_cents,stock_qty,active) VALUES('Count Me',500,10,1)").lastrowid
        self.token=current_user.set(self.uid)
    def tearDown(self):
        current_user.reset(self.token);database.DB_PATH=self.old;self.tmp.cleanup()
    def test_inventory_session_snapshots_and_finalizes(self):
        sid=create_inventory_session('Monthly count')
        row=next(r for r in inventory_session_lines(sid) if r['product_id']==self.pid)
        self.assertEqual(row['theory_qty'],10);self.assertIsNone(row['counted_qty'])
        set_inventory_count(sid,self.pid,7)
        self.assertEqual(next(r for r in inventory_session_lines(sid) if r['product_id']==self.pid)['counted_qty'],7)
        with database.connect() as c:self.assertEqual(c.execute("SELECT stock_qty FROM products WHERE id=?",(self.pid,)).fetchone()[0],10)
        adjusted=finalize_inventory_session(sid);self.assertEqual(adjusted,1)
        with database.connect() as c:self.assertEqual(c.execute("SELECT stock_qty FROM products WHERE id=?",(self.pid,)).fetchone()[0],7)
        self.assertEqual(list_inventory_sessions()[0]['status'],'VALIDATED')
    def test_validated_inventory_cannot_be_edited_twice(self):
        sid=create_inventory_session();set_inventory_count(sid,self.pid,9);finalize_inventory_session(sid)
        with self.assertRaises(ValueError):set_inventory_count(sid,self.pid,8)
        with self.assertRaises(ValueError):finalize_inventory_session(sid)

    def test_whole_unit_product_rejects_fractional_inventory_count(self):
        sid=create_inventory_session()
        with self.assertRaisesRegex(ValueError,'unités entières'):
            set_inventory_count(sid,self.pid,7.5)
        self.assertIsNone(next(r for r in inventory_session_lines(sid) if r['product_id']==self.pid)['counted_qty'])
    def test_fractional_product_accepts_fractional_inventory_count(self):
        with database.connect() as c:c.execute('UPDATE products SET allow_fraction=1 WHERE id=?',(self.pid,))
        sid=create_inventory_session();set_inventory_count(sid,self.pid,7.5)
        self.assertEqual(finalize_inventory_session(sid),1)
        with database.connect() as c:self.assertEqual(c.execute('SELECT stock_qty FROM products WHERE id=?',(self.pid,)).fetchone()[0],7.5)
    def test_deactivated_counted_product_keeps_inventory_open_and_stock_unchanged(self):
        with database.connect() as c:
            retired=c.execute("INSERT INTO products(name,purchase_price_cents,stock_qty,active) VALUES('Z retired',500,5,1)").lastrowid
        sid=create_inventory_session();set_inventory_count(sid,self.pid,8);set_inventory_count(sid,retired,4)
        with database.connect() as c:c.execute('UPDATE products SET active=0 WHERE id=?',(retired,))
        with self.assertRaisesRegex(ValueError,'inactif'):finalize_inventory_session(sid)
        with database.connect() as c:
            self.assertEqual(c.execute('SELECT stock_qty FROM products WHERE id=?',(self.pid,)).fetchone()[0],10)
            self.assertEqual(c.execute('SELECT status FROM inventory_sessions WHERE id=?',(sid,)).fetchone()[0],'OPEN')
            self.assertEqual(c.execute("SELECT COUNT(*) FROM stock_movements WHERE ref_type='inventory_session' AND ref_id=?",(sid,)).fetchone()[0],0)

if __name__=='__main__':unittest.main()
