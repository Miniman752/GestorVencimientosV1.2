import customtkinter as ctk
from config import COLORS, FONTS

def center_window(window, parent):
    """
    Centers a Toplevel window relative to its parent.
    """
    window.update_idletasks()
    try:
        width = window.winfo_width()
        height = window.winfo_height()
        # Calculate position relative to parent
        x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (width // 2)
        y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (height // 2)
        window.geometry(f'+{x}+{y}')
    except Exception:
        pass

def create_header(parent, title, subtitle=None):
    """
    Creates a standard header with title and subtitle.
    """
    header_frame = ctk.CTkFrame(parent, fg_color="transparent")
    header_frame.pack(fill="x", padx=20, pady=10)
    
    ctk.CTkLabel(header_frame, text=title, font=FONTS["heading"], text_color=COLORS["primary_button"]).pack(side="left")
    
    if subtitle:
        ctk.CTkLabel(header_frame, text=f"  |  {subtitle}", font=FONTS["body"], text_color="gray").pack(side="left", padx=10, pady=(5,0))
    
    return header_frame

