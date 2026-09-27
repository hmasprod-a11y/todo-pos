import math,re
from database import get_setting

_NUMBER=re.compile(r'[-+]?\d+(?:[.,]\d+)?')

def serial_ports():
    try:
        from serial.tools import list_ports
        return [p.device for p in list_ports.comports()]
    except Exception:
        return []

def parse_weight(payload):
    if isinstance(payload,bytes):
        payload=payload.decode('ascii','ignore')
    text=str(payload or '').strip()
    match=_NUMBER.search(text)
    if not match:raise ValueError('Poids illisible')
    value=float(match.group(0).replace(',','.'))
    lower=text.lower()
    if ' kg' in lower or lower.endswith('kg'):
        kg=value
    elif ' g' in lower or lower.endswith('g'):
        kg=value/1000.0
    else:
        # Most retail scales configured for POS expose kilograms.
        kg=value
    if not math.isfinite(kg) or kg<=0 or kg>1000:
        raise ValueError('Poids invalide')
    return kg

def read_weight(port=None,baudrate=None,timeout_ms=None):
    explicit=port is not None
    if not explicit and get_setting('scale_enabled','0')!='1':
        raise ValueError('Activez la balance dans Paramètres.')
    port=(port if explicit else get_setting('scale_port','')).strip()
    if not port:raise ValueError('Sélectionnez le port COM de la balance.')
    try:baud=int(baudrate if baudrate is not None else get_setting('scale_baudrate','9600'))
    except (TypeError,ValueError):raise ValueError('BaudRate invalide')
    try:timeout=max(100,int(timeout_ms if timeout_ms is not None else get_setting('scale_timeout_ms','800')))/1000.0
    except (TypeError,ValueError):raise ValueError('Timeout invalide')
    import serial
    try:
        with serial.Serial(port=port,baudrate=baud,timeout=timeout) as device:
            # Generic retail-scale handshake: clear stale bytes, then accept either
            # spontaneous continuous output or a response after CR.
            try:device.reset_input_buffer()
            except Exception:pass
            line=device.readline()
            if not line:
                try:device.write(b'\r')
                except Exception:pass
                line=device.readline()
    except Exception as error:
        raise OSError(f'Balance {port}: {error}') from error
    if not line:raise TimeoutError('Aucune donnée reçue de la balance.')
    return parse_weight(line)
