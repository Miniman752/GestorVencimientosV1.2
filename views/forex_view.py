

import customtkinter as ctk
from tkinter import ttk, filedialog, Menu, messagebox
from config import COLORS, FONTS, FILTER_ALL_OPTION
from controllers.forex_controller import ForexController

from views.import_wizard_view import ImportWizardView
from views.forex_editor_dialog import ForexEditorDialog
from datetime import date, datetime
from utils.import_helper import format_currency
from utils.format_helper import parse_localized_float

# Charting
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
import queue # Added for type check
import pandas as pd

class InspectorPanel(ctk.CTkFrame):
    def __init__(self, parent, view_ref): # Changed controller to view_ref
        super().__init__(parent, fg_color=COLORS["sidebar_background"], width=250)
        self.view = view_ref
        self.controller = view_ref.controller
        self.grid_rowconfigure(0, weight=0) # Header
        self.grid_rowconfigure(1, weight=1) # Content
        
        # Header
        ctk.CTkLabel(self, text="Inspector de Cotización", font=FONTS["heading"], text_color="white").grid(row=0, column=0, pady=20, padx=10, sticky="w")
        
        # Content Container - SCROLLABLE for small screens
        self.content = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.content.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        
        # --- SECTION 1: DETAILS (Depends on Row Selection) ---
        self.details_container = ctk.CTkFrame(self.content, fg_color="transparent")
        self.details_container.pack(fill="x", pady=(0, 20))
        
        # Initial State
        self.lbl_msg = ctk.CTkLabel(self.details_container, text="Seleccione una operación\npara ver detalles.", text_color="gray")
        self.lbl_msg.pack(pady=20)
        
        # --- SECTION 2: STRATEGY (Always Visible if Data Exists) ---
        self.strategy_container = ctk.CTkFrame(self.content, fg_color="transparent")
        self.strategy_container.pack(fill="x")

        # Current Data Holder
        self.current_date = None
        self.current_curr = None
        self.current_sell = 0.0
        self.current_buy = 0.0

    def update_view(self, date_obj, currency_str):
        # Clear only details section
        for w in self.details_container.winfo_children(): w.destroy()
        
        details = self.controller.get_inspector_details(date_obj, currency_str)
        if not details:
            ctk.CTkLabel(self.details_container, text="No data").pack()
            return
            
        self.current_date = details["fecha"]
        self.current_curr = currency_str
        self.current_sell = details["venta"]
        self.current_buy = details["compra"]

        # Date & Currency
        ctk.CTkLabel(self.details_container, text=f"{currency_str} - {details['fecha'].strftime('%d/%m/%Y')}", font=("Segoe UI", 16, "bold"), text_color="white").pack(anchor="w", pady=(0, 5))
        
        # Main Metrics
        self._kpi_card(self.details_container, "Venta", f"${details['venta']:,.2f}")
        
        # Trend
        t_val = details['trend']
        if t_val == "up":
            t_label = "▲ Alza (+)"
            t_color = COLORS.get("status_paid", "#27AE60")
        elif t_val == "down":
            t_label = "▼ Baja (-)"
            t_color = COLORS["status_overdue"]
        else:
            t_label = "➖ Estable (=)"
            t_color = "gray"

        self._kpi_card(self.details_container, "Tendencia", t_label, value_color=t_color)
        
        if details.get("prev_venta"):
             ctk.CTkLabel(self.details_container, text=f"Previo: ${details['prev_venta']:,.2f}", font=("Segoe UI", 10), text_color="gray").pack(anchor="w", pady=(2,0))

        # Actions
        ctk.CTkLabel(self.details_container, text="Acciones", font=("Segoe UI", 12, "bold"), text_color="white").pack(anchor="w", pady=(15, 5))
        
        ctk.CTkButton(self.details_container, text="✏️ Corregir Valor", fg_color=COLORS["primary_button"], command=self.action_edit, height=25).pack(fill="x", pady=2)
        
    def update_strategy(self, currency_str="USD"):
        # Clear Strategy Section
        for w in self.strategy_container.winfo_children(): w.destroy()
        
        strategy = self.controller.get_strategic_analysis(currency_str)
        if not strategy: return

        ctk.CTkFrame(self.strategy_container, height=1, fg_color="#444").pack(fill="x", pady=10) # Separator
        ctk.CTkLabel(self.strategy_container, text="🤖 Análisis IA", font=("Segoe UI", 12, "bold"), text_color="white").pack(anchor="w", pady=(0, 5))
        
        # Main Action Card
        s_color = COLORS.get("status_paid") if strategy['color'] == "green" else COLORS.get("status_overdue") if strategy['color'] == "red" else "gray"
        if strategy['color'] == "green": s_color = "#00C853"
        if strategy['color'] == "red": s_color = "#FF1744"
        
        sf = ctk.CTkFrame(self.strategy_container, fg_color=COLORS["content_surface"], border_width=1, border_color=s_color)
        sf.pack(fill="x", pady=5)
        
        ctk.CTkLabel(sf, text="Recomendación:", font=("Segoe UI", 10), text_color="gray").pack(anchor="w", padx=10, pady=(5,0))
        ctk.CTkLabel(sf, text=strategy["action"], font=("Segoe UI", 14, "bold"), text_color=s_color).pack(anchor="center", pady=5) 
        
        # Details
        self._kpi_card(self.strategy_container, "Tendencia", strategy["trend"])
        self._kpi_card(self.strategy_container, "Momentum", strategy["momentum"])
        
        # Projection Card
        self._kpi_card(self.strategy_container, "Proyección", strategy["projection"], value_color="#ab47bc")


    def _kpi_card(self, parent_widget, label, value, value_color=None):
        if value_color is None: value_color = COLORS["text_primary"]
        f = ctk.CTkFrame(parent_widget, fg_color=COLORS["content_surface"])
        f.pack(fill="x", pady=2) 
        ctk.CTkLabel(f, text=label, font=("Segoe UI", 10), text_color="gray").pack(anchor="w", padx=10, pady=(2,0))
        ctk.CTkLabel(f, text=value, font=("Segoe UI", 13, "bold"), text_color=value_color).pack(anchor="w", padx=10, pady=(0,2))


        
    def action_edit(self):
        new_val = ctk.CTkInputDialog(text=f"Nuevo Venta para {self.current_date}:", title="Corregir").get_input()
        if new_val:
             try:
                 success, msg = self.controller.update_cotizacion_manual(
                     self.current_date, 
                     self.current_curr, 
                     parse_localized_float(self.current_buy), 
                     parse_localized_float(new_val)
                 )
                 if success:
                     self.update_view(self.current_date, self.current_curr)
                     self.view.load_data() # Refresh Main Grid
                 else:
                     messagebox.showerror("Error", msg)
             except Exception as e:
                 messagebox.showerror("Error", str(e))



class ForexView(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color=COLORS["main_background"])
        self.controller = ForexController()
        
        # 3 Column Layout
        self.grid_columnconfigure(1, weight=3) # Grid area
        self.grid_columnconfigure(2, weight=0) # Inspector (Auto width or fixed)
        self.grid_rowconfigure(0, weight=1)
 
        # 1. Filters (Left)
        self.filter_frame = ctk.CTkFrame(self, width=200, corner_radius=0, fg_color=COLORS["sidebar_background"])
        self.filter_frame.grid(row=0, column=0, sticky="nsew")
        self._init_filters()
 
        # 2. Main Grid (Center)
        self.main_frame = ctk.CTkFrame(self, fg_color=COLORS["main_background"])
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self._init_main_grid()
        
        # 3. Inspector (Right)
        # Let's make it visible but empty
        self.inspector = InspectorPanel(self, self) # Pass parent and view_ref (self)
        self.inspector.grid(row=0, column=2, sticky="nsew")
        
        self.refresh_years_combo()
        self.load_data()
        
    def _init_filters(self):
        # ... Reusing code from previous ForexView ...
        ctk.CTkLabel(self.filter_frame, text="Mesa de Dinero", font=FONTS["heading"], text_color="white").pack(pady=20)
        
        ctk.CTkLabel(self.filter_frame, text="Año", text_color="white").pack(pady=(10, 0))
        self.year_frame = ctk.CTkFrame(self.filter_frame, fg_color="transparent")
        self.year_frame.pack(pady=5, padx=10, fill="x")
        self.combo_year = ctk.CTkComboBox(self.year_frame, values=[], width=120)
        self.combo_year.pack(side="left", padx=(0, 5))
        self.btn_year_mgr = ctk.CTkButton(self.year_frame, text="⚙️", width=30, fg_color="gray", command=self.open_year_manager)
        self.btn_year_mgr.pack(side="left")

        ctk.CTkLabel(self.filter_frame, text="Mes", text_color="white").pack(pady=(10, 0))
        self.months_map = {"Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4, "Mayo": 5, "Junio": 6, "Julio": 7, "Agosto": 8, "Septiembre": 9, "Octubre": 10, "Noviembre": 11, "Diciembre": 12}
        self.combo_month = ctk.CTkComboBox(self.filter_frame, values=[FILTER_ALL_OPTION] + list(self.months_map.keys()))
        self.combo_month.set(FILTER_ALL_OPTION)
        self.combo_month.pack(pady=5, padx=10)

        ctk.CTkButton(self.filter_frame, text="Filtrar", width=160, command=self.load_data).pack(pady=10)
        ctk.CTkButton(self.filter_frame, text="Limpiar Filtros", width=160, fg_color="gray", command=self.reset_filters).pack(pady=5)
        
        ctk.CTkLabel(self.filter_frame, text="Operaciones", text_color="white", font=("Segoe UI", 12, "bold")).pack(pady=(40, 10))
        ctk.CTkButton(self.filter_frame, text="Importar CSV", fg_color=COLORS.get("status_paid", "#27AE60"), command=self.open_import_wizard).pack(pady=5)
        ctk.CTkButton(self.filter_frame, text="+ Nueva Manual", fg_color=COLORS["secondary_button"], command=self.add_manual).pack(pady=5)
        
        # Manual Sync Button
        ctk.CTkButton(self.filter_frame, text="☁️ Sincronizar BNA", fg_color=COLORS.get("accent_button", "#3498DB"), command=self.action_sync_bna).pack(pady=5)

    def _init_main_grid(self):
        # 1. Dashboard Summary (Cards)
        self.cards_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.cards_frame.pack(fill="x", pady=(0, 20))
        
        # Init generic cards (Empty first)
        self.card_sell = self._create_metric_card(self.cards_frame, "Venta Actual", "-", "gray")
        self.card_buy = self._create_metric_card(self.cards_frame, "Compra Actual", "-", "gray")
        self.card_spread = self._create_metric_card(self.cards_frame, "Spread", "-", "gray")
        self.card_trend = self._create_metric_card(self.cards_frame, "Tendencia", "-", "gray")

        # 2. Grid Title
        ctk.CTkLabel(self.main_frame, text="Cotizaciones Vigentes", font=FONTS["heading"], text_color=COLORS["text_primary"]).pack(anchor="w", pady=(0, 10))
        
        # 3. Treeview
        self.tree_frame = ctk.CTkFrame(self.main_frame)
        self.tree_frame.pack(fill="both", expand=True)
        
        columns = ("fecha", "moneda", "compra", "venta", "trend")
        self.tree = ttk.Treeview(self.tree_frame, columns=columns, show="headings")
        
        style = ttk.Style()
        style.configure("Treeview", rowheight=30)
        self.tree.heading("fecha", text="FECHA")
        self.tree.heading("moneda", text="MONEDA")
        self.tree.heading("compra", text="COMPRA")
        self.tree.heading("venta", text="VENTA")
        self.tree.heading("trend", text="TENDENCIA")
        
        self.tree.column("fecha", width=100, anchor="center")
        self.tree.column("moneda", width=50, anchor="center")
        self.tree.column("compra", width=80, anchor="e")
        self.tree.column("venta", width=80, anchor="e")
        self.tree.column("trend", width=50, anchor="center")

        sb = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        
        self.tree.tag_configure("oddrow", background="#F4F6F7")
        # Trend Color Tags
        self.tree.tag_configure("trend_up", foreground="#27AE60") # Green
        self.tree.tag_configure("trend_down", foreground="#C0392B") # Red
        self.tree.tag_configure("trend_equal", foreground="gray")
        
        self.tree.bind("<<TreeviewSelect>>", self.on_select_row)
        self.tree.bind("<Button-3>", self.show_context_menu)
        self.tree.bind("<Double-1>", self.on_double_click) # Edit shortcut
        
        # Context Menu
        self.menu = Menu(self, tearoff=0)
        self.menu.add_command(label="✏️ Editar", command=self.edit_selection)
        self.menu.add_command(label="🗑️ Eliminar", command=self.delete_selection)

        # --- CHART SECTION (Bottom) ---
        self.chart_container = ctk.CTkFrame(self.main_frame, fg_color="transparent", height=250)
        self.chart_container.pack(fill="x", expand=False, pady=(20, 0))
        # Title
        ctk.CTkLabel(self.chart_container, text="Análisis Técnico (MACD) - Período Seleccionado", 
                     font=("Segoe UI", 12, "bold"), text_color="gray").pack(anchor="w", padx=5)
        
        self.chart_canvas_frame = ctk.CTkFrame(self.chart_container, fg_color=COLORS["sidebar_background"], corner_radius=10)
        self.chart_canvas_frame.pack(fill="both", expand=True, pady=5)

    def _create_metric_card(self, parent, title, value, color):
        f = ctk.CTkFrame(parent, fg_color=COLORS["content_surface"], width=150, height=80)
        f.pack(side="left", fill="x", expand=True, padx=5)
        f.pack_propagate(False) # Force size
        
        lbl_val = ctk.CTkLabel(f, text=value, font=("Segoe UI", 22, "bold"), text_color=color)
        lbl_val.pack(expand=True, pady=(5,0))
        
        lbl_title = ctk.CTkLabel(f, text=title, font=("Segoe UI", 11), text_color="gray")
        lbl_title.pack(pady=(0, 10))
        
        return lbl_val # Return label to update text/color

    def update_cards(self, latest_row):
        if not latest_row:
            self.card_sell.configure(text="-", text_color="gray")
            self.card_buy.configure(text="-", text_color="gray")
            self.card_spread.configure(text="-", text_color="gray")
            self.card_trend.configure(text="-", text_color="gray")
            return

        # Fetch details for trend calculation (using controller reuse)
        try:
             # We assume default filtered currency from latest row
             details = self.controller.get_inspector_details(latest_row.fecha, latest_row.moneda.name)
             if details:
                 # Venta
                 self.card_sell.configure(text=f"${details['venta']:,.2f}", text_color=COLORS["text_primary"])
                 # Compra
                 self.card_buy.configure(text=f"${details['compra']:,.2f}", text_color=COLORS["text_primary"])
                 # Spread
                 s_color = COLORS["status_paid"] if details['spread_pct'] > 0 else "gray"
                 self.card_spread.configure(text=f"{details['spread_pct']:.2f}%", text_color=s_color)
                 
                 # Trend Logic (User Requirements)
                 # Up: Green, +, Arrow Up
                 # Down: Red, -, Arrow Down
                 # Stable: Gray, =, Flat
                 t_val = details['trend']
                 if t_val == "up":
                     t_txt = "+ ▲ Alza"
                     t_col = COLORS.get("status_paid", "#27AE60")
                 elif t_val == "down":
                     t_txt = "- ▼ Baja"
                     t_col = COLORS["status_overdue"] # Red
                 else:
                     t_txt = "= ▬ Estable"
                     t_col = "gray"
                 
                 self.card_trend.configure(text=t_txt, text_color=t_col)

        except Exception as e:
            print("Card update error:", e)

    def on_select_row(self, event):
        item = self.tree.selection()
        if not item: return
        
        # Use simple index matching since tree is rebuilt 1:1 with current_data
        idx = self.tree.index(item[0])
        
        if hasattr(self, 'current_data') and idx < len(self.current_data):
            record = self.current_data[idx]
            
            # Update Top Cards
            self.update_cards(record)
            
            # Update Inspector
            m_name = record.moneda.name if hasattr(record.moneda, 'name') else str(record.moneda)
            self.inspector.update_view(record.fecha, m_name)

    # ... Methods load_data ...
    def refresh_years_combo(self):
        years = self.controller.get_active_years()
        if not years: years = ["2025"]
        self.combo_year.configure(values=years)
        
        # Force set the first item if current is empty or not in list
        current = self.combo_year.get()
        if years and (not current or current not in years):
             self.combo_year.set(years[0])
        
    def open_year_manager(self):
        YearManagerDialog(self)
        
    def open_import_wizard(self):
        ImportWizardView(self)
        
    def reset_filters(self):
        self.combo_month.set(FILTER_ALL_OPTION)
        # Set to current year if available, else first option
        vals = self.combo_year.cget("values")
        if vals:
             from datetime import date
             curr = str(date.today().year)
             if curr in vals: self.combo_year.set(curr)
             else: self.combo_year.set(vals[0])
        self.load_data()

    def load_data(self):
        # Clear UI immediately to show activity, or keep old data?
        # Typically clearing signals "refresh".
        for item in self.tree.get_children(): self.tree.delete(item)
        
        # UI Feedback
        self.configure(cursor="watch")
        
        # Thread args
        try: year_val = int(self.combo_year.get())
        except: year_val = None
        m_str = self.combo_month.get()
        m_val = self.months_map.get(m_str)
        
        
        # Start Thread
        import threading
        import queue
        self.data_queue = queue.Queue()
        threading.Thread(target=self._load_data_thread, args=(year_val, m_val, self.data_queue), daemon=True).start()
        self.after(100, self._check_queue)

    def _load_data_thread(self, year_val, m_val, q):
        try:
            data = self.controller.get_cotizaciones(year=year_val, month=m_val)
            q.put({"status": "success", "data": data})
        except Exception as e:
            q.put({"status": "error", "error": e})
            
    def _check_queue(self):
        try:
            msg = self.data_queue.get_nowait()
            self.configure(cursor="")
            
            if msg["status"] == "success":
                self._update_ui_with_data(msg["data"])
            elif msg["status"] == "error":
                print(f"Error loading Forex data: {msg['error']}")
        
        except queue.Empty:
            # Keep waiting
            self.after(100, self._check_queue)
        except Exception as e:
            self.configure(cursor="")
            import traceback
            traceback.print_exc()
            print(f"CRITICAL UI ERROR: {e}")

    def _update_ui_with_data(self, data):
        self.current_data = data # Cache for editing
        
        # Update Cards with latest data (first in list)
        if data:
            self.update_cards(data[0])
        else:
            self.update_cards(None)

        for i, row in enumerate(data):
            row_tag = "evenrow" if i%2==0 else "oddrow"
            trend_tag = "trend_equal"
            trend_symbol = "➖"
            
            if i < len(data) - 1:
                prev_row = data[i+1] # Older date
                if row.venta > prev_row.venta:
                    trend_symbol = "▲" # Solid Triangle Up
                    trend_tag = "trend_up"
                elif row.venta < prev_row.venta:
                    trend_symbol = "▼" # Solid Triangle Down
                    trend_tag = "trend_down"
            
            # Format Date
            f_date = row.fecha
            if hasattr(f_date, "strftime"): f_date = f_date.strftime("%d/%m/%Y")
            elif isinstance(f_date, str):
                 # Try to ensure DD/MM/YYYY if it came as YYYY-MM-DD
                 try:
                     parts = f_date.split("-")
                     if len(parts) == 3: f_date = f"{parts[2]}/{parts[1]}/{parts[0]}"
                 except: pass

            self.tree.insert("", "end", values=(
                f_date, 
                row.moneda.name, 
                format_currency(row.compra), 
                format_currency(row.venta), 
                trend_symbol
            ), tags=(row_tag, trend_tag))
        
        # Draw Chart with same filters
        try: year_val = int(self.combo_year.get())
        except: year_val = None
        m_str = self.combo_month.get()
        self._update_chart(str(year_val) if year_val else None, m_str)
        # Update Strategy Panel immediately (Default USD for now)
        self.inspector.update_strategy("USD")


    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.menu.post(event.x_root, event.y_root)

    def on_double_click(self, event):
        self.edit_selection()

    def add_manual(self):
        d = ForexEditorDialog(self)
        self.wait_window(d)
        if d.result:
            r = d.result
            self.controller.update_cotizacion_manual(r['fecha'], r['moneda'], 0.0, r['venta'])
            self.load_data()
            messagebox.showinfo("Éxito", "Cotización agregada.")

    def edit_selection(self):
        sel = self.tree.selection()
        if not sel: return
        idx = self.tree.index(sel[0])
        if idx < len(self.current_data):
            record = self.current_data[idx]
            d = ForexEditorDialog(self, record)
            self.wait_window(d)
            if d.result:
                r = d.result
                self.controller.update_cotizacion_manual(r['fecha'], r['moneda'], 0.0, r['venta'])
                self.load_data()

    def delete_selection(self):
        sel = self.tree.selection()
        if not sel: return
        idx = self.tree.index(sel[0])
        if idx < len(self.current_data):
            record = self.current_data[idx]
            if messagebox.askyesno("Eliminar", f"¿Eliminar cotización del {record.fecha}?"):
                m_name = record.moneda.name if hasattr(record.moneda, 'name') else str(record.moneda)
                self.controller.delete_cotizacion(record.fecha, m_name)
                self.load_data()

    def action_sync_bna(self):
        try:
             self.configure(cursor="watch")
             self.update_idletasks()
             
             success, msg = self.controller.sync_bna()
             
             self.configure(cursor="")
             
             if success:
                 messagebox.showinfo("Sincronización", msg)
                 self.load_data() 
             else:
                 messagebox.showerror("Error", msg)
                 
        except Exception as e:
            self.configure(cursor="")
            messagebox.showerror("Error", str(e))

    def _update_chart(self, year, month_idx):
        for w in self.chart_canvas_frame.winfo_children(): w.destroy()
        
        # Month name to int logic
        m_int = None
        months = ["Todos", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                  "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        
        if month_idx and month_idx in months:
            idx = months.index(month_idx)
            if idx > 0: m_int = idx
            
        y_int = int(year) if year and year != "None" else None
        limit = None if y_int else 90 
        
        df = self.controller.get_chart_data(currency_str="USD", year=y_int, month=m_int, limit=limit)
        
        if df is None or df.empty:
            ctk.CTkLabel(self.chart_canvas_frame, text="Sin datos suficientes para graficar", text_color="gray").pack(expand=True)
            return
            
        # DRAW - MODERN FINTECH PRO STYLE 📊💼
        # Background: Dark Blue-Grey (TradingView Default)
        bg_color = "#1e222d"
        grid_color = "#2a2e39"
        text_color = "#d1d4dc"
        
        fig = Figure(figsize=(8, 3), dpi=90, facecolor=bg_color)
        
        # GridSpec
        gs = fig.add_gridspec(2, 1, height_ratios=[3, 1], hspace=0.1) 
        ax1 = fig.add_subplot(gs[0])
        ax2 = fig.add_subplot(gs[1], sharex=ax1)
        
        for ax in [ax1, ax2]:
            ax.set_facecolor(bg_color)
            ax.tick_params(colors=text_color, labelsize=7, labelcolor=text_color)
            for spine in ax.spines.values(): spine.set_edgecolor(grid_color)
            ax.grid(True, linestyle=":", linewidth=0.5, alpha=0.5, color=grid_color)
            
        # Separate Real vs Projection
        if 'type' not in df.columns:
            df['type'] = 'real'
            
        is_proj = df['type'] == 'projection'
        df_real = df[~is_proj].copy()
        df_proj = df[is_proj].copy()
        
        # --- TOP CHART: CANDLES & MA ---
        
        # 1. Moving Averages - Elegant Thin Lines
        ax1.plot(df_real['fecha'], df_real['EMA_12'], color="#f5c518", linewidth=1.0, alpha=0.8, label="EMA 12") # Soft Gold
        ax1.plot(df_real['fecha'], df_real['EMA_26'], color="#2962ff", linewidth=1.0, alpha=0.8, label="EMA 26") # Royal Blue
        
        # 2. Candles - Professional Palette
        # Teal for Up, Coral for Down
        up_color = "#26a69a"
        down_color = "#ef5350"
        
        width = 0.6 
        dates_real = mdates.date2num(df_real['fecha'])
        
        opens = df_real['Open']
        closes = df_real['Close']
        lows = df_real[['Open', 'Close']].min(axis=1)
        heights = (closes - opens).abs().replace(0, 0.5)
        
        green_mask = df_real['Close'] >= df_real['Open']
        ax1.bar(dates_real[green_mask], heights[green_mask], bottom=lows[green_mask], 
                color=up_color, width=width, align='center', alpha=1.0)
        
        red_mask = ~green_mask
        ax1.bar(dates_real[red_mask], heights[red_mask], bottom=lows[red_mask], 
                color=down_color, width=width, align='center', alpha=1.0)

        # 3. PROJECTION LINE - Tech Blue
        if not df_proj.empty:
            last_real = df_real.iloc[-1]
            df_proj_plot = pd.concat([df_real.iloc[[-1]], df_proj])
            # Solid prediction line
            ax1.plot(df_proj_plot['fecha'], df_proj_plot['venta'], color="#ab47bc", linestyle="--", linewidth=1.5, dashes=(3, 1), label="Forecast")
            
            # Subtle endpoint
            ax1.plot(df_proj_plot['fecha'].iloc[-1], df_proj_plot['venta'].iloc[-1], marker='o', color="#ab47bc", markersize=3)

        # 4. Signals - Subtle Markers
        signals = df_real[df_real['Trade_Signal'].notna()]
        for idx, row in signals.iterrows():
            d_val = mdates.date2num(row['fecha'])
            if row['Trade_Signal'] == "BUY":
                ax1.plot(d_val, row['Low'] * 0.995, marker='^', color=up_color, markersize=5, markeredgewidth=0) 
            else:
                ax1.plot(d_val, row['High'] * 1.005, marker='v', color=down_color, markersize=5, markeredgewidth=0)

        # Header - Minimalist
        ax1.text(0.01, 0.92, "USD/ARS", transform=ax1.transAxes, color=text_color, fontsize=10, fontweight="bold")
        ax1.text(0.08, 0.92, "• DAILY", transform=ax1.transAxes, color="#5d606b", fontsize=10, fontweight="normal")
        
        # --- BOTTOM CHART: MACD ---
        # Histogram with lower alpha
        col_hist = [up_color if v >= 0 else down_color for v in df_real['Hist']]
        ax2.bar(dates_real, df_real['Hist'], color=col_hist, width=width, align='center', alpha=0.5)
        
        ax2.plot(dates_real, df_real['MACD'], color="#2962ff", linewidth=1.0)
        ax2.plot(dates_real, df_real['Signal'], color="#ff6d00", linewidth=1.0)

        ax1.tick_params(labelbottom=False)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%d/%b'))
        
        import matplotlib.ticker as ticker
        ax2.xaxis.set_major_locator(ticker.MaxNLocator(nbins=12))

        canvas = FigureCanvasTkAgg(fig, master=self.chart_canvas_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

# ... YearManagerDialog (Keep existing logic) ...
class YearManagerDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Gestionar Años (Avanzado)")
        self.geometry("340x450")
        self.parent = parent
        self.controller = parent.controller
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        self.top_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.top_frame.grid(row=0, column=0, pady=10, padx=10, sticky="ew")
        self.entry_year = ctk.CTkEntry(self.top_frame, placeholder_text="Nuevo Año (YYYY)")
        self.entry_year.pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(self.top_frame, text="+ Agregar", width=80, command=self.add_year).pack(side="left")
        
        self.scroll_frame = ctk.CTkScrollableFrame(self, label_text="Configuración Vigente")
        self.scroll_frame.grid(row=1, column=0, pady=5, padx=10, sticky="nsew")
        
        self.load_years()
        self.transient(parent)
        self.grab_set()
        
        # UI Focus Fix
        self.lift()
        self.focus_force()
        self.attributes("-topmost", True)

    def load_years(self):
        for w in self.scroll_frame.winfo_children(): w.destroy()
        years = self.controller.get_all_years_config()
        self.vars = {}
        for y_obj in years:
            row = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)
            var = ctk.IntVar(value=y_obj.is_active)
            self.vars[y_obj.year] = var
            ctk.CTkCheckBox(row, text=str(y_obj.year), variable=var, width=60, command=lambda y=y_obj.year: self.on_toggle(y)).pack(side="left", padx=5)
            
            bf = ctk.CTkFrame(row, fg_color="transparent")
            bf.pack(side="right", padx=5)
            ctk.CTkButton(bf, text="✏️", width=30, fg_color=COLORS["primary_button"], command=lambda y=y_obj.year: self.on_edit(y)).pack(side="left", padx=2)
            ctk.CTkButton(bf, text="🗑️", width=30, fg_color=COLORS["status_overdue"], hover_color="#A93226", command=lambda y=y_obj.year: self.on_delete(y)).pack(side="left", padx=2)

    def on_toggle(self, year):
        self.controller.toggle_year_status(year, self.vars[year].get() == 1)
        self.parent.refresh_years_combo()
        
        try:
             val = self.entry_year.get()
             if not val: 
                 messagebox.showwarning("Requerido", "Ingrese un año")
                 return
             y = int(val)
             if str(y) == val and len(str(y))==4:
                  if self.controller.add_year(y):
                      self.entry_year.delete(0, "end")
                      self.load_years()
                      self.parent.refresh_years_combo()
                  else: messagebox.showerror("Error", "Error al agregar")
             else: messagebox.showerror("Error", "Formato inválido")
        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Inválido: {e}")

    def on_edit(self, old):
        new = ctk.CTkInputDialog(text=f"Corregir {old}", title="Editar").get_input()
        if new:
            if self.controller.update_year(old, int(new)):
                self.load_years()
                self.parent.refresh_years_combo()
            else: messagebox.showerror("Error", "Falló actualización")


    def on_delete(self, old):
        if messagebox.askyesno("Borrar", f"¿Borrar {old}?"):
             if self.controller.delete_year(old):
                 self.load_years()
                 self.parent.refresh_years_combo()
             else: messagebox.showerror("Error", "Falló borrado")


