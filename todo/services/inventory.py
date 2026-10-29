import math
from database import get_setting
from services.security import current_user, require_permission, audit

def apply_stock_movement(conn, product_id, qty_delta, movement_type,
                         unit_cost_cents=0, ref_type='', ref_id=None, note='', user_id=None):
    if movement_type in ('ADJUSTMENT','OPENING','INVENTORY'):
        require_permission('STOCK_EDIT',conn)
        if get_setting('manual_stock_edit_enabled','1',conn)!='1':
            raise PermissionError('La modification manuelle du stock est désactivée.')
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


def stock_summary():
    """Stock footer indicators required by the operational stock screen."""
    from database import connect
    with connect() as conn:
        row=conn.execute("""
            SELECT COUNT(*) articles,
                   COALESCE(SUM(CASE WHEN stock_qty<=alert_qty THEN 1 ELSE 0 END),0) alerts,
                   COALESCE(SUM(CASE WHEN stock_qty<0 THEN 1 ELSE 0 END),0) negative,
                   COALESCE(SUM(stock_qty*purchase_price_cents),0) purchase_value_cents,
                   COALESCE(SUM(stock_qty*sale_price_cents),0) sale_value_cents
            FROM products WHERE active=1
        """).fetchone()
        promotions=conn.execute("""
            SELECT COUNT(*)
            FROM quantity_prices qp
            JOIN products p ON p.id=qp.product_id
            WHERE qp.active=1 AND p.active=1
        """).fetchone()[0]
    return {
        'articles':int(row['articles']),
        'alerts':int(row['alerts']),
        'negative':int(row['negative']),
        'active_promotions':int(promotions),
        'purchase_value_cents':int(round(row['purchase_value_cents'] or 0)),
        'sale_value_cents':int(round(row['sale_value_cents'] or 0)),
    }


def stock_products(query='', category_id=None, status='all'):
    """List active stock products with optional family and stock-state filters."""
    from database import connect
    q=(query or '').strip()
    status=(status or 'all').lower()
    if status not in ('all','alerts','negative'):
        raise ValueError('Filtre stock invalide.')
    where=["p.active=1","(?='' OR instr(lower(p.name),lower(?))>0)"]
    params=[q,q]
    if category_id is not None:
        where.append("""EXISTS(
            SELECT 1 FROM product_categories pc
            WHERE pc.product_id=p.id AND pc.category_id=?
        )""")
        params.append(int(category_id))
    if status=='alerts':
        where.append('p.stock_qty<=p.alert_qty')
    elif status=='negative':
        where.append('p.stock_qty<0')
    sql="""SELECT p.id,p.sku,p.name,p.purchase_price_cents,p.sale_price_cents,p.stock_qty,p.alert_qty,
                  COALESCE(NULLIF(p.sku,''),(SELECT pb.barcode FROM product_barcodes pb WHERE pb.product_id=p.id ORDER BY pb.id LIMIT 1),'') code,
                  COALESCE((SELECT group_concat(c.name, ', ')
                            FROM product_categories pc2
                            JOIN categories c ON c.id=pc2.category_id
                            WHERE pc2.product_id=p.id AND c.active=1),'') families,
                  COALESCE((SELECT movement_type||'|'||qty_delta||'|'||created_at
                            FROM stock_movements sm
                            WHERE sm.product_id=p.id
                            ORDER BY sm.id DESC LIMIT 1),'') last
           FROM products p
           WHERE """+' AND '.join(where)+""" ORDER BY p.name COLLATE NOCASE"""
    with connect() as conn:
        return [dict(r) for r in conn.execute(sql,params).fetchall()]


def get_active_categories():
    """Return active catalogue categories without depending on the UI."""
    from database import connect
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, name FROM categories WHERE active=1 "
            "ORDER BY sort_order, name COLLATE NOCASE"
        ).fetchall()
    return [dict(id=row["id"], name=row["name"]) for row in rows]


def product_stock_movements(product_id):
    """Return stock movement history for one product, newest first."""
    from database import connect
    with connect() as conn:
        rows = conn.execute(
            "SELECT sm.*, u.display_name username FROM stock_movements sm "
            "LEFT JOIN users u ON u.id=sm.user_id "
            "WHERE product_id=? ORDER BY sm.id DESC",
            (product_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def adjust_stock(product_id, qty_delta, note):
    """Apply a manual stock adjustment in a single atomic transaction."""
    from database import connect
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        result = apply_stock_movement(
            conn, product_id, qty_delta, "ADJUSTMENT", note=note
        )
        conn.commit()
    return result
