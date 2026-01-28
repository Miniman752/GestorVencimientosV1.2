import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from controllers.credentials_controller import CredentialsController
from controllers.catalogs_controller import CatalogsController
from config import COLORS, FONTS


class CredentialsView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.controller = CredentialsController()
        self.cat_controller = CatalogsController()
        self.configure(fg_color=COLORS["main_background"])
        
        # Grid Layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0) # Header
        self.grid_rowconfigure(1, weight=1) # Content

        # --- Header ---
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        
        ctk.CTkLabel(self.header_frame, text="🔐 Bóveda de Accesos", font=("Segoe UI", 20, "bold")).pack(side="left")
        
        # Filter
        self.filter_var = tk.StringVar(value="Todos")
        self.combo_filter = ctk.CTkComboBox(self.header_frame, variable=self.filter_var, command=self.load_data, width=200)
        self.combo_filter.pack(side="left", padx=20)
        
        ctk.CTkButton(self.header_frame, text="+ Nueva Credencial", command=self.open_add_dialog, fg_color=COLORS["primary_button"]).pack(side="right")

        # --- Content ---
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        
        self.inmuebles_cache = []
        # self.load_combos() # Defer to load_data or first show?
        # Better to try loading, if empty it will be retried in load_data
        self.load_combos()
        self.load_data()

    def load_combos(self):
        self.inmuebles_cache = self.cat_controller.get_inmuebles()
        values = ["Todos"] + [i.alias for i in self.inmuebles_cache]
        self.combo_filter.configure(values=values)

    def load_data(self, _=None):
        # Refresh combos just in case db was empty on init
        if not self.inmuebles_cache:
            self.load_combos()

        # Clear
        for w in self.scroll_frame.winfo_children(): w.destroy()
        
        filter_alias = self.filter_var.get()
        inmueble_id = None
        if filter_alias != "Todos":
            inmuebles = self.cat_controller.get_inmuebles()
            found = next((i for i in inmuebles if i.alias == filter_alias), None)
            if found: inmueble_id = found.id
            
        creds = self.controller.get_credentials(inmueble_id)
        
        if not creds:
             ctk.CTkLabel(self.scroll_frame, text="No hay credenciales registradas.", text_color="gray").pack(pady=20)
             return

        # Render Rows
        for item in creds:
            self._render_row(item)

    def _render_row(self, item):
        card = ctk.CTkFrame(self.scroll_frame, fg_color="white", corner_radius=10)
        card.pack(fill="x", pady=5, padx=5)
        
        # Layout: Inmueble | Web/Usuario | Actions
        
        # Left: Identity
        info_frame = ctk.CTkFrame(card, fg_color="transparent")
        info_frame.pack(side="left", padx=15, pady=10, fill="x", expand=True)
        
        inm_name = item.inmueble.alias if item.inmueble else "N/A"
        prov_name = f" - {item.proveedor.nombre_entidad}" if item.proveedor else ""
        title = f"{inm_name}{prov_name}"
        
        ctk.CTkLabel(info_frame, text=title, font=("Segoe UI", 12, "bold"), text_color="#2C3E50", anchor="w").pack(fill="x")
        
        details = f"Usuario: {item.usuario or '---'} | Web: {item.sitio_web or '---'}"
        ctk.CTkLabel(info_frame, text=details, font=("Segoe UI", 11), text_color="gray", anchor="w").pack(fill="x")
        
        # Actions Frame
        act_frame = ctk.CTkFrame(card, fg_color="transparent")
        act_frame.pack(side="right", padx=15)
        
        # Buttons
        # Copy User
        if item.usuario:
             ctk.CTkButton(act_frame, text="Copiar Usuario", width=80, height=25, fg_color="#EAEDED", text_color="black",
                           command=lambda: self.copy_to_clipboard(item.usuario)).pack(side="left", padx=2)
        
        # View Pass
        ctk.CTkButton(act_frame, text="👁️ Ver Clave", width=80, height=25, fg_color=COLORS["secondary_button"], 
                      command=lambda: self.show_password(item)).pack(side="left", padx=2)

        # Edit/Delete
        ctk.CTkButton(act_frame, text="✎", width=30, height=25, command=lambda: self.open_edit_dialog(item)).pack(side="left", padx=2)
        ctk.CTkButton(act_frame, text="✖", width=30, height=25, fg_color=COLORS["status_overdue"], command=lambda: self.delete_item(item)).pack(side="left", padx=2)

    def copy_to_clipboard(self, text):
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update() # Required for clipboard
        messagebox.showinfo("Copiado", "Texto copiado al portapapeles.", parent=self)

    def show_password(self, item):
        decrypted = self.controller.decrypt_password(item.id)
        if not decrypted:
            messagebox.showwarning("Vacío", "No hay contraseña guardada.")
            return
            
        # Custom Dialog to show and copy
        dlg = ctk.CTkToplevel(self)
        dlg.title("Contraseña Segura")
        dlg.geometry("300x150")
        dlg.attributes("-topmost", True)
        
        ctk.CTkLabel(dlg, text="Contraseña:", font=("Segoe UI", 12, "bold")).pack(pady=(20, 5))
        
        entry = ctk.CTkEntry(dlg, justify="center")
        entry.insert(0, decrypted)
        entry.configure(state="readonly")
        entry.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkButton(dlg, text="Copiar y Cerrar", command=lambda: [self.copy_to_clipboard(decrypted), dlg.destroy()]).pack(pady=10)

    def open_add_dialog(self):
        DialogCredentialForm(self)
        
    def open_edit_dialog(self, item):
        DialogCredentialForm(self, item)

    def delete_item(self, item):
        if messagebox.askyesno("Confirmar", "¿Eliminar esta credencial?"):
            self.controller.delete_credential(cred_id=item.id)
            self.load_data()

class DialogCredentialForm(ctk.CTkToplevel):
    def __init__(self, parent_view, cred=None):
        super().__init__()
        self.parent = parent_view
        self.cred = cred
        self.controller = CredentialsController()
        
        self.title("Editar Credencial" if cred else "Nueva Credencial")
        self.geometry("400x550")
        
        # UI Focus Fix
        self.lift()
        self.focus_force()
        self.attributes("-topmost", True)
        
        ctk.CTkLabel(self, text="Datos de Acceso", font=("Segoe UI", 16, "bold")).pack(pady=15)
        
        # Inmueble (Combo)
        ctk.CTkLabel(self, text="Inmueble *", anchor="w").pack(fill="x", padx=20)
        self.inmuebles = CatalogsController().get_inmuebles()
        self.combo_inm = ctk.CTkComboBox(self, values=[i.alias for i in self.inmuebles])
        self.combo_inm.pack(fill="x", padx=20, pady=5)

        # Proveedor (Combo Optional)
        ctk.CTkLabel(self, text="Proveedor (Opcional)", anchor="w").pack(fill="x", padx=20)
        self.proveedores = CatalogsController().get_proveedores()
        self.combo_prov = ctk.CTkComboBox(self, values=[""] + [p.nombre_entidad for p in self.proveedores])
        self.combo_prov.pack(fill="x", padx=20, pady=5)
        
        # Web
        self.entry_web = ctk.CTkEntry(self, placeholder_text="Sitio Web (URL)")
        self.entry_web.pack(fill="x", padx=20, pady=(15, 5))

        # User
        self.entry_user = ctk.CTkEntry(self, placeholder_text="Usuario / Email / CUIT")
        self.entry_user.pack(fill="x", padx=20, pady=5)

        # Pass
        self.entry_pass = ctk.CTkEntry(self, placeholder_text="Contraseña", show="*")
        self.entry_pass.pack(fill="x", padx=20, pady=5)
        
        # Notes
        self.entry_notes = ctk.CTkTextbox(self, height=80)
        self.entry_notes.insert("0.0", "Notas...")
        self.entry_notes.pack(fill="x", padx=20, pady=10)

        ctk.CTkButton(self, text="Guardar", command=self.save).pack(pady=20)

        if cred: self.load_fields()

    def load_fields(self):
        if self.cred.inmueble: self.combo_inm.set(self.cred.inmueble.alias)
        if self.cred.proveedor: self.combo_prov.set(self.cred.proveedor.nombre_entidad)
        else: self.combo_prov.set("")
        
        if self.cred.sitio_web: self.entry_web.insert(0, self.cred.sitio_web)
        if self.cred.usuario: self.entry_user.insert(0, self.cred.usuario)
        
        # Don't show password by default, only overwrite if typed.
        self.entry_pass.configure(placeholder_text="Dejar vacío para mantener")
        
        if self.cred.notas: 
            self.entry_notes.delete("0.0", "end")
            self.entry_notes.insert("0.0", self.cred.notas)

    def save(self):
        # Resolve IDs
        inm_alias = self.combo_inm.get()
        inm = next((i for i in self.inmuebles if i.alias == inm_alias), None)
        if not inm: return messagebox.showerror("Error", "Seleccione un inmueble válido", parent=self)
        
        prov_name = self.combo_prov.get()
        prov = next((p for p in self.proveedores if p.nombre_entidad == prov_name), None)
        
        web = self.entry_web.get().strip()
        user = self.entry_user.get().strip()
        pasw = self.entry_pass.get().strip()
        notes = self.entry_notes.get("0.0", "end").strip()
        
        try:
            if self.cred:
                # Update
                # Only update pass if provided
                kwargs = {
                    "inmueble_id": inm.id,
                    "proveedor_id": prov.id if prov else None,
                    "sitio_web": web,
                    "usuario": user,
                    "notas": notes
                }
                if pasw: kwargs["password_plain"] = pasw
                
                self.controller.update_credential(cred_id=self.cred.id, **kwargs)
                messagebox.showinfo("Éxito", "Actualizado correctamente", parent=self)
            else:
                # Create
                self.controller.create_credential(
                    session=None, # injected
                    inmueble_id=inm.id,
                    usuario=user,
                    password_plain=pasw,
                    sitio_web=web,
                    proveedor_id=prov.id if prov else None,
                    notas=notes
                )
                messagebox.showinfo("Éxito", "Guardado correctamente", parent=self)
            
            self.parent.load_data()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)
