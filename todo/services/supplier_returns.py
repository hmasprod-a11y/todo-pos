import math
from decimal import Decimal
from services.money import rounded
from database import connect
from services.security import require_admin,current_user,audit
from services.inventory import apply_stock_movement

def supplier_purchase_invoices(supplier_id=None):
    with connect() as conn:
        rows=conn.execute("""
            SELECT p.id,p.supplier_id,p.supplier_invoice,p.total_cents,p.created_at,s.name supplier_name,
                   COALESCE((SELECT SUM(total_cents) FROM supplier_returns sr WHERE sr.purchase_id=p.id),0) returned_cents
            FROM purchases p JOIN suppliers s ON s.id=p.supplier_id
            WHERE (? IS NULL OR p.supplier_id=?)
            ORDER BY p.id DESC
        """,(supplier_id,supplier_id)).fetchall()
        return [dict(r) for r in rows]

def purchase_returnable_lines(purchase_id):
    with connect() as conn:
        rows=conn.execute("""
            SELECT pi.id purchase_item_id,pi.product_id,p.name,pi.qty,pi.unit_cost_cents,
                   COALESCE((SELECT SUM(sri.qty) FROM supplier_return_items sri WHERE sri.purchase_item_id=pi.id),0) returned_qty,
                   p.stock_qty
            FROM purchase_items pi JOIN products p ON p.id=pi.product_id
            WHERE pi.purchase_id=? ORDER BY pi.id
        """,(int(purchase_id),)).fetchall()
        return [dict(r) for r in rows]

def create_supplier_return(purchase_id, items, reason=''):
    if not items: raise ValueError("Retour fournisseur vide")
    reason=(reason or '').strip()
    if not reason: raise ValueError("Raison obligatoire")
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE");require_admin(conn)
        purchase=conn.execute("SELECT id,supplier_id FROM purchases WHERE id=?",(int(purchase_id),)).fetchone()
        if not purchase or purchase['supplier_id'] is None: raise ValueError("Facture fournisseur introuvable")
        normalized=[]
        total=0
        requested={}
        for purchase_item_id,qty in items:
            qty=Decimal(str(qty))
            if not qty.is_finite() or qty<=0:raise ValueError("Quantité retour invalide")
            key=int(purchase_item_id);requested[key]=requested.get(key,Decimal(0))+qty
        stock_required={}
        for purchase_item_id,count in requested.items():
            qty=float(count)
            row=conn.execute("""
                SELECT pi.id,pi.product_id,pi.qty,pi.unit_cost_cents,pi.line_total_cents,p.stock_qty,p.allow_fraction,
                       COALESCE((SELECT SUM(sri.line_total_cents) FROM supplier_return_items sri WHERE sri.purchase_item_id=pi.id),0) returned_cents,
                       COALESCE((SELECT SUM(sri.qty) FROM supplier_return_items sri WHERE sri.purchase_item_id=pi.id),0) returned_qty
                FROM purchase_items pi JOIN products p ON p.id=pi.product_id
                WHERE pi.id=? AND pi.purchase_id=?
            """,(int(purchase_item_id),int(purchase_id))).fetchone()
            if not row: raise ValueError("Ligne achat introuvable")
            remaining=float(row['qty'])-float(row['returned_qty'])
            if qty>remaining+1e-9: raise ValueError("Quantité supérieure au reliquat retournable")
            if not row['allow_fraction'] and not count==count.to_integral_value():raise ValueError('Quantité entière requise.')
            stock_required[row['product_id']]=stock_required.get(row['product_id'],Decimal(0))+count
            if stock_required[row['product_id']]>Decimal(str(row['stock_qty'])):raise ValueError("Stock insuffisant pour ce retour fournisseur")
            cumulative=Decimal(str(row['returned_qty']))+count
            cumulative_total=row['line_total_cents'] if abs(float(cumulative)-float(row['qty']))<=1e-9 else min(row['line_total_cents'],rounded(cumulative*row['unit_cost_cents']))
            line_total=cumulative_total-row['returned_cents']
            if line_total<0:raise ValueError('Montant de retour incohérent.')
            normalized.append((row,qty,line_total));total+=line_total
        uid=current_user.get()
        rid=conn.execute("INSERT INTO supplier_returns(supplier_id,purchase_id,reason,total_cents,user_id) VALUES(?,?,?,?,?)",
                         (purchase['supplier_id'],int(purchase_id),reason,total,uid)).lastrowid
        for row,qty,line_total in normalized:
            conn.execute("""INSERT INTO supplier_return_items(supplier_return_id,purchase_item_id,product_id,qty,unit_cost_cents,line_total_cents)
                            VALUES(?,?,?,?,?,?)""",(rid,row['id'],row['product_id'],qty,row['unit_cost_cents'],line_total))
            apply_stock_movement(conn,row['product_id'],-qty,'SUPPLIER_RETURN',row['unit_cost_cents'],'supplier_return',rid,reason,uid)
        audit(conn,'SUPPLIER_RETURN',rid,str(total),uid);conn.commit()
        return rid,total

def list_supplier_returns(supplier_id=None):
    with connect() as conn:
        return [dict(r) for r in conn.execute("""
            SELECT sr.*,s.name supplier_name,p.supplier_invoice
            FROM supplier_returns sr JOIN suppliers s ON s.id=sr.supplier_id
            JOIN purchases p ON p.id=sr.purchase_id
            WHERE (? IS NULL OR sr.supplier_id=?)
            ORDER BY sr.id DESC
        """,(supplier_id,supplier_id)).fetchall()]

def supplier_return_lines(return_id):
    with connect() as conn:
        return [dict(r) for r in conn.execute("""
            SELECT sri.*,p.name
            FROM supplier_return_items sri JOIN products p ON p.id=sri.product_id
            WHERE sri.supplier_return_id=? ORDER BY sri.id
        """,(int(return_id),)).fetchall()]

