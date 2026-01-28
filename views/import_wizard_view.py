import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from config import COLORS, FONTS

class ImportWizardView(ctk.CTkToplevel):
    def __init__(self, parent_view, mode="forex"): # mode: forex | vencimientos
        super().__init__()
        self.parent_view = parent_view
        self.controller = parent_view.controller
        self.mode = mode
        
        title_suffix = "Mesa de Dinero" if mode == "forex" else "Vencimientos"
        self.title(f"Asistente de Importación - {title_suffix}")
        self.geometry("800x600")
        self.after(100, self.lift) # Bring to front

        self.current_step = 0
        self.file_path = None
        self.df_preview = None
        
        # Mapping Variables (Common)
        self.map_date = ctk.StringVar()
        
        # Forex Specific
        self.map_buy = ctk.StringVar()
        self.map_sell = ctk.StringVar()
        self.map_currency = ctk.StringVar(value="USD")
        
        # Vencimientos Specific
        self.map_amount = ctk.StringVar()
        self.map_desc = ctk.StringVar()
        self.map_entity = ctk.StringVar() # Optional

        # Container
        self.main_container = ctk.CTkFrame(self, fg_color=COLORS["main_background"])
        self.main_container.pack(fill="both", expand=True, padx=20, pady=20)

        # Header
        self.lbl_step = ctk.CTkLabel(self.main_container, text="Paso 1: Carga de Archivo", font=FONTS["heading"], text_color=COLORS["text_primary"])
        self.lbl_step.pack(pady=10)

        # Content Area (Dynamic)
        self.content_frame = ctk.CTkFrame(self.main_container, fg_color=COLORS["content_surface"])
        self.content_frame.pack(fill="both", expand=True, pady=10)

        # Buttons
        self.btn_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.btn_frame.pack(fill="x", pady=10)
        
        self.btn_next = ctk.CTkButton(self.btn_frame, text="Siguiente >", command=self.next_step)
        self.btn_next.pack(side="right")
        
        self.show_step_1()

    def clear_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    # --- STEPS ---

    def show_step_1(self):
        """Upload & Preview"""
        self.clear_content()
        self.lbl_step.configure(text="Paso 1: Seleccionar Archivo CSV/Excel")
        self.current_step = 1
        
        btn_upload = ctk.CTkButton(self.content_frame, text="Seleccionar Archivo", command=self.browse_file)
        btn_upload.pack(pady=20)
        
        self.lbl_file = ctk.CTkLabel(self.content_frame, text="Ningún archivo seleccionado")
        self.lbl_file.pack()

        # Preview Area
        self.txt_preview = ctk.CTkTextbox(self.content_frame, height=200)
        self.txt_preview.pack(fill="x", padx=20, pady=20)
        self.txt_preview.insert("0.0", "Vista previa aparecerá aquí...")
        self.txt_preview.configure(state="disabled")

    def show_step_2(self):
        """Mapping - DYNAMIC based on Mode"""
        if not self.file_path:
            messagebox.showerror("Error", "Seleccione un archivo primero.")
            self.show_step_1()
            return
            
        self.clear_content()
        self.lbl_step.configure(text="Paso 2: Mapeo de Columnas")
        self.current_step = 2

        check_cols = list(self.df_preview.columns)
        
        # Grid layout for mapping
        grid = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        grid.pack(pady=20)
        
        # --- COMMON: DATE ---
        ctk.CTkLabel(grid, text="Columna FECHA:").grid(row=0, column=0, padx=10, pady=10, sticky="e")
        cb_date = ctk.CTkComboBox(grid, values=check_cols, variable=self.map_date)
        cb_date.grid(row=0, column=1, padx=10, pady=10)
        self._auto_select(check_cols, self.map_date, ["date", "fecha", "vencimiento"])
        
        if self.mode == "forex":
            # --- FOREX MAPPING ---
            ctk.CTkLabel(grid, text="Columna COMPRA:").grid(row=1, column=0, padx=10, pady=10, sticky="e")
            cb_buy = ctk.CTkComboBox(grid, values=check_cols, variable=self.map_buy)
            cb_buy.grid(row=1, column=1, padx=10, pady=10)
            self._auto_select(check_cols, self.map_buy, ["compra", "buy"])

            ctk.CTkLabel(grid, text="Columna VENTA:").grid(row=2, column=0, padx=10, pady=10, sticky="e")
            cb_sell = ctk.CTkComboBox(grid, values=check_cols, variable=self.map_sell)
            cb_sell.grid(row=2, column=1, padx=10, pady=10)
            self._auto_select(check_cols, self.map_sell, ["venta", "sell"])
            
            ctk.CTkLabel(grid, text="Moneda Destino:").grid(row=3, column=0, padx=10, pady=10, sticky="e")
            cb_curr = ctk.CTkComboBox(grid, values=["USD", "ARS"], variable=self.map_currency)
            cb_curr.grid(row=3, column=1, padx=10, pady=10)

        elif self.mode == "vencimientos":
            # --- VENCIMIENTOS MAPPING ---
            ctk.CTkLabel(grid, text="Columna MONTO ($):").grid(row=1, column=0, padx=10, pady=10, sticky="e")
            cb_amount = ctk.CTkComboBox(grid, values=check_cols, variable=self.map_amount)
            cb_amount.grid(row=1, column=1, padx=10, pady=10)
            self._auto_select(check_cols, self.map_amount, ["monto", "importe", "total", "valor", "amount"])

            ctk.CTkLabel(grid, text="Columna DESCRIPCIÓN:").grid(row=2, column=0, padx=10, pady=10, sticky="e")
            cb_desc = ctk.CTkComboBox(grid, values=check_cols, variable=self.map_desc)
            cb_desc.grid(row=2, column=1, padx=10, pady=10)
            self._auto_select(check_cols, self.map_desc, ["desc", "concepto", "detalle", "item"])
            
            ctk.CTkLabel(grid, text="Proveedor/Entidad (Opcional):").grid(row=3, column=0, padx=10, pady=10, sticky="e")
            cb_ent = ctk.CTkComboBox(grid, values=["(Detectar Automáticamente)"] + check_cols, variable=self.map_entity)
            cb_ent.grid(row=3, column=1, padx=10, pady=10)
            self.map_entity.set("(Detectar Automáticamente)") 
            # Could auto-detect "proveedor" col if exists

        self.btn_next.configure(text="Importar y Finalizar")
    
    def _auto_select(self, options, var, keywords):
        for c in options:
            for k in keywords:
                if k in c.lower():
                    var.set(c)
                    return

    def browse_file(self):
        path = filedialog.askopenfilename(filetypes=[("CSV/Excel Files", "*.csv *.xlsx")])
        if path:
            self.file_path = path
            self.lbl_file.configure(text=path)
            
            # Controller must implement preview_csv
            if hasattr(self.controller, 'preview_csv'):
                success, result = self.controller.preview_csv(path)
                if success:
                    self.df_preview = result # DataFrame
                    text_preview = result.to_string()
                    self.txt_preview.configure(state="normal")
                    self.txt_preview.delete("0.0", "end")
                    self.txt_preview.insert("0.0", text_preview)
                    self.txt_preview.configure(state="disabled")
                else:
                    messagebox.showerror("Error", result)
            else:
                 messagebox.showerror("Error", "El controlador no soporta previsualización.")

    def next_step(self):
        if self.current_step == 1:
            self.show_step_2()
        elif self.current_step == 2:
            self.run_import()

    def run_import(self):
        # Validate & Build Mapping
        mapping = { 'fecha': self.map_date.get() }
        
        if self.mode == "forex":
            mapping['compra'] = self.map_buy.get()
            mapping['venta'] = self.map_sell.get()
            mapping['moneda_fixed'] = self.map_currency.get()
            
        elif self.mode == "vencimientos":
            mapping['monto'] = self.map_amount.get()
            mapping['descripcion'] = self.map_desc.get()
            ent = self.map_entity.get()
            if ent != "(Detectar Automáticamente)":
                mapping['entidad'] = ent

        success, msg = self.controller.process_import(self.file_path, mapping)
        
        if success:
            messagebox.showinfo("Importación Exitosa", msg)
            self.parent_view.load_data() # Refresh grid
            self.destroy() # Close wizard
        else:
            messagebox.showerror("Falló la Importación", msg)


