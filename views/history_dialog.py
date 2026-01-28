
import customtkinter as ctk
import os
from config import COLORS, FONTS
from services.reconciliation_history_service import ReconciliationHistoryService

class HistoryDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Historial de Conciliaciones 📜")
        self.geometry("600x400")
        
        # Modal
        self.transient(parent)
        self.grab_set()
        
        # UI Focus Fix
        self.lift()
        self.focus_force()
        self.attributes("-topmost", True)
        
        self.service = ReconciliationHistoryService()
        self.result = None
        
        self._init_ui()
        self._load_list()
        
    def _init_ui(self):
        ctk.CTkLabel(self, text="Conciliaciones Guardadas", font=FONTS["heading"]).pack(pady=10)
        
        # Header for list
        h = ctk.CTkFrame(self, fg_color="transparent")
        h.pack(fill="x", padx=20)
        ctk.CTkLabel(h, text="Fuente", width=150, anchor="w", font=("Segoe UI", 12, "bold")).pack(side="left")
        ctk.CTkLabel(h, text="Período", width=100, anchor="w", font=("Segoe UI", 12, "bold")).pack(side="left")
        ctk.CTkLabel(h, text="Guardado", width=150, anchor="w", font=("Segoe UI", 12, "bold")).pack(side="left")
        
        self.scroll = ctk.CTkScrollableFrame(self)
        self.scroll.pack(fill="both", expand=True, padx=20, pady=5)
        
        f_btns = ctk.CTkFrame(self, fg_color="transparent")
        f_btns.pack(pady=10)
        
        ctk.CTkButton(f_btns, text="📂 Abrir Carpeta", command=self._open_folder, fg_color=COLORS["secondary_button"], width=120).pack(side="left", padx=10)
        ctk.CTkButton(f_btns, text="Cerrar", command=self.destroy, fg_color="gray").pack(side="left", padx=10)

    def _load_list(self):
        snapshots = self.service.list_snapshots()
        
        if not snapshots:
            ctk.CTkLabel(self.scroll, text="No hay conciliaciones guardadas.").pack(pady=20)
            return
            
        for meta in snapshots:
            card = ctk.CTkFrame(self.scroll, fg_color=COLORS["content_surface"])
            card.pack(fill="x", pady=2)
            
            # Clickable logic wrapper
            # Delete Button (Icon X or Trash)
            ctk.CTkButton(card, text="🗑️", width=30, command=lambda m=meta: self._delete(m), fg_color="transparent", text_color="red", hover_color="#FADBD8").pack(side="right", padx=5)
            
            # Load Button
            def _load_wrapper(m=meta):
                self.result = m
                self.destroy()
                
            btn = ctk.CTkButton(card, text="📂 Cargar", width=80, command=_load_wrapper, fg_color=COLORS["primary_button"], height=25)
            btn.pack(side="right", padx=5, pady=5)
            
            ctk.CTkLabel(card, text=meta.get('source', '?'), width=150, anchor="w").pack(side="left", padx=5)
            ctk.CTkLabel(card, text=meta.get('period', '?'), width=100, anchor="w").pack(side="left", padx=5)
            
            # Format date
            saved = meta.get('saved_at', '')
            if 'T' in saved: saved = saved.split('T')[0] + ' ' + saved.split('T')[1][:5]
            ctk.CTkLabel(card, text=saved, width=150, anchor="w", text_color="gray").pack(side="left", padx=5)

    def _delete(self, meta):
        from tkinter import messagebox
        if messagebox.askyesno("Confirmar", "¿Eliminar esta conciliación guardada?", parent=self):
             success, msg = self.service.delete_snapshot(meta['period'], meta['source'])
             if success:
                 # Reload list
                 for w in self.scroll.winfo_children(): w.destroy()
                 self._load_list()
             else:
                 messagebox.showerror("Error", msg, parent=self)

    def _open_folder(self):
        import subprocess, platform
        path = self.service.get_storage_path()
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])


