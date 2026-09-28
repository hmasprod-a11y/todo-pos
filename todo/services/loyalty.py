from database import connect,get_setting
from services.security import current_user,require_permission,audit

def loyalty_settings(conn=None):
    return {
        'enabled': get_setting('loyalty_enabled','0',conn)=='1',
        'earn_every_cents': max(1,int(get_setting('loyalty_earn_every_cents','1000',conn) or 1000)),
        'point_value_cents': max(1,int(get_setting('loyalty_point_value_cents','50',conn) or 50)),
    }

def client_points(client_id, conn=None):
    if conn is None:
        with connect() as db:return client_points(client_id,db)
    row=conn.execute("SELECT COALESCE(SUM(points_delta),0) balance FROM loyalty_movements WHERE client_id=?",(int(client_id),)).fetchone()
    return int(row['balance'] or 0)

def loyalty_clients(query=''):
    q=(query or '').strip()
    with connect() as conn:
        rows=conn.execute("""
            SELECT c.id,c.name,c.phone,c.active,
                   COALESCE(SUM(lm.points_delta),0) points,
                   COALESCE((SELECT SUM(s.total_cents) FROM sales s WHERE s.client_id=c.id AND s.status='COMPLETED'),0) sales_total_cents
            FROM clients c LEFT JOIN loyalty_movements lm ON lm.client_id=c.id
            WHERE c.active=1 AND (?='' OR instr(lower(c.name),lower(?))>0 OR instr(lower(c.phone),lower(?))>0)
            GROUP BY c.id ORDER BY points DESC,c.name COLLATE NOCASE
        """,(q,q,q)).fetchall()
        return [dict(r) for r in rows]

def loyalty_history(client_id, limit=500):
    with connect() as conn:
        return [dict(r) for r in conn.execute("""
            SELECT lm.*,COALESCE(u.display_name,'') username
            FROM loyalty_movements lm LEFT JOIN users u ON u.id=lm.user_id
            WHERE lm.client_id=? ORDER BY lm.id DESC LIMIT ?
        """,(int(client_id),int(limit))).fetchall()]

def adjust_points(client_id, points_delta, reason):
    delta=int(points_delta)
    if delta==0: raise ValueError("Variation de points nulle")
    reason=(reason or '').strip()
    if not reason: raise ValueError("Raison obligatoire")
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE");require_permission('MANAGEMENT', conn)
        if not conn.execute("SELECT 1 FROM clients WHERE id=? AND active=1",(int(client_id),)).fetchone():
            raise ValueError("Client introuvable")
        if delta<0 and client_points(client_id,conn)+delta<0:
            raise ValueError("Solde de points insuffisant")
        uid=current_user.get()
        mid=conn.execute("""INSERT INTO loyalty_movements(client_id,points_delta,reason,ref_type,user_id)
                            VALUES(?,?,?,'MANUAL',?)""",(int(client_id),delta,reason,uid)).lastrowid
        audit(conn,'LOYALTY_ADJUST',mid,f"{client_id}:{delta}:{reason}",uid);conn.commit();return mid

def award_sale_points(conn, client_id, sale_id, sale_total_cents, user_id=None):
    if client_id is None:return 0
    settings=loyalty_settings(conn)
    if not settings['enabled']:return 0
    if conn.execute("SELECT 1 FROM loyalty_movements WHERE client_id=? AND ref_type='SALE' AND ref_id=?",(int(client_id),int(sale_id))).fetchone():
        return 0
    points=max(0,int(sale_total_cents)//settings['earn_every_cents'])
    if points<=0:return 0
    conn.execute("""INSERT INTO loyalty_movements(client_id,points_delta,reason,ref_type,ref_id,user_id)
                    VALUES(?,?,?,'SALE',?,?)""",(int(client_id),points,'Points vente',int(sale_id),user_id))
    return points

def redeem_points(conn, client_id, points, sale_id=None, user_id=None):
    pts=int(points)
    if pts<=0: raise ValueError("Points invalides")
    if client_points(client_id,conn)<pts: raise ValueError("Solde de points insuffisant")
    value=pts*loyalty_settings(conn)['point_value_cents']
    conn.execute("""INSERT INTO loyalty_movements(client_id,points_delta,reason,ref_type,ref_id,user_id)
                    VALUES(?,?,?,'REDEEM',?,?)""",(int(client_id),-pts,'Utilisation points',sale_id,user_id))
    return value
