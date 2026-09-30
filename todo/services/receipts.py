from pathlib import Path
import os, tempfile
from database import connect, get_setting
from services.money import fmt
from country_profiles import format_date, get_country_profile


RECEIPT_TEMPLATES={
    'FR_3C': {'lang':'fr','width':42,'layout':'3C'},
    'FR_4C': {'lang':'fr','width':48,'layout':'4C'},
    'FR_2L': {'lang':'fr','width':32,'layout':'2L'},
    'EN_3C': {'lang':'en','width':42,'layout':'3C'},
    'EN_4C': {'lang':'en','width':48,'layout':'4C'},
    'AR_3C': {'lang':'ar','width':42,'layout':'3C'},
    'AR_4C': {'lang':'ar','width':48,'layout':'4C'},
}

def _receipt_profile():
    name=get_setting('receipt_template','').strip().upper()
    if name in RECEIPT_TEMPLATES:
        profile=dict(RECEIPT_TEMPLATES[name]);profile['name']=name;return profile
    try:width=int(get_setting('receipt_chars','42'))
    except (TypeError,ValueError):width=42
    lang=get_setting('language','fr')
    return {'name':'LEGACY','lang':lang,'width':max(32,min(width,64)),'layout':'3C'}

def _receipt_width():
    return _receipt_profile()['width']


def _payment_label(method, lang):
    from services.payment_methods import payment_label
    return payment_label(method,lang)


def build_receipt(sale_id):
    with connect() as conn:
        s=conn.execute("SELECT s.*,u.display_name FROM sales s JOIN users u ON u.id=s.cashier_user_id WHERE s.id=?",(sale_id,)).fetchone()
        items=conn.execute("SELECT * FROM sale_items WHERE sale_id=? ORDER BY id",(sale_id,)).fetchall()
        payments=conn.execute("SELECT payment_method,amount_cents FROM sale_payments WHERE sale_id=? ORDER BY id",(sale_id,)).fetchall()
        taxes=conn.execute("""SELECT tax_rate_basis_points,SUM(tax_net_cents) tax_net_cents,SUM(tax_amount_cents) tax_amount_cents,SUM(tax_gross_cents) tax_gross_cents
                              FROM sale_items WHERE sale_id=? GROUP BY tax_rate_basis_points
                              HAVING SUM(tax_amount_cents)<>0 ORDER BY tax_rate_basis_points""",(sale_id,)).fetchall()
        client=conn.execute('SELECT name FROM clients WHERE id=?',(s['client_id'],)).fetchone() if s and s['client_id'] is not None else None
    if not s: raise ValueError("Vente introuvable")
    profile=_receipt_profile();lang=profile['lang'];ar=lang=='ar'
    tr=lambda fr,arabic,english=None: arabic if ar else (english if lang=='en' and english else fr)
    cur=get_setting("currency","DH");width=profile['width'];rule="="*width;dash="-"*width
    lines=[get_setting("shop_name","ToDo"),rule]
    sale_profile=get_country_profile(s["country_code"] if "country_code" in s.keys() else None)
    lines.append(f"{tr('Date','التاريخ','Date')}: {format_date(s['created_at'], sale_profile)}")
    if get_setting('receipt_show_ticket_no','1')=='1':
        ticket_value=s['client_ticket_no'] if s['client_ticket_no'] is not None else s['sale_no']
        ticket_value=f"{int(ticket_value):06d}" if isinstance(ticket_value,int) else ticket_value
        lines.append(f"{tr('Ticket','التذكرة','Receipt')}: {ticket_value}")
        if s['client_ticket_no'] is not None:
            lines.append(f"{tr('Réf.','المرجع','Ref.')}: {s['sale_no']}")
    if get_setting('receipt_show_sale_mode','1')=='1':
        lines.append(f"{tr('Mode vente','نوع البيع','Sale mode')}: {tr('VENTE','بيع','SALE')}")
    lines.append(f"{tr('Poste','المحطة','Terminal')}: {s['workstation_code']}")
    lines.append(f"{tr('Caissier','الكاشير','Cashier')}: {s['display_name']}")
    if client:lines.append(f"{tr('Client','الزبون','Customer')}: {client['name']}")
    lines.append(dash)
    for i in items:
        if get_setting('receipt_show_barcode','0')=='1' and i['barcode_used']:
            lines.append(f"{tr('Code','الباركود','Barcode')}: {i['barcode_used']}")
        if profile['layout']=='4C':
            lines.append(f"{i['name_snapshot']} | {i['qty']:g} | {fmt(i['unit_price_cents'],cur)} | {fmt(i['net_total_cents'],cur)}")
        elif profile['layout']=='2L':
            lines += [i["name_snapshot"],f"{i['qty']:g} x {fmt(i['unit_price_cents'],cur)} = {fmt(i['net_total_cents'],cur)}"]
        else:
            lines += [i["name_snapshot"],f"  {tr('Qté','الكمية','Qty')} {i['qty']:g} | {tr('Brut','الإجمالي','Gross')} {fmt(i['line_total_cents'],cur)} | {tr('Net','الصافي','Net')} {fmt(i['net_total_cents'],cur)}"]
        if i['pricing_mode']=='PACK':
            lines.append(f"  {i['qty']/i['qty_multiplier']:g} {tr('pack(s)','علبة')} x {fmt(i['unit_price_cents'],cur)} ({i['qty_multiplier']:g} {tr('unités','وحدات')})")
    lines += [
        dash,
        f"{tr('Remise ticket','تخفيض التذكرة','Ticket discount')}: {fmt(s['discount_cents'],cur)}",
    ]
    tax_label=s['tax_label_snapshot'] or tr('Taxe','الضريبة')
    for tax in taxes:
        rate=f"{tax['tax_rate_basis_points']/100:g}%"
        lines.append(f"{tax_label} {rate} | {tr('HT','قبل الضريبة','Net')} {fmt(tax['tax_net_cents'],cur)} | {tr('Taxe','الضريبة','Tax')} {fmt(tax['tax_amount_cents'],cur)} | TTC {fmt(tax['tax_gross_cents'],cur)}")
    if not taxes and s['tax_total_cents']:
        lines.append(f"{tax_label}: {fmt(s['tax_total_cents'],cur)}")
    lines.append(f"{tr('TOTAL','المجموع','TOTAL')}: {fmt(s['total_cents'],cur)}")
    if get_setting('receipt_show_payment','1')=='1':
        lines.append(f"{tr('Paiement','الأداء','Payment')}: {_payment_label(s['payment_method'],lang)}")
    if get_setting('receipt_show_payment','1')=='1' and s['payment_method']=='MIXED':
        for p in payments:lines.append(f"  {_payment_label(p['payment_method'],lang)}: {fmt(p['amount_cents'],cur)}")
    lines += [
        f"{tr('Reçu','المؤدى','Received')}: {fmt(s['paid_cents'],cur)}",
        f"{tr('Monnaie','الباقي','Change')}: {fmt(s['change_cents'],cur)}",
    ]
    if s['payment_method']=='CREDIT':
        lines.append(f"{tr('Dette initiale','الدين الأولي','Opening debt')}: {fmt(s['total_cents']-s['paid_cents'],cur)}")
    lines += [rule,get_setting("receipt_footer",tr("Merci","شكراً","Thank you"))]
    return "\n".join(lines)


def build_escpos_receipt(sale_id, cut=True, open_drawer=False):
    """Return a complete UTF-8 ESC/POS RAW job for a thermal receipt printer."""
    text=build_receipt(sale_id)
    payload=bytearray(b'\x1b@')                         # initialise printer
    payload.extend(b'\x1ba\x01')                     # centre shop header
    first,*rest=text.splitlines()
    payload.extend(b'\x1bE\x01'+first.encode('utf-8')+b'\n\x1bE\x00')
    payload.extend(b'\x1ba\x00')                     # left align body
    if rest:payload.extend(('\n'.join(rest)+'\n').encode('utf-8'))
    payload.extend(b'\n\n')
    if open_drawer:
        pin=get_setting('drawer_pin','0')
        if pin not in ('0','1'):raise ValueError('Connecteur tiroir invalide.')
        payload.extend(bytes((27,112,int(pin),50,250)))
    if cut:payload.extend(b'\x1dV\x00')
    return bytes(payload)


def _send_raw_windows(printer, payload, title):
    if os.name!='nt':raise OSError('Impression thermique RAW disponible sous Windows.')
    import win32print
    handle=win32print.OpenPrinter(printer)
    try:
        job=win32print.StartDocPrinter(handle,1,(title,None,'RAW'))
        try:
            win32print.StartPagePrinter(handle)
            try:
                if win32print.WritePrinter(handle,payload)!=len(payload):
                    raise OSError('Impression thermique incomplète.')
            finally:win32print.EndPagePrinter(handle)
            win32print.EndDocPrinter(handle)
        except Exception:
            win32print.AbortPrinter(handle);raise
    finally:win32print.ClosePrinter(handle)
    return job


def print_receipt_windows(sale_id):
    from services.printers import printer_for
    printer=printer_for('receipt')
    raw=get_setting('thermal_raw','0')=='1'
    if raw:
        if not printer:raise ValueError('Sélectionnez une imprimante de ticket dans les paramètres.')
        return _send_raw_windows(
            printer,
            build_escpos_receipt(sale_id,cut=True,open_drawer=get_setting('drawer_enabled','0')=='1'),
            f"ToDo - Ticket {sale_id}",
        )
    text=build_receipt(sale_id)
    path=Path(tempfile.gettempdir())/f"todo_receipt_{sale_id}.txt"
    path.write_text(text,encoding="utf-8")
    if os.name=="nt":
        if printer:
            from subprocess import list2cmdline
            os.startfile(str(path),'printto',list2cmdline([printer]))
        else:os.startfile(str(path),"print")
    return path


def export_receipt_pdf(sale_id, destination):
    """Create a paginated, printable receipt without sending a printer job."""
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from textwrap import wrap
    path=Path(destination);pdf=canvas.Canvas(str(path),pagesize=A4);pdf.setTitle(f"ToDo ticket {sale_id}")
    y=800;pdf.setFont("Helvetica",10)
    for line in build_receipt(sale_id).splitlines():
        for part in wrap(line,82) or [""]:
            if y<45:pdf.showPage();pdf.setFont("Helvetica",10);y=800
            pdf.drawString(40,y,part);y-=15
    pdf.save();return path
