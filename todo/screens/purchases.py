import tkinter as tk
from tkinter import ttk,messagebox,simpledialog
from database import get_setting, connect
from services.money import to_cents,fmt
from services.purchases import receive_purchase,create_purchase_order,list_purchase_orders,purchase_order_lines,mark_purchase_order_received,cancel_purchase_order
from services.suppliers import list_suppliers, save_supplier
from screens.suppliers import SupplierEditor

class PurchasesFrame(ttk.Frame):
    def __init__(self,master,app=None):
        super().__init__(master,padding=16);self.lines=[];self.app=app
        self.lang=get_setting('language','fr');self.tr=lambda fr,ar: ar if self.lang=='ar' else fr
        top=ttk.Frame(self);top.pack(fill="x")
        ttk.Label(top,text=self.tr('Réceptions','المشتريات'),style='Title.TLabel').pack(side='left')
        self.supplier=tk.StringVar();self.invoice=tk.StringVar()
        self.supplier_choice=ttk.Combobox(top,textvariable=self.supplier,width=22)
        self.supplier_choice.pack(side="left",padx=(20,5))
        self.supplier_choice.bind('<<ComboboxSelected>>',self.select_supplier)
        self.supplier_id=None
        self.supplier.trace_add('write',lambda *args:setattr(self,'supplier_id',None))
        ttk.Label(top,text=self.tr('Fournisseur','المورد')).pack(side="left")
        ttk.Button(top,text='+',width=3,command=lambda:SupplierEditor(self,on_saved=self.refresh_suppliers)).pack(side='left')
        self.refresh_suppliers()
        ttk.Entry(top,textvariable=self.invoice,width=18).pack(side="left",padx=(20,5));ttk.Label(top,text=self.tr('Facture','الفاتورة')).pack(side="left")
        ttk.Button(top,text=self.tr('Commandes ouvertes','الطلبات المفتوحة'),style='Soft.TButton',command=self.orders_window).pack(side='right',padx=4)
        body=ttk.Panedwindow(self,orient="horizontal");body.pack(fill="both",expand=True,pady=8)
        p=ttk.Frame(body);body.add(p,weight=2)
        self.q=tk.StringVar();e=ttk.Entry(p,textvariable=self.q,style='Search.TEntry');e.pack(fill='x',pady=4);e.bind("<KeyRelease>",lambda x:self.search())
        self.prod=ttk.Treeview(p,columns=("id","name","stock","cost"),show="headings")
        for c,h,w in [("id","ID",50),("name",self.tr("Article","المنتوج"),240),("stock",self.tr("Stock","المخزون"),80),("cost",self.tr("Achat","الشراء"),80)]:self.prod.heading(c,text=h);self.prod.column(c,width=w,anchor="center")
        self.prod.pack(fill="both",expand=True);self.prod.bind("<Double-1>",lambda e=None:self.addline());self.prod.bind("<Return>",lambda e=None:self.addline());self.search()
        r=ttk.Frame(body);body.add(r,weight=3)
        ttk.Button(r,text=self.tr('✓  VALIDER réception','✓  تأكيد المشتريات'),style='Success.TButton',command=self.save).pack(side='bottom',fill='x',pady=6,ipady=6)
        ttk.Button(r,text=self.tr('Enregistrer commande','حفظ الطلب'),style='Primary.TButton',command=self.save_order).pack(side='bottom',fill='x',pady=(0,4),ipady=4)
        self.lines_t=ttk.Treeview(r,columns=("name","qty","cost","total"),show="headings")
        for c,h,w in [("name",self.tr("Article","المنتوج"),230),("qty",self.tr("Qté","الكمية"),80),("cost",self.tr("Coût","التكلفة"),90),("total",self.tr("Total","المجموع"),100)]:self.lines_t.heading(c,text=h);self.lines_t.column(c,width=w,anchor="center")
        self.lines_t.pack(fill="both",expand=True)
        line_actions=ttk.Frame(r);line_actions.pack(fill="x",pady=4)
        ttk.Button(line_actions,text=self.tr('Modifier ligne','تعديل السطر'),command=self.edit_line).pack(side="left")
        ttk.Button(line_actions,text=self.tr('Supprimer ligne','حذف السطر'),style='Danger.TButton',command=self.remove_line).pack(side='left',padx=6)
        self.total_label=ttk.Label(line_actions,text=self.tr("Total : 0.00 DH","المجموع: 0.00 DH"),font=("Segoe UI",12,"bold"));self.total_label.pack(side="right")
        self.paid=tk.StringVar(value="0")
        ttk.Entry(line_actions,textvariable=self.paid,width=10).pack(side="right",padx=5)
        self.payment_method=tk.StringVar(value='CASH')
        ttk.Combobox(line_actions,textvariable=self.payment_method,values=('CASH','CARD'),state='readonly',width=7).pack(side='right',padx=5)
        ttk.Label(line_actions,text=self.tr("Payé maintenant (DH)","المؤدى الآن (درهم)")).pack(side="right")
        self._load_pending_reorder()
    def _load_pending_reorder(self):
        if self.app is None:return
        draft=getattr(self.app,'pending_purchase_draft',None)
        if not draft:return
        self.app.pending_purchase_draft=None
        supplier_id=draft.get('supplier_id')
        if supplier_id:
            try:self.refresh_suppliers(supplier_id)
            except (ValueError,StopIteration):pass
        self.lines=[dict(product_id=int(x['product_id']),name=x['name'],qty=float(x['qty']),
                         unit_cost_cents=int(x['unit_cost_cents'])) for x in draft.get('lines',[]) if float(x['qty'])>0]
        self.refresh_lines()

    def refresh_suppliers(self, selected=None):
        self.suppliers=list_suppliers()
        self.supplier_choice['values']=[f"{r['name']} · #{r['id']}" for r in self.suppliers]
        if selected is not None:
            index=next(i for i,r in enumerate(self.suppliers) if r['id']==selected)
            self.supplier_choice.current(index)
            self.supplier_id=selected

    def select_supplier(self, event=None):
        index=self.supplier_choice.current()
        self.supplier_id=self.suppliers[index]['id'] if index>=0 else None

    def search(self):
        q=f"%{self.q.get().strip()}%"
        with connect() as c:r=c.execute("SELECT id,name,stock_qty,purchase_price_cents FROM products WHERE active=1 AND name LIKE ? ORDER BY name LIMIT 100",(q,)).fetchall()
        self.prod.delete(*self.prod.get_children())
        for x in r:self.prod.insert("", "end",values=(x["id"],x["name"],f"{x['stock_qty']:g}",f"{x['purchase_price_cents']/100:.2f}"))
    def addline(self):
        s=self.prod.selection()
        if not s:return
        vals=self.prod.item(s[0],"values");pid=int(vals[0]);name=vals[1]
        qty=simpledialog.askfloat(self.tr("Qté","الكمية"),f"{name}\\n{self.tr('Quantité reçue:','الكمية المستلمة:')}",parent=self,minvalue=0.001)
        if qty is None:return
        cost=simpledialog.askfloat(self.tr("Coût","التكلفة"),f"{self.tr('Prix achat unitaire','ثمن الشراء للوحدة')} {name}:",parent=self,minvalue=0)
        if cost is None:return
        self.lines.append(dict(product_id=pid,name=name,qty=qty,unit_cost_cents=to_cents(cost)));self.refresh_lines()
    def refresh_lines(self):
        self.lines_t.delete(*self.lines_t.get_children())
        total=0
        for x in self.lines:
            line_total=round(x["qty"]*x["unit_cost_cents"]);total+=line_total
            self.lines_t.insert("", "end",values=(x["name"],f"{x['qty']:g}",fmt(x["unit_cost_cents"],""),fmt(line_total,"")))
        self.total_label.configure(text=f"{self.tr('Total','المجموع')} : {fmt(total)}")
    def _selected_line_index(self):
        sel=self.lines_t.selection()
        if not sel:return None
        return self.lines_t.index(sel[0])
    def edit_line(self):
        i=self._selected_line_index()
        if i is None:return
        x=self.lines[i]
        qty=simpledialog.askfloat(self.tr("Qté","الكمية"),f"{x['name']}\\n{self.tr('Quantité reçue:','الكمية المستلمة:')}",initialvalue=x['qty'],parent=self,minvalue=0.001)
        if qty is None:return
        cost=simpledialog.askfloat(self.tr("Coût","التكلفة"),f"{self.tr('Prix achat unitaire','ثمن الشراء للوحدة')} {x['name']}:",initialvalue=x['unit_cost_cents']/100,parent=self,minvalue=0)
        if cost is None:return
        x['qty']=qty;x['unit_cost_cents']=to_cents(cost);self.refresh_lines()
    def remove_line(self):
        i=self._selected_line_index()
        if i is None:return
        del self.lines[i];self.refresh_lines()
    def save_order(self):
        if not self.lines or not self.supplier_id:
            messagebox.showinfo('ToDo',self.tr('Choisissez un fournisseur et ajoutez des articles.','اختر مورداً وأضف المنتجات.'),parent=self);return
        try:
            oid=create_purchase_order(self.supplier_id,self.lines)
            messagebox.showinfo('ToDo',self.tr(f'Commande #{oid} enregistrée sans modifier le stock.',f'تم حفظ الطلب #{oid} دون تغيير المخزون.'),parent=self)
            self.lines=[];self.refresh_lines()
        except Exception as e:messagebox.showerror('ToDo',str(e),parent=self)

    def orders_window(self):
        w=tk.Toplevel(self);w.title(self.tr('Commandes fournisseurs','طلبات الموردين'));w.geometry('900x560');w.transient(self)
        tree=ttk.Treeview(w,columns=('id','supplier','date','lines','total'),show='headings')
        for key,label,width in [('id','ID',60),('supplier',self.tr('Fournisseur','المورد'),220),('date',self.tr('Date','التاريخ'),150),('lines',self.tr('Lignes','السطور'),80),('total',self.tr('Total estimé','المجموع المقدر'),120)]:
            tree.heading(key,text=label);tree.column(key,width=width,anchor='center')
        tree.pack(fill='both',expand=True,padx=12,pady=12)
        def load():
            tree.delete(*tree.get_children())
            for r in list_purchase_orders('OPEN'):
                tree.insert('','end',iid=str(r['id']),values=(r['id'],r['supplier_name'],r['created_at'],r['lines'],fmt(int(r['total_cents']),'')))
        def receive():
            sel=tree.selection()
            if not sel:return
            oid=int(sel[0]); orders={r['id']:r for r in list_purchase_orders('OPEN')}; order=orders.get(oid)
            if not order:return
            self.refresh_suppliers(order['supplier_id'])
            self.lines=[dict(product_id=r['product_id'],name=r['name'],qty=r['qty'],unit_cost_cents=r['unit_cost_cents']) for r in purchase_order_lines(oid)]
            self.refresh_lines();self._pending_order_id=oid;w.destroy()
        def cancel():
            sel=tree.selection()
            if not sel:return
            try:cancel_purchase_order(int(sel[0]));load()
            except Exception as e:messagebox.showerror('ToDo',str(e),parent=w)
        buttons=ttk.Frame(w);buttons.pack(fill='x',padx=12,pady=(0,12))
        ttk.Button(buttons,text=self.tr('Charger pour réception','تحميل للاستلام'),style='Primary.TButton',command=receive).pack(side='left')
        ttk.Button(buttons,text=self.tr('Annuler commande','إلغاء الطلب'),style='Danger.TButton',command=cancel).pack(side='left',padx=6)
        load()

    def save(self):
        if not self.lines:return
        supplier_id=self.supplier_id
        sname=self.supplier.get().strip()
        try:
            if sname and supplier_id is None:
                with connect() as c:
                    rows=c.execute("SELECT id FROM suppliers WHERE name=? AND active=1",(sname,)).fetchall()
                if len(rows)>1:
                    raise ValueError(self.tr('Plusieurs fournisseurs portent ce nom. Choisissez dans la liste.','يوجد أكثر من مورد بهذا الاسم. اختر من اللائحة.'))
                supplier_id=rows[0]['id'] if rows else save_supplier(sname)
                self.refresh_suppliers(supplier_id)
            paid=to_cents(self.paid.get() or "0")
            pid,total=receive_purchase(supplier_id,self.invoice.get().strip(),self.lines,paid_cents=paid,payment_method=self.payment_method.get())
            order_id=getattr(self,'_pending_order_id',None)
            if order_id:
                mark_purchase_order_received(order_id);self._pending_order_id=None
            messagebox.showinfo("ToDo",f"{self.tr('Réception','استلام')} #{pid}\\n{self.tr('Total','المجموع')}: {fmt(total)}",parent=self);self.lines=[];self.paid.set("0");self.refresh_lines();self.search()
        except Exception as e:messagebox.showerror("ToDo",str(e),parent=self)
