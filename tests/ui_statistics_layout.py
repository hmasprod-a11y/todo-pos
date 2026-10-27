"""Windows Tk layout regression for Statistics at the required 1366x768 size."""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.dont_write_bytecode = True
project = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project / 'todo'))
temporary = tempfile.TemporaryDirectory()
os.environ['TODO_DB_PATH'] = str(Path(temporary.name) / 'statistics-layout.db')

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

    for language in ('fr', 'ar', 'en'):
        app.change_language(language)
        app.state('normal')
        app.geometry('1366x768+0+0')
        app.show('statistics')
        app.update()
        stats = app.current
        assert stats.lang == language
        assert len(stats._kpi_labels) == 9
        cards = stats.kpi_frame.grid_slaves()
        positions = {(int(card.grid_info()['row']), int(card.grid_info()['column'])) for card in cards}
        assert positions == {(row, col) for row in range(3) for col in range(3)}, (language, positions)
        canvas = stats.stats_canvas
        assert canvas.winfo_width() > 1000 and canvas.winfo_height() > 500
        assert canvas.bbox('all')[3] > canvas.winfo_height(), language
        canvas.yview_moveto(1.0)
        app.update()
        assert canvas.yview()[1] > 0.99, (language, canvas.yview())
        summary = stats.finance_summary
        assert summary.winfo_rooty() >= canvas.winfo_rooty(), language
        assert summary.winfo_rooty() + summary.winfo_height() <= canvas.winfo_rooty() + canvas.winfo_height(), language
finally:
    app.destroy()
    temporary.cleanup()

print('STATISTICS LAYOUT PASSED: fr/ar/en KPIs and lower summaries reachable at 1366x768')
