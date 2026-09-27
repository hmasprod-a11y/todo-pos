import sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'todo'))
import database
from services.order_slips import build_addition,build_preparation_slip

class OrderSlipTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.old=database.DB_PATH
        database.DB_PATH=Path(self.tmp.name)/'db.sqlite';database.init_db()
        database.set_setting('shop_name','TODO TEST');database.set_setting('workstation_code','02')
        self.cart=[
            {'name':'Café','qty':2,'unit_price_cents':500,'discount_cents':100},
            {'name':'Eau','qty':1,'unit_price_cents':300,'discount_cents':0},
        ]
    def tearDown(self):
        database.DB_PATH=self.old;self.tmp.cleanup()
    def test_addition_contains_prices_discount_and_total(self):
        text=build_addition(self.cart,200,'DH')
        self.assertIn('ADDITION',text);self.assertIn('POSTE 02',text)
        self.assertIn('Café',text);self.assertIn('5.00 DH',text)
        self.assertIn('REMISE TICKET: 2.00 DH',text)
        self.assertIn('TOTAL: 10.00 DH',text)
    def test_preparation_has_quantities_without_prices(self):
        text=build_preparation_slip(self.cart,'C3')
        self.assertIn('BON PREPARATION C3',text);self.assertIn('2 x Café',text);self.assertIn('1 x Eau',text)
        self.assertNotIn('DH',text);self.assertNotIn('TOTAL',text)
    def test_invalid_station_is_rejected(self):
        with self.assertRaises(ValueError):build_preparation_slip(self.cart,'C5')

if __name__=='__main__':unittest.main()
