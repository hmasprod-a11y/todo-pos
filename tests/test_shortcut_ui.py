import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class ShortcutUiTests(unittest.TestCase):
    def test_sale_has_configurable_shortcut_bar(self):
        sale=(ROOT/'todo'/'screens'/'sale.py').read_text(encoding='utf-8')
        settings=(ROOT/'todo'/'screens'/'settings.py').read_text(encoding='utf-8')
        self.assertIn('build_custom_shortcuts',sale)
        self.assertIn('Raccourcis personnalisés',settings)
if __name__=='__main__':unittest.main()
