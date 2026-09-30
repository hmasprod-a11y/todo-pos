import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class MsixPackagingTests(unittest.TestCase):
 def test_msix_template_requires_real_identity_and_official_assets(self):
  manifest=(ROOT/"packaging"/"msix"/"AppxManifest.xml.template").read_text(encoding="utf-8")
  script=(ROOT/"packaging"/"msix"/"build_msix.ps1").read_text(encoding="utf-8")
  self.assertIn("{{IDENTITY_NAME}}",manifest);self.assertIn("{{PUBLISHER}}",manifest)
  self.assertIn("MakeAppx.exe",script);self.assertIn("Missing required Store asset",script)
if __name__=="__main__":unittest.main()
