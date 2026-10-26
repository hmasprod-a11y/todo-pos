"""Actual Tk category persistence and statistics controls after integration."""
import os,sys,tempfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'todo'))
temp=tempfile.TemporaryDirectory();os.environ['TODO_DB_PATH']=str(Path(temp.name)/'ui.db')
from app import ToDoApp
from screens.onboarding import FirstRunWizard
from database import connect
from screens.products import ProductEditor
from screens.settings import CategoryEditor
from screens.statistics import StatisticsFrame
from services.catalog import get_product_categories
from services.cash import open_session
from services.sales import complete_sale,create_return

def fail(*args,**kwargs):raise AssertionError(str(args))
def descendants(w):
    for child in w.winfo_children():
        yield child;yield from descendants(child)
def button(w,label):
    return next(c for c in descendants(w) if c.winfo_class() in ('Button','TButton') and c.cget('text')==label)
with patch('tkinter.messagebox.showerror',fail):
    app=ToDoApp()
    wizard=next(w for w in app.winfo_children() if isinstance(w,FirstRunWizard))
    wizard.pin.set('9876');wizard.pin_confirm.set('9876');wizard.finish();app.update_idletasks();app.report_callback_exception=lambda t,v,tb:fail(v)
    with patch('tkinter.simpledialog.askstring',side_effect=['9876','9876']):
        app.login_pin.set('9876');app.login();app.geometry('1100x640');app.update()
    with connect() as c:
        ids=[c.execute('INSERT INTO categories(name) VALUES(?)',(f'Family {i:02}',)).lastrowid for i in range(30)]
    editor=ProductEditor(app);editor.name.set('TEST multi family');editor.sell.set('15');editor.buy.set('8')
    editor.cat_vars[ids[0]][0].set(True);editor.cat_vars[ids[-1]][0].set(True)
    with patch('tkinter.simpledialog.askstring',return_value='Added inline'):button(editor,'+ Famille').invoke()
    assert editor.cat_vars[ids[0]][0].get() and editor.cat_vars[ids[-1]][0].get()
    button(editor,'Enregistrer').invoke();app.update()
    with connect() as c:
        pid=c.execute("SELECT id FROM products WHERE name='TEST multi family'").fetchone()[0]
        added=c.execute("SELECT id FROM categories WHERE name='Added inline'").fetchone()[0]
    assert set(get_product_categories(pid))=={ids[0],ids[-1],added}
    editor=ProductEditor(app,pid);app.update()
    assert {cid for cid,(v,_) in editor.cat_vars.items() if v.get()}=={ids[0],ids[-1],added}
    editor.cat_vars[ids[0]][0].set(False)
    with connect() as c:cat=dict(c.execute('SELECT * FROM categories WHERE id=?',(ids[-1],)).fetchone())
    editor.edit_category(cat);app.update()
    category=next(w for w in descendants(editor) if isinstance(w,CategoryEditor))
    category.name_var.set('Cats updated');category._pick('#16A34A');category.icon_var.set('🐟')
    button(category,'Enregistrer').invoke();app.update()
    assert editor.cat_vars[ids[-1]][0].get() and not editor.cat_vars[ids[0]][0].get()
    button(editor,'Enregistrer').invoke();app.update()
    assert set(get_product_categories(pid))=={ids[-1],added}
    app.show('sale');app.update()
    family=button(app.sale_frame,'🐟 Cats updated');assert family.cget('bg')=='#16A34A'
    family.invoke();app.update();assert app.sale_frame.cat.get()=='Cats updated'
    session=open_session(app.user['id'],0)
    sale=complete_sale(session,app.user['id'],[dict(product_id=pid,qty=2,unit_price_cents=1500)],'CASH',2500,discount_cents=500)
    with connect() as c:item=c.execute('SELECT id FROM sale_items WHERE sale_id=?',(sale['id'],)).fetchone()[0]
    create_return(sale['id'],session,app.user['id'],[(item,1)])
    app.show('statistics');app.update();stats=app.current;assert isinstance(stats,StatisticsFrame)
    for key,btn in stats._period_btns.items():
        btn.invoke();app.update()
        assert sum(stats.evo_chart._values)==1250
        assert stats.top_chart._items[0][1]==1250
        assert stats.cat_chart._items[0][1]==1250
        assert stats.cashier_chart._items[0][1]==1250
    with connect() as c:c.execute("UPDATE sales SET created_at='2000-01-01 12:00:00'")
    stats.refresh();app.update();assert sum(stats.evo_chart._values)==-1250
    for _ in range(3):
        app.show('sale');app.update();app.show('statistics');app.update()
    # Shared-barcode popup: keypad quantity, one-click add, fractional quantities,
    # invalid input/cancel, independent product identities and no stock columns.
    from services.catalog import scan_barcode
    from PIL import Image
    photo=Path(temp.name)/'shared.png';Image.new('RGB',(20,20),'blue').save(photo)
    with connect() as c:
        first=c.execute("INSERT INTO products(name,sale_price_cents,stock_qty,image_path,allow_fraction) VALUES('Shared large',1000,40,?,1)",(str(photo),)).lastrowid
        second=c.execute("INSERT INTO products(name,sale_price_cents,stock_qty,allow_fraction) VALUES('Shared small',800,50,1)").lastrowid
        for product in (first,second):c.execute("INSERT INTO product_barcodes(product_id,barcode) VALUES(?,'SHARED-UI')",(product,))
    app.show('sale');app.update();sale=app.sale_frame;sale.clear();sale.scan_quantity.set('1')
    rows=scan_barcode('SHARED-UI')
    popup=sale.pick_barcode(rows);app.update()
    from PIL import ImageGrab
    evidence=Path('qa-evidence');evidence.mkdir(exist_ok=True)
    ImageGrab.grab().save(evidence/'shared-barcode-popup.png')
    button(popup,'3').invoke()
    label=next(w for w in descendants(popup) if w.winfo_class()=='Label' and w.cget('text')=='Shared large')
    label.event_generate('<Button-1>');app.update()
    assert len(sale.cart)==1 and sale.cart[0]['product_id']==first and sale.cart[0]['qty']==3
    popup=sale.pick_barcode(rows);app.update()
    for key in ('1','.','5'):button(popup,key).invoke()
    next(w for w in descendants(popup) if w.winfo_class()=='Label' and w.cget('text')=='Shared small').event_generate('<Button-1>');app.update()
    assert len(sale.cart)==2 and sale.cart[1]['product_id']==second and sale.cart[1]['qty']==1.5
    popup=sale.pick_barcode(rows);app.update();button(popup,'0').invoke()
    with patch('tkinter.messagebox.showerror') as invalid:
        next(w for w in descendants(popup) if w.winfo_class()=='Label' and w.cget('text')=='Shared large').event_generate('<Button-1>');app.update()
        assert invalid.call_count==1 and popup.winfo_exists()
    button(popup,'Annuler').invoke();app.update();assert len(sale.cart)==2 and sale.scan_quantity.get()=='1'
    popup=sale.pick_barcode(rows);app.update();button(popup,'2').invoke()
    next(w for w in descendants(popup) if w.winfo_class()=='Label' and w.cget('text')=='Shared large').event_generate('<Button-1>');app.update()
    assert sale.cart[0]['qty']==5 and len(sale.cart)==2
    # Three explicit stock-entry choices operate on the original ProductEditor.
    for action,label,name,amount in [('variant','Créer une variante liée (stock et prix séparés)','Shared linked',3),('independent','Créer un produit indépendant','Shared independent',2),('stock','Ajouter la quantité au stock existant','Ignored topup name',4)]:
        editor=ProductEditor(app);editor.name.set(name);editor.sell.set('7');editor.bar.set('SHARED-UI');editor.stock.set(str(amount))
        def resolve_conflict():
            conflict=next(w for w in descendants(editor) if w.winfo_class()=='Toplevel')
            selector=next(w for w in descendants(conflict) if w.winfo_class()=='TCombobox')
            selector.set(next(value for value in selector.cget('values') if value.startswith('Shared large ')))
            button(conflict,label).invoke()
        app.after(150,resolve_conflict);button(editor,'Enregistrer').invoke();app.update()
        with connect() as c:
            if action=='stock':
                assert c.execute('SELECT stock_qty FROM products WHERE id=?',(first,)).fetchone()[0]==44
                assert not c.execute('SELECT 1 FROM products WHERE name=?',(name,)).fetchone()
            else:
                created=c.execute('SELECT id,stock_qty FROM products WHERE name=?',(name,)).fetchone();assert created['stock_qty']==amount
                relation=c.execute('SELECT parent_product_id FROM product_variants WHERE product_id=?',(created['id'],)).fetchone()
                assert (relation is not None)==(action=='variant')
    sale.clear();sale.render_products();app.update()
    names={str(w.cget('text')) for w in descendants(sale.card_inner) if w.winfo_class()=='Label'}
    assert 'Shared large' in names and 'Shared small' not in names
    print('GUI SHARED BARCODE PASSED: keypad, click, fractional qty, cancel, repeated scan, photos only')
    app.destroy()
temp.cleanup()
print('PASS: 30 families, inline addition, multi-select save/reopen/remove, colour/icon editor, sale family button, 3 statistics periods, discounts/returns, negative chart, navigation')
