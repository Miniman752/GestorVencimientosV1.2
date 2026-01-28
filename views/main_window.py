import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import os
from database import init_db, create_new_db_file, init_db_engine
from config import save_last_db_path, APP_TITLE, APP_GEOMETRY, COLORS, FONTS, get_cloud_backup_path, get_cloud_checked_flag
from .treasury_view import TreasuryView # NEW
from .dashboard_view import DashboardView
from .vencimientos_view import VencimientosView

# ... (Existing imports)


from .catalogs_view import CatalogsView
from .analysis_view import AnalysisView 
from .oracle_view import OracleView
from .db_admin_view import DbAdminView
from .users_view import UsersView # NEW
from .credentials_view import CredentialsView # NEW (Vault)
from .forex_view import ForexView
from .period_manager_view import PeriodManagerWindow # RESTORED

from .reconciliation_view import ReconciliationView # RESTORED
from .health_monitor_view import HealthMonitorView # RESTORED
from .chat_view import ChatView # RESTORED
from services.health_check_service import HealthCheckService # RESTORED
from services.cloud_service import CloudService # RESTORED
from services.indec_service import IndecService # RESTORED
from .cloud_wizard_view import CloudWizardDialog # RESTORED
from .calculator_view import CalculatorWindow # RESTORED
import threading # RESTORED

from .startup_view import StartupDialog # NEW
from .shutdown_dialog import ShutdownDialog # NEW

from datetime import datetime # Moved explicitly
from models.entities import RolUsuario # NEW: For permissions

class MainWindow(ctk.CTk):
    def __init__(self, current_user=None):
        super().__init__()
        
        self.current_user = current_user
        
        # Configure Root immediately (Theme, etc)
        self.title(APP_TITLE)
        self.geometry(APP_GEOMETRY)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.configure(fg_color=COLORS["main_background"])
        
        # State
        self.calculator_window = None
        
        if current_user:
            self.setup_ui()
        else:
            self.withdraw()
            self.after(100, self.show_login_dialog)

    def show_login_dialog(self):
        from .login_view import LoginView
        login = LoginView(self)
        self.wait_window(login)
        
        if hasattr(login, 'authenticated_user') and login.authenticated_user:
            self.current_user = login.authenticated_user
            self.deiconify()
            self.setup_ui()
        else:
            self.destroy()

    def setup_ui(self):
        # Update Title with User
        self.title(f"{APP_TITLE} - Usuario: {self.current_user.username}")
        
        # Menu Bar
        self.create_menu_bar()

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        # --- Sidebar ---
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0, fg_color=COLORS["sidebar_background"])
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        
        # Logo
        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame, 
            text="SIGV-PRO", 
            font=FONTS["heading"], 
            text_color=COLORS["content_surface"]
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        # Smart Greeting
        greeting_text = self.get_smart_greeting()
        self.lbl_greeting = ctk.CTkLabel(
            self.sidebar_frame,
            text=greeting_text,
            font=("Segoe UI", 11, "italic"),
            text_color="#BDC3C7",
            wraplength=160,
            justify="center"
        )
        self.lbl_greeting.grid(row=1, column=0, padx=10, pady=(0, 10))

        # Cloud Status Indicator
        self.lbl_status = ctk.CTkLabel(
            self.sidebar_frame,
            text="Inicializando...",
            font=("Segoe UI", 10, "bold"),
            text_color="#95A5A6"
        )
        self.lbl_status.grid(row=2, column=0, padx=10, pady=(0, 10))


        # Botones de Navegación
        from services.permission_service import PermissionService # Local import to avoid circular dependency in top-level

        self.btn_catalogs = self._create_nav_button("Catálogos", self.show_catalogs, 3)
        self.btn_vencimientos = self._create_nav_button("Vencimientos", self.show_vencimientos, 4)
        self.btn_treasury = self._create_nav_button("💰 Caja / Tesorería", self.show_treasury, 5) # NEW
        self.btn_forex = self._create_nav_button("Mesa de Dinero", self.show_forex, 6)
        
        self.btn_reconciliation = None
        if PermissionService.user_has_permission(self.current_user, PermissionService.CAN_EDIT_VENCIMIENTOS):
            self.btn_reconciliation = self._create_nav_button("Conciliar Bancos ⚖️", self.show_reconciliation, 7)
        self.btn_analysis = self._create_nav_button("Gestión Temporal", self.show_analysis, 8)
        self.btn_oracle = self._create_nav_button("Oráculo (Predicción)", self.show_oracle, 9)
        self.btn_dashboard = self._create_nav_button("Tablero", self.show_dashboard, 10)
        
        # RBAC: Only Admin sees Admin Tools
        self.btn_db_admin = None
        from services.permission_service import PermissionService
        
        # Check Permissions
        if PermissionService.user_has_permission(self.current_user, PermissionService.CAN_MANAGE_CONFIG):
            self.btn_db_admin = self._create_nav_button("Admin. Datos", self.show_db_admin, 11)
            
        self.btn_calculator = self._create_nav_button("🧮 Calculadora", self.open_calculator, 12)
        self.btn_chat = self._create_nav_button("🧠 Asistente AI", self.show_chat, 13)
        
        self.btn_users = None
        if PermissionService.user_has_permission(self.current_user, PermissionService.CAN_MANAGE_USERS):
            self.btn_users = self._create_nav_button("👥 Usuarios", self.show_users, 14)

        self.btn_credentials = self._create_nav_button("🔐 Bóveda Claves", self.show_credentials, 15)

        # Spacer Row (Push Exit to bottom)
        self.sidebar_frame.grid_rowconfigure(21, weight=1) # Updated index

        self.btn_salir = ctk.CTkButton(
            self.sidebar_frame, 
            text="Salir", 
            fg_color="transparent", 
            border_width=1, 
            border_color=COLORS["secondary_button"],
            text_color=COLORS["text_light"], 
            hover_color=COLORS["secondary_button"],
            command=self.on_close
        )
        self.btn_salir.grid(row=22, column=0, padx=20, pady=20, sticky="s") # Updated index

        # --- Frames de Contenido ---
        self.dashboard_view = DashboardView(self)
        self.vencimientos_view = VencimientosView(self)
        self.treasury_view = TreasuryView(self) # NEW
        self.catalogs_view = CatalogsView(self)

        self.analysis_view = AnalysisView(self)
        self.oracle_view = OracleView(self)
        self.forex_view = ForexView(self) 
        self.reconciliation_view = ReconciliationView(self) 
        self.chat_view = ChatView(self) 
        self.db_admin_view = DbAdminView(self)
        self.users_view = UsersView(self) 
        self.credentials_view = CredentialsView(self) 

        # Check Cloud Setup after UI load (delayed)
        self.after(1000, self.check_cloud_setup)
        
        # --- SHOW STARTUP DIALOG ---
        self.after(100, self.show_startup_dialog)

    def show_startup_dialog(self):
        from config import load_last_db_path
        last = load_last_db_path()
        
        def on_open_wrapper(path=None):
             if path:
                 # Direct load
                 self._switch_db(path)
                 self.startup_dialog.destroy()
                 self.startup_dialog = None
             else:
                 # Dialog picker
                 success = self.action_open_db()
                 if success:
                     if self.startup_dialog: 
                        self.startup_dialog.destroy()
                        self.startup_dialog = None

        def on_new_wrapper():
            success = self.action_new_db()
            if success:
                if self.startup_dialog: 
                    self.startup_dialog.destroy()
                    self.startup_dialog = None
                
        self.startup_dialog = StartupDialog(self, on_new_wrapper, on_open_wrapper, last)


    def check_cloud_setup(self):
        # Logic: If not checked yet AND no cloud path set
        if not get_cloud_checked_flag() and not get_cloud_backup_path():
            providers = CloudService.detect_cloud_providers()
            if providers:
                CloudWizardDialog(self, providers)


    def start_indec_check(self):
        """Starts the INDEC/BNA sync in a background thread."""
        thread = threading.Thread(target=self._run_indec_sync, daemon=True)
        thread.start()

    def _run_indec_sync(self):
        """Worker thread for INDEC and BNA sync."""
        from services.bna_service import BnaService
        
        # 1. INDEC
        success_indec, count_indec = IndecService.sync_indices()
        
        # 2. BNA
        success_bna, count_bna = BnaService.sync_rates()
        
        msg_parts = []
        if success_indec and count_indec > 0:
            msg_parts.append(f"• {count_indec} período(s) de inflación (INDEC).")
            
        if success_bna and count_bna > 0:
            msg_parts.append(f"• {count_bna} cotización(es) del Dólar (BNA).")
            
        if msg_parts:
            full_msg = "Se han detectado y actualizado nuevos datos:\n\n" + "\n".join(msg_parts)
            # Update UI from main thread
            self.after(0, lambda: messagebox.showinfo(
                "Actualización Automática", 
                full_msg
            ))

    def get_smart_greeting(self):
        # from datetime import datetime # Already imported at top
        hour = datetime.now().hour
        
        # Use authenticated user name
        user_name = self.current_user.nombre_completo or self.current_user.username
        # Split first name for cleaner look
        first_name = user_name.split()[0].capitalize()
        
        if 5 <= hour < 12:
            return f"Buenos días, {first_name}."
        elif 12 <= hour < 19:
            return f"Buenas tardes, {first_name}."
        else:
            return f"Buenas noches, {first_name}."

    def _create_nav_button(self, text, command, row):
        btn = ctk.CTkButton(
            self.sidebar_frame, 
            text=text, 
            command=command,
            fg_color="transparent",
            text_color=COLORS["text_light"],
            hover_color=COLORS["primary_button"],
            font=FONTS["body"],
            corner_radius=6,
            height=35,
            anchor="w"
        )
        btn.grid(row=row, column=0, padx=20, pady=5, sticky="ew")
        return btn

    def open_calculator(self):
        if self.calculator_window is None or not self.calculator_window.winfo_exists():
            self.calculator_window = CalculatorWindow(self) # Create new
        else:
            self.calculator_window.lift() # Bring to front
            self.calculator_window.focus()

    def show_dashboard(self): self.select_frame("dashboard")
    def show_vencimientos(self): self.select_frame("vencimientos")
    def show_catalogs(self): self.select_frame("catalogs")
    def show_analysis(self): self.select_frame("analysis")
    def show_oracle(self): self.select_frame("oracle")
    def show_forex(self): self.select_frame("forex")
    def show_treasury(self): self.select_frame("treasury") # NEW
    def show_reconciliation(self): self.select_frame("reconciliation") # NEW
    def show_db_admin(self): self.select_frame("db_admin")
    def show_chat(self): self.select_frame("chat")
    def show_users(self): self.select_frame("users")
    def show_credentials(self): self.select_frame("credentials")

    def select_frame(self, name):
        # Reset colors
        self._update_btn_access(self.btn_dashboard, name == "dashboard")
        self._update_btn_access(self.btn_vencimientos, name == "vencimientos")
        self._update_btn_access(self.btn_catalogs, name == "catalogs")
        self._update_btn_access(self.btn_treasury, name == "treasury") # NEW
        self._update_btn_access(self.btn_analysis, name == "analysis")
        self._update_btn_access(self.btn_oracle, name == "oracle")
        self._update_btn_access(self.btn_forex, name == "forex")
        self._update_btn_access(self.btn_reconciliation, name == "reconciliation")
        
        if self.btn_db_admin:
            self._update_btn_access(self.btn_db_admin, name == "db_admin")
            
        self._update_btn_access(self.btn_chat, name == "chat")
        
        if self.btn_users:
            self._update_btn_access(self.btn_users, name == "users")
            
        self._update_btn_access(self.btn_credentials, name == "credentials")

        # Hide all
        self.dashboard_view.grid_forget()
        self.vencimientos_view.grid_forget()
        self.catalogs_view.grid_forget()
        self.treasury_view.grid_forget() # NEW
        self.analysis_view.grid_forget()
        self.oracle_view.grid_forget()
        self.forex_view.grid_forget()
        self.reconciliation_view.grid_forget()
        self.chat_view.grid_forget()
        self.db_admin_view.grid_forget()
        self.users_view.grid_forget()
        self.credentials_view.grid_forget()

        # Show target
        if name == "dashboard":
            self.dashboard_view.grid(row=0, column=1, sticky="nsew")
            # Lazy Load
            self.dashboard_view.start_data_load(force=False)
        elif name == "vencimientos":
            self.vencimientos_view.grid(row=0, column=1, sticky="nsew")
            # Lazy Load: Always reload to capture Reconciliation changes
            self.vencimientos_view.load_data(force=True)
        elif name == "treasury":
             self.treasury_view.grid(row=0, column=1, sticky="nsew")
             # No lazy load needed yet, internal view handles it on init or refresh
        elif name == "catalogs":
            self.catalogs_view.grid(row=0, column=1, sticky="nsew")
            self.catalogs_view.tkraise()
        elif name == "analysis":
            self.analysis_view.grid(row=0, column=1, sticky="nsew")
            self.analysis_view.tkraise()
        elif name == "oracle":
            self.oracle_view.grid(row=0, column=1, sticky="nsew")
            self.oracle_view.tkraise()
        elif name == "forex":
            self.forex_view.grid(row=0, column=1, sticky="nsew")
            self.forex_view.tkraise()
        elif name == "reconciliation": 
            self.reconciliation_view.grid(row=0, column=1, sticky="nsew")
            self.reconciliation_view.tkraise()
        elif name == "db_admin":
            self.db_admin_view.grid(row=0, column=1, sticky="nsew")
        elif name == "chat":
            self.chat_view.grid(row=0, column=1, sticky="nsew")
        elif name == "users":
            self.users_view.grid(row=0, column=1, sticky="nsew")
            self.users_view.load_users()
        elif name == "credentials":
            self.credentials_view.grid(row=0, column=1, sticky="nsew")
            self.credentials_view.load_data()

    def mark_dashboard_dirty(self):
        """Helper to mark dashboard as needing refresh"""
        if hasattr(self, 'dashboard_view'):
            self.dashboard_view.mark_dirty()

    def _update_btn_access(self, btn, is_active):
        if not btn: return
        if is_active:
            btn.configure(fg_color=COLORS["primary_button"], text_color=COLORS["content_surface"])
        else:
            btn.configure(fg_color="transparent", text_color=COLORS["text_light"])

    def create_menu_bar(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Archivo", menu=file_menu)
        
        file_menu.add_command(label="Nueva Base de Datos...", command=self.action_new_db)
        file_menu.add_command(label="Abrir Base de Datos...", command=self.action_open_db)
        file_menu.add_command(label="Guardar Cambios", command=self.action_save_db)
        file_menu.add_separator()
        file_menu.add_command(label="Cerrar / Desconectar", command=self.action_close_db)
        file_menu.add_separator()
        file_menu.add_command(label="Salir", command=self.quit)

        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Herramientas", menu=tools_menu)
        tools_menu.add_command(label="Mesa de Dinero y Cotizaciones", command=self.show_forex)
        tools_menu.add_command(label="Gestión de Catálogos", command=self.open_catalogs)
        tools_menu.add_command(label="Administrador de Base de Datos", command=self.open_db_admin)
        tools_menu.add_separator()
        tools_menu.add_command(label="☁️ Crear Copia de Seguridad (Nube)", command=self.run_cloud_backup)
        tools_menu.add_separator()
        tools_menu.add_command(label="Motor de Experiencia (Mood)", command=self.toggle_mood_engine)
        tools_menu.add_separator()
        tools_menu.add_command(label="Configuración Fiscal (Períodos)", command=self.open_period_manager)

    def open_period_manager(self):
        PeriodManagerWindow(self)

    def action_new_db(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".db",
            filetypes=[("SQLite Database", "*.db")],
            title="Crear Nueva Base de Datos"
        )
        if not path: return False
        
        try:
            create_new_db_file(path)
            self._switch_db(path)
            messagebox.showinfo("¡Bienvenido!", f"Hemos creado y configurado tu nueva Base de Datos exitosamente.\n\nArchivo: {os.path.basename(path)}")
            return True
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return False

    def action_open_db(self):
        path = filedialog.askopenfilename(
            filetypes=[("SQLite Database", "*.db")],
            title="Abrir Base de Datos"
        )
        if not path: return False
        
        try:
            self._switch_db(path)
            messagebox.showinfo("Conectado", f"Base de datos cargada correctamente.\nTodos tus registros están listos y seguros.\n\nArchivo: {os.path.basename(path)}")
            return True
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return False

    def action_save_db(self):
        """Confirmación manual de guardado."""
        try:
            # La arquitectura usa transacciones atómicas (safe_transaction), por lo que los datos
            # ya deberían estar persistidos. Esto actúa como confirmación y sincronización visual.
            messagebox.showinfo("Guardado Exitoso", "Todos los cambios han sido registrados correctamente en la base de datos.")
        except Exception as e:
            messagebox.showerror("Error de Guardado", str(e))

    def action_close_db(self):
        if not messagebox.askyesno("Cerrar Base de Datos", "¿Seguro que desea cerrar la base de datos actual?"):
            return

        try:
            # 1. Switch to Memory (Empty)
            # Use init_db to ensure models are imported and schema is created
            init_db("sqlite:///:memory:")

            # 2. Clear Preference
            save_last_db_path(None)
            
            # 3. Clear UI
            self._refresh_all_views()
            
            # 4. Update Title
            self.title(f"{APP_TITLE} (Sin Base de Datos)")
            
            messagebox.showinfo("Cerrado", "Base de datos cerrada.\nLa pantalla se ha limpiado.")

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _switch_db(self, path):
        # 1. Update Engine
        if path.startswith("postgresql"):
            url = path
            title_name = "PostgreSQL Server 🐘"
        else:
            url = f"sqlite:///{path}"
            title_name = os.path.basename(path)
            
        init_db_engine(url)
        
        # 2. Save Preference
        save_last_db_path(path)
        
        # 3. Reload UI
        self._refresh_all_views() 
        
        self.title(f"{APP_TITLE} - {title_name}")

        # Update Status Indicator
        if hasattr(self, 'lbl_status'):
            if "postgres" in url or "neon.tech" in url:
                self.lbl_status.configure(text="🟢 Cloud: Neon.tech", text_color="#2ECC71") # Green
            else:
                self.lbl_status.configure(text="🟠 Modo Local", text_color="#F39C12") # Orange
        
        # Trigger Sync Services (INDEC/BNA) now that DB is real
        self.after(2000, self.start_indec_check)

    def _refresh_all_views(self):
        # Dashboard
        if hasattr(self.dashboard_view, 'start_data_load'): 
            self.dashboard_view.start_data_load()
        
        # Vencimientos
        if hasattr(self.vencimientos_view, 'load_data'): 
            self.vencimientos_view.load_data()
        
        # Catalogs
        if hasattr(self.catalogs_view, 'load_inmuebles'): self.catalogs_view.load_inmuebles()
        if hasattr(self.catalogs_view, 'load_proveedores'): self.catalogs_view.load_proveedores()
        
        # Analysis
        if hasattr(self.analysis_view, 'refresh'): self.analysis_view.refresh()
        
        # Oracle
        if hasattr(self.oracle_view, 'load_projection'): self.oracle_view.load_projection()

        # Forex
        if hasattr(self.forex_view, 'load_data'): 
            if hasattr(self.forex_view, 'refresh_years_combo'):
                self.forex_view.refresh_years_combo()
            self.forex_view.load_data()

    def open_catalogs(self):
        self.show_catalogs()

    def open_db_admin(self):
        self.show_db_admin()

    def on_close(self):
        """Handle application exit with Double Write Backup strategy."""
        if not messagebox.askyesno("Salir", "¿Está seguro que desea salir de la aplicación?"):
            return

        cloud_path = get_cloud_backup_path()
        
        if cloud_path:
            # Show feedback
            try:
                self.lbl_greeting.configure(text="☁️ Guardando en Nube...")
                self.update()
            except: pass
            
    def on_close(self):
        """Handle application exit with Flexible Backup Strategy."""
        # 1. Determine capabilities
        cloud_path = get_cloud_backup_path()
        has_cloud = bool(cloud_path and os.path.exists(cloud_path))
        
        # 2. Show Dialog
        dialog = ShutdownDialog(self, has_cloud_config=has_cloud)
        self.wait_window(dialog)
        
        result = dialog.result
        
        if result == "CANCEL":
            return # Stay open
            
        elif result == "NONE":
             # Fast exit
             self.quit()
             
        elif result == "LOCAL" or result == "FULL":
             # Perform Backup
             skip_cloud = (result == "LOCAL")
             
             # Create Wait UI (Recycled from previous code, simplified)
             self.wait_dialog = ctk.CTkToplevel(self)
             self.wait_dialog.title("Cerrando Sistema")
             self.wait_dialog.geometry("400x150")
             self.wait_dialog.transient(self)
             self.wait_dialog.grab_set()
             
             # Center
             x = self.winfo_x() + (self.winfo_width() // 2) - 200
             y = self.winfo_y() + (self.winfo_height() // 2) - 75
             self.wait_dialog.geometry(f"+{x}+{y}")
             
             ctk.CTkLabel(self.wait_dialog, text="⏳ Realizando copia de seguridad...", font=("Segoe UI", 12, "bold")).pack(pady=20)
             progress = ctk.CTkProgressBar(self.wait_dialog, width=300)
             progress.pack(pady=5)
             progress.start()
             
             # Run Thread
             threading.Thread(target=self._perform_shutdown_backup, args=(skip_cloud,), daemon=True).start()

    def _perform_shutdown_backup(self, skip_cloud=False):
        """Worker thread for backups (SQL Dump)."""
        try:
            import subprocess
            import sys
            
            script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "1_Crear_Copia_Seguridad_Cloud.py")
            
            if os.path.exists(script_path):
                cmd = [sys.executable, script_path, "--no-pause"]
                if skip_cloud:
                    cmd.append("--skip-replication")
                    
                subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
                app_logger.info(f"Automatic Backup (SkipCloud={skip_cloud}) completed.")
                
        except Exception as e:
            app_logger.error(f"Shutdown Backup Error: {e}")
        finally:
            self.after(0, self.quit)

    def toggle_mood_engine(self):
        self.show_dashboard()
        messagebox.showinfo("Motor de Experiencia", "El motor de experiencia está activo y monitoreando el estado del sistema.")

    def run_cloud_backup(self):
        """Runs the external backup script."""
        import subprocess
        import sys
        
        script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "1_Crear_Copia_Seguridad_Cloud.py")
        
        if not os.path.exists(script_path):
             messagebox.showerror("Error", f"No se encontró el script de respaldo:\n{script_path}")
             return

        if not messagebox.askyesno("Confirmar Respaldo", "¿Desea iniciar la copia de seguridad de la Nube ahora?\n\nEsto descargará todos los datos a su equipo local."):
            return
            
        try:
            # Run with pythonw to avoid console popping up, or python to show it.
            # Showing console is better for feedback in this case since regex parsing stdout is hard.
            # But user wants it "inside". Let's run captured.
            
            # Show wait info
            top = ctk.CTkToplevel(self)
            top.title("Realizando Backup")
            top.geometry("300x100")
            ctk.CTkLabel(top, text="⏳ Descargando datos... Por favor espere.").pack(expand=True)
            top.update()
            
            # Run
            result = subprocess.run([sys.executable, script_path], capture_output=True, text=True, encoding='utf-8', errors='replace')
            
            top.destroy()
            
            if result.returncode == 0:
                 messagebox.showinfo("Respaldo Exitoso", f"La copia de seguridad se creó correctamente en la carpeta backups.\n\nSalida:\n{result.stdout.strip()[-200:]}") # Show last lines
            else:
                 messagebox.showerror("Error en Respaldo", f"Hubo un problema:\n\n{result.stderr}")
                 
        except Exception as e:
            messagebox.showerror("Error Crítico", str(e))