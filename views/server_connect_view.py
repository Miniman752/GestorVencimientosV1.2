import customtkinter as ctk
from tkinter import messagebox
from sqlalchemy import create_engine, text
from config import save_last_db_path, COLORS, FONTS

class ServerConnectDialog(ctk.CTkToplevel):
    def __init__(self, parent, on_success_callback=None):
        super().__init__(parent)
        self.on_success_callback = on_success_callback
        
        self.title("Conectar a Servidor (Modo Cooperativo)")
        self.geometry("450x550")
        self.resizable(False, False)
        
        # Center window
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"+{x}+{y}")
        
        self.configure(fg_color=COLORS["main_background"])
        
        # --- UI ---
        ctk.CTkLabel(self, text="Configuración del Servidor", font=FONTS["heading"], text_color=COLORS["text_primary"]).pack(pady=(20, 10))
        
        ctk.CTkLabel(self, text="Ingrese los datos de su servidor PostgreSQL.", font=FONTS["body"], text_color="gray").pack(pady=(0, 20))
        
        self.frame_form = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_form.pack(padx=30, fill="x")
        
        # Grid Setup
        self.frame_form.grid_columnconfigure(0, weight=1)
        self.frame_form.grid_columnconfigure(1, weight=2)
        
        # Fields
        self.entry_host = self._add_field("Host / IP:", "localhost", 0)
        self.entry_port = self._add_field("Puerto:", "5432", 1)
        self.entry_db = self._add_field("Nombre Base Datos:", "vencimientos_db", 2)
        self.entry_user = self._add_field("Usuario:", "postgres", 3)
        self.entry_pass = self._add_field("Contraseña:", "", 4, is_pass=True)
        
        # Buttons
        self.btn_test = ctk.CTkButton(
            self, 
            text="Probar Conexión", 
            fg_color=COLORS["secondary_button"],
            command=self.test_connection
        )
        self.btn_test.pack(pady=(30, 10), padx=30, fill="x")
        
        self.btn_save = ctk.CTkButton(
            self, 
            text="Guardar y Conectar", 
            fg_color=COLORS["primary_button"],
            state="disabled",
            command=self.save_connection
        )
        self.btn_save.pack(pady=(0, 20), padx=30, fill="x")

        # Status
        self.lbl_status = ctk.CTkLabel(self, text="", font=("Segoe UI", 10))
        self.lbl_status.pack(pady=5)
        
        self.connection_url = None

    def _add_field(self, label, default, row, is_pass=False):
        ctk.CTkLabel(self.frame_form, text=label, anchor="w", text_color=COLORS["text_primary"]).grid(row=row, column=0, pady=10, sticky="w")
        entry = ctk.CTkEntry(self.frame_form, show="*" if is_pass else "")
        entry.insert(0, default)
        entry.grid(row=row, column=1, pady=10, sticky="ew")
        return entry

    def test_connection(self):
        host = self.entry_host.get()
        port = self.entry_port.get()
        db = self.entry_db.get()
        user = self.entry_user.get()
        pwd = self.entry_pass.get()
        
        if not all([host, port, db, user, pwd]):
            messagebox.showwarning("Faltan Datos", "Por favor complete todos los campos.")
            return
            
        # Construct URL
        # Format: postgresql+psycopg2://user:password@host:port/dbname
        url = f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{db}"
        
        try:
            self.lbl_status.configure(text="Intentando conectar...", text_color="blue")
            self.update()
            
            # Simple connect check
            # We specifically try to connect to the target DB. 
            # If it doesn't exist, we might fail.
            # Strategy: Connect to 'postgres' first to check existence? 
            # Ideally user created it, OR we Auto-Create.
            
            # Let's try connecting to 'postgres' system db to verify CREDENTIALS first.
            sys_url = f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/postgres"
            engine = create_engine(sys_url, connect_args={'connect_timeout': 5})
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                
            # Credentials are good. Now check if Target DB exists.
            # We can create it if missing.
            self._ensure_database_exists(engine, db)
            
            # Now verify target connection
            target_engine = create_engine(url)
            with target_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                
            self.lbl_status.configure(text="✅ Conexión Exitosa", text_color=COLORS["status_paid"])
            self.btn_save.configure(state="normal")
            self.connection_url = url
            messagebox.showinfo("Éxito", f"Conexión establecida con el servidor.\nBase de datos '{db}' detectada/creada.")
            
        except Exception as e:
            self.lbl_status.configure(text="❌ Error de Conexión", text_color=COLORS["status_overdue"])
            messagebox.showerror("Error", f"No se pudo conectar:\n{e}\n\nVerifique que PostgreSQL esté corriendo y la contraseña sea correcta.")

    def _ensure_database_exists(self, engine, db_name):
        """Checks if db_name exists, creates if not."""
        from sqlalchemy.exc import ProgrammingError
        
        # Only works if user has rights
        with engine.connect() as conn:
            # Check existence
            # Note: Cannot use bound parameters easily for Identifiers in generic SQL without quoting logic
            # Safe enough for internal tool
            res = conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'"))
            if not res.scalar():
                # Create it
                # COMMIT is required because CREATE DATABASE cannot run in transaction block
                conn.execute(text("COMMIT")) 
                conn.execute(text(f"CREATE DATABASE {db_name}"))
                conn.execute(text("COMMIT")) # Just to be safe returning to autocommit mode

    def save_connection(self):
        if self.connection_url:
            save_last_db_path(self.connection_url)
            messagebox.showinfo("Guardado", "Configuración guardada.\nLa aplicación se reiniciará para conectar al servidor.")
            if self.on_success_callback:
                self.on_success_callback(self.connection_url)
            self.destroy()
