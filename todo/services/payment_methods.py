import re
from database import connect
from services.security import require_admin,audit

def list_payment_methods(active_only=False):
    with connect() as conn:
        rows=conn.execute("SELECT * FROM payment_methods WHERE (?=0 OR active=1) ORDER BY sort_order,name_fr COLLATE NOCASE,id",(1 if active_only else 0,)).fetchall()
        return [dict(r) for r in rows]

def payment_method(code,conn=None):
    code=str(code or '').upper().strip()
    if conn is None:
        with connect() as db:return payment_method(code,db)
    row=conn.execute("SELECT * FROM payment_methods WHERE code=?",(code,)).fetchone()
    return dict(row) if row else None

def save_payment_method(code,name_fr,name_ar='',icon='',method_id=None):
    code=re.sub(r'[^A-Z0-9_]+','_',str(code or '').upper().strip()).strip('_')
    name_fr=(name_fr or '').strip();name_ar=(name_ar or '').strip();icon=(icon or '').strip()[:8]
    if not code or len(code)>24 or not name_fr:raise ValueError('Mode de paiement invalide')
    if code in ('CREDIT','MIXED','AUTO'):raise ValueError('Code réservé')
    with connect() as conn:
        conn.execute('BEGIN IMMEDIATE');require_admin(conn)
        if method_id is None:
            mid=conn.execute("INSERT INTO payment_methods(code,name_fr,name_ar,icon,active,system) VALUES(?,?,?,?,1,0)",(code,name_fr,name_ar,icon)).lastrowid
        else:
            row=conn.execute("SELECT code,system FROM payment_methods WHERE id=?",(int(method_id),)).fetchone()
            if not row:raise ValueError('Mode introuvable')
            if row['system']:code=row['code']
            conn.execute("UPDATE payment_methods SET code=?,name_fr=?,name_ar=?,icon=? WHERE id=?",(code,name_fr,name_ar,icon,int(method_id)));mid=int(method_id)
        audit(conn,'PAYMENT_METHOD_SAVE',mid,code);conn.commit();return mid

def set_payment_method_active(method_id,active):
    with connect() as conn:
        conn.execute('BEGIN IMMEDIATE');require_admin(conn)
        row=conn.execute("SELECT code,system FROM payment_methods WHERE id=?",(int(method_id),)).fetchone()
        if not row:raise ValueError('Mode introuvable')
        if row['system'] and not active:raise ValueError('Espèces et Carte doivent rester actives')
        conn.execute("UPDATE payment_methods SET active=? WHERE id=?",(1 if active else 0,int(method_id)))
        audit(conn,'PAYMENT_METHOD_ACTIVE',method_id,str(int(bool(active))));conn.commit()

def payment_label(code,lang='fr',conn=None):
    code=str(code or '').upper()
    if code=='CREDIT':return 'دين' if lang=='ar' else 'Crédit'
    if code=='MIXED':return 'مختلط' if lang=='ar' else 'Mixte'
    row=payment_method(code,conn)
    if not row:return code
    return (row['name_ar'] or row['name_fr']) if lang=='ar' else row['name_fr']


def payment_icon(code,conn=None):
    code=str(code or '').upper()
    if code=='CREDIT':return '🧾'
    if code=='MIXED':return '🔀'
    row=payment_method(code,conn)
    return (row.get('icon') or '') if row else ''
