"""Windows print spooler integration for an explicitly configured ESC/POS drawer."""
import os
from database import connect,get_setting
from services.security import audit

PURPOSE_KEYS={
    'receipt':'printer_receipt_name',
    'report':'printer_report_name',
    'addition':'printer_addition_name',
    'c1':'printer_kitchen_c1_name',
    'c2':'printer_kitchen_c2_name',
    'c3':'printer_kitchen_c3_name',
    'c4':'printer_kitchen_c4_name',
}

def installed_printers():
    if os.name!='nt':return []
    import win32print
    return sorted({row[2] for row in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL|win32print.PRINTER_ENUM_CONNECTIONS)})

def printer_for(purpose='receipt'):
    key=PURPOSE_KEYS.get(str(purpose).lower())
    if not key:raise ValueError('Usage imprimante invalide.')
    configured=get_setting(key,'').strip()
    if configured:return configured
    # Legacy installs had a single printer_name. Keep them working.
    if purpose in ('receipt','report','addition'):
        return get_setting('printer_name','').strip()
    return ''

def print_file_windows(path,purpose='report'):
    if os.name!='nt':raise OSError('Impression disponible sous Windows.')
    printer=printer_for(purpose)
    if printer:
        from subprocess import list2cmdline
        os.startfile(str(path),'printto',list2cmdline([printer]))
    else:
        os.startfile(str(path),'print')
    with connect() as conn:audit(conn,'PRINT_FILE',None,f'{purpose}:{printer or "DEFAULT"}')
    return path

def open_drawer():
    if get_setting('drawer_enabled','0')!='1':
        raise ValueError('Activez le tiroir compatible ESC/POS dans Paramètres > Impression.')
    printer=printer_for('receipt')
    if not printer:raise ValueError('Sélectionnez une imprimante de ticket dans les paramètres.')
    pin=get_setting('drawer_pin','0')
    if pin not in ('0','1'):raise ValueError('Connecteur tiroir invalide.')
    if os.name!='nt':raise OSError('Le tiroir est disponible sous Windows.')
    import win32print
    handle=win32print.OpenPrinter(printer)
    try:
        job=win32print.StartDocPrinter(handle,1,('ToDo - Tiroir',None,'RAW'))
        try:
            win32print.StartPagePrinter(handle)
            try:
                payload=bytes((27,112,int(pin),50,250))
                if win32print.WritePrinter(handle,payload)!=len(payload):
                    raise OSError('Commande tiroir incomplète.')
            finally:win32print.EndPagePrinter(handle)
            win32print.EndDocPrinter(handle)
        except Exception:
            win32print.AbortPrinter(handle)
            raise
    finally:win32print.ClosePrinter(handle)
    with connect() as conn:audit(conn,'DRAWER_OPEN',job,printer)
    return job


def test_printer(printer=None, raw=None):
    """Send a small real test job using the configured printer mode."""
    printer=(printer if printer is not None else get_setting('printer_name','')).strip()
    if not printer:
        raise ValueError('Sélectionnez une imprimante dans les paramètres.')
    if os.name!='nt':
        raise OSError('Le test imprimante est disponible sous Windows.')
    if raw is None:
        raw=get_setting('thermal_raw','0')=='1'
    if raw:
        import win32print
        payload=b'\x1b@\x1ba\x01ToDo POS\nTEST IMPRIMANTE\nOK\n\n\x1dV\x00'
        handle=win32print.OpenPrinter(printer)
        try:
            job=win32print.StartDocPrinter(handle,1,('ToDo - Test imprimante',None,'RAW'))
            try:
                win32print.StartPagePrinter(handle)
                try:
                    if win32print.WritePrinter(handle,payload)!=len(payload):
                        raise OSError('Impression test incomplète.')
                finally:
                    win32print.EndPagePrinter(handle)
                win32print.EndDocPrinter(handle)
            except Exception:
                win32print.AbortPrinter(handle)
                raise
        finally:
            win32print.ClosePrinter(handle)
    else:
        import tempfile
        from pathlib import Path
        from subprocess import list2cmdline
        path=Path(tempfile.gettempdir())/'todo_printer_test.txt'
        path.write_text('ToDo POS\nTEST IMPRIMANTE\nOK\n',encoding='utf-8')
        os.startfile(str(path),'printto',list2cmdline([printer]))
        job=str(path)
    with connect() as conn:audit(conn,'PRINTER_TEST',None,printer)
    return job


def print_text_windows(text,purpose='addition',title='ToDo'):
    """Print an arbitrary UTF-8 text document using the configured printer route."""
    if os.name!='nt':raise OSError('Impression disponible sous Windows.')
    printer=printer_for(purpose)
    if not printer:
        raise ValueError(f'Aucune imprimante configurée pour {purpose.upper()}.')
    import tempfile
    from pathlib import Path
    from subprocess import list2cmdline
    safe=''.join(ch for ch in str(purpose).lower() if ch.isalnum() or ch in '-_') or 'print'
    path=Path(tempfile.gettempdir())/f'todo_{safe}.txt'
    path.write_text(str(text),encoding='utf-8')
    os.startfile(str(path),'printto',list2cmdline([printer]))
    with connect() as conn:audit(conn,'PRINT_TEXT',None,f'{purpose}:{printer}:{title}')
    return path
