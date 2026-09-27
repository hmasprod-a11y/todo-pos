import sys,unittest
from pathlib import Path
from unittest.mock import MagicMock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'todo'))
from services.customer_serial_display import sale_lines,payment_lines,write_lines

class CustomerSerialDisplayTests(unittest.TestCase):
    def test_formats_20_column_display(self):
        a,b=sale_lines([{'name':'Lait entier','qty':2}],1234,20,'DH')
        self.assertEqual(len(a),20);self.assertEqual(len(b),20);self.assertIn('2x Lait entier',a);self.assertIn('12.34 DH',b)
        p,c=payment_lines(2000,766,20,'DH')
        self.assertIn('20.00 DH',p);self.assertIn('7.66 DH',c)
    def test_serial_payload_contains_init_and_two_lines(self):
        device=MagicMock();ctx=MagicMock();ctx.__enter__.return_value=device;ctx.__exit__.return_value=False
        serial=MagicMock();serial.Serial.return_value=ctx
        with patch.dict(sys.modules,serial=serial):
            self.assertTrue(write_lines('TODO','TOTAL 10.00 DH','COM4',9600,500,20))
        payload=device.write.call_args[0][0]
        self.assertTrue(payload.startswith(b'\x1b@'));self.assertIn(b'TOTAL 10.00 DH',payload)
        serial.Serial.assert_called_once_with(port='COM4',baudrate=9600,timeout=0.5,write_timeout=0.5)

if __name__=='__main__':unittest.main()
