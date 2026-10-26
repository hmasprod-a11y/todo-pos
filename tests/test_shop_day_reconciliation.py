"""One deterministic ledger across purchases, POS, debts, returns and closure."""
import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'todo'))
import database as db
from services.bootstrap import ensure_defaults
from services.security import current_user
from services.cash import open_session,record_cash,session_totals,close_session
from services.sales import complete_sale,create_return
from services.clients import save_client,add_payment,get_client
from services.suppliers import save_supplier
from services.purchases import receive_purchase
from services.supplier_returns import create_supplier_return,purchase_returnable_lines
from services.supplier_payments import add_supplier_payment,supplier_credit_statement
from services.reports import today_summary,period_summary,payment_breakdown,sales_evolution

class ShopDayReconciliationTests(unittest.TestCase):
    def test_full_shop_day_has_one_reconciled_cash_stock_and_debt_ledger(self):
        with tempfile.TemporaryDirectory() as td:
            old=db.DB_PATH;db.DB_PATH=Path(td)/'shop.db';db.init_db();ensure_defaults()
            with db.connect() as c:
                uid=c.execute('SELECT id FROM users LIMIT 1').fetchone()[0]
                pid=c.execute("INSERT INTO products(name,sale_price_cents) VALUES('Rice',1000)").lastrowid
            token=current_user.set(uid)
            try:
                session=open_session(uid,10000);client=save_client('Client');supplier=save_supplier('Supplier')
                purchase,_=receive_purchase(supplier,'SHOP-DAY',[dict(product_id=pid,qty=10,unit_cost_cents=500)],paid_cents=1000,payment_method='CASH')
                cart=lambda qty:[dict(product_id=pid,qty=qty,unit_price_cents=1000)]
                complete_sale(session,uid,cart(2),'CASH',2000,discount_cents=100,request_key='cash')
                mixed=complete_sale(session,uid,cart(2),'MIXED',2000,payments=[('CASH',600),('CARD',1400)],request_key='mixed')
                credit=complete_sale(session,uid,cart(3),'CREDIT',500,client_id=client,request_key='credit')
                add_payment(client,1000,sale_id=credit['id'])
                with db.connect() as c:item=c.execute('SELECT id FROM sale_items WHERE sale_id=?',(mixed['id'],)).fetchone()[0]
                create_return(mixed['id'],session,uid,[(item,1)],refund_method='AUTO')
                line=purchase_returnable_lines(purchase)[0]
                create_supplier_return(purchase,[(line['purchase_item_id'],1)],'Damaged')
                add_supplier_payment(supplier,500,purchase_id=purchase,payment_method='CASH')
                record_cash(session,uid,200,'EXPENSE','Transport');record_cash(session,uid,300,'IN','Float');record_cash(session,uid,100,'OUT','Withdrawal')
                self.assertEqual(get_client(client)['balance_cents'],1500)
                self.assertEqual(supplier_credit_statement()[0]['balance_cents'],3000)
                with db.connect() as c:
                    self.assertEqual(c.execute('SELECT stock_qty FROM products WHERE id=?',(pid,)).fetchone()[0],3)
                    self.assertEqual(c.execute('SELECT SUM(qty_delta) FROM stock_movements WHERE product_id=?',(pid,)).fetchone()[0],3)
                    self.assertEqual(session_totals(c,session),dict(cash_sales=3000,card_sales=1400,cash_returns=300,expenses=200,cash_in=1300,cash_out=1600))
                self.assertEqual(today_summary()['net_sales'],5900);self.assertEqual(period_summary()['gross_margin'],2900)
                self.assertEqual(sum(sales_evolution('month')[1]),5900)
                self.assertEqual(sum(payment_breakdown().values()),3400) # 3000 collected sales -1000 refund +1400 card
                expected,difference,_=close_session(session,12200)
                self.assertEqual((expected,difference),(12200,0))
            finally:current_user.reset(token);db.DB_PATH=old
