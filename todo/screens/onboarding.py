import tkinter as tk
from tkinter import ttk,messagebox
from country_profiles import PROFILES,get_country_profile
from services.globalization import select_country_profile
from services.onboarding import mark_complete
from database import set_setting,connect
from services.security import hash_pin
from localization import Translator,language_direction
from design_system import COLORS

class FirstRunWizard(tk.Toplevel):
    """Offline first-run setup, localized before normal sign-in."""
    def __init__(self,master,on_done):
        super().__init__(master);self.on_done=on_done;self.transient(master);self.grab_set()
        height=min(760,max(500,self.winfo_screenheight()-100))
        self.geometry(f"560x{height}");self.resizable(True,True)
        self.language=tk.StringVar(value="fr");self.language_label=tk.StringVar();self.country=tk.StringVar(value="MA");self.country_label=tk.StringVar();self.shop=tk.StringVar(value="ToDo");self.currency=tk.StringVar(value="DH");self.tax_rate=tk.StringVar(value="20");self.tax_included=tk.BooleanVar(value=True);self.printer=tk.StringVar();self.barcode=tk.StringVar();self.pin=tk.StringVar();self.pin_confirm=tk.StringVar()
        self._barcode_key="";self._language_selected=False;self._texts=[];self._text_inputs=[]
        footer=ttk.Frame(self,padding=(26,8));footer.pack(side="bottom",fill="x")
        viewport=ttk.Frame(self);viewport.pack(side="top",fill="both",expand=True)
        canvas=tk.Canvas(viewport,background=COLORS['canvas'],highlightthickness=0)
        scrollbar=ttk.Scrollbar(viewport,orient="vertical",command=canvas.yview)
        scrollbar.pack(side="right",fill="y")
        canvas.pack(side="left",fill="both",expand=True)
        canvas.configure(yscrollcommand=scrollbar.set)
        body=ttk.Frame(canvas,padding=26);self.body=body
        body_window=canvas.create_window((0,0),window=body,anchor="nw")
        body.bind("<Configure>",lambda e:canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",lambda e:canvas.itemconfigure(body_window,width=e.width))
        self.body_canvas=canvas
        self.welcome=self._label("onboarding.welcome",style="Title.TLabel");self.welcome.pack(fill="x")
        self.subtitle=self._label("onboarding.subtitle");self.subtitle.pack(fill="x",pady=(0,20))
        self._label("onboarding.language").pack(fill="x")
        self.language_box=ttk.Combobox(body,textvariable=self.language_label,state="readonly");self.language_box.pack(fill="x",pady=(0,12));self.language_box.bind("<<ComboboxSelected>>",self.select_language)
        self._label("onboarding.country").pack(fill="x")
        self.country_box=ttk.Combobox(body,textvariable=self.country_label,state="readonly");self.country_box.pack(fill="x",pady=(0,12));self.country_box.bind("<<ComboboxSelected>>",self.select_country)
        self._label("onboarding.shop").pack(fill="x");shop_entry=ttk.Entry(body,textvariable=self.shop);shop_entry.pack(fill="x",pady=(0,12));self._text_inputs.append(shop_entry)
        self._label("onboarding.currency").pack(fill="x");currency_entry=ttk.Entry(body,textvariable=self.currency);currency_entry.pack(fill="x",pady=(0,12));self._text_inputs.append(currency_entry)
        self._label("onboarding.tax_rate").pack(fill="x");tax_entry=ttk.Entry(body,textvariable=self.tax_rate);tax_entry.pack(fill="x",pady=(0,4));self._text_inputs.append(tax_entry)
        self._label("onboarding.tax_included").pack(fill="x");ttk.Checkbutton(body,variable=self.tax_included).pack(anchor="w",pady=(0,12))
        self._label("onboarding.printer").pack(fill="x");printer_entry=ttk.Entry(body,textvariable=self.printer);printer_entry.pack(fill="x",pady=(0,12));self._text_inputs.append(printer_entry)
        self._label("onboarding.barcode").pack(fill="x");barcode_entry=ttk.Entry(body,textvariable=self.barcode);barcode_entry.pack(fill="x",pady=(0,4));self._text_inputs.append(barcode_entry);barcode_entry.bind("<Return>",lambda e:self.confirm_barcode())
        self.barcode_status=ttk.Label(body);self.barcode_status.pack(fill="x")
        self._label("onboarding.pin").pack(fill="x");ttk.Entry(body,textvariable=self.pin,show="•").pack(fill="x")
        self._label("onboarding.pin_confirm").pack(fill="x");ttk.Entry(body,textvariable=self.pin_confirm,show="•").pack(fill="x",pady=(0,6))
        self.summary=ttk.Label(body);self.summary.pack(fill="x",pady=8)
        self.start=ttk.Button(footer,style="Primary.TButton",command=self.finish);self.start.pack(anchor="e",pady=6)
        self.country.trace_add("write",lambda *_:self.apply_country_defaults());self.language.trace_add("write",lambda *_:self.refresh());self.refresh()
    def select_language(self,event=None):
        code=self._language_codes.get(self.language_label.get())
        if code:
            self._language_selected=True;self.language.set(code)

    def select_country(self,event=None):
        code=self._country_codes.get(self.country_label.get())
        if code:self.country.set(code)

    def _label(self,key,**kwargs):
        widget=ttk.Label(self.body,**kwargs);self._texts.append((widget,key));return widget
    def _tr(self,key,**values): return Translator(self.language.get())(key,**values)
    def confirm_barcode(self):
        value=self.barcode.get().strip();self._barcode_key="onboarding.barcode_received" if value else "onboarding.barcode_empty";self.refresh()
    def apply_country_defaults(self):
        profile=get_country_profile(self.country.get())
        self.currency.set(profile.currency)
        self.tax_rate.set(f"{profile.default_tax_rate_basis_points/100:g}")
        self.tax_included.set(profile.tax_included_by_default)
        if not self._language_selected:
            self.language.set(profile.default_language)
    def refresh(self):
        tr=Translator(self.language.get());rtl=language_direction(self.language.get())=="rtl";anchor="e" if rtl else "w"
        self.title("ToDo POS — "+tr("onboarding.welcome"));self.welcome.config(anchor=anchor)
        self._language_codes={tr(f"language.{code}"):code for code in ("en","fr","ar")}
        self.language_box.configure(values=tuple(self._language_codes))
        self.language_label.set(next(label for label,code in self._language_codes.items() if code==self.language.get()))
        country_names={"en":{"MA":"Morocco","FR":"France","GB":"United Kingdom","AE":"United Arab Emirates"},"fr":{"MA":"Maroc","FR":"France","GB":"Royaume-Uni","AE":"Émirats arabes unis"},"ar":{"MA":"المغرب","FR":"فرنسا","GB":"المملكة المتحدة","AE":"الإمارات العربية المتحدة"}}
        names=country_names.get(self.language.get(),country_names["fr"])
        self._country_codes={names.get(code,code):code for code in PROFILES}
        self.country_box.configure(values=tuple(self._country_codes))
        self.country_label.set(next(label for label,code in self._country_codes.items() if code==self.country.get()))
        for widget,key in self._texts:widget.config(text=tr(key),anchor=anchor)
        self.subtitle.config(justify="right" if rtl else "left")
        for entry in self._text_inputs: entry.configure(justify="right" if rtl else "left")
        self.start.config(text=tr("onboarding.start"));self.start.pack_configure(anchor="w" if rtl else "e")
        p=get_country_profile(self.country.get());self.summary.config(text=f"{p.currency} · {p.tax_label} {p.default_tax_rate_basis_points/100:g}%",anchor=anchor)
        if self._barcode_key:self.barcode_status.config(text=tr(self._barcode_key,value=self.barcode.get().strip()),anchor=anchor)
    def finish(self):
        if not self.shop.get().strip():messagebox.showerror("ToDo",self._tr("onboarding.shop_required"),parent=self);return
        if not self.currency.get().strip():
            messagebox.showerror("ToDo",self._tr("onboarding.currency_required"),parent=self);return
        try:
            tax_rate=float(self.tax_rate.get().replace(",", "."))
            if not 0 <= tax_rate <= 100: raise ValueError()
        except (TypeError, ValueError):
            messagebox.showerror("ToDo",self._tr("onboarding.tax_invalid"),parent=self);return
        if not self.pin.get().isdigit() or not 4<=len(self.pin.get())<=12 or self.pin.get()!=self.pin_confirm.get():
            messagebox.showerror("ToDo",self._tr("onboarding.pin_invalid"),parent=self);return
        select_country_profile(self.country.get())
        set_setting("currency",self.currency.get().strip())
        set_setting("tax_default_rate_basis_points",round(tax_rate*100))
        set_setting("tax_default_included",1 if self.tax_included.get() else 0)
        with connect() as conn:conn.execute("UPDATE users SET pin_hash=? WHERE username='admin'",(hash_pin(self.pin.get()),));conn.commit()
        set_setting("language",self.language.get());set_setting("shop_name",self.shop.get().strip());set_setting("printer_name",self.printer.get().strip());mark_complete()
        self.destroy();self.on_done()
