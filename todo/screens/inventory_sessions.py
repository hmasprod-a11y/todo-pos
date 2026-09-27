import tkinter as tk
from tkinter import ttk,messagebox,simpledialog
from database import get_setting
from services.money import fmt
from services.inventory_sessions import create_inventory_session,list_inventory_sessions,inventory_session_lines,set_inventory_count,finalize_inventory_session

class InventorySessionsFrame(ttk.Frame):
    def __init__(self,master,app=None):
        super().__init__(master,padding=16);self.app=app
        self.lang=get_setting('language','fr');self.tr=lambda fr,ar: ar if self.lang=='ar' else fr
        top=ttk.Frame(self);top.pack(fill='x',pady=(0,8))
        ttk.Label(top,text=self.tr('Inventaires enregistrés','الجرد المحفوظ'),style='Title.TLabel').pack(side='left')
        ttk.Button(top,text=self.tr('+ Nouvel inventaire','+ جرد جديد'),style='Primary.TButton',command=self.create).pack(side='right')
        ttk.Label(self,text=self.tr("Chaque inventaire conserve le stock théorique, le comptage réel et les écarts avant validation.",
                                    "كل جرد يحتفظ بالمخزون النظري والكمية المعدودة والفروقات قبل التأكيد."),foreground='#475569').pack(anchor='w',pady=(0,8))
        cols=('id','label','status','date','user','items','counted','qtydiff','valuediff')
        self.tree=ttk.Treeview(self,columns=cols,show='headings',height=18)
        cfg=[
            ('id','ID',55),('label',self.tr('Libellé','البيان'),180),('status',self.tr('Statut','الحالة'),90),
            ('date',self.tr('Date','التاريخ'),145),('user',self.tr('Créé par','أنشأه'),120),
            ('items',self.tr('Articles','المنتجات'),75),('counted',self.tr('Comptés','المعدودة'),75),
            ('qtydiff',self.tr('Écart Qté','فرق الكمية'),90),('valuediff',self.tr('Écart valeur','فرق القيمة'),110)]
        for k,h,w in cfg:self.tree.heading(k,text=h);self.tree.column(k,width=w,anchor='center' if k!='label' else 'w')
        self.tree.pack(fill='both',expand=True)
        self.tree.bind('<Double-1>',lambda e:self.open_selected())
        bar=ttk.Frame(self);bar.pack(fill='x',pady=(8,0))
        ttk.Button(bar,text=self.tr('Ouvrir','فتح'),command=self.open_selected).pack(side='left')
        ttk.Button(bar,text=self.tr('Valider','تأكيد'),style='Success.TButton',command=self.validate_selected).pack(side='left',padx=6)
        ttk.Button(bar,text=self.tr('Actualiser','تحديث'),command=self.refresh).pack(side='left')
        self.refresh()
    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for r in list_inventory_sessions():
            status=self.tr('Ouvert','مفتوح') if r['status']=='OPEN' else self.tr('Validé','مؤكد')
            self.tree.insert('','end',iid=str(r['id']),values=(r['id'],r['label'] or f"Inventaire #{r['id']}",status,r['created_at'],
                r['created_by_name'],r['items'],r['counted'] or 0,f"{float(r['qty_diff'] or 0):g}",fmt(int(round(r['value_diff_cents'] or 0)),'')))
    def _selected(self):
        s=self.tree.selection();return int(s[0]) if s else None
    def create(self):
        label=simpledialog.askstring(self.tr('Nouvel inventaire','جرد جديد'),self.tr('Libellé (optionnel):','البيان (اختياري):'),parent=self) or ''
        try:sid=create_inventory_session(label);self.refresh();self.open_session(sid)
        except Exception as e:messagebox.showerror('ToDo',str(e),parent=self)
    def open_selected(self):
        sid=self._selected()
        if sid:self.open_session(sid)
    def validate_selected(self):
        sid=self._selected()
        if not sid:return
        if not messagebox.askyesno('ToDo',self.tr('Valider définitivement cet inventaire et appliquer les écarts ?','تأكيد هذا الجرد نهائيا وتطبيق الفروقات؟'),parent=self):return
        try:
            n=finalize_inventory_session(sid);messagebox.showinfo('ToDo',self.tr(f'{n} article(s) ajusté(s).',f'تم تعديل {n} منتج.'),parent=self);self.refresh()
        except Exception as e:messagebox.showerror('ToDo',str(e),parent=self)
    def open_session(self,sid):
        sessions={r['id']:r for r in list_inventory_sessions()};session=sessions.get(sid)
        if not session:return
        w=tk.Toplevel(self);w.title(self.tr(f'Inventaire #{sid}',f'الجرد #{sid}'));w.geometry('980x620');w.transient(self.winfo_toplevel())
        top=ttk.Frame(w);top.pack(fill='x',padx=12,pady=12)
        q=tk.StringVar();entry=ttk.Entry(top,textvariable=q,width=32);entry.pack(side='left')
        ttk.Label(top,text=self.tr('Double-cliquez un article pour saisir la quantité comptée.','انقر مرتين على المنتج لإدخال الكمية المعدودة.')).pack(side='left',padx=12)
        tree=ttk.Treeview(w,columns=('id','name','theory','counted','diff','value'),show='headings')
        for k,h,width in [('id','ID',55),('name',self.tr('Article','المنتوج'),300),('theory',self.tr('Théorique','النظري'),95),('counted',self.tr('Compté','المعدود'),95),('diff',self.tr('Écart','الفرق'),90),('value',self.tr('Valeur écart','قيمة الفرق'),110)]:
            tree.heading(k,text=h);tree.column(k,width=width,anchor='center' if k!='name' else 'w')
        tree.pack(fill='both',expand=True,padx=12,pady=(0,12))
        tree.tag_configure('neg',foreground='#DC2626');tree.tag_configure('pos',foreground='#15803D')
        def load(*_):
            tree.delete(*tree.get_children())
            for r in inventory_session_lines(sid,q.get()):
                counted=r['counted_qty'];diff=0 if counted is None else float(counted)-float(r['theory_qty'])
                value=int(round(diff*int(r['unit_cost_cents'])))
                tree.insert('','end',iid=str(r['product_id']),values=(r['product_id'],r['product_name'],f"{r['theory_qty']:g}",
                    '—' if counted is None else f"{counted:g}",'—' if counted is None else f"{diff:+g}",fmt(value,'')),
                    tags=('neg' if diff<0 else 'pos' if diff>0 else '',))
        def edit(event=None):
            if session['status']!='OPEN':return
            sel=tree.selection()
            if not sel:return
            vals=tree.item(sel[0],'values');qty=simpledialog.askfloat(self.tr('Comptage','العد'),self.tr(f"Quantité comptée — {vals[1]} :",f"الكمية المعدودة — {vals[1]}:"),parent=w,minvalue=0)
            if qty is None:return
            try:set_inventory_count(sid,int(sel[0]),qty);load()
            except Exception as e:messagebox.showerror('ToDo',str(e),parent=w)
        tree.bind('<Double-1>',edit);tree.bind('<Return>',edit);q.trace_add('write',load);load()
