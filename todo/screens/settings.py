from database import connect
from pathlib import Path
import os,sys
import tkinter as tk
from tkinter import ttk,messagebox,filedialog,simpledialog
from database import get_setting,set_setting,connect
from services.secrets import get_smtp_password,set_smtp_password
from country_profiles import PROFILES, get_country_profile
from services.globalization import select_country_profile
from services.backup import create_backup,restore_backup,create_full_backup,restore_full_backup
from services.security import hash_pin, require_admin, require_permission, audit



def _sync_windows_startup(enabled):
    """Register/unregister ToDo for the current Windows user."""
    if os.name != 'nt':
        return
    import winreg
    key_path=r'Software\Microsoft\Windows\CurrentVersion\Run'
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER,key_path,0,winreg.KEY_SET_VALUE) as key:
        if enabled:
            if getattr(sys,'frozen',False):
                command=f'"{sys.executable}"'
            else:
                root=Path(__file__).resolve().parents[2]
                py=Path(sys.executable)
                pythonw=py.with_name('pythonw.exe')
                launcher=pythonw if pythonw.exists() else py
                command=f'"{launcher}" "{root / "ToDo.pyw"}"'
            winreg.SetValueEx(key,'ToDoPOS',0,winreg.REG_SZ,command)
        else:
            try:winreg.DeleteValue(key,'ToDoPOS')
            except FileNotFoundError:pass

class CategoryEditor(tk.Toplevel):
    """Edit or create a category — name, color, icon."""
    PALETTE = [
        '#DC2626','#EA580C','#D97706','#65A30D','#16A34A',
        '#0891B2','#2563EB','#7C3AED','#DB2777','#6B7280',
        '#0F766E','#B45309','#1D4ED8','#7E22CE','#BE185D',
    ]
    ICONS = ['','🥩','🧃','🥖','🍎','🧴','🧹','🧊','🥛','🍫',
             '🫙','🧺','💊','🐟','🌿','🔧','📦','🍬','🥚','🧀']

    def __init__(self, master, cat=None, on_saved=None):
        super().__init__(master)
        self.lang=get_setting('language','fr');self.tr=lambda fr,ar: ar if self.lang=='ar' else fr
        self.cat_id  = cat['id']   if cat else None
        self.on_saved= on_saved
        self.title(self.tr('Famille','العائلة'))
        self.resizable(False, False)
        self.transient(master.winfo_toplevel())
        self.grab_set()

        self.name_var  = tk.StringVar(value=cat['name']  if cat else '')
        self.color_var = tk.StringVar(value=cat['color'] if cat else '#2563EB')
        self.icon_var  = tk.StringVar(value=cat['icon']  if cat else '')

        f = ttk.Frame(self, padding=20); f.pack(fill='both', expand=True)

        ttk.Label(f, text=self.tr('Nom','الاسم')).grid(row=0, column=0, sticky='w')
        ttk.Entry(f, textvariable=self.name_var, width=30).grid(row=0, column=1, columnspan=3, sticky='ew', pady=6)

        ttk.Label(f, text=self.tr('Couleur','اللون')).grid(row=1, column=0, sticky='w', pady=8)
        self.swatch = tk.Label(f, width=6, relief='groove')
        self.swatch.grid(row=1, column=1, sticky='w', padx=4)
        self._update_swatch()

        palette_frame = ttk.Frame(f); palette_frame.grid(row=2, column=0, columnspan=4, sticky='ew', pady=4)
        for i, color in enumerate(self.PALETTE):
            btn = tk.Button(palette_frame, bg=color, width=2, height=1, relief='flat', cursor='hand2',
                            command=lambda c=color: self._pick(c))
            btn.grid(row=i//8, column=i%8, padx=2, pady=2)

        ttk.Label(f, text=self.tr('Icône','الأيقونة')).grid(row=3, column=0, sticky='w', pady=8)
        icon_frame = ttk.Frame(f); icon_frame.grid(row=3, column=1, columnspan=3, sticky='ew')
        for i,icon in enumerate(self.ICONS):
            lbl = icon if icon else '—'
            tk.Button(icon_frame, text=lbl, width=3, font=('Segoe UI', 12),
                      relief='flat', cursor='hand2',
                      command=lambda ic=icon: self.icon_var.set(ic)).grid(row=i//7,column=i%7,padx=1)

        ttk.Button(f, text=self.tr('Enregistrer','حفظ'), style='Primary.TButton',
                   command=self.save).grid(row=4, column=0, columnspan=4, sticky='ew', pady=16)

    def _pick(self, color):
        self.color_var.set(color)
        self._update_swatch()

    def _update_swatch(self):
        self.swatch.config(bg=self.color_var.get(), text=self.color_var.get(),
                           fg='#ffffff', font=('Consolas', 8))

    def save(self):
        name  = self.name_var.get().strip()
        color = self.color_var.get().strip() or '#2563EB'
        icon  = self.icon_var.get().strip()
        if not name:
            from tkinter import messagebox
            messagebox.showerror(self.tr('Famille','العائلة'), self.tr('Le nom est obligatoire.','الاسم إجباري.'), parent=self); return
        with connect() as conn:
            require_permission('MANAGEMENT', conn)
            if self.cat_id:
                conn.execute('UPDATE categories SET name=?,color=?,icon=? WHERE id=?',
                             (name, color, icon, self.cat_id))
            else:
                conn.execute('INSERT INTO categories(name,color,icon) VALUES(?,?,?)',
                             (name, color, icon))
            conn.commit()
        self.destroy()
        if self.on_saved: self.on_saved()

class SettingsFrame(ttk.Frame):
    def __init__(self,master,app):
        super().__init__(master,padding=0);self.app=app
        self.lang_ui=get_setting('language','fr');self.tr=lambda fr,ar: ar if self.lang_ui=='ar' else fr

        # Paramètres contient de nombreux blocs; le canvas garde toute la page
        # accessible sur tablette / petite fenêtre sans modifier les widgets.
        self.settings_canvas=tk.Canvas(self,highlightthickness=0,borderwidth=0)
        self.settings_scroll=ttk.Scrollbar(self,orient='vertical',command=self.settings_canvas.yview)
        self.settings_canvas.configure(yscrollcommand=self.settings_scroll.set)
        self.settings_scroll.pack(side='right',fill='y')
        self.settings_canvas.pack(side='left',fill='both',expand=True)
        body=ttk.Frame(self.settings_canvas,padding=16)
        self.settings_window=self.settings_canvas.create_window((0,0),window=body,anchor='nw')
        body.bind('<Configure>',lambda e:self.settings_canvas.configure(scrollregion=self.settings_canvas.bbox('all')))
        self.settings_canvas.bind('<Configure>',lambda e:self.settings_canvas.itemconfigure(self.settings_window,width=e.width))
        self.settings_canvas.bind('<MouseWheel>',self._settings_mousewheel)
        body.bind('<MouseWheel>',self._settings_mousewheel)
        ttk.Label(body,text=self.tr('Paramètres','الإعدادات'),style='Title.TLabel').pack(anchor='w')
        ttk.Label(body,text=self.tr('Configuration du magasin, impression, données et utilisateurs','إعدادات المتجر والطباعة والبيانات والمستخدمين'),foreground='#64748B',font=('Segoe UI',9)).pack(anchor='w',pady=(0,12))
        f=ttk.LabelFrame(body,text=self.tr('Magasin et vente','المتجر والبيع'),padding=10);f.pack(fill="x")
        self.shop=tk.StringVar(value=get_setting("shop_name","ToDo"));self.cur=tk.StringVar(value=get_setting("currency","DH"));self.workstation=tk.StringVar(value=get_setting("workstation_code","01"));self.neg=tk.BooleanVar(value=get_setting("allow_negative_stock","1")=="1")
        self.footer=tk.StringVar(value=get_setting("receipt_footer","Merci"))
        self.block_insufficient=tk.BooleanVar(value=get_setting('block_insufficient_stock','0')=='1')
        self.manual_stock_edit_enabled=tk.BooleanVar(value=get_setting('manual_stock_edit_enabled','1')=='1')
        self.stock_management_enabled=tk.BooleanVar(value=get_setting('stock_management_enabled','1')=='1')
        self.require_client=tk.BooleanVar(value=get_setting('require_client_on_sale','0')=='1')
        self.choose_seller=tk.BooleanVar(value=get_setting('choose_seller_on_sale','0')=='1')
        self.start_with_windows=tk.BooleanVar(value=get_setting('start_with_windows','0')=='1')
        self.windows_mode=tk.BooleanVar(value=get_setting('windows_mode','1')=='1')
        self.credit_enabled=tk.BooleanVar(value=get_setting('credit_enabled','1')=='1')
        self.closure_enabled=tk.BooleanVar(value=get_setting('closure_enabled','1')=='1')
        self.sans_ticket_enabled=tk.BooleanVar(value=get_setting('sans_ticket_enabled','1')=='1')
        self.payment_window_enabled=tk.BooleanVar(value=get_setting('payment_window_enabled','1')=='1')
        self.search_limit=tk.StringVar(value=get_setting("search_limit","60"))
        self.language=tk.StringVar(value=get_setting("language","fr"))
        self.country=tk.StringVar(value=get_setting("country_code","MA"))
        self.country_info=tk.StringVar()
        ttk.Label(f,text=self.tr('Nom magasin','اسم المتجر')).grid(row=0,column=0,sticky="w");ttk.Entry(f,textvariable=self.shop,width=30).grid(row=0,column=1,padx=8)
        ttk.Label(f,text=self.tr('Langue','اللغة')).grid(row=0,column=2,sticky="w",padx=(18,4));ttk.Combobox(f,textvariable=self.language,values=("fr","en","ar"),state="readonly",width=8).grid(row=0,column=3,sticky="w")
        ttk.Label(f,text=self.tr('Pays','البلد')).grid(row=1,column=2,sticky="w",padx=(18,4));self.country_combo=ttk.Combobox(f,textvariable=self.country,values=tuple(PROFILES),state="readonly",width=8);self.country_combo.grid(row=1,column=3,sticky="w");self.country_combo.bind('<<ComboboxSelected>>',self.sync_country_profile)
        ttk.Label(f,text=self.tr('Devise','العملة')).grid(row=1,column=0,sticky="w",pady=5);ttk.Entry(f,textvariable=self.cur,width=10).grid(row=1,column=1,sticky="w",padx=8)
        ttk.Label(f,textvariable=self.country_info,foreground='#475569',wraplength=260).grid(row=2,column=2,columnspan=2,sticky='w',padx=(18,4))
        ttk.Label(f,text=self.tr('Poste de caisse','رقم محطة الصندوق')).grid(row=3,column=2,sticky='w',padx=(18,4));ttk.Entry(f,textvariable=self.workstation,width=12).grid(row=3,column=3,sticky='w')
        self.sync_country_profile()
        ttk.Checkbutton(f,text=self.tr('Gestion de stock','تدبير المخزون'),variable=self.stock_management_enabled).grid(row=2,column=0,columnspan=2,sticky='w')
        ttk.Checkbutton(f,text=self.tr('Autoriser stock négatif','السماح بالمخزون السالب'),variable=self.neg,command=self.sync_stock_options).grid(row=3,column=0,columnspan=2,sticky="w")
        ttk.Checkbutton(f,text=self.tr('Bloquer vente si stock insuffisant','منع البيع عند نقص المخزون'),variable=self.block_insufficient,command=self.sync_stock_options).grid(row=4,column=0,columnspan=2,sticky="w")
        ttk.Checkbutton(f,text=self.tr('Modification / Ajout de stock manuel','تعديل / إضافة المخزون يدوياً'),variable=self.manual_stock_edit_enabled).grid(row=5,column=0,columnspan=2,sticky='w')
        ttk.Checkbutton(f,text=self.tr('Afficher le choix du client pendant la vente','إظهار اختيار الزبون أثناء البيع'),variable=self.require_client).grid(row=6,column=0,columnspan=2,sticky="w")
        ttk.Checkbutton(f,text=self.tr('Choix du vendeur pendant la vente','اختيار البائع أثناء البيع'),variable=self.choose_seller).grid(row=7,column=0,columnspan=2,sticky="w")
        ttk.Checkbutton(f,text=self.tr('Lancer ToDo au démarrage de Windows','تشغيل ToDo مع بدء Windows'),variable=self.start_with_windows,command=self.toggle_windows_startup).grid(row=8,column=0,columnspan=3,sticky="w",pady=(3,0))
        ttk.Checkbutton(f,text=self.tr('Mode Windows (fenêtre)','وضع Windows (نافذة)'),variable=self.windows_mode,command=self.toggle_windows_mode).grid(row=9,column=0,columnspan=3,sticky="w",pady=(3,0))
        ttk.Checkbutton(f,text=self.tr('Activer la vente à crédit','تفعيل البيع بالدين'),variable=self.credit_enabled).grid(row=10,column=0,columnspan=3,sticky="w",pady=(3,0))
        ttk.Checkbutton(f,text=self.tr('Activer la clôture de caisse','تفعيل إغلاق الصندوق'),variable=self.closure_enabled).grid(row=11,column=0,columnspan=3,sticky="w",pady=(3,0))
        ttk.Checkbutton(f,text=self.tr('Autoriser SOLDER sans ticket','السماح بالأداء بدون تذكرة'),variable=self.sans_ticket_enabled).grid(row=12,column=0,columnspan=3,sticky="w",pady=(3,0))
        ttk.Checkbutton(f,text=self.tr('Afficher la fenêtre de paiement','إظهار نافذة الأداء'),variable=self.payment_window_enabled).grid(row=13,column=0,columnspan=3,sticky="w",pady=(3,0))
        ttk.Label(f,text=self.tr('Message bas du ticket','رسالة أسفل التذكرة')).grid(row=14,column=0,sticky="w",pady=5);ttk.Entry(f,textvariable=self.footer,width=34).grid(row=14,column=1,padx=8)
        ttk.Label(f,text=self.tr('Limite résultats recherche','حد نتائج البحث')).grid(row=15,column=0,sticky="w");ttk.Entry(f,textvariable=self.search_limit,width=10).grid(row=15,column=1,sticky="w",padx=8)
        ttk.Button(f,text=self.tr('Enregistrer','حفظ'),style='Primary.TButton',command=self.save).grid(row=16,column=0,pady=8,sticky='ew')
        pg=ttk.LabelFrame(body,text=self.tr('Grilles de prix','لوائح الأثمان'),padding=10);pg.pack(fill="x",pady=10)
        ttk.Label(pg,text=self.tr('Créez les grilles ici, puis définissez le prix de chaque article dans sa fiche.','أنشئ لوائح الأثمان هنا، ثم حدد ثمن كل منتوج في بطاقته.')).pack(anchor="w")
        self.price_grids_frame=ttk.Frame(pg);self.price_grids_frame.pack(fill="x",pady=6)
        self.new_grid_name=tk.StringVar();row=ttk.Frame(pg);row.pack(fill="x")
        ttk.Entry(row,textvariable=self.new_grid_name,width=28).pack(side="left")
        ttk.Button(row,text=self.tr('+ Ajouter grille','+ إضافة لائحة'),style='Soft.TButton',command=self.add_price_grid).pack(side='left',padx=6)
        self.refresh_price_grids()
        sellers=ttk.LabelFrame(body,text=self.tr('Vendeurs','البائعون'),padding=10);sellers.pack(fill="x",pady=10)
        self.sellers_frame=ttk.Frame(sellers);self.sellers_frame.pack(fill="x",pady=(0,6))
        self.new_seller_name=tk.StringVar();sr=ttk.Frame(sellers);sr.pack(fill="x")
        ttk.Entry(sr,textvariable=self.new_seller_name,width=28).pack(side="left")
        ttk.Button(sr,text=self.tr('+ Ajouter vendeur','+ إضافة بائع'),style='Soft.TButton',command=self.add_seller).pack(side='left',padx=6)
        self.refresh_sellers()
        pm=ttk.LabelFrame(body,text=self.tr('Modes de paiement','طرق الأداء'),padding=10);pm.pack(fill='x',pady=10)
        self.payment_methods_frame=ttk.Frame(pm);self.payment_methods_frame.pack(fill='x',pady=(0,6))
        row_pm=ttk.Frame(pm);row_pm.pack(fill='x')
        self.new_payment_code=tk.StringVar();self.new_payment_fr=tk.StringVar();self.new_payment_ar=tk.StringVar();self.new_payment_icon=tk.StringVar()
        ttk.Entry(row_pm,textvariable=self.new_payment_code,width=12).pack(side='left')
        ttk.Entry(row_pm,textvariable=self.new_payment_fr,width=20).pack(side='left',padx=4)
        ttk.Entry(row_pm,textvariable=self.new_payment_ar,width=20).pack(side='left',padx=4)
        ttk.Entry(row_pm,textvariable=self.new_payment_icon,width=6).pack(side='left',padx=4)
        ttk.Button(row_pm,text=self.tr('+ Ajouter mode','+ إضافة طريقة'),style='Soft.TButton',command=self.add_payment_method).pack(side='left',padx=6)
        self.refresh_payment_methods()
        p=ttk.LabelFrame(body,text=self.tr('Impression','الطباعة'),padding=10);p.pack(fill="x",pady=10)
        self.printer=tk.StringVar(value=get_setting('printer_receipt_name',get_setting("printer_name","")))
        self.report_printer=tk.StringVar(value=get_setting('printer_report_name',''))
        self.addition_printer=tk.StringVar(value=get_setting('printer_addition_name',''))
        self.kitchen_printers=[tk.StringVar(value=get_setting(f'printer_kitchen_c{i}_name','')) for i in range(1,5)]
        self.receipt_template=tk.StringVar(value=get_setting('receipt_template','FR_3C'))
        self.print_mode=tk.StringVar(value=get_setting("print_mode","ask"));self.thermal_raw=tk.BooleanVar(value=get_setting('thermal_raw','0')=='1');self.receipt_chars=tk.StringVar(value=get_setting('receipt_chars','42'))
        ttk.Label(p,text=self.tr('Ticket / Solder','التذكرة / الأداء')).grid(row=0,column=0,sticky="w")
        self.printer_choice=ttk.Combobox(p,textvariable=self.printer,width=34);self.printer_choice.grid(row=0,column=1,padx=8)
        ttk.Label(p,text=self.tr('Rapports','التقارير')).grid(row=1,column=0,sticky="w");self.report_printer_choice=ttk.Combobox(p,textvariable=self.report_printer,width=34);self.report_printer_choice.grid(row=1,column=1,padx=8)
        ttk.Label(p,text=self.tr('Addition','الحساب')).grid(row=2,column=0,sticky="w");self.addition_printer_choice=ttk.Combobox(p,textvariable=self.addition_printer,width=34);self.addition_printer_choice.grid(row=2,column=1,padx=8)
        self.kitchen_printer_choices=[]
        for i,var in enumerate(self.kitchen_printers,1):
            ttk.Label(p,text=f'C{i}').grid(row=2+i,column=0,sticky='w')
            cb=ttk.Combobox(p,textvariable=var,width=34);cb.grid(row=2+i,column=1,padx=8);self.kitchen_printer_choices.append(cb)
        ttk.Button(p,text=self.tr('Actualiser imprimantes','تحديث الطابعات'),command=self.refresh_printers).grid(row=0,column=2,padx=5)
        ttk.Button(p,text=self.tr('Tester ticket','اختبار طابعة التذكرة'),style='Soft.TButton',command=self.test_printer).grid(row=0,column=3,padx=5)
        ttk.Label(p,text=self.tr('Modèle ticket','قالب التذكرة')).grid(row=7,column=0,sticky='w')
        ttk.Combobox(p,textvariable=self.receipt_template,values=['FR_3C','FR_4C','FR_2L','AR_3C','AR_4C'],state='readonly',width=12).grid(row=7,column=1,sticky='w',padx=8)
        ttk.Label(p,text=self.tr('Après validation','بعد تأكيد البيع')).grid(row=8,column=0,sticky="w",pady=5)
        suite=ttk.LabelFrame(body,text=self.tr('Configuration Suite — Ticket','إعدادات إضافية — التذكرة'),padding=10);suite.pack(fill='x',pady=10)
        self.receipt_show_payment=tk.BooleanVar(value=get_setting('receipt_show_payment','1')=='1')
        self.receipt_show_ticket_no=tk.BooleanVar(value=get_setting('receipt_show_ticket_no','1')=='1')
        self.receipt_show_sale_mode=tk.BooleanVar(value=get_setting('receipt_show_sale_mode','1')=='1')
        self.receipt_show_barcode=tk.BooleanVar(value=get_setting('receipt_show_barcode','0')=='1')
        self.next_client_ticket=tk.StringVar(value=get_setting('receipt_next_client_ticket','1'))
        ttk.Checkbutton(suite,text=self.tr('Afficher Mode Paiement','إظهار طريقة الأداء'),variable=self.receipt_show_payment).grid(row=0,column=0,sticky='w',padx=6,pady=3)
        ttk.Checkbutton(suite,text=self.tr('Afficher N° TICKET','إظهار رقم التذكرة'),variable=self.receipt_show_ticket_no).grid(row=1,column=0,sticky='w',padx=6,pady=3)
        ttk.Checkbutton(suite,text=self.tr('Afficher Mode Vente','إظهار نوع البيع'),variable=self.receipt_show_sale_mode).grid(row=2,column=0,sticky='w',padx=6,pady=3)
        ttk.Checkbutton(suite,text=self.tr('Afficher Code Barre','إظهار الباركود'),variable=self.receipt_show_barcode).grid(row=3,column=0,sticky='w',padx=6,pady=3)
        ttk.Label(suite,text=self.tr('Prochain N° Ticket Client','رقم تذكرة الزبون التالي')).grid(row=0,column=1,sticky='e',padx=6)
        ttk.Entry(suite,textvariable=self.next_client_ticket,width=12).grid(row=0,column=2,sticky='w',padx=6)
        ttk.Button(suite,text=self.tr('Régénérer automatiquement','إعادة توليد تلقائياً'),style='Soft.TButton',command=self.regenerate_client_ticket_no).grid(row=1,column=1,columnspan=2,sticky='ew',padx=6,pady=4)

        self.print_mode_box=ttk.Combobox(p,state='readonly',width=18)
        self.print_mode_labels={self.tr('Demander','سؤال'):'ask',self.tr('Toujours imprimer','الطباعة دائماً'):'always',self.tr('Ne jamais imprimer','عدم الطباعة'):'never'}
        self.print_mode_box['values']=list(self.print_mode_labels);self.print_mode_box.set(next((k for k,v in self.print_mode_labels.items() if v==self.print_mode.get()),list(self.print_mode_labels)[0]));self.print_mode_box.bind('<<ComboboxSelected>>',lambda e:self.print_mode.set(self.print_mode_labels.get(self.print_mode_box.get(),'ask')));self.print_mode_box.grid(row=8,column=1,sticky='w',padx=8)
        ttk.Label(p,text=self.tr('Comportement impression','سلوك الطباعة')).grid(row=9,column=0,sticky='w')
        ttk.Label(p,text=self.tr('Demander / Toujours / Jamais','سؤال / دائماً / أبداً')).grid(row=9,column=1,columnspan=2,sticky='w')
        ttk.Checkbutton(p,text=self.tr('Mode ticket thermique ESC/POS (RAW)','وضع التذكرة الحرارية ESC/POS (RAW)'),variable=self.thermal_raw).grid(row=10,column=0,columnspan=2,sticky='w')
        ttk.Label(p,text=self.tr('Largeur ticket (caractères)','عرض التذكرة (حروف)')).grid(row=10,column=2,sticky='e')
        ttk.Combobox(p,textvariable=self.receipt_chars,values=['32','42','48'],state='readonly',width=5).grid(row=10,column=3,sticky='w',padx=6)
        self.drawer_enabled=tk.BooleanVar(value=get_setting('drawer_enabled','0')=='1')
        self.drawer_pin=tk.StringVar(value=get_setting('drawer_pin','0'))
        ttk.Checkbutton(p,text=self.tr('Tiroir connecté à une imprimante ESC/POS','درج النقود متصل بطابعة ESC/POS'),variable=self.drawer_enabled).grid(row=11,column=0,columnspan=2,sticky='w')
        ttk.Label(p,text=self.tr('Connecteur tiroir','موصل درج النقود')).grid(row=12,column=0,sticky='w')
        ttk.Combobox(p,textvariable=self.drawer_pin,values=['0','1'],state='readonly',width=5).grid(row=12,column=1,sticky='w',padx=8)
        ttk.Button(p,text=self.tr('Enregistrer impression','حفظ إعدادات الطباعة'),command=self.save).grid(row=13,column=2)
        scale=ttk.LabelFrame(body,text=self.tr('Balance électronique','الميزان الإلكتروني'),padding=10);scale.pack(fill='x',pady=10)
        self.scale_enabled=tk.BooleanVar(value=get_setting('scale_enabled','0')=='1')
        self.scale_port=tk.StringVar(value=get_setting('scale_port',''))
        self.scale_baudrate=tk.StringVar(value=get_setting('scale_baudrate','9600'))
        self.scale_timeout=tk.StringVar(value=get_setting('scale_timeout_ms','800'))
        ttk.Checkbutton(scale,text=self.tr('Activer la balance série','تفعيل الميزان عبر المنفذ التسلسلي'),variable=self.scale_enabled).grid(row=0,column=0,columnspan=2,sticky='w')
        ttk.Label(scale,text=self.tr('Port COM','منفذ COM')).grid(row=1,column=0,sticky='w',pady=4)
        self.scale_port_box=ttk.Combobox(scale,textvariable=self.scale_port,width=18);self.scale_port_box.grid(row=1,column=1,sticky='w',padx=8)
        ttk.Button(scale,text=self.tr('Actualiser ports','تحديث المنافذ'),command=self.refresh_scale_ports).grid(row=1,column=2,padx=4)
        ttk.Label(scale,text='BaudRate').grid(row=2,column=0,sticky='w')
        ttk.Combobox(scale,textvariable=self.scale_baudrate,values=['1200','2400','4800','9600','19200','38400','57600','115200'],width=12,state='readonly').grid(row=2,column=1,sticky='w',padx=8)
        ttk.Label(scale,text=self.tr('Timeout (ms)','مهلة القراءة (ms)')).grid(row=2,column=2,sticky='e')
        ttk.Entry(scale,textvariable=self.scale_timeout,width=8).grid(row=2,column=3,sticky='w',padx=8)
        ttk.Button(scale,text=self.tr('Tester la balance','اختبار الميزان'),style='Soft.TButton',command=self.test_scale).grid(row=3,column=1,sticky='w',pady=6)
        self.refresh_scale_ports()
        d=ttk.LabelFrame(body,text=self.tr('Écran client','شاشة الزبون'),padding=10);d.pack(fill="x",pady=10)
        serial_display=ttk.LabelFrame(body,text=self.tr('Afficheur client série','شاشة الزبون التسلسلية'),padding=10);serial_display.pack(fill='x',pady=10)
        self.customer_serial_enabled=tk.BooleanVar(value=get_setting('customer_serial_enabled','0')=='1')
        self.customer_serial_port=tk.StringVar(value=get_setting('customer_serial_port',''))
        self.customer_serial_baud=tk.StringVar(value=get_setting('customer_serial_baudrate','9600'))
        self.customer_serial_timeout=tk.StringVar(value=get_setting('customer_serial_timeout_ms','500'))
        self.customer_serial_width=tk.StringVar(value=get_setting('customer_serial_width','20'))
        ttk.Checkbutton(serial_display,text=self.tr('Activer afficheur COM','تفعيل شاشة COM'),variable=self.customer_serial_enabled).grid(row=0,column=0,columnspan=2,sticky='w')
        ttk.Label(serial_display,text='Port COM').grid(row=1,column=0,sticky='w')
        self.customer_serial_port_box=ttk.Combobox(serial_display,textvariable=self.customer_serial_port,width=18);self.customer_serial_port_box.grid(row=1,column=1,sticky='w',padx=8)
        ttk.Button(serial_display,text=self.tr('Actualiser ports','تحديث المنافذ'),command=self.refresh_customer_serial_ports).grid(row=1,column=2,padx=4)
        ttk.Label(serial_display,text='BaudRate').grid(row=2,column=0,sticky='w')
        ttk.Combobox(serial_display,textvariable=self.customer_serial_baud,values=['1200','2400','4800','9600','19200','38400'],state='readonly',width=12).grid(row=2,column=1,sticky='w',padx=8)
        ttk.Label(serial_display,text=self.tr('Largeur caractères','عرض الحروف')).grid(row=2,column=2,sticky='e')
        ttk.Combobox(serial_display,textvariable=self.customer_serial_width,values=['16','20','24','40'],state='readonly',width=6).grid(row=2,column=3,sticky='w',padx=8)
        ttk.Label(serial_display,text=self.tr('Timeout (ms)','مهلة الاتصال')).grid(row=3,column=0,sticky='w')
        ttk.Entry(serial_display,textvariable=self.customer_serial_timeout,width=8).grid(row=3,column=1,sticky='w',padx=8)
        ttk.Button(serial_display,text=self.tr('Tester afficheur','اختبار الشاشة'),style='Soft.TButton',command=self.test_customer_serial).grid(row=3,column=2,padx=6)
        self.refresh_customer_serial_ports()
        self.customer_enabled=tk.BooleanVar(value=get_setting('customer_display_enabled','0')=='1')
        self.customer_seconds=tk.StringVar(value=get_setting("customer_slide_seconds","6"))
        current_mode=get_setting('customer_display_mode','promotions')
        self.customer_mode_labels={
            self.tr('Promotions · photos / vidéos','العروض · صور / فيديوهات'):'promotions',
            self.tr('Ticket · articles / prix','التذكرة · المنتجات / الأثمنة'):'prices',
        }
        ttk.Checkbutton(d,text=self.tr('Afficher écran client / publicitaire','إظهار شاشة الزبون / الإعلانات'),variable=self.customer_enabled,command=self.toggle_customer_enabled).pack(anchor='w',pady=(0,8))
        mode_row=ttk.Frame(d);mode_row.pack(fill='x',pady=(0,8))
        ttk.Label(mode_row,text=self.tr('Contenu affiché','المحتوى المعروض'),font=('Segoe UI',10,'bold')).pack(side='left')
        self.customer_mode_box=ttk.Combobox(mode_row,state='readonly',width=30,values=list(self.customer_mode_labels))
        self.customer_mode_box.set(next((label for label,value in self.customer_mode_labels.items() if value==current_mode),list(self.customer_mode_labels)[0]))
        self.customer_mode_box.pack(side='left',padx=8)
        ttk.Button(mode_row,text=self.tr('Tester écran client','اختبار شاشة الزبون'),style='Primary.TButton',command=self.test_customer).pack(side='right')
        media_row=ttk.Frame(d);media_row.pack(fill='x')
        ttk.Label(media_row,text=self.tr('Durée de chaque image (secondes)','مدة كل صورة (ثوانٍ)')).pack(side='left')
        ttk.Spinbox(media_row,from_=2,to=300,textvariable=self.customer_seconds,width=6).pack(side='left',padx=8)
        ttk.Label(media_row,text=self.tr('Dossier : customer_media · images + vidéos · format conseillé 16:9','المجلد: customer_media · صور + فيديوهات · القياس المقترح 16:9'),foreground="#475569").pack(side='left',padx=12)
        rfid=ttk.LabelFrame(body,text=self.tr('RFID','RFID'),padding=10);rfid.pack(fill='x',pady=10)
        self.rfid_enabled=tk.BooleanVar(value=get_setting('rfid_enabled','0')=='1')
        self.rfid_mode=tk.StringVar(value=get_setting('rfid_mode','HID'))
        self.rfid_port=tk.StringVar(value=get_setting('rfid_port',''))
        self.rfid_baud=tk.StringVar(value=get_setting('rfid_baudrate','9600'))
        self.rfid_timeout=tk.StringVar(value=get_setting('rfid_timeout_ms','800'))
        ttk.Checkbutton(rfid,text=self.tr('Activer RFID','تفعيل RFID'),variable=self.rfid_enabled).grid(row=0,column=0,columnspan=2,sticky='w')
        ttk.Label(rfid,text=self.tr('Mode lecteur','وضع القارئ')).grid(row=1,column=0,sticky='w')
        ttk.Combobox(rfid,textvariable=self.rfid_mode,values=['HID','SERIAL'],state='readonly',width=12).grid(row=1,column=1,sticky='w',padx=8)
        ttk.Label(rfid,text='Port COM').grid(row=2,column=0,sticky='w')
        self.rfid_port_box=ttk.Combobox(rfid,textvariable=self.rfid_port,width=18);self.rfid_port_box.grid(row=2,column=1,sticky='w',padx=8)
        ttk.Button(rfid,text=self.tr('Actualiser ports','تحديث المنافذ'),command=self.refresh_rfid_ports).grid(row=2,column=2,padx=4)
        ttk.Label(rfid,text='BaudRate').grid(row=3,column=0,sticky='w')
        ttk.Combobox(rfid,textvariable=self.rfid_baud,values=['1200','2400','4800','9600','19200','38400','57600','115200'],state='readonly',width=12).grid(row=3,column=1,sticky='w',padx=8)
        ttk.Label(rfid,text=self.tr('Timeout (ms)','مهلة القراءة')).grid(row=3,column=2,sticky='e');ttk.Entry(rfid,textvariable=self.rfid_timeout,width=8).grid(row=3,column=3,padx=8,sticky='w')
        ttk.Button(rfid,text=self.tr('Tester RFID série','اختبار RFID التسلسلي'),style='Soft.TButton',command=self.test_rfid).grid(row=4,column=1,sticky='w',pady=6)
        self.refresh_rfid_ports()
        mail=ttk.LabelFrame(body,text=self.tr('E-mail / Gmail','البريد الإلكتروني / Gmail'),padding=10);mail.pack(fill='x',pady=10)
        self.email_enabled=tk.BooleanVar(value=get_setting('email_enabled','0')=='1')
        self.smtp_host=tk.StringVar(value=get_setting('smtp_host','smtp.gmail.com'));self.smtp_port=tk.StringVar(value=get_setting('smtp_port','587'))
        self.smtp_user=tk.StringVar(value=get_setting('smtp_user',''));self.smtp_password=tk.StringVar(value=get_smtp_password())
        self.smtp_from=tk.StringVar(value=get_setting('smtp_from_name','ToDo'))
        self.smtp_subject=tk.StringVar(value=get_setting('smtp_subject','').strip())
        ttk.Checkbutton(mail,text=self.tr('Activer envoi ticket / rapport par e-mail','تفعيل إرسال التذاكر والتقارير بالبريد'),variable=self.email_enabled).grid(row=0,column=0,columnspan=2,sticky='w')
        ttk.Label(mail,text='SMTP').grid(row=1,column=0,sticky='w');ttk.Entry(mail,textvariable=self.smtp_host,width=28).grid(row=1,column=1,sticky='w',padx=8)
        ttk.Label(mail,text='Port').grid(row=1,column=2,sticky='e');ttk.Entry(mail,textvariable=self.smtp_port,width=7).grid(row=1,column=3,sticky='w',padx=8)
        ttk.Label(mail,text=self.tr('Compte Gmail / e-mail','حساب Gmail / البريد')).grid(row=2,column=0,sticky='w');ttk.Entry(mail,textvariable=self.smtp_user,width=32).grid(row=2,column=1,sticky='w',padx=8)
        ttk.Label(mail,text=self.tr('App Password','كلمة مرور التطبيق')).grid(row=3,column=0,sticky='w');ttk.Entry(mail,textvariable=self.smtp_password,width=32,show='•').grid(row=3,column=1,sticky='w',padx=8)
        ttk.Label(mail,text=self.tr('Nom expéditeur','اسم المرسل')).grid(row=4,column=0,sticky='w');ttk.Entry(mail,textvariable=self.smtp_from,width=24).grid(row=4,column=1,sticky='w',padx=8)
        ttk.Label(mail,text=self.tr('Objet','الموضوع')).grid(row=5,column=0,sticky='w');ttk.Entry(mail,textvariable=self.smtp_subject,width=32).grid(row=5,column=1,sticky='w',padx=8)
        ttk.Button(mail,text=self.tr('Tester e-mail','اختبار البريد'),style='Soft.TButton',command=self.test_email).grid(row=5,column=2,padx=6)
        b=ttk.LabelFrame(body,text=self.tr('Données','البيانات'),padding=10);b.pack(fill="x",pady=10)
        ttk.Button(b,text=self.tr('Backup maintenant','نسخ احتياطي الآن'),style='Success.TButton',command=self.backup).pack(side='left',padx=4)
        self.auto_backup=tk.StringVar(value=get_setting("auto_backup_minutes","15"))
        ttk.Label(b,text=self.tr('Backup auto','نسخ احتياطي تلقائي')).pack(side="left",padx=(18,4))
        ttk.Combobox(b,textvariable=self.auto_backup,values=["0","5","10","15","30","60"],state="readonly",width=5).pack(side="left")
        ttk.Label(b,text=self.tr('min (0 = désactivé)','دقيقة (0 = معطل)')).pack(side="left",padx=4)
        ttk.Button(b,text=self.tr('Restaurer backup','استرجاع نسخة احتياطية'),style='Soft.TButton',command=self.restore).pack(side='left',padx=4)
        ttk.Button(b,text=self.tr('Backup complet portable','نسخة كاملة للنقل'),style='Soft.TButton',command=self.full_backup).pack(side='left',padx=4)
        ttk.Button(b,text=self.tr('Restaurer backup complet','استرجاع النسخة الكاملة'),style='Soft.TButton',command=self.full_restore).pack(side='left',padx=4)
        ttk.Button(b,text=self.tr('Base de Données','قاعدة البيانات'),style='Primary.TButton',command=self.database_tools).pack(side='left',padx=8)
        u=ttk.LabelFrame(body,text=self.tr('Utilisateurs','المستخدمون'),padding=10);u.pack(fill="x")
        ttk.Button(u,text=self.tr('Nouvel utilisateur','مستخدم جديد'),style='Primary.TButton',command=self.new_user).pack(side='left');ttk.Button(u,text=self.tr('Gérer utilisateurs','إدارة المستخدمين'),style='Soft.TButton',command=self.manage_users).pack(side='left',padx=8)
        ttk.Button(u,text=self.tr('Changer mon PIN','تغيير PIN'),command=self.change_pin).pack(side="left",padx=8)
        ttk.Button(u,text=self.tr('Journal des actions','سجل العمليات'),command=self.audit_log).pack(side="left",padx=8)
        ttk.Button(u,text=self.tr('À propos - Aide','حول - مساعدة'),style='Soft.TButton',command=self.about_help).pack(side='left',padx=8)
        ttk.Button(u,text=self.tr('Licence','الترخيص'),style='Soft.TButton',command=self.license_tools).pack(side='left',padx=8)
        ttk.Button(u,text=self.tr('Raccourcis personnalisés','اختصارات مخصصة'),style='Soft.TButton',command=self.shortcut_tools).pack(side='left',padx=8)
        ttk.Label(u,text=self.tr('Admin initial: admin / PIN 1234 — changez-le.','المدير الأولي: admin / PIN 1234 — غيّره.')).pack(side="left",padx=15)
    def _settings_mousewheel(self,event):
        if not self.settings_canvas.winfo_exists():
            return
        delta=getattr(event,'delta',0)
        if delta:
            self.settings_canvas.yview_scroll(-1 if delta>0 else 1,'units')
            return 'break'

    def shortcut_tools(self):
        from services.shortcuts import ALLOWED_SHORTCUTS,get_shortcuts,save_shortcuts
        w=tk.Toplevel(self);w.title(self.tr('Raccourcis personnalisés','اختصارات مخصصة'));w.geometry('520x520');w.transient(self.winfo_toplevel());w.grab_set()
        ttk.Label(w,text=self.tr('Choisissez jusqu’à 6 fonctions à afficher directement sur l’écran de vente.','اختر حتى 6 وظائف لتظهر مباشرة في شاشة البيع.'),wraplength=470).pack(anchor='w',padx=16,pady=(16,10))
        labels={
            'calculator':self.tr('Calculatrice','الحاسبة'),
            'held':self.tr("Liste d’attente",'المعلقات'),
            'drawer':self.tr('Tiroir','درج النقود'),
            'duplicate':self.tr('Duplicata','نسخة التذكرة'),
            'price_grid':self.tr('Grille de prix','لائحة الأثمان'),
            'expense':self.tr('Dépenses','المصاريف'),
            'report':self.tr('Rapport','التقارير'),
            'closure':self.tr('Clôture','إغلاق الصندوق'),
            'keyboard':self.tr('Clavier tactile','لوحة المفاتيح'),
        }
        selected=set(get_shortcuts());vars={}
        body=ttk.Frame(w,padding=(16,4));body.pack(fill='both',expand=True)
        for key in ALLOWED_SHORTCUTS:
            var=tk.BooleanVar(value=key in selected);vars[key]=var
            ttk.Checkbutton(body,text=labels[key],variable=var).pack(anchor='w',pady=5)
        def save():
            keys=[key for key in ALLOWED_SHORTCUTS if vars[key].get()]
            if len(keys)>6:
                messagebox.showerror('ToDo',self.tr('Maximum 6 raccourcis.','الحد الأقصى 6 اختصارات.'),parent=w);return
            try:
                save_shortcuts(keys)
                try:
                    frame=self.app.frames.get('sale') if hasattr(self.app,'frames') else None
                    if frame and hasattr(frame,'build_custom_shortcuts'):frame.build_custom_shortcuts()
                except Exception:pass
                messagebox.showinfo('ToDo',self.tr('Raccourcis enregistrés.','تم حفظ الاختصارات.'),parent=w);w.destroy()
            except Exception as error:messagebox.showerror('ToDo',str(error),parent=w)
        bar=ttk.Frame(w);bar.pack(fill='x',padx=16,pady=16)
        ttk.Button(bar,text=self.tr('Enregistrer','حفظ'),style='Primary.TButton',command=save).pack(side='right')
        ttk.Button(bar,text=self.tr('Annuler','إلغاء'),command=w.destroy).pack(side='right',padx=6)

    def toggle_windows_startup(self):
        enabled=bool(self.start_with_windows.get())
        try:
            _sync_windows_startup(enabled)
            set_setting('start_with_windows','1' if enabled else '0')
        except Exception as error:
            self.start_with_windows.set(not enabled)
            messagebox.showerror('ToDo',self.tr(f"Impossible de modifier le démarrage Windows: {error}",f"تعذر تعديل تشغيل Windows: {error}"),parent=self)

    def toggle_windows_mode(self):
        enabled=bool(self.windows_mode.get())
        set_setting('windows_mode','1' if enabled else '0')
        try:self.app.apply_window_mode(enabled)
        except Exception as error:
            messagebox.showerror('ToDo',self.tr(f'Impossible de changer le mode fenêtre: {error}',f'تعذر تغيير وضع النافذة: {error}'),parent=self)


    def sync_stock_options(self):
        if self.block_insufficient.get(): self.neg.set(False)
        elif self.neg.get(): self.block_insufficient.set(False)

    def refresh_sellers(self):
        for w in self.sellers_frame.winfo_children():w.destroy()
        with connect() as c:rows=c.execute("SELECT id,name,active FROM sellers ORDER BY name COLLATE NOCASE").fetchall()
        for r in rows:
            line=ttk.Frame(self.sellers_frame);line.pack(fill="x",pady=2)
            ttk.Label(line,text=r["name"],width=30).pack(side="left")
            ttk.Label(line,text=self.tr("Actif","نشط") if r["active"] else self.tr("Inactif","معطل"),width=12).pack(side="left")
            ttk.Button(line,text=self.tr("Désactiver","تعطيل") if r["active"] else self.tr("Activer","تفعيل"),command=lambda sid=r["id"],a=r["active"]:self.toggle_seller(sid,a)).pack(side="left",padx=4)
    def add_seller(self):
        name=self.new_seller_name.get().strip()
        if not name:return
        try:
            with connect() as c:c.execute("INSERT INTO sellers(name,active) VALUES(?,1)",(name,))
            self.new_seller_name.set("");self.refresh_sellers()
        except Exception as e:messagebox.showerror("ToDo",str(e),parent=self)
    def toggle_seller(self,seller_id,active):
        with connect() as c:c.execute("UPDATE sellers SET active=? WHERE id=?",(0 if active else 1,seller_id))
        self.refresh_sellers()

    def refresh_payment_methods(self):
        from services.payment_methods import list_payment_methods
        for w in self.payment_methods_frame.winfo_children():w.destroy()
        for r in list_payment_methods():
            line=ttk.Frame(self.payment_methods_frame);line.pack(fill='x',pady=2)
            ttk.Label(line,text=r.get('icon') or '·',width=4).pack(side='left')
            ttk.Label(line,text=r['code'],width=12).pack(side='left')
            ttk.Label(line,text=r['name_fr'],width=22).pack(side='left')
            ttk.Label(line,text=r['name_ar'] or '—',width=18).pack(side='left')
            ttk.Label(line,text=self.tr('Actif','نشط') if r['active'] else self.tr('Inactif','معطل'),width=10).pack(side='left')
            if not r['system']:
                ttk.Button(line,text=self.tr('Désactiver','تعطيل') if r['active'] else self.tr('Activer','تفعيل'),
                           command=lambda mid=r['id'],a=r['active']:self.toggle_payment_method(mid,a)).pack(side='left',padx=4)

    def add_payment_method(self):
        from services.payment_methods import save_payment_method
        try:
            save_payment_method(self.new_payment_code.get(),self.new_payment_fr.get(),self.new_payment_ar.get(),self.new_payment_icon.get())
            self.new_payment_code.set('');self.new_payment_fr.set('');self.new_payment_ar.set('');self.new_payment_icon.set('');self.refresh_payment_methods()
        except Exception as e:messagebox.showerror('ToDo',str(e),parent=self)

    def toggle_payment_method(self,method_id,active):
        from services.payment_methods import set_payment_method_active
        try:set_payment_method_active(method_id,not bool(active));self.refresh_payment_methods()
        except Exception as e:messagebox.showerror('ToDo',str(e),parent=self)

    def refresh_price_grids(self):
        for w in self.price_grids_frame.winfo_children():w.destroy()
        with connect() as c:rows=c.execute("SELECT id,name,active FROM price_grids ORDER BY name COLLATE NOCASE").fetchall()
        for r in rows:
            line=ttk.Frame(self.price_grids_frame);line.pack(fill="x",pady=2)
            ttk.Label(line,text=r["name"],width=30).pack(side="left")
            ttk.Label(line,text=self.tr("Active","نشطة") if r["active"] else self.tr("Inactive","معطلة"),width=12).pack(side="left")
            ttk.Button(line,text=self.tr("Désactiver","تعطيل") if r["active"] else self.tr("Activer","تفعيل"),command=lambda gid=r["id"],a=r["active"]:self.toggle_price_grid(gid,a)).pack(side="left",padx=4)
    def add_price_grid(self):
        name=self.new_grid_name.get().strip()
        if not name:return
        try:
            with connect() as c:c.execute("INSERT INTO price_grids(name,active) VALUES(?,1)",(name,))
            self.new_grid_name.set("");self.refresh_price_grids()
        except Exception as e:messagebox.showerror("ToDo",str(e),parent=self)
    def toggle_price_grid(self,grid_id,active):
        with connect() as c:c.execute("UPDATE price_grids SET active=? WHERE id=?",(0 if active else 1,grid_id))
        self.refresh_price_grids()

    def sync_country_profile(self,event=None):
        profile=get_country_profile(self.country.get())
        self.cur.set(profile.currency)
        rate=f"{profile.default_tax_rate_basis_points/100:g}%"
        included=self.tr('taxe comprise','ضريبة مضمّنة') if profile.tax_included_by_default else self.tr('taxe ajoutée','ضريبة مضافة')
        self.country_info.set(f"{profile.currency} · {profile.tax_label} {rate} · {included}")

    def save(self):
        try:
            limit=int(self.search_limit.get())
            if limit<1 or limit>1000:raise ValueError()
        except ValueError:
            messagebox.showerror("ToDo",self.tr("Limite de recherche entre 1 et 1000.","حد البحث بين 1 و1000."),parent=self);return
        workstation=self.workstation.get().strip().upper()
        if not workstation or len(workstation)>16 or not all(ch.isalnum() or ch in '-_' for ch in workstation):
            messagebox.showerror('ToDo',self.tr('Identifiant poste invalide (lettres/chiffres, - ou _).','رقم محطة الصندوق غير صالح.'),parent=self);return
        set_setting("shop_name",self.shop.get().strip() or "ToDo")
        country_changed=self.country.get()!=get_setting('country_code','MA')
        if country_changed: select_country_profile(self.country.get())
        else: set_setting("currency",self.cur.get().strip() or "DH")
        set_setting('workstation_code',workstation);set_setting("allow_negative_stock","1" if self.neg.get() else "0")
        print_mode=self.print_mode.get() or "ask"
        if print_mode not in ('ask','always','never'):print_mode='ask'
        set_setting("receipt_footer",self.footer.get());set_setting("search_limit",limit);set_setting("printer_name",self.printer.get().strip());set_setting('printer_receipt_name',self.printer.get().strip());set_setting('printer_report_name',self.report_printer.get().strip());set_setting('printer_addition_name',self.addition_printer.get().strip())
        for i,var in enumerate(self.kitchen_printers,1):set_setting(f'printer_kitchen_c{i}_name',var.get().strip())
        template=self.receipt_template.get().strip().upper()
        if template not in ('FR_3C','FR_4C','FR_2L','EN_3C','EN_4C','AR_3C','AR_4C'):template='FR_3C'
        try:
            next_ticket=max(1,int(self.next_client_ticket.get()))
        except ValueError:
            messagebox.showerror('ToDo',self.tr('N° Ticket Client invalide.','رقم تذكرة الزبون غير صالح.'),parent=self);return
        set_setting('receipt_show_payment','1' if self.receipt_show_payment.get() else '0');set_setting('receipt_show_ticket_no','1' if self.receipt_show_ticket_no.get() else '0');set_setting('receipt_show_sale_mode','1' if self.receipt_show_sale_mode.get() else '0');set_setting('receipt_show_barcode','1' if self.receipt_show_barcode.get() else '0');set_setting('receipt_next_client_ticket',str(next_ticket))
        set_setting('receipt_template',template);set_setting("print_mode",print_mode)
        set_setting('thermal_raw','1' if self.thermal_raw.get() else '0');set_setting('receipt_chars',self.receipt_chars.get() if self.receipt_chars.get() in ('32','42','48') else '42');set_setting('drawer_enabled','1' if self.drawer_enabled.get() else '0');set_setting('drawer_pin',self.drawer_pin.get());set_setting('block_insufficient_stock','1' if self.block_insufficient.get() else '0');set_setting('manual_stock_edit_enabled','1' if self.manual_stock_edit_enabled.get() else '0');set_setting('stock_management_enabled','1' if self.stock_management_enabled.get() else '0');set_setting('credit_enabled','1' if self.credit_enabled.get() else '0');set_setting('closure_enabled','1' if self.closure_enabled.get() else '0');set_setting('sans_ticket_enabled','1' if self.sans_ticket_enabled.get() else '0');set_setting('payment_window_enabled','1' if self.payment_window_enabled.get() else '0');set_setting('require_client_on_sale','1' if self.require_client.get() else '0');set_setting('choose_seller_on_sale','1' if self.choose_seller.get() else '0');new_language=self.language.get();language_changed=new_language!=get_setting('language','fr');set_setting('language',new_language)
        try:
            seconds=int(self.customer_seconds.get())
            if seconds<2 or seconds>300:raise ValueError()
        except ValueError:
            messagebox.showerror("ToDo",self.tr("Durée écran client entre 2 et 300 secondes.","مدة شاشة الزبون بين 2 و300 ثانية."),parent=self);return
        try:
            scale_timeout=int(self.scale_timeout.get())
            scale_baud=int(self.scale_baudrate.get())
            if scale_timeout<100 or scale_timeout>10000 or scale_baud<=0:raise ValueError()
        except ValueError:
            messagebox.showerror('ToDo',self.tr('Paramètres de balance invalides.','إعدادات الميزان غير صالحة.'),parent=self);return
        set_setting('scale_enabled','1' if self.scale_enabled.get() else '0');set_setting('scale_port',self.scale_port.get().strip());set_setting('scale_baudrate',str(scale_baud));set_setting('scale_timeout_ms',str(scale_timeout))
        try:smtp_port=int(self.smtp_port.get())
        except ValueError:
            messagebox.showerror('ToDo',self.tr('Port SMTP invalide.','منفذ SMTP غير صالح.'),parent=self);return
        if smtp_port<1 or smtp_port>65535:
            messagebox.showerror('ToDo',self.tr('Port SMTP invalide.','منفذ SMTP غير صالح.'),parent=self);return
        try:
            rfid_baud=int(self.rfid_baud.get());rfid_timeout=int(self.rfid_timeout.get())
            if rfid_baud<=0 or rfid_timeout<100 or rfid_timeout>10000:raise ValueError()
        except ValueError:
            messagebox.showerror('ToDo',self.tr('Paramètres RFID invalides.','إعدادات RFID غير صالحة.'),parent=self);return
        set_setting('rfid_enabled','1' if self.rfid_enabled.get() else '0');set_setting('rfid_mode',self.rfid_mode.get());set_setting('rfid_port',self.rfid_port.get().strip());set_setting('rfid_baudrate',str(rfid_baud));set_setting('rfid_timeout_ms',str(rfid_timeout))
        set_setting('email_enabled','1' if self.email_enabled.get() else '0');set_setting('smtp_host',self.smtp_host.get().strip());set_setting('smtp_port',str(smtp_port));set_setting('smtp_user',self.smtp_user.get().strip());set_smtp_password(self.smtp_password.get());set_setting('smtp_from_name',self.smtp_from.get().strip() or 'ToDo');set_setting('smtp_subject',self.smtp_subject.get().strip())
        try:
            customer_serial_baud=int(self.customer_serial_baud.get());customer_serial_timeout=int(self.customer_serial_timeout.get());customer_serial_width=int(self.customer_serial_width.get())
            if customer_serial_baud<=0 or customer_serial_timeout<100 or customer_serial_timeout>10000 or customer_serial_width not in (16,20,24,40):raise ValueError()
        except ValueError:
            messagebox.showerror('ToDo',self.tr('Paramètres afficheur série invalides.','إعدادات الشاشة التسلسلية غير صالحة.'),parent=self);return
        set_setting('customer_serial_enabled','1' if self.customer_serial_enabled.get() else '0');set_setting('customer_serial_port',self.customer_serial_port.get().strip());set_setting('customer_serial_baudrate',str(customer_serial_baud));set_setting('customer_serial_timeout_ms',str(customer_serial_timeout));set_setting('customer_serial_width',str(customer_serial_width))
        set_setting('customer_display_enabled','1' if self.customer_enabled.get() else '0')
        set_setting("customer_slide_seconds",str(seconds))
        mode=self.customer_mode_labels.get(self.customer_mode_box.get(),'promotions')
        set_setting('customer_display_mode',mode)
        if self.app.customer_window and self.app.customer_window.winfo_exists():
            self.app._apply_customer_display_mode()
        backup_minutes=self.auto_backup.get()
        if backup_minutes not in ('0','5','10','15','30','60'):backup_minutes='15'
        set_setting("auto_backup_minutes",backup_minutes)
        self.app.schedule_auto_backup()
        messagebox.showinfo("ToDo",self.tr("Paramètres enregistrés.","تم حفظ الإعدادات."),parent=self)
        if language_changed:
            self.app.after_idle(lambda lang=new_language:self.app.change_language(lang))



    def refresh_rfid_ports(self):
        try:
            from services.rfid import serial_ports
            ports=serial_ports();self.rfid_port_box['values']=ports
            if not self.rfid_port.get() and ports:self.rfid_port.set(ports[0])
        except Exception as error:messagebox.showerror('ToDo',str(error),parent=self)

    def test_rfid(self):
        try:
            from services.rfid import read_tag
            tag=read_tag(self.rfid_port.get().strip(),int(self.rfid_baud.get()),int(self.rfid_timeout.get()))
            messagebox.showinfo('ToDo',self.tr(f'Tag lu : {tag}',f'تمت قراءة الوسم: {tag}'),parent=self)
        except Exception as error:messagebox.showerror('RFID',str(error),parent=self)

    def test_email(self):
        try:
            from services.emailer import test_email_connection
            cfg={'enabled':True,'host':self.smtp_host.get().strip(),'port':int(self.smtp_port.get()),'user':self.smtp_user.get().strip(),'password':self.smtp_password.get(),'from_name':self.smtp_from.get().strip() or 'ToDo','subject':self.smtp_subject.get().strip()}
            test_email_connection(settings=cfg)
            messagebox.showinfo('ToDo',self.tr('E-mail test envoyé.','تم إرسال بريد الاختبار.'),parent=self)
        except Exception as error:
            messagebox.showerror(self.tr('E-mail','البريد الإلكتروني'),str(error),parent=self)

    def refresh_scale_ports(self):
        try:
            from services.scale import serial_ports
            ports=serial_ports();self.scale_port_box['values']=ports
            if not self.scale_port.get() and ports:self.scale_port.set(ports[0])
        except Exception as error:
            messagebox.showerror('ToDo',str(error),parent=self)

    def test_scale(self):
        try:
            from services.scale import read_weight
            weight=read_weight(self.scale_port.get().strip(),int(self.scale_baudrate.get()),int(self.scale_timeout.get()))
            messagebox.showinfo('ToDo',self.tr(f'Poids lu : {weight:.3f} kg',f'الوزن المقروء: {weight:.3f} كغ'),parent=self)
        except Exception as error:
            messagebox.showerror(self.tr('Balance','الميزان'),str(error),parent=self)


    def refresh_customer_serial_ports(self):
        try:
            from services.customer_serial_display import serial_ports
            ports=serial_ports();self.customer_serial_port_box['values']=ports
            if not self.customer_serial_port.get() and ports:self.customer_serial_port.set(ports[0])
        except Exception as error:messagebox.showerror('ToDo',str(error),parent=self)

    def test_customer_serial(self):
        try:
            from services.customer_serial_display import write_lines
            write_lines('TODO MARKET','TEST OK',self.customer_serial_port.get().strip(),int(self.customer_serial_baud.get()),int(self.customer_serial_timeout.get()),int(self.customer_serial_width.get()))
            messagebox.showinfo('ToDo',self.tr('Test envoyé à l’afficheur.','تم إرسال الاختبار إلى الشاشة.'),parent=self)
        except Exception as error:messagebox.showerror(self.tr('Afficheur client','شاشة الزبون'),str(error),parent=self)

    def toggle_customer_enabled(self):
        enabled=bool(self.customer_enabled.get())
        set_setting('customer_display_enabled','1' if enabled else '0')
        opened=bool(self.app.customer_window and self.app.customer_window.winfo_exists())
        if enabled and not opened:
            self.app.toggle_customer_display()
        elif not enabled and opened:
            self.app.toggle_customer_display()

    def test_customer(self):
        mode=self.customer_mode_labels.get(self.customer_mode_box.get(),'promotions')
        if not (self.app.customer_window and self.app.customer_window.winfo_exists()):
            self.app.toggle_customer_display()
        self.app._apply_customer_display_mode(mode)

    def test_printer(self):
        try:
            from services.printers import test_printer
            test_printer(self.printer.get().strip(),bool(self.thermal_raw.get()))
            messagebox.showinfo('ToDo',self.tr('Test envoyé à l’imprimante.','تم إرسال الاختبار إلى الطابعة.'),parent=self)
        except Exception as error:
            messagebox.showerror('ToDo',str(error),parent=self)


    def regenerate_client_ticket_no(self):
        try:
            with connect() as conn:
                row=conn.execute('SELECT COALESCE(MAX(client_ticket_no),0)+1 next_no FROM sales').fetchone()
                value=max(1,int(row['next_no']))
            self.next_client_ticket.set(str(value))
            set_setting('receipt_next_client_ticket',str(value))
            messagebox.showinfo('ToDo',self.tr(f'Prochain N° Ticket Client : {value}',f'رقم تذكرة الزبون التالي: {value}'),parent=self)
        except Exception as error:messagebox.showerror('ToDo',str(error),parent=self)

    def refresh_printers(self):
        from services.printers import installed_printers
        try:
            values=installed_printers()
            self.printer_choice['values']=values;self.report_printer_choice['values']=values;self.addition_printer_choice['values']=values
            for cb in self.kitchen_printer_choices:cb['values']=values
        except Exception as error:messagebox.showerror(self.tr('Imprimantes','الطابعات'),str(error),parent=self)

    def backup(self):
        try:
            p=create_backup()
            messagebox.showinfo("ToDo",self.tr(f"Backup:\n{p}",f"نسخة احتياطية:\n{p}"),parent=self)
        except Exception as e:messagebox.showerror("ToDo",str(e),parent=self)
    def restore(self):
        p=filedialog.askopenfilename(parent=self,filetypes=[("SQLite DB","*.db"),(self.tr("Tous les fichiers","كل الملفات"),"*.*")])
        if not p:return
        if not messagebox.askyesno("ToDo",self.tr("Restaurer ce backup ? Une copie de sécurité sera créée.","استرجاع هذه النسخة؟ سيتم إنشاء نسخة أمان أولاً."),parent=self):return
        try:
            s=restore_backup(p)
            messagebox.showinfo("ToDo",self.tr(f"Restauré. Copie sécurité: {s}\nLe programme va se fermer. Relancez ToDo.",f"تم الاسترجاع. نسخة الأمان: {s}\nسيتم إغلاق البرنامج. أعد تشغيل ToDo."),parent=self)
            self.app.destroy()
        except Exception as e:messagebox.showerror("ToDo",str(e),parent=self)
    def full_backup(self):
        try:
            p=create_full_backup()
            messagebox.showinfo("ToDo",self.tr(f"Backup complet créé:\n{p}",f"تم إنشاء النسخة الكاملة:\n{p}"),parent=self)
        except Exception as e:messagebox.showerror("ToDo",str(e),parent=self)
    def full_restore(self):
        p=filedialog.askopenfilename(parent=self,filetypes=[("ToDo Full Backup","*.todozip")])
        if not p:return
        if not messagebox.askyesno("ToDo",self.tr("Restaurer toutes les données et médias ? Une copie complète de sécurité sera créée.","استرجاع جميع البيانات والوسائط؟ سيتم إنشاء نسخة أمان كاملة أولاً."),parent=self):return
        try:
            safety=restore_full_backup(p)
            messagebox.showinfo("ToDo",self.tr(f"Restauration complète terminée.\nCopie sécurité: {safety}\nToDo va se fermer.","تم الاسترجاع الكامل.\nنسخة الأمان: {safety}\nسيتم إغلاق ToDo."),parent=self)
            self.app.destroy()
        except Exception as e:messagebox.showerror("ToDo",str(e),parent=self)



    def license_tools(self):
        from services.license import license_status,machine_fingerprint,install_license
        from services.license_policy import load_license_policy,save_license_policy
        w=tk.Toplevel(self);w.title(self.tr('Licence','الترخيص'));w.geometry('720x470');w.transient(self.winfo_toplevel());w.grab_set()
        status=license_status()
        ttk.Label(w,text=self.tr('Licence ToDo','ترخيص ToDo'),style='Title.TLabel').pack(anchor='w',padx=18,pady=(16,8))
        box=ttk.LabelFrame(w,text=self.tr('État','الحالة'),padding=12);box.pack(fill='x',padx=18,pady=8)
        rows=[
            (self.tr('Machine ID','معرف الجهاز'),status['machine_id']),
            (self.tr('Protection active','الحماية مفعلة'),self.tr('Oui','نعم') if status['enforced'] else self.tr('Non','لا')),
            (self.tr('Licence installée','الترخيص مثبت'),self.tr('Oui','نعم') if status['installed'] else self.tr('Non','لا')),
            (self.tr('Valide','صالح'),self.tr('Oui','نعم') if status['valid'] else self.tr('Non','لا')),
            (self.tr('Client','الزبون'),status.get('customer') or '—'),
            (self.tr('Date de lancement','تاريخ البداية'),status.get('issued_at') or '—'),
            (self.tr('Expiration','الانتهاء'),status.get('expires_at') or '—'),
            (self.tr('Jours restants','الأيام المتبقية'),str(status.get('days_remaining')) if status.get('days_remaining') is not None else '—'),
            (self.tr('Message','الرسالة'),status.get('error') or self.tr('OK','سليم')),
        ]
        for i,(label,value) in enumerate(rows):
            ttk.Label(box,text=label+':',font=('Segoe UI',9,'bold')).grid(row=i,column=0,sticky='nw',pady=3)
            ttk.Label(box,text=value,wraplength=480).grid(row=i,column=1,sticky='w',padx=8,pady=3)
        keybox=ttk.LabelFrame(w,text=self.tr('Configuration administrateur','إعداد المدير'),padding=12);keybox.pack(fill='x',padx=18,pady=8)
        policy=load_license_policy()
        keyvar=tk.StringVar(value=policy['public_key_b64'])
        enforce=tk.BooleanVar(value=policy['enforced'])
        ttk.Label(keybox,text=self.tr('Clé publique Ed25519 (Base64)','المفتاح العام Ed25519 (Base64)')).grid(row=0,column=0,sticky='w')
        ttk.Entry(keybox,textvariable=keyvar,width=62).grid(row=1,column=0,columnspan=2,sticky='ew',pady=4)
        ttk.Checkbutton(keybox,text=self.tr('Activer la protection licence au démarrage','تفعيل حماية الترخيص عند التشغيل'),variable=enforce).grid(row=2,column=0,columnspan=2,sticky='w',pady=4)
        def save_cfg():
            key=keyvar.get().strip()
            if enforce.get() and not key:
                messagebox.showerror('ToDo',self.tr('Clé publique obligatoire avant activation.','المفتاح العام مطلوب قبل التفعيل.'),parent=w);return
            try:save_license_policy(key,enforce.get())
            except Exception as e:
                messagebox.showerror('ToDo',str(e),parent=w);return
            messagebox.showinfo('ToDo',self.tr('Configuration licence enregistrée.','تم حفظ إعدادات الترخيص.'),parent=w);w.destroy()
        def activate():
            path=filedialog.askopenfilename(parent=w,filetypes=[('ToDo Licence','*.json'),(self.tr('Tous les fichiers','كل الملفات'),'*.*')])
            if not path:return
            try:
                result=install_license(path)
                messagebox.showinfo('ToDo',self.tr(f"Licence activée pour {result['customer']} jusqu'au {result['expires_at']}.",f"تم تفعيل الترخيص لـ {result['customer']} حتى {result['expires_at']}."),parent=w);w.destroy()
            except Exception as error:messagebox.showerror('ToDo',str(error),parent=w)
        bar=ttk.Frame(w);bar.pack(fill='x',padx=18,pady=12)
        ttk.Button(bar,text=self.tr('Installer licence','تثبيت الترخيص'),style='Primary.TButton',command=activate).pack(side='left')
        ttk.Button(bar,text=self.tr('Enregistrer configuration','حفظ الإعداد'),command=save_cfg).pack(side='left',padx=6)
        ttk.Button(bar,text=self.tr('Fermer','إغلاق'),command=w.destroy).pack(side='right')

    def about_help(self):
        from services.support import diagnostics,diagnostic_text,documentation_paths,open_document
        w=tk.Toplevel(self);w.title(self.tr('À propos - Aide','حول - مساعدة'));w.geometry('760x590');w.transient(self.winfo_toplevel())
        try:d=diagnostics()
        except Exception as error:
            messagebox.showerror('ToDo',str(error),parent=w);w.destroy();return
        ttk.Label(w,text=f"ToDo POS {d['version']}",style='Title.TLabel').pack(anchor='w',padx=18,pady=(16,4))
        ttk.Label(w,text=self.tr('Centre d’aide et diagnostic local','مركز المساعدة والتشخيص المحلي'),foreground='#64748B').pack(anchor='w',padx=18,pady=(0,12))
        info=ttk.LabelFrame(w,text=self.tr('Diagnostic','التشخيص'),padding=12);info.pack(fill='x',padx=18,pady=6)
        entries=[
            (self.tr('Magasin','المتجر'),d['shop']),
            (self.tr('Poste','المحطة'),d['workstation']),
            ('SQLite / schema',f"{d['sqlite_version']} / {d['schema_version']}"),
            (self.tr('Intégrité','سلامة البيانات'),d['integrity']),
            (self.tr('Tables','الجداول'),str(d['tables'])),
            (self.tr('Taille base','حجم القاعدة'),f"{d['db_size_bytes']/1024/1024:.2f} MB"),
            (self.tr('Base de données','قاعدة البيانات'),d['db_path']),
            (self.tr('Dernier backup','آخر نسخة احتياطية'),d['last_backup'] or self.tr('Aucun trouvé','لا توجد')),
            (self.tr('PIN admin','PIN المدير'),self.tr('À CHANGER (1234)','يجب تغييره (1234)') if d['default_admin_pin'] else 'OK'),
        ]
        for i,(label,value) in enumerate(entries):
            ttk.Label(info,text=label+':',font=('Segoe UI',9,'bold')).grid(row=i,column=0,sticky='nw',pady=3)
            ttk.Label(info,text=value,wraplength=520).grid(row=i,column=1,sticky='w',padx=10,pady=3)
        docs=ttk.LabelFrame(w,text=self.tr('Documentation','الوثائق'),padding=12);docs.pack(fill='x',padx=18,pady=8)
        labels=[
            ('guide_fr',self.tr('Guide utilisateur FR','دليل المستخدم بالفرنسية')),
            ('guide_ar',self.tr('Guide utilisateur AR','دليل المستخدم بالعربية')),
            ('backup',self.tr('Backup / Restore','النسخ الاحتياطي / الاسترجاع')),
            ('install',self.tr('Installation Windows','تثبيت Windows')),
            ('checklist',self.tr('Checklist livraison','قائمة فحص التسليم')),
            ('privacy',self.tr('Politique de confidentialité','سياسة الخصوصية')),
            ('terms',self.tr("Conditions d’utilisation",'شروط الاستخدام')),
            ('support',self.tr('Support et données','الدعم والبيانات')),
        ]
        paths=documentation_paths()
        for i,(key,label) in enumerate(labels):
            state='normal' if paths[key].is_file() else 'disabled'
            ttk.Button(docs,text=label,state=state,command=lambda k=key:self.open_help_document(k,w)).grid(row=i//2,column=i%2,sticky='ew',padx=4,pady=4)
        docs.columnconfigure(0,weight=1);docs.columnconfigure(1,weight=1)
        from services.demo import launcher_path
        demo_state='normal' if launcher_path().is_file() else 'disabled'
        ttk.Button(docs,text=self.tr('Lancer la démo isolée','تشغيل النسخة التجريبية المعزولة'),state=demo_state,command=lambda:self.launch_isolated_demo(w)).grid(row=4,column=0,columnspan=2,sticky='ew',padx=4,pady=(8,4))
        def copy_diag():
            text_value=diagnostic_text();w.clipboard_clear();w.clipboard_append(text_value)
            messagebox.showinfo('ToDo',self.tr('Diagnostic copié.','تم نسخ التشخيص.'),parent=w)
        bar=ttk.Frame(w);bar.pack(fill='x',padx=18,pady=12)
        ttk.Button(bar,text=self.tr('Copier diagnostic','نسخ التشخيص'),style='Primary.TButton',command=copy_diag).pack(side='left')
        ttk.Button(bar,text=self.tr('Base de Données','قاعدة البيانات'),command=lambda:(w.destroy(),self.database_tools())).pack(side='left',padx=6)
        ttk.Button(bar,text=self.tr('Fermer','إغلاق'),command=w.destroy).pack(side='right')

    def launch_isolated_demo(self,parent):
        try:
            from services.demo import launch_demo
            launch_demo()
            messagebox.showinfo('ToDo',self.tr('La démo s’ouvre avec sa propre base de données.','سيتم فتح النسخة التجريبية بقاعدة بيانات مستقلة.'),parent=parent)
        except FileNotFoundError:
            messagebox.showinfo('ToDo',self.tr('La démo n’est disponible que dans le package Windows qui l’inclut.','النسخة التجريبية متاحة فقط في حزمة Windows التي تتضمنها.'),parent=parent)
        except Exception as error:
            messagebox.showerror('ToDo',str(error),parent=parent)

    def open_help_document(self,key,parent):
        try:
            from services.support import open_document
            open_document(key)
        except Exception as error:messagebox.showerror(self.tr('Aide','المساعدة'),str(error),parent=parent)

    def database_tools(self):
        from services.database_admin import table_inventory,export_table_csv,import_reference_csv,integrity_status,export_schema_sql,export_database_bundle
        w=tk.Toplevel(self);w.title(self.tr('Base de Données','قاعدة البيانات'));w.geometry('850x590');w.transient(self.winfo_toplevel());w.grab_set()
        warning=self.tr("ATTENTION ! Les tables de ventes, caisse et stock sont protégées contre l'import direct. Utilisez Backup/Restore pour une migration complète.",
                        "انتباه! جداول المبيعات والصندوق والمخزون محمية من الاستيراد المباشر. استعمل النسخ الاحتياطي/الاسترجاع للنقل الكامل.")
        tk.Label(w,text=warning,bg='#FEF2F2',fg='#B91C1C',font=('Segoe UI',10,'bold'),wraplength=790,justify='left',padx=12,pady=10).pack(fill='x',padx=12,pady=12)
        tree=ttk.Treeview(w,columns=('table','rows','import'),show='headings',height=18)
        tree.heading('table',text=self.tr('Table','الجدول'));tree.heading('rows',text=self.tr('Lignes','السجلات'));tree.heading('import',text=self.tr('Import CSV','استيراد CSV'))
        tree.column('table',width=330);tree.column('rows',width=120,anchor='center');tree.column('import',width=180,anchor='center')
        tree.pack(fill='both',expand=True,padx=12)
        status=ttk.Label(w,text='');status.pack(fill='x',padx=12,pady=(5,0))
        def refresh():
            tree.delete(*tree.get_children())
            for row in table_inventory():
                tree.insert('','end',iid=row['name'],values=(row['name'],row['rows'],self.tr('Autorisé','مسموح') if row['importable'] else self.tr('Export seulement','تصدير فقط')))
        def selected():
            s=tree.selection()
            if not s:messagebox.showwarning('ToDo',self.tr('Sélectionnez une table.','اختر جدولا.'),parent=w);return None
            return s[0]
        def export_csv():
            table=selected()
            if not table:return
            path=filedialog.asksaveasfilename(parent=w,defaultextension='.csv',filetypes=[('CSV','*.csv')],initialfile=table+'.csv')
            if not path:return
            try:
                export_table_csv(table,path);status.config(text=self.tr(f'Export terminé : {path}',f'تم التصدير: {path}'))
            except Exception as e:messagebox.showerror('ToDo',str(e),parent=w)
        def import_csv():
            table=selected()
            if not table:return
            allowed={r['name'] for r in table_inventory() if r['importable']}
            if table not in allowed:
                messagebox.showerror('ToDo',self.tr('Import direct interdit pour cette table.','الاستيراد المباشر ممنوع لهذا الجدول.'),parent=w);return
            path=filedialog.askopenfilename(parent=w,filetypes=[('CSV','*.csv')])
            if not path:return
            if not messagebox.askyesno('ToDo',self.tr('Importer ce CSV ? Un backup de sécurité sera créé automatiquement.','استيراد CSV؟ سيتم إنشاء نسخة أمان تلقائيا.'),parent=w):return
            try:
                result=import_reference_csv(table,path);refresh()
                messagebox.showinfo('ToDo',self.tr(f"{result['rows']} ligne(s) importée(s).\nBackup: {result['safety']}",f"تم استيراد {result['rows']} سجل.\nنسخة الأمان: {result['safety']}"),parent=w)
            except Exception as e:messagebox.showerror('ToDo',str(e),parent=w)
        def export_schema():
            path=filedialog.asksaveasfilename(parent=w,defaultextension='.sql',filetypes=[('SQL','*.sql')],initialfile='todo_schema.sql')
            if not path:return
            try:
                result=export_schema_sql(path);status.config(text=self.tr(f'Schéma exporté : {result}',f'تم تصدير البنية: {result}'))
            except Exception as e:messagebox.showerror('ToDo',str(e),parent=w)
        def export_bundle():
            path=filedialog.asksaveasfilename(parent=w,defaultextension='.zip',filetypes=[('ZIP','*.zip')],initialfile='todo_database_export.zip')
            if not path:return
            try:
                result=export_database_bundle(path);status.config(text=self.tr(f'Export complet : {result}',f'تم التصدير الكامل: {result}'))
            except Exception as e:messagebox.showerror('ToDo',str(e),parent=w)
        def check():
            try:
                result=integrity_status()
                text_value=self.tr('Base saine.','قاعدة البيانات سليمة.') if result['ok'] else self.tr(f"Problème: {result['integrity']} · FK {result['foreign_key_errors']}",f"مشكلة: {result['integrity']} · العلاقات {result['foreign_key_errors']}")
                messagebox.showinfo(self.tr('Intégrité','سلامة البيانات'),text_value,parent=w)
            except Exception as e:messagebox.showerror('ToDo',str(e),parent=w)
        bar=ttk.Frame(w);bar.pack(fill='x',padx=12,pady=12)
        ttk.Button(bar,text=self.tr('Actualiser','تحديث'),command=refresh).pack(side='left')
        ttk.Button(bar,text=self.tr('Exporter CSV','تصدير CSV'),style='Soft.TButton',command=export_csv).pack(side='left',padx=6)
        ttk.Button(bar,text=self.tr('Importer CSV','استيراد CSV'),style='Primary.TButton',command=import_csv).pack(side='left',padx=6)
        ttk.Button(bar,text=self.tr('Exporter schéma SQL','تصدير بنية SQL'),command=export_schema).pack(side='left',padx=6)
        ttk.Button(bar,text=self.tr('Export complet ZIP','تصدير كامل ZIP'),command=export_bundle).pack(side='left',padx=6)
        ttk.Button(bar,text=self.tr("Vérifier l'intégrité",'فحص سلامة البيانات'),command=check).pack(side='left',padx=6)
        ttk.Button(bar,text=self.tr('Fermer','إغلاق'),command=w.destroy).pack(side='right')
        refresh()

    def new_user(self):
        user=simpledialog.askstring(self.tr("Utilisateur","المستخدم"),self.tr("Username:","اسم المستخدم:"),parent=self)
        if not user:return
        name=simpledialog.askstring(self.tr("Utilisateur","المستخدم"),self.tr("Nom affiché:","الاسم المعروض:"),parent=self) or user
        pin=simpledialog.askstring(self.tr("Utilisateur","المستخدم"),"PIN:",parent=self,show="*")
        if not pin:return
        if not pin.isdigit() or len(pin)<4:
            messagebox.showerror("ToDo",self.tr("PIN : au moins 4 chiffres","PIN: أربعة أرقام على الأقل"),parent=self);return
        role=simpledialog.askstring(self.tr("Utilisateur","المستخدم"),self.tr("Rôle (admin/cashier):","الصلاحية (admin/cashier):"),parent=self) or "cashier"
        if role not in ("admin","cashier"):
            messagebox.showerror("ToDo",self.tr("Rôle invalide","صلاحية غير صالحة"),parent=self);return
        try:
            with connect() as c:c.execute("INSERT INTO users(username,display_name,pin_hash,role) VALUES(?,?,?,?)",(user,name,hash_pin(pin),role));c.commit()
            messagebox.showinfo("ToDo",self.tr("Utilisateur créé.","تم إنشاء المستخدم."),parent=self)
        except Exception as e:messagebox.showerror("ToDo",str(e),parent=self)

    def manage_users(self):
        with connect() as conn: require_admin(conn)
        w=tk.Toplevel(self);w.title(self.tr("Utilisateurs","المستخدمون"));w.geometry("720x500");w.transient(self.winfo_toplevel())
        tree=ttk.Treeview(w,columns=("id","username","name","role","active"),show="headings")
        for key,label,width in [("id","ID",55),("username",self.tr("Utilisateur","المستخدم"),150),("name",self.tr("Nom","الاسم"),190),("role",self.tr("Rôle","الصلاحية"),100),("active",self.tr("Actif","نشط"),70)]:tree.heading(key,text=label);tree.column(key,width=width,anchor="center" if key in ("id","role","active") else "w")
        tree.pack(fill="both",expand=True,padx=12,pady=12);bar=ttk.Frame(w);bar.pack(fill="x",padx=12,pady=(0,12))
        def reload():
            tree.delete(*tree.get_children())
            with connect() as conn: rows=conn.execute("SELECT id,username,display_name,role,active FROM users ORDER BY display_name").fetchall()
            for r in rows:
                role_label=self.tr("Administrateur","مدير") if r["role"]=="admin" else self.tr("Caissier","كاشير") if r["role"]=="cashier" else r["role"]
                tree.insert("","end",iid=str(r["id"]),values=(r["id"],r["username"],r["display_name"],role_label,self.tr("Oui","نعم") if r["active"] else self.tr("Non","لا")))
        def selected():
            sel=tree.selection()
            if not sel: messagebox.showwarning(self.tr("Utilisateurs","المستخدمون"),self.tr("Sélectionnez un utilisateur.","اختر مستخدماً."),parent=w);return None
            return int(sel[0])
        def toggle():
            uid=selected()
            if uid is None:return
            if uid==self.app.user["id"]:messagebox.showwarning(self.tr("Utilisateurs","المستخدمون"),self.tr("Impossible de désactiver votre propre compte.","لا يمكن تعطيل حسابك الحالي."),parent=w);return
            with connect() as conn:
                require_admin(conn);row=conn.execute("SELECT active FROM users WHERE id=?",(uid,)).fetchone();new=0 if row["active"] else 1
                conn.execute("UPDATE users SET active=? WHERE id=?",(new,uid));audit(conn,"USER_ACTIVE_TOGGLE",uid,str(new));conn.commit()
            reload()
        def role():
            uid=selected()
            if uid is None:return
            if uid==self.app.user["id"]:messagebox.showwarning(self.tr("Utilisateurs","المستخدمون"),self.tr("Modifiez un autre compte.","اختر حساباً آخر للتعديل."),parent=w);return
            with connect() as conn:
                require_admin(conn);row=conn.execute("SELECT role FROM users WHERE id=?",(uid,)).fetchone();new="admin" if row["role"]!="admin" else "cashier"
                conn.execute("UPDATE users SET role=? WHERE id=?",(new,uid));audit(conn,"USER_ROLE_CHANGE",uid,new);conn.commit()
            reload()
        def permissions():
            uid=selected()
            if uid is None:return
            from services.security import PERMISSIONS,list_user_permissions,set_user_permission
            values=list_user_permissions(uid)
            pw=tk.Toplevel(w);pw.title(self.tr('Permissions utilisateur','صلاحيات المستخدم'));pw.transient(w);pw.grab_set()
            vars={}
            for i,(code,(fr,ar)) in enumerate(PERMISSIONS.items()):
                var=tk.BooleanVar(value=values.get(code,False));vars[code]=var
                ttk.Checkbutton(pw,text=self.tr(fr,ar),variable=var).grid(row=i,column=0,sticky='w',padx=18,pady=6)
            def save_permissions():
                try:
                    with connect() as conn:
                        conn.execute('BEGIN IMMEDIATE');require_admin(conn)
                        for code,var in vars.items():set_user_permission(uid,code,var.get(),conn)
                        conn.commit()
                    pw.destroy()
                except Exception as e:messagebox.showerror('ToDo',str(e),parent=pw)
            ttk.Button(pw,text=self.tr('Enregistrer','حفظ'),style='Success.TButton',command=save_permissions).grid(row=len(vars),column=0,sticky='ew',padx=18,pady=12)
        ttk.Button(bar,text=self.tr('Activer / Désactiver','تفعيل / تعطيل'),command=toggle).pack(side="left")
        ttk.Button(bar,text=self.tr('Admin ↔ Caissier','مدير ↔ كاشير'),command=role).pack(side="left",padx=8)
        ttk.Button(bar,text=self.tr('Permissions','الصلاحيات'),command=permissions).pack(side='left',padx=8);reload()

    def change_pin(self):
        pin=simpledialog.askstring('PIN',self.tr('Nouveau PIN (4 chiffres minimum):','PIN جديد (4 أرقام على الأقل):'),parent=self,show='*')
        if pin is None:return
        if not pin.isdigit() or len(pin)<4:
            messagebox.showerror('ToDo',self.tr('Utilisez au moins 4 chiffres.','استعمل أربعة أرقام على الأقل.'),parent=self);return
        with connect() as conn:
            conn.execute('UPDATE users SET pin_hash=? WHERE id=?',(hash_pin(pin),self.app.user['id']))
            audit(conn,'PIN_CHANGE',self.app.user['id'])
        messagebox.showinfo('ToDo',self.tr('PIN modifié.','تم تغيير PIN.'),parent=self)

    def audit_log(self):
        w=tk.Toplevel(self);w.title(self.tr('Journal des actions','سجل العمليات'));w.geometry('960x520')
        tree=ttk.Treeview(w,columns=('date','user','action','document','details'),show='headings')
        for key,label,width in [('date',self.tr('Date','التاريخ'),150),('user',self.tr('Utilisateur','المستخدم'),140),('action',self.tr('Action','العملية'),140),('document',self.tr('Document','الوثيقة'),100),('details',self.tr('Détails','التفاصيل'),300)]:
            tree.heading(key,text=label);tree.column(key,width=width)
        tree.pack(fill='both',expand=True,padx=12,pady=12)
        with connect() as conn:
            rows=conn.execute("SELECT a.*,u.display_name username FROM audit_log a LEFT JOIN users u ON u.id=a.user_id ORDER BY a.id DESC LIMIT 1000").fetchall()
        for r in rows:tree.insert('','end',values=(r['created_at'],r['username'] or self.tr('Système','النظام'),r['action'],r['document'],r['details']))
