import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class EditionStatusUiTests(unittest.TestCase):
 def test_about_help_exposes_the_central_free_or_pro_edition(self):
  source=(ROOT/"todo"/"screens"/"settings.py").read_text(encoding="utf-8")
  self.assertIn("(self.tr('Édition','الإصدار','Edition'),d['edition'])",source)
if __name__=="__main__":unittest.main()
