import tkinter as tk
from tkinter import ttk,messagebox,simpledialog
from database import get_setting,set_setting
from services.money import fmt
from services.loyalty import loyalty_clients,loyalty_history,adjust_points,loyalty_settings

class LoyaltyFrame(ttk.Frame):
    def __init__(self,master,app=None):
        super().__init__(master,padding=16);self.app=app
        self.lang=get_setting('language','fr');self.currency=get_setting('currency','DH');self.tr=lambda fr,ar,en=None: ar if self.lang=='ar' else (en if self.lang=='en' and en else fr)
        top=ttk.Frame(self);top.pack(fill='x',pady=(0,8))
        ttk.Label(top,text=self.tr('Fidélité clients','وفاء الزبائن','Customer loyalty'),style='Title.TLabel').pack(side='left')
        ttk.Button(top,text=self.tr('Paramètres fidélité','إعدادات الوفاء','Loyalty settings'),style='Soft.TButton',command=self.settings).pack(side='right')
        self.q=tk.StringVar();entry=ttk.Entry(top,textvariable=self.q,width=32,style='Search.TEntry');entry.pack(side='left',padx=18)
        entry.bind('<KeyRelease>',lambda e:self.refresh())
        cols=('id','name','phone','points','value','sales')
        self.tree=ttk.Treeview(self,columns=cols,show='headings',height=18)
        cfg=[('id','ID',55),('name',self.tr('Client','الزبون','Customer'),240),('phone',self.tr('Téléphone','الهاتف','Phone'),130),
             ('points',self.tr('Points','النقاط','Points'),90),('value',self.tr('Valeur','القيمة','Value'),100),('sales',self.tr('Achats cumulés','مجموع المشتريات','Total purchases'),120)]
        for k,h,w in cfg:self.tree.heading(k,text=h);self.tree.column(k,width=w,anchor='center' if k!='name' else 'w')
        self.tree.pack(fill='both',expand=True);self.tree.bind('<Double-1>',lambda e:self.history())
        bar=ttk.Frame(self);bar.pack(fill='x',pady=(8,0))
        ttk.Button(bar,text=self.tr('+ Ajouter points','+ إضافة نقاط','+ Add points'),style='Success.TButton',command=lambda:self.adjust(1)).pack(side='left')
        ttk.Button(bar,text=self.tr('− Retirer points','− خصم نقاط','− Remove points'),style='Danger.TButton',command=lambda:self.adjust(-1)).pack(side='left',padx=6)
        ttk.Button(bar,text=self.tr('Historique','السجل','History'),command=self.history).pack(side='left')
        self.summary=ttk.Label(bar,text='',font=('Segoe UI',10,'bold'));self.summary.pack(side='right')
        self.refresh()
    def refresh(self):
        rows=loyalty_clients(self.q.get());settings=loyalty_settings();self.tree.delete(*self.tree.get_children())
        total=0
        for r in rows:
            total+=int(r['points'])
            self.tree.insert('','end',iid=str(r['id']),values=(r['id'],r['name'],r['phone'],r['points'],
                fmt(int(r['points'])*settings['point_value_cents'],''),fmt(int(r['sales_total_cents'] or 0),'')))
        self.summary.config(text=self.tr(f'{len(rows)} client(s) · {total} point(s)',f'{len(rows)} زبون · {total} نقطة'))
    def _selected(self):
        s=self.tree.selection();return int(s[0]) if s else None
    def adjust(self,direction):
        cid=self._selected()
        if not cid:return
        pts=simpledialog.askinteger(self.tr('Points','النقاط'),self.tr('Nombre de points:','عدد النقاط:','Number of points:'),parent=self,minvalue=1)
        if pts is None:return
        reason=simpledialog.askstring(self.tr('Raison','السبب','Reason'),self.tr('Raison obligatoire:','السبب إجباري:','Reason required:'),parent=self)
        if not reason:return
        try:adjust_points(cid,direction*pts,reason);self.refresh()
        except Exception as e:messagebox.showerror('ToDo',str(e),parent=self)
    def history(self):
        cid=self._selected()
        if not cid:return
        w=tk.Toplevel(self);w.title(self.tr('Historique fidélité','سجل الوفاء','Loyalty history'));w.geometry('760x500');w.transient(self.winfo_toplevel())
        tree=ttk.Treeview(w,columns=('date','points','reason','ref','user'),show='headings')
        for k,h,width in [('date',self.tr('Date','التاريخ','Date'),150),('points',self.tr('Points','النقاط'),90),('reason',self.tr('Raison','السبب'),250),('ref',self.tr('Référence','المرجع','Reference'),120),('user',self.tr('Utilisateur','المستخدم','User'),120)]:
            tree.heading(k,text=h);tree.column(k,width=width,anchor='center' if k!='reason' else 'w')
        tree.pack(fill='both',expand=True,padx=12,pady=12)
        tree.tag_configure('plus',foreground='#15803D');tree.tag_configure('minus',foreground='#DC2626')
        for r in loyalty_history(cid):
            ref=(r['ref_type'] or '')+(f" #{r['ref_id']}" if r['ref_id'] else '')
            tree.insert('','end',values=(r['created_at'],f"{r['points_delta']:+d}",r['reason'],ref,r['username']),tags=('plus' if r['points_delta']>0 else 'minus',))
    def settings(self):
        s=loyalty_settings();w=tk.Toplevel(self);w.title(self.tr('Paramètres fidélité','إعدادات الوفاء'));w.geometry('500x300');w.transient(self.winfo_toplevel());w.grab_set()
        enabled=tk.BooleanVar(value=s['enabled']);earn=tk.StringVar(value=f"{s['earn_every_cents']/100:.2f}");value=tk.StringVar(value=f"{s['point_value_cents']/100:.2f}")
        f=ttk.Frame(w,padding=18);f.pack(fill='both',expand=True)
        ttk.Checkbutton(f,text=self.tr('Activer la fidélité','تفعيل نظام الوفاء','Enable loyalty'),variable=enabled).grid(row=0,column=0,columnspan=2,sticky='w',pady=8)
        ttk.Label(f,text=self.tr(f'1 point tous les ({self.currency})',f'نقطة واحدة لكل ({self.currency})',f'1 point for every ({self.currency})')).grid(row=1,column=0,sticky='w',pady=8);ttk.Entry(f,textvariable=earn).grid(row=1,column=1,sticky='ew')
        ttk.Label(f,text=self.tr(f'Valeur de 1 point ({self.currency})',f'قيمة النقطة ({self.currency})',f'Value of 1 point ({self.currency})')).grid(row=2,column=0,sticky='w',pady=8);ttk.Entry(f,textvariable=value).grid(row=2,column=1,sticky='ew')
        f.columnconfigure(1,weight=1)
        def save():
            try:
                from services.money import to_cents
                earn_cents=to_cents(earn.get());value_cents=to_cents(value.get())
                if earn_cents<=0 or value_cents<=0:raise ValueError(self.tr('Valeurs invalides','قيم غير صالحة','Invalid values'))
                set_setting('loyalty_enabled','1' if enabled.get() else '0');set_setting('loyalty_earn_every_cents',earn_cents);set_setting('loyalty_point_value_cents',value_cents)
                w.destroy();self.refresh()
            except Exception as e:messagebox.showerror('ToDo',str(e),parent=w)
        ttk.Button(f,text=self.tr('Enregistrer','حفظ'),style='Primary.TButton',command=save).grid(row=3,column=1,sticky='e',pady=16)
