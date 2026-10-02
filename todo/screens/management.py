import tkinter as tk
from tkinter import ttk
from database import get_setting


SECTIONS = [
    ("Flux de stock", "حركة المخزون", "Stock workflow", [
        ("Réceptions", "purchases", "↓", "#0891B2"),
        ("Sorties", "sorties", "↑", "#D97706"),
        ("Promotions", "promotions", "%", "#7C3AED"),
        ("Inventaire", "inventory", "≡", "#16A34A"),
        ("Inventaires enregistrés", "inventory_sessions", "✓", "#0F766E"),
        ("Mouvements de stock", "stock", "↔", "#2563EB"),
    ]),
    ("Partenaires", "الشركاء", "Partners", [
        ("Fournisseurs", "suppliers", "F", "#EA580C"),
        ("Règlements fournisseurs", "supplier_payments", "€", "#EA580C"),
        ("Retours fournisseurs", "supplier_returns", "↩", "#B45309"),
        ("État crédits fournisseurs", "supplier_credits", "!", "#DC2626"),
    ]),
    ("Relation client", "الزبناء", "Customers", [
        ("Clients", "clients", "C", "#2563EB"),
        ("Règlements clients", "clients_payments", "€", "#16A34A"),
        ("État crédits clients", "clients_credits", "!", "#DC2626"),
        ("Fidélité clients", "loyalty", "★", "#A16207"),
        ("Commandes clients", "customer_orders", "□", "#0F766E"),
        ("Devis", "quotations", "≋", "#475569"),
    ]),
    ("Caisse et planning", "الصندوق والمواعيد", "Cash and scheduling", [
        ("Dépenses", "cash", "−", "#D97706"),
        ("Rendez-vous", "rendez_vous", "◷", "#0891B2"),
    ]),
]

LABELS = {
    "Réceptions": ("الاستلامات", "Receipts"), "Sorties": ("الإخراجات", "Stock out"),
    "Promotions": ("العروض", "Promotions"), "Inventaire": ("الجرد", "Inventory"),
    "Inventaires enregistrés": ("سجلات الجرد", "Saved inventories"), "Mouvements de stock": ("حركات المخزون", "Stock movements"),
    "Fournisseurs": ("الموردون", "Suppliers"), "Règlements fournisseurs": ("دفعات الموردين", "Supplier payments"),
    "Retours fournisseurs": ("إرجاع للمورد", "Supplier returns"), "État crédits fournisseurs": ("ديون الموردين", "Supplier credit status"),
    "Clients": ("الزبائن", "Customers"), "Règlements clients": ("دفعات الزبائن", "Customer payments"),
    "État crédits clients": ("ديون الزبائن", "Customer credit status"), "Fidélité clients": ("وفاء الزبائن", "Customer loyalty"),
    "Commandes clients": ("طلبات الزبائن", "Customer orders"), "Devis": ("عروض الأسعار", "Quotations"),
    "Dépenses": ("المصاريف", "Expenses"), "Rendez-vous": ("المواعيد", "Appointments"),
}


class ManagementFrame(ttk.Frame):
    """Structured access to management modules without visual overload."""

    def __init__(self, master, app):
        super().__init__(master, padding=0)
        self.app=app
        self.lang=get_setting("language","fr")
        self.tr=lambda fr,ar,en=None: ar if self.lang=="ar" else (en if self.lang=="en" and en else fr)
        self._build()

    def _build(self):
        root=tk.Frame(self,bg="#F6F7FB")
        root.pack(fill="both",expand=True)
        header=tk.Frame(root,bg="#FFFFFF",height=96)
        header.pack(fill="x");header.pack_propagate(False)
        tk.Label(header,text=self.tr("Gestion","الإدارة","Management"),bg="#FFFFFF",fg="#0F172A",
                 font=("Segoe UI",23,"bold")).pack(anchor="w",padx=30,pady=(19,0))
        tk.Label(header,text=self.tr("Stocks, partenaires et opérations commerciales.","المخزون والشركاء والعمليات التجارية.","Stock, partners and commercial operations."),
                 bg="#FFFFFF",fg="#64748B",font=("Segoe UI",10)).pack(anchor="w",padx=30,pady=(3,0))

        canvas=tk.Canvas(root,bg="#F6F7FB",highlightthickness=0)
        scroll=ttk.Scrollbar(root,orient="vertical",command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right",fill="y");canvas.pack(side="left",fill="both",expand=True)
        body=tk.Frame(canvas,bg="#F6F7FB")
        window=canvas.create_window((0,0),window=body,anchor="nw")
        body.bind("<Configure>",lambda e:canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",lambda e:canvas.itemconfigure(window,width=e.width))
        canvas.bind("<MouseWheel>",lambda e:canvas.yview_scroll(int(-e.delta/120),"units"))

        for fr,ar,en,items in SECTIONS:
            section=tk.Frame(body,bg="#F6F7FB")
            section.pack(fill="x",padx=30,pady=(18,0))
            tk.Label(section,text=self.tr(fr,ar,en),bg="#F6F7FB",fg="#334155",font=("Segoe UI",11,"bold")).pack(anchor="w",pady=(0,8))
            grid=tk.Frame(section,bg="#F6F7FB");grid.pack(fill="x")
            for col in range(3):grid.grid_columnconfigure(col,weight=1,uniform="management")
            for index,(label,key,symbol,color) in enumerate(items):
                self._card(grid,index//3,index%3,label,key,symbol,color)

    def _card(self,parent,row,column,label,key,symbol,color):
        card=tk.Frame(parent,bg="#FFFFFF",highlightbackground="#E2E8F0",highlightthickness=1,cursor="hand2")
        card.grid(row=row,column=column,sticky="ew",padx=(0 if column==0 else 10,0),pady=(0,10))
        accent=tk.Frame(card,bg=color,width=5);accent.pack(side="left",fill="y")
        content=tk.Frame(card,bg="#FFFFFF");content.pack(side="left",fill="both",expand=True,padx=14,pady=13)
        icon=tk.Label(content,text=symbol,bg="#F1F5F9",fg=color,font=("Segoe UI",15,"bold"),width=3,pady=4)
        icon.pack(side="left",padx=(0,11))
        text=tk.Frame(content,bg="#FFFFFF");text.pack(side="left",fill="both",expand=True)
        arabic,english=LABELS[label]
        tk.Label(text,text=self.tr(label,arabic,english),bg="#FFFFFF",fg="#0F172A",font=("Segoe UI",10,"bold"),
                 anchor="w").pack(fill="x")
        tk.Label(text,text=self.tr("Ouvrir le module","فتح الوحدة","Open module"),bg="#FFFFFF",fg="#64748B",
                 font=("Segoe UI",8),anchor="w").pack(fill="x",pady=(3,0))
        arrow=tk.Label(content,text="›",bg="#FFFFFF",fg="#94A3B8",font=("Segoe UI",21))
        arrow.pack(side="right")
        def enter(event):
            card.configure(highlightbackground=color,highlightthickness=2)
        def leave(event):
            card.configure(highlightbackground="#E2E8F0",highlightthickness=1)
        def open_module(event=None):
            self._activate(key)
        for widget in (card,accent,content,icon,text,arrow,*text.winfo_children()):
            widget.bind("<Button-1>",open_module);widget.bind("<Enter>",enter);widget.bind("<Leave>",leave)

    def _activate(self,key):
        if key=="clients_payments":
            self.app.show("clients");return
        if key=="clients_credits":
            from screens.clients import CreditStateWindow
            CreditStateWindow(self.app);return
        if key=="supplier_credits":
            from screens.supplier_payments import SupplierCreditStateWindow
            SupplierCreditStateWindow(self.app);return
        self.app.show(key)
        if key=="cash":
            try:self.app.current.expense()
            except Exception:pass
