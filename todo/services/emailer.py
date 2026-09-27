import smtplib,ssl
from email.message import EmailMessage
from pathlib import Path
from database import get_setting,connect
from services.security import audit

def email_settings():
    try:port=int(get_setting('smtp_port','587'))
    except (TypeError,ValueError):port=587
    return {
        'enabled':get_setting('email_enabled','0')=='1',
        'host':get_setting('smtp_host','smtp.gmail.com').strip(),
        'port':port,
        'user':get_setting('smtp_user','').strip(),
        'password':get_setting('smtp_app_password',''),
        'from_name':get_setting('smtp_from_name','ToDo').strip() or 'ToDo',
    }

def _validate_address(value):
    value=(value or '').strip()
    if '@' not in value or value.startswith('@') or value.endswith('@'):raise ValueError('Adresse e-mail invalide')
    return value

def send_email(to,subject,body,attachments=None,settings=None):
    cfg=settings or email_settings()
    if not cfg.get('enabled',False):raise ValueError('Activez l’envoi e-mail dans Paramètres.')
    host=(cfg.get('host') or '').strip();user=_validate_address(cfg.get('user'));password=cfg.get('password') or ''
    if not host or not password:raise ValueError('Configuration SMTP incomplète.')
    to=_validate_address(to)
    msg=EmailMessage();msg['From']=f"{cfg.get('from_name') or 'ToDo'} <{user}>";msg['To']=to;msg['Subject']=str(subject or 'ToDo')
    msg.set_content(str(body or ''))
    for item in attachments or []:
        path=Path(item)
        data=path.read_bytes()
        suffix=path.suffix.lower()
        if suffix=='.pdf':maintype,subtype='application','pdf'
        elif suffix=='.csv':maintype,subtype='text','csv'
        else:maintype,subtype='application','octet-stream'
        msg.add_attachment(data,maintype=maintype,subtype=subtype,filename=path.name)
    context=ssl.create_default_context()
    with smtplib.SMTP(host,int(cfg.get('port') or 587),timeout=15) as smtp:
        smtp.ehlo();smtp.starttls(context=context);smtp.ehlo();smtp.login(user,password);smtp.send_message(msg)
    with connect() as conn:audit(conn,'EMAIL_SENT',None,f'{to}: {subject}')
    return True

def test_email_connection(to=None,settings=None):
    cfg=settings or email_settings()
    recipient=to or cfg.get('user')
    return send_email(recipient,'ToDo - Test e-mail','Configuration e-mail ToDo opérationnelle.',settings=cfg)
