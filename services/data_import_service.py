
import pandas as pd
import os
from datetime import datetime
from utils.logger import app_logger

from utils.format_helper import parse_localized_float, parse_fuzzy_date

class DataImportService:
    """
    Service responsible for reading files (Excel, CSV, HTML-XLS) and normalizing them
    into a standard list of transaction dictionaries.
    """

    def load_and_normalize(self, file_path, mapping_config):
        """
        Main entry point. reads file, applies mapping, returns standard list.
        Returns: (success: bool, data: list, message: str)
        """
        try:
            # 1. Load Raw DataFrame (The "Gatekeeper" logic)
            df = self._load_file_robust(file_path, mapping_config.get('header_row', 0))
            
            if df is None or df.empty:
                return False, [], "El archivo está vacío o no se pudo leer."

            # 2. Normalize Columns
            transactions = []
            errors = []
            
            # Normalize Loop
            for index, row in df.iterrows():
                try:
                    # Date
                    raw_date = row.get(mapping_config.get('fecha'))
                    date_val = parse_fuzzy_date(raw_date)
                    
                    if not date_val: continue # Skip invalid dates

                    # Amount
                    final_amount = 0.0
                    col_imp = mapping_config.get('importe')
                    col_deb = mapping_config.get('debito')
                    col_cred = mapping_config.get('credito')

                    if col_deb and col_cred and col_deb in row and col_cred in row:
                        v_deb = parse_localized_float(row.get(col_deb))
                        v_cred = parse_localized_float(row.get(col_cred))
                        if v_deb > 0: final_amount = -abs(v_deb)
                        elif v_cred > 0: final_amount = abs(v_cred)
                    elif col_imp and col_imp in row:
                        raw_imp = row.get(col_imp)
                        final_amount = parse_localized_float(raw_imp)
                        # Check specific negative sign indicators if string
                        if isinstance(raw_imp, str) and '-' in raw_imp:
                             final_amount = -abs(final_amount)

                    # Description
                    desc = str(row.get(mapping_config.get('descripcion'), ""))

                    transactions.append({
                        "date": date_val,
                        "description": desc,
                        "amount": final_amount,
                        "raw_row_index": index
                    })

                except Exception as e_row:
                    errors.append(f"Row {index}: {str(e_row)}")

            if not transactions:
                return False, [], "No se encontraron transacciones válidas. Verifique el mapeo de columnas."

            return True, transactions, f"Cargados {len(transactions)} movimientos."

        except Exception as e:
            app_logger.error(f"Import Error: {e}")
            return False, [], str(e)

    def _load_file_robust(self, file_path, header_row):
        """Attempts to load file using multiple strategies."""
        import os
        ext = os.path.splitext(file_path)[1].lower()
        
        # Strategy A: Excel Native (openpyxl)
        try:
            # Try forcing Excel if extension matches or generally
            return pd.read_excel(file_path, header=header_row) # Let pandas auto-engine (usually openpyxl for xlsx, xlrd for xls)
        except Exception:
            pass
            
        # Strategy B: HTML (Fake Excel)
        try:
            dfs = pd.read_html(file_path, header=header_row)
            if dfs: return dfs[0]
        except Exception:
            pass
            
        # Strategy C: CSV / Text (The Fallback)
        try:
            # Sniff delimiter
            delimiter = ','
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    for _ in range(header_row): f.readline()
                    sample = f.read(1024)
                    import csv
                    dialect = csv.Sniffer().sniff(sample)
                    delimiter = dialect.delimiter
            except Exception: pass
            
            return pd.read_csv(file_path, sep=delimiter, header=header_row, encoding='utf-8')
        except Exception as e_csv:
            raise Exception(f"Failed to load file. Formats tried: Excel, HTML, CSV. Last error: {e_csv}")
