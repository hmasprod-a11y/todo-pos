import tkinter as tk
from tkinter import ttk,messagebox,simpledialog
from database import connect,get_setting
from services.money import to_cents,fmt
from services.promotions import list_promotions,save_promotion,set_promotion_active,delete_promotion

class PromotionsFrame(ttk.Frame):
    def __init__(self,master,app=None):
        super().__init__(master,padding=16);self.app=app
        self.lang=get_setting('language','fr');self.tr=lambda fr,ar: ar if self.lang=='ar' else fr
        top=ttk.Frame(self);top.pack(fill='x',pady=(0,8))
        ttk.Label(top,text=self.tr('Promotions','العروض'),style='Title.TLabel').pack(side='left')
        ttk.Button(top,text=self.tr('+ Nouvelle promotion','+ عرض جديد'),style='Primary.TButton',command=self.add).pack(side='right')
        self.q=tk.StringVar();entry=ttk.Entry(top,textvariable=self.q,width=30,style='Search.TEntry');entry.pack(side='left',padx=18)
        entry.bind('<KeyRelease>',lambda e:self.refresh())
        self.only_active=tk.BooleanVar(value=False)
        ttk.Checkbutton(top,text=self.tr('Actives seulement','النشطة فقط'),variable=self.only_active,command=self.refresh).pack(side='left')
        cols=('id','product','base','min','promo','mode','saving','active')
        self.tree=ttk.Treeview(self,columns=cols,show='headings',height=18)
        headers=[
            ('id','ID',55),('product',self.tr('Article','المنتوج'),280),('base',self.tr('Prix normal','الثمن العادي'),100),
            ('min',self.tr('Qté min','الحد الأدنى'),80),('promo',self.tr('Prix promo','ثمن العرض'),100),
            ('mode',self.tr('Mode','النوع'),90),('saving',self.tr('Économie/u','التوفير/وحدة'),100),
            ('active',self.tr('Actif','نشط'),70)]
        for k,h,w in headers:self.tree.heading(k,text=h);self.tree.column(k,width=w,anchor='center' if k!='product' else 'w')
        self.tree.pack(fill='both',expand=True)
        self.tree.bind('<Double-1>',lambda e:self.edit())
        bar=ttk.Frame(self);bar.pack(fill='x',pady=(8,0))
        ttk.Button(bar,text=self.tr('Modifier','تعديل'),command=self.edit).pack(side='left')
        ttk.Button(bar,text=self.tr('Activer / Désactiver','تفعيل / تعطيل'),command=self.toggle).pack(side='left',padx=6)
        ttk.Button(bar,text=self.tr('Supprimer','حذف'),style='Danger.TButton',command=self.delete).pack(side='left')
        self.summary=ttk.Label(bar,text='',font=('Segoe UI',10,'bold'));self.summary.pack(side='right')
        self.refresh()
    def refresh(self):
        rows=list_promotions(self.q.get(),self.only_active.get());self.tree.delete(*self.tree.get_children())
        active=0
        for r in rows:
            saving=max(0,int(r['sale_price_cents'])-int(r['unit_price_cents']));active+=1 if r['active'] else 0
            self.tree.insert('', 'end', iid=str(r['id']), values=(r['id'],r['product_name'],fmt(r['sale_price_cents'],''),
                f"{r['min_qty']:g}",fmt(r['unit_price_cents'],''),r['pricing_mode'],fmt(saving,''),self.tr('Oui','نعم') if r['active'] else self.tr('Non','لا')))
        self.summary.config(text=self.tr(f'{len(rows)} offre(s) · {active} active(s)',f'{len(rows)} عرض · {active} نشط'))
    def _selected(self):
        s=self.tree.selection()
        return int(s[0]) if s else None
    def _editor(self,promotion_id=None):
        current=None
        if promotion_id is not None:
            current=next((r for r in list_promotions() if r['id']==promotion_id),None)
            if not current:return
        with connect() as c:
            products=[dict(r) for r in c.execute("SELECT id,name,sale_price_cents FROM products WHERE active=1 ORDER BY name COLLATE NOCASE")]
        if not products:return
        w=tk.Toplevel(self);w.title(self.tr('Promotion','عرض'));w.geometry('500x340');w.transient(self.winfo_toplevel());w.grab_set()
        labels=[f"{p['name']} · #{p['id']}" for p in products]
        product=tk.StringVar();qty=tk.StringVar(value=f"{current['min_qty']:g}" if current else '2')
        price=tk.StringVar(value=f"{current['unit_price_cents']/100:.2f}" if current else '')
        mode=tk.StringVar(value=current['pricing_mode'] if current else 'UNIT')
        if current:
            idx=next((i for i,p in enumerate(products) if p['id']==current['product_id']),0);product.set(labels[idx])
        else:product.set(labels[0])
        form=ttk.Frame(w,padding=16);form.pack(fill='both',expand=True)
        for i,label in enumerate([self.tr('Article','المنتوج'),self.tr('Quantité minimale','الكمية الدنيا'),self.tr('Prix promotion/unité','ثمن العرض للوحدة'),self.tr('Mode','النوع')]):
            ttk.Label(form,text=label).grid(row=i,column=0,sticky='w',pady=8)
        ttk.Combobox(form,textvariable=product,values=labels,state='readonly',width=34).grid(row=0,column=1,sticky='ew')
        ttk.Entry(form,textvariable=qty).grid(row=1,column=1,sticky='ew')
        ttk.Entry(form,textvariable=price).grid(row=2,column=1,sticky='ew')
        ttk.Combobox(form,textvariable=mode,values=('UNIT','BUNDLE'),state='readonly').grid(row=3,column=1,sticky='ew')
        ttk.Label(form,text=self.tr('UNIT: prix/unité dès le seuil · BUNDLE: lots complets uniquement','UNIT: ثمن الوحدة ابتداء من الحد · BUNDLE: الحزم الكاملة فقط'),wraplength=440).grid(row=4,column=0,columnspan=2,sticky='w',pady=8)
        form.columnconfigure(1,weight=1)
        def save():
            try:
                pid=int(product.get().rsplit('#',1)[1]);save_promotion(pid,float(qty.get()),to_cents(price.get()),mode.get(),promotion_id)
                w.destroy();self.refresh()
            except Exception as e:messagebox.showerror('ToDo',str(e),parent=w)
        ttk.Button(form,text=self.tr('Enregistrer','حفظ'),style='Success.TButton',command=save).grid(row=5,column=1,sticky='e',pady=12)
    def add(self):self._editor()
    def edit(self):
        pid=self._selected()
        if pid:self._editor(pid)
    def toggle(self):
        pid=self._selected()
        if not pid:return
        row=next((r for r in list_promotions() if r['id']==pid),None)
        if row:set_promotion_active(pid,not bool(row['active']));self.refresh()
    def delete(self):
        pid=self._selected()
        if not pid:return
        if not messagebox.askyesno('ToDo',self.tr('Supprimer cette promotion ?','حذف هذا العرض؟'),parent=self):return
        try:delete_promotion(pid);self.refresh()
        except Exception as e:messagebox.showerror('ToDo',str(e),parent=self)
