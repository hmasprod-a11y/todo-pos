import tkinter as tk
import math
import json
import uuid
from tkinter import ttk, messagebox, simpledialog, filedialog
from decimal import Decimal
from database import connect, get_setting
from services.catalog import search_products, scan_barcode, list_categories
from services.pricing import resolve_unit_price, line_total
from services.sales import complete_sale, create_manual_returns, hold_sale, list_held, resume_held
from services.cash import get_open_session
from services.money import fmt, to_cents, allocate
from services.images import abs_image, image_signature
from services.receipts import build_receipt, print_receipt_windows, export_receipt_pdf
from screens.payment import PaymentDialog
try:
    from PIL import Image, ImageTk
except ImportError:
    Image=ImageTk=None


class SaleFrame(ttk.Frame):
    def __init__(self,master,app):
        super().__init__(master,padding=16)
        self.app=app
        self.lang=get_setting('language','fr')
        self.tr=lambda fr,ar,en=None: ar if self.lang=='ar' else (en if self.lang=='en' and en else fr)
        self.seller_id=None
        self.client_id=None
        self.cart=[]
        self.ticket_discount_cents=0
        self.held_id=None
        self.payment='CASH'
        self.price_grid_id=None
        self.price_grid_name=self.tr('Normal','عادي','Normal')
        self.category=None
        self.photo_offset=0
        self.photo_filter=None
        self.currency=get_setting('currency','DH')
        self.images={}
        self.search_job=None
        self.scan_submit_job=None
        self.busy=False
        self.checkout_request=None
        self.return_mode=False
        self.last_sale_snapshot=None
        self.customer_order_id=None
        self.quotation_id=None
        self.bindings=[]
        top=ttk.Frame(self,style='Card.TFrame',padding=(14,10))
        top.pack(fill='x',pady=(0,12))
        title_box=ttk.Frame(top)
        title_box.pack(side='left')
        ttk.Label(title_box,text=self.tr('Vente','البيع','Sale'),style='Title.TLabel').pack(anchor='w')
        ttk.Label(title_box,text=self.tr('Caisse prête pour l’encaissement','الصندوق جاهز للبيع','Ready for checkout'),
                  foreground='#64748B',font=('Segoe UI',9)).pack(anchor='w')
        self.payment_label=tk.Label(top,text=self.tr('Paiement : Espèces','الأداء: نقداً','Payment: Cash'),
                                    bg='#DCFCE7',fg='#166534',font=('Segoe UI',11,'bold'),
                                    padx=14,pady=7,bd=0)
        self.payment_label.pack(side='right')
        self.client_button=ttk.Button(top,text=self.tr('F6 Client : passage','F6 الزبون: عابر','F6 Customer: walk-in'),command=self.choose_client)
        if get_setting('require_client_on_sale','0')=='1':
            self.client_button.pack(side='left',padx=18)
        self.seller_button=ttk.Button(top,text=self.tr('Vendeur : aucun','البائع: لا أحد','Seller: none'),command=self.choose_seller)
        if get_setting('choose_seller_on_sale','0')=='1':
            self.seller_button.pack(side='left',padx=(0,12))
        searchbar=ttk.Frame(self,style='Card.TFrame',padding=(14,12))
        searchbar.pack(fill='x',pady=(0,12))
        ttk.Label(searchbar,text=self.tr('⌕  SCANNER / RECHERCHER','⌕  مسح / بحث','⌕  SCAN / SEARCH'),style='CardTitle.TLabel').pack(side='left',padx=(0,14))
        self.query=tk.StringVar()
        self.entry=ttk.Entry(searchbar,textvariable=self.query,style='Search.TEntry')
        self.entry.pack(side='left',fill='x',expand=True)
        ttk.Label(searchbar,text=self.tr('QTÉ','الكمية','QTY'),style='Card.TLabel',font=('Segoe UI',10,'bold')).pack(side='left',padx=(14,6))
        self.scan_quantity=tk.StringVar(value='1')
        self.quantity_entry=ttk.Entry(searchbar,textvariable=self.scan_quantity,width=6,style='Quantity.TEntry',justify='center')
        self.quantity_entry.pack(side='left')
        self.quantity_entry.bind('<Return>',lambda e:self.focus_search())
        ttk.Button(searchbar,text='×2',style='Soft.TButton',command=self.double_scan_quantity).pack(side='left',padx=(8,0),ipadx=8,ipady=3)
        if get_setting('scale_enabled','0')=='1':
            ttk.Button(searchbar,text=self.tr('⚖ Poids','⚖ الوزن','⚖ Weight'),style='Soft.TButton',command=self.read_scale_weight).pack(side='left',padx=(8,0),ipadx=6,ipady=3)
        self.entry.bind('<Return>',self.confirm_search)
        self.entry.bind('<KeyRelease>',self.handle_scan_input)
        self.entry.bind('<Down>',self.focus_catalog)
        body=ttk.Panedwindow(self,orient='horizontal')
        body.pack(fill='both',expand=True)
        right=ttk.Frame(body,style='Card.TFrame',padding=14);body.add(right,weight=4)
        left=ttk.Frame(body,padding=(12,0,0,0));body.add(left,weight=6)
        filters=ttk.Frame(left);filters.pack(fill='x',pady=(0,8))
        with connect() as conn:
            categories=conn.execute('SELECT id,name FROM categories WHERE active=1 ORDER BY sort_order,name').fetchall()
        self.categories={'Tous':None,**{r['name']:r['id'] for r in categories}}
        self.cat=tk.StringVar(value='Tous')
        self.family_canvas=tk.Canvas(filters,height=48,highlightthickness=0)
        self.family_canvas.pack(fill='x',expand=True)
        family_scroll=ttk.Scrollbar(filters,orient='horizontal',command=self.family_canvas.xview)
        family_scroll.pack(fill='x')
        self.family_canvas.configure(xscrollcommand=family_scroll.set)
        self.category_buttons=ttk.Frame(self.family_canvas)
        self.family_canvas.create_window((0,0),window=self.category_buttons,anchor='nw')
        self.category_buttons.bind('<Configure>',lambda e:self.family_canvas.configure(scrollregion=self.family_canvas.bbox('all')))
        self.catalog_tabs=ttk.Notebook(left)
        self.list_page=ttk.Frame(self.catalog_tabs);self.photo_page=ttk.Frame(self.catalog_tabs)
        self.catalog_tabs.add(self.photo_page,text=self.tr('Photos','اختيار بالصورة','Photos'));self.catalog_tabs.add(self.list_page,text=self.tr('Liste','لائحة','List'))
        self.catalog_tabs.pack(fill='both',expand=True)
        self.products=ttk.Treeview(self.list_page,columns=('price','stock'),show='tree headings',selectmode='browse',style='Catalog.Treeview',height=12)
        self.products.heading('#0',text=self.tr('PRODUIT','المنتوج','PRODUCT'));self.products.column('#0',width=240,minwidth=160)
        for key,label in [('price',self.tr('PRIX','الثمن','PRICE')),('stock',self.tr('STOCK','المخزون','STOCK'))]:
            self.products.heading(key,text=label);self.products.column(key,width=95,stretch=False,anchor='center')
        self.products.pack(fill='both',expand=True)
        photo_nav=ttk.Frame(self.photo_page);photo_nav.pack(side='bottom',fill='x')
        ttk.Button(photo_nav,text=self.tr('Précédent','السابق','Previous'),command=lambda:self.photo_next(-1)).pack(side='left')
        self.photo_more=ttk.Button(photo_nav,text=self.tr('Suivant','التالي','Next'),command=lambda:self.photo_next(1));self.photo_more.pack(side='right')
        self.card_canvas=tk.Canvas(self.photo_page,background='#F6F7FB',highlightthickness=0)
        self.card_scroll=ttk.Scrollbar(self.photo_page,orient='vertical',command=self.card_canvas.yview)
        self.card_inner=ttk.Frame(self.card_canvas)
        self.card_inner.bind('<Configure>',lambda e:self.card_canvas.configure(scrollregion=self.card_canvas.bbox('all')))
        self.card_canvas.create_window((0,0),window=self.card_inner,anchor='nw')
        self.card_canvas.configure(yscrollcommand=self.card_scroll.set)
        self.card_canvas.bind('<Configure>',self.layout_cards)
        self.card_canvas.pack(side='left',fill='both',expand=True);self.card_scroll.pack(side='right',fill='y')
        self.products.bind('<Double-1>',self.add_selected_product)
        self.products.bind('<Return>',self.add_selected_product)
        ttk.Button(left,text=self.tr('＋  Ajouter le produit sélectionné  ↵','＋  إضافة المنتوج المحدد  ↵','＋  Add selected product  ↵'),style='Primary.TButton',command=self.add_selected_product).pack(fill='x',pady=(8,0),ipady=4)
        keypad=ttk.LabelFrame(left,text=self.tr('Pavé numérique','الأرقام','Keypad'),padding=5);keypad.pack(fill='x',pady=(8,0))
        for pos,key in enumerate(['7','8','9','4','5','6','1','2','3','0','.','⌫']):
            ttk.Button(keypad,text=key,style=('Danger.TButton' if key=='⌫' else 'Soft.TButton'),command=lambda k=key:self.keypad_press(k)).grid(row=pos//3,column=pos%3,sticky='nsew',padx=3,pady=3,ipady=8)
        for col in range(3):keypad.columnconfigure(col,weight=1)
        checkout_area=ttk.Frame(right,style='Card.TFrame')
        checkout_area.pack(side='bottom',fill='x')

        self.edit_controls=ttk.Frame(checkout_area,style='Card.TFrame')
        self.edit_controls.pack(fill='x',pady=(2,4))
        actions=ttk.Frame(self.edit_controls,style='Card.TFrame');actions.pack(fill='x')
        for label,command in [('−',lambda:self.change(-1)),('+',lambda:self.change(1)),('×2',self.double_selected),(self.tr('Qté F8','الكمية F8','Qty F8'),self.set_qty),(self.tr('Remise ligne','تخفيض السطر','Line discount'),self.line_discount),(self.tr('Suppr.','حذف','Delete'),self.remove)]:
            button_style='Danger.TButton' if label==self.tr('Suppr.','حذف','Delete') else 'Soft.TButton'
            ttk.Button(actions,text=label,style=button_style,command=command).pack(side='left',expand=True,fill='x',padx=2,ipady=0)
        ttk.Button(self.edit_controls,text=self.tr('☰  Fonctions','☰  الوظائف','☰  Functions'),style='Soft.TButton',
                   command=self.functions).pack(fill='x',pady=(3,0),ipady=0)

        self.subtotal_label=ttk.Label(checkout_area,text='',style='Card.TLabel',
                                     font=('Segoe UI',9,'bold'),foreground='#475569')
        self.subtotal_label.pack(anchor='e',pady=(0,2))

        total_color=getattr(self.app,'theme_color','#2563EB')
        self.total_box=tk.Frame(checkout_area,bg=total_color,padx=12,pady=6)
        self.total_box.pack(fill='x',pady=(2,4))
        tk.Label(self.total_box,text=self.tr('TOTAL NET','المجموع الصافي','NET TOTAL'),bg=total_color,fg='white',
                 font=('Segoe UI',11,'bold')).pack(side='left')
        self.total_label=tk.Label(self.total_box,text='',bg=total_color,fg='white',
                                  font=('Segoe UI',24,'bold'))
        self.total_label.pack(side='right')

        self.last_sale_box=tk.Frame(checkout_area,bg='#1117D9',padx=14,pady=10,bd=1,relief='solid')
        self.last_sale_summary=tk.Label(
            self.last_sale_box,
            text=self.tr('DERNIÈRE VENTE  ·  FACTURE —  ·  PAYÉ —  ·  RENDU —',
                         'آخر بيع  ·  الفاتورة —  ·  المؤدى —  ·  الباقي —','LAST SALE  ·  RECEIPT —  ·  PAID —  ·  CHANGE —'),
            bg='#1117D9',fg='white',font=('Consolas',13,'bold'),anchor='w',
            justify='left'
        )
        self.last_sale_summary.pack(fill='x')

        self.checkout_buttons=ttk.Frame(checkout_area,style='Card.TFrame')
        self.checkout_buttons.pack(fill='x',pady=(2,0))
        self.checkout_main=ttk.Button(self.checkout_buttons,text=self.tr('✓ SOLDER avec ticket F5','✓ الأداء مع التذكرة F5','✓ PAY with receipt F5'),
                                      style='Success.TButton',command=lambda:self.checkout(True))
        self.checkout_main.pack(side='left',expand=True,fill='x',padx=(0,2),ipady=3)
        self.checkout_without_ticket=None
        if get_setting('sans_ticket_enabled','1')=='1':
            self.checkout_without_ticket=ttk.Button(self.checkout_buttons,text=self.tr('SOLDER sans ticket','الأداء بدون تذكرة','PAY without receipt'),
                                                     style='Primary.TButton',command=lambda:self.checkout(False))
            self.checkout_without_ticket.pack(side='left',expand=True,fill='x',padx=(2,0),ipady=3)
        # Return is an immediate cashier action: keep it beside payment, never
        # in a lower toolbar that can be hidden on a compact screen.
        self.return_button=ttk.Button(self.checkout_buttons,text=self.tr('↩ RETOUR  F9','↩ إرجاع  F9','↩ RETURN  F9'),
                                      style='Danger.TButton',command=self.toggle_return_mode)
        self.return_button.pack(side='left',expand=True,fill='x',padx=(2,0),ipady=3)

        ticket_header=ttk.Frame(right,style='Card.TFrame')
        ticket_header.pack(fill='x',pady=(0,8))
        self.ticket_title=ttk.Label(ticket_header,text=self.tr('🧾  Ticket en cours','🧾  التذكرة الحالية','🧾  Current receipt'),style='CardTitle.TLabel')
        self.ticket_title.pack(side='left')
        ttk.Label(ticket_header,text=self.tr('Sélectionnez une ligne pour la modifier','حدد سطراً لتعديله','Select a line to edit it'),style='Card.TLabel',
                  foreground='#64748B',font=('Segoe UI',9)).pack(side='right')
        self.ticket=ttk.Treeview(right,columns=('qty','price','discount','total'),show='tree headings',selectmode='browse',style='Cart.Treeview',height=12)
        self.ticket.heading('#0',text=self.tr('ARTICLE','المنتوج','ITEM'));self.ticket.column('#0',width=190,minwidth=120)
        for key,label,width in [('qty',self.tr('QTÉ','الكمية','QTY'),55),('price',self.tr('P.U.','ثمن الوحدة','UNIT PRICE'),70),('discount',self.tr('REMISE %','التخفيض %','DISCOUNT %'),75),('total',self.tr('NET','الصافي','NET'),85)]:
            self.ticket.heading(key,text=label);self.ticket.column(key,width=width+8,minwidth=48,anchor='center')
        self.ticket.tag_configure('offer',background='#DCFCE7',foreground='#166534')
        self.ticket.tag_configure('even',background='#F8FAFC')
        self.ticket.tag_configure('odd',background='#FFFFFF')
        self.ticket.pack(fill='both',expand=True)
        self.ticket.bind('<Delete>',lambda e:self.remove())
        footer=ttk.Frame(self);footer.pack(fill='x',pady=(12,0))
        footer_actions=[
            (self.tr('F2  ESPÈCES','F2  نقداً','F2  CASH'),lambda:self.set_payment('CASH'),'Success.TButton'),
            (self.tr('F3  CARTE','F3  بطاقة','F3  CARD'),lambda:self.set_payment('CARD'),'Primary.TButton'),
            (self.tr('F4  Attente','F4  انتظار','F4  HOLD'),self.hold,'Soft.TButton'),
            (self.tr('Liste attente','لائحة الانتظار','Held receipts'),self.show_held,'Soft.TButton'),
            (self.tr('F7  Remise','F7  تخفيض','F7  Discount'),self.discount,'Soft.TButton'),
            (self.tr('ESC  Annuler','ESC  إلغاء','ESC  Cancel'),self.cancel,'Danger.TButton'),
        ]
        for label,command,style in footer_actions:
            button=ttk.Button(footer,text=label,style=style,command=command)
            button.pack(side='left',expand=True,fill='x',padx=3,ipady=3)
        self.custom_shortcut_bar=ttk.Frame(self)
        self.custom_shortcut_bar.pack(fill='x',pady=(6,0))
        self.build_custom_shortcuts()
        status_bar=tk.Frame(self,bg='#E2E8F0',padx=10,pady=6)
        status_bar.pack(fill='x',pady=(8,0))
        self.status=tk.Label(status_bar,text=self.tr('● Scanner prêt   ·   Ctrl+F Rechercher   ·   Entrée Ajouter','● الماسح جاهز   ·   Ctrl+F بحث   ·   Enter إضافة','● Scanner ready   ·   Ctrl+F Search   ·   Enter Add'),
                             bg='#E2E8F0',fg='#334155',font=('Segoe UI',9,'bold'))
        self.status.pack(side='left')
        tk.Label(status_bar,text='ToDo POS',bg='#E2E8F0',fg='#64748B',
                 font=('Segoe UI',9)).pack(side='right')
        commands={'<F2>':lambda:self.set_payment('CASH'),'<F3>':lambda:self.set_payment('CARD'),'<F4>':self.hold,'<F5>':lambda:self.checkout(True),'<F7>':self.discount,'<F8>':self.set_qty,'<F9>':self.toggle_return_mode,'<Escape>':self.cancel,'<Control-f>':self.focus_search}
        if get_setting('require_client_on_sale','0')=='1':commands['<F6>']=self.choose_client
        for sequence,command in commands.items():
            binding=app.bind(sequence,lambda e,c=command:self.shortcut(e,c),add='+')
            self.bindings.append((sequence,binding))
        self.render_products();self.refresh();self.after_idle(self.focus_search)


    def read_scale_weight(self):
        try:
            from services.scale import read_weight
            weight=read_weight()
            index=self.selected()
            if index is not None:
                line=self.cart[index]
                allow=line.get('allow_fraction')
                if allow is None:
                    with connect() as conn:
                        row=conn.execute('SELECT allow_fraction FROM products WHERE id=?',(line['product_id'],)).fetchone()
                    allow=bool(row and row['allow_fraction'])
                if not allow:
                    raise ValueError(self.tr('Le produit sélectionné ne se vend pas au poids.','المنتوج المحدد لا يباع بالوزن.','The selected product is not sold by weight.'))
                self.update_quantity(index,weight)
                self.status.config(text=self.tr(f'Poids appliqué : {weight:.3f} kg',f'تم تطبيق الوزن: {weight:.3f} كغ',f'Weight applied: {weight:.3f} kg'))
            else:
                self.scan_quantity.set(f'{weight:.3f}')
                self.quantity_entry.focus_set();self.quantity_entry.selection_range(0,'end')
                self.status.config(text=self.tr(f'Poids lu : {weight:.3f} kg — choisissez/scannez un article.',f'تمت قراءة الوزن: {weight:.3f} كغ — اختر أو امسح منتوجاً.',f'Weight read: {weight:.3f} kg — choose or scan a product.'))
        except Exception as error:
            messagebox.showerror(self.tr('Balance','الميزان','Scale'),str(error),parent=self)
        finally:
            if not self.quantity_entry.focus_get() is self.quantity_entry:self.focus_search()

    def double_scan_quantity(self):
        try:
            value=float(self.scan_quantity.get().replace(',','.'))
            if not math.isfinite(value) or value<=0:raise ValueError()
            self.scan_quantity.set(f"{value*2:g}")
        except ValueError:
            self.scan_quantity.set('2')
        self.quantity_entry.focus_set();self.quantity_entry.selection_range(0,'end')

    def double_selected(self):
        index=self.selected()
        if index is not None:self.update_quantity(index,self.cart[index]['qty']*2)

    def keypad_press(self,key):
        target=self.quantity_entry if self.quantity_entry.focus_get() is self.quantity_entry else self.entry
        if key=='⌫':
            try:
                start=target.index(tk.INSERT)
                if start>0:target.delete(start-1,start)
            except tk.TclError:pass
        else:
            target.insert(tk.INSERT,key)
        target.focus_set()

    def shortcut(self,event,command):
        if self.winfo_viewable() and event.widget.winfo_toplevel()==self.app:
            command();return 'break'

    def _cancel_pending_input_jobs(self):
        for attr in ('search_job','scan_submit_job'):
            job=getattr(self,attr,None)
            if not job:
                continue
            try:self.after_cancel(job)
            except Exception:pass
            setattr(self,attr,None)

    def destroy(self):
        self._cancel_pending_input_jobs()
        for sequence,binding in self.bindings:
            self.app.unbind(sequence,binding)
        super().destroy()

    def focus_search(self):
        if self.entry.winfo_exists():
            self.entry.focus_force()
            self.entry.selection_range(0,'end')

    def focus_catalog(self,event=None):
        self.catalog_tabs.select(self.list_page)
        rows=self.products.get_children()
        if rows:
            self.products.focus_set();self.products.selection_set(rows[0]);self.products.focus(rows[0])
        return 'break'

    def layout_cards(self,event=None):
        columns=max(1,self.card_canvas.winfo_width()//167)
        for index,card in enumerate(self.card_inner.winfo_children()):
            card.grid_configure(row=index//columns,column=index%columns)

    def functions(self):
        window=tk.Toplevel(self);window.title(self.tr('Fonctions','الوظائف','Functions'))
        window.transient(self.winfo_toplevel());window.grab_set()
        window.configure(bg='#F6F7FB')
        window.geometry('820x590')
        window.minsize(720,520)
        header=tk.Frame(window,bg='#0F172A',height=62)
        header.pack(fill='x');header.pack_propagate(False)
        tk.Label(header,text=self.tr('☰  Fonctions de caisse','☰  وظائف الصندوق','☰  Cashier functions'),bg='#0F172A',fg='white',
                 font=('Segoe UI',17,'bold')).pack(side='left',padx=18)
        tk.Button(header,text='✕',bg='#DC2626',fg='white',activebackground='#B91C1C',activeforeground='white',
                  relief='flat',bd=0,font=('Segoe UI',14,'bold'),width=4,cursor='hand2',
                  command=window.destroy).pack(side='right',fill='y')
        body=ttk.Frame(window,padding=16)
        body.pack(fill='both',expand=True)
        def run(command):
            window.destroy();command()
        commands=[(self.tr('Duplicata','نسخة التذكرة','Duplicate'),self.duplicate_receipt),
                  (self.tr('Divers','منتوج أو مبلغ إضافي','Miscellaneous'),self.add_misc),
                  (self.tr('Flash','فلاش','Flash'),self.flash_summary),
                  (self.tr('Modifier quantité','تعديل الكمية','Edit quantity'),self.set_qty),
                  (self.tr('Modifier prix','تعديل الثمن','Edit price'),self.set_price),
                  (self.tr('Remise ticket','تخفيض التذكرة','Receipt discount'),self.discount),
                  (self.tr('Remise ligne','تخفيض السطر','Line discount'),self.line_discount),
                  (self.tr('Supprimer ligne','حذف السطر','Delete line'),self.remove),
                  (self.tr('Grille de prix','لائحة الأثمان','Price grid'),self.choose_price_grid),
                  (self.tr('Compter la caisse','حساب الصندوق','Count cash drawer'),self.cash_tools),
                  (self.tr('Dépenses','المصاريف','Expenses'),lambda:self.cash_tools('expense')),
                  (self.tr('Rapport','التقارير','Reports'),lambda:self.app.show('journal')),
                  (self.tr('Addition','الحساب قبل الأداء','Bill'),self.print_addition),
                  (self.tr('C1 Préparation','C1 تحضير','C1 Preparation'),lambda:self.print_preparation('C1')),
                  (self.tr('C2 Préparation','C2 تحضير','C2 Preparation'),lambda:self.print_preparation('C2')),
                  (self.tr('C3 Préparation','C3 تحضير','C3 Preparation'),lambda:self.print_preparation('C3')),
                  (self.tr('C4 Préparation','C4 تحضير','C4 Preparation'),lambda:self.print_preparation('C4')),
                  (self.tr('Raccourcis','الاختصارات','Shortcuts'),self.show_shortcuts),
                  (self.tr('⌨ Clavier','⌨ لوحة المفاتيح','⌨ Keyboard'),self.toggle_keyboard),
                  (self.tr('Calculatrice','الحاسبة','Calculator'),self.calculator),
                  (self.tr('Verrouiller','قفل الصندوق','Lock cashier'),self.app.lock_cashier),
                  (self.tr('Thème','الألوان','Theme'),self.app.choose_theme),
                  (self.tr('Tiroir','درج النقود','Cash drawer'),self.open_drawer),
                  (self.tr('Attente','انتظار','Hold'),self.hold),
                  (self.tr("Liste d’attente",'المعلقات','Held receipts'),self.show_held)]
        if get_setting('closure_enabled','1')=='1':
            commands.insert(10,(self.tr('Clôture','إغلاق الصندوق','Close cash drawer'),lambda:self.cash_tools('close')))
        danger_labels={self.tr('Supprimer ligne','حذف السطر','Delete line'),self.tr('Clôture','إغلاق الصندوق','Close cash drawer')}
        for index,(label,command) in enumerate(commands):
            style='Danger.TButton' if label in danger_labels else 'Soft.TButton'
            ttk.Button(body,text=label,style=style,command=lambda c=command:run(c)).grid(
                row=index//3,column=index%3,padx=6,pady=6,ipady=8,sticky='nsew')
        for col in range(3):body.columnconfigure(col,weight=1)
        for row in range((len(commands)+2)//3):body.rowconfigure(row,weight=1)
        ttk.Button(window,text=self.tr('Fermer','رجوع','Close'),style='Primary.TButton',
                   command=lambda:run(self.focus_search)).pack(fill='x',padx=16,pady=(0,16),ipady=5)
        window.bind('<Escape>',lambda e:run(self.focus_search))
        window.update_idletasks()
        parent=window.master.winfo_toplevel()
        x=max(0,parent.winfo_rootx()+(parent.winfo_width()-window.winfo_width())//2)
        y=max(0,parent.winfo_rooty()+(parent.winfo_height()-window.winfo_height())//2)
        window.geometry(f'+{x}+{y}')

    def choose_price_grid(self):
        with connect() as conn:
            grids=conn.execute("SELECT id,name FROM price_grids WHERE active=1 ORDER BY name COLLATE NOCASE").fetchall()
        choices=[(None,self.tr('Normal','عادي','Normal'))]+[(r['id'],r['name']) for r in grids]
        w=tk.Toplevel(self);w.title(self.tr('Grille de prix','لائحة الأثمان','Price grid'));w.transient(self.winfo_toplevel());w.grab_set()
        ttk.Label(w,text=self.tr('Choisir la grille appliquée à cette vente','اختر لائحة الأثمان المطبقة على هذا البيع','Choose the price grid for this sale'),style='Subtitle.TLabel').pack(padx=20,pady=(18,10))
        def select(grid_id,name):
            self.price_grid_id=grid_id;self.price_grid_name=name
            with connect() as conn:
                for line in self.cart:
                    if line.get('is_misc') or line.get('manual_unit_price'):continue
                    line['unit_price_cents']=str(resolve_unit_price(line['product_id'],line['qty'],line.get('barcode_id'),conn,grid_id))
            w.destroy();self.refresh();self.status.config(text=self.tr(f'Grille active : {name}',f'لائحة الأثمان الحالية: {name}',f'Active price grid: {name}'));self.focus_search()
        for grid_id,name in choices:
            ttk.Button(w,text=('✓ ' if grid_id==self.price_grid_id else '')+name,command=lambda g=grid_id,n=name:select(g,n)).pack(fill='x',padx=20,pady=4,ipady=6)
        def cancel():
            self.query.set('');self.scan_quantity.set('1');w.destroy();self.focus_search()
        w.bind('<Escape>',lambda e:cancel())

    def restore_price(self):
        index=self.selected()
        if index is None:return
        line=self.cart[index]
        if line.get('is_misc'):return
        with connect() as conn:
            product=conn.execute('SELECT sale_price_cents FROM products WHERE id=?',(line['product_id'],)).fetchone()
        line['unit_price_cents']=str(product['sale_price_cents'])
        line['manual_unit_price']=True
        line['discount_cents']=min(line.get('discount_cents',0),line_total(line['unit_price_cents'],line['qty']))
        self.ticket_discount_cents=min(self.ticket_discount_cents,self.totals()[0])
        self.refresh(index);self.focus_search()

    def toggle_keyboard(self):
        self.app.toggle_keyboard(self.entry)

    def calculator(self):
        from screens.cashier_tools import Calculator
        Calculator(self)

    def open_drawer(self):
        from services.printers import open_drawer
        try:
            open_drawer();self.status.config(text=self.tr('Commande envoyée au tiroir.','تم إرسال أمر فتح الدرج.','Cash-drawer command sent.'))
        except Exception as error:messagebox.showerror(self.tr('Tiroir','درج النقود','Cash drawer'),str(error),parent=self)

    def add_misc(self):
        from services.misc import misc_line
        window=tk.Toplevel(self)
        window.title(self.tr('Divers','منتوج إضافي','Miscellaneous item'))
        window.transient(self.winfo_toplevel())
        window.grab_set()
        window.geometry('560x360')
        window.resizable(False,False)

        root=ttk.Frame(window,padding=14);root.pack(fill='both',expand=True)
        form=ttk.Frame(root);form.pack(side='left',fill='both',expand=True,padx=(0,12))
        keypad=ttk.Frame(root);keypad.pack(side='right',fill='y')

        name_var=tk.StringVar()
        price_var=tk.StringVar()
        qty_var=tk.StringVar(value='1')

        ttk.Label(form,text=self.tr(f'Prix ({self.currency})',f'الثمن ({self.currency})',f'Price ({self.currency})'),font=('Segoe UI',11,'bold')).pack(anchor='w')
        price_entry=ttk.Entry(form,textvariable=price_var,font=('Segoe UI',22,'bold'),justify='right',style='Search.TEntry')
        price_entry.pack(fill='x',pady=(4,12),ipady=5)

        ttk.Label(form,text=self.tr('Nom (facultatif)','الاسم (اختياري)','Name (optional)')).pack(anchor='w')
        name_entry=ttk.Entry(form,textvariable=name_var)
        name_entry.pack(fill='x',pady=(4,12),ipady=3)

        ttk.Label(form,text=self.tr('Quantité','الكمية','Quantity')).pack(anchor='w')
        qty_entry=ttk.Entry(form,textvariable=qty_var,font=('Segoe UI',16,'bold'),justify='right')
        qty_entry.pack(fill='x',pady=(4,14),ipady=3)

        target={'entry':price_entry}
        for entry in (price_entry,qty_entry):
            entry.bind('<FocusIn>',lambda e,w=entry:target.__setitem__('entry',w))

        def keypress(key):
            entry=target['entry']
            if key=='⌫':
                try:
                    pos=entry.index(tk.INSERT)
                    if pos>0:entry.delete(pos-1,pos)
                except tk.TclError:pass
            elif key=='C':
                entry.delete(0,tk.END)
            else:
                entry.insert(tk.INSERT,key)
            entry.focus_set()

        for index,key in enumerate(['7','8','9','4','5','6','1','2','3','0','.','⌫']):
            ttk.Button(keypad,text=key,style=('Danger.TButton' if key=='⌫' else 'Soft.TButton'),
                       command=lambda k=key:keypress(k)).grid(row=index//3,column=index%3,sticky='nsew',padx=2,pady=2,ipadx=8,ipady=8)
        ttk.Button(keypad,text='C',style='Danger.TButton',command=lambda:keypress('C')).grid(
            row=4,column=0,columnspan=3,sticky='nsew',padx=2,pady=(4,2),ipady=6)
        for col in range(3):keypad.columnconfigure(col,weight=1)

        buttons=ttk.Frame(form);buttons.pack(fill='x',side='bottom')
        def close():
            window.destroy();self.focus_search()
        def save():
            try:
                label=name_var.get().strip() or self.tr('Divers','متنوع','Miscellaneous')
                line=misc_line(label,price_var.get(),qty_var.get())
                self.cart.append(line);self.refresh(len(self.cart)-1)
                window.destroy();self.focus_search()
            except (ValueError,ArithmeticError) as error:
                messagebox.showerror(self.tr('Divers','منتوج إضافي','Miscellaneous item'),str(error),parent=window)
                price_entry.focus_set();price_entry.selection_range(0,'end')
        ttk.Button(buttons,text=self.tr('✓ Valider','✓ تأكيد','✓ Confirm'),style='Success.TButton',command=save).pack(side='left',expand=True,fill='x',padx=(0,4),ipady=8)
        ttk.Button(buttons,text=self.tr('Annuler','إلغاء','Cancel'),style='Soft.TButton',command=close).pack(side='left',expand=True,fill='x',padx=(4,0),ipady=8)

        window.bind('<Return>',lambda e:save())
        window.bind('<Escape>',lambda e:close())
        window.protocol('WM_DELETE_WINDOW',close)
        window.after_idle(lambda:(price_entry.focus_force(),price_entry.selection_range(0,'end')))
        # Test hooks and touch workflow state.
        window.misc_name_var=name_var;window.misc_price_var=price_var;window.misc_qty_var=qty_var
        window.misc_confirm=buttons.winfo_children()[0]

    def flash_summary(self):
        session=get_open_session()
        if not session:
            messagebox.showinfo('ToDo',self.tr('Aucune caisse ouverte.','لا يوجد صندوق مفتوح.','No open cash drawer.'),parent=self);return
        with connect() as conn:
            rows=conn.execute("""SELECT sp.payment_method,COALESCE(SUM(sp.amount_cents),0) amount
                FROM sale_payments sp JOIN sales s ON s.id=sp.sale_id
                WHERE s.session_id=? AND s.status='COMPLETED'
                GROUP BY sp.payment_method""",(session['id'],)).fetchall()
        totals={r['payment_method']:int(r['amount']) for r in rows}
        # sale_payments stores mixed sales as their real CASH/CARD components.
        # CREDIT is debt, not cash received, so Flash must not count it as espèces.
        cash=totals.get('CASH',0)
        card=totals.get('CARD',0)
        lines=[self.tr('VENTES DE LA CAISSE','مبيعات الصندوق','CASH DRAWER SALES'),
               self.tr('ESPÈCES : ','نقداً: ','CASH: ')+fmt(cash,self.currency),
               self.tr('CARTE : ','بطاقة: ','CARD: ')+fmt(card,self.currency)]
        messagebox.showinfo('FLASH','\n'.join(lines),parent=self)
        self.focus_search()

    def cash_tools(self,action=None):
        from screens.cashdesk import CashFrame
        window=tk.Toplevel(self);window.title(self.tr('Caisse','الصندوق','Cash drawer'))
        window.transient(self.app)
        # Direct closure must not create a modal-on-modal grab chain on Windows.
        # The denomination counter opened by CashFrame.close() is the only modal.
        if action!='close':
            window.grab_set()
        frame=CashFrame(window,self.app);frame.pack(fill='both',expand=True)
        ttk.Button(window,text=self.tr('Retour à la vente','العودة للبيع','Back to sale'),command=window.destroy).pack(pady=8)
        window.bind('<Escape>',lambda e:window.destroy())
        if action=='close':
            def after_closed():
                if window.winfo_exists():
                    window.destroy()
                self.focus_search()
            window.after_idle(lambda:frame.close(on_closed=after_closed))
        elif action=='expense':
            window.after_idle(frame.expense)


    def print_addition(self):
        if not self.cart:
            messagebox.showinfo('ToDo',self.tr('Ticket vide.','التذكرة فارغة.','Empty receipt.'),parent=self);return
        try:
            from services.order_slips import print_addition
            print_addition(self.cart,self.ticket_discount_cents,self.currency)
            self.status.config(text=self.tr('Addition envoyée à l’imprimante.','تم إرسال الحساب إلى الطابعة.','Bill sent to the printer.'))
        except Exception as error:
            messagebox.showerror(self.tr('Addition','الحساب','Bill'),str(error),parent=self)
        finally:self.focus_search()

    def print_preparation(self,station):
        if not self.cart:
            messagebox.showinfo('ToDo',self.tr('Ticket vide.','التذكرة فارغة.','Empty receipt.'),parent=self);return
        try:
            from services.order_slips import print_preparation
            print_preparation(self.cart,station)
            self.status.config(text=self.tr(f'Bon {station} envoyé.',f'تم إرسال ورقة {station}.',f'Preparation slip {station} sent.'))
        except Exception as error:
            messagebox.showerror(station,str(error),parent=self)
        finally:self.focus_search()

    def build_custom_shortcuts(self):
        from services.shortcuts import get_shortcuts
        for child in self.custom_shortcut_bar.winfo_children():child.destroy()
        actions={
            'calculator':(self.tr('Calculatrice','الحاسبة','Calculator'),self.calculator),
            'held':(self.tr("Liste d’attente",'المعلقات','Held receipts'),self.show_held),
            'drawer':(self.tr('Tiroir','درج النقود','Cash drawer'),self.open_drawer),
            'duplicate':(self.tr('Duplicata','نسخة التذكرة','Duplicate'),self.duplicate_receipt),
            'price_grid':(self.tr('Grille de prix','لائحة الأثمان','Price grid'),self.choose_price_grid),
            'expense':(self.tr('Dépenses','المصاريف','Expenses'),lambda:self.cash_tools('expense')),
            'report':(self.tr('Rapport','التقارير','Reports'),lambda:self.app.show('journal')),
            'closure':(self.tr('Clôture','إغلاق الصندوق','Close cash drawer'),lambda:self.cash_tools('close')),
            'keyboard':(self.tr('⌨ Clavier','⌨ لوحة المفاتيح','⌨ Keyboard'),self.toggle_keyboard),
        }
        for key in get_shortcuts():
            if key=='closure' and get_setting('closure_enabled','1')!='1':continue
            label,command=actions[key]
            ttk.Button(self.custom_shortcut_bar,text=label,style='Soft.TButton',command=command).pack(side='left',expand=True,fill='x',padx=2)

    def show_shortcuts(self):
        messagebox.showinfo(self.tr('Raccourcis','الاختصارات','Shortcuts'),
            self.tr('F2 : Espèces\\nF3 : Carte\\nF4 : Attente\\nF5 : Solder\\nF7 : Remise\\nF8 : Quantité\\nCtrl+F : Recherche\\nEntrée : Ajouter / Confirmer\\nSuppr : Supprimer ligne\\nÉchap : Annuler','F2 : نقداً\\nF3 : بطاقة\\nF4 : انتظار\\nF5 : إتمام البيع\\nF7 : تخفيض\\nF8 : الكمية\\nCtrl+F : بحث\\nEnter : إضافة / تأكيد\\nDelete : حذف السطر\\nEsc : إلغاء','F2: Cash\\nF3: Card\\nF4: Hold\\nF5: Pay\\nF7: Discount\\nF8: Quantity\\nCtrl+F: Search\\nEnter: Add / Confirm\\nDelete: Delete line\\nEsc: Cancel'),parent=self)

    def duplicate_receipt(self):
        with connect() as conn:
            rows=conn.execute('SELECT id,sale_no,total_cents,created_at FROM sales ORDER BY id DESC LIMIT 100').fetchall()
        window=tk.Toplevel(self);window.title(self.tr('Duplicata — choisir un ticket','نسخة التذكرة — اختر تذكرة','Duplicate — choose a receipt'))
        window.transient(self.winfo_toplevel());window.grab_set()
        tree=ttk.Treeview(window,columns=('number','date','total'),show='headings',height=12)
        for key,label in [('number',self.tr('Ticket','التذكرة','Receipt')),('date',self.tr('Date','التاريخ','Date')),('total',self.tr('Total','المجموع','Total'))]:tree.heading(key,text=label)
        tree.pack(fill='both',expand=True,padx=12,pady=12)
        for row in rows:tree.insert('','end',iid=str(row['id']),values=(row['sale_no'],row['created_at'],fmt(row['total_cents'],self.currency)))
        def choose(event=None):
            if not tree.selection():return
            sid=int(tree.selection()[0]);row=next(r for r in rows if r['id']==sid)
            window.destroy();self.show_receipt(row)
        ttk.Button(window,text=self.tr('Voir / Imprimer','عرض / طباعة','View / Print'),command=choose).pack(pady=10)
        tree.bind('<Return>',choose);tree.bind('<Double-1>',choose)
        window.bind('<Escape>',lambda e:window.destroy())
        if rows:tree.selection_set(str(rows[0]['id']));tree.focus_set()

    def handle_scan_input(self,event=None):
        if event and event.keysym in ('Return','Down','Up','Escape'):
            return
        self.schedule_search(event)
        if self.scan_submit_job:
            try:self.after_cancel(self.scan_submit_job)
            except Exception:pass
            self.scan_submit_job=None
        code=self.query.get().strip()
        if len(code)<4 or any(ch.isspace() for ch in code):
            return
        # Auto-submit only exact known barcodes. Normal text searches stay manual.
        self.scan_submit_job=self.after(500,self.auto_submit_barcode)

    def auto_submit_barcode(self):
        self.scan_submit_job=None
        code=self.query.get().strip()
        if not code:return
        rows=scan_barcode(code)
        if not rows:return
        self.confirm_search()

    def schedule_search(self,event=None):
        if event and event.keysym in ('Return','Down','Up','Escape'):return
        if self.search_job:self.after_cancel(self.search_job)
        self.search_job=self.after(120,self.render_products)

    def thumbnail(self,row,size=40):
        key=(row['id'],image_signature(row['image_path']),size)
        if key not in self.images and Image:
            path=abs_image(row['image_path']) if row['image_path'] else None
            if path:
                try:
                    with Image.open(path) as source:
                        im=source.copy();im.thumbnail((size,size))
                    self.images[key]=ImageTk.PhotoImage(im,master=self)
                except (OSError,ValueError):pass
        return self.images.get(key,'')

    def photo_next(self,direction):
        self.photo_offset=max(0,self.photo_offset+direction*60);self.render_products()
        self.card_canvas.yview_moveto(0)

    def render_products(self):
        self.search_job=None
        with connect() as conn:
            categories=conn.execute('SELECT id,name FROM categories WHERE active=1 ORDER BY sort_order,name').fetchall()
        self.categories={'Tous':None,**{r['name']:r['id'] for r in categories}}
        if self.cat.get() not in self.categories:self.cat.set('Tous')
        for child in self.category_buttons.winfo_children(): child.destroy()
        category_rows=list_categories()
        # Default colours for "Tous" and fallback
        all_colors = {'Tous': ('#1e293b', '#ffffff')}
        for cat_row in category_rows:
            bg = cat_row['color'] or '#2563EB'
            # compute a readable text colour (white or black) based on luminance
            try:
                r2,g2,b2 = int(bg[1:3],16), int(bg[3:5],16), int(bg[5:7],16)
                lum = (0.299*r2 + 0.587*g2 + 0.114*b2)
                fg = '#ffffff' if lum < 140 else '#1e293b'
            except Exception:
                fg = '#ffffff'
            all_colors[cat_row['name']] = (bg, fg)
        active = self.cat.get()
        for name, (bg, fg) in all_colors.items():
            if name not in self.categories:
                continue
            icon = ''
            for cat_row in category_rows:
                if cat_row['name'] == name:
                    icon = (cat_row['icon'] + ' ') if cat_row['icon'] else ''
                    break
            label = icon + name
            is_active = (name == active)
            border  = '#f59e0b' if is_active else bg
            relief  = 'solid'   if is_active else 'flat'
            btn = tk.Button(
                self.category_buttons,
                text=label,
                bg=bg, fg=fg,
                activebackground=bg, activeforeground=fg,
                relief=relief, bd=2 if is_active else 0,
                highlightbackground=border,
                font=('Segoe UI', 9, 'bold' if is_active else 'normal'),
                padx=10, pady=6, cursor='hand2',
                command=lambda n=name: self.choose_category(n)
            )
            btn.pack(side='left', padx=3, pady=2)
        rows=search_products(self.query.get(),self.categories[self.cat.get()])
        self.products.delete(*self.products.get_children())
        for child in self.card_inner.winfo_children():child.destroy()
        self.product_rows={str(r['id']):r for r in rows}
        photo_filter=(self.query.get(),self.categories[self.cat.get()])
        if photo_filter!=self.photo_filter:self.photo_offset=0;self.photo_filter=photo_filter
        # The tactile grid intentionally contains only products with an image.
        # In this shop workflow, images are assigned only to barcode-problem exceptions.
        photo_rows=search_products(*photo_filter,limit=61,images_only=True,offset=self.photo_offset)
        self.photo_more.configure(state='normal' if len(photo_rows)>60 else 'disabled')
        photo_rows=photo_rows[:60]
        visible_rows={r['id']:r for r in [*rows,*photo_rows]}
        with connect() as conn:
            display_prices={pid:resolve_unit_price(pid,1,None,conn,self.price_grid_id) for pid in visible_rows}
        columns=max(1,self.card_canvas.winfo_width()//167)
        for row in rows:
            self.products.insert('', 'end',iid=str(row['id']),text=row['name'],image=self.thumbnail(row),values=(fmt(display_prices[row['id']],''),f"{row['stock_qty']:g}"))
        for index,row in enumerate(photo_rows):
            thumb=self.thumbnail(row,90)
            if not thumb:continue
            card=tk.Frame(self.card_inner,bg='white',bd=1,relief='solid',highlightthickness=1,highlightbackground='#E2E8F0',width=155,height=168,cursor='hand2')
            card.grid(row=index//columns,column=index%columns,padx=6,pady=6);card.grid_propagate(False)
            picture=tk.Label(card,image=thumb or '',text='' if thumb else '📦',bg='white',font=('Segoe UI',26));picture.pack(fill='both',expand=True)
            tk.Label(card,text=row['name'],bg='white',fg='#0F172A',font=('Segoe UI',9,'bold'),wraplength=140,pady=2).pack()
            tk.Label(card,text=fmt(display_prices.get(row['id'],row['sale_price_cents']),self.currency),bg='#2563EB',fg='white',font=('Segoe UI',11,'bold'),pady=3).pack(fill='x')
            for widget in [card,*card.winfo_children()]:
                widget.bind('<Button-1>',lambda e,pid=row['id']:self.add_product(pid))

    def choose_category(self,name):
        self.cat.set(name)
        self.render_products()

    def _begin_new_sale(self):
        if self.cart or self.last_sale_snapshot is None:
            return
        self.last_sale_snapshot=None
        self.last_sale_discount_cents=0
        self.last_sale_summary.config(
            text=self.tr('DERNIÈRE VENTE  ·  FACTURE —  ·  PAYÉ —  ·  RENDU —',
                         'آخر بيع  ·  الفاتورة —  ·  المؤدى —  ·  الباقي —',
                         'LAST SALE  ·  RECEIPT —  ·  PAID —  ·  CHANGE —')
        )
        self.refresh()

    def confirm_search(self,event=None):
        self._cancel_pending_input_jobs()
        code=self.query.get().strip()
        if not code:return 'break'
        scanner_like=len(code)>=4 and not any(ch.isspace() for ch in code)
        if scanner_like:
            self._begin_new_sale()
        from services.rfid import lookup_tag
        tag=lookup_tag(code) if get_setting('rfid_enabled','0')=='1' else None
        if tag and tag['target_type']=='PRODUCT':
            self._begin_new_sale();self.add_product(tag['target_id']);self.query.set('');return 'break'
        if tag and tag['target_type']=='CLIENT':
            from services.clients import get_client
            client=get_client(tag['target_id'])
            if client and client.get('active',1):
                self.client_id=tag['target_id'];self.update_client_label();self.query.set('');self.status.config(text=self.tr(f"Client RFID : {client['name']}",f"زبون RFID: {client['name']}",f"RFID customer: {client['name']}"));self.focus_search();return 'break'
        rows=scan_barcode(code)
        if len(rows)==1:
            r=rows[0];self.add_product(r['id'],r['barcode_id'],r['qty_multiplier'],r['barcode'])
        elif len(rows)>1:self.pick_barcode(rows)
        else:
            # Barcode-like scanner input must never silently become a name search.
            if scanner_like:
                self.unknown_product(code)
            else:
                rows=search_products(code,limit=2)
                if len(rows)==1:self.add_product(rows[0]['id'])
                else:
                    self.render_products();self.focus_catalog()
                    self.status.config(text=self.tr('Choisissez un produit puis Entrée.','اختر منتوجاً ثم اضغط Enter.','Choose a product, then press Enter.') if rows else self.tr('Aucun produit trouvé.','لم يتم العثور على أي منتوج.','No product found.'))
        return 'break'

    def unknown_product(self,code):
        from services.security import require_admin
        from screens.products import ProductEditor
        window=tk.Toplevel(self)
        window.title(self.tr('Produit inconnu','منتوج غير معروف','Unknown product'))
        window.configure(bg='#DC2626');window.geometry('640x340')
        window.transient(self.winfo_toplevel());window.grab_set()
        self.bell()
        tk.Label(window,text=self.tr('!  Produit inconnu','!  منتوج غير معروف','!  Unknown product'),bg='#DC2626',fg='white',font=('Segoe UI',30,'bold')).pack(pady=(28,8))
        tk.Label(window,text=self.tr('Produit inconnu','منتوج غير معروف','Unknown product'),bg='#DC2626',fg='white',font=('Segoe UI',18)).pack()
        tk.Label(window,text=code,bg='#DC2626',fg='white',font=('Segoe UI',20),wraplength=580).pack(pady=18)
        def close():
            window.destroy();self.query.set('');self.render_products();self.after_idle(self.focus_search)
        def create():
            try:
                with connect() as conn:require_admin(conn)
            except PermissionError as error:
                messagebox.showerror('ToDo',str(error),parent=window);return
            window.destroy()
            editor=ProductEditor(self,on_saved=self.render_products)
            editor.bar.set(code)
            self.wait_window(editor)
            self.query.set('');self.render_products();self.focus_search()
        buttons=tk.Frame(window,bg='#DC2626');buttons.pack(pady=12)
        ttk.Button(buttons,text=self.tr('Ajouter le produit','إضافة المنتوج','Add product'),command=create).pack(side='left',padx=8,ipady=10)
        back=ttk.Button(buttons,text=self.tr('Retour à la vente','رجوع للبيع','Back to sale'),command=close)
        back.pack(side='left',padx=8,ipady=10);back.focus_set()
        window.protocol('WM_DELETE_WINDOW',close)
        window.bind('<Escape>',lambda e:close())
        window.bind('<Return>',lambda e:close())

    def pick_barcode(self,rows):
        w=tk.Toplevel(self);w.title(self.tr('Même code-barres','نفس الباركود','Same barcode'));w.geometry('980x620');w.transient(self);w.grab_set()
        quantity=tk.StringVar(w,value=self.scan_quantity.get())
        ttk.Label(w,text=self.tr('Cliquez sur le produit à ajouter','اضغط على المنتوج لإضافته','Click the product to add'),font=('Segoe UI',16,'bold')).pack(anchor='w',padx=16,pady=14)
        body=ttk.Frame(w);body.pack(fill='both',expand=True,padx=16,pady=(0,16))
        keypad=ttk.Frame(body);keypad.pack(side='right',fill='y',padx=(14,0))
        ttk.Label(keypad,text=self.tr('Quantité ×','الكمية ×','Quantity ×'),font=('Segoe UI',14,'bold')).pack()
        entry=ttk.Entry(keypad,textvariable=quantity,width=10,font=('Segoe UI',22),justify='right');entry.pack(pady=8)
        keys=ttk.Frame(keypad);keys.pack()
        fresh=[True]
        def press(key):
            old=quantity.get()
            if fresh[0] and key not in ('⌫','C'):old=''
            fresh[0]=False
            quantity.set(old[:-1] if key=='⌫' else ('' if key=='C' else old+key))
        entry.bind('<KeyPress>',lambda e:fresh.__setitem__(0,False))
        for i,key in enumerate(('7','8','9','4','5','6','1','2','3','C','0','.','⌫')):
            ttk.Button(keys,text=key,width=4,command=lambda k=key:press(k)).grid(row=i//3,column=i%3,padx=2,pady=3,ipady=10)
        def close():w.destroy();self.focus_search()
        ttk.Button(keypad,text=self.tr('Annuler','إلغاء','Cancel'),command=close).pack(fill='x',pady=14)
        canvas=tk.Canvas(body,highlightthickness=0);scroll=ttk.Scrollbar(body,orient='vertical',command=canvas.yview);inner=ttk.Frame(canvas)
        inner.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')));canvas.create_window((0,0),window=inner,anchor='nw');canvas.configure(yscrollcommand=scroll.set);scroll.pack(side='right',fill='y');canvas.pack(side='left',fill='both',expand=True)
        def choose(r):
            try:
                count=float(quantity.get().replace(',','.'))
                if not math.isfinite(count) or count<=0:raise ValueError()
                with connect() as conn:
                    p=conn.execute('SELECT allow_fraction FROM products WHERE id=? AND active=1',(r['id'],)).fetchone()
                    if not p or (not p['allow_fraction'] and not (count*r['qty_multiplier']).is_integer()):raise ValueError()
                    resolve_unit_price(r['id'],count*r['qty_multiplier'],r['barcode_id'],conn,self.price_grid_id)
            except (ValueError,OverflowError):
                messagebox.showerror('ToDo',self.tr('Quantité invalide','الكمية غير صالحة','Invalid quantity'),parent=w);return
            self.scan_quantity.set(quantity.get());w.destroy();self.add_product(r['id'],r['barcode_id'],r['qty_multiplier'],r['barcode'])
        with connect() as conn:
            details=[(r,conn.execute('SELECT image_path FROM products WHERE id=?',(r['id'],)).fetchone(),resolve_unit_price(r['id'],r['qty_multiplier'],r['barcode_id'],conn,self.price_grid_id)) for r in rows]
        for i,(r,p,price) in enumerate(details):
            card=tk.Frame(inner,bg='white',bd=1,relief='solid',cursor='hand2');card.grid(row=i//3,column=i%3,padx=7,pady=7,sticky='nsew')
            thumb=self.thumbnail({'id':r['id'],'image_path':p['image_path']},100);tk.Label(card,image=thumb or '',text='' if thumb else '📦',bg='white',font=('Segoe UI',30)).pack(fill='both',expand=True,padx=6,pady=6)
            tk.Label(card,text=r['name'],bg='white',font=('Segoe UI',11,'bold'),wraplength=180).pack(fill='x',padx=6)
            tk.Label(card,text=fmt(line_total(price,r['qty_multiplier']),self.currency),bg='#2563EB',fg='white',font=('Segoe UI',15,'bold'),pady=6).pack(fill='x',pady=(6,0))
            for widget in [card,*card.winfo_children()]:widget.bind('<Button-1>',lambda e,x=r:choose(x))
        for col in range(3):inner.columnconfigure(col,weight=1)
        w.protocol('WM_DELETE_WINDOW',close);w.bind('<Escape>',lambda e:close())
        return w

    def add_selected_product(self,event=None):
        if self.products.selection():self.add_product(int(self.products.selection()[0]))
        return 'break'

    def add_product(self,pid,barcode_id=None,qty=1,barcode=''):
        try:
            self._begin_new_sale()
            qty=float(qty)*float(self.scan_quantity.get().replace(',','.'))
            if not math.isfinite(float(qty)) or float(qty)<=0:
                raise ValueError(self.tr('Quantité invalide','الكمية غير صالحة','Invalid quantity'))
            with connect() as conn:
                p=conn.execute('SELECT * FROM products WHERE id=? AND active=1',(pid,)).fetchone()
                if not p:raise ValueError(self.tr('Article introuvable','المنتوج غير موجود','Product not found'))
                if not p['allow_fraction'] and not float(qty).is_integer():raise ValueError(self.tr('Quantité entière requise','الكمية يجب أن تكون عدداً صحيحاً','A whole quantity is required'))
                index=next((i for i,x in enumerate(self.cart) if x['product_id']==pid and x.get('barcode_id')==barcode_id),None)
                new_qty=float(qty)+(self.cart[index]['qty'] if index is not None else 0)
                unit=resolve_unit_price(pid,new_qty,barcode_id,conn,self.price_grid_id)
                if index is not None and self.cart[index].get('manual_unit_price'):
                    unit=Decimal(self.cart[index]['unit_price_cents'])
                barcode_row=conn.execute('SELECT qty_multiplier,price_override_cents FROM product_barcodes WHERE id=?',(barcode_id,)).fetchone() if barcode_id else None
                # A carton/pack barcode must keep its physical quantity step even when it has no special pack price.
                step=barcode_row['qty_multiplier'] if barcode_row else 1
                if index is None:
                    self.cart.append(dict(product_id=pid,name=p['name'],qty=new_qty,barcode_id=barcode_id,barcode=barcode,unit_price_cents=str(unit),qty_multiplier=step,base_price_cents=p['sale_price_cents'],image_path=p['image_path'],allow_fraction=p['allow_fraction'],discount_cents=0))
                    index=len(self.cart)-1
                else:self.cart[index].update(qty=new_qty,unit_price_cents=str(unit))
            self.query.set('');self.scan_quantity.set('1');self.refresh(index);self.focus_search()
            self.status.config(text=self.tr('Ajouté : ','تمت الإضافة: ','Added: ')+p['name'])
        except Exception as e:messagebox.showerror('ToDo',str(e),parent=self)

    def selected(self):
        selected=self.ticket.selection()
        return int(selected[0]) if selected else (len(self.cart)-1 if self.cart else None)

    def totals(self):
        sub=sum(line_total(x['unit_price_cents'],x['qty'])-int(x.get('discount_cents',0)) for x in self.cart)
        return sub,max(0,sub-self.ticket_discount_cents)

    def refresh(self,index=None):
        if index is None:index=self.selected()
        self.ticket.delete(*self.ticket.get_children())
        sub,total=self.totals()
        sign=-1 if self.return_mode else 1
        # The active ticket is always the current sale. A completed sale is shown
        # only in the separate reminder block, Logica-style, while the new ticket
        # immediately returns to 0.00 and remains ready for the next customer.
        display_cart=self.cart
        display_ticket_discount=self.ticket_discount_cents
        weights=[line_total(x['unit_price_cents'],x['qty'])-int(x.get('discount_cents',0)) for x in display_cart]
        nets=allocate(total,weights)
        for i,(x,net) in enumerate(zip(display_cart,nets)):
            gross=line_total(x['unit_price_cents'],x['qty'])
            offer=Decimal(str(x['unit_price_cents']))<x.get('base_price_cents',0) or gross>net
            thumb=self.thumbnail({'id':x['product_id'],'image_path':x.get('image_path','')})
            step=x.get('qty_multiplier',1)
            name=x['name']+(f' · pack ×{step:g}' if step!=1 else '')
            quantity=(f"{x['qty']/step:g}p" if step!=1 else f"{x['qty']:g}")
            if self.return_mode:quantity='-'+quantity
            price=fmt(sign*line_total(x['unit_price_cents'],step),'')
            tag='offer' if offer else ('even' if i%2==0 else 'odd')
            discount_pct=(float(gross-net)*100/float(gross)) if gross else 0
            discount_text=(f"{discount_pct:.1f}%".replace('.0%','%')) if discount_pct else '—'
            self.ticket.insert('','end',iid=str(i),text=name,image=thumb,values=(quantity,price,discount_text,fmt(sign*net,'')),tags=(tag,))
        if self.cart:
            chosen=str(min(index if index is not None else len(self.cart)-1,len(self.cart)-1))
            self.ticket.selection_set(chosen);self.ticket.see(chosen)
        self.subtotal_label.config(text=f"{self.tr('Sous-total','المجموع الفرعي','Subtotal')} {fmt(sign*sub,self.currency)}  ·  {self.tr('Remise ticket','تخفيض التذكرة','Receipt discount')} {fmt(display_ticket_discount,self.currency)}")
        item_count=len(display_cart)
        completed=not self.cart and bool(self.last_sale_snapshot)
        if self.return_mode:
            self.ticket_title.config(text=self.tr(f'↩  RETOUR EN COURS  ·  {item_count} article(s)',f'↩  إرجاع جارٍ  ·  {item_count} منتوج',f'↩  RETURN IN PROGRESS  ·  {item_count} item(s)'))
        else:
            self.ticket_title.config(text=self.tr(f'🧾  Ticket en cours  ·  {item_count} article(s)',f'🧾  التذكرة الحالية  ·  {item_count} منتوج',f'🧾  Current receipt  ·  {item_count} item(s)'))
        if completed:
            if not self.last_sale_box.winfo_manager():self.last_sale_box.pack(fill='x',pady=(4,6),before=self.total_box)
        elif self.last_sale_box.winfo_manager():
            self.last_sale_box.pack_forget()
        if not self.edit_controls.winfo_manager():self.edit_controls.pack(fill='x',pady=(2,4),before=self.subtotal_label)
        if not self.checkout_buttons.winfo_manager():self.checkout_buttons.pack(fill='x',pady=(2,0))
        self.total_label.config(text=fmt(sign*total,self.currency))
        self.app.update_customer_display(display_cart,sign*total)

    def update_quantity(self,index,qty):
        if not math.isfinite(float(qty)):
            messagebox.showerror('ToDo',self.tr('Quantité invalide.','الكمية غير صالحة.','Invalid quantity.'),parent=self);return
        x=self.cart[index]
        if qty<=0:self.cart.pop(index)
        else:
            if not x.get('allow_fraction',False) and not float(qty).is_integer():
                messagebox.showerror('ToDo',self.tr('Quantité entière requise.','الكمية يجب أن تكون عدداً صحيحاً.','A whole quantity is required.'),parent=self);return
            try:unit=Decimal(x['unit_price_cents']) if x.get('manual_unit_price') else resolve_unit_price(x['product_id'],qty,x.get('barcode_id'),grid_id=self.price_grid_id)
            except ValueError as e:
                messagebox.showerror('ToDo',str(e),parent=self);return
            x.update(qty=qty,unit_price_cents=str(unit))
            x['discount_cents']=min(x.get('discount_cents',0),line_total(unit,qty))
        self.ticket_discount_cents=min(self.ticket_discount_cents,self.totals()[0])
        self.refresh(index);self.focus_search()

    def change(self,delta):
        index=self.selected()
        if index is not None:self.update_quantity(index,self.cart[index]['qty']+delta*self.cart[index].get('qty_multiplier',1))

    def set_qty(self):
        index=self.selected()
        if index is None:return
        step=self.cart[index].get('qty_multiplier',1)
        qty=simpledialog.askfloat(self.tr('Quantité','الكمية','Quantity'),self.tr('Nombre de packs:','عدد العلب:','Number of packs:') if step!=1 else self.tr('Nouvelle quantité:','الكمية الجديدة:','New quantity:'),initialvalue=self.cart[index]['qty']/step,parent=self,minvalue=0.001)
        if qty is not None:self.update_quantity(index,qty*step)
        self.focus_search()

    def remove(self):
        index=self.selected()
        if index is not None:self.update_quantity(index,0)

    def discount(self):
        from services.security import require_permission
        try:require_permission('DISCOUNT')
        except PermissionError as e:messagebox.showerror('ToDo',str(e),parent=self);return
        if not self.cart:return
        amount=simpledialog.askfloat(self.tr('Remise ticket','تخفيض التذكرة','Receipt discount'),self.tr('Montant de la remise:','قيمة التخفيض:','Discount amount:'),parent=self,minvalue=0,maxvalue=self.totals()[0]/100)
        if amount is not None:self.ticket_discount_cents=to_cents(amount);self.refresh()
        self.focus_search()

    def line_discount(self):
        from services.security import require_permission
        try:require_permission('DISCOUNT')
        except PermissionError as e:messagebox.showerror('ToDo',str(e),parent=self);return
        index=self.selected()
        if index is None:return
        x=self.cart[index]
        amount=simpledialog.askfloat(self.tr('Remise ligne','تخفيض السطر','Line discount'),self.tr('Montant de la remise:','قيمة التخفيض:','Discount amount:'),parent=self,minvalue=0,maxvalue=line_total(x['unit_price_cents'],x['qty'])/100)
        if amount is not None:
            x['discount_cents']=to_cents(amount)
            self.ticket_discount_cents=min(self.ticket_discount_cents,self.totals()[0]);self.refresh(index)
        self.focus_search()

    def set_price(self):
        from services.security import require_permission
        try:require_permission('PRICE_EDIT')
        except PermissionError as e:messagebox.showerror('ToDo',str(e),parent=self);return
        index=self.selected()
        if index is None:return
        line=self.cart[index]
        if line.get('qty_multiplier',1)!=1:
            messagebox.showinfo('ToDo',self.tr('Pour un pack, utilisez la remise ligne.','بالنسبة للعلبة، استعمل تخفيض السطر.','For a pack, use the line discount.'),parent=self);return
        amount=simpledialog.askstring(self.tr('Modifier prix','تعديل الثمن','Edit price'),self.tr(f"{line['name']}\nNouveau prix unitaire ({self.currency}) :",f"{line['name']}\nالثمن الجديد للوحدة ({self.currency}):",f"{line['name']}\nNew unit price ({self.currency}):"),initialvalue=f"{Decimal(line['unit_price_cents'])/100:.2f}",parent=self)
        if amount is None:return
        try:
            price=to_cents(amount)
            if price<0:raise ValueError(self.tr('Prix invalide','الثمن غير صالح','Invalid price'))
            line['unit_price_cents']=str(price)
            line['manual_unit_price']=True
            line['discount_cents']=min(line.get('discount_cents',0),line_total(price,line['qty']))
            self.ticket_discount_cents=min(self.ticket_discount_cents,self.totals()[0])
            self.refresh(index)
        except Exception as error:messagebox.showerror('ToDo',str(error),parent=self)
        self.focus_search()

    def choose_seller(self):
        window=tk.Toplevel(self);window.title(self.tr('Choisir vendeur','اختيار البائع','Choose seller'));window.geometry('420x420');window.transient(self.app);window.grab_set()
        tree=ttk.Treeview(window,columns=('name',),show='headings');tree.heading('name',text=self.tr('Vendeur','البائع','Seller'));tree.pack(fill='both',expand=True,padx=12,pady=12)
        with connect() as c:rows=c.execute("SELECT id,name FROM sellers WHERE active=1 ORDER BY name COLLATE NOCASE").fetchall()
        for row in rows:tree.insert('','end',iid=str(row['id']),values=(row['name'],))
        buttons=ttk.Frame(window);buttons.pack(fill='x',padx=12,pady=(0,12))
        def select(clear=False):
            if not clear and not tree.selection():return
            self.seller_id=None if clear else int(tree.selection()[0]);self.update_seller_label();window.destroy();self.focus_search()
        ttk.Button(buttons,text=self.tr('Choisir','اختيار','Choose'),command=select).pack(side='left')
        ttk.Button(buttons,text=self.tr('Aucun vendeur','بدون بائع','No seller'),command=lambda:select(True)).pack(side='left',padx=8)
        tree.bind('<Double-1>',lambda e:select())
    def update_seller_label(self):
        name=None
        if self.seller_id is not None:
            with connect() as c:
                row=c.execute("SELECT name FROM sellers WHERE id=?",(self.seller_id,)).fetchone()
                name=row['name'] if row else None
        self.seller_button.configure(text=(self.tr('Vendeur : ','البائع: ','Seller: ')+(name or self.tr('aucun','لا أحد','none')))[:40])

    def choose_client(self):
        from services.clients import list_clients
        window=tk.Toplevel(self);window.title(self.tr('Choisir client','اختيار الزبون','Choose customer'));window.geometry('580x460')
        window.transient(self.app);window.grab_set()
        query=tk.StringVar();entry=ttk.Entry(window,textvariable=query);entry.pack(fill='x',padx=12,pady=12)
        buttons=ttk.Frame(window);buttons.pack(side='bottom',fill='x',padx=12,pady=12)
        tree=ttk.Treeview(window,columns=('name','phone'),show='headings')
        tree.heading('name',text=self.tr('Client','الزبون','Customer'));tree.heading('phone',text=self.tr('Téléphone','الهاتف','Phone'));tree.pack(fill='both',expand=True,padx=12)
        def refresh(*args):
            tree.delete(*tree.get_children())
            for row in list_clients(query.get()):tree.insert('','end',iid=str(row['id']),values=(row['name'],row['phone']))
        def select(clear=False):
            if not clear and not tree.selection():return
            self.client_id=None if clear else int(tree.selection()[0])
            self.update_client_label();window.destroy();self.focus_search()
        ttk.Button(buttons,text=self.tr('Choisir','اختيار','Choose'),command=select).pack(side='left')
        ttk.Button(buttons,text=self.tr('Client de passage','زبون عابر','Walk-in customer'),command=lambda:select(True)).pack(side='left',padx=10)
        tree.bind('<Double-1>',lambda e:select());entry.bind('<KeyRelease>',refresh);refresh();entry.focus_set()

    def update_client_label(self):
        from services.clients import get_client
        name=get_client(self.client_id)['name'] if self.client_id is not None else self.tr('passage','عابر','walk-in')
        self.client_button.configure(text=self.tr('F6 Client : ','F6 الزبون: ','F6 Customer: ')+name[:30])

    def load_quotation(self,payload):
        if self.cart:
            raise ValueError(self.tr('Videz ou mettez en attente le ticket actuel avant de charger un devis.','أفرغ أو علّق التذكرة الحالية قبل تحميل عرض السعر.','Empty or hold the current receipt before loading a quotation.'))
        quote=payload['quotation'];self.quotation_id=int(quote['id']);self.client_id=quote['client_id']
        self.cart=[dict(product_id=int(x['product_id']),name=x['name'],qty=float(x['qty']),unit_price_cents=str(int(x['unit_price_cents'])),
                        base_price_cents=int(x['unit_price_cents']),discount_cents=0,allow_fraction=1,barcode_id=None,barcode='') for x in payload['cart']]
        self.update_client_label();self.refresh();self.status.config(text=self.tr(f"Devis #{quote['id']} chargé.",f"تم تحميل عرض السعر #{quote['id']}.",f"Quotation #{quote['id']} loaded."));self.focus_search()

    def load_customer_order(self,payload):
        if self.cart:
            raise ValueError(self.tr('Videz ou mettez en attente le ticket actuel avant de charger une commande.','أفرغ أو علّق التذكرة الحالية قبل تحميل الطلب.','Empty or hold the current receipt before loading an order.'))
        order=payload['order'];self.customer_order_id=int(order['id']);self.client_id=int(order['client_id'])
        self.cart=[dict(product_id=int(x['product_id']),name=x['name'],qty=float(x['qty']),unit_price_cents=str(int(x['unit_price_cents'])),
                        base_price_cents=int(x['unit_price_cents']),discount_cents=0,allow_fraction=1,barcode_id=None,barcode='') for x in payload['cart']]
        self.update_client_label();self.refresh();self.status.config(text=self.tr(f"Commande client #{order['id']} chargée.",f"تم تحميل طلب الزبون #{order['id']}.",f"Customer order #{order['id']} loaded."));self.focus_search()

    def toggle_return_mode(self):
        if self.busy:return
        if self.cart:
            messagebox.showinfo('ToDo',self.tr('Validez, annulez ou mettez le ticket actuel en attente avant de changer de mode.','أكد أو ألغ أو علّق التذكرة الحالية قبل تغيير الوضع.','Complete, cancel, or hold the current receipt before changing mode.'),parent=self)
            return
        self.return_mode=not self.return_mode
        self.ticket_discount_cents=0
        self._update_return_controls()
        self.refresh()
        self.status.config(text=self.tr('↩ Retour activé : scannez les articles à reprendre, puis SOLDER.','↩ تم تفعيل الإرجاع: امسح المنتوجات المرجعة ثم اضغط الأداء.','↩ Return mode: scan returned items, then PAY.') if self.return_mode else self.tr('● Vente activée : scanner prêt.','● تم تفعيل البيع: الماسح جاهز.','● Sale mode: scanner ready.'))
        self.focus_search()

    def _update_return_controls(self):
        if not hasattr(self,'return_button'):return
        if self.return_mode:
            self.return_button.config(text=self.tr('F9  VENTE','F9  البيع','F9  SALE'),style='Success.TButton')
            self.checkout_main.config(text=self.tr('↩ VALIDER RETOUR F5','↩ تأكيد الإرجاع F5','↩ CONFIRM RETURN F5'),style='Danger.TButton')
            if self.checkout_without_ticket:self.checkout_without_ticket.pack_forget()
            self.payment_label.config(text=self.tr('Remboursement : Espèces','الاسترجاع: نقداً','Refund: Cash'),bg='#FEE2E2',fg='#B91C1C')
        else:
            self.return_button.config(text=self.tr('F9  Retour','F9  إرجاع','F9  Return'),style='Danger.TButton')
            self.checkout_main.config(text=self.tr('✓ SOLDER avec ticket F5','✓ الأداء مع التذكرة F5','✓ PAY with receipt F5'),style='Success.TButton')
            if self.checkout_without_ticket and not self.checkout_without_ticket.winfo_manager():
                self.checkout_without_ticket.pack(side='left',expand=True,fill='x',padx=(2,0),ipady=3)
            self.payment_label.config(text=self.tr('Paiement : Espèces','الأداء: نقداً','Payment: Cash'),bg='#DCFCE7',fg='#166534')

    def set_payment(self,method):
        self.payment=method
        labels={'CASH':self.tr('Espèces','نقداً','Cash'),'CARD':self.tr('Carte','بطاقة','Card'),
                'CREDIT':self.tr('Crédit','دين','Credit'),'MIXED':self.tr('Mixte','مختلط','Mixed')}
        palette={'CASH':('#DCFCE7','#166534'),'CARD':('#DBEAFE','#1D4ED8'),
                 'CREDIT':('#FEF3C7','#92400E'),'MIXED':('#EDE9FE','#6D28D9')}
        bg,fg=palette.get(method,('#E2E8F0','#334155'))
        self.payment_label.config(text=self.tr('Paiement : ','الأداء: ','Payment: ')+labels.get(method,method),bg=bg,fg=fg)
        self.focus_search()

    def clear(self,preserve_last_sale=False):
        self._cancel_pending_input_jobs()
        self.cart=[];self.ticket_discount_cents=0;self.return_mode=False;self._update_return_controls();self.held_id=None;self.client_id=None;self.customer_order_id=None;self.quotation_id=None;self.seller_id=None;self.price_grid_id=None;self.price_grid_name=self.tr('Normal','عادي','Normal');self.payment='CASH';self.query.set('');self.scan_quantity.set('1');self.payment_label.config(text=self.tr('Paiement : Espèces','الأداء: نقداً','Payment: Cash'),bg='#DCFCE7',fg='#166534');self.update_client_label();self.update_seller_label()
        if not preserve_last_sale:
            self.last_sale_snapshot=None;self.last_sale_discount_cents=0
        self.refresh();self.focus_search()

    def cancel(self):
        if self.cart and not messagebox.askyesno(self.tr('Annuler','إلغاء'),self.tr('Vider le ticket en cours ? Un ticket en attente reste sauvegardé.','إفراغ التذكرة الحالية؟ التذكرة الموضوعة في الانتظار تبقى محفوظة.','Clear the current receipt? A held receipt remains saved.'),parent=self):return
        self.clear()

    def hold(self):
        if not self.cart:return
        label=simpledialog.askstring(self.tr('Attente','انتظار','Hold'),self.tr('Nom ou numéro du ticket:','اسم أو رقم التذكرة:','Receipt name or number:'),parent=self)
        if label is None:return
        try:
            hold_sale(self.app.user['id'],self.cart,label,self.ticket_discount_cents,self.held_id,client_id=self.client_id,seller_id=self.seller_id,price_grid_id=self.price_grid_id,payment_method=self.payment)
            self.clear();self.status.config(text=self.tr('Ticket et remise sauvegardés.','تم حفظ التذكرة والتخفيض.','Receipt and discount saved.'))
        except Exception as e:messagebox.showerror('ToDo',str(e),parent=self)

    def show_held(self):
        if self.cart:
            messagebox.showinfo('ToDo',self.tr('Mettez le ticket actuel en attente avant de reprendre un autre.','ضع التذكرة الحالية في الانتظار قبل استئناف تذكرة أخرى.','Hold the current receipt before resuming another one.'),parent=self);return
        rows=list_held()
        if not rows:
            messagebox.showinfo('ToDo',self.tr('Aucun ticket en attente.','لا توجد تذكرة في الانتظار.','No held receipts.'),parent=self);return
        w=tk.Toplevel(self);w.title(self.tr('Tickets en attente','التذاكر في الانتظار','Held receipts'));w.transient(self);w.grab_set()
        tree=ttk.Treeview(w,columns=('date','discount'),show='tree headings')
        tree.heading('#0',text=self.tr('Ticket','التذكرة','Receipt'));tree.heading('date',text=self.tr('Date','التاريخ','Date'));tree.heading('discount',text=self.tr('Remise','التخفيض','Discount'))
        tree.pack(fill='both',expand=True,padx=12,pady=12)
        for r in rows:tree.insert('','end',iid=str(r['id']),text=r['label'],values=(r['created_at'],fmt(r['discount_cents'])))
        def resume(event=None):
            if not tree.selection():return
            state=resume_held(int(tree.selection()[0]))
            self.cart=state['cart'];self.ticket_discount_cents=state['discount_cents'];self.held_id=state['held_id']
            self.client_id=state.get('client_id');self.update_client_label()
            self.seller_id=state.get('seller_id');self.update_seller_label()
            self.price_grid_id=state.get('price_grid_id')
            if self.price_grid_id is not None:
                with connect() as conn:grid=conn.execute('SELECT name FROM price_grids WHERE id=? AND active=1',(self.price_grid_id,)).fetchone()
                if grid:self.price_grid_name=grid['name']
                else:self.price_grid_id=None;self.price_grid_name=self.tr('Normal','عادي','Normal')
            else:self.price_grid_name=self.tr('Normal','عادي','Normal')
            self.set_payment(state.get('payment_method') or 'CASH')
            self.refresh();w.destroy();self.focus_search()
        tree.bind('<Return>',resume);tree.bind('<Double-1>',resume)
        ttk.Button(w,text=self.tr('Reprendre','استئناف','Resume'),command=resume).pack(pady=8)

    def checkout(self, print_ticket=True):
        if not print_ticket and get_setting('sans_ticket_enabled','1')!='1':
            messagebox.showinfo('ToDo',self.tr('Le paiement sans ticket est désactivé dans les paramètres.','الأداء بدون تذكرة معطل من الإعدادات.','Payment without a receipt is disabled in settings.'),parent=self);return
        if not self.cart or self.busy:return
        session=get_open_session()
        if not session:
            messagebox.showinfo('ToDo',self.tr('Ouvrez la caisse avant de vendre.','افتح الصندوق قبل البيع.','Open the cash drawer before selling.'),parent=self);return
        self.busy=True
        self.last_sale_snapshot=None
        try:
            total=self.totals()[1]
            if self.return_mode:
                result=create_manual_returns(session['id'],self.app.user['id'],self.cart,self.ticket_discount_cents)
                self.clear()
                self.status.config(text=self.tr(f"Retour validé : {fmt(result['amount_cents'],self.currency)} rendus en espèces · {result['return_no']}",f"تم تأكيد الإرجاع: {fmt(result['amount_cents'],self.currency)} نقداً · {result['return_no']}",f"Return completed: {fmt(result['amount_cents'],self.currency)} cash refunded · {result['return_no']}"))
                self.render_products()
                return
            loyalty_points_used=0
            from services.clients import get_client
            client_name=get_client(self.client_id)['name'] if self.client_id is not None else None
            if self.client_id is not None:
                from services.loyalty import client_points,loyalty_settings
                cfg=loyalty_settings()
                balance=client_points(self.client_id)
                if cfg['enabled'] and balance>0:
                    max_points=min(balance,total//cfg['point_value_cents'])
                    if max_points>0 and messagebox.askyesno('ToDo',self.tr(
                        f"Ce client a {balance} point(s). Utiliser des points sur ce ticket ?",
                        f"لدى هذا الزبون {balance} نقطة. هل تريد استعمال النقاط في هذه الفاتورة؟",
                         f"This customer has {balance} point(s). Use points on this receipt?"),parent=self):
                        pts=simpledialog.askinteger(self.tr('Points fidélité','نقاط الوفاء','Loyalty points'),self.tr(
                            f"Points à utiliser (max {max_points}) :",f"عدد النقاط المستعملة (الأقصى {max_points}):",f"Points to use (max {max_points}):"),
                            parent=self,minvalue=1,maxvalue=max_points)
                        if pts:
                            loyalty_points_used=pts
                            total-=pts*cfg['point_value_cents']
            mode=get_setting('print_mode','ask')
            use_payment_window=get_setting('payment_window_enabled','1')=='1' or self.payment in ('MIXED','CREDIT')
            if use_payment_window:
                dialog=PaymentDialog(self,total,self.currency,self.payment,client_name=client_name)
                dialog.print_ticket.set(print_ticket and mode=='always')
                self.wait_window(dialog)
                if dialog.result is None:return
                self.payment,paid,dialog_print,payments=dialog.result
                self.set_payment(self.payment)
            else:
                paid=total
                if print_ticket and mode=='ask':
                    dialog_print=messagebox.askyesno(
                        'ToDo',
                        self.tr('Imprimer le ticket ?','طباعة التذكرة؟','Print the receipt?'),
                        parent=self
                    )
                else:
                    dialog_print=(print_ticket and mode=='always')
                payments=None
            completed_payment=self.payment
            request_signature=json.dumps([session['id'],self.app.user['id'],self.cart,self.payment,paid,self.ticket_discount_cents,self.held_id,self.client_id,payments,self.seller_id,loyalty_points_used,self.customer_order_id,self.quotation_id,self.price_grid_id],sort_keys=True,default=str)
            if self.checkout_request is None or self.checkout_request[0]!=request_signature:
                self.checkout_request=(request_signature,uuid.uuid4().hex)
            result=complete_sale(session['id'],self.app.user['id'],self.cart,self.payment,paid,self.ticket_discount_cents,self.held_id,client_id=self.client_id,payments=payments,seller_id=self.seller_id,loyalty_points=loyalty_points_used,customer_order_id=self.customer_order_id,quotation_id=self.quotation_id,price_grid_id=self.price_grid_id,request_key=self.checkout_request[1])
            # The completed ticket stays visible until the first item of the next sale.
            # Business cart state is cleared immediately so the completed sale cannot be submitted twice.
            self.last_sale_snapshot=[dict(line) for line in self.cart]
            self.last_sale_discount_cents=self.ticket_discount_cents
            labels={'CASH':self.tr('ESPÈCES','نقداً','CASH'),'CARD':self.tr('CARTE','بطاقة','CARD'),
                    'CREDIT':self.tr('CRÉDIT','دين','CREDIT'),'MIXED':self.tr('MIXTE','مختلط','MIXED')}
            self.last_sale_summary.config(text=self.tr(
                f"TOTAL : {fmt(total,self.currency)}\nMODE P : {labels.get(completed_payment,completed_payment)}\nPAYÉ : {fmt(paid,self.currency)}\nRENDU : {fmt(result['change_cents'],self.currency)}",
                f"المجموع : {fmt(total,self.currency)}\nطريقة الأداء : {labels.get(completed_payment,completed_payment)}\nالمؤدى : {fmt(paid,self.currency)}\nالباقي : {fmt(result['change_cents'],self.currency)}",
                f"TOTAL : {fmt(total,self.currency)}\nPAYMENT : {labels.get(completed_payment,completed_payment)}\nPAID : {fmt(paid,self.currency)}\nCHANGE : {fmt(result['change_cents'],self.currency)}"
            ))
            self.clear(preserve_last_sale=True)
            self.checkout_request=None
            self.status.config(text=self.tr(f"Dernière vente : {fmt(total,self.currency)} · Reçu : {fmt(paid,self.currency)} · Monnaie : {fmt(result['change_cents'],self.currency)} · {result['sale_no']}",f"آخر بيع: {fmt(total,self.currency)} · المستلم: {fmt(paid,self.currency)} · الباقي: {fmt(result['change_cents'],self.currency)} · {result['sale_no']}",f"Last sale: {fmt(total,self.currency)} · Received: {fmt(paid,self.currency)} · Change: {fmt(result['change_cents'],self.currency)} · {result['sale_no']}"))
            if get_setting('customer_serial_enabled','0')=='1':
                try:
                    from services.customer_serial_display import show_payment
                    show_payment(paid,result['change_cents'])
                except Exception:
                    pass
            try:
                if print_ticket and mode!='never' and (mode=='always' or dialog_print):
                    print_receipt_windows(result['id'])
            except Exception as e:
                self.status.config(text=self.tr(f"Vente enregistrée · Impression indisponible : {e}",f"تم تسجيل البيع · الطباعة غير متاحة: {e}",f"Sale recorded · Printing unavailable: {e}"))
            self.render_products()
        except Exception as e:messagebox.showerror('ToDo',str(e),parent=self)
        finally:self.busy=False;self.focus_search()

    def show_receipt(self,result):
        w=tk.Toplevel(self);w.title(result['sale_no']);w.geometry('450x560');w.transient(self)
        buttons=ttk.Frame(w);buttons.pack(side='bottom',fill='x')
        def save_pdf():
            path=filedialog.asksaveasfilename(parent=w,defaultextension='.pdf',filetypes=[('PDF','*.pdf')],initialfile=result['sale_no']+'.pdf')
            if path:export_receipt_pdf(result['id'],path)
        ttk.Button(buttons,text=self.tr('Enregistrer PDF','حفظ PDF','Save PDF'),command=save_pdf).pack(side='left',padx=8,pady=8)
        text=tk.Text(w,font=('Consolas',11),padx=16,pady=16)
        text.pack(fill='both',expand=True);text.insert('1.0',build_receipt(result['id']));text.config(state='disabled')
        ttk.Button(buttons,text=self.tr('Imprimer','طباعة','Print'),command=lambda:print_receipt_windows(result['id'])).pack(side='left',padx=12,pady=12)
        def send_mail():
            address=simpledialog.askstring(self.tr('E-mail','البريد الإلكتروني','Email'),self.tr('Adresse destinataire:','بريد المستلم:','Recipient address:'),parent=w)
            if not address:return
            try:
                from services.emailer import send_email
                send_email(address,self.tr(f"Ticket {result['sale_no']}",f"تذكرة {result['sale_no']}",f"Receipt {result['sale_no']}"),build_receipt(result['id']))
                messagebox.showinfo('ToDo',self.tr('Ticket envoyé.','تم إرسال التذكرة.','Receipt sent.'),parent=w)
            except Exception as error:messagebox.showerror(self.tr('E-mail','البريد الإلكتروني','Email'),str(error),parent=w)
        if get_setting('email_enabled','0')=='1':
            ttk.Button(buttons,text=self.tr('E-mail','بريد','Email'),command=send_mail).pack(side='left',padx=8,pady=12)
        ttk.Button(buttons,text=self.tr('Fermer','إغلاق','Close'),command=w.destroy).pack(side='right',padx=12,pady=12)
        w.bind('<Escape>',lambda e:w.destroy())
