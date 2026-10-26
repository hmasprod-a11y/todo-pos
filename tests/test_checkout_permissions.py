import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'todo'))
import database as db
from services.security import current_user,hash_pin
from services.cash import open_session
from services.sales import complete_sale,hold_sale
from services.quotations import create_quotation
from services.customer_orders import create_customer_order

class CheckoutPermissionTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.old=db.DB_PATH;db.DB_PATH=Path(self.tmp.name)/'db.sqlite';db.init_db()
  with db.connect() as c:
   self.admin=c.execute("INSERT INTO users(username,display_name,pin_hash,role) VALUES('admin','Admin',?,'admin')",(hash_pin('fixture'),)).lastrowid
   self.user=c.execute("INSERT INTO users(username,display_name,pin_hash,role) VALUES('cash','Cash',?,'cashier')",(hash_pin('fixture'),)).lastrowid
   for permission in ('PRICE_EDIT','DISCOUNT'):c.execute('INSERT INTO user_permissions VALUES(?,?,0)',(self.user,permission))
   self.pid=c.execute("INSERT INTO products(name,sale_price_cents,stock_qty) VALUES('Product',1000,100)").lastrowid
   self.client=c.execute("INSERT INTO clients(name) VALUES('Client')").lastrowid
  self.token=current_user.set(self.user);self.session=open_session(self.user,0)
 def tearDown(self):current_user.reset(self.token);db.DB_PATH=self.old;self.tmp.cleanup()
 def sale(self,unit=1000,quantity=1,**kwargs):
  line=dict(product_id=self.pid,qty=quantity,unit_price_cents=unit)
  if 'line_discount' in kwargs:line['discount_cents']=kwargs.pop('line_discount')
  if 'barcode_id' in kwargs:line['barcode_id']=kwargs.pop('barcode_id')
  return complete_sale(self.session,self.user,[line],'CASH',100000,**kwargs)
 def unchanged(self):
  with db.connect() as c:return tuple(c.execute('SELECT stock_qty,(SELECT COUNT(*) FROM sales),(SELECT COUNT(*) FROM sale_payments),(SELECT COUNT(*) FROM stock_movements) FROM products WHERE id=?',(self.pid,)).fetchone())
 def test_direct_manual_price_is_rejected_without_permission(self):
  before=self.unchanged()
  with self.assertRaises(PermissionError):self.sale(1)
  self.assertEqual(self.unchanged(),before)
 def test_manual_flag_is_not_authorization(self):
  with self.assertRaises(PermissionError):complete_sale(self.session,self.user,[dict(product_id=self.pid,qty=1,unit_price_cents=1,manual_unit_price=True)],'CASH',1)
 def test_ticket_discount_needs_permission(self):
  before=self.unchanged()
  with self.assertRaises(PermissionError):self.sale(discount_cents=100)
  self.assertEqual(self.unchanged(),before)
 def test_line_discount_needs_permission(self):
  with self.assertRaises(PermissionError):self.sale(line_discount=100)
 def test_catalog_price_remains_allowed(self):self.assertEqual(self.sale()['total_cents'],1000)
 def test_explicit_permission_allows_override_and_audit(self):
  with db.connect() as c:c.execute("UPDATE user_permissions SET allowed=1 WHERE user_id=? AND permission='PRICE_EDIT'",(self.user,))
  result=self.sale(800)
  with db.connect() as c:self.assertEqual(c.execute("SELECT COUNT(*) FROM audit_log WHERE action='SALE_PRICE_OVERRIDE' AND document=?",(str(result['id']),)).fetchone()[0],1)
 def test_explicit_discount_permission(self):
  with db.connect() as c:c.execute("UPDATE user_permissions SET allowed=1 WHERE user_id=? AND permission='DISCOUNT'",(self.user,))
  self.assertEqual(self.sale(discount_cents=100,line_discount=100)['total_cents'],800)
 def test_active_price_grid_is_allowed(self):
  with db.connect() as c:
   gid=c.execute("INSERT INTO price_grids(name) VALUES('Pro')").lastrowid
   c.execute('INSERT INTO product_grid_prices(product_id,grid_id,unit_price_cents) VALUES(?,?,700)',(self.pid,gid))
  self.assertEqual(self.sale(700,price_grid_id=gid)['total_cents'],700)
  with self.assertRaises(PermissionError):self.sale(600,price_grid_id=gid)
 def test_quantity_offer_is_allowed(self):
  with db.connect() as c:c.execute("INSERT INTO quantity_prices(product_id,min_qty,unit_price_cents) VALUES(?,2,800)",(self.pid,))
  self.assertEqual(self.sale(800,quantity=2)['total_cents'],1600)
 def test_pack_price_is_allowed(self):
  with db.connect() as c:bid=c.execute("INSERT INTO product_barcodes(product_id,barcode,qty_multiplier,price_override_cents) VALUES(?,'PACK',6,4500)",(self.pid,)).lastrowid
  self.assertEqual(self.sale(750,quantity=6,barcode_id=bid)['total_cents'],4500)
 def document(self,order=False):
  current_user.set(self.admin)
  try:
   return (create_customer_order(self.client,[dict(product_id=self.pid,qty=2,unit_price_cents=600)]) if order else create_quotation([dict(product_id=self.pid,qty=2,unit_price_cents=600)],self.client))[0]
  finally:current_user.set(self.user)
 def test_agreed_quotation_price_is_allowed(self):
  qid=self.document();self.assertEqual(self.sale(600,quantity=2,quotation_id=qid,client_id=self.client)['total_cents'],1200)
 def test_agreed_order_price_is_allowed(self):
  oid=self.document(True);self.assertEqual(self.sale(600,quantity=2,customer_order_id=oid,client_id=self.client)['total_cents'],1200)
 def test_document_cannot_authorize_different_price(self):
  qid=self.document()
  with self.assertRaises(PermissionError):self.sale(1,quotation_id=qid,client_id=self.client)
 def test_document_cannot_authorize_excess_quantity(self):
  qid=self.document()
  with self.assertRaises(PermissionError):self.sale(600,quantity=3,quotation_id=qid,client_id=self.client)
 def test_split_rows_cannot_reuse_document_allowance(self):
  qid=self.document();line=dict(product_id=self.pid,qty=2,unit_price_cents=600)
  with self.assertRaises(PermissionError):complete_sale(self.session,self.user,[line,line],'CASH',100000,quotation_id=qid,client_id=self.client)
 def test_held_manual_override_is_rechecked(self):
  with db.connect() as c:c.execute("UPDATE user_permissions SET allowed=1 WHERE user_id=? AND permission='PRICE_EDIT'",(self.user,))
  held=hold_sale(self.user,[dict(product_id=self.pid,qty=1,unit_price_cents=500)])
  with db.connect() as c:c.execute("UPDATE user_permissions SET allowed=0 WHERE user_id=? AND permission='PRICE_EDIT'",(self.user,))
  with self.assertRaises(PermissionError):self.sale(500,held_id=held)

if __name__=='__main__':unittest.main()
