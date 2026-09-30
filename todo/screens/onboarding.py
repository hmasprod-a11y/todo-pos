import tkinter as tk
from tkinter import ttk,messagebox
from country_profiles import PROFILES,get_country_profile
from services.globalization import select_country_profile
from services.onboarding import mark_complete
from database import set_setting

class FirstRunWizard(tk.Toplevel):
    """Minimal offline first-run setup before normal sign-in."""
    def __init__(self,master,on_done):
        super().__init__(master);self.on_done=on_done;self.transient(master);self.grab_set()
        self.title("ToDo POS — First setup");self.geometry("520x420");self.resizable(False,False)
        self.language=tk.StringVar(value="fr");self.country=tk.StringVar(value="MA");self.shop=tk.StringVar(value="ToDo");self.printer=tk.StringVar()
        body=ttk.Frame(self,padding=26);body.pack(fill="both",expand=True)
        ttk.Label(body,text="Welcome to ToDo POS",style="Title.TLabel").pack(anchor="w")
        ttk.Label(body,text="Set up your shop. You can change these settings later.").pack(anchor="w",pady=(0,20))
        for label,var,values in [("Language",self.language,("en","fr","ar")),("Country",self.country,tuple(PROFILES))]:
            ttk.Label(body,text=label).pack(anchor="w");ttk.Combobox(body,textvariable=var,values=values,state="readonly").pack(fill="x",pady=(0,12))
        ttk.Label(body,text="Shop name").pack(anchor="w");ttk.Entry(body,textvariable=self.shop).pack(fill="x",pady=(0,12))
        ttk.Label(body,text="Receipt printer (optional)").pack(anchor="w");ttk.Entry(body,textvariable=self.printer).pack(fill="x",pady=(0,12))
        self.summary=ttk.Label(body);self.summary.pack(anchor="w",pady=8);self.country.trace_add("write",lambda *_:self.apply_country_defaults());self.refresh()
        ttk.Button(body,text="Start ToDo",style="Primary.TButton",command=self.finish).pack(anchor="e",pady=14)
    def apply_country_defaults(self):
        profile=get_country_profile(self.country.get())
        self.language.set(profile.default_language)
        self.refresh()
    def refresh(self):
        p=get_country_profile(self.country.get());self.summary.config(text=f"{p.currency} · {p.tax_label} {p.default_tax_rate_basis_points/100:g}%")
    def finish(self):
        if not self.shop.get().strip():messagebox.showerror("ToDo","Shop name is required.",parent=self);return
        select_country_profile(self.country.get());set_setting("language",self.language.get());set_setting("shop_name",self.shop.get().strip());set_setting("printer_name",self.printer.get().strip());mark_complete()
        self.destroy();self.on_done()
