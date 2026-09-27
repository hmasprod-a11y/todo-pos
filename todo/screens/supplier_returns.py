import tkinter as tk
from tkinter import ttk,messagebox,simpledialog
from database import get_setting
from services.money import fmt
from services.suppliers import list_suppliers
from services.supplier_returns import supplier_purchase_invoices,purchase_returnable_lines,create_supplier_return,list_supplier_returns

class SupplierReturnsFrame(ttk.Frame):
    def __init__(self,master,app=None):
        super().__init__(master,padding=16);self.app=app
        self.lang=get_setting('language','fr');self.tr=lambda fr,ar: ar if self.lang=='ar' else fr
        top=ttk.Frame(self);top.pack(fill='x',pady=(0,8))
        ttk.Label(top,text=self.tr('Retours fournisseurs','إرجاع السلع للمورد'),style='Title.TLabel').pack(side='left')
        ttk.Button(top,text=self.tr('+ Nouveau retour','+ إرجاع جديد'),style='Primary.TButton',command=self.new_return).pack(side='right')
        cols=('id','supplier','invoice','date','total','reason')
        self.tree=ttk.Treeview(self,columns=cols,show='headings',height=18)
        for k,h,w in [('id','ID',60),('supplier',self.tr('Fournisseur','المورد'),220),('invoice',self.tr('Facture','الفاتورة'),140),('date',self.tr('Date','التاريخ'),145),('total',self.tr('Avoir','قيمة الإرجاع'),110),('reason',self.tr('Raison','السبب'),260)]:
            self.tree.heading(k,text=h);self.tree.column(k,width=w,anchor='center' if k not in ('supplier','reason') else 'w')
        self.tree.pack(fill='both',expand=True)
        ttk.Button(self,text=self.tr('Actualiser','تحديث'),command=self.refresh).pack(anchor='w',pady=8)
        self.refresh()
    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for r in list_supplier_returns():
            self.tree.insert('','end',iid=str(r['id']),values=(r['id'],r['supplier_name'],r['supplier_invoice'],r['created_at'],fmt(r['total_cents'],''),r['reason']))
    def new_return(self):
        suppliers=list_suppliers()
        if not suppliers:return
        w=tk.Toplevel(self);w.title(self.tr('Nouveau retour fournisseur','إرجاع جديد للمورد'));w.geometry('920x620');w.transient(self.winfo_toplevel());w.grab_set()
        supplier_var=tk.StringVar();invoice_var=tk.StringVar();supplier_map={}
        supplier_labels=[f"{s['name']} · #{s['id']}" for s in suppliers]
        supplier=ttk.Combobox(w,textvariable=supplier_var,values=supplier_labels,state='readonly',width=36);supplier.pack(anchor='w',padx=12,pady=(12,4))
        invoice=ttk.Combobox(w,textvariable=invoice_var,state='readonly',width=45);invoice.pack(anchor='w',padx=12,pady=4)
        tree=ttk.Treeview(w,columns=('id','name','bought','returned','stock','cost','qty'),show='headings')
        for k,h,width in [('id','ID',55),('name',self.tr('Article','المنتوج'),260),('bought',self.tr('Acheté','المشترى'),80),('returned',self.tr('Déjà retourné','سبق إرجاعه'),95),('stock',self.tr('Stock','المخزون'),80),('cost',self.tr('Coût','التكلفة'),90),('qty',self.tr('Qté retour','كمية الإرجاع'),90)]:
            tree.heading(k,text=h);tree.column(k,width=width,anchor='center' if k!='name' else 'w')
        tree.pack(fill='both',expand=True,padx=12,pady=8)
        quantities={}
        invoice_map={}
        def load_invoices(event=None):
            idx=supplier.current()
            if idx<0:return
            sid=suppliers[idx]['id'];rows=supplier_purchase_invoices(sid)
            labels=[f"#{r['id']} · {r['supplier_invoice'] or self.tr('Sans facture','بدون فاتورة')} · {r['created_at'][:10]}" for r in rows]
            invoice['values']=labels;invoice_map.clear();invoice_map.update({labels[i]:rows[i] for i in range(len(rows))})
            invoice_var.set(labels[0] if labels else '');load_lines()
        def load_lines(event=None):
            tree.delete(*tree.get_children());quantities.clear()
            row=invoice_map.get(invoice_var.get())
            if not row:return
            for x in purchase_returnable_lines(row['id']):
                quantities[x['purchase_item_id']]=0
                tree.insert('','end',iid=str(x['purchase_item_id']),values=(x['purchase_item_id'],x['name'],f"{x['qty']:g}",f"{x['returned_qty']:g}",f"{x['stock_qty']:g}",fmt(x['unit_cost_cents'],''),'0'))
        def edit(event=None):
            sel=tree.selection()
            if not sel:return
            iid=sel[0];vals=tree.item(iid,'values')
            max_qty=min(float(vals[2])-float(vals[3]),float(vals[4]))
            qty=simpledialog.askfloat(self.tr('Quantité retour','كمية الإرجاع'),self.tr(f"Quantité à retourner — {vals[1]} :",f"الكمية المراد إرجاعها — {vals[1]}:"),parent=w,minvalue=0,maxvalue=max_qty)
            if qty is None:return
            quantities[int(iid)]=qty
            vals=list(vals);vals[6]=f"{qty:g}";tree.item(iid,values=vals)
        def save():
            row=invoice_map.get(invoice_var.get())
            if not row:return
            items=[(iid,qty) for iid,qty in quantities.items() if qty>0]
            reason=simpledialog.askstring(self.tr('Raison','السبب'),self.tr('Raison du retour:','سبب الإرجاع:'),parent=w)
            if not reason:return
            try:
                rid,total=create_supplier_return(row['id'],items,reason)
                messagebox.showinfo('ToDo',self.tr(f'Retour #{rid} enregistré · Avoir {fmt(total)}',f'تم تسجيل الإرجاع #{rid} · القيمة {fmt(total)}'),parent=w)
                w.destroy();self.refresh()
            except Exception as e:messagebox.showerror('ToDo',str(e),parent=w)
        supplier.bind('<<ComboboxSelected>>',load_invoices);invoice.bind('<<ComboboxSelected>>',load_lines);tree.bind('<Double-1>',edit);tree.bind('<Return>',edit)
        ttk.Button(w,text=self.tr('Enregistrer le retour','حفظ الإرجاع'),style='Success.TButton',command=save).pack(pady=(0,12))
        if supplier_labels:supplier.current(0);load_invoices()
