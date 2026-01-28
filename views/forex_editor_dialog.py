
import customtkinter as ctk
from datetime import date, datetime
from utils.format_helper import parse_localized_float, parse_fuzzy_date
from config import COLORS, FONTS

class ForexEditorDialog(ctk.CTkToplevel):
    def __init__(self, parent, record=None):
        super().__init__(parent)
        self.title("Cotización Manual 💱")
        self.geometry("400x400")
        
        # Modal
        self.transient(parent)
        self.grab_set()
        # UI Focus Fix
        self.lift()
        self.focus_force()
        self.attributes("-topmost", True)
        
        self.record = record # If None, New
        self.result = None
        
        self._init_ui()
        if record: self._load_data()
        
    def _init_ui(self):
        self.grid_columnconfigure(1, weight=1)
        
        # Date
        ctk.CTkLabel(self, text="Fecha (DD/MM/AAAA):").grid(row=0, column=0, padx=20, pady=10, sticky="w")
        self.entry_date = ctk.CTkEntry(self)
        self.entry_date.grid(row=0, column=1, padx=20, pady=10, sticky="ew")
        
        # Currency
        ctk.CTkLabel(self, text="Moneda:").grid(row=1, column=0, padx=20, pady=10, sticky="w")
        currencies = ["USD", "EUR", "BRL", "CLP", "UYU"]
        self.combo_currency = ctk.CTkComboBox(self, values=currencies)
        self.combo_currency.set("USD")
        self.combo_currency.grid(row=1, column=1, padx=20, pady=10, sticky="ew")
        
        # Buy - REMOVED (Not in DB)
        # ctk.CTkLabel(self, text="Compra:").grid(row=2, column=0, padx=20, pady=10, sticky="w")
        # self.entry_buy = ctk.CTkEntry(self)
        # self.entry_buy.grid(row=2, column=1, padx=20, pady=10, sticky="ew")

        # Sell
        ctk.CTkLabel(self, text="Venta:").grid(row=3, column=0, padx=20, pady=10, sticky="w")
        self.entry_sell = ctk.CTkEntry(self)
        self.entry_sell.grid(row=3, column=1, padx=20, pady=10, sticky="ew")
        
        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=4, column=0, columnspan=2, pady=30)
        
        ctk.CTkButton(btn_frame, text="Cancelar", command=self.destroy, fg_color="gray").pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Guardar", command=self.save, fg_color=COLORS["status_paid"]).pack(side="left", padx=10)
        
    def _load_data(self):
        # Record is expected to be an object (SQLAlchemy model or similar) or dict
        # Based on ForexView it's an object `row`
        d = getattr(self.record, 'fecha', date.today())
        d_str = d.strftime("%d/%m/%Y") if hasattr(d, 'strftime') else str(d)
        
        moneda = getattr(self.record, 'moneda', "USD")
        m_name = moneda.name if hasattr(moneda, 'name') else str(moneda)
        
        self.entry_date.insert(0, d_str)
        self.entry_date.configure(state="disabled") # PK usually shouldn't change edit? OR allow delete+insert. 
                                                   # If user changes date, it's a new record logic-wise. 
                                                   # Let's allow edit, controller handles Upsert appropriately.
        self.entry_date.configure(state="normal") 

        self.combo_currency.set(m_name)
        # Assuming PK is Date+Currency, changing them means distinct record. 
        # But we don't have ID. So update_manual works by date/currency. 
        # If user changes date/currency, it creates a new one and leaves old one?
        # Ideally we should delete old logical key if modified. 
        # But `update_cotizacion_manual` uses the PASSED date/currency as key.
        # If I change date, it upserts new date. The old date record remains.
        # That's fine for "Manual Load". For "Edit", maybe we want to Remove old + Add new?
        # For now, simplistic Upsert is safer. User can delete old one if needed.
        
        # self.entry_buy.insert(0, str(getattr(self.record, 'compra', 0.0)))
        self.entry_sell.insert(0, str(getattr(self.record, 'venta', 0.0)))

    def save(self):
        try:
            d_input = self.entry_date.get()
            dt = parse_fuzzy_date(d_input)
            
            if not dt: raise ValueError("Fecha Invalida")
            
            new_data = {
                "fecha": dt,
                "moneda": self.combo_currency.get(),
                "compra": 0.0, # float(self.entry_buy.get() or 0),
                "venta": parse_localized_float(self.entry_sell.get() or 0)
            }
            
            self.result = new_data
            self.destroy()
        except ValueError:
            from tkinter import messagebox
            messagebox.showerror("Error", "Datos inválidos (Fecha DD/MM/AAAA o Montos numéricos)", parent=self)


