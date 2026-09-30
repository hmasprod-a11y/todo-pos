import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class StoreVideoStoryboardTests(unittest.TestCase):
 def test_storyboard_covers_required_store_demo_flow(self):
  text=(ROOT/"docs"/"STORE_DEMO_VIDEO_STORYBOARD.md").read_text(encoding="utf-8")
  for step in ("Scan","Cart","Pay","Change","Receipt","Stock"):self.assertIn(step,text)
if __name__=="__main__":unittest.main()
