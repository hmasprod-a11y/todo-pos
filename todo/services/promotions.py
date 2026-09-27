import math
from database import connect
from services.security import require_admin, audit

def list_promotions(query='', active_only=False):
    q=(query or '').strip()
    with connect() as conn:
        rows=conn.execute("""
            SELECT qp.id,qp.product_id,p.name product_name,p.sale_price_cents,
                   qp.min_qty,qp.unit_price_cents,qp.pricing_mode,qp.active
            FROM quantity_prices qp JOIN products p ON p.id=qp.product_id
            WHERE p.active=1
              AND (?='' OR instr(lower(p.name),lower(?))>0)
              AND (?=0 OR qp.active=1)
            ORDER BY p.name COLLATE NOCASE,qp.min_qty,qp.id
        """,(q,q,1 if active_only else 0)).fetchall()
        return [dict(r) for r in rows]

def save_promotion(product_id, min_qty, unit_price_cents, pricing_mode='UNIT', promotion_id=None):
    pid=int(product_id);qty=float(min_qty);price=int(unit_price_cents);mode=str(pricing_mode).upper()
    if not math.isfinite(qty) or qty<=0: raise ValueError("Quantité minimale invalide")
    if price<0: raise ValueError("Prix promotion invalide")
    if mode not in ('UNIT','BUNDLE'): raise ValueError("Mode promotion invalide")
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE");require_admin(conn)
        if not conn.execute("SELECT 1 FROM products WHERE id=? AND active=1",(pid,)).fetchone():
            raise ValueError("Article introuvable")
        if promotion_id is None:
            promo_id=conn.execute(
                "INSERT INTO quantity_prices(product_id,min_qty,unit_price_cents,pricing_mode,active) VALUES(?,?,?,?,1)",
                (pid,qty,price,mode)).lastrowid
            audit(conn,"PROMOTION_CREATE",promo_id,f"{pid}:{qty}:{price}:{mode}")
        else:
            promo_id=int(promotion_id)
            if conn.execute("""UPDATE quantity_prices SET product_id=?,min_qty=?,unit_price_cents=?,pricing_mode=?
                               WHERE id=?""",(pid,qty,price,mode,promo_id)).rowcount!=1:
                raise ValueError("Promotion introuvable")
            audit(conn,"PROMOTION_UPDATE",promo_id,f"{pid}:{qty}:{price}:{mode}")
        conn.commit();return promo_id

def set_promotion_active(promotion_id, active):
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE");require_admin(conn)
        if conn.execute("UPDATE quantity_prices SET active=? WHERE id=?",(1 if active else 0,int(promotion_id))).rowcount!=1:
            raise ValueError("Promotion introuvable")
        audit(conn,"PROMOTION_ACTIVE",promotion_id,str(int(bool(active))));conn.commit()

def delete_promotion(promotion_id):
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE");require_admin(conn)
        if conn.execute("DELETE FROM quantity_prices WHERE id=?",(int(promotion_id),)).rowcount!=1:
            raise ValueError("Promotion introuvable")
        audit(conn,"PROMOTION_DELETE",promotion_id);conn.commit()
