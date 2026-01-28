import customtkinter as ctk
import threading
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime
from services.proactive_service import ProactiveService
from services.vencimiento_service import VencimientoService
from config import COLORS, FONTS
from models.entities import Vencimiento, EstadoVencimiento, Moneda
from services.cognitive_service import CognitiveService
from utils.import_helper import format_currency
from utils.format_helper import parse_localized_float
from database import SessionLocal

class DashboardView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        # Modern SaaS Background (Soft Blue-Grey)
        self.configure(fg_color="#F0F3F5")

        # Grid Configuration
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0) # Header
        self.grid_rowconfigure(1, weight=0) # Compact KPIs
        self.grid_rowconfigure(2, weight=1) # Trends (Line + Donut)
        self.grid_rowconfigure(3, weight=1) # Actions (Timeline + Top)

        # --- ROW 0: HEADER ---
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, padx=25, pady=(20, 15), sticky="ew")
        
        # Title
        title_box = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        title_box.pack(side="left")
        ctk.CTkLabel(title_box, text="Hola, Admin 👋", font=("Segoe UI", 26, "bold"), text_color="#2C3E50").pack(anchor="w")
        ctk.CTkLabel(title_box, text="Aquí está tu resumen financiero", font=("Segoe UI", 13), text_color="#7F8C8D").pack(anchor="w")

        # Controls
        ctrl_box = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        ctrl_box.pack(side="right")
        
        # --- Month Navigation (NEW) ---
        from views.components.time_navigator import TimeNavigatorView
        nav_box = ctk.CTkFrame(ctrl_box, fg_color="transparent")
        nav_box.pack(side="left", padx=10)
        
        self.time_navigator = TimeNavigatorView(nav_box, on_change_command=self.on_period_change)
        self.time_navigator.pack(side="left", padx=2)
        
        # Initialize Bounds
        self.after(100, self.update_navigator_limits)
        
        # COGNITIVE PULSE (Restored)
        self.lbl_status = ctk.CTkLabel(ctrl_box, text="ZEN MODE", font=("Segoe UI", 11, "bold"), 
                                       text_color="#2ECC71", fg_color="#EAFAF1", corner_radius=10, width=100, height=24)
        self.lbl_status.pack(side="left", padx=(10, 5))
        
        self.lbl_streak = ctk.CTkLabel(ctrl_box, text="", font=("Segoe UI", 11, "bold"), corner_radius=10, height=24)
        # Packed dynamically in apply_ux_state
        
        self.lbl_loading = ctk.CTkLabel(ctrl_box, text="Actualizando...", font=("Segoe UI", 11, "bold"), text_color="#A569BD")
        
        self.switch_currency = ctk.CTkSwitch(ctrl_box, text="USD", font=("Segoe UI", 12, "bold"), 
                                             command=self.reload_data, width=50, progress_color="#A569BD", fg_color="#D7BDE2")
        self.switch_currency.pack(side="right", padx=10)

        # --- ROW 1: COMPACT KPIs (Color Cards) ---
        self.kpi_container = ctk.CTkFrame(self, fg_color="transparent")
        self.kpi_container.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.kpi_container.grid_columnconfigure((0,1,2), weight=1)

        # Modern Layout: Distinct colored cards
        self.kpi_card_1 = self._create_kpi_card_saas(self.kpi_container, 0, "#FDEDEC", "#E74C3C") # Red Tint
        self.kpi_card_2 = self._create_kpi_card_saas(self.kpi_container, 1, "#EBF5FB", "#3498DB") # Blue Tint
        self.kpi_card_3 = self._create_kpi_card_saas(self.kpi_container, 2, "#E9F7EF", "#2ECC71") # Green Tint

        # --- ROW 2: TRENDS & COMPOSITION ---
        self.trends_row = ctk.CTkFrame(self, fg_color="transparent")
        self.trends_row.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.trends_row.grid_columnconfigure(0, weight=3) # Line Chart (Wide)
        self.trends_row.grid_columnconfigure(1, weight=2) # Donut (Narrow)
        self.trends_row.grid_rowconfigure(0, weight=1)

        # Evolution (Left)
        self.card_evolution = self._create_saas_card(self.trends_row)
        self.card_evolution.grid(row=0, column=0, padx=(0, 20), sticky="nsew")
        
        # Composition (Right)
        self.card_composition = self._create_saas_card(self.trends_row)
        self.card_composition.grid(row=0, column=1, padx=0, sticky="nsew")

        # --- ROW 3: ACTION & DRIVERS ---
        self.action_row = ctk.CTkFrame(self, fg_color="transparent")
        self.action_row.grid(row=3, column=0, padx=20, pady=(0, 25), sticky="nsew")
        self.action_row.grid_columnconfigure(0, weight=2) # Timeline
        self.action_row.grid_columnconfigure(1, weight=1) # Top Bar
        self.action_row.grid_rowconfigure(0, weight=1)

        # Timeline (Left)
        self.card_timeline = self._create_saas_card(self.action_row)
        self.card_timeline.grid(row=0, column=0, padx=(0, 20), sticky="nsew")
        
        # Timeline Header
        tl_head = ctk.CTkFrame(self.card_timeline, fg_color="transparent", height=30)
        tl_head.pack(fill="x", padx=20, pady=15)
        # Iconic Header
        ctk.CTkLabel(tl_head, text="📅 Agenda de Pagos", font=("Segoe UI", 14, "bold"), text_color="#2C3E50").pack(side="left")
        
        # Table Header (Pill Shape)
        self.tbl_header = ctk.CTkFrame(self.card_timeline, fg_color="#F8F9F9", height=35, corner_radius=15)
        self.tbl_header.pack(fill="x", padx=20, pady=(0,10))
        self.tbl_header.grid_columnconfigure(0, weight=1)
        self.tbl_header.grid_columnconfigure(1, weight=4)
        self.tbl_header.grid_columnconfigure(2, weight=1)
        
        self._setup_sort_buttons()

        self.scroll_t = ctk.CTkScrollableFrame(self.card_timeline, fg_color="transparent")
        # Match Header Padding (20px) for strict alignment
        self.scroll_t.pack(fill="both", expand=True, padx=20, pady=5)
        self.scroll_t.grid_columnconfigure(0, weight=1)
        self.scroll_t.grid_columnconfigure(1, weight=4)
        self.scroll_t.grid_columnconfigure(2, weight=1)

        # Top Drivers (Right)
        self.card_drivers = self._create_saas_card(self.action_row)
        self.card_drivers.grid(row=0, column=1, padx=0, sticky="nsew")

        # State
        self.target_currency = "ARS"
        self._pulse_job = None
        self.timeline_data = []
        self.db_sort_col = "date"
        self.db_sort_desc = False
        self.current_date = datetime.now().date()
        
        # Perf Flags
        self.is_dirty = True
        self.last_loaded_params = None # (date, currency)

    def _create_saas_card(self, parent):
        # White, Round (20px), Subtle Shadow effect via border color
        return ctk.CTkFrame(parent, fg_color="#FFFFFF", corner_radius=20, border_width=1, border_color="#EAEDED")

    def _create_kpi_card_saas(self, parent, col, bg_color, accent_color):
        f = ctk.CTkFrame(parent, fg_color=bg_color, corner_radius=20, border_width=0)
        f.grid(row=0, column=col, padx=10, sticky="ew")
        return f

    def _setup_sort_buttons(self):
        cols = [("FECHA", "date", "w"), ("CONCEPTO", "detail", "w"), ("IMPORTE", "amount", "e")]
        self.header_btns = {}
        for idx, (txt, key, anchor) in enumerate(cols):
            btn = ctk.CTkButton(
                self.tbl_header, text=txt, font=("Segoe UI", 11, "bold"), 
                text_color="#95A5A6", fg_color="transparent", hover_color="#EAEDED",
                anchor=anchor, height=30, command=lambda c=key: self.sort_timeline_by(c)
            )
            btn.grid(row=0, column=idx, sticky="ew", padx=15)
            self.header_btns[key] = btn

    # ... data loading ...
    def reload_data(self):
        # Explicit reload (Switch toggled or Month changed)
        self.target_currency = Moneda.USD.value if self.switch_currency.get() == 1 else Moneda.ARS.value
        self.start_data_load(force=True)

    def mark_dirty(self):
        self.is_dirty = True

    def start_data_load(self, force=True):
        # Update Period Label always
        # Update Period Label always
        if hasattr(self, 'time_navigator'):
             self.time_navigator.current_date = self.current_date
             self.time_navigator.update_ui()
        
        # Lazy Check
        # Params that affect data: current_date (month/year), target_currency
        current_params = (self.current_date.month, self.current_date.year, self.target_currency)
        
        if not force and not self.is_dirty and current_params == self.last_loaded_params:
            return

        self.last_loaded_params = current_params
        self.is_dirty = False

        self.lbl_loading.pack(side="left", padx=5)
        threading.Thread(target=self.fetch_data, daemon=True).start()

    def fetch_data(self):
        from controllers.dashboard_controller import DashboardController
        data = DashboardController().get_executive_summary(currency=self.target_currency, reference_date=self.current_date)
        self.after(0, lambda: self.update_ui(data))

    def update_ui(self, data):
        self.lbl_loading.pack_forget()
        if not data: return

        # Restore Cognitive State
        self.apply_ux_state(data.ux_state) 
        sym = "US$" if self.target_currency == "USD" else "$"

        # 1. KPIs (SaaS Style)
        # Deuda
        self._render_saas_kpi(self.kpi_card_1, "Deuda Pendiente", f"{sym}{format_currency(data.kpis.deuda_exigible)}", "#E74C3C")
        # Prevision
        self._render_saas_kpi(self.kpi_card_2, "Previsión (15 días)", f"{sym}{format_currency(data.kpis.prevision_caja)}", "#3498DB")
        # Eficiencia
        # Eficiencia (Modified to Financial Efficiency)
        # Logic: If saved > 0 -> Green, Else (Surcharge) -> Red
        is_saving = data.kpis.total_ahorrado >= 0
        color = "#2ECC71" if is_saving else "#E74C3C" 
        lbl = "Ahorro Mes" if is_saving else "Recargo Mes"
        val = f"{sym}{format_currency(abs(data.kpis.total_ahorrado))}"
        
        # Optional: Show % in small text? For now, main value.
        self._render_saas_kpi(self.kpi_card_3, lbl, val, color, subtext=f"{data.kpis.ahorro_pct:.1f}%")

        # 2. Charts
        self._render_chart_header(self.card_evolution, "📈 Tendencia de Gastos", lambda p: self.draw_evolution(p, data.charts.evolution))
        self._render_chart_header(self.card_composition, "🍩 Distribución", lambda p: self.draw_donut(p, data.charts.by_category))
        self._render_chart_header(self.card_drivers, "🏆 Top 5 Costos", lambda p: self.draw_horizontal_bar(p, data.charts.top_properties, sym))

        # --- AI INSIGHTS CARD (New) ---
        # Insert a new frame or use an existing slot? 
        # Ideally we want a prominent "Assistant" section.
        # Let's override 'Timeline' header or add a specialized AI card if data exists.
        
        if data.ai:
             self._render_ai_insights(data.ai, sym)

        # 3. Timeline
        self.timeline_data = list(data.timeline)
        self.render_timeline_items()

    def _render_ai_insights(self, ai, sym):
        # We need a dedicated container. For now, let's inject it into action_row or above it?
        # Let's re-purpose the top bar "Smart Greeting" area or add a new Row?
        # Adding a new row might break grid layout if not configured.
        # Let's use a Modal Overlay? No.
        # Let's insert it dynamically into the "Stats" container (KPI) or below header?
        # KPI container has 3 cols. Let's add a NEW row for AI? 
        # Or simpler: Add it to the top of "Timeline" card as a "Featured Insight"?
        pass # Placeholder for actual implementation in next step
        
        # ACTUALLY, let's create a dedicated method to build the UI properly
        # We will add a new frame 'ai_frame' in __init__? 
        # Or just pack it into self.header_frame?
        
        # Best spot: Top of "Timeline" (Left Action Panel)
        # Clear previous AI widgets if any
        # We need a stable container. 
        # Let's use 'self.card_timeline' header area.
        
        # 1. Forecast Banner
        if ai.forecast_amount > 0:
            # Check if banner exists
            if not hasattr(self, 'ai_banner'):
                 self.ai_banner = ctk.CTkFrame(self.card_timeline, fg_color="#F3E5F5", corner_radius=10, border_color="#D7BDE2", border_width=1)
                 self.ai_banner.pack(fill="x", padx=20, pady=(10, 0), before=self.tbl_header)
            
            for w in self.ai_banner.winfo_children(): w.destroy()
            
            # Icon
            ctk.CTkLabel(self.ai_banner, text="🔮", font=("Segoe UI", 20)).pack(side="left", padx=10, pady=5)
            
            # Text
            txt_frame = ctk.CTkFrame(self.ai_banner, fg_color="transparent")
            txt_frame.pack(side="left", fill="both", expand=True)
            
            f_val = f"{sym}{format_currency(ai.forecast_amount)}"
            ctk.CTkLabel(txt_frame, text=f"Predicción Mes Próximo: {f_val}", font=("Segoe UI", 12, "bold"), text_color="#8E44AD", anchor="w").pack(fill="x")
            ctk.CTkLabel(txt_frame, text=ai.forecast_reason, font=("Segoe UI", 11), text_color="#5B2C6F", anchor="w").pack(fill="x")
            
        # 2. Creep Alerts (Insect)
        if ai.price_alerts:
             if not hasattr(self, 'creep_banner'):
                 self.creep_banner = ctk.CTkFrame(self.card_drivers, fg_color="#FDEDEC", corner_radius=10, border_color="#F1948A", border_width=1)
                 self.creep_banner.pack(fill="x", padx=20, pady=(10, 0), before=self.card_drivers.winfo_children()[0] if self.card_drivers.winfo_children() else None)
             
             for w in self.creep_banner.winfo_children(): w.destroy()
             
             ctk.CTkLabel(self.creep_banner, text="🐜 Inflación Hormiga Detectada", font=("Segoe UI", 11, "bold"), text_color="#E74C3C").pack(anchor="w", padx=10, pady=(5,0))
             
             for alert in ai.price_alerts[:2]: # Show max 2
                 ctk.CTkLabel(self.creep_banner, text=f"• {alert}", font=("Segoe UI", 10), text_color="#C0392B", anchor="w").pack(anchor="w", padx=15, pady=2)

    def _render_saas_kpi(self, card, title, value, accent_color, subtext=None):
        for w in card.winfo_children(): w.destroy()
        
        # Center content
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=20, pady=15)
        
        ctk.CTkLabel(content, text=title, font=("Segoe UI", 11, "bold"), text_color=accent_color).pack(anchor="w")
        ctk.CTkLabel(content, text=value, font=("Segoe UI", 26, "bold"), text_color="#2C3E50").pack(anchor="w", pady=(5,0))
        if subtext:
             ctk.CTkLabel(content, text=subtext, font=("Segoe UI", 10), text_color="#7F8C8D").pack(anchor="w")

    def _render_chart_header(self, card, title, draw_fn):
        for w in card.winfo_children(): w.destroy()
        
        h = ctk.CTkFrame(card, fg_color="transparent", height=30)
        h.pack(fill="x", padx=20, pady=(15, 5))
        ctk.CTkLabel(h, text=title, font=("Segoe UI", 13, "bold"), text_color="#34495E").pack(side="left")
        
        plot_frame = ctk.CTkFrame(card, fg_color="transparent")
        plot_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        draw_fn(plot_frame)

    # --- CHARTS (Modern SaaS Polish) ---
    def draw_evolution(self, parent, data_list):
        if not data_list or sum(x['amount'] for x in data_list) == 0:
            ctk.CTkLabel(parent, text="Sin actividad reciente", font=("Segoe UI", 12), text_color="#BDC3C7").pack(expand=True)
            return

        fig = Figure(figsize=(5, 3), dpi=90, facecolor="#FFFFFF")
        fig.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.15)
        
        ax = fig.add_subplot(111)
        ax.set_facecolor("#FFFFFF")
        
        dates = [x['period'] for x in data_list]
        vals = [x['amount'] for x in data_list]
        x_nums = range(len(dates))

        # Modern "Glow" Color
        color_main = "#A569BD" # Purple
        
        # S M O O T H I N G
        try:
            import numpy as np
            from scipy.interpolate import make_interp_spline
            
            # Create smooth curve
            X_Y_Spline = make_interp_spline(x_nums, vals)
            X_ = np.linspace(min(x_nums), max(x_nums), 500)
            Y_ = X_Y_Spline(X_)
            
            # Plot
            # 1. Glow (Thick, low alpha)
            ax.plot(X_, Y_, color=color_main, linewidth=6, alpha=0.2)
            # 2. Core (Thin, solid)
            ax.plot(X_, Y_, color=color_main, linewidth=2.5)
            # 3. Fill
            ax.fill_between(X_, Y_, color=color_main, alpha=0.05)
            
        except ImportError:
            # Fallback if no scipy
            ax.plot(dates, vals, color=color_main, linewidth=5, alpha=0.2)
            ax.plot(dates, vals, color=color_main, marker='o', markersize=5, linewidth=2)
            ax.fill_between(dates, vals, color=color_main, alpha=0.05)
        
        # Clean Grid
        ax.grid(True, linestyle=':', alpha=0.3, color='#95A5A6')
        for s in ax.spines.values(): s.set_visible(False)
        
        # Custom X Ticks
        # If smoothed, we need to map back the ticks. 
        # Matplotlib handles categories well with 'plot', but 'plot(num, num)' needs manual ticks.
        # Simple hack: just set xticks to x_nums and labels to dates
        ax.set_xticks(x_nums)
        ax.set_xticklabels(dates)
        
        ax.tick_params(axis='x', labelcolor="#7F8C8D", labelsize=9, pad=5)
        ax.tick_params(axis='y', left=False, labelleft=False)

        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def draw_donut(self, parent, data_dict):
        if not data_dict:
             ctk.CTkLabel(parent, text="Sin gastos registrados", font=("Segoe UI", 12), text_color="#BDC3C7").pack(expand=True)
             return

        # Clean Data: Cast to float, ignore negatives (Pie can't handle them)
        try:
            # Ensure values are floats
            clean_vals = []
            clean_labels = []
            
            for k, v in data_dict.items():
                val_float = parse_localized_float(v)
                if val_float > 0.01: # Filter tiny/negative
                    clean_vals.append(val_float)
                    clean_labels.append(k)
            
            if not clean_vals or sum(clean_vals) == 0:
                 ctk.CTkLabel(parent, text="Sin gastos significativos", font=("Segoe UI", 12), text_color="#BDC3C7").pack(expand=True)
                 return
                 
        except Exception as e:
            ctk.CTkLabel(parent, text="Error en datos", font=("Segoe UI", 12), text_color="#E74C3C").pack(expand=True)
            return

        fig = Figure(figsize=(4, 4), dpi=90, facecolor="#FFFFFF")
        # Layout: Legend at BOTTOM to avoid squeezing width
        fig.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.25)
        
        ax = fig.add_subplot(111)
        
        # CANDY PASTEL PALETTE
        colors = ['#AC92EB', '#4FC1E8', '#A0D568', '#FFCE54', '#ED5564']
        
        # Thinner modern ring + Auto Pct
        wedges, texts, autotexts = ax.pie(clean_vals, labels=None, autopct='%1.0f%%', startangle=90, colors=colors, pctdistance=0.80, 
                                          wedgeprops=dict(width=0.40, edgecolor='white', linewidth=3), labeldistance=1.1)
        
        # Style percentages
        for t in autotexts: t.set_fontsize(8); t.set_color("white"); t.set_fontweight('bold')
        
        # Legend (Bottom, 2 columns)
        ax.legend(wedges, clean_labels, loc="upper center", bbox_to_anchor=(0.5, -0.02), frameon=False, fontsize=8, ncol=2)
        
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def draw_horizontal_bar(self, parent, data_dict, currency_sym="$"):
        if not data_dict or sum(data_dict.values()) == 0:
             ctk.CTkLabel(parent, text="Buscando datos...", font=("Segoe UI", 12), text_color="#BDC3C7").pack(expand=True)
             return
        
        # Bigger figure for labels
        fig = Figure(figsize=(4, 3), dpi=90, facecolor="#FFFFFF")
        
        # Tight Layout for Auto-Spacing
        # Increased Left Margin for Address Labels (0.30 -> 0.45)
        # Increased Bottom slightly
        fig.subplots_adjust(left=0.45, right=0.95, top=0.95, bottom=0.10)
        
        ax = fig.add_subplot(111)
        ax.set_facecolor("#FFFFFF")
        
        items = sorted(data_dict.items(), key=lambda x: x[1])
        # Increased limit to 40 chars to prevent cutting off addresses
        keys = [x[0][:40] + '..' if len(x[0])>40 else x[0] for x in items] 
        # Convert Decimals to float for Matplotlib
        vals = [parse_localized_float(x[1]) for x in items]
        
        # Bars
        # Bars
        bars = ax.barh(keys, vals, color="#4FC1E8", height=0.6)
        
        for s in ax.spines.values(): s.set_visible(False)
        
        # RESTORE Y LABELS - Left Aligned visually
        ax.set_yticks(range(len(keys)))
        ax.set_yticklabels(keys)
        # Force strict Left Alignment for professional list look
        # We use a large padding to push the "Left Edge" of the text to the far left
        for label in ax.get_yticklabels():
             label.set_horizontalalignment('left')
             
        ax.tick_params(axis='y', left=False, labelcolor="#2C3E50", labelsize=10, pad=125) 
        
        ax.set_xticks([])
        ax.tick_params(axis='x', bottom=False, labelbottom=False)
        
        # Expand X-Axis to fit value labels on the right (approx 20% margin)
        if vals:
             ax.set_xlim(0, max(vals) * 1.20)
        
        # Value Label on the right
        for i, val in enumerate(vals):
             # Increased font size for values + 2 decimal places
             ax.text(val, i, f" {currency_sym}{val:,.2f}", va='center', fontsize=9, color="#7F8C8D")

        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def sort_timeline_by(self, key):
        if self.db_sort_col == key:
            self.db_sort_desc = not self.db_sort_desc
        else:
            self.db_sort_col = key
            self.db_sort_desc = False
            
        def get_v(x, k):
            if k == 'amount': return x.monto
            if k == 'date': 
                try: d,m = x.fecha.split('/'); return int(m)*100+int(d)
                except: return 0
            return x.detalle
            
        self.timeline_data.sort(key=lambda x: get_v(x, self.db_sort_col), reverse=self.db_sort_desc)
        self.render_timeline_items()

    def render_timeline_items(self):
        for w in self.scroll_t.winfo_children(): w.destroy()
        sym = "US$" if self.target_currency == "USD" else "$"
        
        for i, item in enumerate(self.timeline_data):
            # Spacer
            row = ctk.CTkFrame(self.scroll_t, fg_color="transparent")
            row.pack(fill="x", pady=6) # Increased spacing between rows
            row.grid_columnconfigure(0, weight=1)
            row.grid_columnconfigure(1, weight=5) # More weight for Detail
            row.grid_columnconfigure(2, weight=1)
            
            # Pill row with subtle border
            f = ctk.CTkFrame(row, fg_color="#FFFFFF", corner_radius=12, border_width=1, border_color="#D7E4E9") # Slightly darker border for contrast
            f.grid(row=0, column=0, columnspan=3, sticky="nsew")
            
            # Grid Layout for STRICT alignment with Header
            f.grid_columnconfigure(0, weight=1)
            f.grid_columnconfigure(1, weight=4)
            f.grid_columnconfigure(2, weight=1)

            # Date (Col 0)
            ctk.CTkLabel(f, text=item.fecha, font=("Segoe UI", 12, "bold"), text_color="#A569BD").grid(row=0, column=0, sticky="w", padx=15, pady=10)
            
            # Detail (Col 1)
            # Use 'ew' to fill space? 'w' is safer for text.
            ctk.CTkLabel(f, text=item.detalle, font=("Segoe UI", 12), text_color="#566573", anchor="w").grid(row=0, column=1, sticky="ew", padx=5)
            
            # Amount (Col 2)
            ctk.CTkLabel(f, text=f"{sym}{format_currency(item.monto)}", font=("Segoe UI", 12, "bold"), text_color="#2C3E50").grid(row=0, column=2, sticky="e", padx=15)

    # --- COGNITIVE LOGIC ---
    def apply_ux_state(self, state):
        if self._pulse_job: self.after_cancel(self._pulse_job); self._pulse_job=None
        
        # 1. Status Badge with Icons
        icons = {"ZEN": "🌿", "FOCUS": "⚡", "CRITICAL": "🔥", "CHAOS": "🌪️"}
        icon = icons.get(state.status, "•")
        
        txt = f"{icon} {state.status}"
        
        # Colors (Background / Text)
        colors = {
            "ZEN": ("#EAFAF1", "#2ECC71"),      # Soft Green
            "FOCUS": ("#FEF9E7", "#F1C40F"),    # Soft Yellow
            "CRITICAL": ("#FADBD8", "#E74C3C"), # Soft Red
            "CHAOS": ("#D6DBDF", "#2C3E50")     # Grey
        }
        bg, fg = colors.get(state.status, ("#EAFAF1", "#2ECC71"))
        
        self.lbl_status.configure(text=txt, fg_color=bg, text_color=fg)
        
        # 2. Streak Badge (Gamification)
        if hasattr(state, 'streak'):
            if state.streak > 0:
                self.lbl_streak.configure(text=f"💎 {state.streak} Días Racha", fg_color="#E8F8F5", text_color="#1ABC9C")
                self.lbl_streak.pack(side="left", padx=5)
            else:
                self.lbl_streak.pack_forget() # Hide if no streak


    def on_period_change(self, target_date):
        # Update current date and reload
        self.current_date = target_date
        
        # Check Period Status (Governance)
        try:
            from services.period_service import PeriodService
            from models.entities import EstadoPeriodo
            
            status = PeriodService.check_period_status(target_date) 
            if status == EstadoPeriodo.CERRADO:
                self.time_navigator.set_lock_status(True)
            else:
                self.time_navigator.set_lock_status(False)
        except Exception: 
            # PeriodLockedError (BLOQUEADO) or other errors defaulting to locked safety
            self.time_navigator.set_lock_status(True)

        self.reload_data()

    def update_navigator_limits(self):
        try:
            from services.period_service import PeriodService
            from datetime import date
            
            # Fetch all periods (sorted desc)
            periods = PeriodService.get_all_periods()
            if not periods:
                return # Can't limit if no periods
                
            # Min = Last in list (Oldest)
            # Max = First in list (Newest)
            
            # Parse YYYY-MM
            def parse_p(p_str):
                 y, m = map(int, p_str.split('-'))
                 return date(y, m, 1)
            
            min_d = parse_p(periods[-1].periodo_id)
            max_d = parse_p(periods[0].periodo_id)
            
            # Update Navigator
            # Note: Dashboard typically doesn't allow creating new periods from here, 
            # so we won't pass an on_new_period_command unless requested.
            self.time_navigator.set_bounds(min_d, max_d)
            
            # Ensure navigator reflects current date
            self.time_navigator.update_ui(self.current_date)
            
        except Exception as e:
            print(f"Error limiting navigator: {e}")

    def tkraise(self, *args, **kwargs):
        super().tkraise(*args, **kwargs)
        # Lazy Load on Show
        self.start_data_load(force=False)
