import customtkinter as ctk
from tkinter import messagebox
from services.period_service import PeriodService
from models.entities import EstadoPeriodo
from config import COLORS, FONTS
from datetime import date
from utils.exceptions import AppIntegrityError

class PeriodManagerWindow(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Administrador de Períodos Fiscales")
        self.geometry("900x600")
        
        # Center
        self.after(10, self._center_window)
        
        # UI Focus Fix
        self.lift()
        self.focus_force()
        self.attributes("-topmost", True)

        # Header
        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(self.header, text="Gestión de Períodos Fiscales", font=FONTS["heading"], text_color=COLORS["primary_button"]).pack(side="left")
        
        ctk.CTkButton(self.header, text="+ Nuevo Período", command=self.open_create_dialog, fg_color=COLORS["primary_button"]).pack(side="right")

        # Column Headers
        self.cols_frame = ctk.CTkFrame(self, height=30, fg_color="transparent")
        self.cols_frame.pack(fill="x", padx=20, pady=(10,0))
        
        headers = ["Período", "Estado", "Cierre", "Responsable", "Notas", "Acciones"]
        weights = [1, 1, 1, 1, 2, 2]
        
        for idx, (h, w) in enumerate(zip(headers, weights)):
            self.cols_frame.grid_columnconfigure(idx, weight=w)
            ctk.CTkLabel(self.cols_frame, text=h, font=("Segoe UI", 11, "bold")).grid(row=0, column=idx, sticky="w", padx=5)

        # Scrollable List
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color=COLORS["content_surface"])
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=5)
        for idx in range(len(weights)):
             self.scroll_frame.grid_columnconfigure(idx, weight=weights[idx])

        self.load_periods()
        
    def _center_window(self):
        self.update_idletasks()
        try:
            width = self.winfo_width()
            height = self.winfo_height()
            x = self.master.winfo_rootx() + (self.master.winfo_width() // 2) - (width // 2)
            y = self.master.winfo_rooty() + (self.master.winfo_height() // 2) - (height // 2)
            self.geometry(f'+{x}+{y}')
        except: pass

    def load_periods(self):
        try:
            if not self.winfo_exists() or not self.scroll_frame.winfo_exists():
                return
            for w in self.scroll_frame.winfo_children(): w.destroy()
        except Exception:
            return
        
        periods = PeriodService.get_all_periods()
        if not periods:
             # Ensure current exists just in case
             PeriodService.check_period_status(date.today())
             periods = PeriodService.get_all_periods()

        for p in periods:
            self.render_row(p)

    def render_row(self, period):
        # Color Logic
        c_state = COLORS["status_paid"]
        if period.estado == EstadoPeriodo.CERRADO: c_state = COLORS["status_pending"]
        elif period.estado == EstadoPeriodo.BLOQUEADO: c_state = COLORS["status_overdue"]

        # 1. Periodo
        ctk.CTkLabel(self.scroll_frame, text=period.periodo_id, font=("Segoe UI", 12, "bold")).grid(row=self.scroll_frame.grid_size()[1], column=0, sticky="w", padx=5, pady=5)
        
        # 2. Estado (Label Colored)
        state_str = period.estado.value if hasattr(period.estado, "value") else str(period.estado)
        ctk.CTkLabel(self.scroll_frame, text=state_str, text_color=c_state).grid(row=self.scroll_frame.grid_size()[1]-1, column=1, sticky="w", padx=5)

        # 3. Fecha Cierre
        cierre = period.fecha_cierre.strftime("%d/%m/%Y") if period.fecha_cierre else "-"
        ctk.CTkLabel(self.scroll_frame, text=cierre).grid(row=self.scroll_frame.grid_size()[1]-1, column=2, sticky="w", padx=5)
        
        # 4. Responsable (Disabled - Field missing in DB)
        # resp = getattr(period, 'usuario_responsable', None) or "-"
        resp = "-"
        ctk.CTkLabel(self.scroll_frame, text=resp).grid(row=self.scroll_frame.grid_size()[1]-1, column=3, sticky="w", padx=5)
        
        # 5. Notas (Truncated)
        notas = period.notas or ""
        short_notes = (notas[:25] + '...') if len(notas) > 25 else notas
        ctk.CTkLabel(self.scroll_frame, text=short_notes, text_color="gray").grid(row=self.scroll_frame.grid_size()[1]-1, column=4, sticky="w", padx=5)

        # 6. Acciones Frame
        f_actions = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        f_actions.grid(row=self.scroll_frame.grid_size()[1]-1, column=5, sticky="e", padx=5)
        
        ctk.CTkButton(f_actions, text="✎", width=30, fg_color="gray", command=lambda p=period: self.open_edit_dialog(p)).pack(side="left", padx=2)
        ctk.CTkButton(f_actions, text="🗑", width=30, fg_color=COLORS["status_overdue"], command=lambda p=period: self.delete_period(p)).pack(side="left", padx=2)

    def delete_period(self, period):
        if messagebox.askyesno("Confirmar Eliminación", f"¿Está seguro de eliminar el período {period.periodo_id}?\nEsta acción es irreversible."):
            try:
                if PeriodService.delete_period(period.periodo_id):
                    self.load_periods()
                    messagebox.showinfo("Éxito", "Período eliminado.")
            except AppIntegrityError as e:
                # Force delete flow
                if messagebox.askyesno("⚠️ Registros Activos", f"{str(e)}\n\n¿Desea eliminar el período eliminando TAMBIÉN todos sus registros asociados? (Irreversible)"):
                    try:
                        if PeriodService.delete_period(period.periodo_id, force=True):
                            self.load_periods()
                            messagebox.showinfo("Éxito", "Período y registros eliminados.")
                    except Exception as e2:
                        messagebox.showerror("Error", f"Fallo eliminación forzada: {e2}")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo eliminar:\n{e}")

    def open_create_dialog(self):
        CreatePeriodDialog(self)

    def open_edit_dialog(self, period):
        EditPeriodDialog(self, period)


class CreatePeriodDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Nuevo Período")
        self.geometry("300x250")
        
        # UI Focus Fix
        self.lift()
        self.focus_force()
        self.attributes("-topmost", True)
        
        # Center
        from utils.gui_helpers import center_window
        self.update_idletasks()
        self.after(10, lambda: center_window(self, parent))
        
        self.parent = parent
        
        ctk.CTkLabel(self, text="Año:").pack(pady=5)
        self.entry_year = ctk.CTkEntry(self)
        self.entry_year.insert(0, str(date.today().year))
        self.entry_year.pack()
        
        ctk.CTkLabel(self, text="Mes:").pack(pady=5)
        self.entry_month = ctk.CTkEntry(self)
        self.entry_month.insert(0, str(date.today().month))
        self.entry_month.pack()
        
        ctk.CTkButton(self, text="Crear", command=self.save, fg_color=COLORS["primary_button"]).pack(pady=20)
        
        self.transient(parent)
        self.grab_set()

    def save(self):
        try:
            y = int(self.entry_year.get())
            m = int(self.entry_month.get())
            if not (1 <= m <= 12): raise ValueError("Mes inválido")
            
            PeriodService.create_period(y, m)
            self.parent.load_periods()
            self.destroy()
        except ValueError as ve:
             messagebox.showerror("Error", str(ve))
        except Exception as e:
             messagebox.showerror("Error", f"Fallo creación: {e}")

class EditPeriodDialog(ctk.CTkToplevel):
    def __init__(self, parent, period):
        super().__init__(parent)
        self.title(f"Modificar Período {period.periodo_id}")
        self.geometry("400x450")
        
        # UI Focus Fix
        self.lift()
        self.focus_force()
        self.attributes("-topmost", True)
        
        self.parent = parent
        self.period = period
        
        ctk.CTkLabel(self, text="Estado:").pack(pady=5)
        vals = [e.value for e in EstadoPeriodo]
        self.combo_status = ctk.CTkComboBox(self, values=vals)
        
        current_val = period.estado.value if hasattr(period.estado, "value") else str(period.estado)
        self.combo_status.set(current_val)
        self.combo_status.pack()
        
        ctk.CTkLabel(self, text="Notas de Auditoría:").pack(pady=5)
        self.txt_notes = ctk.CTkTextbox(self, height=100)
        if period.notas: self.txt_notes.insert("1.0", period.notas)
        self.txt_notes.pack(padx=20, fill="x")
        
        # ctk.CTkLabel(self, text="Responsable:").pack(pady=5)
        # self.entry_user = ctk.CTkEntry(self)
        # if hasattr(period, 'usuario_responsable') and period.usuario_responsable: 
        #    self.entry_user.insert(0, period.usuario_responsable)
        # self.entry_user.pack()

        ctk.CTkButton(self, text="Guardar Cambios", command=self.save, fg_color=COLORS["primary_button"]).pack(pady=20)
        
        self.transient(parent)
        self.grab_set()

    def save(self):
        try:
            new_status_str = self.combo_status.get()
            new_enum = next((e for e in EstadoPeriodo if e.value == new_status_str), None)
            notes = self.txt_notes.get("1.0", "end-1c")
            user = None
            
            # Security Confirm
            if new_enum == EstadoPeriodo.ABIERTO and self.period.estado != EstadoPeriodo.ABIERTO:
                 if not messagebox.askyesno("Advertencia Seguridad", "¿Está seguro de RE-ABRIR este período?\nEsto permitirá modificaciones históricas."):
                     return

            if PeriodService.update_period(self.period.periodo_id, new_enum, notes, user):
                self.parent.load_periods()
                self.destroy()
            else:
                messagebox.showerror("Error", "No se pudo actualizar.")
        except Exception as e:
            messagebox.showerror("Error", f"Fallo actualización: {e}")


