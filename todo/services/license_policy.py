import json, os
from pathlib import Path

import database
from services.secrets import protect_secret,reveal_secret

POLICY_FILE='license_policy.dat'

def _path():
    return Path(database.BASE_DIR)/'data'/POLICY_FILE

def _legacy_policy():
    enforced=database.get_setting('license_enforced','0')=='1'
    public_key=database.get_setting('license_public_key_b64','').strip()
    return {'enforced':enforced,'public_key_b64':public_key}

def load_license_policy():
    path=_path()
    if path.exists():
        try:
            raw=reveal_secret(path.read_text(encoding='utf-8').strip())
            data=json.loads(raw)
            return {'enforced':bool(data.get('enforced')),'public_key_b64':str(data.get('public_key_b64') or '').strip()}
        except Exception as exc:
            raise ValueError('Politique de licence illisible ou altérée.') from exc
    legacy=_legacy_policy()
    if legacy['enforced'] or legacy['public_key_b64']:
        save_license_policy(legacy['public_key_b64'],legacy['enforced'],maintenance=True)
        database.set_setting('license_enforced','0')
        database.set_setting('license_public_key_b64','')
    return legacy

def save_license_policy(public_key_b64,enforced,maintenance=False):
    public_key_b64=(public_key_b64 or '').strip()
    enforced=bool(enforced)
    path=_path()
    current=None
    if path.exists():
        current=load_license_policy()
    maintenance=maintenance or os.environ.get('TODO_LICENSE_MAINTENANCE')=='1'
    if current and current['enforced'] and not maintenance:
        if not enforced:
            raise PermissionError('La protection de licence active ne peut pas être désactivée depuis les paramètres.')
        if current['public_key_b64']!=public_key_b64:
            raise PermissionError('La clé publique active ne peut pas être remplacée depuis les paramètres.')
    if enforced and not public_key_b64:
        raise ValueError('Une clé publique est requise pour activer la protection.')
    path.parent.mkdir(parents=True,exist_ok=True)
    payload=json.dumps({'enforced':enforced,'public_key_b64':public_key_b64},sort_keys=True,separators=(',',':'))
    path.write_text(protect_secret(payload),encoding='utf-8')
    return {'enforced':enforced,'public_key_b64':public_key_b64}
