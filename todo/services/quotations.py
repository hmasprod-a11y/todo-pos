import math
from database import connect
from services.security import require_permission,current_user,audit
from services.pricing import resolve_unit_price
from services.money import rounded

def create_quotation(lines, client_id=None, valid_until=None, notes=''):
    if not lines: raise ValueError("Devis vide")
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE");require_permission('MANAGEMENT', conn)
        if client_id is not None and not conn.execute("SELECT 1 FROM clients WHERE id=? AND active=1",(int(client_id),)).fetchone():
            raise ValueError("Client introuvable")
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
        qid=conn.execute("""INSERT INTO quotations(client_id,valid_until,notes,total_cents,created_by)
                            VALUES(?,?,?,?,?)""",(client_id,valid_until,(notes or '').strip(),total,uid)).lastrowid
        conn.executemany("""INSERT INTO quotation_items(quotation_id,product_id,name_snapshot,qty,unit_price_cents,line_total_cents)
                            VALUES(?,?,?,?,?,?)""",[(qid,*r) for r in normalized])
        audit(conn,'QUOTATION_CREATE',qid,str(total),uid);conn.commit()
        return qid,total

def list_quotations(status=''):
    with connect() as conn:
        return [dict(r) for r in conn.execute("""
            SELECT q.*,COALESCE(c.name,'') client_name,COALESCE(c.phone,'') phone,COALESCE(u.display_name,'') created_by_name
            FROM quotations q
            LEFT JOIN clients c ON c.id=q.client_id
            LEFT JOIN users u ON u.id=q.created_by
            WHERE (?='' OR q.status=?)
            ORDER BY q.id DESC
        """,(status,status)).fetchall()]

def quotation_lines(quotation_id):
    with connect() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM quotation_items WHERE quotation_id=? ORDER BY id",(int(quotation_id),)).fetchall()]

def quotation_cart(quotation_id):
    with connect() as conn:
        q=conn.execute("""SELECT q.*,COALESCE(c.name,'') client_name FROM quotations q
                          LEFT JOIN clients c ON c.id=q.client_id WHERE q.id=?""",(int(quotation_id),)).fetchone()
        if not q or q['status']!='OPEN': raise ValueError("Devis indisponible")
        lines=[dict(r) for r in conn.execute("""SELECT product_id,name_snapshot name,qty,unit_price_cents
                                               FROM quotation_items WHERE quotation_id=? ORDER BY id""",(int(quotation_id),)).fetchall()]
        return dict(quotation=dict(q),cart=lines)

def cancel_quotation(quotation_id):
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE");require_permission('MANAGEMENT', conn)
        if conn.execute("UPDATE quotations SET status='CANCELLED' WHERE id=? AND status='OPEN'",(int(quotation_id),)).rowcount!=1:
            raise ValueError("Devis introuvable ou déjà clôturé")
        audit(conn,'QUOTATION_CANCEL',quotation_id);conn.commit()
