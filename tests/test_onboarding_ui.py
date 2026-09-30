import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class FirstRunWizardUiTests(unittest.TestCase):
 def test_app_opens_wizard_before_login_when_setup_is_incomplete(self):
  app=(ROOT/"todo"/"app.py").read_text(encoding="utf-8");wizard=(ROOT/"todo"/"screens"/"onboarding.py").read_text(encoding="utf-8")
  self.assertIn("is_complete() else FirstRunWizard",app);self.assertIn("select_country_profile",wizard);self.assertIn("mark_complete()",wizard);self.assertIn('geometry("560x650")',wizard);self.assertIn('entry.configure(justify="right" if rtl else "left")',wizard);self.assertIn("self.language_box",wizard)
if __name__=="__main__":unittest.main()
