import tkinter as tk
from tkinter import ttk
from services.reports import today_summary
from services.money import fmt


MODULES = [
    ("Vente", "البيع", "Sales", "sale", "01", "#2563EB"),
    ("Stock", "المخزون", "Stock", "stock", "02", "#0891B2"),
    ("Journal", "السجل", "Journal", "journal", "03", "#7C3AED"),
    ("Gestion", "الإدارة", "Management", "management", "04", "#0F766E"),
    ("Paramètres", "الإعدادات", "Settings", "settings", "05", "#64748B"),
    ("Statistiques", "الإحصائيات", "Statistics", "statistics", "06", "#16A34A"),
]


class HomeFrame(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master, padding=0)
        self.app=app
        from database import get_setting
        self.lang=get_setting("language","fr")
        self.tr=lambda fr,ar,en=None: ar if self.lang=="ar" else (en if self.lang=="en" and en else fr)
        self._build()

    def _build(self):
        root=tk.Frame(self,bg="#F6F7FB")
        root.pack(fill="both",expand=True)

        header=tk.Frame(root,bg="#FFFFFF",height=116)
        header.pack(fill="x");header.pack_propagate(False)
        tk.Label(header,text=self.tr("Bonjour","مرحباً","Welcome"),bg="#FFFFFF",fg="#0F172A",
                 font=("Segoe UI",24,"bold")).pack(anchor="w",padx=34,pady=(23,0))
        tk.Label(header,text=self.tr("Choisissez un module pour commencer.","اختر وحدة للبدء.","Choose a module to get started."),
                 bg="#FFFFFF",fg="#64748B",font=("Segoe UI",10)).pack(anchor="w",padx=34,pady=(3,0))

        metrics=tk.Frame(root,bg="#F6F7FB")
        metrics.pack(fill="x",padx=34,pady=(22,10))
        try:
            s=today_summary()
            kpis=[
                (self.tr("Ventes aujourd’hui","مبيعات اليوم","Today's sales"),fmt(s["net_sales"])),
                (self.tr("Tickets","التذاكر","Receipts"),str(s["tickets"])),
                (self.tr("Marge brute","الهامش الإجمالي","Gross margin"),fmt(s["gross_margin"])),
                (self.tr("Alertes stock","تنبيهات المخزون","Stock alerts"),str(s["alerts"])),
            ]
        except Exception:
            kpis=[]
        for i,(label,value) in enumerate(kpis):
            card=tk.Frame(metrics,bg="#FFFFFF",highlightbackground="#E2E8F0",highlightthickness=1)
            card.grid(row=0,column=i,sticky="nsew",padx=(0 if i==0 else 8,0))
            metrics.grid_columnconfigure(i,weight=1)
            tk.Label(card,text=label.upper(),bg="#FFFFFF",fg="#64748B",font=("Segoe UI",8,"bold")).pack(anchor="w",padx=16,pady=(12,2))
            tk.Label(card,text=value,bg="#FFFFFF",fg="#0F172A",font=("Segoe UI",18,"bold")).pack(anchor="w",padx=16,pady=(0,12))

        workspace=tk.Frame(root,bg="#F6F7FB")
        workspace.pack(fill="both",expand=True,padx=34,pady=(10,30))
        tk.Label(workspace,text=self.tr("Modules","الوحدات","Modules"),bg="#F6F7FB",fg="#334155",
                 font=("Segoe UI",12,"bold")).grid(row=0,column=0,columnspan=3,sticky="w",pady=(0,10))
        for column in range(3):workspace.grid_columnconfigure(column,weight=1,uniform="module")

        for index,(fr,ar,en,key,number,color) in enumerate(MODULES):
            row=index//3+1;column=index%3
            card=tk.Frame(workspace,bg="#FFFFFF",highlightbackground="#E2E8F0",highlightthickness=1,cursor="hand2")
            card.grid(row=row,column=column,sticky="nsew",padx=(0 if column==0 else 10,0),pady=(0,10),ipadx=0,ipady=0)
            accent=tk.Frame(card,bg=color,height=5);accent.pack(fill="x")
            content=tk.Frame(card,bg="#FFFFFF");content.pack(fill="both",expand=True,padx=18,pady=16)
            badge=tk.Label(content,text=number,bg="#F1F5F9",fg=color,font=("Segoe UI",10,"bold"),width=4,pady=6)
            badge.pack(side="left",padx=(0,14))
            text=tk.Frame(content,bg="#FFFFFF");text.pack(side="left",fill="both",expand=True)
            tk.Label(text,text=self.tr(fr,ar,en),bg="#FFFFFF",fg="#0F172A",font=("Segoe UI",13,"bold")).pack(anchor="w")
            subtitles={
                "sale":self.tr("Encaisser et scanner","البيع والمسح","Scan and checkout"),
                "stock":self.tr("Articles et mouvements","المنتجات والحركات","Items and movements"),
                "journal":self.tr("Ventes et rapports","المبيعات والتقارير","Sales and reports"),
                "management":self.tr("Clients, fournisseurs, achats","الزبناء والموردون والمشتريات","Customers, suppliers, purchases"),
                "settings":self.tr("Appareils et configuration","الأجهزة والإعدادات","Devices and configuration"),
                "statistics":self.tr("Suivi de l’activité","متابعة النشاط","Business insights"),
            }
            tk.Label(text,text=subtitles[key],bg="#FFFFFF",fg="#64748B",font=("Segoe UI",9)).pack(anchor="w",pady=(3,0))
            arrow=tk.Label(content,text="›",bg="#FFFFFF",fg="#94A3B8",font=("Segoe UI",25))
            arrow.pack(side="right")
            def enter(event,box=card,accent_color=color):
                box.configure(highlightbackground=accent_color,highlightthickness=2)
            def leave(event,box=card):
                box.configure(highlightbackground="#E2E8F0",highlightthickness=1)
            def go(event=None,module=key):
                self.app.show(module)
            for widget in (card,accent,content,badge,text,arrow,*text.winfo_children()):
                widget.bind("<Button-1>",go);widget.bind("<Enter>",enter);widget.bind("<Leave>",leave)
