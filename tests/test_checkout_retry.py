import sys,tempfile,unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'todo'))
import database as db
from services.security import current_user,hash_pin
from services.cash import open_session
from services.sales import complete_sale,hold_sale,list_held,resume_held

class CheckoutRetryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.old=db.DB_PATH;db.DB_PATH=Path(self.tmp.name)/'db.sqlite';db.init_db()
        with db.connect() as c:
            self.uid=c.execute("INSERT INTO users(username,display_name,pin_hash,role) VALUES('admin','Admin',?,'admin')",(hash_pin('fixture'),)).lastrowid
            self.other=c.execute("INSERT INTO users(username,display_name,pin_hash,role) VALUES('other','Other',?,'admin')",(hash_pin('fixture'),)).lastrowid
            self.pid=c.execute("INSERT INTO products(name,sale_price_cents,stock_qty) VALUES('Product',1000,100)").lastrowid
        self.token=current_user.set(self.uid);self.session=open_session(self.uid,0);self.cart=[dict(product_id=self.pid,qty=2,unit_price_cents=1000)]
    def tearDown(self):current_user.reset(self.token);db.DB_PATH=self.old;self.tmp.cleanup()
    def sale(self,**kw):return complete_sale(self.session,self.uid,self.cart,'CASH',2000,request_key='fixture-request',**kw)
    def assert_once(self):
        with db.connect() as c:
            self.assertEqual(tuple(c.execute('SELECT stock_qty,(SELECT COUNT(*) FROM sales),(SELECT COUNT(*) FROM sale_payments),(SELECT COUNT(*) FROM checkout_requests) FROM products WHERE id=?',(self.pid,)).fetchone()),(98,1,1,1))
    def test_retry_returns_original_result_and_no_second_effect(self):
        first=self.sale();db.init_db();self.assertEqual(self.sale(),first);self.assert_once()
    def test_backup_restore_preserves_idempotency_journal(self):
        from services import backup
        from unittest.mock import patch
        first=self.sale()
        with patch.object(backup,'DB_PATH',db.DB_PATH),patch.object(backup,'BASE',Path(self.tmp.name)):
            snapshot=backup.create_backup()
            with db.connect() as c:c.execute('DELETE FROM checkout_requests')
            backup.restore_backup(snapshot)
        self.assertEqual(self.sale(),first);self.assert_once()

    def test_concurrent_submissions_only_commit_once(self):
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:self.sale(),range(2)))
        self.assertEqual(results[0],results[1]);self.assert_once()
    def test_changed_request_cannot_reuse_key(self):
        self.sale();self.cart[0]['qty']=1
        with self.assertRaises(ValueError):self.sale()
        self.assert_once()
    def test_rollback_does_not_consume_key(self):
        self.cart[0]['qty']=0
        with self.assertRaises(ValueError):self.sale()
        self.cart[0]['qty']=2;self.sale();self.assert_once()
    def test_held_retry_returns_committed_sale(self):
        hid=hold_sale(self.uid,self.cart);first=self.sale(held_id=hid)
        self.assertEqual(self.sale(held_id=hid),first);self.assert_once()
        with self.assertRaises(ValueError):complete_sale(self.session,self.uid,self.cart,'CASH',2000,held_id=hid)
    def test_concurrent_held_consumption_without_key(self):
        hid=hold_sale(self.uid,self.cart)
        def submit(_):
            try:return complete_sale(self.session,self.uid,self.cart,'CASH',2000,held_id=hid)['id']
            except ValueError:return None
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(submit,range(2)))
        self.assertEqual(sum(x is not None for x in results),1)
        with db.connect() as c:self.assertEqual(c.execute('SELECT stock_qty FROM products WHERE id=?',(self.pid,)).fetchone()[0],98)
    def test_held_list_and_resume_obey_ownership(self):
        mine=hold_sale(self.uid,self.cart);current_user.set(self.other);theirs=hold_sale(self.other,self.cart)
        self.assertEqual([r['id'] for r in list_held()],[theirs])
        with self.assertRaises(PermissionError):resume_held(mine)
        current_user.set(self.uid);self.assertEqual([r['id'] for r in list_held()],[mine])
