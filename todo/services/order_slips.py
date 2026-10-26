from database import get_setting
from services.money import fmt
from services.pricing import line_total
from services.printers import print_text_windows

def _money_line(line):
    qty=float(line.get('qty',0))
    unit=int(float(line.get('unit_price_cents',0)))
    gross=line_total(unit,qty)-int(line.get('discount_cents',0))
    return qty,unit,max(0,gross)

def build_addition(cart,ticket_discount_cents=0,currency=None):
    if not cart:raise ValueError('Ticket vide.')
    currency=currency or get_setting('currency','DH')
    shop=get_setting('shop_name','ToDo')
    workstation=get_setting('workstation_code','01')
    lines=[shop,'ADDITION',f'POSTE {workstation}','-'*38]
    subtotal=0
    for line in cart:
        qty,unit,total=_money_line(line);subtotal+=total
        lines.append(str(line.get('name','ARTICLE')))
        lines.append(f'  {qty:g} x {fmt(unit,currency)} = {fmt(total,currency)}')
    discount=max(0,int(ticket_discount_cents or 0))
    total=max(0,subtotal-discount)
    lines+=['-'*38,f'REMISE TICKET: {fmt(discount,currency)}',f'TOTAL: {fmt(total,currency)}','-'*38]
    return '\n'.join(lines)

def build_preparation_slip(cart,station):
    if not cart:raise ValueError('Ticket vide.')
    station=str(station).upper()
    if station not in ('C1','C2','C3','C4'):raise ValueError('Station invalide.')
    shop=get_setting('shop_name','ToDo');workstation=get_setting('workstation_code','01')
    lines=[shop,f'BON PREPARATION {station}',f'POSTE {workstation}','-'*38]
    for line in cart:
        qty=float(line.get('qty',0))
        lines.append(f'{qty:g} x {line.get("name","ARTICLE")}')
    lines+=['-'*38]
    return '\n'.join(lines)

def print_addition(cart,ticket_discount_cents=0,currency=None):
    text=build_addition(cart,ticket_discount_cents,currency)
    return print_text_windows(text,'addition','Addition')

def print_preparation(cart,station):
    station=str(station).upper()
    text=build_preparation_slip(cart,station)
    return print_text_windows(text,station.lower(),f'Preparation {station}')

