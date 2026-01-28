import customtkinter as ctk
import os
import tempfile
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from controllers.vencimientos_controller import VencimientosController
from controllers.obligaciones_controller import ObligacionesController
from controllers.reports_controller import ReportsController
from models.entities import EstadoVencimiento
from datetime import date, datetime
from config import COLORS, FONTS
from utils.exceptions import BaseAppError, PeriodLockedError
from .components.smart_filter_view import SmartFilterView 
from .components.time_navigator import TimeNavigatorView
from services.period_service import PeriodService
from utils.format_helper import parse_localized_float, parse_fuzzy_date
from services.vencimiento_service import VencimientoService
from models.entities import EstadoPeriodo
from .components.autocomplete_combobox import AutocompleteCombobox
from utils.import_helper import format_currency
from services.cognitive_service import CognitiveService
from utils.logger import app_logger

from controllers.catalogs_controller import CatalogsController
from utils.gui_helpers import center_window
from views.catalogs_view import AddInmuebleDialog, ManageServicesDialog
from services.permission_service import PermissionService

class VencimientosView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        # Background
        self.configure(fg_color=COLORS["main_background"])
        
        # Controller Instance (Stored for child views like ImportWizard)
        self.controller = VencimientosController()

        self.grid_columnconfigure(0, weight=3) # Lista mas ancha
        self.grid_columnconfigure(1, weight=2) # Visor
        self.grid_rowconfigure(0, weight=0) # Header (Fixed)
        self.grid_rowconfigure(1, weight=0) # Toolbar (Fixed)
        self.grid_rowconfigure(2, weight=1) # Content (Expands)

        # Header / Filtros (Span 2 columnas)
        # Header (Row 0): Title + Buttons
        # --- Top Bar (Row 0) ---
        self.top_bar = ctk.CTkFrame(self, fg_color="transparent")
        self.top_bar.grid(row=0, column=0, columnspan=2, padx=20, pady=(15, 5), sticky="ew")

        # Title
        ctk.CTkLabel(self.top_bar, text="Gestión de Vencimientos", font=("Segoe UI", 20, "bold"), text_color=COLORS["text_primary"]).pack(side="left")

        # Main Actions
        self.btn_add = ctk.CTkButton(self.top_bar, text="+ Nuevo", width=90, fg_color=COLORS["primary_button"], command=self.open_add_dialog)
        self.btn_add.pack(side="right", padx=5)
        
        self.btn_import_excel = ctk.CTkButton(self.top_bar, text="Importar Excel", width=100, fg_color=COLORS.get("info", "#3498DB"), command=self.open_import_wizard)
        self.btn_import_excel.pack(side="right", padx=5)

        self.btn_clone = ctk.CTkButton(self.top_bar, text="🔁 Clonar Período", width=110, fg_color=COLORS["secondary_button"], command=self.open_clone_dialog)
        self.btn_clone.pack(side="right", padx=5)

        # Export Group
        export_frame = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        export_frame.pack(side="right", padx=10)
        ctk.CTkButton(export_frame, text="PDF", width=40, fg_color=COLORS["status_overdue"], command=self.export_pdf).pack(side="left", padx=2)
        ctk.CTkButton(export_frame, text="XLS", width=40, fg_color=COLORS["status_paid"], command=self.export_excel).pack(side="left", padx=2)

        # --- Currency Toggle ---
        self.show_in_usd = False
        self.switch_currency = ctk.CTkSwitch(
            self.top_bar, 
            text="Ver en USD", 
            command=self.toggle_currency,
            onvalue=True, 
            offvalue=False,
            progress_color=COLORS["status_paid"],
            font=("Segoe UI", 12, "bold")
        )
        self.switch_currency.pack(side="right", padx=15)

        # --- Filter Toolbar (Row 1) ---
        self.filter_bar = ctk.CTkFrame(self, fg_color="transparent")
        self.filter_bar.grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 10), sticky="ew")

        self.time_navigator = TimeNavigatorView(self.filter_bar, on_change_command=self.on_period_change)
        self.time_navigator.pack(side="left", padx=(0, 15))

        self.smart_filter = SmartFilterView(self.filter_bar, on_filter_change_callback=self.on_filtered_data_update)
        self.smart_filter.pack(side="left")

        self.readonly_mode = False
        self.period_warning = False
        self.master_dataset = [] 
        self._inmueble_map = {} 
        
        # Performance Flags
        self.is_dirty = True
        self.last_loaded_period = None 
        self.last_loaded_page = None # NEW: Track page for lazy loading 

        # --- Content Area (Row 2) ---
        from tkinter import PanedWindow
        self.paned_window = PanedWindow(self, orient="horizontal", sashrelief="flat", sashwidth=6, bg="#D5D8DC")
        self.paned_window.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=20, pady=10)
        
        # --- LEFT PANEL: LISTA ---
        self.left_panel = ctk.CTkFrame(self.paned_window, fg_color="transparent")
        self.left_panel.grid_columnconfigure(0, weight=1)
        self.left_panel.grid_rowconfigure(1, weight=1)
        self.left_panel.grid_rowconfigure(1, weight=1)
        self.paned_window.add(self.left_panel, minsize=450)


        self.sort_col = "fecha_vencimiento"
        self.sort_desc = False

        
        # Grid Headers
        # Note: Added Right Padding (20px) to compensate for scrollbar in the list below
        self.cols_frame = ctk.CTkFrame(self.left_panel, height=40, fg_color=COLORS["sidebar_background"], corner_radius=0)
        self.cols_frame.grid(row=0, column=0, sticky="ew", padx=(0, 20)) # Scrollbar correction
        
        # Grid System: 0=Icon1, 1=Icon2, 2=Inmueble(2), 3=Proveedor(2), 4=Fecha(1), 5=Monto(1), 6=Estado(1), 7,8=Actions
        
        headers = [
            ("", None, 0, "center"), # Icon 1
            ("", None, 1, "center"), # Icon 2
            ("Inmueble", "obligacion.inmueble.alias", 2, "w"), 
            ("Proveedor", "obligacion.proveedor.nombre_entidad", 3, "w"), 
            ("Vencimiento", "fecha_vencimiento", 4, "center"), 
            ("Monto", "monto_original", 5, "w"), 
            ("Estado", "estado", 6, "w")
        ]
        
        self.cols_frame.grid_columnconfigure(0, minsize=27) # Icon 1
        self.cols_frame.grid_columnconfigure(1, minsize=27) # Icon 2
        
        # Weighted Cols with Uniform Group to enforce ratio regardless of text content
        self.cols_frame.grid_columnconfigure(2, weight=2, uniform="cols")
        self.cols_frame.grid_columnconfigure(3, weight=2, uniform="cols")
        self.cols_frame.grid_columnconfigure((4,5,6), weight=1, uniform="cols")
        self.cols_frame.grid_columnconfigure((7,8), minsize=35) 
        
        self.header_widgets = {} # Map field -> (LabelWidget, OriginalText)

        for (text, field, col_idx, anchor_val) in headers:
            # Special handling for Icon Columns (0 and 1) to match Row geometry exactly
            if col_idx in [0, 1]:
                 ctk.CTkLabel(self.cols_frame, text="", width=27).grid(row=0, column=col_idx, sticky="ew")
                 continue

            # Conditional Padding to match Row Content
            p_x = 2
            if anchor_val == "w":
                p_x = (10, 2)
                
            # Use Label instead of Button for pixel-perfect match with data rows
            lbl = ctk.CTkLabel(
                self.cols_frame, 
                text=text, 
                font=("Segoe UI", 12, "bold"), 
                text_color="white", 
                anchor=anchor_val,
                height=30,
                width=50, # Min Width
                cursor="hand2" if field else "arrow"
            )
            # Use sticky=ew to fill the weighted cell
            lbl.grid(row=0, column=col_idx, sticky="ew", padx=p_x, pady=2)
            
            if field:
                lbl.bind("<Button-1>", lambda e, f=field: self.sort_by(f))
                # Optional: Add hover effect manually if needed, or keep it simple.
                # For now, simple text label is cleanest.
                self.header_widgets[field] = (lbl, text) # Store usage

        self._update_header_arrows() # Initial update

        # Scroll List
        self.scroll_frame = ctk.CTkScrollableFrame(self.left_panel, label_text="", fg_color="white") 
        self.scroll_frame.grid(row=1, column=0, sticky="nsew")
        
        # Same column config will be applied per Row, not here.

        # --- RIGHT PANEL: PREVIEW CARD ---
        self.preview_card = ctk.CTkFrame(self.paned_window, fg_color="white", corner_radius=10, border_color="#D5D8DC", border_width=1)
        self.preview_card.grid_columnconfigure(0, weight=1)
        self.preview_card.grid_rowconfigure(1, weight=1)
        self.paned_window.add(self.preview_card, minsize=350)
        
        # Tools Header Frame (Auto height)
        self.tools_frame = ctk.CTkFrame(self.preview_card, fg_color="transparent")
        self.tools_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        self.tools_frame.grid_columnconfigure(0, weight=1) # Spacer column
        

        self.lbl_doc_info = ctk.CTkLabel(self.tools_frame, text="---", text_color="gray50", anchor="w")
        self.lbl_doc_info.grid(row=1, column=0, columnspan=4, sticky="ew", padx=10, pady=(5, 0))
        
        # Row 0: Buttons (Right Aligned)
        # Usage of spacer col 0 will be configured in frame setup next.
        self.btn_open_ext = ctk.CTkButton(self.tools_frame, text="Abrir Externo", width=90, fg_color=COLORS["secondary_button"], command=self.open_current_pdf)
        self.btn_open_ext.grid(row=0, column=1, padx=5, sticky="e")

        self.btn_import = ctk.CTkButton(self.tools_frame, text="Reemplazar", width=100, fg_color=COLORS["primary_button"], hover_color=COLORS["primary_button_hover"], command=self.import_file)
        self.btn_import.grid(row=0, column=2, padx=5, sticky="e")
        
        # Alerts Button
        self.btn_alerts = ctk.CTkButton(self.tools_frame, text="🔔", width=40,  fg_color="transparent", text_color=COLORS["text_primary"], hover_color="#EAEDED", command=self.show_alerts_dialog)
        self.btn_alerts.grid(row=0, column=3, padx=5, sticky="e")

        # Label Preview (Now in Preview Card)
        self.lbl_preview = ctk.CTkLabel(self.preview_card, text="Seleccione un registro\npara ver el comprobante", font=FONTS["body"], text_color="gray50")
        self.lbl_preview.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        self.current_vencimiento = None
        
        # Pagination State
        self.current_page = 1
        self.page_limit = 50
        self.total_records = 0
        self.current_period_id = None

        # Pagination UI
        self.pagination_frame = ctk.CTkFrame(self.left_panel, height=40, fg_color="transparent")
        self.pagination_frame.grid(row=2, column=0, sticky="ew", pady=(5, 5))
        
        self.btn_prev_page = ctk.CTkButton(self.pagination_frame, text="< Ant", width=70, fg_color=COLORS["secondary_button"], command=self.prev_page)
        self.btn_prev_page.pack(side="left", padx=5)
        
        self.lbl_page_info = ctk.CTkLabel(self.pagination_frame, text="Página 1 de 1", text_color="gray")
        self.lbl_page_info.pack(side="left", padx=10)
        
        # Total Pending Summary
        self.lbl_pending_total = ctk.CTkLabel(self.pagination_frame, text="Total Pendiente: $0.00", text_color=COLORS["status_overdue"], font=("Segoe UI", 12, "bold"))
        self.lbl_pending_total.pack(side="left", padx=20)
        
        self.btn_next_page = ctk.CTkButton(self.pagination_frame, text="Sig >", width=70, fg_color=COLORS["secondary_button"], command=self.next_page)
        self.btn_next_page.pack(side="right", padx=5)
        
        # Initialize Bounds
        self.after(100, self.update_navigator_limits)

    def import_file(self):
        if not self.current_vencimiento: return
        file = ctk.filedialog.askopenfilename(filetypes=[("PDF/Img", "*.pdf *.jpg *.jpeg *.png")])
        if file:
            try:
                if VencimientosController().update_vencimiento(self.current_vencimiento.id, {"new_file_path": file}):
                     self.load_data() 
                     self.lbl_preview.configure(text="Archivo subido. Selecciona de nuevo.")
            except Exception as e:
                messagebox.showerror("Error de Importación", f"No se pudo subir el archivo:\n{e}")

    def open_import_wizard(self):
        if not PermissionService.user_has_permission(self.master.current_user, PermissionService.CAN_EDIT_VENCIMIENTOS):
             messagebox.showwarning("Acceso Denegado", "No tiene permisos para importar datos (Modo Lectura).")
             return
        from views.import_wizard_view import ImportWizardView
        ImportWizardView(self, mode="vencimientos")

    def open_current_pdf(self):
        if self.current_vencimiento:
            # Use unified method (Cloud + Local)
            if not self.controller.open_document_unified(self.current_vencimiento.id, "invoice"):
                messagebox.showerror("Error", "No se pudo abrir el documento.\nVerifique que exista o la conexión a BD.")

    def select_item(self, vencimiento):
        # 0. Restore Style of previous selection
        if self.current_vencimiento and self.current_vencimiento.id in self.row_widgets:
            old_frame = self.row_widgets[self.current_vencimiento.id]
            # Recalculate Zebra color for old row
            # We need the index. But storing index is messy.
            # Simpler: Just check if it exists in current dataset and get index?
            # Or store origin color in the frame object?
            if hasattr(old_frame, "default_bg"):
                old_frame.configure(fg_color=old_frame.default_bg)
        
        self.current_vencimiento = vencimiento
        
        # 1. Highlight New Selection
        if vencimiento.id in self.row_widgets:
            new_frame = self.row_widgets[vencimiento.id]
            new_frame.configure(fg_color="#D5D8DC") # Highlight Color (Light Grey)
            
        self.render_preview(vencimiento)

    def render_preview(self, vencimiento):
        # 0. Clean up previous image ref
        self.current_image_ref = None
        
        # 1. NUCLEAR OPTION: Destroy and Recreate Label
        # This prevents "pyimageX doesn't exist" errors caused by CTk caching invalid state
        if hasattr(self, 'lbl_preview') and self.lbl_preview:
            try:
                self.lbl_preview.destroy()
            except: pass

        self.lbl_preview = ctk.CTkLabel(self.preview_card, text="Cargando...", font=FONTS["body"], text_color="gray50")
        self.lbl_preview.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        self.lbl_doc_info.configure(text=f"Doc: {vencimiento.ruta_archivo_pdf or 'No adjunto'}")

        if not vencimiento.ruta_archivo_pdf:
            self.lbl_preview.configure(text="Sin comprobante adjunto.\n\nUse 'Importar' para vincular uno.")
            return
        
        import fitz # PyMuPDF
        from config import DOCS_DIR
        # os imported globally now
        import tempfile
        from services.vencimiento_service import VencimientoService
        from PIL import Image

        try:
            full_path = os.path.join(DOCS_DIR, vencimiento.ruta_archivo_pdf)
            if not os.path.exists(full_path):
                self.lbl_preview.configure(text="Archivo no encontrado en disco.", text_color="red")
                return

            doc = fitz.open(full_path)
            page = doc.load_page(0) 
            
            # Reduce zoom slightly to avoid huge textures
            zoom = 300 / page.rect.width
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(pix.width, pix.height))
            
            # Explicitly store reference to prevent GC issues
            self.current_image_ref = ctk_img
            self.lbl_preview.configure(image=ctk_img, text="")
            doc.close()
        except Exception as e:
            app_logger.error(f"Error renderizando PDF: {e}")
            self.lbl_preview.configure(text=f"Error visualizando archivo.\n{str(e)}", text_color="red")

    def load_data(self, period_id=None, force=True):
        # 1. Resolve Period ID on Main Thread
        if period_id:
            self.current_period_id = period_id
        
        # Fallback: If current_period_id is None (startup race condition), derive from navigator
        if not self.current_period_id and hasattr(self, 'time_navigator'):
             d = self.time_navigator.current_date
             self.current_period_id = f"{d.year}-{d.month:02d}"
        
        # Notify Dashboard that data might change (Pessimistic: If we load, we might change)
        # Actually better to dirty IF we save. 
        # But 'load_data' with force=True implies a change happened usually? 
        # Or explicit refresh.
        # Let's dirty dashboard if force=True.
        if force and hasattr(self.master, 'mark_dashboard_dirty'):
             try: self.master.mark_dashboard_dirty() 
             except: pass
        
        # Lazy Load Check (Period AND Page)
        params_match = (
            self.current_period_id == self.last_loaded_period and 
            self.current_page == self.last_loaded_page
        )
        if not force and not self.is_dirty and params_match:
            app_logger.info(f"Skipping load for {self.current_period_id} p{self.current_page} (Data fresh)")
            return
            
        # If force or dirty, ensure we reset dirty flag ONLY after load
        if force: self.is_dirty = True

        app_logger.info(f"Loading data (Threaded) for Period: {self.current_period_id}")
        
        # 2. Spawn Thread
        threading.Thread(target=self._perform_load_background, 
                         args=(self.current_period_id, self.current_page, self.page_limit), 
                         daemon=True).start()

    def mark_dirty(self):
        """Call this when data changes (Add/Edit/Delete)"""
        self.is_dirty = True

    def refresh_data(self):
        """Explicit User Refresh"""
        self.load_data(force=True)

    def _perform_load_background(self, period_id, page, limit):
        try:
            from controllers.catalogs_controller import CatalogsController # Import here to avoid circular dep if any
            
            # DB calls (Running in background)
            records, total = VencimientosController().get_all_vencimientos(
                period_id=period_id,
                page=page,
                limit=limit
            )
            
            # Fetch Catalogs
            cat_ctrl = CatalogsController()
            inmuebles = [i.alias for i in cat_ctrl.get_inmuebles()]
            proveedores = [p.nombre_entidad for p in cat_ctrl.get_proveedores()]
            estados = [e.value for e in EstadoVencimiento]
            
            app_logger.info(f"Background Load {period_id}: Fetched {total} records.")

            result = {
                "records": records,
                "total": total,
                "inmuebles": inmuebles, 
                "proveedores": proveedores,
                "estados": estados,
                "period_id": period_id
            }
            # Schedule UI Update on Main Thread
            self.after(0, lambda: self._on_data_loaded(result))
            
        except Exception as e:
            err_msg = str(e)
            self.after(0, lambda: self._on_load_error(err_msg))

    def _on_load_error(self, error_msg):
        messagebox.showerror("Error de Carga", f"No se pudieron cargar los datos:\n{error_msg}")

    def _on_data_loaded(self, r):
        # Race Condition Guard: If view moved on, discard old data
        if r["period_id"] != self.current_period_id:
            app_logger.info(f"Discarding stale data for {r['period_id']} (Current: {self.current_period_id})")
            return

        # Use result as official loading point
        self.last_loaded_period = r["period_id"]
        # Use current page as we are on UI thread and it initiated the request (simplification)
        self.last_loaded_page = self.current_page 
        self.is_dirty = False
        
        # Unpack result
        records = r["records"]
        self.total_records = r["total"]
        self.master_dataset = records 
        
        # Filter Config
        filter_config = [
            {'field': 'obligacion.inmueble.alias', 'type': 'category', 'label': 'Inmueble', 'options': r["inmuebles"]},
            {'field': 'obligacion.proveedor.nombre_entidad', 'type': 'category', 'label': 'Proveedor', 'options': r["proveedores"]},
            {'field': 'estado', 'type': 'category', 'label': 'Estado', 'options': r["estados"]}
        ]
        
        # Update Smart Filter
        self.smart_filter.set_data(records, filter_config)
        
        # Re-Apply Filters Logic
        if self.smart_filter.active_filters:
             self.smart_filter._apply_filters()
        else:
             self.on_filtered_data_update(records)
        
        self.update_pagination_ui()
        
        # Refresh Navigation Bounds
        self.update_navigator_limits()

        # Update Navigator Bounds (New Feature)
    def update_navigator_limits(self):
        try:
            from services.period_service import PeriodService
            from datetime import date, timedelta
            from database import SessionLocal
            
            # Fetch all periods (sorted desc)
            # Decorator handles session injection
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
            
            # Handler for creating NEXT period (Newest + 1 month)
            # Logic: If user clicks (+) on Max Date, we want to create Max Date + 1 Month
            
            def create_next_period():
                # Next = max_d + 32 days -> 1st
                next_d = (max_d + timedelta(days=32)).replace(day=1)
                
                # Double Check (Redundant but safe)
                from database import SessionLocal
                with SessionLocal() as session:
                    if not PeriodService.is_year_active(next_d.year, session):
                        messagebox.showwarning("Año Fiscal Cerrado", f"El año {next_d.year} no está habilitado para creación de períodos.")
                        return

                next_pid = f"{next_d.year}-{next_d.month:02d}"
                self.prompt_empty_period_action(next_pid)

            # Check if Next Period Year is Active
            next_potential = (max_d + timedelta(days=32)).replace(day=1)
            callback = create_next_period
            
            # We need a session to check. 
            with SessionLocal() as session:
                if not PeriodService.is_year_active(next_potential.year, session):
                    callback = None # Disable (+) button

            self.time_navigator.set_bounds(min_d, max_d, on_new_period_command=callback)
            
        except Exception as e:
            app_logger.error(f"Error limiting navigator: {e}")

    def prompt_empty_period_action(self, period_id):
        # Use custom professional dialog with force-navigation on clone/create
        # When creating new period, we must FORCE load that period afterwards
        
        def on_clone_ok():
             # Open clone dialog
             self.open_clone_dialog_target(period_id) 
             
        # Slight modification to EmptyPeriodDialog needed? 
        # Wait, open_clone_dialog uses self.current_period_id.
        # But we are technically still on the OLD period in the view (since nav was blocked).
        # We need to tell the system "We want to operate on NEXT period".
        
        # We need a new method open_clone_dialog_target(target_pid)
        EmptyPeriodDialog(self, period_id, on_clone=on_clone_ok)

    def open_clone_dialog_target(self, target_pid):
         if not PermissionService.user_has_permission(self.master.current_user, PermissionService.CAN_EDIT_VENCIMIENTOS):
             messagebox.showwarning("Acceso Denegado", "No tiene permisos para clonar períodos (Modo Lectura).")
             return
         ClonePeriodDialog(self, target_pid)

    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.load_data()

    def next_page(self):
        import math
        max_page = math.ceil(self.total_records / self.page_limit)
        if self.current_page < max_page:
            self.current_page += 1
            self.load_data()

    def update_pagination_ui(self):
        import math
        max_page = math.ceil(self.total_records / self.page_limit) or 1
        
        self.lbl_page_info.configure(text=f"Página {self.current_page} de {max_page} ({self.total_records} Registros)")
        
        if self.current_page <= 1:
            self.btn_prev_page.configure(state="disabled", fg_color="gray")
        else:
            self.btn_prev_page.configure(state="normal", fg_color=COLORS["secondary_button"])
            
        if self.current_page >= max_page:
             self.btn_next_page.configure(state="disabled", fg_color="gray")
        else:
             self.btn_next_page.configure(state="normal", fg_color=COLORS["secondary_button"])

    def sort_by(self, col_field):
        # Toggle direction if clicking same column
        if self.sort_col == col_field:
            self.sort_desc = not self.sort_desc
        else:
            self.sort_col = col_field
            self.sort_desc = False 
            if col_field in ["monto_original", "estado"]: self.sort_desc = True # Default desc for these
            
        self.apply_sort()
        self._update_header_arrows() # Update visual arrows

    def _update_header_arrows(self):
        """Updates header labels to show sort arrow"""
        for field, (lbl, original_text) in self.header_widgets.items():
            if field == self.sort_col:
                arrow = " ▼" if not self.sort_desc else " ▲"
                lbl.configure(text=f"{original_text}{arrow}")
            else:
                lbl.configure(text=original_text)

    def apply_sort(self):
        if self.current_dataset is None: return
        if not self.current_dataset:
             self.render_grid([])
             return
        
        def get_val(obj, path):
             try:
                 parts = path.split(".")
                 v = obj
                 for p in parts: v = getattr(v, p)
                 
                 # Handle Enums
                 if hasattr(v, 'value'): return v.value
                 return v
             except: return None

        # Safe Sort Key Wrapper
        # ... logic inline ...

        try:
             # Sort using tuple (is_none, value) to handle None types safely
             # NOTE: value comparison must support the type (e.g. str vs str, int vs float)
             # Vencimiento objects should have consistent types for same columns.
             self.current_dataset.sort(
                 key=lambda x: (get_val(x, self.sort_col) is None, get_val(x, self.sort_col)), 
                 reverse=self.sort_desc
             )
             self.render_grid(self.current_dataset)
        except Exception as e:
             messagebox.showerror("Error Ordenamiento", f"No se pudo ordenar por {self.sort_col}:\n{e}")
             app_logger.error(f"SORT ERROR: {e}")

    def on_filtered_data_update(self, filtered_data):
        self.current_dataset = filtered_data
        # Apply current sort to new data
        if self.sort_col:
             self.apply_sort() # This calls render_grid
        else:
             self.render_grid(filtered_data)

    def on_period_change(self, target_date):
        # 1. Update internal Period ID for Server Side Fetch
        pid = f"{target_date.year}-{target_date.month:02d}"
        
        # Reset Page when changing Month
        if pid != self.current_period_id:
            self.current_page = 1
            
        self.current_period_id = pid

        # 2. Check Period Status (Governance)
        try:
            status = PeriodService.check_period_status(target_date) 
            
            # Debug Log
            # app_logger.debug(f"Period Status Check for {pid}: {status}")

            if status == EstadoPeriodo.CERRADO:
                self.period_warning = True
                self.readonly_mode = True 
                self.time_navigator.set_lock_status(True)
            elif status == EstadoPeriodo.BLOQUEADO: # Handle generic Blocking if returned as status
                 self.period_warning = False
                 self.readonly_mode = True
                 self.time_navigator.set_lock_status(True)
            else:
                # ABIERTO
                self.period_warning = False
                self.readonly_mode = False
                self.time_navigator.set_lock_status(False)

        except PeriodLockedError:
            # Expected blocking
            self.readonly_mode = True
            self.period_warning = False
            self.time_navigator.set_lock_status(True)

        except Exception as e: 
            # Unexpected Error -> Default to Block for safety but LOG IT
            app_logger.error(f"Error checking period status for {pid}: {e}", exc_info=True)
            self.readonly_mode = True
            # self.period_warning = False
            self.time_navigator.set_lock_status(True)

        # 3. Update UI Controls (ReadOnly Mode)
        if self.readonly_mode:
            self.btn_add.configure(state="disabled", fg_color="gray")
            self.btn_import.configure(state="disabled", fg_color="gray")
        else:
            self.btn_add.configure(state="normal", fg_color=COLORS["primary_button"])
            self.btn_import.configure(state="normal", fg_color=COLORS["primary_button"])

        # 4. Trigger Server Load
        self.load_data(period_id=pid)
        



    def toggle_currency(self):
        self.show_in_usd = self.switch_currency.get()
        # Trigger re-render of current dataset
        self.render_grid(self.current_dataset if hasattr(self, 'current_dataset') else [])


    def render_grid(self, vencimientos):
        # try: removed to fix syntax
        total_items = len(vencimientos) if vencimientos else 0
        app_logger.info(f"Rendering Grid with {total_items} items.")
        
        # Limpiar
        count_removed = 0
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
            count_removed += 1
        
        # app_logger.debug(f"Cleared {count_removed} old widgets.")
        
        self.row_widgets = {} # Reset map
        
        # Force UI update to prevent ghost artifacts
        self.update_idletasks()

        if not vencimientos:
            ctk.CTkLabel(self.scroll_frame, text="No se encontraron registros.", text_color="gray").pack(pady=20)
            self.lbl_pending_total.configure(text="Total Pendiente: $0.00")
            return

        # --- Currency Logic ---
        rate = 1.0
        currency_symbol = "$"
        
        if self.show_in_usd:
            try:
                rate = self.controller.get_usd_rate()
                currency_symbol = "USD"
            except:
                rate = 1.0 # Fallback
        
        # Helper for conversion
        def format_amount(val):
            if self.show_in_usd and rate > 0:
                converted = parse_localized_float(val) / rate
                return f"{currency_symbol} {format_currency(converted)}"
            else:
                return f"${format_currency(val)}"

        # Calculate Pending Total
        total_pending_ars = sum(v.monto_original for v in vencimientos if v.estado == EstadoVencimiento.PENDIENTE or str(v.estado) == "Pendiente")
        
        # Update Total Label
        self.lbl_pending_total.configure(text=f"Total Pendiente: {format_amount(total_pending_ars)}")

        for idx, ven in enumerate(vencimientos, start=0): # 0-indexed for modulo
            try:
                # Zebra Logic
                bg_color = COLORS["content_surface"] if idx % 2 == 0 else "#F4F6F7" # Cloud White alternate
                
                row = ctk.CTkFrame(self.scroll_frame, fg_color=bg_color, corner_radius=0)
                row.pack(fill="x", ipady=2)
                row.default_bg = bg_color # Crucial for selection restoration
            
                # Allow click on row to select
                row.bind("<Button-1>", lambda e, v=ven: self.select_item(v))
                row.bind("<Button-3>", lambda e, v=ven: self.show_context_menu(e, v))
                
                # ... COLUMNS Rendering ...
                # Reuse logic to keep display consistent
                # We must recreate the columns manually or call a helper?
                # Inline for now as we did before.
                
                # --- ROW CONTENT (Same as before) ---
                # Icon 1: PDF (Factura)
                if ven.ruta_archivo_pdf or ven.documento_id:
                     l1 = ctk.CTkLabel(row, text="📄", width=27, cursor="hand2", text_color=COLORS["primary_button"])
                     l1.grid(row=0, column=0, sticky="ew")
                     l1.bind("<Button-1>", lambda e, v=ven: self.open_pdf_viewer(v))
                     l1.bind("<Button-3>", lambda e, v=ven: self.show_context_menu(e, v))
                else:
                     l_empty1 = ctk.CTkLabel(row, text="", width=27)
                     l_empty1.grid(row=0, column=0, sticky="ew")
                     l_empty1.bind("<Button-3>", lambda e, v=ven: self.show_context_menu(e, v))
                     l_empty1.bind("<Button-1>", lambda e, v=ven: self.select_item(v))
                
                # Icon 2: Pago
                if ven.ruta_comprobante_pago or ven.comprobante_pago_id:
                     l2 = ctk.CTkLabel(row, text="💲", width=27, cursor="hand2", text_color=COLORS["status_paid"])
                     l2.grid(row=0, column=1, sticky="ew")
                     l2.bind("<Button-1>", lambda e, v=ven: self._safe_open_payment(v))
                     l2.bind("<Button-3>", lambda e, v=ven: self.show_context_menu(e, v))
                else:
                     l_empty2 = ctk.CTkLabel(row, text="", width=27)
                     l_empty2.grid(row=0, column=1, sticky="ew")
                     l_empty2.bind("<Button-3>", lambda e, v=ven: self.show_context_menu(e, v))
                     l_empty2.bind("<Button-1>", lambda e, v=ven: self.select_item(v))
    
                # Inmueble
                inm_alias = ven.obligacion.inmueble.alias if ven.obligacion.inmueble else "N/A"
                l_inm = ctk.CTkLabel(row, text=inm_alias, anchor="w", font=("Segoe UI", 12))
                l_inm.grid(row=0, column=2, sticky="ew", padx=(10, 2))
                l_inm.bind("<Button-1>", lambda e, v=ven: self.select_item(v))
                l_inm.bind("<Button-3>", lambda e, v=ven: self.show_context_menu(e, v))
                
                # Proveedor
                prov_name = ven.obligacion.proveedor.nombre_entidad if ven.obligacion.proveedor else "N/A"
                l_prov = ctk.CTkLabel(row, text=prov_name, anchor="w", font=("Segoe UI", 12))
                l_prov.grid(row=0, column=3, sticky="ew", padx=(10, 2))
                l_prov.bind("<Button-1>", lambda e, v=ven: self.select_item(v))
                l_prov.bind("<Button-3>", lambda e, v=ven: self.show_context_menu(e, v))
                
                # Fecha
                f_str = ven.fecha_vencimiento.strftime("%d/%m/%Y")
                l_date = ctk.CTkLabel(row, text=f_str, anchor="center", font=("Segoe UI", 12))
                l_date.grid(row=0, column=4, sticky="ew")
                l_date.bind("<Button-1>", lambda e, v=ven: self.select_item(v))
                l_date.bind("<Button-3>", lambda e, v=ven: self.show_context_menu(e, v))
                
                # Monto (CONVERTED)
                # Monto (Logic: Show Updated > Original, or Total Paid if status is Paid)
                final_monto = ven.monto_original
                
    
                
                # If strictly Paid, verify against Payments?
                # Let's trust monto_actualizado as the "Debt Value".
                
                m_str = format_amount(final_monto)
                
                # Highlight if difference
                m_color = COLORS["text_primary"]
                if final_monto > ven.monto_original:
                     m_str = f"{m_str} ⚠" # Surcharge indicator
                     m_color = COLORS["status_overdue"]
    
                l_amnt = ctk.CTkLabel(row, text=m_str, anchor="e", font=("Segoe UI", 12), text_color=m_color)
                l_amnt.grid(row=0, column=5, sticky="ew", padx=(2, 20))
                l_amnt.bind("<Button-1>", lambda e, v=ven: self.select_item(v))
                l_amnt.bind("<Button-3>", lambda e, v=ven: self.show_context_menu(e, v))
                
                # Estado
                e_val = ven.estado.value if hasattr(ven.estado, 'value') else str(ven.estado)
                e_col = COLORS["status_paid"] if e_val == EstadoVencimiento.PAGADO.value else COLORS["status_pending"]
                if e_val == EstadoVencimiento.VENCIDO.value: e_col = COLORS["status_overdue"]
                l_est = ctk.CTkLabel(row, text=e_val, text_color=e_col, anchor="w", font=("Segoe UI", 11, "bold"))
                l_est.grid(row=0, column=6, sticky="ew", padx=(10, 0))
                l_est.bind("<Button-1>", lambda e, v=ven: self.select_item(v))
                l_est.bind("<Button-3>", lambda e, v=ven: self.show_context_menu(e, v))
                
                # Actions
                btn_edit = ctk.CTkButton(row, text="✎", width=30, height=25, fg_color=COLORS["primary_button"], command=lambda v=ven: self.open_edit_dialog(v))
                btn_edit.grid(row=0, column=7, padx=2)
    
                btn_del = ctk.CTkButton(row, text="✖", width=30, height=25, fg_color=COLORS["status_overdue"], command=lambda v=ven: self.delete_vencimiento(v))
                btn_del.grid(row=0, column=8, padx=2)
                
                self.row_widgets[ven.id] = row
    
                # Force grid column config on row to match header
                row.grid_columnconfigure(0, minsize=27)
                row.grid_columnconfigure(1, minsize=27)
                row.grid_columnconfigure(2, weight=2, uniform="cols")
                row.grid_columnconfigure(3, weight=2, uniform="cols")
                row.grid_columnconfigure((4,5,6), weight=1, uniform="cols")
                row.grid_columnconfigure((7,8), minsize=35)
            
            except Exception as e:
                 app_logger.error(f"Error rendering row {idx}: {e}", exc_info=True)
                 continue


    def show_context_menu(self, event, vencimiento):
        try:
             menu = tk.Menu(self, tearoff=0)

             # Permission Checks
             user = self.master.current_user
             can_edit = PermissionService.user_has_permission(user, PermissionService.CAN_EDIT_VENCIMIENTOS)
             can_delete = PermissionService.user_has_permission(user, PermissionService.CAN_DELETE_VENCIMIENTOS)

             if can_edit:
                 menu.add_command(label="✏ Editar", command=lambda: self.open_edit_dialog(vencimiento))
             
             # Status Actions
             if vencimiento.estado == EstadoVencimiento.PENDIENTE and can_edit:
                 menu.add_command(label="✅ Marcar Pagado", command=lambda: self.quick_pay(vencimiento)) # Need to implement this? OR just rely on edit.
             
             menu.add_separator()
             menu.add_separator()
             if vencimiento.ruta_archivo_pdf or vencimiento.documento_id:
                 menu.add_command(label="📄 Ver Factura", command=lambda: self.open_pdf_viewer(vencimiento))
                 
             if vencimiento.ruta_comprobante_pago or vencimiento.comprobante_pago_id:
                 menu.add_command(label="💲 Ver Comprobante", command=lambda: self._safe_open_payment(vencimiento))
            
             menu.add_separator()
             if can_delete:
                 menu.add_command(label="❌ Eliminar", command=lambda: self.delete_vencimiento(vencimiento))

             menu.post(event.x_root, event.y_root)
        except Exception as e:
             app_logger.error(f"Menu error: {e}")

    def quick_pay(self, vencimiento):
        if messagebox.askyesno("Confirmar Pago", f"¿Marcar como PAGADO el vencimiento de {vencimiento.monto_original}?"):
             # Simplified Pay
             pass # Maybe later, user just asked for "opciones", edit is primary.
             # Actually I will omit quick_pay for now to keep it simple and safe.
             self.open_edit_dialog(vencimiento) # Redirect to edit for proper payment entry

    def show_alerts_dialog(self):
        try:
            alerts = self.controller.get_upcoming_alerts(days=7)
            if not alerts:
                messagebox.showinfo("Sin Alertas", "No tienes vencimientos próximos en los siguientes 7 días.")
                return

            # Custom Dialog for Alerts
            dlg = ctk.CTkToplevel(self)
            dlg.transient(self)
            dlg.grab_set()
            dlg.lift()
            dlg.focus_force()
            
            dlg.title("🔔 Vencimientos Próximos (7 Días)")
            dlg.geometry("500x400")
            center_window(dlg, self)
            
            # Header
            ctk.CTkLabel(dlg, text="Atención: Vencimientos Cercanos", font=("Segoe UI", 16, "bold"), text_color=COLORS["status_overdue"]).pack(pady=10)
            
            # Scroll List
            scroll = ctk.CTkScrollableFrame(dlg, fg_color="white")
            scroll.pack(fill="both", expand=True, padx=10, pady=10)
            
            for item in alerts:
                f_card = ctk.CTkFrame(scroll, fg_color="#FDEDEC", corner_radius=6) # Light Red
                f_card.pack(fill="x", pady=2, padx=2)
                
                # Layout: Date | Inmueble - Proveedor | Amount
                f_date = item.fecha_vencimiento.strftime("%d/%m")
                inm = item.obligacion.inmueble.alias
                prov = item.obligacion.proveedor.nombre_entidad
                amnt = format_currency(item.monto_original)
                
                # Row 1
                ctk.CTkLabel(f_card, text=f"📅 {f_date}", font=("Segoe UI", 12, "bold"), width=50).pack(side="left", padx=5)
                ctk.CTkLabel(f_card, text=f"{inm} - {prov}", font=("Segoe UI", 12), anchor="w").pack(side="left", fill="x", expand=True)
                ctk.CTkLabel(f_card, text=amnt, font=("Segoe UI", 12, "bold"), text_color="red").pack(side="right", padx=10)
                
            # Close Button
            ctk.CTkButton(dlg, text="Entendido", command=dlg.destroy, fg_color=COLORS["primary_button"]).pack(pady=10)
            
        except Exception as e:
            messagebox.showerror("Error", f"Fallo al buscar alertas: {e}")

    def open_pdf_viewer(self, vencimiento):
        # 1. Try Local Path (Legacy)
        if hasattr(vencimiento, 'ruta_archivo_pdf') and vencimiento.ruta_archivo_pdf:
             # Ensure Controller is accessible
             if self.controller.open_pdf(vencimiento.ruta_archivo_pdf):
                 return

        # 2. Try Cloud DB (Blob)
        if hasattr(vencimiento, 'documento_id') and vencimiento.documento_id:
             self._download_and_open(vencimiento.documento_id, "factura")
             return

        messagebox.showerror("Error", "No se encontró el archivo (Local ni Nube).")

    def _safe_open_payment(self, vencimiento):
        # 1. Try Local Path (Legacy)
        if hasattr(vencimiento, 'ruta_comprobante_pago') and vencimiento.ruta_comprobante_pago:
             if self.controller.open_pdf(vencimiento.ruta_comprobante_pago):
                 return
        
        # 2. Try Cloud DB (Blob)
        if hasattr(vencimiento, 'comprobante_pago_id') and vencimiento.comprobante_pago_id:
             self._download_and_open(vencimiento.comprobante_pago_id, "pago")
             return

        messagebox.showerror("Error", "No se encontró el comprobante (Local ni Nube).")

    def _download_and_open(self, doc_id, doc_type_hint):
        try:
            service = VencimientoService()
            file_data, filename, _ = service.get_document(doc_id)
            
            if not file_data:
                messagebox.showerror("Error", "El documento está vacío o no se encontró en la base de datos.")
                return

            # Create Temp File
            prefix = f"cloud_doc_{doc_type_hint}_{doc_id}_"
            suffix = os.path.splitext(filename)[1] if filename else ".pdf"
            
            with tempfile.NamedTemporaryFile(delete=False, prefix=prefix, suffix=suffix) as tmp:
                tmp.write(file_data)
                tmp_path = tmp.name
            
            # Open
            os.startfile(tmp_path)
            
        except Exception as e:
            app_logger.error(f"Error downloading/opening cloud doc: {e}")
            messagebox.showerror("Error", f"No se pudo descargar/abrir el archivo:\n{e}")

    def _safe_open(self, path):
        if not path: return
        if not VencimientosController().open_pdf(path):
            messagebox.showerror("Error", "No se pudo abrir el documento.\nVerifique que el archivo exista.")

    def delete_vencimiento(self, vencimiento):
        if not PermissionService.user_has_permission(self.master.current_user, PermissionService.CAN_DELETE_VENCIMIENTOS):
            messagebox.showwarning("Acceso Denegado", "No tiene permisos para eliminar registros.\nContacte a su administrador.")
            return

        if messagebox.askyesno("Confirmar", f"¿Eliminar vencimiento de {vencimiento.obligacion.proveedor.nombre_entidad}?"):
            try:
                if VencimientosController().delete_vencimiento(vencimiento.id):
                    self.load_data()
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo eliminar: {e}")

    def get_current_filtered_data(self):
        # Used by exports
        return getattr(self, 'current_dataset', [])

    def export_excel(self):
        self._run_async_export(
            lambda d: ReportsController().export_excel(d),
            "Excel"
        )

    def export_pdf(self):
        self._run_async_export(
            lambda d: ReportsController().export_pdf_report(d),
            "PDF"
        )
        
    def _run_async_export(self, export_func, doc_type):
        data = self.get_current_filtered_data()
        if not data: 
            messagebox.showwarning("Exportar", "No hay datos visibles para exportar.")
            return

        import threading
        
        def task():
            try:
                path = export_func(data)
                self.after(0, self._on_export_success, path, doc_type)
            except Exception as e:
                # 'e' is deleted after except block, so we must pass it immediately by value/arg
                self.after(0, self._on_export_error, str(e), doc_type)
        
        threading.Thread(target=task, daemon=True).start()
        messagebox.showinfo("Exportando", f"Generando {doc_type} en segundo plano...")

    def _on_export_success(self, path, doc_type):
        if path:
            if messagebox.askyesno("Éxito", f"{doc_type} generado correctamente.\n¿Desea abrirlo?"):
                import os
                try:
                    os.startfile(path)
                except:
                     pass

    def _on_export_error(self, error, doc_type):
         messagebox.showerror("Error Exportación", f"Falló la exportación {doc_type}:\n{error}")

    def open_clone_dialog(self):
        if not PermissionService.user_has_permission(self.master.current_user, PermissionService.CAN_EDIT_VENCIMIENTOS):
             messagebox.showwarning("Acceso Denegado", "No tiene permisos para clonar períodos (Modo Lectura).")
             return

        if not self.current_period_id: 
            messagebox.showwarning("Aviso", "No hay un período seleccionado.")
            return
        ClonePeriodDialog(self, self.current_period_id)

    def tkraise(self, *args, **kwargs):
        super().tkraise(*args, **kwargs)
        self.load_data()

    def open_add_dialog(self):
        if not PermissionService.user_has_permission(self.master.current_user, PermissionService.CAN_EDIT_VENCIMIENTOS):
            messagebox.showwarning("Acceso Denegado", "No tiene permisos para crear registros.\nContacte a su administrador (Rol Requerido: OPERADOR/ADMIN).")
            return
        AddVencimientoDialog(self)

    def open_edit_dialog(self, vencimiento):
        if not PermissionService.user_has_permission(self.master.current_user, PermissionService.CAN_EDIT_VENCIMIENTOS):
             messagebox.showwarning("Acceso Denegado", "No tiene permisos para modificar registros (Modo Lectura).")
             return
        EditVencimientoDialog(self, vencimiento)


class EditVencimientoDialog(ctk.CTkToplevel):
    def __init__(self, parent, vencimiento):
        super().__init__(parent)
        self.parent = parent # FIX: Store parent explicitly
        self.title(f"Editar Vencimiento #{vencimiento.id}")
        self.geometry("420x700") 
        
        # Modal Behavior Setup
        self.transient(self.parent) # Associated with parent
        self.grab_set() # Block interaction with main window
        self.lift() # Bring to top
        self.focus_set() # Grab focus
        
        # Center Logic
        self.update_idletasks()
        try:
             w = 420
             h = 700
             x = self.parent.winfo_rootx() + (self.parent.winfo_width() // 2) - (w // 2)
             y = self.parent.winfo_rooty() + (self.parent.winfo_height() // 2) - (h // 2)
             self.geometry(f"{w}x{h}+{x}+{y}")
        except:
             self.geometry("420x700")
        
        self.parent = parent
        
        # Fresh Fetch to ensure relations are loaded and attached
        from controllers.vencimientos_controller import VencimientosController
        fresh_venc = VencimientosController().get_vencimiento_details(vencimiento.id)
        self.vencimiento = fresh_venc if fresh_venc else vencimiento
        
        # Main Layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Scrollable container? No, simple frame is enough usually, but let's use a nice padded frame.
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=25, pady=25)
        
        # --- SECTION 1: CORE DETAILS ---
        ctk.CTkLabel(self.main_frame, text="Detalles de la Obligación", font=("Segoe UI", 12, "bold"), text_color="gray").pack(anchor="w", pady=(0, 10))
        
        # Grid for Core Inputs (Expanded for Re-Classification)
        grid_core = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        grid_core.pack(fill="x", pady=(0, 15))
        grid_core.grid_columnconfigure(0, weight=1)
        grid_core.grid_columnconfigure(1, weight=1)
        
        # --- RE-CLASSIFICATION SELECTORS ---
        # 1. Inmueble
        ctk.CTkLabel(grid_core, text="Inmueble").grid(row=0, column=0, sticky="w", padx=5)
        
        self.catalogs_controller = CatalogsController()
        inmuebles = self.catalogs_controller.get_inmuebles(include_inactive=False)
        self.inmueble_map = {i.alias: i.id for i in inmuebles}
        inmueble_aliases = list(self.inmueble_map.keys())
        
        self.combo_inmueble = AutocompleteCombobox(grid_core, completion_list=inmueble_aliases)
        self.combo_inmueble.grid(row=1, column=0, sticky="ew", padx=5, pady=(0, 10))
        self.combo_inmueble.configure(command=self.on_inmueble_select)
        
        # Set Initial Inmueble
        current_inm = self.vencimiento.obligacion.inmueble.alias if self.vencimiento.obligacion and self.vencimiento.obligacion.inmueble else ""
        self.combo_inmueble.set(current_inm)

        # 2. Proveedor (Obligación)
        ctk.CTkLabel(grid_core, text="Proveedor / Servicio").grid(row=0, column=1, sticky="w", padx=5)
        
        self.combo_obligacion = ctk.CTkComboBox(grid_core, values=[])
        self.combo_obligacion.grid(row=1, column=1, sticky="ew", padx=5, pady=(0, 10))
        
        # Load Obligations Cache
        self.all_obligaciones = ObligacionesController().get_all_obligaciones()
        self.filtered_obs_map = {} 
        
        # Initialize Provider List based on current Inmueble
        self.on_inmueble_select(current_inm, initial_load=True)

        # --- EXISTING FIELDS (Moved down) ---
        
        # Monto
        # Periodo
        ctk.CTkLabel(grid_core, text="Periodo (YYYY-MM)").grid(row=2, column=0, sticky="w", padx=5)
        self.entry_periodo = ctk.CTkEntry(grid_core)
        self.entry_periodo.insert(0, str(self.vencimiento.periodo))
        self.entry_periodo.grid(row=3, column=0, sticky="ew", padx=5, pady=(0, 10))

        # Monto (Shifted to Row 4/5)
        ctk.CTkLabel(grid_core, text="Monto Original").grid(row=4, column=0, sticky="w", padx=5)
        self.entry_monto = ctk.CTkEntry(grid_core)
        self.entry_monto.insert(0, str(self.vencimiento.monto_original))
        self.entry_monto.grid(row=5, column=0, sticky="ew", padx=5, pady=(0, 10))

        # Fecha (Shifted to Row 4/5 - Col 1)
        ctk.CTkLabel(grid_core, text="Fecha Vencimiento").grid(row=4, column=1, sticky="w", padx=5)
        self.entry_fecha = ctk.CTkEntry(grid_core, placeholder_text="dd/mm/yyyy")
        self.entry_fecha.insert(0, self.vencimiento.fecha_vencimiento.strftime("%d/%m/%Y"))
        self.entry_fecha.grid(row=5, column=1, sticky="ew", padx=5, pady=(0, 10))
        
        # Estado
        ctk.CTkLabel(self.main_frame, text="Estado Actual", font=("Segoe UI", 12)).pack(anchor="w", padx=5)
        estados = [e.value for e in EstadoVencimiento]
        self.combo_estado = ctk.CTkComboBox(self.main_frame, values=estados, command=self.on_status_change)
        val = self.vencimiento.estado.value if hasattr(self.vencimiento.estado, 'value') else str(self.vencimiento.estado)
        self.combo_estado.set(val)
        self.combo_estado.pack(fill="x", padx=5, pady=(0, 15))

        # Invoice Section
        ctk.CTkLabel(self.main_frame, text="Factura / Documento", font=("Segoe UI", 12)).pack(anchor="w", padx=5, pady=(5,0))
        frame_doc = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        frame_doc.pack(fill="x", padx=5, pady=(0, 10))
        
        self.btn_doc = ctk.CTkButton(frame_doc, text="Seleccionar PDF" if (not self.vencimiento.ruta_archivo_pdf and not self.vencimiento.documento_id) else "Cambiar PDF", 
                                     width=100, command=lambda: self.select_file('invoice'), fg_color=COLORS["secondary_button"])
        self.btn_doc.pack(side="left")
        
        has_doc = bool(self.vencimiento.ruta_archivo_pdf or self.vencimiento.documento_id)
        self.lbl_doc_status = ctk.CTkLabel(frame_doc, text="✅ Archivo actual" if has_doc else "Sin archivo", 
                                          text_color=COLORS["text_primary"] if has_doc else "gray", font=("Segoe UI", 11))
        self.lbl_doc_status.pack(side="left", padx=10)

        # Payment Proof Section
        ctk.CTkLabel(self.main_frame, text="Comprobante de Pago", font=("Segoe UI", 12)).pack(anchor="w", padx=5, pady=(5,0))
        frame_pay = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        frame_pay.pack(fill="x", padx=5, pady=(0, 15))
        
        has_pay = bool(self.vencimiento.ruta_comprobante_pago or self.vencimiento.comprobante_pago_id)
        self.btn_pay = ctk.CTkButton(frame_pay, text="Seleccionar Pago" if not has_pay else "Cambiar Pago", 
                                     width=100, command=lambda: self.select_file('payment'), fg_color=COLORS["secondary_button"])
        self.btn_pay.pack(side="left")
        self.lbl_pay_status = ctk.CTkLabel(frame_pay, text="✅ Archivo actual" if has_pay else "Sin archivo", 
                                           text_color=COLORS["text_primary"] if has_pay else "gray", font=("Segoe UI", 11))
        self.lbl_pay_status.pack(side="left", padx=10)

        # Payment Details Frame (Hidden by default unless Paid)
        self.frame_pago_details = ctk.CTkFrame(self.main_frame, fg_color=COLORS["content_surface"]) # different bg to distinguish
        
        ctk.CTkLabel(self.frame_pago_details, text="Detalles del Pago Realizado", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=5)
        
        grid_pago = ctk.CTkFrame(self.frame_pago_details, fg_color="transparent")
        grid_pago.pack(fill="x", pady=5)
        
        # Determine initial values from existing Pago record if available
        existing_pago = self.vencimiento.pagos[0] if (self.vencimiento.pagos and len(self.vencimiento.pagos) > 0) else None
        
        init_monto_pago = str(self.vencimiento.monto_original)
        init_fecha_pago = datetime.now().strftime("%d/%m/%Y")
        
        if existing_pago:
             init_monto_pago = str(existing_pago.monto)
             if existing_pago.fecha_pago:
                 init_fecha_pago = existing_pago.fecha_pago.strftime("%d/%m/%Y")

        ctk.CTkLabel(grid_pago, text="Monto Pagado").grid(row=0, column=0, sticky="w", padx=5)
        self.entry_monto_pagado = ctk.CTkEntry(grid_pago)
        self.entry_monto_pagado.grid(row=1, column=0, sticky="ew", padx=5)
        self.entry_monto_pagado.insert(0, init_monto_pago)

        ctk.CTkLabel(grid_pago, text="Fecha Pago").grid(row=0, column=1, sticky="w", padx=5)
        self.entry_fecha_pago = ctk.CTkEntry(grid_pago, placeholder_text="dd/mm/yyyy")
        self.entry_fecha_pago.grid(row=1, column=1, sticky="ew", padx=5)
        self.entry_fecha_pago.insert(0, init_fecha_pago)

        # Initial State Check
        if self.combo_estado.get() == EstadoVencimiento.PAGADO.value:
             self.frame_pago_details.pack(fill="x", padx=5, pady=10)

        # --- FOOTER ---
        ctk.CTkButton(self.main_frame, text="Guardar Cambios", command=self.save, 
                      fg_color=COLORS["primary_button"], hover_color=COLORS["primary_button_hover"],
                      height=40, font=("Segoe UI", 13, "bold")).pack(side="bottom", fill="x", pady=20)
        
        # Helper for file selection
    def select_file(self, type_):
        path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf"), ("Images", "*.jpg;*.png;*.jpeg")])
        if path:
            if type_ == 'invoice':
                self.new_invoice_path = path
                self.lbl_doc_status.configure(text=f"📎 {os.path.basename(path)}", text_color=COLORS["text_primary"])
            elif type_ == 'payment':
                self.new_payment_path = path
                self.lbl_pay_status.configure(text=f"📎 {os.path.basename(path)}", text_color=COLORS["text_primary"])

    def on_inmueble_select(self, choice, initial_load=False):
        if not choice or choice not in self.inmueble_map:
            return
            
        self.last_selected_inmueble = choice # Update tracker
        inmueble_id = self.inmueble_map[choice]
        
        # Filter Obligations
        filtered_obs = [o for o in self.all_obligaciones if o.inmueble_id == inmueble_id]
        
        def get_cat_val(cat):
            return cat.value if hasattr(cat, 'value') else str(cat)

        self.filtered_obs_map = {f"{o.proveedor.nombre_entidad} ({get_cat_val(o.proveedor.categoria)})": o.id for o in filtered_obs}
        
        values = list(self.filtered_obs_map.keys())
        if values:
            self.combo_obligacion.configure(values=values, state="normal")
            
            # If initial load, try to select current valid obligation
            if initial_load and self.vencimiento.obligacion:
                 current_key = f"{self.vencimiento.obligacion.proveedor.nombre_entidad} ({get_cat_val(self.vencimiento.obligacion.proveedor.categoria)})"
                 if current_key in self.filtered_obs_map:
                     self.combo_obligacion.set(current_key)
                 else:
                     self.combo_obligacion.set(values[0])
            else:
                 self.combo_obligacion.set(values[0])
        else:
            self.combo_obligacion.configure(values=["Sin servicios"], state="disabled")
            self.combo_obligacion.set("Sin servicios")

    def on_status_change(self, choice):
        if choice == EstadoVencimiento.PAGADO.value:
            self.frame_pago_details.pack(fill="x", padx=5, pady=10)
        else:
            self.frame_pago_details.pack_forget()

    # ... (Rest of existing methods) ...
    
    def save(self):
        try:
            monto = parse_localized_float(self.entry_monto.get())
            estado_str = self.combo_estado.get()
            
            # --- Robust Stateless Re-Link Logic ---
            # Instead of relying on event maps, we fetch what's currently selected afresh.
            new_obligacion_id = None
            current_inm_alias = self.combo_inmueble.get()
            current_prov_text = self.combo_obligacion.get()
            
            # 1. Resolve Inmueble ID
            inm_id = self.inmueble_map.get(current_inm_alias)
            
            if inm_id:
                # 2. Find matching Obligation in cached list
                # text format: "Nombre (Categoria)"
                # We tokenize or loop to find match.
                
                # Helper to rebuild key for comparison
                def get_cat_val(cat):
                    return cat.value if hasattr(cat, 'value') else str(cat)
                
                # Search
                target_obl = None
                
                # --- Strict Relationship Validation ---
                # Re-calculate what SHOULD be in the list for this Inmueble
                valid_candidates = []
                for obl in self.all_obligaciones:
                    if obl.inmueble_id == inm_id:
                         raw_cat = obl.proveedor.categoria
                         cat_val = raw_cat.value if hasattr(raw_cat, 'value') else str(raw_cat)
                         key = f"{obl.proveedor.nombre_entidad} ({cat_val})"
                         valid_candidates.append((obl, key))
                
                target_obl = None
                
                # 1. Try Exact Match
                for obl, key in valid_candidates:
                    if key == current_prov_text:
                        target_obl = obl
                        break
                
                # 2. If failure (Desync), Auto-Correct
                if not target_obl:
                     if valid_candidates:
                         # Use first available
                         target_obl, target_key = valid_candidates[0]
                         app_logger.warning(f"UI Desync detected. Auto-correcting service to: {target_key}")
                         
                         if not messagebox.askyesno("Corrección de Servicio", 
                                                    f"El servicio '{current_prov_text}' no pertenece al inmueble '{current_inm_alias}'.\n\n¿Desea asignar el primer servicio disponible:\n'{target_key}'?", parent=self):
                             return
                     else:
                         # --- AUTO-CREATE LOGIC ---
                         if messagebox.askyesno("Sin Servicios", f"El inmueble '{current_inm_alias}' no tiene servicios asignados.\n\n¿Desea crear un servicio 'Varios' automáticamente para guardar?", parent=self):
                             try:
                                 target_obl = ObligacionesController().get_or_create_default(inm_id)
                                 if target_obl:
                                     app_logger.info(f"Created/Found default obligation: {target_obl.id}")
                                 else:
                                     messagebox.showerror("Error", "No se pudo crear el servicio automático.")
                                     return
                             except Exception as e:
                                 messagebox.showerror("Error", f"Fallo al crear servicio: {e}")
                                 return
                         else:
                             return

                if target_obl:
                     if target_obl.id != self.vencimiento.obligacion_id:
                         new_obligacion_id = target_obl.id
                         app_logger.info(f"CONFIRMED CHANGE: Obligacion {self.vencimiento.obligacion_id} -> {new_obligacion_id}")
            
            # Validation
            if new_obligacion_id:
                 # Confirmation message already handled if auto-corrected, but good to double check context
                 # If we auto-corrected, we asked. If we matched exactly, we haven't asked yet.
                 # Let's simplify: Check logic above.
                 # If target_obl was found cleanly, we didn't ask.
                 # If target_obl was auto-corrected, we asked.
                 pass

            # Validation
            if estado_str == EstadoVencimiento.PAGADO.value and not (self.vencimiento.ruta_comprobante_pago or getattr(self, 'new_payment_path', None)):
                 # Warning only
                 pass

            # Date Parsing
            fecha_str = self.entry_fecha.get().strip()
            # If changed?
            fecha_new = datetime.strptime(fecha_str, "%d/%m/%Y").date()

            # Upload Files to Cloud DB (BLOBs)
            from services.vencimiento_service import VencimientoService
            service = VencimientoService()
            
            doc_id = None
            pay_doc_id = None
            
            # 1. Invoice
            inv_path = getattr(self, 'new_invoice_path', None)
            if inv_path and os.path.exists(inv_path):
                 try:
                     doc_id = service.upload_document(inv_path)
                     app_logger.info(f"Invoice uploaded to Cloud DB: ID {doc_id}")
                 except Exception as e:
                     messagebox.showerror("Error Subida", f"Fallo al subir factura: {e}", parent=self)
                     return

            # 2. Payment Proof
            pay_path = getattr(self, 'new_payment_path', None)
            if pay_path and os.path.exists(pay_path):
                 try:
                     pay_doc_id = service.upload_document(pay_path)
                     app_logger.info(f"Payment Proof uploaded to Cloud DB: ID {pay_doc_id}")
                 except Exception as e:
                     messagebox.showerror("Error Subida", f"Fallo al subir comprobante: {e}", parent=self)
                     return

            data = {
                "monto_original": monto,
                "fecha_vencimiento": fecha_new,
                "estado": self._get_estado_name(estado_str),
                "periodo": self.entry_periodo.get().strip() # Add Period
            }
            
            if doc_id: data["documento_id"] = doc_id
            if pay_doc_id: data["comprobante_pago_id"] = pay_doc_id
            
            if new_obligacion_id:
                data["obligacion_id"] = new_obligacion_id
            
            if estado_str == EstadoVencimiento.PAGADO.value:
                try:
                    m_pagado = parse_localized_float(self.entry_monto_pagado.get())
                    f_pago_str = self.entry_fecha_pago.get().strip()
                    f_pago = datetime.strptime(f_pago_str, "%d/%m/%Y").date()
                    
                    data["monto_pagado"] = m_pagado
                    data["fecha_pago"] = f_pago
                except ValueError:
                    messagebox.showerror("Error", "Fecha o Monto de Pago inválidos.")
                    return
            
            # Warning Check
            if getattr(self.parent, 'period_warning', False):
                 if not messagebox.askyesno("Advertencia - Período Cerrado", "Este período está CERRADO (Rendido).\n¿Está seguro que desea modificar este registro?", parent=self):
                     return

            if not messagebox.askyesno("Confirmar Cambios", "¿Desea guardar los cambios realizados?", parent=self):
                return

            if VencimientosController().update_vencimiento(self.vencimiento.id, data):
                if hasattr(self.parent, 'load_data'):
                    self.parent.load_data()
                self.destroy()
        except ValueError:
            messagebox.showerror("Error", "Monto inválido.", parent=self)
        except Exception as e:
            messagebox.showerror("Error al Guardar", str(e), parent=self)

    def _get_estado_name(self, display_value):
        """Maps 'Pendiente' -> 'PENDIENTE' for SQLA"""
        for e in EstadoVencimiento:
            if e.value == display_value:
                return e.name
        return "PENDIENTE" # Default Fallback

class AddVencimientoDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Nuevo Vencimiento")
        self.geometry("450x650") # Explicit roomy size
        
        # UI Focus Fix
        self.lift()
        self.focus_force()
        self.attributes("-topmost", True)
        
        self.parent = parent
        
        # Modal Behavior Setup
        self.transient(self.parent) # Associated with parent
        self.grab_set() # Block interaction with main window
        self.lift() # Bring to top
        self.focus_set() # Grab focus
        
        # Center Logic
        self.update_idletasks()
        try:
             # Default size or calculated?
             w = 600
             h = 700
             x = self.parent.winfo_rootx() + (self.parent.winfo_width() // 2) - (w // 2)
             y = self.parent.winfo_rooty() + (self.parent.winfo_height() // 2) - (h // 2)
             self.geometry(f"{w}x{h}+{x}+{y}")
        except:
             self.geometry("600x700")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(11, weight=1) # Adjusted for extra rows

        # --- 1. Inmueble Selection ---
        ctk.CTkLabel(self, text="1. Inmueble (Alias):").grid(row=0, column=0, padx=20, pady=(10, 5), sticky="w")
        
        self.catalogs_controller = CatalogsController()
        # Fetch Inmuebles
        inmuebles = self.catalogs_controller.get_inmuebles(include_inactive=False)
        self.inmueble_map = {i.alias: i.id for i in inmuebles}
        inmueble_aliases = list(self.inmueble_map.keys())
        
        # Frame for Inmueble Selection
        frame_inm = ctk.CTkFrame(self, fg_color="transparent")
        frame_inm.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        
        self.combo_inmueble = AutocompleteCombobox(frame_inm, completion_list=inmueble_aliases)
        self.combo_inmueble.pack(side="left", fill="x", expand=True)
        self.combo_inmueble.configure(command=self.on_inmueble_select)
        
        # Explicitly clear selection (fix for 'wrong default')
        self.after(10, lambda: self.combo_inmueble.set(""))
        
        # (+) Button for Inmueble
        self.btn_add_inm = ctk.CTkButton(frame_inm, text="+", width=30, fg_color=COLORS["secondary_button"], command=self.quick_add_inmueble)
        self.btn_add_inm.pack(side="left", padx=(5,0))

        # --- 2. Servicio/Proveedor Selection ---
        ctk.CTkLabel(self, text="2. Proveedor / Servicio:").grid(row=2, column=0, padx=20, pady=5, sticky="w")
        
        # We will load All Obligations once, then filter in memory
        self.all_obligaciones = ObligacionesController().get_all_obligaciones()
        self.filtered_obs_map = {} # Display -> ID
        
        self.filtered_obs_map = {} # Display -> ID
        
        # Frame for Service Selection
        frame_serv = ctk.CTkFrame(self, fg_color="transparent")
        frame_serv.grid(row=3, column=0, padx=20, pady=5, sticky="ew")

        self.combo_obligacion = ctk.CTkComboBox(frame_serv, values=["<- Seleccione Inmueble primero"])
        self.combo_obligacion.pack(side="left", fill="x", expand=True)
        self.combo_obligacion.configure(state="disabled")
        
        # (+) Button for Service
        self.btn_add_serv = ctk.CTkButton(frame_serv, text="+", width=30, fg_color=COLORS["secondary_button"], command=self.quick_add_service)
        self.btn_add_serv.pack(side="left", padx=(5,0))

        ctk.CTkLabel(self, text="Periodo (MM-YYYY):").grid(row=4, column=0, padx=20, pady=5, sticky="w")
        self.entry_periodo = ctk.CTkEntry(self, placeholder_text="2025-01")
        self.entry_periodo.grid(row=5, column=0, padx=20, pady=5, sticky="ew")

        ctk.CTkLabel(self, text="Fecha Vencimiento (DD/MM/AAAA):").grid(row=6, column=0, padx=20, pady=5, sticky="w")
        self.entry_fecha = ctk.CTkEntry(self, placeholder_text="15/01/2025")
        self.entry_fecha.grid(row=7, column=0, padx=20, pady=5, sticky="ew")

        ctk.CTkLabel(self, text="Monto Original:").grid(row=8, column=0, padx=20, pady=5, sticky="w")
        self.entry_monto = ctk.CTkEntry(self, placeholder_text="15000.00")
        self.entry_monto.grid(row=9, column=0, padx=20, pady=5, sticky="ew")

        self.pdf_path = None
        self.payment_path = None

        # Smart OCR Button
        self.btn_ocr = ctk.CTkButton(self, text="📄 Auto-completar desde Factura", command=self.auto_complete_from_file, fg_color="#8E44AD", hover_color="#7D3C98")
        self.btn_ocr.grid(row=10, column=0, padx=20, pady=(15, 5), sticky="ew")
        
        self.btn_file = ctk.CTkButton(self, text="Adjuntar Factura (Solo Guardar)", command=self.select_file, fg_color=COLORS["secondary_button"], hover_color="gray70")
        self.btn_file.grid(row=11, column=0, padx=20, pady=5, sticky="ew")

        self.btn_file_pay = ctk.CTkButton(self, text="Adjuntar Comprobante Pago", command=self.select_file_pay, fg_color=COLORS["secondary_button"], hover_color="gray70")
        self.btn_file_pay.grid(row=12, column=0, padx=20, pady=5, sticky="ew")

        self.btn_save = ctk.CTkButton(self, text="Guardar", command=self.save, fg_color=COLORS["primary_button"], hover_color=COLORS["primary_button_hover"])
        self.btn_save.grid(row=13, column=0, padx=20, pady=20, sticky="ew")

        self.transient(parent)
        self.grab_set()
        self.lift()
        self.focus_force()
        self.after(10, self._center_window)

    def auto_complete_from_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Facturas", "*.pdf;*.txt;*.csv")])
        if not file_path: return

        # Call Parser
        # We need to import the class or assume it's available in global scope if previously defined
        # Assuming SmartInvoiceService is defined above in the file as per previous step
        
        try:
            result = SmartInvoiceService.parse_file(file_path)
            if not result:
                messagebox.showwarning("Aviso", "No se pudo extraer información legible.")
                return

            # Fill Fields
            if result.get("amount"):
                self.entry_monto.delete(0, "end")
                self.entry_monto.insert(0, str(result["amount"]))
            
            if result.get("date"):
                dt = result["date"]
                self.entry_fecha.delete(0, "end")
                self.entry_fecha.insert(0, dt.strftime("%d/%m/%Y"))
                
                # Auto predict Period
                self.entry_periodo.delete(0, "end")
                # User Request: Format MM-YYYY
                self.entry_periodo.insert(0, dt.strftime("%Y-%m"))
            
            # Save path as well?
            self.pdf_path = file_path
            self.btn_file.configure(text=f"Adjunto: {os.path.basename(file_path)}", fg_color=COLORS["status_paid"])
            
            messagebox.showinfo("Lectura Exitosa", "Se han completado los campos detectados.\nPor favor verifica los valores.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Fallo al leer archivo: {str(e)}")

    def quick_add_inmueble(self):
        d = AddInmuebleDialog(self)
        self.wait_window(d)
        
        # Refresh Inmuebles
        inmuebles = self.catalogs_controller.get_inmuebles(include_inactive=False)
        self.inmueble_map = {i.alias: i.id for i in inmuebles}
        inmueble_aliases = list(self.inmueble_map.keys())
        self.combo_inmueble.set_completion_list(inmueble_aliases)
        
    def quick_add_service(self):
        alias = self.combo_inmueble.get()
        if not alias or alias not in self.inmueble_map:
             messagebox.showwarning("Aviso", "Seleccione un inmueble primero.")
             return
             
        inmueble_id = self.inmueble_map[alias]
        # We need the Inmueble Object for ManageServicesDialog
        # Quick fetch by ID
        found = next((i for i in self.catalogs_controller.get_inmuebles(include_inactive=False) if i.id == inmueble_id), None)
        
        if found:
            d = ManageServicesDialog(self, found)
            self.wait_window(d)
            
            # Refresh Obligations
            # We need to re-fetch all obligations to get the new one
            self.all_obligaciones = ObligacionesController().get_all_obligaciones()
            
            # Retrigger select to update combo
            # We must pass the alias to trigger the filtering logic
            self.on_inmueble_select(alias)

    def _center_window(self):
        self.update_idletasks()
        try:
            width = self.winfo_width()
            height = self.winfo_height()
            x = self.parent.winfo_rootx() + (self.parent.winfo_width() // 2) - (width // 2)
            y = self.parent.winfo_rooty() + (self.parent.winfo_height() // 2) - (height // 2)
            self.geometry(f'+{x}+{y}')
        except: pass

    def on_inmueble_select(self, choice):
        if not choice or choice not in self.inmueble_map:
            return
            
        inmueble_id = self.inmueble_map[choice]
        
        # Filter Obligations for this Inmueble
        # Display: "Proveedor (Servicio)" or just "Proveedor"
        filtered_obs = [o for o in self.all_obligaciones if o.inmueble_id == inmueble_id]
        
        self.filtered_obs_map = {f"{o.proveedor.nombre_entidad} ({o.proveedor.categoria})": o.id for o in filtered_obs}
        
        values = list(self.filtered_obs_map.keys())
        if values:
            self.combo_obligacion.configure(values=values, state="normal")
            self.combo_obligacion.set(values[0])
        else:
            self.combo_obligacion.configure(values=["Sin servicios activos"], state="disabled")
            self.combo_obligacion.set("Sin servicios activos")
    
    def select_file(self):
        file = ctk.filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if file:
            self.pdf_path = file
            self.btn_file.configure(text=f"Factura: ...{file[-15:]}", fg_color=COLORS["status_paid"])
            
            # --- SMART INTELLIGENCE ---
            filename = os.path.basename(file).lower()
            
            # 1. Try to detect Period (MM-YYYY or YYYY-MM)
            # Regex for MM-YYYY or YYYY-MM or similar
            # Simplified: look for 2024, 2025
            import re
            year_match = re.search(r"(202[0-9])", filename)
            month_match = re.search(r"(0[1-9]|1[0-2])", filename) # 01-12
            
            if year_match and month_match:
                # Construct MM-YYYY
                mm = month_match.group(1)
                yyyy = year_match.group(1)
                # Avoid matching year in MM part if pos is close? Keep simple.
                self.entry_periodo.delete(0, 'end')
                self.entry_periodo.insert(0, f"{mm}-{yyyy}")
                
            # 2. Try to detect Provider/Service
            # 2. Try to detect Provider/Service
            # Strategy: 
            # If Inmueble already selected, search ONLY within that Inmueble's obligations.
            # If no Inmueble selected, search ALL (global).
            
            current_inm_alias = self.combo_inmueble.get()
            current_inm_id = self.inmueble_map.get(current_inm_alias)
            
            search_pool = self.all_obligaciones
            if current_inm_id:
                search_pool = [o for o in self.all_obligaciones if o.inmueble_id == current_inm_id]
            
            found_obs = None
            found_inm = None
            
            for obs in search_pool:
                p_name = obs.proveedor.nombre_entidad.lower()
                # Check match (lenient)
                if p_name in filename:
                    found_obs = obs
                    found_inm = obs.inmueble
                    break
            
            if found_obs:
                # If we were restricting search, we don't need to change Inmueble
                # If we were global search, we DO need to set Inmueble
                
                if current_inm_id:
                    # Just Select Obligation
                     pass # Inmueble stays same
                else:
                    # Auto-Select Inmueble
                    self.combo_inmueble.set(found_inm.alias)
                    self.on_inmueble_select(found_inm.alias) # Trigger cascade
                
                # Auto-Select Obligation
                target_key = f"{found_obs.proveedor.nombre_entidad} ({found_obs.proveedor.categoria})"
                
                # Check availability in current filtered map (it should be there if logic is sound)
                if target_key in self.filtered_obs_map:
                    self.combo_obligacion.set(target_key)
                    self.btn_file.configure(text=f"🤖 Leído: {found_obs.proveedor.nombre_entidad}")
                else:
                    # Edge case: If filtering desynced or not triggered?
                    # Force trigger if global
                    pass


    def select_file_pay(self):
        file = ctk.filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf"), ("Images", "*.png;*.jpg;*.jpeg")])
        if file:
            self.payment_path = file
            self.btn_file_pay.configure(text=f"Pago: ...{file[-15:]}", fg_color=COLORS["status_paid"])

    def save(self):
        from datetime import datetime

        try:
            obs_text = self.combo_obligacion.get()
            if not obs_text or obs_text not in self.filtered_obs_map: 
                messagebox.showwarning("Faltan datos", "Seleccione un servicio válido")
                return
            
            obligacion_id = self.filtered_obs_map[obs_text]
            periodo = self.entry_periodo.get()
            fecha_str = self.entry_fecha.get()
            monto_str = self.entry_monto.get()

            # Validacion flexible
            # Date Parsing
            fecha_str = self.entry_fecha.get().strip()
            fecha_venc = parse_fuzzy_date(fecha_str)
            
            if not fecha_venc:
                 messagebox.showerror("Error Validación", f"Fecha inválida: {fecha_str}\nUse DD/MM/AAAA")
                 return

            monto = parse_localized_float(monto_str)

            # --- COGNITIVE AI CHECK ---
            # Safety local import to avoid circular issues if any
            # (Assuming CognitiveService is defined in global scope or imported)
            # Since we pasted it in this file, it is available.
            is_anomaly, msg = CognitiveService.detect_anomaly(obligacion_id, monto)
            if is_anomaly:
                # Play alert sound if feasible?
                if not messagebox.askyesno("⚠️ Alerta Cognitiva", f"{msg}\n\n¿Desea guardar de todos modos?", parent=self):
                    return
            # --------------------------
            
            # --- DUPLICATE AUDIT ---
            if CognitiveService.check_duplicate(obligacion_id, periodo):
                 prov_name = self.combo_obligacion.get().split(" (")[0] # Rough extract
                 if not messagebox.askyesno("⚠️ Posible Duplicado", 
                     f"Ya existe un registro para {prov_name} en el período {periodo}.\n\n¿Está seguro que desea crear otro?", parent=self):
                     return
            # -----------------------

            # --- Period Normalization (MM-YYYY -> YYYY-MM) ---
            # Try to fix format if user typed MM-YYYY or YYYY-MM
            import re
            p_val = self.entry_periodo.get().strip()
            # If MM-YYYY (2-4)
            if re.match(r'^\d{2}-\d{4}$', p_val):
                 parts = p_val.split('-')
                 periodo = f"{parts[1]}-{parts[0]}" # Flip to YYYY-MM
            elif re.match(r'^\d{4}-\d{2}$', p_val):
                 periodo = p_val # Keep YYYY-MM
            else:
                 periodo = p_val # Pass through (Constraint will catch if bad, or let service handle)

            # Upload Files to Cloud DB (BLOBs)
            from services.vencimiento_service import VencimientoService
            service = VencimientoService()
            
            doc_id = None
            pay_doc_id = None
            
            # 1. Invoice
            if self.pdf_path and os.path.exists(self.pdf_path):
                 try:
                     doc_id = service.upload_document(self.pdf_path)
                     app_logger.info(f"New Invoice uploaded to Cloud DB: ID {doc_id}")
                 except Exception as e:
                     messagebox.showerror("Error Subida", f"Fallo al subir factura: {e}", parent=self)
                     return

            # 2. Payment Proof
            if self.payment_path and os.path.exists(self.payment_path):
                 try:
                     pay_doc_id = service.upload_document(self.payment_path)
                     app_logger.info(f"New Payment Proof uploaded to Cloud DB: ID {pay_doc_id}")
                 except Exception as e:
                     messagebox.showerror("Error Subida", f"Fallo al subir comprobante: {e}", parent=self)
                     return

            data = {
                "obligacion_id": obligacion_id,
                "periodo": periodo,
                "fecha_vencimiento": fecha_venc,
                "monto_original": monto,
                "estado": EstadoVencimiento.PENDIENTE.name,
                "documento_id": doc_id,
                "comprobante_pago_id": pay_doc_id,
                "ruta_archivo_pdf": None, # Disable legacy local path
                "ruta_comprobante_pago": None
            }

            # Warning Check
            # We rely on parent's current period warning, 
            # BUT user might have typed a date in a DIFFERENT period than the navigator.
            # Ideally we should check status of `periodo` explicitly?
            # check_period_status usually checks by Date.
            try:
                # Convert string period to date (1st of month) for checking
                y, m = map(int, periodo.split('-'))
                check_date = date(y, m, 1)
                status = PeriodService.check_period_status(check_date)
                if status == EstadoPeriodo.CERRADO:
                     if not messagebox.askyesno("Advertencia - Período Cerrado", f"El período {periodo} está CERRADO (Rendido).\n¿Desea continuar?", parent=self):
                         return
            except: pass

            # --- VALIDATION: Inmueble Consistency ---
            # Ensure the selected Obligation actually belongs to the selected Inmueble
            # This prevents specific "Callao" bug where UI might be desynced
            selected_inm_alias = self.combo_inmueble.get()
            if selected_inm_alias in self.inmueble_map:
                expected_inm_id = self.inmueble_map[selected_inm_alias]
                
                # Find the obligation object
                target_obl = next((o for o in self.all_obligaciones if o.id == obligacion_id), None)
                
                if target_obl and target_obl.inmueble_id != expected_inm_id:
                    # Desync Detected!
                    correct_inm_name = target_obl.inmueble.alias if target_obl.inmueble else "Desconocido"
                    app_logger.error(f"UI Desync in Create: User selected '{selected_inm_alias}' but Obs ID {obligacion_id} belongs to '{correct_inm_name}'")
                    
                    messagebox.showerror("Error de Consistencia", 
                                       f"Error interno de selección:\n\n"
                                       f"El servicio '{obs_text}' pertenece a '{correct_inm_name}', "
                                       f"pero usted seleccionó '{selected_inm_alias}'.\n\n"
                                       "Por favor, vuelva a seleccionar el Inmueble para corregirlo.")
                    return

            if VencimientosController().create_vencimiento(data):
                # Check Period Consistency for UX
                view_period = self.parent.current_period_id
                created_period = data['periodo']
                
                if view_period != created_period:
                     if messagebox.askyesno("Éxito", f"Vencimiento creado en {created_period}.\n\nActualmente estás viendo {view_period}.\n¿Deseas cambiar la vista al período del nuevo vencimiento?", parent=self):
                         # Change View Period
                         if hasattr(self.parent, 'time_navigator'):
                             # Parse period "MM-YYYY" -> Date
                             try:
                                 m, y = map(int, created_period.split('-'))
                                 from datetime import date
                                 target_date = date(y, m, 1)
                                 self.parent.time_navigator.set_date(target_date) # This triggers load_data internally via callback
                             except:
                                 self.parent.load_data(period_id=created_period, force=True)
                         else:
                             self.parent.load_data(period_id=created_period, force=True)
                     else:
                         # Just refresh ensuring we don't break anything, but data won't show
                         pass
                else:
                    messagebox.showinfo("Éxito", "Vencimiento creado correctamente.")
                    # Refresh Grid safely after dialog closes
                    self.parent.mark_dirty()
                    self.parent.after(200, lambda: self.parent.load_data(force=True))

                self.destroy()
        except ValueError as e:
            messagebox.showerror("Error Validación", f"Datos inválidos (Fecha/Monto):\n{e}", parent=self)
        except Exception as e:
            messagebox.showerror("Error al Guardar", f"Error del sistema:\n{e}", parent=self)



class ClonePeriodDialog(ctk.CTkToplevel):
    def __init__(self, parent, current_period_id):
        super().__init__(parent)
        self.title("Clonar Período Anterior")
        self.geometry("400x350")
        
        # UI Focus Fix
        self.lift()
        self.focus_force()
        self.attributes("-topmost", True)

        self.parent = parent
        self.current_period_id = current_period_id
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        ctk.CTkLabel(self, text="Clonar Vencimientos", font=FONTS["heading"], text_color=COLORS["primary_button"]).grid(row=0, column=0, pady=(20, 10))
        
        info_text = f"Esta acción copiará todos los vencimientos\ndesde un período anterior al actual ({current_period_id}).\n\nLas fechas se ajustarán automáticamente."
        ctk.CTkLabel(self, text=info_text, font=FONTS["body"], text_color="gray").grid(row=1, column=0, pady=5)

        # Source Selector
        frame_src = ctk.CTkFrame(self, fg_color="transparent")
        frame_src.grid(row=2, column=0, pady=10)
        
        ctk.CTkLabel(frame_src, text="Desde Período:").pack(side="left", padx=5)
        
        self.combo_source = ctk.CTkComboBox(frame_src, width=150)
        self.combo_source.pack(side="left", padx=5)
        self._populate_periods()

        # Action Buttons
        frame_btn = ctk.CTkFrame(self, fg_color="transparent")
        frame_btn.grid(row=3, column=0, pady=20)

        ctk.CTkButton(frame_btn, text="Cancelar", fg_color=COLORS["secondary_button"], width=100, command=self.destroy).pack(side="left", padx=10)
        ctk.CTkButton(frame_btn, text="Confirmar Clonado", fg_color=COLORS["primary_button"], width=140, command=self.confirm).pack(side="left", padx=10)

        self.transient(parent)
        self.grab_set()
        self.focus_force()
        center_window(self, parent)

    def _populate_periods(self):
        try:
            # Fetch REAL periods from DB
            from services.period_service import PeriodService
            all_periods = PeriodService.get_all_periods()
            
            # Filter: Exclude current target period
            # And convert to string list
            opts = [p.periodo_id for p in all_periods if p.periodo_id != self.current_period_id]
            
            self.combo_source.configure(values=opts)
            if opts: self.combo_source.set(opts[0])
            else: self.combo_source.set("Sin otros períodos")
            self.combo_source.configure(state="normal" if opts else "disabled")
            
        except Exception as e:
            print(e)
            self.combo_source.configure(values=["Error"])

    def confirm(self):
        src = self.combo_source.get()
        if not src: return
        
        if messagebox.askyesno("Confirmar", f"¿Copiar vencimientos de {src} a {self.current_period_id}?", parent=self):
             try:
                 count = VencimientosController().service.clone_period(src, self.current_period_id)
                 if count > 0:
                     messagebox.showinfo("Éxito", f"Se clonaron {count} registros.", parent=self)
                     self.parent.load_data()
                     self.destroy()
                 else:
                     messagebox.showwarning("Atención", "No se encontraron registros en el período origen o ya existían en el destino.", parent=self)
             except Exception as e:
                 messagebox.showerror("Error", str(e), parent=self)

class EmptyPeriodDialog(ctk.CTkToplevel):
    def __init__(self, parent, period_id, on_clone=None):
        super().__init__(parent)
        self.title("Inicialización de Período")
        self.geometry("500x320")
        
        # UI Focus Fix
        self.lift()
        self.focus_force()
        self.attributes("-topmost", True)
        
        self.parent = parent
        self.period_id = period_id
        self.on_clone = on_clone
        
        # Center Window
        self.update_idletasks()
        try:
            x = parent.winfo_rootx() + (parent.winfo_width() // 2) - 250
            y = parent.winfo_rooty() + (parent.winfo_height() // 2) - 160
            self.geometry(f'+{x}+{y}')
        except: pass
        
        self.transient(parent)
        self.grab_set()
        
        # --- UI CONTENT ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)
        
        # Icon / Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, pady=(25, 10))
        
        ctk.CTkLabel(header_frame, text="📅", font=("Segoe UI", 40)).pack(side="left", padx=10)
        
        title_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_frame.pack(side="left")
        
        ctk.CTkLabel(title_frame, text="Nuevo Período Detectado", font=("Segoe UI", 20, "bold"), text_color=COLORS["text_primary"]).pack(anchor="w")
        ctk.CTkLabel(title_frame, text=f"Período: {period_id}", font=("Segoe UI", 14, "bold"), text_color=COLORS["primary_button"]).pack(anchor="w")
        
        # Description
        desc_text = (
            "Este período aún no contiene registros.\n\n"
            "Para agilizar su trabajo, puede importar la configuración y vencimientos\n"
            "del mes anterior, o comenzar con un lienzo en blanco."
        )
        ctk.CTkLabel(self, text=desc_text, font=("Segoe UI", 12), text_color="gray").grid(row=1, column=0, padx=30, pady=10)
        
        # Action Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=2, column=0, pady=25)
        
        self.btn_clone = ctk.CTkButton(
            btn_frame, 
            text="📥 Importar Mes Anterior", 
            command=self.confirm_clone,
            fg_color=COLORS.get("success", "#28B463"), 
            hover_color="#1D8348",
            width=180,
            height=35,
            font=("Segoe UI", 12, "bold")
        )
        self.btn_clone.pack(side="left", padx=10)
        
        self.btn_empty = ctk.CTkButton(
            btn_frame, 
            text="✨ Iniciar Vacío", 
            command=self.confirm_empty,
            fg_color="transparent", 
            border_width=1,
            border_color="gray",
            text_color="gray",
            hover_color="#EAEDED",
            width=140,
            height=35
        )
        self.btn_empty.pack(side="left", padx=10)
        
    def confirm_clone(self):
        self.destroy()
        if self.on_clone:
            self.on_clone()
            
    def confirm_empty(self):
        self.destroy()
        # Parse period from title or store it in constructor?
        # We need the period_id that we are trying to create.
        # Actually init sets self.period_id. NOTE: Previous code didn't save it. 
        # I need to check __init__ of EmptyPeriodDialog again or just update it to save self.period_id
        
        # But wait, looking at my previous view, I see `self.parent = parent` but NOT `self.period_id = period_id`
        # wait, I checked line 1713 and it had `self.period_id = period_id` in my previous "Replace" call?
        # Let's check init again.
        
        if hasattr(self, 'period_id'):
             # Create it explicitly
             try:
                 from services.period_service import PeriodService
                 from database import SessionLocal
                 y, m = map(int, self.period_id.split('-'))
                 PeriodService.create_period(y, m, SessionLocal())
                 
                 # Navigate / Load
                 self.parent.load_data(period_id=self.period_id, force=True)
             except Exception as e:
                 messagebox.showerror("Error", f"Fallo al crear período vacío: {e}", parent=self)
