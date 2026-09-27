import sys,unittest
from pathlib import Path
from unittest.mock import MagicMock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'todo'))
from app import ToDoApp

class CloseConfirmationTests(unittest.TestCase):
    def make_app(self,with_cart=True):
        app=object.__new__(ToDoApp)
        app.lock_window=None
        app.user={'id':1}
        app.sale_frame=MagicMock()
        app.sale_frame.cart=[{'product_id':1}] if with_cart else []
        app.sale_frame.ticket_discount_cents=0
        app.sale_frame.held_id=None
        app.sale_frame.client_id=None
        app.destroy=MagicMock()
        return app
    @patch('app.get_setting',side_effect=lambda key,default='': {'language':'fr','backup_on_close':'1'}.get(key,default))
    @patch('app.messagebox.askyesno',return_value=False)
    def test_cancel_close_keeps_ticket_and_window(self,ask,get_setting):
        app=self.make_app(True)
        app.on_close()
        self.assertTrue(app.sale_frame.cart)
        app.destroy.assert_not_called()
        app.sale_frame.focus_search.assert_called_once()
    @patch('app.create_backup')
    @patch('services.sales.hold_sale')
    @patch('app.get_setting',side_effect=lambda key,default='': {'language':'fr','backup_on_close':'1'}.get(key,default))
    @patch('app.messagebox.askyesno',return_value=True)
    def test_confirm_close_holds_ticket_backups_then_closes(self,ask,get_setting,hold,backup):
        app=self.make_app(True)
        app.on_close()
        hold.assert_called_once()
        backup.assert_called_once()
        self.assertEqual(app.sale_frame.cart,[])
        app.destroy.assert_called_once()

if __name__=='__main__':unittest.main()
