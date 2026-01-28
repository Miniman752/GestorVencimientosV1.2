
import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog, Menu
from config import COLORS, FONTS
from controllers.reconciliation_controller import ReconciliationController
from services.source_config_service import SourceConfigService
from views.source_manager_view import SourceManagerView
from views.record_editor_dialog import RecordEditorDialog
from views.history_dialog import HistoryDialog

from services.reconciliation_history_service import ReconciliationHistoryService

class ReconciliationView(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color=COLORS["main_background"])
        self.controller = ReconciliationController()
        self.config_service = SourceConfigService()
        self.history_service = ReconciliationHistoryService()
        
        # Grid Layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1) # Main Content
        
        # Header
        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        ctk.CTkLabel(self.header, text="Centro de Conciliación y Auditoría", font=FONTS["heading"], text_color=COLORS["text_primary"]).pack(side="left")
        
        # Main Content Area
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        
        # 1. Control Bar (Top Card)
        self.ctrl_frame = ctk.CTkFrame(self.content, fg_color=COLORS["content_surface"])
        self.ctrl_frame.pack(fill="x", pady=(0, 20))
        
        # Simplified: Just Load File
        self.btn_file = ctk.CTkButton(self.ctrl_frame, text="📄 Cargar Archivo Bancario", command=self.browse_file, fg_color=COLORS["primary_button"], width=200)
        self.btn_file.pack(side="left", padx=20, pady=20)
        
        self.lbl_file = ctk.CTkLabel(self.ctrl_frame, text="Ningún archivo seleccionado", text_color="gray")
        self.lbl_file.pack(side="left", padx=10)
        
        # Clear Button
        ctk.CTkButton(self.ctrl_frame, text="🗑️", width=40, command=self._clear_all, fg_color="transparent", border_width=1, text_color="gray").pack(side="left", padx=5)
        
        self.btn_analyze = ctk.CTkButton(self.ctrl_frame, text="🔍 Iniciar Conciliación", command=self.run_analysis, state="disabled", fg_color=COLORS["primary_button_hover"], width=180)
        self.btn_analyze.pack(side="right", padx=20)
        
        # 2. Stats Dashboard
        self.stats_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        self.stats_frame.pack(fill="x", pady=(0, 20))
        
        self.card_match = self._create_card(self.stats_frame, "Coincidencias", "0", COLORS["status_paid"])
        self.card_new = self._create_card(self.stats_frame, "Nuevos Registros", "0", COLORS["primary_button_hover"]) # Blue
        self.card_conflict = self._create_card(self.stats_frame, "Conflictos", "0", COLORS["status_overdue"])
        
        # 3. Discrepancy Grid
        self.grid_frame = ctk.CTkFrame(self.content, fg_color=COLORS["content_surface"])
        self.grid_frame.pack(fill="both", expand=True)
        
        self._init_grid()
        
        # 4. Action Footer
        # 4. Action Footer & Saving
        self.footer = ctk.CTkFrame(self, fg_color="transparent")
        self.footer.grid(row=2, column=0, sticky="ew", padx=20, pady=20)
        
        # Left: Manual Control
        ctk.CTkButton(self.footer, text="+ Agregar Manual", command=self._add_manual_record, fg_color=COLORS["secondary_button"], width=120).pack(side="left")
        
        # Center: Saving
        self.frame_save = ctk.CTkFrame(self.footer, fg_color="transparent")
        self.frame_save.pack(side="left", padx=50)
        
        ctk.CTkLabel(self.frame_save, text="Período:").pack(side="left", padx=5)
        self.entry_period = ctk.CTkEntry(self.frame_save, width=100, placeholder_text="MM-YYYY")
        self.entry_period.pack(side="left", padx=5)
        from datetime import datetime
        self.entry_period.insert(0, datetime.now().strftime("%Y-%m"))
        
        ctk.CTkButton(self.frame_save, text="💾 Guardar Conciliación", command=self._save_snapshot, fg_color=COLORS["status_pending"]).pack(side="left", padx=(10, 5)) 
        ctk.CTkButton(self.frame_save, text="📜 Historial", command=self._open_history, fg_color=COLORS["secondary_button"], width=80).pack(side="left", padx=5)
        # Explicit Close Button
        ctk.CTkButton(self.frame_save, text="❌ Cerrar", command=self._clear_all, fg_color="transparent", border_width=1, text_color="gray", width=60, hover_color="#FADBD8").pack(side="left", padx=5)
        
        # Export Buttons
        ctk.CTkButton(self.frame_save, text="📊 Excel", command=lambda: self._export_current("excel"), fg_color="#27AE60", width=60).pack(side="left", padx=5) # Green
        ctk.CTkButton(self.frame_save, text="📄 PDF", command=lambda: self._export_current("pdf"), fg_color="#E74C3C", width=60).pack(side="left", padx=5) # Red
        
        # Right: Commit
        self.btn_commit = ctk.CTkButton(self.footer, text="✅ Comprometer en Base de Datos", command=self.commit_changes, state="disabled", fg_color=COLORS["status_paid"], height=40)
        self.btn_commit.pack(side="right")
        
        # Context Menu
        self.menu = Menu(self, tearoff=0)
        self.menu.add_command(label="✏️ Editar", command=self._edit_selection)
        self.menu.add_command(label="🗑️ Eliminar", command=self._delete_selection)
        self.menu.add_separator()
        self.menu.add_command(label="📎 Cargar Comprobante y Conciliar", command=self._quick_reconcile_upload)
        self.menu.add_command(label="➕ Nuevo Manual", command=self._add_manual_record)
        
        # State
        self.current_file = None
        self.current_report = []
        
        self._reload_sources() # Initial Load

    def _export_current(self, fmt):
        if not self.current_report:
            messagebox.showwarning("Aviso", "No hay datos para exportar.")
            return

        ext = ".xlsx" if fmt == "excel" else ".pdf"
        fname = filedialog.asksaveasfilename(
            defaultextension=ext,
            filetypes=[(fmt.upper(), "*" + ext)],
            title=f"Exportar Conciliación a {fmt.upper()}"
        )
        if fname:
            success, msg = self.controller.export_report(self.current_report, fmt, fname)
            if success:
                messagebox.showinfo("Éxito", msg)
            else:
                messagebox.showerror("Error", msg)

    def open_source_manager(self):
        w = SourceManagerView(self)
        self.wait_window(w)
        self._reload_sources()

    def _create_card(self, parent, title, value, color):
        f = ctk.CTkFrame(parent, fg_color=color, height=100)
        f.pack(side="left", fill="x", expand=True, padx=5)
        f.pack_propagate(False)
        ctk.CTkLabel(f, text=value, font=("Segoe UI", 32, "bold"), text_color="white").pack(expand=True)
        ctk.CTkLabel(f, text=title, font=("Segoe UI", 12), text_color="white").pack(pady=(0, 10))
        return f.winfo_children()[0]

    def _clear_all(self):
        if self.current_report:
             if not messagebox.askyesno("Limpiar", "¿Estás seguro de limpiar la pantalla?\n⚠️ Esto no deshace los pagos que ya hayas confirmado en la Base de Datos."):
                 return
                 
        self.current_report = []
        self.current_file = None
        self.lbl_file.configure(text="Ningún archivo seleccionado")
        self.btn_analyze.configure(state="disabled")
        self.btn_commit.configure(state="disabled")
        
        # Reset Cards
        self.card_match.configure(text="0")
        self.card_new.configure(text="0")
        self.card_conflict.configure(text="0")
        
        self._analyze_refresh()

    def browse_file(self):
        path = filedialog.askopenfilename(filetypes=[("Archivos de Datos", "*.xlsx *.xls *.csv"), ("Excel Files", "*.xlsx;*.xls"), ("CSV Files", "*.csv")])
        if path:
            self.current_file = path
            self.lbl_file.configure(text=f"...{path[-30:]}")
            self.btn_analyze.configure(state="normal")

    def _init_grid(self):
        # Generic columns, we will change headings dynamically
        self.cols = ("col1", "col2", "col3", "col4", "col5", "col6")
        self.tree = ttk.Treeview(self.grid_frame, columns=self.cols, show="headings")
        
        style = ttk.Style()
        style.configure("Treeview", rowheight=30)
        
        # Initial Headers (Placeholder)
        self.tree.heading("col1", text="Fecha", command=lambda: self._sort_column("fecha", "col1"))
        self.tree.heading("col2", text="Moneda", command=lambda: self._sort_column("moneda", "col2"))
        self.tree.heading("col3", text="Estado", command=lambda: self._sort_column("status", "col3"))
        self.tree.heading("col4", text="Valor Mío", command=lambda: self._sort_column("valor_db", "col4"))
        self.tree.heading("col5", text="Valor Banco", command=lambda: self._sort_column("valor_csv", "col5"))
        self.tree.heading("col6", text="Acción")
        
        self.tree.column("col1", width=100, anchor="center")
        self.tree.column("col2", width=80, anchor="w")
        self.tree.column("col3", width=100, anchor="center")
        self.tree.column("col4", width=120, anchor="e")
        self.tree.column("col5", width=120, anchor="e")
        self.tree.column("col6", width=150, anchor="center")
        
        sb = ttk.Scrollbar(self.grid_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        
        self.tree.tag_configure("CONFLICT", background="#FADBD8")
        self.tree.tag_configure("NEW", background="#D6EAF8")
        self.tree.tag_configure("MATCH", background="#D5F5E3")
        
        # State for sort
        self.sort_col = None
        self.sort_reverse = False
        
        # Bind Rights Click & Double Click
        self.tree.bind("<Button-3>", self._on_right_click)
        self.tree.bind("<Double-1>", self._edit_selection)

    def _sort_column(self, key, col_id):
        if not self.current_report: return
        
        # Toggle match
        if self.sort_col == key:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_col = key
            self.sort_reverse = False
            
        # Update Arrows
        for c in self.cols:
            t = self.tree.heading(c, "text").replace(" ▲", "").replace(" ▼", "")
            if c == col_id:
                t += " ▼" if self.sort_reverse else " ▲"
            self.tree.heading(c, text=t)
            
        # Sort Data
        def sort_key(x):
            val = x.get(key)
            
            # Special Key: Description composite
            if key == "smart_desc":
                val = x.get('descripcion') or x.get('concepto') or x.get('moneda', '')
            
            # Handle None
            if val is None:
                return "" if isinstance(x.get('status', ''), str) else 0
            
            # Case insensitive for strings
            if isinstance(val, str):
                return val.lower()
            return val

        try:
             self.current_report.sort(key=sort_key, reverse=self.sort_reverse)
        except Exception as e:
             # Fallback for mixed types
             print(f"Sort Warning: {e}")
             self.current_report.sort(key=lambda x: str(x.get(key, "")), reverse=self.sort_reverse)
             
        self._analyze_refresh()

    def _on_right_click(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.menu.post(event.x_root, event.y_root)

    def _edit_selection(self, event=None):
        sel = self.tree.selection()
        if not sel: return
        idx = self.tree.index(sel[0]) # Assuming index matches current_report order? YES, if not sorted/filtered.
        # Treeview index corresponds to insertion order if we don't sort. We always repopulate fully.
        
        record = self.current_report[idx]
        
        dialog = RecordEditorDialog(self, record)
        self.wait_window(dialog)
        
        if dialog.result:
            self.current_report[idx] = dialog.result
            self._analyze_refresh() # Just refresh grid

    def _quick_reconcile_upload(self):
        """
        Action: Open file dialog -> Call Controller -> Create & Reconcile
        """
        sel = self.tree.selection()
        if not sel: return
        
        idx = self.tree.index(sel[0])
        record = self.current_report[idx]
        
        # Check eligibility
        if record.get('status') in ["MATCH", "CONCILIADO"]:
             messagebox.showwarning("Aviso", "Este registro ya está conciliado.")
             return
             
        # Ask for File
        file_path = filedialog.askopenfilename(
            title="Seleccionar Comprobante",
            filetypes=[("Archivos PDF/Imagen", "*.pdf *.jpg *.jpeg *.png")]
        )
        if not file_path: return
        
        # Call Controller
        success, res = self.controller.quick_create_from_receipt(record, file_path)
        
        if success:
             # Update Grid Record
             record['id'] = res
             record['status'] = "CONCILIADO"
             # Assume amount matches fully
             record['valor_db'] = abs(record['valor_csv'])
             
             self._analyze_refresh()
             messagebox.showinfo("Éxito", "Conciliación Rápida Completada.\nRegistro creado y comprobante adjunto.")
        else:
             messagebox.showerror("Error", f"Falló la conciliación rápida: {res}")

    def _delete_selection(self):
        sel = self.tree.selection()
        if not sel: return
        
        idx = self.tree.index(sel[0])
        record = self.current_report[idx]
        
        is_matched = record.get('status') in ["MATCH", "CONCILIADO"]
        msg = "¿Borrar fila seleccionada?"
        if is_matched:
             msg += "\n⚠️ Esta acción deshará la conciliación en la Base de Datos."
             
        if not messagebox.askyesno("Eliminar", msg): return
        
        if is_matched and 'id' in record:
             # Revert in DB
             success, err = self.controller.revert_match(record['id'])
             if not success:
                  messagebox.showerror("Error", f"No se pudo deshacer la conciliación: {err}")
                  return
        
        del self.current_report[idx]
        self._analyze_refresh()

    def _add_manual_record(self):
        dialog = RecordEditorDialog(self)
        self.wait_window(dialog)
        if dialog.result:
            self.current_report.append(dialog.result)
            self._analyze_refresh()

    def _save_snapshot(self):
        if not self.current_report: return
        period = self.entry_period.get()
        source = "Extracto Bancario"
        
        # Calc Stats
        stats = {"match": 0, "new": 0, "conflict": 0, "total": len(self.current_report)}
        for r in self.current_report:
            s = r['status']
            if s == "MATCH": stats['match']+=1
            elif "NO" in s: stats['new']+=1
            else: stats['conflict']+=1
            
        success, path = self.history_service.save_snapshot(period, source, self.current_report, stats)
        if success:
            messagebox.showinfo("Guardado", f"Conciliación guardada en:\n{path}")
        else:
            messagebox.showerror("Error", path)

    def _analyze_refresh(self):
        # Refresh grid from self.current_report without re-running analysis
        source_type = "Banco" 
        self._populate_grid(self.current_report, source_type)

    def _open_history(self):
        d = HistoryDialog(self)
        self.wait_window(d)
        
        if d.result:
            # Load Snapshot
            meta = d.result
            period = meta.get('period', '')
            source = meta.get('source', '')
            
            data = self.history_service.load_snapshot(period, source)
            if data and 'items' in data:
                self.current_report = data['items']
                
                # Update UI
                # self.combo_source.set(source) # Removed
                self.entry_period.delete(0, "end")
                self.entry_period.insert(0, period)
                
                self._analyze_refresh()
                self.btn_commit.configure(state="normal")
                
                messagebox.showinfo("Cargado", f"Conciliación de {source} ({period}) cargada.")
    def _reload_sources(self):
        # Deprecated / No-op
        pass

    def run_analysis(self):
        msg = ctk.CTkLabel(self.content, text=f"Analizando archivo...", font=("Segoe UI", 20))
        msg.place(relx=0.5, rely=0.5, anchor="center")
        self.update_idletasks() # Force UI update
        
        # Default to 'Banco' logic which uses Smart Header Detection
        source_type = "Banco"
        mapping = None # Auto-detect defaults to None
        
        # Call Controller
        success, report = self.controller.analyze(source_type, self.current_file, mapping)
        msg.destroy()
        
        if not success:
            messagebox.showerror("Error", f"No se pudo analizar: {report}")
            return
            
        self.current_report = report
        self._populate_grid(report, source_type)
        self.btn_commit.configure(state="normal")
        
    def _populate_grid(self, report, source_type):
        for item in self.tree.get_children(): self.tree.delete(item)
        
        # Update Headings based on Source (Keep Sort Bindings)
        # We need to re-apply text but keep the command? Or just re-declare. 
        # Re-declaring forces logic again.
        
        # Helper to set text while preserving arrow if active
        def _set_h(col, title):
            current = self.tree.heading(col, "text")
            suffix = ""
            if "▲" in current: suffix = " ▲"
            if "▼" in current: suffix = " ▼"
            self.tree.heading(col, text=title + suffix) # Command persists? No, need to rebind or rely on init.
            # Actually, changing text doesn't remove command.
        
        if source_type == "Forex":
             _set_h("col1", "Fecha Op.")
             _set_h("col2", "Moneda")
             _set_h("col4", "Valor DB (Venta)")
             _set_h("col5", "CSV (Venta)")
             # Rebind Sorts
             self.tree.heading("col2", command=lambda: self._sort_column("moneda", "col2"))
        else: # Bank / Suppliers
             _set_h("col1", "Fecha")
             _set_h("col2", "Concepto/Ref")
             _set_h("col4", "Monto DB")
             _set_h("col5", "Monto CSV")
             # Rebind Sorts
             self.tree.heading("col2", command=lambda: self._sort_column("smart_desc", "col2"))

        n_match, n_new, n_conflict = 0, 0, 0
        
        for r in report:
            status = r['status']
            if status in ["MATCH", "CONCILIADO"]: n_match += 1
            elif status in ["NO_EN_SISTEMA", "NO_EN_BANCO"]: n_new += 1
            else: n_conflict += 1 # Any DIFERENCIA or CONFLICT
            
            # Action Text
            if status == "MATCH" or status == "CONCILIADO": 
                action = "OK"
            elif status == "NO_EN_SISTEMA": action = "Crear en Sistema"
            elif status == "NO_EN_BANCO": action = "Investigar"
            else: action = "⚡ Resolver"
            
            # Formatear
            vals = list(r.values()) # Not safe, dict order varies
            
            # Safe Access
            fecha = self._format_date(r.get('fecha', ''))
            
            if source_type == "Forex":
                # Forex Specific keys
                col2 = r.get('moneda_compra', '') + "/" + r.get('moneda_venta', '') 
                col4 = r.get('valor_db', '')
                col5 = r.get('valor_csv', '')
            else:
                col2 = r.get('descripcion') or r.get('concepto') or r.get('moneda', '')
                col4 = f"{r.get('valor_db', 0):,.2f}"
                col5 = f"{r.get('valor_csv', 0):,.2f}"
            
            tag = "MATCH"
            if "NO" in status: tag = "NEW"
            elif "DIFERENCIA" in status or "CONFLICTO" in status: tag = "CONFLICT"
            
            self.tree.insert("", "end", values=(fecha, col2, status, col4, col5, action), tags=(tag,))
            
        # Update Cards
        # (Assuming _create_card returned the label widget inside? No, it returned the frame?)
        # Wait, I need to update the labels.
        # In _create_card I returned f.winfo_children()[0] which is the VAL label.
        self.card_match.configure(text=str(n_match))
        self.card_new.configure(text=str(n_new))
        self.card_conflict.configure(text=str(n_conflict))
        
        self.tree.bind("<Double-1>", lambda e: self.on_row_click(e, report))

    def _format_date(self, val):
        if not val: return ""
        try:
            from datetime import datetime
            import pandas as pd
            if isinstance(val, (datetime, pd.Timestamp)):
                return val.strftime("%d/%m/%Y")
            # If string ISO
            if isinstance(val, str) and "-" in val:
                # Try parsing YYYY-MM-DD
                return datetime.strptime(val.split("T")[0], "%Y-%m-%d").strftime("%d/%m/%Y")
        except: pass
        return str(val)

    def on_row_click(self, event, report):
        item = self.tree.selection()
        if not item: return
        # Get index
        idx = self.tree.index(item)
        data = report[idx]
        
        # Always open Smart Resolution Dialog
        ResolutionDialog(self, data)

    def commit_changes(self):
        if not self.current_report: return
        
        # Calculate Stats
        n_match = sum(1 for r in self.current_report if r['status'] == "MATCH")
        n_conciliated = sum(1 for r in self.current_report if r['status'] == "CONCILIADO")
        n_pending = sum(1 for r in self.current_report if r['status'] in ["NO_EN_SISTEMA", "NO_EN_BANCO", "DIFERENCIA_IMPORTE", "CONFLICTO", "NEW"])
        
        msg = f"Resumen de Conciliación:\n\n✅ Coincidencias Verificadas: {n_match}\n🔗 Conciliados Manualmente: {n_conciliated}\n⚠️ Pendientes de Resolución: {n_pending}"
        
        if n_pending > 0:
             msg += "\n\nExisten registros pendientes. Por favor, resuelva los conflictos (doble clic) antes de finalizar."
             messagebox.showwarning("Atención", msg)
             return

        confirmed = messagebox.askyesno("Confirmar Conciliación", f"{msg}\n\n¿Desea cerrar este informe y guardar una instantánea en el historial?")
        if not confirmed: return
        
        try:
             count = 0
             # Basic implementation handling Forex only for now
             for r in self.current_report:
                 # Forex Check
                 if ("csv_conta" in r or "csv_venta" in r) and r['status'] in ["NEW", "CONFLICT"]: 
                     self.controller.update_cotizacion_manual(r['fecha'], r['moneda'], r['csv_compra'], r['csv_venta'])
                     count += 1
             
             # Also save snapshot automatically on "Success"
             self._save_snapshot()
             
             success_msg = "Conciliación Finalizada con Éxito."
             if count > 0: success_msg += f"\nSe actualizaron {count} registros Forex."
             
             messagebox.showinfo("Éxito", success_msg)
             
             # Clear
             self._clear_all()
             
        except Exception as e:
            messagebox.showerror("Error Crítico", str(e))

class ResolutionDialog(ctk.CTkToplevel):
    def __init__(self, parent, data):
        super().__init__(parent)
        self.title("Resolución de Conflictos Inteligente")
        self.geometry("900x500")
        
        # UI Focus Fix
        self.lift()
        self.focus_force()
        self.attributes("-topmost", True)
        
        self.parent_view = parent
        self.bank_data = data
        self.selected_venc_id = None
        
        # Main Layout: Header, Content (VS), Footer
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # --- HEADER ---
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        
        status = data['status']
        color = COLORS["status_overdue"] if "DIFERENCIA" in status else COLORS["status_pending"]
        
        ctk.CTkLabel(header_frame, text=f"Diagnóstico: {status}", font=("Segoe UI", 24, "bold"), text_color=color).pack()
        ctk.CTkLabel(header_frame, text="Compare los datos del sistema con el extracto bancario y resuelva el conflicto.", font=("Segoe UI", 12), text_color="gray").pack()

        # --- CONTENT (VS View) ---
        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.grid(row=1, column=0, sticky="nsew", padx=20)
        content_frame.grid_columnconfigure(0, weight=1) # System
        content_frame.grid_columnconfigure(1, weight=0) # Space
        content_frame.grid_columnconfigure(2, weight=0) # VS
        content_frame.grid_columnconfigure(3, weight=0) # Space
        content_frame.grid_columnconfigure(4, weight=1) # Bank
        content_frame.grid_rowconfigure(0, weight=1)
        
        # LEFT CARD: SYSTEM
        self._build_system_card(content_frame, data)
        
        # VS SEPARATOR
        vs_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        vs_frame.grid(row=0, column=2)
        ctk.CTkLabel(vs_frame, text="⚡", font=("Segoe UI", 40)).pack()
        if "IMPORTE" in status:
             diff = data['valor_csv'] - data['valor_db']
             ctk.CTkLabel(vs_frame, text=f"Diff:\n${diff:,.2f}", text_color="red", font=("Segoe UI", 12, "bold")).pack()

        # RIGHT CARD: BANK
        self._build_bank_card(content_frame, data)
        
        # --- FOOTER ---
        footer_frame = ctk.CTkFrame(self, fg_color=COLORS["content_surface"], height=70)
        footer_frame.grid(row=2, column=0, sticky="ew", pady=(20,0))
        
        ctk.CTkButton(footer_frame, text="Cerrar", command=self.destroy, fg_color="transparent", border_width=1, text_color="gray").pack(side="right", padx=20, pady=15)
        
        self.btn_apply = ctk.CTkButton(footer_frame, text="🔗 Confirmar Conciliación", command=self._apply_match, state="disabled", fg_color=COLORS["status_paid"], width=200, height=40)
        self.btn_apply.pack(side="right", padx=10, pady=15)

        # Trigger Auto-Search
        self.after(200, self._auto_search)

    def _build_system_card(self, parent, data):
        card = ctk.CTkFrame(parent, fg_color="white", corner_radius=15, border_color="#D5D8DC", border_width=1)
        card.grid(row=0, column=0, sticky="nsew")
        
        ctk.CTkLabel(card, text="🏛️ EN SISTEMA", font=("Segoe UI", 14, "bold"), text_color="#2C3E50").pack(pady=(20, 10))
        
        # Details
        info = ctk.CTkFrame(card, fg_color="#F8F9F9", corner_radius=10)
        info.pack(fill="x", padx=20, pady=10)
        
        self._row(info, "Fecha:", str(data.get('fecha')))
        self._row(info, "Importe:", f"${data.get('valor_db', 0):,.2f}")
        
        # System Description (if available from id lookup)
        desc = data.get('concepto', '---')
        if "✅" in desc: desc = desc.replace("✅ ", "") # remove verify check
        self._row(info, "Ref:", desc)

        # Edit Button
        btn = ctk.CTkButton(card, text="✏️ Editar Registro Interno", command=self._edit_internal_record, fg_color="#D6EAF8", text_color="#2E86C1", hover_color="#AED6F1")
        btn.pack(pady=20)
        
        if not data.get('id'):
            btn.configure(text="✨ Crear Nuevo desde Banco", command=self._create_new_internal, state="normal", fg_color=COLORS["secondary_button"], text_color="#2C3E50")
        else:
            # Show Unmatch/Delete option for existing links
            btn_del = ctk.CTkButton(card, text="🗑️ Eliminar y Desconciliar", command=self._unmatch_action, fg_color="transparent", text_color="red", hover_color="#FADBD8", height=25)
            btn_del.pack(pady=(0, 20))

    def _unmatch_action(self):
        v_id = self.bank_data.get('id')
        if not v_id: return
        
        from tkinter import messagebox
        confirm = messagebox.askyesno("Confirmar Eliminación", 
                                      "¿Está seguro de que desea eliminar este registro del sistema?\n\n"
                                      "Esta acción borrará el Vencimiento y anulará la conciliación.\n"
                                      "Use esta opción si el registro fue creado por error.",
                                      icon="warning", parent=self)
        if not confirm: return
        
        success, msg = self.parent_view.controller.delete_vencimiento(v_id)
        if success:
            # Reset Bank Data State
            self.bank_data['id'] = None
            self.bank_data['valor_db'] = 0
            self.bank_data['status'] = "NO_EN_SISTEMA"
            self.bank_data.pop('concepto', None)
            
            messagebox.showinfo("Eliminado", "Registro eliminado y desvinculado correctamente.", parent=self)
            self.destroy()
            self.parent_view.run_analysis() # Refresh Grid
        else:
            messagebox.showerror("Error", f"No se pudo eliminar: {msg}", parent=self)

    def _build_bank_card(self, parent, data):
        card = ctk.CTkFrame(parent, fg_color="white", corner_radius=15, border_color="#D5D8DC", border_width=1)
        card.grid(row=0, column=4, sticky="nsew")
        
        ctk.CTkLabel(card, text="🏦 EN BANCO", font=("Segoe UI", 14, "bold"), text_color="#2C3E50").pack(pady=(20, 10))
        
        # Details
        info = ctk.CTkFrame(card, fg_color="#F8F9F9", corner_radius=10)
        info.pack(fill="x", padx=20, pady=10)
        
        self._row(info, "Fecha:", str(data.get('fecha')))
        self._row(info, "Importe:", f"${data.get('valor_csv', 0):,.2f}")
        self._row(info, "Concepto:", data.get('original_row', {}).get('description', data.get('concepto', '')))

        # Section: Link Manual
        ctk.CTkLabel(card, text="Vincular Manualmente:", font=("Segoe UI", 12, "bold"), text_color="gray").pack(pady=(20, 5), anchor="w", padx=20)
        
        search_box = ctk.CTkFrame(card, fg_color="transparent")
        search_box.pack(fill="x", padx=20)
        
        self.entry_search = ctk.CTkEntry(search_box, placeholder_text="Nombre, Monto o Referencia...")
        self.entry_search.pack(side="left", fill="x", expand=True)
        self.entry_search.bind("<Return>", lambda e: self._search_vencimientos())
        
        # Clear Button
        ctk.CTkButton(search_box, text="✖", width=30, fg_color="gray", hover_color="darkred", command=lambda: self.entry_search.delete(0, 'end')).pack(side="left", padx=2)
        ctk.CTkButton(search_box, text="🔍", width=40, command=self._search_vencimientos).pack(side="left", padx=(2,0))
        
        self.list_results = ctk.CTkComboBox(card, values=["Use el buscador..."], command=self._on_select_vencimiento)
        self.list_results.pack(fill="x", padx=20, pady=10)

    def _row(self, parent, label, value):
        f = ctk.CTkFrame(parent, fg_color="transparent", height=25)
        f.pack(fill="x", pady=2, padx=10)
        ctk.CTkLabel(f, text=label, font=("Segoe UI", 11, "bold"), width=80, anchor="w", text_color="gray").pack(side="left")
        ctk.CTkLabel(f, text=str(value), font=("Segoe UI", 12), text_color="black", anchor="w").pack(side="left")

    def _create_new_internal(self):
        # Prepare template from Bank Data
        tpl = {
            'fecha': self.bank_data.get('fecha'),
            'valor_db': self.bank_data.get('valor_csv'), # Pre-fill System Value match
            'valor_csv': self.bank_data.get('valor_csv'),
            'concepto': self.bank_data.get('concepto', '') or self.bank_data.get('descripcion', ''),
            'moneda': self.bank_data.get('moneda', 'ARS'),
            'status': "NO_EN_SISTEMA"
        }
        
        dialog = RecordEditorDialog(self, tpl)
        self.wait_window(dialog)
        
        if dialog.result:
            # User confirmed creation
            data = dialog.result
            
            # Get Period from Parent View
            period = self.parent_view.entry_period.get()
            
            success, res = self.parent_view.controller.create_vencimiento_from_bank(data, period)
            
            if success:
                new_id = res
                # Update Local Bank Data to reflect Match
                self.bank_data['id'] = new_id
                self.bank_data['valor_db'] = data['valor_db']
                self.bank_data['concepto'] = data['concepto']
                self.bank_data['status'] = "CONCILIADO"
                
                # Refresh UI
                self.destroy()
                self.parent_view._analyze_refresh() # Refresh Grid
                from tkinter import messagebox
                messagebox.showinfo("Éxito", "Registro creado y conciliado correctamente.")
            else:
                from tkinter import messagebox
                messagebox.showerror("Error", f"Fallo al crear: {res}")

    def _edit_internal_record(self):
        v_id = self.bank_data.get('id')
        if not v_id: return
        try:
            # Fetch real object
            v_obj = self.parent_view.controller.get_vencimiento(v_id)
            if not v_obj:
                 messagebox.showerror("Error", "No se pudo recuperar el vencimiento de la base de datos.", parent=self)
                 return
                 
            from views.vencimientos_view import EditVencimientoDialog
            dlg = EditVencimientoDialog(self.parent_view, v_obj)
            self.wait_window(dlg)
            
            # Refresh Local Data from DB (Post-Edit)
            updated_v = self.parent_view.controller.get_vencimiento(v_id)
            if updated_v:
                 # Update Report Dict
                 self.bank_data['valor_db'] = updated_v.monto_original
                 # Recalculate Status? 
                 # We can't easily recalc without full logic, but let's assume if amounts match -> MATCH
                 # Or just leave as is but update values.
                 # Let's try a simple heuristic:
                 diff = abs(abs(self.bank_data['valor_csv']) - updated_v.monto_original)
                 if diff < 1.0: 
                      self.bank_data['status'] = "MATCH"
                 else:
                      self.bank_data['status'] = "DIFERENCIA_IMPORTE"
                 
                 desc = "Vencimiento"
                 if updated_v.obligacion and updated_v.obligacion.proveedor:
                      desc = updated_v.obligacion.proveedor.nombre_entidad
                 self.bank_data['concepto'] = f"✅ {desc}"

            self.parent_view._analyze_refresh()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _auto_search(self):
        try:
            val = abs(float(self.bank_data.get('valor_csv', 0)))
            if val > 0:
                self.entry_search.delete(0, "end")
                self.entry_search.insert(0, str(val))
                self._search_vencimientos()
        except: pass

    def _search_vencimientos(self):
        term = self.entry_search.get()
        results = self.parent_view.controller.search_vencimientos(term)
        self.results_map = {f"${r['monto']} - {r['descripcion']}": r['id'] for r in results}
        
        vals = list(self.results_map.keys())
        if not vals: vals = ["Sin resultados"]
        
        self.list_results.configure(values=vals)
        self.list_results.set(vals[0])
        if vals != ["Sin resultados"]:
             self._on_select_vencimiento(vals[0]) # Auto-select first

    def _on_select_vencimiento(self, selection):
        if hasattr(self, 'results_map') and selection in self.results_map:
             self.selected_venc_id = self.results_map[selection]
             self.btn_apply.configure(state="normal")
        else:
             self.btn_apply.configure(state="disabled")

    def _apply_match(self):
         if not self.selected_venc_id: return
         success, msg = self.parent_view.controller.apply_match(self.bank_data, self.selected_venc_id)
         if success:
              self.bank_data['status'] = "CONCILIADO"
              self.parent_view._populate_grid(self.parent_view.current_report, "Banco")
              self.destroy()
         else:
              messagebox.showerror("Error", msg, parent=self)
        



