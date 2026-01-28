
import customtkinter as ctk
from tkinter import filedialog, messagebox
import pandas as pd
import csv
from config import COLORS, FONTS
from services.source_config_service import SourceConfigService

class SourceWizardView(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Asistente de Alta de Fuente 🧙‍♂️")
        self.geometry("900x700")
        
        # Modal Logic
        self.transient(parent)
        self.grab_set()
        self.lift()
        self.focus_set()
        
        self.service = SourceConfigService()
        self.current_step = 1

        # State
        self.file_path = None
        self.raw_lines = []
        self.delimiter = ";"
        self.header_row = 0
        self.df = None
        
        # UI Layout
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        
        # Footer Navigation
        self.footer = ctk.CTkFrame(self, height=60, fg_color=COLORS["content_surface"])
        self.footer.grid(row=1, column=0, sticky="ew")
        
        self.btn_back = ctk.CTkButton(self.footer, text="⬅️ Atrás", command=self.go_back, state="disabled", fg_color="gray")
        self.btn_back.pack(side="left", padx=20, pady=15)
        
        self.lbl_step = ctk.CTkLabel(self.footer, text="Paso 1 de 4", font=("Segoe UI", 12, "bold"), text_color="gray")
        self.lbl_step.pack(side="left", expand=True)
        
        self.btn_next = ctk.CTkButton(self.footer, text="Siguiente ➡️", command=self.go_next, state="disabled")
        self.btn_next.pack(side="right", padx=20, pady=15)
        
        self.show_step_1()

# ... (skipping to go_next)

    def go_next(self):
        if self.current_step == 1: self.show_step_2()
        elif self.current_step == 2: 
            self._refresh_step_2() # Force update columns before mapping
            self.show_step_3()
        elif self.current_step == 3: 
            # Capture mapping before widgets are destroyed
            self.saved_mapping = {}
            for k, cb in self.mapping_vars.items():
                self.saved_mapping[k] = cb.get()
            self.show_step_4()
        elif self.current_step == 4: self.finish_wizard()

# ... (skipping to _refresh_step_2)

    def _refresh_step_2(self):
        try:
            h = int(self.entry_header.get())
            self.header_row = h
            
            import os
            ext = os.path.splitext(self.file_path)[1].lower() if self.file_path else ".csv"
            
            if ext in ['.xlsx', '.xls']:
                # Excel
                self.df = pd.read_excel(self.file_path, sheet_name=self.sheet_name, header=self.header_row, nrows=10)
            else:
                # CSV
                self.df = pd.read_csv(self.file_path, sep=self.delimiter, header=self.header_row, nrows=10, encoding='utf-8')
            
            # Clean Columns
            self.df.columns = [str(c).strip() for c in self.df.columns]
                
            cols = list(self.df.columns)
            self.lbl_columns.configure(text=f"Columnas Detectadas ({len(cols)}): {', '.join(cols[:5])}...")
            
            self.grid_preview.delete("1.0", "end")
            self.grid_preview.insert("1.0", self.df.to_string())
        except Exception as e:
            self.lbl_columns.configure(text=f"Error: {e}")


        
    def go_back(self):
        if self.current_step == 2: self.show_step_1()
        elif self.current_step == 3: self.show_step_2()
        elif self.current_step == 4: self.show_step_3()

    def _clear_container(self):
        for w in self.container.winfo_children(): w.destroy()

    def _update_nav(self, step, can_next=True, is_last=False):
        self.current_step = step
        self.lbl_step.configure(text=f"Paso {step} de 4")
        self.btn_back.configure(state="normal" if step > 1 else "disabled", fg_color="gray" if step == 1 else COLORS["secondary_button"])
        self.btn_next.configure(text="Guardar y Finalizar ✅" if is_last else "Siguiente ➡️", 
                                state="normal" if can_next else "disabled",
                                fg_color=COLORS["status_paid"] if is_last else COLORS["primary_button"])

    # --- STEP 1: UPLOAD & DETECT ---
    def show_step_1(self):
        self._clear_container()
        self._update_nav(1, can_next=False)
        
        ctk.CTkLabel(self.container, text="1. Carga de Muestra", font=FONTS["heading"]).pack(pady=(0, 20))
        ctk.CTkLabel(self.container, text="Sube un archivo de ejemplo (CSV o Excel).", text_color="gray").pack()
        
        btn = ctk.CTkButton(self.container, text="📂 Seleccionar Archivo", command=self.load_file, height=50, width=200)
        btn.pack(pady=40)
        
        self.lbl_file_info = ctk.CTkLabel(self.container, text="", font=("Courier New", 12))
        self.lbl_file_info.pack(pady=10)
        
        # Sheet Selector (for Excel)
        self.frame_sheet = ctk.CTkFrame(self.container, fg_color="transparent")
        self.lbl_sheet = ctk.CTkLabel(self.frame_sheet, text="Hoja de Cálculo:", anchor="w")
        self.lbl_sheet.pack(side="left", padx=10)
        self.combo_sheet = ctk.CTkComboBox(self.frame_sheet, command=self._on_sheet_change)
        self.combo_sheet.pack(side="left")
        
        self.txt_preview = ctk.CTkTextbox(self.container, width=800, height=200)
        self.txt_preview.pack(pady=10)
        
    def load_file(self):
        path = filedialog.askopenfilename(filetypes=[("Data Files", "*.csv;*.xlsx;*.xls"), ("CSV", "*.csv"), ("Excel", "*.xlsx;*.xls")])
        if not path: return
        self.file_path = path
        self.sheet_name = 0 # Default
        
        # Detect Type
        import os
        ext = os.path.splitext(path)[1].lower()
        
        try:
            preview_text = ""
            info_text = f"Archivo: {os.path.basename(path)}\n"
            
            if ext in ['.xlsx', '.xls']:
                # EXCEL FLOW
                xls = pd.ExcelFile(path)
                sheets = xls.sheet_names
                
                info_text += f"Formato: Excel ({len(sheets)} Hojas)"
                
                if len(sheets) > 1:
                    self.frame_sheet.pack(pady=10) # Show selector
                    self.combo_sheet.configure(values=sheets)
                    self.combo_sheet.set(sheets[0])
                    self.sheet_name = sheets[0]
                else:
                    self.frame_sheet.pack_forget()
                    self.sheet_name = sheets[0]
                    
                # Preview
                df = pd.read_excel(path, sheet_name=self.sheet_name, nrows=10, header=None)
                preview_text = df.to_string()
                
            else:
                # CSV FLOW
                self.frame_sheet.pack_forget()
                self.sheet_name = 0
                
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    sample = f.read(2048)
                    sniffer = csv.Sniffer()
                    try: dialect = sniffer.sniff(sample)
                    except: dialect = None
                    
                    self.delimiter = dialect.delimiter if dialect else ';'
                    if '\t' in sample and self.delimiter not in sample: self.delimiter = '\t'
                    
                    info_text += f"Delimitador Detectado: '{self.delimiter}'"
                    
                    f.seek(0)
                    lines = [next(f) for _ in range(10)]
                    preview_text = "".join(lines)

            self.lbl_file_info.configure(text=info_text)
            self.txt_preview.delete("1.0", "end")
            self.txt_preview.insert("1.0", preview_text)
            
            self.btn_next.configure(state="normal")
            
        except Exception as e:
            messagebox.showerror("Error de Lectura", str(e))

    def _on_sheet_change(self, choice):
        if not self.file_path: return
        self.sheet_name = choice
        try:
            df = pd.read_excel(self.file_path, sheet_name=self.sheet_name, nrows=10, header=None)
            self.txt_preview.delete("1.0", "end")
            self.txt_preview.insert("1.0", df.to_string())
        except Exception as e:
            messagebox.showerror("Error cambiar hoja", str(e))


    # --- STEP 2: HEADER CLEANING ---
    def show_step_2(self):
        self._clear_container()
        self._update_nav(2, can_next=True)
        
        ctk.CTkLabel(self.container, text="2. Limpieza de Encabezado", font=FONTS["heading"]).pack(pady=10)
        ctk.CTkLabel(self.container, text="Indica en qué fila comienzan los títulos de las columnas (0-Indexed).", text_color="gray").pack()
        
        frame_input = ctk.CTkFrame(self.container, fg_color="transparent")
        frame_input.pack(pady=20)
        ctk.CTkLabel(frame_input, text="Fila de Encabezado:").pack(side="left", padx=10)
        self.entry_header = ctk.CTkEntry(frame_input, width=50)
        self.entry_header.insert(0, str(self.header_row))
        self.entry_header.pack(side="left")
        ctk.CTkButton(frame_input, text="↻ Actualizar Vista", command=self._refresh_step_2, width=120).pack(side="left", padx=10)
        
        self.lbl_columns = ctk.CTkLabel(self.container, text="Columnas Detectadas: -", text_color=COLORS["status_paid"])
        self.lbl_columns.pack(pady=5)
        
        self.grid_preview = ctk.CTkTextbox(self.container, width=800, height=250, wrap="none")
        self.grid_preview.pack()
        
        self._refresh_step_2()
        
    def _refresh_step_2(self):
        try:
            h = int(self.entry_header.get())
            self.header_row = h
            
            import os
            ext = os.path.splitext(self.file_path)[1].lower() if self.file_path else ".csv"
            
            if ext in ['.xlsx', '.xls']:
                # Excel
                self.df = pd.read_excel(self.file_path, sheet_name=self.sheet_name, header=self.header_row, nrows=10)
            else:
                # CSV
                self.df = pd.read_csv(self.file_path, sep=self.delimiter, header=self.header_row, nrows=10, encoding='utf-8')
                
            cols = list(self.df.columns)
            self.lbl_columns.configure(text=f"Columnas Detectadas ({len(cols)}): {', '.join(map(str, cols[:5]))}...")
            
            self.grid_preview.delete("1.0", "end")
            self.grid_preview.insert("1.0", self.df.to_string())
        except Exception as e:
            self.lbl_columns.configure(text=f"Error: {e}")

    # --- STEP 3: MAPPING ---
    def show_step_3(self):
        if self.df is None: return
        self._clear_container()
        self._update_nav(3, can_next=True)
        
        ctk.CTkLabel(self.container, text="3. Mapeo Inteligente", font=FONTS["heading"]).pack(pady=10)
        
        # Mapping Grid
        f = ctk.CTkScrollableFrame(self.container, width=600, height=400)
        f.pack(fill="both", expand=True)
        
        self.mapping_vars = {}
        cols = ["(Ignorar)"] + list(map(str, self.df.columns))
        
        # Fields to Map
        fields = [
            ("Fecha", "fecha"),
            ("Descripción", "descripcion"),
            ("Identificador Único", "identificador_unico"),
            ("Importe Entrada (Crédito)", "importe_entrada"),
            ("Importe Salida (Débito)", "importe_salida"),
            ("Importe Multi-Moneda (ARS)", "importe_ars"),
            ("Importe Multi-Moneda (USD)", "importe_usd"),
        ]
        
        for i, (label, key) in enumerate(fields):
            row_f = ctk.CTkFrame(f, fg_color="transparent")
            row_f.pack(fill="x", pady=5)
            ctk.CTkLabel(row_f, text=label, width=200, anchor="w", font=("Segoe UI", 12, "bold")).pack(side="left")
            
            cb = ctk.CTkComboBox(row_f, values=cols, width=300)
            cb.pack(side="left")
            
            # Smart Guess
            # map(str, ...) used above, so columns are strings
            guess = next((str(c) for c in self.df.columns if key.split('_')[0].lower() in str(c).lower() or (key=='importe_entrada' and 'credito' in str(c).lower()) or (key=='importe_salida' and 'debito' in str(c).lower())), "(Ignorar)")
            if guess != "(Ignorar)": cb.set(guess)
            else: cb.set("(Ignorar)")
            
            self.mapping_vars[key] = cb

    # --- STEP 4: RULES & SAVE ---
    def show_step_4(self):
        self._clear_container()
        self._update_nav(4, is_last=True)
        
        ctk.CTkLabel(self.container, text="4. Finalizar Configuración", font=FONTS["heading"]).pack(pady=10)
        
        self.entry_name = ctk.CTkEntry(self.container, placeholder_text="Nombre de la Fuente (Ej: Visa Galicia)", width=400)
        self.entry_name.pack(pady=20)
        
        ctk.CTkLabel(self.container, text="Tipo de Moneda Predeterminada:", anchor="w").pack()
        self.combo_curr = ctk.CTkComboBox(self.container, values=["ARS", "USD", "EUR"])
        self.combo_curr.pack(pady=5)
        
    def finish_wizard(self):
        name = self.entry_name.get()
        if not name: 
            messagebox.showerror("Error", "Debes ingresar un nombre.")
            return

        final_mapping = {}
        final_mapping = {}
        # Use saved state, fallback to empty if direct finish (rare)
        source_map = getattr(self, 'saved_mapping', {})
        for k, val in source_map.items():
            if val != "(Ignorar)":
                final_mapping[k] = val
        
        import os
        ext = os.path.splitext(self.file_path)[1].lower() if self.file_path else ".csv"
        fmt = "XLSX" if ext in ['.xlsx', '.xls'] else "CSV"
        
        config = {
            "name": name,
            "type": "Banco",
            "format": fmt,
            "currency": self.combo_curr.get(),
            "delimiter": self.delimiter,
            "header_row": self.header_row,
            "sheet_name": self.sheet_name,
            "mapping": final_mapping
        }
        
        self.service.add_source(config)
        messagebox.showinfo("Éxito", f"Fuente '{name}' creada correctamente.")
        self.destroy()


