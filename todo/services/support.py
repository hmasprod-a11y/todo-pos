from pathlib import Path
import os,sqlite3,sys,subprocess
import database
from database import connect,get_setting
from services.security import verify_pin

APP_VERSION='1.1.0'

DOCS={
    'guide_fr':'USER_GUIDE_FR.md',
    'guide_ar':'USER_GUIDE_AR.md',
    'backup':'BACKUP_RESTORE.md',
    'install':'INSTALLATION_WINDOWS.md',
    'checklist':'RELEASE_CHECKLIST.md',
}

def _app_root():
    if getattr(sys,'frozen',False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]

def documentation_paths():
    root=_app_root()
    folder=root/'docs'
    return {key:folder/name for key,name in DOCS.items()}

def latest_backup():
    candidates=[]
    for folder in (database.BASE_DIR/'backups',_app_root()/'todo'/'backups',_app_root()/'backups'):
        if folder.exists():
            candidates.extend([p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in ('.db','.todozip')])
    if not candidates:return None
    return max(candidates,key=lambda p:p.stat().st_mtime)

def diagnostics():
    db_path=Path(database.DB_PATH)
    with connect() as conn:
        integrity=conn.execute('PRAGMA integrity_check').fetchone()[0]
        schema=conn.execute('PRAGMA user_version').fetchone()[0]
        tables=conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchone()[0]
        admin=conn.execute("SELECT pin_hash FROM users WHERE username='admin' AND active=1 ORDER BY id LIMIT 1").fetchone()
        default_admin_pin=bool(admin and verify_pin('1234',admin['pin_hash']))
    backup=latest_backup()
    return {
        'version':APP_VERSION,
        'shop':get_setting('shop_name','ToDo'),
        'workstation':get_setting('workstation_code','01'),
        'db_path':str(db_path.resolve()),
        'db_size_bytes':db_path.stat().st_size if db_path.exists() else 0,
        'sqlite_version':sqlite3.sqlite_version,
        'schema_version':int(schema),
        'tables':int(tables),
        'integrity':integrity,
        'last_backup':str(backup) if backup else '',
        'default_admin_pin':default_admin_pin,
    }

def diagnostic_text():
    d=diagnostics()
    return '\n'.join([
        f"ToDo POS {d['version']}",
        f"Magasin: {d['shop']}",
        f"Poste: {d['workstation']}",
        f"SQLite: {d['sqlite_version']} / schema {d['schema_version']}",
        f"Base: {d['db_path']}",
        f"Taille DB: {d['db_size_bytes']} octets",
        f"Tables: {d['tables']}",
        f"Intégrité: {d['integrity']}",
        f"Dernier backup: {d['last_backup'] or 'aucun'}",
        f"PIN admin par défaut: {'À CHANGER' if d['default_admin_pin'] else 'OK'}",
    ])

def open_document(key):
    paths=documentation_paths()
    if key not in paths:raise ValueError('Document inconnu.')
    path=paths[key]
    if not path.is_file():raise FileNotFoundError(f'Document introuvable: {path}')
    if os.name=='nt':os.startfile(str(path))
    elif sys.platform=='darwin':subprocess.Popen(['open',str(path)])
    else:subprocess.Popen(['xdg-open',str(path)])
    return path
