import base64,hashlib,json,os,platform,shutil,uuid
from datetime import date
from pathlib import Path
import database
from database import connect,get_setting
from services.security import require_admin,audit

LICENSE_FILE='license.json'

def _license_path():
    return Path(database.BASE_DIR)/'data'/LICENSE_FILE

def machine_fingerprint():
    raw=''
    if os.name=='nt':
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,r'SOFTWARE\Microsoft\Cryptography') as key:
                raw=str(winreg.QueryValueEx(key,'MachineGuid')[0])
        except Exception:
            raw=''
    if not raw:
        raw='|'.join([platform.node(),platform.system(),platform.machine(),str(uuid.getnode())])
    return hashlib.sha256(raw.encode('utf-8')).hexdigest().upper()

def _payload_bytes(document):
    payload={k:document[k] for k in ('customer','machine_id','issued_at','expires_at') if k in document}
    return json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')

def verify_license_document(document,public_key_b64,machine_id=None,today=None):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    if not isinstance(document,dict):raise ValueError('Licence invalide.')
    for key in ('customer','machine_id','issued_at','expires_at','signature'):
        if not document.get(key):raise ValueError(f'Champ licence manquant: {key}')
    try:
        key_bytes=base64.b64decode(public_key_b64,validate=True)
        signature=base64.b64decode(document['signature'],validate=True)
        Ed25519PublicKey.from_public_bytes(key_bytes).verify(signature,_payload_bytes(document))
    except Exception as exc:
        raise ValueError('Signature licence invalide.') from exc
    current_machine=(machine_id or machine_fingerprint()).upper()
    if document['machine_id'].upper()!=current_machine:
        raise ValueError('Cette licence appartient à un autre poste.')
    try:
        expiry=date.fromisoformat(document['expires_at'])
    except ValueError as exc:
        raise ValueError("Date d'expiration licence invalide.") from exc
    current=today or date.today()
    if expiry<current:raise ValueError('Licence expirée.')
    return {'valid':True,'customer':document['customer'],'expires_at':document['expires_at'],'machine_id':current_machine}

def load_installed_license():
    path=_license_path()
    if not path.is_file():return None
    try:return json.loads(path.read_text(encoding='utf-8'))
    except (OSError,json.JSONDecodeError):return None

def license_status():
    enforced=get_setting('license_enforced','0')=='1'
    public_key=get_setting('license_public_key_b64','').strip()
    document=load_installed_license()
    result={'enforced':enforced,'installed':bool(document),'valid':False,'machine_id':machine_fingerprint(),'customer':'','expires_at':'','error':''}
    if not document:
        if enforced:result['error']='Aucune licence installée.'
        return result
    if not public_key:
        result['error']='Clé publique de licence non configurée.'
        return result
    try:
        verified=verify_license_document(document,public_key)
        result.update(verified)
    except Exception as exc:result['error']=str(exc)
    return result

def install_license(source):
    with connect() as conn:require_admin(conn)
    public_key=get_setting('license_public_key_b64','').strip()
    if not public_key:raise ValueError('Configurez la clé publique avant activation.')
    src=Path(source)
    if not src.is_file():raise ValueError('Fichier licence introuvable.')
    try:document=json.loads(src.read_text(encoding='utf-8'))
    except Exception as exc:raise ValueError('Fichier licence invalide.') from exc
    verify_license_document(document,public_key)
    dst=_license_path();dst.parent.mkdir(parents=True,exist_ok=True)
    temp=dst.with_suffix('.tmp');temp.write_text(json.dumps(document,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(dst)
    with connect() as conn:audit(conn,'LICENSE_INSTALL',document.get('customer',''),document.get('expires_at',''))
    return license_status()

def assert_license_if_enforced():
    if get_setting('license_enforced','0')!='1':return True
    status=license_status()
    if not status['valid']:raise PermissionError(status['error'] or 'Licence invalide.')
    return True
