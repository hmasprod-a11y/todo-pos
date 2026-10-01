import tkinter as tk
from tkinter import ttk,messagebox,simpledialog
from services.cash import get_open_session,open_session,close_session,session_totals,record_cash,cash_activity
from services.money import to_cents,fmt
from services.globalization import current_country_profile
from database import connect, get_setting

class CashFrame(ttk.Frame):
    def __init__(self,master,app):
        super().__init__(master,padding=15);self.app=app
        self.lang=get_setting('language','fr');self.currency=current_country_profile().currency;self.tr=lambda fr,ar,en=None: ar if self.lang=='ar' else (en if self.lang=='en' and en else fr)
        ttk.Label(self,text=self.tr('Caisse','الصندوق','Cash drawer'),style='Title.TLabel').pack(anchor='w',pady=(0,8))
        self.info=ttk.Label(self,text="",font=("Segoe UI",12));self.info.pack(anchor="w",pady=8)
        self.kpis=ttk.Frame(self);self.kpis.pack(fill="x",pady=8);self.kpi_labels={}
        for key,title in [("expected",self.tr("Cash attendu","النقد المتوقع","Expected cash")),("sales",self.tr("Ventes cash","المبيعات النقدية","Cash sales")),("card",self.tr("Ventes carte","مبيعات البطاقة","Card sales")),("expenses",self.tr("Dépenses","المصاريف","Expenses")),("returns",self.tr("Retours cash","المرتجعات النقدية","Cash returns"))]:
            card=ttk.LabelFrame(self.kpis,text=title,padding=8);card.pack(side="left",fill="x",expand=True,padx=3);lbl=ttk.Label(card,text="—",font=("Segoe UI",16,"bold"));lbl.pack();self.kpi_labels[key]=lbl
        b=ttk.Frame(self);b.pack(anchor="w",pady=8)
        ttk.Button(b,text=self.tr('Ouvrir caisse','فتح الصندوق','Open drawer'),style='Success.TButton',command=self.open).pack(side='left',padx=4)
        ttk.Button(b,text=self.tr('Dépense','مصروف','Expense'),style='Danger.TButton',command=self.expense).pack(side='left',padx=4)
        ttk.Button(b,text=self.tr('Cash IN','إدخال نقدي','Cash IN'),style='Soft.TButton',command=lambda:self.cashmove('IN')).pack(side='left',padx=4)
        ttk.Button(b,text=self.tr('Cash OUT','إخراج نقدي','Cash OUT'),style='Soft.TButton',command=lambda:self.cashmove('OUT')).pack(side='left',padx=4)
        if get_setting('closure_enabled','1')=='1':
            ttk.Button(b,text=self.tr('Clôturer','إغلاق الصندوق','Close drawer'),style='Primary.TButton',command=self.close).pack(side='left',padx=4)
        ttk.Button(b,text=self.tr('Journal caisse','سجل الصندوق','Cash journal'),style='Soft.TButton',command=self.cash_journal).pack(side='left',padx=4)
        ttk.Button(b,text=self.tr('Historique clôtures','سجل الإغلاقات','Closure history'),style='Soft.TButton',command=self.history).pack(side='left',padx=4)
        self.details=tk.Text(self,height=16,font=("Consolas",11));self.details.pack(fill="x",pady=15);self.refresh()
    def refresh(self):
        s=get_open_session();self.details.config(state="normal");self.details.delete("1.0","end")
        if not s:
            self.info.config(text=self.tr('Aucune caisse ouverte','لا يوجد صندوق مفتوح','No open cash drawer'))
            for lbl in self.kpi_labels.values():lbl.config(text="—")
            self.details.config(state="disabled");return
        with connect() as c:t=session_totals(c,s["id"])
        expected=int(s["opening_cash_cents"])+t["cash_sales"]-t["cash_returns"]-t["expenses"]+t["cash_in"]-t["cash_out"]
        self.kpi_labels["expected"].config(text=fmt(expected));self.kpi_labels["sales"].config(text=fmt(t["cash_sales"]));self.kpi_labels["card"].config(text=fmt(t["card_sales"]));self.kpi_labels["expenses"].config(text=fmt(t["expenses"]));self.kpi_labels["returns"].config(text=fmt(t["cash_returns"]))
        self.info.config(text=self.tr(f"Caisse #{s['id']} ouverte depuis {s['opened_at']}",f"الصندوق #{s['id']} مفتوح منذ {s['opened_at']}",f"Cash drawer #{s['id']} open since {s['opened_at']}"))
        txt=self.tr(f"""Fond de caisse : {fmt(s['opening_cash_cents'])}
Ventes cash    : {fmt(t['cash_sales'])}
Ventes carte   : {fmt(t['card_sales'])}
Retours cash   : {fmt(t['cash_returns'])}
Dépenses       : {fmt(t['expenses'])}
Cash IN        : {fmt(t['cash_in'])}
Cash OUT       : {fmt(t['cash_out'])}
""",f"""رصيد الافتتاح : {fmt(s['opening_cash_cents'])}
المبيعات النقدية : {fmt(t['cash_sales'])}
مبيعات البطاقة : {fmt(t['card_sales'])}
المرتجعات النقدية : {fmt(t['cash_returns'])}
المصاريف : {fmt(t['expenses'])}
إدخال نقدي : {fmt(t['cash_in'])}
إخراج نقدي : {fmt(t['cash_out'])}
""",f"""Opening cash : {fmt(s['opening_cash_cents'])}
Cash sales    : {fmt(t['cash_sales'])}
Card sales    : {fmt(t['card_sales'])}
Cash returns  : {fmt(t['cash_returns'])}
Expenses      : {fmt(t['expenses'])}
Cash IN       : {fmt(t['cash_in'])}
Cash OUT      : {fmt(t['cash_out'])}
""")
        self.details.insert("1.0",txt);self.details.config(state="disabled")
    def open(self):
        v=simpledialog.askfloat(self.tr("Ouverture","فتح الصندوق","Open cash drawer"),self.tr(f"Fond de caisse ({self.currency}):",f"رصيد الافتتاح ({self.currency}):",f"Opening cash ({self.currency}):"),parent=self,minvalue=0)
        if v is None:return
        try:open_session(self.app.user["id"],to_cents(v));self.refresh()
        except Exception as e:messagebox.showerror("ToDo",str(e),parent=self)
    def expense(self):
        s=get_open_session()
        if not s:messagebox.showerror("ToDo",self.tr("Ouvrez la caisse.","افتح الصندوق أولاً.","Open the cash drawer first."),parent=self);return
        label=simpledialog.askstring(self.tr("Dépense","مصروف","Expense"),self.tr("Libellé:","البيان:","Description:"),parent=self)
        if not label:return
        amount=simpledialog.askfloat(self.tr("Dépense","مصروف","Expense"),self.tr(f"Montant ({self.currency}):",f"المبلغ ({self.currency}):",f"Amount ({self.currency}):"),parent=self,minvalue=0.01)
        if amount is None:return
        try:record_cash(s['id'],self.app.user['id'],to_cents(amount),'EXPENSE',label)
        except Exception as e:messagebox.showerror('ToDo',str(e),parent=self);return
        self.refresh()
    def cashmove(self,typ):
        s=get_open_session()
        if not s:return
        amount=simpledialog.askfloat(typ,self.tr(f"Montant ({self.currency}):",f"المبلغ ({self.currency}):",f"Amount ({self.currency}):"),parent=self,minvalue=0.01)
        if amount is None:return
        note=simpledialog.askstring(typ,self.tr("Note:","ملاحظة:","Note:"),parent=self) or ""
        try:record_cash(s['id'],self.app.user['id'],to_cents(amount),typ,note)
        except Exception as e:messagebox.showerror('ToDo',str(e),parent=self);return
        self.refresh()
    def cash_journal(self):
        s=get_open_session()
        if not s:
            messagebox.showinfo('ToDo',self.tr('Aucune caisse ouverte','لا يوجد صندوق مفتوح','No open cash drawer'),parent=self);return
        rows=cash_activity(s['id'])
        w=tk.Toplevel(self);w.title(self.tr('Journal de caisse','سجل الصندوق','Cash journal'));w.geometry('900x560');w.transient(self.winfo_toplevel())
        tree=ttk.Treeview(w,columns=('time','doc','type','amount','note'),show='headings')
        for key,label,width,anchor in [
            ('time',self.tr('Date','التاريخ','Date'),150,'center'),('doc',self.tr('Document','الوثيقة','Document'),140,'center'),
            ('type',self.tr('Type','النوع','Type'),150,'center'),('amount',self.tr('Mouvement cash','حركة النقد','Cash movement'),120,'e'),
            ('note',self.tr('Détail','التفصيل','Details'),280,'w')]:
            tree.heading(key,text=label);tree.column(key,width=width,anchor=anchor)
        tree.tag_configure('out',foreground='#DC2626');tree.tag_configure('in',foreground='#15803D')
        tree.pack(fill='both',expand=True,padx=12,pady=12)
        labels={'SALE':self.tr('Vente cash','بيع نقدي','Cash sale'),'CREDIT_DEPOSIT':self.tr('Acompte crédit','تسبيق دين','Credit deposit'),
                'RETURN':self.tr('Retour cash','مرتجع نقدي','Cash return'),'EXPENSE':self.tr('Dépense','مصروف','Expense'),
                'CASH_IN':self.tr('Cash IN','إدخال نقدي','Cash IN'),'CASH_OUT':self.tr('Cash OUT','إخراج نقدي','Cash OUT'),
                'CLIENT_PAYMENT':self.tr('Règlement client','تسديد زبون','Customer payment'),'SUPPLIER_PAYMENT':self.tr('Règlement fournisseur','تسديد مورد','Supplier payment')}
        net=0
        for r in rows:
            amount=int(r['amount_cents']);net+=amount
            tree.insert('','end',values=(r['created_at'],r['document'],labels.get(r['kind'],r['kind']),fmt(amount,''),r['note'] or ''),
                        tags=('in' if amount>=0 else 'out',))
        ttk.Label(w,text=self.tr(f'Mouvement net hors fond de caisse: {fmt(net)}',f'صافي حركة النقد دون رصيد الافتتاح: {fmt(net)}',f'Net movement excluding opening cash: {fmt(net)}'),
                  font=('Segoe UI',11,'bold')).pack(anchor='e',padx=12,pady=(0,12))

    def history(self):
        w=tk.Toplevel(self);w.title(self.tr('Historique des clôtures','سجل إغلاقات الصندوق','Closure history'));w.geometry("1050x560");w.transient(self.winfo_toplevel())
        cols=("id","opened_by","closed_by","opened","closed","opening","expected","actual","diff")
        tree=ttk.Treeview(w,columns=cols,show="headings")
        cfg=[
            ("id",self.tr("Caisse","الصندوق","Cash drawer"),60),
            ("opened_by",self.tr("Ouvert par","فتح بواسطة","Opened by"),120),
            ("closed_by",self.tr("Clôturé par","أغلق بواسطة","Closed by"),120),
            ("opened",self.tr("Ouverture","الفتح","Opened"),135),
            ("closed",self.tr("Clôture","الإغلاق","Closed"),135),
            ("opening",self.tr("Fond","الرصيد","Opening"),85),
            ("expected",self.tr("Attendu","المتوقع","Expected"),85),
            ("actual",self.tr("Réel","الفعلي","Actual"),85),
            ("diff",self.tr("Écart","الفرق","Difference"),85)
        ]
        for key,title,width in cfg:tree.heading(key,text=title);tree.column(key,width=width,anchor="center")
        tree.tag_configure("bad",foreground="#DC2626");tree.tag_configure("ok",foreground="#15803D")
        tree.pack(fill="both",expand=True,padx=12,pady=12)
        with connect() as c:
            rows=c.execute("""SELECT cs.*,
                       COALESCE(open_u.display_name,'?') opened_by_name,
                       COALESCE(close_u.display_name,open_u.display_name,'?') closed_by_name
                FROM cash_sessions cs
                LEFT JOIN users open_u ON open_u.id=cs.user_id
                LEFT JOIN users close_u ON close_u.id=cs.closed_by_user_id
                WHERE cs.status='CLOSED'
                ORDER BY cs.id DESC LIMIT 1000""").fetchall()
        total_diff=0
        for r in rows:
            diff=int(r["difference_cents"] or 0);total_diff+=diff;tag="ok" if diff==0 else "bad"
            tree.insert("","end",values=(
                r["id"],r["opened_by_name"],r["closed_by_name"],r["opened_at"],r["closed_at"],
                fmt(r["opening_cash_cents"],""),fmt(r["expected_cash_cents"],""),
                fmt(r["actual_cash_cents"] or 0,""),fmt(diff,"")
            ),tags=(tag,))
        ttk.Label(w,text=self.tr(f"{len(rows)} clôture(s) · Écart cumulé {fmt(total_diff)}",f"{len(rows)} إغلاق · الفرق التراكمي {fmt(total_diff)}",f"{len(rows)} closure(s) · Cumulative difference {fmt(total_diff)}"),font=("Segoe UI",11,"bold")).pack(anchor="e",padx=12,pady=(0,12))

    def _open_close_cash(self, expected, on_closed=None):
        parent=self.winfo_toplevel()
        w=tk.Toplevel(self)
        w.title(self.tr('Comptage caisse','عدّ الصندوق','Cash count'))
        w.transient(parent)
        w.geometry('560x520')
        w.protocol('WM_DELETE_WINDOW',w.destroy)
        ttk.Label(w,text=self.tr('Cash attendu','النقد المتوقع','Expected cash'),font=('Segoe UI',11)).pack(pady=(16,2))
        ttk.Label(w,text=fmt(expected),font=('Segoe UI',24,'bold')).pack()
        counts={}
        summary=ttk.Label(w,text='',font=('Segoe UI',10));summary.pack(pady=6)
        total_label=ttk.Label(w,text=fmt(0),font=('Segoe UI',22,'bold'));total_label.pack(pady=4)
        grid=ttk.Frame(w);grid.pack(fill='x',padx=16,pady=8)
        values=(200,100,50,20,10,5,2,1,0.5)
        def refresh():
            cents=sum(to_cents(str(v))*n for v,n in counts.items())
            total_label.config(text=fmt(cents))
            summary.config(text=' · '.join(f'{v:g}×{n}' for v,n in counts.items() if n))
            return cents
        def add(v,delta=1):
            counts[v]=max(0,counts.get(v,0)+delta)
            refresh()
        for i,v in enumerate(values):
            box=ttk.Frame(grid);box.grid(row=i//3,column=i%3,sticky='nsew',padx=4,pady=4)
            ttk.Button(box,text=f'+ {v:g} {self.currency}',command=lambda x=v:add(x),width=13).pack(fill='x')
            ttk.Button(box,text=self.tr('Retirer','نقص','Remove')+f' {v:g}',command=lambda x=v:add(x,-1),width=13).pack(fill='x',pady=(2,0))
        for c in range(3):grid.columnconfigure(c,weight=1)
        def clear():
            counts.clear();refresh()
        def validate():
            actual_cents=refresh()
            try:
                exp,diff,_=close_session(get_open_session()['id'],actual_cents)
            except Exception as e:
                messagebox.showerror('ToDo',str(e),parent=w);return
            messagebox.showinfo(
                self.tr('Clôture','إغلاق الصندوق','Close drawer'),
                self.tr(
                    f'Attendu: {fmt(exp)}\nRéel: {fmt(actual_cents)}\nDifférence: {fmt(diff)}',
                    f'المتوقع: {fmt(exp)}\nالفعلي: {fmt(actual_cents)}\nالفرق: {fmt(diff)}',
                    f'Expected: {fmt(exp)}\nActual: {fmt(actual_cents)}\nDifference: {fmt(diff)}'
                ),
                parent=w
            )
            w.destroy()
            self.refresh()
            if on_closed:
                self.after_idle(on_closed)
        buttons=ttk.Frame(w);buttons.pack(side='bottom',fill='x',padx=16,pady=16)
        ttk.Button(buttons,text=self.tr('Effacer','مسح','Clear'),command=clear).pack(side='left')
        ttk.Button(buttons,text=self.tr('Annuler','إلغاء','Cancel'),command=w.destroy).pack(side='right',padx=6)
        ttk.Button(buttons,text=self.tr('Valider le comptage','تأكيد العد','Confirm count'),style='Primary.TButton',command=validate).pack(side='right')
        w.bind('<Escape>',lambda e:w.destroy())
        w.update_idletasks()
        x=max(0,parent.winfo_rootx()+(parent.winfo_width()-w.winfo_width())//2)
        y=max(0,parent.winfo_rooty()+(parent.winfo_height()-w.winfo_height())//2)
        w.geometry(f'+{x}+{y}')
        w.lift();w.focus_force()
        return w

    def close(self,on_closed=None):
        if get_setting('closure_enabled','1')!='1':
            messagebox.showinfo('ToDo',self.tr('La clôture est désactivée dans les paramètres.','إغلاق الصندوق معطل من الإعدادات.','Cash closure is disabled in settings.'),parent=self);return None
        s=get_open_session()
        if not s:return None
        with connect() as c:t=session_totals(c,s["id"])
        expected=int(s["opening_cash_cents"])+t["cash_sales"]-t["cash_returns"]-t["expenses"]+t["cash_in"]-t["cash_out"]
        return self._open_close_cash(expected,on_closed=on_closed)
