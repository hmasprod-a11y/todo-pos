import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class SettingsServicesEnglishTests(unittest.TestCase):
 def test_rfid_email_and_data_settings_have_english(self):
  s=(ROOT/"todo"/"screens"/"settings.py").read_text(encoding="utf-8")
  for x in ("Enable RFID","Email / Gmail","Test email","Back up now"):self.assertIn(x,s)
if __name__=="__main__":unittest.main()
