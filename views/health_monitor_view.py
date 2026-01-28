
import customtkinter as ctk
import threading
from config import COLORS, FONTS
from services.health_check_service import HealthCheckService

class HealthMonitorView(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Monitor de Integridad del Sistema 🩺")
        self.geometry("500x500")
        
        self.service = HealthCheckService()
        
        # Modal
        self.transient(parent)
        self.lift()
        self.focus_set()
        
        self._init_ui()
        self.after(500, self.run_checks) # Auto run after show
        
    def _init_ui(self):
        # Header
        self.header = ctk.CTkFrame(self, height=80, fg_color="transparent")
        self.header.pack(fill="x", padx=20, pady=20)
        
        self.lbl_status = ctk.CTkLabel(self.header, text="Analizando...", font=("Segoe UI", 24, "bold"))
        self.lbl_status.pack()
        
        self.lbl_desc = ctk.CTkLabel(self.header, text="Ejecutando protocolos de prueba...", text_color="gray")
        self.lbl_desc.pack()
        
        # Progress
        self.progress = ctk.CTkProgressBar(self)
        self.progress.pack(fill="x", padx=40, pady=10)
        self.progress.start()
        
        # Results List
        self.scroll = ctk.CTkScrollableFrame(self, label_text="Protocolos de Prueba")
        self.scroll.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Close Button
        self.btn_close = ctk.CTkButton(self, text="Cerrar", command=self.destroy, state="disabled")
        self.btn_close.pack(pady=20)
        
    def run_checks(self):
        # Thread to simulate 'scanning' visual and not freeze UI
        threading.Thread(target=self._execute_service, daemon=True).start()
        
    def _execute_service(self):
        import time
        time.sleep(1) # Fake delay for dramatic effect "Analyzing..."
        
        report = self.service.run_diagnostics()
        
        self.after(0, lambda: self._show_results(report))
        
    def _show_results(self, report):
        self.progress.stop()
        self.progress.pack_forget()
        self.btn_close.configure(state="normal")
        
        status = report["status"]
        msg = report["message"]
        
        # Update Header
        color = COLORS["status_paid"] if status == "GREEN" else (COLORS["status_pending"] if status == "YELLOW" else COLORS["status_overdue"])
        icon = "✅" if status == "GREEN" else ("⚠️" if status == "YELLOW" else "❌")
        
        self.lbl_status.configure(text=f"{icon} {status} STATUS", text_color=color)
        self.lbl_desc.configure(text=msg)
        
        # Render Tests
        for t in report["tests"]:
            row = ctk.CTkFrame(self.scroll, fg_color="transparent")
            row.pack(fill="x", pady=5)
            
            t_icon = "✅" if t["status"] == "OK" else "❌"
            t_col = COLORS["text_primary"] if t["status"] == "OK" else COLORS["status_overdue"]
            
            ctk.CTkLabel(row, text=t_icon, font=("Segoe UI", 16)).pack(side="left", padx=10)
            
            info = ctk.CTkFrame(row, fg_color="transparent")
            info.pack(side="left", fill="x")
            
            ctk.CTkLabel(info, text=t["name"], font=("Segoe UI", 12, "bold"), text_color=t_col).pack(anchor="w")
            ctk.CTkLabel(info, text=t["details"], font=("Segoe UI", 11), text_color="gray").pack(anchor="w")


