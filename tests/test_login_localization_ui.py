import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class LoginLocalizationUiTests(unittest.TestCase):
 def test_login_uses_json_translations_and_mirrors_user_input_for_arabic(self):
  source=(ROOT/"todo"/"screens"/"login.py").read_text(encoding="utf-8")
  self.assertIn('self.tr=Translator(self.lang)',source)
  self.assertIn('self.tr("login.invalid")',source)
  self.assertIn('justify="right" if self.rtl else "left"',source)
if __name__=="__main__":unittest.main()
