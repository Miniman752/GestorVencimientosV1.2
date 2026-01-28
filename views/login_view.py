
import customtkinter as ctk
from PIL import Image
import os
from services.auth_service import AuthService

class LoginView(ctk.CTkToplevel):
    def __init__(self, master=None):
        super().__init__(master)
        
        self.title("Iniciar Sesión - Gestor de Vencimientos")
        self.geometry("400x500")
        
        # Center the window
        # Use master to center if available, else screen
        if master:
            x = master.winfo_x() + (master.winfo_width() // 2) - 200
            y = master.winfo_y() + (master.winfo_height() // 2) - 250
            if x < 0: x = 0
            if y < 0: y = 0
        else:
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            x = (screen_width - 400) // 2
            y = (screen_height - 500) // 2
        
        self.geometry(f"400x500+{x}+{y}")
        
        self.resizable(False, False)
        
        self.authenticated_user = None # Result storage
        
        self._build_ui()
        
        # Bind Enter key
        self.bind('<Return>', lambda event: self._login())

    def _build_ui(self):
        # Header / Logo Area
        self.header_frame = ctk.CTkFrame(self, height=150, corner_radius=0, fg_color="transparent")
        self.header_frame.pack(fill="x", pady=(40, 20))
        
        ctk.CTkLabel(self.header_frame, text="🔐", font=("Segoe UI", 48)).pack()
        ctk.CTkLabel(self.header_frame, text="Bienvenido", font=("Segoe UI", 24, "bold")).pack(pady=5)
        ctk.CTkLabel(self.header_frame, text="Inicie sesión para continuar", font=("Segoe UI", 12), text_color="gray").pack()

        # Input Frame
        self.input_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.input_frame.pack(fill="both", expand=True, padx=40)
        
        # Username
        ctk.CTkLabel(self.input_frame, text="Usuario", anchor="w").pack(fill="x", pady=(10, 0))
        self.entry_user = ctk.CTkEntry(self.input_frame, height=40, placeholder_text="Ingrese su usuario")
        self.entry_user.pack(fill="x", pady=(5, 15))
        
        # Password
        ctk.CTkLabel(self.input_frame, text="Contraseña", anchor="w").pack(fill="x")
        self.entry_pass = ctk.CTkEntry(self.input_frame, height=40, placeholder_text="Ingrese su contraseña", show="*")
        self.entry_pass.pack(fill="x", pady=(5, 5))
        
        self.chk_show_pass = ctk.CTkCheckBox(self.input_frame, text="Mostrar contraseña", 
                                             font=("Segoe UI", 11), 
                                             height=20, corner_radius=0, 
                                             command=self.toggle_password)
        self.chk_show_pass.pack(fill="x", pady=(0, 5))
        
        # Error Label (Hidden initially)
        self.lbl_error = ctk.CTkLabel(self.input_frame, text="", text_color="#E74C3C", font=("Segoe UI", 11))
        self.lbl_error.pack(pady=(5, 5))
        
        # Button
        self.btn_login = ctk.CTkButton(self.input_frame, text="INGRESAR", height=45, font=("Segoe UI", 13, "bold"),
                                       fg_color="#3498DB", hover_color="#2980B9",
                                       command=self._login)
        self.btn_login.pack(fill="x", pady=20)
        
        # Version
        ctk.CTkLabel(self, text="v2.5 Enterprise", font=("Segoe UI", 10), text_color="gray").pack(side="bottom", pady=10)
        
        # Focus
        self.entry_user.focus()

    def toggle_password(self):
        if self.chk_show_pass.get():
            self.entry_pass.configure(show="")
        else:
            self.entry_pass.configure(show="*")

    def _login(self):
        u = self.entry_user.get().strip()
        p = self.entry_pass.get().strip()
        
        if not u or not p:
            self.lbl_error.configure(text="Complete todos los campos")
            return
            
        self.btn_login.configure(state="disabled", text="Verificando...")
        self.update()
        
        user = AuthService.login(u, p)
        
        if user:
            self.authenticated_user = user
            # We don't destroy here, we let the caller (MainWindow) handle the transition
            # or we destroy if we are done.
            # But wait, we need to block. 
            # If we destroy, wait_window returns.
            self.destroy()
        else:
            self.lbl_error.configure(text="Usuario o contraseña incorrectos")
            self.btn_login.configure(state="normal", text="INGRESAR")
            self.entry_pass.delete(0, 'end')
