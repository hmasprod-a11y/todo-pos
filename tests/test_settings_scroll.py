import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class SettingsScrollTests(unittest.TestCase):
    def test_settings_page_is_scrollable(self):
        text=(ROOT/'todo'/'screens'/'settings.py').read_text(encoding='utf-8')
        start=text.index('class SettingsFrame')
        end=text.index('    def shortcut_tools',start)
        block=text[start:end]
        self.assertIn('self.settings_canvas=tk.Canvas(self',block)
        self.assertIn("self.settings_scroll=ttk.Scrollbar(self,orient='vertical'",block)
        self.assertIn("create_window((0,0),window=body",block)
        self.assertIn("scrollregion=self.settings_canvas.bbox('all')",block)
        self.assertIn("itemconfigure(self.settings_window,width=e.width)",block)
        for section in (
            "ttk.LabelFrame(body,text=self.tr('Magasin et vente'",
            "ttk.LabelFrame(body,text=self.tr('Impression'",
            "ttk.LabelFrame(body,text=self.tr('Balance électronique'",
            "ttk.LabelFrame(body,text=self.tr('RFID'",
            "ttk.LabelFrame(body,text=self.tr('E-mail / Gmail'",
            "ttk.LabelFrame(body,text=self.tr('Données'",
            "ttk.LabelFrame(body,text=self.tr('Utilisateurs'",
        ):
            self.assertIn(section,block)

if __name__=='__main__':unittest.main()
