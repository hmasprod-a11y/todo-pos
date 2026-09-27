from database import get_setting

def serial_ports():
    try:
        from serial.tools import list_ports
        return [p.device for p in list_ports.comports()]
    except Exception:
        return []

def _ascii(text):
    return str(text or '').encode('ascii','replace').decode('ascii')

def _fit(text,width):
    width=max(8,min(int(width),40))
    return _ascii(text)[:width].ljust(width)

def sale_lines(cart,total_cents,width=20,currency='DH'):
    if cart:
        last=cart[-1]
        qty=float(last.get('qty',1))
        name=str(last.get('name','ARTICLE'))
        line1=f"{qty:g}x {name}"
    else:
        line1='BIENVENUE TODO'
    line2=f"TOTAL {int(total_cents)/100:.2f} {currency}"
    return _fit(line1,width),_fit(line2,width)

def payment_lines(paid_cents,change_cents,width=20,currency='DH'):
    return _fit(f"PAYE {int(paid_cents)/100:.2f} {currency}",width),_fit(f"MONNAIE {int(change_cents)/100:.2f} {currency}",width)

def write_lines(line1,line2,port=None,baudrate=None,timeout_ms=None,width=None):
    explicit=port is not None
    if not explicit and get_setting('customer_serial_enabled','0')!='1':
        return False
    port=(port if explicit else get_setting('customer_serial_port','')).strip()
    if not port:raise ValueError('Sélectionnez le port COM de l’afficheur client.')
    baud=int(baudrate if baudrate is not None else get_setting('customer_serial_baudrate','9600'))
    timeout=max(100,int(timeout_ms if timeout_ms is not None else get_setting('customer_serial_timeout_ms','500')))/1000.0
    width=int(width if width is not None else get_setting('customer_serial_width','20'))
    payload=(b'\x1b@'+_fit(line1,width).encode('ascii','replace')+b'\r\n'+_fit(line2,width).encode('ascii','replace'))
    import serial
    with serial.Serial(port=port,baudrate=baud,timeout=timeout,write_timeout=timeout) as device:
        device.write(payload);device.flush()
    return True

def show_sale(cart,total_cents):
    currency=get_setting('currency','DH');width=int(get_setting('customer_serial_width','20'))
    a,b=sale_lines(cart,total_cents,width,currency)
    return write_lines(a,b,width=width)

def show_payment(paid_cents,change_cents):
    currency=get_setting('currency','DH');width=int(get_setting('customer_serial_width','20'))
    a,b=payment_lines(paid_cents,change_cents,width,currency)
    return write_lines(a,b,width=width)
