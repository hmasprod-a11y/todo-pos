from database import get_setting,set_setting
from services.security import require_permission

ALLOWED_SHORTCUTS=(
    'calculator','held','drawer','duplicate','price_grid',
    'expense','report','closure','keyboard'
)
DEFAULT_SHORTCUTS=('calculator','held','drawer')

def get_shortcuts():
    raw=get_setting('custom_shortcuts',','.join(DEFAULT_SHORTCUTS))
    result=[]
    for key in str(raw or '').split(','):
        key=key.strip()
        if key in ALLOWED_SHORTCUTS and key not in result:
            result.append(key)
    return result[:6] or list(DEFAULT_SHORTCUTS)

def save_shortcuts(keys):
    require_permission('SETTINGS')
    selected=[]
    for key in keys:
        key=str(key).strip()
        if key not in ALLOWED_SHORTCUTS:
            raise ValueError('Raccourci invalide.')
        if key not in selected:selected.append(key)
    if len(selected)>6:
        raise ValueError('Maximum 6 raccourcis.')
    set_setting('custom_shortcuts',','.join(selected))
    return selected
