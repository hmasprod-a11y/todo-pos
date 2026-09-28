import math
from database import connect
from services.security import require_permission,current_user,audit
from services.pricing import resolve_unit_price
from services.money import rounded

def create_customer_order(client_id, lines, delivery_address='', notes=''):
    if not lines: raise ValueError("Commande vide")
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE");require_permission('MANAGEMENT', conn)
        client=conn.execute("SELECT id FROM clients WHERE id=? AND active=1",(int(client_id),)).fetchone()
        if not client: raise ValueError("Client introuvable")
        normalized=[];total=0
        for x in lines:
            pid=int(x['product_id']);qty=float(x['qty'])
            if not math.isfinite(qty) or qty<=0: raise ValueError("Quantité invalide")
            p=conn.execute("SELECT id,name,allow_fraction FROM products WHERE id=? AND active=1",(pid,)).fetchone()
            if not p: raise ValueError("Article introuvable")
            if not p['allow_fraction'] and not qty.is_integer(): raise ValueError("Quantité fractionnée interdite")
            unit=int(x.get('unit_price_cents') if x.get('unit_price_cents') is not None else resolve_unit_price(pid,qty,None,conn))
            if unit<0: raise ValueError("Prix invalide")
            line_total=rounded(unit*qty);total+=line_total
            normalized.append((pid,p['name'],qty,unit,line_total))
        uid=current_user.get()
        oid=conn.execute("""INSERT INTO customer_orders(client_id,delivery_address,notes,total_cents,created_by)
                            VALUES(?,?,?,?,?)""",(int(client_id),(delivery_address or '').strip(),(notes or '').strip(),total,uid)).lastrowid
        conn.executemany("""INSERT INTO customer_order_items(order_id,product_id,name_snapshot,qty,unit_price_cents,line_total_cents)
                            VALUES(?,?,?,?,?,?)""",[(oid,*r) for r in normalized])
        audit(conn,'CUSTOMER_ORDER_CREATE',oid,str(total),uid);conn.commit()
        return oid,total

def list_customer_orders(status=''):
    with connect() as conn:
        return [dict(r) for r in conn.execute("""
            SELECT o.*,c.name client_name,c.phone,
                   COALESCE(u.display_name,'') created_by_name
            FROM customer_orders o
            JOIN clients c ON c.id=o.client_id
            LEFT JOIN users u ON u.id=o.created_by
            WHERE (?='' OR o.status=?)
            ORDER BY o.id DESC
        """,(status,status)).fetchall()]

def customer_order_lines(order_id):
    with connect() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM customer_order_items WHERE order_id=? ORDER BY id",(int(order_id),)).fetchall()]

def set_customer_order_status(order_id,status):
    status=str(status).upper()
    if status not in ('OPEN','READY','CANCELLED'): raise ValueError("Statut invalide")
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE");require_permission('MANAGEMENT', conn)
        row=conn.execute("SELECT status FROM customer_orders WHERE id=?",(int(order_id),)).fetchone()
        if not row or row['status'] in ('COMPLETED','CANCELLED'): raise ValueError("Commande déjà clôturée")
        conn.execute("UPDATE customer_orders SET status=? WHERE id=?",(status,int(order_id)))
        audit(conn,'CUSTOMER_ORDER_STATUS',order_id,status);conn.commit()

def order_cart(order_id):
    with connect() as conn:
        order=conn.execute("""SELECT o.*,c.name client_name FROM customer_orders o
                              JOIN clients c ON c.id=o.client_id WHERE o.id=?""",(int(order_id),)).fetchone()
        if not order or order['status'] not in ('OPEN','READY'): raise ValueError("Commande indisponible")
        lines=[dict(r) for r in conn.execute("""SELECT product_id,name_snapshot name,qty,unit_price_cents
                                               FROM customer_order_items WHERE order_id=? ORDER BY id""",(int(order_id),)).fetchall()]
        return dict(order=dict(order),cart=lines)
