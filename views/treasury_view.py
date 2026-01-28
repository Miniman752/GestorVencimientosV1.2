import customtkinter as ctk
from datetime import date
from tkinter import messagebox, filedialog
import csv
from config import COLORS, FONTS, FILTER_ALL_OPTION
from services.treasury_service import TreasuryService
from services.catalogs_service import CatalogService
from services.period_service import PeriodService
from utils.gui_helpers import create_header
from tkcalendar import DateEntry

class TreasuryView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        
        self.service = TreasuryService()
        self.catalog_service = CatalogService()
        self.period_service = PeriodService()
        
        # State
        self.sort_col = "fecha"
        self.sort_desc = True
        self.movements_cache = [] 
        self.header_buttons = {} # Map col_key -> button widget
        
        # Determine initial range
        today = date.today()
        self.start_date = date(today.year, today.month, 1)
        import calendar
        last_day = calendar.monthrange(today.year, today.month)[1]
        self.end_date = date(today.year, today.month, last_day)

        # Map Caches
        self.map_inmuebles = {}
        self.map_proveedores = {}
        
        self.setup_ui()
        self.populate_filters()
        
    def setup_ui(self):
        # Header
        create_header(self, "Caja y Tesorería", "Visión general de movimientos financieros (Egresos)")
        
        # --- Filter Bar ---
        self.filter_frame = ctk.CTkFrame(self, fg_color=COLORS["card_background"], height=80)
        self.filter_frame.pack(fill="x", padx=20, pady=10)
        
        # Row 1: Combos
        row1 = ctk.CTkFrame(self.filter_frame, fg_color="transparent")
        row1.pack(fill="x", padx=10, pady=5)
        
        # Periodo
        ctk.CTkLabel(row1, text="Período:", font=FONTS["body"]).pack(side="left", padx=5)
        self.cmb_period = ctk.CTkComboBox(row1, width=120, state="readonly", command=self.on_period_change)
        self.cmb_period.pack(side="left", padx=5)
        self.cmb_period.set(FILTER_ALL_OPTION)
        
        # Inmueble
        ctk.CTkLabel(row1, text="Inmueble:", font=FONTS["body"]).pack(side="left", padx=(15, 5))
        self.cmb_inmueble = ctk.CTkComboBox(row1, width=150, state="readonly")
        self.cmb_inmueble.pack(side="left", padx=5)
        self.cmb_inmueble.set(FILTER_ALL_OPTION)
        
        # Entidad
        ctk.CTkLabel(row1, text="Entidad:", font=FONTS["body"]).pack(side="left", padx=(15, 5))
        self.cmb_entidad = ctk.CTkComboBox(row1, width=150, state="readonly")
        self.cmb_entidad.pack(side="left", padx=5)
        self.cmb_entidad.set(FILTER_ALL_OPTION)
        
        # Clear Button
        ctk.CTkButton(row1, text="🧹 Limpiar", width=80, fg_color=COLORS["secondary_button"], 
                      command=self.clear_filters).pack(side="left", padx=(20, 5))

        # Row 2: Dates & Action
        row2 = ctk.CTkFrame(self.filter_frame, fg_color="transparent")
        row2.pack(fill="x", padx=10, pady=5)

        # Date Pickers
        self.lbl_dates = ctk.CTkLabel(row2, text="Fechas (Si Período = Todos):", font=("Segoe UI", 10, "italic"), text_color="gray")
        self.lbl_dates.pack(side="left", padx=5)
        
        ctk.CTkLabel(row2, text="Desde:", font=FONTS["body"]).pack(side="left", padx=(5, 5))
        self.date_from = DateEntry(row2, width=12, background='darkblue',
                                foreground='white', borderwidth=2, date_pattern='dd/mm/y')
        self.date_from.set_date(self.start_date)
        self.date_from.pack(side="left", padx=5)
        
        ctk.CTkLabel(row2, text="Hasta:", font=FONTS["body"]).pack(side="left", padx=(10, 5))
        self.date_to = DateEntry(row2, width=12, background='darkblue',
                                foreground='white', borderwidth=2, date_pattern='dd/mm/y')
        self.date_to.set_date(self.end_date)
        self.date_to.pack(side="left", padx=5)
        
        # Toggle Switch
        self.switch_usd = ctk.CTkSwitch(row2, text="Ver en USD", font=FONTS["body"])
        self.switch_usd.pack(side="right", padx=15)
        self.switch_usd.configure(command=self.on_switch_toggle)

        # Action Buttons
        ctk.CTkButton(row2, text="📄 CSV", width=80, fg_color="#27AE60", 
                      command=self.export_csv).pack(side="right", padx=5)

        ctk.CTkButton(row2, text="📄 PDF", width=80, fg_color="#E74C3C", 
                      command=self.export_pdf).pack(side="right", padx=5)
                      
        ctk.CTkButton(row2, text="🔄 Actualizar", width=100, 
                      fg_color=COLORS["primary_button"], command=self.load_data).pack(side="right", padx=5)
        
        # --- KPI Cards ---
        self.cards_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.cards_frame.pack(fill="x", padx=20, pady=5)
        
        self.card_total_ars = self.create_kpi_card(self.cards_frame, "Total Egresos (ARS)", "$ 0.00")
        self.card_total_ars.pack(side="left", expand=True, fill="both", padx=(0, 10))
        
        self.card_total_usd = self.create_kpi_card(self.cards_frame, "Total Egresos (Eq. USD)", "USD 0.00")
        self.card_total_usd.pack(side="left", expand=True, fill="both", padx=10)
        
        self.card_count = self.create_kpi_card(self.cards_frame, "Movimientos", "0")
        self.card_count.pack(side="left", expand=True, fill="both", padx=(10, 0))
        
        # --- Data Grid ---
        # Headers
        self.headers_frame = ctk.CTkFrame(self, height=30, fg_color="transparent")
        self.headers_frame.pack(fill="x", padx=20, pady=(15, 0))
        
        # REMOVED "Medio Pago" based on user request
        self.cols_config = [
            ("Fecha", "fecha", 1),
            ("Tipo", "tipo", 1),
            ("Categoría", "categoria", 1),
            ("Entidad", "entidad", 2),
            ("Concepto (Inmueble)", "concepto", 1),
            ("Monto", "monto", 1),
            ("Moneda", "moneda", 1)
        ]
        
        for idx, (display, key, weight) in enumerate(self.cols_config):
            self.headers_frame.grid_columnconfigure(idx, weight=weight)
            # Make header clickable for sort
            # Align header right for Monto
            h_anchor = "e" if key == "monto" else "w"
            
            btn = ctk.CTkButton(self.headers_frame, text=display, fg_color="transparent", 
                                text_color="black", font=("Segoe UI", 11, "bold"),
                                anchor=h_anchor, hover_color="#D5DBDB",
                                command=lambda k=key: self.sort_data(k))
            btn.grid(row=0, column=idx, sticky="ew", padx=2)
            self.header_buttons[key] = btn # Store ref
            
        # Scrollable Content
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color=COLORS["content_surface"])
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=5)
        
        for idx, (_, _, weight) in enumerate(self.cols_config):
             self.scroll_frame.grid_columnconfigure(idx, weight=weight)

        # Start Load
        self.after(100, self.load_data)

    def populate_filters(self):
        # Inmuebles
        inms = self.catalog_service.get_inmuebles()
        self.map_inmuebles = {i.alias: i.id for i in inms}
        vals_i = sorted(list(self.map_inmuebles.keys()))
        self.cmb_inmueble.configure(values=[FILTER_ALL_OPTION] + vals_i)
        
        # Proveedores
        provs = self.catalog_service.get_proveedores()
        self.map_proveedores = {p.nombre_entidad: p.id for p in provs}
        vals_p = sorted(list(self.map_proveedores.keys()))
        self.cmb_entidad.configure(values=[FILTER_ALL_OPTION] + vals_p)
        
        # Periods
        periods = self.period_service.get_all_periods()
        vals_period = [p.periodo_id for p in periods]
        self.cmb_period.configure(values=[FILTER_ALL_OPTION] + vals_period)

    def create_kpi_card(self, parent, title, value):
        card = ctk.CTkFrame(parent, fg_color=COLORS["card_background"], corner_radius=10)
        ctk.CTkLabel(card, text=title, font=("Segoe UI", 12, "bold"), text_color="gray").pack(pady=(10, 0))
        lbl_value = ctk.CTkLabel(card, text=value, font=("Segoe UI", 20, "bold"), text_color=COLORS["text_primary"])
        lbl_value.pack(pady=(5, 10))
        card.lbl_value = lbl_value 
        return card
        
    def on_period_change(self, choice):
        # Exclusive Mode Logic
        if choice != FILTER_ALL_OPTION:
            # Disable Dates
            self.date_from.configure(state="disabled")
            self.date_to.configure(state="disabled")
            self.lbl_dates.configure(text_color=COLORS["status_overdue"]) # Visual cue? Or check color prop
        else:
            # Enable Dates
            self.date_from.configure(state="normal")
            self.date_to.configure(state="normal")
            self.lbl_dates.configure(text_color="gray")

    def clear_filters(self):
        self.cmb_period.set(FILTER_ALL_OPTION)
        self.on_period_change(FILTER_ALL_OPTION) # Reset states
        
        self.cmb_inmueble.set(FILTER_ALL_OPTION)
        self.cmb_entidad.set(FILTER_ALL_OPTION)
        self.date_from.set_date(self.start_date)
        self.date_to.set_date(self.end_date)
        self.load_data()

    def export_csv(self):
        if not self.movements_cache:
            messagebox.showwarning("Exportar", "No hay datos para exportar.")
            return

        filename = filedialog.asksaveasfilename(defaultextension=".csv", 
                                                filetypes=[("CSV", "*.csv"), ("All", "*.*")],
                                                title="Guardar Reporte de Caja")
        if not filename: return
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                # Headers
                headers = [cols[0] for cols in self.cols_config]
                writer.writerow(headers)
                
                # Rows
                for item in self.movements_cache:
                    row = [
                        item.get("fecha"),
                        item.get("tipo"),
                        item.get("categoria"),
                        item.get("entidad"),
                        item.get("concepto"),
                        item.get("monto"),
                        item.get("moneda")
                        # removed medio_pago
                    ]
                    writer.writerow(row)
            
            messagebox.showinfo("Exportar", "Archivo guardado exitosamente.")
            import os
            os.startfile(filename) 
        except Exception as e:
            messagebox.showerror("Error", f"Fallo al exportar: {e}")

    def export_pdf(self):
        if not self.movements_cache:
            messagebox.showwarning("Exportar", "No hay datos para exportar.")
            return

        filename = filedialog.asksaveasfilename(defaultextension=".pdf", 
                                                filetypes=[("PDF", "*.pdf")],
                                                title="Guardar Reporte Profesional")
        if not filename: return
        
        try:
            from controllers.reports_controller import ReportsController
            # Use current filtered data (self.movements_cache)
            path = ReportsController().export_treasury_pdf(self.movements_cache, filename)
            
            if messagebox.askyesno("Éxito", "Reporte PDF generado correctamente.\n¿Desea abrirlo ahora?"):
                import os
                try:
                    os.startfile(path)
                except:
                     pass
        except Exception as e:
            messagebox.showerror("Error", f"Fallo al exportar PDF: {e}")

    def load_data(self):
        # 1. Clear Grid
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
            
        # 2. Get Dates & Filters
        try:
            d_start = self.date_from.get_date()
            d_end = self.date_to.get_date()
        except:
             d_start = self.start_date
             d_end = self.end_date
             
        p_val = self.cmb_period.get()
        period_id = p_val if p_val != FILTER_ALL_OPTION else None
        
        i_val = self.cmb_inmueble.get()
        inm_id = self.map_inmuebles.get(i_val)
        
        e_val = self.cmb_entidad.get()
        prov_id = self.map_proveedores.get(e_val)

        # 3. Fetch Data
        try:
            summary = self.service.get_summary(d_start, d_end, inm_id, prov_id, period_id)
            self.movements_cache = self.service.get_movements(d_start, d_end, inm_id, prov_id, period_id)
            
            # 4. Update Cards
            totals = summary["totals"]
            total_usd = summary.get("total_usd_equivalent", 0.0)
            
            total_ars = 0.0
            for k, v in totals.items():
                ks = str(k).upper()
                if "USD" not in ks and "DOLAR" not in ks:
                    total_ars += v
            
            self.card_total_ars.lbl_value.configure(text=f"$ {total_ars:,.2f}")
            self.card_total_usd.lbl_value.configure(text=f"USD {total_usd:,.2f}")
            self.card_count.lbl_value.configure(text=str(summary["count"]))
            
            # 5. Apply Sort & Render
            self.update_headers_ui() # Update indicators
            self.apply_sort()
                
        except Exception as e:
            print(f"Error loading treasury: {e}")
            # Ensure scroll_frame exists roughly even if error, but here it failed because it didn't exist
            if hasattr(self, 'scroll_frame'):
                ctk.CTkLabel(self.scroll_frame, text=f"Error: {e}").pack()

    def on_switch_toggle(self):
        # Re-render without fetching
        self.apply_sort()

    def sort_data(self, key):
        if self.sort_col == key:
            self.sort_desc = not self.sort_desc # Toggle
        else:
            self.sort_col = key
            # Default desc for amounts/dates
            self.sort_desc = True if key in ["fecha", "monto"] else False
            
        self.update_headers_ui()
        self.apply_sort()

    def update_headers_ui(self):
        for key, btn in self.header_buttons.items():
            # Find display name
            display_name = next(c[0] for c in self.cols_config if c[1] == key)
            
            if key == self.sort_col:
                arrow = " ▼" if self.sort_desc else " ▲"
                btn.configure(text=f"{display_name}{arrow}", text_color=COLORS["primary_button"])
            else:
                btn.configure(text=display_name, text_color="black")

    def apply_sort(self):
        # Clear
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
            
        if not self.movements_cache:
            return

        # Sort in place
        def get_sort_val(item):
            # Special case for "monto" if switch is ON
            if self.sort_col == "monto" and self.switch_usd.get():
                return item.get("monto_usd", 0.0)
            
            val = item.get(self.sort_col)
            if val is None: return ""
            return val
            
        self.movements_cache.sort(key=get_sort_val, reverse=self.sort_desc)
        
        for idx, mov in enumerate(self.movements_cache):
            self.render_row(idx, mov)

    def render_row(self, idx, item):
        # Format Date
        d = item["fecha"]
        date_str = d.strftime("%d/%m/%Y") if d else ""
        
        # Determine Amount Display
        if self.switch_usd.get():
             amount_str = f"USD {item.get('monto_usd', 0.0):,.2f}"
             curr_str = "USD (Eq)"
        else:
             amount_str = f"{item['monto']:,.2f}"
             curr_str = item["moneda"]

        # Create Row widgets
        row_widgets = [
            date_str,
            item["tipo"],
            item["categoria"],
            item["entidad"],
            item["concepto"],
            amount_str,
            curr_str
            # Removed Medio Pago
        ]
        
        for col_idx, text in enumerate(row_widgets):
             # Align Monto Right (Index 5)
             align = "e" if col_idx == 5 else "w"
             
             label = ctk.CTkLabel(self.scroll_frame, text=text, anchor=align, text_color="black")
             label.grid(row=idx, column=col_idx, sticky="ew", padx=2, pady=2)
             
             if col_idx == 1: # Tipo Color
                 if text == "EGRESO": label.configure(text_color=COLORS["status_overdue"])
                 else: label.configure(text_color=COLORS["status_paid"])
