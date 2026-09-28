import sys
import traceback
from datetime import datetime
from pathlib import Path

import database

LOG_NAME='todo.log'

def log_path():
    path=Path(database.BASE_DIR)/'logs'/LOG_NAME
    path.parent.mkdir(parents=True,exist_ok=True)
    return path

def write_exception(exc_type, exc_value, exc_tb, context='Unhandled exception'):
    path=log_path()
    stamp=datetime.now().isoformat(timespec='seconds')
    detail=''.join(traceback.format_exception(exc_type,exc_value,exc_tb))
    with path.open('a',encoding='utf-8') as fh:
        fh.write(f"\n[{stamp}] {context}\n{detail}")
    return path

def install_exception_handlers(root):
    previous=sys.excepthook

    def global_hook(exc_type,exc_value,exc_tb):
        try:
            write_exception(exc_type,exc_value,exc_tb,'sys.excepthook')
        finally:
            if previous and previous is not global_hook:
                previous(exc_type,exc_value,exc_tb)

    def tk_hook(exc_type,exc_value,exc_tb):
        path=None
        try:
            path=write_exception(exc_type,exc_value,exc_tb,'Tk callback')
        except Exception:
            pass
        try:
            from tkinter import messagebox
            messagebox.showerror(
                'ToDo',
                'Une erreur inattendue est survenue.\n\n'
                'Le détail a été enregistré pour le support'
                + (f' :\n{path}' if path else '.'),
                parent=root
            )
        except Exception:
            pass

    sys.excepthook=global_hook
    root.report_callback_exception=tk_hook
    return tk_hook
