import tkinter as tk
from tkinter import ttk,messagebox,simpledialog
from datetime import date,timedelta
from database import connect,get_setting
from services.money import fmt
from services.clients import list_clients
from services.quotations import create_quotation,list_quotations,quotation_lines,quotation_cart,cancel_quotation

class QuotationsFrame(ttk.Frame):
    def __init__(self,master,app=None):
        super().__init__(master,padding=16);self.app=app
        self.lang=get_setting('language','fr');self.tr=lambda fr,ar: ar if self.lang=='ar' else fr
        top=ttk.Frame(self);top.pack(fill='x',pady=(0,8))
        ttk.Label(top,text=self.tr('Devis','عروض الأسعار'),style='Title.TLabel').pack(side='left')
        ttk.Button(top,text=self.tr('+ Nouveau devis','+ عرض سعر جديد'),style='Primary.TButton',command=self.new_quote).pack(side='right')
        self.status=tk.StringVar(value='')
        ttk.Combobox(top,textvariable=self.status,values=('', 'OPEN','CONVERTED','CANCELLED'),state='readonly',width=14).pack(side='right',padx=8)
        self.status.trace_add('write',lambda *_:self.refresh())
        cols=('id','client','status','total','valid','date')
        self.tree=ttk.Treeview(self,columns=cols,show='headings',height=18)
        for k,h,w in [('id','ID',55),('client',self.tr('Client','الزبون'),240),('status',self.tr('Statut','الحالة'),90),
                      ('total',self.tr('Total','المجموع'),100),('valid',self.tr('Valable jusqu’au','صالح حتى'),110),('date',self.tr('Date','التاريخ'),145)]:
            self.tree.heading(k,text=h);self.tree.column(k,width=w,anchor='center' if k!='client' else 'w')
        self.tree.pack(fill='both',expand=True)
        bar=ttk.Frame(self);bar.pack(fill='x',pady=(8,0))
        ttk.Button(bar,text=self.tr('Charger en caisse','تحميل للكاشير'),style='Success.TButton',command=self.load_sale).pack(side='left')
        ttk.Button(bar,text=self.tr('Détails','التفاصيل'),command=self.details).pack(side='left',padx=6)
        ttk.Button(bar,text=self.tr('Annuler devis','إلغاء العرض'),style='Danger.TButton',command=self.cancel).pack(side='left')
        self.refresh()
    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        labels={'OPEN':self.tr('Ouvert','مفتوح'),'CONVERTED':self.tr('Converti','تحول لبيع'),'CANCELLED':self.tr('Annulé','ملغى')}
        for r in list_quotations(self.status.get()):
            self.tree.insert('','end',iid=str(r['id']),values=(r['id'],r['client_name'] or self.tr('Passage','عابر'),labels.get(r['status'],r['status']),fmt(r['total_cents'],''),r['valid_until'] or '—',r['created_at']))
    def _selected(self):
        s=self.tree.selection();return int(s[0]) if s else None
    def load_sale(self):
        qid=self._selected()
        if not qid or self.app is None:return
        try:
            payload=quotation_cart(qid);self.app.show('sale');self.app.current.load_quotation(payload)
        except Exception as e:messagebox.showerror('ToDo',str(e),parent=self)
    def cancel(self):
        qid=self._selected()
        if not qid:return
        try:cancel_quotation(qid);self.refresh()
        except Exception as e:messagebox.showerror('ToDo',str(e),parent=self)
    def details(self):
        qid=self._selected()
        if not qid:return
        w=tk.Toplevel(self);w.title(self.tr(f'Devis #{qid}',f'عرض السعر #{qid}'));w.geometry('700x460');w.transient(self.winfo_toplevel())
        tree=ttk.Treeview(w,columns=('name','qty','price','total'),show='headings')
        for k,h,width in [('name',self.tr('Article','المنتوج'),280),('qty',self.tr('Qté','الكمية'),80),('price',self.tr('Prix','الثمن'),100),('total',self.tr('Total','المجموع'),110)]:
            tree.heading(k,text=h);tree.column(k,width=width,anchor='center' if k!='name' else 'w')
        tree.pack(fill='both',expand=True,padx=12,pady=12)
        for r in quotation_lines(qid):tree.insert('','end',values=(r['name_snapshot'],f"{r['qty']:g}",fmt(r['unit_price_cents'],''),fmt(r['line_total_cents'],'')))
    def new_quote(self):
        clients=list_clients();w=tk.Toplevel(self);w.title(self.tr('Nouveau devis','عرض سعر جديد'));w.geometry('960x650');w.transient(self.winfo_toplevel());w.grab_set()
        client_var=tk.StringVar(value=self.tr('Passage','عابر'));client_labels=[self.tr('Passage','عابر')]+[f"{c['name']} · #{c['id']}" for c in clients]
        ttk.Combobox(w,textvariable=client_var,values=client_labels,state='readonly',width=38).pack(anchor='w',padx=12,pady=(12,4))
        valid=tk.StringVar(value=(date.today()+timedelta(days=7)).isoformat());ttk.Entry(w,textvariable=valid,width=18).pack(anchor='w',padx=12,pady=4)
        search=tk.StringVar();ttk.Entry(w,textvariable=search,width=36).pack(anchor='w',padx=12,pady=6)
        body=ttk.Panedwindow(w,orient='horizontal');body.pack(fill='both',expand=True,padx=12,pady=6)
        left=ttk.Frame(body);right=ttk.Frame(body);body.add(left,weight=2);body.add(right,weight=3)
        products=ttk.Treeview(left,columns=('id','name','price'),show='headings')
        for k,h,width in [('id','ID',50),('name',self.tr('Article','المنتوج'),230),('price',self.tr('Prix','الثمن'),90)]:products.heading(k,text=h);products.column(k,width=width)
        products.pack(fill='both',expand=True)
        quote=ttk.Treeview(right,columns=('name','qty','price','total'),show='headings')
        for k,h,width in [('name',self.tr('Article','المنتوج'),220),('qty',self.tr('Qté','الكمية'),70),('price',self.tr('Prix','الثمن'),90),('total',self.tr('Total','المجموع'),100)]:quote.heading(k,text=h);quote.column(k,width=width)
        quote.pack(fill='both',expand=True);lines=[]
        def search_products(*_):
            q=search.get().strip()
            with connect() as c:rows=c.execute("SELECT id,name,sale_price_cents FROM products WHERE active=1 AND (?='' OR instr(lower(name),lower(?))>0) ORDER BY name LIMIT 100",(q,q)).fetchall()
            products.delete(*products.get_children())
            for r in rows:products.insert('','end',iid=str(r['id']),values=(r['id'],r['name'],fmt(r['sale_price_cents'],'')))
        def redraw():
            quote.delete(*quote.get_children())
            for i,x in enumerate(lines):quote.insert('','end',iid=str(i),values=(x['name'],f"{x['qty']:g}",fmt(x['unit_price_cents'],''),fmt(round(x['qty']*x['unit_price_cents']),'')))
        def add(event=None):
            s=products.selection()
            if not s:return
            vals=products.item(s[0],'values');qty=simpledialog.askfloat(self.tr('Quantité','الكمية'),self.tr(f"Quantité — {vals[1]} :",f"الكمية — {vals[1]}:"),parent=w,minvalue=0.001)
            if qty is None:return
            price=simpledialog.askfloat(self.tr('Prix devis','ثمن العرض'),self.tr('Prix unitaire (DH):','ثمن الوحدة (درهم):'),parent=w,initialvalue=float(vals[2]),minvalue=0)
            if price is None:return
            lines.append(dict(product_id=int(vals[0]),name=vals[1],qty=qty,unit_price_cents=int(round(price*100))));redraw()
        def save():
            try:
                cid=None if client_var.get()==self.tr('Passage','عابر') else int(client_var.get().rsplit('#',1)[1])
                qid,total=create_quotation(lines,cid,valid.get() or None)
                messagebox.showinfo('ToDo',self.tr(f'Devis #{qid} enregistré · {fmt(total)}',f'تم حفظ عرض السعر #{qid} · {fmt(total)}'),parent=w);w.destroy();self.refresh()
            except Exception as ex:messagebox.showerror('ToDo',str(ex),parent=w)
        search.trace_add('write',search_products);products.bind('<Double-1>',add);products.bind('<Return>',add);search_products()
        ttk.Button(w,text=self.tr('Enregistrer devis','حفظ عرض السعر'),style='Success.TButton',command=save).pack(pady=(4,12))
