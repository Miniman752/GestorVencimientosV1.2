
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
from config import COLORS, FONTS, set_cloud_backup_path, set_cloud_checked_flag
from services.cloud_service import CloudService
import os
from datetime import datetime

class CloudWizardDialog(ctk.CTkToplevel):
    def __init__(self, parent, providers):
        super().__init__(parent)
        self.providers = providers
        self.title("Integración de Nube - Control Total")
        self.geometry("600x550")
        self.resizable(False, False)
        self.configure(fg_color=COLORS["main_background"])
        
        # Center window
        self.update_idletasks()
        try:
            x = (self.winfo_screenwidth() - self.winfo_width()) // 2
            y = (self.winfo_screenheight() - self.winfo_height()) // 2
            self.geometry(f"+{x}+{y}")
        except: pass

        # --- Header ---
        self.lbl_title = ctk.CTkLabel(
            self, 
            text="☁️ Detector de Nube", 
            font=("Segoe UI", 22, "bold"),
            text_color=COLORS["text_primary"]
        )
        self.lbl_title.pack(pady=(25, 5))

        # --- Security Trust Card ---
        self.frame_trust = ctk.CTkFrame(self, fg_color="#D6EAF8", corner_radius=10) # Light blue trust color
        self.frame_trust.pack(pady=(10, 5), padx=30, fill="x")
        
        self.lbl_trust_title = ctk.CTkLabel(
            self.frame_trust, 
            text="🔒 ¿Por qué es seguro?", 
            font=("Segoe UI", 12, "bold"), 
            text_color="#21618C"
        )
        self.lbl_trust_title.pack(pady=(10, 0))
        
        self.lbl_trust_desc = ctk.CTkLabel(
            self.frame_trust,
            text=("Este sistema usa tu carpeta local ya sincronizada.\n"
                  "NO necesitamos tu contraseña ni accesos extra.\n"
                  "Tú tienes el control total."),
            font=("Segoe UI", 11),
            text_color="#2E86C1",
            justify="center"
        )
        self.lbl_trust_desc.pack(pady=(5, 10))

        # --- Detection & Selection ---
        self.lbl_instruction = ctk.CTkLabel(
            self, 
            text="Hemos detectado estas carpetas. Selecciona una o elige manualmente:",
            text_color="gray",
            font=FONTS["body"]
        )
        self.lbl_instruction.pack(pady=(15, 5))

        self.frame_options = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_options.pack(pady=5, fill="x", padx=40)
        
        self.selected_path = tk.StringVar(value=None)
        
        # Detected Providers List
        for p in providers:
            rad = ctk.CTkRadioButton(
                self.frame_options,
                text=f"Usar {p['name']} ({p['path']})",
                value=p['path'],
                variable=self.selected_path,
                font=("Segoe UI", 12, "bold"),
                text_color=COLORS["text_primary"],
                fg_color=COLORS["primary_button"],
                hover_color=COLORS["primary_button_hover"]
            )
            rad.pack(pady=5, anchor="w")
            
        # Manual Option Button
        self.btn_manual = ctk.CTkButton(
            self.frame_options,
            text="📂 Elegir otra carpeta manualmente...",
            font=("Segoe UI", 11),
            fg_color="transparent",
            border_width=1,
            border_color="gray",
            text_color=COLORS["text_primary"],
            hover_color="#EAEDED",
            command=self.on_manual_select
        )
        self.btn_manual.pack(pady=10, anchor="w", fill="x")

        # --- Trust Verification Test ---
        self.btn_test = ctk.CTkButton(
            self,
            text="🧪 Probar Sincronización",
            font=("Segoe UI", 12),
            fg_color="#F39C12", # Orange for 'Test'
            hover_color="#D68910",
            text_color="white",
            height=32,
            command=self.on_test_sync
        )
        self.btn_test.pack(pady=(5, 20))

        # --- Actions ---
        self.btn_confirm = ctk.CTkButton(
            self,
            text="✅ Confirmar y Conectar",
            font=("Segoe UI", 13, "bold"),
            fg_color=COLORS["status_paid"],
            hover_color="#229954",
            height=45,
            command=self.on_confirm
        )
        self.btn_confirm.pack(pady=(0, 10), fill="x", padx=60)
        
        self.btn_skip = ctk.CTkButton(
            self,
            text="Cancelar (Seguiré usando solo Local)",
            font=("Segoe UI", 11),
            fg_color="transparent",
            text_color="gray",
            hover_color="#E5E7E9",
            command=self.on_skip
        )
        self.btn_skip.pack(pady=5)
        
        # Make modal
        self.transient(parent)
        self.grab_set()

    def on_manual_select(self):
        path = filedialog.askdirectory(title="Seleccionar Carpeta de Nube")
        if path:
            self.selected_path.set(path)
            tk.messagebox.showinfo("Selección Manual", f"Has seleccionado:\n{path}\n\nMarca la opción en la lista si deseas confirmar.")
            # Hack: Add a temporary radio button or just force confirmation? 
            # Better: Just update the UI label or assume selection.
            # For simplicity in this wizard, let's auto-confirm or just update a label?
            # Let's show it in a label next to the button
            self.btn_manual.configure(text=f"📂 Seleccionado: {path}")

    def on_test_sync(self):
        path = self.selected_path.get()
        if not path:
            tk.messagebox.showwarning("Atención", "Primero selecciona una carpeta de la lista o elige una manualmente.")
            return
            
        try:
            test_file = os.path.join(path, "test_sigv.txt")
            with open(test_file, "w") as f:
                f.write(f"Prueba de Sincronizacion SIGV\nFecha: {datetime.now()}\nEstado: OK")
            
            tk.messagebox.showinfo(
                "Prueba Exitosa", 
                f"Hemos creado el archivo 'test_sigv.txt' en:\n{path}\n\n"
                "Revisa tu celular o la web de tu proveedor de nube. "
                "Si ves el archivo, ¡la sincronización funciona!"
            )
        except Exception as e:
            tk.messagebox.showerror("Error de Prueba", f"No pudimos escribir en la carpeta.\nDetalle: {e}")

    def on_confirm(self):
        path = self.selected_path.get()
        if path:
            set_cloud_backup_path(path)
            set_cloud_checked_flag(True)
            tk.messagebox.showinfo("Configurado", "¡Excelente! Tus datos ahora están doblemente protegidos.")
            self.destroy()
        else:
            tk.messagebox.showwarning("Selección", "Por favor selecciona un servicio o elige una carpeta manualmente.")

    def on_skip(self):
        set_cloud_checked_flag(True) # Don't ask again
        self.destroy()


