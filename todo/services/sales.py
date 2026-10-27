import hashlib
import json, math
from decimal import Decimal
from datetime import datetime
from uuid import uuid4
from database import connect, get_setting
from services.inventory import apply_stock_movement
from services.pricing import resolve_unit_price, resolve_line_price, line_total
from services.money import allocate, rounded
from fiscal.tax import calculate_tax
from services.security import audit, current_user, has_permission

def sale_number():
    return 'V-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid4().hex[:12].upper()

def return_number():
    return 'R-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid4().hex[:12].upper()

def next_client_ticket_number(conn):
    row=conn.execute("SELECT value FROM settings WHERE key='receipt_next_client_ticket'").fetchone()
    try:number=max(1,int(row['value'])) if row else 1
    except (TypeError,ValueError):number=1
    conn.execute("""INSERT INTO settings(key,value) VALUES('receipt_next_client_ticket',?)
                    ON CONFLICT(key) DO UPDATE SET value=excluded.value""",(str(number+1),))
    return number

def validate_session(conn,session_id,user_id):
    session=conn.execute("SELECT id,user_id,workstation_code FROM cash_sessions WHERE id=? AND status='OPEN'",(session_id,)).fetchone()
    if not session:
        raise ValueError('Ouvrez la caisse avant cette opération.')
    if int(session['user_id'])!=int(user_id):
        raise PermissionError('Cette caisse appartient à un autre utilisateur.')
    if not conn.execute('SELECT id FROM users WHERE id=? AND active=1',(user_id,)).fetchone():
        raise ValueError('Utilisateur invalide')
    if current_user.get() is not None and current_user.get()!=user_id:
        raise PermissionError('Utilisateur incompatible')
    return session

def _document_prices(conn, quotation_id, customer_order_id, client_id):
    """Only persisted, open commercial documents may authorize agreed prices."""
    if quotation_id is not None and customer_order_id is not None:
        raise ValueError('Choisissez un seul document source.')
    if quotation_id is not None:
        document=conn.execute("SELECT client_id,status FROM quotations WHERE id=?",(int(quotation_id),)).fetchone()
        if not document or document['status']!='OPEN':raise ValueError('Devis indisponible.')
        if document['client_id'] is not None and (client_id is None or int(document['client_id'])!=int(client_id)):
            raise ValueError('Client incompatible avec le devis.')
        rows=conn.execute('SELECT product_id,qty,unit_price_cents FROM quotation_items WHERE quotation_id=?',(int(quotation_id),))
    elif customer_order_id is not None:
        document=conn.execute("SELECT client_id,status FROM customer_orders WHERE id=?",(int(customer_order_id),)).fetchone()
        if not document or document['status'] not in ('OPEN','READY'):raise ValueError('Commande client indisponible.')
        if client_id is None or int(document['client_id'])!=int(client_id):raise ValueError('Client incompatible avec la commande.')
        rows=conn.execute('SELECT product_id,qty,unit_price_cents FROM customer_order_items WHERE order_id=?',(int(customer_order_id),))
    else:return {}
    prices={}
    for row in rows:
        key=(int(row['product_id']),Decimal(str(row['unit_price_cents'])))
        prices[key]=prices.get(key,Decimal(0))+Decimal(str(row['qty']))
    return prices

def complete_sale(session_id,user_id,cart,payment_method,paid_cents,discount_cents=0,held_id=None,client_id=None,payments=None,seller_id=None,loyalty_points=0,customer_order_id=None,quotation_id=None,price_grid_id=None,request_key=None):
    if not cart:
        raise ValueError('Ticket vide')
    payment_method=str(payment_method).upper()
    if payments is not None and payment_method not in ('CASH','CARD','MIXED'):
        raise ValueError('Mode de paiement invalide')
    with connect() as conn:
        conn.execute('BEGIN IMMEDIATE')
        if payments is None and payment_method!='CREDIT':
            from services.payment_methods import payment_method as get_payment_method
            method_row=get_payment_method(payment_method,conn)
            if not method_row or not method_row['active']:
                raise ValueError('Mode de paiement invalide')
        session=validate_session(conn,session_id,user_id)
        fingerprint=None
        if request_key is not None:
            request_key=str(request_key).strip()
            if not request_key or len(request_key)>128:raise ValueError('Identifiant de paiement invalide.')
            payload=dict(session_id=session_id,user_id=user_id,cart=cart,payment_method=payment_method,paid_cents=paid_cents,discount_cents=discount_cents,held_id=held_id,client_id=client_id,payments=payments,seller_id=seller_id,loyalty_points=loyalty_points,customer_order_id=customer_order_id,quotation_id=quotation_id,price_grid_id=price_grid_id)
            fingerprint=hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False,default=str).encode('utf-8')).hexdigest()
            previous=conn.execute('SELECT * FROM checkout_requests WHERE request_key=?',(request_key,)).fetchone()
            if previous:
                if previous['cashier_user_id']!=user_id or previous['session_id']!=session_id or previous['fingerprint']!=fingerprint:
                    raise ValueError('Cet identifiant de paiement correspond à un autre ticket.')
                return json.loads(previous['result_json'])
        if held_id is not None and not conn.execute('SELECT id FROM held_sales WHERE id=? AND cashier_user_id=?',(held_id,user_id)).fetchone():
            raise ValueError('Ce ticket en attente a déjà été encaissé, supprimé ou appartient à un autre utilisateur.')
        if client_id is not None and not conn.execute('SELECT id FROM clients WHERE id=? AND active=1',(client_id,)).fetchone():
            raise ValueError('Client introuvable.')
        if seller_id is not None and not conn.execute('SELECT id FROM sellers WHERE id=? AND active=1',(seller_id,)).fetchone():
            raise ValueError('Vendeur introuvable.')
        if payment_method=='CREDIT' and client_id is None:
            raise ValueError('Choisissez un client pour une vente à crédit.')
        can_edit_price=has_permission('PRICE_EDIT',user_id=user_id,conn=conn)
        can_discount=has_permission('DISCOUNT',user_id=user_id,conn=conn)
        if int(discount_cents)>0 and not can_discount:
            raise PermissionError('Permission insuffisante pour la remise.')
        if price_grid_id is not None and not conn.execute('SELECT 1 FROM price_grids WHERE id=? AND active=1',(int(price_grid_id),)).fetchone():
            raise ValueError('Grille de prix indisponible.')
        document_prices=_document_prices(conn,quotation_id,customer_order_id,client_id)
        price_overrides=[]
        stock_management=get_setting('stock_management_enabled','1',conn)=='1'
        block_stock=get_setting('block_insufficient_stock','0',conn)=='1'
        allow_negative=get_setting('allow_negative_stock','1',conn)=='1'
        must_block=stock_management and (block_stock or not allow_negative)
        required_stock={}
        normalized=[]
        for line in cart:
            pid=int(line['product_id']);qty=float(line['qty'])
            if not math.isfinite(qty) or qty<=0:
                raise ValueError('Quantité invalide')
            p=conn.execute('SELECT * FROM products WHERE id=? AND (active=1 OR is_misc=1)',(pid,)).fetchone()
            if not p:
                raise ValueError('Article introuvable')
            if p['is_misc']:
                p=dict(p)
                p['name']=str(line.get('name','')).strip()
                if not p['name'] or len(p['name'])>150:raise ValueError('Libellé Divers invalide')
            if not p['allow_fraction'] and not qty.is_integer():
                raise ValueError('Cet article se vend en unités entières.')
            if must_block and not p['is_misc']:
                # Different barcodes/pack lines can consume the same product.
                # Validate their combined base-unit quantity before any writes.
                entry=required_stock.setdefault(pid,[p,Decimal(0)])
                entry[1]+=Decimal(str(qty))
            unit=line.get('unit_price_cents')
            pricing=None
            if line.get('barcode_id'):
                pricing=resolve_line_price(pid,qty,line['barcode_id'],conn,price_grid_id)
                if pricing['pricing_mode']=='PACK':unit=pricing['base_unit_price_cents']
            automatic=p['sale_price_cents'] if p['is_misc'] else resolve_unit_price(pid,qty,line.get('barcode_id'),conn,price_grid_id)
            if unit is None:
                unit=automatic
            unit=Decimal(str(unit))
            if not unit.is_finite() or unit<0:
                raise ValueError('Prix invalide')
            if not p['is_misc'] and unit not in (Decimal(str(automatic)),Decimal(str(p['sale_price_cents']))):
                key=(pid,unit);agreed=document_prices.get(key,Decimal(0))
                if agreed>=Decimal(str(qty)):
                    document_prices[key]=agreed-Decimal(str(qty))
                elif not can_edit_price:
                    raise PermissionError('Permission insuffisante pour modifier le prix.')
                else:
                    price_overrides.append(dict(product_id=pid,automatic=str(automatic),applied=str(unit)))
            gross=line_total(unit,qty)
            discount=int(line.get('discount_cents',0))
            if discount<0 or discount>gross:
                raise ValueError('Remise ligne invalide')
            if discount>0 and not can_discount:
                raise PermissionError('Permission insuffisante pour la remise.')
            normalized.append((p,qty,unit,gross,discount,pricing['barcode'] if pricing else line.get('barcode',''),pricing))
        for product,required in required_stock.values():
            available=Decimal(str(product['stock_qty']))
            if required>available:
                raise ValueError(f"Stock insuffisant pour {product['name']} (disponible: {product['stock_qty']:g}).")
        weights=[x[3]-x[4] for x in normalized]
        subtotal=sum(weights);discount=int(discount_cents)
        if discount<0 or discount>subtotal:
            raise ValueError('La remise dépasse le montant du ticket.')
        loyalty_points=int(loyalty_points or 0)
        loyalty_value=0
        if loyalty_points:
            if client_id is None:
                raise ValueError('Choisissez un client pour utiliser les points.')
            from services.loyalty import client_points, loyalty_settings
            cfg=loyalty_settings(conn)
            if not cfg['enabled']:
                raise ValueError('La fidélité est désactivée.')
            if loyalty_points>client_points(client_id,conn):
                raise ValueError('Solde de points insuffisant.')
            loyalty_value=loyalty_points*cfg['point_value_cents']
            if loyalty_value>subtotal-discount:
                raise ValueError('La valeur des points dépasse le total du ticket.')
        pre_tax_total=subtotal-discount-loyalty_value
        line_bases=allocate(pre_tax_total,weights)
        tax_breakdowns=[
            calculate_tax(base,int(p['tax_rate_basis_points']),tax_included=bool(p['tax_included']))
            for (p,*_),base in zip(normalized,line_bases)
        ]
        total=sum(tax.gross_cents for tax in tax_breakdowns)
        tax_total=sum(tax.tax_cents for tax in tax_breakdowns)
        paid=int(paid_cents)
        split=None
        if payments is not None:
            split=[(str(method).upper(),int(amount)) for method,amount in payments if int(amount)>0]
            if not split or any(method not in ('CASH','CARD') for method,amount in split):
                raise ValueError('Répartition de paiement invalide.')
            if sum(amount for method,amount in split)!=total:
                raise ValueError('Le paiement mixte doit couvrir exactement le ticket.')
            payment_method='MIXED' if len(split)>1 else split[0][0]
            paid=total
        if payment_method=='CASH' and paid<total:
            raise ValueError('Montant reçu insuffisant.')
        if payment_method not in ('CASH','CREDIT'):paid=total
        if paid<0 or (payment_method=='CREDIT' and paid>total):
            raise ValueError('Acompte invalide.')
        change=max(0,paid-total)
        no=sale_number()
        client_ticket_no=next_client_ticket_number(conn)
        workstation=(session['workstation_code'] or '01').strip().upper()
        stock_tracked=get_setting('stock_management_enabled','1',conn)=='1'
        country_code=get_setting('country_code','MA',conn).strip().upper() or 'MA'
        tax_label=get_setting('tax_label','Tax',conn).strip() or 'Tax'
        sid=conn.execute('INSERT INTO sales(sale_no,session_id,cashier_user_id,subtotal_cents,discount_cents,total_cents,payment_method,paid_cents,change_cents,client_id,seller_id,client_ticket_no,workstation_code,stock_tracked,country_code,tax_label_snapshot,tax_total_cents) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                         (no,session_id,user_id,subtotal,discount+loyalty_value,total,payment_method,paid,change,client_id,seller_id,client_ticket_no,workstation,1 if stock_tracked else 0,country_code,tax_label,tax_total)).lastrowid
        if split is None:
            settled=paid-change if payment_method=='CASH' else paid
            conn.execute('INSERT INTO sale_payments(sale_id,payment_method,amount_cents) VALUES(?,?,?)',(sid,payment_method,settled))
        else:
            conn.executemany('INSERT INTO sale_payments(sale_id,payment_method,amount_cents) VALUES(?,?,?)',[(sid,method,amount) for method,amount in split])
        for (p,qty,unit,gross,line_discount,barcode,pricing),tax,line_base in zip(normalized,tax_breakdowns,line_bases):
            pack=pricing and pricing['pricing_mode']=='PACK'
            customer_total=tax.gross_cents
            conn.execute('INSERT INTO sale_items(sale_id,product_id,barcode_used,name_snapshot,qty,unit_price_cents,cost_price_cents,discount_cents,line_total_cents,net_total_cents,qty_multiplier,pricing_mode,tax_rate_basis_points,tax_included,tax_class,tax_net_cents,tax_amount_cents,tax_gross_cents) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                         (sid,p['id'],barcode,p['name'],qty,pricing['unit_price_cents'] if pack else rounded(unit),p['purchase_price_cents'],gross-line_base,gross,customer_total,pricing['qty_multiplier'] if pricing else 1,'PACK' if pack else 'UNIT',tax.rate_basis_points,1 if tax.tax_included else 0,p['tax_class'] if 'tax_class' in p.keys() else 'STANDARD',tax.net_cents,tax.tax_cents,tax.gross_cents))
            if stock_tracked and not p['is_misc']:
                apply_stock_movement(conn,p['id'],-qty,'SALE',p['purchase_price_cents'],'sale',sid,no,user_id)
        if quotation_id is not None:
            quote=conn.execute("SELECT client_id,status FROM quotations WHERE id=?",(int(quotation_id),)).fetchone()
            if not quote or quote['status']!='OPEN':
                raise ValueError('Devis indisponible.')
            if quote['client_id'] is not None and (client_id is None or int(quote['client_id'])!=int(client_id)):
                raise ValueError('Client incompatible avec le devis.')
            conn.execute("UPDATE quotations SET status='CONVERTED',sale_id=?,converted_at=CURRENT_TIMESTAMP WHERE id=?",(sid,int(quotation_id)))
            audit(conn,'QUOTATION_CONVERT',quotation_id,no,user_id)
        if customer_order_id is not None:
            order=conn.execute("SELECT client_id,status FROM customer_orders WHERE id=?",(int(customer_order_id),)).fetchone()
            if not order or order['status'] not in ('OPEN','READY'):
                raise ValueError('Commande client indisponible.')
            if client_id is None or int(order['client_id'])!=int(client_id):
                raise ValueError('Client incompatible avec la commande.')
            conn.execute("UPDATE customer_orders SET status='COMPLETED',sale_id=?,completed_at=CURRENT_TIMESTAMP WHERE id=?",(sid,int(customer_order_id)))
            audit(conn,'CUSTOMER_ORDER_COMPLETE',customer_order_id,no,user_id)
        if loyalty_points:
            from services.loyalty import redeem_points
            redeem_points(conn,client_id,loyalty_points,sid,user_id)
        if client_id is not None:
            from services.loyalty import award_sale_points
            award_sale_points(conn,client_id,sid,total,user_id)
        if held_id is not None:
            conn.execute('DELETE FROM held_sales WHERE id=?',(held_id,))
        if price_overrides:audit(conn,'SALE_PRICE_OVERRIDE',sid,json.dumps(price_overrides,ensure_ascii=False),user_id)
        audit(conn,'SALE',sid,no,user_id)
        result=dict(id=sid,sale_no=no,client_ticket_no=client_ticket_no,workstation_code=workstation,stock_tracked=stock_tracked,subtotal_cents=subtotal,discount_cents=discount+loyalty_value,tax_total_cents=tax_total,total_cents=total,paid_cents=paid,change_cents=change,loyalty_points_used=loyalty_points,loyalty_value_cents=loyalty_value)
        if request_key is not None:
            conn.execute('INSERT INTO checkout_requests VALUES(?,?,?,?,?,?)',(request_key,user_id,session_id,fingerprint,json.dumps(result),sid))
        return result

def hold_sale(user_id,cart,label='',discount_cents=0,held_id=None,client_id=None,seller_id=None,price_grid_id=None,payment_method='CASH'):
    if not cart:raise ValueError('Ticket vide')
    payload=json.dumps(cart,ensure_ascii=False,default=str)
    with connect() as conn:
        conn.execute('BEGIN IMMEDIATE')
        if not conn.execute('SELECT id FROM users WHERE id=? AND active=1',(user_id,)).fetchone():
            raise ValueError('Utilisateur invalide')
        if current_user.get() is not None and current_user.get()!=user_id:
            raise PermissionError('Utilisateur incompatible')
        if client_id is not None and not conn.execute('SELECT id FROM clients WHERE id=? AND active=1',(client_id,)).fetchone():
            raise ValueError('Client introuvable.')
        if held_id is None:
            held_id=conn.execute('INSERT INTO held_sales(label,cashier_user_id,payload_json,discount_cents,client_id,seller_id,price_grid_id,payment_method) VALUES(?,?,?,?,?,?,?,?)',(label or 'Ticket en attente',user_id,payload,int(discount_cents),client_id,seller_id,price_grid_id,payment_method)).lastrowid
        else:
            cur=conn.execute('UPDATE held_sales SET label=?,payload_json=?,discount_cents=?,client_id=?,seller_id=?,price_grid_id=?,payment_method=? WHERE id=? AND cashier_user_id=?',(label or 'Ticket en attente',payload,int(discount_cents),client_id,seller_id,price_grid_id,payment_method,held_id,user_id))
            if cur.rowcount!=1:raise ValueError('Ticket en attente introuvable')
        audit(conn,'HOLD',held_id,user_id=user_id)
        return held_id

def list_held():
    with connect() as conn:
        uid=current_user.get()
        return conn.execute('SELECT * FROM held_sales WHERE cashier_user_id=? ORDER BY id DESC',(uid,)).fetchall() if uid is not None else conn.execute('SELECT * FROM held_sales ORDER BY id DESC').fetchall()

def resume_held(held_id):
    with connect() as conn:
        row=conn.execute('SELECT * FROM held_sales WHERE id=?',(held_id,)).fetchone()
        if not row:raise ValueError('Ticket introuvable')
        active_user=current_user.get()
        if active_user is not None and int(row['cashier_user_id'])!=int(active_user):
            raise PermissionError('Ce ticket en attente appartient à un autre utilisateur.')
        cart=json.loads(row['payload_json'])
        for line in cart:
            if line.get('pricing_mode')=='PACK':
                price=resolve_line_price(line['product_id'],line['qty'],line.get('barcode_id'),conn)
                line['unit_price_cents']=str(price['base_unit_price_cents'])
                line['qty_multiplier']=price['qty_multiplier']
                line.pop('pricing_mode',None)
        return dict(cart=cart,discount_cents=row['discount_cents'],held_id=row['id'],client_id=row['client_id'],seller_id=row['seller_id'],price_grid_id=row['price_grid_id'],payment_method=row['payment_method'])

def manual_return_number():
    return 'MR-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid4().hex[:12].upper()


def create_manual_returns(session_id, user_id, cart, ticket_discount_cents=0):
    """Register the current cashier cart as a cash return, without an original receipt."""
    if not cart:
        raise ValueError('Ticket vide')
    discount=max(0,int(ticket_discount_cents))
    with connect() as conn:
        conn.execute('BEGIN IMMEDIATE')
        validate_session(conn,session_id,user_id)
        from services.security import require_permission
        require_permission('RETURNS',conn)
        lines=[]
        weights=[]
        for line in cart:
            quantity=Decimal(str(line['qty']))
            if not quantity.is_finite() or quantity<=0:
                raise ValueError('Quantité retour invalide')
            product=conn.execute('SELECT * FROM products WHERE id=?',(int(line['product_id']),)).fetchone()
            if not product:
                raise ValueError('Article introuvable')
            if not product['allow_fraction'] and quantity!=quantity.to_integral_value():
                raise ValueError('Cet article se retourne en unités entières.')
            amount=max(0,line_total(line['unit_price_cents'],quantity)-int(line.get('discount_cents',0)))
            lines.append((product,quantity,amount))
            weights.append(amount)
        total=max(0,sum(weights)-discount)
        amounts=allocate(total,weights)
        document_no=manual_return_number()
        saved=[]
        for position,((product,quantity,_),amount) in enumerate(zip(lines,amounts),start=1):
            number=f'{document_no}-{position:02d}'
            rid=conn.execute('INSERT INTO manual_returns(return_no,session_id,cashier_user_id,product_id,qty,amount_cents) VALUES(?,?,?,?,?,?)',(number,session_id,user_id,product['id'],float(quantity),amount)).lastrowid
            if not product['is_misc']:
                apply_stock_movement(conn,product['id'],float(quantity),'RETURN_MANUAL',product['purchase_price_cents'],'manual_return',rid,number,user_id)
            audit(conn,'MANUAL_RETURN',rid,f'{number}; product={product["id"]}; qty={quantity}; amount={amount}',user_id)
            saved.append(dict(id=rid,return_no=number,product_id=product['id'],qty=float(quantity),amount_cents=amount))
        return dict(return_no=document_no,amount_cents=total,items=saved)


def create_manual_return(session_id, user_id, product_id, qty, amount_cents):
    """Compatibility entry point for one manually priced returned item."""
    result=create_manual_returns(session_id,user_id,[dict(product_id=product_id,qty=qty,unit_price_cents=int(amount_cents)/float(qty),discount_cents=0)])
    item=result['items'][0]
    return dict(id=item['id'],return_no=item['return_no'],product_id=item['product_id'],qty=item['qty'],amount_cents=item['amount_cents'])


def create_return(sale_id,session_id,user_id,items,reason='',refund_method='CASH'):
    if not items:raise ValueError('Aucun article à retourner')
    if refund_method not in ('CASH','CARD','AUTO'):raise ValueError('Mode de remboursement invalide')
    with connect() as conn:
        conn.execute('BEGIN IMMEDIATE');validate_session(conn,session_id,user_id)
        from services.security import require_permission
        require_permission('RETURNS',conn)
        sale=conn.execute('SELECT * FROM sales WHERE id=?',(sale_id,)).fetchone()
        if not sale:raise ValueError('Vente introuvable')
        requested={}
        for item,qty in items:
            qty=Decimal(str(qty))
            if not qty.is_finite() or qty<=0:raise ValueError('Quantité retour invalide')
            requested[int(item)]=requested.get(int(item),Decimal(0))+qty
        validated=[]
        for item,qty in requested.items():
            si=conn.execute('SELECT * FROM sale_items WHERE id=? AND sale_id=?',(item,sale_id)).fetchone()
            if not si:raise ValueError('Ligne introuvable')
            if si['pricing_mode']=='PACK' or si['qty_multiplier']!=1:
                packs=qty/Decimal(str(si['qty_multiplier']))
                if abs(packs-packs.to_integral_value())>Decimal('0.000000001'):
                    raise ValueError('Le retour doit respecter la quantité du pack/carton.')
            old=conn.execute('SELECT COALESCE(SUM(qty),0),COALESCE(SUM(line_total_cents),0) FROM return_items WHERE sale_item_id=?',(item,)).fetchone()
            cumulative=Decimal(str(old[0]))+qty;sold=Decimal(str(si['qty']))
            if cumulative>sold+Decimal('0.000000001'):raise ValueError('Quantité retour invalide')
            # Cumulative rounding guarantees that final partial return refunds the exact residual cent.
            due=max(0,rounded(Decimal(si['net_total_cents'])*min(cumulative,sold)/sold)-old[1])
            validated.append((si,float(qty),due))
        total=sum(x[2] for x in validated)
        refunded=conn.execute('SELECT COALESCE(SUM(total_cents),0) FROM returns WHERE sale_id=?',(sale_id,)).fetchone()[0]
        remaining=max(0,sale['total_cents']-refunded)
        if total>remaining:
            raise ValueError('Les anciens remboursements dépassent le solde. Vérification administrateur requise.')
        refund_paid=total
        if refund_method=='AUTO':
            if sale['payment_method']=='MIXED':
                parts=conn.execute("SELECT payment_method,amount_cents FROM sale_payments WHERE sale_id=? AND payment_method IN ('CASH','CARD')",(sale_id,)).fetchall()
                original={r['payment_method']:int(r['amount_cents']) for r in parts}
                prior=conn.execute("SELECT COALESCE(SUM(total_cents),0) FROM returns WHERE sale_id=?",(sale_id,)).fetchone()[0]
                cumulative=min(int(sale['total_cents']),int(prior)+int(total))
                denominator=Decimal(max(1,int(sale['total_cents'])))
                cash_target=rounded(Decimal(cumulative)*Decimal(original.get('CASH',0))/denominator)
                cash_before=rounded(Decimal(prior)*Decimal(original.get('CASH',0))/denominator)
                cash_refund=max(0,cash_target-cash_before)
                card_refund=max(0,total-cash_refund)
                refund_method='CASH' if cash_refund==total else ('CARD' if cash_refund==0 else 'MIXED')
            else:
                refund_method='CARD' if sale['payment_method']=='CARD' else 'CASH'
        if sale['client_id'] is not None and sale['payment_method']=='CREDIT':
            from services.clients import client_sales
            balance=next(r['balance_cents'] for r in client_sales(sale['client_id'],conn) if r['id']==sale_id)
            refund_paid=max(0,total-max(0,balance))
        no=return_number()
        rid=conn.execute('INSERT INTO returns(return_no,sale_id,session_id,cashier_user_id,total_cents,refund_method,reason,refund_paid_cents) VALUES(?,?,?,?,?,?,?,?)',(no,sale_id,session_id,user_id,total,refund_method,reason,refund_paid)).lastrowid
        if refund_method=='MIXED':
            conn.execute("INSERT INTO return_payments(return_id,payment_method,amount_cents) VALUES(?,?,?)",(rid,'CASH',cash_refund))
            conn.execute("INSERT INTO return_payments(return_id,payment_method,amount_cents) VALUES(?,?,?)",(rid,'CARD',card_refund))
        elif refund_method in ('CASH','CARD'):
            conn.execute("INSERT INTO return_payments(return_id,payment_method,amount_cents) VALUES(?,?,?)",(rid,refund_method,refund_paid))
        for si,qty,due in validated:
            conn.execute('INSERT INTO return_items(return_id,sale_item_id,product_id,qty,unit_price_cents,line_total_cents) VALUES(?,?,?,?,?,?)',(rid,si['id'],si['product_id'],qty,si['unit_price_cents'],due))
            misc=conn.execute('SELECT is_misc FROM products WHERE id=?',(si['product_id'],)).fetchone()[0]
            if sale['stock_tracked'] and not misc:
                apply_stock_movement(conn,si['product_id'],qty,'RETURN',si['cost_price_cents'],'return',rid,reason or no,user_id)
        audit(conn,'RETURN',rid,reason,user_id)
        refund_parts=[dict(payment_method=r['payment_method'],amount_cents=r['amount_cents']) for r in conn.execute('SELECT payment_method,amount_cents FROM return_payments WHERE return_id=? ORDER BY payment_method',(rid,))]
        return dict(id=rid,return_no=no,total_cents=total,refund_paid_cents=refund_paid,debt_reduction_cents=total-refund_paid,refund_method=refund_method,refund_payments=refund_parts)

