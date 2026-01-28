
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime
from config import COLORS, FONTS
from controllers.db_admin_controller import DbAdminController

class DbAdminView(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color=COLORS["main_background"])
        self.controller = DbAdminController()
        
        # Grid Layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        self.header = ctk.CTkLabel(
            self, 
            text="Centro de Control de Datos (Data Vault)", 
            font=FONTS["heading"],
            text_color=COLORS["text_primary"]
        )
        self.header.grid(row=0, column=0, columnspan=2, padx=20, pady=20, sticky="w")

        # --- Card 1: Backup & Restore ---
        self.card_backup = ctk.CTkFrame(self, fg_color=COLORS["content_surface"], corner_radius=10)
        self.card_backup.grid(row=1, column=0, padx=20, pady=20, sticky="nsew")
        
        ctk.CTkLabel(self.card_backup, text="Respaldo y Recuperación", font=("Segoe UI", 16, "bold"), text_color=COLORS["text_primary"]).pack(pady=15)
        
        self.btn_backup = ctk.CTkButton(
            self.card_backup, 
            text="Crear Respaldo Ahora", 
            fg_color=COLORS["primary_button"],
            hover_color=COLORS["primary_button_hover"],
            command=self.action_backup
        )
        self.btn_backup.pack(pady=10, padx=20, fill="x")

        self.btn_backup_full = ctk.CTkButton(
            self.card_backup,
            text="Respaldo SQL Completo (Lento)",
            fg_color="#7D3C98", # Purple
            hover_color="#6C3483",
            command=self.action_backup_full
        )
        self.btn_backup_full.pack(pady=10, padx=20, fill="x")

        self.btn_restore = ctk.CTkButton(
            self.card_backup, 
            text="Restaurar desde Copia", 
            fg_color=COLORS["status_overdue"], # Red/Warning color
            hover_color="#A93226",
            command=self.action_restore
        )
        self.btn_restore.pack(pady=10, padx=20, fill="x")

        self.lbl_status = ctk.CTkLabel(self.card_backup, text="Estado: Sistema Operativo", text_color="gray")
        self.lbl_status.pack(pady=20, side="bottom")

        # --- Card 2: Portability ---
        self.card_portability = ctk.CTkFrame(self, fg_color=COLORS["content_surface"], corner_radius=10)
        self.card_portability.grid(row=1, column=1, padx=20, pady=20, sticky="nsew")
        
        ctk.CTkLabel(self.card_portability, text="Portabilidad de Datos", font=("Segoe UI", 16, "bold"), text_color=COLORS["text_primary"]).pack(pady=15)

        self.btn_export_excel = ctk.CTkButton(
            self.card_portability, 
            text="Exportar TODO a Excel", 
            fg_color=COLORS["status_paid"], # Green-ish
            hover_color="#229954",
            command=self.action_export_excel
        )
        self.btn_export_excel.pack(pady=10, padx=20, fill="x")


        self.btn_export_sql = ctk.CTkButton(
            self.card_portability, 
            text="Generar Dump SQL", 
            fg_color=COLORS["secondary_button"],
            text_color="white",
            command=self.action_export_sql
        )
        self.btn_export_sql.pack(pady=10, padx=20, fill="x")

        self.btn_zip_source = ctk.CTkButton(
            self.card_portability,
            text="📦 Empaquetar Programa (ZIP)",
            fg_color="#F39C12", # Orange
            text_color="white",
            command=self.action_zip_source
        )
        self.btn_zip_source.pack(pady=10, padx=20, fill="x")

        # --- Card 3: Oracle Maintenance ---
        self.card_oracle = ctk.CTkFrame(self, fg_color=COLORS["content_surface"], corner_radius=10)
        self.card_oracle.grid(row=2, column=0, columnspan=1, padx=20, pady=20, sticky="nsew")
        
        ctk.CTkLabel(self.card_oracle, text="Mantenimiento Oráculo", font=("Segoe UI", 16, "bold"), text_color=COLORS["text_primary"]).pack(pady=15)
        
        self.btn_apply_rules = ctk.CTkButton(
            self.card_oracle, 
            text="🛠️ Aplicar Reglas de Ajuste (Auto)", 
            fg_color=COLORS["primary_button"],
            command=self.action_apply_rules
        )
        self.btn_apply_rules.pack(pady=10, padx=20)
        
        # --- Card Recycle Bin (New) ---
        self.card_recycle = ctk.CTkFrame(self, fg_color=COLORS["content_surface"], corner_radius=10)
        self.card_recycle.grid(row=2, column=1, padx=20, pady=20, sticky="nsew")
        
        ctk.CTkLabel(self.card_recycle, text="Papelera de Reciclaje", font=("Segoe UI", 16, "bold"), text_color=COLORS["text_primary"]).pack(pady=15)
        
        self.btn_recycle = ctk.CTkButton(
            self.card_recycle,
            text="🗑️ Ver Elementos Eliminados",
            fg_color="#D35400", # Dark Orange
            command=self.open_recycle_bin
        )
        self.btn_recycle.pack(pady=10, padx=20)
        
        # --- Recent Backups List (Mini Table) ---
        self.frame_list = ctk.CTkFrame(self, fg_color=COLORS["content_surface"], corner_radius=10)
        self.frame_list.grid(row=3, column=0, columnspan=2, padx=20, pady=20, sticky="nsew")
        
        # Header with Open Button
        header_frame = ctk.CTkFrame(self.frame_list, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(header_frame, text="Copias de Seguridad Recientes", font=("Segoe UI", 14, "bold"), text_color=COLORS["text_primary"]).pack(side="left")
        
        ctk.CTkButton(
            header_frame, 
            text="📂 Abrir Carpeta", 
            width=120, 
            fg_color=COLORS["secondary_button"], 
            command=self.action_open_folder
        ).pack(side="right")
        
        self.backup_list_box = tk.Listbox(self.frame_list, height=5, borderwidth=0, highlightthickness=0)
        self.backup_list_box.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        
        # --- Card 3: Path Configuration (New) ---
        self.card_config = ctk.CTkFrame(self, fg_color=COLORS["content_surface"], corner_radius=10)
        self.card_config.grid(row=3, column=0, columnspan=2, padx=20, pady=(0, 20), sticky="nsew")
        
        ctk.CTkLabel(self.card_config, text="Configuración de Almacenamiento", font=("Segoe UI", 14, "bold"), text_color=COLORS["text_primary"]).pack(pady=10, padx=20, anchor="w")
        
        path_frame = ctk.CTkFrame(self.card_config, fg_color="transparent")
        path_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        self.lbl_current_path = ctk.CTkLabel(path_frame, text=f"Ruta actual: {self.controller.backup_dir}", text_color="gray")
        self.lbl_current_path.pack(side="left")
        
        ctk.CTkButton(
            path_frame, 
            text="Cambiar Ruta...", 
            width=100, 
            fg_color=COLORS["primary_button"],
            command=self.action_change_path
        ).pack(side="right")
        
        self.refresh_backup_list()
        
        # --- Cloud Config Section ---
        cloud_frame = ctk.CTkFrame(self.card_config, fg_color="transparent")
        cloud_frame.pack(fill="x", padx=20, pady=(10, 20))
        
        self.lbl_cloud_status = ctk.CTkLabel(cloud_frame, text="Nube: ...", text_color="gray")
        self.lbl_cloud_status.pack(side="left")
        
        ctk.CTkButton(
            cloud_frame,
            text="Configurar Nube",
            width=100,
            fg_color="#5D6D7E",
            command=self.action_config_cloud
        ).pack(side="right")
        
        # --- Server Coop Mode Match ---
        server_frame = ctk.CTkFrame(self.card_config, fg_color="transparent")
        server_frame.pack(fill="x", padx=20, pady=(5, 10))
        
        ctk.CTkLabel(server_frame, text="Modo Cooperativo (Servidor):", text_color="gray").pack(side="left")
        
        ctk.CTkButton(
            server_frame,
            text="Conectar a PostgreSQL 🐘",
            width=150,
            fg_color="#2E86C1",
            command=self.action_connect_server
        ).pack(side="right")
        
        self.update_cloud_ui()

    def update_cloud_ui(self):
        from config import get_cloud_backup_path
        path = get_cloud_backup_path()
        if path:
            self.lbl_cloud_status.configure(text=f"Nube Activa: {path}", text_color=COLORS["status_paid"])
        else:
            self.lbl_cloud_status.configure(text="Nube: No configurada", text_color="gray")

    def action_config_cloud(self):
        from services.cloud_service import CloudService
        from views.cloud_wizard_view import CloudWizardDialog
        
        providers = CloudService.detect_cloud_providers()
        # Always show wizard when manually requested, even if checked flag is True
        # We pass self.winfo_toplevel() as parent
        headers = CloudWizardDialog(self.winfo_toplevel(), providers)
        # Wait for window close to update UI
        self.wait_window(headers)
        self.wait_window(headers)
        self.update_cloud_ui()

    def action_connect_server(self):
        from views.server_connect_view import ServerConnectDialog
        
        def on_connect(url):
            # Offer Migration
            if messagebox.askyesno("Migración de Datos", "¿Desea copiar todos los datos actuales (SQLite) al nuevo Servidor (PostgreSQL)?\n\nSi elige NO, empezará con una base vacía."):
                success, msg = self.controller.migrate_sqlite_to_postgres(url)
                if success:
                     messagebox.showinfo("Migración Exitosa", "Todos los datos han sido trasladados al servidor.")
                else:
                     messagebox.showerror("Error de Migración", msg)
            
            # Restart hint
            messagebox.showwarning("Reinicio Requerido", "La aplicación debe reiniciarse para conectar con la nueva base de datos.")
            self.quit()

        ServerConnectDialog(self.winfo_toplevel(), on_success_callback=on_connect)

    def refresh_backup_list(self):
        self.backup_list_box.delete(0, tk.END)
        backups = self.controller.get_backups_list()
        for b in backups:
            self.backup_list_box.insert(tk.END, b)

    def action_backup(self):
        # 1. Show Loading (Indeterminate)
        from tkinter import Toplevel, ttk
        
        loading_popup = Toplevel(self)
        loading_popup.title("Realizando Backup")
        loading_popup.geometry("300x120")
        loading_popup.transient(self)
        loading_popup.grab_set()
        
        # Force Top
        loading_popup.lift()
        loading_popup.attributes("-topmost", True)
        
        # Center
        x = self.winfo_rootx() + (self.winfo_width() // 2) - 150
        y = self.winfo_rooty() + (self.winfo_height() // 2) - 60
        loading_popup.geometry(f"+{x}+{y}")
        
        ctk.CTkLabel(loading_popup, text="⏳ Creando copia de seguridad...", font=("Segoe UI", 12)).pack(pady=20)
        
        bar = ctk.CTkProgressBar(loading_popup, width=200)
        bar.pack(pady=5)
        bar.configure(mode="indeterminate")
        bar.start()
        
        # Force Render
        loading_popup.update()
        
        def run_thread():
            import threading
            try:
                 success, msg = self.controller.create_backup()
                 self.after(0, lambda: on_finish(success, msg))
            except Exception as e:
                 self.after(0, lambda: on_finish(False, str(e)))

        def on_finish(success, msg):
            loading_popup.destroy()
            if success:
                messagebox.showinfo("Respaldo Exitoso", f"{msg}\n\nUbicación: {self.controller.backup_dir}")
                self.refresh_backup_list()
                self.lbl_status.configure(text=f"Último respaldo: Ahora mismo")
            else:
                messagebox.showerror("Error de Respaldo", msg)
                
        import threading
        t = threading.Thread(target=run_thread)
        t.start()
        
    def action_backup_full(self):
        """Standard Full Backup (SQL) for Cloud."""
        if not messagebox.askyesno("Backup Completo (Lento)", "Este respaldo incluirá TODOS los archivos adjuntos (PDFs).\nPuede tomar varios minutos y generar un archivo grande.\n\n¿Desea continuar?"):
            return
            
        # UI Threading Pattern
        from tkinter import Toplevel
        
        loading_popup = Toplevel(self)
        loading_popup.title("Backup SQL Completo")
        loading_popup.geometry("300x120")
        loading_popup.transient(self)
        loading_popup.grab_set()
        
        loading_popup.lift()
        loading_popup.attributes("-topmost", True)
        
        # Center
        x = self.winfo_rootx() + (self.winfo_width() // 2) - 150
        y = self.winfo_rooty() + (self.winfo_height() // 2) - 60
        loading_popup.geometry(f"+{x}+{y}")
        
        ctk.CTkLabel(loading_popup, text="⏳ Generando SQL Dump...", font=("Segoe UI", 12)).pack(pady=20)
        
        bar = ctk.CTkProgressBar(loading_popup, width=200)
        bar.pack(pady=5)
        bar.configure(mode="determinate") # Change to determinate
        bar.set(0)
        
        lbl_info = ctk.CTkLabel(loading_popup, text="Iniciando...", font=("Segoe UI", 10))
        lbl_info.pack(pady=2)

        loading_popup.update()
        
        def run_thread():
            import threading
            try:
                 # Callback wrapper to run on UI thread
                 def cb(pct, msg):
                     loading_popup.after(0, lambda: update_ui(pct, msg))
                     
                 def update_ui(pct, msg):
                     try:
                         bar.set(pct)
                         lbl_info.configure(text=f"{msg} ({int(pct*100)}%)")
                     except: pass

                 # Generate filename
                 ts = datetime.now().strftime("%Y-%m-%d_%H%M")
                 fname = f"SIGV_FULL_Backup_{ts}.sql"
                 target = self.controller.backup_dir / fname
                 
                 success, msg = self.controller.generate_cloud_sql_dump(target, progress_callback=cb)
                 self.after(0, lambda: on_finish(success, msg))
            except Exception as e:
                 self.after(0, lambda: on_finish(False, str(e)))

        def on_finish(success, msg):
            loading_popup.destroy()
            if success:
                messagebox.showinfo("Backup SQL Completo", msg)
                self.refresh_backup_list()
            else:
                messagebox.showerror("Error Backup SQL", msg)
                
        import threading
        t = threading.Thread(target=run_thread)
        t.start()

    def action_zip_source(self):
        """Backups the Application Source Code."""
        # UI Threading Pattern
        from tkinter import Toplevel
        
        loading_popup = Toplevel(self)
        loading_popup.title("Empaquetando Programa")
        loading_popup.geometry("300x120")
        loading_popup.transient(self)
        loading_popup.grab_set()
        
        loading_popup.lift()
        loading_popup.attributes("-topmost", True)
        
        # Center
        x = self.winfo_rootx() + (self.winfo_width() // 2) - 150
        y = self.winfo_rooty() + (self.winfo_height() // 2) - 60
        loading_popup.geometry(f"+{x}+{y}")
        
        ctk.CTkLabel(loading_popup, text="📦 Comprimiendo Archivos...", font=("Segoe UI", 12)).pack(pady=20)
        
        bar = ctk.CTkProgressBar(loading_popup, width=200)
        bar.pack(pady=5)
        bar.configure(mode="determinate")
        bar.set(0)
        
        lbl_info = ctk.CTkLabel(loading_popup, text="Iniciando...", font=("Segoe UI", 10))
        lbl_info.pack(pady=2)

        loading_popup.update()
        
        def run_thread():
            import threading
            try:
                 def cb(pct, msg):
                     loading_popup.after(0, lambda: update_ui(pct, msg))
                     
                 def update_ui(pct, msg):
                     try:
                         bar.set(pct)
                         lbl_info.configure(text=f"{msg} ({int(pct*100)}%)")
                     except: pass

                 # Generate filename
                 ts = datetime.now().strftime("%Y-%m-%d_%H%M")
                 fname = f"SIGV_APP_Source_{ts}.zip"
                 target = self.controller.backup_dir / fname
                 
                 success, msg = self.controller.create_source_zip(target, progress_callback=cb)
                 self.after(0, lambda: on_finish(success, msg))
            except Exception as e:
                 self.after(0, lambda: on_finish(False, str(e)))

        def on_finish(success, msg):
            loading_popup.destroy()
            if success:
                messagebox.showinfo("Empaque Exitoso", msg)
                # self.refresh_backup_list() # Not in list because it is zip not db
            else:
                messagebox.showerror("Error Empaque", msg)
                
        import threading
        t = threading.Thread(target=run_thread)
        t.start()

    def action_restore(self):
        # 1. Ask for file
        # Use controller.backup_dir (Path object)
        # Allow Hybrid Restore (SQL or DB)
        filetypes = [
             ("Todos los Respaldos", "*.db *.sql"),
             ("SQL Dump (Postgres)", "*.sql"),
             ("SQLite DB (Legacy)", "*.db")
        ]
        
        filename = filedialog.askopenfilename(
            initialdir=str(self.controller.backup_dir),
            title="Seleccionar Archivo de Respaldo",
            filetypes=filetypes
        )
        if not filename: return

        # 2. Warning & Password
        confirm = messagebox.askyesno("ADVERTENCIA CRÍTICA", 
                                      "¿Está seguro? Esto REEMPLAZARÁ TODOS los datos actuales con la copia seleccionada.\n\n"
                                      "• Si usa un SQL Dump, se restaurará tal cual.\n"
                                      "• Si usa un archivo .db (SQLite) en la Nube, se migrarán sus datos.\n\n"
                                      "Esta acción es irreversible.")
        if not confirm: return
        
        pwd = ctk.CTkInputDialog(text="Ingrese Contraseña de Administrador:", title="Seguridad").get_input()
        
        # 3. Restore
        success, msg = self.controller.restore_database(filename, pwd)
        if success:
            messagebox.showinfo("Restauración Completada", "Base de datos restaurada.\nTodo está exactamente como lo dejaste en ese momento.\nPor favor reinicia la aplicación.")
        else:
            messagebox.showerror("Error de Restauración", msg)

    def action_open_folder(self):
        self.controller.open_backup_folder()

    def action_change_path(self):
        path = filedialog.askdirectory(title="Seleccionar Carpeta para Respaldos")
        if path:
            success, msg = self.controller.set_custom_backup_path(path)
            if success:
                self.lbl_current_path.configure(text=f"Ruta actual: {self.controller.backup_dir}")
                self.refresh_backup_list()
                messagebox.showinfo("Ruta Actualizada", "A partir de ahora, tus respaldos se guardarán en esta carpeta.")

    def action_export_excel(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Files", "*.xlsx")],
            title="Guardar Exportación Completa"
        )
        if not filename: return
        
        success, msg = self.controller.export_to_excel_full(filename)
        if success: messagebox.showinfo("Exportar Excel", "Tus datos han sido exportados exitosamente a Excel.")
        else: messagebox.showerror("Error", msg)

    def action_export_sql(self):
        filename = f"dump_{datetime.now().strftime('%Y%m%d')}.sql"
        f = filedialog.asksaveasfilename(defaultextension=".sql", initialfile=filename)
        if f:
             success, msg = self.controller.export_to_sql_dump(f)
             if success:
                 messagebox.showinfo("Exportar SQL", "Dump SQL generado correctamente.\nEste archivo contiene la estructura y datos para reconstruir la base de datos.")
             else:
                 messagebox.showerror("Error", msg)
            
    def action_apply_rules(self):
        if messagebox.askyesno("Confirmar", "¿Aplicar reglas de ajuste por defecto a obligaciones sin regla?"):
            success, msg = self.controller.apply_default_rules()
            if success:
                messagebox.showinfo("Éxito", msg)
            else:
                messagebox.showerror("Error", msg)

    def open_recycle_bin(self):
        from views.recycle_bin_view import RecycleBinDialog
        RecycleBinDialog(self)
        # Refresh logic if needed? 
        # Recycle Bin changes happen in isolation, mainly affect Vencimientos view.

    # --- ADD TO UI (In __init__ or helper) ---
    # Since we are using replace_file, we should inject the UI code in __init__ too. 
    # But replace_file handles contiguous blocks. 
    # I need to edit __init__ separately to add the button.
    # This block only adds the method.


