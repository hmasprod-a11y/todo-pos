import sys,unittest
from pathlib import Path
from unittest.mock import MagicMock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'todo'))
from services.scale import parse_weight,read_weight

class ScaleTests(unittest.TestCase):
    def test_parse_common_scale_formats(self):
        self.assertAlmostEqual(parse_weight(b'ST,GS,  1.245 kg\r\n'),1.245)
        self.assertAlmostEqual(parse_weight('NET 750 g'),0.750)
        self.assertAlmostEqual(parse_weight('2,350'),2.350)
        with self.assertRaises(ValueError):parse_weight('NO WEIGHT')
    def test_serial_read_uses_configurable_port(self):
        device=MagicMock();device.readline.return_value=b'0.825 kg\r\n'
        context=MagicMock();context.__enter__.return_value=device;context.__exit__.return_value=False
        serial=MagicMock();serial.Serial.return_value=context
        with patch.dict(sys.modules,serial=serial):
            self.assertAlmostEqual(read_weight('COM7',9600,500),0.825)
        serial.Serial.assert_called_once_with(port='COM7',baudrate=9600,timeout=0.5)

if __name__=='__main__':unittest.main()
