import tkinter as tk
from tkinter import ttk,messagebox
from country_profiles import PROFILES,get_country_profile
from services.globalization import select_country_profile
from services.onboarding import mark_complete
from database import set_setting,connect
from services.security import hash_pin
from localization import Translator,language_direction

class FirstRunWizard(tk.Toplevel):
    """Offline first-run setup, localized before normal sign-in."""
    def __init__(self,master,on_done):
        super().__init__(master);self.on_done=on_done;self.transient(master);self.grab_set()
        self.geometry("560x650");self.resizable(False,False)
        self.language=tk.StringVar(value="fr");self.country=tk.StringVar(value="MA");self.shop=tk.StringVar(value="ToDo");self.printer=tk.StringVar();self.barcode=tk.StringVar();self.pin=tk.StringVar();self.pin_confirm=tk.StringVar()
        self._barcode_key="";self._texts=[]
        body=ttk.Frame(self,padding=26);body.pack(fill="both",expand=True);self.body=body
        self.welcome=self._label("onboarding.welcome",style="Title.TLabel");self.welcome.pack(fill="x")
        self.subtitle=self._label("onboarding.subtitle");self.subtitle.pack(fill="x",pady=(0,20))
        for key,var,values in [("onboarding.language",self.language,("en","fr","ar")),("onboarding.country",self.country,tuple(PROFILES))]:
            label=self._label(key);label.pack(fill="x");ttk.Combobox(body,textvariable=var,values=values,state="readonly").pack(fill="x",pady=(0,12))
        self._label("onboarding.shop").pack(fill="x");ttk.Entry(body,textvariable=self.shop).pack(fill="x",pady=(0,12))
        self._label("onboarding.printer").pack(fill="x");ttk.Entry(body,textvariable=self.printer).pack(fill="x",pady=(0,12))
        self._label("onboarding.barcode").pack(fill="x");barcode_entry=ttk.Entry(body,textvariable=self.barcode);barcode_entry.pack(fill="x",pady=(0,4));barcode_entry.bind("<Return>",lambda e:self.confirm_barcode())
        self.barcode_status=ttk.Label(body);self.barcode_status.pack(fill="x")
        self._label("onboarding.pin").pack(fill="x");ttk.Entry(body,textvariable=self.pin,show="•").pack(fill="x")
        self._label("onboarding.pin_confirm").pack(fill="x");ttk.Entry(body,textvariable=self.pin_confirm,show="•").pack(fill="x",pady=(0,6))
        self.summary=ttk.Label(body);self.summary.pack(fill="x",pady=8)
        self.start=ttk.Button(body,style="Primary.TButton",command=self.finish);self.start.pack(anchor="e",pady=14)
        self.country.trace_add("write",lambda *_:self.apply_country_defaults());self.language.trace_add("write",lambda *_:self.refresh());self.refresh()
    def _label(self,key,**kwargs):
        widget=ttk.Label(self.body,**kwargs);self._texts.append((widget,key));return widget
    def _tr(self,key,**values): return Translator(self.language.get())(key,**values)
    def confirm_barcode(self):
        value=self.barcode.get().strip();self._barcode_key="onboarding.barcode_received" if value else "onboarding.barcode_empty";self.refresh()
    def apply_country_defaults(self):
        self.language.set(get_country_profile(self.country.get()).default_language)
    def refresh(self):
        tr=Translator(self.language.get());rtl=language_direction(self.language.get())=="rtl";anchor="e" if rtl else "w"
        self.title("ToDo POS — "+tr("onboarding.welcome"));self.welcome.config(anchor=anchor)
        for widget,key in self._texts:widget.config(text=tr(key),anchor=anchor)
        self.subtitle.config(justify="right" if rtl else "left")
        self.start.config(text=tr("onboarding.start"));self.start.pack_configure(anchor="w" if rtl else "e")
        p=get_country_profile(self.country.get());self.summary.config(text=f"{p.currency} · {p.tax_label} {p.default_tax_rate_basis_points/100:g}%",anchor=anchor)
        if self._barcode_key:self.barcode_status.config(text=tr(self._barcode_key,value=self.barcode.get().strip()),anchor=anchor)
    def finish(self):
        if not self.shop.get().strip():messagebox.showerror("ToDo",self._tr("onboarding.shop_required"),parent=self);return
        if not self.pin.get().isdigit() or not 4<=len(self.pin.get())<=12 or self.pin.get()!=self.pin_confirm.get():
            messagebox.showerror("ToDo",self._tr("onboarding.pin_invalid"),parent=self);return
        select_country_profile(self.country.get())
        with connect() as conn:conn.execute("UPDATE users SET pin_hash=? WHERE username='admin'",(hash_pin(self.pin.get()),));conn.commit()
        set_setting("language",self.language.get());set_setting("shop_name",self.shop.get().strip());set_setting("printer_name",self.printer.get().strip());mark_complete()
        self.destroy();self.on_done()
