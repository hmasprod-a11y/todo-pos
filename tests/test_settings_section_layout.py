import re,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class SettingsSectionLayoutTests(unittest.TestCase):
    def setUp(self):
        self.text=(ROOT/'todo'/'screens'/'settings.py').read_text(encoding='utf-8')

    def _block(self,start,end):
        a=self.text.index(start)
        b=self.text.index(end,a)
        return self.text[a:b]

    def test_category_editor_save_does_not_overlap_icon_row(self):
        block=self._block("ttk.Label(f, text=self.tr('Nom'","    def _pick")
        self.assertIn("grid(row=3",block)
        self.assertIn("grid(row=4",block)
        self.assertNotIn("grid(row=16",block)

    def test_configuration_suite_barcode_has_real_row(self):
        block=self._block("suite=ttk.LabelFrame","        self.print_mode_box=")
        self.assertIn("receipt_show_barcode).grid(row=3",block)
        self.assertNotIn("grid(row=16",block)

    def test_peripheral_and_mail_sections_have_no_row_16_placeholders(self):
        for start,end in [
            ("p=ttk.LabelFrame(self,text=self.tr('Impression'","scale=ttk.LabelFrame"),
            ("scale=ttk.LabelFrame","d=ttk.LabelFrame"),
            ("serial_display=ttk.LabelFrame","        self.refresh_customer_serial_ports()"),
            ("rfid=ttk.LabelFrame","        self.refresh_rfid_ports()"),
            ("mail=ttk.LabelFrame","b=ttk.LabelFrame"),
        ]:
            with self.subTest(section=start):
                self.assertNotIn("grid(row=16",self._block(start,end))

if __name__=='__main__':unittest.main()
