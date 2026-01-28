
import customtkinter as ctk
from tkinter import messagebox
from config import COLORS, FONTS
from services.source_config_service import SourceConfigService
from views.source_wizard_view import SourceWizardView

class SourceManagerView(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Gestor de Fuentes de Datos")
        self.geometry("950x650")
        
        # Modal Logic
        self.transient(parent) # Link to parent
        self.grab_set()        # Modal lock
        
        # UI Focus Fix
        self.lift()            # Front
        self.focus_force()
        self.attributes("-topmost", True)
        
        self.service = SourceConfigService()
        self.sources = []
        self.current_source = None
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self._init_ui()
        self.load_list()
        
    def _init_ui(self):
        # --- SIDEBAR ---
        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        ctk.CTkLabel(self.sidebar, text="Fuentes Configuradas", font=FONTS["heading"]).pack(pady=20, padx=10)
        
        self.scroll_list = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent")
        self.scroll_list.pack(fill="both", expand=True, padx=5, pady=5)
        
        ctk.CTkButton(self.sidebar, text="+ Nueva Fuente", command=self.new_source, fg_color=COLORS["secondary_button"]).pack(pady=(20, 5), padx=20)
        ctk.CTkButton(self.sidebar, text="🪄 Asistente Mágico", command=self.open_wizard, fg_color=COLORS["primary_button"]).pack(pady=(5, 20), padx=20)

        # --- MAIN FORM ---
        self.main_frame = ctk.CTkFrame(self, fg_color=COLORS["content_surface"])
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        
        # Title
        self.lbl_title = ctk.CTkLabel(self.main_frame, text="Detalle de Fuente", font=FONTS["heading"], text_color=COLORS["text_primary"])
        self.lbl_title.pack(anchor="w", pady=20, padx=20)
        
        # Form Container
        self.form_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.form_frame.pack(fill="both", expand=True, padx=20)
        self.form_frame.grid_columnconfigure(1, weight=1)
        self.form_frame.grid_columnconfigure(3, weight=1)
        
        # --- SECTION 1: GENERAL ---
        self._label(0, 0, "Nombre de la Fuente:")
        self.entry_name = self._entry(0, 1)
        
        self._label(1, 0, "Tipo de Fuente:")
        self.combo_type = self._combo(1, 1, ["Extracto Bancario", "Sistema Externo", "Excel Manual", "API"])

        self._label(2, 0, "Moneda Predet.:")
        self.combo_currency = self._combo(2, 1, ["ARS", "USD", "EUR"])

        # Divider
        ctk.CTkFrame(self.form_frame, height=2, fg_color="gray").grid(row=3, column=0, columnspan=4, sticky="ew", pady=15)
        ctk.CTkLabel(self.form_frame, text="Configuración de Archivo", font=("Segoe UI", 12, "bold")).grid(row=4, column=0, sticky="w")
        
        # --- SECTION 2: FILE FORMAT ---
        self._label(5, 0, "Formato:")
        self.combo_format = self._combo(5, 1, ["CSV", "XLSX", "TXT", "JSON"])
        
        self._label(5, 2, "Fila Encabezado:")
        self.entry_header = self._entry(5, 3, "0")
        
        self._label(6, 0, "Delimitador:")
        self.combo_delimiter = self._combo(6, 1, ["Detectar (; , | tab)", ";", ",", "|", "tab"])

        # Divider
        ctk.CTkFrame(self.form_frame, height=2, fg_color="gray").grid(row=7, column=0, columnspan=4, sticky="ew", pady=15)
        ctk.CTkLabel(self.form_frame, text="Mapeo de Columnas (Mapping)", font=("Segoe UI", 12, "bold")).grid(row=8, column=0, sticky="w")
        
        # --- SECTION 3: MAPPING ---
        self.map_entries = {}
        row = 9
        
        self._label(row, 0, "Columna Fecha:"); 
        self.map_entries['fecha'] = self._entry(row, 1, "Fecha")
        
        self._label(row, 2, "Columna Descripción:"); 
        self.map_entries['descripcion'] = self._entry(row, 3, "Descripción")
        
        row += 1
        self._label(row, 0, "Columna Importe Entrada:"); 
        self.map_entries['importe_entrada'] = self._entry(row, 1, "Crédito")
        
        self._label(row, 2, "Columna Importe Salida:"); 
        self.map_entries['importe_salida'] = self._entry(row, 3, "Débito")
        
        row += 1
        self._label(row, 0, "Columna ID Único:"); 
        self.map_entries['identificador_unico'] = self._entry(row, 1, "Referencia")

        # Buttons
        btn_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", side="bottom", pady=20, padx=20)
        
        self.btn_save = ctk.CTkButton(btn_frame, text="💾 Guardar Configuración", command=self.save_current, fg_color=COLORS["status_paid"])
        self.btn_save.pack(side="right", padx=10)
        self.btn_delete = ctk.CTkButton(btn_frame, text="🗑️ Eliminar", command=self.delete_current, fg_color=COLORS["status_overdue"])
        self.btn_delete.pack(side="left", padx=10)

    # Helpers
    def _label(self, r, c, txt):
        ctk.CTkLabel(self.form_frame, text=txt, anchor="w").grid(row=r, column=c, sticky="w", pady=5, padx=5)
    def _entry(self, r, c, placeholder=""):
        e = ctk.CTkEntry(self.form_frame)
        e.grid(row=r, column=c, sticky="ew", pady=5, padx=5)
        e.insert(0, placeholder)
        return e
    def _combo(self, r, c, values):
        cb = ctk.CTkComboBox(self.form_frame, values=values)
        cb.grid(row=r, column=c, sticky="ew", pady=5, padx=5)
        return cb

    def load_list(self):
        for w in self.scroll_list.winfo_children(): w.destroy()
        self.sources = self.service.get_sources()
        for s in self.sources:
            btn = ctk.CTkButton(self.scroll_list, text=s['name'], command=lambda x=s: self.load_source(x), fg_color="transparent", border_width=1, text_color=("black", "white"), anchor="w")
            btn.pack(fill="x", pady=2)

    def load_source(self, source):
        self.current_source = source
        self.lbl_title.configure(text=f"Editando: {source['name']}")
        
        # Set Fields
        self.entry_name.delete(0, "end"); self.entry_name.insert(0, source['name'])
        self.combo_type.set(source.get('type', 'Extracto Bancario'))
        self.combo_currency.set(source.get('currency', 'ARS'))
        self.combo_format.set(source.get('format', 'CSV'))
        self.combo_delimiter.set(source.get('delimiter', 'Detectar (; , | tab)'))
        self.entry_header.delete(0, "end"); self.entry_header.insert(0, str(source.get('header_row', 0)))
        
        mapping = source.get('mapping', {})
        for k, v in self.map_entries.items():
            v.delete(0, "end")
            v.insert(0, mapping.get(k, ""))

    def new_source(self):
        self.current_source = None
        self.lbl_title.configure(text="Nueva Fuente de Datos")
        self.entry_name.delete(0, "end")
        self.entry_header.delete(0, "end"); self.entry_header.insert(0, "0")
        for v in self.map_entries.values(): v.delete(0, "end")

    def save_current(self):
        name = self.entry_name.get()
        if not name: return
        
        mapping = {k: v.get() for k, v in self.map_entries.items()}
        
        header_val = 0
        try: header_val = int(self.entry_header.get())
        except: pass
        
        new_data = {
            "name": name,
            "type": self.combo_type.get(),
            "currency": self.combo_currency.get(),
            "format": self.combo_format.get(),
            "delimiter": self.combo_delimiter.get(),
            "header_row": header_val,
            "mapping": mapping
        }
        
        if self.current_source:
             self.service.update_source(self.current_source['name'], new_data)
        else:
             self.service.add_source(new_data)
             
        messagebox.showinfo("Guardado", "Fuente guardada correctamente.", parent=self)
        self.load_list()
        self.new_source()


    def delete_current(self):
        if not self.current_source: return
        if messagebox.askyesno("Confirmar", f"¿Eliminar {self.current_source['name']}?", parent=self):
            self.service.delete_source(self.current_source['name'])
            self.load_list()
            self.new_source()

    def open_wizard(self):
        w = SourceWizardView(self)
        self.wait_window(w)
        try:
            if self.winfo_exists():
                self.load_list()
        except: pass




