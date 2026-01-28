
import customtkinter as ctk
from datetime import date
from config import COLORS, FONTS
from utils.format_helper import parse_localized_float, parse_fuzzy_date

class RecordEditorDialog(ctk.CTkToplevel):
    def __init__(self, parent, record=None):
        super().__init__(parent)
        self.title("Editar Registro" if record else "Nuevo Registro")
        self.geometry("600x650")
        
        # Modal
        self.transient(parent)
        self.grab_set()
        # UI Focus Fix
        self.lift()
        self.focus_force()
        self.attributes("-topmost", True)
        
        self.record = record
        self.result = None
        self.matched_id = None
        self.files = {} # {'invoice': path, 'payment': path}
        
        self._init_ui()
        if record: self._load_data()
        
    def _init_ui(self):
        # Main Background matching the app theme
        self.configure(fg_color="#F0F2F5") # Light Gray similar to ResolutionDialog
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # --- MAIN CARD ---
        self.card = ctk.CTkFrame(self, fg_color="white", corner_radius=15, border_width=1, border_color="#D5D8DC")
        self.card.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.card.grid_columnconfigure(1, weight=1)
        
        # Header
        ctk.CTkLabel(self.card, text="📝 Detalles del Registro", font=("Segoe UI", 16, "bold"), text_color="#2C3E50").grid(row=0, column=0, columnspan=2, pady=(20, 15))
        
        # --- LEFT SIDE: MANUAL EDIT ---
        # Date
        ctk.CTkLabel(self.card, text="Fecha:", font=("Segoe UI", 12, "bold"), text_color="gray").grid(row=1, column=0, padx=20, pady=5, sticky="w")
        self.entry_date = ctk.CTkEntry(self.card, width=150, placeholder_text="DD/MM/AAAA")
        self.entry_date.grid(row=1, column=1, padx=20, pady=5, sticky="ew")
        
        # Concept
        ctk.CTkLabel(self.card, text="Concepto:", font=("Segoe UI", 12, "bold"), text_color="gray").grid(row=2, column=0, padx=20, pady=5, sticky="w")
        self.entry_desc = ctk.CTkEntry(self.card, placeholder_text="Descripción del movimiento...")
        self.entry_desc.grid(row=2, column=1, padx=20, pady=5, sticky="ew")
        
        # Amount CSV (Bank)
        ctk.CTkLabel(self.card, text="Monto Banco:", font=("Segoe UI", 12, "bold"), text_color="gray").grid(row=3, column=0, padx=20, pady=5, sticky="w")
        self.entry_amt_csv = ctk.CTkEntry(self.card)
        self.entry_amt_csv.grid(row=3, column=1, padx=20, pady=5, sticky="ew")

        # Amount System
        ctk.CTkLabel(self.card, text="Monto Sistema:", font=("Segoe UI", 12, "bold"), text_color="gray").grid(row=4, column=0, padx=20, pady=5, sticky="w")
        self.entry_amt_sys = ctk.CTkEntry(self.card)
        self.entry_amt_sys.grid(row=4, column=1, padx=20, pady=5, sticky="ew")
        
        # Status
        ctk.CTkLabel(self.card, text="Estado:", font=("Segoe UI", 12, "bold"), text_color="gray").grid(row=5, column=0, padx=20, pady=5, sticky="w")
        self.combo_status = ctk.CTkComboBox(self.card, values=["CONCILIADO", "NO_EN_SISTEMA", "NO_EN_BANCO", "DIFERENCIA_FECHA"])
        self.combo_status.grid(row=5, column=1, padx=20, pady=5, sticky="ew")
        
        self.combo_status.grid(row=5, column=1, padx=20, pady=5, sticky="ew")

        # --- FILES SECTION ---
        ctk.CTkLabel(self.card, text="Documentos:", font=("Segoe UI", 12, "bold"), text_color="gray").grid(row=6, column=0, padx=20, pady=5, sticky="w")
        
        files_frame = ctk.CTkFrame(self.card, fg_color="transparent")
        files_frame.grid(row=6, column=1, padx=20, pady=5, sticky="ew")
        
        self.btn_invoice = ctk.CTkButton(files_frame, text="📄 Factura", command=lambda: self._pick_file('invoice'), fg_color=COLORS["secondary_button"], width=100)
        self.btn_invoice.pack(side="left", padx=2)
        
        self.btn_payment = ctk.CTkButton(files_frame, text="💸 Comprobante", command=lambda: self._pick_file('payment'), fg_color=COLORS["secondary_button"], width=100)
        self.btn_payment.pack(side="left", padx=2)
        
        self.lbl_files = ctk.CTkLabel(files_frame, text="", text_color="gray", font=("Segoe UI", 10))
        self.lbl_files.pack(side="left", padx=5)

        # Separator
        
        ctk.CTkLabel(self.card, text="🔍 Buscar Coincidencia en Sistema", font=("Segoe UI", 12, "bold"), text_color="#3498DB").grid(row=7, column=0, columnspan=2, pady=(0, 5))
        
        search_frame = ctk.CTkFrame(self.card, fg_color="#F8F9F9", corner_radius=8)
        search_frame.grid(row=8, column=0, columnspan=2, padx=20, sticky="ew")
        
        self.entry_search = ctk.CTkEntry(search_frame, placeholder_text="Buscar nombre, fecha o monto...", border_width=0)
        self.entry_search.pack(side="left", fill="x", expand=True, padx=5, pady=5)
        self.entry_search.bind("<Return>", lambda e: self.search_sys())
        
        ctk.CTkButton(search_frame, text="🔍", width=30, command=self.search_sys, fg_color="transparent", text_color="gray", hover_color="#D5D8DC").pack(side="right", padx=5)
        
        self.combo_results = ctk.CTkComboBox(self.card, values=["Use el buscador..."], command=self.on_select_sys)
        self.combo_results.grid(row=9, column=0, columnspan=2, padx=20, pady=(10, 20), sticky="ew")
        
        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=1, column=0, pady=10)
        
        ctk.CTkButton(btn_frame, text="Cancelar", command=self.destroy, fg_color="transparent", border_width=1, text_color="gray").pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Guardar Cambios", command=self.save, fg_color=COLORS["primary_button"], width=150).pack(side="left", padx=10)

    def _load_data(self):
        d = self.record.get("fecha", date.today())
        d_str = ""
        try:
            if hasattr(d, 'strftime'): d_str = d.strftime("%d/%m/%Y")
            elif isinstance(d, str):
                 if "-" in d and len(d)>=10: 
                     from datetime import datetime
                     d_str = datetime.strptime(d[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
                 else: d_str = d
        except: d_str = str(d)
        
        self.entry_date.insert(0, d_str)
        self.entry_desc.insert(0, self.record.get("concepto", ""))
        self.entry_amt_csv.insert(0, str(self.record.get("valor_csv", 0.0)))
        self.entry_amt_sys.insert(0, str(self.record.get("valor_db", 0.0)))
        
        st = self.record.get("status", "NO_EN_SISTEMA")
        if st == "MATCH": st = "CONCILIADO"
        self.combo_status.set(st)

    def search_sys(self):
        term = self.entry_search.get()
        # Assume parent is ReconciliationView -> has controller
        if hasattr(self.master, 'controller'):
             results = self.master.controller.search_vencimientos(term)
             self.results_map = {f"${r['monto']} - {r['descripcion']}": r for r in results}
             vals = list(self.results_map.keys())
             if not vals: vals = ["Sin resultados"]
             self.combo_results.configure(values=vals)
             self.combo_results.set(vals[0])
             if vals != ["Sin resultados"]: self.on_select_sys(vals[0])
             if vals != ["Sin resultados"]: self.on_select_sys(vals[0])
             
             # Force open dropdown if possible? No easy way in CTk.

    def on_select_sys(self, choice):
        if hasattr(self, 'results_map') and choice in self.results_map:
             r = self.results_map[choice]
             self.matched_id = r['id']
             
             # Fill Amount System
             self.entry_amt_sys.delete(0, 'end')
             self.entry_amt_sys.insert(0, str(r['monto']))
             
             # Auto-Complete Concept if empty?
             if not self.entry_desc.get():
                  self.entry_desc.insert(0, r['descripcion'])
             
             # Set Status
             self.combo_status.set("CONCILIADO")
             
    def _parse_date(self, d_str):
        if not d_str: return None
        for fmt in ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y"]:
            try:
                from datetime import datetime
                return datetime.strptime(d_str.strip(), fmt)
            except: continue
        return None

    def _pick_file(self, ftype):
        from tkinter import filedialog
        path = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf"), ("Imágenes", "*.jpg *.jpeg *.png")])
        if path:
            self.files[ftype] = path
            # Update Label
            inv = "✅ Factura" if 'invoice' in self.files else ""
            pay = "✅ Pago" if 'payment' in self.files else ""
            self.lbl_files.configure(text=f"{inv} {pay}".strip())

    def save(self):
        try:
            # Validate Date with helper
            d_input = self.entry_date.get()
            dt_date = parse_fuzzy_date(d_input)
            
            if not dt_date:
                raise ValueError("Fecha inválida")
                
            d_iso = dt_date.strftime("%Y-%m-%d")
            
            # Apply Match if selected!
            if self.matched_id:
                b_val = parse_localized_float(self.entry_amt_csv.get() or 0)
                b_data = {
                    'fecha': dt_date,
                    'valor_csv': b_val,
                    'concepto': self.entry_desc.get()
                }
                
                if hasattr(self.master, 'controller'):
                    self.master.controller.apply_match(b_data, self.matched_id)
            
            new_data = {
                "fecha": d_iso,
                "concepto": self.entry_desc.get(),
                "valor_csv": parse_localized_float(self.entry_amt_csv.get() or 0),
                "valor_db": parse_localized_float(self.entry_amt_sys.get() or 0),
                "status": self.combo_status.get(),
                "moneda": self.record.get("moneda", "ARS") if self.record else "ARS",
                "ref": self.record.get("ref", "") if self.record else "",
                "files": self.files  # Pass files to result
            }
            
            self.result = new_data
            self.destroy()
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Error", f"Error al guardar: {e}\nUse formato DD/MM/AAAA", parent=self)


