import re
from database import connect,get_setting
from services.security import require_admin,audit

TAG_RE=re.compile(r'^[A-Za-z0-9:_-]{4,64}$')

def normalize_tag(tag):
    value=str(tag or '').strip()
    if not TAG_RE.fullmatch(value):raise ValueError('Tag RFID invalide')
    return value

def get_tag_for_target(target_type,target_id):
    with connect() as conn:
        row=conn.execute("SELECT tag FROM rfid_tags WHERE target_type=? AND target_id=?",(str(target_type).upper(),int(target_id))).fetchone()
        return row['tag'] if row else ''

def bind_tag(tag,target_type,target_id,conn=None):
    tag=normalize_tag(tag) if tag else ''
    target_type=str(target_type).upper()
    if target_type not in ('PRODUCT','CLIENT'):raise ValueError('Type RFID invalide')
    own=conn is None
    if own:conn=connect();conn.execute('BEGIN IMMEDIATE');require_admin(conn)
    try:
        conn.execute("DELETE FROM rfid_tags WHERE target_type=? AND target_id=?",(target_type,int(target_id)))
        if tag:
            existing=conn.execute("SELECT target_type,target_id FROM rfid_tags WHERE tag=?",(tag,)).fetchone()
            if existing:raise ValueError('Tag RFID déjà utilisé')
            conn.execute("INSERT INTO rfid_tags(tag,target_type,target_id) VALUES(?,?,?)",(tag,target_type,int(target_id)))
        audit(conn,'RFID_BIND',target_id,f'{target_type}:{tag}')
        if own:conn.commit()
        return tag
    finally:
        if own:conn.close()

def lookup_tag(tag):
    try:tag=normalize_tag(tag)
    except ValueError:return None
    with connect() as conn:
        row=conn.execute("SELECT tag,target_type,target_id FROM rfid_tags WHERE tag=?",(tag,)).fetchone()
        return dict(row) if row else None

def serial_ports():
    try:
        from serial.tools import list_ports
        return [p.device for p in list_ports.comports()]
    except Exception:return []

def read_tag(port=None,baudrate=None,timeout_ms=None):
    explicit=port is not None
    if not explicit and get_setting('rfid_enabled','0')!='1':raise ValueError('Activez RFID dans Paramètres.')
    if not explicit and get_setting('rfid_mode','HID')!='SERIAL':raise ValueError('RFID est configuré en mode USB/HID.')
    port=(port if explicit else get_setting('rfid_port','')).strip()
    if not port:raise ValueError('Sélectionnez le port COM RFID.')
    baud=int(baudrate if baudrate is not None else get_setting('rfid_baudrate','9600'))
    timeout=max(100,int(timeout_ms if timeout_ms is not None else get_setting('rfid_timeout_ms','800')))/1000.0
    import serial
    with serial.Serial(port=port,baudrate=baud,timeout=timeout) as device:
        line=device.readline()
    if not line:raise TimeoutError('Aucun tag RFID reçu.')
    return normalize_tag(line.decode('ascii','ignore').strip())
