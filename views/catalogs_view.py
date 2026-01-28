import customtkinter as ctk
from tkinter import messagebox
from utils.gui_helpers import center_window
from controllers.catalogs_controller import CatalogsController
from models.entities import EstadoInmueble, CategoriaServicio, TipoAjuste, Obligacion
from config import COLORS
from utils.exceptions import AppValidationError
from services.cognitive_service import CognitiveService
from database import SessionLocal
from services.permission_service import PermissionService

class CatalogsView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.configure(fg_color=COLORS["main_background"])
        
        self.controller = CatalogsController()

        # Tabs
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=20)
        
        self.tabview.configure(fg_color=COLORS["content_surface"])
        self.tabview._segmented_button.configure(selected_color=COLORS["primary_button"], selected_hover_color=COLORS["primary_button_hover"])

        self.tab_inmuebles = self.tabview.add("Inmuebles")
        self.tab_proveedores = self.tabview.add("Proveedores")

        # Sort State
        self.inm_sort_col = "alias"
        self.inm_sort_desc = False
        self.inm_header_widgets = {}

        self.prov_sort_col = "nombre_entidad"
        self.prov_sort_desc = False
        self.prov_header_widgets = {}

        self.setup_inmuebles_tab()
        self.setup_proveedores_tab()

    # --- INMUEBLES ---
    def setup_inmuebles_tab(self):
        # 1. Toolbar (Row 0)
        tool_frame = ctk.CTkFrame(self.tab_inmuebles, fg_color="transparent")
        tool_frame.pack(fill="x", padx=10, pady=10)
        
        # Search
        self.entry_search_inm = ctk.CTkEntry(tool_frame, placeholder_text="🔍 Buscar Inmueble...", width=300, height=35)
        self.entry_search_inm.pack(side="left", padx=5)
        self.entry_search_inm.bind("<KeyRelease>", lambda e: self.load_inmuebles())
        
        # Inactive Toggle
        self.chk_inactive_inm = ctk.CTkCheckBox(tool_frame, text="Inactivos", command=self.load_inmuebles, height=24)
        self.chk_inactive_inm.pack(side="left", padx=15)

        # New Button
        ctk.CTkButton(tool_frame, text="+ Nuevo", width=100, height=35, 
                     fg_color=COLORS["primary_button"], hover_color=COLORS["primary_button_hover"], 
                     command=self.open_add_inmueble).pack(side="right", padx=5)

        # Refresh Button
        ctk.CTkButton(tool_frame, text="Actualizar", width=80, height=35,
                      fg_color=COLORS.get("secondary_button", "#555555"), 
                      command=self.load_inmuebles).pack(side="right", padx=5)

        # 2. Grid Header (Row 1)
        header_frame = ctk.CTkFrame(self.tab_inmuebles, height=35, fg_color=COLORS["sidebar_background"], corner_radius=6)
        header_frame.pack(fill="x", padx=10, pady=(5,0))
        
        # Columns Config: Alias (40%), Titular (30%), Estado (15%), Acciones (15%)
        # Columns Config: Alias (40%), Titular (30%), Estado (15%), Acciones (15%)
        # Added uniform="cols" for strict alignment
        header_frame.grid_columnconfigure(0, weight=3, uniform="cols") # Alias
        header_frame.grid_columnconfigure(1, weight=2, uniform="cols") # Titular
        header_frame.grid_columnconfigure(2, weight=1, uniform="cols") # Estado
        header_frame.grid_columnconfigure(3, weight=1, uniform="cols") # Acciones
        
        # Text, Field, Column, Anchor
        headers = [
            ("Inmueble / Dirección", "alias", 0, "w"), 
            ("Acciones", None, 3, "center")
        ]
        
        for text, field, col, anchor in headers:
            # Consistent Padding: Left aligned gets (10,0), Center gets 5
            px = (10, 0) if anchor == "w" else 5
            lbl = ctk.CTkLabel(header_frame, text=text, font=("Segoe UI", 12, "bold"), text_color="white", anchor=anchor)
            lbl.grid(row=0, column=col, sticky="ew", padx=px, pady=5)
            
            if field:
                lbl.bind("<Button-1>", lambda e, f=field: self.sort_inmuebles_by(f))
                lbl.configure(cursor="hand2")
                self.inm_header_widgets[field] = (lbl, text)
        
        self._update_inmuebles_arrows()

        # 3. List Area
        self.list_inmuebles = ctk.CTkScrollableFrame(self.tab_inmuebles, label_text="", fg_color="white")
        self.list_inmuebles.pack(fill="both", expand=True, padx=10, pady=5)
        self.list_inmuebles.grid_columnconfigure(0, weight=3, uniform="cols")
        self.list_inmuebles.grid_columnconfigure(1, weight=2, uniform="cols")
        self.list_inmuebles.grid_columnconfigure(2, weight=1, uniform="cols")
        self.list_inmuebles.grid_columnconfigure(3, weight=1, uniform="cols")

    def load_inmuebles(self):
        for w in self.list_inmuebles.winfo_children(): w.destroy()
        
        try:
            show_inactive = self.chk_inactive_inm.get()
            search_txt = self.entry_search_inm.get().lower()
            items = self.controller.get_inmuebles(include_inactive=show_inactive)
            
            # Apply Sort
            if self.inm_sort_col:
                def get_sort_val(x):
                    val = getattr(x, self.inm_sort_col, "")
                    if hasattr(val, 'value'): return val.value # Enum
                    if isinstance(val, str): return val.lower()
                    return val or ""
                
                try:
                    items.sort(key=get_sort_val, reverse=self.inm_sort_desc)
                except Exception:
                    pass # Fallback if sort fails
            
            for i, item in enumerate(items):
                # Safe Search
                alias_clean = (item.alias or "").strip()
                if search_txt and search_txt not in alias_clean.lower(): continue
                    
                # Zebra Striping
                bg_color = "transparent" if i % 2 == 0 else COLORS["main_background"]
                
                row = ctk.CTkFrame(self.list_inmuebles, fg_color=bg_color, corner_radius=6)
                row.pack(fill="x", pady=2)
                
                # Match Header columns weights + Uniform
                row.grid_columnconfigure(0, weight=3, uniform="cols") # Alias
                row.grid_columnconfigure(1, weight=2, uniform="cols") # Titular
                row.grid_columnconfigure(2, weight=1, uniform="cols") # Estado
                row.grid_columnconfigure(3, weight=1, uniform="cols") # Acciones
                
                # Alias & Dir
                dir_clean = (item.direccion or "").strip()
                alias_text = f"{alias_clean}\n{dir_clean}"
                ctk.CTkLabel(row, text=alias_text, text_color=COLORS["text_primary"], anchor="w", justify="left", font=("Segoe UI", 12)).grid(row=0, column=0, sticky="ew", padx=(10, 0), pady=5)

                # Titular Removed
                # titular_clean = (item.titular or "-").strip()
                # ctk.CTkLabel(row, text=titular_clean, text_color="gray", anchor="w", font=("Segoe UI", 12)).grid(row=0, column=1, sticky="ew", padx=(10, 0))

                # Status Removed
                # is_active = (item.estado == EstadoInmueble.ACTIVO)
                # status_color = COLORS["status_paid"] if is_active else "gray"
                # status_text = "ACTIVO" if is_active else "INACTIVO"
                # ctk.CTkLabel(row, text=status_text, text_color=status_color, font=("Segoe UI", 10, "bold")).grid(row=0, column=2, sticky="ew")
                
                # Actions
                action_frame = ctk.CTkFrame(row, fg_color="transparent")
                action_frame.grid(row=0, column=3)
                
                ctk.CTkButton(action_frame, text="✎", width=30, height=30, fg_color=COLORS["primary_button"], command=lambda x=item: self.open_edit_inmueble(x)).pack(side="left", padx=2)
                
                # Undo/Delete button - Logic Simplified due to schema alignment
                ctk.CTkButton(action_frame, text="❌", width=30, height=30, fg_color=COLORS["status_overdue"], command=lambda x=item: self.delete_inmueble(x)).pack(side="left", padx=2)

        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron cargar los inmuebles:\n{e}")


    def open_add_inmueble(self):
        if not PermissionService.user_has_permission(self.master.current_user, PermissionService.CAN_MANAGE_CATALOGS):
             messagebox.showwarning("Acceso Denegado", "No tiene permisos para modificar catálogos (Modo Lectura).")
             return
        AddInmuebleDialog(self)

    def open_edit_inmueble(self, item):
        if not PermissionService.user_has_permission(self.master.current_user, PermissionService.CAN_MANAGE_CATALOGS):
             messagebox.showwarning("Acceso Denegado", "No tiene permisos para modificar catálogos (Modo Lectura).")
             return
        EditInmuebleDialog(self, item)

    def delete_inmueble(self, item):
        if not PermissionService.user_has_permission(self.master.current_user, PermissionService.CAN_MANAGE_CATALOGS):
             messagebox.showwarning("Acceso Denegado", "No tiene permisos para modificar catálogos (Modo Lectura).")
             return
        msg = f"¿ELIMINAR DEFINITIVAMENTE '{item.alias}'?\nEsta acción no se puede deshacer."

        if messagebox.askyesno("Confirmar", msg):
            try:
                if self.controller.delete_inmueble(item.id):
                    self.load_inmuebles()
            except Exception as e:
                messagebox.showerror("Error", f"Fallo al eliminar:\n{e}")

    # --- PROVEEDORES ---
    def setup_proveedores_tab(self):
        # 1. Toolbar
        tool_frame = ctk.CTkFrame(self.tab_proveedores, fg_color="transparent")
        tool_frame.pack(fill="x", padx=10, pady=10)
        
        self.entry_search_prov = ctk.CTkEntry(tool_frame, placeholder_text="🔍 Buscar Proveedor...", width=300, height=35)
        self.entry_search_prov.pack(side="left", padx=5)
        self.entry_search_prov.bind("<KeyRelease>", lambda e: self.load_proveedores())
        
        self.chk_inactive_prov = ctk.CTkCheckBox(tool_frame, text="Inactivos", command=self.load_proveedores, height=24)
        self.chk_inactive_prov.pack(side="left", padx=15)

        # 1. New Button (Rightmost)
        ctk.CTkButton(tool_frame, text="+ Nuevo", width=100, height=35, 
                     fg_color=COLORS["primary_button"], hover_color=COLORS["primary_button_hover"], 
                     command=self.open_add_proveedor).pack(side="right", padx=5)

        # 2. Refresh Button (To the left of New)
        ctk.CTkButton(tool_frame, text="Actualizar", width=80, height=35,
                      fg_color=COLORS.get("secondary_button", "#555555"), 
                      command=self.load_proveedores).pack(side="right", padx=5)

        # 2. Grid Header
        # Add extra right padding to compensate for scrollbar (approx 15-20px)
        header_frame = ctk.CTkFrame(self.tab_proveedores, height=35, fg_color=COLORS["sidebar_background"], corner_radius=6)
        header_frame.pack(fill="x", padx=(10, 25), pady=(5,0))
        
        # Columns: Proveedor (40%), Categoria (20%), Estado (20%), Acciones (20%)
        # Columns: Proveedor (40%), Categoria (20%), Estado (20%), Acciones (20%)
        # Added uniform="cols"
        header_frame.grid_columnconfigure(0, weight=4, uniform="cols") # Proveedor
        header_frame.grid_columnconfigure(1, weight=2, uniform="cols") # Categoria
        header_frame.grid_columnconfigure(2, weight=2, uniform="cols") # Estado
        header_frame.grid_columnconfigure(3, weight=2, uniform="cols") # Acciones

        headers = [
            ("Proveedor / Entidad", "nombre_entidad", 0, "w"), 
            ("Categoría", "categoria", 1, "center"), 
            ("Acciones", None, 3, "center")
        ]
        
        for text, field, col, anchor in headers:
            px = (10, 0) if anchor == "w" else 5
            lbl = ctk.CTkLabel(header_frame, text=text, font=("Segoe UI", 12, "bold"), text_color="white", anchor=anchor)
            lbl.grid(row=0, column=col, sticky="ew", padx=px, pady=5)
            
            if field:
                 lbl.bind("<Button-1>", lambda e, f=field: self.sort_proveedores_by(f))
                 lbl.configure(cursor="hand2")
                 self.prov_header_widgets[field] = (lbl, text)

        self._update_proveedores_arrows()

        self.list_proveedores = ctk.CTkScrollableFrame(self.tab_proveedores, label_text="", fg_color="white")
        self.list_proveedores.pack(fill="both", expand=True, padx=10, pady=5)
        self.list_proveedores.grid_columnconfigure(0, weight=4, uniform="cols")
        self.list_proveedores.grid_columnconfigure(1, weight=2, uniform="cols")
        self.list_proveedores.grid_columnconfigure(2, weight=2, uniform="cols")
        self.list_proveedores.grid_columnconfigure(3, weight=2, uniform="cols")

    def load_proveedores(self):
        for w in self.list_proveedores.winfo_children(): w.destroy()
        
        try:
            show_inactive = self.chk_inactive_prov.get()
            search_txt = self.entry_search_prov.get().lower()
            items = self.controller.get_proveedores(include_inactive=show_inactive)
            
            # Apply Sort
            if self.prov_sort_col:
                def get_sort_val(x):
                    val = getattr(x, self.prov_sort_col, "")
                    if hasattr(val, 'value'): return val.value # Enum
                    if isinstance(val, str): return val.lower()
                    return val or ""
                
                try:
                    items.sort(key=get_sort_val, reverse=self.prov_sort_desc)
                except Exception: 
                    pass
            
            for i, item in enumerate(items):
                # Clean Data
                name_clean = (item.nombre_entidad or "").strip()
                if search_txt and search_txt not in name_clean.lower(): continue
                
                # Zebra Striping
                bg_color = "transparent" if i % 2 == 0 else COLORS["main_background"]
                
                row = ctk.CTkFrame(self.list_proveedores, fg_color=bg_color, corner_radius=6)
                row.pack(fill="x", pady=2)
                
                # Match Weights + Uniform
                row.grid_columnconfigure(0, weight=4, uniform="cols")
                row.grid_columnconfigure(1, weight=2, uniform="cols")
                row.grid_columnconfigure(2, weight=2, uniform="cols")
                row.grid_columnconfigure(3, weight=2, uniform="cols")
                
                # Name
                ctk.CTkLabel(row, text=name_clean, text_color=COLORS["text_primary"], anchor="w", font=("Segoe UI", 12)).grid(row=0, column=0, sticky="ew", padx=(10, 0), pady=5)
                
                # Categoria (Centered now)
                cat_val = item.categoria.value if hasattr(item.categoria, 'value') else str(item.categoria)
                ctk.CTkLabel(row, text=cat_val, text_color="gray", anchor="center", font=("Segoe UI", 12)).grid(row=0, column=1, sticky="ew", padx=5)
                
                # Status Removed
                # is_active = (item.activo == 1)
                # status_color = COLORS["status_paid"] if is_active else "gray"
                # status_text = "ACTIVO" if is_active else "INACTIVO"
                # ctk.CTkLabel(row, text=status_text, text_color=status_color, font=("Segoe UI", 10, "bold"), anchor="center").grid(row=0, column=2, sticky="ew")
                
                # Actions
                action_frame = ctk.CTkFrame(row, fg_color="transparent")
                action_frame.grid(row=0, column=3)
                
                ctk.CTkButton(action_frame, text="✎", width=30, height=30, fg_color=COLORS["primary_button"], command=lambda x=item: self.open_edit_proveedor(x)).pack(side="left", padx=2)
                
                ctk.CTkButton(action_frame, text="❌", width=30, height=30, fg_color=COLORS["status_overdue"], command=lambda x=item: self.delete_proveedor(x)).pack(side="left", padx=2)

        except Exception as e:
            messagebox.showerror("Error", f"Error cargando proveedores:\n{e}")

    def open_add_proveedor(self):
        if not PermissionService.user_has_permission(self.master.current_user, PermissionService.CAN_MANAGE_CATALOGS):
             messagebox.showwarning("Acceso Denegado", "No tiene permisos para modificar catálogos (Modo Lectura).")
             return
        AddProveedorDialog(self)

    def open_edit_proveedor(self, item):
        if not PermissionService.user_has_permission(self.master.current_user, PermissionService.CAN_MANAGE_CATALOGS):
             messagebox.showwarning("Acceso Denegado", "No tiene permisos para modificar catálogos (Modo Lectura).")
             return
        EditProveedorDialog(self, item)

    def delete_proveedor(self, item):
        if not PermissionService.user_has_permission(self.master.current_user, PermissionService.CAN_MANAGE_CATALOGS):
             messagebox.showwarning("Acceso Denegado", "No tiene permisos para modificar catálogos (Modo Lectura).")
             return
        msg = f"¿ELIMINAR DEFINITIVAMENTE '{item.nombre_entidad}'?\nEsta acción no se puede deshacer."

        if messagebox.askyesno("Confirmar", msg):
            try:
                if self.controller.delete_proveedor(item.id):
                    self.load_proveedores()
            except AppValidationError as e:
                messagebox.showwarning("No se puede eliminar", str(e))
            except Exception as e:
                messagebox.showerror("Error", f"Fallo al eliminar:\n{e}")

    def tkraise(self, *args, **kwargs):
        super().tkraise(*args, **kwargs)
        self.load_inmuebles()
        self.load_proveedores()

    # --- Sorting Logic ---
    def sort_inmuebles_by(self, field):
        if self.inm_sort_col == field:
            self.inm_sort_desc = not self.inm_sort_desc
        else:
            self.inm_sort_col = field
            self.inm_sort_desc = False
        self._update_inmuebles_arrows()
        self.load_inmuebles()

    def _update_inmuebles_arrows(self):
        for field, (lbl, text) in self.inm_header_widgets.items():
            if field == self.inm_sort_col:
                arrow = " ▼" if not self.inm_sort_desc else " ▲"
                lbl.configure(text=f"{text}{arrow}")
            else:
                lbl.configure(text=text)

    def sort_proveedores_by(self, field):
        if self.prov_sort_col == field:
            self.prov_sort_desc = not self.prov_sort_desc
        else:
            self.prov_sort_col = field
            self.prov_sort_desc = False
        self._update_proveedores_arrows()
        self.load_proveedores()

    def _update_proveedores_arrows(self):
        for field, (lbl, text) in self.prov_header_widgets.items():
            if field == self.prov_sort_col:
                arrow = " ▼" if not self.prov_sort_desc else " ▲"
                lbl.configure(text=f"{text}{arrow}")
            else:
                lbl.configure(text=text)

class AddInmuebleDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Nuevo Inmueble")
        self.parent = parent
        
        # Determine size logic: Auto but with min-size
        self.minsize(350, 320)
        
        # Main Container with padding
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Header
        ctk.CTkLabel(main_frame, text="Registrar Inmueble", font=("Segoe UI", 16, "bold"), text_color=COLORS["text_primary"]).pack(pady=(0, 15))
        
        # Fields
        ctk.CTkLabel(main_frame, text="Alias (Ej. Casa Centro)", anchor="w").pack(fill="x", pady=(5, 2))
        self.entry_alias = ctk.CTkEntry(main_frame, width=300, height=35)
        self.entry_alias.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(main_frame, text="Dirección Completa", anchor="w").pack(fill="x", pady=(5, 2))
        self.entry_dir = ctk.CTkEntry(main_frame, width=300, height=35)
        self.entry_dir.pack(fill="x", pady=(0, 10))
        
        # ctk.CTkLabel(main_frame, text="Titular", anchor="w").pack(fill="x", pady=(5, 2))
        # self.entry_titular = ctk.CTkEntry(main_frame, width=300, height=35)
        # self.entry_titular.pack(fill="x", pady=(0, 10))

        # Actions
        ctk.CTkButton(main_frame, text="Guardar Inmueble", height=40, font=("Segoe UI", 13, "bold"), 
                      command=self.save, fg_color=COLORS["primary_button"], hover_color=COLORS["primary_button_hover"]).pack(pady=(20, 0), fill="x")
        
        self.transient(parent)
        self.grab_set()
        
        # UI Focus Fix
        self.lift()
        self.focus_force()
        self.attributes("-topmost", True)
        
        self.update_idletasks()
        self.after(10, lambda: center_window(self, self.parent))
        
    def save(self):
        try:
            alias = self.entry_alias.get()
            if not alias: raise ValueError("Alias requerido")

            data = {
                "alias": alias,
                "direccion": self.entry_dir.get(),
                "tipo_propiedad": "Otro"
            }
            
            # Controller can be retrieved via parent.controller or specific instantiation if needed.
            ctl = getattr(self.parent, 'controller', None) or getattr(self.parent, 'catalogs_controller', None)
            
            if ctl and ctl.create_inmueble(data):
                if hasattr(self.parent, 'load_inmuebles'):
                    self.parent.load_inmuebles()
                self.destroy()
        except AppValidationError as e:
            messagebox.showwarning("Invalido", str(e), parent=self)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

class EditInmuebleDialog(ctk.CTkToplevel):
    def __init__(self, parent, item):
        super().__init__(parent)
        self.title("Editar Inmueble")
        self.geometry("300x350")
        self.parent = parent
        self.item = item
        
        ctk.CTkLabel(self, text="Alias").pack(pady=2)
        self.entry_alias = ctk.CTkEntry(self)
        self.entry_alias.insert(0, item.alias)
        self.entry_alias.pack(pady=2)
        
        ctk.CTkLabel(self, text="Dirección").pack(pady=2)
        self.entry_dir = ctk.CTkEntry(self)
        self.entry_dir.insert(0, item.direccion)
        self.entry_dir.pack(pady=2)
        
        # ctk.CTkLabel(self, text="Titular").pack(pady=2)
        # self.entry_titular = ctk.CTkEntry(self)
        # if item.titular: self.entry_titular.insert(0, item.titular)
        # self.entry_titular.pack(pady=2)

        # self.chk_activo = ctk.CTkCheckBox(self, text="Activo")
        # if item.estado == EstadoInmueble.ACTIVO:
        #     self.chk_activo.select()
        # self.chk_activo.pack(pady=10)

        ctk.CTkButton(self, text="Guardar Cambios", command=self.save, fg_color=COLORS["primary_button"], hover_color=COLORS["primary_button_hover"]).pack(pady=(20, 10))
        self.transient(parent)
        self.grab_set()
        
        # UI Focus Fix
        self.lift()
        self.focus_force()
        self.attributes("-topmost", True)
        self.after(10, lambda: center_window(self, self.parent))
        
    def save(self):
        # 1. Ask for confirmation
        if not messagebox.askyesno("Confirmar Guardar", "¿Estás seguro de guardar los cambios?", parent=self):
            return

        try:
            data = {
                "alias": self.entry_alias.get(),
                "direccion": self.entry_dir.get(),
                # "titular": self.entry_titular.get(),
                # "estado": EstadoInmueble.ACTIVO if self.chk_activo.get() == 1 else EstadoInmueble.INACTIVO
            }
            if self.parent.controller.update_inmueble(self.item.id, data):
                messagebox.showinfo("Éxito", "Cambios guardados correctamente.", parent=self)
                self.after(50, lambda: self.parent.load_inmuebles())
                self.destroy()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    def open_services(self):
        ManageServicesDialog(self.parent, self.item)

class ManageServicesDialog(ctk.CTkToplevel):
    def __init__(self, parent, inmueble):
        super().__init__(parent)
        self.title(f"Servicios: {inmueble.alias}")
        self.geometry("600x450")
        self.parent = parent
        self.inmueble = inmueble
        self.controller = CatalogsController() # Direct usage

        # Header
        self.top_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.top_frame.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(self.top_frame, text=f"Administrar Servicios de {inmueble.alias}", font=("Segoe UI", 16, "bold")).pack(side="left")

        # List Area
        self.headers_frame = ctk.CTkFrame(self, height=30)
        self.headers_frame.pack(fill="x", padx=20, pady=(10,0))
        # Cols: Proveedor | Categoria | Regla Ajuste | Accion
        self.cols = [("Proveedor", 200), ("Cat", 100), ("Regla Ajuste", 150), ("Accion", 80)]
        for col, w in self.cols:
            ctk.CTkLabel(self.headers_frame, text=col, width=w, anchor="w", font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)

        self.list_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.list_frame.pack(fill="both", expand=True, padx=20, pady=5)

        # Add Area
        self.add_frame = ctk.CTkFrame(self)
        self.add_frame.pack(fill="x", padx=20, pady=20)
        
        self.setup_add_ui()
        self.load_services()
        
        self.transient(parent)
        self.grab_set()
        
        # UI Focus Fix
        self.lift()
        self.focus_force()
        self.attributes("-topmost", True)
        
        self.after(10, self._center_window)

    def _center_window(self):
        try:
            w, h = 600, 450
            x = self.parent.winfo_rootx() + (self.parent.winfo_width() // 2) - (w // 2)
            y = self.parent.winfo_rooty() + (self.parent.winfo_height() // 2) - (h // 2)
            self.geometry(f'+{x}+{y}')
        except Exception:
            pass
        self.transient(self.parent)
        self.grab_set()
        self.after(10, lambda: center_window(self, self.parent))

    def setup_add_ui(self):
        ctk.CTkLabel(self.add_frame, text="Nuevo Servicio:").pack(side="left", padx=10)
        
        # Proveedor Combo
        self.provs = self.controller.get_proveedores(include_inactive=False)
        self.prov_map = {p.nombre_entidad: p.id for p in self.provs}
        self.combo_prov = ctk.CTkComboBox(self.add_frame, values=list(self.prov_map.keys()), width=150)
        self.combo_prov.pack(side="left", padx=5)
        
        # Rule Combo
        self.rules = [e.value for e in TipoAjuste]
        self.combo_rule = ctk.CTkComboBox(self.add_frame, values=self.rules, width=150)
        self.combo_rule.set(TipoAjuste.ESTACIONAL_IPC.value) # Default
        self.combo_rule.pack(side="left", padx=5)

        ctk.CTkButton(self.add_frame, text="+ Agregar", width=80, command=self.add_service).pack(side="left", padx=10)

    def load_services(self):
        for w in self.list_frame.winfo_children(): w.destroy()
        
        # Get Obs
        # We need a proper getter. 
        # Using Repository directly here for speed as Controller.get_obligaciones(inm_id) is missing
        db = None
        try:
            db = SessionLocal()
            obs = db.query(Obligacion).filter_by(inmueble_id=self.inmueble.id).all()
            
            for o in obs:
                row = ctk.CTkFrame(self.list_frame, fg_color=COLORS["content_surface"])
                row.pack(fill="x", pady=2)
                
                # Link objects
                prov_name = o.proveedor.nombre_entidad if o.proveedor else "?"
                cat_name = o.proveedor.categoria if o.proveedor else "?"
                rule_name = o.reglas_ajuste.tipo_ajuste if o.reglas_ajuste else "Fijo (Implícito)"
                
                ctk.CTkLabel(row, text=prov_name, width=200, anchor="w").pack(side="left", padx=5)
                ctk.CTkLabel(row, text=cat_name, width=100, anchor="w").pack(side="left", padx=5)
                
                # Rule is editable via popup? Or Combo? Let's use Combo for quick edit
                rule_cb = ctk.CTkComboBox(row, values=self.rules, width=140, height=24)
                rule_cb.set(rule_name)
                rule_cb.pack(side="left", padx=5)
                # Auto-save rule on change? No, let's add a button or event
                rule_cb.configure(command=lambda val, oid=o.id: self.update_rule(oid, val))

                ctk.CTkButton(row, text="X", width=30, fg_color=COLORS["status_overdue"], 
                             command=lambda oid=o.id: self.delete_service(oid)).pack(side="left", padx=10)
                
        except Exception as e:
            messagebox.showerror("Error Carga", f"Error cargando servicios: {e}")
        finally:
            if db: db.close()

    def add_service(self):
        try:
            p_name = self.combo_prov.get()
            if not p_name or p_name not in self.prov_map: return
            
            pid = self.prov_map[p_name]
            rule = self.combo_rule.get()
            
            data = {
                "inmueble_id": self.inmueble.id,
                "servicio_id": pid,
                "tipo_ajuste": rule,
                "referencia": ""
            }
            if self.controller.create_obligacion(data):
                self.load_services()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    def update_rule(self, oid, new_val):
        self.controller.update_obligacion_rule(oid, new_val)
        # No reload needed

    def delete_service(self, oid):
        if messagebox.askyesno("Confirmar", "¿Quitar este servicio del inmueble?", parent=self):
            if self.controller.delete_obligacion(oid):
                self.load_services()

class AddProveedorDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Nuevo Proveedor")
        self.geometry("300x250")
        self.parent = parent
        
        ctk.CTkLabel(self, text="Nombre Entidad").pack(pady=2)
        self.entry_nombre = ctk.CTkEntry(self)
        self.entry_nombre.pack(pady=2)
        
        ctk.CTkLabel(self, text="Categoría").pack(pady=2)
        cats = [c.value for c in CategoriaServicio]
        self.combo_cat = ctk.CTkComboBox(self, values=cats)
        self.combo_cat.pack(pady=2)

        self.chk_activo = ctk.CTkCheckBox(self, text="Activo")
        self.chk_activo.select()
        self.chk_activo.pack(pady=5)
        
        self.entry_nombre.bind("<FocusOut>", self._on_name_blur)

        ctk.CTkButton(self, text="Crear", command=self.save, fg_color=COLORS["primary_button"], hover_color=COLORS["primary_button_hover"]).pack(pady=20)
        
        self.transient(parent)
        self.grab_set()
        
        # UI Focus Fix
        self.lift()
        self.focus_force()
        self.attributes("-topmost", True)
        self.after(10, lambda: center_window(self, self.parent))

    def _on_name_blur(self, event=None):
        name = self.entry_nombre.get()
        if name:
            predicted = CognitiveService.predict_category(name)
            if predicted:
                self.combo_cat.set(predicted)
        
    def save(self):
        try:
            nombre = self.entry_nombre.get()
            if not nombre: raise ValueError("Nombre requerido")

            cat_val = self.combo_cat.get()
            cat_enum = next((c for c in CategoriaServicio if c.value == cat_val), None)
            
            data = {
                "nombre": nombre,
                "categoria": cat_enum,
                "frecuencia": "Mensual",
                # "activo": 1 if self.chk_activo.get() == 1 else 0
            }
            if self.parent.controller.create_proveedor(data):
                self.parent.load_proveedores()
                self.destroy()
        except AppValidationError as e:
            messagebox.showwarning("Invalido", str(e), parent=self)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

class EditProveedorDialog(ctk.CTkToplevel):
    def __init__(self, parent, item):
        super().__init__(parent)
        self.title("Editar Proveedor")
        self.geometry("300x250")
        self.parent = parent
        self.item = item
        
        ctk.CTkLabel(self, text="Nombre Entidad").pack(pady=2)
        self.entry_nombre = ctk.CTkEntry(self)
        self.entry_nombre.insert(0, item.nombre_entidad)
        self.entry_nombre.pack(pady=2)
        
        ctk.CTkLabel(self, text="Categoría").pack(pady=2)
        cats = [c.value for c in CategoriaServicio]
        self.combo_cat = ctk.CTkComboBox(self, values=cats)
        self.combo_cat = ctk.CTkComboBox(self, values=cats)
        c_val = item.categoria
        if hasattr(c_val, 'value'): c_val = c_val.value
        self.combo_cat.set(c_val)
        self.combo_cat.pack(pady=2)

        # self.chk_activo = ctk.CTkCheckBox(self, text="Activo")
        # if getattr(item, 'is_active', True): # Safe access or remove if column gone
        #     self.chk_activo.select()
        # self.chk_activo.pack(pady=5)
        
        ctk.CTkButton(self, text="Guardar Cambios", command=self.save, fg_color=COLORS["primary_button"], hover_color=COLORS["primary_button_hover"]).pack(pady=20)

        self.transient(parent)
        self.grab_set()
        
        # UI Focus Fix
        self.lift()
        self.focus_force()
        self.attributes("-topmost", True)
        self.after(10, lambda: center_window(self, self.parent))
        
    def save(self):
        # 1. Ask for confirmation
        if not messagebox.askyesno("Confirmar Guardar", "¿Estás seguro de guardar los cambios?", parent=self):
            return

        try:
            cat_val = self.combo_cat.get()
            cat_enum = next((c for c in CategoriaServicio if c.value == cat_val), None)
            
            data = {
                "nombre": self.entry_nombre.get(),
                "categoria": cat_enum,
                # "activo": 1 if self.chk_activo.get() == 1 else 0
            }
            if self.parent.controller.update_proveedor(self.item.id, data):
                messagebox.showinfo("Éxito", "Cambios guardados correctamente.")
                self.parent.load_proveedores()
                self.destroy()
        except Exception as e:
            messagebox.showerror("Error", str(e))




