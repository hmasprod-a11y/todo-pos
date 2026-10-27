"""Windows Tk geometry checks for cashier screens in French, Arabic and English."""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.dont_write_bytecode = True
project = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project / 'todo'))
temporary = tempfile.TemporaryDirectory()
os.environ['TODO_DB_PATH'] = str(Path(temporary.name) / 'cashier-layout.db')

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

    def visible_within(widget, container):
        assert widget.winfo_ismapped(), widget
        x0, y0 = widget.winfo_rootx(), widget.winfo_rooty()
        x1, y1 = x0 + widget.winfo_width(), y0 + widget.winfo_height()
        cx0, cy0 = container.winfo_rootx(), container.winfo_rooty()
        cx1, cy1 = cx0 + container.winfo_width(), cy0 + container.winfo_height()
        assert widget.winfo_width() > 20 and widget.winfo_height() > 10, (widget, widget.winfo_width(), widget.winfo_height())
        assert cx0 <= x0 and cy0 <= y0 and x1 <= cx1 and y1 <= cy1, (widget, (x0,y0,x1,y1), (cx0,cy0,cx1,cy1))

    for language in ('fr', 'ar', 'en'):
        app.change_language(language)
        app.deiconify()
        app.state('normal')
        app.geometry('1366x768+0+0')
        app.show('sale')
        app.update()
        sale = app.current
        assert sale.lang == language
        for widget in (sale.entry, sale.quantity_entry, sale.ticket, sale.total_box, sale.checkout_main, sale.return_button):
            visible_within(widget, app.content)
        app.show('cash')
        app.update()
        cash = app.current
        assert cash.lang == language
        for widget in (cash.info, cash.kpis, cash.details):
            visible_within(widget, app.content)
finally:
    app.destroy()
    temporary.cleanup()

print('CASHIER LAYOUT PASSED: sale and cash controls visible at 1366x768 in fr/ar/en')
