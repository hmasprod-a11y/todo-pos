import sys,tempfile,unittest
from pathlib import Path
from unittest.mock import MagicMock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'todo'))
import database
from services import backup
from services.bootstrap import ensure_defaults
from services.security import current_user
from services.emailer import send_email

class EmailTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.old=database.DB_PATH
        database.DB_PATH=Path(self.tmp.name)/'db.sqlite';backup.DB_PATH=database.DB_PATH;backup.BASE=Path(self.tmp.name)
        database.init_db();ensure_defaults()
        with database.connect() as c:self.uid=c.execute("SELECT id FROM users WHERE username='admin'").fetchone()[0]
        self.token=current_user.set(self.uid)
    def tearDown(self):
        current_user.reset(self.token);database.DB_PATH=self.old;self.tmp.cleanup()
    def test_smtp_tls_login_and_attachment(self):
        attachment=Path(self.tmp.name)/'report.csv';attachment.write_text('a,b\n1,2\n',encoding='utf-8')
        smtp=MagicMock();ctx=MagicMock();ctx.__enter__.return_value=smtp;ctx.__exit__.return_value=False
        cfg={'enabled':True,'host':'smtp.gmail.com','port':587,'user':'shop@example.com','password':'app-pass','from_name':'ToDo','subject':'Objet magasin'}
        with patch('services.emailer.smtplib.SMTP',return_value=ctx):
            self.assertTrue(send_email('client@example.com','Rapport','Bonjour',[attachment],cfg))
        smtp.starttls.assert_called_once();smtp.login.assert_called_once_with('shop@example.com','app-pass');smtp.send_message.assert_called_once()
        msg=smtp.send_message.call_args[0][0]
        self.assertEqual(msg['To'],'client@example.com');self.assertEqual(msg['Subject'],'Objet magasin');self.assertEqual(len(list(msg.iter_attachments())),1)

    def test_blank_configured_subject_keeps_message_subject(self):
        smtp=MagicMock();ctx=MagicMock();ctx.__enter__.return_value=smtp;ctx.__exit__.return_value=False
        cfg={'enabled':True,'host':'smtp.gmail.com','port':587,'user':'shop@example.com','password':'app-pass','from_name':'ToDo','subject':''}
        with patch('services.emailer.smtplib.SMTP',return_value=ctx):
            self.assertTrue(send_email('client@example.com','Ticket 42','Bonjour',settings=cfg))
        msg=smtp.send_message.call_args[0][0]
        self.assertEqual(msg['Subject'],'Ticket 42')

if __name__=='__main__':unittest.main()
