import math
from decimal import Decimal
from services.money import rounded
from database import connect
from services.security import require_permission, audit
from services.inventory import apply_stock_movement

def receive_purchase(supplier_id, supplier_invoice, lines, notes="", paid_cents=0, payment_method="CARD", order_id=None):
    if not lines:
        raise ValueError("Réception vide")
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        require_permission('MANAGEMENT', conn)
        normalized=[]
        for x in lines:
            pid=int(x["product_id"]);qty=float(x["qty"]);cost=int(x["unit_cost_cents"])
            if not math.isfinite(qty) or qty <= 0 or cost < 0:
                raise ValueError("Quantité réception invalide")
            product=conn.execute("SELECT allow_fraction FROM products WHERE id=? AND active=1",(pid,)).fetchone()
            if not product:
                raise ValueError("Article introuvable")
            if not product["allow_fraction"] and not qty.is_integer():
                raise ValueError("Quantité fractionnée interdite pour cet article")
            normalized.append((pid,qty,cost))
        if order_id is not None:
            order=conn.execute('SELECT supplier_id,status FROM purchase_orders WHERE id=?',(int(order_id),)).fetchone()
            if not order or order['status']!='OPEN':raise ValueError('Commande introuvable ou déjà réceptionnée.')
            if order['supplier_id']!=supplier_id:raise ValueError('Fournisseur incompatible avec la commande.')
            def quantities(rows):
                result={}
                for pid,qty in rows:result[pid]=result.get(pid,Decimal(0))+Decimal(str(qty))
                return result
            expected=quantities(conn.execute('SELECT product_id,qty FROM purchase_order_items WHERE order_id=?',(int(order_id),)))
            actual=quantities((pid,qty) for pid,qty,cost in normalized)
            if actual!=expected:raise ValueError('Réception partielle non disponible : les quantités doivent correspondre à la commande complète.')
        total = sum(rounded(Decimal(str(qty)) * cost) for pid,qty,cost in normalized)
        paid_cents = int(paid_cents or 0)
        payment_method = str(payment_method).upper()
        if paid_cents < 0 or paid_cents > total:
            raise ValueError("Règlement fournisseur invalide")
        if payment_method not in ('CASH','CARD'):
            raise ValueError("Mode de paiement invalide")
        if supplier_id:
            supplier=conn.execute("SELECT 1 FROM suppliers WHERE id=? AND active=1",(supplier_id,)).fetchone()
            if not supplier:
                raise ValueError("Fournisseur introuvable")
        if paid_cents and not supplier_id:
            raise ValueError("Fournisseur obligatoire pour enregistrer un règlement")
        invoice = (supplier_invoice or "").strip()
        if supplier_id and invoice:
            duplicate = conn.execute("SELECT id FROM purchases WHERE supplier_id=? AND lower(trim(supplier_invoice))=lower(?) LIMIT 1", (supplier_id, invoice)).fetchone()
            if duplicate:
                raise ValueError("Facture fournisseur déjà enregistrée.")
        cur = conn.execute(
            "INSERT INTO purchases(supplier_id,supplier_invoice,total_cents,notes) VALUES(?,?,?,?)",
            (supplier_id or None, invoice, total, notes or "")
        )
        pid_purchase = cur.lastrowid
        for pid,qty,cost in normalized:
            lt=rounded(Decimal(str(qty)) * cost)
            conn.execute(
                "INSERT INTO purchase_items(purchase_id,product_id,qty,unit_cost_cents,line_total_cents) VALUES(?,?,?,?,?)",
                (pid_purchase,pid,qty,cost,lt)
            )
            conn.execute("UPDATE products SET purchase_price_cents=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",(cost,pid))
            apply_stock_movement(conn,pid,qty,"PURCHASE",cost,"purchase",pid_purchase,invoice)
        if paid_cents:
            session_id = user_id = None
            if payment_method == 'CASH':
                from services.cash import get_open_session
                from services.security import current_user
                session = get_open_session()
                user_id = current_user.get()
                if not session:
                    raise ValueError("Ouvrez la caisse avant un règlement fournisseur en espèces.")
                if user_id is None or int(session['user_id']) != int(user_id):
                    raise PermissionError("Cette caisse appartient à un autre utilisateur.")
                session_id = int(session['id'])
            payment_id=conn.execute(
                "INSERT INTO supplier_payments(supplier_id,purchase_id,amount_cents,note,payment_method,session_id,user_id) VALUES(?,?,?,?,?,?,?)",
                (supplier_id,pid_purchase,paid_cents,"Règlement à la réception",payment_method,session_id,user_id)
            ).lastrowid
            audit(conn,"SUPPLIER_PAYMENT",payment_id,str(paid_cents))
        if order_id is not None:
            conn.execute('INSERT INTO purchase_order_receipts(order_id,purchase_id) VALUES(?,?)',(int(order_id),pid_purchase))
            conn.execute("UPDATE purchase_orders SET status='RECEIVED',received_at=CURRENT_TIMESTAMP WHERE id=?",(int(order_id),))
            audit(conn,'PURCHASE_ORDER_RECEIVED',order_id,str(pid_purchase))
        audit(conn,"PURCHASE_RECEIVE",pid_purchase,str(total))
        conn.commit()
        return pid_purchase, total


def create_purchase_order(supplier_id, lines, notes=''):
    if not supplier_id or not lines:
        raise ValueError("Fournisseur et lignes obligatoires")
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        require_permission('MANAGEMENT', conn)
        if not conn.execute("SELECT 1 FROM suppliers WHERE id=? AND active=1",(supplier_id,)).fetchone():
            raise ValueError("Fournisseur introuvable")
        normalized=[]
        for x in lines:
            pid=int(x["product_id"]);qty=float(x["qty"]);cost=int(x.get("unit_cost_cents") or 0)
            if not math.isfinite(qty) or qty<=0 or cost<0:
                raise ValueError("Ligne commande invalide")
            p=conn.execute("SELECT allow_fraction FROM products WHERE id=? AND active=1",(pid,)).fetchone()
            if not p:
                raise ValueError("Article introuvable")
            if not p["allow_fraction"] and not qty.is_integer():
                raise ValueError("Quantité fractionnée interdite pour cet article")
            normalized.append((pid,qty,cost))
        oid=conn.execute("INSERT INTO purchase_orders(supplier_id,notes) VALUES(?,?)",(supplier_id,notes or "")).lastrowid
        conn.executemany("INSERT INTO purchase_order_items(order_id,product_id,qty,unit_cost_cents) VALUES(?,?,?,?)",[(oid,*x) for x in normalized])
        audit(conn,"PURCHASE_ORDER_CREATE",oid,str(len(normalized)))
        conn.commit()
        return oid

def list_purchase_orders(status='OPEN'):
    with connect() as conn:
        return [dict(r) for r in conn.execute("""
            SELECT po.id,po.supplier_id,po.status,po.created_at,po.received_at,po.notes,s.name supplier_name,
                   COUNT(poi.id) lines,COALESCE(SUM(poi.qty*poi.unit_cost_cents),0) total_cents
            FROM purchase_orders po JOIN suppliers s ON s.id=po.supplier_id
            LEFT JOIN purchase_order_items poi ON poi.order_id=po.id
            WHERE (?='' OR po.status=?)
            GROUP BY po.id ORDER BY po.id DESC
        """,(status,status)).fetchall()]

def purchase_order_lines(order_id):
    with connect() as conn:
        return [dict(r) for r in conn.execute("""
            SELECT poi.product_id,p.name,poi.qty,poi.unit_cost_cents
            FROM purchase_order_items poi JOIN products p ON p.id=poi.product_id
            WHERE poi.order_id=? ORDER BY poi.id
        """,(order_id,)).fetchall()]

def mark_purchase_order_received(order_id):
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        require_permission('MANAGEMENT', conn)
        if conn.execute("UPDATE purchase_orders SET status='RECEIVED',received_at=CURRENT_TIMESTAMP WHERE id=? AND status='OPEN'",(order_id,)).rowcount!=1:
            raise ValueError("Commande introuvable ou déjà clôturée")
        audit(conn,"PURCHASE_ORDER_RECEIVED",order_id)
        conn.commit()

def cancel_purchase_order(order_id):
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        require_permission('MANAGEMENT', conn)
        if conn.execute("UPDATE purchase_orders SET status='CANCELLED' WHERE id=? AND status='OPEN'",(order_id,)).rowcount!=1:
            raise ValueError("Commande introuvable ou déjà clôturée")
        audit(conn,"PURCHASE_ORDER_CANCEL",order_id)
        conn.commit()

