import tkinter as tk
from tkinter import ttk,messagebox,simpledialog
from database import connect,get_setting
from services.money import fmt
from services.clients import list_clients
from services.customer_orders import create_customer_order,list_customer_orders,customer_order_lines,set_customer_order_status,order_cart

class CustomerOrdersFrame(ttk.Frame):
    def __init__(self,master,app=None):
        super().__init__(master,padding=16);self.app=app
        self.lang=get_setting('language','fr');self.tr=lambda fr,ar,en=None: ar if self.lang=='ar' else (en if self.lang=='en' and en else fr)
        top=ttk.Frame(self);top.pack(fill='x',pady=(0,8))
        ttk.Label(top,text=self.tr('Commandes clients','طلبات الزبائن','Customer orders'),style='Title.TLabel').pack(side='left')
        ttk.Button(top,text=self.tr('+ Nouvelle commande','+ طلب جديد','+ New order'),style='Primary.TButton',command=self.new_order).pack(side='right')
        self.status=tk.StringVar(value='')
        ttk.Combobox(top,textvariable=self.status,values=('', 'OPEN','READY','COMPLETED','CANCELLED'),state='readonly',width=14).pack(side='right',padx=8)
        self.status.trace_add('write',lambda *_:self.refresh())
        cols=('id','client','phone','status','total','date','address')
        self.tree=ttk.Treeview(self,columns=cols,show='headings',height=18)
        for k,h,w in [('id','ID',55),('client',self.tr('Client','الزبون','Customer'),200),('phone',self.tr('Téléphone','الهاتف','Phone'),120),
                      ('status',self.tr('Statut','الحالة','Status'),90),('total',self.tr('Total','المجموع','Total'),100),
                      ('date',self.tr('Date','التاريخ','Date'),145),('address',self.tr('Adresse','العنوان','Address'),260)]:
            self.tree.heading(k,text=h);self.tree.column(k,width=w,anchor='center' if k not in ('client','address') else 'w')
        self.tree.pack(fill='both',expand=True)
        bar=ttk.Frame(self);bar.pack(fill='x',pady=(8,0))
        ttk.Button(bar,text=self.tr('Marquer prête','جاهز للاستلام','Mark ready'),command=lambda:self.set_status('READY')).pack(side='left')
        ttk.Button(bar,text=self.tr('Charger en caisse','تحميل للكاشير','Load in checkout'),style='Success.TButton',command=self.load_sale).pack(side='left',padx=6)
        ttk.Button(bar,text=self.tr('Annuler','إلغاء','Cancel'),style='Danger.TButton',command=lambda:self.set_status('CANCELLED')).pack(side='left')
        ttk.Button(bar,text=self.tr('Détails','التفاصيل','Details'),command=self.details).pack(side='left',padx=6)
        self.refresh()
    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for r in list_customer_orders(self.status.get()):
            labels={'OPEN':self.tr('Ouverte','مفتوح','Open'),'READY':self.tr('Prête','جاهز','Ready'),'COMPLETED':self.tr('Terminée','مكتمل','Completed'),'CANCELLED':self.tr('Annulée','ملغى','Cancelled')}
            self.tree.insert('','end',iid=str(r['id']),values=(r['id'],r['client_name'],r['phone'],labels.get(r['status'],r['status']),fmt(r['total_cents'],''),r['created_at'],r['delivery_address']))
    def _selected(self):
        s=self.tree.selection();return int(s[0]) if s else None
    def set_status(self,status):
        oid=self._selected()
        if not oid:return
        try:set_customer_order_status(oid,status);self.refresh()
        except Exception as e:messagebox.showerror('ToDo',str(e),parent=self)
    def load_sale(self):
        oid=self._selected()
        if not oid or self.app is None:return
        try:
            payload=order_cart(oid);self.app.show('sale');self.app.current.load_customer_order(payload)
        except Exception as e:messagebox.showerror('ToDo',str(e),parent=self)
    def details(self):
        oid=self._selected()
        if not oid:return
        w=tk.Toplevel(self);w.title(self.tr(f'Commande #{oid}',f'الطلب #{oid}'));w.geometry('700x460');w.transient(self.winfo_toplevel())
        tree=ttk.Treeview(w,columns=('name','qty','price','total'),show='headings')
        for k,h,width in [('name',self.tr('Article','المنتوج','Product'),280),('qty',self.tr('Qté','الكمية','Qty'),80),('price',self.tr('Prix','الثمن','Price'),100),('total',self.tr('Total','المجموع','Total'),110)]:
            tree.heading(k,text=h);tree.column(k,width=width,anchor='center' if k!='name' else 'w')
        tree.pack(fill='both',expand=True,padx=12,pady=12)
        for r in customer_order_lines(oid):tree.insert('','end',values=(r['name_snapshot'],f"{r['qty']:g}",fmt(r['unit_price_cents'],''),fmt(r['line_total_cents'],'')))
    def new_order(self):
        clients=list_clients()
        if not clients:
            messagebox.showinfo('ToDo',self.tr('Créez d’abord un client.','أنشئ زبوناً أولاً.','Create a customer first.'),parent=self);return
        w=tk.Toplevel(self);w.title(self.tr('Nouvelle commande client','طلب زبون جديد','New customer order'));w.geometry('960x650');w.transient(self.winfo_toplevel());w.grab_set()
        client_var=tk.StringVar();labels=[f"{c['name']} · #{c['id']}" for c in clients]
        ttk.Combobox(w,textvariable=client_var,values=labels,state='readonly',width=38).pack(anchor='w',padx=12,pady=(12,4));client_var.set(labels[0])
        address=tk.StringVar();notes=tk.StringVar()
        ttk.Entry(w,textvariable=address,width=60).pack(anchor='w',padx=12,pady=4)
        ttk.Label(w,text=self.tr('Adresse de livraison','عنوان التوصيل','Delivery address')).place(x=500,y=48)
        search=tk.StringVar();e=ttk.Entry(w,textvariable=search,width=36);e.pack(anchor='w',padx=12,pady=6)
        body=ttk.Panedwindow(w,orient='horizontal');body.pack(fill='both',expand=True,padx=12,pady=6)
        left=ttk.Frame(body);right=ttk.Frame(body);body.add(left,weight=2);body.add(right,weight=3)
        products=ttk.Treeview(left,columns=('id','name','price'),show='headings')
        for k,h,width in [('id','ID',50),('name',self.tr('Article','المنتوج','Product'),230),('price',self.tr('Prix','الثمن','Price'),90)]:products.heading(k,text=h);products.column(k,width=width)
        products.pack(fill='both',expand=True)
        order=ttk.Treeview(right,columns=('name','qty','price','total'),show='headings')
        for k,h,width in [('name',self.tr('Article','المنتوج','Product'),220),('qty',self.tr('Qté','الكمية','Qty'),70),('price',self.tr('Prix','الثمن','Price'),90),('total',self.tr('Total','المجموع','Total'),100)]:order.heading(k,text=h);order.column(k,width=width)
        order.pack(fill='both',expand=True)
        lines=[]
        def search_products(*_):
            q=search.get().strip()
            with connect() as c:rows=c.execute("SELECT id,name,sale_price_cents FROM products WHERE active=1 AND (?='' OR instr(lower(name),lower(?))>0) ORDER BY name LIMIT 100",(q,q)).fetchall()
            products.delete(*products.get_children())
            for r in rows:products.insert('','end',iid=str(r['id']),values=(r['id'],r['name'],fmt(r['sale_price_cents'],'')))
        def redraw():
            order.delete(*order.get_children())
            for i,x in enumerate(lines):order.insert('','end',iid=str(i),values=(x['name'],f"{x['qty']:g}",fmt(x['unit_price_cents'],''),fmt(round(x['qty']*x['unit_price_cents']),'')))
        def add(event=None):
            s=products.selection()
            if not s:return
            vals=products.item(s[0],'values');qty=simpledialog.askfloat(self.tr('Quantité','الكمية','Quantity'),self.tr(f"Quantité — {vals[1]} :",f"الكمية — {vals[1]}:"),parent=w,minvalue=0.001)
            if qty is None:return
            price_cents=int(round(float(vals[2])*100))
            lines.append(dict(product_id=int(vals[0]),name=vals[1],qty=qty,unit_price_cents=price_cents));redraw()
        def save():
            try:
                cid=int(client_var.get().rsplit('#',1)[1]);oid,total=create_customer_order(cid,lines,address.get(),notes.get())
                messagebox.showinfo('ToDo',self.tr(f'Commande #{oid} enregistrée · {fmt(total)}',f'تم حفظ الطلب #{oid} · {fmt(total)}'),parent=w);w.destroy();self.refresh()
            except Exception as ex:messagebox.showerror('ToDo',str(ex),parent=w)
        search.trace_add('write',search_products);products.bind('<Double-1>',add);products.bind('<Return>',add);search_products()
        ttk.Entry(w,textvariable=notes,width=60).pack(anchor='w',padx=12,pady=4)
        ttk.Button(w,text=self.tr('Enregistrer commande','حفظ الطلب','Save order'),style='Success.TButton',command=save).pack(pady=(4,12))
