import sys,tempfile,unittest
from pathlib import Path
from unittest.mock import MagicMock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'todo'))
import database
from services.bootstrap import ensure_defaults
from services.security import current_user
from services.rfid import bind_tag,lookup_tag,get_tag_for_target,read_tag

class RFIDTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.old=database.DB_PATH;database.DB_PATH=Path(self.tmp.name)/'db.sqlite'
        database.init_db();ensure_defaults()
        with database.connect() as c:
            self.uid=c.execute("SELECT id FROM users WHERE username='admin'").fetchone()[0]
            self.pid=c.execute("INSERT INTO products(name,sale_price_cents) VALUES('RFID Product',1000)").lastrowid
            self.cid=c.execute("INSERT INTO clients(name) VALUES('RFID Client')").lastrowid
        self.token=current_user.set(self.uid)
    def tearDown(self):
        current_user.reset(self.token);database.DB_PATH=self.old;self.tmp.cleanup()
    def test_bind_and_lookup_product_and_client(self):
        bind_tag('ABC12345','PRODUCT',self.pid);bind_tag('CLI98765','CLIENT',self.cid)
        self.assertEqual(lookup_tag('ABC12345')['target_id'],self.pid)
        self.assertEqual(get_tag_for_target('CLIENT',self.cid),'CLI98765')
        with self.assertRaises(ValueError):bind_tag('ABC12345','CLIENT',self.cid)
    def test_serial_reader_returns_tag(self):
        device=MagicMock();device.readline.return_value=b'TAG778899\r\n'
        ctx=MagicMock();ctx.__enter__.return_value=device;ctx.__exit__.return_value=False
        serial=MagicMock();serial.Serial.return_value=ctx
        with patch.dict(sys.modules,serial=serial):
            self.assertEqual(read_tag('COM9',9600,500),'TAG778899')

if __name__=='__main__':unittest.main()
