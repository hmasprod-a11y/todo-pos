import math
from database import get_setting
from services.security import current_user, require_permission, audit

def apply_stock_movement(conn, product_id, qty_delta, movement_type,
                         unit_cost_cents=0, ref_type='', ref_id=None, note='', user_id=None):
    if movement_type in ('ADJUSTMENT','OPENING','INVENTORY'):
        require_permission('STOCK_EDIT',conn)
        if not note.strip():
            raise ValueError('La raison est obligatoire.')
    row=conn.execute('SELECT name,stock_qty FROM products WHERE id=?',(product_id,)).fetchone()
    if not row:
        raise ValueError('Article introuvable')
    delta=float(qty_delta)
    if not math.isfinite(delta):
        raise ValueError('Quantité invalide')
    old=float(row['stock_qty']);new=old+delta
    if not math.isfinite(new):
        raise ValueError('Quantité invalide')
    if delta < 0 and new < -1e-9 and get_setting('allow_negative_stock','1',conn)!='1':
        raise ValueError(f"Stock insuffisant: {row['name']} (disponible {old:g})")
    uid=user_id or current_user.get()
    conn.execute('UPDATE products SET stock_qty=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',(new,product_id))
    conn.execute('INSERT INTO stock_movements(product_id,movement_type,qty_delta,old_qty,stock_after,unit_cost_cents,ref_type,ref_id,note,user_id) VALUES(?,?,?,?,?,?,?,?,?,?)',
                 (product_id,movement_type,delta,old,new,int(unit_cost_cents or 0),ref_type,ref_id,note,uid))
    audit(conn,'STOCK_'+movement_type,ref_id or product_id,note,uid)
    return new


def stock_activity(query='', movement_type='', limit=2000):
    """Global stock ledger with product, actor, before/after quantities and document."""
    q=(query or '').strip()
    movement_type=(movement_type or '').strip().upper()
    params=[q,q]
    extra=''
    if movement_type:
        extra=' AND sm.movement_type=?'
        params.append(movement_type)
    params.append(int(limit))
    from database import connect
    with connect() as conn:
        rows=conn.execute("""
            SELECT sm.*,p.name product_name,COALESCE(u.display_name,'') username
            FROM stock_movements sm
            JOIN products p ON p.id=sm.product_id
            LEFT JOIN users u ON u.id=sm.user_id
            WHERE (?='' OR instr(lower(p.name),lower(?))>0)
        """+extra+""" ORDER BY sm.id DESC LIMIT ?""",params).fetchall()
        return [dict(r) for r in rows]


def reorder_list():
    """Products at/below alert level with a practical target of twice the alert threshold."""
    from database import connect
    with connect() as conn:
        rows=conn.execute("""
            SELECT p.id,p.name,p.sku,p.supplier_code,p.stock_qty,p.alert_qty,p.purchase_price_cents,p.allow_fraction,
                   p.preferred_supplier_id,COALESCE(s.name,'') preferred_supplier_name
            FROM products p
            LEFT JOIN suppliers s ON s.id=p.preferred_supplier_id
            WHERE p.active=1 AND p.alert_qty>0 AND p.stock_qty<=p.alert_qty
            ORDER BY (p.alert_qty-p.stock_qty) DESC,p.name COLLATE NOCASE
        """).fetchall()
    result=[]
    for row in rows:
        r=dict(row)
        target=float(r['alert_qty'])*2
        suggested=max(0.0,target-float(r['stock_qty']))
        if not r['allow_fraction']:
            suggested=math.ceil(suggested)
        r['target_qty']=target
        r['suggested_qty']=suggested
        r['estimated_cost_cents']=int(round(suggested*int(r['purchase_price_cents'])))
        result.append(r)
    return result
