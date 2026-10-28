import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class SettingsEnglishTests(unittest.TestCase):
 def test_core_shop_settings_have_explicit_english(self):
  source=(ROOT/"todo"/"screens"/"settings.py").read_text(encoding="utf-8")
  for label in ("Shop and locale","Cash workstation","Stock management","Enable cash closure","Category","Name is required.","User created.","User permissions","Enable / Disable","Search limit must be between 1 and 1000.","Invalid customer receipt number."):self.assertIn(label,source)
if __name__=="__main__":unittest.main()
