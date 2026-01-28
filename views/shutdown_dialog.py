import customtkinter as ctk
from config import COLORS, FONTS

class ShutdownDialog(ctk.CTkToplevel):
    def __init__(self, parent, has_cloud_config=False):
        super().__init__(parent)
        
        self.title("Confirmar Salida")
        self.geometry("400x320")
        self.resizable(False, False)
        
        # Modal
        self.transient(parent)
        self.grab_set()
        
        self.result = "CANCEL" # Default
        
        # Color Scheme
        self.configure(fg_color="#FFFFFF") # Clean white
        
        # Header
        header = ctk.CTkFrame(self, height=50, fg_color=COLORS["primary_button"], corner_radius=0)
        header.pack(fill="x")
        
        ctk.CTkLabel(header, text="¿Desea salir del sistema?", font=("Segoe UI", 16, "bold"), text_color="white").pack(pady=10)
        
        # Body
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=20, pady=15)
        
        ctk.CTkLabel(body, text="Seleccione una opción de respaldo:", font=FONTS["body"], text_color="gray30").pack(pady=(0, 15))
        
        # Options
        
        # 1. Full Backup (Only if Cloud Configured)
        if has_cloud_config:
            self.btn_full = ctk.CTkButton(
                body, 
                text="☁️  Respaldo Completo\n(Local + Nube)", 
                font=("Segoe UI", 12, "bold"),
                fg_color=COLORS["status_paid"], # Green-ish
                hover_color="#27AE60",
                height=50,
                command=lambda: self.finish("FULL")
            )
            self.btn_full.pack(fill="x", pady=5)
            
        # 2. Local Only
        self.btn_local = ctk.CTkButton(
            body, 
            text="💾  Sólo Respaldo Local\n(Rápido)", 
            font=("Segoe UI", 12),
            fg_color=COLORS["secondary_button"], 
            height=40,
            command=lambda: self.finish("LOCAL")
        )
        self.btn_local.pack(fill="x", pady=5)
        
        # 3. Exit No Backup
        self.btn_exit = ctk.CTkButton(
            body, 
            text="🚪  Salir sin Respaldar", 
            font=("Segoe UI", 12),
            fg_color="transparent",
            text_color="#C0392B",
            hover_color="#FDEDEC",
            border_width=1,
            border_color="#C0392B",
            height=30,
            command=lambda: self.finish("NONE")
        )
        self.btn_exit.pack(fill="x", pady=(15, 5))
        
        # Footer (Cancel)
        ctk.CTkButton(
            self, 
            text="Cancelar", 
            fg_color="transparent", 
            text_color="gray", 
            width=100,
            command=self.destroy
        ).pack(side="bottom", pady=10)
        
        # Center
        self.center_window()
        
    def center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')

    def finish(self, value):
        self.result = value
        self.destroy()
