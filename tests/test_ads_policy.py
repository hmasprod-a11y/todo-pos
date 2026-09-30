import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"todo"))
from services.ads import is_allowed_surface,placement_for
class AdsPolicyTests(unittest.TestCase):
 def test_cashier_critical_surfaces_are_never_ad_eligible(self):
  for surface in ("sale","payment","change","cash_closure","receipt"):
   self.assertFalse(is_allowed_surface(surface));self.assertIsNone(placement_for(surface))
 def test_offline_provider_never_requires_network_or_tracking(self):
  self.assertTrue(is_allowed_surface("dashboard"));self.assertIsNone(placement_for("dashboard"))
if __name__=="__main__":unittest.main()
