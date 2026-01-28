import customtkinter as ctk
from datetime import date
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading

from config import COLORS, FONTS
from utils.import_helper import format_currency
from dtos.oracle import SimulationParams
from services.oracle_service import OracleService

class OracleView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(fg_color=COLORS["main_background"])
        self.service = OracleService()

        # Layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- CONTROL SIMULATOR (Toolbar) ---
        self.sim_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.sim_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=10)
        
        ctk.CTkLabel(self.sim_frame, text="Oráculo Financiero (Predicción) 🔮", font=FONTS["heading"], text_color=COLORS["text_primary"]).pack(side="left", padx=0)

        # Right Toolbar
        tool_right = ctk.CTkFrame(self.sim_frame, fg_color="transparent")
        tool_right.pack(side="right")
        
        # USD Entry
        ctk.CTkButton(tool_right, text="▶ Simular Escenario", width=140, command=self.load_projection, fg_color=COLORS["primary_button"]).pack(side="right", padx=10)
        
        self.entry_usd = ctk.CTkEntry(tool_right, width=80, placeholder_text="USD Fut")
        self.entry_usd.pack(side="right", padx=5)
        self.entry_usd.insert(0, "1200") # Default
        ctk.CTkLabel(tool_right, text="USD Futuro:", font=("Segoe UI", 12)).pack(side="right", padx=5)

        # Inflation Slider
        self.lbl_inf = ctk.CTkLabel(tool_right, text="Inf. Est.: 5%", font=("Segoe UI", 12, "bold"), text_color=COLORS["accent_purple"])
        self.lbl_inf.pack(side="right", padx=10)
        
        self.slider_inf = ctk.CTkSlider(tool_right, from_=0, to=50, number_of_steps=50, command=self.on_sim_change, width=150)
        self.slider_inf.set(5) 
        self.slider_inf.pack(side="right", padx=5)

        # --- CONTENT ---
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=3) # Chart
        self.content_frame.grid_rowconfigure(1, weight=2) # Grid/Summary

        # Chart Card
        self.chart_frame = ctk.CTkFrame(self.content_frame, fg_color=COLORS["content_surface"], corner_radius=10, border_width=1, border_color="#D5D8DC")
        self.chart_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 15))
        
        ctk.CTkLabel(self.chart_frame, text="La Montaña de Gastos (Proyección Acumulada)", font=("Segoe UI", 12, "bold"), text_color="gray").pack(pady=5)

        # Summary Grid Card
        self.grid_container = ctk.CTkFrame(self.content_frame, fg_color=COLORS["content_surface"], corner_radius=10, border_width=1, border_color="#D5D8DC")
        self.grid_container.grid(row=1, column=0, sticky="nsew")
        
        ctk.CTkLabel(self.grid_container, text="Flujo de Fondos Proyectado (12 Meses)", font=("Segoe UI", 12, "bold"), text_color=COLORS["text_primary"]).pack(anchor="w", padx=15, pady=10)
        
        # Table Header
        header_frame = ctk.CTkFrame(self.grid_container, height=30, fg_color=COLORS["sidebar_background"], corner_radius=6)
        header_frame.pack(fill="x", padx=10, pady=(0, 5))
        header_frame.grid_columnconfigure(0, weight=1)
        header_frame.grid_columnconfigure(1, weight=1)
        header_frame.grid_columnconfigure(2, weight=3)
        
        cols = [("Mes / Período", 0, "center"), ("Proyección Total", 1, "center"), ("Detalle Crítico (Top Driver)", 2, "w")]
        for txt, col, anchor in cols:
             ctk.CTkLabel(header_frame, text=txt, font=("Segoe UI", 11, "bold"), text_color="white", anchor=anchor).grid(row=0, column=col, sticky="ew", padx=10, pady=5)

        self.grid_frame = ctk.CTkScrollableFrame(self.grid_container, fg_color="transparent")
        self.grid_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.grid_frame.grid_columnconfigure(0, weight=1)
        self.grid_frame.grid_columnconfigure(1, weight=1)
        self.grid_frame.grid_columnconfigure(2, weight=3)

    def on_sim_change(self, val):
        self.lbl_inf.configure(text=f"Inf. Est.: {int(val)}%")

    def load_projection(self):
        try:
            usd_val = float(self.entry_usd.get())
        except: 
            usd_val = 0.0

        params = SimulationParams(
            start_date=date.today(),
            months_to_project=12,
            monthly_inflation_pct=self.slider_inf.get(),
            future_usd_value=usd_val
        )
        
        threading.Thread(target=self._run_bg, args=(params,), daemon=True).start()

    def _run_bg(self, params):
        data = self.service.project_budget(params)
        self.after(0, lambda: self.render(data))

    def render(self, data):
        # 1. Chart (Stacked Area)
        # Clear specific widgets inside chart frame except the title? 
        # Easier to recreate canvas frame wrapper
        for w in self.chart_frame.winfo_children(): 
            if isinstance(w, ctk.CTkLabel): continue # Keep title
            w.destroy()

        fig = Figure(figsize=(5, 3), dpi=80, facecolor=COLORS["content_surface"])
        ax = fig.add_subplot(111)
        ax.set_facecolor(COLORS["content_surface"])

        # Prepare data for plot
        months = sorted(list(data.total_by_month.keys()))
        totals = [data.total_by_month[m] for m in months]
        
        ax.fill_between(months, totals, color=COLORS["primary_button"], alpha=0.4, label="Proyección Total")
        ax.plot(months, totals, color=COLORS["primary_button"], marker="o")
        
        # ax.set_title("La Montaña de Gastos (Proyección Acumulada)", color=COLORS["text_primary"]) # Moved to Label
        ax.tick_params(colors=COLORS["text_primary"], rotation=45, labelsize=8)
        ax.grid(True, linestyle="--", alpha=0.2)
        for spine in ax.spines.values(): spine.set_visible(False) # Clean look
        
        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=(0,10))

        # 2. Detail Grid inside Scrollable
        for w in self.grid_frame.winfo_children(): w.destroy()
        
        # Simple list view for now - could be a Treeview in future
        for i, m in enumerate(months):
            bg = "transparent" if i % 2 == 0 else COLORS["main_background"]
            row = ctk.CTkFrame(self.grid_frame, fg_color=bg, corner_radius=4)
            row.pack(fill="x", pady=1)
            row.grid_columnconfigure(0, weight=1)
            row.grid_columnconfigure(1, weight=1)
            row.grid_columnconfigure(2, weight=3)
            
            # Period
            ctk.CTkLabel(row, text=m, font=("Consolas", 12), anchor="center").grid(row=0, column=0, sticky="ew")
            
            # Total
            val = data.total_by_month[m]
            ctk.CTkLabel(row, text=f"${format_currency(val)}", font=("Segoe UI", 12, "bold"), text_color=COLORS["primary_button"], anchor="center").grid(row=0, column=1, sticky="ew")
            
            # Top Driver
            cat_breakdown = [item for item in data.items if item.period == m]
            top_text = "-"
            if cat_breakdown:
                top = max(cat_breakdown, key=lambda x: x.amount_projected)
                pct = (top.amount_projected / val) * 100 if val > 0 else 0
                # "⚠ Provider (Category): $Amount (Pct%)"
                top_text = f"⚠ {top.description} ({top.category}): ${format_currency(top.amount_projected)} ({int(pct)}%)"
            
            ctk.CTkLabel(row, text=top_text, text_color="gray", anchor="w", font=("Segoe UI", 11)).grid(row=0, column=2, sticky="ew", padx=15)

    def tkraise(self, *args, **kwargs):
        super().tkraise(*args, **kwargs)
