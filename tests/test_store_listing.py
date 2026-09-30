import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class StoreListingTests(unittest.TestCase):
 def test_store_listing_is_shipped_in_all_three_store_languages(self):
  for language in ("EN","FR","AR"):
   text=(ROOT/"docs"/f"STORE_LISTING_{language}.md").read_text(encoding="utf-8")
   self.assertIn("ToDo POS",text);self.assertIn("offline" if language=="EN" else "hors ligne" if language=="FR" else "دون اتصال",text)
if __name__=="__main__":unittest.main()
