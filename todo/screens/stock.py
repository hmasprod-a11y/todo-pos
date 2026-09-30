import csv
import tkinter as tk
from tkinter import ttk,messagebox,simpledialog,filedialog
from database import connect, get_setting
from services.inventory import apply_stock_movement, stock_activity, reorder_list, stock_summary, stock_products

class StockFrame(ttk.Frame):
    def __init__(self,master,app=None):
        super().__init__(master,padding=16)
        self.lang=get_setting('language','fr');self.tr=lambda fr,ar,en=None: ar if self.lang=='ar' else (en if self.lang=='en' and en else fr)
        top=ttk.Frame(self);top.pack(fill="x",pady=(0,8))
        ttk.Label(top,text=self.tr('Stock','المخزون','Stock'),style="Title.TLabel").pack(side="left")
        ttk.Label(self,text=self.tr('Quantités, mouvements et inventaire — nom, prix et photo restent dans Articles.','الكميات والحركات والجرد — تعديل الاسم والثمن والصورة يبقى في المنتجات.','Quantities, movements and inventory — name, price and photo remain in Products.'),foreground="#475569").pack(anchor="w",pady=(0,8))
        ttk.Button(top,text=self.tr('Ajustement','تسوية المخزون','Adjust stock'),style="Primary.TButton",command=self.adjust).pack(side="right")
        ttk.Button(top,text=self.tr('Désactiver','تعطيل','Deactivate'),style='Danger.TButton',command=self.deactivate_selected).pack(side='right',padx=4)
        ttk.Button(top,text=self.tr('+ Nouveau','+ جديد','+ New'),style='Success.TButton',command=self.new_product).pack(side='right',padx=4)
        self.q=tk.StringVar();self.filter=tk.StringVar(value=self.tr('Tous','الكل'))
        self.search_entry=ttk.Entry(top,textvariable=self.q,width=22,style="Search.TEntry");self.search_entry.pack(side="left",padx=(20,8));self.search_entry.bind("<KeyRelease>",lambda e:self.refresh())
        box=ttk.Combobox(top,textvariable=self.filter,values=[self.tr('Tous','الكل'),self.tr('Alertes stock','تنبيهات المخزون','Stock alerts'),self.tr('Stock négatif','مخزون سالب','Negative stock')],state="readonly",width=14);box.pack(side="left");box.bind("<<ComboboxSelected>>",lambda e:self.refresh())
        with connect() as c:
            category_rows=c.execute("SELECT id,name FROM categories WHERE active=1 ORDER BY sort_order,name COLLATE NOCASE").fetchall()
        self.family_values=[(self.tr('Toutes familles','كل الفئات','All categories'),None)]+[(r['name'],r['id']) for r in category_rows]
        self.family_map={label:cid for label,cid in self.family_values}
        self.family=tk.StringVar(value=self.family_values[0][0])
        family_box=ttk.Combobox(top,textvariable=self.family,values=[label for label,_ in self.family_values],state='readonly',width=18)
        family_box.pack(side='left',padx=(6,0));family_box.bind('<<ComboboxSelected>>',lambda e:self.refresh())
        ttk.Button(top,text=self.tr('Réapprovisionnement','إعادة الطلب','Reorder'),style="Soft.TButton",command=self.reorder_window).pack(side="right",padx=8)
        ttk.Button(top,text=self.tr('Journal global','السجل العام','Global journal'),style="Soft.TButton",command=self.global_ledger).pack(side="right",padx=8)
        ttk.Button(top,text=self.tr('Historique','السجل','History'),style="Soft.TButton",command=self.ledger).pack(side="right",padx=8)
        if app is not None:
            ttk.Button(top,text=self.tr('Articles','المنتجات'),style="Soft.TButton",command=lambda: app.show("products")).pack(side="right",padx=8)
        cols=("code","name","family","purchase","sale","stock","alert","last")
        self.t=ttk.Treeview(self,columns=cols,show="headings",height=14)
        for c,h,w,anchor in [
            ("code",self.tr("Code","الكود","Code"),120,"center"),
            ("name",self.tr("Article","المنتوج","Product"),230,"w"),
            ("family",self.tr("Famille","الفئة","Category"),170,"w"),
            ("purchase",self.tr("PRIX_A","ثمن الشراء","BUY PRICE"),90,"e"),
            ("sale",self.tr("PRIX_V","ثمن البيع","SALE PRICE"),90,"e"),
            ("stock",self.tr("Stock","المخزون"),80,"e"),
            ("alert",self.tr("Alerte","التنبيه","Alert"),75,"e"),
            ("last",self.tr("Dernier mouvement","آخر حركة","Last movement"),210,"w"),
        ]:
            self.t.heading(c,text=h);self.t.column(c,width=w,anchor=anchor)
        self.t.pack(fill="both",expand=True)
        self.kpi=tk.Frame(self,bg="#F6F7FB");self.kpi.pack(fill="x",pady=(8,0))
        self.kpi_values=[]
        for title,bg in [(self.tr("Articles","المنتجات","Products"),"#2563EB"),(self.tr("Alertes","التنبيهات"),"#F59E0B"),(self.tr("Stock négatif","المخزون السالب"),"#DC2626"),(self.tr("Promotions actives","العروض النشطة","Active promotions"),"#BE185D"),(self.tr("Valeur achat","قيمة الشراء"),"#16A34A"),(self.tr("Valeur vente","قيمة البيع"),"#7C3AED")]:
            card=tk.Frame(self.kpi,bg=bg,height=62);card.pack(side="left",fill="x",expand=True,padx=3);card.pack_propagate(False)
            value=tk.Label(card,text="0",bg=bg,fg="white",font=("Segoe UI",15,"bold"));value.pack(anchor="w",padx=10,pady=(5,0));tk.Label(card,text=title,bg=bg,fg="white").pack(anchor="w",padx=10);self.kpi_values.append(value)
        self.refresh()
        self.after_idle(lambda: self.search_entry.focus_force() if self.search_entry.winfo_exists() else None)
    def _movement_label(self, value):
        labels={'ADJUSTMENT':self.tr('Ajustement','تسوية'),'OPENING':self.tr('Ouverture','رصيد افتتاحي'),'INVENTORY':self.tr('Inventaire','جرد'),'PURCHASE':self.tr('Réception','استلام'),'SALE':self.tr('Vente','بيع'),'RETURN':self.tr('Retour','إرجاع'),'OUT':self.tr('Sortie','إخراج')}
        return labels.get(value, value or '')

    def _ref_label(self, value):
        labels={'purchase':self.tr('Réception','استلام'),'sale':self.tr('Vente','بيع'),'return':self.tr('Retour','إرجاع'),'inventory':self.tr('Inventaire','جرد'),'import':self.tr('Import','استيراد'),'adjustment':self.tr('Ajustement','تسوية')}
        return labels.get((value or '').lower(), value or '')

    def refresh(self):
        status='all'
        if self.filter.get()==self.tr("Alertes stock","تنبيهات المخزون"):status='alerts'
        elif self.filter.get()==self.tr("Stock négatif","مخزون سالب"):status='negative'
        category_id=self.family_map.get(self.family.get()) if hasattr(self,'family_map') else None
        r=stock_products(self.q.get().strip(),category_id,status)
        summary=stock_summary()
        for label,value in zip(self.kpi_values,[
            summary['articles'],summary['alerts'],summary['negative'],summary['active_promotions'],
            f"{summary['purchase_value_cents']/100:.2f}",f"{summary['sale_value_cents']/100:.2f}"
        ]):label.config(text=str(value))
        self.t.delete(*self.t.get_children())
        for x in r:
            tags=('negative',) if x['stock_qty']<0 else (('alert',) if x['stock_qty']<=x['alert_qty'] else ())
            last=x["last"]
            if last:
                parts=last.split("|",2);last=f"{self._movement_label(parts[0])} {parts[1]} @ {parts[2]}" if len(parts)==3 else last
            self.t.insert("", "end",iid=str(x['id']),values=(
                x.get("code") or f"#{x['id']}",x["name"],x.get("families") or '—',
                f"{x['purchase_price_cents']/100:.2f}",f"{x['sale_price_cents']/100:.2f}",
                f"{x['stock_qty']:g}",f"{x['alert_qty']:g}",last
            ),tags=tags)
        self.t.tag_configure('negative',background='#FEE2E2',foreground='#991B1B');self.t.tag_configure('alert',background='#FEF3C7',foreground='#92400E')
    def new_product(self):
        from screens.products import ProductEditor
        ProductEditor(self,on_saved=self.refresh)

    def deactivate_selected(self):
        selection=self.t.selection()
        if not selection:return
        pid=int(selection[0])
        values=self.t.item(selection[0],'values')
        name=values[1] if len(values)>1 else f'#{pid}'
        if not messagebox.askyesno(
            self.tr('Désactiver article','تعطيل المنتوج'),
            self.tr(f"Désactiver « {name} » ? L'historique sera conservé.",f'تعطيل « {name} »؟ سيتم الاحتفاظ بالسجل.'),
            parent=self
        ):return
        try:
            from services.catalog import deactivate_product
            deactivate_product(pid);self.refresh()
        except Exception as error:messagebox.showerror('ToDo',str(error),parent=self)

    def adjust(self):
        s=self.t.selection()
        if not s:return
        pid=int(s[0]);q=simpledialog.askfloat(self.tr("Ajustement","تسوية المخزون"),self.tr("Variation (+/-):","التغيير (+/-):"),parent=self)
        if q is None or q==0:return
        note=simpledialog.askstring(self.tr("Ajustement","تسوية المخزون"),self.tr("Raison obligatoire:","السبب إجباري:"),parent=self) or ""
        if not note.strip():return
        try:
            with connect() as c:c.execute("BEGIN IMMEDIATE");apply_stock_movement(c,pid,q,"ADJUSTMENT",note=note);c.commit()
            self.refresh()
        except Exception as e:messagebox.showerror("ToDo",str(e),parent=self)

    def reorder_window(self):
        rows=reorder_list()
        w=tk.Toplevel(self);w.title(self.tr("Réapprovisionnement","إعادة الطلب"));w.geometry('1000x620');w.transient(self)
        ttk.Label(w,text=self.tr("Articles à commander — cible automatique = 2 × seuil d'alerte","منتجات لإعادة الطلب — الهدف التلقائي = ضعفي حد التنبيه"),
                  font=('Segoe UI',11,'bold')).pack(anchor='w',padx=12,pady=(12,4))
        tree=ttk.Treeview(w,columns=('name','supplier_name','sku','supplier','stock','alert','target','order','cost'),show='headings')
        for key,label,width,anchor_col in [
            ('name',self.tr('Article','المنتوج'),220,'w'),('supplier_name',self.tr('Fournisseur','المورد'),160,'w'),('sku','SKU',90,'center'),
            ('supplier',self.tr('Code fournisseur','كود المورد'),110,'center'),('stock',self.tr('Stock','المخزون','Stock'),70,'e'),
            ('alert',self.tr('Seuil','الحد'),80,'e'),('target',self.tr('Cible','الهدف'),80,'e'),
            ('order',self.tr('À commander','للطلب'),95,'e'),('cost',self.tr('Coût estimé','التكلفة المقدرة'),110,'e')]:
            tree.heading(key,text=label);tree.column(key,width=width,anchor=anchor_col)
        tree.pack(fill='both',expand=True,padx=12,pady=8)
        total=0
        for r in rows:
            total+=r['estimated_cost_cents']
            tree.insert('','end',values=(r['name'],r['preferred_supplier_name'] or self.tr('Non assigné','غير محدد'),r['sku'] or '',r['supplier_code'] or '',f"{r['stock_qty']:g}",
                f"{r['alert_qty']:g}",f"{r['target_qty']:g}",f"{r['suggested_qty']:g}",f"{r['estimated_cost_cents']/100:.2f}"))
        supplier_ids=sorted({int(r['preferred_supplier_id']) for r in rows if r.get('preferred_supplier_id')})
        suppliers={int(r['preferred_supplier_id']):r['preferred_supplier_name'] for r in rows if r.get('preferred_supplier_id')}
        footer=ttk.Frame(w);footer.pack(fill='x',padx=12,pady=(0,12))
        supplier_var=tk.StringVar()
        supplier_values=[f"{suppliers[sid]} · #{sid}" for sid in supplier_ids]
        if supplier_values:supplier_var.set(supplier_values[0])
        ttk.Label(footer,text=self.tr('Fournisseur','المورد')).pack(side='left',padx=(0,4))
        ttk.Combobox(footer,textvariable=supplier_var,values=supplier_values,state='readonly',width=24).pack(side='left',padx=(0,8))
        ttk.Label(footer,text=self.tr(f"Coût total estimé: {total/100:.2f} DH",f"إجمالي التكلفة المقدرة: {total/100:.2f} درهم"),
                  font=('Segoe UI',11,'bold')).pack(side='right')
        def export_csv():
            path=filedialog.asksaveasfilename(parent=w,defaultextension='.csv',filetypes=[('CSV','*.csv')],
                title=self.tr('Exporter la liste','تصدير اللائحة'))
            if not path:return
            with open(path,'w',newline='',encoding='utf-8-sig') as fh:
                wr=csv.writer(fh)
                wr.writerow(['Article','Fournisseur','SKU','Code fournisseur','Stock','Seuil','Cible','Quantité à commander','Coût estimé cents'])
                for r in rows:
                    wr.writerow([r['name'],r['preferred_supplier_name'],r['sku'],r['supplier_code'],r['stock_qty'],r['alert_qty'],r['target_qty'],r['suggested_qty'],r['estimated_cost_cents']])
            messagebox.showinfo('ToDo',self.tr('Liste exportée.','تم تصدير اللائحة.'),parent=w)
        ttk.Button(footer,text=self.tr('Exporter CSV','تصدير CSV'),style='Soft.TButton',command=export_csv).pack(side='left')
        def prepare_reception():
            if self.app is None:
                messagebox.showerror('ToDo',self.tr("Navigation indisponible.","التنقل غير متاح."),parent=w);return
            value=supplier_var.get().strip()
            if not value:
                messagebox.showinfo('ToDo',self.tr("Aucun fournisseur préféré assigné.","لا يوجد مورد مفضل محدد."),parent=w);return
            supplier_id=int(value.rsplit('#',1)[1])
            selected=[r for r in rows if r.get('preferred_supplier_id')==supplier_id and r['suggested_qty']>0]
            if not selected:return
            self.app.pending_purchase_draft={'supplier_id':supplier_id,'lines':[
                {'product_id':r['id'],'name':r['name'],'qty':r['suggested_qty'],'unit_cost_cents':r['purchase_price_cents']}
                for r in selected]}
            w.destroy();self.app.show('purchases')
        ttk.Button(footer,text=self.tr('Préparer réception','تحضير الاستلام'),style='Primary.TButton',command=prepare_reception).pack(side='left',padx=6)

    def global_ledger(self):
        w=tk.Toplevel(self);w.title(self.tr("Journal global du stock","السجل العام للمخزون"));w.geometry('1180x650');w.transient(self)
        tools=ttk.Frame(w);tools.pack(fill='x',padx=12,pady=(12,4))
        query=tk.StringVar();kind=tk.StringVar(value=self.tr('Tous','الكل'))
        ttk.Entry(tools,textvariable=query,width=30).pack(side='left')
        kinds=[self.tr('Tous','الكل'),'SALE','PURCHASE','RETURN','INVENTORY','ADJUSTMENT','OUT','OPENING']
        ttk.Combobox(tools,textvariable=kind,values=kinds,state='readonly',width=16).pack(side='left',padx=6)
        tree=ttk.Treeview(w,columns=('date','product','user','type','old','delta','new','document','reason'),show='headings')
        for key,label,width in [
            ('date',self.tr('Date','التاريخ'),145),('product',self.tr('Article','المنتوج'),220),
            ('user',self.tr('Utilisateur','المستخدم'),110),('type',self.tr('Type','النوع'),100),
            ('old',self.tr('Avant','قبل'),70),('delta',self.tr('Variation','التغيير'),75),
            ('new',self.tr('Après','بعد'),70),('document',self.tr('Document','الوثيقة'),120),
            ('reason',self.tr('Raison','السبب'),260)]:
            tree.heading(key,text=label);tree.column(key,width=width)
        tree.pack(fill='both',expand=True,padx=12,pady=(4,12))
        tree.tag_configure('out',foreground='#B91C1C');tree.tag_configure('in',foreground='#15803D')
        def load(*_):
            selected='' if kind.get()==self.tr('Tous','الكل') else kind.get()
            rows=stock_activity(query.get(),selected)
            tree.delete(*tree.get_children())
            for r in rows:
                ref=f"{self._ref_label(r['ref_type'])} #{r['ref_id'] or ''}".strip()
                tree.insert('','end',values=(r['created_at'],r['product_name'],r['username'] or self.tr('Historique','سجل'),
                    self._movement_label(r['movement_type']),r['old_qty'],r['qty_delta'],r['stock_after'],ref,r['note']),
                    tags=('out' if float(r['qty_delta'])<0 else 'in',))
        ttk.Button(tools,text=self.tr('Actualiser','تحديث'),command=load).pack(side='left')
        query.trace_add('write',load);kind.trace_add('write',load);load()

    def ledger(self):
        selection=self.t.selection()
        if not selection:return
        pid=int(selection[0])
        w=tk.Toplevel(self);w.title(self.tr("Historique des mouvements","سجل حركات المخزون"));w.geometry('1050x550');w.transient(self)
        tree=ttk.Treeview(w,columns=('date','user','type','old','delta','new','document','reason'),show='headings')
        for key,label,width in [('date',self.tr('Date','التاريخ'),145),('user',self.tr('Utilisateur','المستخدم'),100),('type',self.tr('Type','النوع'),100),('old',self.tr('Avant','قبل'),70),('delta',self.tr('Variation','التغيير'),70),('new',self.tr('Après','بعد'),70),('document',self.tr('Document','الوثيقة'),100),('reason',self.tr('Raison','السبب'),220)]:
            tree.heading(key,text=label);tree.column(key,width=width)
        tree.pack(fill='both',expand=True,padx=12,pady=12)
        with connect() as conn:
            rows=conn.execute("SELECT sm.*,u.display_name username FROM stock_movements sm LEFT JOIN users u ON u.id=sm.user_id WHERE product_id=? ORDER BY sm.id DESC",(pid,)).fetchall()
        for r in rows:
            tree.insert('','end',values=(r['created_at'],r['username'] or self.tr('Historique','سجل'),self._movement_label(r['movement_type']),r['old_qty'],r['qty_delta'],r['stock_after'],f"{self._ref_label(r['ref_type'])} #{r['ref_id'] or ''}",r['note']))
