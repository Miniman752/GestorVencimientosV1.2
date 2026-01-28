import tkinter as tk
import customtkinter as ctk
from config import THEME_COLOR
from database import init_db, SessionLocal
from utils.logger import app_logger
from views.main_window import MainWindow
# Force import to ensure PyInstaller detects it
import controllers.forex_controller

def main():
    # --- Console Detachment (Frozen Mode) ---
    import sys
    import multiprocessing
    
    # Required for Windows frozen apps
    multiprocessing.freeze_support()
    
    import logging
    if getattr(sys, 'frozen', False):
         # Remove StreamHandlers to prevent recursion (Log -> Stdout -> Log -> ...)
         handlers = app_logger.handlers[:]
         for handler in handlers:
             if isinstance(handler, logging.StreamHandler):
                 app_logger.removeHandler(handler)

         # Redirect stdout/stderr to logger
         class LogWriter:
             def __init__(self, level): 
                 self.level = level
                 self.encoding = 'utf-8' # Fix for some logging calls checking encoding
             def write(self, message): 
                 if message.strip(): 
                     try:
                         # Prevent recursion if logging itself fails or if library writes to stderr
                         # We skip standard logging flow if it looks like a recursive call
                         self.level(message.strip())
                     except Exception:
                         pass # Safe fallback
             def flush(self): pass
         
         sys.stdout = LogWriter(app_logger.info)
         sys.stderr = LogWriter(app_logger.error)
         
    # --- Supress Known Matplotlib Warnings to avoid Infinite loops ---
    import warnings
    warnings.filterwarnings("ignore", module="matplotlib")
    warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib")
    
    # Inicializar Base de Datos
    app_logger.info("Iniciando aplicación Gestor de Vencimientos...")
    init_db()
    
    # MIGRATION: Auto-assign logic
    from services.migration_service import MigrationService
    MigrationService.run_startup_migrations()
    
    # Configuración de CustomTkinter
    ctk.set_appearance_mode("Light")
    ctk.set_default_color_theme(THEME_COLOR)

    # --- Global Error Handling (Zero-Crash Policy) ---
    import sys
    import traceback
    from tkinter import messagebox

    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        # Recursion Guard
        if exc_type is RecursionError:
             print("CRITICAL: Redispatched RecursionError. Suppressing UI.")
             return

        err_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        app_logger.error(f"Uncaught Exception:\n{err_msg}")
        
        # Show friendly dialog
        messagebox.showerror("Error Inesperado", f"Ha ocurrido un error no controlado:\n\n{exc_value}\n\nConsulte el log para más detalles.")

    sys.excepthook = handle_exception
    # -----------------------------------------------

    # 1. Ensure Auth System Ready
    from services.auth_service import AuthService
    if AuthService.ensure_admin_exists():
        messagebox.showinfo("Bienvenido - Primer Inicio", 
                          "Se ha creado un usuario Administrador por defecto.\n\n"
                          "👤 Usuario: admin\n"
                          "🔑 Clave: admin\n\n"
                          "Por favor, cambie su contraseña ingresando al menú 'Usuarios'.")

    
    # 2. Main Window (Handles Login internally)
    app = MainWindow()
    app.report_callback_exception = handle_exception
    app.mainloop()


if __name__ == "__main__":
    main()