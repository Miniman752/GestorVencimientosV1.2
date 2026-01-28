import customtkinter as ctk
from tkinter import messagebox
from services.recycle_bin_service import RecycleBinService
from config import COLORS, FONTS

class RecycleBinDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Papelera de Reciclaje 🗑️")
        self.geometry("700x500")
        
        # Center
        x = parent.winfo_x() + 50
        y = parent.winfo_y() + 50
        self.geometry(f"+{x}+{y}")
        
        self.service = RecycleBinService()
        self.var_selection = ctk.IntVar(value=0)
        
        self.setup_ui()
        self.load_data()
        
        self.grab_set()
        
    def setup_ui(self):
        # Header
        ctk.CTkLabel(self, text="Elementos Eliminados", font=("Segoe UI", 20, "bold")).pack(pady=20)
        
        # Explain
        ctk.CTkLabel(self, text="Selecciona un registro para gestionar:", text_color="gray").pack()
        
        # List Frame
        self.scroll = ctk.CTkScrollableFrame(self, fg_color=COLORS["content_surface"])
        self.scroll.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Actions
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkButton(btn_frame, text="♻️ Restaurar", fg_color=COLORS["status_paid"], command=self.action_restore).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="🔥 Eliminar Definitivamente", fg_color=COLORS["status_overdue"], command=self.action_hard_delete).pack(side="right", padx=10)
        
    def load_data(self):
        for w in self.scroll.winfo_children(): w.destroy()
        self.var_selection.set(0) # Reset selection
        
        items = self.service.get_deleted_vencimientos()
        
        if not items:
            ctk.CTkLabel(self.scroll, text="La papelera está vacía. 🍃").pack(pady=50)
            return
            
        for v in items:
            self._render_row(v)
            
    def _render_row(self, v):
        row = ctk.CTkFrame(self.scroll, fg_color="transparent")
        row.pack(fill="x", pady=2)
        
        # Enforce property Single Selection Group
        rb = ctk.CTkRadioButton(row, text="", value=v.id, variable=self.var_selection)
        rb.pack(side="left", padx=5)

        txt = f"{v.fecha_vencimiento} | {v.obligacion.inmueble.alias} - {v.obligacion.proveedor.nombre_entidad} | ${v.monto_original:,.2f}"
        
        # Make label clickable too
        lbl = ctk.CTkLabel(row, text=txt, anchor="w", cursor="hand2")
        lbl.pack(side="left", fill="x", expand=True)
        lbl.bind("<Button-1>", lambda e, val=v.id: self.var_selection.set(val))
    
    # Removed select_item as we use var_selection directly now

    def action_restore(self):
        sel_id = self.var_selection.get()
        if not sel_id:
             messagebox.showwarning("Selección", "Por favor selecciona un registro.")
             return
             
        if self.service.restore_vencimiento(sel_id):
            messagebox.showinfo("Éxito", "Registro restaurado. Volverá a aparecer en las listas principales.")
            self.load_data()
            
    def action_hard_delete(self):
        sel_id = self.var_selection.get()
        if not sel_id:
             messagebox.showwarning("Selección", "Por favor selecciona un registro.")
             return
        
        if not messagebox.askyesno("Confirmar", "Esta acción es IRREVERSIBLE.\n¿Borrar definitivamente?"):
            return
            
        if self.service.hard_delete_vencimiento(sel_id):
            messagebox.showinfo("Eliminado", "Registro purgado del sistema.")
            self.load_data()
