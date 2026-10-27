import math
from database import connect
from services.security import require_admin,current_user,audit
from services.inventory import apply_stock_movement

def create_inventory_session(label=''):
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE");require_admin(conn)
        uid=current_user.get()
        sid=conn.execute("INSERT INTO inventory_sessions(label,created_by) VALUES(?,?)",((label or '').strip(),uid)).lastrowid
        rows=conn.execute("SELECT id,name,stock_qty,purchase_price_cents FROM products WHERE active=1 ORDER BY name").fetchall()
        conn.executemany("""INSERT INTO inventory_session_items(session_id,product_id,product_name,theory_qty,unit_cost_cents)
                            VALUES(?,?,?,?,?)""",[(sid,r['id'],r['name'],r['stock_qty'],r['purchase_price_cents']) for r in rows])
        audit(conn,'INVENTORY_SESSION_CREATE',sid,str(len(rows)),uid);conn.commit();return sid

def list_inventory_sessions():
    with connect() as conn:
        return [dict(r) for r in conn.execute("""
            SELECT s.*,COALESCE(u.display_name,'') created_by_name,COALESCE(v.display_name,'') validated_by_name,
                   COUNT(i.id) items,
                   SUM(CASE WHEN i.counted_qty IS NOT NULL THEN 1 ELSE 0 END) counted,
                   COALESCE(SUM(CASE WHEN i.counted_qty IS NOT NULL THEN ABS(i.counted_qty-i.theory_qty) ELSE 0 END),0) qty_diff,
                   COALESCE(SUM(CASE WHEN i.counted_qty IS NOT NULL THEN (i.counted_qty-i.theory_qty)*i.unit_cost_cents ELSE 0 END),0) value_diff_cents
            FROM inventory_sessions s
            LEFT JOIN users u ON u.id=s.created_by LEFT JOIN users v ON v.id=s.validated_by
            LEFT JOIN inventory_session_items i ON i.session_id=s.id
            GROUP BY s.id ORDER BY s.id DESC
        """).fetchall()]

def inventory_session_lines(session_id, query=''):
    q=(query or '').strip()
    with connect() as conn:
        return [dict(r) for r in conn.execute("""
            SELECT * FROM inventory_session_items
            WHERE session_id=? AND (?='' OR instr(lower(product_name),lower(?))>0)
            ORDER BY product_name
        """,(int(session_id),q,q)).fetchall()]

def set_inventory_count(session_id, product_id, counted_qty):
    qty=float(counted_qty)
    if not math.isfinite(qty) or qty<0: raise ValueError("Quantité comptée invalide")
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE");require_admin(conn)
        status=conn.execute("SELECT status FROM inventory_sessions WHERE id=?",(int(session_id),)).fetchone()
        if not status or status['status']!='OPEN': raise ValueError("Inventaire clôturé")
        item=conn.execute("""SELECT p.active,p.allow_fraction FROM inventory_session_items i
                             JOIN products p ON p.id=i.product_id
                             WHERE i.session_id=? AND i.product_id=?""",
                          (int(session_id),int(product_id))).fetchone()
        if not item: raise ValueError("Article introuvable")
        if not item['active']: raise ValueError("Article inactif dans l'inventaire")
        if not item['allow_fraction'] and not qty.is_integer():
            raise ValueError("Cet article se compte en unités entières.")
        conn.execute("UPDATE inventory_session_items SET counted_qty=? WHERE session_id=? AND product_id=?",
                     (qty,int(session_id),int(product_id)))
        conn.commit()

def finalize_inventory_session(session_id):
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE");require_admin(conn)
        row=conn.execute("SELECT status FROM inventory_sessions WHERE id=?",(int(session_id),)).fetchone()
        if not row or row['status']!='OPEN': raise ValueError("Inventaire introuvable ou déjà validé")
        lines=conn.execute("SELECT * FROM inventory_session_items WHERE session_id=? AND counted_qty IS NOT NULL",(int(session_id),)).fetchall()
        if not lines: raise ValueError("Aucun comptage saisi")
        # Validate every counted line before moving any stock. A deactivated
        # product must not silently disappear from a validated inventory.
        targets=[]
        for r in lines:
            current=conn.execute("SELECT stock_qty,allow_fraction FROM products WHERE id=? AND active=1",(r['product_id'],)).fetchone()
            if not current: raise ValueError("Article inactif dans l'inventaire")
            target=float(r['counted_qty'])
            if not math.isfinite(target) or target<0: raise ValueError("Quantité comptée invalide")
            if not current['allow_fraction'] and not target.is_integer():
                raise ValueError("Cet article se compte en unités entières.")
            targets.append((r,current,target))
        adjusted=0
        for r,current,target in targets:
            now=float(current['stock_qty']);delta=target-now
            if abs(delta)<=1e-9: continue
            apply_stock_movement(conn,r['product_id'],delta,'INVENTORY',r['unit_cost_cents'],'inventory_session',int(session_id),
                                 f"Inventaire #{session_id}: {now:g} -> {target:g}")
            adjusted+=1
        uid=current_user.get()
        conn.execute("UPDATE inventory_sessions SET status='VALIDATED',validated_by=?,validated_at=CURRENT_TIMESTAMP WHERE id=?",(uid,int(session_id)))
        audit(conn,'INVENTORY_SESSION_VALIDATE',session_id,str(adjusted),uid);conn.commit()
        return adjusted
