import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"todo"))
from services.fiscal_connectors import availability,connector_for_country
class FiscalConnectorTests(unittest.TestCase):
 def test_no_country_claims_fiscal_connector_before_verification(self):
  for code in ("MA","FR","GB","AE"):
   self.assertIsNone(connector_for_country(code));self.assertFalse(availability(code)["available"])
if __name__=="__main__":unittest.main()
