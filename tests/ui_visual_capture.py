"""Capture real Windows Tk screens and record display clipping for design review.

These images are evidence from the running app, not rendered mockups. Geometry
metadata makes an off-screen window visible even when its screenshot is cropped.
"""
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
records = []


def capture(window, language, route):
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
        app.change_language(language)
        app.geometry("1366x768+0+0")
        for route in ("sale", "products", "stock", "cash", "statistics", "settings"):
            app.show(route)
            capture(app, language, route)
        app.show("products")
        editor = ProductEditor(app.current)
        capture(editor, language, "product-editor")
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
