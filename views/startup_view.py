
import customtkinter as ctk
from config import COLORS, FONTS
import os

class StartupDialog(ctk.CTkToplevel):
    def __init__(self, parent, on_new_db, on_open_db, last_db_path=None):
        super().__init__(parent)
        self.parent = parent
        self.on_new_db = on_new_db
        self.on_open_db = on_open_db
        
        self.title("Bienvenido - SIGV-Pro")
        self.geometry("500x400")
        self.resizable(False, False)
        
        # Center window
        self.update_idletasks()
        width = 500
        height = 400
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        
        self.configure(fg_color=COLORS["main_background"])
        
        # Make modal
        self.transient(parent)
        self.grab_set()
        
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self._init_ui(last_db_path)
        
    def _init_ui(self, last_db_path):
        # Logo / Header
        header_frame = ctk.CTkFrame(self, fg_color=COLORS["sidebar_background"], corner_radius=0, height=80)
        header_frame.pack(fill="x")
        
        ctk.CTkLabel(
            header_frame, 
            text="Gestor de Vencimientos", 
            font=FONTS["heading"], 
            text_color=COLORS["content_surface"]
        ).place(relx=0.5, rely=0.5, anchor="center")
        
        # Content
        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=40, pady=40)
        
        ctk.CTkLabel(
            content_frame, 
            text="Seleccione un origen de datos para comenzar:",
            font=FONTS["body"],
            text_color=COLORS["text_primary"]
        ).pack(pady=(0, 20))
        
        # Determine if we have a valid history
        # Allow Postgres URL or Existing File
        is_postgres = last_db_path and last_db_path.startswith("postgresql")
        has_recent = is_postgres or (last_db_path and last_db_path.lower() != "none" and os.path.exists(last_db_path))
        
        if has_recent:
            if is_postgres:
                db_name = "PostgreSQL Server 🐘"
            else:
                db_name = os.path.basename(last_db_path)
                
            # 1. Primary Action: Continue
            ctk.CTkButton(
                content_frame,
                text=f"📂  Continuar con: {db_name}",
                font=("Segoe UI", 13, "bold"),
                height=50,
                fg_color=COLORS["primary_button"],
                hover_color=COLORS["primary_button_hover"],
                command=lambda: self.on_open_db(last_db_path)
            ).pack(fill="x", pady=10)
            
            # 2. Secondary
            ctk.CTkButton(
                content_frame,
                text="📂  Abrir Otra Base de Datos...",
                font=("Segoe UI", 12),
                height=40,
                fg_color=COLORS["secondary_button"],
                command=self.on_open_db
            ).pack(fill="x", pady=5)
            
            # 3. New
            ctk.CTkButton(
                content_frame,
                text="🆕  Crear Nueva...",
                font=("Segoe UI", 12),
                height=40,
                fg_color="transparent",
                border_width=1,
                border_color=COLORS["secondary_button"],
                text_color=COLORS["text_primary"],
                command=self.on_new_db
            ).pack(fill="x", pady=5)
            
        else:
            # Standard View
            ctk.CTkButton(
                content_frame,
                text="📂  Abrir Base de Datos Existente",
                font=("Segoe UI", 13, "bold"),
                height=50,
                fg_color=COLORS["primary_button"],
                hover_color=COLORS["primary_button_hover"],
                command=self.on_open_db
            ).pack(fill="x", pady=10)
            
            ctk.CTkButton(
                content_frame,
                text="🆕  Crear Nueva Base de Datos",
                font=("Segoe UI", 13, "bold"),
                height=50,
                fg_color=COLORS["secondary_button"],
                hover_color="gray", 
                command=self.on_new_db
            ).pack(fill="x", pady=10)

    def on_close(self):
        # Prevent closing without selection? 
        # Or just exit app?
        # User confirmed they want safe operation. Let's quit app if they don't pick.
        self.parent.quit()

