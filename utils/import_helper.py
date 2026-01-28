import pandas as pd
import os
from utils.logger import app_logger

def format_currency(value):
    """
    Formats a float to '1.234,56' style (Argentina/Euro).
    """
    if value is None: return "0,00"
    try:
        val = float(value)
        # Format as 1,234.56 then swap
        return "{:,.2f}".format(val).replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return str(value)

def load_data_file(file_path, file_format="CSV", header_row=0, delimiter=None):
    """
    Unified loader for CSV and Excel files.
    - Handles 'header_row' (0-indexed).
    - Auto-detects delimiter if None for CSV.
    - Returns DataFrame with all columns as string to avoid type inference issues.
    """
    try:
        ext = os.path.splitext(file_path)[1].lower()
        app_logger.debug(f"Loading file '{file_path}' (Ext: {ext})")
        
        # Override format based on extension if obvious
        if ext in ['.xlsx', '.xls']:
            file_format = "EXCEL"
        
        if file_format.upper() == "EXCEL":
            # Excel check
            # Do NOT force dtype=str for Excel, let it detect Dates correctly
            df = pd.read_excel(file_path, header=header_row)
        else:
            # CSV Default
            # CSV Default
            # Try robust auto-detection
            try:
                # First try with python engine which supports auto-detect
                df = pd.read_csv(file_path, sep=None, engine='python', header=header_row, encoding='utf-8', dtype=str)
            except Exception:
                # Fallback to standard (sometimes python engine is stricter on quoting)
                # Try common delimiters
                try:
                    df = pd.read_csv(file_path, sep=';', header=header_row, encoding='utf-8', dtype=str)
                except Exception:
                    df = pd.read_csv(file_path, sep=',', header=header_row, encoding='utf-8', dtype=str)
            
        return df.fillna("")
    except Exception as e:
        raise Exception(f"File Load Error: {e}")




