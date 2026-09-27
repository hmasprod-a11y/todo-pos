import hashlib, hmac, secrets
from contextvars import ContextVar
from database import connect

current_user=ContextVar('todo_user',default=None)

def hash_pin(pin):
    salt=secrets.token_hex(16)
    digest=hashlib.pbkdf2_hmac('sha256',str(pin).encode(),salt.encode(),120000).hex()
    return f'pbkdf2$120000${salt}${digest}'

def verify_pin(pin, stored):
    if not stored.startswith('pbkdf2$'):
        return hmac.compare_digest(hashlib.sha256(str(pin).encode()).hexdigest(),stored)
    _,iterations,salt,digest=stored.split('$')
    actual=hashlib.pbkdf2_hmac('sha256',str(pin).encode(),salt.encode(),int(iterations)).hex()
    return hmac.compare_digest(actual,digest)

def require_admin(conn):
    uid=current_user.get()
    user=conn.execute("SELECT role FROM users WHERE id=? AND active=1",(uid,)).fetchone()
    if not user or user['role']!='admin':
        raise PermissionError('Action réservée à un administrateur.')
    return uid

def audit(conn,action,document,details='',user_id=None):
    conn.execute('INSERT INTO audit_log(user_id,action,document,details) VALUES(?,?,?,?)',(user_id or current_user.get(),action,str(document),str(details)))

PERMISSIONS={
    'DISCOUNT':('Remises','التخفيضات'),
    'PRICE_EDIT':('Modifier prix','تعديل الثمن'),
    'RETURNS':('Retours clients','مرتجعات الزبائن'),
    'STOCK_EDIT':('Modifier stock','تعديل المخزون'),
    'REPORTS':('Journal / statistiques','السجل / الإحصائيات'),
    'MANAGEMENT':('Gestion','الإدارة'),
    'SETTINGS':('Paramètres','الإعدادات'),
}
LEGACY_CASHIER_DEFAULTS={'DISCOUNT':1,'PRICE_EDIT':1,'RETURNS':1}

def has_permission(permission,user_id=None,conn=None):
    permission=str(permission).upper()
    uid=user_id if user_id is not None else current_user.get()
    own=conn is None
    if own:conn=connect()
    try:
        user=conn.execute("SELECT role,active FROM users WHERE id=?",(uid,)).fetchone()
        if not user or not user['active']:return False
        if user['role']=='admin':return True
        row=conn.execute("SELECT allowed FROM user_permissions WHERE user_id=? AND permission=?",(uid,permission)).fetchone()
        if row is not None:return bool(row['allowed'])
        return bool(LEGACY_CASHIER_DEFAULTS.get(permission,0))
    finally:
        if own:conn.close()

def require_permission(permission,conn=None):
    if not has_permission(permission,conn=conn):
        raise PermissionError('Permission insuffisante.')
    return current_user.get()

def set_user_permission(user_id,permission,allowed,conn=None):
    permission=str(permission).upper()
    if permission not in PERMISSIONS:raise ValueError('Permission invalide')
    own=conn is None
    if own:
        conn=connect();conn.execute('BEGIN IMMEDIATE');require_admin(conn)
    try:
        conn.execute("""INSERT INTO user_permissions(user_id,permission,allowed) VALUES(?,?,?)
                        ON CONFLICT(user_id,permission) DO UPDATE SET allowed=excluded.allowed""",
                     (int(user_id),permission,1 if allowed else 0))
        audit(conn,'USER_PERMISSION',user_id,f'{permission}={1 if allowed else 0}')
        if own:conn.commit()
    finally:
        if own:conn.close()

def list_user_permissions(user_id):
    with connect() as conn:
        return {code:has_permission(code,user_id,conn) for code in PERMISSIONS}
