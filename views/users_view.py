
import customtkinter as ctk
from tkinter import messagebox, ttk
from services.auth_service import AuthService
from models.entities import RolUsuario

class UsersView(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.parent = parent
        self.auth_service = AuthService()
        
        # Header
        self.header = ctk.CTkFrame(self, height=60, fg_color="transparent")
        self.header.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(self.header, text="Gestión de Usuarios", font=("Segoe UI", 24, "bold"), text_color="#34495E").pack(side="left")
        
        # Toolbar
        self.toolbar = ctk.CTkFrame(self, height=50, fg_color="transparent")
        self.toolbar.pack(fill="x", padx=20, pady=(0, 10))
        
        ctk.CTkButton(self.toolbar, text="+ Nuevo Usuario", fg_color="#2ECC71", hover_color="#27AE60", width=120, command=self.open_create_dialog).pack(side="left", padx=(0, 10))
        ctk.CTkButton(self.toolbar, text="🔄 Recargar", fg_color="gray", width=100, command=self.load_users).pack(side="left")

        # Table Frame
        self.table_frame = ctk.CTkFrame(self, fg_color="white", corner_radius=10)
        self.table_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Treeview
        columns = ("id", "username", "nombre", "rol", "activo", "ultimo_login")
        self.tree = ttk.Treeview(self.table_frame, columns=columns, show="headings", height=15)
        
        self.tree.heading("id", text="ID")
        self.tree.heading("username", text="Usuario")
        self.tree.heading("nombre", text="Nombre Completo")
        self.tree.heading("rol", text="Rol")
        self.tree.heading("activo", text="Estado")
        self.tree.heading("ultimo_login", text="Último Acceso")
        
        self.tree.column("id", width=50, anchor="center")
        self.tree.column("username", width=150)
        self.tree.column("nombre", width=200)
        self.tree.column("rol", width=100)
        self.tree.column("activo", width=80, anchor="center")
        self.tree.column("ultimo_login", width=120)
        
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Context Menu
        # Context Menu & Edit
        self.tree.bind("<Button-3>", self.show_context_menu)
        self.tree.bind("<Double-1>", self.open_edit_dialog)
        
        self.load_users()

    def load_users(self):
        # Clear
        for i in self.tree.get_children(): self.tree.delete(i)
        
        users = self.auth_service.list_users()
        for u in users:
            status = "Activo" if u.is_active else "Inactivo"
            # last_login = u.last_login.strftime("%d/%m/%Y") if u.last_login else "-"
            rol_name = u.rol.value if hasattr(u.rol, 'value') else str(u.rol)
            
            self.tree.insert("", "end", values=(u.id, u.username, u.nombre_completo, rol_name, status, "-"))

    def open_create_dialog(self):
        DialogUserForm(self)

    def open_edit_dialog(self, event):
        item_id = self.tree.identify_row(event.y)
        if not item_id: return
        
        # Get ID from tree values
        # values = (id, username, ...)
        values = self.tree.item(item_id)['values']
        user_id = values[0]
        
        user_obj = self.auth_service.get_user(user_id)
        if user_obj:
            DialogUserForm(self, user_obj)

    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if not item: return
        self.tree.selection_set(item)
        
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Cambiar Contraseña...", command=self.action_change_pass)
        menu.add_command(label="Eliminar Usuario", command=self.action_delete)
        menu.post(event.x_root, event.y_root)

    def action_delete(self):
        sel = self.tree.selection()
        if not sel: return
        item = self.tree.item(sel[0])
        uid, uname = item['values'][0], item['values'][1]
        
        if uname == "admin":
            messagebox.showwarning("Acción Prohibida", "No se puede eliminar al administrador principal.")
            return

        if messagebox.askyesno("Confirmar", f"¿Eliminar usuario '{uname}'?"):
            self.auth_service.delete_user(user_id=uid)
            self.load_users()

    def action_change_pass(self):
        sel = self.tree.selection()
        if not sel: return
        uid = self.tree.item(sel[0])['values'][0]
        
        new_pass = ctk.CTkInputDialog(text="Nueva Contraseña:", title="Resetear Password").get_input()
        if new_pass:
            self.auth_service.change_password(user_id=uid, new_password=new_pass)
            messagebox.showinfo("Éxito", "Contraseña actualizada.")

import tkinter as tk
class DialogUserForm(ctk.CTkToplevel):
    def __init__(self, parent_view, user_to_edit=None):
        super().__init__()
        self.parent = parent_view
        self.user_to_edit = user_to_edit
        self.title("Editar Usuario" if user_to_edit else "Nuevo Usuario")
        self.geometry("350x500")
        self.resizable(False, False)
        
        # UI Focus Fix
        self.lift()
        self.focus_force()
        self.attributes("-topmost", True)
        
        title_text = f"Editar: {user_to_edit.username}" if user_to_edit else "Crear Usuario"
        ctk.CTkLabel(self, text=title_text, font=("Segoe UI", 18, "bold")).pack(pady=20)
        
        # Username
        self.entry_user = ctk.CTkEntry(self, placeholder_text="Usuario (Login)")
        self.entry_user.pack(fill="x", padx=20, pady=10)
        if user_to_edit:
            self.entry_user.insert(0, user_to_edit.username)
            self.entry_user.configure(state="disabled") # Username immutable
        
        # Full Name
        self.entry_name = ctk.CTkEntry(self, placeholder_text="Nombre Completo")
        self.entry_name.pack(fill="x", padx=20, pady=10)
        if user_to_edit and user_to_edit.nombre_completo:
            self.entry_name.insert(0, user_to_edit.nombre_completo)

        # Password
        pass_placeholder = "Dejar vacío para mantener actual" if user_to_edit else "Contraseña"
        
        if user_to_edit:
             ctk.CTkLabel(self, text="⚠️ Clave encriptada (No visible)", font=("Segoe UI", 10), text_color="gray").pack(anchor="w", padx=20, pady=(10,0))

        self.entry_pass = ctk.CTkEntry(self, placeholder_text=pass_placeholder, show="*")
        self.entry_pass.pack(fill="x", padx=20, pady=(5 if user_to_edit else 10, 5))
        
        # Show Password Toggle
        self.chk_show_pass = ctk.CTkCheckBox(self, text="Mostrar contraseña", 
                                             font=("Segoe UI", 11), 
                                             height=20, corner_radius=0, 
                                             command=self.toggle_password)
        self.chk_show_pass.pack(fill="x", padx=25, pady=(0, 10))
        
        # Role
        ctk.CTkLabel(self, text="Rol:", anchor="w").pack(fill="x", padx=25)
        self.combo_role = ctk.CTkComboBox(self, values=[r.value for r in RolUsuario])
        self.combo_role.pack(fill="x", padx=20, pady=5)
        
        if user_to_edit:
            current_role_val = user_to_edit.rol.value if hasattr(user_to_edit.rol, 'value') else str(user_to_edit.rol)
            self.combo_role.set(current_role_val)
        else:
            self.combo_role.set(RolUsuario.OPERADOR.value)
        
        ctk.CTkButton(self, text="Guardar Cambios" if user_to_edit else "Crear Usuario", command=self.save).pack(pady=30)
        
    def toggle_password(self):
        if self.chk_show_pass.get():
            self.entry_pass.configure(show="")
        else:
            self.entry_pass.configure(show="*")
        
    def save(self):
        u = self.entry_user.get().strip()
        p = self.entry_pass.get().strip()
        n = self.entry_name.get().strip()
        r_str = self.combo_role.get()
        
        # Validation
        if not self.user_to_edit:
            if not u or not p:
                messagebox.showerror("Error", "Usuario y Contraseña requeridos", parent=self)
                return
        
        # Map Role
        role_enum = next((r for r in RolUsuario if r.value == r_str), RolUsuario.OPERADOR)
        
        try:
            if self.user_to_edit:
                # Update Mode - Use Keyword Args
                AuthService.update_user(user_id=self.user_to_edit.id, nombre=n, role=role_enum)
                if p: # Only update pass if provided
                    AuthService.change_password(user_id=self.user_to_edit.id, new_password=p)
                msg = "Usuario actualizado."
            else:
                # Create Mode
                AuthService.create_user(username=u, password=p, role=role_enum, nombre=n)
                msg = "Usuario creado."
                
            self.parent.load_users()
            self.destroy()
            messagebox.showinfo("Éxito", msg)
            
        except ValueError as e:
            messagebox.showerror("Error", str(e), parent=self)
        except Exception as e:
            messagebox.showerror("Error", f"Error de base de datos: {e}", parent=self)
