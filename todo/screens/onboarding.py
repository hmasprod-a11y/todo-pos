import tkinter as tk
from tkinter import ttk,messagebox
from country_profiles import PROFILES,get_country_profile
from services.globalization import select_country_profile
from services.onboarding import mark_complete
from database import set_setting,connect
from services.security import hash_pin

class FirstRunWizard(tk.Toplevel):
    """Minimal offline first-run setup before normal sign-in."""
    def __init__(self,master,on_done):
        super().__init__(master);self.on_done=on_done;self.transient(master);self.grab_set()
        self.title("ToDo POS — First setup");self.geometry("520x420");self.resizable(False,False)
        self.language=tk.StringVar(value="fr");self.country=tk.StringVar(value="MA");self.shop=tk.StringVar(value="ToDo");self.printer=tk.StringVar();self.barcode=tk.StringVar();self.pin=tk.StringVar();self.pin_confirm=tk.StringVar()
        body=ttk.Frame(self,padding=26);body.pack(fill="both",expand=True)
        ttk.Label(body,text="Welcome to ToDo POS",style="Title.TLabel").pack(anchor="w")
        ttk.Label(body,text="Set up your shop. You can change these settings later.").pack(anchor="w",pady=(0,20))
        for label,var,values in [("Language",self.language,("en","fr","ar")),("Country",self.country,tuple(PROFILES))]:
            ttk.Label(body,text=label).pack(anchor="w");ttk.Combobox(body,textvariable=var,values=values,state="readonly").pack(fill="x",pady=(0,12))
        ttk.Label(body,text="Shop name").pack(anchor="w");ttk.Entry(body,textvariable=self.shop).pack(fill="x",pady=(0,12))
        ttk.Label(body,text="Receipt printer (optional)").pack(anchor="w");ttk.Entry(body,textvariable=self.printer).pack(fill="x",pady=(0,12))
        ttk.Label(body,text="Barcode scanner test (optional)").pack(anchor="w");barcode_entry=ttk.Entry(body,textvariable=self.barcode);barcode_entry.pack(fill="x",pady=(0,4));barcode_entry.bind("<Return>",lambda e:self.confirm_barcode())
        self.barcode_status=ttk.Label(body);self.barcode_status.pack(anchor="w")
        ttk.Label(body,text="New admin PIN").pack(anchor="w");ttk.Entry(body,textvariable=self.pin,show="•").pack(fill="x")
        ttk.Label(body,text="Confirm admin PIN").pack(anchor="w");ttk.Entry(body,textvariable=self.pin_confirm,show="•").pack(fill="x",pady=(0,6))
        self.summary=ttk.Label(body);self.summary.pack(anchor="w",pady=8);self.country.trace_add("write",lambda *_:self.apply_country_defaults());self.refresh()
        ttk.Button(body,text="Start ToDo",style="Primary.TButton",command=self.finish).pack(anchor="e",pady=14)
    def confirm_barcode(self):
        value=self.barcode.get().strip()
        self.barcode_status.config(text=(f"Barcode received: {value}" if value else "Enter or scan a barcode."))
    def apply_country_defaults(self):
        profile=get_country_profile(self.country.get())
        self.language.set(profile.default_language)
        self.refresh()
    def refresh(self):
        p=get_country_profile(self.country.get());self.summary.config(text=f"{p.currency} · {p.tax_label} {p.default_tax_rate_basis_points/100:g}%")
    def finish(self):
        if not self.shop.get().strip():messagebox.showerror("ToDo","Shop name is required.",parent=self);return
        if not self.pin.get().isdigit() or not 4<=len(self.pin.get())<=12 or self.pin.get()!=self.pin_confirm.get():
            messagebox.showerror("ToDo","Enter the same 4–12 digit admin PIN twice.",parent=self);return
        select_country_profile(self.country.get())
        with connect() as conn:
            conn.execute("UPDATE users SET pin_hash=? WHERE username='admin'",(hash_pin(self.pin.get()),));conn.commit()
        set_setting("language",self.language.get());set_setting("shop_name",self.shop.get().strip());set_setting("printer_name",self.printer.get().strip());mark_complete()
        self.destroy();self.on_done()
