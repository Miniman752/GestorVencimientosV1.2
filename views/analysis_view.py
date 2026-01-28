import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date
from tkcalendar import DateEntry
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading

from config import COLORS, FONTS
from utils.import_helper import format_currency
from utils.format_helper import parse_localized_float
from dtos.analysis import AnalysisRequestDTO
from services.time_lord_service import TimeLordService
from services.indec_service import IndecService

class AnalysisView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(fg_color=COLORS["main_background"])
        
        self.service = TimeLordService()

        # Main Layout: TabView
        self.tabview = ctk.CTkTabview(self, fg_color="transparent")
        self.tabview.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.tab_dashboard = self.tabview.add("Tablero de Análisis")
        self.tab_ipc = self.tabview.add("Gestión de Índices IPC")
        
        # Init Sort State
        self.ipc_sort_col = "fecha" # fecha, valor
        self.ipc_sort_desc = True
        self.ipc_header_widgets = {}
        self.ipc_rows = []

        self._init_dashboard_tab()
        self._init_ipc_tab()

    def _init_dashboard_tab(self):
        # 1. Control Panel (Toolbar)
        ctrl_frame = ctk.CTkFrame(self.tab_dashboard, fg_color="transparent")
        ctrl_frame.pack(fill="x", pady=(0, 15))
        
        # Tools
        ctk.CTkLabel(ctrl_frame, text="Proyecciones Temporales", font=FONTS["heading"], text_color=COLORS["text_primary"]).pack(side="left", padx=10)
        
        # Right Side Tools
        ctk.CTkButton(ctrl_frame, text="↻ Refrescar", width=100, fg_color=COLORS["primary_button"], command=self.load_dashboard_data).pack(side="right", padx=10)
        
        self.switch_inf = ctk.CTkSwitch(ctrl_frame, text="Ajuste Inflación", command=self.on_param_change)
        self.switch_inf.pack(side="right", padx=15)
        
        self.combo_gran = ctk.CTkComboBox(ctrl_frame, values=["Diario", "Semanal", "Mensual", "Anual"], command=self.on_param_change, width=120)
        self.combo_gran.set("Mensual")
        self.combo_gran.pack(side="right", padx=10)

        # 2. Main Content Grid
        viz_frame = ctk.CTkFrame(self.tab_dashboard, fg_color="transparent")
        viz_frame.pack(fill="both", expand=True)
        viz_frame.grid_columnconfigure(0, weight=3) # Chart
        viz_frame.grid_columnconfigure(1, weight=1) # Stats
        viz_frame.grid_rowconfigure(0, weight=1)
        
        # Chart Card
        self.chart_frame = ctk.CTkFrame(viz_frame, fg_color=COLORS["content_surface"], corner_radius=10, border_width=1, border_color="#D5D8DC")
        self.chart_frame.grid(row=0, column=0, sticky="nsew", padx=(0,10))
        
        # Chart Title
        ctk.CTkLabel(self.chart_frame, text="Evolución y Tendencia", font=("Segoe UI", 12, "bold"), text_color="gray").pack(pady=5)
        
        # PERFORMANCE OPTIMIZATION: Init Canvas Once
        self.fig = Figure(figsize=(5, 4), dpi=80, facecolor=COLORS["content_surface"])
        self.ax = self.fig.add_subplot(111)
        self.chart_canvas = FigureCanvasTkAgg(self.fig, master=self.chart_frame)
        self.chart_canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
        
        # Sidebar (Stats & Alerts)
        side_frame = ctk.CTkFrame(viz_frame, fg_color="transparent")
        side_frame.grid(row=0, column=1, sticky="nsew")
        
        # Total KPI Card
        self.kpi_card = ctk.CTkFrame(side_frame, fg_color=COLORS["content_surface"], height=100, corner_radius=10, border_width=1, border_color="#D5D8DC")
        self.kpi_card.pack(fill="x", pady=(0,15))
        
        ctk.CTkLabel(self.kpi_card, text="Total Período", font=("Segoe UI", 11), text_color="gray").pack(pady=(15, 0))
        self.lbl_total_val = ctk.CTkLabel(self.kpi_card, text="$0", font=("Segoe UI", 24, "bold"), text_color=COLORS["primary_button"])
        self.lbl_total_val.pack(pady=(5, 15))
        
        # Alerts Panel
        self.alerts_frame = ctk.CTkScrollableFrame(side_frame, label_text="Alertas Estacionales", fg_color=COLORS["content_surface"], 
                                                  label_font=("Segoe UI", 12, "bold"), label_text_color=COLORS["text_primary"])
        self.alerts_frame.pack(fill="both", expand=True)

    def _init_ipc_tab(self):
        # 1. Input Card
        top_frame = ctk.CTkFrame(self.tab_ipc, fg_color=COLORS["content_surface"], corner_radius=10, border_width=1, border_color="#D5D8DC")
        top_frame.pack(fill="x", pady=(0, 15))
        
        header = ctk.CTkFrame(top_frame, height=30, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=(10, 5))
        ctk.CTkLabel(header, text="Carga de Índices (IPC)", font=("Segoe UI", 14, "bold"), text_color=COLORS["text_primary"]).pack(side="left")
        
        form_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        form_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        # Input Elements
        ctk.CTkLabel(form_frame, text="Período:", font=("Segoe UI", 12)).pack(side="left", padx=(0, 5))
        self.ipc_date_entry = DateEntry(form_frame, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='dd/mm/yyyy')
        self.ipc_date_entry.pack(side="left", padx=5)
        
        ctk.CTkLabel(form_frame, text="Valor (%):", font=("Segoe UI", 12)).pack(side="left", padx=(15, 5))
        self.ipc_val_entry = ctk.CTkEntry(form_frame, width=80, placeholder_text="4.2")
        self.ipc_val_entry.pack(side="left", padx=5)
        
        ctk.CTkButton(form_frame, text="+ Agregar Manual", command=self.add_ipc_manual, fg_color=COLORS["primary_button"], width=130).pack(side="left", padx=20)
        
        ctk.CTkButton(form_frame, text="☁️ Sincronizar INDEC", command=self.sync_indec, fg_color=COLORS["accent_purple"]).pack(side="right", padx=5)

        # 2. Table Area
        bottom_frame = ctk.CTkFrame(self.tab_ipc, fg_color="transparent")
        bottom_frame.pack(fill="both", expand=True)
        
        # Table Header
        header_frame = ctk.CTkFrame(bottom_frame, height=35, fg_color=COLORS["sidebar_background"], corner_radius=6)
        header_frame.pack(fill="x", pady=(0, 5))
        header_frame.grid_columnconfigure(0, weight=1) # Fecha
        header_frame.grid_columnconfigure(1, weight=1) # Valor
        header_frame.grid_columnconfigure(2, weight=2) # Origen
        header_frame.grid_columnconfigure(3, weight=1) # Actions
        
        # Headers with Sort Logic
        cols = [("Fecha (Mes/Año)", 0, "center", "fecha"), ("Valor (%)", 1, "center", "valor"), ("Acciones", 3, "center", None)]
        
        self.ipc_header_widgets = {}
        for txt, col, anchor, sort_key in cols:
             # Col mapping adjusted: Fecha=0, Valor=1, Actions=3 (keep 3 for layout stability or move to 2)
             # Let's move Actions to 2
            lbl = ctk.CTkLabel(header_frame, text=txt, font=("Segoe UI", 12, "bold"), text_color="white", anchor=anchor, cursor="hand2" if sort_key else "arrow")
            # If col 3 is actions, re-map
            final_col = col if col < 2 else 2
            lbl.grid(row=0, column=final_col, sticky="ew", padx=10, pady=5)
            
            if sort_key:
                lbl.bind("<Button-1>", lambda e, k=sort_key: self.sort_ipc_by(k))
                self.ipc_header_widgets[sort_key] = (lbl, txt)
            
        self._update_ipc_header_arrows()

        # Scrollable List
        self.list_ipc = ctk.CTkScrollableFrame(bottom_frame, fg_color=COLORS["content_surface"])
        self.list_ipc.pack(fill="both", expand=True)
        self.list_ipc.grid_columnconfigure(0, weight=1)
        self.list_ipc.grid_columnconfigure(1, weight=1)
        self.list_ipc.grid_columnconfigure(2, weight=2)
        self.list_ipc.grid_columnconfigure(3, weight=1)
    
    def sort_ipc_by(self, key):
        print(f"DEBUG: sort_ipc_by called with {key}")
        if self.ipc_sort_col == key:
            self.ipc_sort_desc = not self.ipc_sort_desc
        else:
            self.ipc_sort_col = key
            self.ipc_sort_desc = True
            
        self._update_ipc_header_arrows()
        self.load_ipc_data()

    def _update_ipc_header_arrows(self):
        for key, (lbl, orig_txt) in self.ipc_header_widgets.items():
            if key == self.ipc_sort_col:
                arrow = " ▼" if self.ipc_sort_desc else " ▲"
                lbl.configure(text=f"{orig_txt}{arrow}")
            else:
                lbl.configure(text=orig_txt)

    def load_ipc_data(self):
        print(f"DEBUG: loading data. Sort: {self.ipc_sort_col} (Desc: {self.ipc_sort_desc})")
        
        # Robust Clear: Destroy explicitly tracked rows
        for row in self.ipc_rows:
            try:
                row.destroy()
            except: pass
        self.ipc_rows.clear()
        
        indices = self.service.get_all_indices()
        
        # Apply Sort
        if self.ipc_sort_col == "fecha":
            indices.sort(key=lambda x: x.periodo, reverse=self.ipc_sort_desc)
        elif self.ipc_sort_col == "valor":
             # Force float conversion for safe sort
            # Sort
             indices.sort(key=lambda x: parse_localized_float(x.valor or 0), reverse=self.ipc_sort_desc)

        for i, idx in enumerate(indices):
            # Zebra
            bg = "transparent" if i % 2 == 0 else COLORS["main_background"]
            
            row = ctk.CTkFrame(self.list_ipc, fg_color=bg, corner_radius=0)
            row.pack(fill="x", pady=1)
            self.ipc_rows.append(row) # Track for next clear
            
            row.grid_columnconfigure(0, weight=1)
            row.grid_columnconfigure(1, weight=1)
            row.grid_columnconfigure(2, weight=2)
            row.grid_columnconfigure(3, weight=1)
            
            p_str = idx.periodo.strftime("%m/%Y")
            
            # Date
            ctk.CTkLabel(row, text=p_str, anchor="center", font=("Consolas", 12)).grid(row=0, column=0, sticky="ew")
            
            # Val
            color_val = COLORS["status_overdue"] if idx.valor > 10 else COLORS["text_primary"]
            ctk.CTkLabel(row, text=f"{idx.valor:.1f}%", anchor="center", font=("Segoe UI", 12, "bold"), text_color=color_val).grid(row=0, column=1, sticky="ew")
            
            # Source Removed
            # ctk.CTkLabel(row, text=idx.descripcion or "Manual", anchor="w", font=("Segoe UI", 12)).grid(row=0, column=2, sticky="ew", padx=10)
            
            # Action
            act_frame = ctk.CTkFrame(row, fg_color="transparent")
            act_frame.grid(row=0, column=2)
            
            ctk.CTkButton(act_frame, text="✎", width=30, height=25, fg_color=COLORS["primary_button"], command=lambda x=idx: self.edit_ipc(x.id, x.valor)).pack(side="left", padx=2)
            ctk.CTkButton(act_frame, text="🗑️", width=30, height=25, fg_color=COLORS["status_overdue"], command=lambda x=idx: self.delete_ipc(x.id)).pack(side="left", padx=2)

    # --- ACTION HANDLERS ---
    # NOTE: Replaced Treeview, so click handlers need update.
    # However, double click logic (on_ipc_double_click) is replaced by Edit button in row.

    def add_ipc_manual(self):
        try:
            val = parse_localized_float(self.ipc_val_entry.get())
            dt = self.ipc_date_entry.get_date()
            dt = dt.replace(day=1) # Normalize
            
            self.service.add_index(dt, val, "Manual")
            self.load_ipc_data()
            self.ipc_val_entry.delete(0, "end")
            messagebox.showinfo("Guardado", f"Índice para {dt.strftime('%m/%Y')} agregado.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def delete_ipc(self, item_id):
        confirm = messagebox.askyesno("Confirmar Eliminación", 
                                      "¿Estás seguro de eliminar este índice?\nEsto podría afectar cálculos históricos.")
        if confirm:
            try:
                self.service.delete_index(int(item_id))
                self.load_ipc_data()
            except Exception as e:
                messagebox.showerror("Error", str(e))
    
    # Removed delete_selected_ipc (legacy)
    # Removed on_ipc_double_click (legacy)
    # Kept edit_ipc logic (called from button)

    def edit_ipc(self, idx_id, current_val):
        dialog = ctk.CTkInputDialog(text=f"Editar Valor para ID {idx_id}:", title="Corregir Índice")
        new_val = dialog.get_input()
        if new_val:
            try:
                val_dec = parse_localized_float(new_val)
                self.service.update_index(int(idx_id), val_dec)
                self.load_ipc_data()
                messagebox.showinfo("Éxito", "Índice actualizado.")
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def sync_indec(self):
        def _run():
            try:
                success, count = IndecService.sync_indices()
                self.after(0, lambda: self._post_sync(success, count))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error Sync", str(e)))
        
        threading.Thread(target=_run, daemon=True).start()
        
    def _post_sync(self, success, count):
        if success:
            messagebox.showinfo("Sincronización INDEC", f"Proceso completado.\nNuevos registros: {count}")
            self.load_ipc_data()
        else:
            messagebox.showwarning("INDEC", "No se pudieron obtener datos nuevos (API Error o sin cambios).")



    # --- DASHBOARD LOGIC (Simplified) ---
    def on_param_change(self, _=None): self.load_dashboard_data()
    
    def load_dashboard_data(self):
        # ... Reuse logic ...
        gran_map = {"Diario": "D", "Semanal": "W", "Mensual": "M", "Anual": "Y"}
        # Dynamic date range: from 2023 to end of current year
        today = date.today()
        end_of_year = date(today.year, 12, 31)
        
        req = AnalysisRequestDTO(
            start_date=date(2023,1,1),
            end_date=end_of_year,
            granularity=gran_map[self.combo_gran.get()],
            adjust_inflation=self.switch_inf.get() == 1
        )
        threading.Thread(target=self._fetch_bg, args=(req,), daemon=True).start()

    def _fetch_bg(self, req):
        data = self.service.get_analysis(req)
        self.after(0, lambda: self.render(data))

    def render(self, data):
        self.lbl_total_val.configure(text=f"${format_currency(data.total_period)}")
        
        # Optimize: Clear axes instead of destroying widget
        self.ax.clear()
        
        dates = [x['date'] for x in data.time_series]
        vals = [x['value'] for x in data.time_series]
        
        self.ax.plot(dates, vals, marker='o', color=COLORS["primary_button"])
        
        # Format Date Axis if needed (Auto usually works well enough for overview)
        if len(dates) > 10:
             self.fig.autofmt_xdate()
             
        self.chart_canvas.draw()

    def tkraise(self, *args, **kwargs):
        super().tkraise(*args, **kwargs)
        self.load_dashboard_data()
        self.load_ipc_data()


