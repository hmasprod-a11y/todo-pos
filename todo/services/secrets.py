import base64, os
from pathlib import Path

import database

PREFIX_DPAPI='dpapi:'
PREFIX_FERNET='fernet:'

def _fernet():
    from cryptography.fernet import Fernet
    key_path=Path(database.BASE_DIR)/'data'/'.secret_key'
    key_path.parent.mkdir(parents=True,exist_ok=True)
    if key_path.exists():
        key=key_path.read_bytes().strip()
    else:
        key=Fernet.generate_key()
        key_path.write_bytes(key)
    return Fernet(key)

def protect_secret(value):
    value=value or ''
    if not value:return ''
    if os.name=='nt':
        try:
            import win32crypt
            blob=win32crypt.CryptProtectData(
                value.encode('utf-8'),
                'ToDo POS',
                None,None,None,
                getattr(win32crypt,'CRYPTPROTECT_LOCAL_MACHINE',4)
            )
            return PREFIX_DPAPI+base64.b64encode(blob).decode('ascii')
        except Exception:
            pass
    token=_fernet().encrypt(value.encode('utf-8')).decode('ascii')
    return PREFIX_FERNET+token

def reveal_secret(stored):
    stored=stored or ''
    if not stored:return ''
    if stored.startswith(PREFIX_DPAPI):
        if os.name!='nt':
            raise ValueError('Secret Windows non lisible sur cet appareil.')
        import win32crypt
        raw=base64.b64decode(stored[len(PREFIX_DPAPI):])
        _desc,data=win32crypt.CryptUnprotectData(raw,None,None,None,0)
        return data.decode('utf-8')
    if stored.startswith(PREFIX_FERNET):
        token=stored[len(PREFIX_FERNET):].encode('ascii')
        return _fernet().decrypt(token).decode('utf-8')
    # Legacy plaintext value. Caller may transparently migrate it.
    return stored

def get_smtp_password():
    stored=database.get_setting('smtp_app_password','')
    if not stored:return ''
    value=reveal_secret(stored)
    if not (stored.startswith(PREFIX_DPAPI) or stored.startswith(PREFIX_FERNET)):
        database.set_setting('smtp_app_password',protect_secret(value))
    return value

def set_smtp_password(value):
    database.set_setting('smtp_app_password',protect_secret(value))
