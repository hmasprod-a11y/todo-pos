"""Capture real Windows Tk screens and record display clipping for design review.

These images are evidence from the running app, not rendered mockups. Geometry
metadata makes an off-screen window visible even when its screenshot is cropped.
"""
import faulthandler
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.dont_write_bytecode = True
project = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project / "todo"))
temporary = tempfile.TemporaryDirectory()
os.environ["TODO_DB_PATH"] = str(Path(temporary.name) / "visual-capture.db")

from PIL import ImageGrab, ImageStat
from app import ToDoApp
from screens.onboarding import FirstRunWizard
from screens.products import ProductEditor

output = project / "qa-evidence" / "ui-visual"
output.mkdir(parents=True, exist_ok=True)
app = ToDoApp()
def raise_tk_exception(kind, value, traceback):
    raise value.with_traceback(traceback)
app.report_callback_exception = raise_tk_exception
records = []
faulthandler.dump_traceback_later(120, repeat=True)


def capture(window, language, route):
    print(f'Capture start: {language}/{route}', flush=True)
    app.update_idletasks()
    app.update()
    screen = (app.winfo_screenwidth(), app.winfo_screenheight())
    bounds = (window.winfo_rootx(), window.winfo_rooty(),
              window.winfo_width(), window.winfo_height())
    x, y, width, height = bounds
    visible = (max(0, x), max(0, y),
               min(screen[0], x + width), min(screen[1], y + height))
    if visible[2] <= visible[0] or visible[3] <= visible[1]:
        raise AssertionError(f"{route} has no visible area: {bounds}")
    image = ImageGrab.grab(bbox=visible).convert("RGB")
    if max(ImageStat.Stat(image).stddev) < 2:
        raise AssertionError(f"{route} screenshot is blank")
    relative = Path(language) / f"{route}.png"
    path = output / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)
    print(f'Capture saved: {language}/{route}', flush=True)
    records.append({
        "language": language, "route": route,
        "file": str(relative).replace("\\", "/"),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "display": screen, "window": bounds,
        "visible_capture": visible,
        "outside_display": x < 0 or y < 0 or x + width > screen[0] or y + height > screen[1],
    })


try:
    wizard = next(child for child in app.winfo_children()
                  if isinstance(child, FirstRunWizard))
    for language in ("fr", "ar", "en"):
        wizard.language.set(language)
        app.update()
        if not wizard.start.winfo_ismapped():
            raise AssertionError(f"{language}: onboarding start is hidden")
        if wizard.start.winfo_rooty() + wizard.start.winfo_height() > wizard.winfo_rooty() + wizard.winfo_height():
            raise AssertionError(f"{language}: onboarding start is clipped")
        capture(wizard, language, "onboarding")
    wizard.pin.set("9876")
    wizard.pin_confirm.set("9876")
    wizard.finish()
    app.withdraw()
    with patch("tkinter.simpledialog.askstring", side_effect=["9876", "9876"]):
        app.login_pin.set("9876")
        app.login()
    app.deiconify()
    app.state("normal")
    for language in ("fr", "ar", "en"):
        print(f'Language start: {language}', flush=True)
        app.change_language(language)
        app.geometry("1366x768+0+0")
        for route in (
            "home", "sale", "products", "management", "stock", "inventory",
            "inventory_sessions", "sorties", "purchases", "suppliers",
            "supplier_payments", "supplier_returns", "clients",
            "customer_orders", "quotations", "loyalty", "promotions",
            "returns", "cash", "journal", "statistics", "settings",
            "rendez_vous",
        ):
            app.show(route)
            capture(app, language, route)
        app.show("products")
        editor = ProductEditor(app.current)
        app.update()
        for button in (editor.save_button, editor.cancel_button):
            if not button.winfo_ismapped():
                raise AssertionError(f"{language}: product action is hidden")
            bottom = button.winfo_rooty() + button.winfo_height()
            if bottom > editor.winfo_rooty() + editor.winfo_height():
                raise AssertionError(f"{language}: product action is clipped")
        capture(editor, language, "product-editor")
        editor.body_canvas.yview_moveto(1.0)
        capture(editor, language, "product-editor-bottom")
        editor.destroy()
finally:
    app.destroy()
    temporary.cleanup()

manifest = {
    "source_commit": os.environ.get("GITHUB_SHA", "local"),
    "capture_method": "Pillow ImageGrab of the running Windows Tk application",
    "requested_window": [1366, 768],
    "records": records,
}
(output / "manifest.json").write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(f"Captured {len(records)} real Windows screenshots in {output}")
