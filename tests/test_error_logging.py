import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'todo'))
import database
from services import error_logging

class DummyRoot:
    report_callback_exception=None

class ErrorLoggingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.old_base=database.BASE_DIR
        database.BASE_DIR=Path(self.tmp.name)
    def tearDown(self):
        database.BASE_DIR=self.old_base;self.tmp.cleanup()

    def test_exception_is_written_to_support_log(self):
        try:
            raise RuntimeError('boom-for-log')
        except RuntimeError:
            exc_type,exc_value,exc_tb=sys.exc_info()
        path=error_logging.write_exception(exc_type,exc_value,exc_tb,'unit test')
        text=path.read_text(encoding='utf-8')
        self.assertIn('unit test',text);self.assertIn('RuntimeError: boom-for-log',text)

    def test_tk_callback_handler_is_installed(self):
        root=DummyRoot()
        hook=error_logging.install_exception_handlers(root)
        self.assertIs(root.report_callback_exception,hook)
        self.assertTrue(callable(sys.excepthook))

if __name__=='__main__':unittest.main()
