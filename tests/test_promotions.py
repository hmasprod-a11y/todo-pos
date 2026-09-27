import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'todo'))
import database
from services.bootstrap import ensure_defaults
from services.security import current_user
from services.promotions import list_promotions,save_promotion,set_promotion_active,delete_promotion

class PromotionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.old=database.DB_PATH;database.DB_PATH=Path(self.tmp.name)/'db.sqlite'
        database.init_db();ensure_defaults()
        with database.connect() as c:
            self.uid=c.execute("SELECT id FROM users").fetchone()[0]
            self.pid=c.execute("INSERT INTO products(name,sale_price_cents,stock_qty,active) VALUES('Promo Item',1000,10,1)").lastrowid
        self.token=current_user.set(self.uid)
    def tearDown(self):
        current_user.reset(self.token);database.DB_PATH=self.old;self.tmp.cleanup()
    def test_promotion_crud_and_activation(self):
        promo=save_promotion(self.pid,2,800,'UNIT')
        row=list_promotions('Promo')[0]
        self.assertEqual(row['id'],promo);self.assertEqual(row['unit_price_cents'],800);self.assertEqual(row['min_qty'],2)
        set_promotion_active(promo,False)
        self.assertEqual(list_promotions('',True),[])
        save_promotion(self.pid,3,700,'BUNDLE',promo)
        row=list_promotions()[0];self.assertEqual(row['pricing_mode'],'BUNDLE');self.assertEqual(row['min_qty'],3)
        delete_promotion(promo);self.assertEqual(list_promotions(),[])
    def test_invalid_promotion_is_rejected(self):
        for qty,price,mode in [(0,100,'UNIT'),(2,-1,'UNIT'),(2,100,'BAD')]:
            with self.assertRaises(ValueError):save_promotion(self.pid,qty,price,mode)

if __name__=='__main__':unittest.main()
