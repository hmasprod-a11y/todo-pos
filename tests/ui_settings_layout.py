"""Windows Tk regression for Settings administration controls in all languages."""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
import tkinter.ttk as ttk

sys.dont_write_bytecode = True
project = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project / 'todo'))
temporary = tempfile.TemporaryDirectory()
os.environ['TODO_DB_PATH'] = str(Path(temporary.name) / 'settings-layout.db')

from app import ToDoApp
from screens.onboarding import FirstRunWizard

app = ToDoApp()
try:
    wizard = next(child for child in app.winfo_children() if isinstance(child, FirstRunWizard))
    wizard.pin.set('9876')
    wizard.pin_confirm.set('9876')
    wizard.finish()
    app.withdraw()
    with patch('tkinter.simpledialog.askstring', side_effect=['9876', '9876']):
        app.login_pin.set('9876')
        app.login()

    expected = {
        'fr': ('Données', 'Utilisateurs', 'Restaurer backup'),
        'ar': ('البيانات', 'المستخدمون', 'استرجاع نسخة احتياطية'),
        'en': ('Data', 'Users', 'Restore backup'),
    }
    for language, (data_title, users_title, restore_label) in expected.items():
        app.change_language(language)
        app.deiconify()
        app.state('normal')
        app.geometry('1366x768+0+0')
        app.show('settings')
        app.update()
        page = app.current
        canvas = page.settings_canvas
        body = canvas.nametowidget(canvas.itemcget(page.settings_window, 'window'))
        groups = {widget.cget('text'): widget for widget in body.winfo_children() if isinstance(widget, ttk.LabelFrame)}
        data, users = groups[data_title], groups[users_title]
        assert len(data.winfo_children()) == 2, language
        assert len(users.winfo_children()) == 3, language
        assert data.winfo_reqwidth() <= canvas.winfo_width(), (language, 'data', data.winfo_reqwidth(), canvas.winfo_width())
        assert users.winfo_reqwidth() <= canvas.winfo_width(), (language, 'users', users.winfo_reqwidth(), canvas.winfo_width())
        labels = [button.cget('text') for row in data.winfo_children() for button in row.winfo_children() if isinstance(button, ttk.Button)]
        assert restore_label in labels, (language, labels)
        for group in (data, users):
            for row in group.winfo_children()[:2]:
                buttons = [child for child in row.winfo_children() if isinstance(child, ttk.Button)]
                if buttons:
                    last = buttons[-1]
                    assert last.winfo_rootx() + last.winfo_width() <= canvas.winfo_rootx() + canvas.winfo_width(), (language, last.cget('text'))
finally:
    app.destroy()
    temporary.cleanup()

print('SETTINGS LAYOUT PASSED: fr/ar/en administration controls fit at 1366x768')
