import customtkinter as ctk
from datetime import date, timedelta
from config import COLORS, FONTS

class TimeNavigatorView(ctk.CTkFrame):
    def __init__(self, master, on_change_command=None, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(fg_color="transparent")
        
        self.on_change = on_change_command
        self.current_date = date.today().replace(day=1) # Always 1st of month

        # Layout
        self.btn_prev = ctk.CTkButton(self, text="<<", width=40, command=self.go_prev, fg_color=COLORS["secondary_button"])
        self.btn_prev.pack(side="left", padx=5)

        self.lbl_period = ctk.CTkLabel(self, text=self.format_label(), font=("Segoe UI", 16, "bold"), width=150, text_color=COLORS["text_primary"])
        self.lbl_period.pack(side="left", padx=5)

        self.btn_next = ctk.CTkButton(self, text=">>", width=40, command=self.go_next, fg_color=COLORS["secondary_button"])
        self.btn_next.pack(side="left", padx=5)
        
        # Status Icon (Lock/Open)
        self.lbl_status = ctk.CTkLabel(self, text="🔓", font=("Segoe UI", 16))
        self.lbl_status.pack(side="left", padx=10)

    def format_label(self):
        months = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        m = months[self.current_date.month - 1]
        return f"{m} {self.current_date.year}"

    def go_prev(self):
        # Subtract one month
        # Logic: First day of previous month
        self.current_date = (self.current_date.replace(day=1) - timedelta(days=1)).replace(day=1)
        self.update_ui()
        if self.on_change: self.on_change(self.current_date)

    def go_next(self):
        # Add one month logic
        # Logic: First day of next month
        next_date = (self.current_date.replace(day=1) + timedelta(days=32)).replace(day=1)
        
        # Check Max Constraint
        if hasattr(self, 'max_date') and self.max_date:
             # Just compare Month/Year
             if next_date > self.max_date.replace(day=1):
                 # We are at the edge. If ON_NEW handler exists, trigger it?
                 if hasattr(self, 'on_new_period_command') and self.on_new_period_command:
                     self.on_new_period_command()
                 return # Block navigation
                 
        self.current_date = next_date
        self.update_ui()
        if self.on_change: self.on_change(self.current_date)

    def set_bounds(self, min_date, max_date, on_new_period_command=None):
        self.min_date = min_date
        self.max_date = max_date
        self.on_new_period_command = on_new_period_command
        self.update_ui()

    def set_date(self, new_date):
        """External setter to sync navigator"""
        self.current_date = new_date.replace(day=1)
        self.update_ui()
        # Trigger callback? Usually yes if external set implies "Go there"
        if self.on_change: self.on_change(self.current_date)

    def update_ui(self, *args):
        self.lbl_period.configure(text=self.format_label())
        
        # Enable/Disable Buttons based on bounds
        if hasattr(self, 'min_date') and self.min_date:
             prev_month = (self.current_date.replace(day=1) - timedelta(days=1)).replace(day=1)
             if prev_month < self.min_date.replace(day=1):
                 self.btn_prev.configure(state="disabled", fg_color="gray")
             else:
                 self.btn_prev.configure(state="normal", fg_color=COLORS["secondary_button"])

        if hasattr(self, 'max_date') and self.max_date:
             next_month = (self.current_date.replace(day=1) + timedelta(days=32)).replace(day=1)
             if next_month > self.max_date.replace(day=1):
                 # Check if we have a "New Period" command
                 if hasattr(self, 'on_new_period_command') and self.on_new_period_command:
                     self.btn_next.configure(state="normal", text="+", fg_color=COLORS["primary_button"]) # Show + icon
                 else:
                     self.btn_next.configure(state="disabled", text=">>", fg_color="gray")
             else:
                 self.btn_next.configure(state="normal", text=">>", fg_color=COLORS["secondary_button"])


    def set_lock_status(self, is_locked: bool):
        icon = "🔒" if is_locked else "🔓"
        color = COLORS["status_overdue"] if is_locked else COLORS["status_paid"]
        self.lbl_status.configure(text=icon, text_color=color)


